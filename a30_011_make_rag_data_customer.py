# a30_011_make_rag_data_customer.py
# カスタマーサポートFAQデータのRAG前処理（helper_rag.py利用版）
# streamlit run a30_011_make_rag_data_customer.py --server.port=8501

import streamlit as st
import pandas as pd
import logging
from typing import List
from pathlib import Path

# 共通機能のインポート
from helper_rag import (
    AppConfig, RAGConfig, TokenManager, safe_execute,
    select_model, show_model_info, estimate_token_usage,
    validate_data, load_dataset, process_rag_data,
    create_download_data, display_statistics, save_files_to_output,
    show_usage_instructions, setup_page_config, setup_page_header, setup_sidebar_header
)

# ===================================================================
# helper_rag.py を利用した改修版
# ===================================================================

# 基本ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================================================
# カスタマーサポートFAQ特有の処理関数
# ==================================================
def validate_customer_support_data_specific(df) -> List[str]:
    """カスタマーサポートFAQデータ特有の検証"""
    support_issues = []

    # サポート関連用語の存在確認
    support_keywords = [
        '問題', '解決', 'トラブル', 'エラー', 'サポート', 'ヘルプ', '対応',
        'problem', 'issue', 'error', 'help', 'support', 'solution', 'troubleshoot'
    ]

    if 'question' in df.columns:
        questions_with_support_terms = 0
        for _, row in df.iterrows():
            question_text = str(row.get('question', '')).lower()
            if any(keyword in question_text for keyword in support_keywords):
                questions_with_support_terms += 1

        support_ratio = (questions_with_support_terms / len(df)) * 100
        support_issues.append(f"サポート関連用語を含む質問: {questions_with_support_terms:,}件 ({support_ratio:.1f}%)")

    # 回答の長さ分析
    if 'answer' in df.columns:
        answer_lengths = df['answer'].astype(str).str.len()
        avg_answer_length = answer_lengths.mean()
        if avg_answer_length < 50:
            support_issues.append(f"⚠️ 平均回答長が短い可能性: {avg_answer_length:.0f}文字")
        else:
            support_issues.append(f"✅ 適切な回答長: 平均{avg_answer_length:.0f}文字")

    # 質問の種類分析（簡易版）
    if 'question' in df.columns:
        question_starters = ['どうすれば', 'なぜ', 'いつ', 'どこで', 'どのように',
                             'what', 'how', 'why', 'when', 'where']
        question_type_count = 0
        for _, row in df.iterrows():
            question_text = str(row.get('question', '')).lower()
            if any(starter in question_text for starter in question_starters):
                question_type_count += 1

        question_type_ratio = (question_type_count / len(df)) * 100
        support_issues.append(f"疑問形質問: {question_type_count:,}件 ({question_type_ratio:.1f}%)")

    return support_issues


# ==================================================
# メイン処理関数
# ==================================================
def main():
    """メイン処理関数"""

    # データセットタイプの設定
    DATASET_TYPE = "customer_support_faq"

    # ページ設定（共通関数利用）
    setup_page_config(DATASET_TYPE)

    # ヘッダー（共通関数利用）
    setup_page_header(DATASET_TYPE)

    # =================================================
    # サイドバー: モデル選択機能（共通関数利用）
    # =================================================
    setup_sidebar_header(DATASET_TYPE)

    # モデル選択（共通関数利用）
    selected_model = select_model(key="customer_model_selection")

    # 選択されたモデル情報を表示（共通関数利用）
    show_model_info(selected_model)

    st.sidebar.markdown("---")

    # 前処理設定
    st.sidebar.header("⚙️ 前処理設定")
    combine_columns_option = st.sidebar.checkbox(
        "複数列を結合する（Vector Store用）",
        value=True,
        help="複数列を結合してRAG用テキストを作成"
    )
    show_validation = st.sidebar.checkbox(
        "データ検証を表示",
        value=True,
        help="データの品質検証結果を表示"
    )

    # カスタマーサポートデータ特有の設定
    with st.sidebar.expander("💬 サポートデータ設定", expanded=False):
        preserve_formatting = st.checkbox(
            "書式を保護",
            value=True,
            help="回答内の重要な書式を保護"
        )
        normalize_questions = st.checkbox(
            "質問を正規化",
            value=True,
            help="質問文の表記ゆれを統一"
        )

    # =================================================
    # メインエリア: ファイル処理
    # =================================================

    # 現在の選択モデル情報表示
    with st.expander("📊 選択中のモデル情報", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"🤖 選択モデル: **{selected_model}**")
        with col2:
            limits = AppConfig.get_model_limits(selected_model)
            st.info(f"📏 最大トークン: **{limits['max_tokens']:,}**")

    # ファイルアップロード
    st.subheader("📁 データファイルのアップロード")
    uploaded_file = st.file_uploader(
        "カスタマーサポートFAQデータのCSVファイルをアップロードしてください",
        type=['csv'],
        help="question, answer の2列を含むCSVファイル"
    )

    if uploaded_file is not None:
        try:
            # ファイル情報の確認
            st.info(f"📁 ファイル: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")

            # セッション状態でファイル処理状況を管理
            file_key = f"file_{uploaded_file.name}_{uploaded_file.size}"

            # ファイルが変更された場合は再読み込み（共通関数利用）
            if st.session_state.get('current_file_key') != file_key:
                with st.spinner("📖 ファイルを読み込み中..."):
                    df, validation_results = load_dataset(uploaded_file, DATASET_TYPE)

                # セッション状態に保存
                st.session_state['current_file_key'] = file_key
                st.session_state['original_df'] = df
                st.session_state['validation_results'] = validation_results
                st.session_state['original_rows'] = len(df)
                st.session_state['file_processed'] = False

                logger.info(f"新しいファイルを読み込み: {len(df):,}行")
            else:
                # セッション状態から取得
                df = st.session_state['original_df']
                validation_results = st.session_state['validation_results']
                logger.info(f"セッション状態からファイルを取得: {len(df):,}行")

            st.success(f"✅ ファイルが正常に読み込まれました。行数: **{len(df):,}**")

            # 元データの表示
            st.subheader("📋 元データプレビュー")
            st.dataframe(df.head(10), use_container_width=True)

            # データ検証結果の表示
            if show_validation:
                st.subheader("🔍 データ検証")

                # 基本検証結果（共通関数の結果）
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**基本統計:**")
                    for issue in validation_results:
                        st.info(issue)

                with col2:
                    # カスタマーサポートデータ特有の検証
                    support_issues = validate_customer_support_data_specific(df)
                    if support_issues:
                        st.write("**サポートデータ特有の分析:**")
                        for issue in support_issues:
                            st.info(issue)

            # 前処理実行
            st.subheader("⚙️ 前処理実行")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write("前処理を実行すると、データのクレンジング・正規化・結合が行われます。")
            with col2:
                process_button = st.button("🚀 前処理を実行", type="primary", key="process_button",
                                           use_container_width=True)

            if process_button:
                try:
                    with st.spinner("⚙️ 前処理中..."):
                        # RAGデータの前処理（共通関数利用）
                        df_processed = process_rag_data(
                            df.copy(),
                            DATASET_TYPE,
                            combine_columns_option
                        )

                    st.success("✅ 前処理が完了しました！")

                    # セッション状態に処理済みデータを保存
                    st.session_state['processed_df'] = df_processed
                    st.session_state['file_processed'] = True

                    # 前処理後のデータ表示
                    st.subheader("✅ 前処理後のデータプレビュー")
                    st.dataframe(df_processed.head(10), use_container_width=True)

                    # 統計情報の表示（共通関数利用）
                    display_statistics(df, df_processed, DATASET_TYPE)

                    # 選択されたモデルでのトークン使用量推定（共通関数利用）
                    estimate_token_usage(df_processed, selected_model)

                    # カスタマーサポートデータ特有の後処理分析
                    if 'Combined_Text' in df_processed.columns:
                        st.subheader("💬 カスタマーサポートデータ特有の分析")

                        col1, col2 = st.columns(2)

                        with col1:
                            # 結合テキストのサポート用語分析
                            combined_texts = df_processed['Combined_Text']
                            support_keywords = ['問題', 'エラー', 'トラブル', 'サポート', 'ヘルプ']

                            keyword_counts = {}
                            for keyword in support_keywords:
                                count = combined_texts.str.contains(keyword, case=False, na=False).sum()
                                keyword_counts[keyword] = count

                            if keyword_counts:
                                st.write("**サポート関連用語の出現頻度:**")
                                for keyword, count in keyword_counts.items():
                                    percentage = (count / len(df_processed)) * 100
                                    st.write(f"- {keyword}: {count:,}件 ({percentage:.1f}%)")

                        with col2:
                            # 質問の長さ分布
                            if 'question' in df_processed.columns:
                                question_lengths = df_processed['question'].str.len()
                                st.write("**質問の長さ統計:**")
                                st.metric("平均質問長", f"{question_lengths.mean():.0f}文字")
                                st.metric("最長質問", f"{question_lengths.max():,}文字")
                                st.metric("最短質問", f"{question_lengths.min():,}文字")

                    logger.info(f"カスタマーサポートFAQデータ処理完了: {len(df):,} → {len(df_processed):,}行")

                except Exception as process_error:
                    st.error(f"❌ 前処理エラー: {str(process_error)}")
                    logger.error(f"前処理エラー: {process_error}")
                    with st.expander("🔧 詳細エラー情報", expanded=False):
                        st.code(str(process_error))

            # 処理済みデータがある場合のみダウンロード・保存セクションを表示
            if st.session_state.get('file_processed', False) and 'processed_df' in st.session_state:
                df_processed = st.session_state['processed_df']

                # ダウンロード・保存セクション
                st.subheader("💾 ダウンロード・保存")

                # ダウンロード用データの作成（キャッシュ）（共通関数利用）
                if 'download_data' not in st.session_state or st.session_state.get('download_data_key') != file_key:
                    with st.spinner("📦 ダウンロード用データを準備中..."):
                        csv_data, text_data = create_download_data(
                            df_processed,
                            combine_columns_option,
                            DATASET_TYPE
                        )
                        st.session_state['download_data'] = (csv_data, text_data)
                        st.session_state['download_data_key'] = file_key
                else:
                    csv_data, text_data = st.session_state['download_data']

                # ブラウザダウンロード
                st.write("**📥 ブラウザダウンロード**")
                col1, col2 = st.columns(2)

                with col1:
                    st.download_button(
                        label="📊 CSV形式でダウンロード",
                        data=csv_data,
                        file_name=f"preprocessed_{DATASET_TYPE}_{len(df_processed)}rows.csv",
                        mime="text/csv",
                        help="前処理済みのカスタマーサポートFAQデータをCSV形式でダウンロード",
                        use_container_width=True
                    )

                with col2:
                    if text_data:
                        st.download_button(
                            label="📝 テキスト形式でダウンロード",
                            data=text_data,
                            file_name=f"customer_support_faq.txt",
                            mime="text/plain",
                            help="Vector Store/RAG用に最適化された結合テキスト",
                            use_container_width=True
                        )
                    else:
                        st.info("結合テキストが利用できません")

                # ローカル保存（共通関数利用）
                st.write("**💾 ローカルファイル保存（OUTPUTフォルダ）**")

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write("処理済みデータを OUTPUTフォルダに保存します。")
                with col2:
                    save_button = st.button("🔄 OUTPUTフォルダに保存", type="secondary", key="save_button",
                                            use_container_width=True)

                if save_button:
                    try:
                        with st.spinner("💾 ファイル保存中..."):
                            saved_files = save_files_to_output(
                                df_processed,
                                DATASET_TYPE,
                                csv_data,
                                text_data
                            )

                        if saved_files:
                            st.success("✅ ファイル保存完了！")

                            # 保存されたファイル一覧を表示
                            with st.expander("📂 保存されたファイル一覧", expanded=True):
                                for file_type, file_path in saved_files.items():
                                    if Path(file_path).exists():
                                        file_size = Path(file_path).stat().st_size
                                        st.success(f"**{file_type.upper()}**: `{file_path}` ({file_size:,} bytes)")
                                    else:
                                        st.error(f"**{file_type.upper()}**: `{file_path}` ❌ ファイルが見つかりません")

                                # OUTPUTフォルダの場所を表示
                                output_path = Path("OUTPUT").resolve()
                                st.info(f"**保存場所**: `{output_path}`")
                                try:
                                    file_count = len(list(output_path.glob("*")))
                                    st.info(f"**フォルダ内ファイル数**: {file_count:,}個")
                                except:
                                    st.info("フォルダ情報取得中...")
                        else:
                            st.error("❌ ファイル保存に失敗しました")

                    except Exception as save_error:
                        st.error(f"❌ ファイル保存エラー: {str(save_error)}")
                        logger.error(f"保存エラー: {save_error}")

        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")
            logger.error(f"ファイル読み込みエラー: {e}")

            with st.expander("🔧 詳細エラー情報", expanded=False):
                st.code(str(e))

                # ファイル情報の詳細確認
                if uploaded_file is not None:
                    st.write("**ファイル診断:**")
                    st.write(f"- ファイル名: {uploaded_file.name}")
                    st.write(f"- ファイルサイズ: {uploaded_file.size:,} bytes")
                    st.write(f"- ファイルタイプ: {uploaded_file.type}")

    else:
        st.info("👆 CSVファイルをアップロードしてください")

        # サンプルファイルの説明
        with st.expander("📄 必要なファイル形式", expanded=False):
            st.write("**CSVファイルの要件:**")
            st.write("- エンコーディング: UTF-8")
            st.write("- 必須列: question, answer")
            st.write("- ファイル形式: .csv")

            st.write("**サンプルデータ例:**")
            sample_data = {
                "question": [
                    "パスワードを忘れました",
                    "支払い方法を変更したい",
                    "サービスが利用できません"
                ],
                "answer"  : [
                    "パスワードリセットページからリセットできます",
                    "アカウント設定から支払い方法を変更してください",
                    "システムの状況を確認し、サポートにお問い合わせください"
                ]
            }
            sample_df = pd.DataFrame(sample_data)
            st.dataframe(sample_df, use_container_width=True)

    # 使用方法の説明（共通関数利用）
    show_usage_instructions(DATASET_TYPE)

    # セッション状態の表示（デバッグ用）
    if st.sidebar.checkbox("🔧 セッション状態を表示", value=False):
        with st.sidebar.expander("デバッグ情報", expanded=False):
            st.write(f"**選択モデル**: {selected_model}")
            st.write(f"**ファイル処理済み**: {st.session_state.get('file_processed', False)}")

            if 'original_df' in st.session_state:
                df = st.session_state['original_df']
                st.write(f"**元データ**: {len(df):,}行")

            if 'processed_df' in st.session_state:
                df_processed = st.session_state['processed_df']
                st.write(f"**処理済みデータ**: {len(df_processed):,}行")

            # OUTPUTフォルダの状態
            try:
                output_dir = Path("OUTPUT")
                if output_dir.exists():
                    file_count = len(list(output_dir.glob(f"*{DATASET_TYPE}*")))
                    st.write(f"**保存済みファイル**: {file_count:,}個")
                else:
                    st.write("**OUTPUTフォルダ**: 未作成")
            except Exception as e:
                st.write(f"**フォルダ状態**: エラー ({e})")


# ==================================================
# アプリケーション実行
# ==================================================
if __name__ == "__main__":
    main()

# 実行コマンド:
# streamlit run a30_011_make_rag_data_customer.py --server.port=8501
