#!/usr/bin/env python3
"""
チルトサーボ単体テストスクリプト
サーボライブラリを直接呼び出して上下可動域の確認を行う
"""

import time
import servo_control


def main():
    print("=" * 50)
    print("チルトサーボ単体テスト")
    print("=" * 50)
    print()
    print(f"可動範囲: {servo_control.TILT_DOWN}° (下) 〜 {servo_control.TILT_UP}° (上)")
    print(f"中央位置: {servo_control.TILT_CENTER}°")
    print()

    try:
        # サーボ初期化
        print("サーボを初期化中...")
        kit = servo_control.initialize_servo_kit()
        print("[OK] 初期化完了")
        print()

        # 中央位置へ移動（台形制御で滑らかに）
        print(f"1. 中央位置へ移動 ({servo_control.TILT_CENTER} deg)...")
        servo_control.set_tilt_angle(kit, servo_control.TILT_CENTER, smooth=True)
        time.sleep(1)
        print("   完了")
        print()

        # 下端へ移動（台形制御で滑らかに）
        print(f"2. 下端へ移動 ({servo_control.TILT_DOWN} deg)...")
        servo_control.set_tilt_angle(kit, servo_control.TILT_DOWN, smooth=True)
        time.sleep(1)
        print("   完了")
        print()

        # 上端へ移動（台形制御で滑らかに）
        print(f"3. 上端へ移動 ({servo_control.TILT_UP} deg)...")
        servo_control.set_tilt_angle(kit, servo_control.TILT_UP, smooth=True)
        time.sleep(1)
        print("   完了")
        print()

        # 中央に戻る（台形制御で滑らかに）
        print(f"4. 中央位置へ戻る ({servo_control.TILT_CENTER} deg)...")
        servo_control.set_tilt_angle(kit, servo_control.TILT_CENTER, smooth=True)
        time.sleep(1)
        print("   完了")
        print()

        print("=" * 50)
        print("テスト完了")
        print("=" * 50)
        print()
        print("確認事項:")
        print("  - サーボが物理的に動いたか？")
        print("  - 中央→下→上→中央 の順に動作したか？")
        print()

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("サーボを解放...")
        try:
            servo_control.release_servos(kit)
        except:
            pass
        print("終了")


if __name__ == "__main__":
    main()
