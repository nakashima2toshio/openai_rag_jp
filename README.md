概要：
・プログラムとドキュメントの対応表：


| プログラム名                          | 概要                                           | OUTPUT                                      |
| ------------------------------------- | ---------------------------------------------- | ------------------------------------------- |
| a30_00_dl_dataset_from_huggingface.py | テストデータを<br/>HuggingFaceからダウンロード | customer_support_faq.csv<br />trivia_qa.csv |
| a30_011_make_rag_data_customer.py     | ① カスタマーサポート・FAQ加工                 | customer_support_faq.csv                    |
| a30_013_make_rag_data_medical.py      | ③ 医療質問回答データ加工                      | medical_qa.csv                              |
| a30_014_make_rag_data_sciq.py         | ④ 科学・技術QAデータ加工                      | sciq_qa.csv                                 |
| a30_015_make_rag_data_legal.py        | ⑤ 法律・判例QAデータ加工                      | legal_qa.csv                                |
| a30_020_make_vsid.py                  | OpenAI vector storeに登録                      | vs_id                                       |
| a30_30_rag_search.py                  | RAGサーチ                                      |                                             |
| helper_api.py                         | ヘルパー関数：OpenAI API                       |                                             |
| helper_st.py                          | Streamlit ヘルパー関数                         |                                             |
| helper_rag.py                         | OpenAI API　RAG処理ヘルパー                    |                                             |

（1）開発の準備
・requirements.txt から必要なソフトをインストールする。

（2）HuggingFaceからテスト用データとして、以下をダウンロードする。
customer_support_faq.csv    ① カスタマーサポート・FAQデータセット
trivia_qa.csv               ② 一般知識・トリビアQAデータセット
medical_qa.csv              ③ 医療質問回答データセット
sciq_qa.csv                 ④ 科学・技術QAデータセット
legal_qa.csv                ⑤ 法律・判例QAデータセット
[a30_00_dl_dataset_from_huggingface.py]

（3）それぞれのダウンロードしたCSVファイルをRAG用のデータとして加工し、TXTファイルを作成する。
[a30_011_make_rag_data_customer.py]
[a30_013_make_rag_data_medical.py]
[a30_014_make_rag_data_sciq.py]
[a30_015_make_rag_data_legal.py]

（4）RAG用のデータとして加工ずみのTXTファイルをOpenAIのvector storeに登録する。
[a30_020_make_vsid.py]

（5）vector store に登録されたデータを利用して、検索を実施する。
[a30_30_rag_search.py]

（6）ヘルパー関数
[helper_api.py]
[helper_rag.py]
[helper_st.py]
