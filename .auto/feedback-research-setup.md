# フィードバック H1 オフライン準備

PUBLIC60 は既に露出した **開発用** benchmark。独立検証ではない。H1 は承認済み root の汎用 submit-error 修正だけを比較する。v5 SYSTEM、モデル、役割、入力60件×5、出典抽出、組立器、公式採点、上限は不変。v16 の再試行・文言探索はない。新候補の実モデル結果/Q はまだない。

- primary: 300回答の最終 `NO_ACCEPTED_SUBMIT` 数 `format_fallbacks`、小さい方が良い。
- keep: 合計7未満 **かつ** 全5回の canonical60件・ID・既知usage・source/runtime binding、各回 F1A≥.60/F1B≥.75、平均Q≥.8029455012419827、平均HitA≥.30。非ゼロfallbackも測定可能。旧 gain≥.02 / zero-fallback gate は適用しない。
- 全5回の収集後だけ、fallbackの合法neutral出力を含む全件を変更なしの公式graderで採点。通信/usage/保存の不確実性はSTOP、primary/quality unavailable。identity再利用・再開・HTTP retryなし。

## 歴史的 reference（新しい推論ではない）

original `public60-v5-r1` と `public60b-v5-r2..5` の実測5回だけを取り込む。accepted293、fallback7、Q=.8051187036988255、noise=.0021732024568427814、F1A=.7009478538890304、F1B=.9167303284950343、HitA=.30、941 calls / 8950166 tokens。旧v16はFAILEDのまま。

旧protocol、phase、公式結果、canonical/ledger、全5 archived workspaceと元source、runtimeを検証し、旧 `verify_original()` は呼ばない。root比較ではdispatcher変更と固定SHAの承認済みfeedback修正だけを除外し、旧source pinsは書き換えない。reference checkpointは専用exclusive marker。import時間・歴史的case wall・歴史的usageを新推論時間/費用と区別する。

## 準備・検証結果

`bash .auto/measure.sh --feedback-prepare` 成功。exclusive workspace5個/300 contexts、最初の60件は実SDK＋fake providerで180回の役割/schema検査。remote calls=0、credentials読取り=0。旧v5と入力/messages/pages/schema/モデル/上限/sourceの同値性を検証（runnerの承認済みSHA差だけ許可）。gold/expected/dataset/旧analysisはworkspaceにコピーしない。

実行したテスト:

```sh
PI_PACKAGE_ROOT=/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent \
PI_SUBAGENTS_ROOT=/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents \
/tmp/hackapertus-ost-contract/.venv/bin/python -B -Werror::ResourceWarning -m pytest -q -p no:cacheprovider \
.auto/test_feedback_research.py .auto/test_format_failure_repro.py \
track_2a/dev/format track_2a/tests/test_source_spans.py \
--deselect=track_2a/dev/format/test_submission.py::test_saved_33_reproduce_then_normalize_27_reject_6 \
--deselect=track_2a/dev/format/test_wire.py::test_reconstructed_old_http400_declaration_rejected_new_projection_passes
```

**196 passed / 2 deselected**（新controller架空テスト35件を含む）。歴史的raw fixtureテスト2件とcached応答replayは今回の読取り禁止に従い未実行。途中の公式macroテストはcontract環境のsklearn未配置を確認し、既存公式Pythonへ分離。socket mockのSSL継承問題も修正し最終成功。架空例だけで公式macroを検証しPUBLIC再採点はしていない。

`bash -n .auto/measure.sh .auto/checks.sh`、AST解析、変更ファイルの行末空白検査、新controller `verify()` 成功。git禁止のため `git diff --check` は未実行。実モデル・新candidate採点・reference checkpoint実行・init/log/commitは未実施。candidate job/phase/reference markerはまだ存在しない。

## 親が実行する順序

親が新primary `format_fallbacks` を一度だけ初期化する。必須entry point:

```sh
bash .auto/measure.sh --feedback-reference
bash .auto/measure.sh --feedback-execute h1
```

各wrapperは実際のoperator timestampを渡す。referenceをrun_experiment→log_experimentし、承認済みroot修正をreference checkpoint commitで保護してからcandidateを実行する（discardによるroot修正喪失を防ぐ）。candidateも終了後直ちにlog。初期化やlog、git操作はこのオフラインsetupでは行っていない。再prepare不可、既存の凍結generationを使用。チェックは `feedback_reference` / `feedback_candidate` を専用helperへdispatchしround/phase/protocol SHAを検証する。

## 凍結SHA256

- control `output/cscs/public60-feedback-protocol.json`: `9afd74206ae8e035142f20b9c22ef2dd87f8fcf527d406f4b29b61f0ce7b4335`
- helper `.auto/feedback_research.py`: `e022d668c7840c5a12b63d71aa5719b470fb9478d5a34d70185eabded53939db`
- root `track_2a/dev/format/run_comparison.py`: `01dff6b930a546dbe1b0f8651cebe0cec5f4d3987eeecf2bb9309b4ecea799b6`

controlはmeasure/checks/helper/tests、source/runtime/input/workspace、歴史的reference artifactをpin済み。変更後の無断再凍結不可。実AIへの改善効果・未露出問題への一般化は未検証。
