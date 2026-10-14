# PUBLIC60 継続準備

所有者は「同じ60問で v5 をあと4回、完了した1回も使い、v16 を5回、全結果を公式採点して点数と形式失敗を比較する」に同意した。v5 と v16 の両方で decoder fallback だけでは収集を止めない。問題、失敗出力、反復を差し替えない。HTTP、使用量不明、時間制限、job 内 STOP は従来どおり停止し、再送も再開もしない。

旧 `.auto/public_validation.py` を変更せず、同ファイル由来の一回限りの専用コピー `.auto/public_validation_continue.py` を追加した。measure/checks は新しい分岐だけを追加した。旧分岐は旧 protocol と不一致になり停止するため、旧実行に戻さない。

## 固定と既存反復

旧 protocol SHA256:
`719f36396fb3807862dd8403425462a47e0a1cb7de1bfa794404e405ce22e2e0`

旧 helper SHA256:
`eeeceea62e469fa0b55fe42dd6c74d51f07d22c1858173f0681111cd768bc64d`

旧 protocol、全旧 workspace、最初の job、旧 phase と STOP を含む1303ファイルの事前チェックポイント SHA256:
`7c67d1ccf25c10b81eff0e4de118d9b3e60ad0fc495b552a8f1e64cf503af375`

新 protocol `output/cscs/public60-continue-v16-protocol.json` SHA256:
`944b3f98519bb6e5592317f86a623cc824fa8a69cfce28befbf4da0f77b8f7e2`

完了済み `public60-v5-r1` は60行、accepted 59、fallback 1、187 requests、既知使用量1,782,477 tokens のまま読み取り専用で保持する。旧 phase STOP も保持する。manifest、全成果物、ledger、canonical と record prediction の一致、ID 順、使用量、モデルと source/schema binding、SDK、元ソースを検証する。新 v5 は booklet の workspace パスだけ正規化して旧 r1 と全 manifest 契約と入力の等価性を検証する。不完全 job や job 内 fence を import しない。

新規は `public60b-v5-r2..5` の4 job、`public60b-v16-r1..5` の5 job だけ。入力専用 workspace は `output/cscs/public60b-workspaces`。全9 manifest と source/runtime、helper、テスト、dispatcher を新 protocol に固定した。各 variant の実 SDK mock は60件、180 fictional calls、remote calls 0、credential reads 0。gold は workspace にコピーしない。正解、失敗ラベル、応答本文を使った選択や調整をしない。

## 採点と条件

各 phase の全5反復の完了確認後に、既存の無変更公式 grader に全60 canonical 行を直接渡す。合法な app fallback は普通の予測としてそのまま採点する。gold に基づく誤答化、行の除外、人工ペナルティ、再ラベルはしない。expected は既存 completion bundle にだけあり、grader 側で使用する。

v5 は初回を含む実測5回から Q と SD、noise を求める。Q は `(0.30 F1A + 0.28 F1B) / 0.58`、noise は `2 sqrt(2) SD / sqrt(5)`。完了と採点前には primary metric を出さない。baseline gain 0 は全5回の実測採点後だけ出す。

v16 の採用条件は変更しない。5回すべて fallback 0、各回 F1A >= .60 と F1B >= .75、平均 gain >= .02 かつ新 noise より大、平均 evidence HitA は baseline 以上。候補不合格は全5回を採点した後の `--check` で checks_failed とし、早い fallback では収集を止めない。accepted と fallback は各反復と全体で別々に報告する。

各 job は300 POST、78.72M declared token budget、parent70B/child8B、温度0、parent3/child2、repair1、出力256、request60秒/socket45秒/case300秒、240000 byte request guard のまま。残り v5 4回に新90分、続く v16 5回に別の新90分を設ける。baseline の合計使用量は旧 r1 を一度だけ含める。新コマンド wall time と全反復 case wall time を区別し、phase に旧反復 case wall time も保存する。

## 検証と準備状況

`PI_PACKAGE_ROOT` と `PI_SUBAGENTS_ROOT` を指定して、`python -B -W error::ResourceWarning -m pytest -q .auto/test_public_validation_continue.py .auto/test_public_validation.py .auto/test_prepare_public_validation.py track_2a/dev/format` を実行し、204 passed、2 skipped。shell syntax、Python AST、diff whitespace も確認する。SDK root 未指定の最初の試行は SDK EOF で失敗し、既存の固定 runtime root を指定した試行で通った。テストを弱めていない。

実際の `bash .auto/measure.sh --public-continue-prepare` は外側の400秒制限に達した。9個の prepared.json と両 variant の payload-audit.json は完成していた。入力専用コピーの root/source/booklet と SDK capture 完了を再検証し、同じ prepare_only 関数で固定処理だけ完了した。workspace の再生成、SDK capture の再実行、job の生成、grader、ライブ transport は一切行っていない。新 protocol を再検証済み。旧1303ファイルは事前 SHA と一致する。

ライブ推論、公式実測採点、experiment 初期化、experiment log、commit はまだ行っていない。実測の品質は未確認。2件の既存 skip はテスト出力どおり未検証。

## 親が実行するコマンド

準備は完了済みなので prepare を繰り返さない。

1. `bash .auto/measure.sh --public-continue-baseline`
2. 完了後 `bash .auto/checks.sh`
3. baseline 計測後 `bash .auto/measure.sh --public-continue-candidate v16`
4. 完了後 `bash .auto/checks.sh`

親の run_experiment と log_experiment を使う。新 control と phase binding を使い、旧 r1 は再実行しない。報告は集計値と hash に限定する。
