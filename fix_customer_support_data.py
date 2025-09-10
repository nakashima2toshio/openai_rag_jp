#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Customer Support FAQデータ修正スクリプト
CSVファイルからテキストファイルを正しく生成する
"""

import pandas as pd
from pathlib import Path

def fix_customer_support_data():
    """Customer Support FAQデータを修正"""
    
    # CSVファイルを読み込み
    csv_path = Path("datasets/customer_support_faq.csv")
    output_dir = Path("OUTPUT")
    output_dir.mkdir(exist_ok=True)
    
    print(f"📂 CSVファイル読み込み: {csv_path}")
    df = pd.read_csv(csv_path)
    
    print(f"📊 データ件数: {len(df)}件")
    print(f"📋 カラム: {list(df.columns)}")
    
    # questionとanswerをCombined_Textカラムに結合
    if 'question' in df.columns and 'answer' in df.columns:
        df['Combined_Text'] = df['question'] + ' ' + df['answer']
        print(f"✅ Combined_Textカラムを作成しました")
    else:
        print(f"❌ 必要なカラムが見つかりません: {list(df.columns)}")
        return False
    
    # CSVファイルとして保存
    csv_output_path = output_dir / "preprocessed_customer_support_faq.csv"
    df.to_csv(csv_output_path, index=False)
    print(f"💾 CSV保存: {csv_output_path}")
    
    # テキストファイルとして保存（Combined_Textカラムの内容のみ）
    txt_output_path = output_dir / "customer_support_faq.txt"
    with open(txt_output_path, 'w', encoding='utf-8') as f:
        for text in df['Combined_Text']:
            f.write(text + '\n')
    
    print(f"💾 TXT保存: {txt_output_path}")
    print(f"📝 テキストファイル行数: {len(df)}行")
    
    # 最初の3件をサンプル表示
    print("\n📌 サンプルデータ（最初の3件）:")
    for i, text in enumerate(df['Combined_Text'].head(3), 1):
        print(f"[{i}] {text[:100]}...")
    
    return True

if __name__ == "__main__":
    success = fix_customer_support_data()
    if success:
        print("\n✅ データ修正が完了しました！")
        print("次のステップ:")
        print("1. streamlit run a02_set_vector_store_vsid.py --server.port=8502")
        print("   でVector Storeを再作成してください")
        print("2. streamlit run a20_rag_search_cloud_vs.py --server.port=8501")
        print("   でRAG検索をテストしてください")
    else:
        print("\n❌ データ修正に失敗しました")