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

## 📁 ドキュメント体系

```
docs/
├── README.md (本ファイル)
├── pet_monitoring_requirements.md                                          # 要件定義書
├── raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md # P制御設計レポート
├── servo_control_specification.md                                          # サーボ制御仕様
└── detection_and_tracking_specification.md                                 # 検出・追跡仕様
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

本プロジェクトは、以下のプロジェクトで開発されたサーボ制御ライブラリを使用しています：

**12-001-rpi-pan-tilt-camera-mount**
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
| 2025-12-14 | 初版作成（README、サーボ制御仕様書、検出・追跡仕様書） |
