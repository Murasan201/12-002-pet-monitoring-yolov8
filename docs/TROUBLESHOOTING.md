# トラブルシューティング

**プロジェクト**: 12-002-pet-monitoring-yolov8
**作成日**: 2025-12-17
**目的**: 環境構築・テスト・運用中に発生したエラーと解決策のナレッジベース

---

## 記録フォーマット

各問題は以下の形式で記録する：

```markdown
### 問題 X: [問題のタイトル]

**発生日**: YYYY-MM-DD

**発生状況**: [どのような操作・状況で発生したか]

**エラーメッセージ**:
```
[エラーメッセージ]
```

**原因**:
- [原因1]
- [原因2]

**解決策**:
```bash
[解決コマンド]
```

**確認方法**:
```bash
[確認コマンド]
```

**ステータス**: [x] 解決済み / [ ] 未解決
```

---

## 環境構築

（環境構築時のエラーをここに記録）

---

## Hailo-8L関連

（Hailo-8L AIアクセラレータ関連のエラーをここに記録）

---

## カメラ関連

### 問題 1: OpenCV VideoCaptureでフレームが取得できない

**発生日**: 2025-12-17

**発生状況**: camera_tracker.pyのテスト実行時、cv2.VideoCapture(0)でカメラを開いた後、cap.read()がFalseを返す

**エラーメッセージ**:
```
ERROR: Failed to read frame
```

**原因**:
- Raspberry Pi Camera Module V3（IMX708センサー）はlibcameraバックエンドを使用
- OpenCVのVideoCaptureはV4L2バックエンドを使用するため、libcameraカメラに直接アクセスできない
- Raspberry Pi OS BookwormではPicamera2がlibcameraの推奨インターフェース

**解決策**:
Picamera2を使用してカメラにアクセスする：
```python
from picamera2 import Picamera2
import cv2

picam2 = Picamera2()
config = picam2.create_still_configuration(main={'size': (640, 480)})
picam2.configure(config)
picam2.start()

# フレーム取得（RGB形式）
frame_rgb = picam2.capture_array()

# OpenCVで処理する場合はBGRに変換
frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

picam2.stop()
```

**確認方法**:
```bash
python3 -c "from picamera2 import Picamera2; p = Picamera2(); p.start(); f = p.capture_array(); print(f'OK: {f.shape}'); p.stop()"
```

**ステータス**: [x] 解決済み（camera_tracker.pyをPicamera2対応に修正完了）

---

## サーボ制御関連

（サーボモーター・PCA9685関連のエラーをここに記録）

---

## 物体検出関連

（YOLO検出・推論関連のエラーをここに記録）

---

## P制御・追跡関連

### 問題 2: パン（左右）サーボが逆方向に動作する

**発生日**: 2025-12-17

**発生状況**: camera_tracker.pyで追跡テスト実行時、検出対象が画面右側にいるのにカメラが左を向こうとする。結果としてパン角度が左端（35度）に張り付いて追従しない

**ログの症状**:
```csv
bbox_cx,error_x,raw_delta_pan,delta_pan,pan_angle
531,211.0,-4.220,-3.000,35.0
```
- error_x > 0（対象は右側）なのに delta_pan が負（左に動こうとする）
- pan_angle が 35.0（PAN_LEFT）に張り付いている

**原因**:
- P制御の符号が逆だった
- 誤: `raw_delta_pan = -self.kp_pan * error_x`
- 対象が右にいる時（error_x > 0）にパン角度を減らしていた

**解決策**:
P制御の符号を修正：
```python
# 修正前（誤）
raw_delta_pan = -self.kp_pan * error_x

# 修正後（正）
raw_delta_pan = self.kp_pan * error_x
```

論理：
- 対象が右（error_x > 0）→ パン角度を増やす → カメラが右を向く
- 対象が左（error_x < 0）→ パン角度を減らす → カメラが左を向く

**確認方法**:
```bash
# CSVログを有効にしてテスト実行
python3 camera_tracker.py --classes person --display --continuous --flip --log test.csv

# ログを確認：error_xの符号とdelta_panの符号が一致していることを確認
```

**ステータス**: [x] 解決済み

---

### 問題 3: チルト（上下）サーボが追従しない

**発生日**: 2025-12-17

**発生状況**: パンの修正後、チルトが追従しない問題が発覚。対象が画面下部にいる時間帯があったにも関わらず、tilt_angleが45度（TILT_DOWN）に張り付いて動かない

**ログの症状**:
```csv
bbox_cy,error_y,raw_delta_tilt,delta_tilt,tilt_angle
104,-136.0,-2.720,-2.720,45.0
```
- error_y < 0（対象は上側）なのに delta_tilt が負（さらに下に動こうとする）
- tilt_angle が 45.0（TILT_DOWN）に張り付いている

**原因**:
- flip（上下反転）モード時に符号を反転させる条件分岐を追加したが、これが誤りだった
- flipは画像表示のみを反転するもので、サーボの動作方向には影響しない
- 誤ったコード:
```python
if self.flip_vertical:
    raw_delta_tilt = self.kp_tilt * error_y  # 誤り
else:
    raw_delta_tilt = -self.kp_tilt * error_y
```

**解決策**:
flip条件分岐を削除し、統一した式を使用：
```python
# 修正後（正）- flipに関係なく同じ式
raw_delta_tilt = -self.kp_tilt * error_y
```

論理：
- 対象が上（error_y < 0）→ delta_tilt > 0 → チルト角度が増加 → カメラが上を向く
- 対象が下（error_y > 0）→ delta_tilt < 0 → チルト角度が減少 → カメラが下を向く

**重要な理解**:
- `--flip`オプションは`cv2.flip(frame, 0)`で画像を上下反転するだけ
- 反転後の画像座標系でerror_yを計算するので、サーボの動作方向は変わらない
- flipの有無でP制御の符号を変える必要はない

**補足（組み付け起因の符号ズレ）**:
- 画像の上下反転とは別に、サーボホーンの付け直しや機構組み付けにより「角度が増える方向」が逆になることがある
- この場合、**画面下に対象がいるのにカメラがさらに上を向く**等が発生する
- 対策: `TILT_DIRECTION=-1`（必要に応じて `PAN_DIRECTION=-1`）で追跡制御の符号を反転して切り分ける

**確認方法**:
```bash
# CSVログを有効にしてテスト実行
python3 camera_tracker.py --classes person --display --continuous --flip --log test.csv

# ログを確認：error_yが負の時にdelta_tiltが正であることを確認
```

**ステータス**: [x] 解決済み

---

### 問題 4: チルト追従の調査中（未解決）

**発生日**: 2025-12-17

**発生状況**: `--flip`オプション使用時、上下方向（チルト）の追従が期待通りに動作しない

**調査経過**:

1. **tracking.csv** - パン符号修正前のログ
2. **tracking4.csv** - パン修正後、チルトが動作しない報告
   - error_y が小さい値（-1〜-2程度）でデッドバンド内に入っていることが多い
   - error_y が大きい時もチルトの動きが限定的
3. **tracking5.csv** - flip条件分岐追加後
   - チルトは45.0〜114.5の範囲で変化を確認
   - error_y > 0 の時に delta_tilt > 0 となりチルト増加
   - しかしユーザ報告では「全く上下方向の角度が変化しない」

**ログデータ例（tracking5.csv）**:
```csv
# チルトが変化している例
timestamp,error_y,raw_delta_tilt,delta_tilt,tilt_angle
23:31:45.620,73.0,1.460,1.460,46.5
23:31:51.760,131.0,2.620,2.620,65.5
23:31:55.913,156.0,3.120,3.000,92.1
23:32:01.152,183.0,3.660,3.000,114.5

# error_yがデッドバンド内で変化しない例
23:31:44.787,-1.0,-0.020,0.000,45.0
23:32:04.467,-2.0,-0.040,0.000,109.8
```

**考えられる原因（調査継続）**:
1. デッドバンド（25ピクセル）が大きすぎて、多くのフレームで動作しない
2. 対象が画面中央付近に長時間留まり、チルト制御が発動しない
3. パン追従が優先され、チルトの誤差が小さくなっている
4. flip時の符号反転の必要性と実装の整合性

**現在のコード（camera_tracker.py:284-289）**:
```python
if self.flip_vertical:
    # 逆さまマウント: 符号を反転
    raw_delta_tilt = self.kp_tilt * error_y
else:
    # 通常マウント
    raw_delta_tilt = -self.kp_tilt * error_y
```

**単体テスト結果（2025-12-17）**:
- チャンネル0（パン）: 正常動作
- チャンネル1（チルト）: 動作せず
- チャンネル切り替えテスト:
  - パンサーボをチャンネル1に接続 → 動作する
  - チルトサーボをチャンネル0に接続 → 動作しない
- **結論: チルトサーボ（モーター）の故障**

**次のステップ**:
- [x] サーボ物理動作の直接確認
- [x] チャンネル切り替えテストで原因特定
- [x] チルトサーボを新品に交換して再テスト

**解決策**:
チルトサーボ（SG90）を新品に交換

**確認方法**:
```bash
source .venv/bin/activate && python3 -c "
import servo_control
import time
kit = servo_control.initialize_servo_kit()
servo_control.set_pan_tilt(kit, 80, 90)
time.sleep(1)
servo_control.set_pan_tilt(kit, 35, 135)
time.sleep(1)
servo_control.set_pan_tilt(kit, 125, 45)
time.sleep(1)
servo_control.set_center_position(kit)
servo_control.release_servos(kit)
print('Test complete')
"
```

**関連ログファイル**:
- `tracking.csv` - 初期テスト
- `tracking4.csv` - パン修正後
- `tracking5.csv` - flip条件分岐追加後

**ステータス**: [x] 解決済み（2025-12-18 サーボ交換で解決）

---

### 問題 5: サーボ角度限界での振動（解決済み）

**発生日**: 2025-12-17

**発生状況**: パン追跡テスト時、カメラが右端方向に大きく移動した際にマウントが振動する現象が発生

**原因**:
- パンの符号が逆だったため、目標と反対方向に移動しようとしていた
- サーボが角度限界（PAN_LEFT=35度）に到達しても、P制御が反対方向への力を加え続けていた
- これによりサーボが限界位置で振動

**解決策**:
問題2（パン符号の修正）を適用することで解消

**ステータス**: [x] 解決済み（パン符号修正により解消）

---

### 問題 6: チルトサーボがマウント組み込み後に動作しない

**発生日**: 2025-12-18

**発生状況**:
- 問題4で故障したチルトサーボを新品に交換
- サーボ単体テストでは正常動作を確認（90°→135°→45°→90°）
- カメラをマウントに組み込んだ後、チルトサーボが動作しなくなった
- パンサーボは正常に動作する

**症状**:
- チルトサーボに指令を送っても動かない
- サーボ解放コマンド（`angle=None`、`duty_cycle=0`）を実行してもトルクが出続ける
- 手でチルトを動かそうとしてもびくともしない
- パン（CH0）は正常動作

**試した解放方法**:
```python
# 方法1: servo_control.release_servos()
servo_control.release_servos(kit)

# 方法2: 直接Noneを設定
kit.servo[1].angle = None

# 方法3: duty_cycleを0に設定
kit._pca.channels[1].duty_cycle = 0
```
→ いずれもトルクが出続け、解放されない

**原因**:
- SG90サーボの物理的な可動限界
- TILT_UP=135度がサーボのギア限界を超えていた
- 限界角度に達するとギアがロックし、解放信号も効かなくなる

**解決策**:
チルト上限を135度から120度に変更:
```python
# servo_control.py
TILT_UP = 120  # チルトサーボの上端（SG90の物理的限界を考慮）
```

**確認方法**:
```bash
source .venv/bin/activate && python3 -c "
import servo_control
import time
kit = servo_control.initialize_servo_kit()
servo_control.set_tilt_angle(kit, 90)
time.sleep(0.5)
servo_control.set_tilt_angle(kit, 120)
time.sleep(0.5)
servo_control.set_tilt_angle(kit, 45)
time.sleep(0.5)
servo_control.set_tilt_angle(kit, 90)
servo_control.release_servos(kit)
print('Test complete')
"
```

**変更したファイル**:
- `servo_control.py`: TILT_UP を 135 → 120 に変更

**ステータス**: [x] 解決済み（2025-12-18 チルト上限を120度に変更）

---

### 問題 7: P制御追跡時のハンチング（発振）

**発生日**: 2025-12-18

**発生状況**:
- 追跡テスト中、対象を追従中に突然マウントが振動を始めた
- 特に中央から大きく離れた位置への追従時に発生しやすい
- 一度振動が始まると収束せず、振幅が増大する

**症状**:
- サーボがガクガクと左右（または上下）に振動
- 振動がさらに振動を誘発し、収束しない
- カメラ映像がぶれて検出位置も不安定に

**原因**:
- P制御のゲイン（Kp）が高すぎる
- 1回あたりの角度変化量（delta_angle_max）が大きすぎる
- 更新頻度（FPS）が高すぎ、サーボが安定する前に次の指令が来る
- デッドバンドが小さすぎ、微小な検出誤差にも反応

**ハンチングの発生メカニズム**:
1. サーボが移動中にカメラ画像がぶれる
2. ぶれた画像で検出位置が変動
3. 変動した位置に対してさらにサーボが追従
4. この繰り返しで振動が増幅（正のフィードバック）

**解決策**:
P制御パラメータを以下のように調整：

| パラメータ | 調整前 | 調整後 |
|-----------|--------|--------|
| kp_pan | 0.02 | 0.01 |
| kp_tilt | 0.02 | 0.01 |
| deadband | 25px | 40px |
| delta_angle_max | 3.0° | 1.0° |
| fps | 10 Hz | 5 Hz |

**コマンド例**:
```bash
# 調整後のパラメータで実行
python3 camera_tracker.py --classes person --display --continuous --flip \
    --kp-pan 0.01 --kp-tilt 0.01 --deadband 40 --delta-max 1.0 --fps 5
```

**確認方法**:
```bash
# デフォルトパラメータが更新されているため、以下のコマンドで動作確認
source .venv/bin/activate && python3 camera_tracker.py --classes person --display --continuous --flip
```

**変更したファイル**:
- `camera_tracker.py`: デフォルトパラメータを実機検証済みの値に変更
- `docs/detection_and_tracking_specification.md`: 仕様書を更新

**調整の優先順位（参考）**:
1. delta_angle_maxを下げる（最も効果的）
2. FPSを下げる（サーボの安定化時間を確保）
3. Kpを下げる（応答を穏やかに）
4. deadbandを広げる（微小振動の抑制）

**ステータス**: [x] 解決済み（2025-12-18 パラメータ調整で安定動作を確認）

---

## UI・操作関連

### 問題 5: qキーで終了できない

**発生日**: 2025-12-17

**発生状況**: `--continuous --display`オプションで実行中、qキーを押しても終了せず、一瞬停止した後に再スキャンが始まる

**原因**:
- `scan_and_track()`メソッドがqキー押下時に`False`を返していた
- メインループでは`False`を「対象が見つからなかった」と解釈して再スキャンを開始
- qキー終了と検出失敗の区別ができていなかった

**解決策**:
戻り値に`None`を追加してユーザ終了を区別：
```python
# scan_and_track()メソッド内
if cv2.waitKey(1) & 0xFF == ord('q'):
    print("終了キーが押されました")
    return None  # ユーザ終了（FalseではなくNone）

# メインループ
result = tracker.scan_and_track(...)
if result is None:
    print("ユーザにより終了されました")
    break  # ループを抜ける
if not result:
    print("対象が見つかりません。再スキャン...")
```

戻り値の意味：
- `True`: ペットを検出して追跡した
- `False`: ペットが見つからなかった（再スキャン対象）
- `None`: ユーザがqキーで終了した（ループを抜ける）

**ステータス**: [x] 解決済み

---

## Slack通知関連

### 問題 8: ペット未検出時に同じ画像が繰り返し送信される

**発生日**: 2025-12-20

**発生状況**:
- main.py で1分間隔の定期通知テストを実行
- ペットが検出されなかったため、同じ画像が5分間繰り返し送信された
- ユーザーの期待: ペットがいない場合でもその時点の部屋の写真を撮影して送信してほしい

**症状**:
- Slack に届く画像がすべて同一（最初にキャプチャされた画像）
- ペット検出なしの状態が続くと `get_latest_image()` が古い画像を返し続ける

**原因**:
- `capture_images()` がペット検出時のみ呼び出される設計になっている
- ペット未検出時は新規画像のキャプチャが行われない
- `get_latest_image()` は過去の保存済み画像のパスを返すため、古い画像が送信される

**対策案**:

| 案 | 内容 | メリット | デメリット |
|----|------|----------|------------|
| A | 定期通知時に必ず新規撮影 | シンプル、最新状況を常に把握可能 | ペット検出関係なく撮影するためストレージ消費増 |
| B | 検出有無に関わらず定期撮影 | 一定間隔でスナップショット | 同上 |
| C | 前回と異なる画像のみ送信 | 重複削減 | 実装複雑、同じ場所にいると送信されない |

**推奨対策**: 案A - 定期通知時に必ず新規撮影する

**実装方針**:
```python
# main.py の定期通知ロジックを修正
def _send_periodic_notification(self):
    # 毎回新しい画像をキャプチャして送信
    paths = capture_images(count=1, long_edge=800, jpeg_quality=70)
    if paths:
        result = upload_images(file_paths=paths, message="定期通知")
```

**解決策**:
main.py の定期Slack通知ロジックを修正:
- `get_latest_image()` で過去の画像を取得する代わりに
- 通知時に必ず `capture_images()` で新規画像をキャプチャして送信

**変更ファイル**: main.py（278-295行目）

**ステータス**: [x] 解決済み（2025-12-20）

---

### 問題 9: パンサーボが右側領域で振動する

**発生日**: 2025-12-20

**発生状況**:
- main.py で追跡テスト中
- カメラが正面から見て左から右に移動するとき
- 特にパン角度が中央（80度）より右側（80度〜125度）の領域で振動が発生
- サーボ内部のフィードバックがオーバーシュートを繰り返し、収束しない

**症状**:
- パンサーボがガタガタと左右に振動
- 振動が収束せず継続する
- 左側領域（35度〜80度）では発生しにくい

**原因（推定）**:
1. **サーボの個体差**: SG90の特性として、特定の角度範囲でギアのバックラッシュが大きい可能性
2. **機械的な問題**: マウントの重心バランスにより右側で負荷が増大
3. **P制御パラメータ**: 右側領域でゲインが高すぎる可能性
4. **サーボの非線形特性**: 角度によってトルク特性が変化

**調査ポイント**:
- [ ] サーボ単体で右側領域への移動テスト
- [ ] マウントの重心バランス確認
- [ ] P制御ゲインを右側でさらに下げるテスト
- [ ] サーボの交換テスト

**対策案**:

| 案 | 内容 | 効果 |
|----|------|------|
| A | Kp_pan をさらに下げる（0.01 → 0.005） | 全体的に応答が遅くなるが安定 |
| B | 右側領域のみゲインを下げる（適応ゲイン） | 左右で異なる特性に対応可能 |
| C | delta_angle_max をさらに下げる（1.0 → 0.5） | 急激な動きを抑制 |
| D | FPS をさらに下げる（5 → 3） | サーボ安定化時間を確保 |
| E | サーボを交換 | 個体差の可能性を排除 |

**現在のパラメータ**:
```
KP_PAN=0.02
KP_TILT=0.02
DEADBAND=10
delta_angle_max=1.0（コード内デフォルト）
tracking_fps=5.0（コード内デフォルト）
```

**確認コマンド**:
```bash
# ゲインを下げてテスト
source .venv/bin/activate && python camera_tracker.py --display --continuous
```

**ステータス**: [ ] 未解決

---

### 問題 10: スキャン動作が左上エリアのみに限定される

**発生日**: 2025-12-20

**発生状況**:
- main.py で人間検出を追加してテスト実行
- 可動域テスト（servo_control.py 単体）では正常にパン35°〜125°、チルト45°〜120°の全範囲を移動
- しかし実際の検出モード（main.py）では左上エリアのみで動作
- バウンディングボックスが表示されていないのに「検出」として処理されている

**観察された動作パターン**:
1. 左上からスタート（パン35°、チルト45°）
2. 中央上まで水平に移動
3. 中央下まで縦に移動
4. また中央上から左上へ水平移動
5. しばらく停止 → 繰り返し

**ログの証拠**:
```
2025-12-20 23:13:04,389 - camera_tracker - INFO - ペット検出（パン: 35.0°、チルト: 45.0°）
2025-12-20 23:13:04,389 - camera_tracker - INFO - ペット検出！追跡モードへ移行します
```
→ スキャン開始直後の最初の位置（PAN_LEFT=35, TILT_DOWN=45）で毎回検出が発生

**追加の検証ログ（2025-12-20/21）**:
```
# logs/run_20251220_233649.log より
2025-12-20 23:41:24,763 - camera_tracker - INFO - ペット検出（パン: 91.2°、チルト: 63.8°）: cat 0.54 bbox=[0, 1, 528, 477]
2025-12-20 23:41:24,763 - camera_tracker - INFO - 追跡開始（時間: 8.0秒、FPS: 5.0 Hz）
2025-12-20 23:41:37,478 - camera_tracker - INFO - ペット検出（パン: 35.0°、チルト: 45.0°）: cat 0.55 bbox=[344, 387, 638, 479]
2025-12-20 23:41:37,478 - camera_tracker - INFO - 追跡開始（時間: 8.0秒、FPS: 5.0 Hz）
```
- **左上スタート位置（35°,45°）で cat 0.55 の検出**が発生しており、誤検出（false positive）で追跡へ入るループが起きている可能性が高い

**推測される原因**:

1. **シングルトンパターンによる古い設定の残存**
   - `_tracker_instance` がシングルトンとして保持されている
   - 以前のテスト実行時に `conf_threshold=0.25`（デフォルト値）で作成されたインスタンスが残っている可能性
   - 新しく設定した `CONF_THRESHOLD=0.5` が反映されていない
   - Python プロセスが同一セッションで再利用されると古いインスタンスが使われる

2. **信頼度0.5でもまだ誤検出が発生**
   - 壁や床の模様などが低確率でペットとして検出されている
   - スキャン開始位置（35°, 45°）で毎回誤検出が発生し、フルスキャンが実行されない
   - 左上エリアの背景に誤検出を誘発する特徴がある可能性

3. **バウンディングボックスが見えない理由**
   - `--display` オプションなしで実行しているため、映像ウィンドウが表示されていない
   - または、検出はされているが描画される前に次の処理に移っている
   - 内部的には検出されているが可視化されていない

4. **headless環境での `--display` 実行によるクラッシュ**
   - SSH/GUIなし環境で `cv2.imshow` が実行されると OpenCV(Qt) が `could not connect to display` で落ちる
   - 結果として「表示確認できない」「プロセスが落ちる」が混在し、原因切り分けが難しくなる

**動作パターンの解釈**:
「左上→中央上→中央下→中央上→左上」という動きは：
1. スキャン開始位置（35°, 45°）で誤検出
2. `_track_pet` による追跡モードに入る
3. P制御が「検出対象を中央に捉えよう」としてサーボを動かす
4. 実際には対象がないので追跡が終了（または見失い）
5. 再スキャン開始 → また同じ位置で誤検出 → 繰り返し

**確認すべき点**:
- [ ] 古いインスタンスをクリアして新しい設定で初期化されているか確認
- [ ] 信頼度閾値0.5で本当に誤検出が防げているかログで確認
- [ ] スキャン開始位置で何が検出されているか（クラス名と信頼度をログ出力）
- [ ] `--display` オプションを付けて実行し、何が検出されているか視覚的に確認
- [ ] headless環境の場合は `--display` を付けない（もしくは DISPLAY を用意する）

**対策案**:

| 案 | 内容 | 効果 |
|----|------|------|
| A | プロセス再起動で古いインスタンスをクリア | 新しいconf_threshold設定が確実に反映される |
| B | 検出時にクラス名と信頼度をログ出力 | 何が誤検出されているか特定可能 |
| C | 信頼度閾値をさらに上げる（0.5→0.6 or 0.7） | 誤検出をさらに減らす |
| D | `--display` オプションで視覚的に確認 | 実際に何が検出されているか確認 |
| E | スキャン開始位置を変更（中央から開始） | 左上の誤検出ポイントを回避 |

**実装した対策（2025-12-20/21）**:
- **検出ログ強化**: 検出時に `class/conf/bbox/角度` をログ出力し、誤検出の根拠を残せるようにした
- **headless安全化**: `--display` 指定でも `DISPLAY` が未設定なら自動で無効化（クラッシュ回避）
- **誤検出抑制**:
  - `CONF_THRESHOLD` を引き上げ可能（例: 0.6）
  - bbox面積比フィルタを追加（例: `MIN_BBOX_AREA_RATIO=0.02`, `MAX_BBOX_AREA_RATIO=0.55`）

**関連するコード箇所**:

1. シングルトンインスタンス管理:
```python
# camera_tracker.py:90-95
global _tracker_instance
if _tracker_instance is None:
    _tracker_instance = _create_tracker_from_env()
```

2. 信頼度閾値の設定:
```python
# camera_tracker.py:250-251
conf_threshold = float(os.getenv("CONF_THRESHOLD", "0.5"))
```

3. 検出判定:
```python
# camera_tracker.py:600-632
def _detect_pet(self, frame):
    detections = self.detector.detect(frame)
    # 最も信頼度の高い検出を選択
    for det in detections:
        conf = det['confidence']
        if conf > best_conf:
            best_conf = conf
            best_box = ...
    return best_box
```

4. スキャン開始位置:
```python
# camera_tracker.py:490-501
for i in range(steps_tilt):
    tilt_angle = servo_control.TILT_DOWN + i * tilt_step  # 45°から開始
    for j in range(steps_pan):
        pan_angle = servo_control.PAN_LEFT + j * pan_step  # 35°から開始
```

**環境情報**:
```
CONF_THRESHOLD=0.5  # .envに追加済み
YOLO_MODEL_PATH=models/yolov8s_h8l.hef
検出対象: cat, dog, person
```

**ステータス**: [ ] 未解決（誤検出の根拠取得と抑制策は実装済み、現場で再現頻度を監視中）

---

### 問題 11: `--display` 実行時に OpenCV(Qt) がクラッシュする（GUIなし環境）

**発生日**: 2025-12-20

**発生状況**:
- SSH/GUIなし（`DISPLAY` 未設定）の環境で `python3 main.py --display --verbose` を実行

**エラーメッセージ**:
```
qt.qpa.xcb: could not connect to display
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" ...
This application failed to start because no Qt platform plugin could be initialized.
```

**原因**:
- `cv2.imshow()` が X サーバ（`DISPLAY`）に接続できず OpenCV(Qt) が初期化失敗

**解決策**:
- headless環境では `--display` を使わない
- もしくは X/Wayland（`DISPLAY`）を用意する
- **実装対応**: `main.py` / `camera_tracker.py` にて `--display` かつ `DISPLAY` 未設定の場合は自動で無効化し、クラッシュを回避

**確認方法**:
```bash
source .venv/bin/activate
python3 main.py --display --no-slack --verbose
# DISPLAY が無い場合は警告が出て display が無効化され、クラッシュしないこと
```

**ステータス**: [x] 解決済み（headless安全化を実装）

---

### 問題 12: ターミナルの日本語ログが文字化けする（EUC-JPロケール）

**発生日**: 2025-12-20

**発生状況**:
- `main.py` 実行時の日本語ログが `�` を含む文字化けになる

**原因**:
- ロケールが `LC_ALL=ja_JP.EUC-JP` になっており、UTF-8のログが正しく表示できない

**解決策（暫定）**:
```bash
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
python3 main.py --no-slack --verbose
```

**確認方法**:
```bash
locale
```

**ステータス**: [ ] 未解決（暫定回避で運用中、恒久対応はOSロケールをUTF-8へ統一）

---

### 問題 13: サーボが停止しない（トルクが抜けない/暴れ続ける）

**発生日**: 2025-12-20

**発生状況**:
- 追跡や固定スクリプト実行後、停止させてもサーボが動作継続/トルク保持してしまう

**原因（可能性）**:
- 制御プロセスが残っていて PWM 指令が継続している
- PCA9685 が PWM を出し続け、サーボがトルクを保持している

**解決策**:
1) 制御プロセスを停止
2) サーボを中央へ戻す
3) `release_servos()` を実行
4) それでもダメなら **PWMを強制OFF（duty_cycle=0）**

**確認/復旧コマンド例**:
```bash
cd 12-002-pet-monitoring-yolov8
source .venv/bin/activate
pkill -9 -f "python3 .*main\\.py" || true
pkill -9 -f "python3 .*camera_tracker\\.py" || true

python3 - <<'PY'
import time
import servo_control
kit = servo_control.initialize_servo_kit()
servo_control.set_center_position(kit, smooth=True)
time.sleep(0.8)
try:
    servo_control.release_servos(kit)
except Exception as e:
    print("release_servos failed:", e)
try:
    kit._pca.channels[servo_control.PAN_CHANNEL].duty_cycle = 0
    kit._pca.channels[servo_control.TILT_CHANNEL].duty_cycle = 0
    print("OK: duty_cycle=0 (PWM off)")
except Exception as e:
    print("PWM off failed:", e)
PY
```

**ステータス**: [x] 解決済み（強制停止＋PWM OFFで復旧可能手順を確立）

---

### 問題 14: チルト上げ方向で激しい振動（ケーブル剛性/外乱起因）

**発生日**: 2025-12-21

**発生状況**:
- 左右の振動は Raspberry Pi 配置を変更してケーブルに余裕を持たせると改善
- ただし **チルトを上げる方向（TILT_UP側）で強い振動**が発生
- チルトを下げる方向ではほぼ発生しない
- PWMで角度固定中に手が当たる等の外乱で一度発振すると、SG90内部フィードバックで収束しにくいことがある

**原因（推定）**:
- カメラモジュールのFPCケーブルの「腰」が強く、上側コネクタに挿さっていることで
  **上から押さえつける力（外乱トルク）**がチルト上げ方向に作用する
- 外乱 → フレームたわみ/画像ブレ → 検出中心の揺れ → 追跡制御が過反応 → ハンチング

**解決策（推奨）**:
- **配線取り回し**: チルト軸近傍で曲げ点を作り、コネクタ直近に力が掛からないようにする
- **ストレインリリーフ**: コネクタから数cmの位置で固定し、コネクタに力を入れない
- **ソフト側で抑制**:
  - `KP_TILT` を下げる（例: 0.01 → 0.005）
  - `DELTA_ANGLE_MAX` を下げる（例: 0.5 → 0.3）
  - `TRACKING_FPS` を下げる（例: 3 → 2）
- **固定作業時の対策**: 角度保持（トルクON）だと外乱で発振しやすいため、位置合わせ後に解放する
  - `hold_servo_position.py --mode move-and-release` / `--mode move-and-pwm-off` を使用

**追加の検証結果（2025-12-21）**:
- Raspberry Pi本体をカメラマウント直後に配置し、**カメラモジュールケーブルに余長を確保**すると左右方向の振動が解消
- ケーブルの取り回しを調整して**チルト上げ方向でもケーブルが押し付ける力（テンション）が掛からない**ようにしたところ、
  追跡中の激しい振動が発生しなくなった

**結論**:
- ケーブル等の外部テンション（外乱トルク）がサーボ・フレームへ加わるとハンチング/振動の原因となる
- 設置時は「余長の確保」「曲げ点の最適化」「固定点（ストレインリリーフ）」を必ず行う

**確認方法**:
```bash
source .venv/bin/activate
KP_TILT=0.005 DELTA_ANGLE_MAX=0.3 TRACKING_FPS=2.0 python3 main.py --no-slack --verbose
```

**ステータス**: [x] 解決済み（ケーブル取り回しと余長確保で振動が解消）

---

### 問題 15: 検出は動くがスキャン/追従でサーボが動かない（サーボ電源コネクタ未接続）

**発生日**: 2025-12-21

**発生状況**:
- `main.py --display` でカメラ映像や検出は動作するが、カメラマウントが初期位置から動かずスキャン/追従しない

**原因**:
- サーボ用電源コネクタの挿し込み不良（外部電源が供給されていなかった）

**解決策**:
- サーボ電源コネクタを確実に挿し直す（外部5Vの供給確認）

**確認方法**:
```bash
source .venv/bin/activate
python3 - <<'PY'
import time, servo_control
kit = servo_control.initialize_servo_kit()
servo_control.set_pan_tilt(kit, 35, 90); time.sleep(1)
servo_control.set_pan_tilt(kit, 125, 90); time.sleep(1)
servo_control.set_pan_tilt(kit, 80, 90); time.sleep(0.5)
servo_control.release_servos(kit)
print("OK")
PY
```

**ステータス**: [x] 解決済み

---

### 問題 16: 検出方向と逆にチルトが動く（上下方向の符号が逆）

**発生日**: 2025-12-21

**発生状況**:
- 可動域テスト（`test_pan_tilt_range.py`）ではパン/チルトともに端まで正常に動作
- しかしメインアプリ（`main.py --display`）では、**画面下に対象（person等）がいるのにカメラがさらに上を向く**ように見える
- スキャンが不自然に見える／追跡に入っても端で飽和して「追従していない」ように見えることがある

**原因**:
- カメラが上下反転マウントされており、表示/検出のために画像を上下反転している
- 画像反転は座標系（error_y）の向きを変えるが、サーボの物理的な回転方向（角度が増える/減るで上を向くか下を向くか）は機構側の都合で決まる
- この2つの整合が取れていないと、**error_yに対するdelta_tiltの符号が実機の向きと逆**になり、結果として「下にいるのに上へ向く」が起きる

**解決策**:
- チルト方向の符号を環境変数で反転して合わせる:
  - `TILT_DIRECTION=-1`（必要に応じて `PAN_DIRECTION=-1` も同様に切り分け）

実行例:
```bash
LC_ALL=C.UTF-8 LANG=C.UTF-8 \
TILT_DIRECTION=-1 \
python3 main.py --display --no-slack --verbose --classes cat dog person
```

**確認方法**:
- `--display` で、画面下に対象がいる場合に **カメラが下を向く方向**へ動くことを確認
- `logs/tracking_debug.csv` で、対象が下側にいるフレームで delta_tilt が期待する向きになっていることを確認
- `logs/debug_frames/` の保存画像に `err=(x,y)` と `delta=(pan,tilt)`、`before/after` が焼き込まれるので、画像単体でも整合確認が可能

**ステータス**: [x] 解決済み（`TILT_DIRECTION=-1` で正常化）

---

### 問題 17: 検出後に数秒で追跡が終わり、すぐサーチ（スキャン）に戻ってしまう

**発生日**: 2025-12-21

**発生状況**:
- 検出後に追跡は開始するが、少し動くと一瞬検出が外れることがあり、その直後に追跡をやめてスキャン（サーチ）に戻る
- 「映像が止まった」ように見えることがある（実際にはスキャン/追跡の状態が画面上で分からず、ロスト→再スキャンに見える）

**原因**:
- YOLOの検出はブレ/露出/姿勢変化/一時的な遮蔽により、1〜数フレーム程度の「瞬断」が起きることがある
- 瞬断を即ロスト扱いにすると、追跡が頻繁に中断されて不安定に見える

**解決策**:
- ロスト判定に猶予時間を導入し、瞬断では追跡を終了しないようにする
  - `TRACK_LOST_TIMEOUT`: 未検出がこの秒数を超えたらロスト（追跡終了）
  - `RESCAN_DELAY_SECONDS`: ロスト後、再スキャンに入る前の待機秒数

実行例:
```bash
LC_ALL=C.UTF-8 LANG=C.UTF-8 \
TILT_DIRECTION=-1 \
TRACK_LOST_TIMEOUT=10.0 RESCAN_DELAY_SECONDS=2.0 \
python3 main.py --display --no-slack --verbose --classes cat dog person
```

**確認方法**:
- 少し動いて一瞬検出が外れても、すぐにサーチへ戻らず追跡が継続することを確認
- `--display` では画面左下のオーバーレイに `mode` / `last_seen_age` / `ts` が表示されるので、
  ロストが原因か（`last_seen_age` が増えていく）や、表示更新が止まっているか（`ts` が進まない）を切り分け可能

**ステータス**: [x] 解決済み（ロスト猶予導入で追跡が安定）

---

### 問題 18: Slack通知が初回のみ送信され、それ以降送信されない（追跡が戻らず定期タスクが回らない）

**発生日**: 2025-12-21

**発生状況**:
- Slack通知を有効にして起動（`--no-slack` なし、`--interval 1` 等でテスト）
- 起動直後（または最初のタイミング）に1回だけSlackへ送信されるが、その後は送信されない

**原因**:
- 追跡が「検出が続く限り継続」するようになった結果、`main.py` のメインループが `camera_tracker.scan_and_track()` から戻ってこない
- そのため、`main.py` 側の `run_periodic_tasks()` が呼ばれず、定期Slack通知の判定が進まない（= 送信が止まる）

**解決策**:
- `camera_tracker.scan_and_track()` に `tick_callback` を追加し、追跡/スキャンの内部ループから定期的に呼び出す（協調スケジューリング）
- `main.py` は `tick_callback=self.run_periodic_tasks` を渡し、追跡中でも定期タスク（画像保存/Slack送信）が動くようにする

**確認方法**:
- `--interval 1` で起動し、追跡が継続している状態でも1分ごとにSlack送信されることを確認
- ログに `=== 定期Slack通知 ===` が継続的に出ることを確認

**ステータス**: [x] 解決済み（tick_callback導入で追跡中も定期送信が継続）

## 参照ドキュメント

- `reference/11-002-raspi-hailo8l-yolo-detector/docs/TROUBLESHOOTING.md` - Hailo8Lライブラリのトラブルシューティング
- `reference/12-001-rpi-pan-tilt-camera-mount/docs/troubleshooting.md` - サーボ制御のトラブルシューティング

---

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2025-12-17 | 初版作成 |
| 2025-12-17 | 問題2〜5を追加（P制御符号、チルト追従、振動、qキー終了） |
| 2025-12-17 | 問題4をチルト追従調査中として更新、ログファイル追加 |
| 2025-12-20 | 問題8（同一画像の繰り返し送信）、問題9（右側領域での振動）を追加 |
| 2025-12-20 | 問題10（スキャン動作が左上エリアのみに限定される）を追加 |
| 2025-12-20 | 問題11（headless環境での `--display` クラッシュ）、問題12（文字化け/EUC-JPロケール）を追加 |
| 2025-12-20 | 問題13（サーボが停止しない→PWM OFFで復旧）を追加 |
| 2025-12-21 | 問題14（チルト上げ方向の振動：ケーブル剛性/外乱）を追加 |
| 2025-12-21 | 問題15（検出は動くがサーボが動かない：電源コネクタ未接続）を追加 |
| 2025-12-21 | 問題16（検出方向と逆にチルトが動く：上下方向の符号）を追加 |
| 2025-12-21 | 問題17（追跡が数秒で終わってサーチに戻る：ロスト猶予）を追加 |
| 2025-12-21 | 問題18（Slack通知が初回のみ：追跡が戻らず定期タスクが回らない）を追加 |
