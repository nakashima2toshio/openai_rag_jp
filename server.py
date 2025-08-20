#!/usr/bin/env python3
"""
MCPサーバー起動スクリプト  
Usage: python server.py [--port PORT] [--test]
"""

import os
import sys
import time
import subprocess
import argparse
import requests
from pathlib import Path


def check_database_connections():
    """データベース接続確認"""
    connections_ok = True
    
    # PostgreSQL接続確認
    print("🐘 PostgreSQL接続確認...")
    try:
        import psycopg2
        conn_str = os.getenv('PG_CONN_STR', 'postgresql://testuser:testpass@localhost:5432/testdb')
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        print("  ✅ PostgreSQL接続成功")
    except ImportError:
        print("  ❌ psycopg2-binary パッケージが不足しています")
        connections_ok = False
    except Exception as e:
        print(f"  ❌ PostgreSQL接続失敗: {e}")
        connections_ok = False
    
    # Redis接続確認
    print("🔴 Redis接続確認...")
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        print("  ✅ Redis接続成功")
    except ImportError:
        print("  ❌ redis パッケージが不足しています")
        connections_ok = False
    except Exception as e:
        print(f"  ❌ Redis接続失敗: {e}")
        connections_ok = False
    
    if not connections_ok:
        print("\n💡 解決方法:")
        print("1. Dockerサービスを起動:")
        print("   docker-compose -f docker-compose/docker-compose.yml up -d")
        print("2. データを投入:")
        print("   python data.py")
    
    return connections_ok


def start_api_server(port=8000):
    """APIサーバーを起動"""
    print(f"🚀 APIサーバーを起動中（ポート: {port}）...")
    
    # サーバーファイルの存在確認
    if not Path("mcp_api_server.py").exists():
        print("❌ mcp_api_server.py が見つかりません")
        return None
    
    # バックグラウンドでAPIサーバーを起動
    try:
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "mcp_api_server:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--reload"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # サーバーの起動を待機
        print("⏳ サーバーの起動を待機中...")
        for i in range(30):
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=2)
                if response.status_code == 200:
                    health_data = response.json()
                    print("✅ APIサーバーが起動しました!")
                    print(f"📍 URL: http://localhost:{port}")
                    print(f"📖 ドキュメント: http://localhost:{port}/docs")
                    print(f"🏥 ヘルス: {health_data.get('status', 'unknown')}")
                    return process
            except Exception:
                pass
            
            print(f"   ... 待機中 ({i + 1}/30)")
            time.sleep(1)
        
        print("❌ APIサーバーの起動に失敗しました")
        process.terminate()
        return None
        
    except Exception as e:
        print(f"❌ APIサーバー起動エラー: {e}")
        return None


def test_api_endpoints(port=8000):
    """APIエンドポイントのテスト"""
    print("🧪 APIエンドポイントのテスト...")
    
    base_url = f"http://localhost:{port}"
    test_endpoints = [
        ("GET", "/health", "ヘルスチェック"),
        ("GET", "/api/customers?limit=1", "顧客一覧"),
        ("GET", "/api/products?limit=1", "商品一覧"),
        ("GET", "/api/stats/sales", "売上統計")
    ]
    
    successful_tests = 0
    for method, endpoint, description in test_endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.request(method, url, timeout=5)
            
            if response.status_code == 200:
                print(f"  ✅ {description}: OK")
                successful_tests += 1
            else:
                print(f"  ⚠️ {description}: {response.status_code}")
        except Exception as e:
            print(f"  ❌ {description}: エラー - {e}")
    
    print(f"\n📊 テスト結果: {successful_tests}/{len(test_endpoints)} 成功")
    return successful_tests == len(test_endpoints)


def display_usage_info(port=8000):
    """使用方法の表示"""
    print("\n" + "=" * 50)
    print("📚 使用方法")
    print("=" * 50)
    
    print(f"\n💡 基本的な使用方法:")
    print(f"🌐 APIドキュメント: http://localhost:{port}/docs")
    print(f"📖 ReDoc: http://localhost:{port}/redoc")
    print(f"🏥 ヘルスチェック: curl http://localhost:{port}/health")
    
    print(f"\n🔧 サーバー管理:")
    print("- サーバー停止: Ctrl+C")
    print(f"- ポート確認: netstat -an | grep {port}")


def main():
    parser = argparse.ArgumentParser(description="MCPサーバー起動")
    parser.add_argument("--port", type=int, default=8000, help="ポート番号（デフォルト: 8000）")
    parser.add_argument("--test", action="store_true", help="起動後にテストを実行")
    args = parser.parse_args()
    
    print("🚀 MCPサーバー起動を開始します")
    print("=" * 50)
    
    # 1. データベース接続確認
    if not check_database_connections():
        print("❌ データベース接続に失敗しました")
        print("データを投入してください: python data.py")
        sys.exit(1)
    
    # 2. APIサーバー起動
    server_process = start_api_server(args.port)
    if not server_process:
        print("❌ APIサーバーの起動に失敗しました")
        sys.exit(1)
    
    # 3. テスト実行（指定された場合）
    if args.test:
        if test_api_endpoints(args.port):
            print("✅ 全てのエンドポイントが正常です")
        else:
            print("⚠️ 一部のエンドポイントに問題があります")
    
    # 4. 使用方法表示
    display_usage_info(args.port)
    
    print("\n🎉 サーバー起動完了!")
    print("⏸️ サーバーを停止するには Ctrl+C を押してください...")
    
    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 サーバーを停止中...")
        server_process.terminate()
        server_process.wait()
        print("✅ サーバーが停止しました")


if __name__ == "__main__":
    main()