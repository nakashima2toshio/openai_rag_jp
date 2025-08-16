# config.yaml
# OpenAI Responses API デモアプリケーションの設定ファイル

# アプリケーション基本情報
app:
  name: "OpenAI-API Basic Demo"
  version: "1.0.0"
  description: "OpenAI Responses APIを使用したデモアプリケーション"
  author: "Toshio Nakashima"

# モデル設定
models:
  default: "gpt-4o-mini"
  available:
    - "gpt-4o"
    - "gpt-4o-mini"
    - "gpt-4o-audio-preview"
    - "gpt-4o-mini-audio-preview"
    - "gpt-4.1"
    - "gpt-4.1-mini"
    - "o3-mini"
    - "o4-mini"
    - "o1-mini"
    - "o4"
    - "o3"
    - "o1"

  # カテゴリ別モデル
  categories:
    reasoning: ["o1", "o1-mini", "o3", "o3-mini", "o4", "o4-mini"]
    standard: ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"]
    audio: ["gpt-4o-audio-preview", "gpt-4o-mini-audio-preview"]
    vision: ["gpt-4o", "gpt-4o-mini"]

# モデル料金設定（1000トークンあたりのドル）
model_pricing:
  gpt-4o:
    input: 0.005
    output: 0.015
  gpt-4o-mini:
    input: 0.00015
    output: 0.0006
  gpt-4o-audio-preview:
    input: 0.01
    output: 0.02
  gpt-4o-mini-audio-preview:
    input: 0.00025
    output: 0.001
  gpt-4.1:
    input: 0.0025
    output: 0.01
  gpt-4.1-mini:
    input: 0.0001
    output: 0.0004
  o1:
    input: 0.015
    output: 0.06
  o1-mini:
    input: 0.003
    output: 0.012
  o3:
    input: 0.03
    output: 0.12
  o3-mini:
    input: 0.006
    output: 0.024
  o4:
    input: 0.05
    output: 0.20
  o4-mini:
    input: 0.01
    output: 0.04

# API設定
api:
  timeout: 30
  max_retries: 3
  retry_delay: 1
  max_tokens: 4096
  openai_api_key: null  # 環境変数 OPENAI_API_KEY から取得
  message_limit: 50  # メッセージ履歴の保持上限

# UI設定
ui:
  page_title: "OpenAI Responses API Demo"
  page_icon: "🤖"
  layout: "wide"
  initial_sidebar_state: "expanded"
  text_area_height: 75
  max_file_search_results: 20
  sidebar_width: 300
  message_display_limit: 50

  # フォーム設定
  forms:
    submit_on_enter: true
    clear_on_submit: false
    show_progress: true

  # テーマ設定
  theme:
    primary_color: "#FF4B4B"
    background_color: "#FFFFFF"
    secondary_background_color: "#F0F2F6"
    text_color: "#262730"
    font: "sans serif"

# デフォルトメッセージ
default_messages:
  developer: |
    You are a strong developer and good at teaching software developer professionals.
    Please provide an up-to-date, informed overview of the API by function, then show
    cookbook programs for each, and explain the API options.
    あなたは強力な開発者でありソフトウェア開発者の専門家に教えるのが得意です。
    OpenAIのAPIを機能別に最新かつ詳細に説明してください。
    それぞれのAPIのサンプルプログラムを示しAPIのオプションについて説明してください。

  user: |
    Organize and identify the problem and list the issues.
    Then, provide a solution procedure for the issues you have organized and identified,
    and solve the problems/issues according to the solution procedures.
    不具合、問題を特定し、整理して箇条書きで列挙・説明してください。
    次に、整理・特定した問題点の解決手順を示しなさい。
    次に、解決手順に従って問題・課題を解決してください。

  assistant: |
    OpenAIのAPIを使用するには、公式openaiライブラリが便利です。
    回答は日本語でお答えします。どのようなことをお手伝いしましょうか？

# エラーメッセージ（多言語対応）
error_messages:
  ja:
    general_error: "エラーが発生しました"
    api_key_missing: "APIキーが設定されていません。環境変数を確認してください。"
    file_not_found: "ファイルが見つかりません: {filename}"
    parse_error: "データの解析に失敗しました。形式を確認してください。"
    network_error: "ネットワークエラーが発生しました。接続を確認してください。"
    model_not_supported: "このモデルはサポートされていません: {model}"
    token_limit_exceeded: "トークン数が上限を超えています。"
    permission_denied: "アクセス権限がありません。"
    rate_limit_exceeded: "レート制限に達しました。しばらく待ってから再試行してください。"
    invalid_request: "リクエストが無効です。パラメータを確認してください。"

  en:
    general_error: "An error occurred"
    api_key_missing: "API key is not set. Please check your environment variables."
    file_not_found: "File not found: {filename}"
    parse_error: "Failed to parse data. Please check the format."
    network_error: "Network error occurred. Please check your connection."
    model_not_supported: "This model is not supported: {model}"
    token_limit_exceeded: "Token count exceeds the limit."
    permission_denied: "Access denied."
    rate_limit_exceeded: "Rate limit exceeded. Please wait and try again."
    invalid_request: "Invalid request. Please check the parameters."

# サンプルデータ
samples:
  images:
    nature: "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"

  prompts:
    event_example: "台湾フェス2025 ～あつまれ！究極の台湾グルメ～ in Kawasaki Spark"
    weather_query: "週末の東京の天気とおすすめの屋内アクティビティは？"
    responses_query: "OpenAIのAPIで、responses.createを説明しなさい。"
    code_query: "Pythonで素数を判定する関数を作成してください。"
    analysis_query: "最近のAI技術のトレンドを3つ教えてください。"
    math_problem: "2X + 1 = 5  Xはいくつ？"

  documents:
    simple_text: "これはテストドキュメントです。"
    json_example: '{"name": "test", "value": 123}'

# ファイルパス設定
paths:
  data: "data"
  cities_csv: "data/cities_list.csv"
  images_dir: "images"
  datasets_dir: "datasets"
  logs_dir: "logs"
  cache_dir: "cache"
  config_dir: "config"
  temp_dir: "temp"

# ロギング設定
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: null  # ファイルログを無効化（必要に応じて "logs/app.log" に変更）
  max_bytes: 10485760  # 10MB
  backup_count: 5

  # ログレベル別設定
  loggers:
    openai_helper:
      level: "INFO"
      handlers: ["console"]  # "file" を削除
    streamlit:
      level: "WARNING"
      handlers: ["console"]

# キャッシュ設定
cache:
  enabled: true
  ttl: 3600  # 1時間
  max_size: 100  # 最大100エントリ

  # キャッシュタイプ別設定
  types:
    api_responses:
      ttl: 1800  # 30分
      max_size: 50
    model_info:
      ttl: 86400  # 24時間
      max_size: 20
    user_preferences:
      ttl: 604800  # 1週間
      max_size: 30

# 実験的機能
experimental:
  enable_beta_features: false
  debug_mode: false
  performance_monitoring: true

  # ベータ機能
  beta_features:
    - "advanced_caching"
    - "multi_language_support"
    - "custom_themes"

  # パフォーマンス設定
  performance:
    enable_profiling: false
    max_metrics_history: 100
    auto_optimization: false

# セキュリティ設定
security:
  # APIキー管理
  api_key_rotation: false
  api_key_validation: true

  # レート制限
  rate_limiting:
    enabled: false
    requests_per_minute: 60
    requests_per_hour: 1000

  # ログ記録
  audit_logging: false
  sensitive_data_masking: true

# 国際化設定
i18n:
  default_language: "ja"
  available_languages: ["ja", "en"]
  auto_detect: false

  # 翻訳ファイル
  translation_files:
    ja: "i18n/ja.json"
    en: "i18n/en.json"

# 統合設定
integrations:
  # 外部API
  external_apis:
    openweather:
      enabled: true
      api_key_env: "OPENWEATHER_API_KEY"
      timeout: 10

  # データベース
  databases:
    vector_store:
      enabled: false
      provider: "chroma"
      connection_string: null

  # 分析ツール
  analytics:
    google_analytics: null
    mixpanel: null

# 開発者設定
development:
  # デバッグ
  debug:
    enabled: false
    verbose: false
    show_internal_errors: false

  # テスト
  testing:
    mock_api_calls: false
    test_data_dir: "tests/data"

  # プロファイリング
  profiling:
    enabled: false
    output_dir: "profiling"

# デモ設定
demos:
  # カテゴリ別デモ
  categories:
    - name: "基本機能"
      icon: "🎯"
      demos:
        - "simple_chat"
        - "structured_output"
        - "function_calling"

    - name: "高度な機能"
      icon: "🚀"
      demos:
        - "vision"
        - "audio"
        - "streaming"
        - "chain_of_thought"

    - name: "ツール連携"
      icon: "🔧"
      demos:
        - "file_search"
        - "web_search"
        - "computer_use"

    - name: "ユーティリティ"
      icon: "⚙️"
      demos:
        - "token_counter"
        - "model_comparison"
        - "cost_calculator"

  # デモ別設定
  demo_configs:
    simple_chat:
      title: "シンプルチャット"
      description: "基本的なチャット機能のデモ"
      category: "基本機能"

    structured_output:
      title: "構造化出力"
      description: "JSONスキーマを使用した構造化データ出力"
      category: "基本機能"

    function_calling:
      title: "関数呼び出し"
      description: "外部関数を呼び出す機能のデモ"
      category: "基本機能"

    vision:
      title: "画像認識"
      description: "画像を理解して回答する機能"
      category: "高度な機能"

    chain_of_thought:
      title: "思考の連鎖"
      description: "段階的推論による問題解決"
      category: "高度な機能"

# バックアップとリストア
backup:
  auto_backup: false
  backup_interval: 86400  # 24時間
  backup_retention: 7  # 7日間
  backup_location: "backups"

  # バックアップ対象
  include:
    - "config"
    - "logs"
    - "user_data"

  exclude:
    - "cache"
    - "temp"

# 通知設定
notifications:
  enabled: false

  # 通知タイプ
  types:
    errors: true
    warnings: false
    info: false

  # 通知先
  destinations:
    email: null
    slack: null
    discord: null

# ヘルスチェック
health_check:
  enabled: true
  interval: 300  # 5分

  # チェック項目
  checks:
    - "api_connectivity"
    - "disk_space"
    - "memory_usage"

  # 閾値
  thresholds:
    disk_space_warning: 80  # %
    memory_usage_warning: 80  # %
