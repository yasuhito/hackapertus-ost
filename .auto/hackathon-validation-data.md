# ハッカソンの検証データ確認

確認日: 2026-10-14（実行環境の時計）。対象: Track 2A OST。

## 結論

**正解ラベル付きの公式公開データはあります。ただし、独立した公開 validation/dev/test 分割は確認できませんでした。現在確認できた公開分割は train のみです。未使用の独立検証データがあるとは言えません。**

- 公式スターター README は `v1.1.jsonl` から各行について Task A と Task B を作り、正解を `expected-labels.jsonl` に出力すると説明しています。原文: “one task A and one task B case per row”, “contains gold labels for local scoring only”。[S1: 28–46行]
- 公開データのメタデータでは `default/train` が **1,488行**。ファイル一覧は README、`v1.1.jsonl`、`v1.1.parquet` などで、別の検証・テストファイルはありません。取得時点の revision は `fc2b27600310778da6bbf445651ddbca22d86269`、最終更新は 2026-10-08。`private:false`、`gated:false`、ライセンスは MIT。[S2–S5]
- データカードには独仏伊、ラベル `0/1/2`、`reference_string`、`booklet_url`、日付フィールドが記載されています。Task A の冊子と Task B の参照文に対応します。収録日付の範囲、日付別件数、Task A の正解ページ番号は確認したカードに記載されていません。1,488 は元データ行数で、Task A/B 合計件数ではありません。[S2]
- 本番評価について README は “The official score uses a held-out private set” と明記しています。これは公開ラベル付き開発データとは別の非公開評価セットです。ラベルなし提出用 test の配布、利用者向け採点サーバー、アクセス条件は確認できませんでした。LLM 接続用 proxy は検証用採点サーバーと同一視できません。[S1: 206–209行]

## 未確認と制約

公式サイトの公開 HTML とそのリンク先の公開表示用 JavaScript は取得でき、Getting Started Guide へのリンクを確認しました。[S6] Notion は JavaScript 必須の画面しか取得できず、スターターからリンクされた詳細ガイドは HTTP 403 でした。[S7–S8] したがって、詳細ガイドに別データの案内がないとは断定しません。

ローカル README は公開 `v1.1.jsonl` の利用を記載していますが、今回 dev54 の行照合や利用履歴監査はしていません。同じ公開データに候補があっても「未使用」は未確認です。依頼時の情報では dev54 と内部 test は既に繰り返し評価済みで、新しい独立検証とは扱えません。公式の非公開セットと、プロジェクト内の保護対象 holdout も区別してください。

## 安全な次の一手

まず主催者に、参加者向けの別ラベル付き dev/validation と採点サービスの有無を問い合わせてください。公開 train の別部分を使う場合も、所有者の承認後に revision、既使用データとの重複、保護対象の除外を確認し、評価前に範囲を固定する必要があります。今回、データ本体・PDFのダウンロード、データプレビュー、モデル呼び出し、評価、提出、保護 holdout へのアクセスはしていません。

## 一次資料（すべて上記確認日にアクセス）

- S1: [公式スターター README、指定 commit](https://gitlab.com/ifsoftware/hackapertus-starter/-/blob/5e6957729b77a126006049305ad1ef241211a5b4/README.md)
- S2: [OST データカード、確認 revision](https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets/blob/fc2b27600310778da6bbf445651ddbca22d86269/README.md)
- S3: [公開状態・revision・ファイル一覧 API](https://huggingface.co/api/datasets/OSTswiss/MNLIoverSwissVotingBooklets)
- S4: [分割メタデータ API](https://datasets-server.huggingface.co/splits?dataset=OSTswiss%2FMNLIoverSwissVotingBooklets)
- S5: [件数メタデータ API](https://datasets-server.huggingface.co/size?dataset=OSTswiss%2FMNLIoverSwissVotingBooklets)
- S6: [公式オンラインハックサイト](https://hackapertus.ch/online-hack)、[同ページが参照する表示用 JavaScript](https://hackapertus.ch/assets/index-Bp_XzZcx.js)
- S7: [公式サイトが案内する Getting Started Guide](https://hackapertus.notion.site/getting-started-guide-onlinehack)
- S8: [スターターが案内する詳細ガイド](https://notes.rehash.ch/s/7912e1d2-5d79-4c93-add9-12ec4a6d1b1e)
- ローカル補助資料: `README.md:81–89`、`track_2a/README.md:19–20`（作業ツリー。公開元とローカル利用の説明のみ確認）。
