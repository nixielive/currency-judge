# Ubuntu MySQLセットアップ

リポジトリのルートで実行します。MySQL 8.0以上が必要です。

## DBとユーザー（管理者操作）

```sh
sudo mysql < sql/mysql_schema.sql
sudo mysql < sql/mysql_user.sql
```

2つ目のコマンドは新規ユーザーを作り、生成されたパスワードを表示します。
既存ユーザーがある場合は停止するので、パスワードを変更する前に接続設定を確認してください。
パスワードはチャットに貼らず、次のローカル設定に記入します。

```sh
install -m 600 config/mysql.example.cnf config/mysql.cnf
code config/mysql.cnf
```

`password` を生成された値に置き換えて保存します。このファイルはGit管理外です。
ユーザーはこのDBのSELECT/INSERTのみ許可され、履歴の更新・削除はできません。

## 実行

```sh
.venv/bin/python -m pip install -e '.[mysql]'
PYTHONPATH=src .venv/bin/python -m currency_judge --mysql-config config/mysql.cnf --once
# 10秒ごとの収集（Ctrl+Cで停止）
PYTHONPATH=src .venv/bin/python -m currency_judge --mysql-config config/mysql.cnf
```

SQLiteの既存データは移行しません。MySQLに新しい観測を追記します。
価格はDecimal文字列、時刻はUTCオフセット付きISO文字列、JSONは元応答の内容を保存します。
テーブルはInnoDBで、取得履歴と6ペアを1トランザクションに保存します。
DB自体が停止している間はエラー履歴もDBへ保存できず、CLIログに出力します。

## DBeaver

新規接続でMySQLを選び、以下を入力します。

- Host: `127.0.0.1`
- Port: `3306`
- Database: `currency_judge`
- Username: `currency_judge`
- Password: 上記の生成値

初回に求められたMySQLドライバーをダウンロードし、接続テストします。
ローカル接続で「Public Key Retrieval is not allowed」が出る場合は、
ドライバープロパティの `allowPublicKeyRetrieval` を `true` に設定します。

```sql
SELECT symbol, bid, ask, quality, price_time, received_at
FROM quotes ORDER BY id DESC LIMIT 6;
SELECT status, COUNT(*) FROM collection_runs GROUP BY status;
```
