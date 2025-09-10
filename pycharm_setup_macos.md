# PyCharm メモリ最適化設定ガイド (macOS版)

## 1. VM Optionsファイルの適用

### 方法1: PyCharm GUI経由（推奨）
1. PyCharmを開く
2. メニューバー → Help → Edit Custom VM Options... を選択
3. 以下の内容をコピー＆ペースト：

```
-Xms4096m
-Xmx12288m
-XX:ReservedCodeCacheSize=1024m
-XX:SoftRefLRUPolicyMSPerMB=50
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-XX:ConcGCThreads=4
-XX:MetaspaceSize=512m
-XX:MaxMetaspaceSize=2048m
-XX:MaxDirectMemorySize=2048m
-XX:+AlwaysPreTouch
-XX:+UseStringDeduplication
-XX:+UseCompressedOops
```

4. PyCharmを完全に終了（Cmd+Q）
5. PyCharmを再起動

### 方法2: 直接ファイル配置
```bash
# PyCharmのバージョンを確認
ls ~/Library/Application\ Support/JetBrains/

# 該当するディレクトリにコピー（例：PyCharm2024.3）
cp pycharm.vmoptions ~/Library/Application\ Support/JetBrains/PyCharm2024.3/
```

## 2. PyCharm内部設定の最適化

### メモリ設定
- PyCharm → Settings (Cmd+,)
- Appearance & Behavior → System Settings → Memory Settings
  - IDE max heap size: 12288 MB に設定

### エディタ設定
- Editor → General
  - Maximum number of contents to keep in clipboard: 5
  - Recent files limit: 20
  - Undo limit: 100

### インデックス設定
- Editor → File Types
  - Ignored files and folders に以下を追加：
    - `*.pyc`
    - `__pycache__`
    - `.git`
    - `node_modules`
    - `venv`
    - `.idea/workspace.xml`

## 3. macOS固有の最適化コマンド

### 正しいmacOSコマンド
```bash
# メモリ圧縮の確認
vm_stat

# PyCharmのメモリ使用状況確認
ps aux | grep pycharm | grep -v grep

# PyCharmプロセスの優先度を上げる（オプション）
# プロセスIDを取得
pgrep -f pycharm

# 優先度変更（要管理者権限）
# sudo renice -n -5 -p [プロセスID]

# キャッシュクリア（問題が続く場合）
rm -rf ~/Library/Caches/JetBrains/PyCharm*
```

## 4. 追加の最適化Tips

### プロジェクト設定
1. File → Invalidate Caches... → Invalidate and Restart
   - 月1回程度実行を推奨

2. 不要なプラグインの無効化
   - PyCharm → Settings → Plugins
   - 使用していないプラグインを無効化

3. プロジェクトインデックスの最適化
   - Project Structure → Project Settings → Modules
   - Excluded に大きなデータフォルダを追加

### Activity Monitorでの監視
1. アプリケーション → ユーティリティ → アクティビティモニタ
2. PyCharmのメモリ使用量を確認
3. 12GB以下で安定していることを確認

## 5. トラブルシューティング

### それでもメモリ不足が発生する場合

1. ヒープサイズを調整
```
-Xmx8192m  # 8GBに減らす
```

2. Python環境の最適化
```bash
# 仮想環境のクリーンアップ
pip cache purge
```

3. macOSのメモリ最適化
```bash
# メモリプレッシャーの確認
memory_pressure

# DNSキャッシュのクリア（ネットワーク関連のメモリ解放）
sudo dscacheutil -flushcache
```

## 6. 推奨される定期メンテナンス

### 週次
- PyCharmの再起動

### 月次
- Invalidate Caches and Restart
- `.idea/workspace.xml` の削除と再生成

### 必要に応じて
- macOSの再起動
- PyCharmの再インストール（最終手段）