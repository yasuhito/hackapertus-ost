# CSCS dev54の有限評価ジョブ

`--user-run`を明示すると固定の課金を伴うジョブを開始します。TTYとYES入力は不要です。実行者が範囲とcredits消費を事前に承認した場合だけ使ってください。

```sh
./track_2a/dev/cscs/run.sh --user-run
```

準備だけ（キーを読まず通信しない）：

```sh
./track_2a/dev/cscs/run.sh --prepare-only
```

2026-10-13 JSTに対話版と非対話版の実API評価が完了しました。各108 POST、677,425 tokensです。両実行とも8Bはoutput_valid23/54、70Bは28/54でした。詳しい結果はローカル`output/cscs/dev54-rerun-report.md`にあります。購入操作・fallbackはありませんが、CSCSの価格や残高は未知です。Unlimited表示は無料保証ではありません。

共有用fixtureは`fixtures/cases-portable.jsonl`です。旧fixtureの絶対PDFパスだけを相対パスにし、54件のclaim/reference/vote/IDは変えていません。元fixtureと過去成果物はローカルに保全し、変更・削除していません。runnerとfixtureのhashが変わるため過去jobの再開は拒否されます。送信不確実なjobのfenceを新jobで回避してはいけません。

## 原因と変更

旧8Bの2件目Aはspan_idに禁止されたtextを追加し厳格schema不合格。raw JSONは完全で、旧runnerのhash一致とコード経路からfinish_reason=stopの条件を通ったことを確認（finish_reasonそのものは旧記録に保存されていない）。251 completion tokensであり、256token上限による打切りの証拠はない。raw分類2もdev gold0と不一致だが、改善コードはgoldを読まない。

v2はAPI usageが既知の全応答をdurable台帳へ加算する。無効出力も消費/時間/失敗ケースに含める。旧stateの1289tokensを改ざんせず、旧実消費19,281を別auditに記録。

既知の形式不合格、length終了、余分text、未知spanなどは評価失敗として数え再試行しない。70Bを含む独立ケースを進める。出力検証を緩めず、失敗予測はerror付きneutral placeholderとなり、採点時にgoldがneutralでも誤答になる。認証/非200、usage不明・不一致・上限超過、誤server model、API error、送信不確実、中断、保存障害は全停止。送信前の独立inflight fenceを保持し自動再開/自動修復しない。

全ケース共通のsystem末尾へ、evidenceはspan_idだけ、text/page/説明/引用は禁止、compact JSONのみという短い再確認を追加。case特例やgold由来ルールなし。native strict json_schema案はschema_candidate()としてmock検証済みだがCSCS対応未知のため送信しない。unsupported時のfallbackも作らない。v2はfinish_reason/raw outputを不合格時にも記録する。

## 範囲とbudget

固定dev54 A27/B27、portable case SHA256 `4e152ed1118149c4ca0fecc5d7b20d7676f43a24b613b8cb465bb5eb0d80a44a`。投票日は2020-09-27と2021-03-07だけで、2024-06-09のholdoutは含みません。非thinking v1.5 8B/70B各54、総上限108POST、各3件(B,A,B)先行。両モデル同一vote_pages/context、temperature0、出力256/request（最大27,648）。全ジョブ2,000,000 token予算、次POST前に公式文脈262,144＋256＝262,400を保守予約。usage knownと上限適合を別検証し、既知usageは不合格でも計上してから停止/続行を決定。サービスの文脈制限/usageが正しい前提の制限で、金額上限ではない。UTF8 bytes/4をhard capにしない。

POST wall deadline60秒/socket45秒、retry/redirect/proxy/fallbackなし。各モデル5-30分を仮置き、108件すべて60秒なら最大約108分のAPI待ち＋ローカル処理。軽い準備約9秒。重みダウンロード/生成サーバーなし。

## パスと保全

- `track_2a/dev/cscs/`: run.sh、候補コード、tests、固定cases fixture、既存pypdf6.1.1＋BSDライセンス同梱vendor。システムpython3を使う（Python3.14で検証）。一切のpip/network installなし。`/tmp`のvenv依存なし。
- `output/cscs/legacy-dev54-v1/`: 本人の停止済み旧ジョブ全6ファイルをhash照合コピー。inflight/state/raw結果をそのまま保持。実行対象にしない。
- `output/cscs/legacy-preparation-v1/`: 旧helper・smoke・準備証跡のhash照合コピー。
- `output/cscs/preparation-v2/`: tests.log、copy-hashes.json、legacy-usage-audit.json、verification.json、scan.json、candidate.patch。
- `output/cscs/dev54-v2/`: 完了済み非対話実行の結果。summary.json、2つのpredictions.jsonl、各raw/usage/検証結果、state、manifestを保存。
- `output/cscs/dev54-rerun-interactive/`: 完了済み対話実行の保全コピー。

結果output/cscsはgitignore。ソースのコミットとprivate repositoryへのpushは結果の公開ではありません。入力PDFは既存repo/booklets内、input/gold/holdoutを変更しない。runtimeはgold/holdoutを読まない。API keyは既存~/.config/hackapertus-ost-cscs/api-keyをそのまま使い、エージェントは読取/移動/コピーしない。directory700/file600は暗号化ではない。キー/headers/error response bodyは記録しない。非秘密パターン検査は既知キー値を取得せず実施。

同じ承認済みコマンドによる再開はdurable完了記録を再送しない。inflight/state.pendingが残ると拒否。削除や新job名で回避しない。途中の保存障害がdisk上で成功に見える場合も独立fenceが阻止。任意rollbackやリモートexactly-once保証ではない。

完了時はsummary.jsonと8b/70b-predictions.jsonlを親へ。停止時はSTOP表示と非秘密state/inflight/最後の結果を返す。キー不要。macro-F1/根拠の評価は別の保存結果採点で行う。

## 検証

非対話化後のCSCS関連56 testsが成功しました。testsでは実socket生成を禁止します。旧失敗応答の厳格不合格＋17992tokens既知確認、無効54件でも70B独立54件続行、全108件消費計上、完了/失敗記録の再送回避、usage/model/budget異常全停止、保存障害fence、wall deadlineを検証。--help/--prepare-only成功、準備54件、キー読取/認証通信0。旧ジョブ保全hashを再照合済み。形式違反の多くはevidenceの文字列配列でした。非対話化による品質改善はありません。

公式API資料: https://docs.cscs.ch/services/inference/api/#llm-inference-api-service
