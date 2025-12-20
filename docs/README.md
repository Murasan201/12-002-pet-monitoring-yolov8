# ドキュメント索引

本ディレクトリには、ペット監視システム（12-002-pet-monitoring-yolov8）の技術仕様書および設計ドキュメントが含まれています。

---

## 📋 ドキュメント一覧

### 1. 要件定義書
**ファイル**: [`pet_monitoring_requirements.md`](./pet_monitoring_requirements.md)

**概要**: ペット見守りシステム全体の要件定義

**主な内容**:
- システム概要と目的
- ハードウェア・ソフトウェア構成
- モジュール構成（camera_tracker.py、slack_uploader.py、main.py）
- 機能仕様（対象検出、追跡、制御方式、定期スキャン、画像保存、Slack通知）
- 想定利用シナリオ

**対象読者**: プロジェクト全体を理解したい全ての開発者

---

### 2. P制御設計レポート
**ファイル**: [`raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md`](./raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md)

**概要**: P制御方式の検討と設計根拠

**主な内容**:
- ジッタと周期不定の課題整理
- PCA9685（Adafruit Servo HAT）採用理由
- P制御の設計方針（PID制御ではなくP制御のみを採用する理由）
- Kpパラメータの初期値計算方法
- 実装サンプルコード
- SunFounder PiCar-X参考情報

**対象読者**: P制御の設計背景を理解したい開発者、パラメータ調整を行う開発者

---

### 3. サーボ制御仕様書
**ファイル**: [`servo_control_specification.md`](./servo_control_specification.md)

**概要**: パン・チルトカメラマウントのサーボ制御に関する仕様

**主な内容**:
- ハードウェア構成（Adafruit Servo HAT、SG90サーボ）
- 動作範囲（パン: 35-125°、チルト: 45-135°）
- 台形制御アルゴリズムの詳細説明
- `servo_control.py` ライブラリAPI仕様
- セットアップ手順とトラブルシューティング

**対象読者**: サーボ制御部分の実装・保守を行う開発者

---

### 4. オブジェクト検出・追跡仕様書
**ファイル**: [`detection_and_tracking_specification.md`](./detection_and_tracking_specification.md)

**概要**: YOLOv8による物体検出とP制御による追跡アルゴリズムの仕様

**主な内容**:
- YOLOv8物体検出の仕組み（モデル、検出対象、検出プロセス）
- P制御（比例制御）の理論と実装
- スキャン機能（全域探索アルゴリズム）
- 追跡フェーズ（P制御ループ）
- 画像キャプチャとリサイズ処理
- `CameraTracker` クラスAPI仕様
- パフォーマンス最適化とトラブルシューティング

**対象読者**: オブジェクト検出・追跡部分の実装・保守を行う開発者

---

### 5. Slack通知機能仕様書
**ファイル**: [`slack_notification_specification.md`](./slack_notification_specification.md)

**概要**: ペット検出時のSlack通知機能モジュールの仕様

**主な内容**:
- モジュール設計（関数ライブラリとして利用可能）
- API仕様（`upload_images()`, `send_message()`, `send_notification()`）
- Slack App設定とOAuthスコープ
- 環境変数による設定管理
- エラーハンドリングとリトライ処理
- CLIとしての実行方法
- セキュリティ考慮事項

**対象読者**: Slack通知機能の実装・保守を行う開発者

---

### 7. P制御追跡 技術検討レポート
**ファイル**: [`p_control_tracking_technical_report.md`](./p_control_tracking_technical_report.md)

**概要**: 非リアルタイムOS環境でのP制御追跡における安定化手法の技術検討

**主な内容**:
- Linux + YOLO推論環境での制御上の制約
- デッドバンド（不感帯）の設計指針と推奨値
- 角度制限（角度変化量制限）の設計指針と推奨値
- 推奨制御アルゴリズム（擬似コード付き）
- チューニング手順
- 想定される失敗モードと対策

**対象読者**: P制御パラメータのチューニングを行う開発者、追跡機能の安定化を検討する開発者

---

### 8. トラブルシューティング
**ファイル**: [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md)

**概要**: 環境構築・テスト・運用中に発生したエラーと解決策のナレッジベース

**主な内容**:
- 環境構築時のエラーと解決策
- Hailo-8L AIアクセラレータ関連の問題
- カメラ接続・撮影関連の問題
- サーボ制御関連の問題
- 物体検出・追跡関連の問題

**対象読者**: 環境構築を行う開発者、エラー発生時のトラブルシューティング

---

### 9. セットアップ手順書
**ファイル**: [`SETUP_GUIDE.md`](./SETUP_GUIDE.md)

**概要**: 書籍掲載用のセットアップ手順を詳細に記録

**主な内容**:
- 前提条件（ハードウェア構成、ソフトウェア要件）
- ステップバイステップのセットアップ手順
- 各ステップの詳細解説と期待される出力
- 動作確認方法

**対象読者**: Raspberry Pi初心者〜中級者、書籍読者

---

### 10. 参考文献
**ファイル**: [`REFERENCES.md`](./REFERENCES.md)

**概要**: 書籍掲載用の参考文献リスト

**主な内容**:
- 公式ドキュメント（Raspberry Pi、Hailo、OpenCV、Adafruit）
- GitHubリポジトリ
- 技術記事・チュートリアル
- データセット

**対象読者**: 書籍執筆者、詳細情報を求める開発者

---

## 📁 ドキュメント体系

```
docs/
├── README.md (本ファイル)
├── pet_monitoring_requirements.md                                          # 要件定義書
├── raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md # P制御設計レポート
├── servo_control_specification.md                                          # サーボ制御仕様
├── detection_and_tracking_specification.md                                 # 検出・追跡仕様
├── slack_notification_specification.md                                     # Slack通知機能仕様
├── p_control_tracking_technical_report.md                                  # P制御追跡 技術検討レポート
├── TROUBLESHOOTING.md                                                      # トラブルシューティング
├── SETUP_GUIDE.md                                                          # セットアップ手順書
└── REFERENCES.md                                                           # 参考文献
```

---

## 🔗 関連ドキュメント

プロジェクトルートディレクトリにも重要なドキュメントがあります：

| ドキュメント | 場所 | 説明 |
|------------|------|------|
| **プロジェクトREADME** | `../README.md` | プロジェクト概要とセットアップ手順 |
| **Claude Code ルール** | `../CLAUDE.md` | 開発ルールとガイドライン |

---

## 📚 参照プロジェクト

本プロジェクトは、以下のプロジェクトで開発されたライブラリを使用しています：

### 11-002-raspi-hailo8l-yolo-detector（物体検出）
Hailo-8L AIアクセラレータを使用したYOLO物体検出ライブラリ
- GitHub: https://github.com/Murasan201/11-002-raspi-hailo8l-yolo-detector
- ローカル参照: `../reference/11-002-raspi-hailo8l-yolo-detector/`
- **ライブラリAPI**: `../reference/11-002-raspi-hailo8l-yolo-detector/docs/LIBRARY_API.md` ← **実装時は必ず参照**
- 要件定義書: `../reference/11-002-raspi-hailo8l-yolo-detector/docs/11_002_raspi_hailo_8_l_yolo_detector.md`
- セットアップ: `../reference/11-002-raspi-hailo8l-yolo-detector/docs/SETUP_GUIDE.md`
- トラブルシューティング: `../reference/11-002-raspi-hailo8l-yolo-detector/docs/TROUBLESHOOTING.md`

### 12-001-rpi-pan-tilt-camera-mount（サーボ制御）
パン・チルトカメラマウントのサーボ制御ライブラリ
- GitHub: https://github.com/Murasan201/12-001-rpi-pan-tilt-camera-mount
- ローカル参照: `../reference/12-001-rpi-pan-tilt-camera-mount/`
- 仕様書: `../reference/12-001-rpi-pan-tilt-camera-mount/docs/specification.md`
- トラブルシューティング: `../reference/12-001-rpi-pan-tilt-camera-mount/docs/troubleshooting.md`

---

## 📖 読む順序の推奨

### 新規参加者向け
1. `../README.md` - プロジェクト全体像を把握
2. `pet_monitoring_requirements.md` - システム要件を理解
3. `servo_control_specification.md` - サーボ制御の仕様を確認
4. `detection_and_tracking_specification.md` - 検出・追跡の仕様を確認

### サーボ制御の実装・修正を行う場合
1. `servo_control_specification.md` - 本プロジェクトの仕様
2. `../reference/12-001-rpi-pan-tilt-camera-mount/docs/specification.md` - 元プロジェクトの詳細仕様
3. `../reference/12-001-rpi-pan-tilt-camera-mount/docs/troubleshooting.md` - 既知の問題と解決策

### 検出・追跡の実装・修正を行う場合
1. `detection_and_tracking_specification.md` - 検出・追跡仕様
2. `raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md` - P制御の設計根拠
3. `p_control_tracking_technical_report.md` - P制御追跡の技術検討（デッドバンド・角度制限）

### Hailo8L物体検出の実装・修正を行う場合
1. `../reference/11-002-raspi-hailo8l-yolo-detector/docs/LIBRARY_API.md` - **ライブラリAPI（実装時必須）**
2. `../reference/11-002-raspi-hailo8l-yolo-detector/docs/11_002_raspi_hailo_8_l_yolo_detector.md` - 要件定義書
3. `../reference/11-002-raspi-hailo8l-yolo-detector/docs/SETUP_GUIDE.md` - セットアップ手順
4. `../reference/11-002-raspi-hailo8l-yolo-detector/README.md` - 使用方法

---

## 🛠️ ドキュメント作成ルール

本ディレクトリのドキュメントは以下のルールに従って作成してください：

### ファイル命名規則
- 仕様書: `*_specification.md`
- 設計書: `*_design.md`
- 実装ノート: `*_notes.md`

### フォーマット
- Markdown形式
- 見出しレベル1（`#`）はドキュメントタイトルのみ
- 適切な見出し階層を使用
- コードブロックには言語指定を付ける

### 更新時の注意
- バージョン番号を更新
- 変更履歴セクションに記録
- 関連ドキュメントへの影響を確認

詳細は `../CLAUDE.md` の Documentationセクションを参照してください。

---

## 📝 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2025-12-20 | Slack通知機能仕様書（slack_notification_specification.md）を追加 |
| 2025-12-17 | セットアップ手順書（SETUP_GUIDE.md）、参考文献（REFERENCES.md）を追加 |
| 2025-12-17 | トラブルシューティングドキュメント（TROUBLESHOOTING.md）を追加 |
| 2025-12-17 | P制御追跡 技術検討レポート（p_control_tracking_technical_report.md）を追加 |
| 2025-12-17 | 参照プロジェクトに11-002-raspi-hailo8l-yolo-detector（Hailo8L物体検出）を追加 |
| 2025-12-14 | 初版作成（README、サーボ制御仕様書、検出・追跡仕様書） |
