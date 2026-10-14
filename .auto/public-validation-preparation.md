# 公開追加検証データの準備 v2

## 現在の状態: fixed v2 完成

データ準備だけで完了。元の30行、60 A/Bケース、除外条件、seed、順位、instruction、official scorerは変更していません。モデル呼び出し、評価、採点、experiments、git操作、採用なし。

完成束: `output/validation/v16-public-v2-completion/`。cases、expected、prepared-contexts、context-auditは各60件、source-metadataは30件、検証済みPDFは21件です。casesはinput-only。goldは別のexpectedファイルで、この束全体を将来のmodel workspaceへコピーしてはいけません。モデルへ渡すのはcase inputだけです。レポートにはraw source、claim、reference、gold、context本文を表示していません。

`--resume-preparation` は旧freezeファイルSHAとselection SHAを固定照合し、公開source SHA、公式metadata、split SHA、全54 input対応、source indices、group digests、recipe、seed、順位入力・順位・全manifest選択情報を現行コードで完全再計算して一致検査します。不一致なら転送前に停止。旧freezeにはpreparation code SHAが記録されていなかったため、その歴史的コードSHA一致は主張しません。完成manifestにはこの欠落を明記し、現行ranking/recipe関数SHAと全準備/contextコードSHA、original freezeへの参照を記録しました。選択を更新する入口ではありません。

親の同一公式URL curl診断はHTTP200、2,424,583 bytes、pypdf 6.1.1で32ページ、SHA `9df0813f2728c9de6dd29b132acf11d3e13bf7a011b7e6475a4c8b5155c889c8`。urllibでの過去3不完全取得に対し、別transportで完全取得できた証拠です。低レベル原因を断定しません。その診断PDFとHTTP証拠のあるv2 PDF 1件を読み取り専用で再利用し、残り19選択URLだけをdirect curl HTTP/1.1で取得しました。旧v2の2件はhash/parserは正常でもHTTP metadataが欠けるため、新しい束では同じURLを完全取得しました。旧3 canonical PDFは一切変更なし。各転送は120秒、30MiB、HTTPS政府domain限定、redirect禁止、同一URL最大3回。HTTP status、encoding/range、Content-Length、全bytes SHA、EOF、pinned parserを検証してからatomic/exclusive保存。新失敗転送は別名receipts/bytesを保持する実装です。実完了では新失敗なし。

固定SHA:

- source: `87ee4afd9c0ee8861106c50f05884481402ca668aecf927df68fc52d915b02fd`
- split: `963cb7cfaab01cb8b178cf0ce1d5207e464ad0a81b5868370186aa161d0be3d9`
- original selection freeze: `acf1805ca02358e8913ead392e587247b2b0f36d7300e8114e790307807e8007`
- original freeze file: `73a1facf98d42b6334b2547c64e004e0ece355b78f1fe27daf4410073e11df92`
- completion manifest file: `b08743451bdbb67476ce2fc8641c34824fe1ae1d1fa10a7c2d14d512d4036dc4`
- completion manifest freeze: `530708f506490841e922c6ce99c88d7f5cbc5f4902e14c9f599317354ec1dfbf`

実行検証（Python `/tmp/hackapertus-ost-contract/.venv/bin/python -B`）:

- 変更前の架空テスト: 新curl/resume入口未実装による2 errorsを再現。
- `-W error::ResourceWarning -m unittest discover -s .auto -p test_prepare_public_validation.py -q`: 最終20 tests成功。curl full bytes/headers、失敗、size、redirect、長さ、no overwrite、freeze不一致、recipe/seed/ranking fields/split mapping変更拒否、既存HTTPError closeを含む。追加の架空resumeテストは最初90行だったため固定1488行contractで失敗し、架空1488行へ修正して成功。
- `.auto/prepare_public_validation.py --resume-preparation`: complete、60 cases、stderr空。再実行はcomplete-read-onlyで全artifact SHA照合のみ。
- offline再検証: Backend.completeを禁止し、全60 `predict.context(..., 'vote_pages')`、source offsets、candidate schema、prepared messages/audit SHAを完全再現。全21 PDFのbytes/hash/parser/pagesを再照合。
- v1、旧v2、指定diagnostic-v3の全40ファイルを実行前後SHA比較して不変。証拠はignored `output/validation/preparation-completion-audit/`。

変更は準備script、架空test、このreportのみ。production/evaluator/frozen v16は変更なし。非公開競技データ、sibling、historical TEST output、`.auto/log`、`.auto/prompt`は読みません。モデル推論・評価は未実行で対象外です。公開追加問題であり、秘密の独立未見benchmarkとは主張しません。以下は旧partialの履歴です。

## 旧 partial 実行時の状態（以下は履歴）

**partial。データ準備だけを実行し、PDF の完全取得が3回とも失敗したため停止しました。モデル呼び出し、評価、採点、experiments/init/log、commit、採用はしていません。** 選択の差し替え、再シード、PDF修復、OCR、別URLへの変更もありません。v1の23保存ファイルは実行前後の全SHA比較でバイト不変です。

変更ファイルは `.auto/prepare_public_validation.py`、`.auto/test_prepare_public_validation.py`、この文書だけです。元source、production、evals、候補SYSTEM v16には変更なし。非公開競技データ、original siblings、個別historical TEST出力、`.auto/log`、`.auto/prompt` は読みませんでした。使用済みfixtureはinputの対応検査を機械処理のみで行い、goldや出力の分析・表示はしていません。

## v2の選択条件と固定結果

公式公開全1,488行を対象にします。2024-06-09を含め、四日付を禁止する公式根拠は確認されていません。ユーザーの最新条件に従い、四日付や冊子全体ではなく、現在使用している54 IDに対応する27 source行と、その正規化主張+言語、正規化参照+言語だけを除外します。

出典はv1と同じ公式 `OSTswiss/MNLIoverSwissVotingBooklets/v1.1.jsonl`。revision `fc2b27600310778da6bbf445651ddbca22d86269`、source SHA `87ee4afd9c0ee8861106c50f05884481402ca668aecf927df68fc52d915b02fd`。公開publisher LFS metadata SHAとの一致を今回も検証しました。seedは `ost-v16-public-validation-20261014-v1` のまま。入力のみの順位で参照グループの代表を先に決め、その後0/1/2を各10行round-robinで選びます。PDF可用性・性能・日付・言語でのフィルタはありません。

- split train36 + test18 = unique54、27 A/Bペア、範囲と全54入力対応を検証。
- 除外union65行、非排他的ヒット: 使用済み行27、主張41、参照62。ブロックグループ主張27、参照24。
- 適格1,423行、参照代表641。代表ラベル数0:223、1:149、2:269。
- 固定30行、ラベル各10行。A/B計60件、各ラベル20件を予定。参照重複0。使用済み27行との個別行・主張・参照重複すべて0。
- 使用済み27行との日付重複0行、冊子重複0行・0冊子。許可した結果たまたま0であり、冊子held-outを選択条件にはしていません。
- 以前除外した四日付全331行に対しては日付重複5行、冊子重複5行・3冊子。新文書held-out一般化を主張できません。
- 主張言語 de10/fr10/it10、参照言語 de10/fr9/it11、異言語20/30。PDF URLは21件。
- 日付: 2020-02-09:2、2021-06-13:1、2021-09-26:1、2022-02-13:2、2022-05-15:1、2022-09-25:2、2023-06-18:4、2024-03-03:4、2024-06-09:1、2024-09-22:1、2024-11-24:6、2025-11-30:3、2026-03-08:2。
- PDF/contextより前の選択freeze SHA: `acf1805ca02358e8913ead392e587247b2b0f36d7300e8114e790307807e8007`。
- `selection-freeze.json`ファイルSHA: `73a1facf98d42b6334b2547c64e004e0ece355b78f1fe27daf4410073e11df92`。完成manifest SHAはありません。

## PDF障害の診断と修正

同じ2021-06-13ドイツ語URLを同じ従来要求ヘッダで診断取得しました。HTTP 200、Content-Length 1,563,498、Range/Encodingなし、redirectなし。単発 `read(30MiB+1)` は1,376,549バイトで戻り、`PdfStreamError`。v1の1,376,548バイトとは長さ・SHAが異なり、どちらもEOF欠落です。架空の宣言長999・実体15バイト応答でも旧コードは不完全PDFを書き込みました。

要求ヘッダを変えず読み取りだけ64KiBループに変えた同一URLの次の診断取得は1,563,498バイト、SHA `521e39af06717d2adeb2f787a08b533164921a952c59b7ad3e5b114fcadec744`、pypdf 6.1.1で144ページ解析成功。現行 `predict.context(..., 'vote_pages')` も診断用公開入力で成功、ページ10/11/144、候補4件。これはv2選択の差し替えではありません。

再現したコード不具合は、単発readの短い返却を完全取得と見なし、宣言長・EOF・parserを検証せず保存したことです。低レベルで短く返る原因までは断定しません。修正はbounded read loop、最大30MiB、identity encoding、HTTP状態/Range/長さ/EOF/pinned parser検証、HTTPS政府domainとredirect検証、同一URLのtransport/不完全bodyのみ最大3回のbounded retryです。検証後のみatomic/exclusive作成し、失敗実体とHTTP記録は別名に保持。v1再利用は旧receipt SHAとparserを検証した正常PDFだけです。

v2実行では次のURLが3回ともContent-Length未満で終了しました。真に不完全な応答の原因は未解決のため、追加取得せず停止しました。

`https://www.bk.admin.ch/dam/de/sd-web/aSmZ7rOvZDrG/2020-02-09_erlaeuterungen_des_bundesrates.pdf`

宣言長2,424,583バイト、実体は順に2,353,165 / 2,201,365 / 1,368,357バイト。HTTPはいずれも200、失敗phaseは `pdf-download`、型は `IncompletePDF`。HTTP metadata・失敗bytes・SHAは個別receiptに保持。検証済みcanonical PDFは3件。60件context loop、coverage集計、完成manifestは未実行です。

## 保存物と検証

すべての入力・gold・PDF・partialはignored `output/` 配下です。

- `output/validation/v16-public-v2/`: official metadata、選択freeze（ID/index/split/source SHAとgroup fingerprints、raw textなし）、3検証済みPDFとreceipt、同一URL3失敗bytes/receipt、failure.json。
- `output/validation/pdf-diagnostic-v2/`: v1前SHA一覧、架空旧パターン、同一URLの旧read/loop診断PDFとHTTP receipts、診断context receipt。
- v2未作成: cases.jsonl、expected.jsonl、source-metadata.jsonl、prepared-contexts.jsonl、context-audit.jsonl、booklets/manifest.json、selection-manifest.json。入力束は未完成です。実装はcasesをinput-only、goldを別expectedにし、非neutralのみ元公式referenceを保持します。
- 完成後のみ全artifact/code/PDF/input/schema/context SHAとSYSTEM SHA、ページ/候補ID、後選択exact-reference coverageをmanifestに記録します。停止後にHTTP error非retry、失敗応答のclose、事前code SHA記録を補強。ResourceWarningをエラーにする条件でも17単体テスト成功。既存partialは更新・再実行していません。

実行済みチェック（Pythonは `/tmp/hackapertus-ost-contract/.venv/bin/python -B`）:

- `-m unittest discover -s .auto -p test_prepare_public_validation.py -v`: 最終17テスト成功。架空PDF/HTTP、長さ/EOF/header/size/redirect、同一URLretry上限、HTTP error非retry、immutable、54対応、日付許可、跨日重複排除、代表先行、gold分離、context失敗非置換を検証。
- `-m pytest -q -p no:cacheprovider track_2a/tests/test_source_spans.py track_2a/tests/test_span_pipeline.py -k 'not pipeline and not selection'`: 26成功、6 deselected。
- `-m pytest -q -p no:cacheprovider track_2a/tests/test_span_pipeline.py::test_system_matches_submit_contract_without_duplicate_text_output`: 1成功。
- 両準備Pythonの `ast.parse`: 成功。v1全23ファイルSHA比較: 不変。partial再実行拒否: 成功。診断済み実PDF context: 成功。
- `.auto/prepare_public_validation.py` 実行: 上記PDF取得blockerで終了1。再選択・追加取得なし。
- `unittest discover -s track_2a/tests` はpytest形式のため0件で終了5。pytestで上記source-only対象を改めて実行しました。
- `-m ruff check ...`: ruff未導入で実行不可。依存追加はしていません。

これは「このプロンプト改善で使っていない追加の公開問題」の準備です。秘密の独立未見データとは主張しません。歴史的mock train1,157行のexposureは監査していません。評価には改めてユーザー承認が必要です。

---

# v1 履歴（保存物は変更なし）

## 状態

**準備は未完了、PDF/context エラーで停止。評価、モデル呼び出し、採点、採用は一切していません。** 再取得、行の差し替え、再シード、既存 partial の上書きはしていません。

実行: `python -B .auto/prepare_public_validation.py`。終了コード 1。公開 PDF 19件を取得後、現在の v5 `predict.context(..., 'vote_pages')` で `PdfStreamError`、stderr は `EOF marker not found`。HTTP エラーではなく、PDF 解析段階の失敗です。実装は `%PDF` とサイズ、HTTPS `www.bk.admin.ch` およびリダイレクト先を確認しますが、それだけでは解析可能性を保証しません。

## 固定済みの選択と出典

- 公式公開 `OSTswiss/MNLIoverSwissVotingBooklets/v1.1.jsonl`、1,488行。
- revision: `fc2b27600310778da6bbf445651ddbca22d86269`。
- [指定 revision の公開 LFS メタデータ](https://huggingface.co/api/datasets/OSTswiss/MNLIoverSwissVotingBooklets/tree/fc2b27600310778da6bbf445651ddbca22d86269) の SHA とローカル source の SHA が一致: `87ee4afd9c0ee8861106c50f05884481402ca668aecf927df68fc52d915b02fd`。元 source は変更なし。
- 固定 seed: `ost-v16-public-validation-20261014-v1`。
- 除外日: 2020-09-27、2021-03-07、2024-03-03、2024-06-09。最後の日は競技禁止日と確定したからではなく、保守的な歴史的 dev 除外です。
- 日付該当331行。冊子、正規化参照と言語、正規化主張と言語の重なりも除外し、除外 union 340行、適格1,148行。非排他的除外ヒット: 日付331、冊子331、参照331、主張340。
- ブロック済みグループ: 冊子12、参照157、主張263。適格参照グループ508。ラベルを見る前の参照代表を順位で固定し、その代表のラベル分布は 0:179、1:118、2:211。
- 選択30行、各ラベル10行、A/B同一行ペアの計画60件、各ラベル20件。選択参照重複0、歴史的冊子・参照・主張グループ重複すべて0。
- **選択のみの freeze SHA**: `720257b0567aa8af2638b56b9047ccf18a00198a68f6107cb0936fbcf15a5178`。完成 manifest の freeze SHA は未作成。

元行の分布:

- 参照言語 de:10、fr:9、it:11。主張言語 de:12、fr:8、it:10。異言語ペア19/30。
- 日付: 2020-02-09:2、2021-06-13:2、2021-09-26:1、2022-02-13:3、2022-05-15:1、2022-09-25:3、2023-06-18:6、2024-09-22:1、2024-11-24:6、2025-11-30:3、2026-03-08:2。

## 障害と保存物

取得済み19件中、次の6 URL の保存バイト列には末尾2,048バイト内の `%%EOF` がありません。解析失敗の原因候補です。これはネットワーク切断と断定できず、失敗した個別 case の記録も現実行では保存されていません。**原因特定や再試行をせず停止しています。** URL、バイト数、全 PDF SHA は ignored `booklets/manifest.json` にあります。

- https://www.bk.admin.ch/dam/de/sd-web/UxUxfYD5ma0h/2021-06-13_erlaeuterungen_des_bundesrates.pdf
- https://www.bk.admin.ch/dam/de/sd-web/aSmZ7rOvZDrG/2020-02-09_erlaeuterungen_des_bundesrates.pdf
- https://www.bk.admin.ch/dam/de/sd-web/iWYLyEPfLvhn/2024-09-22_erlaeuterungen_des_bundesrates.pdf
- https://www.bk.admin.ch/dam/it/sd-web/Lv5UWt6X1iUj/2023-06-18_spiegazioni_del_consigliofederale.pdf
- https://www.bk.admin.ch/dam/it/sd-web/SwAIDvDocLte/2022-09-25_spiegazioni_del_consigliofederale.pdf
- https://www.bk.admin.ch/dam/it/sd-web/aSmZ7rOvZDrG/2020-02-09_spiegazioni_del_consigliofederale.pdf

`output/validation/v16-public-v1/` は既存 `.gitignore` の `output/` により全体が ignored。保存済み: `official-source-metadata.json`、`selection-freeze.json`、`booklets/manifest.json`、19 PDF、`failure.json`。未作成: 完成 `selection-manifest.json`、`cases.jsonl`、`expected.jsonl`、`source-metadata.jsonl`、`prepared-contexts.jsonl`、`context-audit.jsonl`。完成した60件の入力束はありません。

実装では完成 manifest は排他的作成、完成束の再実行は SHA 確認のみ、partial 再実行は拒否します。予定ケースには gold を含めず、gold は別ファイルで、今後もモデル workspace の外に置く必要があります。Task A gold reference は元行の公式参照そのまま、ページや引用を発明しません。

## テストと限界

- `python -B -m unittest discover -s .auto -p test_prepare_public_validation.py -v`: 架空データ10テスト成功。固定順位、四日付と跨日グループ除外、参照代表先行、ペア/gold 分離、ラベル検証、不足停止、SHA不一致、immutable/partial拒否、不正URL/PDF、source-only候補と context エラー伝播を確認。
- 両 Python ファイルの `ast.parse`: 成功。
- 実データ準備: 上記 PDF 解析エラーで失敗。60件の context、完成 manifest、引用 coverage 診断は未検証。

これは「このプロンプト改善で使っていない追加の公開検証」であり、秘密の未見ベンチマークではありません。歴史的 train 1,157行は mock training に使われています。公式非公開競技データ、個別 historical TEST 出力、`.auto/log.jsonl`、`.auto/prompt.md` は開いていません。モデル/API inference、experiments/init/log、git commit/revert/adoption は実行していません。評価前にはユーザーへ規模と条件を説明する必要があります。
