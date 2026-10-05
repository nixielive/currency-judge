# Currency Judge

複数の為替レートを入力に、USD/JPYの5分後の方向を検証する実験用システム。
現在は最初の段階として、GMOコインの公開APIからのレート収集とSQLite保存に対応しています。
MySQL 8.0以上への保存も選択できます。DB・ユーザーの作成と接続手順は
[MySQLセットアップ](config/MYSQL_SETUP.md)を参照してください（実MySQLへの単発保存を確認済み）。
予測・答え合わせ・Web UI・売買シミュレーションは今後の実装です。詳細は [PLAN.md](PLAN.md)。

## 起動

Python 3.12以上が必要です。現段階では外部パッケージ、口座、APIキーは不要です。
リポジトリのルートで実行してください。

```sh
# 1回取得して終了
PYTHONPATH=src python3 -m currency_judge --once

# 10秒ごとに継続取得（Ctrl+Cで終了）
PYTHONPATH=src python3 -m currency_judge

# 保存先と間隔を指定
PYTHONPATH=src python3 -m currency_judge --db data/experiment.sqlite3 --interval 30
```

PCのスリープ・電源断中は収集できません。再起動時には既存DBへ追記します。
UbuntuでPC起動時から自動収集するには、[systemdサービスの導入手順](deploy/README.md)を使用します。
失敗時は最大300秒まで待機時間を延ばして再試行します。単発取得の失敗は終了コード1です。

## 保存データ

- `collection_runs`: 取得開始・完了時刻、成功/失敗、エラー、成功応答JSON。
- `quotes`: 取得元、通貨ペア、bid/ask/mid、価格時刻、受信時刻、市場状態、品質。
- 価格はDecimalで計算して文字列保存し、時刻はUTCオフセット付きISO形式で保存。
- 品質は `VALID` / `CLOSED` / `STALE` / `FUTURE`。15秒超の古い価格はSTALE。
- 6ペアの欠損、不正価格、不正時刻はそのバッチを保存せず失敗を記録。
- 過去の観測は上書きしません。品質がVALIDでも予測入力として使えるかは今後の予測時刻条件で判定します。

```sh
sqlite3 -header -column data/currency_judge.sqlite3 'SELECT symbol,bid,ask,quality,received_at FROM quotes ORDER BY id DESC LIMIT 6;'
```

SQLiteはWALモードです。稼働中のバックアップにはSQLiteのバックアップ機能を使用してください。

## Ubuntu / VS Codeでの開発

Python 3.12以上とVS Codeで、Macと同じソースコードを使って開発できます。
Macの仮想環境はコピーせず、Ubuntu側で作り直します。

```sh
# 現段階は標準ライブラリだけなのでpipなしで作成可能
python3 -m venv --without-pip .venv
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
code .
```

MySQL用依存を導入する際にpipがなければ、Ubuntuの `python3.12-venv` を
インストールして `python3 -m venv .venv` でpip付き環境を作成します。

VS Codeの推奨拡張は公式Codex（`openai.chatgpt`）とPython（`ms-python.python`）です。
Codexのサイドバーを開き、必要ならChatGPTアカウントでサインインしてください。
Pythonインタープリターは `.venv/bin/python` を選択します。
テストビューでunittestを実行でき、実行とデバッグの「為替レートを1回取得」で単発取得できます。

開発方針は `AGENTS.md`、進捗と次の作業は `PLAN.md` に記録されています。
Mac側の会話にしかない要件は別途引き継いでください。
過去の収集データはGit管理対象外の `data/` にあるため、必要ならMacから別途移行します。
稼働中のSQLiteの移行には、上記のバックアップ機能を使用してください。

## テスト実行

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

テストは固定データと一時DBを使い、ネットワーク接続や実際の待機を必要としません。

## データ取得元

[GMOコイン外国為替FX API](https://api.coin.z.com/fxdocs/) の
`https://forex-api.coin.z.com/public/v1/ticker` を利用します。
初期入力はUSD/JPY、EUR/USD、EUR/JPY、GBP/USD、GBP/JPY、AUD/USDです。
