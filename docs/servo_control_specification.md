# サーボ制御仕様書

**バージョン**: 1.0
**作成日**: 2025-12-14
**プロジェクト名**: 12-002-pet-monitoring-yolov8
**参照プロジェクト**: [12-001-rpi-pan-tilt-camera-mount](https://github.com/Murasan201/12-001-rpi-pan-tilt-camera-mount)

---

## 1. 概要

### 1.1 目的
本仕様書は、ペット監視システムにおけるパン・チルトカメラマウントのサーボ制御について定義する。
YOLOv8による物体検出結果に基づいてカメラの向きを自動調整し、ペットを画角中央に捉え続けることを目的とする。

### 1.2 制御ライブラリ
サーボ制御には、プロジェクト12-001で開発・検証された `servo_control.py` ライブラリを使用する。
このライブラリは台形制御による滑らかな動作と振動防止機能を実装している。

### 1.3 設計方針
- **関心の分離**: オブジェクト検出処理とサーボ制御処理を分離
- **再利用性**: 検証済みライブラリを活用し、信頼性を確保
- **保守性**: 各モジュールを独立して保守・テスト可能な設計

---

## 2. ハードウェア構成

### 2.1 使用部品
| 部品名 | 型番/仕様 | 数量 | 用途 |
|--------|----------|------|------|
| Raspberry Pi | Raspberry Pi 5（またはRaspberry Pi 4） | 1 | メインコントローラ |
| カメラモジュール | Raspberry Pi カメラモジュール v3 | 1 | 映像撮影 |
| サーボドライバ | Adafruit 16-Channel PWM/Servo HAT (PCA9685) | 1 | サーボモーター制御 |
| サーボモーター | SG90 | 2 | パン・チルト動作 |
| マウントキット | SG90サーボ用パン・チルトマウント | 1 | カメラ取り付け |

### 2.2 接続仕様
- **パン（左右）サーボ**: チャンネル0
- **チルト（上下）サーボ**: チャンネル1
- **通信方式**: I2C（アドレス: 0x40）
- **PWM周波数**: 50Hz
- **パルス幅範囲**: 750μs ～ 2250μs（SG90最適化設定）

---

## 3. 動作仕様

### 3.1 動作範囲（実機検証済み）

| サーボ | 範囲 | 中央位置 | 備考 |
|--------|------|----------|------|
| パン（左右） | 35～125度 | 80度 | フレーム構造により物理的中央は80度 |
| チルト（上下） | 45～120度 | 90度 | SG90の物理的限界を考慮 |

**注意事項**:
- パンサーボの中央位置は90度ではなく80度（フレーム構造による）
- 範囲外の角度を指定するとValueErrorが発生
- 物理的制約を超える角度指定は機構破損の原因となる
- **ケーブル等の外部テンションに注意**:
  - カメラモジュールのFPCケーブルや給電ケーブル等が引っ張られると、サーボに外乱トルクが加わりハンチング/振動の原因となる
  - 「余長の確保」「曲げ点を回転中心付近へ寄せる」「固定点（ストレインリリーフ）を設ける」を必ず行う
- **回転方向（符号）に注意**:
  - 同じ配線・同じコードでも、サーボホーンの付け直しや機構の組み付けによって「角度が増える方向」が逆になることがある
  - 症状例: 画面下に対象がいるのにカメラがさらに上を向く／画面右に対象がいるのにさらに左へ向く
  - 対策: `PAN_DIRECTION` / `TILT_DIRECTION`（`1` or `-1`）で追跡制御の符号を反転して切り分ける

### 3.2 制御パラメータ

| 項目 | 仕様 | 説明 |
|------|------|------|
| PWM周波数 | 50Hz | サーボモーター標準周波数 |
| パルス幅（最小） | 750μs | SG90の最小パルス幅 |
| パルス幅（最大） | 2250μs | SG90の最大パルス幅 |
| ステップ角度 | 1度 | 台形制御の1ステップあたりの角度 |
| 通常移動待機時間 | 0.02秒 | 通常速度での各ステップ間の待機時間 |
| 減速距離 | 5度 | 目標位置手前この距離で減速開始 |
| 減速時待機時間 | 0.06秒 | 減速時の待機時間（通常の3倍） |

---

## 4. 台形制御

### 4.1 台形制御とは
台形制御（Trapezoidal Control）は、サーボモーターの移動時に以下の特性を持つ制御方式：

1. **加速フェーズ**: 開始位置から徐々に速度を上げる（本実装では省略）
2. **等速フェーズ**: 一定速度で移動
3. **減速フェーズ**: 目標位置に近づくと速度を落とす

本実装では、簡略化した台形制御を採用し、主に**減速フェーズ**に注力している。

### 4.2 実装アルゴリズム

```
開始位置から目標位置へ1度ずつ移動
├─ 目標位置まで5度以上離れている場合
│   └─ 通常速度で移動（0.02秒待機）
└─ 目標位置まで5度以内の場合
    └─ 減速して移動（0.06秒待機、通常の3倍遅く）
```

**疑似コード**:
```python
for angle in range(start_angle, end_angle, step):
    distance_to_end = abs(end_angle - angle)

    if distance_to_end <= 5:  # 減速距離
        delay = 0.06  # 減速
    else:
        delay = 0.02  # 通常速度

    servo.angle = angle
    time.sleep(delay)
```

### 4.3 台形制御の効果

| 項目 | 効果 | 検証結果 |
|------|------|---------|
| 振動抑制 | 目標位置での振動を完全に停止 | ✅ 実機検証済み |
| 駆動音低減 | 約70%の騒音低減 | ✅ 実機検証済み |
| 滑らかな動作 | 急激な動きによる機構への負荷軽減 | ✅ 実機検証済み |
| 位置精度 | オーバーシュート防止 | ✅ 実機検証済み |

### 4.4 パルス幅設定の重要性
SG90サーボは**750～2250μs**のパルス幅範囲で動作するよう設計されている。
デフォルト設定（1000～2000μs）では以下の問題が発生：
- サーボの振動
- 位置精度の低下
- 駆動音の増加

`servo_control.py` では、初期化時に適切なパルス幅を設定することで、これらの問題を解決している。

---

## 5. servo_control.py ライブラリ仕様

### 5.1 提供関数

#### 5.1.1 initialize_servo_kit()
```python
def initialize_servo_kit() -> ServoKit
```
**機能**: ServoKitを初期化し、SG90に最適なパルス幅を設定
**戻り値**: 初期化済みのServoKitオブジェクト
**例外**: I2C通信エラー時にException

#### 5.1.2 set_pan_angle()
```python
def set_pan_angle(kit: ServoKit, angle: float, smooth: bool = True) -> None
```
**機能**: パンサーボを指定角度に移動
**引数**:
- `kit`: ServoKitオブジェクト
- `angle`: 目標角度（35～125度）
- `smooth`: 台形制御使用フラグ（デフォルトTrue）

**例外**: 範囲外の角度指定時にValueError

#### 5.1.3 set_tilt_angle()
```python
def set_tilt_angle(kit: ServoKit, angle: float, smooth: bool = True) -> None
```
**機能**: チルトサーボを指定角度に移動
**引数**:
- `kit`: ServoKitオブジェクト
- `angle`: 目標角度（45～120度）
- `smooth`: 台形制御使用フラグ（デフォルトTrue）

**例外**: 範囲外の角度指定時にValueError

#### 5.1.4 set_pan_tilt()
```python
def set_pan_tilt(kit: ServoKit, pan_angle: float, tilt_angle: float, smooth: bool = True) -> None
```
**機能**: パンとチルトを同時に指定角度へ移動（順次実行）
**引数**:
- `kit`: ServoKitオブジェクト
- `pan_angle`: パン目標角度（35～125度）
- `tilt_angle`: チルト目標角度（45～120度）
- `smooth`: 台形制御使用フラグ（デフォルトTrue）

**例外**: 範囲外の角度指定時にValueError

#### 5.1.5 set_center_position()
```python
def set_center_position(kit: ServoKit, smooth: bool = True) -> None
```
**機能**: 両サーボを中央位置へ移動（パン80度、チルト90度）
**引数**:
- `kit`: ServoKitオブジェクト
- `smooth`: 台形制御使用フラグ（デフォルトTrue）

#### 5.1.6 release_servos()
```python
def release_servos(kit: ServoKit) -> None
```
**機能**: サーボの電力供給を停止し、位置保持を解除
**用途**: 振動停止、バッテリー節約
**注意**: 位置保持ができなくなるため、重いカメラを搭載時は注意

### 5.2 定数定義

```python
# サーボチャンネル
PAN_CHANNEL = 0
TILT_CHANNEL = 1

# パルス幅（SG90用）
PULSE_MIN = 750
PULSE_MAX = 2250

# 動作範囲
PAN_CENTER = 80
PAN_LEFT = 35
PAN_RIGHT = 125

TILT_CENTER = 90
TILT_DOWN = 45
TILT_UP = 120

# 台形制御パラメータ
STEP_ANGLE = 1
NORMAL_DELAY = 0.02
SLOW_DISTANCE = 5
SLOW_DELAY = 0.06
```

---

## 6. 使用例

### 6.1 基本的な使用方法

```python
import servo_control

# サーボ初期化
kit = servo_control.initialize_servo_kit()

# 中央位置へ移動
servo_control.set_center_position(kit)

# パンを右へ移動
servo_control.set_pan_angle(kit, 100)

# チルトを上へ移動
servo_control.set_tilt_angle(kit, 110)

# パン・チルトを同時に移動
servo_control.set_pan_tilt(kit, 80, 90)

# サーボ解放
servo_control.release_servos(kit)
```

### 6.2 物体検出との統合例

```python
import servo_control

# サーボ初期化
kit = servo_control.initialize_servo_kit()

# 物体検出結果に基づいて角度を計算（仮の値）
pan_angle = calculate_pan_angle(detection_result)
tilt_angle = calculate_tilt_angle(detection_result)

# 台形制御で滑らかに移動
servo_control.set_pan_tilt(kit, pan_angle, tilt_angle, smooth=True)
```

---

## 7. システムアーキテクチャ

### 7.1 モジュール構成

```
ペット監視システム
├── camera_tracker.py
│   ├── YOLOv8物体検出
│   ├── P制御ロジック（検出結果→角度変換）
│   └── servo_control.py を呼び出し ← 本仕様の対象
│
├── servo_control.py ← 本仕様書が定義
│   ├── サーボ初期化
│   ├── 台形制御による移動
│   └── 角度範囲チェック
│
├── slack_uploader.py
│   └── Slack通知
│
└── main.py
    └── 全体オーケストレーション
```

### 7.2 制御フロー

```
物体検出
    ↓
検出座標取得
    ↓
P制御で目標角度計算
    ↓
servo_control.set_pan_tilt()
    ↓
台形制御で移動
    ↓
目標位置到達
```

---

## 8. エラーハンドリング

### 8.1 角度範囲エラー

```python
try:
    servo_control.set_pan_angle(kit, 150)  # 範囲外
except ValueError as e:
    print(f"エラー: {e}")
    # "パン角度は 35～125度の範囲で指定してください（指定値: 150度）"
```

### 8.2 I2C通信エラー

```python
try:
    kit = servo_control.initialize_servo_kit()
except Exception as e:
    print(f"サーボ初期化エラー: {e}")
    print("対処方法:")
    print("  1. I2C接続を確認: i2cdetect -y 1")
    print("  2. サーボHATが正しく接続されているか確認")
    print("  3. サーボ用電源が接続されているか確認")
```

---

## 9. セットアップ手順

### 9.1 ハードウェアセットアップ

1. Raspberry Piの電源を切る
2. Adafruit Servo HATをRaspberry Piに取り付け
3. サーボモーターをサーボHATに接続
   - パンサーボ: 0番端子
   - チルトサーボ: 1番端子
4. サーボ用電源（5V 4A推奨）を接続
5. I2C接続確認: `sudo i2cdetect -y 1`（0x40が表示されることを確認）

### 9.2 ソフトウェアセットアップ

```bash
# 必要なライブラリのインストール
sudo pip3 install adafruit-circuitpython-servokit --break-system-packages

# 動作確認
python3 servo_control.py
```

---

## 10. トラブルシューティング

### 10.1 サーボが動かない

**症状**: `initialize_servo_kit()` でエラー、またはサーボが応答しない

**確認事項**:
1. I2C接続: `sudo i2cdetect -y 1` でアドレス0x40が表示されるか
2. サーボ用電源が接続されているか（Raspberry Piの電源とは別）
3. サーボケーブルが正しいチャンネルに接続されているか

### 10.2 サーボが振動する

**症状**: サーボが目標位置で細かく振動する

**対処方法**:
1. `servo_control.py` を使用していることを確認（台形制御が実装されている）
2. パルス幅が750-2250μsに設定されていることを確認
3. 物理的な負荷が大きすぎないか確認

### 10.3 動作範囲エラー

**症状**: `ValueError: パン角度は 35～125度の範囲で指定してください`

**対処方法**:
- 指定角度が範囲内か確認
- P制御の計算結果が範囲外になっていないか確認
- 必要に応じてクリッピング処理を追加

```python
# 角度のクリッピング例
pan_angle = max(35, min(125, calculated_pan_angle))
tilt_angle = max(45, min(120, calculated_tilt_angle))
```

---

## 11. 参考資料

### 11.1 関連ドキュメント
- 親プロジェクト仕様書: `reference/12-001-rpi-pan-tilt-camera-mount/docs/specification.md`
- トラブルシューティング: `reference/12-001-rpi-pan-tilt-camera-mount/docs/troubleshooting.md`
- 本プロジェクト要件定義: `pet_monitoring_requirements.md`
- P制御設計: `raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md`

### 11.2 関連プロジェクト
- [12-001-rpi-pan-tilt-camera-mount](https://github.com/Murasan201/12-001-rpi-pan-tilt-camera-mount) - サーボ制御ライブラリの開発元
- [08-002-rpi-servo-multi-control](https://github.com/Murasan201/08-002-rpi-servo-multi-control) - サーボ制御の基礎

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0 | 2025-12-14 | 初版作成 |
| 1.1 | 2025-12-18 | チルト上限を135度→120度に変更（SG90の物理的限界を考慮） |
