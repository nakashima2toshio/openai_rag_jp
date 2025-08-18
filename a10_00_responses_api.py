a10_00_responses_api.pya10_00_responses_api.py# streamlit run a10_00_responses_api.py --server.port=8510
# --------------------------------------------------
# OpenAI Responses API デモアプリケーション（統一化版）
# Streamlitを使用したインタラクティブなAPIテストツール
# 統一化版: 構成・構造・ライブラリ・エラー処理の完全統一
# --------------------------------------------------
import os
import sys
import json
import base64
import glob
import logging
from datetime import datetime
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path

import streamlit as st
import pandas as pd
import requests
from pydantic import BaseModel, ValidationError

from openai import OpenAI
from openai.types.responses import (
    EasyInputMessageParam,
    ResponseInputTextParam,
    ResponseInputImageParam,
    ResponseFormatTextJSONSchemaConfigParam,
    ResponseTextConfigParam,
    FileSearchToolParam,
    WebSearchToolParam,
    ComputerToolParam,
    Response,  # ← この行を追加
)
from openai.types.responses.web_search_tool_param import UserLocation

# プロジェクトディレクトリの設定
BASE_DIR = Path(__file__).resolve().parent.parent
THIS_DIR = Path(__file__).resolve().parent

# PYTHONPATHに親ディレクトリを追加
sys.path.insert(0, str(BASE_DIR))

# ヘルパーモジュールをインポート（統一化）
try:
    from helper_st import (
        UIHelper, MessageManagerUI, ResponseProcessorUI,
        SessionStateManager, error_handler_ui, timer_ui,
        InfoPanelManager, safe_streamlit_json
    )
    from helper_api import (
        config, logger, TokenManager, OpenAIClient,
        EasyInputMessageParam, ResponseInputTextParam,
        ConfigManager, MessageManager, sanitize_key,
        error_handler, timer, get_default_messages,
        ResponseProcessor, format_timestamp
    )
except ImportError as e:
    st.error(f"ヘルパーモジュールのインポートに失敗しました: {e}")
    st.info("必要なファイルが存在することを確認してください: helper_st.py, helper_api.py")
    st.stop()


# ページ設定
def setup_page_config():
    """ページ設定（重複実行エラー回避）"""
    try:
        st.set_page_config(
            page_title=config.get("ui.page_title", "OpenAI Responses API デモ"),
            page_icon=config.get("ui.page_icon", "🤖"),
            layout=config.get("ui.layout", "wide"),
            initial_sidebar_state="expanded"
        )
    except st.errors.StreamlitAPIException:
        # 既に設定済みの場合は無視
        pass


# ページ設定の実行
setup_page_config()

# サンプル画像 URL（config.ymlから取得）
image_path_sample = config.get(
    "samples.images.nature",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/"
    "Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-"
    "Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
)

# https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg

# ==================================================
# 共通UI関数（統一化版）
# ==================================================
def setup_common_ui(demo_name: str) -> str:
    """共通UI設定（統一化版）"""
    safe_key = sanitize_key(demo_name)

    # ヘッダー表示
    st.write(f"# {demo_name}")

    # モデル選択（統一されたUI）
    model = UIHelper.select_model(f"model_{safe_key}")
    st.write("選択したモデル:", model)

    return model


def setup_sidebar_panels(selected_model: str):
    """サイドバーパネルの統一設定（helper_st.pyのInfoPanelManagerを使用）"""
    st.sidebar.write("### 📋 情報パネル")

    InfoPanelManager.show_model_info(selected_model)
    InfoPanelManager.show_session_info()
    InfoPanelManager.show_performance_info()
    InfoPanelManager.show_cost_info(selected_model)
    InfoPanelManager.show_debug_panel()
    InfoPanelManager.show_settings()


# ==================================================
# 基底クラス
# ==================================================
class BaseDemo(ABC):
    """デモ機能の基底クラス（統一化版）"""

    def __init__(self, demo_name: str):
        self.demo_name = demo_name
        self.config = ConfigManager("config.yml")

        # OpenAIクライアントの初期化（統一されたエラーハンドリング）
        try:
            self.client = OpenAIClient()
        except Exception as e:
            st.error(f"OpenAIクライアントの初期化に失敗しました: {e}")
            st.stop()

        self.safe_key = sanitize_key(demo_name)
        self.message_manager = MessageManagerUI(f"messages_{self.safe_key}")
        self.model = None

        # セッション状態の初期化（統一化）
        SessionStateManager.init_session_state()
        self._initialize_session_state()

    def _initialize_session_state(self):
        """セッション状態の統一的初期化"""
        session_key = f"demo_state_{self.safe_key}"
        if session_key not in st.session_state:
            st.session_state[session_key] = {
                'initialized'    : True,
                'model'          : self.config.get("models.default", "gpt-4o-mini"),
                'execution_count': 0
            }

    def get_model(self) -> str:
        """選択されたモデルを取得（統一化）"""
        return st.session_state.get(f"model_{self.safe_key}",
                                    config.get("models.default", "gpt-4o-mini"))

    def is_reasoning_model(self, model: str = None) -> bool:
        """推論系モデルかどうかを判定（統一化）"""
        if model is None:
            model = self.get_model()

        # config.ymlから取得、フォールバックあり
        reasoning_models = config.get("models.categories.reasoning",
                                      ["o1", "o1-mini", "o3", "o3-mini", "o4", "o4-mini"])
        
        # GPT-5系モデルも推論系として扱う（temperatureサポートなし）
        frontier_models = config.get("models.categories.frontier",
                                    ["gpt-5", "gpt-5-mini", "gpt-5-nano"])

        # モデル名に推論系モデルの識別子が含まれているかチェック
        reasoning_indicators = ["o1", "o3", "o4", "gpt-5"]
        return any(indicator in model.lower() for indicator in reasoning_indicators) or \
            any(reasoning_model in model for reasoning_model in reasoning_models) or \
            any(frontier_model in model for frontier_model in frontier_models)

    def create_temperature_control(self, default_temp: float = 0.3, help_text: str = None) -> Optional[float]:
        """Temperatureコントロールを作成（統一化・推論系モデル・GPT-5系では無効化）"""
        model = self.get_model()

        if self.is_reasoning_model(model):
            st.info("ℹ️ 推論系モデル（o1, o3, o4, gpt-5系）ではtemperatureパラメータは使用されません")
            return None
        else:
            return st.slider(
                "Temperature",
                0.0, 1.0, default_temp, 0.05,
                help=help_text or "低い値ほど一貫性のある回答"
            )

    def initialize(self):
        """共通の初期化処理（統一化）"""
        self.model = setup_common_ui(self.demo_name)
        setup_sidebar_panels(self.model)

    def handle_error(self, e: Exception):
        """統一的エラーハンドリング"""
        # 多言語対応エラーメッセージ
        lang = config.get("i18n.default_language", "ja")
        error_msg = config.get(f"error_messages.{lang}.general_error", "エラーが発生しました")
        st.error(f"{error_msg}: {str(e)}")

        if config.get("experimental.debug_mode", False):
            with st.expander("🔧 詳細エラー情報", expanded=False):
                st.exception(e)

    def show_debug_info(self):
        """デバッグ情報の統一表示"""
        if st.sidebar.checkbox("🔧 デモ状態を表示", value=False, key=f"debug_{self.safe_key}"):
            with st.sidebar.expander("デモデバッグ情報", expanded=False):
                st.write(f"**デモ名**: {self.demo_name}")
                st.write(f"**選択モデル**: {self.model}")

                session_state = st.session_state.get(f"demo_state_{self.safe_key}", {})
                st.write(f"**実行回数**: {session_state.get('execution_count', 0)}")

    @error_handler_ui
    @timer_ui
    def call_api_unified(self, messages: List[EasyInputMessageParam], temperature: Optional[float] = None, **kwargs):
        """統一されたAPI呼び出し（temperatureパラメータ対応）"""
        model = self.get_model()

        # API呼び出しパラメータの準備
        api_params = {
            "input": messages,
            "model": model
        }

        # temperatureサポートチェック（reasoning系モデルは除外）
        if not self.is_reasoning_model(model) and temperature is not None:
            api_params["temperature"] = temperature

        # その他のパラメータ
        api_params.update(kwargs)

        # responses.create を使用（統一されたAPI呼び出し）
        return self.client.create_response(**api_params)

    @abstractmethod
    def run(self):
        """各デモの実行処理（サブクラスで実装）"""
        pass


# ==================================================
# テキスト応答デモ
# ==================================================
class TextResponseDemo(BaseDemo):
    """基本的なテキスト応答のデモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        with st.expander("OpenAI API(IPO):実装例", expanded=False):
            st.write(
                "responses.create()の基本的なテキスト応答デモ。デフォルトメッセージ+ユーザー入力でOne-Shot応答を実行。EasyInputMessageParamでメッセージ構築し、ResponseProcessorUIで結果表示。")
            st.code("""
            messages = get_default_messages()
            messages.append(
                EasyInputMessageParam(role="user", content=user_input)
            )

        # 統一されたAPI呼び出し（temperatureパラメータ対応）
        response = self.call_api_unified(messages, temperature=temperature)
        　┗ api_params = {
            "input": messages,
            "model": model
            }
            self.client.responses.create(**params)
        ResponseProcessorUI.display_response(response)
            """)

        example_query = config.get("samples.prompts.responses_query",
                                   "OpenAIのAPIで、responses.createを説明しなさい。")
        st.write(f"質問の例: {example_query}")

        with st.form(key=f"text_form_{self.safe_key}"):
            user_input = st.text_area(
                "質問を入力してください:",
                height=config.get("ui.text_area_height", 75)
            )

            # 統一されたtemperatureコントロール
            temperature = self.create_temperature_control(
                default_temp=0.3,
                help_text="低い値ほど一貫性のある回答"
            )

            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(user_input, temperature)

        self.show_debug_info()

    def _process_query(self, user_input: str, temperature: Optional[float]):
        """クエリの処理（統一化版）"""
        # 実行回数を更新
        session_key = f"demo_state_{self.safe_key}"
        if session_key in st.session_state:
            st.session_state[session_key]['execution_count'] += 1

        # トークン情報の表示
        UIHelper.show_token_info(user_input, self.model, position="sidebar")

        # デフォルトメッセージを取得（config.ymlから）
        messages = get_default_messages()
        messages.append(
            EasyInputMessageParam(role="user", content=user_input)
        )

        with st.spinner("処理中..."):
            response = self.call_api_unified(messages, temperature=temperature)

        st.success("応答を取得しました")
        ResponseProcessorUI.display_response(response)


# ==================================================
# 必要なインポートの追加（エラー修正）
# ==================================================
import pandas as pd
from openai.types.responses import Response

# ==================================================
# メモリ応答デモ（改修版・エラー修正版）- 連続会話対応
# ==================================================
class MemoryResponseDemo(BaseDemo):
    """連続会話を管理するデモ（改修版・エラー修正版）"""

    def __init__(self, demo_name: str):
        super().__init__(demo_name)
        # 会話ステップの管理
        self.conversation_steps = []
        self._initialize_conversation_state()

    def _initialize_conversation_state(self):
        """会話状態の初期化"""
        session_key = f"conversation_steps_{self.safe_key}"
        if session_key not in st.session_state:
            st.session_state[session_key] = []

        self.conversation_steps = st.session_state[session_key]

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（改修版）"""
        self.initialize()
        st.write(
            "**連続会話デモ（改修版）**\n"
            "responses.create()で連続した会話を実現。各ステップで「プロンプト + 回答」の履歴を保持し、"
            "新しい質問を追加して連続実行します。会話の流れと各ステップが視覚的に確認できます。"
        )

        with st.expander("OpenAI API(IPO):実装例", expanded=False):
            st.code("""
            # 1回目: 初回質問
            messages = get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input_1))
            response_1 = self.call_api_unified(messages, temperature=temperature)
              ┗ api_params = {
                "input": messages,
                "model": model
                }
                self.client.responses.create(**params)
    
            # 2回目以降: 履歴 + 新しい質問
            messages.append(EasyInputMessageParam(role="assistant", content=response_1_text))
            messages.append(EasyInputMessageParam(role="user", content=user_input_2))
            response_2 = self.call_api_unified(messages, temperature=temperature)
    
            # 連続実行...
            """)

        # 会話履歴の表示
        self._display_conversation_history()

        # 新しい質問の入力フォーム
        self._create_input_form()

        # 会話管理ボタン
        self._create_conversation_controls()

        self.show_debug_info()

    def _display_conversation_history(self):
        """会話履歴の表示"""
        if not self.conversation_steps:
            st.info("💬 会話を開始してください。質問を入力すると会話履歴が表示されます。")
            return

        st.subheader("📝 会話履歴")

        # 会話統計の表示
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("会話ステップ数", len(self.conversation_steps))
        with col2:
            total_tokens = sum(step.get('total_tokens', 0) for step in self.conversation_steps)
            st.metric("累計トークン数", f"{total_tokens:,}")
        with col3:
            if self.conversation_steps:
                latest_step = self.conversation_steps[-1]
                latest_time = latest_step.get('timestamp', 'N/A')
                st.metric("最新質問時刻", latest_time[-8:] if len(latest_time) > 8 else latest_time)  # 時刻部分のみ表示

        # 各会話ステップの表示
        for i, step in enumerate(self.conversation_steps, 1):
            with st.expander(
                    f"🔄 ステップ {i}: {step['user_input'][:50]}{'...' if len(step['user_input']) > 50 else ''}",
                    expanded=(i == len(self.conversation_steps))):

                # ステップ詳細情報
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**質問時刻**: {step.get('timestamp', 'N/A')}")
                    st.write(f"**使用モデル**: {step.get('model', 'N/A')}")
                with col2:
                    if 'usage' in step and step['usage']:
                        usage = step['usage']
                        st.write(f"**トークン使用**")
                        st.write(f"入力: {usage.get('prompt_tokens', 0)}")
                        st.write(f"出力: {usage.get('completion_tokens', 0)}")
                        st.write(f"合計: {usage.get('total_tokens', 0)}")

                # ユーザーの質問
                st.write("**👤 ユーザーの質問:**")
                st.markdown(f"> {step['user_input']}")

                # AIの回答
                st.write("**🤖 AIの回答:**")
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(step['assistant_response'])

                # この時点でのメッセージ履歴
                if st.checkbox(f"メッセージ履歴を表示 (ステップ {i})", key=f"show_messages_{i}_{self.safe_key}"):
                    st.write("**📋 この時点でのメッセージ履歴:**")
                    messages = step.get('messages_at_step', [])
                    for j, msg in enumerate(messages):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        content_preview = content[:100] + '...' if len(content) > 100 else content
                        st.write(f"{j + 1}. **{role}**: {content_preview}")

    def _create_input_form(self):
        """入力フォームの作成（フォーム不使用版）"""
        st.subheader("💭 新しい質問")

        # 現在の会話コンテキスト情報
        if self.conversation_steps:
            st.info(
                f"ℹ️ 現在 {len(self.conversation_steps)} ステップの会話履歴があります。新しい質問はこの履歴を踏まえて回答されます。")
        else:
            st.info("ℹ️ 最初の質問です。デフォルトプロンプトと共に送信されます。")

        # セッション状態でユーザー入力を管理
        input_key = f"user_input_{self.safe_key}"
        temp_key = f"temperature_{self.safe_key}"

        # 初期化
        if input_key not in st.session_state:
            st.session_state[input_key] = ""
        if temp_key not in st.session_state:
            st.session_state[temp_key] = 0.3

        # 質問例の表示
        example_questions = self._get_example_questions()
        if example_questions:
            st.write("**質問例:** （クリックで入力欄に設定）")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button(f"📝 {example_questions[0][:30]}...", key=f"example_0_{self.safe_key}",
                             help=example_questions[0]):
                    st.session_state[input_key] = example_questions[0]
                    st.rerun()
            with col2:
                if len(example_questions) > 1:
                    if st.button(f"📝 {example_questions[1][:30]}...", key=f"example_1_{self.safe_key}",
                                 help=example_questions[1]):
                        st.session_state[input_key] = example_questions[1]
                        st.rerun()
            with col3:
                if len(example_questions) > 2:
                    if st.button(f"📝 {example_questions[2][:30]}...", key=f"example_2_{self.safe_key}",
                                 help=example_questions[2]):
                        st.session_state[input_key] = example_questions[2]
                        st.rerun()

        # 入力エリア（セッション状態と連動）
        user_input = st.text_area(
            "質問を入力してください:",
            value=st.session_state[input_key],
            height=config.get("ui.text_area_height", 75),
            key=f"text_area_{self.safe_key}",
            placeholder="前回の会話を踏まえた質問をしてください...",
            on_change=self._on_text_change
        )

        # ユーザー入力の同期
        st.session_state[input_key] = user_input

        # Temperature設定
        col1, col2 = st.columns([2, 1])
        with col1:
            if not self.is_reasoning_model(self.model):
                temperature = st.slider(
                    "Temperature",
                    0.0, 1.0, st.session_state[temp_key], 0.05,
                    help="低い値ほど一貫性のある回答",
                    key=f"temp_slider_{self.safe_key}"
                )
                st.session_state[temp_key] = temperature
            else:
                st.info("ℹ️ 推論系モデル（o1, o3, o4系）ではtemperatureパラメータは使用されません")
                temperature = None

        # ボタン群
        with col2:
            col2_1, col2_2, col2_3 = st.columns(3)

            with col2_1:
                submitted = st.button(
                    "🚀 送信",
                    key=f"submit_{self.safe_key}",
                    use_container_width=True,
                    type="primary"
                )

            with col2_2:
                clear_clicked = st.button(
                    "🔄 クリア",
                    key=f"clear_{self.safe_key}",
                    use_container_width=True
                )

            with col2_3:
                st.write("")  # スペース調整

        # ボタン処理
        if clear_clicked:
            st.session_state[input_key] = ""
            st.rerun()

        if submitted and user_input.strip():
            self._process_conversation_step(user_input, temperature)
        elif submitted and not user_input.strip():
            st.warning("⚠️ 質問を入力してください。")

    def _on_text_change(self):
        """テキストエリアの変更時コールバック"""
        # このメソッドは必要に応じて処理を追加
        pass

    def _get_example_questions(self):
        """会話ステップに応じた質問例を取得"""
        if not self.conversation_steps:
            # 初回質問の例
            return [
                "Python でウェブスクレイピングの基本的な方法を教えてください",
                "機械学習の教師あり学習について説明してください",
                "REST APIとは何か、基本的な概念を教えてください"
            ]
        else:
            # 継続質問の例
            return [
                "もう少し詳しく説明してください",
                "具体的なコード例を示してください",
                "関連する技術やライブラリも教えてください",
                "実際のプロジェクトではどのように活用しますか？",
                "これの注意点やベストプラクティスはありますか？"
            ]

    def _process_conversation_step(self, user_input: str, temperature: Optional[float]):
        """会話ステップの処理"""
        # 実行回数を更新
        session_key = f"demo_state_{self.safe_key}"
        if session_key in st.session_state:
            st.session_state[session_key]['execution_count'] += 1

        # トークン情報の表示
        UIHelper.show_token_info(user_input, self.model, position="sidebar")

        # メッセージ履歴の構築
        messages = self._build_conversation_messages(user_input)

        # APIコール
        with st.spinner("🤖 AIが思考中..."):
            response = self.call_api_unified(messages, temperature=temperature)

        # レスポンスからテキストを抽出
        assistant_texts = ResponseProcessor.extract_text(response)
        assistant_response = assistant_texts[0] if assistant_texts else "応答を取得できませんでした"

        # 会話ステップの記録
        step_data = {
            'step_number'       : len(self.conversation_steps) + 1,
            'timestamp'         : format_timestamp(),
            'model'             : self.model,
            'user_input'        : user_input,
            'assistant_response': assistant_response,
            'messages_at_step'  : [dict(msg) for msg in messages],  # EasyInputMessageParamを辞書に変換
            'temperature'       : temperature,
            'usage'             : self._extract_usage_info(response),
            'total_tokens'      : self._calculate_total_tokens(response)
        }

        # セッション状態に保存
        self.conversation_steps.append(step_data)
        st.session_state[f"conversation_steps_{self.safe_key}"] = self.conversation_steps

        # 成功メッセージと即座の表示更新
        st.success(f"✅ ステップ {step_data['step_number']} の応答を取得しました")

        # レスポンスの表示
        st.subheader("🤖 最新の回答")
        ResponseProcessorUI.display_response(response)

        # フォームの再描画（入力フィールドがクリアされる）
        st.rerun()

    def _build_conversation_messages(self, new_user_input: str) -> List[EasyInputMessageParam]:
        """会話履歴を基にメッセージリストを構築"""
        # デフォルトメッセージから開始
        messages = get_default_messages()

        # 過去の会話ステップを追加
        for step in self.conversation_steps:
            messages.append(EasyInputMessageParam(role="user", content=step['user_input']))
            messages.append(EasyInputMessageParam(role="assistant", content=step['assistant_response']))

        # 新しいユーザー入力を追加
        messages.append(EasyInputMessageParam(role="user", content=new_user_input))

        return messages

    def _extract_usage_info(self, response: Response) -> Dict[str, Any]:
        """レスポンスから使用量情報を抽出"""
        try:
            if hasattr(response, 'usage') and response.usage:
                usage_obj = response.usage

                # Pydantic モデルの場合
                if hasattr(usage_obj, 'model_dump'):
                    return usage_obj.model_dump()
                elif hasattr(usage_obj, 'dict'):
                    return usage_obj.dict()
                else:
                    # 手動で属性を抽出
                    return {
                        'prompt_tokens'    : getattr(usage_obj, 'prompt_tokens', 0),
                        'completion_tokens': getattr(usage_obj, 'completion_tokens', 0),
                        'total_tokens'     : getattr(usage_obj, 'total_tokens', 0)
                    }
            return {}
        except Exception as e:
            logger.error(f"使用量情報の抽出エラー: {e}")
            return {}

    def _calculate_total_tokens(self, response: Response) -> int:
        """総トークン数の計算"""
        usage_info = self._extract_usage_info(response)
        return usage_info.get('total_tokens', 0)

    def _create_conversation_controls(self):
        """会話管理コントロール"""
        st.subheader("🛠️ 会話管理")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("🗑️ 会話履歴クリア", key=f"clear_conv_{self.safe_key}"):
                self.conversation_steps.clear()
                st.session_state[f"conversation_steps_{self.safe_key}"] = []
                st.success("会話履歴をクリアしました")
                st.rerun()

        with col2:
            if st.button("📥 会話履歴エクスポート", key=f"export_conv_{self.safe_key}"):
                self._export_conversation()

        with col3:
            uploaded_file = st.file_uploader(
                "📤 会話履歴インポート",
                type=['json'],
                key=f"import_conv_{self.safe_key}",
                help="過去にエクスポートした会話履歴をインポート"
            )
            if uploaded_file is not None:
                self._import_conversation(uploaded_file)

        with col4:
            if self.conversation_steps and st.button("📊 会話統計", key=f"stats_conv_{self.safe_key}"):
                self._show_conversation_statistics()

    def _export_conversation(self):
        """会話履歴のエクスポート"""
        if not self.conversation_steps:
            st.warning("エクスポートする会話履歴がありません")
            return

        export_data = {
            "export_info"       : {
                "timestamp"   : format_timestamp(),
                "total_steps" : len(self.conversation_steps),
                "model_used"  : self.model,
                "demo_version": "MemoryResponseDemo_v2.0"
            },
            "conversation_steps": self.conversation_steps
        }

        try:
            UIHelper.create_download_button(
                export_data,
                f"conversation_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
                "📥 会話履歴JSONダウンロード"
            )
        except Exception as e:
            st.error(f"エクスポートエラー: {e}")

    def _import_conversation(self, uploaded_file):
        """会話履歴のインポート"""
        try:
            content = uploaded_file.read()
            data = json.loads(content)

            if "conversation_steps" in data:
                imported_steps = data["conversation_steps"]

                # 現在の履歴に追加 or 置換
                replace_option = st.radio(
                    "インポート方法",
                    ["現在の履歴に追加", "現在の履歴を置換"],
                    key=f"import_option_{self.safe_key}"
                )

                if st.button("インポート実行", key=f"execute_import_{self.safe_key}"):
                    if replace_option == "現在の履歴を置換":
                        self.conversation_steps = imported_steps
                    else:
                        self.conversation_steps.extend(imported_steps)

                    st.session_state[f"conversation_steps_{self.safe_key}"] = self.conversation_steps
                    st.success(f"{len(imported_steps)}ステップの会話履歴をインポートしました")
                    st.rerun()
            else:
                st.error("有効な会話履歴データが見つかりません")

        except Exception as e:
            st.error(f"インポートエラー: {e}")
            logger.error(f"Conversation import error: {e}")

    def _show_conversation_statistics(self):
        """会話統計の表示"""
        if not self.conversation_steps:
            return

        with st.expander("📊 詳細統計", expanded=True):
            # 基本統計
            total_steps = len(self.conversation_steps)
            total_user_chars = sum(len(step['user_input']) for step in self.conversation_steps)
            total_assistant_chars = sum(len(step['assistant_response']) for step in self.conversation_steps)
            total_tokens = sum(step.get('total_tokens', 0) for step in self.conversation_steps)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("総会話ステップ", total_steps)
                st.metric("ユーザー入力文字数", f"{total_user_chars:,}")
                st.metric("AI応答文字数", f"{total_assistant_chars:,}")
            with col2:
                st.metric("総トークン数", f"{total_tokens:,}")
                if total_steps > 0:
                    avg_tokens = total_tokens / total_steps
                    st.metric("平均トークン/ステップ", f"{avg_tokens:.1f}")

                # コスト推定
                try:
                    estimated_cost = TokenManager.estimate_cost(
                        total_tokens // 2,  # 概算で半分を入力トークンと仮定
                        total_tokens // 2,  # 半分を出力トークンと仮定
                        self.model
                    )
                    st.metric("推定総コスト", f"${estimated_cost:.6f}")
                except Exception as e:
                    st.warning(f"コスト推定エラー: {e}")

            # 時系列グラフ（簡易版）
            st.write("**ステップ別トークン使用量**")
            step_tokens = [step.get('total_tokens', 0) for step in self.conversation_steps]
            if step_tokens:
                try:
                    df = pd.DataFrame({
                        'ステップ'  : range(1, len(step_tokens) + 1),
                        'トークン数': step_tokens
                    })
                    st.bar_chart(df.set_index('ステップ'))
                except Exception as e:
                    st.warning(f"グラフ表示エラー: {e}")

            # 質問の傾向分析（簡易版）
            st.write("**質問の長さ分布**")
            question_lengths = [len(step['user_input']) for step in self.conversation_steps]
            if question_lengths:
                avg_length = sum(question_lengths) / len(question_lengths)
                max_length = max(question_lengths)
                min_length = min(question_lengths)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("平均質問長", f"{avg_length:.1f}文字")
                with col2:
                    st.metric("最長質問", f"{max_length}文字")
                with col3:
                    st.metric("最短質問", f"{min_length}文字")

# ==================================================
# 画像応答デモ
# ==================================================
class ImageResponseDemo(BaseDemo):
    """画像入力のデモ（統一化版）"""

    def __init__(self, demo_name: str, use_base64: bool = False):
        super().__init__(demo_name)
        self.use_base64 = use_base64

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        with st.expander("OpenAI API(IPO):実装例", expanded=False):
            st.write(
                "マルチモーダル対応のresponses.create()デモ。URL・Base64形式の画像入力に対応。ResponseInputTextParamとResponseInputImageParamを組み合わせて画像解析を実行。GPT-4oの視覚機能活用例。")
            st.code("""
            messages = get_default_messages()
            messages.append(
                EasyInputMessageParam(
                    role="user",
                    content=[
                        ResponseInputTextParam(type="input_text", text=question),
                        ResponseInputImageParam(
                            type="input_image",
                            image_url=image_url,
                            detail="auto"
                        ),
                    ],
                )
            )
            response = self.call_api_unified(messages, temperature=temperature)
            ResponseProcessorUI.display_response(response)
            """)

        if self.use_base64:
            self._run_base64_demo()
        else:
            self._run_url_demo()

    def _run_url_demo(self):
        """URL画像のデモ（統一化版）"""
        st.write("例: このイメージを日本語で説明しなさい。")

        image_url = st.text_input(
            "画像URLを入力してください",
            value=image_path_sample,
            key=f"img_url_{self.safe_key}"
        )

        if image_url:
            try:
                st.image(image_url, caption="入力画像", use_container_width=True)
            except Exception as e:
                st.error(f"画像の表示に失敗しました: {e}")

        with st.form(key=f"img_form_{self.safe_key}"):
            question = st.text_input("質問", value="このイメージを日本語で説明しなさい。")

            # 統一されたtemperatureコントロール
            temperature = self.create_temperature_control(
                default_temp=0.3,
                help_text="低い値ほど一貫性のある回答"
            )

            submitted = st.form_submit_button("画像で質問")

        if submitted and image_url and question:
            self._process_image_question(question, image_url, temperature)

    def _run_base64_demo(self):
        """Base64画像のデモ（統一化版）"""
        images_dir = config.get("paths.images_dir", "images")
        files = self._get_image_files(images_dir)

        if not files:
            st.warning(f"{images_dir} に画像ファイルがありません")
            return

        file_path = st.selectbox("画像ファイルを選択", files, key=f"img_select_{self.safe_key}")

        with st.form(key=f"img_b64_form_{self.safe_key}"):
            # 統一されたtemperatureコントロール
            temperature = self.create_temperature_control(
                default_temp=0.3,
                help_text="低い値ほど一貫性のある回答"
            )

            submitted = st.form_submit_button("選択画像で実行")

        if submitted and file_path:
            self._process_base64_image(file_path, temperature)

    def _get_image_files(self, images_dir: str) -> List[str]:
        """画像ファイルのリストを取得"""
        patterns = ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif"]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(f"{images_dir}/{pattern}"))
        return sorted(files)

    def _encode_image(self, path: str) -> str:
        """画像をBase64エンコード"""
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception as e:
            st.error(f"画像エンコードエラー: {e}")
            return ""

    def _process_image_question(self, question: str, image_url: str, temperature: Optional[float]):
        """画像質問の処理（統一化版）"""
        messages = get_default_messages()
        messages.append(
            EasyInputMessageParam(
                role="user",
                content=[
                    ResponseInputTextParam(type="input_text", text=question),
                    ResponseInputImageParam(
                        type="input_image",
                        image_url=image_url,
                        detail="auto"
                    ),
                ],
            )
        )

        with st.spinner("処理中..."):
            response = self.call_api_unified(messages, temperature=temperature)

        st.subheader("回答:")
        ResponseProcessorUI.display_response(response)

    def _process_base64_image(self, file_path: str, temperature: Optional[float]):
        """Base64画像の処理（統一化版）"""
        b64 = self._encode_image(file_path)
        if not b64:
            return

        st.image(file_path, caption="選択画像", width=320)

        messages = get_default_messages()
        messages.append(
            EasyInputMessageParam(
                role="user",
                content=[
                    ResponseInputTextParam(
                        type="input_text",
                        text="このイメージを日本語で説明しなさい。"
                    ),
                    ResponseInputImageParam(
                        type="input_image",
                        image_url=f"data:image/jpeg;base64,{b64}",
                        detail="auto"
                    ),
                ],
            )
        )

        with st.spinner("処理中..."):
            response = self.call_api_unified(messages, temperature=temperature)

        st.subheader("出力テキスト:")
        ResponseProcessorUI.display_response(response)


# ==================================================
# 構造化出力デモ（修正版・左ペインモデル選択統一）
# ==================================================
class StructuredOutputDemo(BaseDemo):
    """構造化出力のデモ"""

    class Event(BaseModel):
        """イベント情報のPydanticモデル"""
        name: str
        date: str
        participants: List[str]

    def __init__(self, demo_name: str, use_parse: bool = False):
        super().__init__(demo_name)
        self.use_parse = use_parse

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（修正版・左ペインモデル選択統一）"""
        self.initialize()  # 左ペインにモデル選択が作成される
        st.write(
            "構造化出力特化のresponses.create()/responses.parse()デモ。PydanticモデルとJSON Schemaによる型安全な出力抽出。"
            "イベント情報の構造化抽出例を通じて、データ処理アプリでのAPI活用を学習。"
        )
        with st.expander("OpenAI API(IPO):実装例", expanded=False):
            st.code("""
            # イベント情報のPydanticモデル
            class Event(BaseModel):
                name: str
                date: str
                participants: List[str]
            
            # 実行方式を選択
            # ["responses.create() を使用", "responses.parse() を使用"]
            # responses.createを使用した実行 ---------------------------
            schema = {
                "type"                : "object",
                "properties"          : {
                    "name"        : {
                        "type"       : "string",
                        "description": "イベントの名前"
                    },
                    "date"        : {
                        "type"       : "string",
                        "description": "イベントの開催日（YYYY-MM-DD形式）"
                    },
                    "participants": {
                        "type"       : "array",
                        "items"      : {"type": "string"},
                        "description": "参加者リスト"
                    },
                },
                "required"            : ["name", "date", "participants"],
                "additionalProperties": False,
            }
    
            messages = [
                EasyInputMessageParam(
                    role="developer",
                    content="Extract event details from the text. Extract name, date, and participants."
                ),
                EasyInputMessageParam(
                    role="user",
                    content=[ResponseInputTextParam(type="input_text", text=text)]
                ),
            ]
            text_cfg = ResponseTextConfigParam(
                format=ResponseFormatTextJSONSchemaConfigParam(
                    name="event_extraction",
                    type="json_schema",
                    schema=schema,
                    strict=True,
                )
            )
            api_params = {
                "model": model,
                "input": messages,
                "text" : text_cfg
            }
            response = self.client.create_response(**api_params)
            # ----------------------------------------------------
            
            # responses.parseを使用した実行
            # Responses API用のメッセージ形式
            messages = [
                EasyInputMessageParam(
                    role="developer",
                    content="Extract event details from the text. Extract name, date, and participants."
                ),
                EasyInputMessageParam(
                    role="user",
                    content=[ResponseInputTextParam(type="input_text", text=text)]
                ),
            ]
            api_params = {
                "model"      : model,
                "input"      : messages,
                "text_format": self.Event,
            }
            response = self.client.parse_response(**api_params)
            event = response.output_parsed
            
            """)

        # 選択されたモデルの表示（情報として）
        st.info(f"🤖 使用モデル: **{self.model}**")

        # モデルの推奨事項
        if "gpt-4o" in self.model:
            st.success("✅ 構造化出力に適したモデルが選択されています")
        elif self.model.startswith("o"):
            st.warning("⚠️ 推論系モデルは構造化出力で制限される場合があります")
        else:
            st.info("ℹ️ 構造化出力には gpt-4o 系モデルが推奨されます")

        # イベント情報入力
        default_event = config.get("samples.prompts.event_example",
                                   "台湾フェス2025-08-21 ～あつまれ！究極の台湾グルメ～")

        st.subheader("📝 イベント情報入力")
        text = st.text_input(
            "イベント詳細を入力",
            value=default_event,
            key=f"struct_input_{self.safe_key}",
            help="イベント名、日付、参加者情報を含むテキストを入力してください"
        )

        # 統一されたtemperatureコントロール
        temperature = self.create_temperature_control(
            default_temp=0.1,
            help_text="構造化出力では低い値を推奨"
        )

        # 実行方式の選択
        st.subheader("⚙️ 実行方式")
        use_parse_option = st.radio(
            "実行方式を選択",
            ["responses.create() を使用", "responses.parse() を使用"],
            index=0 if not self.use_parse else 1,
            key=f"parse_option_{self.safe_key}",
            help="responses.create()は汎用的、chat.completions.parse()はPydantic特化"
        )

        # 選択に基づいてuse_parseを更新
        self.use_parse = (use_parse_option == "responses.parse() を使用")

        # 実行ボタン
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            execute_button = st.button(
                "🚀 イベント抽出を実行",
                key=f"struct_btn_{self.safe_key}",
                use_container_width=True,
                type="primary"
            )

        # 実行処理
        if execute_button and text.strip():
            if self.use_parse:
                self._run_with_parse(self.model, text, temperature)
            else:
                self._run_with_create(self.model, text, temperature)
        elif execute_button and not text.strip():
            st.warning("⚠️ イベント詳細を入力してください。")

        # サンプル表示
        self._show_sample_output()

    def _run_with_create(self, model: str, text: str, temperature: Optional[float]):
        """responses.createを使用した実行（修正版）"""
        try:
            st.info("🔄 responses.create() でイベント情報を抽出中...")

            schema = {
                "type"                : "object",
                "properties"          : {
                    "name"        : {
                        "type"       : "string",
                        "description": "イベントの名前"
                    },
                    "date"        : {
                        "type"       : "string",
                        "description": "イベントの開催日（YYYY-MM-DD形式）"
                    },
                    "participants": {
                        "type"       : "array",
                        "items"      : {"type": "string"},
                        "description": "参加者リスト"
                    },
                },
                "required"            : ["name", "date", "participants"],
                "additionalProperties": False,
            }

            messages = [
                EasyInputMessageParam(
                    role="developer",
                    content="Extract event details from the text. Extract name, date, and participants."
                ),
                EasyInputMessageParam(
                    role="user",
                    content=[ResponseInputTextParam(type="input_text", text=text)]
                ),
            ]

            text_cfg = ResponseTextConfigParam(
                format=ResponseFormatTextJSONSchemaConfigParam(
                    name="event_extraction",
                    type="json_schema",
                    schema=schema,
                    strict=True,
                )
            )

            with st.spinner("🤖 AI がイベント情報を抽出しています..."):
                # 統一されたAPI呼び出し（左ペインで選択されたモデルを使用）
                api_params = {
                    "model": model,
                    "input": messages,
                    "text" : text_cfg
                }

                # temperatureサポートチェック
                if not self.is_reasoning_model(model) and temperature is not None:
                    api_params["temperature"] = temperature

                response = self.client.create_response(**api_params)

            # 結果の表示
            st.success("✅ イベント情報の抽出が完了しました")

            # JSON出力をPydanticモデルで検証
            event = self.Event.model_validate_json(response.output_text)

            st.subheader("📋 抽出結果 (responses.create)")
            self._display_extracted_event(event, response)

        except (ValidationError, json.JSONDecodeError) as e:
            st.error("❌ 構造化データの解析に失敗しました")
            with st.expander("🔧 エラー詳細", expanded=False):
                st.exception(e)
        except Exception as e:
            self.handle_error(e)

    def _run_with_parse(self, model: str, text: str, temperature: Optional[float]):
        """responses.parseを使用した実行"""
        try:
            st.info("🔄 responses.parse() でイベント情報を抽出中...")

            # Responses API用のメッセージ形式に変更
            messages = [
                EasyInputMessageParam(
                    role="developer",
                    content="Extract event details from the text. Extract name, date, and participants."
                ),
                EasyInputMessageParam(
                    role="user",
                    content=[ResponseInputTextParam(type="input_text", text=text)]
                ),
            ]

            with st.spinner("🤖 AI がイベント情報を抽出しています..."):
                # 統一されたAPI呼び出し（responses.parseを使用）
                api_params = {
                    "model": model,
                    "input": messages,
                    "text_format": self.Event
                }

                # temperatureサポートチェック
                if not self.is_reasoning_model(model) and temperature is not None:
                    api_params["temperature"] = temperature

                response = self.client.parse_response(**api_params)

            # 結果の表示
            st.success("✅ イベント情報の抽出が完了しました")

            # responses.parseの結果はoutput_parsedに格納される
            event = response.output_parsed

            st.subheader("📋 抽出結果 (responses.parse)")
            self._display_extracted_event(event, response)

        except Exception as e:
            st.error(f"❌ responses.parse実行エラー: {str(e)}")
            self.handle_error(e)

    def _display_extracted_event(self, event: Event, response):
        """抽出されたイベント情報の表示（エクスパンダー入れ子修正版）"""
        # メインの結果表示
        col1, col2 = st.columns([2, 1])

        with col1:
            # イベント情報を見やすく表示
            st.write("**🎉 イベント名**")
            st.success(event.name)

            st.write("**📅 開催日**")
            st.info(event.date)

            st.write("**👥 参加者**")
            if event.participants:
                for i, participant in enumerate(event.participants, 1):
                    st.write(f"{i}. {participant}")
            else:
                st.write("参加者情報なし")

        with col2:
            # 統計情報
            st.metric("参加者数", len(event.participants))
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                if hasattr(usage, 'total_tokens'):
                    st.metric("使用トークン数", getattr(usage, 'total_tokens', 0))

        # 構造化データの表示（エクスパンダーなしで直接表示）
        st.write("---")
        st.write("**🔧 構造化データ (Pydantic):**")

        # Pydanticモデルとして表示
        safe_streamlit_json(event.model_dump())

        # Pythonオブジェクトとして表示
        st.write("**Python オブジェクト:**")
        st.code(repr(event), language="python")

        # レスポンス詳細（エクスパンダーなしで簡潔に表示）
        st.write("---")
        st.write("**📊 API レスポンス概要:**")

        # 基本情報のみ表示
        info_cols = st.columns(3)
        with info_cols[0]:
            model_name = getattr(response, 'model', 'N/A')
            st.write(f"**モデル**: {model_name}")
        with info_cols[1]:
            response_id = getattr(response, 'id', 'N/A')
            st.write(f"**ID**: {response_id[:10]}..." if len(str(response_id)) > 10 else f"**ID**: {response_id}")
        with info_cols[2]:
            st.write(f"**形式**: Structured JSON")

    def _show_sample_output(self):
        """サンプル出力の表示（修正版）"""
        with st.expander("📖 サンプル出力例", expanded=False):
            st.write("**入力例:**")
            st.code('台湾フェス2025 ～あつまれ！究極の台湾グルメ～ in Kawasaki Spark', language="text")

            st.write("**期待される出力:**")
            sample_event = {
                "name"        : "台湾フェス2025 ～あつまれ！究極の台湾グルメ～",
                "date"        : "2025-08-15",
                "participants": ["グルメ愛好家", "台湾料理ファン", "地域住民"]
            }
            safe_streamlit_json(sample_event)

            st.write("**実行方式の違い:**")
            st.write("- **responses.create()**: JSON Schemaを使用した汎用的な構造化出力")
            st.write("- **responses.parse()**: Pydanticモデルを直接使用した型安全な出力")

            st.write("**Pydantic モデル定義:**")
            st.code('''
class Event(BaseModel):
    """イベント情報のPydanticモデル"""
    name: str
    date: str
    participants: List[str]
            ''', language="python")


# ==================================================
# 天気デモ
# ==================================================
class WeatherDemo(BaseDemo):
    """OpenWeatherMap APIを使用した天気デモ（改修版・ボタン実行対応）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（改修版）"""
        self.initialize()
        st.header("構造化出力: 天気デモ")
        st.write(
            "外部API連携デモ（改修版）。都市選択後、「APIを実行」ボタンでOpenWeatherMap APIを呼び出し、"
            "天気情報を表示します。実世界データ統合とUI操作フローの実装例。"
        )
        with st.expander("利用：OpenWeatherMap API(比較用)", expanded=False):
            st.code("""
            df_jp = self._load_japanese_cities(cities_json)
            # def _get_current_weather
            url = "http://api.openweathermap.org/data/2.5/weather"
                params = {
                    "lat"  : lat,
                    "lon"  : lon,
                    "appid": api_key,
                    "units": unit,
                    "lang" : "ja"  # 日本語での天気説明
                }
            response = requests.get(url, params=params, timeout=config.get("api.timeout", 30))
            """)

        # 都市データの読み込み（JSONから日本都市のみ）
        cities_json = config.get("paths.cities_json", "data/city_jp.list.json")
        if not Path(cities_json).exists():
            st.error(f"都市データファイルが見つかりません: {cities_json}")
            return

        df_jp = self._load_japanese_cities(cities_json)

        # 都市選択UI
        city, lat, lon = self._select_city(df_jp)

        # APIを実行ボタンの追加
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            api_execute = st.button(
                "🌤️ APIを実行",
                key=f"weather_api_{self.safe_key}",
                use_container_width=True,
                type="primary",
                help=f"選択した都市（{city}）の天気情報を取得します"
            )

        # 選択された都市の情報表示
        if city and lat and lon:
            with st.expander("📍 選択された都市情報", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("都市名", city)
                with col2:
                    st.metric("緯度", f"{lat:.4f}")
                with col3:
                    st.metric("経度", f"{lon:.4f}")

        # APIキーの確認
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            st.warning("⚠️ OPENWEATHER_API_KEY環境変数が設定されていません")
            st.info("天気APIを利用するには、OpenWeatherMapのAPIキーが必要です。")
            st.code("export OPENWEATHER_API_KEY='your-api-key'", language="bash")
            return

        # APIを実行ボタンが押された場合
        if api_execute:
            if city and lat and lon:
                st.info(f"🔍 {city}の天気情報を取得中...")
                self._display_weather(lat, lon, city)
            else:
                st.error("❌ 都市が正しく選択されていません。都市を選択してから再実行してください。")

    def _load_japanese_cities(self, json_path: str) -> pd.DataFrame:
        """日本の都市データを city_jp.list.json から読み込み"""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                cities_list = json.load(f)
            # 必要なカラムのみ抽出
            df = pd.DataFrame([
                {
                    "name": city["name"],
                    "lat" : city["coord"]["lat"],
                    "lon" : city["coord"]["lon"],
                    "id"  : city["id"]
                }
                for city in cities_list
            ])
            # 都市名でソート
            return df.sort_values("name").reset_index(drop=True)
        except Exception as e:
            st.error(f"都市データの読み込みに失敗しました: {e}")
            return pd.DataFrame()

    def _select_city(self, df: pd.DataFrame) -> tuple:
        """都市選択UI（改修版）"""
        if df.empty:
            st.error("都市データが空です")
            return "Tokyo", 35.6895, 139.69171

        # 都市選択の説明
        st.subheader("🏙️ 都市選択")
        st.write("天気情報を取得したい都市を選択してください：")

        # 都市選択ボックス
        city = st.selectbox(
            "都市を選択してください",
            df["name"].tolist(),
            key=f"city_{self.safe_key}",
            help="日本国内の主要都市から選択できます"
        )

        row = df[df["name"] == city].iloc[0]

        return city, row["lat"], row["lon"]

    def _display_weather(self, lat: float, lon: float, city_name: str = None):
        """天気情報の表示（改修版）"""
        try:
            # 実行時間の計測開始
            start_time = time.time()

            # 現在の天気
            with st.spinner(f"🌤️ {city_name or '選択した都市'}の現在の天気を取得中..."):
                today = self._get_current_weather(lat, lon)

            if today:
                st.success("✅ 現在の天気情報を取得しました")

                # 現在の天気表示
                with st.container():
                    st.write("### 📍 本日の天気")

                    # メトリクス表示
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🏙️ 都市", today['city'])
                    with col2:
                        st.metric("🌡️ 気温", f"{today['temperature']}℃")
                    with col3:
                        st.metric("💨 天気", today['description'])
                    with col4:
                        # 座標情報
                        coord = today.get('coord', {})
                        st.metric("📍 座標", f"{coord.get('lat', 'N/A'):.2f}, {coord.get('lon', 'N/A'):.2f}")

            # 週間予報
            with st.spinner("📊 5日間予報を取得中..."):
                forecast = self._get_weekly_forecast(lat, lon)

            if forecast:
                st.success("✅ 週間予報を取得しました")

                # 5日間予報表示
                with st.container():
                    st.write("### 📅 5日間予報 （3時間毎データの日別平均）")

                    # テーブル形式で表示
                    forecast_df = pd.DataFrame(forecast)

                    # データフレームのカラム名を日本語に変更
                    forecast_df = forecast_df.rename(columns={
                        'date'    : '日付',
                        'temp_avg': '平均気温(℃)',
                        'weather' : '天気'
                    })

                    st.dataframe(
                        forecast_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    # グラフ表示
                    if len(forecast) > 1:
                        st.write("### 📈 気温推移")
                        temp_data = pd.DataFrame({
                            '日付'    : [item['date'] for item in forecast],
                            '平均気温': [item['temp_avg'] for item in forecast]
                        })
                        st.line_chart(temp_data.set_index('日付'))

            # 実行時間の表示
            end_time = time.time()
            execution_time = end_time - start_time

            with st.expander("🔧 API実行詳細", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("実行時間", f"{execution_time:.2f}秒")
                with col2:
                    st.metric("API呼び出し数", "2回")  # 現在天気 + 5日間予報
                with col3:
                    st.metric("データ形式", "JSON")

                st.write("**API詳細:**")
                st.write("- 現在の天気: OpenWeatherMap Current Weather API")
                st.write("- 5日間予報: OpenWeatherMap 5 Day Weather Forecast API")
                st.write("- データ更新頻度: リアルタイム")

        except Exception as e:
            st.error(f"❌ 天気情報の取得に失敗しました: {str(e)}")
            logger.error(f"Weather API error: {e}")

            # エラーの詳細表示（デバッグモード時）
            if config.get("experimental.debug_mode", False):
                with st.expander("🔧 エラー詳細", expanded=False):
                    st.exception(e)

    def _get_current_weather(self, lat: float, lon: float, unit: str = "metric") -> dict[str, Any] | None:
        """現在の天気を取得（改修版）"""
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            st.error("❌ OPENWEATHER_API_KEY環境変数が設定されていません")
            return None

        try:
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                "lat"  : lat,
                "lon"  : lon,
                "appid": api_key,
                "units": unit,
                "lang" : "ja"  # 日本語での天気説明
            }

            response = requests.get(url, params=params, timeout=config.get("api.timeout", 30))
            response.raise_for_status()
            data = response.json()

            return {
                "city"       : data["name"],
                "temperature": round(data["main"]["temp"], 1),
                "description": data["weather"][0]["description"],
                "coord"      : data["coord"],
                "humidity"   : data["main"]["humidity"],
                "pressure"   : data["main"]["pressure"],
                "wind_speed" : data.get("wind", {}).get("speed", 0)
            }
        except requests.exceptions.RequestException as e:
            st.error(f"❌ 天気API呼び出しエラー: {e}")
            logger.error(f"Weather API request error: {e}")
            return None
        except Exception as e:
            st.error(f"❌ 天気データ処理エラー: {e}")
            logger.error(f"Weather data processing error: {e}")
            return None

    def _get_weekly_forecast(self, lat: float, lon: float, unit: str = "metric") -> List[dict]:
        """週間予報を取得（改修版）"""
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return []

        try:
            url = "http://api.openweathermap.org/data/2.5/forecast"
            params = {
                "lat"  : lat,
                "lon"  : lon,
                "units": unit,
                "appid": api_key,
                "lang" : "ja"  # 日本語での天気説明
            }

            response = requests.get(url, params=params, timeout=config.get("api.timeout", 30))
            response.raise_for_status()
            data = response.json()

            # 日別に集計
            daily = {}
            for item in data["list"]:
                date = item["dt_txt"].split(" ")[0]
                temp = item["main"]["temp"]
                weather = item["weather"][0]["description"]

                if date not in daily:
                    daily[date] = {"temps": [], "weather": weather}
                daily[date]["temps"].append(temp)

            # 平均気温を計算
            result = []
            for date, info in daily.items():
                avg_temp = round(sum(info["temps"]) / len(info["temps"]), 1)
                result.append({
                    "date"    : date,
                    "temp_avg": avg_temp,
                    "weather" : info["weather"]
                })

            return result

        except requests.exceptions.RequestException as e:
            st.error(f"❌ 予報API呼び出しエラー: {e}")
            logger.error(f"Forecast API request error: {e}")
            return []
        except Exception as e:
            st.error(f"❌ 予報データ処理エラー: {e}")
            logger.error(f"Forecast data processing error: {e}")
            return []

# ==================================================
# FileSearchデモ
# ==================================================
# 作成: POST /v1/vector_stores
# 一覧取得: GET /v1/vector_stores
# 詳細取得: GET /v1/vector_stores/{vector_store_id}
# 更新: POST /v1/vector_stores/{vector_store_id}
# 削除: DELETE /v1/vector_stores/{vector_store_id}
# 検索: POST /v1/vector_stores/{vector_store_id}/search
# ==================================================
class FileSearchVectorStoreDemo(BaseDemo):
    """FileSearch専用デモ（正しいOpenAI API対応版）"""

    def __init__(self, demo_name: str):
        super().__init__(demo_name)
        self._vector_stores_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5分間キャッシュ

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（正しいAPI対応版）"""
        self.initialize()
        st.header("FileSearchデモ")
        st.write(
            "（注）Vector Storeのデータは、英語なので、質問は英語の必要があります。"
            "セレクタで選択可能。responses.create()でドキュメント検索を実行し、"
            "Vector Store検索APIでの直接検索も可能。"
        )
        with st.expander("利用：OpenWeatherMap API(比較用)", expanded=False):
            st.code("""
            # FileSearchツールパラメータの作成
            fs_tool = FileSearchToolParam(
                type="file_search",
                vector_store_ids=[vector_store_id],
                max_num_results=max_results
            )
            # API呼び出し
            response = self.call_api_unified(
                messages=[EasyInputMessageParam(role="user", content=query)],
                tools=[fs_tool],
                include=["file_search_call.results"]
            )
            
            # self.call_api_unified
            # API呼び出しパラメータの準備
            api_params = {
                "input": messages,
                "model": model
            }
            # responses.create を使用（統一されたAPI呼び出し）
            
            return self.client.create_response(**api_params)
            """)

        # Vector Storeの取得と選択
        vector_store_info = self._get_vector_store_selection()

        if not vector_store_info:
            st.warning("⚠️ 利用可能なVector Storeが見つかりません。")
            st.info("💡 OpenAI PlaygroundでVector Storeを作成してください。")
            return

        vector_store_id = vector_store_info["id"]
        vector_store_name = vector_store_info["name"]

        # 選択されたVector Store情報を表示
        with st.expander("📂 選択されたVector Store情報", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write("**名前**:", vector_store_name)
                st.write("**ID**:", f"`{vector_store_id}`")

            with col2:
                if "file_counts" in vector_store_info:
                    file_counts = vector_store_info["file_counts"]
                    total_files = file_counts.get("total", 0)
                    completed_files = file_counts.get("completed", 0)
                    in_progress = file_counts.get("in_progress", 0)
                    failed = file_counts.get("failed", 0)

                    st.write("**ファイル数**:", f"{completed_files}/{total_files}")
                    if in_progress > 0:
                        st.info(f"⏳ 処理中: {in_progress}件")
                    if failed > 0:
                        st.warning(f"⚠️ 失敗: {failed}件")

            with col3:
                if "created_at" in vector_store_info:
                    created_date = datetime.fromtimestamp(vector_store_info["created_at"]).strftime("%Y-%m-%d %H:%M")
                    st.write("**作成日時**:", created_date)
                if "bytes" in vector_store_info:
                    bytes_size = vector_store_info["bytes"]
                    if bytes_size > 0:
                        mb_size = bytes_size / (1024 * 1024)
                        st.write("**容量**:", f"{mb_size:.2f} MB")

        #
        with st.expander("📂 英文-質問例", expanded=False):
            st.code("""
customer_support_faq.csv ：カスタマーサポート・FAQデータセット
    "How do I create a new account?",
    "What payment methods are available?",
    "Can I return a product?",
    "I forgot my password",
    "How can I contact the support team?"

sciq_qa.csv  ：科学・技術QAデータセット
    "What are the latest trends in artificial intelligence?",
    "What is the principle of quantum computing?",
    "What are the types and characteristics of renewable energy?",
    "What are the current status and challenges of gene editing technology?",
    "What are the latest technologies in space exploration?"

medical_qa.csv   ： 医療質問回答データセット
    "How to prevent high blood pressure?",
    "What are the symptoms and treatment of diabetes?",
    "What are the risk factors for heart disease?",
    "What are the guidelines for healthy eating?",
    "What is the relationship between exercise and health?"

legal_qa.csv  ：法律・判例QAデータセット
    "What are the important clauses in contracts?",
    "How to protect intellectual property rights?",
    "What are the basic principles of labor law?",
    "What is an overview of personal data protection law?",
    "What is the scope of application of consumer protection law?"
            """)

        st.write(
            "AI検索で回答が得られない固有の情報にも[Vector Store]から検索できます。"
            "Vector Storeのスコアが0.8以上はかなり良い、0.6以上が良いです。"
        )
        # 検索タブ
        tab1, tab2 = st.tabs(["🤖 AI検索 (Responses API)", "🔍 直接検索 (Vector Store API)"])


        with tab1:
            self._run_responses_search(vector_store_id)

        with tab2:
            self._run_direct_search(vector_store_id)

        # Vector Store一覧更新
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Vector Store一覧更新", key=f"refresh_{self.safe_key}"):
                self._clear_vector_stores_cache()
                st.rerun()

    def _run_responses_search(self, vector_store_id: str):
        """Responses APIを使用したFileSearch"""
        st.subheader("🤖 AI検索 (Responses API)")
        st.write("Responses APIのfile_searchツールを使用したAI回答付き検索")

        # 検索クエリ入力
        query = st.text_input(
            "🔍 検索クエリ",
            value="When is the payment deadline for the invoice? return policy?",
            help="Vector Store内のドキュメントから検索したい内容を入力してください",
            key=f"ai_search_query_{self.safe_key}"
        )

        # 検索オプション
        with st.expander("🔧 検索オプション", expanded=False):
            max_results = st.slider(
                "最大検索結果数",
                min_value=1,
                max_value=20,
                value=5,
                help="検索で取得する最大結果数"
            )

        # FileSearch実行
        if st.button("🚀 AI検索実行", key=f"ai_search_exec_{self.safe_key}", use_container_width=True):
            if query.strip():
                self._execute_ai_search(vector_store_id, query, max_results)
            else:
                st.error("❌ 検索クエリを入力してください。")

    def _run_direct_search(self, vector_store_id: str):
        """Vector Store APIを使用した直接検索"""
        st.subheader("🔍 直接検索 (Vector Store API)")
        st.write("Vector Store APIの検索機能を直接使用した検索")

        # 検索クエリ入力
        query = st.text_input(
            "🔍 検索クエリ",
            value="When is the payment deadline for the invoice? return policy?",
            help="Vector Store内のドキュメントから検索したい内容を入力してください",
            key=f"direct_search_query_{self.safe_key}"
        )

        # 検索オプション
        with st.expander("🔧 詳細検索オプション", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                max_results = st.slider(
                    "最大検索結果数",
                    min_value=1,
                    max_value=50,
                    value=10,
                    help="検索で取得する最大結果数（1-50）"
                )
                rewrite_query = st.checkbox(
                    "クエリ書き換え",
                    value=False,
                    help="自然言語クエリをベクトル検索用に書き換える"
                )
            with col2:
                # フィルタオプション（将来の拡張用）
                st.write("**フィルタオプション**")
                st.info("今後のアップデートで追加予定")

        # 直接検索実行
        if st.button("🔍 直接検索実行", key=f"direct_search_exec_{self.safe_key}", use_container_width=True):
            if query.strip():
                self._execute_direct_search(vector_store_id, query, max_results, rewrite_query)
            else:
                st.error("❌ 検索クエリを入力してください。")

    def _get_vector_stores(self) -> List[Dict[str, Any]]:
        """正しいOpenAI APIからVector Storeのリストを取得"""
        # キャッシュチェック
        if (self._vector_stores_cache is not None and
                self._cache_timestamp is not None and
                time.time() - self._cache_timestamp < self._cache_ttl):
            return self._vector_stores_cache

        try:
            with st.spinner("🔄 Vector Store一覧を取得中..."):
                # より明確なアクセス方法
                openai_client = self.client.client
                response = openai_client.vector_stores.list(
                    limit=20,
                    order="desc"  # 新しい順に取得
                )

                vector_stores = []
                # 最新の4つのみを処理
                for vs in response.data[:4]:
                    # file_countsはオブジェクトなので属性として直接アクセス
                    file_counts_obj = getattr(vs, 'file_counts', None)
                    if file_counts_obj:
                        file_counts_dict = {
                            "total"      : getattr(file_counts_obj, 'total', 0),
                            "completed"  : getattr(file_counts_obj, 'completed', 0),
                            "failed"     : getattr(file_counts_obj, 'failed', 0),
                            "in_progress": getattr(file_counts_obj, 'in_progress', 0),
                            "cancelled"  : getattr(file_counts_obj, 'cancelled', 0)
                        }
                    else:
                        file_counts_dict = {
                            "total"      : 0,
                            "completed"  : 0,
                            "failed"     : 0,
                            "in_progress": 0,
                            "cancelled"  : 0
                        }

                    vector_store_info = {
                        "id"         : vs.id,
                        "name"       : vs.name or f"Vector Store {vs.id[:8]}",
                        "created_at" : vs.created_at,
                        "bytes"      : getattr(vs, 'bytes', 0),
                        "file_counts": file_counts_dict,
                        "object"     : getattr(vs, 'object', 'vector_store'),
                    }
                    vector_stores.append(vector_store_info)

                # キャッシュ更新
                self._vector_stores_cache = vector_stores
                self._cache_timestamp = time.time()

                logger.info(f"取得したVector Store数: {len(vector_stores)}")
                return vector_stores

        except Exception as e:
            logger.error(f"Vector Store取得エラー: {e}")
            error_message = str(e)

            # 具体的なエラーメッセージの表示
            if "authentication" in error_message.lower():
                st.error("🔐 認証エラー: OpenAI APIキーを確認してください。")
            elif "rate limit" in error_message.lower():
                st.error("⏱️ レート制限エラー: しばらく待ってから再試行してください。")
            elif "permission" in error_message.lower() or "forbidden" in error_message.lower():
                st.error("🚫 権限エラー: Vector Store APIへのアクセス権限がありません。")
            else:
                st.error(f"❌ Vector Storeの取得に失敗しました: {error_message}")

            # フォールバック: デフォルトのVector Store
            st.info("💡 フォールバック: デフォルトのVector Storeを使用します。")
            fallback_stores = [{
                "id"         : "vs_68345a403a548191817b3da8404e2d82",
                "name"       : "デフォルト Vector Store (フォールバック)",
                "created_at" : time.time(),
                "bytes"      : 0,
                "file_counts": {"total": "不明", "completed": "不明", "failed": 0, "in_progress": 0}
            }]
            return fallback_stores

    def _clear_vector_stores_cache(self):
        """Vector Storeキャッシュをクリア"""
        self._vector_stores_cache = None
        self._cache_timestamp = None
        st.success("✅ キャッシュをクリアしました")

    def _get_vector_store_selection(self) -> Optional[Dict[str, Any]]:
        """Vector Store選択UIとデータ取得"""
        vector_stores = self._get_vector_stores()

        if not vector_stores:
            return None

        # セレクタ用の選択肢を作成
        options = []
        for vs in vector_stores:
            # ファイル数情報
            file_counts = vs.get('file_counts', {})
            total_files = file_counts.get('total', 0)
            completed_files = file_counts.get('completed', 0)
            file_info = f"({completed_files}/{total_files} files)"

            # 容量情報
            bytes_size = vs.get('bytes', 0)
            if bytes_size > 0:
                mb_size = bytes_size / (1024 * 1024)
                size_info = f" | {mb_size:.1f}MB"
            else:
                size_info = ""

            option_text = f"📂 {vs['name']} - {vs['id'][:20]}... {file_info}{size_info}"
            options.append(option_text)

        # Vector Store選択
        selected_index = st.selectbox(
            "📂 Vector Storeを選択",
            range(len(options)),
            format_func=lambda x: options[x],
            key=f"vs_select_{self.safe_key}",
            help="検索対象のVector Storeを選択してください"
        )

        return vector_stores[selected_index]

    def _execute_ai_search(self, vector_store_id: str, query: str, max_results: int = 5):
        """Responses APIを使用したAI検索の実行"""
        try:
            # FileSearchツールパラメータの作成
            fs_tool = FileSearchToolParam(
                type="file_search",
                vector_store_ids=[vector_store_id],
                max_num_results=max_results
            )

            # 実行時間を測定
            start_time = time.time()

            with st.spinner("🤖 AI検索中..."):
                # API呼び出し
                response = self.call_api_unified(
                    messages=[EasyInputMessageParam(role="user", content=query)],
                    tools=[fs_tool],
                    include=["file_search_call.results"]
                )

            execution_time = time.time() - start_time

            # 結果表示
            st.success(f"✅ AI検索完了 ({execution_time:.2f}秒)")

            # メイン回答の表示
            st.subheader("🤖 AI回答")
            ResponseProcessorUI.display_response(response, show_details=False)

            # FileSearch詳細結果の表示
            if hasattr(response, "file_search_call") and response.file_search_call:
                with st.expander("📄 FileSearch詳細結果", expanded=True):
                    if hasattr(response.file_search_call, "results") and response.file_search_call.results:
                        self._display_ai_search_results(response.file_search_call.results)
                    else:
                        st.info("ℹ️ 詳細な検索結果が返されませんでした")
            else:
                st.info("ℹ️ FileSearch呼び出し結果が見つかりませんでした")

            # パフォーマンス情報
            self._show_performance_info(response, execution_time, vector_store_id, max_results)

        except Exception as e:
            self.handle_error(e)
            logger.error(f"AI検索実行エラー: {e}")

    def _execute_direct_search(self, vector_store_id: str, query: str, max_results: int = 10,
                               rewrite_query: bool = False):
        """Vector Store APIを使用した直接検索の実行"""
        try:
            start_time = time.time()

            with st.spinner("🔍 直接検索中..."):
                # より明確なアクセス方法
                openai_client = self.client.client
                search_response = openai_client.vector_stores.search(
                    vector_store_id=vector_store_id,
                    query=query,
                    max_num_results=max_results,
                    rewrite_query=rewrite_query
                )

            execution_time = time.time() - start_time

            # 結果表示
            st.success(f"✅ 直接検索完了 ({execution_time:.2f}秒)")

            # 検索情報の表示
            st.subheader("🔍 検索情報")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**検索クエリ**: {getattr(search_response, 'search_query', query)}")
                st.write(f"**結果数**: {len(search_response.data)}件")
            with col2:
                st.write(f"**実行時間**: {execution_time:.2f}秒")
                st.write(f"**次ページ有無**: {'有り' if getattr(search_response, 'has_more', False) else '無し'}")

            # 直接検索結果の表示
            self._display_direct_search_results(search_response.data)

        except Exception as e:
            self.handle_error(e)
            logger.error(f"直接検索実行エラー: {e}")

    def _display_ai_search_results(self, results: List[Any]):
        """AI検索結果の表示"""
        try:
            if not results:
                st.info("🔍 検索結果がありません")
                return

            st.write(f"**検索結果件数**: {len(results)}件")

            for i, result in enumerate(results, 1):
                with st.expander(f"📄 結果 {i}", expanded=i <= 2):
                    # メインコンテンツの表示
                    if hasattr(result, 'content'):
                        content = result.content
                        st.write("**内容**:")
                        if len(content) > 500:
                            st.text_area(
                                "検索結果内容",
                                content,
                                height=150,
                                key=f"ai_content_{i}_{self.safe_key}",
                                help="検索でヒットした文書の内容"
                            )
                        else:
                            st.markdown(f"> {content}")

                    # メタデータ情報
                    col1, col2 = st.columns(2)
                    with col1:
                        if hasattr(result, 'file_name'):
                            st.write(f"**📄 ファイル名**: {result.file_name}")
                        if hasattr(result, 'file_id'):
                            st.write(f"**🆔 ファイルID**: {result.file_id}")
                    with col2:
                        if hasattr(result, 'score'):
                            st.write(f"**🎯 関連度**: {result.score:.4f}")

                    # デバッグ情報
                    if config.get("experimental.debug_mode", False):
                        with st.expander("🔧 Raw Data", expanded=False):
                            safe_streamlit_json(result)

        except Exception as e:
            st.error(f"❌ AI検索結果表示エラー: {e}")

    def _display_direct_search_results(self, results: List[Any]):
        """直接検索結果の表示"""
        try:
            if not results:
                st.info("🔍 検索結果がありません")
                return

            st.subheader("📋 検索結果")

            for i, result in enumerate(results, 1):
                # スコアによる色分け
                score = getattr(result, 'score', 0)
                if score >= 0.9:
                    score_color = "🟢"  # 高関連度
                elif score >= 0.7:
                    score_color = "🟡"  # 中関連度
                else:
                    score_color = "🔴"  # 低関連度

                with st.expander(f"{score_color} 結果 {i} (スコア: {score:.3f})", expanded=i <= 3):
                    # ファイル情報
                    col1, col2 = st.columns(2)
                    with col1:
                        if hasattr(result, 'filename'):
                            st.write(f"**📄 ファイル名**: {result.filename}")
                        if hasattr(result, 'file_id'):
                            st.write(f"**🆔 ファイルID**: {result.file_id}")
                    with col2:
                        st.write(f"**🎯 スコア**: {score:.4f}")

                    # コンテンツ表示
                    if hasattr(result, 'content') and result.content:
                        st.write("**📝 コンテンツ**:")
                        for content_item in result.content:
                            if hasattr(content_item, 'type') and content_item.type == "text":
                                text_content = getattr(content_item, 'text', '')
                                if len(text_content) > 500:
                                    st.text_area(
                                        "コンテンツ",
                                        text_content,
                                        height=150,
                                        key=f"direct_content_{i}_{self.safe_key}"
                                    )
                                else:
                                    st.markdown(f"> {text_content}")

                    # 属性情報
                    if hasattr(result, 'attributes') and result.attributes:
                        st.write("**🏷️ 属性**:")
                        for key, value in result.attributes.items():
                            st.write(f"- **{key}**: {value}")

                    # デバッグ情報
                    if config.get("experimental.debug_mode", False):
                        with st.expander("🔧 Raw Data", expanded=False):
                            safe_streamlit_json(result)

        except Exception as e:
            st.error(f"❌ 直接検索結果表示エラー: {e}")

    def _show_performance_info(self, response: Any, execution_time: float, vector_store_id: str, max_results: int):
        """パフォーマンス情報の表示"""
        with st.expander("📊 実行情報", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**実行詳細**")
                st.write(f"- 実行時間: {execution_time:.2f}秒")
                st.write(f"- Vector Store ID: `{vector_store_id}`")
                st.write(f"- 最大検索結果数: {max_results}")
                st.write(f"- 使用モデル: {self.get_model()}")

            with col2:
                if hasattr(response, 'usage') and response.usage:
                    st.write("**トークン使用量**")
                    usage_data = ResponseProcessor._serialize_usage(response.usage)

                    prompt_tokens = usage_data.get('prompt_tokens', 0)
                    completion_tokens = usage_data.get('completion_tokens', 0)
                    total_tokens = usage_data.get('total_tokens', 0)

                    st.write(f"- 入力: {prompt_tokens:,} tokens")
                    st.write(f"- 出力: {completion_tokens:,} tokens")
                    st.write(f"- 合計: {total_tokens:,} tokens")

                    # コスト計算
                    model = self.get_model()
                    cost = TokenManager.estimate_cost(prompt_tokens, completion_tokens, model)
                    st.write(f"- **推定コスト**: ${cost:.6f}")

    def show_debug_info(self):
        """デバッグ情報の表示（拡張版）"""
        super().show_debug_info()

        if config.get("experimental.debug_mode", False):
            with st.sidebar.expander("🔍 FileSearch Debug", expanded=False):
                st.write("**API情報**")
                st.write("- 使用API: Vector Stores API")
                st.write("- エンドポイント: /v1/vector_stores")

                st.write("**キャッシュ状態**")
                if self._vector_stores_cache:
                    st.write(f"- キャッシュされたVector Store数: {len(self._vector_stores_cache)}")
                    if self._cache_timestamp:
                        cache_age = time.time() - self._cache_timestamp
                        st.write(f"- キャッシュ経過時間: {cache_age:.1f}秒")
                else:
                    st.write("- キャッシュなし")

                if st.button("キャッシュ強制クリア", key="debug_clear_cache"):
                    self._clear_vector_stores_cache()

# ==================================================
# WebSearch Toolsデモ
# ==================================================
class WebSearchToolsDemo(BaseDemo):
    """WebSearch専用デモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        st.header("WebSearch Toolsデモ　API情報")
        with st.expander("利用：WebSearch Toolsデモ", expanded=False):
            st.code("""
            user_location = UserLocation(
                type="approximate",
                country="JP",
                city="Tokyo",
                region="Tokyo"
            )

            ws_tool = WebSearchToolParam(
                type="web_search_preview",
                user_location=user_location,
                search_context_size=context_size
            )
            
            default_query = config.get("samples.prompts.weather_query",
                                   "週末の東京の新宿の天気とおすすめの屋内アクティビティは？")
            query = st.text_input("検索クエリ", value=default_query)
            
            response = self.call_api_unified(
                    messages=[EasyInputMessageParam(role="user", content=query)],
                    tools=[ws_tool]
                )
                ┗# API呼び出しパラメータの準備
                api_params = {
                    "input": messages,
                    "model": model
                }
                self.client.create_response(**api_params)
                
            ResponseProcessorUI.display_response(response)
                
            """)

        st.write(
            "WebSearchツール専用デモ。WebSearchToolParamで地域設定・検索コンテキストサイズを指定し、responses.create()でWeb検索を実行。日本の東京地域設定で実用的な検索機能を実装。")

        default_query = config.get("samples.prompts.weather_query",
                                   "週末の東京の新宿の天気とおすすめの屋内アクティビティは？")
        query = st.text_input("検索クエリ", value=default_query)

        # Literal型の制約に対応
        context_size: Literal["low", "medium", "high"] = st.selectbox(
            "検索コンテキストサイズ",
            ["low", "medium", "high"],
            index=1,
            key=f"ws_context_{self.safe_key}"
        )

        if st.button("WebSearch実行", key=f"ws_exec_{self.safe_key}"):
            self._execute_web_search(query, context_size)

    def _execute_web_search(self, query: str, context_size: Literal["low", "medium", "high"]):
        """WebSearchの実行（統一化版）"""
        try:
            user_location = UserLocation(
                type="approximate",
                country="JP",
                city="Tokyo",
                region="Tokyo"
            )

            ws_tool = WebSearchToolParam(
                type="web_search_preview",
                user_location=user_location,
                search_context_size=context_size
            )

            with st.spinner("検索中..."):
                response = self.call_api_unified(
                    messages=[EasyInputMessageParam(role="user", content=query)],
                    tools=[ws_tool]
                )

            st.subheader("検索結果")
            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)


# ==================================================
# Computer Useデモ（統一化版）
# ==================================================
class ComputerUseDemo(BaseDemo):
    """Computer Use Tool のデモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        st.header("Computer Useデモ")
        st.write("利用：OpenAI API")
        st.warning("Computer Use APIは実験的な機能です。実行には特別な権限が必要です。")

        model = "computer-use-preview"
        st.write("使用モデル:", model)

        instruction = st.text_area(
            "実行指示",
            value="ブラウザで https://news.ycombinator.com を開いて、"
                  "トップ記事のタイトルをコピーしてメモ帳に貼り付けて",
            height=100
        )

        # Literal型の制約に対応
        environment: Literal["browser", "mac", "windows", "ubuntu", "linux"] = st.selectbox(
            "実行環境",
            ["browser", "mac", "windows", "ubuntu"],
            key=f"cu_env_{self.safe_key}"
        )

        if st.button("Computer Use実行", key=f"cu_exec_{self.safe_key}"):
            self._execute_computer_use(model, instruction, environment)

    def _execute_computer_use(self, model: str, instruction: str,
                              environment: Literal["windows", "mac", "linux", "ubuntu", "browser"]):
        """Computer Useの実行（統一化版）"""
        try:
            cu_tool = ComputerToolParam(
                type="computer_use_preview",
                display_width=1280,
                display_height=800,
                environment=environment,
            )

            messages = [
                EasyInputMessageParam(
                    role="user",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=instruction
                        )
                    ]
                )
            ]

            with st.spinner("実行中..."):
                response = self.call_api_unified(
                    messages=messages,
                    model=model,
                    tools=[cu_tool],
                    truncation="auto",
                    stream=False,
                    include=["computer_call_output.output.image_url"]
                )

            st.subheader("実行結果")
            ResponseProcessorUI.display_response(response)

            # Computer Use特有の出力処理
            for output in response.output:
                if hasattr(output, 'type') and output.type == 'computer_call':
                    st.subheader("Computer Use アクション")
                    if hasattr(output, 'action'):
                        st.write('実行アクション:', output.action)
                    if hasattr(output, 'image_url'):
                        st.image(output.image_url, caption="スクリーンショット")

        except Exception as e:
            self.handle_error(e)

# ==================================================
# デモマネージャー
# ==================================================
class DemoManager:
    """デモの管理クラス（統一化版）"""

    def __init__(self):
        self.config = ConfigManager("config.yml")
        self.demos = self._initialize_demos()

    def _initialize_demos(self) -> Dict[str, BaseDemo]:
        """デモインスタンスの初期化（統一化版）"""
        return {
            "Text Responses (One Shot)"  : TextResponseDemo("Text Responses(one shot)"),
            "Text Responses (Memory)"    : MemoryResponseDemo("Text Responses(memory)"),
            "Image to Text 画像入力(URL)"   : ImageResponseDemo("Image_URL", use_base64=False),
            "Image to Text 画像入力(base64)": ImageResponseDemo("Image_Base64", use_base64=True),
            "Structured Output 構造化出力" : StructuredOutputDemo("Structured_Output_create", use_parse=False),
            "Open Weather API" : WeatherDemo("OpenWeatherAPI"),
            "File Search-Tool vector store": FileSearchVectorStoreDemo("FileSearch_vsid"),
            "Tools - Web Search Tools"     : WebSearchToolsDemo("WebSearch"),
            "Computer Use Tool Param"      : ComputerUseDemo("Computer_Use"),
        }

    @error_handler_ui
    @timer_ui
    def run(self):
        """アプリケーションの実行（統一化版）"""
        # セッション状態の初期化（統一化）
        SessionStateManager.init_session_state()

        # デモ選択
        demo_name = st.sidebar.radio(
            "デモを選択",
            list(self.demos.keys()),
            key="demo_selection"
        )

        # セッション状態の更新
        if "current_demo" not in st.session_state:
            st.session_state.current_demo = demo_name
        elif st.session_state.current_demo != demo_name:
            st.session_state.current_demo = demo_name

        # 選択されたデモの実行
        demo = self.demos.get(demo_name)
        if demo:
            demo.run()
        else:
            st.error(f"デモ '{demo_name}' が見つかりません")

        # フッター情報（統一化）
        self._display_footer()

    def _display_footer(self):
        """フッター情報の表示（統一化版）"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 情報")

        # 現在の設定情報
        with st.sidebar.expander("現在の設定"):
            safe_streamlit_json({
                "default_model": config.get("models.default"),
                "api_timeout"  : config.get("api.timeout"),
                "ui_layout"    : config.get("ui.layout"),
            })

        # バージョン情報
        st.sidebar.markdown("### バージョン")
        st.sidebar.markdown("- OpenAI Responses API Demo v3.0 (統一化版)")
        st.sidebar.markdown("- Streamlit " + st.__version__)

        # リンク
        st.sidebar.markdown("### リンク")
        st.sidebar.markdown("[OpenAI API ドキュメント](https://platform.openai.com/docs)")
        st.sidebar.markdown("[Streamlit ドキュメント](https://docs.streamlit.io)")

        # 統計情報
        with st.sidebar.expander("📊 統計情報"):
            st.metric("利用可能デモ数", len(self.demos))
            st.metric("現在のデモ", st.session_state.get("current_demo", "未選択"))


# ==================================================
# メイン関数
# ==================================================
def main():
    """アプリケーションのエントリーポイント（統一化版）"""

    try:
        # ロギングの設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 環境変数のチェック
        if not os.getenv("OPENAI_API_KEY"):
            st.error("環境変数 OPENAI_API_KEY が設定されていません。")
            st.info("export OPENAI_API_KEY='your-api-key' を実行してください。")
            st.stop()

        # セッション状態の初期化（統一化）
        SessionStateManager.init_session_state()

        # デモマネージャーの作成と実行
        manager = DemoManager()
        manager.run()

    except Exception as e:
        st.error(f"アプリケーションの起動に失敗しました: {str(e)}")
        logger.error(f"Application startup error: {e}")

        # デバッグ情報の表示
        if config.get("experimental.debug_mode", False):
            with st.expander("🔧 詳細エラー情報", expanded=False):
                st.exception(e)


if __name__ == "__main__":
    main()

# streamlit run a10_00_responses_api.py --server.port=8510

