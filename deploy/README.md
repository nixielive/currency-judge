# PC起動時の自動収集（systemd）

このサービスはUbuntuのtakeshiユーザーと現在のプロジェクト配置専用です。
ユーザー名・プロジェクトの場所を変える場合はサービス内のパスを変更してください。
パスには実体の `/home/takeshi/ドキュメント/projects/currency-judge` を使っています。

## 登録・起動

ターミナルで手動収集が動いていればCtrl+Cで止め、重複起動を避けてください。
プロジェクトのルートから実行します。

```sh
sudo install -m 644 deploy/currency-judge.service /etc/systemd/system/currency-judge.service
sudo systemctl daemon-reload
sudo systemctl enable --now mysql.service currency-judge.service
systemctl status currency-judge.service --no-pager
```

ログイン前から起動し、VS Codeやターミナルを閉じても収集を続けます。
正常時は10秒間隔で6ペアを追記します。取得失敗時は最大300秒のバックオフ、
プロセス終了時は15秒後にsystemdが再起動します。MySQLの起動後に開始し、
起動時にDBへ接続できなければ再起動を繰り返します。
実行中のMySQL接続切断は次の保存トランザクション前に再接続を試みます。
途中までの保存トランザクションを自動で再実行することはありません。
通信・DB停止中やスリープ・電源断中の観測は後から取得できません。

## ログと操作

```sh
# ログをリアルタイムに表示（Ctrl+Cはログ表示だけを停止）
journalctl -u currency-judge.service -f
# 停止
sudo systemctl stop currency-judge.service
# 再起動（Pythonコードや接続設定の変更後）
sudo systemctl restart currency-judge.service
# 自動起動を無効化して停止
sudo systemctl disable --now currency-judge.service
```

停止時にはSIGINTを送り、現在の処理を終えてDB接続を閉じます。
サービス定義を変更した場合は、プロジェクト内のファイルを再度installし、
daemon-reloadとrestartを実行します。PCのスリープ中は収集されないため、
常時収集したい場合はUbuntuの電源設定で自動サスペンドを無効にしてください。

## 保存確認（DBeaver）

```sql
SELECT id, status, completed_at FROM collection_runs ORDER BY id DESC LIMIT 10;
SELECT symbol, quality, received_at FROM quotes ORDER BY id DESC LIMIT 6;
```

再起動後もログと上記の時刻が進むことを確認してください。
