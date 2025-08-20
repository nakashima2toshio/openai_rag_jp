#!/usr/bin/env python3
"""
Qdrant Customer Support FAQ 登録スクリプト
datasets/customer_support_faq.csv を Qdrant に登録する
"""

import os
import pandas as pd
import logging
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http import models
import openai

from helper_api import ConfigManager, setup_logger


class QdrantCustomerUploader:
    """Customer Support FAQをQdrantに登録するクラス"""
    
    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        self.config = ConfigManager()
        self.logger = setup_logger("qdrant_customer", "INFO")
        
        # Qdrantクライアント初期化
        self.qdrant_client = QdrantClient(url=qdrant_url)
        
        # OpenAIクライアント初期化
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY環境変数が設定されていません")
        
        self.openai_client = openai.OpenAI()
        self.collection_name = "customer_support_faq"
        self.vector_size = 1536  # text-embedding-ada-002の次元数
        
    def create_collection(self) -> bool:
        """Qdrantコレクションを作成"""
        try:
            # 既存コレクションがあれば削除
            collections = self.qdrant_client.get_collections().collections
            if any(col.name == self.collection_name for col in collections):
                self.logger.info(f"既存コレクション '{self.collection_name}' を削除中...")
                self.qdrant_client.delete_collection(self.collection_name)
            
            # 新しいコレクション作成
            self.logger.info(f"コレクション '{self.collection_name}' を作成中...")
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            self.logger.info("コレクション作成完了")
            return True
            
        except Exception as e:
            self.logger.error(f"コレクション作成エラー: {e}")
            return False
    
    def get_embedding(self, text: str) -> List[float]:
        """OpenAI APIでテキストの埋め込みベクトルを取得"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text.replace("\n", " ")
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"埋め込み生成エラー: {e}")
            raise
    
    def load_csv_data(self, csv_path: str) -> pd.DataFrame:
        """CSVファイルを読み込み"""
        try:
            df = pd.read_csv(csv_path)
            self.logger.info(f"CSVファイル読み込み完了: {len(df)}件")
            return df
        except Exception as e:
            self.logger.error(f"CSVファイル読み込みエラー: {e}")
            raise
    
    def upload_data(self, csv_path: str) -> bool:
        """CSVデータをQdrantにアップロード"""
        try:
            # CSVデータ読み込み
            df = self.load_csv_data(csv_path)
            
            points = []
            total_rows = len(df)
            
            for idx, row in df.iterrows():
                question = str(row['question'])
                answer = str(row['answer'])
                
                # 質問と回答を結合してテキスト作成
                combined_text = f"質問: {question}\n回答: {answer}"
                
                # 埋め込みベクトル生成
                self.logger.info(f"処理中: {idx + 1}/{total_rows}")
                embedding = self.get_embedding(combined_text)
                
                # ポイント作成
                point = PointStruct(
                    id=idx,
                    vector=embedding,
                    payload={
                        "question": question,
                        "answer": answer,
                        "combined_text": combined_text,
                        "index": idx,
                        "created_at": datetime.now().isoformat()
                    }
                )
                points.append(point)
            
            # バッチでアップロード
            self.logger.info("Qdrantにデータをアップロード中...")
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            self.logger.info(f"アップロード完了: {len(points)}件")
            return True
            
        except Exception as e:
            self.logger.error(f"データアップロードエラー: {e}")
            return False
    
    def search_test(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """検索テスト"""
        try:
            # クエリの埋め込み生成
            query_embedding = self.get_embedding(query)
            
            # 検索実行
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit
            )
            
            results = []
            for result in search_results:
                results.append({
                    "score": result.score,
                    "question": result.payload["question"],
                    "answer": result.payload["answer"],
                    "index": result.payload["index"]
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"検索エラー: {e}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """コレクション情報を取得"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "status": collection_info.status
            }
        except Exception as e:
            self.logger.error(f"コレクション情報取得エラー: {e}")
            return {}


def main():
    """メイン処理"""
    logger = setup_logger("main", "INFO")
    
    try:
        # CSVファイルパス
        csv_path = "datasets/customer_support_faq.csv"
        
        if not Path(csv_path).exists():
            logger.error(f"CSVファイルが見つかりません: {csv_path}")
            return
        
        # QdrantUploaderインスタンス作成
        uploader = QdrantCustomerUploader()
        
        # コレクション作成
        if not uploader.create_collection():
            logger.error("コレクション作成に失敗しました")
            return
        
        # データアップロード
        if not uploader.upload_data(csv_path):
            logger.error("データアップロードに失敗しました")
            return
        
        # コレクション情報表示
        info = uploader.get_collection_info()
        logger.info(f"コレクション情報: {info}")
        
        # 検索テスト
        logger.info("検索テストを実行...")
        test_queries = [
            "アカウントを作成したい",
            "注文をキャンセルしたい", 
            "配送期間について"
        ]
        
        for query in test_queries:
            logger.info(f"\n検索クエリ: {query}")
            results = uploader.search_test(query)
            for i, result in enumerate(results, 1):
                logger.info(f"  {i}. スコア: {result['score']:.3f}")
                logger.info(f"     質問: {result['question']}")
                logger.info(f"     回答: {result['answer'][:100]}...")
        
        logger.info("\n=== 処理完了 ===")
        logger.info(f"Qdrant管理画面: http://localhost:6333/dashboard")
        
    except Exception as e:
        logger.error(f"メイン処理エラー: {e}")


if __name__ == "__main__":
    main()