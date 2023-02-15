# Nostify

[Nostr](https://github.com/nostr-protocol/nips)のリレーサーバーに接続して、discordに投稿するdiscord botのソースコードです。

## 起動方法

リポジトリをクローンします。
```sh
git clone https://github.com/kojira/nostify.git
cd nostify
cp .env.example .env
cp ./bot/.env.example ./bot/.env
```

`./bot/.env`の環境変数を適切な値に編集します。
```
BOT_TOKEN=replace your bot token
BOT_APPLICATION_ID=replace your bot application id
ADMIN_GUILD=admin guild id
```

以下のコマンドで実行。

```sh
docker compose up -d
```

## commands

|command|function|
|--|--|
|/filter|npubで始まる文字列を指定するとNostr上に新たに該当の投稿を見つけるとコマンドを実行したチャンネルに投稿する。現状指定できるのは投稿者の公開鍵のみ。|
|/help|ヘルプコマンドを表示|

## NGワード指定

http://127.0.0.1:8080 からPHPMyAdminが使えます。
ng_wordsテーブルに指定したキーワードが含まれるNoteを無視するようになります。
statusは0で有効、0以外で無効です。


