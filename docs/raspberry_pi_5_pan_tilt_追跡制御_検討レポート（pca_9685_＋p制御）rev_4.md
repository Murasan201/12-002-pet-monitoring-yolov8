# Raspberry Pi 5 + Pan‑Tilt 追跡制御：ジッタ対策と制御方式の検討レポート（rev4）

**対象リポジトリ**："12-002-pet-monitoring-yolov8"（https://github.com/Murasan201/12-002-pet-monitoring-yolov8）

---

## 1. 背景と目的
Raspberry Pi 5、Camera Module v3、SG90×2（パン・チルト）を用い、YOLOで検出したオブジェクト（ペット）を追跡するためにカメラの画角を自動で調整する。アプリの要件は「数分〜数十分に一度、画角を変更できれば十分」であり、リアルタイム性は厳しくない。一方で、Raspberry Pi（汎用OS上）では**一定周期の厳密な制御ループ**や**ソフトウェアPWM**に起因するジッタが懸念される。本レポートでは、

- 一定周期を前提としない制御方式
- PWM生成のジッタを回避するハード構成
- 実装難易度・保守性・コストのバランス

を踏まえた実装方針をまとめる。

---

## 2. 課題の整理（ジッタと周期不定）
- **OSスケジューリング起因ジッタ**：Linux通常カーネルではユーザー空間タスクの実行タイミングが数百µs〜ms単位でぶれる。
- **ソフトウェアPWMの限界**：RPi.GPIO/gpiozero等でのPWMは負荷や他プロセスの影響を受け、SG90では角度の微振動（ハンチング）が目立つケースが多い。
- **Pi 5のpigpio対応状況**：DMA駆動による高精度PWMで定評のあるpigpioはPi 5では未対応（または不安定）報告があり、現時点では安定運用が難しい可能性がある。

> まとめ：**PWM生成はOSから切り離し（ハード/外付けへオフロード）**、制御ループは**可変サンプリング（dt補正）**で設計する方針が現実的。

---

## 3. 解決策の選択肢

### 3.1 ソフト面の対策（制御ループ）
- **動的dtでの制御**：毎ループで`dt = 現在時刻 − 前回時刻`を測定し、比例・積分・微分の算出にdtを反映すれば、固定周期を仮定しなくても安定性が確保しやすい。

### 3.2 ハード面の対策（PWM生成）
**PCA9685（I²Cサーボドライバ）のみを用いる方針**とし、ドライバは以下の**HAT製品（実装済み）**を採用する。

- **Adafruit 16-Channel PWM / Servo HAT for Raspberry Pi - Mini Kit**  
  製品ページ: https://www.adafruit.com/product/2327?srsltid=AfmBOoo7yLWqbkozOyCfN7pSpXl6FgWqzOT84Mp6_bRgnqJGACO_nEdp

**採用理由と利点**
- **ジッタ回避**：PCA9685がハードウェアで50〜60HzのPWMを独立生成。Pi側はI²Cで角度指令を送るのみ。
- **高分解能**：12-bit（4096 step）で1〜2ms域のパルス幅を安定出力。SG90等のホビーサーボに最適。
- **拡張性**：16chまで拡張可能。Pan/Tilt以外に照明や追加アクチュエータも同一HATで制御。
- **実装容易**：Adafruit CircuitPythonの`ServoKit`により`servo[i].angle = θ`の一行で角度制御が可能。

**配線・電源方針（要点）**
- HATのV+（サーボ電源）には**外部5V（2A以上）**を供給し、Raspberry Pi 5V系とは**分離**。GNDは**共通化**。
- I²Cは標準のGPIO2（SDA）/GPIO3（SCL）を使用。

---

## 4. 制御方式の検討（PID vs. 単純P）
本案件では**単純P制御**を採用する。実装の具体像は、SunFounder PiCar‑X の顔追跡サンプル（Python）にある比例制御ロジックを参考にする：

- 参照：SunFounder PiCar‑X 顔追跡（Python）  
  https://docs.sunfounder.com/projects/picar-x/ja/latest/python/python_stare_at_you.html

**実装方針（本件への当てはめ）**
1. **誤差計算**：YOLOの検出バウンディングボックス中心 `(cx, cy)` と画面中心 `(W/2, H/2)` との差分を `error_x, error_y` とする。
2. **比例変換**：`Δpan = -Kp_pan * error_x`、`Δtilt = +Kp_tilt * error_y` として角度を更新。符号は座標系に合わせる。
3. **角度制限・デッドバンド**：`[0, 180]` などの範囲にクリップ。微小揺れ防止に `abs(error) < ε` なら**無動作**（例：ε=10px）。
4. **スムージング（任意）**：`Δθ` に低域フィルタ（例：`Δθ_f = α*Δθ + (1-α)*Δθ_prev`）を適用し、急峻なステップを抑制。
5. **更新周期**：本用途は低頻度で良い。連続追従する場合でも**10Hz以下**で十分。数分単位のイベント駆動であれば必要時のみ1回更新。
6. **Kp調整**：`Kp ≈ (画像幅/可動角) × 減衰係数` を初期目安に、小さめ（例0.02）から試し、オーバーシュート・振動を見ながら増減。

> 補足：積分・微分は不要。整定誤差が気になる場合だけ `I += error*dt` を加える簡易PIで対応可能。

---

## 5. 推奨アーキテクチャ
1. **PWM生成**：上記Adafruit HAT（PCA9685）。サーボ用電源（5V系）はPiから分離し、GND共通。
2. **制御ループ**：Pi（Python）でYOLO推論→目標中心座標→誤差計算→比例計算→角度コマンドをI²C送信。更新周期は10Hz以下（またはイベント駆動）。

---

## 6. ハード構成と配線

### 6.1 配線（例）
| 信号/電源 | 接続先 |
|---|---|
| HAT VCC | Raspberry Pi 3.3V |
| HAT GND & Servo GND | Raspberry Pi GND（**Piとサーボ電源のGND共通化**）|
| SDA/SCL | Pi GPIO2 (SDA) / GPIO3 (SCL) |
| V+（サーボ電源） | 外部5V電源（2A以上推奨）|
| CH0 / CH1 | SG90（Pan / Tilt）|

> 注意：サーボの突入電流によりPiの電源がドロップしないよう**サーボ用5Vは別系統**を推奨。

---

## 7. ソフトウェア実装（骨格）

### 7.1 依存パッケージ
```bash
sudo pip3 install adafruit-circuitpython-pca9685 adafruit-circuitpython-servokit
```

### 7.2 単純P制御のサンプル（SunFounderロジックを参考に）
```python
import time, busio, board
from adafruit_servokit import ServoKit

# --- HW 初期化 ---
i2c  = busio.I2C(board.SCL, board.SDA)
kit  = ServoKit(channels=16, i2c=i2c)
pan_servo, tilt_servo = kit.servo[0], kit.servo[1]

# 角度の初期値
pan_servo.angle  = 90
tilt_servo.angle = 90

# --- P制御パラメータ／設定 ---
Kp_pan, Kp_tilt = 0.02, 0.02
FRAME_W, FRAME_H = 640, 480
DEADBAND = 10  # px: 微小揺れ防止

# YOLOの検出中心を返す関数（無検出時 None）
def get_target_center():
    return None  # TODO: 実装

while True:
    tgt = get_target_center()
    if tgt is not None:
        cx, cy = tgt
        error_x = cx - FRAME_W/2
        error_y = cy - FRAME_H/2

        if abs(error_x) > DEADBAND:
            pan_servo.angle = max(min((pan_servo.angle or 90) - Kp_pan*error_x, 180), 0)
        if abs(error_y) > DEADBAND:
            tilt_servo.angle = max(min((tilt_servo.angle or 90) + Kp_tilt*error_y, 180), 0)

    time.sleep(0.1)  # 10Hz（用途によりさらに低頻度で可）
```

### 7.3 Kpの初期目安
- 近似：`Kp ≈ (画像幅[px] / 可動角[deg]) × 減衰係数`
- 例：640px/180° ≈ 3.56（1px ≈ 0.28°）。実運用では**1/50〜1/100**（例：**0.02**）から開始。
- 目視でオーバーシュートや振動が出ない範囲まで徐々に増減。

---

## 8. 本案件に対する最終提案（rev4）
1. **Adafruit 16ch Servo HAT（PCA9685）を正式採用**：PWM生成を完全オフロードし、ジッタ要因を排除。
2. **単純P制御**：SunFounder PiCar‑Xの顔追跡ロジックを参考に、誤差×Kpで角度更新。デッドバンドと角度クリップを必須化。
3. **更新頻度は低く**：10Hz以下、またはイベント駆動（数分単位）運用。
4. **電源分離**：5Vサーボ電源をPiから分離し、GND共通。

---

## 9. 参考情報（代表URL）
- SunFounder PiCar‑X 顔追跡（Python）  
  https://docs.sunfounder.com/projects/picar-x/ja/latest/python/python_stare_at_you.html
- Adafruit 16-Channel PWM / Servo HAT for Raspberry Pi - Mini Kit  
  https://www.adafruit.com/product/2327?srsltid=AfmBOoo7yLWqbkozOyCfN7pSpXl6FgWqzOT84Mp6_bRgnqJGACO_nEdp
- Adafruit PCA9685 Servo Driver（一般解説）  
  https://learn.adafruit.com/16-channel-pwm-servo-driver
- Adafruit CircuitPython ServoKit（Python API）  
  https://docs.circuitpython.org/projects/servokit/en/latest/

