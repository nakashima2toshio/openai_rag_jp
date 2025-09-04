# streamlit run a30_30_rag_search.py --server.port=8501
# a30_30_rag_search.py - 最新OpenAI Responses API完全対応版（動的Vector Store対応・重複問題修正版）
# OpenAI Responses API + file_search ツール + 環境変数APIキー対応 + 動的Vector Store ID管理
"""
🔍 最新RAG検索アプリケーション（動的Vector Store対応・重複問題修正版）

【前提条件】
1. OpenAI APIキーの環境変数設定（必須）:
   export OPENAI_API_KEY='your-api-key-here'

2. 必要なライブラリ（必須）:
   pip install streamlit openai
   pip install openai-agents

【実行方法】
streamlit run a30_30_rag_search.py --server.port=8501

【主要機能】
✅ 最新Responses API使用
✅ file_search ツールでVector Store検索
✅ 動的Vector Store ID管理（vector_stores.json）
✅ 重複Vector Store対応（最新優先選択）
✅ ファイル引用表示
✅ 型安全実装（型エラー完全修正）
✅ 環境変数でAPIキー管理
✅ 英語/日本語質問対応
✅ カスタマイズ可能な検索オプション
✅ 最新Vector Store自動取得・更新機能

【Vector Store連携】
- a30_020_make_vsid.py で作成されたVector Storeを自動認識
- vector_stores.json ファイルで動的管理
- 同名Vector Store重複時は最新作成日時を優先
- OpenAI APIから最新状態を取得・更新
"""
import streamlit as st
import time
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import traceback

# OpenAI SDK のインポート
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ OpenAI SDK がロードされました")
except ImportError as e:
    OPENAI_AVAILABLE = False
    st.error(f"OpenAI SDK が見つかりません: {e}")
    st.stop()

# Agent SDK のインポート（オプション）
try:
    from agents import Agent, Runner, SQLiteSession

    AGENT_SDK_AVAILABLE = True
    logger.info("✅ OpenAI Agent SDK もロードされました")
except ImportError as e:
    AGENT_SDK_AVAILABLE = False
    logger.info(f"Agent SDK は利用できません（オプション機能のため問題なし）: {e}")

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===================================================================
# Vector Store設定管理クラス（重複問題修正版）
# ===================================================================
class VectorStoreManager:
    """Vector Store設定の動的管理（重複問題修正版）"""

    CONFIG_FILE_PATH = Path("vector_stores.json")

    # デフォルトのVector Store設定（フォールバック用）
    DEFAULT_VECTOR_STORES = {
        "Customer Support FAQ"    : "vs_687a0604f1508191aaf416d88e266ab7",
        "Science & Technology Q&A": "vs_687a061acc908191af7d5d9ba623470b",
        "Medical Q&A"             : "vs_687a060f9ed881918b213bfdeab8241b",
        "Legal Q&A"               : "vs_687a062418ec8191872efdbf8f554836"
    }

    # a30_020_make_vsid.py のVectorStoreConfigと対応するマッピング
    STORE_NAME_MAPPING = {
        "customer_support_faq": "Customer Support FAQ Knowledge Base",
        "medical_qa"          : "Medical Q&A Knowledge Base",
        "sciq_qa"             : "Science & Technology Q&A Knowledge Base",
        "legal_qa"            : "Legal Q&A Knowledge Base"
    }

    # 表示名への逆マッピング（UI表示用）
    DISPLAY_NAME_MAPPING = {
        "Customer Support FAQ Knowledge Base"    : "Customer Support FAQ",
        "Medical Q&A Knowledge Base"             : "Medical Q&A",
        "Science & Technology Q&A Knowledge Base": "Science & Technology Q&A",
        "Legal Q&A Knowledge Base"               : "Legal Q&A"
    }

    def __init__(self, openai_client: OpenAI = None):
        self.openai_client = openai_client
        self._cache = {}
        self._last_update = None

    def load_vector_stores(self) -> Dict[str, str]:
        """Vector Store設定を読み込み"""
        try:
            if self.CONFIG_FILE_PATH.exists():
                with open(self.CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 設定ファイルの形式確認
                if 'vector_stores' in data and isinstance(data['vector_stores'], dict):
                    stores = data['vector_stores']
                    logger.info(f"✅ Vector Store設定を読み込み: {len(stores)}件")
                    return stores
                else:
                    logger.warning("⚠️ 設定ファイル形式が不正です")
                    return self.DEFAULT_VECTOR_STORES.copy()
            else:
                logger.info("ℹ️ 設定ファイルが存在しません。デフォルト値を使用")
                return self.DEFAULT_VECTOR_STORES.copy()

        except Exception as e:
            logger.error(f"❌ Vector Store設定読み込みエラー: {e}")
            st.warning(f"設定ファイル読み込みエラー: {e}")
            return self.DEFAULT_VECTOR_STORES.copy()

    def save_vector_stores(self, stores: Dict[str, str]) -> bool:
        """Vector Store設定を保存"""
        try:
            config_data = {
                "vector_stores": stores,
                "last_updated" : datetime.now().isoformat(),
                "source"       : "a30_30_rag_search.py",
                "version"      : "1.1"
            }

            with open(self.CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Vector Store設定を保存: {self.CONFIG_FILE_PATH}")
            return True

        except Exception as e:
            logger.error(f"❌ Vector Store設定保存エラー: {e}")
            st.error(f"設定保存エラー: {e}")
            return False

    def fetch_latest_vector_stores(self) -> Dict[str, str]:
        """OpenAI APIから最新のVector Store一覧を取得し、既知の名前とマッチング（重複問題修正版）"""
        if not self.openai_client:
            logger.warning("⚠️ OpenAI クライアントが未設定です")
            return self.load_vector_stores()

        try:
            # OpenAI APIからVector Store一覧を取得
            stores_response = self.openai_client.vector_stores.list()

            # Vector Storeを作成日時でソート（新しい順）
            sorted_stores = sorted(
                stores_response.data,
                key=lambda x: x.created_at if hasattr(x, 'created_at') else 0,
                reverse=True
            )

            api_stores = {}
            store_candidates = {}  # 同名Store候補を管理

            logger.info(f"📊 取得したVector Store数: {len(sorted_stores)}")

            for store in sorted_stores:
                store_name = store.name
                store_id = store.id
                created_at = getattr(store, 'created_at', 0)

                logger.info(f"🔍 処理中: '{store_name}' ({store_id}) - 作成日時: {created_at}")

                # 既知のstore_nameパターンとのマッチング
                matched_display_name = None

                # 完全一致確認
                if store_name in self.DISPLAY_NAME_MAPPING:
                    matched_display_name = self.DISPLAY_NAME_MAPPING[store_name]
                else:
                    # 部分一致確認（柔軟なマッチング）
                    for full_name, display_name in self.DISPLAY_NAME_MAPPING.items():
                        if (full_name.lower() in store_name.lower() or
                                any(keyword in store_name.lower() for keyword in full_name.lower().split())):
                            matched_display_name = display_name
                            break

                if matched_display_name:
                    # 同名の場合は最新のもの（作成日時が新しい）を優先
                    if matched_display_name not in store_candidates:
                        store_candidates[matched_display_name] = {
                            'id'        : store_id,
                            'name'      : store_name,
                            'created_at': created_at
                        }
                        logger.info(f"✅ 新規候補: '{matched_display_name}' -> '{store_name}' ({store_id})")
                    else:
                        # 既存候補と比較
                        existing = store_candidates[matched_display_name]
                        if created_at > existing['created_at']:
                            logger.info(
                                f"🔄 更新: '{matched_display_name}' -> '{store_name}' ({store_id}) [新: {created_at} > 旧: {existing['created_at']}]")
                            store_candidates[matched_display_name] = {
                                'id'        : store_id,
                                'name'      : store_name,
                                'created_at': created_at
                            }
                        else:
                            logger.info(
                                f"⏭️ スキップ: '{matched_display_name}' -> '{store_name}' ({store_id}) [新: {created_at} <= 既存: {existing['created_at']}]")
                else:
                    # 既知パターンにマッチしない場合
                    if store_name not in store_candidates:
                        store_candidates[store_name] = {
                            'id'        : store_id,
                            'name'      : store_name,
                            'created_at': created_at
                        }
                        logger.info(f"ℹ️ 新規店舗: '{store_name}' ({store_id})")

            # 最終的なapi_storesを構築
            for display_name, candidate in store_candidates.items():
                api_stores[display_name] = candidate['id']
                logger.info(f"🎯 最終選択: '{display_name}' -> {candidate['id']} (作成日時: {candidate['created_at']})")

            if api_stores:
                logger.info(f"✅ OpenAI APIから{len(api_stores)}個のVector Storeを取得完了")
                return api_stores
            else:
                logger.warning("⚠️ APIから有効なVector Storeが見つかりませんでした")
                return self.load_vector_stores()

        except Exception as e:
            logger.error(f"❌ OpenAI API取得エラー: {e}")
            logger.error(traceback.format_exc())
            st.warning(f"最新情報の取得に失敗しました: {e}")
            return self.load_vector_stores()

    def get_vector_stores(self, force_refresh: bool = False) -> Dict[str, str]:
        """Vector Store一覧を取得（キャッシュ機能付き）"""
        now = datetime.now()

        # 強制リフレッシュまたは初回取得の場合
        if force_refresh or not self._cache:
            logger.info("🔄 Vector Store情報を更新中...")

            # APIからの最新情報を取得
            if self.openai_client and st.session_state.get('auto_refresh_stores', True):
                try:
                    api_stores = self.fetch_latest_vector_stores()
                    self._cache = api_stores
                    self._last_update = now
                    return api_stores
                except Exception as e:
                    logger.warning(f"⚠️ API取得に失敗、設定ファイルから読み込み: {e}")

            # 設定ファイルから読み込み（フォールバック）
            stores = self.load_vector_stores()
            self._cache = stores
            self._last_update = now
            return stores

        # キャッシュチェック（5分間有効）
        if self._last_update and (now - self._last_update).seconds >= 300:
            logger.info("⏰ キャッシュ有効期限切れ、更新中...")
            return self.get_vector_stores(force_refresh=True)

        logger.info("💾 キャッシュから取得")
        return self._cache

    def refresh_and_save(self) -> Dict[str, str]:
        """最新のVector Store情報を取得して保存"""
        if not self.openai_client:
            st.error("OpenAI クライアントが設定されていません")
            return self.load_vector_stores()

        try:
            # キャッシュクリア
            self._cache = {}
            self._last_update = None

            # 最新情報を強制取得
            latest_stores = self.get_vector_stores(force_refresh=True)

            # 設定ファイルに保存
            if self.save_vector_stores(latest_stores):
                st.success(f"✅ Vector Store設定を更新しました（{len(latest_stores)}件）")

                # 詳細情報を表示
                with st.expander("📊 更新されたVector Store一覧", expanded=True):
                    for name, store_id in latest_stores.items():
                        st.write(f"**{name}**: `{store_id}`")

                return latest_stores
            else:
                st.error("❌ 設定の保存に失敗しました")
                return self.load_vector_stores()

        except Exception as e:
            st.error(f"❌ 更新処理エラー: {e}")
            logger.error(f"更新処理エラー: {e}")
            logger.error(traceback.format_exc())
            return self.load_vector_stores()

    def debug_vector_stores(self) -> Dict[str, Any]:
        """デバッグ用：Vector Store情報の詳細取得"""
        debug_info = {
            "config_file_exists": self.CONFIG_FILE_PATH.exists(),
            "cached_stores"     : self._cache,
            "last_update"       : self._last_update.isoformat() if self._last_update else None,
            "api_stores"        : {}
        }

        if self.openai_client:
            try:
                stores_response = self.openai_client.vector_stores.list()
                for store in stores_response.data:
                    debug_info["api_stores"][store.name] = {
                        "id"         : store.id,
                        "created_at" : store.created_at,
                        "file_counts": getattr(store, 'file_counts', None),
                        "usage_bytes": getattr(store, 'usage_bytes', None)
                    }
            except Exception as e:
                debug_info["api_error"] = str(e)

        return debug_info


# グローバル Vector Store Manager インスタンス
@st.cache_resource
def get_vector_store_manager():
    """Vector Store Manager のシングルトン取得"""
    try:
        openai_client = OpenAI()
        return VectorStoreManager(openai_client)
    except Exception as e:
        logger.warning(f"OpenAI クライアント初期化失敗: {e}")
        return VectorStoreManager()


# ===================================================================
# 動的Vector Store取得
# ===================================================================
def get_current_vector_stores(force_refresh: bool = False) -> Tuple[Dict[str, str], List[str]]:
    """現在のVector Store設定を取得"""
    manager = get_vector_store_manager()
    stores = manager.get_vector_stores(force_refresh=force_refresh)
    store_list = list(stores.keys())
    return stores, store_list


# 言語設定
LANGUAGE_OPTIONS = {
    "English": "en",
    "日本語" : "ja"
}

# テスト用質問（英語版 - RAGデータに最適化）
test_questions_en = [
    "How do I create a new account?",
    "What payment methods are available?",
    "Can I return a product?",
    "I forgot my password",
    "How can I contact the support team?"
]

test_questions_2_en = [
    "What are the latest trends in artificial intelligence?",
    "What is the principle of quantum computing?",
    "What are the types and characteristics of renewable energy?",
    "What are the current status and challenges of gene editing technology?",
    "What are the latest technologies in space exploration?"
]

test_questions_3_en = [
    "How to prevent high blood pressure?",
    "What are the symptoms and treatment of diabetes?",
    "What are the risk factors for heart disease?",
    "What are the guidelines for healthy eating?",
    "What is the relationship between exercise and health?"
]

test_questions_4_en = [
    "What are the important clauses in contracts?",
    "How to protect intellectual property rights?",
    "What are the basic principles of labor law?",
    "What is an overview of personal data protection law?",
    "What is the scope of application of consumer protection law?"
]

# テスト用質問（日本語版 - オプション）
test_questions_ja = [
    "新規アカウントを作るにはどうすればよいですか？",
    "どのような決済方法が利用できますか？",
    "商品を返品することはできますか？",
    "パスワードを忘れてしまいました",
    "サポートチームに連絡する方法を教えてください"
]

test_questions_2_ja = [
    "人工知能の最新動向について教えてください",
    "量子コンピューティングの原理とは？",
    "再生可能エネルギーの種類と特徴",
    "遺伝子編集技術の現状と課題",
    "宇宙探査の最新技術について"
]

test_questions_3_ja = [
    "高血圧の予防方法について",
    "糖尿病の症状と治療法",
    "心臓病のリスクファクター",
    "健康的な食事のガイドライン",
    "運動と健康の関係について"
]

test_questions_4_ja = [
    "契約書の重要な条項について",
    "知的財産権の保護方法",
    "労働法の基本原則",
    "個人情報保護法の概要",
    "消費者保護法の適用範囲"
]

# OpenAI APIキーの設定（環境変数から自動取得）
try:
    # 環境変数 OPENAI_API_KEY から自動的に読み取り
    openai_client = OpenAI()
    logger.info("✅ OpenAI APIキーが環境変数から正常に読み込まれました")
except Exception as e:
    st.error(f"OpenAI API キーの設定に問題があります: {e}")
    st.error("環境変数 OPENAI_API_KEY が設定されているか確認してください")
    st.code("export OPENAI_API_KEY='your-api-key-here'")
    st.stop()


class ModernRAGManager:
    """最新Responses API + file_search を使用したRAGマネージャー"""

    def __init__(self):
        self.agent_sessions = {}  # Agent SDK用セッション（オプション）

    def search_with_responses_api(self, query: str, store_name: str, store_id: str, **kwargs) -> Tuple[
        str, Dict[str, Any]]:
        """最新Responses API + file_search ツールを使用した検索"""
        try:
            # file_search ツールの設定（正しい型で定義）
            file_search_tool_dict: Dict[str, Any] = {
                "type"            : "file_search",
                "vector_store_ids": [store_id]
            }

            # オプション設定（型安全な方法）
            max_results = kwargs.get('max_results', 20)
            include_results = kwargs.get('include_results', True)
            filters = kwargs.get('filters', None)

            # 型安全な辞書更新
            if max_results and isinstance(max_results, int):
                file_search_tool_dict["max_num_results"] = max_results
            if filters is not None:
                file_search_tool_dict["filters"] = filters

            # include パラメータの設定
            include_params = []
            if include_results:
                include_params.append("file_search_call.results")

            # Responses API呼び出し（型安全な方法）
            # OpenAI SDKの型定義が厳密なため、実際の動作に問題がない場合は型チェックを無視
            response = openai_client.responses.create(
                model="gpt-4o-mini",
                input=query,
                tools=[file_search_tool_dict],  # type: ignore[arg-type]
                include=include_params if include_params else None
            )

            # レスポンステキストの抽出
            response_text = self._extract_response_text(response)

            # ファイル引用の抽出
            citations = self._extract_citations(response)

            # メタデータの構築（型を明示的に指定）
            metadata: Dict[str, Any] = {
                "store_name": store_name,
                "store_id"  : store_id,
                "query"     : query,
                "timestamp" : datetime.now().isoformat(),
                "model"     : "gpt-4o-mini",
                "method"    : "responses_api_file_search",
                "citations" : citations,
                "tool_calls": self._extract_tool_calls(response)
            }

            # 使用統計があれば追加（型安全な方法）
            if hasattr(response, 'usage') and response.usage is not None:
                try:
                    # ResponseUsageオブジェクトを辞書に変換
                    if hasattr(response.usage, 'model_dump'):
                        metadata["usage"] = response.usage.model_dump()
                    elif hasattr(response.usage, 'dict'):
                        metadata["usage"] = response.usage.dict()
                    else:
                        # 手動で属性を抽出
                        usage_dict = {}
                        for attr in ['prompt_tokens', 'completion_tokens', 'total_tokens']:
                            if hasattr(response.usage, attr):
                                usage_dict[attr] = getattr(response.usage, attr)
                        metadata["usage"] = usage_dict
                except Exception as e:
                    logger.warning(f"使用統計の変換に失敗: {e}")
                    metadata["usage"] = str(response.usage)

            return response_text, metadata

        except Exception as e:
            error_msg = f"Responses API検索でエラーが発生しました: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())

            # エラー時のメタデータ（型安全）
            error_metadata: Dict[str, Any] = {
                "error"     : str(e),
                "method"    : "responses_api_error",
                "store_name": store_name,
                "store_id"  : store_id,
                "query"     : query,
                "timestamp" : datetime.now().isoformat()
            }
            return error_msg, error_metadata

    def search_with_agent_sdk(self, query: str, store_name: str, store_id: str) -> Tuple[str, Dict[str, Any]]:
        """Agent SDKを使用した検索（簡易版 - file_searchはResponses APIで実行）"""
        try:
            if not AGENT_SDK_AVAILABLE:
                logger.info("Agent SDK利用不可、Responses APIにフォールバック")
                return self.search_with_responses_api(query, store_name, store_id)

            # 注意: Agent SDKでのfile_searchツール統合は複雑なため、
            # 現在は簡易版として通常のAgent実行のみ行い、
            # 実際のRAG機能はResponses APIに委譲

            # Agent SDKセッションの取得/作成
            session_key = f"{store_name}_agent"
            if session_key not in self.agent_sessions:
                self.agent_sessions[session_key] = SQLiteSession(session_key)

            session = self.agent_sessions[session_key]

            # 簡易Agent作成（file_searchなし）
            agent = Agent(
                name=f"RAG_Agent_{store_name.replace(' ', '_')}",
                instructions=f"""
                You are a helpful assistant specializing in {store_name}.
                Provide informative and accurate responses based on your knowledge.
                Be professional and helpful in your responses.
                """,
                model="gpt-4o-mini"
            )

            # Runner実行（セッション管理のみの利点）
            result = Runner.run_sync(
                agent,
                query,
                session=session
            )

            response_text = result.final_output if hasattr(result, 'final_output') else str(result)

            # メタデータの構築
            metadata: Dict[str, Any] = {
                "store_name": store_name,
                "store_id"  : store_id,
                "query"     : query,
                "timestamp" : datetime.now().isoformat(),
                "model"     : "gpt-4o-mini",
                "method"    : "agent_sdk_simple_session",
                "note"      : "Agent SDKセッション管理のみ、RAG機能なし"
            }

            logger.info("Agent SDK検索完了（簡易版）")
            return response_text, metadata

        except Exception as e:
            error_msg = f"Agent SDK検索でエラーが発生: {str(e)}"
            logger.error(error_msg)
            logger.warning("Agent SDKエラーによりResponses APIにフォールバック")
            # Agent SDKが失敗した場合はResponses APIにフォールバック
            return self.search_with_responses_api(query, store_name, store_id)

    def search(self, query: str, store_name: str, store_id: str, use_agent_sdk: bool = True, **kwargs) -> Tuple[
        str, Dict[str, Any]]:
        """統合検索メソッド"""
        if use_agent_sdk and AGENT_SDK_AVAILABLE:
            return self.search_with_agent_sdk(query, store_name, store_id)
        else:
            return self.search_with_responses_api(query, store_name, store_id, **kwargs)

    def _extract_response_text(self, response) -> str:
        """レスポンスからテキストを抽出"""
        try:
            # output_text属性がある場合
            if hasattr(response, 'output_text'):
                return response.output_text

            # output配列から抽出
            if hasattr(response, 'output') and response.output:
                for item in response.output:
                    if hasattr(item, 'type') and item.type == "message":
                        if hasattr(item, 'content') and item.content:
                            for content in item.content:
                                if hasattr(content, 'type') and content.type == "output_text":
                                    return content.text

            return "レスポンステキストの抽出に失敗しました"

        except Exception as e:
            logger.error(f"レスポンステキスト抽出エラー: {e}")
            return f"テキスト抽出エラー: {e}"

    def _extract_citations(self, response) -> List[Dict[str, Any]]:
        """ファイル引用情報を抽出"""
        citations: List[Dict[str, Any]] = []
        try:
            if hasattr(response, 'output') and response.output:
                for item in response.output:
                    if hasattr(item, 'type') and item.type == "message":
                        if hasattr(item, 'content') and item.content:
                            for content in item.content:
                                if hasattr(content, 'annotations'):
                                    for annotation in content.annotations:
                                        if hasattr(annotation, 'type') and annotation.type == "file_citation":
                                            citations.append({
                                                "file_id" : getattr(annotation, 'file_id', ''),
                                                "filename": getattr(annotation, 'filename', ''),
                                                "index"   : getattr(annotation, 'index', 0)
                                            })
        except Exception as e:
            logger.error(f"引用情報抽出エラー: {e}")

        return citations

    def _extract_tool_calls(self, response) -> List[Dict[str, Any]]:
        """ツール呼び出し情報を抽出"""
        tool_calls: List[Dict[str, Any]] = []
        try:
            if hasattr(response, 'output') and response.output:
                for item in response.output:
                    if hasattr(item, 'type') and item.type == "file_search_call":
                        tool_calls.append({
                            "id"     : getattr(item, 'id', ''),
                            "type"   : "file_search",
                            "status" : getattr(item, 'status', ''),
                            "queries": getattr(item, 'queries', [])
                        })
        except Exception as e:
            logger.error(f"ツール呼び出し情報抽出エラー: {e}")

        return tool_calls


# グローバルインスタンス
@st.cache_resource
def get_rag_manager():
    """RAGマネージャーのシングルトン取得"""
    return ModernRAGManager()


def initialize_session_state():
    """セッション状態の初期化"""
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    if 'current_query' not in st.session_state:
        st.session_state.current_query = ""
    if 'selected_store' not in st.session_state:
        # 動的に最初のVector Storeを選択
        _, store_list = get_current_vector_stores()
        st.session_state.selected_store = store_list[0] if store_list else "Customer Support FAQ"
    if 'selected_language' not in st.session_state:
        st.session_state.selected_language = "English"  # デフォルトは英語（RAGデータに合わせて）
    if 'use_agent_sdk' not in st.session_state:
        st.session_state.use_agent_sdk = False  # デフォルトはResponses API直接使用
    if 'search_options' not in st.session_state:
        st.session_state.search_options = {
            'max_results'    : 20,
            'include_results': True,
            'show_citations' : True
        }
    if 'auto_refresh_stores' not in st.session_state:
        st.session_state.auto_refresh_stores = True


def display_search_history():
    """検索履歴の表示"""
    st.header("🕒 検索履歴")

    if not st.session_state.search_history:
        st.info("検索履歴がありません")
        return

    # 履歴をエクスパンダーで表示
    for i, item in enumerate(st.session_state.search_history[:10]):  # 最新10件
        with st.expander(f"履歴 {i + 1}: {item['query'][:50]}..."):
            st.markdown(f"**質問:** {item['query']}")
            st.markdown(f"**Vector Store:** {item['store_name']}")
            st.markdown(f"**Store ID:** `{item.get('store_id', 'N/A')}`")
            st.markdown(f"**実行時間:** {item['timestamp']}")
            st.markdown(f"**検索方法:** {item.get('method', 'unknown')}")

            # 引用情報表示
            if 'citations' in item and item['citations']:
                st.markdown("**引用ファイル:**")
                for citation in item['citations']:
                    st.markdown(f"- {citation.get('filename', 'Unknown file')}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("再実行", key=f"rerun_{i}"):
                    st.session_state.current_query = item['query']
                    st.session_state.selected_store = item['store_name']
                    st.rerun()
            with col2:
                if st.button("詳細表示", key=f"detail_{i}"):
                    st.json(item)


def get_selected_store_index(selected_store: str, store_list: List[str]) -> int:
    """選択されたVector Storeのインデックスを取得"""
    try:
        return store_list.index(selected_store)
    except ValueError:
        return 0  # デフォルトは最初のインデックス


def get_test_questions_by_store(store_name: str, language: str) -> List[str]:
    """Vector Storeに応じたテスト質問を取得（動的対応）"""
    # 動的なVector Storeに対応するための柔軟なマッピング
    store_question_mapping = {
        # Customer Support FAQ系
        ("Customer Support FAQ", "English")    : test_questions_en,
        ("Customer Support FAQ", "日本語")     : test_questions_ja,

        # Science & Technology系
        ("Science & Technology Q&A", "English"): test_questions_2_en,
        ("Science & Technology Q&A", "日本語") : test_questions_2_ja,

        # Medical系
        ("Medical Q&A", "English")             : test_questions_3_en,
        ("Medical Q&A", "日本語")              : test_questions_3_ja,

        # Legal系
        ("Legal Q&A", "English")               : test_questions_4_en,
        ("Legal Q&A", "日本語")                : test_questions_4_ja,
    }

    # 完全一致確認
    key = (store_name, language)
    if key in store_question_mapping:
        return store_question_mapping[key]

    # 部分一致確認（柔軟対応）
    for (mapped_store, mapped_lang), questions in store_question_mapping.items():
        if (mapped_lang == language and
                (mapped_store.lower() in store_name.lower() or
                 any(word in store_name.lower() for word in mapped_store.lower().split()))):
            return questions

    # デフォルト（Customer Support FAQ）
    default_key = ("Customer Support FAQ", language)
    return store_question_mapping.get(default_key, test_questions_en)


def display_test_questions():
    """テスト用質問の表示（動的Vector Store対応）"""
    # 現在選択されているVector Storeと言語を取得
    selected_store = st.session_state.get('selected_store', 'Customer Support FAQ')
    selected_language = st.session_state.get('selected_language', 'English')

    # 対応する質問を取得
    questions = get_test_questions_by_store(selected_store, selected_language)

    # ヘッダーの動的生成
    if selected_language == "English":
        header = f"Test Questions ({selected_store})"
    else:
        header = f"テスト用質問（{selected_store}）"

    st.header(f"💡 {header}")

    # RAGデータが英語の場合の注意書き
    if selected_language == "日本語":
        st.warning("⚠️ RAGデータは英語で作成されています。英語での質問をお勧めします。")
    else:
        st.success("✅ 英語質問（RAGデータに最適化）")

    if not questions:
        if selected_language == "English":
            st.info("No test questions available for this Vector Store")
        else:
            st.info("このVector Storeに対応するテスト質問がありません")
        return

    # 質問ボタンの表示
    for i, question in enumerate(questions):
        button_key = f"test_q_{selected_store}_{selected_language}_{i}_{hash(question)}"
        if st.button(f"Q{i + 1}: {question}", key=button_key):
            st.session_state.current_query = question
            st.session_state.selected_store = selected_store
            st.rerun()


def display_vector_store_management():
    """Vector Store管理UI（重複問題修正版）"""
    st.header("🗄️ Vector Store管理（最新ID優先）")

    manager = get_vector_store_manager()

    col1, col2 = st.columns(2)
    with col1:
        st.write("**現在の設定ファイル**")
        if manager.CONFIG_FILE_PATH.exists():
            file_stat = manager.CONFIG_FILE_PATH.stat()
            st.success(f"✅ 存在 ({file_stat.st_size} bytes)")
            modified_time = datetime.fromtimestamp(file_stat.st_mtime)
            st.write(f"最終更新: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.warning("⚠️ 設定ファイル未作成")

    with col2:
        st.write("**操作**")
        if st.button("🔄 最新情報に更新", type="primary"):
            with st.spinner("最新のVector Store情報を取得中..."):
                updated_stores = manager.refresh_and_save()
                st.session_state['vector_stores_updated'] = datetime.now().isoformat()
                # キャッシュクリア
                st.cache_resource.clear()
                st.rerun()

        if st.button("📊 デバッグ情報表示"):
            debug_info = manager.debug_vector_stores()
            with st.expander("🔍 デバッグ情報", expanded=True):
                st.json(debug_info)

        if st.button("📁 設定ファイル表示"):
            if manager.CONFIG_FILE_PATH.exists():
                try:
                    with open(manager.CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                        config_content = f.read()
                    st.code(config_content, language='json')
                except Exception as e:
                    st.error(f"ファイル読み込みエラー: {e}")
            else:
                st.warning("設定ファイルが存在しません")


def display_system_info():
    """システム情報の表示"""
    with st.expander("🔧 システム情報", expanded=False):
        st.write("**利用可能な機能:**")
        st.write(f"- OpenAI SDK: {'✅' if OPENAI_AVAILABLE else '❌'}")
        st.write(f"- Responses API: ✅")
        st.write(f"- file_search ツール: ✅")
        st.write(f"- Agent SDK: {'✅（簡易版）' if AGENT_SDK_AVAILABLE else '❌'}")
        st.write(f"- Vector Store RAG: ✅")
        st.write(f"- ファイル引用: ✅")
        st.write(f"- 検索結果詳細: ✅")
        st.write(f"- 型安全実装: ✅")
        st.write(f"- 環境変数APIキー: ✅")
        st.write(f"- 動的Vector Store管理: ✅")
        st.write(f"- 重複ID解決: ✅（最新優先）")

        st.write("**APIキー設定:**")
        st.write("- 環境変数 `OPENAI_API_KEY` から自動取得")
        st.write("- Streamlit secrets.toml 不要")
        st.code("export OPENAI_API_KEY='your-api-key-here'")

        # 動的Vector Store情報
        st.write("**Vector Stores（動的・最新優先）:**")
        stores, _ = get_current_vector_stores()
        for i, (name, store_id) in enumerate(stores.items(), 1):
            st.write(f"{i}. {name}: `{store_id}`")

        if st.session_state.search_history:
            st.write(f"**検索履歴:** {len(st.session_state.search_history)} 件")

        # Vector Store連動情報
        st.write("**設定情報:**")
        selected_store = st.session_state.get('selected_store', 'Customer Support FAQ')
        selected_language = st.session_state.get('selected_language', 'English')

        st.write(f"- 選択Vector Store: {selected_store}")
        st.write(f"- 言語: {selected_language}")
        st.write(f"- Agent SDK使用: {'有効' if st.session_state.get('use_agent_sdk', False) else '無効'}")
        st.write(f"- 自動更新: {'有効' if st.session_state.get('auto_refresh_stores', True) else '無効'}")

        # RAG最適化情報
        if selected_language == "English":
            st.write("- 🎯 RAG最適化: ✅")
        else:
            st.write("- ⚠️ RAG最適化: 言語不一致")


def display_search_options():
    """検索オプションの表示"""
    with st.expander("⚙️ 検索オプション", expanded=False):
        # 最大結果数
        max_results = st.slider(
            "最大検索結果数",
            min_value=1,
            max_value=50,
            value=st.session_state.search_options['max_results'],
            help="Vector Storeから取得する最大結果数"
        )
        st.session_state.search_options['max_results'] = max_results

        # 検索結果詳細を含める
        include_results = st.checkbox(
            "検索結果詳細を含める",
            value=st.session_state.search_options['include_results'],
            help="file_search_call.resultsを含める"
        )
        st.session_state.search_options['include_results'] = include_results

        # 引用表示
        show_citations = st.checkbox(
            "ファイル引用を表示",
            value=st.session_state.search_options['show_citations'],
            help="レスポンスにファイル引用情報を表示"
        )
        st.session_state.search_options['show_citations'] = show_citations

        # Agent SDK使用設定
        if AGENT_SDK_AVAILABLE:
            use_agent_sdk = st.checkbox(
                "Agent SDKを使用",
                value=st.session_state.use_agent_sdk,
                help="Agent SDKを使用してセッション管理を有効化"
            )
            st.session_state.use_agent_sdk = use_agent_sdk

        # Vector Store自動更新設定
        auto_refresh = st.checkbox(
            "Vector Store自動更新",
            value=st.session_state.auto_refresh_stores,
            help="起動時にOpenAI APIから最新のVector Store情報を取得"
        )
        st.session_state.auto_refresh_stores = auto_refresh


def display_search_results(response_text: str, metadata: Dict[str, Any]):
    """検索結果の表示"""
    st.markdown("### 🤖 回答")
    st.markdown(response_text)

    # ファイル引用の表示
    if metadata.get('citations') and st.session_state.search_options['show_citations']:
        st.markdown("### 📚 引用ファイル")
        citations = metadata['citations']
        for i, citation in enumerate(citations, 1):
            st.markdown(f"{i}. **{citation.get('filename', 'Unknown file')}** (ID: `{citation.get('file_id', '')}`)")

    # メタデータ表示
    st.markdown("---")
    st.markdown("### 📊 検索情報")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Vector Store:** {metadata.get('store_name', '')}")
        st.markdown(f"**Store ID:** `{metadata.get('store_id', '')}`")
        st.markdown(f"**検索方法:** {metadata.get('method', '')}")

    with col2:
        st.markdown(f"**モデル:** {metadata.get('model', '')}")
        st.markdown(f"**実行時間:** {metadata.get('timestamp', '')}")
        if 'tool_calls' in metadata and metadata['tool_calls']:
            st.markdown(f"**ツール呼び出し:** {len(metadata['tool_calls'])}回")

    # 詳細情報
    with st.expander("🔍 詳細情報", expanded=False):
        st.json(metadata)


def main():
    """メイン関数"""
    st.set_page_config(
        page_title="最新RAG検索アプリ（重複問題修正版）",
        page_icon="🔍",
        layout="wide"
    )

    # セッション状態の初期化（デフォルト値設定）
    initialize_session_state()

    # RAGマネージャーの取得
    rag_manager = get_rag_manager()

    # Vector Store設定の取得（強制リフレッシュは初回のみ）
    force_refresh = st.session_state.get('force_initial_refresh', True)
    if force_refresh:
        st.session_state['force_initial_refresh'] = False

    vector_stores, vector_store_list = get_current_vector_stores(force_refresh=force_refresh)

    # ヘッダー
    st.write("🔍 最新RAG検索アプリケーション（重複問題修正・最新ID優先版）")

    # API状況表示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("✅ OpenAI Responses API 利用可能")
        st.success("✅ file_search ツール対応")
    with col2:
        if AGENT_SDK_AVAILABLE:
            st.success("✅ Agent SDK 利用可能")
        else:
            st.info("ℹ️ Agent SDK 未利用（Responses APIのみ）")
    with col3:
        st.success(f"✅ 動的Vector Store管理")
        st.success(f"🔄 重複ID解決（最新優先）")
        st.info(f"📊 利用可能店舗: {len(vector_stores)}件")

    st.markdown("---")

    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")

        # Vector Store選択（動的）
        if vector_store_list:
            # 現在の選択が利用可能かチェック
            current_selected = st.session_state.get('selected_store', vector_store_list[0])
            if current_selected not in vector_store_list:
                current_selected = vector_store_list[0]
                st.session_state.selected_store = current_selected

            selected_store = st.selectbox(
                "Vector Store を選択",
                options=vector_store_list,
                index=vector_store_list.index(current_selected),
                key="store_selection"
            )
            st.session_state.selected_store = selected_store

            # 選択されたVector Store IDを表示
            selected_store_id = vector_stores.get(selected_store, "未知のID")
            st.code(selected_store_id)

            # ID更新状況表示
            if st.session_state.get('vector_stores_updated'):
                update_time = st.session_state['vector_stores_updated']
                update_dt = datetime.fromisoformat(update_time)
                st.caption(f"最終更新: {update_dt.strftime('%H:%M:%S')}")
        else:
            st.error("❌ 利用可能なVector Storeがありません")
            st.stop()

        # 言語選択
        st.markdown("---")
        selected_language = st.selectbox(
            "Test Question Language",
            options=list(LANGUAGE_OPTIONS.keys()),
            index=list(LANGUAGE_OPTIONS.keys()).index(st.session_state.selected_language),
            key="language_selection",
            help="英語質問はRAGデータに最適化されています"
        )
        st.session_state.selected_language = selected_language

        # 言語に応じた推奨表示
        if selected_language == "English":
            st.success("✅ Optimized for English RAG data")
        else:
            st.warning("⚠️ RAGデータは英語です")

        # 検索オプション
        display_search_options()

        # Vector Store管理
        st.markdown("---")
        with st.expander("🗄️ Vector Store管理", expanded=False):
            display_vector_store_management()

        # システム情報
        display_system_info()

        # テスト用質問（選択されたVector Storeに対応）
        with st.expander("💡 テスト用質問", expanded=True):
            display_test_questions()

    # メインコンテンツ
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("❓ 質問入力")

        # 質問入力フォーム
        with st.form("search_form"):
            query = st.text_area(
                "質問を入力してください",
                value=st.session_state.current_query,
                height=100,
                key="query_input",
                help="英語での質問がRAGデータに最適化されています"
            )

            submitted = st.form_submit_button("🔍 検索実行", type="primary")

        if submitted and query.strip():
            st.session_state.current_query = query

            # 検索実行
            with col2:
                st.header("🤖 検索結果")

                with st.spinner("🔍 Vector Store検索中..."):
                    # 選択されたVector StoreのIDを取得
                    selected_store_id = vector_stores.get(selected_store, "")
                    if not selected_store_id:
                        st.error(f"❌ Vector Store ID が見つかりません: {selected_store}")
                        return

                    # 検索オプションの取得
                    search_options = st.session_state.search_options

                    # 検索実行（store_idも渡す）
                    final_result, final_metadata = rag_manager.search(
                        query,
                        selected_store,
                        selected_store_id,
                        use_agent_sdk=st.session_state.use_agent_sdk,
                        max_results=search_options['max_results'],
                        include_results=search_options['include_results']
                    )

                # 結果表示
                display_search_results(final_result, final_metadata)

                # 検索履歴に追加（型安全）
                history_item: Dict[str, Any] = {
                    "query"         : query,
                    "store_name"    : selected_store,
                    "store_id"      : selected_store_id,
                    "timestamp"     : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "method"        : final_metadata.get('method', 'unknown'),
                    "citations"     : final_metadata.get('citations', []),
                    "result_preview": final_result[:200] + "..." if len(final_result) > 200 else final_result
                }

                # 重複チェック
                if not any(item['query'] == query and item['store_name'] == selected_store
                           for item in st.session_state.search_history):
                    st.session_state.search_history.insert(0, history_item)
                    st.session_state.search_history = st.session_state.search_history[:50]  # 最新50件保持

        elif submitted and not query.strip():
            st.error("質問を入力してください")

    with col2:
        if not st.session_state.current_query:
            st.header("🤖 検索結果")
            st.info("質問を入力して検索を実行してください")

            # API機能説明
            st.markdown("### 🚀 利用可能な機能")
            st.markdown("""
            - **最新Responses API**: OpenAIの最新API
            - **file_search ツール**: Vector Storeからの高精度検索
            - **動的Vector Store管理**: 自動ID更新・設定ファイル連携
            - **重複ID解決**: 同名Vector Storeの最新作成日時優先
            - **ファイル引用**: 検索結果の出典表示
            - **カスタマイズ可能**: 結果数、フィルタリング等
            - **Agent SDK連携**: セッション管理（オプション）
            - **型安全実装**: 型エラー修正済み
            - **環境変数APIキー**: セキュアな設定方法
            """)

            # 重複問題修正の説明
            with st.expander("🔄 重複ID問題修正について", expanded=False):
                st.markdown("""
                **修正内容: 同名Vector Storeの重複問題解決**

                **問題:**
                - 同じ名前で複数のVector Storeが存在
                - 古いIDが選択されるバグ
                - 作成日時での優先度が未実装

                **修正:**
                - **作成日時ソート**: Vector Store一覧を作成日時順（新しい順）でソート
                - **最新優先選択**: 同名の場合は`created_at`が最新のものを優先
                - **詳細ログ出力**: どのIDが選択されたかをログで確認可能
                - **デバッグ機能**: サイドバーで詳細情報を確認可能

                **選択ロジック:**
                1. OpenAI APIからVector Store一覧を取得
                2. 作成日時(`created_at`)で降順ソート
                3. 同名Store候補の中から最新を選択
                4. 設定ファイルに保存・キャッシュ

                **確認方法:**
                - サイドバー「Vector Store管理」→「デバッグ情報表示」
                - ログでどのIDが選択されたかを確認
                """)

            # Vector Store動的管理の説明
            with st.expander("🗄️ 動的Vector Store管理について", expanded=False):
                st.markdown("""
                **新機能: 動的Vector Store管理**

                - **自動更新**: OpenAI APIから最新のVector Store一覧を取得
                - **設定ファイル連携**: `vector_stores.json` で永続化
                - **a30_020_make_vsid.py 連携**: 新規作成されたVector Storeを自動認識
                - **フォールバック**: 設定ファイルがない場合はデフォルト値を使用

                **設定ファイル形式:**
                ```json
                {
                  "vector_stores": {
                    "Customer Support FAQ": "vs_xxx...",
                    "Medical Q&A": "vs_yyy...",
                    ...
                  },
                  "last_updated": "2025-01-XX...",
                  "source": "a30_30_rag_search.py",
                  "version": "1.1"
                }
                ```

                **更新方法:**
                1. サイドバーの「Vector Store管理」で「最新情報に更新」をクリック
                2. 自動でOpenAI APIから最新一覧を取得（重複解決済み）
                3. 設定ファイルに保存して永続化
                """)

            # トラブルシューティング
            with st.expander("🚨 トラブルシューティング", expanded=False):
                st.markdown("""
                **重複ID問題の場合:**
                - サイドバー「Vector Store管理」→「最新情報に更新」をクリック
                - 「デバッグ情報表示」で選択されたIDを確認
                - ログで最新作成日時のIDが選択されているかを確認

                **APIキーエラーの場合:**
                ```bash
                # 環境変数確認
                echo $OPENAI_API_KEY

                # 設定方法
                export OPENAI_API_KEY='your-api-key-here'

                # 永続化（.bashrc/.zshrcに追加）
                echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.bashrc
                ```

                **Vector Store関連エラー:**
                - Vector Store IDが正しいか確認
                - 「最新情報に更新」ボタンで再取得
                - a30_020_make_vsid.py で新規作成後は更新が必要

                **その他のエラー:**
                - OpenAI SDKが最新版か確認: `pip install --upgrade openai`
                - インターネット接続を確認
                - vector_stores.json ファイルの形式を確認
                """)

    # 検索履歴セクション
    st.markdown("---")
    display_search_history()

    # フッター
    st.markdown("---")
    st.markdown("#### 最新RAG検索アプリケーション（重複問題修正・最新ID優先版）")
    st.markdown("🚀 **OpenAI Responses API + file_search ツール** による次世代RAG")
    st.markdown("✨ **修正機能**: 重複Vector Store ID問題解決、最新作成日時優先")
    st.markdown("🔗 **a30_020_make_vsid.py 連携**: 新規Vector Store自動認識")
    st.markdown("🔑 **セキュリティ**: 環境変数でのAPIキー管理")
    if AGENT_SDK_AVAILABLE:
        st.markdown("🔧 **Agent SDK**: セッション管理サポート（簡易版）")
    else:
        st.markdown("⚡ **高性能**: 直接Responses API使用")


if __name__ == "__main__":
    main()

# streamlit run a30_30_rag_search.py --server.port=8501
