# streamlit run mcp_qdrant_show.py --server.port=8501
# Qdrantデータ専用の表示アプリ
# streamlit run mcp_qdrant_show.py --server.port=8501

import streamlit as st
import requests
import pandas as pd
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any, List


def safe_get_secret(key: str, default: Any = None) -> Any:
    """Streamlit secretsから安全に値を取得"""
    try:
        return st.secrets.get(key, default)
    except Exception:
        return os.getenv(key, default)


class QdrantManager:
    """Qdrant管理クラス"""

    def __init__(self):
        self.name = "Qdrant"
        self.url = safe_get_secret('QDRANT_URL', os.getenv('QDRANT_URL', 'http://localhost:6333'))

    def check_connection(self) -> Dict[str, str]:
        """Qdrant接続状態をチェック"""
        try:
            response = requests.get(f'{self.url}/', timeout=3)
            if response.status_code == 200:
                return {"status": "🟢 接続OK", "details": "正常"}
            else:
                return {"status": f"🔴 接続NG", "details": f"Status: {response.status_code}"}
        except Exception as e:
            return {"status": f"🔴 接続NG", "details": str(e)[:50]}

    def get_data_summary(self) -> Dict[str, Any]:
        """Qdrantデータの概要取得"""
        try:
            response = requests.get(f'{self.url}/collections', timeout=3)
            if response.status_code == 200:
                collections = response.json().get('result', {}).get('collections', [])
                return {
                    "collection_count": len(collections),
                    "collections": [col['name'] for col in collections],
                    "status": "complete"
                }
            return {"collection_count": "?", "status": "error"}
        except Exception:
            return {"collection_count": "?", "status": "error"}

    def get_all_collections_data(self) -> Dict[str, Any]:
        """全コレクションのデータを取得"""
        try:
            # コレクション一覧を取得
            response = requests.get(f'{self.url}/collections', timeout=5)
            if response.status_code != 200:
                return {"error": "コレクション一覧の取得に失敗"}

            collections_data = response.json()
            collections = collections_data.get('result', {}).get('collections', [])
            
            if not collections:
                return {"message": "コレクションが見つかりません"}

            all_data = {}

            for collection in collections:
                collection_name = collection['name']
                collection_info = {}

                # コレクションの詳細情報を取得
                detail_response = requests.get(
                    f'{self.url}/collections/{collection_name}',
                    timeout=5
                )
                
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    result = detail_data.get('result', {})
                    config = result.get('config', {})
                    
                    collection_info['details'] = {
                        'ベクトル数': result.get('points_count', 0),
                        'ベクトル次元': config.get('params', {}).get('vectors', {}).get('size', 'N/A'),
                        '距離計算': config.get('params', {}).get('vectors', {}).get('distance', 'N/A'),
                        'ステータス': result.get('status', 'unknown')
                    }

                    # ポイントデータを取得
                    points_response = requests.post(
                        f'{self.url}/collections/{collection_name}/points/scroll',
                        json={"limit": 50, "with_payload": True, "with_vector": False},
                        headers={'Content-Type': 'application/json'},
                        timeout=5
                    )

                    if points_response.status_code == 200:
                        points_data = points_response.json()
                        points = points_data.get('result', {}).get('points', [])
                        collection_info['points'] = points
                    else:
                        collection_info['points'] = []

                all_data[collection_name] = collection_info

            # クラスター情報も取得
            try:
                cluster_response = requests.get(f'{self.url}/cluster', timeout=5)
                if cluster_response.status_code == 200:
                    all_data['_cluster_info'] = cluster_response.json()
            except:
                pass

            # telemetry情報も取得
            try:
                telemetry_response = requests.get(f'{self.url}/telemetry', timeout=5)
                if telemetry_response.status_code == 200:
                    all_data['_telemetry'] = telemetry_response.json()
            except:
                pass

            return all_data

        except Exception as e:
            return {"error": f"データ取得エラー: {e}"}


def render_qdrant_data(qdrant_manager: QdrantManager):
    """Qdrantデータの表示"""
    st.header("🟠 Qdrant データ表示")
    
    # 接続状態チェック
    status = qdrant_manager.check_connection()
    
    if "🔴" in status["status"]:
        st.error(f"Qdrantサーバーに接続できません: {status['details']}")
        st.info("Qdrantサーバーを起動してください: docker-compose -f docker-compose/docker-compose.mcp-demo.yml up -d qdrant")
        return

    st.success(f"接続状態: {status['status']}")
    
    # データ概要
    summary = qdrant_manager.get_data_summary()
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("コレクション数", summary.get('collection_count', '?'))
    
    with col2:
        if summary.get('collections'):
            st.write("**コレクション一覧:**")
            for collection in summary['collections']:
                st.write(f"• {collection}")

    st.markdown("---")

    # 全データ取得・表示
    if st.button("🔍 全コレクションデータを表示", key="show_all_qdrant_data"):
        with st.spinner("全コレクションデータを取得中..."):
            all_data = qdrant_manager.get_all_collections_data()
            
            if 'error' in all_data:
                st.error(all_data['error'])
                return
            
            if 'message' in all_data:
                st.info(all_data['message'])
                return

            # 各コレクションのデータを表示
            for collection_name, collection_data in all_data.items():
                if collection_name.startswith('_'):  # システム情報はスキップ
                    continue
                    
                st.subheader(f"📚 コレクション: {collection_name}")
                
                # コレクション詳細情報
                if 'details' in collection_data:
                    col1, col2, col3, col4 = st.columns(4)
                    details = collection_data['details']
                    
                    with col1:
                        st.metric("ベクトル数", details.get('ベクトル数', 'N/A'))
                    with col2:
                        st.metric("ベクトル次元", details.get('ベクトル次元', 'N/A'))
                    with col3:
                        st.write(f"**距離計算:** {details.get('距離計算', 'N/A')}")
                    with col4:
                        st.write(f"**ステータス:** {details.get('ステータス', 'N/A')}")

                # ポイントデータ
                if 'points' in collection_data and collection_data['points']:
                    st.write(f"**🔍 データサンプル ({len(collection_data['points'])} 件):**")
                    
                    # ポイントをDataFrameに変換
                    points_data = []
                    for point in collection_data['points']:
                        row = {'ID': point.get('id', 'N/A')}
                        payload = point.get('payload', {})
                        
                        # payloadの各フィールドを列として追加
                        for key, value in payload.items():
                            # 長すぎる文字列は切り詰め
                            if isinstance(value, str) and len(value) > 100:
                                row[key] = value[:100] + '...'
                            else:
                                row[key] = value
                        
                        points_data.append(row)
                    
                    if points_data:
                        df = pd.DataFrame(points_data)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("データが空です")
                else:
                    st.info("ポイントデータがありません")
                
                st.markdown("---")

            # システム情報の表示
            if '_cluster_info' in all_data:
                with st.expander("🏥 クラスター情報", expanded=False):
                    cluster_info = all_data['_cluster_info']
                    result = cluster_info.get('result', {})
                    cluster_status = result.get('status')
                    
                    if cluster_status == 'disabled':
                        st.info("クラスター機能は無効です（単一ノード構成）")
                        st.write(f"**構成モード:** スタンドアローン")
                    elif cluster_status == 'enabled' or 'peers' in result:
                        col1, col2 = st.columns(2)
                        with col1:
                            peers = result.get('peers', [])
                            st.write(f"**ピア数:** {len(peers)}")
                            st.write(f"**ローカルピアID:** {result.get('peer_id', 'N/A')}")
                        with col2:
                            consensus_thread = result.get('consensus_thread_status', {})
                            st.write(f"**リーダー:** {consensus_thread.get('is_leader', False)}")
                            st.write(f"**クラスター状態:** {cluster_status or '有効'}")
                    else:
                        st.warning(f"不明なクラスター状態: {cluster_status}")
                    
                    st.json(cluster_info)

            if '_telemetry' in all_data:
                with st.expander("📊 Telemetry情報", expanded=False):
                    telemetry = all_data['_telemetry']
                    telemetry_result = telemetry.get('result', {})
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**ノードID:** {telemetry_result.get('id', 'N/A')}")
                        collections_count = len(telemetry_result.get('collections', {}))
                        st.write(f"**コレクション数:** {collections_count}")
                    with col2:
                        app_info = telemetry_result.get('app', {})
                        st.write(f"**バージョン:** {app_info.get('version', 'N/A')}")
                        st.write(f"**名前:** {app_info.get('name', 'N/A')}")
                    
                    st.json(telemetry)


def main():
    """メインアプリケーション"""
    load_dotenv()

    st.set_page_config(
        page_title="Qdrant データ表示",
        page_icon="🟠",
        layout="wide"
    )

    st.markdown("# 🟠 Qdrant データ表示アプリ")
    st.markdown("docker-compose起動後: `streamlit run mcp_qdrant_show.py --server.port=8501`")
    st.markdown("---")

    # カスタムCSS
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .status-good {
            color: #28a745;
            font-weight: bold;
        }
        .status-bad {
            color: #dc3545;
            font-weight: bold;
        }
        .info-box {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #17a2b8;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # QdrantManager インスタンス作成
    qdrant_manager = QdrantManager()

    # サイドバー情報
    with st.sidebar:
        st.header("📊 Qdrant 情報")
        
        # 更新ボタン
        if st.button("🔄 データ更新"):
            st.cache_data.clear()
            st.rerun()
        
        # 接続状態
        status = qdrant_manager.check_connection()
        st.markdown(f"**接続状態**: {status['status']}")
        if status['details']:
            st.markdown(f"**詳細**: {status['details']}")
        
        # 概要情報
        summary = qdrant_manager.get_data_summary()
        if summary.get('status') == 'complete':
            st.markdown(f"**コレクション数**: {summary.get('collection_count', '?')}")
            if summary.get('collections'):
                st.markdown("**コレクション:**")
                for collection in summary['collections']:
                    st.markdown(f"• {collection}")

        st.markdown("---")
        st.markdown("### 💡 使い方")
        st.markdown("1. Qdrantサーバーを起動")
        st.markdown("2. '全コレクションデータを表示' ボタンをクリック")
        st.markdown("3. 各コレクションの詳細データを確認")

    # メインコンテンツ
    render_qdrant_data(qdrant_manager)

    # フッター
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p><strong>🟠 Qdrant Data Viewer</strong> - 全コレクションデータ表示アプリ</p>
        <p>Made with ❤️ using Streamlit</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

# streamlit run mcp_qdrant_show.py --server.port=8501