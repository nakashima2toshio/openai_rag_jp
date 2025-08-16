# a30_020_make_vsid.py
# Vector Store作成Streamlitアプリ（完全修正版）
# streamlit run a30_020_make_vsid.py --server.port=8502

import streamlit as st
import pandas as pd
import os
import re
import time
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

# OpenAI SDK のインポート
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError as e:
    OPENAI_AVAILABLE = False
    st.error(f"OpenAI SDK が見つかりません: {e}")
    st.stop()

# 共通機能のインポート
try:
    from helper_rag import (
        AppConfig, RAGConfig, TokenManager, safe_execute,
        select_model, show_model_info,
        setup_page_config, setup_page_header, setup_sidebar_header,
        create_output_directory
    )

    HELPER_AVAILABLE = True
except ImportError as e:
    HELPER_AVAILABLE = False
    logging.warning(f"ヘルパーモジュールのインポートに失敗: {e}")

# ===================================================================
# ログ設定
# ===================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===================================================================
# 設定クラス
# ===================================================================
@dataclass
class VectorStoreConfig:
    """Vector Store設定データクラス"""
    dataset_type: str
    filename: str
    store_name: str
    description: str
    chunk_size: int = 1000
    overlap: int = 100
    max_file_size_mb: int = 400  # OpenAI制限より少し余裕を持って設定
    max_chunks_per_file: int = 40000  # チャンク数制限

    @classmethod
    def get_all_configs(cls) -> Dict[str, 'VectorStoreConfig']:
        """全データセット設定を取得（ファイルサイズ制限対応）"""
        return {
            "customer_support_faq": cls(
                dataset_type="customer_support_faq",
                filename="customer_support_faq.txt",
                store_name="Customer Support FAQ Knowledge Base",
                description="カスタマーサポートFAQデータベース",
                chunk_size=2000,  # サイズ拡大
                overlap=100,
                max_file_size_mb=30,  # より保守的な制限
                max_chunks_per_file=4000  # チャンク数削減
            ),
            "medical_qa"          : cls(
                dataset_type="medical_qa",
                filename="medical_qa.txt",
                store_name="Medical Q&A Knowledge Base",
                description="医療質問回答データベース",
                chunk_size=16000,  # 大幅増加：チャンク数を半減
                overlap=300,
                max_file_size_mb=20,  # さらに厳格なファイルサイズ制限
                max_chunks_per_file=6000  # チャンク数を大幅削減
            ),
            "sciq_qa"             : cls(
                dataset_type="sciq_qa",
                filename="sciq_qa.txt",
                store_name="Science & Technology Q&A Knowledge Base",
                description="科学技術質問回答データベース",
                chunk_size=2000,  # サイズ拡大
                overlap=100,
                max_file_size_mb=25,  # より保守的な制限
                max_chunks_per_file=8000  # チャンク数削減
            ),
            "legal_qa"            : cls(
                dataset_type="legal_qa",
                filename="legal_qa.txt",
                store_name="Legal Q&A Knowledge Base",
                description="法律質問回答データベース",
                chunk_size=3000,  # サイズ拡大
                overlap=150,
                max_file_size_mb=25,  # より保守的な制限
                max_chunks_per_file=6000  # チャンク数削減
            )
        }


# ===================================================================
# Vector Store処理クラス
# ===================================================================
class VectorStoreProcessor:
    """Vector Store用データ処理クラス"""

    def __init__(self):
        self.configs = VectorStoreConfig.get_all_configs()

    def load_text_file(self, filepath: Path) -> List[str]:
        """テキストファイルを読み込み、行ごとのリストとして返す"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 空行と短すぎる行を除去
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # 10文字以上の行のみ保持
                    cleaned_lines.append(line)

            logger.info(f"ファイル読み込み完了: {filepath.name} - {len(cleaned_lines)}行")
            return cleaned_lines

        except FileNotFoundError:
            logger.error(f"ファイルが見つかりません: {filepath}")
            return []
        except Exception as e:
            logger.error(f"ファイル読み込みエラー: {filepath} - {e}")
            return []

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """長いテキストを指定サイズのチャンクに分割"""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # 文の境界で分割するように調整
            if end < len(text):
                # 句読点を探す
                for punct in ['。', '！', '？', '.', '!', '?']:
                    punct_pos = text.rfind(punct, start, end)
                    if punct_pos > start + chunk_size // 2:
                        end = punct_pos + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # 次の開始位置を設定（オーバーラップを考慮）
            start = max(start + 1, end - overlap)

            # 無限ループ防止
            if start >= len(text):
                break

        return chunks

    def clean_text(self, text: str) -> str:
        """テキストのクレンジング処理"""
        if not text:
            return ""

        # 改行を空白に置換
        text = text.replace('\n', ' ').replace('\r', ' ')

        # 連続した空白を1つの空白にまとめる
        text = re.sub(r'\s+', ' ', text)

        # 先頭・末尾の空白を除去
        text = text.strip()

        return text

    def text_to_jsonl_data(self, lines: List[str], dataset_type: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """テキスト行をJSONL用のデータ構造に変換（サイズ制限チェック付き）"""
        config = self.configs.get(dataset_type)
        if not config:
            raise ValueError(f"未知のデータセットタイプ: {dataset_type}")

        chunk_size = config.chunk_size
        overlap = config.overlap
        max_chunks = config.max_chunks_per_file

        jsonl_data = []
        total_size = 0
        warnings = []

        for idx, line in enumerate(lines):
            # テキストクリーニング
            cleaned_text = self.clean_text(line)

            if not cleaned_text:
                continue

            # 長いテキストをチャンクに分割
            chunks = self.chunk_text(cleaned_text, chunk_size, overlap)

            for chunk_idx, chunk in enumerate(chunks):
                # チャンク数制限チェック
                if len(jsonl_data) >= max_chunks:
                    warnings.append(
                        f"⚠️ チャンク数が上限({max_chunks:,})に達しました。残り{len(lines) - idx:,}行はスキップされます。")
                    break

                jsonl_entry = {
                    "id"      : f"{dataset_type}_{idx}_{chunk_idx}",
                    "text"    : chunk,
                    "metadata": {
                        "dataset"      : dataset_type,
                        "original_line": idx,
                        "chunk_index"  : chunk_idx,
                        "total_chunks" : len(chunks)
                    }
                }

                jsonl_data.append(jsonl_entry)
                total_size += len(json.dumps(jsonl_entry, ensure_ascii=False))

                # ファイルサイズ制限チェック（概算）
                estimated_size_mb = total_size / (1024 * 1024)
                if estimated_size_mb > config.max_file_size_mb:
                    warnings.append(
                        f"⚠️ ファイルサイズが上限({config.max_file_size_mb}MB)に達しました。残りはスキップされます。")
                    break

            # 制限に達した場合はループを抜ける
            if len(jsonl_data) >= max_chunks or total_size / (1024 * 1024) > config.max_file_size_mb:
                break

        # 統計情報
        stats = {
            "original_lines"   : len(lines),
            "processed_lines"  : idx + 1 if jsonl_data else 0,
            "total_chunks"     : len(jsonl_data),
            "estimated_size_mb": total_size / (1024 * 1024),
            "warnings"         : warnings,
            "chunk_size_used"  : chunk_size,
            "overlap_used"     : overlap
        }

        logger.info(
            f"{dataset_type}: {len(lines)}行 -> {len(jsonl_data)}チャンク (推定{stats['estimated_size_mb']:.1f}MB)")

        if warnings:
            for warning in warnings:
                logger.warning(warning)

        return jsonl_data, stats


# ===================================================================
# Vector Store管理クラス
# ===================================================================
class VectorStoreManager:
    """Vector Store管理クラス"""

    def __init__(self, api_key: str = None):
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OpenAI APIキーが設定されていません。環境変数 OPENAI_API_KEY を確認してください。")

        self.client = OpenAI(api_key=api_key)
        self.processor = VectorStoreProcessor()
        self.configs = VectorStoreConfig.get_all_configs()
        self.created_stores = {}

    def create_vector_store_from_jsonl_data(self, jsonl_data: List[Dict], store_name: str) -> Optional[str]:
        """JSONL形式のデータからVector Storeを作成"""
        temp_file_path = None
        uploaded_file_id = None

        try:
            # 入力データの検証
            if not isinstance(jsonl_data, list):
                logger.error(f"❌ jsonl_dataがリストではありません: {type(jsonl_data)}")
                return None

            if not jsonl_data:
                logger.error("❌ jsonl_dataが空です")
                return None

            logger.info(f"Vector Store作成開始: {len(jsonl_data)}エントリ")

            # 一時ファイルを作成してアップロード用のJSONLファイルを準備
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                for i, entry in enumerate(jsonl_data):
                    # エントリが辞書型であることを確認
                    if not isinstance(entry, dict):
                        logger.error(f"エントリ {i} が辞書型ではありません: {type(entry)}")
                        return None

                    # 必要なキーが存在することを確認
                    if "id" not in entry or "text" not in entry:
                        logger.error(f"エントリ {i} に必要なキーがありません: {list(entry.keys())}")
                        return None

                    # メタデータは文字列として保存（OpenAI側の制限対応）
                    jsonl_entry = {
                        "id"  : entry["id"],
                        "text": entry["text"]
                    }
                    temp_file.write(json.dumps(jsonl_entry, ensure_ascii=False) + '\n')

                temp_file_path = temp_file.name

            logger.info(f"JSONLファイル作成完了: {len(jsonl_data)}エントリ")

            # Step 1: ファイルをOpenAIにアップロード
            with open(temp_file_path, 'rb') as file:
                uploaded_file = self.client.files.create(
                    file=file,
                    purpose="assistants"
                )
                uploaded_file_id = uploaded_file.id

            logger.info(f"ファイルアップロード完了: File ID={uploaded_file_id}")

            # Step 2: Vector Storeを作成
            vector_store = self.client.vector_stores.create(
                name=store_name,
                metadata={
                    "created_by" : "vector_store_streamlit_app",
                    "version"    : "2025.1",
                    "data_format": "jsonl_as_txt",
                    "entry_count": str(len(jsonl_data))
                }
            )

            logger.info(f"Vector Store作成完了: ID={vector_store.id}")

            # Step 3: ファイルをVector Storeに追加
            vector_store_file = self.client.vector_stores.files.create(
                vector_store_id=vector_store.id,
                file_id=uploaded_file_id
            )

            logger.info(f"Vector StoreFileリンク作成完了")

            # Step 4: ファイル処理完了を待機
            max_wait_time = 600  # 最大10分待機
            wait_interval = 5  # 5秒間隔でチェック
            waited_time = 0

            while waited_time < max_wait_time:
                file_status = self.client.vector_stores.files.retrieve(
                    vector_store_id=vector_store.id,
                    file_id=uploaded_file_id
                )

                if file_status.status == "completed":
                    updated_vector_store = self.client.vector_stores.retrieve(vector_store.id)

                    logger.info(f"✅ Vector Store作成完了:")
                    logger.info(f"  - ID: {vector_store.id}")
                    logger.info(f"  - Name: {vector_store.name}")
                    logger.info(f"  - ファイル数: {updated_vector_store.file_counts.total}")
                    logger.info(f"  - ストレージ使用量: {updated_vector_store.usage_bytes} bytes")

                    return vector_store.id

                elif file_status.status == "failed":
                    error_msg = getattr(file_status, 'last_error', 'Unknown error')
                    logger.error(f"❌ ファイル処理失敗: {error_msg}")

                    # 詳細エラー情報をログ出力
                    if hasattr(file_status, 'last_error') and file_status.last_error:
                        logger.error(f"エラーコード: {getattr(file_status.last_error, 'code', 'N/A')}")
                        logger.error(f"エラーメッセージ: {getattr(file_status.last_error, 'message', 'N/A')}")

                    return None

                elif file_status.status in ["in_progress", "cancelling"]:
                    time.sleep(wait_interval)
                    waited_time += wait_interval
                else:
                    logger.warning(f"⚠️ 予期しないステータス: {file_status.status}")
                    time.sleep(wait_interval)
                    waited_time += wait_interval

            logger.error(f"❌ Vector Store作成タイムアウト (制限時間: {max_wait_time}秒)")
            return None

        except Exception as e:
            logger.error(f"Vector Store作成エラー: {e}")
            return None

        finally:
            # 一時ファイルを削除
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                logger.info("🗑️ 一時ファイルを削除しました")

    def process_single_dataset(self, dataset_type: str, output_dir: Path = None) -> Dict[str, Any]:
        """単一データセットの処理（完全修正版）"""
        if output_dir is None:
            output_dir = Path("OUTPUT")

        config = self.configs.get(dataset_type)
        if not config:
            return {"success": False, "error": f"未知のデータセットタイプ: {dataset_type}"}

        # ファイルパスの構築
        filepath = output_dir / config.filename

        if not filepath.exists():
            return {"success": False, "error": f"ファイルが見つかりません: {filepath}"}

        try:
            # Step 1: ファイル読み込み
            text_lines = self.processor.load_text_file(filepath)

            if not text_lines:
                return {"success": False, "error": f"有効なテキストが見つかりません: {filepath}"}

            # Step 2: JSONL形式に変換（修正版）
            try:
                result = self.processor.text_to_jsonl_data(text_lines, dataset_type)

                # タプルであることを確認
                if not isinstance(result, tuple) or len(result) != 2:
                    logger.error(f"text_to_jsonl_dataの戻り値が期待する形式ではありません: {type(result)}")
                    return {"success": False, "error": "内部エラー: 変換処理の戻り値が不正"}

                # タプルを分離
                jsonl_data_list, stats_dict = result

                # 型チェック
                if not isinstance(jsonl_data_list, list):
                    logger.error(f"jsonl_dataがリストではありません: {type(jsonl_data_list)}")
                    return {"success": False, "error": "内部エラー: JSONLデータがリスト型ではない"}

                if not isinstance(stats_dict, dict):
                    logger.error(f"statsが辞書ではありません: {type(stats_dict)}")
                    return {"success": False, "error": "内部エラー: 統計データが辞書型ではない"}

                logger.info(f"✅ JSONL変換成功: {len(jsonl_data_list)}チャンク作成")

            except Exception as convert_error:
                logger.error(f"JSONL変換でエラー: {convert_error}")
                return {"success": False, "error": f"JSONL変換エラー: {str(convert_error)}"}

            if not jsonl_data_list:
                return {"success": False, "error": f"JSONL変換に失敗: {dataset_type}"}

            # サイズ制限警告のチェック
            if stats_dict.get("warnings"):
                warning_msg = "; ".join(stats_dict["warnings"])
                logger.warning(f"{dataset_type}: {warning_msg}")

            # 事前ファイルサイズチェック
            estimated_size_mb = stats_dict.get("estimated_size_mb", 0)
            if estimated_size_mb > 25:  # 25MB制限に厳格化
                logger.error(f"❌ ファイルサイズが大きすぎます: {estimated_size_mb:.1f}MB > 25MB")
                return {
                    "success": False,
                    "error"  : f"ファイルサイズが制限を超えています: {estimated_size_mb:.1f}MB (制限: 25MB). チャンクサイズを大きくするか、データを分割してください。"
                }

            # 医療QA特有の追加制限
            if dataset_type == "medical_qa":
                if len(jsonl_data_list) > 5000:  # さらに厳格な制限
                    logger.warning(f"医療QAデータのチャンク数制限適用: {len(jsonl_data_list):,} -> 5,000")
                    jsonl_data_list = jsonl_data_list[:5000]
                    stats_dict["warnings"].append("医療QAデータのチャンク数を5,000に制限しました")

                # サイズ再計算
                total_size_recalc = sum(len(json.dumps(entry, ensure_ascii=False)) for entry in jsonl_data_list)
                estimated_size_mb_recalc = total_size_recalc / (1024 * 1024)

                # 15MB制限でさらにチェック
                if estimated_size_mb_recalc > 15:
                    # さらに削減が必要
                    target_chunks = int(len(jsonl_data_list) * 15 / estimated_size_mb_recalc)
                    target_chunks = max(1000, target_chunks)  # 最低1000チャンクは保証
                    logger.warning(
                        f"医療QAデータのサイズ制限適用: {len(jsonl_data_list):,} -> {target_chunks:,}チャンク")
                    jsonl_data_list = jsonl_data_list[:target_chunks]
                    stats_dict["warnings"].append(
                        f"医療QAデータを15MB以下にするため{target_chunks:,}チャンクに制限しました")

                    # 最終サイズ再計算
                    total_size_recalc = sum(len(json.dumps(entry, ensure_ascii=False)) for entry in jsonl_data_list)
                    estimated_size_mb_recalc = total_size_recalc / (1024 * 1024)

                stats_dict["estimated_size_mb"] = estimated_size_mb_recalc
                stats_dict["total_chunks"] = len(jsonl_data_list)

                logger.info(f"医療QA最適化後: {len(jsonl_data_list):,}チャンク, {estimated_size_mb_recalc:.1f}MB")

            # Step 3: Vector Store作成（修正版 - jsonl_data_listを渡す）
            store_name = config.store_name
            logger.info(f"Vector Store作成開始: {store_name}")

            # ここが重要：jsonl_data_listを渡す（タプルではなく）
            vector_store_id = self.create_vector_store_from_jsonl_data(jsonl_data_list, store_name)

            if vector_store_id:
                self.created_stores[dataset_type] = vector_store_id

                return {
                    "success"          : True,
                    "vector_store_id"  : vector_store_id,
                    "store_name"       : store_name,
                    "processed_lines"  : stats_dict.get("processed_lines", 0),
                    "total_lines"      : stats_dict.get("original_lines", 0),
                    "created_chunks"   : len(jsonl_data_list),
                    "estimated_size_mb": stats_dict.get("estimated_size_mb", 0),
                    "warnings"         : stats_dict.get("warnings", []),
                    "config_used"      : {
                        "chunk_size": stats_dict.get("chunk_size_used", 0),
                        "overlap"   : stats_dict.get("overlap_used", 0)
                    }
                }
            else:
                return {"success": False, "error": f"Vector Store作成に失敗: {dataset_type}"}

        except Exception as e:
            logger.error(f"{dataset_type} 処理エラー: {str(e)}")
            return {"success": False, "error": f"処理中にエラーが発生: {str(e)}"}

    def list_vector_stores(self) -> List[Dict]:
        """既存のVector Storeを一覧表示"""
        try:
            stores = self.client.vector_stores.list()
            store_list = []

            for store in stores.data:
                store_info = {
                    "id"         : store.id,
                    "name"       : store.name,
                    "file_counts": store.file_counts.total if store.file_counts else 0,
                    "created_at" : store.created_at,
                    "usage_bytes": store.usage_bytes
                }
                store_list.append(store_info)

            return store_list
        except Exception as e:
            logger.error(f"Vector Store一覧取得エラー: {e}")
            return []


# ===================================================================
# Streamlit UI管理クラス
# ===================================================================
class VectorStoreUI:
    """Vector Store用Streamlit UI管理クラス"""

    def __init__(self):
        self.configs = VectorStoreConfig.get_all_configs()
        self.manager = None

    def setup_page(self):
        """ページ設定"""
        try:
            st.set_page_config(
                page_title="Vector Store作成アプリ（完全版）",
                page_icon="🔗",
                layout="wide",
                initial_sidebar_state="expanded"
            )
        except st.errors.StreamlitAPIException:
            pass

    def setup_header(self):
        """ヘッダー設定"""
        st.title("🔗 Vector Store作成アプリ（完全版）")
        st.caption("OpenAI Vector Storeの自動作成・管理システム")
        st.markdown("---")

    def setup_sidebar(self) -> Tuple[str, bool]:
        """サイドバー設定"""
        st.sidebar.title("🔗 Vector Store作成")
        st.sidebar.markdown("---")

        # モデル選択（参考表示用）
        if HELPER_AVAILABLE:
            selected_model = select_model(key="vector_store_model")
            show_model_info(selected_model)
        else:
            selected_model = st.sidebar.selectbox(
                "🤖 参考モデル",
                ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
                help="参考表示用（Vector Store作成には直接影響しません）"
            )

        st.sidebar.markdown("---")

        # 全データセット処理オプション
        process_all = st.sidebar.checkbox(
            "🚀 全データセット一括処理",
            value=False,
            help="4つのデータセットを一括でVector Store化"
        )

        # APIキー確認
        with st.sidebar.expander("🔑 API設定確認", expanded=False):
            api_key_status = "✅ 設定済み" if os.getenv("OPENAI_API_KEY") else "❌ 未設定"
            st.write(f"**OpenAI APIキー**: {api_key_status}")

            if not os.getenv("OPENAI_API_KEY"):
                st.error("環境変数 OPENAI_API_KEY を設定してください")
                st.code("export OPENAI_API_KEY='your-api-key-here'")

        return selected_model, process_all

    def display_dataset_selection(self) -> List[str]:
        """データセット選択UI"""
        st.subheader("📋 データセット選択")

        # データセット一覧表示
        col1, col2 = st.columns(2)
        selected_datasets = []

        for idx, (dataset_type, config) in enumerate(self.configs.items()):
            col = col1 if idx % 2 == 0 else col2

            with col:
                # チェックボックスでデータセット選択
                selected = st.checkbox(
                    f"{config.description}",
                    key=f"dataset_{dataset_type}",
                    help=f"ファイル: {config.filename}"
                )

                if selected:
                    selected_datasets.append(dataset_type)

                # ファイル存在確認
                output_dir = Path("OUTPUT")
                filepath = output_dir / config.filename

                if filepath.exists():
                    file_size = filepath.stat().st_size
                    st.success(f"✅ ファイル存在 ({file_size:,} bytes)")
                else:
                    st.error(f"❌ ファイル不在: {config.filename}")

        return selected_datasets

    def display_file_status(self):
        """ファイル状況表示"""
        st.subheader("📁 ファイル状況")

        output_dir = Path("OUTPUT")

        if not output_dir.exists():
            st.error(f"❌ OUTPUTディレクトリが見つかりません: {output_dir}")
            return

        # ファイル状況をテーブル表示
        file_data = []
        for dataset_type, config in self.configs.items():
            filepath = output_dir / config.filename

            if filepath.exists():
                file_size = filepath.stat().st_size
                modified_time = datetime.fromtimestamp(filepath.stat().st_mtime)
                status = "✅ 利用可能"
            else:
                file_size = 0
                modified_time = None
                status = "❌ ファイル不在"

            file_data.append({
                "データセット": config.description,
                "ファイル名"  : config.filename,
                "サイズ"      : f"{file_size:,} bytes" if file_size > 0 else "-",
                "更新日時"    : modified_time.strftime("%Y-%m-%d %H:%M:%S") if modified_time else "-",
                "状態"        : status
            })

        df_files = pd.DataFrame(file_data)
        st.dataframe(df_files, use_container_width=True)

    def display_results(self, results: Dict[str, Dict]):
        """処理結果表示（改善版）"""
        st.subheader("📊 処理結果")

        successful = {k: v for k, v in results.items() if v.get("success", False)}
        failed = {k: v for k, v in results.items() if not v.get("success", False)}

        # サマリー表示
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("処理対象", len(results))
        with col2:
            st.metric("成功", len(successful))
        with col3:
            st.metric("失敗", len(failed))

        # 成功結果の詳細
        if successful:
            st.write("### ✅ 作成成功")
            success_data = []
            for dataset_type, result in successful.items():
                config = self.configs[dataset_type]

                # 警告がある場合の表示準備
                warning_text = ""
                if result.get("warnings"):
                    warning_text = f" ⚠️ {len(result['warnings'])}件の警告"

                success_data.append({
                    "データセット"   : config.description,
                    "Vector Store ID": result["vector_store_id"],
                    "Store名"        : result["store_name"],
                    "処理行数"       : f"{result.get('processed_lines', 0):,} / {result.get('total_lines', 0):,}",
                    "チャンク数"     : f"{result['created_chunks']:,}",
                    "推定サイズ"     : f"{result.get('estimated_size_mb', 0):.1f} MB",
                    "状態"           : f"完了{warning_text}"
                })

            df_success = pd.DataFrame(success_data)
            st.dataframe(df_success, use_container_width=True)

            # 警告詳細表示
            for dataset_type, result in successful.items():
                if result.get("warnings"):
                    config = self.configs[dataset_type]
                    with st.expander(f"⚠️ {config.description} の警告詳細", expanded=False):
                        for warning in result["warnings"]:
                            st.warning(warning)

                        # 設定情報も表示
                        config_used = result.get("config_used", {})
                        st.info(
                            f"使用設定: チャンクサイズ={config_used.get('chunk_size', 'N/A')}, オーバーラップ={config_used.get('overlap', 'N/A')}")

        # 失敗結果の詳細
        if failed:
            st.write("### ❌ 作成失敗")
            for dataset_type, result in failed.items():
                config = self.configs[dataset_type]
                st.error(f"**{config.description}**: {result['error']}")

                # 対処法の提案
                if "too large" in result['error'].lower():
                    st.info(
                        "💡 **対処法**: ファイルサイズが大きすぎます。チャンクサイズを大きくするか、データを分割してください。")
                elif "not found" in result['error'].lower():
                    st.info("💡 **対処法**: 必要なファイルがOUTPUTディレクトリに存在することを確認してください。")

        return successful, failed

    def display_existing_stores(self, manager: VectorStoreManager):
        """既存Vector Store表示（修正版）"""
        st.subheader("📚 既存Vector Store一覧")

        try:
            stores = manager.list_vector_stores()

            if not stores:
                st.info("Vector Storeが見つかりません")
                return

            # Vector Store一覧をテーブル表示（修正版）
            store_data = []
            for idx, store in enumerate(stores[:20]):  # 最新20件
                created_date = datetime.fromtimestamp(store['created_at'])
                store_data.append({
                    "番号"            : idx + 1,
                    "名前"            : store['name'],
                    "ID"              : store['id'],
                    "ファイル数"      : store['file_counts'],
                    "ストレージ使用量": f"{store['usage_bytes']:,} bytes",
                    "作成日時"        : created_date.strftime("%Y-%m-%d %H:%M:%S")
                })

            df_stores = pd.DataFrame(store_data)
            st.dataframe(df_stores, use_container_width=True, hide_index=True)

            # 統計情報
            total_storage = sum(store['usage_bytes'] for store in stores)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("総Vector Store数", len(stores))
            with col2:
                st.metric("総ストレージ使用量", f"{total_storage / (1024 * 1024):.1f} MB")
            with col3:
                total_files = sum(store['file_counts'] for store in stores)
                st.metric("総ファイル数", total_files)

        except Exception as e:
            st.error(f"Vector Store一覧の取得に失敗: {e}")
            logger.error(f"Vector Store一覧取得エラー: {e}")


# ===================================================================
# メイン関数
# ===================================================================
def initialize_session_state():
    """セッション状態の初期化"""
    if 'vector_store_results' not in st.session_state:
        st.session_state.vector_store_results = {}
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = {}


def main():
    """メイン処理関数"""

    # セッション状態の初期化
    initialize_session_state()

    # UI管理インスタンス
    ui = VectorStoreUI()

    # ページ設定
    ui.setup_page()
    ui.setup_header()

    # OpenAI SDK利用可能性確認
    if not OPENAI_AVAILABLE:
        st.error("OpenAI SDKが利用できません。`pip install openai` でインストールしてください。")
        return

    # APIキー確認
    if not os.getenv("OPENAI_API_KEY"):
        st.error("🔑 OpenAI APIキーが設定されていません")
        st.code("export OPENAI_API_KEY='your-api-key-here'")
        st.info("APIキーを設定してからアプリを再起動してください")
        return

    # サイドバー設定
    selected_model, process_all = ui.setup_sidebar()

    # Vector Store Manager の初期化
    try:
        manager = VectorStoreManager()
        ui.manager = manager
    except Exception as e:
        st.error(f"Vector Store Manager の初期化に失敗: {e}")
        return

    # メインコンテンツエリア
    tab1, tab2, tab3 = st.tabs(["🔗 Vector Store作成", "📁 ファイル状況", "📚 既存Store一覧"])

    with tab1:
        # データセット選択または一括処理
        if process_all:
            st.subheader("🚀 全データセット一括処理")
            selected_datasets = list(ui.configs.keys())

            # 全データセット状況表示
            all_files_exist = True
            output_dir = Path("OUTPUT")

            for dataset_type in selected_datasets:
                config = ui.configs[dataset_type]
                filepath = output_dir / config.filename

                if filepath.exists():
                    st.success(f"✅ {config.description}: {config.filename}")
                else:
                    st.error(f"❌ {config.description}: {config.filename} が見つかりません")
                    all_files_exist = False

            if not all_files_exist:
                st.warning("⚠️ 一部ファイルが見つかりません。個別処理を使用してください。")
                selected_datasets = []

        else:
            # 個別データセット選択
            selected_datasets = ui.display_dataset_selection()

        # Vector Store作成実行
        if selected_datasets:
            st.markdown("---")
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"**選択データセット数**: {len(selected_datasets)}")
                for dataset_type in selected_datasets:
                    config = ui.configs[dataset_type]
                    st.write(f"- {config.description}")

            with col2:
                create_button = st.button(
                    "🚀 Vector Store作成開始",
                    type="primary",
                    use_container_width=True
                )

            if create_button:
                # 処理実行
                results = {}

                # 全体の進行状況表示
                st.markdown("---")
                st.subheader("🚀 Vector Store作成進行状況")

                overall_progress = st.progress(0)
                overall_status = st.empty()

                for idx, dataset_type in enumerate(selected_datasets):
                    config = ui.configs[dataset_type]

                    # 個別データセットの進行状況
                    with st.container():
                        st.write(f"### 📋 {idx + 1}/{len(selected_datasets)}: {config.description}")

                        # 個別進行状況バー
                        dataset_progress = st.progress(0)
                        dataset_status = st.empty()

                        try:
                            # Vector Store作成実行
                            dataset_progress.progress(0.1)
                            dataset_status.text("🔄 処理開始...")

                            with st.spinner(f"🔄 {config.description} を処理中..."):
                                result = manager.process_single_dataset(dataset_type)
                                results[dataset_type] = result

                            if result["success"]:
                                dataset_progress.progress(1.0)
                                dataset_status.success(f"✅ 完了 - Vector Store ID: `{result['vector_store_id']}`")

                                # 詳細情報表示
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("処理行数",
                                              f"{result.get('processed_lines', 0):,} / {result.get('total_lines', 0):,}")
                                with col2:
                                    st.metric("作成チャンク数", f"{result['created_chunks']:,}")
                                with col3:
                                    st.metric("推定サイズ", f"{result.get('estimated_size_mb', 0):.1f} MB")

                                # 警告がある場合は表示
                                if result.get("warnings"):
                                    for warning in result["warnings"]:
                                        st.warning(warning)

                            else:
                                dataset_progress.progress(0)
                                dataset_status.error(f"❌ 失敗: {result['error']}")

                                # エラー対処法の提案
                                if "too large" in result['error'].lower():
                                    st.info("💡 ファイルサイズが大きすぎます。設定を調整して再試行してください。")
                                elif "not found" in result['error'].lower():
                                    st.info("💡 必要なファイルがOUTPUTディレクトリに存在することを確認してください。")

                        except Exception as e:
                            error_msg = f"予期しないエラー: {str(e)}"
                            results[dataset_type] = {"success": False, "error": error_msg}
                            dataset_progress.progress(0)
                            dataset_status.error(f"❌ {error_msg}")
                            logger.error(f"{dataset_type} 処理中の例外: {e}")

                        st.markdown("---")

                        # 全体進行状況更新
                        overall_progress.progress((idx + 1) / len(selected_datasets))
                        overall_status.text(f"進行状況: {idx + 1}/{len(selected_datasets)} 完了")

                # 全体完了
                overall_progress.progress(1.0)
                overall_status.success("🎉 全体処理完了!")

                # 結果をセッション状態に保存
                st.session_state.vector_store_results = results

                # 結果表示
                st.markdown("---")
                successful, failed = ui.display_results(results)

                # 結果のJSONダウンロード
                if results:
                    result_json = json.dumps(results, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="📄 結果をJSONでダウンロード",
                        data=result_json,
                        file_name=f"vector_store_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )

                    # 成功したVector Store IDの一覧表示
                    if successful:
                        st.subheader("🔗 作成されたVector Store ID一覧")
                        id_list = []
                        for dataset_type, result in successful.items():
                            config = ui.configs[dataset_type]
                            id_list.append(f"# {config.description}")
                            id_list.append(f"{dataset_type.upper()}_VECTOR_STORE_ID = \"{result['vector_store_id']}\"")
                            id_list.append("")

                        id_text = "\n".join(id_list)
                        st.code(id_text, language="python")

                        st.download_button(
                            label="📋 Vector Store IDをコピー用テキストでダウンロード",
                            data=id_text,
                            file_name=f"vector_store_ids_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain"
                        )

        else:
            st.info("👆 作成するVector Storeのデータセットを選択してください")

    with tab2:
        # ファイル状況表示
        ui.display_file_status()

        # 詳細情報
        with st.expander("📁 ディレクトリ詳細情報", expanded=False):
            output_dir = Path("OUTPUT")
            if output_dir.exists():
                st.write(f"**ディレクトリパス**: `{output_dir.absolute()}`")

                # ディレクトリ内ファイル一覧
                files = list(output_dir.glob("*.txt"))
                st.write(f"**テキストファイル数**: {len(files)}")

                for file in files:
                    file_size = file.stat().st_size
                    modified_time = datetime.fromtimestamp(file.stat().st_mtime)
                    st.write(f"- {file.name}: {file_size:,} bytes ({modified_time.strftime('%Y-%m-%d %H:%M:%S')})")
            else:
                st.error(f"OUTPUTディレクトリが存在しません: {output_dir}")

    with tab3:
        # 既存Vector Store一覧
        ui.display_existing_stores(manager)

        # リフレッシュボタン
        if st.button("🔄 一覧を更新", type="secondary"):
            st.rerun()

    # フッター
    st.markdown("---")
    st.markdown("### 🔗 Vector Store作成アプリ（完全修正版）")
    st.markdown("✨ **OpenAI Vector Store自動作成システム** - エラー完全修正版")
    st.markdown("🚀 **機能**: 複数データセット対応、型安全処理、エラー解決済み")


if __name__ == "__main__":
    main()

# 実行コマンド:
# streamlit run a30_020_make_vsid.py --server.port=8502
