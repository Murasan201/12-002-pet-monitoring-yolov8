# 参考文献

**プロジェクト**: 12-002-pet-monitoring-yolov8（ペット見守りシステム）
**作成日**: 2025-12-17
**目的**: 書籍掲載用の参考文献リスト

---

## 公式ドキュメント

### Raspberry Pi

1. **Raspberry Pi Documentation**
   - URL: https://www.raspberrypi.com/documentation/
   - 参照日: 2025-12-17
   - 概要: Raspberry Piの公式ドキュメント。ハードウェア仕様、OS設定、カメラ設定などを参照

2. **Raspberry Pi Camera Documentation**
   - URL: https://www.raspberrypi.com/documentation/accessories/camera.html
   - 参照日: 2025-12-17
   - 概要: Camera Module V3の仕様、Picamera2の使用方法

3. **Raspberry Pi AI Kit Documentation**
   - URL: https://www.raspberrypi.com/documentation/accessories/ai-kit.html
   - 参照日: 2025-12-17
   - 概要: Hailo-8L AIアクセラレータの概要、セットアップ手順

### Hailo

1. **Hailo Developer Zone**
   - URL: https://hailo.ai/developer-zone/
   - 参照日: 2025-12-17
   - 概要: HailoRT SDK、モデル最適化、APIリファレンス

2. **Hailo Model Zoo**
   - URL: https://github.com/hailo-ai/hailo_model_zoo
   - 参照日: 2025-12-17
   - 概要: Hailo用に最適化されたモデルコレクション（YOLOv8含む）

### OpenCV

1. **OpenCV Documentation**
   - URL: https://docs.opencv.org/
   - 参照日: 2025-12-17
   - 概要: 画像処理、動画キャプチャ、描画関数のAPIリファレンス

### Adafruit

1. **Adafruit 16-Channel PWM/Servo HAT for Raspberry Pi**
   - URL: https://learn.adafruit.com/adafruit-16-channel-pwm-servo-hat-for-raspberry-pi
   - 参照日: 2025-12-17
   - 概要: PCA9685搭載Servo HATの使用方法、I2C設定、Pythonライブラリ

2. **Adafruit CircuitPython ServoKit Documentation**
   - URL: https://docs.circuitpython.org/projects/servokit/en/latest/
   - 参照日: 2025-12-17
   - 概要: サーボ制御用Pythonライブラリの APIリファレンス

---

## GitHub リポジトリ

### 本プロジェクト関連

1. **11-002-raspi-hailo8l-yolo-detector**
   - URL: https://github.com/Murasan201/11-002-raspi-hailo8l-yolo-detector
   - 参照日: 2025-12-17
   - 概要: Hailo-8L用YOLO物体検出ライブラリ。本プロジェクトで使用

2. **12-001-rpi-pan-tilt-camera-mount**
   - URL: https://github.com/Murasan201/12-001-rpi-pan-tilt-camera-mount
   - 参照日: 2025-12-17
   - 概要: パン・チルトカメラマウントのサーボ制御ライブラリ。本プロジェクトで使用

### YOLOv8

1. **Ultralytics YOLOv8**
   - URL: https://github.com/ultralytics/ultralytics
   - 参照日: 2025-12-17
   - 概要: YOLOv8の公式リポジトリ。モデル仕様、学習方法、推論APIを参照

---

## 技術記事・チュートリアル

### 顔追跡・物体追跡

1. **SunFounder PiCar-X 顔追跡チュートリアル**
   - URL: https://docs.sunfounder.com/projects/picar-x/ja/latest/python/python_stare_at_you.html
   - 参照日: 2025-12-17
   - 概要: P制御による顔追跡の実装例。追跡アルゴリズムの設計参考

---

## データセット

1. **COCO Dataset (Common Objects in Context)**
   - URL: https://cocodataset.org/
   - 参照日: 2025-12-17
   - 概要: YOLOv8の学習に使用されたデータセット。80クラス分類（cat: 15, dog: 16）

---

## 書籍

（参考にした技術書籍があれば追記）

---

## 記録ルール

新しい参考文献を追加する際は、以下の形式で記録してください：

```markdown
X. **[タイトル]**
   - URL: [URL]
   - 参照日: YYYY-MM-DD
   - 概要: [どのような情報を参照したか、1-2行で説明]
```

---

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2025-12-17 | 初版作成（主要な公式ドキュメント、GitHubリポジトリを記載） |
