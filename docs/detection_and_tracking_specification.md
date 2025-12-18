# オブジェクト検出・追跡仕様書

**バージョン**: 1.1
**作成日**: 2025-12-14
**更新日**: 2025-12-17
**プロジェクト名**: 12-002-pet-monitoring-yolov8
**関連ドキュメント**:
- `servo_control_specification.md` - サーボ制御仕様
- `raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md` - P制御設計レポート
- `p_control_tracking_technical_report.md` - P制御追跡 技術検討レポート

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
- **安定性**: 角度制限による急峻な動作の防止
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
| モデル | YOLOv8s (Hailo-8L最適化版) |
| モデルファイル | yolov8s_h8l.hef |
| 学習データセット | COCO (Common Objects in Context) |
| 検出可能クラス数 | 80クラス |
| 入力サイズ | 640x640 (自動リサイズ) |
| AIアクセラレータ | Hailo-8L使用 |
| 推論速度 | 10+ FPS（Hailo-8Lアクセラレーション時） |

**YOLOv8s + Hailo-8Lを選択する理由**:
- Hailo-8Lアクセラレータによる高速推論
- Raspberry Pi 5でリアルタイム検出が可能
- ペット検出に十分な精度と速度のバランス

### 2.3 検出対象クラス

COCOデータセットのクラスID:
| クラスID | クラス名 | 説明 |
|---------|---------|------|
| 15 | cat | 猫 |
| 16 | dog | 犬 |

**実装**:
```python
# Hailo8Lライブラリで初期化時に指定
self.detector = YOLODetector(model_path, target_classes=['cat', 'dog'])
```

#### 2.3.1 検出対象クラスの変更方法

デフォルトでは犬（dog）と猫（cat）を検出対象としていますが、コマンドラインオプションで変更可能です。

**使用可能なクラス一覧を表示**:
```bash
python camera_tracker.py --list-classes
```

**変更例**:
```bash
# 人物のみを検出
python camera_tracker.py --classes person

# 人物・犬・猫を検出
python camera_tracker.py --classes person cat dog

# 鳥を検出
python camera_tracker.py --classes bird
```

**プログラムからの変更**:
```python
from camera_tracker import CameraTracker

# 人物を検出対象に設定
tracker = CameraTracker(
    model_path="models/yolov8s_h8l.hef",
    target_classes=['person']
)

# 複数クラスを検出対象に設定
tracker = CameraTracker(
    model_path="models/yolov8s_h8l.hef",
    target_classes=['person', 'cat', 'dog']
)
```

**主なCOCOクラス（ペット監視で有用なもの）**:
| クラス名 | 説明 | 用途例 |
|---------|------|-------|
| person | 人物 | 不審者検知、来客検知 |
| cat | 猫 | ペット監視 |
| dog | 犬 | ペット監視 |
| bird | 鳥 | 小動物監視 |

### 2.4 検出プロセス

#### 2.4.1 検出の流れ
```python
def _detect_pet(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    # Hailo-8L検出器で物体検出を実行（犬・猫のみフィルタリング済み）
    detections = self.detector.detect(frame)

    best_box = None
    best_conf = 0.0

    for det in detections:
        conf = det['confidence']
        if conf > best_conf:
            best_conf = conf
            bbox = det['bbox']  # [x1, y1, x2, y2]
            best_box = (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))

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

# 角度変化量の制限（急峻な動きを防止）
delta_pan = max(-delta_angle_max, min(delta_angle_max, delta_pan))
delta_tilt = max(-delta_angle_max, min(delta_angle_max, delta_tilt))
```

**符号の調整**:
- パンは **マイナス符号** を付ける（座標系の向きを調整）
- チルトは **プラス符号** のまま

**角度変化量の制限**:
- 1回の更新での角度変化を制限することで、急峻な動作を防止
- サーボ内部制御との干渉を低減し、オーバーシュートを防止

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
# デッドバンドが未指定の場合は画面幅の4%を使用
if deadband is None:
    self.deadband = int(0.04 * frame_width)  # 640px → 25px
else:
    self.deadband = deadband

if abs(error_x) > self.deadband:
    # 誤差が閾値を超えた場合のみ制御
    delta_pan = -Kp_pan * error_x
    pan_angle += delta_pan
else:
    # 誤差が小さい場合は何もしない
    pass
```

**デッドバンドの設計根拠**:
- 画面幅の3～5%を推奨（技術検討レポート参照）
- YOLOの検出揺らぎ（数px～数十px）に対する過剰応答を抑止
- 中心付近で安定した挙動を実現

**効果**:
- デッドバンド以内の誤差は無視
- サーボの無駄な動作を削減
- 消費電力削減
- 機構への負荷軽減

### 3.4 制御パラメータ

| パラメータ | デフォルト値 | 説明 |
|----------|------------|------|
| Kp_pan | 0.01 | パン制御の比例ゲイン |
| Kp_tilt | 0.01 | チルト制御の比例ゲイン |
| deadband | 40ピクセル | 不感帯の幅 |
| delta_angle_max | 1.0度 | 1回の更新での最大角度変化量 |
| fps | 5.0 Hz | 追跡ループの更新頻度 |

**実機検証済みパラメータ（2025-12-18）**:

上記のデフォルト値は実機テストで安定動作を確認したパラメータです。

| パラメータ | 初期値 | 最終値 | 調整理由 |
|-----------|--------|--------|---------|
| Kp | 0.02 | 0.01 | ハンチング（発振）防止 |
| deadband | 25px | 40px | 微小振動の抑制 |
| delta_angle_max | 3.0° | 1.0° | オーバーシュート防止 |
| fps | 10 Hz | 5 Hz | サーボ安定化時間の確保 |

これらのパラメータは以下の条件で検証されました：
- ハードウェア: Raspberry Pi 5 + PCA9685 + SG90サーボ
- 検出対象: 人間（person）
- カメラ: Raspberry Pi Camera Module V3（上下反転設置）

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

#### 3.4.2 角度制限（Δθ_max）の調整ガイド

**目的**:
- 大誤差時の急峻な指令を抑止
- サーボ内部制御との干渉を低減
- オーバーシュートの防止

**効果**:
- 1回の更新で変化させる角度に上限を設けることで、急激な動作を防止
- 非リアルタイムOS（Linux）環境でも安定した挙動を実現
- サーボの内部制御ループとの干渉を最小化

**調整手順**:
1. **delta_angle_max = 3.0度** から開始（推奨初期値）
2. 追跡動作を観察
   - 追従が遅すぎる場合: 値を増やす（4.0度まで）
   - オーバーシュート・振動が発生する場合: 値を減らす（2.0度まで）
3. デッドバンド近傍で自然に減速する挙動を確認

**設計根拠**:
- 技術検討レポート（`p_control_tracking_technical_report.md`）参照
- SG90クラスのサーボでは 2～4度/update を推奨
- 周期ジッタの影響を吸収し、安定性を向上

### 3.5 更新周期

| 項目 | 仕様 |
|------|------|
| 追跡ループ周波数 | 5 Hz (デフォルト) |
| フレーム間隔 | 0.2 秒 |
| 最小周波数 | 1 Hz 以下でも動作可能 |

**実装**:
```python
tracking_fps = 5.0
frame_delay = 1.0 / tracking_fps  # 0.2秒

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
| tracking_fps | 5 Hz | 追跡ループの更新周波数 |

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
    model_path: str = "models/yolov8s_h8l.hef",
    camera_index: int = 0,
    frame_width: int = 640,
    frame_height: int = 480,
    pan_channel: int = 0,
    tilt_channel: int = 1,
    kp_pan: float = 0.02,
    kp_tilt: float = 0.02,
    deadband: Optional[int] = None,
    delta_angle_max: float = 3.0,
)
```

| パラメータ | 型 | デフォルト値 | 説明 |
|----------|---|------------|------|
| model_path | str | "models/yolov8s_h8l.hef" | YOLOv8 Hailo-8Lモデルファイルのパス |
| camera_index | int | 0 | カメラデバイスのインデックス |
| frame_width | int | 640 | フレーム幅 |
| frame_height | int | 480 | フレーム高さ |
| pan_channel | int | 0 | パンサーボのチャンネル |
| tilt_channel | int | 1 | チルトサーボのチャンネル |
| kp_pan | float | 0.01 | パンのP制御ゲイン |
| kp_tilt | float | 0.01 | チルトのP制御ゲイン |
| deadband | Optional[int] | 40 | デッドバンド幅（px） |
| delta_angle_max | float | 1.0 | 1回の更新での最大角度変化量（度） |

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

# トラッカー初期化（実機検証済みパラメータ）
tracker = CameraTracker(
    model_path="models/yolov8s_h8l.hef",
    kp_pan=0.01,
    kp_tilt=0.01,
    deadband=40,
    delta_angle_max=1.0
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

## 9. コマンドラインパラメータ一覧

`camera_tracker.py`は以下のコマンドラインパラメータをサポートしています。

### 9.1 基本パラメータ

| パラメータ | 型 | デフォルト値 | 説明 |
|-----------|------|-------------|------|
| `--model` | str | `models/yolov8s_h8l.hef` | HEFモデルファイルのパス |
| `--classes` | str (複数) | `cat dog` | 検出対象のクラス名（スペース区切り） |
| `--list-classes` | flag | - | 使用可能なクラス名一覧を表示して終了 |

### 9.2 カメラパラメータ

| パラメータ | 型 | デフォルト値 | 説明 |
|-----------|------|-------------|------|
| `--width` | int | `640` | カメラ画像の幅（ピクセル） |
| `--height` | int | `480` | カメラ画像の高さ（ピクセル） |
| `--flip` | flag | - | カメラ映像を上下反転（逆さま設置時） |

### 9.3 P制御パラメータ

| パラメータ | 型 | デフォルト値 | 説明 |
|-----------|------|-------------|------|
| `--kp-pan` | float | `0.01` | パン制御の比例ゲイン（大きいほど応答が速い） |
| `--kp-tilt` | float | `0.01` | チルト制御の比例ゲイン |
| `--deadband` | int | `40` | 不感帯（ピクセル）。この範囲内の誤差は無視 |
| `--delta-max` | float | `1.0` | 1回の更新での最大角度変化量（度） |

### 9.4 スキャン・追跡パラメータ

| パラメータ | 型 | デフォルト値 | 説明 |
|-----------|------|-------------|------|
| `--scan-pan` | int | `9` | パン軸のスキャンステップ数 |
| `--scan-tilt` | int | `5` | チルト軸のスキャンステップ数 |
| `--duration` | float | `8.0` | 追跡時間（秒）。`--continuous`使用時は無視 |
| `--fps` | float | `5.0` | 追跡ループの更新頻度（Hz） |
| `--continuous` | flag | - | 継続実行モード（Ctrl+C または qキーで終了） |

### 9.5 表示・ログパラメータ

| パラメータ | 型 | デフォルト値 | 説明 |
|-----------|------|-------------|------|
| `--display` | flag | - | カメラ映像をウィンドウに表示（qキーで終了） |
| `--log` | str | なし | デバッグログのCSVファイルパス |

### 9.6 画像キャプチャパラメータ

| パラメータ | 型 | デフォルト値 | 説明 |
|-----------|------|-------------|------|
| `--capture` | flag | - | 追跡後に画像をキャプチャする |
| `--capture-dir` | str | `captures` | キャプチャ画像の保存先ディレクトリ |
| `--capture-count` | int | `3` | キャプチャする画像の枚数 |

### 9.7 使用例

```bash
# 基本的な実行（デフォルト設定：犬・猫を検出、8秒追跡）
python camera_tracker.py

# 人物を検出対象に変更
python camera_tracker.py --classes person

# 映像を表示しながら継続実行
python camera_tracker.py --display --continuous

# P制御パラメータを調整（応答を速くする）
python camera_tracker.py --kp-pan 0.02 --kp-tilt 0.02 --deadband 20

# デバッグログを出力
python camera_tracker.py --log tracking.csv --display

# 追跡後に画像をキャプチャ
python camera_tracker.py --capture --capture-dir ./images --capture-count 5

# カメラを逆さまに設置した場合
python camera_tracker.py --flip

# 高解像度で実行
python camera_tracker.py --width 1280 --height 720
```

---

## 10. パフォーマンス最適化

### 10.1 YOLOv8推論速度

| デバイス | FPS | 備考 |
|---------|-----|------|
| Raspberry Pi 5 | 1～3 FPS | YOLOv8n使用時 |
| PC (CPU) | 10～20 FPS | 参考値 |
| GPU搭載PC | 30+ FPS | 参考値 |

**最適化案**:
- モデルをONNX形式に変換
- 入力サイズを小さくする（320x320など）
- フレームスキップ（2フレームに1回推論）

### 10.2 メモリ使用量

| 項目 | 使用量 |
|------|--------|
| YOLOv8nモデル | 約10 MB |
| フレームバッファ | 約1 MB |
| 合計 | 約50～100 MB |

---

## 11. トラブルシューティング

### 11.1 ペットが検出されない

**原因**:
- 照明が暗い
- ペットが小さすぎる（遠い）
- YOLOの信頼度が低い

**対処**:
- 照明を明るくする
- カメラとペットの距離を調整
- スキャンステップ数を増やす

### 11.2 追跡が不安定（振動する・ハンチング）

**原因**:
- Kpが大きすぎる
- デッドバンドが小さすぎる
- delta_angle_maxが大きすぎる
- FPSが高すぎる（サーボが安定する前に次の指令が来る）

**対処（実機検証済み）**:
```python
tracker = CameraTracker(
    kp_pan=0.01,   # ゲインを半分に
    kp_tilt=0.01,
    deadband=40,   # デッドバンドを広げる
    delta_angle_max=1.0  # 角度制限を厳しくする
)

# FPSも下げる
tracker.scan_and_track(tracking_fps=5.0)
```

**調整の優先順位**:
1. まずdelta_angle_maxを下げる（3.0 → 1.0度）
2. FPSを下げてサーボの安定化時間を確保（10 Hz → 5 Hz）
3. Kpを下げる（0.02 → 0.01）
4. 最後の手段としてdeadbandを広げる（25px → 40px）

**ハンチングの発生メカニズム**:
1. サーボが移動中にカメラ画像がぶれる
2. ぶれた画像で検出位置が変動
3. 変動した位置に対してさらにサーボが追従
4. この繰り返しで振動が増幅（正のフィードバック）

**解決のポイント**:
- FPSを下げてサーボが安定してから次のフレームを処理
- delta_angle_maxを下げて1回の移動量を制限
- Kpを下げて応答を穏やかにする

### 11.3 追跡が遅い（応答が鈍い）

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

### 11.4 YOLOv8推論が遅い

**原因**:
- Raspberry Piの処理能力限界

**対処**:
- YOLOv8nを使用（最軽量モデル）
- 追跡FPSを下げる（10 Hz → 5 Hz）
- フレームサイズを小さくする（640x480 → 320x240）

---

## 12. 将来の拡張案

### 12.1 マルチターゲット追跡
現在は最も信頼度の高い1体のみ追跡。複数ペットの同時追跡に対応。

### 12.2 PID制御への拡張
I（積分）成分を追加して定常偏差を削減。

```python
# I成分の追加
integral_x += error_x * dt
delta_pan = -(Kp * error_x + Ki * integral_x)
```

### 12.3 適応的ゲイン調整
ペットの大きさや移動速度に応じてKpを自動調整。

### 12.4 学習ベース追跡
YOLOv8に加えて、追跡専用アルゴリズム（DeepSORT等）を導入。

---

## 13. 参考資料

### 13.1 関連ドキュメント
- `servo_control_specification.md` - サーボ制御仕様
- `pet_monitoring_requirements.md` - 要件定義書
- `raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md` - P制御設計レポート
- `p_control_tracking_technical_report.md` - P制御追跡 技術検討レポート（デッドバンド・角度制限の設計根拠）

### 13.2 外部リソース
- **YOLOv8公式**: https://docs.ultralytics.com/
- **COCOデータセット**: https://cocodataset.org/
- **SunFounder PiCar-X 顔追跡**: https://docs.sunfounder.com/projects/picar-x/ja/latest/python/python_stare_at_you.html
- **OpenCV公式**: https://opencv.org/

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0 | 2025-12-14 | 初版作成 |
| 1.1 | 2025-12-17 | Hailo-8Lライブラリ対応、角度制限（delta_angle_max）追加、デッドバンド動的計算対応、技術検討レポート追加 |
| 1.2 | 2025-12-18 | 実機検証済みパラメータに更新（Kp=0.01, deadband=40px, delta_max=1.0°, fps=5Hz）、ハンチング対策追記 |
