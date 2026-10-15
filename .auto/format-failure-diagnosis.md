# PUBLIC60 診断結果、修正なし

**確認済み:** JSON構文エラーではありません。1,884応答の引数はすべて厳密JSONとして合法で、終了理由はすべて `stop`、256トークン上限到達はゼロです。

19失敗のsubmit検証76回の内訳:
- 72回: 整数ラベルが非neutralなのにID配列が空。`source_spans.py:79-80` の `restore` が `ValueError("supporting span required")` を送出。
- 4回: `submission.py:73-74` の `DUPLICATE_ID`。

17件は前者を4回、2件は子の重複IDを2回、その後親の前者を2回繰り返します。全件が親3応答・子2応答を消費。同一役割の再試行38組中36組は生引数も解析値も同一、残る2組も同じ違反です。

**診断バグ:** `run_comparison.py:367-377` はJSON解析とassembler検証を同じexceptで扱い、小文字を含む検証例外を `INVALID_TOOL_JSON` に置換します。架空例 `{"label":0,"candidate_ids":[]}` でも実SDK経路で再現します。文字列ラベルの問題ではなく、ラベルと証拠の契約違反です。出典一致・復元後canonical検証のエラーは今回ありません。

**SDK変異説は否定:** 全19件の完全キャッシュ再生で、直接assembler入力とSDK転送前入力のハッシュ・例外・順序が一致。拒否は転送前です。成功対照には同じ下位例外56回、重複13回もあり、診断発生だけでは失敗を説明しません。

再試行要求38回すべてに汎用schemaマーカー、36回に誤ったJSONコードがあり、具体的な下位メッセージはゼロ。フィードバック不足と違反反復は確認済みですが、改善の因果効果は未検証です。意味判断の正誤は評価していません。

検証コマンド（`PY=/tmp/hackapertus-ost-contract/.venv/bin/python`）:
```
$PY -B .auto/diagnose_format_failures.py --probes --probe-artifact validation-probes-final.json
$PY -B -m pytest -q -p no:cacheprovider .auto/test_format_failure_repro.py
$PY -B -m pytest -q -p no:cacheprovider --runxfail .auto/test_format_failure_repro.py::test_red_signal_preserve_real_validation_reason_at_sdk_seam
```
結果: 診断成功、5 passed / 2 strict xfailed。最後は意図どおり1 failed。成果物はexclusive作成のため再実行時は新しい名前を指定してください。

`output/diagnostics/public60-format/validation-probes-final.json` に匿名化分類・役割別系列・要求ハッシュを保存。初期integrityとの比較で保護3,348ファイルのSHA256不変。既存成果物を保持。ネットワーク・モデル・評価呼出しなし。

次の最小提案: 検証規則を維持し、JSON解析失敗と下位検証失敗を分離、固定の具体的エラーコードと一般的な修復案内を返す。今回は適用していません。
