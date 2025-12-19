# Claude Code Rules

## Project Overview
This is a pet monitoring system using YOLOv8 for object detection.

**Repository**: https://github.com/Murasan201/12-002-pet-monitoring-yolov8

**Requirements Document**: `pet_monitoring_requirements.md`

## Work Process
- **IMPORTANT**: At the start of any work session, review `docs/README.md` to understand the documentation structure
- Always review `pet_monitoring_requirements.md` before starting any work
- Ensure all implementations align with the requirements specified in the document

## Coding Guidelines
- Follow Python PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and modular
- **Comments**: Write all code comments in Japanese
- **Comment Style**: Add beginner-friendly comments without compromising readability

## Git Commit Guidelines
- Write clear, concise commit messages
- Use present tense (e.g., "Add feature" not "Added feature")
- Reference issue numbers when applicable

### コミット前の必須チェック項目

**CRITICAL**: コミット前に以下のファイルが含まれていないことを必ず確認すること。

| 除外対象ファイル | 理由 |
|------------------|------|
| `tracking*.csv` | 動作確認用ログデータ（個人環境依存） |
| `*.log` | ログファイル |
| `*.jpg`, `*.png`, `*.jpeg` | カメラ画像（容量・プライバシー） |
| `*.mp4`, `*.avi` | 動画ファイル |
| `.env` | 環境変数（認証情報を含む可能性） |

**確認コマンド**:
```bash
# ステージングされたファイルの確認
git status

# 除外対象ファイルが含まれていないか確認
git diff --cached --name-only | grep -E '\.(csv|log|jpg|png|jpeg|mp4|avi)$'
```

上記コマンドで出力があった場合は、`git reset HEAD <file>` でステージングを解除すること。

## Testing
- Write unit tests for new functionality
- Ensure all tests pass before committing
- Maintain test coverage

## Environment Setup Rules

### 仮想環境の使用

**CRITICAL**: 環境構築は必ずPython仮想環境（venv）を作成した上で実施すること。

```bash
# 仮想環境の作成（--system-site-packages でシステムパッケージにアクセス可能）
python3 -m venv .venv --system-site-packages

# 仮想環境の有効化
source .venv/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

**--system-site-packages を使用する理由**:
- HailoRT SDKはシステムパッケージとしてインストールされている
- Picamera2もシステムパッケージとして提供されている
- これらのパッケージに仮想環境からアクセスするために必要

### セットアップ手順書の作成

**CRITICAL**: 環境構築の手順は `docs/SETUP_GUIDE.md` に書籍掲載用として詳細に記録すること。

#### 記録すべき内容

1. **前提条件**: ハードウェア構成、OS、事前準備
2. **手順**: ステップバイステップのコマンドと解説
3. **確認方法**: 各ステップ完了後の動作確認コマンド
4. **解説**: 初心者向けの補足説明（なぜその操作が必要か）
5. **期待される出力**: コマンド実行時の出力例

#### 記録フォーマット

```markdown
### ステップ X: [ステップ名]

**目的**: [このステップで何を行うか]

**コマンド**:
```bash
[実行するコマンド]
```

**解説**:
[初心者向けの説明。なぜこの操作が必要か、何が起こるか]

**期待される出力**:
```
[コマンド実行時の出力例]
```

**確認方法**:
```bash
[動作確認コマンド]
```
```

### 参考文献の記録

**CRITICAL**: 参照した重要なドキュメントは `docs/REFERENCES.md` に書籍掲載用の参考文献として記録すること。

#### 記録すべき参考文献

| 種類 | 例 |
|------|-----|
| 公式ドキュメント | Raspberry Pi公式、Hailo公式、OpenCV公式 |
| GitHub リポジトリ | 使用したライブラリのリポジトリ |
| 技術記事 | 参考にした技術ブログ、Qiita記事など |
| 書籍 | 参考にした技術書籍 |

#### 記録フォーマット

```markdown
### [カテゴリ名]

1. **[タイトル]**
   - URL: [URL]
   - 参照日: YYYY-MM-DD
   - 概要: [どのような情報を参照したか]
```

## Troubleshooting Documentation

### エラー記録の義務

**CRITICAL**: 環境構築・テスト・運用中に発生したすべてのエラーとその解決策は、必ず `docs/TROUBLESHOOTING.md` に記録すること。

### 記録すべき情報

1. **発生日**: エラーが発生した日付（YYYY-MM-DD形式）
2. **発生状況**: どのような操作・状況で発生したか
3. **エラーメッセージ**: 実際に表示されたエラーメッセージ（コードブロックで記載）
4. **原因**: エラーの原因を箇条書きで記載
5. **解決策**: 解決手順をコマンド付きで記載
6. **確認方法**: 解決後の確認コマンド
7. **ステータス**: 解決済み / 未解決

### 記録のタイミング

- エラー発生直後に記録を開始
- 解決策が判明した時点で更新
- 同種のエラーが再発した場合は追記

### 記録のカテゴリ

| カテゴリ | 対象 |
|---------|------|
| 環境構築 | パッケージインストール、依存関係のエラー |
| Hailo-8L関連 | AIアクセラレータの認識、推論エラー |
| カメラ関連 | カメラ接続、撮影、Picamera2のエラー |
| サーボ制御関連 | PCA9685、サーボモーター動作のエラー |
| 物体検出関連 | YOLO検出、モデル読み込みのエラー |
| P制御・追跡関連 | 追跡動作、パラメータ調整の問題 |

### 記録の目的

- 将来同じエラーに遭遇した際の参照資料
- 書籍・技術記事執筆時の情報源
- 他の開発者への知識共有
- プロジェクトのナレッジベース構築

## Documentation
- **Documentation Directory**: All project documentation, specifications, and design documents must be stored in the `docs/` directory
- **File Organization**:
  - Specifications: `docs/*_specification.md`
  - Design documents: `docs/*_design.md`
  - Implementation notes: `docs/*_notes.md`
- Update documentation when adding new features
- Include usage examples where appropriate
- Keep README.md up to date
- Write documentation in markdown format

## MCP Tools Usage
- **Web Search**: Use Google Search agent (MCP) when you need to search for information online
- **Code Understanding**: Use Serena (MCP) for analyzing and understanding documentation and source code structure when needed

## Hailo-8L Object Detection
This project uses Hailo-8L AI accelerator for real-time YOLO object detection.

**Detection Library**: `raspi_hailo8l_yolo.py` (from 11-002-raspi-hailo8l-yolo-detector)

**Reference Repository**: https://github.com/Murasan201/11-002-raspi-hailo8l-yolo-detector
- Local reference: `/home/pi/work/project/kodansya/12-002-pet-monitoring-yolov8/reference/11-002-raspi-hailo8l-yolo-detector`

### Hardware Configuration
- **AI Accelerator**: Raspberry Pi AI Kit (Hailo-8L)
- **Camera**: Raspberry Pi Camera Module V3 (IMX708)
- **Platform**: Raspberry Pi 5
- **OS**: Raspberry Pi OS (Bookworm or later)
- **Python**: 3.11+

### Library Integration

ライブラリとして使用する場合、以下のファイルをコピーしてください。

**必須ファイル:**
```
raspi_hailo8l_yolo.py    # メインライブラリ（単一ファイル）
```
※ この1ファイルで全ての機能（YOLODetector, CameraManager, draw_detections等）が含まれています。

**モデルファイル:**
別途HEFモデルファイルが必要です：
```bash
# システムにインストール済みのモデルへのシンボリックリンク作成
mkdir -p models
ln -sf /usr/share/hailo-models/yolov8s_h8l.hef models/yolov8s_h8l.hef
```

**依存パッケージ:**
- opencv-python
- numpy
- HailoRT SDK（システムパッケージ）
- Picamera2（Camera Module V3使用時）

### Available Classes and Functions
The `raspi_hailo8l_yolo.py` library provides the following API:

```python
from raspi_hailo8l_yolo import YOLODetector, CameraManager, draw_detections, COCO_CLASSES

# Initialize detector with HEF model
detector = YOLODetector("models/yolov8s_h8l.hef")

# Perform detection on image
detections = detector.detect(image)

# Draw detection results
result = draw_detections(image, detections)

# Available COCO classes for pet detection
# 'cat', 'dog' are included in COCO_CLASSES
```

### Key Features
- **Library Design**: Can be imported as a module or run as CLI application
- **High-Speed Inference**: Hailo-8L accelerated YOLO detection
- **Real-time Processing**: Live video processing from Camera Module V3
- **Target Classes**: Can filter specific classes (e.g., 'cat', 'dog' for pet monitoring)
- **Detection Logging**: CSV output support for detection results

### Related Documentation
- **Library API**: `reference/11-002-raspi-hailo8l-yolo-detector/docs/LIBRARY_API.md` ← **実装時は必ずこのドキュメントを参照**
- Requirements: `reference/11-002-raspi-hailo8l-yolo-detector/docs/11_002_raspi_hailo_8_l_yolo_detector.md`
- Setup Guide: `reference/11-002-raspi-hailo8l-yolo-detector/docs/SETUP_GUIDE.md`
- Troubleshooting: `reference/11-002-raspi-hailo8l-yolo-detector/docs/TROUBLESHOOTING.md`
- README: `reference/11-002-raspi-hailo8l-yolo-detector/README.md`

---

## Camera Mount Control
This project uses a pan-tilt camera mount controlled by servo motors.

**Control Library**: `servo_control.py` (copied from 12-001-rpi-pan-tilt-camera-mount)

**Reference Repository**: https://github.com/Murasan201/12-001-rpi-pan-tilt-camera-mount
- Local reference: `/home/pi/work/project/kodansya/12-002-pet-monitoring-yolov8/reference/12-001-rpi-pan-tilt-camera-mount`

### Hardware Configuration
- **Servo Driver**: Adafruit 16-Channel PWM/Servo HAT (PCA9685)
- **Servo Motors**: SG90 x 2
- **Pan Servo**: Channel 0 (35-125°, center at 80°)
- **Tilt Servo**: Channel 1 (45-135°, center at 90°)
- **Communication**: I2C (address 0x40)
- **PWM Frequency**: 50Hz
- **Pulse Width**: 750-2250μs (SG90 optimized)

### Available Functions
The `servo_control.py` library provides the following functions for camera control:

```python
import servo_control

# Initialize servo kit
kit = servo_control.initialize_servo_kit()

# Move pan servo (horizontal: left/right)
servo_control.set_pan_angle(kit, 80)

# Move tilt servo (vertical: up/down)
servo_control.set_tilt_angle(kit, 90)

# Move both servos simultaneously
servo_control.set_pan_tilt(kit, 80, 90)

# Return to center position
servo_control.set_center_position(kit)

# Release servos (stop holding position)
servo_control.release_servos(kit)
```

### Key Features
- **Trapezoidal Control**: Smooth motion with automatic deceleration near target
- **Vibration Prevention**: Optimized pulse width settings for SG90 servos
- **Library Design**: Reusable functions for integration with object tracking
- **Validated Range**: Tested safe operating ranges for the physical mount

### Related Documentation
- Specification: `reference/12-001-rpi-pan-tilt-camera-mount/docs/specification.md`
- Troubleshooting: `reference/12-001-rpi-pan-tilt-camera-mount/docs/troubleshooting.md`
- README: `reference/12-001-rpi-pan-tilt-camera-mount/README.md`

---

## Project Management & Development Delegation

### PM（プロジェクトマネージャー）の役割

PMは以下の役割を担い、直接コーディング作業を行わない：
- プロジェクト全体の進捗管理
- 要件の明確化と優先順位付け
- タスクの分割と割り当て
- 成果物のレビューと品質管理

### サブエージェントへの作業依頼ルール

**CRITICAL**: PMがコーディング作業を行う際は、必ずサブエージェント（Task tool）を起動して作業を委譲すること。

#### 依頼時の必須事項

1. **参照仕様書の明示的な指定**
   - 必ず参照すべきドキュメントのパスを指定する
   - サブエージェントは指定された仕様書を読み込んでから作業を開始する

2. **指定すべき仕様書の種類**

| 作業内容                    | 必須参照ドキュメント                              |
|-----------------------------|---------------------------------------------------|
| 新機能実装                  | `docs/pet_monitoring_requirements.md`（要件定義書）|
| 検出・追跡機能              | `docs/detection_and_tracking_specification.md`    |
| サーボ制御                  | `docs/servo_control_specification.md`             |
| Hailo8L物体検出             | `reference/11-002-raspi-hailo8l-yolo-detector/docs/LIBRARY_API.md`（実装API） |
| コード修正/リファクタリング | `CLAUDE.md`（Coding Guidelinesセクション）        |
| ドキュメント/コメント追加   | `COMMENT_STYLE_GUIDE.md`（コメント標準）          |
| 全般的な開発作業            | `CLAUDE.md`（本ドキュメント）                     |

3. **依頼プロンプトのテンプレート**

```
以下のタスクを実行してください。

【タスク】
<具体的な作業内容>

【参照仕様書】
- docs/<仕様書名>.md

【制約事項】
- 仕様書のルールに従うこと
- 日本語でコメントを記載すること
```

#### サブエージェント起動例

Task tool を使用:
- `subagent_type`: "general-purpose" または "Plan"
- `model`: "sonnet" ← コーディング作業では必ず sonnet を指定
- `prompt`: 上記テンプレートに従った依頼内容

#### モデル指定ルール

**IMPORTANT**: コーディング作業のためにサブエージェントを起動する際は、必ず `model: "sonnet"` を指定すること。

| モデル | 用途                                                   |
|--------|--------------------------------------------------------|
| sonnet | コーディング作業（実装、修正、リファクタリング）       |
| haiku  | 軽微な調査、簡単な質問応答（コーディング以外）         |
| opus   | 複雑な設計判断、アーキテクチャ検討（PMが直接使用）     |

#### 作業フロー

```
1. PM: 要件を分析しタスクを定義
       ↓
2. PM: 参照仕様書を特定
       ↓
3. PM: Task tool でサブエージェントを起動
       ↓
4. サブエージェント: 仕様書を読み込み
       ↓
5. サブエージェント: コーディング作業を実施
       ↓
6. PM: 成果物をレビュー
```