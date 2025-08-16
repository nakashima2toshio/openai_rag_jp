# a30_015_make_rag_data_legal.py
# 法律・判例QAデータのRAG前処理（helper_rag.py利用版）
# streamlit run a30_015_make_rag_data_legal.py --server.port=8505

import streamlit as st
import pandas as pd
import logging
import re
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
# 法律・判例QA特有の処理関数
# ==================================================
def validate_legal_data_specific(df) -> List[str]:
    """法律・判例QAデータ特有の検証"""
    legal_issues = []

    # 法律関連用語の存在確認
    legal_keywords = [
        '法律', '条文', '判例', '裁判', '最高裁', '地裁', '高裁', '民法', '刑法', '商法', '憲法',
        '契約', '損害賠償', '違法', '合法', '権利', '義務', '責任',
        'law', 'legal', 'court', 'judge', 'civil', 'criminal', 'contract', 'liability'
    ]

    # 大文字小文字を考慮した列名検索
    question_col = None
    for col in df.columns:
        if 'question' in col.lower():
            question_col = col
            break

    if question_col is not None:
        questions_with_legal_terms = 0
        for _, row in df.iterrows():
            question_text = str(row.get(question_col, '')).lower()
            if any(keyword in question_text for keyword in legal_keywords):
                questions_with_legal_terms += 1

        legal_ratio = (questions_with_legal_terms / len(df)) * 100
        legal_issues.append(f"法律関連用語を含む質問: {questions_with_legal_terms:,}件 ({legal_ratio:.1f}%)")

    # 回答の長さ分析（法律回答は通常詳細で長い）
    answer_col = None
    for col in df.columns:
        if 'answer' in col.lower():
            answer_col = col
            break

    if answer_col is not None:
        answer_lengths = df[answer_col].astype(str).str.len()
        avg_answer_length = answer_lengths.mean()
        if avg_answer_length < 100:
            legal_issues.append(f"⚠️ 平均回答長が短い可能性: {avg_answer_length:.0f}文字")
        else:
            legal_issues.append(f"✅ 適切な回答長: 平均{avg_answer_length:.0f}文字")

        # 詳細な回答長分析
        short_answers = (answer_lengths <= 100).sum()
        medium_answers = ((answer_lengths > 100) & (answer_lengths <= 500)).sum()
        long_answers = (answer_lengths > 500).sum()

        legal_issues.append(f"短い回答（≤100文字）: {short_answers:,}件")
        legal_issues.append(f"中程度の回答（101-500文字）: {medium_answers:,}件")
        legal_issues.append(f"長い回答（>500文字）: {long_answers:,}件")

    # 判例番号や条文参照の確認（詳細版）
    if answer_col is not None:
        reference_patterns = {
            '条文参照': r'第\d+条',
            '民法条文': r'民法第?\d+条',
            '刑法条文': r'刑法第?\d+条',
            '憲法条文': r'憲法第?\d+条',
            '判例'    : r'判例|最判|東京地判|大阪高判',
            '年月日'  : r'\d{4}年\d{1,2}月\d{1,2}日',
            '事件番号': r'(平成|令和)\d+年'
        }

        reference_analysis = {}
        for pattern_name, pattern in reference_patterns.items():
            try:
                count = df[answer_col].str.contains(pattern, regex=True, na=False).sum()
                if count > 0:
                    percentage = (count / len(df)) * 100
                    reference_analysis[pattern_name] = f"{count:,}件 ({percentage:.1f}%)"
            except Exception:
                reference_analysis[pattern_name] = "検索エラー"

        if reference_analysis:
            legal_issues.append("**法的根拠の参照分析:**")
            for ref_type, count_info in reference_analysis.items():
                legal_issues.append(f"  - {ref_type}: {count_info}")

    return legal_issues


# ==================================================
# メイン処理関数
# ==================================================
def main():
    """メイン処理関数"""

    # データセットタイプの設定
    DATASET_TYPE = "legal_qa"

    # ページ設定（共通関数利用）
    setup_page_config(DATASET_TYPE)

    # ヘッダー（共通関数利用）
    setup_page_header(DATASET_TYPE)

    # =================================================
    # サイドバー: モデル選択機能（共通関数利用）
    # =================================================
    setup_sidebar_header(DATASET_TYPE)

    # モデル選択（共通関数利用）
    selected_model = select_model(key="legal_model_selection")

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

    # 法律データ特有の設定
    with st.sidebar.expander("⚖️ 法律データ設定", expanded=False):
        preserve_legal_terms = st.checkbox(
            "法律用語を保護",
            value=True,
            help="法律専門用語の過度な正規化を防ぐ"
        )
        preserve_references = st.checkbox(
            "法的根拠を保護",
            value=True,
            help="条文番号や判例番号などの法的根拠を保護"
        )
        normalize_case_names = st.checkbox(
            "判例名を正規化",
            value=False,
            help="判例名の表記ゆれを統一"
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
        "法律・判例QAデータのCSVファイルをアップロードしてください",
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
                    # 法律データ特有の検証
                    legal_issues = validate_legal_data_specific(df)
                    if legal_issues:
                        st.write("**法律・判例QAデータ特有の分析:**")
                        for issue in legal_issues:
                            if issue.startswith("**"):
                                st.write(issue)
                            elif issue.startswith("  - "):
                                st.caption(issue)
                            else:
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

                    # 法律データ特有の後処理分析
                    if 'Combined_Text' in df_processed.columns:
                        st.subheader("⚖️ 法律データ特有の分析")

                        col1, col2 = st.columns(2)

                        with col1:
                            # 結合テキストの法律用語分析
                            combined_texts = df_processed['Combined_Text']
                            legal_keywords = ['法律', '条文', '判例', '民法', '刑法', '契約', '責任']

                            keyword_counts = {}
                            for keyword in legal_keywords:
                                count = combined_texts.str.contains(keyword, case=False, na=False).sum()
                                keyword_counts[keyword] = count

                            if keyword_counts:
                                st.write("**法律用語の出現頻度:**")
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

                        # 法的根拠の詳細分析
                        answer_col = None
                        for col in df_processed.columns:
                            if 'answer' in col.lower():
                                answer_col = col
                                break

                        if answer_col is not None:
                            st.write("**法的根拠の参照分析:**")

                            # より詳細な法的参照パターンの分析
                            detailed_patterns = {
                                '条文参照'  : r'第\d+条',
                                '民法'      : r'民法',
                                '刑法'      : r'刑法',
                                '憲法'      : r'憲法',
                                '判例'      : r'判例',
                                '最高裁判例': r'最判',
                                '地裁判例'  : r'地判',
                                '高裁判例'  : r'高判'
                            }

                            reference_stats = {}
                            total_with_references = 0

                            for pattern_name, pattern in detailed_patterns.items():
                                try:
                                    count = df_processed[answer_col].str.contains(pattern, regex=True, na=False).sum()
                                    if count > 0:
                                        percentage = (count / len(df_processed)) * 100
                                        reference_stats[pattern_name] = (count, percentage)
                                        if pattern_name == '条文参照':  # 基本的な法的根拠として条文参照をカウント
                                            total_with_references = count
                                except Exception:
                                    reference_stats[pattern_name] = (0, 0)

                            if reference_stats:
                                col1, col2, col3 = st.columns(3)

                                # 主要統計の表示
                                with col1:
                                    total_refs = sum(count for count, _ in reference_stats.values())
                                    st.metric("法的参照総数", f"{total_refs:,}")

                                with col2:
                                    if total_with_references > 0:
                                        ref_ratio = (total_with_references / len(df_processed)) * 100
                                        st.metric("根拠含有率", f"{ref_ratio:.1f}%")
                                    else:
                                        st.metric("根拠含有率", "0%")

                                with col3:
                                    if reference_stats:
                                        avg_refs_per_answer = total_refs / len(df_processed)
                                        st.metric("平均参照数/回答", f"{avg_refs_per_answer:.1f}")
                                    else:
                                        st.metric("平均参照数/回答", "0")

                                # 詳細な参照タイプ別統計
                                st.write("**参照タイプ別統計:**")
                                for ref_type, (count, percentage) in reference_stats.items():
                                    if count > 0:
                                        st.write(f"- {ref_type}: {count:,}件 ({percentage:.1f}%)")

                        # 回答長の詳細分析
                        if answer_col is not None:
                            st.write("**回答長の詳細分析:**")
                            answer_lengths = df_processed[answer_col].astype(str).str.len()

                            # 回答長のカテゴリ分析
                            very_short = (answer_lengths <= 50).sum()
                            short = ((answer_lengths > 50) & (answer_lengths <= 100)).sum()
                            medium = ((answer_lengths > 100) & (answer_lengths <= 300)).sum()
                            long = ((answer_lengths > 300) & (answer_lengths <= 500)).sum()
                            very_long = (answer_lengths > 500).sum()

                            col1, col2, col3, col4, col5 = st.columns(5)
                            with col1:
                                st.metric("極短", f"{very_short}")
                                st.caption("≤50文字")
                            with col2:
                                st.metric("短", f"{short}")
                                st.caption("51-100文字")
                            with col3:
                                st.metric("中", f"{medium}")
                                st.caption("101-300文字")
                            with col4:
                                st.metric("長", f"{long}")
                                st.caption("301-500文字")
                            with col5:
                                st.metric("極長", f"{very_long}")
                                st.caption(">500文字")

                    logger.info(f"法律・判例QAデータ処理完了: {len(df):,} → {len(df_processed):,}行")

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
                        help="前処理済みの法律・判例QAデータをCSV形式でダウンロード",
                        use_container_width=True
                    )

                with col2:
                    if text_data:
                        st.download_button(
                            label="📝 テキスト形式でダウンロード",
                            data=text_data,
                            file_name=f"legal_qa.txt",
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
                    "契約違反があった場合の損害賠償はどうなりますか？",
                    "民法第415条について教えてください",
                    "刑事事件と民事事件の違いは何ですか？"
                ],
                "answer"  : [
                    "契約違反による損害賠償は民法第415条に基づき、債務不履行により生じた損害の賠償を求めることができます...",
                    "民法第415条は債務不履行による損害賠償について定めた条文で、債務者がその債務の本旨に従った履行をしないとき...",
                    "刑事事件は国家が犯罪者を処罰する手続きで、民事事件は私人間の権利義務関係を解決する手続きです..."
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
# streamlit run a30_015_make_rag_data_legal.py --server.port=8505
