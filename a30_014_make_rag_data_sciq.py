# a30_014_make_rag_data_sciq.py
# 科学・技術QAデータのRAG前処理（helper_rag.py利用版）
# streamlit run a30_014_make_rag_data_sciq.py --server.port=8504

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
# SciQ（科学・技術QA）特有の処理関数
# ==================================================
def validate_sciq_data_specific(df) -> List[str]:
    """SciQ（科学・技術QA）データ特有の検証"""
    sciq_issues = []

    # 科学・技術関連用語の存在確認
    science_keywords = [
        '化学', '物理', '生物', '数学', '地理', '天文', '医学', '工学',
        'chemistry', 'physics', 'biology', 'math', 'geography', 'astronomy',
        'medicine', 'engineering', 'science', 'theory', 'experiment', 'formula'
    ]

    # 大文字小文字を考慮した列名検索
    question_col = None
    for col in df.columns:
        if 'question' in col.lower():
            question_col = col
            break

    if question_col is not None:
        questions_with_science_terms = 0
        for _, row in df.iterrows():
            question_text = str(row.get(question_col, '')).lower()
            if any(keyword in question_text for keyword in science_keywords):
                questions_with_science_terms += 1

        science_ratio = (questions_with_science_terms / len(df)) * 100
        sciq_issues.append(f"科学・技術関連用語を含む質問: {questions_with_science_terms:,}件 ({science_ratio:.1f}%)")

    # 回答の種類分析（選択肢形式vs記述形式）
    answer_col = None
    for col in df.columns:
        if 'correct_answer' in col.lower() or 'answer' in col.lower():
            answer_col = col
            break

    if answer_col is not None:
        answer_lengths = df[answer_col].astype(str).str.len()
        avg_answer_length = answer_lengths.mean()

        # 短い回答（選択肢形式）と長い回答（記述形式）の判定
        short_answers = (answer_lengths <= 50).sum()
        long_answers = (answer_lengths > 50).sum()

        sciq_issues.append(f"短い回答（≤50文字）: {short_answers:,}件")
        sciq_issues.append(f"長い回答（>50文字）: {long_answers:,}件")
        sciq_issues.append(f"平均回答長: {avg_answer_length:.0f}文字")

    # 多肢選択問題の分析（distractorがある場合）
    distractor_columns = [col for col in df.columns if 'distractor' in col.lower()]
    if distractor_columns:
        sciq_issues.append(f"✅ 多肢選択形式: {len(distractor_columns)}個の選択肢列が存在")

        for col in distractor_columns:
            non_empty = df[col].dropna().count()
            sciq_issues.append(f"  - {col}: {non_empty:,}件のデータ")

    # 補足説明の分析（supportがある場合）
    support_col = None
    for col in df.columns:
        if 'support' in col.lower():
            support_col = col
            break

    if support_col is not None:
        support_count = df[support_col].dropna().count()
        support_ratio = (support_count / len(df)) * 100
        sciq_issues.append(f"補足説明付き質問: {support_count:,}件 ({support_ratio:.1f}%)")

        if support_count > 0:
            support_lengths = df[support_col].dropna().astype(str).str.len()
            avg_support_length = support_lengths.mean()
            sciq_issues.append(f"平均補足説明長: {avg_support_length:.0f}文字")

    return sciq_issues


# ==================================================
# メイン処理関数
# ==================================================
def main():
    """メイン処理関数"""

    # データセットタイプの設定
    DATASET_TYPE = "sciq_qa"

    # ページ設定（共通関数利用）
    setup_page_config(DATASET_TYPE)

    # ヘッダー（共通関数利用）
    setup_page_header(DATASET_TYPE)

    # =================================================
    # サイドバー: モデル選択機能（共通関数利用）
    # =================================================
    setup_sidebar_header(DATASET_TYPE)

    # モデル選択（共通関数利用）
    selected_model = select_model(key="sciq_model_selection")

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

    # SciQデータ特有の設定
    with st.sidebar.expander("🔬 SciQデータ設定", expanded=False):
        include_distractors = st.checkbox(
            "選択肢（distractor）を含める",
            value=False,
            help="不正解選択肢も結合テキストに含める"
        )
        include_support = st.checkbox(
            "補足説明（support）を含める",
            value=True,
            help="補足説明を結合テキストに含める"
        )
        preserve_scientific_notation = st.checkbox(
            "科学的記法を保護",
            value=True,
            help="数式や化学式の表記を保護"
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
        "SciQ（科学・技術QA）データのCSVファイルをアップロードしてください",
        type=['csv'],
        help="question, correct_answer の2列を含むCSVファイル（distractor, support列はオプション）"
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

            # カラム情報の表示
            st.subheader("📊 データ構造情報")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**検出されたカラム:**")
                for col in df.columns:
                    st.write(f"- {col}")
            with col2:
                st.write("**データ型:**")
                for col, dtype in df.dtypes.items():
                    st.write(f"- {col}: {dtype}")

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
                    # SciQデータ特有の検証
                    sciq_issues = validate_sciq_data_specific(df)
                    if sciq_issues:
                        st.write("**SciQ（科学・技術QA）データ特有の分析:**")
                        for issue in sciq_issues:
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

                    # SciQデータ特有の後処理分析
                    if 'Combined_Text' in df_processed.columns:
                        st.subheader("🔬 SciQデータ特有の分析")

                        col1, col2 = st.columns(2)

                        with col1:
                            # 結合テキストの科学用語分析
                            combined_texts = df_processed['Combined_Text']
                            science_keywords = ['化学', '物理', '生物', '数学', 'chemistry', 'physics', 'biology',
                                                'math']

                            keyword_counts = {}
                            for keyword in science_keywords:
                                count = combined_texts.str.contains(keyword, case=False, na=False).sum()
                                keyword_counts[keyword] = count

                            if keyword_counts:
                                st.write("**科学・技術用語の出現頻度:**")
                                for keyword, count in keyword_counts.items():
                                    percentage = (count / len(df_processed)) * 100
                                    st.write(f"- {keyword}: {count:,}件 ({percentage:.1f}%)")

                        with col2:
                            # 質問の複雑度分析
                            question_col = None
                            for col in df_processed.columns:
                                if 'question' in col.lower():
                                    question_col = col
                                    break

                            if question_col is not None:
                                question_lengths = df_processed[question_col].str.len()
                                st.write("**質問の複雑度統計:**")
                                st.metric("平均質問長", f"{question_lengths.mean():.0f}文字")
                                st.metric("最長質問", f"{question_lengths.max():,}文字")
                                st.metric("最短質問", f"{question_lengths.min():,}文字")

                        # 多肢選択問題の分析
                        distractor_columns = [col for col in df_processed.columns if 'distractor' in col.lower()]
                        if distractor_columns:
                            st.write("**多肢選択問題の分析:**")
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric("選択肢数", len(distractor_columns))
                            with col2:
                                # 最も多くの選択肢を持つ問題数
                                max_distractors = 0
                                for col in distractor_columns:
                                    non_empty = df_processed[col].dropna().count()
                                    max_distractors = max(max_distractors, non_empty)
                                st.metric("最大選択肢数", max_distractors)
                            with col3:
                                # 平均選択肢利用率
                                total_distractors = sum(
                                    df_processed[col].dropna().count() for col in distractor_columns)
                                avg_usage = (total_distractors / (len(df_processed) * len(distractor_columns))) * 100
                                st.metric("選択肢利用率", f"{avg_usage:.1f}%")

                        # 補足説明の分析
                        support_col = None
                        for col in df_processed.columns:
                            if 'support' in col.lower():
                                support_col = col
                                break

                        if support_col is not None:
                            st.write("**補足説明の分析:**")
                            support_data = df_processed[support_col].dropna()
                            if len(support_data) > 0:
                                support_lengths = support_data.astype(str).str.len()
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("平均説明長", f"{support_lengths.mean():.0f}文字")
                                with col2:
                                    st.metric("最大説明長", f"{support_lengths.max():,}文字")
                                with col3:
                                    support_ratio = (len(support_data) / len(df_processed)) * 100
                                    st.metric("説明含有率", f"{support_ratio:.1f}%")

                    logger.info(f"SciQ（科学・技術QA）データ処理完了: {len(df):,} → {len(df_processed):,}行")

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
                        help="前処理済みのSciQ（科学・技術QA）データをCSV形式でダウンロード",
                        use_container_width=True
                    )

                with col2:
                    if text_data:
                        st.download_button(
                            label="📝 テキスト形式でダウンロード",
                            data=text_data,
                            file_name=f"sciq_qa.txt",
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
            st.write("- 必須列: question, correct_answer")
            st.write("- オプション列: distractor1, distractor2, distractor3, support")
            st.write("- ファイル形式: .csv")

            st.write("**サンプルデータ例:**")
            sample_data = {
                "question"      : [
                    "What is the chemical symbol for water?",
                    "Which planet is closest to the sun?",
                    "What is the speed of light in vacuum?"
                ],
                "correct_answer": [
                    "H2O",
                    "Mercury",
                    "299,792,458 meters per second"
                ],
                "distractor1"   : [
                    "HO2",
                    "Venus",
                    "300,000,000 meters per second"
                ],
                "support"       : [
                    "Water is a chemical compound consisting of two hydrogen atoms and one oxygen atom.",
                    "Mercury is the smallest and innermost planet in the Solar System.",
                    "The speed of light in vacuum is a universal physical constant."
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
# streamlit run a30_014_make_rag_data_sciq.py --server.port=8504
