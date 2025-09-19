## a01_load_set_rag_data データフロー（PPT原稿）

本資料は、a01_load_set_rag_data.py の入出力と処理フローに焦点を当てた、パワーポイント用の原稿です。発表スライド作成時に、この原稿の見出し・箇条書き・表をそのまま転用できます。

---

## Slide 1｜目的と概要
- 目的：複数ドメインのCSV/HuggingFaceデータを統一前処理し、RAG用に最適化したCSV/TXT/JSONを生成
- 実行：`streamlit run a01_load_set_rag_data.py --server.port=8501`
- 主な対象データセット：
  - customer_support_faq（FAQ）／medical_qa（医療）／sciq_qa（科学）／legal_qa（法律）／trivia_qa（雑学）
- 主要機能：データ読込、検証、テキスト結合、トークン推定、エクスポート、OUTPUT保存

---

## Slide 2｜入力場所・入力ファイル（Where/What）
- 入力経路は2種類：CSVアップロード または HuggingFace自動ダウンロード
- 保存先とファイル命名（HuggingFaceから取得時）：
  - 保存ディレクトリ：`datasets/`
  - CSV：`<dataset>_<split>_<samples>_<timestamp>.csv`
  - メタデータ：`<dataset>_<split>_<samples>_<timestamp>_metadata.json`

| 入力経路 | 入力場所 | 入力ファイル/形式 | 保存先 | 備考 |
|---|---|---|---|---|
| CSVアップロード | ローカル（ブラウザ経由） | CSV（UTF-8） | セッション内（明示保存なし） | 必須列はデータセット種別に依存 |
| HuggingFace | ネットワーク | HFデータセット | `datasets/` | CSV化＋メタデータJSONを自動保存 |

---

## Slide 3｜データセット別の必須列（What）
- UIの「必須列」は RAGConfig に準拠

| データセット | 必須列（UI表示） | 補足 |
|---|---|---|
| customer_support_faq | `question`, `answer` | FAQ形式のQ/A |
| medical_qa | `Question`, `Complex_CoT`, `Response` | Complex_CoTがないデータでも読み込みは可能だが、UI上は必須表示 |
| sciq_qa | `question`, `correct_answer` | `distractor1..3`, `support`があれば活用 |
| legal_qa | `question`, `answer` | 法的参照語の混入有無を検証で確認 |
| trivia_qa | `question`, `answer` | `entity_pages`, `search_results`を抽出・要約して活用 |

---

## Slide 4｜処理（How）
- 前処理の中核は `helper_rag.py`：`clean_text` / `process_rag_data` / `combine_columns`
- 代表的な処理手順：
  1) 重複・全NA行の除去、インデックス整理
  2) 必須列に対してクレンジング（改行・空白正規化、引用符正規化など）
  3) 列結合で `Combined_Text` を生成（データセット特性に応じた並び・項目）
  4) 空の `Combined_Text` 行を除去
  5) オプションでユーザー選択カラム＋セパレータで上書き結合（スペース/改行/タブ/カスタム）
  6) トークン使用量の概算（サンプルから推定）

| ステップ | 内容 | 関連関数/箇所 |
|---|---|---|
| 1 | 重複/空行除去・リセット | `process_rag_data` |
| 2 | 列クレンジング | `clean_text`（必須列に対して適用） |
| 3 | 結合テキスト生成 | `combine_columns`（datasetごとテンプレート） |
| 4 | 空結合の除去 | `process_rag_data` 内処理 |
| 5 | セパレータ適用 | a01のUIで選択、`Combined_Text`再生成 |
| 6 | トークン推定 | `estimate_token_usage` |

---

## Slide 5｜セパレータと結合の挙動（How）
- デフォルト：`combine_columns` が各データセットの主要列をスペースで自然結合
- UI選択で再結合：対象カラムとセパレータ（スペース/改行/タブ/カスタム）を指定し `Combined_Text` を上書き
- 例：`question` + 改行 + `answer`、`Question | Complex_CoT | Response` など

---

## Slide 6｜検証（Quality）
- 共通検証：必須列の存在、空値件数、重複件数、基本統計を提示
- データセット固有検証：
  - FAQ：質問にサポート関連語が含まれるか、回答平均長など
  - 医療：医療語の混入、Complex_CoTの充足率、回答平均長
  - SciQ：科学語の混入、選択肢・support列の有無
  - 法律：質問の法的語、回答に条・法・規則・判例の参照有無、長さ分布

---

## Slide 7｜出力場所・出力ファイル（Where/What）
- ダウンロードボタン（ブラウザ）：CSV/TXT/メタデータを即時取得
- OUTPUT保存ボタン：所定の命名で `OUTPUT/` に保存

| 出力場所 | ファイル名 | 内容 | 生成条件 |
|---|---|---|---|
| ダウンロード | `preprocessed_<dataset_type>.csv` | 元列＋`Combined_Text` を含むCSV | ダウンロード操作 |
| ダウンロード | `<dataset_type>.txt` | `Combined_Text` のみ1行1レコード | `Combined_Text`がある場合 |
| ダウンロード | `metadata_<dataset_type>.json` | 処理設定・行数などのメタ情報 | ダウンロード操作 |
| OUTPUT/ | `preprocessed_<dataset_type>.csv` | 上記CSVと同等 | 「OUTPUTに保存」操作 |
| OUTPUT/ | `<dataset_type>.txt` | 上記TXTと同等 | `Combined_Text`がある場合 |
| OUTPUT/ | `metadata_<dataset_type>.json` | 保存時のメタ情報 | 常に |

---

## Slide 8｜データフロー（全体像）
- 入力（CSV/HTTP）→ 読込 → 検証 → 前処理（クリーニング＋結合）→ 推定 → エクスポート（DL/保存）
- HuggingFace入力は `datasets/` にバージョン付きで自動保存
- 最終成果物は `OUTPUT/` 配下に集約（CSV/TXT/JSON）

---

## Slide 9｜操作手順（UIガイド）
- 左ペイン：データセット選択、モデル選択、データセット固有オプション
- タブ1：CSVアップロード または HFロード（split, samples 指定）→ プレビュー
- タブ2：共通＋固有の検証結果を確認
- タブ3：結合カラムとセパレータを設定 → 「前処理を実行」
- タブ4：処理サマリー、CSV/TXT/JSONのダウンロード、`OUTPUT/` への保存

---

## Slide 10｜命名規則まとめ（Reference）
- HF保存（入力）
  - `datasets/<dataset>_<split>_<samples>_<timestamp>.csv`
  - `datasets/<dataset>_<split>_<samples>_<timestamp>_metadata.json`
- 出力（成果物）
  - `OUTPUT/preprocessed_<dataset_type>.csv`
  - `OUTPUT/<dataset_type>.txt`
  - `OUTPUT/metadata_<dataset_type>.json`

---

## Slide 11｜TODO（実装・運用の明確化）
- 入力・検証
  - [ ] medical_qaで`Complex_CoT`が欠損するケースのUIメッセージ明確化（必須/推奨の切替）
  - [ ] アップロードCSVも希望時に`datasets/`へ保存するオプションを追加
  - [ ] 列名マッピングUI（ユーザーが必須列に対応付けできる）
- 前処理
  - [ ] セパレータ再結合ロジックを`helper_rag`側に集約し一元化
  - [ ] 大規模データのチャンク処理（低メモリ動作）
- 出力/メタデータ
  - [ ] メタデータに各処理ステップのフラグとパラメータ（選択カラム/セパレータ等）を追加
  - [ ] `OUTPUT/`保存時のファイル名にタイムスタンプ付与（バージョン管理強化）
- 品質/テスト
  - [ ] `helper_rag`主要関数の`pytest`ユニットテスト追加（I/Oはモック）
  - [ ] 検証項目の閾値やキーワードを`config.yml`側で管理

---

## 付録｜発表メモ（話し方の目安）
- 「入力はCSVかHF、HFは`datasets/`に自動保存。次に検証で品質チェック、前処理でクリーニングと結合を行い`Combined_Text`を作成。最後にダウンロードまたは`OUTPUT/`に保存します。ファイル名と保存先は表の通りで、運用時は命名規則に沿って追跡しやすくしています。」
- 「データセット固有検証と結合テンプレートにより、FAQ/医療/SciQ/法律/Triviaと幅広いデータに一貫したパイプラインを提供します。」
- 「TODOにある列マッピングやメタデータ拡張は、ユーザー体験と再現性の向上に直結するため、優先度高です。」

