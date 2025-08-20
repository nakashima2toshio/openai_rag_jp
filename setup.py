#!/usr/bin/env python3
"""
MCP環境セットアップスクリプト
Usage: python setup.py [--quick]
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def check_python_version():
    """Python バージョンチェック"""
    print("🐍 Python バージョンチェック...")
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8以上が必要です。現在のバージョン: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} - OK")
    return True


def detect_package_manager():
    """パッケージマネージャーの検出"""
    if subprocess.run(["which", "uv"], capture_output=True).returncode == 0:
        print("✅ uvを使用してパッケージをインストール")
        return "uv"
    else:
        print("📦 pipを使用してパッケージをインストール")
        return "pip"


def install_packages(package_manager="pip"):
    """必要なパッケージをインストール"""
    print("📦 必要なパッケージをインストール中...")
    
    if package_manager == "uv":
        packages = [
            "streamlit>=1.48.0",
            "openai>=1.99.9", 
            "fastapi>=0.116.1",
            "uvicorn[standard]>=0.24.0",
            "psycopg2-binary>=2.9.0",
            "redis>=5.0.0",
            "elasticsearch>=8.10.0", 
            "qdrant-client>=1.6.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "python-dotenv>=1.0.0"
        ]
        
        try:
            # uvプロジェクトを初期化（既存の場合はスキップ）
            if not Path("pyproject.toml").exists():
                subprocess.run(["uv", "init", "."], check=True)
            
            for package in packages:
                subprocess.run(["uv", "add", package], check=True)
            print("✅ uvでのインストール完了")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ uvでのインストール失敗: {e}")
            return False
    else:
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--upgrade"
            ], check=True, capture_output=True)
            print("✅ pipでのインストール完了")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ pipでのインストール失敗: {e}")
            return False


def create_env_template():
    """環境変数テンプレートファイルの作成"""
    print("🔧 .env テンプレートファイル作成中...")
    
    env_template = """# OpenAI API Key (必須)
OPENAI_API_KEY=your-openai-api-key-here

# Database URLs
REDIS_URL=redis://localhost:6379/0
PG_CONN_STR=postgresql://testuser:testpass@localhost:5432/testdb
ELASTIC_URL=http://localhost:9200
QDRANT_URL=http://localhost:6333

# Optional API Keys
PINECONE_API_KEY=your-pinecone-api-key-here
"""
    
    if not Path(".env").exists():
        Path(".env").write_text(env_template)
        print("⚠️  .env ファイルを作成しました。OPENAI_API_KEY を設定してください。")
    else:
        print("✅ .env ファイルは既に存在します")


def verify_installation():
    """インストール確認"""
    print("🔍 インストール確認中...")
    
    required_modules = [
        "streamlit", "openai", "fastapi", "uvicorn", 
        "psycopg2", "redis", "elasticsearch", "qdrant_client",
        "pandas", "requests"
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module}")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n❌ 不足パッケージ: {', '.join(missing_modules)}")
        return False
    
    print("✅ 全ての依存関係が満たされています")
    return True


def main():
    parser = argparse.ArgumentParser(description="MCP環境セットアップ")
    parser.add_argument("--quick", action="store_true", help="クイックセットアップ（検証をスキップ）")
    args = parser.parse_args()
    
    print("🚀 MCP環境セットアップを開始します")
    print("=" * 50)
    
    # 1. Python バージョンチェック
    if not check_python_version():
        sys.exit(1)
    
    # 2. パッケージマネージャー検出
    package_manager = detect_package_manager()
    
    # 3. パッケージインストール
    if not install_packages(package_manager):
        print("❌ セットアップ失敗: パッケージのインストールに失敗")
        sys.exit(1)
    
    # 4. 環境変数テンプレート作成
    create_env_template()
    
    # 5. インストール確認（クイックモードでない場合）
    if not args.quick:
        if not verify_installation():
            print("❌ セットアップ失敗: 一部のパッケージが不足")
            sys.exit(1)
    
    print("\n🎉 環境セットアップ完了!")
    print("\n次のステップ:")
    print("1. .env ファイルで OPENAI_API_KEY を設定")
    print("2. サーバー起動: python server.py")
    print("3. データ投入: python data.py")


if __name__ == "__main__":
    main()