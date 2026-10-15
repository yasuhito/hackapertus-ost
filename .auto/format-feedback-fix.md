# SDK submit フィードバック修正

ユーザー承認の現行 root 修正。`track_2a/dev/format/run_comparison.py` のみ実装変更。
JSON構文解析とsubmit検証を分離。固定 `ValueError('supporting span required')` を `SUPPORTING_SPAN_REQUIRED` に分類する。既知コード以外の例外本文は返さない。
厳密な整数0/2と空ID配列、正確なキー集合だけは解析値をそのままPiへ渡す。既存TypeBoxを通過後、既存assemblerが再拒否し、既存submit-extensionが `{ok:false,error,message}` をtool結果に直列化する。診断は再拒否時だけ加算。メッセージは供給IDの引用と出典判断の再確認を促し、ID捏造や形式だけのラベル変更を禁じる。

`source_spans.py`、`submission.py`、app、SDK/TS、schema、system、モデル、呼出し上限、修復予算は変更なし。文字列/boolラベル、余分/不足キー、非配列、未知/重複ID、重複JSONキー、不正JSONは引き続き拒否する。

## 実行結果

修正前: `.auto/test_format_failure_repro.py::test_missing_support_feedback_reaches_real_sdk_tool_message` は **1 failed**。実際の次回tool本文が `invalid_schema: INVALID_TOOL_JSON` の汎用検証文字列で、JSON結果として読めなかった。
修正後: 同ファイル **7 passed**。strict xfailは残していない。

追加テスト:
- `track_2a/dev/format/test_feedback.py`: 架空例で子と親の次回native payload内の正確なerror/messageを検査。fake providerがその理由を見た場合だけ供給IDを追加し、同じラベルで各1修復後に受理。非修復例は拒否を維持。既存positive無修復テストも成功。
- `.auto/test_format_feedback_replay.py`: PUBLICの19失敗を保存応答だけで現行driverに再生。直接検証とSDK診断はsupport不足72回、重複4回。19件すべて不受理、親3/子2のまま。過去payload SHA一致は主張しない。

最終コマンド:
```sh
PI_PACKAGE_ROOT=/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent \
PI_SUBAGENTS_ROOT=/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents \
/tmp/hackapertus-ost-contract/.venv/bin/python -B -Werror::ResourceWarning -m pytest -q -p no:cacheprovider \
.auto/test_format_failure_repro.py .auto/test_format_feedback_replay.py \
track_2a/dev/format track_2a/tests/test_source_spans.py
```
**162 passed, 2 skipped**。`git diff --check` 成功。
途中の追加テスト誤りも修正した。JS直列化は空白なしのため文字列比較ではなくJSON構造の厳密比較が必要。Piのexecution_startはvalidator前に発生し、通常tool終了イベント購読は親だけなので、execute到達証明にはassembler呼出し数を使用した。

## 過去の整合性と限界

既存 `integrity.json` の3,348ファイルをSHA256で確認し、3,347不変。唯一の変更は承認済み現行 `run_comparison.py`。アーカイブ、過去記録、基準hashは変更していない。追加テストは既存snapshot対象外。
旧診断helperのhistorical replay/probesは変更も再実行もしていない。旧比較はhistorical copiesを使う必要がある。無関係の既存pending notes/scriptsはそのまま。
ネットワーク、実LLM、live評価、再採点、phase再実行なし。fakeの修復成功はfakeだけの因果確認であり、実AIの修復率・判断精度改善は未測定。2 skippedは未配置のhistorical source-only evidence/payloadに依存する既存テストで、その経路は未検証。
