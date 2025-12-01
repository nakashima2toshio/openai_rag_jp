# a01_load_non_qa_rag_data.py - 使用方法ドキュメント

## 📚 概要

`a01_load_non_qa_rag_data.py`は、Q&Aペアを持たない非構造化データ（Wikipedia、ニュース記事、学術論文、コードなど）をRAG（Retrieval-Augmented Generation）システム用に前処理するStreamlitアプリケーションです。

### 主な特徴

- ✅ **7種類のデータセットタイプに対応**
- ✅ **HuggingFaceから直接ダウンロード**
- ✅ **データ品質チェック機能**
- ✅ **トークン使用量推定**
- ✅ **柔軟な前処理オプション**
- ✅ **複数フォーマットでの出力**（CSV/TXT/JSON）

---

## 🎯 対応データセット

### 1. 📚 Wikipedia日本語版

**特徴:**
- 百科事典的な正確な知識
- 構造化されたテキスト
- 幅広いトピックをカバー

**HuggingFace情報:**
```
データセット名: wikipedia
Config: 20220301.ja
Split: train
推奨サンプル数: 500-1000件
```

**主要フィールド:**
- `title`: 記事タイトル
- `text`: 記事本文

**注意点:**
- Wikiマークアップ（`[[リンク]]`、`==見出し==`）が含まれる
- マークアップ除去オプションを推奨

**使用例:**
- 一般知識データベース
- エンティティ情報検索
- 定義・概念説明

---

### 2. 📰 livedoorニュースコーパス

**特徴:**
- 日本語のニュース記事
- 9つのカテゴリ（トピックニュース、Sports Watch、ITライフハック、家電チャンネル、MOVIE ENTER、独女通信、エスマックス、livedoor HOMME、Peachy）
- 約7,400記事

**HuggingFace情報:**
```
データセット名: livedoor_news_corpus
Config: (なし)
Split: train
推奨サンプル数: 1000件
```

**主要フィールド:**
- `title`: ニュースタイトル
- `body`: 記事本文
- `category`: カテゴリ情報

**注意点:**
- URLが本文に含まれる場合あり
- カテゴリによって記事の特性が異なる

**使用例:**
- 最新ニュース検索
- トレンド分析
- 特定カテゴリの情報検索

---

### 3. 🌐 CC-News（英語ニュース）

**特徴:**
- Common Crawlから抽出された英語ニュース
- 2016年9月～2019年2月の記事
- 多様なトピックとソース

**HuggingFace情報:**
```
データセット名: cc_news
Config: (なし)
Split: train
推奨サンプル数: 1000件
```

**主要フィールド:**
- `title`: ニュースタイトル
- `text`: 記事本文
- `domain`: ニュースソースのドメイン
- `date`: 公開日

**注意点:**
- データサイズが大きい（76GB）
- 最初のN件のみ取得を推奨

**使用例:**
- 英語ニュース検索
- 国際情報データベース
- 時系列分析

---

### 4. 🏥 PubMed Abstracts（医学論文）

**特徴:**
- 医学・生物学分野の論文要旨
- 高度に専門的な内容
- 科学的に検証された情報

**HuggingFace情報:**
```
データセット名: scientific_papers
Config: pubmed
Split: train
推奨サンプル数: 500件
```

**主要フィールド:**
- `abstract`: 論文要旨
- `article`: 論文本文（一部データのみ）
- `section_names`: セクション名

**注意点:**
- 医学専門用語が多数
- 引用形式（[1], [2]）が含まれる
- 文字数が長い（平均1,000-2,000文字）

**使用例:**
- 医学知識データベース
- 症状・治療法検索
- 医学研究支援

---

### 5. 🔬 arXiv Dataset（学術論文）

**特徴:**
- 物理学、数学、コンピュータサイエンス等の学術論文
- プレプリントサーバーの論文
- 最新の研究動向

**HuggingFace情報:**
```
データセット名: scientific_papers
Config: arxiv
Split: train
推奨サンプル数: 500件
```

**主要フィールド:**
- `abstract`: 論文要旨
- `article`: 論文本文
- `section_names`: セクション名

**注意点:**
- LaTeX形式の数式が含まれる可能性
- 本文は非常に長い（10,000文字以上）
- 本文を含める場合は処理時間が増加

**使用例:**
- 学術研究データベース
- 最新研究トレンド分析
- 技術文献検索

---

### 6. 💻 GitHub Code（IT/AIコード）

**特徴:**
- GitHubの公開リポジトリからのコード
- ドキュメント文字列（docstring）付き
- 6つのプログラミング言語対応

**HuggingFace情報:**
```
データセット名: code_search_net
Config: python (または java, javascript, go, php, ruby)
Split: train
推奨サンプル数: 1000件
```

**主要フィールド:**
- `func_name`: 関数名
- `func_documentation_string`: ドキュメント文字列
- `code`: 関数コード
- `language`: プログラミング言語

**注意点:**
- コードとドキュメントの品質にばらつき
- 言語ごとに異なるデータセット
- コード部分は長くなる可能性

**使用例:**
- コード検索システム
- プログラミング学習支援
- API使用例検索

**対応言語:**
- Python
- Java
- JavaScript
- Go
- PHP
- Ruby

---

### 7. 💡 Stack Overflow（IT/AI Q&A）

**特徴:**
- 技術的な質問と回答
- コミュニティによる評価付き
- 実践的な問題解決

**HuggingFace情報:**
```
データセット名: pacovaldez/stackoverflow-questions
Config: (なし)
Split: train
推奨サンプル数: 1000件
```

**主要フィールド:**
- `title`: 質問タイトル
- `body`: 質問本文
- `tags`: タグ情報
- `score`: スコア（投票数）

**注意点:**
- 質問の品質にばらつき
- コードスニペットが含まれる
- タグでフィルタリング可能

**使用例:**
- 技術Q&Aシステム
- エラー解決支援
- プログラミング学習

**人気タグ例:**
- python, javascript, java
- react, node.js, django
- machine-learning, tensorflow

---

## 🚀 インストールと起動

### 前提条件

```bash
# Python 3.8以上
python --version

# 必要なパッケージ
pip install streamlit pandas datasets
```

### 起動方法

```bash
# アプリケーション起動
streamlit run a01_load_non_qa_rag_data.py --server.port=8502

# ブラウザで自動的に開く
# 手動の場合: http://localhost:8502
```

---

## 📖 基本的な使い方

### ステップ1: データセットタイプの選択

1. **サイドバー**を開く
2. **「データセットタイプ選択」**から以下を選択：
   - 📚 Wikipedia日本語版
   - 📰 livedoorニュースコーパス
   - 🌐 CC-News (英語ニュース)
   - 🏥 PubMed Abstracts (医学論文)
   - 🔬 arXiv (学術論文)
   - 💻 GitHub Code (IT/AI)
   - 💡 Stack Overflow (IT/AI Q&A)

3. 選択すると**推奨設定**が自動表示される

---

### ステップ2: データの取得

#### 方法A: CSVファイルをアップロード

1. **「データアップロード」タブ**を開く
2. **「ファイルを選択」**ボタンをクリック
3. CSVファイルを選択してアップロード

**必要なCSV形式:**
```csv
# Wikipedia/ニュースの場合
title,text
"記事タイトル","記事本文..."

# 論文の場合
abstract,article
"要旨...","本文..."

# コードの場合
func_name,func_documentation_string,code
"my_function","関数の説明","def my_function()..."
```

#### 方法B: HuggingFaceから自動ダウンロード（推奨）

1. **「または、HuggingFaceから自動ロード」**セクションに移動
2. 以下を設定：
   - **データセット名**: 推奨値が自動入力される
   - **Split名**: `train`（通常）
   - **サンプル数**: 100-1000件
   - **Config名**: データセットによって異なる

3. **「📥 HuggingFaceからロード」**ボタンをクリック
4. ダウンロード完了を待つ（数秒～数分）

**自動保存:**
- `datasets/`フォルダに自動保存
- メタデータも同時保存
- 次回から再利用可能

---

### ステップ3: データ検証

1. **「データ検証」タブ**を開く
2. 以下が自動表示される：

**📋 基本検証:**
- 総行数・総列数
- 空値の確認
- 重複行の検出

**🔍 データセット固有の検証:**
- Wikipedia: マークアップの有無
- ニュース: 記事長の分析
- 論文: 学術用語の検出
- コード: ドキュメントの有無
- Stack Overflow: タグの分布

3. **検証結果を確認**：
   - ✅ 緑色: 問題なし
   - 💡 青色: 情報
   - ⚠️ 黄色: 警告

---

### ステップ4: 前処理実行

1. **「前処理実行」タブ**を開く
2. **前処理設定**を調整：

**基本設定:**
- ☑️ **短いテキストを除外**:
  - 最小文字数: 100文字（調整可能）

- ☑️ **重複を除去**:
  - 完全一致の重複を削除

**データセット固有設定（サイドバー）:**

| データセット | 設定項目 | 説明 |
|------------|---------|------|
| Wikipedia | Wikiマークアップを除去 | `[[]]`や`==`を削除 |
| ニュース | URLを除去 | 本文中のURLを削除 |
| 論文 | 引用を保持 | `[1]`形式を保持 |
| 論文 | 本文を含める | 要旨+本文を結合 |
| コード | コードを含める | ドキュメント+コード |
| コード | プログラミング言語 | Python/Java/JS等 |
| Stack Overflow | タグを含める | タグ情報を追加 |
| Stack Overflow | 最小スコア | 低スコア除外 |

3. **「🚀 前処理を実行」**ボタンをクリック

4. **処理結果を確認**：
   - 処理件数
   - 除外された件数
   - テキスト長の統計
   - トークン使用量推定

---

### ステップ5: 結果のダウンロード・保存

1. **「結果・ダウンロード」タブ**を開く

2. **処理サマリー**を確認：
   - 処理件数
   - 除外件数
   - 残存率

3. **ファイルダウンロード**（3形式）：

   **📄 CSVファイル:**
   ```
   ファイル名: preprocessed_[dataset_type].csv
   内容: 全カラム + Combined_Text
   用途: データ分析、バックアップ
   ```

   **📝 テキストファイル:**
   ```
   ファイル名: [dataset_type].txt
   内容: Combined_Textのみ（1行1レコード）
   用途: RAG用ベクトル化
   ```

   **📋 メタデータ(JSON):**
   ```
   ファイル名: metadata_[dataset_type].json
   内容: 処理履歴、設定、統計情報
   用途: 処理の追跡、再現性
   ```

4. **OUTPUTフォルダに保存**：
   - **「💾 OUTPUTフォルダに保存」**ボタンをクリック
   - `OUTPUT/`ディレクトリに保存
   - 保存されたファイル一覧が表示

---

## 💡 データセット別の使用例

### 例1: Wikipedia日本語版で知識ベース構築

```python
# 設定
データセット: Wikipedia日本語版
HuggingFace: wikipedia / 20220301.ja
サンプル数: 1000件
オプション: Wikiマークアップを除去 ✓

# 用途
- 一般知識Q&Aシステム
- エンティティ情報検索
- 定義・概念説明
```

**処理の流れ:**
1. Wikipedia記事1000件をダウンロード
2. マークアップ（`[[]]`、`==`）を自動除去
3. タイトル+本文を自然な文章として結合
4. 短い記事（<100文字）を除外
5. RAG用テキストとして出力

**出力例:**
```
量子力学 量子力学とは、原子や分子などのミクロな世界での物理現象を記述する...
```

---

### 例2: livedoorニュースで日本語ニュース検索

```python
# 設定
データセット: livedoorニュースコーパス
HuggingFace: livedoor_news_corpus
サンプル数: 全件（約7,400件）
オプション: URLを除去 ✓

# 用途
- 最新トレンド検索
- カテゴリ別情報検索
- ニュース要約システム
```

**カテゴリ分析:**
- トピックニュース
- Sports Watch
- ITライフハック
- 家電チャンネル
- MOVIE ENTER
- 独女通信
- エスマックス
- livedoor HOMME
- Peachy

---

### 例3: PubMedで医学知識データベース

```python
# 設定
データセット: PubMed Abstracts
HuggingFace: scientific_papers / pubmed
サンプル数: 500件
オプション: 引用を保持 ✓

# 用途
- 医学文献検索
- 症状・治療法の調査
- 医学研究支援
```

**特徴:**
- 査読済みの信頼性の高い情報
- 医学専門用語が豊富
- 要旨から詳細情報を取得

---

### 例4: GitHub Codeでプログラミング支援

```python
# 設定
データセット: GitHub Code
HuggingFace: code_search_net / python
サンプル数: 1000件
オプション:
  - コードを含める ✓
  - プログラミング言語: Python

# 用途
- コード検索システム
- API使用例の提示
- プログラミング学習支援
```

**出力構造:**
```
関数名: calculate_total
説明: 合計を計算する関数です
コード: def calculate_total(items):
    return sum(items)
```

---

### 例5: Stack Overflowで技術Q&A

```python
# 設定
データセット: Stack Overflow
HuggingFace: pacovaldez/stackoverflow-questions
サンプル数: 1000件
オプション:
  - タグを含める ✓
  - 最小スコア: 5

# 用途
- 技術Q&Aシステム
- エラー解決支援
- ベストプラクティス検索
```

**人気タグでフィルタリング:**
- `python`, `javascript`, `java`
- `react`, `django`, `tensorflow`
- `machine-learning`, `deep-learning`

---

## 🔧 詳細設定ガイド

### トークン使用量の最適化

**推奨設定:**

| データセット | 推奨サンプル数 | 推奨最小文字数 | 理由 |
|------------|-------------|-------------|------|
| Wikipedia | 500-1000 | 200 | 記事長のばらつき大 |
| ニュース | 1000-2000 | 100 | 比較的均一 |
| PubMed | 300-500 | 500 | 長文、専門的 |
| arXiv | 300-500 | 500 | 非常に長文 |
| GitHub Code | 1000-1500 | 50 | 短いコードあり |
| Stack Overflow | 1000-1500 | 100 | 質問長に差 |

**コスト推定:**

```python
# 1000件、平均500文字の場合
推定トークン数: 約250,000トークン
Embedding費用: 約$0.025（text-embedding-3-small）
```

---

### データ品質向上のコツ

#### 1. 短いテキストの除外

**目的:** ノイズの削除、検索精度向上

**推奨設定:**
- Wikipedia: 200文字以上
- ニュース: 100文字以上
- 論文: 500文字以上
- コード: 50文字以上

#### 2. 重複の除去

**重要性:**
- ストレージの節約
- 検索結果の多様性向上
- トークン使用量の削減

**動作:**
- `Combined_Text`が完全一致する行を削除
- 最初の行を保持

#### 3. データセット固有の前処理

**Wikipedia:**
```
除去対象:
- [[リンク]]
- ==見出し==
- {{テンプレート}}
- <!-- コメント -->
```

**ニュース:**
```
除去対象:
- URL（http://, https://）
- メールアドレス
- 広告文言
```

**論文:**
```
保持対象:
- 引用番号 [1], [2]
- 数式（LaTeX形式）
- 専門用語
```

**コード:**
```
結合対象:
- 関数名
- ドキュメント文字列
- コード本体
```

---

## 📊 出力ファイルの詳細

### 1. CSVファイル（preprocessed_[type].csv）

**構造:**
```csv
title,text,Combined_Text,...
"タイトル","元のテキスト","結合後のテキスト",...
```

**用途:**
- データ分析
- 中間処理
- バックアップ

**特徴:**
- 元のカラムを全て保持
- `Combined_Text`カラムが追加
- UTF-8エンコーディング

---

### 2. テキストファイル（[type].txt）

**構造:**
```
結合後のテキスト1
結合後のテキスト2
結合後のテキスト3
...
```

**用途:**
- RAG用ベクトル化
- Embedding生成
- 軽量なデータ配布

**特徴:**
- `Combined_Text`のみ
- 1行1レコード
- インデックスなし

---

### 3. メタデータファイル（metadata_[type].json）

**構造:**
```json
{
  "dataset_type": "wikipedia_ja",
  "dataset_name": "Wikipedia日本語版",
  "processed_at": "2025-01-15T10:30:00",
  "row_count": 950,
  "original_count": 1000,
  "removed_count": 50,
  "config": {
    "remove_short_text": true,
    "min_length": 200,
    "remove_duplicates": true,
    "options": {
      "remove_markup": true
    }
  }
}
```

**用途:**
- 処理履歴の追跡
- 再現性の確保
- 設定の記録

---

## 🆚 Q&A版との違い

| 項目 | Q&A版（a01_load_set_rag_data.py） | 非Q&A版（本ファイル） |
|------|-----------------------------------|---------------------|
| **データ構造** | question + answer | title + text/body/abstract |
| **対応データセット** | FAQ、医療QA、科学QA、法律QA、雑学QA | Wikipedia、ニュース、論文、コード |
| **結合方法** | 質問と回答を明示的に結合 | タイトルと本文を自然に結合 |
| **主な用途** | 質問応答システム | 知識検索、文書検索 |
| **テキスト長** | 短め（100-500文字） | 長め（500-2000文字） |
| **構造化度** | 高い（Q&Aペア） | 低い（自由形式） |
| **前処理の重点** | 質問の正規化 | マークアップ・URL除去 |

### 使い分けの目安

**Q&A版を使うべき場合:**
- ユーザーが質問形式で問い合わせる
- 明確な答えが存在する
- FAQ、Q&Aデータがある

**非Q&A版を使うべき場合:**
- 幅広い知識ベースを構築
- 文書検索・情報検索
- 記事・論文・コードから学習

---

## 🔍 トラブルシューティング

### よくあるエラーと解決方法

#### 1. HuggingFaceからのダウンロードエラー

**エラー:**
```
データセットのロードに失敗しました: FileNotFoundError
```

**原因:**
- データセット名が間違っている
- Config名が必要だが指定されていない
- Split名が存在しない

**解決方法:**
```python
# 正しい形式を確認
# HuggingFaceのデータセットページで確認
https://huggingface.co/datasets/[dataset_name]

# 例: Wikipedia
データセット名: wikipedia
Config: 20220301.ja  # 必須
Split: train

# 例: livedoor
データセット名: livedoor_news_corpus
Config: (空欄)  # 不要
Split: train
```

---

#### 2. メモリ不足エラー

**エラー:**
```
MemoryError: Unable to allocate array
```

**原因:**
- サンプル数が多すぎる
- 長文データ（論文等）を大量に読み込み

**解決方法:**
```python
# サンプル数を減らす
推奨: 100-500件から開始

# 段階的に増やす
1回目: 100件
2回目: 500件
3回目: 1000件

# 本文を含めない（arXivの場合）
オプション: 本文を含める ☐
```

---

#### 3. 処理が遅い

**症状:**
- ダウンロードに10分以上かかる
- 前処理が終わらない

**原因:**
- データセットが大きい（CC-Newsなど）
- 本文を含めている（arXiv）

**解決方法:**
```python
# サンプル数を制限
CC-News: 100件まで
arXiv: 500件まで

# 本文を除外
arXiv: 要旨のみ使用

# ローカルにキャッシュ
datasets/フォルダから再利用
```

---

#### 4. 空のテキストが多い

**症状:**
```
処理後の行数が大幅に減少
除外件数: 800件 / 1000件
```

**原因:**
- 必須フィールドが空
- 最小文字数が厳しすぎる

**解決方法:**
```python
# 最小文字数を調整
推奨: 50-100文字

# データセットを確認
データ検証タブで空値をチェック

# 別のSplitを試す
Split: train → test, validation
```

---

#### 5. 文字化け

**症状:**
- 日本語が正しく表示されない
- 特殊文字が ? になる

**原因:**
- エンコーディングの問題
- データセット自体の問題

**解決方法:**
```python
# CSVファイルをUTF-8で保存
Excel: 名前を付けて保存 → UTF-8 CSV

# データセットを再ダウンロード
HuggingFaceから再取得

# 日本語対応データセットを使用
Wikipedia日本語版、livedoorニュース等
```

---

## ❓ よくある質問（FAQ）

### Q1: どのデータセットが一番おすすめですか？

**A:** 用途によります：

- **初めてRAGを試す**: livedoorニュース（日本語、サイズ適度）
- **一般知識**: Wikipedia日本語版
- **専門知識（医学）**: PubMed Abstracts
- **技術情報**: Stack Overflow
- **コード検索**: GitHub Code

---

### Q2: サンプル数はどれくらいが適切ですか？

**A:** 以下を参考にしてください：

```
テスト・学習: 100-500件
開発環境: 500-1000件
本番環境: 1000-5000件

※ トークン使用量とコストを要確認
```

---

### Q3: データの更新頻度はどうすればいいですか？

**A:** データの性質によります：

| データタイプ | 推奨更新頻度 | 理由 |
|------------|-----------|------|
| Wikipedia | 月1回 | 定期的に更新される |
| ニュース | 日次-週次 | 最新情報が重要 |
| 論文 | 月1回-四半期 | 新しい研究成果 |
| コード | 月1回 | 新しいAPI・パターン |
| Stack Overflow | 週次-月次 | 新しい質問・回答 |

---

### Q4: 複数のデータセットを混ぜて使えますか？

**A:** はい、可能です：

```bash
# 手順
1. 各データセットを個別に処理
2. TXTファイルを結合
3. メタデータを統合

# コマンド例
cat wikipedia_ja.txt livedoor_news.txt > combined.txt
```

**注意点:**
- データの性質が大きく異なる場合、検索精度が下がる可能性
- ドメイン別にコレクションを分ける方が推奨

---

### Q5: 商用利用は可能ですか？

**A:** データセットのライセンスによります：

| データセット | ライセンス | 商用利用 |
|------------|----------|---------|
| Wikipedia | CC BY-SA 3.0 | ✅ 可（帰属表示必要） |
| livedoor | 独自 | ⚠️ 要確認 |
| CC-News | 各ソース依存 | ⚠️ 要確認 |
| PubMed | Public Domain | ✅ 可 |
| arXiv | 各論文の権利 | ⚠️ 要確認 |
| GitHub Code | 各リポジトリ | ⚠️ 要確認 |
| Stack Overflow | CC BY-SA 4.0 | ✅ 可（帰属表示必要） |

**推奨:**
- HuggingFaceのデータセットページでライセンスを確認
- 商用利用前に必ず権利関係を確認

---

### Q6: エラーが出た場合はどうすればいいですか？

**A:** 以下の順序で確認：

1. **エラーメッセージを確認**
   - 何が問題かを特定

2. **トラブルシューティングを参照**
   - 本ドキュメントの該当セクション

3. **サンプル数を減らす**
   - 100件で試す

4. **別のデータセットを試す**
   - livedoorニュース（安定）

5. **ログを確認**
   - `logs/`ディレクトリ

---

### Q7: 処理済みデータはどこに保存されますか？

**A:** 以下の場所に保存されます：

```
プロジェクトルート/
├── OUTPUT/                # 処理済みファイル
│   ├── preprocessed_*.csv
│   ├── *.txt
│   └── metadata_*.json
│
└── datasets/              # ダウンロード元データ
    ├── *.csv
    └── *_metadata.json
```

---

### Q8: Vector Storeへの登録はどうすればいいですか？

**A:** 次のステップで実行：

**Cloud版（OpenAI Vector Store）:**
```bash
# ステップ1: 本アプリで前処理
streamlit run a01_load_non_qa_rag_data.py

# ステップ2: Vector Store作成
python a02_set_vector_store_vsid.py

# ステップ3: 検索
streamlit run a03_rag_search_cloud_vs.py
```

**Local版（Qdrant）:**
```bash
# ステップ1: 本アプリで前処理
streamlit run a01_load_non_qa_rag_data.py

# ステップ2: Qdrant起動
docker-compose up -d

# ステップ3: データ登録
python a30_qdrant_registration.py

# ステップ4: 検索
streamlit run a50_rag_search_local_qdrant.py
```

---

## 🎓 ベストプラクティス

### 1. 段階的なアプローチ

```
フェーズ1: 小規模テスト（100件）
- データの品質確認
- 前処理オプションの調整
- トークン使用量の確認

フェーズ2: 中規模開発（500-1000件）
- RAGシステムの構築
- 検索精度の評価
- パラメータのチューニング

フェーズ3: 本番展開（1000件以上）
- 本番データで運用
- 定期的な更新
- パフォーマンス監視
```

---

### 2. データ品質の維持

**定期的なチェック:**
```python
# 月次タスク
□ データセットの更新確認
□ 新しい記事・論文の追加
□ 古いデータの削除

# 処理前
□ データ検証の実行
□ 空値・重複のチェック
□ テキスト長の分析

# 処理後
□ サンプルの目視確認
□ トークン使用量の確認
□ メタデータの保存
```

---

### 3. コスト管理

**OpenAI Embedding費用の目安:**

```python
# text-embedding-3-small の場合
1,000件 × 500文字 = 約250,000トークン
費用: $0.025

10,000件 × 500文字 = 約2,500,000トークン
費用: $0.25

# 推奨
- 最初は小規模で試す
- トークン推定機能を活用
- 定期的にコストを確認
```

---

### 4. バージョン管理

**メタデータの活用:**
```json
{
  "dataset_type": "wikipedia_ja",
  "version": "v1.0",
  "processed_at": "2025-01-15",
  "source": {
    "dataset": "wikipedia",
    "config": "20220301.ja",
    "sample_size": 1000
  },
  "preprocessing": {
    "remove_markup": true,
    "min_length": 200
  }
}
```

---

## 📚 参考リンク

### HuggingFace データセット

- [Wikipedia](https://huggingface.co/datasets/wikipedia)
- [livedoor News Corpus](https://huggingface.co/datasets/livedoor_news_corpus)
- [CC-News](https://huggingface.co/datasets/cc_news)
- [Scientific Papers](https://huggingface.co/datasets/scientific_papers)
- [CodeSearchNet](https://huggingface.co/datasets/code_search_net)
- [Stack Overflow Questions](https://huggingface.co/datasets/pacovaldez/stackoverflow-questions)

### OpenAI ドキュメント

- [Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [Vector Stores](https://platform.openai.com/docs/assistants/tools/file-search)
- [Pricing](https://openai.com/pricing)

### プロジェクト関連

- [README.md](../README.md) - プロジェクト全体のドキュメント
- [README_2.md](../README_2.md) - Q&A版の使用例
- [a02_set_vector_store_vsid.md](./a02_set_vector_store_vsid.md) - Vector Store作成
- [a30_qdrant_registration.md](./a30_qdrant_registration.md) - Qdrant登録

---

## 🆘 サポート

### 問題が発生した場合

1. **本ドキュメントを確認**
   - トラブルシューティングセクション
   - よくある質問（FAQ）

2. **ログを確認**
   ```bash
   # ターミナルのログ
   # Streamlitアプリのエラー表示
   ```

3. **設定をリセット**
   ```bash
   # サイドバーの設定を初期値に戻す
   # 別のデータセットで試す
   ```

4. **小規模で再試行**
   ```bash
   # サンプル数: 100件
   # 最小文字数: 50文字
   ```

---

## 📝 更新履歴

| バージョン | 日付 | 変更内容 |
|----------|------|---------|
| 1.0.0 | 2025-01-15 | 初版リリース |

---

**開発環境**: Python 3.8+ | Streamlit | HuggingFace Datasets | OpenAI API

**ライセンス**: プロジェクトのライセンスに従う

**作成者**: openai_rag_jp プロジェクトチーム
