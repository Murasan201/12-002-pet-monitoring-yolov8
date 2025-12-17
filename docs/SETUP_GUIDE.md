# セットアップ手順書

**プロジェクト**: 12-002-pet-monitoring-yolov8（ペット見守りシステム）
**作成日**: 2025-12-17
**対象読者**: Raspberry Pi初心者〜中級者
**目的**: 書籍掲載用のセットアップ手順を詳細に記録

---

## 前提条件

### ハードウェア構成

| コンポーネント | 製品名 | 備考 |
|---------------|--------|------|
| メインボード | Raspberry Pi 5 | 4GB/8GB RAM推奨 |
| AIアクセラレータ | Raspberry Pi AI Kit (Hailo-8L) | M.2 HAT+ に装着 |
| カメラ | Raspberry Pi Camera Module V3 | IMX708センサー |
| サーボドライバ | Adafruit 16-Channel PWM/Servo HAT | PCA9685搭載 |
| サーボモーター | SG90 × 2 | パン・チルト用 |
| 電源 | 5V 5A USB-C電源アダプター | 公式推奨電源 |
| ストレージ | microSD 32GB以上 | Class 10以上推奨 |

### ソフトウェア要件

| 項目 | バージョン |
|------|-----------|
| OS | Raspberry Pi OS (Bookworm) 64-bit |
| Python | 3.11以上 |
| HailoRT SDK | システムパッケージとして事前インストール |

### 事前準備

- Raspberry Pi OSがインストールされ、SSHまたはデスクトップでアクセス可能
- インターネット接続が確立されている
- I2Cが有効化されている（サーボHAT用）
- カメラが有効化されている

---

## セットアップ手順

### ステップ 1: システムの更新

**目的**: OSとパッケージを最新の状態にする

**コマンド**:
```bash
sudo apt update && sudo apt full-upgrade -y
```

**解説**:
Raspberry Pi OSのパッケージリストを更新し、インストール済みのすべてのパッケージを最新バージョンにアップグレードします。セキュリティパッチや新機能が含まれるため、プロジェクト開始前に必ず実行してください。

**期待される出力**:
```
Hit:1 http://deb.debian.org/debian bookworm InRelease
...
XX packages upgraded, XX newly installed, XX to remove and XX not upgraded.
```

**確認方法**:
```bash
cat /etc/os-release
```

---

### ステップ 2: Hailo-8L AIアクセラレータの確認

**目的**: Hailo-8Lデバイスが正しく認識されているか確認する

**コマンド**:
```bash
hailortcli fw-control identify
```

**解説**:
Hailo-8L AIアクセラレータがシステムに認識され、ファームウェアが正しく動作しているかを確認します。このコマンドはHailoRT SDKに含まれており、`hailo-all`パッケージをインストールすると利用可能になります。

**期待される出力**:
```
Executing on device: 0000:01:00.0
Identifying board
Control Protocol Version: X
Firmware Version: X.X.X (release, app, extended context switch buffer)
...
Device Architecture: HAILO8L
Serial Number: HLXXXXXXXXXXXX
```

**確認方法**:
デバイスアーキテクチャが`HAILO8L`と表示されれば正常です。

**エラーが発生した場合**:
`docs/TROUBLESHOOTING.md` の「Hailo-8L関連」セクションを参照してください。

---

### ステップ 3: カメラの確認

**目的**: Camera Module V3が正しく認識されているか確認する

**コマンド**:
```bash
rpicam-hello --list-cameras
```

**解説**:
Raspberry Pi Camera Module V3（IMX708センサー）がシステムに認識されているかを確認します。`rpicam-hello`はRaspberry Pi OS Bookworm以降で使用可能なカメラテストツールです。

**期待される出力**:
```
Available cameras
-----------------
0 : imx708 [4608x2592 10-bit RGGB] (/base/soc/i2c0mux/i2c@1/imx708@1a)
    Modes: 'SRGGB10_CSI2P' : 1536x864 [120.13 fps - (768, 432)/3072x1728 crop]
           'SRGGB10_CSI2P' : 2304x1296 [56.03 fps - (0, 0)/4608x2592 crop]
           'SRGGB10_CSI2P' : 4608x2592 [14.35 fps - (0, 0)/4608x2592 crop]
```

**確認方法**:
`imx708`が表示されればCamera Module V3が正しく認識されています。

---

### ステップ 4: I2Cの確認（サーボHAT用）

**目的**: Adafruit Servo HATがI2Cで認識されているか確認する

**コマンド**:
```bash
sudo i2cdetect -y 1
```

**解説**:
I2Cバス上のデバイスをスキャンし、PCA9685（Servo HAT）のI2Cアドレスを確認します。デフォルトのアドレスは`0x40`です。

**期待される出力**:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: 40 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: 70 -- -- -- -- -- -- --
```

**確認方法**:
`40`が表示されればServo HATが正しく認識されています。`70`はPCA9685の「All Call」アドレスです。

---

### ステップ 5: プロジェクトディレクトリの準備

**目的**: プロジェクトをクローンまたは作成する

**コマンド**:
```bash
cd ~/work/project
git clone https://github.com/Murasan201/12-002-pet-monitoring-yolov8.git
cd 12-002-pet-monitoring-yolov8
```

**解説**:
GitHubからプロジェクトをクローンします。既にローカルにある場合は`git pull`で最新の状態に更新してください。

---

### ステップ 6: Python仮想環境の作成

**目的**: プロジェクト専用のPython環境を構築する

**コマンド**:
```bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
```

**解説**:
Python仮想環境を作成し、有効化します。`--system-site-packages`オプションは非常に重要です。これにより、システムにインストールされているHailoRT SDKやPicamera2パッケージに仮想環境からアクセスできるようになります。

**なぜ仮想環境を使うのか**:
- プロジェクトごとに依存パッケージを分離できる
- システム全体のPython環境を汚染しない
- 再現性のある環境を構築できる

**期待される出力**:
プロンプトの先頭に`(.venv)`が表示されます：
```
(.venv) pi@raspberrypi:~/work/project/12-002-pet-monitoring-yolov8 $
```

**確認方法**:
```bash
which python3
# 出力: /home/pi/work/project/12-002-pet-monitoring-yolov8/.venv/bin/python3
```

---

### ステップ 7: 依存パッケージのインストール

**目的**: プロジェクトに必要なPythonパッケージをインストールする

**コマンド**:
```bash
pip install -r requirements.txt
```

**解説**:
`requirements.txt`に記載されている依存パッケージをインストールします。主なパッケージには以下が含まれます：
- `opencv-python`: 画像処理ライブラリ
- `numpy`: 数値計算ライブラリ
- `adafruit-circuitpython-servokit`: サーボ制御ライブラリ

**期待される出力**:
```
Successfully installed opencv-python-x.x.x numpy-x.x.x ...
```

**確認方法**:
```bash
pip list
```

---

### ステップ 8: モデルファイルの準備

**目的**: Hailo-8L用のYOLOモデルファイルを配置する

**コマンド**:
```bash
mkdir -p models
ln -sf /usr/share/hailo-models/yolov8s_h8l.hef models/yolov8s_h8l.hef
```

**解説**:
Hailo-8L用に最適化されたYOLOv8モデル（HEF形式）へのシンボリックリンクを作成します。HEFファイルはHailo Runtime用にコンパイルされた専用フォーマットです。システムにプリインストールされているモデルを使用することで、別途ダウンロードする必要がありません。

**確認方法**:
```bash
ls -la models/
# yolov8s_h8l.hef -> /usr/share/hailo-models/yolov8s_h8l.hef と表示される
```

---

### ステップ 9: インポートテスト

**目的**: すべてのモジュールが正しくインポートできるか確認する

**コマンド**:
```bash
python3 -c "from camera_tracker import CameraTracker; print('Import successful')"
```

**解説**:
プロジェクトのメインモジュール（`camera_tracker.py`）が依存するすべてのライブラリとともに正しくインポートできるかを確認します。

**期待される出力**:
```
Import successful
```

**エラーが発生した場合**:
`docs/TROUBLESHOOTING.md` を参照してください。

---

## セットアップ完了後の確認

### 動作確認チェックリスト

- [ ] Hailo-8Lデバイスが認識されている
- [ ] カメラが認識されている
- [ ] Servo HATがI2Cで認識されている
- [ ] 仮想環境が有効化されている
- [ ] 依存パッケージがインストールされている
- [ ] モデルファイルが配置されている
- [ ] インポートテストが成功している

---

## 次のステップ

セットアップが完了したら、以下のドキュメントを参照してください：

1. `docs/detection_and_tracking_specification.md` - 検出・追跡機能の仕様
2. `docs/servo_control_specification.md` - サーボ制御の仕様
3. `README.md` - 使用方法

---

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2025-12-17 | 初版作成 |
