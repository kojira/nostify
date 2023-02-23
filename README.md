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

## 設定

### 設定ファイル

`common/config.yml` が設定ファイルです。
現状はリレーサーバーの設定のみです。
デフォルトで以下のものを入れてあります。

```yml
relay_servers:
  - "wss://relay-jp.nostr.wirednet.jp"
  - "wss://relay.damus.io"
  - "wss://relay.nostr.wirednet.jp"
  - "wss://nostr.h3z.jp"
  - "wss://relay.snort.social"
  - "wss://nostr-pub.wellorder.net/"
  - "wss://relay.current.fyi"
  - "wss://nos.lol"
```

### NGワード指定

http://127.0.0.1:8080 からPHPMyAdminが使えます。
ng_wordsテーブルに指定したキーワードが含まれるNoteを無視するようになります。
statusは0で有効、0以外で無効です。

## TODO

- [x] 設定したフィルタを削除する機能
- [x] フィルタの設定状況を確認する機能
- [x] キーワード指定できるようにしてcontentの内容が一致したら投稿する機能
- [ ] リポストを取得できるようにする
- [ ] kind 1以外のフィルタも指定できるようにする
- [ ] 過去ログを検索できる機能
- [ ] Eventの統計情報をグラフ表示する機能
- [ ] kind 0のリクエストを減らすため、ユーザーテーブルを作ってキャッシュする
