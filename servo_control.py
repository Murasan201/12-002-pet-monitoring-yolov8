#!/usr/bin/env python3
"""
パン・チルトサーボ制御ライブラリ
サーボモーターの基本動作を提供するライブラリモジュール
スタンドアロン実行とライブラリimportの両方に対応
要件定義書: docs/specification.md
"""

import time
from adafruit_servokit import ServoKit

# ===== サーボ制御の定数 =====
SERVO_CHANNELS = 16          # サーボHATのチャンネル数
PAN_CHANNEL = 0              # パンサーボ（左右）のチャンネル
TILT_CHANNEL = 1             # チルトサーボ（上下）のチャンネル

# パルス幅設定（SG90サーボ用）
PULSE_MIN = 750              # 最小パルス幅（μs）
PULSE_MAX = 2250             # 最大パルス幅（μs）

# 動作範囲（実機検証済み）
PAN_CENTER = 80              # パンサーボの物理的中央（フレームが正面を向く位置）
PAN_LEFT = 35                # パンサーボの左端
PAN_RIGHT = 125              # パンサーボの右端

TILT_CENTER = 90             # チルトサーボの中央
TILT_DOWN = 45               # チルトサーボの下端
TILT_UP = 135                # チルトサーボの上端

# 台形制御パラメータ
STEP_ANGLE = 1               # 1ステップあたりの角度（度）
NORMAL_DELAY = 0.02          # 通常移動時の待機時間（秒）
SLOW_DISTANCE = 5            # 減速開始距離（度）
SLOW_DELAY = NORMAL_DELAY * 3  # 減速時の待機時間（秒）


def initialize_servo_kit():
    """
    ServoKitの初期化

    PCA9685チップを使用したサーボHATを初期化します。
    SG90サーボに最適なパルス幅（750-2250μs）を設定することで、
    振動を防止し、正確な角度制御を実現します。

    Returns:
        ServoKit: 初期化されたServoKitオブジェクト

    Raises:
        Exception: I2C通信エラーまたはサーボHAT接続エラー
    """
    # ServoKitの初期化（16チャンネル）
    kit = ServoKit(channels=SERVO_CHANNELS)

    # パルス幅範囲を設定（SG90サーボ用）
    # デフォルト設定（1000-2000μs）では振動が発生するため、
    # SG90の仕様（750-2250μs）に合わせて明示的に設定
    kit.servo[PAN_CHANNEL].set_pulse_width_range(PULSE_MIN, PULSE_MAX)
    kit.servo[TILT_CHANNEL].set_pulse_width_range(PULSE_MIN, PULSE_MAX)

    return kit


def move_servo_smooth(servo, start_angle, end_angle,
                      step=STEP_ANGLE, normal_delay=NORMAL_DELAY,
                      slow_distance=SLOW_DISTANCE):
    """
    台形制御でサーボを滑らかに移動

    急激な動作による振動・騒音を防止するため、目標位置に近づくと
    自動的に減速します。慣性による振動を抑制し、静かで滑らかな
    動作を実現します。

    Args:
        servo: ServoKitのサーボオブジェクト（kit.servo[n]）
        start_angle (float): 開始角度（度）
        end_angle (float): 目標角度（度）
        step (int): 1ステップあたりの角度（小さいほど滑らか、デフォルト1度）
        normal_delay (float): 通常移動時の待機時間（秒、デフォルト0.02）
        slow_distance (int): 減速開始距離（度、デフォルト5度）

    動作の流れ:
        1. 開始位置から目標位置へ1度ずつ移動
        2. 目標位置まで5度以内に近づいたら減速（3倍遅く）
        3. 目標位置で停止

    効果:
        - 振動の完全停止
        - 駆動音の大幅な低減
        - 滑らかで自然な動き
    """
    # 移動方向に応じて角度リストを生成
    if start_angle < end_angle:
        # 右方向または上方向への移動
        angles = range(int(start_angle), int(end_angle) + 1, step)
    else:
        # 左方向または下方向への移動
        angles = range(int(start_angle), int(end_angle) - 1, -step)

    angles_list = list(angles)

    # 各角度へ順次移動（台形制御）
    for angle in angles_list:
        # 目標位置までの距離を計算
        distance_to_end = abs(end_angle - angle)

        # 目標位置に近づいたら減速
        if distance_to_end <= slow_distance:
            delay = SLOW_DELAY  # 減速（3倍遅く）
        else:
            delay = normal_delay  # 通常速度

        # サーボを移動
        servo.angle = angle
        time.sleep(delay)


def set_pan_angle(kit, angle, smooth=True):
    """
    パンサーボ（左右）を指定角度に移動

    Args:
        kit (ServoKit): 初期化済みのServoKitオブジェクト
        angle (float): 目標角度（PAN_LEFT～PAN_RIGHT、35-125度）
        smooth (bool): 台形制御を使用するか（デフォルトTrue）

    Raises:
        ValueError: 角度が範囲外の場合
    """
    # 角度の範囲チェック
    if not (PAN_LEFT <= angle <= PAN_RIGHT):
        raise ValueError(
            f"パン角度は {PAN_LEFT}～{PAN_RIGHT}度の範囲で指定してください（指定値: {angle}度）"
        )

    # 現在の角度を取得（初回はNoneの場合がある）
    try:
        current_angle = kit.servo[PAN_CHANNEL].angle
        if current_angle is None:
            current_angle = PAN_CENTER
    except:
        current_angle = PAN_CENTER

    # 台形制御で移動
    if smooth:
        move_servo_smooth(kit.servo[PAN_CHANNEL], current_angle, angle)
    else:
        # 直接移動（テスト用）
        kit.servo[PAN_CHANNEL].angle = angle


def set_tilt_angle(kit, angle, smooth=True):
    """
    チルトサーボ（上下）を指定角度に移動

    Args:
        kit (ServoKit): 初期化済みのServoKitオブジェクト
        angle (float): 目標角度（TILT_DOWN～TILT_UP、45-135度）
        smooth (bool): 台形制御を使用するか（デフォルトTrue）

    Raises:
        ValueError: 角度が範囲外の場合
    """
    # 角度の範囲チェック
    if not (TILT_DOWN <= angle <= TILT_UP):
        raise ValueError(
            f"チルト角度は {TILT_DOWN}～{TILT_UP}度の範囲で指定してください（指定値: {angle}度）"
        )

    # 現在の角度を取得（初回はNoneの場合がある）
    try:
        current_angle = kit.servo[TILT_CHANNEL].angle
        if current_angle is None:
            current_angle = TILT_CENTER
    except:
        current_angle = TILT_CENTER

    # 台形制御で移動
    if smooth:
        move_servo_smooth(kit.servo[TILT_CHANNEL], current_angle, angle)
    else:
        # 直接移動（テスト用）
        kit.servo[TILT_CHANNEL].angle = angle


def set_pan_tilt(kit, pan_angle, tilt_angle, smooth=True):
    """
    パンとチルトを同時に指定角度に移動

    Args:
        kit (ServoKit): 初期化済みのServoKitオブジェクト
        pan_angle (float): パンの目標角度（35-125度）
        tilt_angle (float): チルトの目標角度（45-135度）
        smooth (bool): 台形制御を使用するか（デフォルトTrue）

    Raises:
        ValueError: 角度が範囲外の場合
    """
    # パンを移動
    set_pan_angle(kit, pan_angle, smooth)

    # チルトを移動
    set_tilt_angle(kit, tilt_angle, smooth)


def set_center_position(kit, smooth=True):
    """
    両サーボを中央位置に移動

    Args:
        kit (ServoKit): 初期化済みのServoKitオブジェクト
        smooth (bool): 台形制御を使用するか（デフォルトTrue）
    """
    set_pan_angle(kit, PAN_CENTER, smooth)
    set_tilt_angle(kit, TILT_CENTER, smooth)


def release_servos(kit):
    """
    サーボを解放して振動を完全に停止

    サーボの電力供給を停止することで、位置保持をやめます。
    振動が気になる場合や、バッテリー節約のために使用します。

    Args:
        kit (ServoKit): 初期化済みのServoKitオブジェクト

    注意:
        サーボを解放すると位置保持ができなくなります。
        重いカメラを搭載している場合は、サーボが動いてしまう可能性があります。
    """
    kit.servo[PAN_CHANNEL].fraction = None
    kit.servo[TILT_CHANNEL].fraction = None


def test_pan_servo(kit):
    """
    パンサーボの動作テスト

    左端 → 中央 → 右端 → 中央の順に動作確認を行います。

    Args:
        kit (ServoKit): 初期化済みのServoKitオブジェクト
    """
    print("\n=== パンサーボ動作テスト ===")

    print(f"左端へ移動 ({PAN_LEFT}度)...")
    set_pan_angle(kit, PAN_LEFT)
    time.sleep(1)

    print(f"中央へ移動 ({PAN_CENTER}度)...")
    set_pan_angle(kit, PAN_CENTER)
    time.sleep(1)

    print(f"右端へ移動 ({PAN_RIGHT}度)...")
    set_pan_angle(kit, PAN_RIGHT)
    time.sleep(1)

    print(f"中央へ戻ります ({PAN_CENTER}度)...")
    set_pan_angle(kit, PAN_CENTER)
    time.sleep(1)

    print("✓ パンサーボテスト完了")


def test_tilt_servo(kit):
    """
    チルトサーボの動作テスト

    下端 → 中央 → 上端 → 中央の順に動作確認を行います。

    Args:
        kit (ServoKit): 初期化済みのServoKitオブジェクト
    """
    print("\n=== チルトサーボ動作テスト ===")

    print(f"下端へ移動 ({TILT_DOWN}度)...")
    set_tilt_angle(kit, TILT_DOWN)
    time.sleep(1)

    print(f"中央へ移動 ({TILT_CENTER}度)...")
    set_tilt_angle(kit, TILT_CENTER)
    time.sleep(1)

    print(f"上端へ移動 ({TILT_UP}度)...")
    set_tilt_angle(kit, TILT_UP)
    time.sleep(1)

    print(f"中央へ戻ります ({TILT_CENTER}度)...")
    set_tilt_angle(kit, TILT_CENTER)
    time.sleep(1)

    print("✓ チルトサーボテスト完了")


def test_pan_tilt_combined(kit):
    """
    パン・チルト複合動作テスト

    複数の位置を順番に動かして、複合動作を確認します。

    Args:
        kit (ServoKit): 初期化済みのServoKitオブジェクト
    """
    print("\n=== パン・チルト複合動作テスト ===")

    # テストパターン: (パン角度, チルト角度, 説明)
    test_patterns = [
        (PAN_CENTER, TILT_CENTER, "中央"),
        (PAN_LEFT, TILT_CENTER, "左"),
        (PAN_CENTER, TILT_UP, "上"),
        (PAN_RIGHT, TILT_CENTER, "右"),
        (PAN_CENTER, TILT_DOWN, "下"),
        (PAN_LEFT, TILT_UP, "左上"),
        (PAN_RIGHT, TILT_UP, "右上"),
        (PAN_RIGHT, TILT_DOWN, "右下"),
        (PAN_LEFT, TILT_DOWN, "左下"),
        (PAN_CENTER, TILT_CENTER, "中央に戻る"),
    ]

    for pan, tilt, description in test_patterns:
        print(f"{description}へ移動 (パン: {pan}度, チルト: {tilt}度)...")
        set_pan_tilt(kit, pan, tilt)
        time.sleep(1.5)

    print("✓ 複合動作テスト完了")


def main():
    """
    メイン関数：サーボの動作テストを実行

    スタンドアロン実行時にサーボの動作確認を行います。
    ライブラリとしてimportされた場合は、この関数は実行されません。
    """
    print("=" * 60)
    print("パン・チルトサーボ制御プログラム")
    print("=" * 60)
    print()
    print("このプログラムは、サーボモーターの基本動作をテストします。")
    print("各テストが順番に実行されます。")
    print()
    print(f"動作範囲:")
    print(f"  パン  : {PAN_LEFT}～{PAN_RIGHT}度（中央: {PAN_CENTER}度）")
    print(f"  チルト: {TILT_DOWN}～{TILT_UP}度（中央: {TILT_CENTER}度）")
    print()

    try:
        # サーボの初期化
        print("サーボモーターを初期化中...")
        kit = initialize_servo_kit()
        print(f"✓ 初期化完了（パルス幅: {PULSE_MIN}-{PULSE_MAX}μs）")

        # 中央位置へ移動
        print("\n中央位置へ移動...")
        set_center_position(kit)
        time.sleep(1)
        print("✓ 中央位置に移動しました")

        # パンサーボテスト
        test_pan_servo(kit)
        time.sleep(1)

        # チルトサーボテスト
        test_tilt_servo(kit)
        time.sleep(1)

        # 複合動作テスト
        test_pan_tilt_combined(kit)

        print("\n全てのテストが完了しました。")
        print("Ctrl+C を押すと終了します。")

        # 待機モード
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n割り込み信号を受信しました。終了処理を実行中...")

    except ValueError as e:
        print(f"\n設定エラー: {e}")

    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        print("\n対処方法:")
        print("  1. サーボHATが正しく接続されているか確認")
        print("  2. I2C接続を確認: i2cdetect -y 1")
        print("  3. サーボ用電源が接続されているか確認")
        print("  4. サーボがチャンネル0（パン）と1（チルト）に接続されているか確認")

    finally:
        # サーボを解放（振動停止）
        print("\nサーボを解放します...")
        try:
            release_servos(kit)
            print("✓ サーボを解放しました")
        except:
            pass

        print("プログラムを終了しました。")


# ライブラリとしてimportされた場合はmain()を実行しない
if __name__ == "__main__":
    main()
