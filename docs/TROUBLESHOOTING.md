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

**次のステップ**:
- [ ] ログデータとユーザの観察の差異を確認
- [ ] デッドバンドを小さくしてテスト
- [ ] チルトのみの単体テストを実施
- [ ] サーボ物理動作の直接確認

**関連ログファイル**:
- `tracking.csv` - 初期テスト
- `tracking4.csv` - パン修正後
- `tracking5.csv` - flip条件分岐追加後

**ステータス**: [ ] 未解決（調査継続）

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
