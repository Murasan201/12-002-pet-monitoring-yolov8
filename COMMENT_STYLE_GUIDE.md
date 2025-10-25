# Pythonコメント記載標準ガイド

## 概要

このドキュメントは、初心者向け教育教材として最適なPythonコードのコメント記載方法を定義します。
`lcd_display.py`で実践されているコメントスタイルを標準化し、他のプロジェクトにも展開可能な形式としてまとめています。

## 基本方針

### 目的
- **初心者が理解できる**: プログラミング初心者でも処理内容を理解できる説明
- **適度な情報量**: コードの可読性を損なわない程度の詳細さ
- **実用的な情報**: 実際の使用シーンで役立つヒントや注意事項を含む

### 言語
- **日本語**: すべてのコメントは日本語で記載する
- **明確な表現**: 技術用語は必要に応じて説明を加える

---

## 1. ファイルヘッダーコメント

### 形式
```python
#!/usr/bin/env python3
"""
[プロジェクト名]
[簡潔な説明文：1-2行]
要件定義書: [要件定義書ファイル名]
"""
```

### 実例
```python
#!/usr/bin/env python3
"""
LCD文字表示アプリ
LCD1602モジュールに文字列を表示するPythonアプリケーション
要件定義書: 06-002_LCD文字表示アプリ_要件定義書.md
"""
```

### 重要ポイント
- ファイルの目的を1-2行で簡潔に説明
- 要件定義書や関連ドキュメントへの参照を記載
- シバン（`#!/usr/bin/env python3`）を必ず含める

---

## 2. クラスのdocstring

### 形式
```python
class ClassName:
    """
    [クラスの役割を1行で説明]
    [補足情報：設計意図や対象ユーザーなど]
    """
```

### 実例
```python
class LCDDisplay:
    """
    LCD1602ディスプレイを制御するクラス
    初心者向けに機能を整理し、簡潔な実装にしています
    """
```

### 重要ポイント
- クラスの役割を明確に記載
- 設計意図や教育的配慮があれば追加説明
- 短く簡潔に（3行以内推奨）

---

## 3. メソッド/関数のdocstring

### 形式（引数あり）
```python
def method_name(self, arg1, arg2='default'):
    """
    [処理内容を1行で説明]

    Args:
        arg1 (型): 引数の説明（使用例や注意事項も記載）
        arg2 (型): 引数の説明（デフォルト値の意味も説明）
    """
```

### 実例1: 初期化メソッド
```python
def __init__(self, i2c_address=0x27, i2c_port=1, charmap='A02'):
    """
    LCDディスプレイの初期化

    Args:
        i2c_address (int): I²Cアドレス（通常0x27または0x3F）
        i2c_port (int): I²Cポート番号（Raspberry Pi 5では通常1）
        charmap (str): 文字マップ（'A02'または'A00'、文字化け時は切り替え）
    """
```

### 実例2: シンプルなメソッド
```python
def clear_display(self):
    """
    画面をクリアする
    """
```

### 実例3: 複雑なメソッド
```python
def scroll_text(self, text, line=1, scroll_delay=0.3):
    """
    長い文字列をスクロール表示する

    Args:
        text (str): 表示する文字列
        line (int): 表示行（1または2）
        scroll_delay (float): スクロール間隔（秒）
    """
```

### 重要ポイント
- 処理内容を1行で簡潔に説明
- 引数の型と説明を明確に記載
- 典型的な値や使用例を括弧内に追加
- デフォルト値の意味を説明
- 引数がない場合は1行のみでOK

---

## 4. インラインコメント

### 原則
- **重要な処理**: 複雑なロジックや重要な判定には必ずコメント
- **初心者への配慮**: ライブラリの仕様や技術的な背景を説明
- **実用的なヒント**: トラブルシューティング情報を含める

### パターン1: 初期化処理
```python
# RPLCDライブラリを使用してPCF8574T搭載のI²C接続LCDを初期化
# PCF8574TはPCF8574の低電圧版で、指定は'PCF8574'でOK
self.lcd = CharLCD(
    i2c_expander='PCF8574',  # PCF8574Tもこの指定で動作
    address=i2c_address,
    port=i2c_port,
    cols=16, rows=2,
    charmap=charmap,         # 文字化け時はA00に変更
    auto_linebreaks=True
)
```

**ポイント**:
- ライブラリの仕様や互換性情報を記載
- トラブルシューティングのヒント（文字化け対策など）

### パターン2: 座標・位置指定
```python
# 行の指定（1行目: (0,0), 2行目: (0,1)）
if line == 1:
    self.lcd.cursor_pos = (0, 0)
elif line == 2:
    self.lcd.cursor_pos = (0, 1)
```

**ポイント**:
- ユーザー視点（1行目/2行目）とシステム視点（0/1）の対応を明示

### パターン3: アルゴリズム説明
```python
# 16文字以内の場合はそのまま表示
if len(text) <= 16:
    # 行をクリアしてから表示
    self.lcd.write_string(' ' * 16)  # 行をクリア
    self.lcd.cursor_pos = (0, line - 1)
    self.lcd.write_string(text)
```

**ポイント**:
- 条件分岐の意図を説明
- 各ステップの目的を明示

### パターン4: バグ対策・特殊処理
```python
# バックライトを明示的に有効化（一部基板で必要）
self.lcd.backlight_enabled = True
```

**ポイント**:
- なぜこの処理が必要なのかを説明
- ハードウェアの違いなど実装背景を記載

### パターン5: ループ処理の説明
```python
# 文字列の末尾にスペースを追加してループしやすくする
scroll_text = text + "    "

# スクロール表示（文字列を一周表示）
for i in range(len(scroll_text)):
    # 表示する16文字の部分を取得
    display_part = scroll_text[i:i+16]

    # 16文字に満たない場合は先頭から補完
    if len(display_part) < 16:
        display_part += scroll_text[:16-len(display_part)]
```

**ポイント**:
- データ加工の意図を説明
- ループ処理全体の目的を記載
- 各ステップの役割を明示

---

## 5. エラーハンドリングのコメント

### 形式
```python
try:
    # 処理内容
    pass
except Exception as e:
    print(f"[処理名]エラー: {e}")
    print("[ユーザー向けヒント]")
```

### 実例
```python
try:
    self.lcd = CharLCD(...)
    print(f"LCD初期化完了: I²Cアドレス 0x{i2c_address:02X}, charmap={charmap}")
except Exception as e:
    print(f"LCD初期化エラー: {e}")
    print("接続とI²Cアドレスを確認してください")
    print("ヒント: i2cdetect -y 1 でアドレスを確認")
    sys.exit(1)
```

### 重要ポイント
- エラーメッセージには処理名を含める
- ユーザーが実行可能な対処方法を提示
- 具体的なコマンド例を記載

---

## 6. main関数のコメント

### 形式
```python
def main():
    """
    メイン関数：[全体の処理フローを簡潔に説明]
    """
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(...)

    # 引数の定義
    parser.add_argument(...)

    # [変数名]の変換（説明）
    try:
        # 変換処理
        pass
    except ValueError:
        # エラー処理
        pass

    # [オブジェクト名]の初期化
    obj = ClassName(...)

    try:
        # 実行モードに応じた処理
        if condition1:
            # [モード名]モード
            pass
        elif condition2:
            # [モード名]モード
            pass

    except KeyboardInterrupt:
        print("\n\n割り込み信号を受信しました。終了処理を実行中...")

    except Exception as e:
        print(f"実行エラー: {e}")

    finally:
        # 必ずリソースをクリーンアップ
        obj.close()
```

### 実例
```python
def main():
    """
    メイン関数：コマンドライン引数を処理してLCD表示を実行
    """
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(...)

    # I²Cアドレスの変換（文字列から整数へ）
    try:
        if args.address.startswith('0x'):
            i2c_addr = int(args.address, 16)
        else:
            i2c_addr = int(args.address)
    except ValueError:
        print(f"エラー: 無効なI²Cアドレス '{args.address}'")
        sys.exit(1)

    # LCDディスプレイの初期化
    lcd_display = LCDDisplay(...)

    try:
        # 実行モードに応じた処理
        if args.clear:
            # 画面クリアモード
            lcd_display.clear_display()

        elif args.test:
            # テストモード
            print("テスト表示を開始します...")
            ...

    except KeyboardInterrupt:
        print("\n\n割り込み信号を受信しました。終了処理を実行中...")

    finally:
        # 必ずリソースをクリーンアップ
        lcd_display.close()
```

### 重要ポイント
- 処理の区切りごとにセクションコメント
- 各モードの説明を記載
- 例外処理の意図を明示

---

## 7. コメント記載のベストプラクティス

### DO（推奨）

✅ **処理の意図を説明する**
```python
# 行をクリアしてから表示
self.lcd.write_string(' ' * 16)
```

✅ **初心者向けの補足情報**
```python
# PCF8574TはPCF8574の低電圧版で、指定は'PCF8574'でOK
i2c_expander='PCF8574'
```

✅ **トラブルシューティング情報**
```python
# 文字化け時はA00に変更
charmap=charmap
```

✅ **座標や値の対応関係**
```python
# 行の指定（1行目: (0,0), 2行目: (0,1)）
```

✅ **ハードウェア固有の情報**
```python
# バックライトを明示的に有効化（一部基板で必要）
self.lcd.backlight_enabled = True
```

### DON'T（非推奨）

❌ **コードをそのまま日本語にしただけ**
```python
# write_stringを実行する
self.lcd.write_string(text)
```

❌ **自明な内容の繰り返し**
```python
# textをprintする
print(text)
```

❌ **過度に長いコメント**
```python
# この関数はLCD1602ディスプレイに文字列を表示するための関数です。
# 引数として受け取った文字列を16文字ごとに区切って表示します。
# 表示位置は1行目または2行目を指定できます。
# （50行以上続く...）
```

❌ **技術用語の説明なし**
```python
# PCF8574Tで初期化
self.lcd = CharLCD(i2c_expander='PCF8574', ...)
```
→ 初心者にはPCF8574とPCF8574Tの関係がわからない

---

## 8. コメント記載チェックリスト

コードレビュー時に以下を確認してください：

### ファイルレベル
- [ ] ファイルヘッダーに目的と要件定義書への参照があるか
- [ ] シバンが記載されているか

### クラスレベル
- [ ] クラスのdocstringが簡潔かつ明確か
- [ ] 設計意図や対象ユーザーが記載されているか

### メソッド/関数レベル
- [ ] docstringに処理内容が記載されているか
- [ ] 引数の型と説明が明確か
- [ ] 典型的な値や使用例が記載されているか

### インラインコメント
- [ ] 複雑な処理に説明があるか
- [ ] 初心者向けの補足情報があるか
- [ ] トラブルシューティング情報が含まれているか
- [ ] ハードウェア固有の情報が説明されているか

### エラーハンドリング
- [ ] エラーメッセージに処理名が含まれているか
- [ ] ユーザー向けの対処方法が提示されているか
- [ ] 具体的なコマンド例が記載されているか

---

## 9. プロジェクト別カスタマイズ

このガイドは基本フォーマットです。各プロジェクトの特性に応じて以下をカスタマイズしてください：

### ハードウェア関連プロジェクト
- 電気的仕様（電圧、電流など）の記載
- 配線情報や安全注意事項
- 互換性情報（チップバージョンなど）

### API/Web関連プロジェクト
- エンドポイントの説明
- レスポンス形式の例
- レート制限やタイムアウト情報

### データ処理関連プロジェクト
- データ形式の説明
- 変換ロジックの詳細
- パフォーマンス考慮事項

---

## 10. 参考資料

- **PEP 257**: Docstring Conventions
- **Google Python Style Guide**: Comments and Docstrings
- **本プロジェクト**: `lcd_display.py`（実装例）

---

**最終更新**: 2025-10-23
**文書番号**: COMMENT-STYLE-GUIDE-001
**対象**: 教育向けPythonプロジェクト全般
