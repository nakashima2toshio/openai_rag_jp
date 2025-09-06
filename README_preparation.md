# README_preparation.md - 開発環境の準備

## 必要な環境

### Python環境

- Python 3.8以上
- pip（パッケージ管理ツール）

### 推奨環境

- macOS、Linux、またはWindows
- メモリ: 8GB以上
- ディスク容量: 10GB以上（データセット保存用）

## 契約関連
- （1）https://chatgpt.com/auth/login — ChatGPTの利用開始ページ（無料利用やPlus/Go/Teamの申込み・管理もここから行えます）。  ￼
- （2）https://platform.openai.com/signup — 開発者向け「OpenAI API」のサインアップページ（APIキー発行・請求管理は同プラットフォーム内）。

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd openai_rag_jp
```

### 2. Python仮想環境の作成（推奨）

```bash
# venvを使用する場合python -m venv venv

# macOS/Linuxの場合
source venv/bin/activate

# Windowsの場合
venv\Scripts\activate
```

### 3. 必要なパッケージのインストール

```bash
# ライブラリーのインストール　Mac, Linux, Windows
python -m pip install -r requirements.txt
(pip install -r requirements.txt)
```

### 4. 環境変数の設定

#### 必須の環境変数

OpenAI APIキーが必要です。以下のいずれかの方法で設定してください：

**方法1: 環境変数として設定**

```bash
# macOS/Linux
export OPENAI_API_KEY="your-api-key-here"

# Windows (コマンドプロンプト)
set OPENAI_API_KEY="your-api-key-here"

# Windows (PowerShell)
$env:OPENAI_API_KEY="your-api-key-here"
```

**方法2: .envファイルを作成**
プロジェクトルートに`.env`ファイルを作成：

```
OPENAI_API_KEY=your-api-key-here
```

#### オプションの環境変数

天気情報デモを使用する場合：

```
OPENWEATHER_API_KEY=your-weather-api-key-here
```

### 5. 設定ファイルの確認

`config.yml`ファイルが存在することを確認してください。このファイルには以下の設定が含まれています：

- モデル設定（GPT-4o、o1、o3、o4シリーズ）
- APIタイムアウトとリトライ設定
- UI設定（Streamlit用）
- 多言語サポート設定
- トークン価格情報

### 6. ディレクトリ構造の確認

以下のディレクトリが自動的に作成されます：

```
openai_rag_jp/
├── datasets/        # HuggingFaceからダウンロードしたデータセット
├── OUTPUT/          # 処理済みファイルとメタデータ
├── doc/            # ドキュメント（マークダウン形式）
└── logs/           # 実行ログ
```

## 動作確認

### 基本的な動作確認

```bash
# Pythonバージョンの確認
python --version

# パッケージインストールの確認
python -c "import openai; print('OpenAI package installed')"
python -c "import streamlit; print('Streamlit package installed')"
python -c "import datasets; print('HuggingFace datasets installed')"
```

### OpenAI API接続テスト

```python
# helper_api.pyのテスト
python -c "
from helper_api import ConfigManager
cm = ConfigManager()
print('Config loaded successfully')
"
```

## トラブルシューティング

### 1. パッケージインストールエラー

```bash
# pipをアップグレード
pip install --upgrade pip

# 個別にインストール
pip install openai streamlit datasets pandas numpy
```

### 2. OpenAI APIキーエラー

- APIキーが正しく設定されているか確認
- APIキーの前後に余分なスペースがないか確認
- OpenAIダッシュボードでAPIキーの有効性を確認

### 3. メモリ不足エラー

- 大きなデータセットを処理する際は、バッチサイズを調整
- config.ymlでメモリ関連の設定を調整

### 4. ネットワークエラー

- プロキシ設定が必要な環境では、helper_api.pyのプロキシ設定を確認
- APIタイムアウト設定をconfig.ymlで調整

## 開発ツール（オプション）

### PyCharm

プロジェクトはPyCharmでの開発に最適化されています：

1. PyCharmでプロジェクトを開く
2. Python interpreterを設定
3. 環境変数を実行構成に追加

### VS Code

VS Codeを使用する場合：

1. Python拡張機能をインストール
2. `.vscode/settings.json`でPythonパスを設定
3. `.vscode/launch.json`でデバッグ構成を設定

## 次のステップ

環境構築が完了したら、`README_2.md`を参照して実際の利用方法を確認してください。
