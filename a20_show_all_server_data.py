#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
a20_show_all_server_data.py - データベースサーバー統合監視ツール
=============================================================
起動: streamlit run a20_show_all_server_data.py --server.port=8502

【主要機能】
✅ 4つのデータベースサーバーの接続状態チェック（Redis, PostgreSQL, Elasticsearch, Qdrant）
✅ 各サーバーのデータ表示機能
✅ デバッグ機能（詳細ログ、接続テスト、パフォーマンス測定）
✅ サーバーメトリクス表示（メモリ、CPU、レスポンスタイム）
✅ 自動リフレッシュ機能
✅ エクスポート機能（CSV, JSON）
"""

import streamlit as st
import pandas as pd
import json
import time
import logging
import traceback
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import socket
import subprocess
import platform

# psutilのインポート（オプション）
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("psutil not available. Install with: pip install psutil")

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベースクライアントのインポート（オプション）
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis client not available. Install with: pip install redis")

try:
    import psycopg2
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    logger.warning("PostgreSQL client not available. Install with: pip install psycopg2")

try:
    from elasticsearch import Elasticsearch
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    logger.warning("Elasticsearch client not available. Install with: pip install elasticsearch")

try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("Qdrant client not available. Install with: pip install qdrant-client")

# ===================================================================
# サーバー設定
# ===================================================================
SERVER_CONFIG = {
    "redis": {
        "name": "Redis",
        "host": "localhost",
        "port": 6379,
        "icon": "🔴",
        "default_db": 0,
        "health_check_cmd": "redis-cli ping",
        "docker_image": "redis:latest"
    },
    "postgresql": {
        "name": "PostgreSQL",
        "host": "localhost",
        "port": 5432,
        "icon": "🐘",
        "database": "postgres",
        "user": "postgres",
        "password": "postgres",
        "health_check_cmd": "pg_isready",
        "docker_image": "postgres:latest"
    },
    "elasticsearch": {
        "name": "Elasticsearch",
        "host": "localhost",
        "port": 9200,
        "icon": "🔍",
        "scheme": "http",
        "health_check_endpoint": "/_cluster/health",
        "docker_image": "elasticsearch:8.10.0"
    },
    "qdrant": {
        "name": "Qdrant",
        "host": "localhost",
        "port": 6333,
        "icon": "🎯",
        "url": "http://localhost:6333",
        "health_check_endpoint": "/collections",
        "docker_image": "qdrant/qdrant"
    }
}

# ===================================================================
# サーバー接続チェッククラス
# ===================================================================
class ServerHealthChecker:
    """各サーバーの接続状態をチェック"""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.connection_cache = {}
        
    def check_port(self, host: str, port: int, timeout: float = 2.0) -> bool:
        """ポートが開いているかチェック"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            if self.debug_mode:
                logger.error(f"Port check failed for {host}:{port}: {e}")
            return False
    
    def check_redis(self) -> Tuple[bool, str, Optional[Dict]]:
        """Redis接続チェック"""
        config = SERVER_CONFIG["redis"]
        start_time = time.time()
        
        # まずポートチェック
        if not self.check_port(config["host"], config["port"]):
            return False, "Connection refused (port closed)", None
        
        if not REDIS_AVAILABLE:
            return False, "Redis client not installed", None
        
        try:
            client = redis.Redis(
                host=config["host"],
                port=config["port"],
                db=config["default_db"],
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # PINGテスト
            ping_result = client.ping()
            
            # サーバー情報取得
            info = client.info()
            metrics = {
                "version": info.get("redis_version", "Unknown"),
                "uptime": info.get("uptime_in_seconds", 0),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "Unknown"),
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
            
            self.connection_cache["redis"] = client
            return True, "Connected", metrics
            
        except Exception as e:
            error_msg = str(e)
            if self.debug_mode:
                error_msg = f"{error_msg}\n{traceback.format_exc()}"
            return False, error_msg, None
    
    def check_postgresql(self) -> Tuple[bool, str, Optional[Dict]]:
        """PostgreSQL接続チェック"""
        config = SERVER_CONFIG["postgresql"]
        start_time = time.time()
        
        # まずポートチェック
        if not self.check_port(config["host"], config["port"]):
            return False, "Connection refused (port closed)", None
        
        if not POSTGRESQL_AVAILABLE:
            return False, "PostgreSQL client not installed", None
        
        try:
            conn = psycopg2.connect(
                host=config["host"],
                port=config["port"],
                database=config["database"],
                user=config["user"],
                password=config["password"],
                connect_timeout=5
            )
            
            cursor = conn.cursor()
            # バージョン取得
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            
            # データベースリスト取得
            cursor.execute("SELECT COUNT(*) FROM pg_database")
            db_count = cursor.fetchone()[0]
            
            # テーブル数取得
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            
            metrics = {
                "version": version.split(' ')[1] if version else "Unknown",
                "database_count": db_count,
                "table_count": table_count,
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
            
            self.connection_cache["postgresql"] = conn
            return True, "Connected", metrics
            
        except Exception as e:
            error_msg = str(e)
            if self.debug_mode:
                error_msg = f"{error_msg}\n{traceback.format_exc()}"
            return False, error_msg, None
    
    def check_elasticsearch(self) -> Tuple[bool, str, Optional[Dict]]:
        """Elasticsearch接続チェック"""
        config = SERVER_CONFIG["elasticsearch"]
        start_time = time.time()
        
        # まずポートチェック
        if not self.check_port(config["host"], config["port"]):
            return False, "Connection refused (port closed)", None
        
        if not ELASTICSEARCH_AVAILABLE:
            return False, "Elasticsearch client not installed", None
        
        try:
            # Elasticsearch 8.x用の設定
            from elasticsearch import __version__ as es_version
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            es = Elasticsearch(
                [f"{config['scheme']}://{config['host']}:{config['port']}"],
                request_timeout=5,
                verify_certs=False,
                ssl_show_warn=False,
                basic_auth=None  # 必要に応じて認証情報を追加
            )
            
            # ヘルスチェック
            health = es.cluster.health()
            
            # インデックス情報
            indices = es.indices.stats()
            
            metrics = {
                "cluster_name": health.get("cluster_name", "Unknown"),
                "status": health.get("status", "Unknown"),
                "node_count": health.get("number_of_nodes", 0),
                "index_count": len(indices.get("indices", {})),
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
            
            self.connection_cache["elasticsearch"] = es
            return True, "Connected", metrics
            
        except Exception as e:
            error_msg = str(e)
            if self.debug_mode:
                error_msg = f"{error_msg}\n{traceback.format_exc()}"
            return False, error_msg, None
    
    def check_qdrant(self) -> Tuple[bool, str, Optional[Dict]]:
        """Qdrant接続チェック"""
        config = SERVER_CONFIG["qdrant"]
        start_time = time.time()
        
        # まずポートチェック
        if not self.check_port(config["host"], config["port"]):
            return False, "Connection refused (port closed)", None
        
        if not QDRANT_AVAILABLE:
            return False, "Qdrant client not installed", None
        
        try:
            client = QdrantClient(url=config["url"], timeout=5)
            
            # コレクション取得
            collections = client.get_collections()
            
            metrics = {
                "collection_count": len(collections.collections),
                "collections": [c.name for c in collections.collections],
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
            
            self.connection_cache["qdrant"] = client
            return True, "Connected", metrics
            
        except Exception as e:
            error_msg = str(e)
            if self.debug_mode:
                error_msg = f"{error_msg}\n{traceback.format_exc()}"
            return False, error_msg, None
    
    def check_all_servers(self) -> Dict[str, Tuple[bool, str, Optional[Dict]]]:
        """すべてのサーバーをチェック"""
        results = {}
        
        check_methods = {
            "redis": self.check_redis,
            "postgresql": self.check_postgresql,
            "elasticsearch": self.check_elasticsearch,
            "qdrant": self.check_qdrant
        }
        
        for server_key, check_method in check_methods.items():
            results[server_key] = check_method()
        
        return results

# ===================================================================
# データ取得クラス
# ===================================================================
class ServerDataFetcher:
    """各サーバーからデータを取得"""
    
    def __init__(self, checker: ServerHealthChecker):
        self.checker = checker
    
    def fetch_redis_data(self, pattern: str = "*", limit: int = 100) -> pd.DataFrame:
        """Redisのデータを取得"""
        if "redis" not in self.checker.connection_cache:
            return pd.DataFrame({"Error": ["Not connected"]})
        
        try:
            client = self.checker.connection_cache["redis"]
            keys = client.keys(pattern)[:limit]
            
            data = []
            for key in keys:
                key_type = client.type(key).decode('utf-8')
                
                if key_type == "string":
                    value = client.get(key)
                    if value:
                        value = value.decode('utf-8', errors='ignore')
                elif key_type == "list":
                    value = f"List[{client.llen(key)} items]"
                elif key_type == "set":
                    value = f"Set[{client.scard(key)} items]"
                elif key_type == "hash":
                    value = f"Hash[{len(client.hkeys(key))} fields]"
                else:
                    value = f"Type: {key_type}"
                
                data.append({
                    "Key": key.decode('utf-8', errors='ignore'),
                    "Type": key_type,
                    "Value": value,
                    "TTL": client.ttl(key)
                })
            
            return pd.DataFrame(data) if data else pd.DataFrame({"Info": ["No data found"]})
            
        except Exception as e:
            return pd.DataFrame({"Error": [str(e)]})
    
    def fetch_postgresql_data(self, query: str = None) -> pd.DataFrame:
        """PostgreSQLのデータを取得"""
        if "postgresql" not in self.checker.connection_cache:
            return pd.DataFrame({"Error": ["Not connected"]})
        
        try:
            conn = self.checker.connection_cache["postgresql"]
            cursor = conn.cursor()
            
            if query is None:
                # デフォルト: テーブル一覧を取得
                query = """
                    SELECT 
                        schemaname as "Schema",
                        tablename as "Table",
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as "Size"
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY schemaname, tablename
                    LIMIT 100
                """
            
            # カーソルでクエリを実行
            cursor.execute(query)
            
            # カラム名を取得
            columns = [desc[0] for desc in cursor.description]
            
            # 結果を取得
            rows = cursor.fetchall()
            cursor.close()
            
            # DataFrameを作成
            if rows:
                df = pd.DataFrame(rows, columns=columns)
                return df
            else:
                return pd.DataFrame({"Info": ["No data found"]})
            
        except Exception as e:
            return pd.DataFrame({"Error": [str(e)]})
    
    def fetch_elasticsearch_data(self, index: str = "*", size: int = 100) -> pd.DataFrame:
        """Elasticsearchのデータを取得"""
        if "elasticsearch" not in self.checker.connection_cache:
            return pd.DataFrame({"Error": ["Not connected"]})
        
        try:
            es = self.checker.connection_cache["elasticsearch"]
            
            # インデックス一覧を取得
            indices = es.indices.get_alias(index=index)
            
            data = []
            for idx_name, idx_info in indices.items():
                stats = es.indices.stats(index=idx_name)
                idx_stats = stats["indices"][idx_name]["total"]
                
                data.append({
                    "Index": idx_name,
                    "Docs Count": idx_stats["docs"]["count"],
                    "Size": idx_stats["store"]["size_in_bytes"],
                    "Size (Human)": self._format_bytes(idx_stats["store"]["size_in_bytes"]),
                    "Aliases": ", ".join(idx_info.get("aliases", {}).keys()) or "None"
                })
            
            return pd.DataFrame(data) if data else pd.DataFrame({"Info": ["No indices found"]})
            
        except Exception as e:
            return pd.DataFrame({"Error": [str(e)]})
    
    def fetch_qdrant_data(self) -> pd.DataFrame:
        """Qdrantのデータを取得"""
        if "qdrant" not in self.checker.connection_cache:
            return pd.DataFrame({"Error": ["Not connected"]})
        
        try:
            client = self.checker.connection_cache["qdrant"]
            collections = client.get_collections()
            
            data = []
            for collection in collections.collections:
                try:
                    info = client.get_collection(collection.name)
                    data.append({
                        "Collection": collection.name,
                        "Vectors Count": info.vectors_count,
                        "Points Count": info.points_count,
                        "Indexed Vectors": info.indexed_vectors_count,
                        "Status": info.status
                    })
                except:
                    data.append({
                        "Collection": collection.name,
                        "Vectors Count": "N/A",
                        "Points Count": "N/A",
                        "Indexed Vectors": "N/A",
                        "Status": "Error"
                    })
            
            return pd.DataFrame(data) if data else pd.DataFrame({"Info": ["No collections found"]})
            
        except Exception as e:
            return pd.DataFrame({"Error": [str(e)]})
    
    def fetch_qdrant_collection_points(self, collection_name: str, limit: int = 50) -> pd.DataFrame:
        """Qdrantコレクションの詳細データを取得"""
        if "qdrant" not in self.checker.connection_cache:
            return pd.DataFrame({"Error": ["Not connected"]})
        
        try:
            client = self.checker.connection_cache["qdrant"]
            
            # スクロールを使ってポイントを取得
            points_result = client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            points = points_result[0]  # scrollは (points, next_offset) のタプルを返す
            
            if not points:
                return pd.DataFrame({"Info": ["No points found in collection"]})
            
            # ポイントをDataFrameに変換
            data = []
            for point in points:
                row = {"ID": point.id}
                
                # payloadの各フィールドを列として追加
                if point.payload:
                    for key, value in point.payload.items():
                        # 長すぎる文字列は切り詰め
                        if isinstance(value, str) and len(value) > 200:
                            row[key] = value[:200] + '...'
                        elif isinstance(value, (list, dict)):
                            row[key] = str(value)[:200] + '...' if len(str(value)) > 200 else str(value)
                        else:
                            row[key] = value
                
                data.append(row)
            
            return pd.DataFrame(data)
            
        except Exception as e:
            return pd.DataFrame({"Error": [str(e)]})
    
    def fetch_qdrant_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Qdrantコレクションの詳細情報を取得"""
        if "qdrant" not in self.checker.connection_cache:
            return {"error": "Not connected"}
        
        try:
            client = self.checker.connection_cache["qdrant"]
            collection_info = client.get_collection(collection_name)
            
            # configの構造を安全にアクセス
            vector_config = collection_info.config.params.vectors
            
            # vector_configの型を判定して適切に処理
            if hasattr(vector_config, 'size'):
                # 単一ベクトル設定
                vector_size = vector_config.size
                distance = vector_config.distance
            elif hasattr(vector_config, '__iter__'):
                # Named vectors設定の場合
                vector_sizes = {}
                distances = {}
                for name, config in vector_config.items() if isinstance(vector_config, dict) else []:
                    vector_sizes[name] = config.size if hasattr(config, 'size') else 'N/A'
                    distances[name] = config.distance if hasattr(config, 'distance') else 'N/A'
                vector_size = vector_sizes if vector_sizes else 'N/A'
                distance = distances if distances else 'N/A'
            else:
                vector_size = 'N/A'
                distance = 'N/A'
            
            return {
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "indexed_vectors": collection_info.indexed_vectors_count,
                "status": collection_info.status,
                "config": {
                    "vector_size": vector_size,
                    "distance": distance,
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _format_bytes(self, size: int) -> str:
        """バイトサイズを人間が読みやすい形式に変換"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

# ===================================================================
# Streamlit UI
# ===================================================================
def main():
    st.set_page_config(
        page_title="DB Server Monitor",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # セッションステート初期化
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False
    if "refresh_interval" not in st.session_state:
        st.session_state.refresh_interval = 30
    
    # タイトル
    st.title("🔍 データベースサーバー統合監視ツール")
    st.markdown("Redis, PostgreSQL, Elasticsearch, Qdrant の状態監視とデータ表示")
    
    # サイドバー（左ペイン）
    with st.sidebar:
        st.header("⚙️ サーバー接続状態")
        
        # デバッグモード切り替え
        debug_mode = st.checkbox("🐛 デバッグモード", value=st.session_state.debug_mode)
        st.session_state.debug_mode = debug_mode
        
        # 自動リフレッシュ設定
        col1, col2 = st.columns(2)
        with col1:
            auto_refresh = st.checkbox("🔄 自動更新", value=st.session_state.auto_refresh)
            st.session_state.auto_refresh = auto_refresh
        with col2:
            if auto_refresh:
                refresh_interval = st.number_input("間隔(秒)", min_value=5, max_value=300, value=30)
                st.session_state.refresh_interval = refresh_interval
        
        # 接続チェック実行ボタン
        check_button = st.button("🔍 接続チェック実行", type="primary", use_container_width=True)
        
        # HealthCheckerインスタンス
        checker = ServerHealthChecker(debug_mode=debug_mode)
        
        # 接続状態表示エリア
        status_container = st.container()
        
        # 自動リフレッシュまたはボタン押下時に実行
        if check_button or (auto_refresh and time.time() % refresh_interval < 1):
            with status_container:
                with st.spinner("チェック中..."):
                    results = checker.check_all_servers()
                
                # 各サーバーの状態表示
                for server_key, config in SERVER_CONFIG.items():
                    is_connected, message, metrics = results[server_key]
                    
                    # ステータス表示
                    if is_connected:
                        st.success(f"{config['icon']} **{config['name']}**")
                        st.caption(f"✅ {message}")
                        
                        # メトリクス表示
                        if metrics and debug_mode:
                            with st.expander(f"詳細情報", expanded=False):
                                for key, value in metrics.items():
                                    st.text(f"{key}: {value}")
                    else:
                        st.error(f"{config['icon']} **{config['name']}**")
                        st.caption(f"❌ {message}")
                        
                        # エラー詳細（デバッグモード）
                        if debug_mode:
                            with st.expander("エラー詳細", expanded=False):
                                st.code(message)
                                st.caption(f"Host: {config.get('host')}:{config.get('port')}")
                                
                                # Docker起動コマンド表示
                                if "docker_image" in config:
                                    st.info("Docker起動コマンド:")
                                    if server_key == "redis":
                                        cmd = f"docker run -d -p {config['port']}:{config['port']} {config['docker_image']}"
                                    elif server_key == "postgresql":
                                        cmd = f"docker run -d -p {config['port']}:{config['port']} -e POSTGRES_PASSWORD=postgres {config['docker_image']}"
                                    elif server_key == "elasticsearch":
                                        cmd = f"docker run -d -p {config['port']}:{config['port']} -e discovery.type=single-node {config['docker_image']}"
                                    elif server_key == "qdrant":
                                        cmd = f"docker run -d -p {config['port']}:{config['port']} {config['docker_image']}"
                                    st.code(cmd, language="bash")
                
                st.divider()
                
                # システム情報（デバッグモード）
                if debug_mode and PSUTIL_AVAILABLE:
                    st.subheader("📊 システム情報")
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("CPU使用率", f"{cpu_percent}%")
                    with col2:
                        st.metric("メモリ使用率", f"{memory.percent}%")
                    
                    st.caption(f"Platform: {platform.system()} {platform.release()}")
                    st.caption(f"Python: {platform.python_version()}")
                elif debug_mode:
                    st.subheader("📊 システム情報")
                    st.caption(f"Platform: {platform.system()} {platform.release()}")
                    st.caption(f"Python: {platform.python_version()}")
                    st.info("psutil not installed. Install with: pip install psutil")
        
        # サーバー選択ラジオボタン
        st.divider()
        st.subheader("📊 データ表示サーバー選択")
        server_options = {
            "redis": f"{SERVER_CONFIG['redis']['icon']} Redis",
            "postgresql": f"{SERVER_CONFIG['postgresql']['icon']} PostgreSQL",
            "elasticsearch": f"{SERVER_CONFIG['elasticsearch']['icon']} Elasticsearch",
            "qdrant": f"{SERVER_CONFIG['qdrant']['icon']} Qdrant"
        }
        selected_server = st.radio(
            "表示するサーバーを選択",
            options=list(server_options.keys()),
            format_func=lambda x: server_options[x],
            key="selected_server"
        )
    
    # メインエリア（右ペイン）
    st.header(f"📊 {server_options[selected_server]} データ表示")
    
    # データ取得用インスタンス
    data_fetcher = ServerDataFetcher(checker)
    
    # 選択されたサーバーに応じて表示を切り替え
    if selected_server == "redis":
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            pattern = st.text_input("検索パターン", value="*", key="redis_pattern")
        with col2:
            limit = st.number_input("表示件数", min_value=1, max_value=1000, value=100, key="redis_limit")
        with col3:
            fetch_redis = st.button("🔍 データ取得", key="fetch_redis")
        
        if fetch_redis:
            with st.spinner("Redisデータ取得中..."):
                try:
                    if not REDIS_AVAILABLE:
                        st.error("Redis clientがインストールされていません。")
                        st.code("pip install redis", language="bash")
                    else:
                        # 直接Redisクライアントを作成して接続
                        import redis
                        redis_config = SERVER_CONFIG["redis"]
                        redis_client = redis.Redis(
                            host=redis_config["host"],
                            port=redis_config["port"],
                            db=redis_config["default_db"],
                            socket_timeout=5,
                            socket_connect_timeout=5,
                            decode_responses=True  # 文字列として自動デコード
                        )
                        
                        # 接続確認
                        redis_client.ping()
                        
                        # キーを取得
                        keys = redis_client.keys(pattern)
                        
                        if not keys:
                            st.info(f"パターン '{pattern}' に一致するキーが見つかりません")
                        else:
                            # limitを適用
                            keys = keys[:limit]
                            
                            data = []
                            for key in keys:
                                try:
                                    key_type = redis_client.type(key)
                                    
                                    if key_type == "string":
                                        value = redis_client.get(key)
                                        if value and len(value) > 200:
                                            value = value[:200] + '...'
                                    elif key_type == "list":
                                        list_len = redis_client.llen(key)
                                        sample = redis_client.lrange(key, 0, 2)
                                        value = f"List[{list_len} items]: {sample[:3]}..."
                                    elif key_type == "set":
                                        set_size = redis_client.scard(key)
                                        sample = list(redis_client.smembers(key))[:3]
                                        value = f"Set[{set_size} items]: {sample}..."
                                    elif key_type == "hash":
                                        hash_len = redis_client.hlen(key)
                                        sample = dict(list(redis_client.hgetall(key).items())[:3])
                                        value = f"Hash[{hash_len} fields]: {sample}..."
                                    elif key_type == "zset":
                                        zset_size = redis_client.zcard(key)
                                        sample = redis_client.zrange(key, 0, 2, withscores=True)
                                        value = f"ZSet[{zset_size} items]: {sample[:3]}..."
                                    else:
                                        value = f"Type: {key_type}"
                                    
                                    ttl = redis_client.ttl(key)
                                    ttl_str = "永続" if ttl == -1 else f"{ttl}秒" if ttl > 0 else "期限切れ"
                                    
                                    data.append({
                                        "Key": key,
                                        "Type": key_type,
                                        "Value": value,
                                        "TTL": ttl_str
                                    })
                                except Exception as e:
                                    data.append({
                                        "Key": key,
                                        "Type": "Error",
                                        "Value": str(e)[:100],
                                        "TTL": "N/A"
                                    })
                            
                            if data:
                                df = pd.DataFrame(data)
                                st.write(f"**検索結果: {len(data)} 件のキー**")
                                st.dataframe(df, use_container_width=True)
                                
                                # エクスポート機能
                                col1, col2 = st.columns(2)
                                with col1:
                                    csv = df.to_csv(index=False)
                                    st.download_button(
                                        label="📥 CSVダウンロード",
                                        data=csv,
                                        file_name=f"redis_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                with col2:
                                    json_str = df.to_json(orient="records", indent=2)
                                    st.download_button(
                                        label="📥 JSONダウンロード",
                                        data=json_str,
                                        file_name=f"redis_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                        mime="application/json"
                                    )
                            else:
                                st.info("データが取得できませんでした")
                                
                except redis.ConnectionError as e:
                    st.error(f"Redis接続エラー: {str(e)}")
                    st.info("Redisサーバーが起動していることを確認してください")
                    st.code("docker run -d -p 6379:6379 redis:latest", language="bash")
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
                    import traceback
                    if debug_mode:
                        st.code(traceback.format_exc())
    
    elif selected_server == "postgresql":
        # タブを作成
        tab1, tab2, tab3 = st.tabs(["📊 テーブル一覧", "📝 SQLクエリ", "🔍 テーブルデータ表示"])
        
        with tab1:
            st.subheader("テーブル一覧")
            if st.button("🔄 テーブル一覧を取得", key="fetch_tables"):
                with st.spinner("テーブル一覧を取得中..."):
                    # PostgreSQL接続を新規作成
                    pg_checker = ServerHealthChecker(debug_mode=debug_mode)
                    pg_result = pg_checker.check_postgresql()
                    
                    if pg_result[0]:
                        pg_fetcher = ServerDataFetcher(pg_checker)
                        # テーブル一覧を取得
                        table_query = """
                            SELECT 
                                schemaname as "Schema",
                                tablename as "Table",
                                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as "Size"
                            FROM pg_tables 
                            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                            ORDER BY schemaname, tablename
                        """
                        df_tables = pg_fetcher.fetch_postgresql_data(query=table_query)
                        
                        if not df_tables.empty and "Table" in df_tables.columns:
                            st.success(f"✅ {df_tables.shape[0]} 個のテーブルが見つかりました")
                            st.dataframe(df_tables, use_container_width=True)
                            # セッションステートにテーブルリストを保存
                            st.session_state['pg_tables'] = df_tables[['Schema', 'Table']].values.tolist()
                        else:
                            st.info("テーブルが見つかりませんでした")
                    else:
                        st.error(f"PostgreSQL接続エラー: {pg_result[1]}")
        
        with tab2:
            st.subheader("SQLクエリ")
            
            # まずテーブルリストを取得
            if 'pg_tables_for_query' not in st.session_state:
                if st.button("📋 テーブルリストを取得", key="get_tables_for_query"):
                    with st.spinner("テーブルリストを取得中..."):
                        pg_checker = ServerHealthChecker(debug_mode=debug_mode)
                        pg_result = pg_checker.check_postgresql()
                        
                        if pg_result[0]:
                            pg_fetcher = ServerDataFetcher(pg_checker)
                            table_query = """
                                SELECT schemaname, tablename 
                                FROM pg_tables 
                                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                                ORDER BY schemaname, tablename
                            """
                            df_tables = pg_fetcher.fetch_postgresql_data(query=table_query)
                            if not df_tables.empty:
                                st.session_state['pg_tables_for_query'] = df_tables.values.tolist()
                                st.rerun()
            
            # テーブル選択とクエリテンプレート
            if 'pg_tables_for_query' in st.session_state and st.session_state['pg_tables_for_query']:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # テーブル選択
                    table_options = ["カスタムクエリ"] + [f"{schema}.{table}" for schema, table in st.session_state['pg_tables_for_query']]
                    selected_table_for_query = st.selectbox(
                        "テーブルを選択（またはカスタムクエリ）",
                        options=table_options,
                        key="selected_table_for_query"
                    )
                
                with col2:
                    # クエリテンプレート選択
                    if selected_table_for_query != "カスタムクエリ":
                        query_templates = {
                            "すべて選択": f"SELECT * FROM {selected_table_for_query}",
                            "先頭10行": f"SELECT * FROM {selected_table_for_query} LIMIT 10",
                            "先頭100行": f"SELECT * FROM {selected_table_for_query} LIMIT 100",
                            "行数カウント": f"SELECT COUNT(*) as total_rows FROM {selected_table_for_query}",
                            "カラム情報": f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema || '.' || table_name = '{selected_table_for_query}'",
                            "最近追加されたレコード": f"SELECT * FROM {selected_table_for_query} ORDER BY id DESC LIMIT 10",
                            "ランダムサンプル": f"SELECT * FROM {selected_table_for_query} ORDER BY RANDOM() LIMIT 10",
                        }
                        
                        template = st.selectbox(
                            "クエリテンプレート",
                            options=list(query_templates.keys()),
                            key="query_template"
                        )
                        
                        # 選択されたテンプレートのクエリを設定
                        default_query = query_templates[template]
                    else:
                        default_query = "SELECT * FROM test_users LIMIT 10"
                
                # クエリエディタ
                query = st.text_area(
                    "SQLクエリ（編集可能）",
                    value=default_query if 'pg_tables_for_query' in st.session_state else "SELECT * FROM test_users LIMIT 10",
                    height=150,
                    key="pg_query_editor"
                )
                
                # 行数制限オプション
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    add_limit = st.checkbox("行数制限を追加", key="add_limit")
                with col2:
                    if add_limit:
                        limit_value = st.number_input("制限行数", min_value=1, max_value=10000, value=100, key="limit_value")
                        if "LIMIT" not in query.upper():
                            query = f"{query.rstrip(';')} LIMIT {limit_value}"
                
                # クエリ実行ボタン
                fetch_pg = st.button("🔍 クエリ実行", key="fetch_pg", type="primary")
                
                if fetch_pg:
                    with st.spinner("クエリを実行中..."):
                        # PostgreSQL接続を新規作成
                        pg_checker = ServerHealthChecker(debug_mode=debug_mode)
                        pg_result = pg_checker.check_postgresql()
                        
                        if pg_result[0]:
                            # 接続成功時にデータ取得
                            pg_fetcher = ServerDataFetcher(pg_checker)
                            
                            # クエリの実行時間を計測
                            import time
                            start_time = time.time()
                            df = pg_fetcher.fetch_postgresql_data(query=query)
                            execution_time = time.time() - start_time
                            
                            if not df.empty and "Error" not in df.columns and "Info" not in df.columns:
                                # 実行結果の統計
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("取得行数", f"{df.shape[0]:,}")
                                with col2:
                                    st.metric("列数", f"{df.shape[1]:,}")
                                with col3:
                                    st.metric("実行時間", f"{execution_time:.3f}秒")
                                with col4:
                                    # メモリ使用量（概算）
                                    memory_usage = df.memory_usage(deep=True).sum() / 1024 / 1024
                                    st.metric("データサイズ", f"{memory_usage:.2f} MB")
                                
                                # データ表示
                                st.dataframe(df, use_container_width=True, height=400)
                                
                                # データ分析セクション
                                with st.expander("📊 データ分析", expanded=False):
                                    # 数値列の統計
                                    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
                                    if len(numeric_cols) > 0:
                                        st.write("**数値列の統計:**")
                                        st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                                    
                                    # カラム情報
                                    col_info = pd.DataFrame({
                                        'カラム名': df.columns,
                                        'データ型': df.dtypes.astype(str),
                                        'NULL数': df.isnull().sum(),
                                        'ユニーク値数': [df[col].nunique() for col in df.columns],
                                        'サンプル値': [str(df[col].iloc[0]) if len(df) > 0 else 'N/A' for col in df.columns]
                                    })
                                    st.write("**カラム情報:**")
                                    st.dataframe(col_info, use_container_width=True)
                                
                                # エクスポート機能
                                st.divider()
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    csv = df.to_csv(index=False)
                                    st.download_button(
                                        label="📥 CSVダウンロード",
                                        data=csv,
                                        file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                with col2:
                                    json_str = df.to_json(orient="records", indent=2)
                                    st.download_button(
                                        label="📥 JSONダウンロード",
                                        data=json_str,
                                        file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                        mime="application/json"
                                    )
                                with col3:
                                    # クエリ自体も保存
                                    st.download_button(
                                        label="📥 SQLクエリ保存",
                                        data=query,
                                        file_name=f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
                                        mime="text/plain"
                                    )
                                    
                            elif "Info" in df.columns:
                                st.info(df.iloc[0]["Info"])
                            elif "Error" in df.columns:
                                st.error(f"クエリ実行エラー: {df.iloc[0]['Error']}")
                                st.code(query, language="sql")
                            else:
                                st.warning("データが見つかりませんでした")
                        else:
                            st.error(f"PostgreSQL接続エラー: {pg_result[1]}")
                            st.info("PostgreSQLサーバーが起動していることを確認してください")
                            st.code("docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:latest", language="bash")
            else:
                st.info("まず「テーブルリストを取得」ボタンをクリックしてください")
        
        with tab3:
            st.subheader("テーブルデータ表示")
            
            # まずテーブルリストを取得
            if 'pg_tables' not in st.session_state:
                if st.button("📋 テーブルリストを取得", key="get_table_list"):
                    with st.spinner("テーブルリストを取得中..."):
                        pg_checker = ServerHealthChecker(debug_mode=debug_mode)
                        pg_result = pg_checker.check_postgresql()
                        
                        if pg_result[0]:
                            pg_fetcher = ServerDataFetcher(pg_checker)
                            table_query = """
                                SELECT schemaname, tablename 
                                FROM pg_tables 
                                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                                ORDER BY schemaname, tablename
                            """
                            df_tables = pg_fetcher.fetch_postgresql_data(query=table_query)
                            if not df_tables.empty:
                                st.session_state['pg_tables'] = df_tables.values.tolist()
                                st.rerun()
            
            # テーブル選択とデータ表示
            if 'pg_tables' in st.session_state and st.session_state['pg_tables']:
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    # テーブル選択
                    table_options = [f"{schema}.{table}" for schema, table in st.session_state['pg_tables']]
                    selected_table = st.selectbox(
                        "テーブルを選択",
                        options=table_options,
                        key="selected_pg_table"
                    )
                
                with col2:
                    # 行数制限
                    row_limit = st.number_input(
                        "表示行数",
                        min_value=1,
                        max_value=10000,
                        value=100,
                        key="pg_row_limit"
                    )
                
                with col3:
                    # データ取得ボタン
                    fetch_table_data = st.button("📊 データ表示", key="fetch_table_data")
                
                if fetch_table_data and selected_table:
                    with st.spinner(f"{selected_table} のデータを取得中..."):
                        # PostgreSQL接続を新規作成
                        pg_checker = ServerHealthChecker(debug_mode=debug_mode)
                        pg_result = pg_checker.check_postgresql()
                        
                        if pg_result[0]:
                            pg_fetcher = ServerDataFetcher(pg_checker)
                            
                            # 選択されたテーブルからデータを取得
                            data_query = f"SELECT * FROM {selected_table} LIMIT {row_limit}"
                            df_data = pg_fetcher.fetch_postgresql_data(query=data_query)
                            
                            if not df_data.empty and "Error" not in df_data.columns:
                                # テーブル情報を表示
                                st.success(f"✅ {selected_table} から {df_data.shape[0]} 行を取得")
                                
                                # データの統計情報
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("行数", df_data.shape[0])
                                with col2:
                                    st.metric("列数", df_data.shape[1])
                                with col3:
                                    # 総行数を取得
                                    count_query = f"SELECT COUNT(*) as total FROM {selected_table}"
                                    df_count = pg_fetcher.fetch_postgresql_data(query=count_query)
                                    if not df_count.empty:
                                        total_rows = df_count.iloc[0]['total']
                                        st.metric("総行数", total_rows)
                                
                                # データを表示
                                st.dataframe(df_data, use_container_width=True)
                                
                                # カラム情報を表示
                                with st.expander("📋 カラム情報"):
                                    col_info = pd.DataFrame({
                                        'カラム名': df_data.columns,
                                        'データ型': df_data.dtypes.astype(str),
                                        'NULL以外の値': df_data.count(),
                                        'ユニーク値数': [df_data[col].nunique() for col in df_data.columns]
                                    })
                                    st.dataframe(col_info, use_container_width=True)
                                
                                # エクスポート機能
                                st.divider()
                                col1, col2 = st.columns(2)
                                with col1:
                                    csv = df_data.to_csv(index=False)
                                    st.download_button(
                                        label=f"📥 {selected_table} CSVダウンロード",
                                        data=csv,
                                        file_name=f"{selected_table.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                with col2:
                                    json_str = df_data.to_json(orient="records", indent=2)
                                    st.download_button(
                                        label=f"📥 {selected_table} JSONダウンロード",
                                        data=json_str,
                                        file_name=f"{selected_table.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                        mime="application/json"
                                    )
                            elif "Error" in df_data.columns:
                                st.error(f"データ取得エラー: {df_data.iloc[0]['Error']}")
                            else:
                                st.warning("データが見つかりませんでした")
                        else:
                            st.error(f"PostgreSQL接続エラー: {pg_result[1]}")
            else:
                st.info("まず「テーブルリストを取得」ボタンをクリックしてください")
    
    elif selected_server == "elasticsearch":
        # タブを作成
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 インデックス一覧", 
            "🔍 ドキュメント検索",
            "📈 クラスタ統計",
            "🔧 詳細分析"
        ])
        
        with tab1:
            st.subheader("インデックス一覧と詳細")
            
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                index_pattern = st.text_input("インデックスパターン", value="*", key="es_index_pattern")
            with col2:
                show_system = st.checkbox("システムインデックスを含む", key="show_system_indices")
            with col3:
                fetch_indices = st.button("🔄 インデックス取得", key="fetch_indices")
            
            if fetch_indices:
                with st.spinner("インデックス情報を取得中..."):
                    es_checker = ServerHealthChecker(debug_mode=debug_mode)
                    es_result = es_checker.check_elasticsearch()
                    
                    if es_result[0]:
                        es = es_checker.connection_cache["elasticsearch"]
                        
                        try:
                            # インデックス一覧を取得
                            indices = es.indices.get_alias(index=index_pattern)
                            
                            # インデックス情報を整理
                            index_data = []
                            for idx_name, idx_info in indices.items():
                                # システムインデックスのフィルタリング
                                if not show_system and (idx_name.startswith('.') or idx_name.startswith('_')):
                                    continue
                                
                                # 統計情報を取得
                                stats = es.indices.stats(index=idx_name)
                                idx_stats = stats["indices"][idx_name]["total"]
                                
                                # マッピング情報を取得
                                mappings = es.indices.get_mapping(index=idx_name)
                                field_count = 0
                                if idx_name in mappings and "mappings" in mappings[idx_name]:
                                    properties = mappings[idx_name]["mappings"].get("properties", {})
                                    field_count = len(properties)
                                
                                # 設定情報を取得
                                settings = es.indices.get_settings(index=idx_name)
                                shards = settings[idx_name]["settings"]["index"].get("number_of_shards", "N/A")
                                replicas = settings[idx_name]["settings"]["index"].get("number_of_replicas", "N/A")
                                
                                index_data.append({
                                    "インデックス名": idx_name,
                                    "ドキュメント数": f"{idx_stats['docs']['count']:,}",
                                    "削除済み": f"{idx_stats['docs'].get('deleted', 0):,}",
                                    "サイズ": f"{idx_stats['store']['size_in_bytes'] / 1024 / 1024:.2f} MB",
                                    "フィールド数": field_count,
                                    "シャード数": shards,
                                    "レプリカ数": replicas,
                                    "エイリアス": ", ".join(idx_info.get("aliases", {}).keys()) or "なし"
                                })
                            
                            if index_data:
                                df_indices = pd.DataFrame(index_data)
                                st.success(f"✅ {len(df_indices)} 個のインデックスが見つかりました")
                                
                                # インデックス一覧を表示
                                st.dataframe(df_indices, use_container_width=True, height=400)
                                
                                # インデックスリストをセッションステートに保存
                                st.session_state['es_indices'] = df_indices["インデックス名"].tolist()
                                
                                # エクスポート機能
                                col1, col2 = st.columns(2)
                                with col1:
                                    csv = df_indices.to_csv(index=False)
                                    st.download_button(
                                        label="📥 CSVダウンロード",
                                        data=csv,
                                        file_name=f"es_indices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                with col2:
                                    json_str = df_indices.to_json(orient="records", indent=2)
                                    st.download_button(
                                        label="📥 JSONダウンロード",
                                        data=json_str,
                                        file_name=f"es_indices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                        mime="application/json"
                                    )
                            else:
                                st.info("インデックスが見つかりませんでした")
                        except Exception as e:
                            st.error(f"エラー: {str(e)}")
                    else:
                        st.error(f"Elasticsearch接続エラー: {es_result[1]}")
        
        with tab2:
            st.subheader("ドキュメント検索と表示")
            
            # インデックス選択
            if 'es_indices' not in st.session_state:
                st.info("まず「インデックス一覧」タブでインデックスを取得してください")
            else:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    selected_index = st.selectbox(
                        "インデックスを選択",
                        options=st.session_state['es_indices'],
                        key="selected_es_index"
                    )
                
                with col2:
                    doc_limit = st.number_input(
                        "取得件数",
                        min_value=1,
                        max_value=1000,
                        value=10,
                        key="es_doc_limit"
                    )
                
                # 検索クエリ
                search_query = st.text_area(
                    "検索クエリ（JSONフォーマット）※空白の場合は全件取得",
                    value='{\n  "match_all": {}\n}',
                    height=100,
                    key="es_search_query"
                )
                
                # 検索実行
                if st.button("🔍 ドキュメント検索", key="search_docs"):
                    with st.spinner("ドキュメントを検索中..."):
                        es_checker = ServerHealthChecker(debug_mode=debug_mode)
                        es_result = es_checker.check_elasticsearch()
                        
                        if es_result[0]:
                            es = es_checker.connection_cache["elasticsearch"]
                            
                            try:
                                # クエリをパース
                                import json
                                if search_query.strip():
                                    query = json.loads(search_query)
                                else:
                                    query = {"match_all": {}}
                                
                                # 検索実行
                                response = es.search(
                                    index=selected_index,
                                    query=query,
                                    size=doc_limit
                                )
                                
                                # 結果を処理
                                hits = response["hits"]["hits"]
                                total = response["hits"]["total"]["value"]
                                
                                st.success(f"✅ {total:,} 件中 {len(hits)} 件を表示")
                                
                                # ドキュメントを表形式で表示
                                if hits:
                                    # データを整形
                                    docs_data = []
                                    for hit in hits:
                                        doc = {
                                            "_id": hit["_id"],
                                            "_score": hit.get("_score", "N/A")
                                        }
                                        # _sourceフィールドをフラット化
                                        source = hit.get("_source", {})
                                        for key, value in source.items():
                                            # 長い文字列は切り詰め
                                            if isinstance(value, str) and len(value) > 100:
                                                doc[key] = value[:100] + "..."
                                            elif isinstance(value, (dict, list)):
                                                doc[key] = json.dumps(value, ensure_ascii=False)[:100] + "..."
                                            else:
                                                doc[key] = value
                                        docs_data.append(doc)
                                    
                                    df_docs = pd.DataFrame(docs_data)
                                    st.dataframe(df_docs, use_container_width=True, height=400)
                                    
                                    # 詳細表示（エキスパンダー）
                                    with st.expander("📝 ドキュメント詳細（JSON形式）"):
                                        for i, hit in enumerate(hits[:5], 1):  # 最初の5件のみ
                                            st.write(f"**ドキュメント {i} (ID: {hit['_id']})**")
                                            st.json(hit["_source"])
                                            if i < min(5, len(hits)):
                                                st.divider()
                                    
                                    # エクスポート
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        csv = df_docs.to_csv(index=False)
                                        st.download_button(
                                            label="📥 CSVダウンロード",
                                            data=csv,
                                            file_name=f"{selected_index}_docs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                            mime="text/csv"
                                        )
                                    with col2:
                                        json_str = json.dumps(hits, ensure_ascii=False, indent=2)
                                        st.download_button(
                                            label="📥 JSONダウンロード",
                                            data=json_str,
                                            file_name=f"{selected_index}_docs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                            mime="application/json"
                                        )
                                else:
                                    st.info("ドキュメントが見つかりませんでした")
                                    
                            except json.JSONDecodeError:
                                st.error("検索クエリのJSON形式が不正です")
                            except Exception as e:
                                st.error(f"検索エラー: {str(e)}")
                        else:
                            st.error(f"Elasticsearch接続エラー: {es_result[1]}")
        
        with tab3:
            st.subheader("クラスタ統計情報")
            
            if st.button("📊 統計情報を取得", key="get_cluster_stats"):
                with st.spinner("クラスタ情報を取得中..."):
                    es_checker = ServerHealthChecker(debug_mode=debug_mode)
                    es_result = es_checker.check_elasticsearch()
                    
                    if es_result[0]:
                        es = es_checker.connection_cache["elasticsearch"]
                        
                        try:
                            # クラスタヘルス
                            health = es.cluster.health()
                            
                            # クラスタ統計
                            stats = es.cluster.stats()
                            
                            # ノード情報
                            nodes = es.nodes.info()
                            
                            # クラスタ状態を表示
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                status_color = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
                                st.metric("クラスタ状態", f"{status_color.get(health['status'], '⚪')} {health['status'].upper()}")
                            
                            with col2:
                                st.metric("ノード数", f"{health['number_of_nodes']:,}")
                            
                            with col3:
                                st.metric("データノード数", f"{health['number_of_data_nodes']:,}")
                            
                            with col4:
                                st.metric("アクティブシャード", f"{health['active_shards']:,}")
                            
                            # 詳細統計
                            st.divider()
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**インデックス統計:**")
                                st.write(f"• 総インデックス数: {stats['indices']['count']:,}")
                                st.write(f"• 総ドキュメント数: {stats['indices']['docs']['count']:,}")
                                st.write(f"• 総データサイズ: {stats['indices']['store']['size_in_bytes'] / 1024 / 1024 / 1024:.2f} GB")
                                st.write(f"• 総フィールド数: {stats['indices']['mappings']['field_types'][0]['count'] if stats['indices']['mappings']['field_types'] else 0:,}")
                            
                            with col2:
                                st.write("**ノード情報:**")
                                for node_id, node_info in nodes['nodes'].items():
                                    st.write(f"• ノード名: {node_info['name']}")
                                    st.write(f"  - バージョン: {node_info['version']}")
                                    st.write(f"  - ロール: {', '.join(node_info.get('roles', []))}")
                                    break  # 最初のノードのみ表示
                            
                            # JVMメモリ情報
                            if 'jvm' in stats['nodes']:
                                st.divider()
                                st.write("**JVMメモリ使用状況:**")
                                jvm = stats['nodes']['jvm']['mem']
                                heap_used = jvm['heap_used_in_bytes'] / 1024 / 1024
                                heap_max = jvm['heap_max_in_bytes'] / 1024 / 1024
                                st.progress(heap_used / heap_max, text=f"ヒープ使用率: {heap_used:.1f} MB / {heap_max:.1f} MB ({heap_used/heap_max*100:.1f}%)")
                            
                        except Exception as e:
                            st.error(f"統計情報取得エラー: {str(e)}")
                    else:
                        st.error(f"Elasticsearch接続エラー: {es_result[1]}")
        
        with tab4:
            st.subheader("インデックス詳細分析")
            
            if 'es_indices' not in st.session_state:
                st.info("まず「インデックス一覧」タブでインデックスを取得してください")
            else:
                selected_index_detail = st.selectbox(
                    "分析するインデックスを選択",
                    options=st.session_state['es_indices'],
                    key="selected_index_detail"
                )
                
                if st.button("🔬 詳細分析", key="analyze_index"):
                    with st.spinner(f"{selected_index_detail} を分析中..."):
                        es_checker = ServerHealthChecker(debug_mode=debug_mode)
                        es_result = es_checker.check_elasticsearch()
                        
                        if es_result[0]:
                            es = es_checker.connection_cache["elasticsearch"]
                            
                            try:
                                # マッピング情報
                                mappings = es.indices.get_mapping(index=selected_index_detail)
                                
                                # 設定情報
                                settings = es.indices.get_settings(index=selected_index_detail)
                                
                                # フィールド統計
                                field_caps = es.field_caps(index=selected_index_detail, fields="*")
                                
                                # マッピング表示
                                st.write("**📋 フィールドマッピング:**")
                                if selected_index_detail in mappings:
                                    properties = mappings[selected_index_detail]["mappings"].get("properties", {})
                                    
                                    field_data = []
                                    for field_name, field_info in properties.items():
                                        field_data.append({
                                            "フィールド名": field_name,
                                            "タイプ": field_info.get("type", "N/A"),
                                            "インデックス": field_info.get("index", True),
                                            "アナライザー": field_info.get("analyzer", "standard")
                                        })
                                    
                                    if field_data:
                                        df_fields = pd.DataFrame(field_data)
                                        st.dataframe(df_fields, use_container_width=True)
                                
                                # 設定表示
                                with st.expander("⚙️ インデックス設定"):
                                    index_settings = settings[selected_index_detail]["settings"]["index"]
                                    st.json({
                                        "作成日": index_settings.get("creation_date", "N/A"),
                                        "UUID": index_settings.get("uuid", "N/A"),
                                        "シャード数": index_settings.get("number_of_shards", "N/A"),
                                        "レプリカ数": index_settings.get("number_of_replicas", "N/A"),
                                        "リフレッシュ間隔": index_settings.get("refresh_interval", "N/A")
                                    })
                                
                                # サンプルデータ取得
                                st.divider()
                                st.write("**📝 サンプルドキュメント (最新5件):**")
                                
                                sample_response = es.search(
                                    index=selected_index_detail,
                                    size=5,
                                    sort="_doc"
                                )
                                
                                for i, hit in enumerate(sample_response["hits"]["hits"], 1):
                                    with st.expander(f"ドキュメント {i} (ID: {hit['_id']})"):
                                        st.json(hit["_source"])
                                
                            except Exception as e:
                                st.error(f"分析エラー: {str(e)}")
    
    elif selected_server == "qdrant":
        # コレクション概要表示
        st.subheader("📚 コレクション一覧")
        
        # Qdrantクライアントの再接続（データ取得のため）
        try:
            if not QDRANT_AVAILABLE:
                st.warning("Qdrant clientがインストールされていません。")
                st.code("pip install qdrant-client", language="bash")
            else:
                # 直接Qdrantクライアントを作成して接続
                from qdrant_client import QdrantClient
                qdrant_config = SERVER_CONFIG["qdrant"]
                client = QdrantClient(url=qdrant_config["url"], timeout=5)
                
                # コレクション一覧を自動取得
                try:
                    collections = client.get_collections()
                    if collections.collections:
                        collection_names = [c.name for c in collections.collections]
                        st.session_state['qdrant_collections'] = collection_names
                        
                        # コレクション情報をDataFrame化
                        data = []
                        for collection in collections.collections:
                            try:
                                info = client.get_collection(collection.name)
                                data.append({
                                    "Collection": collection.name,
                                    "Vectors Count": info.vectors_count,
                                    "Points Count": info.points_count,
                                    "Indexed Vectors": info.indexed_vectors_count,
                                    "Status": info.status
                                })
                            except Exception as e:
                                data.append({
                                    "Collection": collection.name,
                                    "Vectors Count": "N/A",
                                    "Points Count": "N/A",
                                    "Indexed Vectors": "N/A",
                                    "Status": f"Error: {str(e)[:50]}"
                                })
                        
                        if data:
                            df = pd.DataFrame(data)
                            st.dataframe(df, use_container_width=True)
                            
                            # エクスポート機能
                            col1, col2 = st.columns(2)
                            with col1:
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="📥 CSVダウンロード",
                                    data=csv,
                                    file_name=f"qdrant_collections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv"
                                )
                            with col2:
                                json_str = df.to_json(orient="records", indent=2)
                                st.download_button(
                                    label="📥 JSONダウンロード",
                                    data=json_str,
                                    file_name=f"qdrant_collections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                    mime="application/json"
                                )
                    else:
                        st.info("コレクションが見つかりません")
                        
                except Exception as e:
                    st.error(f"コレクション一覧の取得に失敗: {str(e)}")
                    st.info("Qdrantサーバーが起動していることを確認してください")
                    st.code("docker run -p 6333:6333 qdrant/qdrant", language="bash")
                    
        except Exception as e:
            st.error(f"Qdrant接続エラー: {str(e)}")
        
        # コレクション詳細表示
        st.divider()
        st.subheader("🔍 コレクション詳細データ")
        
        # セッションステートからコレクション一覧を取得
        if 'qdrant_collections' in st.session_state and st.session_state['qdrant_collections']:
            selected_collection = st.selectbox(
                "詳細を表示するコレクションを選択",
                options=st.session_state['qdrant_collections'],
                key="selected_collection"
            )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                limit = st.number_input("表示件数", min_value=1, max_value=500, value=50, key="qdrant_limit")
            with col2:
                show_details = st.button("📊 詳細情報を表示", key="show_collection_details")
            with col3:
                fetch_points = st.button("🔍 ポイントデータを取得", key="fetch_collection_points")
            
            # コレクション詳細情報の表示
            if show_details and QDRANT_AVAILABLE:
                with st.spinner(f"{selected_collection} の詳細情報を取得中..."):
                    try:
                        # 直接クライアントを使用
                        info = client.get_collection(selected_collection)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("ベクトル数", info.vectors_count)
                        with col2:
                            st.metric("ポイント数", info.points_count)
                        with col3:
                            st.metric("インデックス済み", info.indexed_vectors_count)
                        with col4:
                            st.metric("ステータス", info.status)
                        
                        # 設定情報
                        st.write("**ベクトル設定:**")
                        try:
                            vector_config = info.config.params.vectors
                            if hasattr(vector_config, 'size'):
                                st.write(f"  • ベクトル次元: {vector_config.size}")
                                st.write(f"  • 距離計算: {vector_config.distance}")
                            else:
                                st.write(f"  • 設定: {vector_config}")
                        except:
                            st.write("  • ベクトル設定情報を取得できません")
                            
                    except Exception as e:
                        st.error(f"エラー: {str(e)}")
            
            # ポイントデータの表示
            if fetch_points and QDRANT_AVAILABLE:
                with st.spinner(f"{selected_collection} のポイントデータを取得中..."):
                    try:
                        # スクロールを使ってポイントを取得
                        points_result = client.scroll(
                            collection_name=selected_collection,
                            limit=limit,
                            with_payload=True,
                            with_vectors=False
                        )
                        
                        points = points_result[0]  # scrollは (points, next_offset) のタプルを返す
                        
                        if points:
                            # ポイントをDataFrameに変換
                            data = []
                            for point in points:
                                row = {"ID": point.id}
                                
                                # payloadの各フィールドを列として追加
                                if point.payload:
                                    for key, value in point.payload.items():
                                        # 長すぎる文字列は切り詰め
                                        if isinstance(value, str) and len(value) > 200:
                                            row[key] = value[:200] + '...'
                                        elif isinstance(value, (list, dict)):
                                            row[key] = str(value)[:200] + '...' if len(str(value)) > 200 else str(value)
                                        else:
                                            row[key] = value
                                
                                data.append(row)
                            
                            if data:
                                df_points = pd.DataFrame(data)
                                st.write(f"**{selected_collection} のデータサンプル ({len(df_points)} 件):**")
                                st.dataframe(df_points, use_container_width=True)
                                
                                # エクスポート機能
                                col1, col2 = st.columns(2)
                                with col1:
                                    csv = df_points.to_csv(index=False)
                                    st.download_button(
                                        label="📥 ポイントデータ CSVダウンロード",
                                        data=csv,
                                        file_name=f"{selected_collection}_points_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                with col2:
                                    json_str = df_points.to_json(orient="records", indent=2)
                                    st.download_button(
                                        label="📥 ポイントデータ JSONダウンロード",
                                        data=json_str,
                                        file_name=f"{selected_collection}_points_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                        mime="application/json"
                                    )
                        else:
                            st.info("ポイントデータが見つかりません")
                            
                    except Exception as e:
                        st.error(f"ポイントデータ取得エラー: {str(e)}")
        else:
            st.info("コレクションが見つかりません。Qdrantサーバーが起動していることを確認してください。")
    
    # フッター
    st.divider()
    st.caption(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # デバッグ情報表示
    if debug_mode:
        with st.expander("🐛 デバッグ情報", expanded=False):
            st.subheader("インストール済みクライアント")
            st.write({
                "Redis": "✅" if REDIS_AVAILABLE else "❌",
                "PostgreSQL": "✅" if POSTGRESQL_AVAILABLE else "❌",
                "Elasticsearch": "✅" if ELASTICSEARCH_AVAILABLE else "❌",
                "Qdrant": "✅" if QDRANT_AVAILABLE else "❌",
                "psutil": "✅" if PSUTIL_AVAILABLE else "❌"
            })
            
            st.subheader("サーバー設定")
            st.json(SERVER_CONFIG)
            
            st.subheader("接続キャッシュ")
            st.write(list(checker.connection_cache.keys()) if 'checker' in locals() else [])

if __name__ == "__main__":
    main()