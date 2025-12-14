# オブジェクト検出・追跡仕様書

**バージョン**: 1.0
**作成日**: 2025-12-14
**プロジェクト名**: 12-002-pet-monitoring-yolov8
**関連ドキュメント**:
- `servo_control_specification.md` - サーボ制御仕様
- `raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md` - P制御設計レポート

---

## 1. 概要

### 1.1 目的
本仕様書は、YOLOv8による物体検出とP制御による追跡アルゴリズムを定義する。
ペット（犬・猫）を自動検出し、カメラの向きを調整してペットを画角中央に捉え続けることを目的とする。

### 1.2 システム構成
```
カメラ映像
    ↓
YOLOv8物体検出
    ↓
バウンディングボックス取得
    ↓
中心座標計算
    ↓
P制御で目標角度計算
    ↓
サーボ制御ライブラリへ指令
    ↓
カメラ向き調整
```

### 1.3 設計方針
- **リアルタイム性**: 10Hz以下の更新頻度で十分（数分単位のイベント駆動も可）
- **制御方式**: 単純P制御（比例制御のみ、I・D成分は不使用）
- **安定性**: デッドバンド機構による微小振動防止
- **検出精度**: YOLOv8の信頼度ベース検出

---

## 2. YOLOv8 物体検出

### 2.1 YOLOv8とは
**YOLO (You Only Look Once)** は、リアルタイム物体検出アルゴリズムの一種。
YOLOv8はUltralyticsが開発した最新バージョンで、高速かつ高精度な検出が可能。

**特徴**:
- **単一ステージ検出**: 1回のニューラルネットワーク処理で複数物体を検出
- **バウンディングボックス**: 各物体を矩形で囲む
- **クラス分類**: 物体の種類（犬、猫、人など）を識別
- **信頼度スコア**: 検出の確からしさを0.0～1.0で出力

### 2.2 使用モデル
| 項目 | 仕様 |
|------|------|
| モデル | YOLOv8n (nano) |
| モデルファイル | yolov8n.pt |
| 学習データセット | COCO (Common Objects in Context) |
| 検出可能クラス数 | 80クラス |
| 入力サイズ | 640x640 (自動リサイズ) |
| 推論速度 | Raspberry Pi 5で約1～3 FPS |

**YOLOv8nを選択する理由**:
- 最軽量モデルで、Raspberry Pi 5でも動作可能
- ペット検出には十分な精度
- メモリ消費量が少ない

### 2.3 検出対象クラス

COCOデータセットのクラスID:
| クラスID | クラス名 | 説明 |
|---------|---------|------|
| 15 | cat | 猫 |
| 16 | dog | 犬 |

**実装**:
```python
self.target_classes = [15, 16]  # 猫と犬のみ
```

### 2.4 検出プロセス

#### 2.4.1 検出の流れ
```python
def _detect_pet(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    # 1. YOLOv8で推論実行
    results = self.model(frame, verbose=False)

    # 2. 検出結果から最も信頼度の高いペットを選択
    best_box = None
    best_conf = 0.0

    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])      # クラスID
            conf = float(box.conf[0])   # 信頼度

            # ターゲットクラス（犬・猫）かつ最高信頼度
            if cls in self.target_classes and conf > best_conf:
                best_conf = conf
                xyxy = box.xyxy[0].cpu().numpy()
                best_box = (int(xyxy[0]), int(xyxy[1]),
                           int(xyxy[2]), int(xyxy[3]))

    return best_box  # (x1, y1, x2, y2) or None
```

#### 2.4.2 バウンディングボックス
検出結果は以下の形式で返される：
```
(x1, y1, x2, y2)
```
- `x1, y1`: 矩形の左上座標
- `x2, y2`: 矩形の右下座標

**中心座標の計算**:
```python
cx = (x1 + x2) // 2  # 中心のX座標
cy = (y1 + y2) // 2  # 中心のY座標
```

### 2.5 検出パラメータ

| パラメータ | デフォルト値 | 説明 |
|----------|------------|------|
| verbose | False | 推論時の詳細ログを抑制 |
| conf_threshold | (自動) | 信頼度の閾値（YOLOv8デフォルト使用） |

**注意事項**:
- 複数のペットが検出された場合、**最も信頼度の高い1体のみ**を追跡
- 信頼度が低い検出は自動的に除外される

---

## 3. P制御による追跡

### 3.1 P制御とは

**P制御（比例制御、Proportional Control）** は、最もシンプルなフィードバック制御方式。

**制御式**:
```
制御量 = Kp × 誤差
```

- `Kp`: 比例ゲイン（制御の強さを決定するパラメータ）
- `誤差`: 目標値と現在値の差

**特徴**:
- ✅ 実装がシンプル
- ✅ 応答が速い
- ✅ 調整パラメータが1つだけ
- ⚠️ 定常偏差が残る可能性（本用途では許容）
- ⚠️ Kpが大きすぎると振動・オーバーシュート

### 3.2 本システムでのP制御実装

#### 3.2.1 誤差の計算
```python
# 画面中央座標
center_x = frame_width / 2   # 例: 640 / 2 = 320
center_y = frame_height / 2  # 例: 480 / 2 = 240

# ペット（バウンディングボックス）の中心座標
pet_center_x, pet_center_y = get_box_center(box)

# 誤差 = ペット位置 - 画面中央
error_x = pet_center_x - center_x  # 水平方向の誤差（ピクセル）
error_y = pet_center_y - center_y  # 垂直方向の誤差（ピクセル）
```

**誤差の意味**:
- `error_x > 0`: ペットが画面右側にいる → カメラを右に動かす
- `error_x < 0`: ペットが画面左側にいる → カメラを左に動かす
- `error_y > 0`: ペットが画面下側にいる → カメラを下に動かす
- `error_y < 0`: ペットが画面上側にいる → カメラを上に動かす

#### 3.2.2 制御量の計算
```python
delta_pan = -Kp_pan * error_x   # パンの変化量（度）
delta_tilt = Kp_tilt * error_y  # チルトの変化量（度）
```

**符号の調整**:
- パンは **マイナス符号** を付ける（座標系の向きを調整）
- チルトは **プラス符号** のまま

#### 3.2.3 角度の更新
```python
# 新しい角度を計算
new_pan_angle = current_pan_angle + delta_pan
new_tilt_angle = current_tilt_angle + delta_tilt

# 角度範囲にクリップ（0～180度）
new_pan_angle = max(0, min(180, new_pan_angle))
new_tilt_angle = max(0, min(180, new_tilt_angle))

# サーボに指令
pan_servo.angle = new_pan_angle
tilt_servo.angle = new_tilt_angle
```

### 3.3 デッドバンド（不感帯）

**目的**: 微小な誤差による細かい揺れ（ジッタ）を防止

**実装**:
```python
DEADBAND = 10  # ピクセル

if abs(error_x) > DEADBAND:
    # 誤差が閾値を超えた場合のみ制御
    delta_pan = -Kp_pan * error_x
    pan_angle += delta_pan
else:
    # 誤差が小さい場合は何もしない
    pass
```

**効果**:
- ±10ピクセル以内の誤差は無視
- サーボの無駄な動作を削減
- 消費電力削減
- 機構への負荷軽減

### 3.4 制御パラメータ

| パラメータ | デフォルト値 | 説明 |
|----------|------------|------|
| Kp_pan | 0.02 | パン制御の比例ゲイン |
| Kp_tilt | 0.02 | チルト制御の比例ゲイン |
| DEADBAND | 10 px | 不感帯の幅 |

#### 3.4.1 Kpの調整ガイド

**初期値の計算式**:
```
Kp ≈ (画像幅[px] / 可動角[deg]) × 減衰係数
```

**例**:
- 画像幅: 640 px
- 可動角: 180 度
- 1ピクセルあたり: 640 / 180 ≈ 3.56 px/deg → 約0.28 deg/px
- 減衰係数: 1/50 ～ 1/100
- **Kp初期値: 0.02 ～ 0.04**

**調整手順**:
1. **Kp = 0.02** から開始
2. 追跡動作を観察
   - 応答が遅い場合: Kpを増やす（0.03, 0.04...）
   - 振動・オーバーシュートが発生する場合: Kpを減らす（0.015, 0.01...）
3. 安定して中央に収束するまで調整

**目標**:
- オーバーシュートなし
- 振動なし
- 1～2秒で中央に収束

### 3.5 更新周期

| 項目 | 仕様 |
|------|------|
| 追跡ループ周波数 | 10 Hz (デフォルト) |
| フレーム間隔 | 0.1 秒 |
| 最小周波数 | 1 Hz 以下でも動作可能 |

**実装**:
```python
tracking_fps = 10.0
frame_delay = 1.0 / tracking_fps  # 0.1秒

while tracking:
    loop_start = time.time()

    # 検出・制御処理
    process_tracking()

    # 次のフレームまで待機
    elapsed = time.time() - loop_start
    if elapsed < frame_delay:
        time.sleep(frame_delay - elapsed)
```

---

## 4. スキャン機能

### 4.1 目的
可動域全体を探索してペットを発見する。

### 4.2 スキャンアルゴリズム

```
チルト（上下）を段階的に変更
    ↓
各チルト位置で、パン（左右）を段階的に変更
    ↓
各位置でフレームを取得してYOLOv8検出
    ↓
ペット検出 → 追跡モードへ移行
ペット未検出 → 次の位置へ
```

**疑似コード**:
```python
for tilt_angle in range(30, 150, step_tilt):
    move_tilt(tilt_angle)
    wait_stabilization(0.3秒)

    for pan_angle in range(0, 180, step_pan):
        move_pan(pan_angle)
        wait_stabilization(0.2秒)

        frame = capture()
        if detect_pet(frame):
            return True  # 検出成功、追跡へ

return False  # 検出失敗
```

### 4.3 スキャンパラメータ

| パラメータ | デフォルト値 | 説明 |
|----------|------------|------|
| scan_steps_pan | 9 | パン軸のステップ数 |
| scan_steps_tilt | 5 | チルト軸のステップ数 |
| パン範囲 | 0～180度 | 探索範囲（水平） |
| チルト範囲 | 30～150度 | 探索範囲（垂直） |
| パン待機時間 | 0.2秒 | 各パン位置での安定待機 |
| チルト待機時間 | 0.3秒 | 各チルト位置での安定待機 |

**スキャン時間の計算**:
```
総時間 ≈ scan_steps_tilt × (0.3秒 + scan_steps_pan × 0.2秒)
      ≈ 5 × (0.3 + 9 × 0.2)
      ≈ 5 × 2.1
      ≈ 10.5秒
```

### 4.4 スキャンパターン

```
チルト30度  →→→→→→→→→ (パン0→180度)
チルト60度  →→→→→→→→→
チルト90度  →→→→→→→→→
チルト120度 →→→→→→→→→
チルト150度 →→→→→→→→→
```

---

## 5. 追跡フェーズ

### 5.1 追跡プロセス

```
1. ペット検出（スキャンで発見）
    ↓
2. 追跡ループ開始（指定時間）
    ↓
3. フレーム取得
    ↓
4. YOLOv8でペット検出
    ↓
5. 検出成功
   ├─ Yes → P制御で角度更新
   └─ No  → サーボ停止（前回位置を維持）
    ↓
6. 追跡時間終了まで繰り返し
```

### 5.2 追跡パラメータ

| パラメータ | デフォルト値 | 説明 |
|----------|------------|------|
| tracking_duration | 8.0秒 | 追跡を継続する時間 |
| tracking_fps | 10 Hz | 追跡ループの更新周波数 |

**実装例**:
```python
def track_pet(duration=8.0, fps=10.0):
    start_time = time.time()
    frame_delay = 1.0 / fps

    while time.time() - start_time < duration:
        loop_start = time.time()

        # フレーム取得
        frame = capture()

        # ペット検出
        box = detect_pet(frame)
        if box is not None:
            # 中心座標取得
            cx, cy = get_box_center(box)

            # 誤差計算
            error_x = cx - frame_width / 2
            error_y = cy - frame_height / 2

            # P制御で角度更新
            update_servo_angles(error_x, error_y)

        # フレームレート維持
        elapsed = time.time() - loop_start
        if elapsed < frame_delay:
            time.sleep(frame_delay - elapsed)
```

### 5.3 ロスト時の挙動

ペットが画角から外れた場合:
- **現在の実装**: サーボを停止、前回位置を維持
- **将来の拡張案**:
  - 最後に検出した方向へゆっくり移動
  - 再スキャンを実施
  - タイムアウト後にホームポジション復帰

---

## 6. 画像キャプチャ機能

### 6.1 目的
追跡中のペット画像を記録し、Slack通知用に保存する。

### 6.2 キャプチャ処理フロー

```
1. 追跡完了後にキャプチャ開始
    ↓
2. フレーム取得
    ↓
3. 画像リサイズ（長辺を指定サイズに）
    ↓
4. JPEG圧縮
    ↓
5. ファイル保存
    ↓
6. 指定枚数まで繰り返し
```

### 6.3 キャプチャパラメータ

| パラメータ | デフォルト値 | 説明 |
|----------|------------|------|
| count | 3 | 撮影枚数 |
| long_edge | 800 px | リサイズ後の長辺サイズ |
| jpeg_quality | 70 | JPEG圧縮品質（0～100） |
| interval | 0.5秒 | 撮影間隔 |

### 6.4 リサイズアルゴリズム

**目的**: ファイルサイズを削減し、Slack通知の転送量を最小化

**アスペクト比維持リサイズ**:
```python
height, width = frame.shape[:2]

if width > height:
    # 横長画像
    new_width = long_edge
    new_height = int(height * long_edge / width)
else:
    # 縦長画像
    new_height = long_edge
    new_width = int(width * long_edge / height)

resized = cv2.resize(frame, (new_width, new_height))
```

**例**:
- 元画像: 640x480
- 長辺: 800
- リサイズ後: 800x600

### 6.5 ファイル命名規則

```
pet_<timestamp>_<sequence>.jpg
```

**例**:
```
pet_20251214_143025_123_1.jpg
pet_20251214_143025_623_2.jpg
pet_20251214_143026_123_3.jpg
```

- `timestamp`: YYYYmmdd_HHMMSS_fff（ミリ秒まで）
- `sequence`: 撮影順序（1, 2, 3...）

### 6.6 JPEG圧縮

| 品質値 | 説明 | ファイルサイズ目安 |
|-------|------|-----------------|
| 90-100 | 最高品質 | 大きい（200KB～） |
| 70-80 | 高品質 | 中程度（50～150KB） |
| 50-60 | 標準品質 | 小さい（30～80KB） |
| 30-40 | 低品質 | 非常に小さい（～50KB） |

**デフォルト値70の理由**:
- 安全確認に十分な画質
- ファイルサイズとのバランスが良い
- Slack通知の転送負荷が小さい

---

## 7. CameraTrackerクラス API仕様

### 7.1 コンストラクタ

```python
def __init__(
    self,
    model_path: str = "yolov8n.pt",
    camera_index: int = 0,
    frame_width: int = 640,
    frame_height: int = 480,
    pan_channel: int = 0,
    tilt_channel: int = 1,
    kp_pan: float = 0.02,
    kp_tilt: float = 0.02,
    deadband: int = 10,
)
```

| パラメータ | 型 | デフォルト値 | 説明 |
|----------|---|------------|------|
| model_path | str | "yolov8n.pt" | YOLOv8モデルファイルのパス |
| camera_index | int | 0 | カメラデバイスのインデックス |
| frame_width | int | 640 | フレーム幅 |
| frame_height | int | 480 | フレーム高さ |
| pan_channel | int | 0 | パンサーボのチャンネル |
| tilt_channel | int | 1 | チルトサーボのチャンネル |
| kp_pan | float | 0.02 | パンのP制御ゲイン |
| kp_tilt | float | 0.02 | チルトのP制御ゲイン |
| deadband | int | 10 | デッドバンド幅（px） |

### 7.2 scan_and_track()

```python
def scan_and_track(
    self,
    scan_steps_pan: int = 9,
    scan_steps_tilt: int = 5,
    tracking_duration: float = 8.0,
    tracking_fps: float = 10.0,
) -> bool
```

**機能**: 全域スキャン→ペット検出→追跡

**戻り値**:
- `True`: ペットを検出して追跡した
- `False`: ペットが見つからなかった

**例外**:
- `RuntimeError`: カメラが開けない場合

### 7.3 capture_images()

```python
def capture_images(
    self,
    save_dir: str,
    count: int = 3,
    long_edge: int = 800,
    jpeg_quality: int = 70,
    interval: float = 0.5,
) -> List[str]
```

**機能**: 静止画を撮影してリサイズ・圧縮保存

**戻り値**: 保存したファイルパスのリスト

**例外**:
- `RuntimeError`: カメラが開けない場合

### 7.4 reset_position()

```python
def reset_position(self) -> None
```

**機能**: サーボを中央位置（90度）にリセット

### 7.5 cleanup()

```python
def cleanup(self) -> None
```

**機能**: リソースのクリーンアップ（カメラ解放、サーボリセット）

---

## 8. 使用例

### 8.1 基本的な使用方法

```python
from camera_tracker import CameraTracker

# トラッカー初期化
tracker = CameraTracker(
    model_path="yolov8n.pt",
    kp_pan=0.02,
    kp_tilt=0.02,
    deadband=10
)

# スキャン→追跡
detected = tracker.scan_and_track(
    scan_steps_pan=9,
    scan_steps_tilt=5,
    tracking_duration=8.0
)

if detected:
    # 画像キャプチャ
    image_paths = tracker.capture_images(
        save_dir="./captured_images",
        count=3,
        long_edge=800,
        jpeg_quality=70
    )
    print(f"Captured {len(image_paths)} images")
else:
    print("No pet detected")

# クリーンアップ
tracker.cleanup()
```

### 8.2 カスタムパラメータ

```python
# より高速な追跡
tracker = CameraTracker(
    kp_pan=0.04,  # ゲインを2倍に
    kp_tilt=0.04,
    deadband=5    # デッドバンドを狭く
)

# より細かいスキャン
detected = tracker.scan_and_track(
    scan_steps_pan=15,   # ステップ数を増加
    scan_steps_tilt=8,
    tracking_duration=10.0  # 追跡時間を延長
)
```

---

## 9. パフォーマンス最適化

### 9.1 YOLOv8推論速度

| デバイス | FPS | 備考 |
|---------|-----|------|
| Raspberry Pi 5 | 1～3 FPS | YOLOv8n使用時 |
| PC (CPU) | 10～20 FPS | 参考値 |
| GPU搭載PC | 30+ FPS | 参考値 |

**最適化案**:
- モデルをONNX形式に変換
- 入力サイズを小さくする（320x320など）
- フレームスキップ（2フレームに1回推論）

### 9.2 メモリ使用量

| 項目 | 使用量 |
|------|--------|
| YOLOv8nモデル | 約10 MB |
| フレームバッファ | 約1 MB |
| 合計 | 約50～100 MB |

---

## 10. トラブルシューティング

### 10.1 ペットが検出されない

**原因**:
- 照明が暗い
- ペットが小さすぎる（遠い）
- YOLOの信頼度が低い

**対処**:
- 照明を明るくする
- カメラとペットの距離を調整
- スキャンステップ数を増やす

### 10.2 追跡が不安定（振動する）

**原因**:
- Kpが大きすぎる
- デッドバンドが小さすぎる

**対処**:
```python
tracker = CameraTracker(
    kp_pan=0.01,   # ゲインを下げる
    kp_tilt=0.01,
    deadband=15    # デッドバンドを広げる
)
```

### 10.3 追跡が遅い（応答が鈍い）

**原因**:
- Kpが小さすぎる
- デッドバンドが大きすぎる

**対処**:
```python
tracker = CameraTracker(
    kp_pan=0.03,   # ゲインを上げる
    kp_tilt=0.03,
    deadband=5     # デッドバンドを狭める
)
```

### 10.4 YOLOv8推論が遅い

**原因**:
- Raspberry Piの処理能力限界

**対処**:
- YOLOv8nを使用（最軽量モデル）
- 追跡FPSを下げる（10 Hz → 5 Hz）
- フレームサイズを小さくする（640x480 → 320x240）

---

## 11. 将来の拡張案

### 11.1 マルチターゲット追跡
現在は最も信頼度の高い1体のみ追跡。複数ペットの同時追跡に対応。

### 11.2 PID制御への拡張
I（積分）成分を追加して定常偏差を削減。

```python
# I成分の追加
integral_x += error_x * dt
delta_pan = -(Kp * error_x + Ki * integral_x)
```

### 11.3 適応的ゲイン調整
ペットの大きさや移動速度に応じてKpを自動調整。

### 11.4 学習ベース追跡
YOLOv8に加えて、追跡専用アルゴリズム（DeepSORT等）を導入。

---

## 12. 参考資料

### 12.1 関連ドキュメント
- `servo_control_specification.md` - サーボ制御仕様
- `pet_monitoring_requirements.md` - 要件定義書
- `raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md` - P制御設計

### 12.2 外部リソース
- **YOLOv8公式**: https://docs.ultralytics.com/
- **COCOデータセット**: https://cocodataset.org/
- **SunFounder PiCar-X 顔追跡**: https://docs.sunfounder.com/projects/picar-x/ja/latest/python/python_stare_at_you.html
- **OpenCV公式**: https://opencv.org/

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0 | 2025-12-14 | 初版作成 |
