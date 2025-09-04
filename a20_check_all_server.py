#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
a20_check_all_server.py - データベースサーバー統合監視ツール
=============================================================
起動: streamlit run a20_check_all_server.py --server.port=8502

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
            es = Elasticsearch(
                [f"{config['scheme']}://{config['host']}:{config['port']}"],
                request_timeout=5,
                verify_certs=False,
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
            
            df = pd.read_sql_query(query, conn)
            return df if not df.empty else pd.DataFrame({"Info": ["No data found"]})
            
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
                df = data_fetcher.fetch_redis_data(pattern=pattern, limit=limit)
                st.dataframe(df, use_container_width=True)
                
                # エクスポート機能
                if not df.empty and "Error" not in df.columns:
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
    
    elif selected_server == "postgresql":
        query = st.text_area(
            "SQLクエリ",
            value="SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public' LIMIT 10",
            height=100,
            key="pg_query"
        )
        fetch_pg = st.button("🔍 クエリ実行", key="fetch_pg")
        
        if fetch_pg:
            with st.spinner("PostgreSQLデータ取得中..."):
                df = data_fetcher.fetch_postgresql_data(query=query)
                st.dataframe(df, use_container_width=True)
                
                # エクスポート機能
                if not df.empty and "Error" not in df.columns:
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 CSVダウンロード",
                            data=csv,
                            file_name=f"postgresql_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    with col2:
                        json_str = df.to_json(orient="records", indent=2)
                        st.download_button(
                            label="📥 JSONダウンロード",
                            data=json_str,
                            file_name=f"postgresql_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
    
    elif selected_server == "elasticsearch":
        col1, col2 = st.columns([3, 1])
        with col1:
            index_pattern = st.text_input("インデックスパターン", value="*", key="es_index")
        with col2:
            fetch_es = st.button("🔍 データ取得", key="fetch_es")
        
        if fetch_es:
            with st.spinner("Elasticsearchデータ取得中..."):
                df = data_fetcher.fetch_elasticsearch_data(index=index_pattern)
                st.dataframe(df, use_container_width=True)
                
                # エクスポート機能
                if not df.empty and "Error" not in df.columns:
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 CSVダウンロード",
                            data=csv,
                            file_name=f"elasticsearch_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    with col2:
                        json_str = df.to_json(orient="records", indent=2)
                        st.download_button(
                            label="📥 JSONダウンロード",
                            data=json_str,
                            file_name=f"elasticsearch_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
    
    elif selected_server == "qdrant":
        fetch_qdrant = st.button("🔍 コレクション取得", key="fetch_qdrant")
        
        if fetch_qdrant:
            with st.spinner("Qdrantデータ取得中..."):
                df = data_fetcher.fetch_qdrant_data()
                st.dataframe(df, use_container_width=True)
                
                # エクスポート機能
                if not df.empty and "Error" not in df.columns:
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 CSVダウンロード",
                            data=csv,
                            file_name=f"qdrant_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    with col2:
                        json_str = df.to_json(orient="records", indent=2)
                        st.download_button(
                            label="📥 JSONダウンロード",
                            data=json_str,
                            file_name=f"qdrant_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
    
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