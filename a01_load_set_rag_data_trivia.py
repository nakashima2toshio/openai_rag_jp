#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
a01_load_set_rag_data_trivia.py - TriviaQAデータセット専用処理ツール
====================================================================
起動: python a01_load_set_rag_data_trivia.py

【主要機能】
✅ HuggingFaceからTriviaQAデータセットを自動ダウンロード
✅ データの検証と前処理
✅ RAG用にテキストを結合
✅ datasets/trivia_qa.csv に保存

【TriviaQAデータセットについて】
- 一般的な雑学知識に関する質問応答データセット
- 質問、回答、エビデンス（根拠となる文章）を含む
- WikipediaやWebページからのソース情報付き
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, Optional
from datasets import load_dataset

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TriviaQAProcessor:
    """TriviaQAデータセット処理クラス"""
    
    def __init__(self):
        self.dataset_name = "trivia_qa"
        self.output_dir = Path("datasets")
        self.output_dir.mkdir(exist_ok=True)
        self.output_file = self.output_dir / "trivia_qa.csv"
        
    def download_dataset(self, subset: str = "rc", split: str = "train", sample_size: int = 1000) -> pd.DataFrame:
        """
        HuggingFaceからTriviaQAデータセットをダウンロード
        
        Args:
            subset: データセットのサブセット ("rc" or "unfiltered")
                - rc: Reading Comprehension (コンテキスト付き)
                - unfiltered: フィルタリングなしの完全版
            split: データ分割 ("train", "validation", "test")
            sample_size: 取得するサンプル数
            
        Returns:
            pd.DataFrame: ダウンロードしたデータ
        """
        try:
            logger.info(f"TriviaQAデータセットをダウンロード中... (subset={subset}, split={split})")
            
            # データセットをロード
            dataset = load_dataset("trivia_qa", subset, split=split)
            
            # サンプル数を制限
            if len(dataset) > sample_size:
                dataset = dataset.select(range(sample_size))
            
            # DataFrameに変換
            data_list = []
            for item in dataset:
                # TriviaQAの構造に基づいてデータを抽出
                record = {
                    'question_id': item.get('question_id', ''),
                    'question': item.get('question', ''),
                    'answer': self._extract_answer(item.get('answer', {})),
                    'entity_pages': self._extract_entity_pages(item.get('entity_pages', [])),
                    'search_results': self._extract_search_results(item.get('search_results', [])),
                }
                data_list.append(record)
            
            df = pd.DataFrame(data_list)
            
            logger.info(f"✅ {len(df)}件のデータを取得しました")
            logger.info(f"カラム: {df.columns.tolist()}")
            
            return df
            
        except Exception as e:
            logger.error(f"データセットのダウンロードに失敗しました: {e}")
            raise
    
    def _extract_answer(self, answer_dict: Dict) -> str:
        """回答情報を抽出"""
        if isinstance(answer_dict, dict):
            # 正規化された回答を優先的に使用
            normalized_value = answer_dict.get('normalized_value', '')
            if normalized_value:
                return normalized_value
            
            # aliasesがある場合は最初の値を使用
            aliases = answer_dict.get('aliases', [])
            if aliases:
                return aliases[0]
            
            # valueがある場合はそれを使用
            value = answer_dict.get('value', '')
            if value:
                return value
        
        return str(answer_dict) if answer_dict else ''
    
    def _extract_entity_pages(self, entity_pages) -> str:
        """エンティティページ情報を抽出（Wikipediaなど）"""
        if not entity_pages:
            return ''
        
        # entity_pagesが辞書の場合の処理
        if isinstance(entity_pages, dict):
            titles = []
            # 辞書のキーをイテレート（最初の3つまで）
            for i, (key, page) in enumerate(entity_pages.items()):
                if i >= 3:
                    break
                if isinstance(page, dict):
                    title = page.get('title', '')
                    if title:
                        titles.append(title)
                elif isinstance(page, str):
                    titles.append(page)
            return ' | '.join(titles)
        
        # entity_pagesがリストの場合の処理
        elif isinstance(entity_pages, list):
            titles = []
            for i, page in enumerate(entity_pages):
                if i >= 3:  # 最初の3つまで
                    break
                if isinstance(page, dict):
                    title = page.get('title', '')
                    if title:
                        titles.append(title)
                elif isinstance(page, str):
                    titles.append(page)
            return ' | '.join(titles)
        
        return ''
    
    def _extract_search_results(self, search_results) -> str:
        """検索結果（コンテキスト）を抽出"""
        if not search_results:
            return ''
        
        contexts = []
        
        # search_resultsが辞書の場合の処理
        if isinstance(search_results, dict):
            # 辞書のキーをイテレート（最初の2つまで）
            for i, (key, result) in enumerate(search_results.items()):
                if i >= 2:
                    break
                if isinstance(result, dict):
                    # search_contextまたはdescriptionを探す
                    search_context = result.get('search_context', result.get('description', ''))
                    if search_context:
                        # 長すぎる場合は切り詰める
                        if len(search_context) > 500:
                            search_context = search_context[:500] + '...'
                        contexts.append(search_context)
                elif isinstance(result, str):
                    # 直接文字列の場合
                    if len(result) > 500:
                        result = result[:500] + '...'
                    contexts.append(result)
        
        # search_resultsがリストの場合の処理
        elif isinstance(search_results, list):
            for i, result in enumerate(search_results):
                if i >= 2:  # 最初の2つまで
                    break
                if isinstance(result, dict):
                    # search_contextまたはdescriptionを探す
                    search_context = result.get('search_context', result.get('description', ''))
                    if search_context:
                        # 長すぎる場合は切り詰める
                        if len(search_context) > 500:
                            search_context = search_context[:500] + '...'
                        contexts.append(search_context)
                elif isinstance(result, str):
                    # 直接文字列の場合
                    if len(result) > 500:
                        result = result[:500] + '...'
                    contexts.append(result)
        
        return ' '.join(contexts)
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """データの検証"""
        logger.info("データ検証を実行中...")
        
        is_valid = True
        
        # 必須カラムのチェック
        required_columns = ['question', 'answer']
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"❌ 必須カラム '{col}' が見つかりません")
                is_valid = False
        
        # データの存在チェック
        if len(df) == 0:
            logger.error("❌ データが空です")
            is_valid = False
        
        # 質問と回答の有効性チェック
        if 'question' in df.columns:
            null_questions = df['question'].isnull().sum()
            empty_questions = (df['question'] == '').sum()
            if null_questions > 0 or empty_questions > 0:
                logger.warning(f"⚠️ 空の質問が{null_questions + empty_questions}件あります")
        
        if 'answer' in df.columns:
            null_answers = df['answer'].isnull().sum()
            empty_answers = (df['answer'] == '').sum()
            if null_answers > 0 or empty_answers > 0:
                logger.warning(f"⚠️ 空の回答が{null_answers + empty_answers}件あります")
        
        if is_valid:
            logger.info("✅ データ検証に合格しました")
        
        return is_valid
    
    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """RAG用にデータを前処理"""
        logger.info("データの前処理を実行中...")
        
        # NaN値を空文字列に置換
        df = df.fillna('')
        
        # RAG用にテキストを結合
        combined_texts = []
        for _, row in df.iterrows():
            parts = []
            
            # 質問を追加
            if row['question']:
                parts.append(f"Question: {row['question']}")
            
            # 回答を追加
            if row['answer']:
                parts.append(f"Answer: {row['answer']}")
            
            # エンティティページ情報を追加（あれば）
            if 'entity_pages' in row and row['entity_pages']:
                parts.append(f"Related Pages: {row['entity_pages']}")
            
            # 検索結果（コンテキスト）を追加（あれば）
            if 'search_results' in row and row['search_results']:
                parts.append(f"Context: {row['search_results']}")
            
            combined_text = '\n'.join(parts)
            combined_texts.append(combined_text)
        
        df['combined_text'] = combined_texts
        
        logger.info(f"✅ {len(df)}件のデータを前処理しました")
        
        return df
    
    def save_data(self, df: pd.DataFrame) -> tuple:
        """データをCSV、テキスト、メタデータファイルとして保存
        
        Returns:
            tuple: (csv_path, txt_path, metadata_path)
        """
        try:
            # OUTPUTディレクトリを作成
            output_dir = Path("OUTPUT")
            output_dir.mkdir(exist_ok=True)
            
            # タイムスタンプを生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 1. CSVファイルとして保存（datasetsフォルダ）
            df.to_csv(self.output_file, index=False, encoding='utf-8')
            logger.info(f"✅ CSVファイル保存完了: {self.output_file}")
            
            # 2. テキストファイルとして保存（OUTPUTフォルダ）
            txt_filename = f"trivia_qa_{timestamp}.txt"
            txt_path = output_dir / txt_filename
            
            # combined_textカラムの内容をテキストファイルに保存
            if 'combined_text' in df.columns:
                with open(txt_path, 'w', encoding='utf-8') as f:
                    for idx, text in enumerate(df['combined_text'].dropna(), 1):
                        f.write(f"=== Document {idx} ===\n")
                        f.write(text)
                        f.write("\n\n")
                logger.info(f"✅ テキストファイル保存完了: {txt_path}")
            else:
                logger.warning("⚠️ combined_textカラムが存在しないため、テキストファイルは作成されませんでした")
                txt_path = None
            
            # 3. 処理済みCSVファイル（OUTPUTフォルダ）
            processed_csv_filename = f"preprocessed_trivia_qa_{timestamp}.csv"
            processed_csv_path = output_dir / processed_csv_filename
            df.to_csv(processed_csv_path, index=False, encoding='utf-8')
            logger.info(f"✅ 処理済みCSVファイル保存完了: {processed_csv_path}")
            
            # 4. メタデータファイル（OUTPUTフォルダ）
            metadata_filename = f"metadata_trivia_qa_{timestamp}.json"
            metadata_path = output_dir / metadata_filename
            
            metadata = {
                'dataset_name': 'trivia_qa',
                'dataset_type': 'trivia_qa',
                'created_at': datetime.now().isoformat(),
                'processed_at': datetime.now().isoformat(),
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist(),
                'file_paths': {
                    'original_csv': str(self.output_file),
                    'processed_csv': str(processed_csv_path),
                    'text_file': str(txt_path) if txt_path else None
                },
                'statistics': {
                    'total_records': int(len(df)),
                    'non_empty_questions': int(df['question'].notna().sum()) if 'question' in df.columns else 0,
                    'non_empty_answers': int(df['answer'].notna().sum()) if 'answer' in df.columns else 0,
                    'avg_question_length': float(df['question'].str.len().mean()) if 'question' in df.columns else 0.0,
                    'avg_answer_length': float(df['answer'].str.len().mean()) if 'answer' in df.columns else 0.0,
                    'avg_combined_text_length': float(df['combined_text'].str.len().mean()) if 'combined_text' in df.columns else 0.0
                }
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ メタデータファイル保存完了: {metadata_path}")
            
            return str(self.output_file), str(txt_path) if txt_path else None, str(metadata_path)
            
        except Exception as e:
            logger.error(f"データの保存に失敗しました: {e}")
            raise
    
    def display_statistics(self, df: pd.DataFrame):
        """データ統計を表示"""
        logger.info("\n" + "="*50)
        logger.info("📊 データ統計")
        logger.info("="*50)
        logger.info(f"総レコード数: {len(df)}")
        logger.info(f"カラム数: {len(df.columns)}")
        logger.info(f"カラム名: {', '.join(df.columns)}")
        
        if 'question' in df.columns:
            avg_question_length = df['question'].str.len().mean()
            logger.info(f"質問の平均文字数: {avg_question_length:.1f}")
        
        if 'answer' in df.columns:
            avg_answer_length = df['answer'].str.len().mean()
            logger.info(f"回答の平均文字数: {avg_answer_length:.1f}")
        
        if 'combined_text' in df.columns:
            avg_combined_length = df['combined_text'].str.len().mean()
            logger.info(f"結合テキストの平均文字数: {avg_combined_length:.1f}")
        
        logger.info("="*50)
    
    def display_samples(self, df: pd.DataFrame, n: int = 3):
        """データサンプルを表示"""
        logger.info("\n" + "="*50)
        logger.info(f"📝 データサンプル（最初の{n}件）")
        logger.info("="*50)
        
        for i in range(min(n, len(df))):
            logger.info(f"\n--- サンプル {i+1} ---")
            if 'question' in df.columns:
                logger.info(f"質問: {df.iloc[i]['question'][:200]}...")
            if 'answer' in df.columns:
                logger.info(f"回答: {df.iloc[i]['answer'][:100]}...")
            if 'entity_pages' in df.columns and df.iloc[i]['entity_pages']:
                logger.info(f"関連ページ: {df.iloc[i]['entity_pages'][:100]}...")
            if 'combined_text' in df.columns:
                logger.info(f"結合テキスト（先頭）: {df.iloc[i]['combined_text'][:200]}...")

def main():
    """メイン処理"""
    processor = TriviaQAProcessor()
    
    try:
        # パラメータ設定
        SUBSET = "rc"  # "rc" (Reading Comprehension) or "unfiltered"
        SPLIT = "train"  # "train", "validation", or "test"  
        SAMPLE_SIZE = 1000  # 取得するサンプル数
        
        logger.info("="*50)
        logger.info("TriviaQAデータセット処理を開始します")
        logger.info(f"設定: subset={SUBSET}, split={SPLIT}, sample_size={SAMPLE_SIZE}")
        logger.info("="*50)
        
        # 1. データセットをダウンロード
        logger.info("\n📥 Step 1: データセットのダウンロード")
        df = processor.download_dataset(subset=SUBSET, split=SPLIT, sample_size=SAMPLE_SIZE)
        
        # 2. データ検証
        logger.info("\n🔍 Step 2: データ検証")
        is_valid = processor.validate_data(df)
        if not is_valid:
            logger.warning("データ検証で問題が見つかりましたが、処理を続行します")
        
        # 3. データ前処理
        logger.info("\n⚙️ Step 3: データ前処理")
        df = processor.preprocess_data(df)
        
        # 4. データ保存
        logger.info("\n💾 Step 4: データ保存")
        csv_path, txt_path, metadata_path = processor.save_data(df)
        
        # 5. 統計表示
        processor.display_statistics(df)
        
        # 6. サンプル表示
        processor.display_samples(df)
        
        logger.info("\n" + "="*50)
        logger.info("✅ 処理が完了しました！")
        logger.info("\n📂 出力ファイル:")
        logger.info(f"  - CSVファイル: {csv_path}")
        if txt_path:
            logger.info(f"  - テキストファイル: {txt_path}")
        logger.info(f"  - メタデータ: {metadata_path}")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"❌ エラーが発生しました: {e}")
        raise

if __name__ == "__main__":
    main()