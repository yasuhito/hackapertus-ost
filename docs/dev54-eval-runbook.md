# dev54の評価runbook

この手順は内部dev54の54件だけを使う。競技holdoutは使わない。productionはv0のまま。新しいモデル評価は高宮さんが候補と規模を承認した場合だけ実行する。2026-10-13のrunbook検証ではAPIを呼ばず、prepare-only、tests、保存済み出力の公式採点だけを使う。

## 0. 範囲と停止条件

- datesは2020-09-27と2021-03-07だけ。`test_no_split_leakage`は実行しない。広いdataset検索や競技holdoutの検査もしない。
- train36件/test18件、label-date-balanced-v2、seed20261016を固定する。source-row A/Bと同一referenceを分割しない。分割は成績から変更しない。
- 候補の改善材料はTRAINだけ。TESTは公式採点の集計を採否確認に使い、個別出力・ログを開かない。内部testは過去に露出済みなので未知汎化の証拠ではない。
- 新規例は架空で、dev54から引用・言い換えしない。54件機械overlapを確認する。機械チェックだけで意味的paraphraseの不存在を証明したとは言わない。
- productionを直接編集しない。候補はsource-only copyでSYSTEMだけ変更し、prompt hashと本番不変を確認する。
- unknown usage、inflight、state.pending、STOP.json、非ゼロexitが出たら停止。retry、fence削除、job名変更による回避をしない。既存jobを新しいcodeで再開しない。
- 高宮さんのcheckpointでSTATUS: SKILL-STOPを書く。採用前に副指標の悪化を報告して承認を待つ。最大5候補、2〜3連続非改善でも停止する。v1/v2の2連続非改善で現在の候補ループは停止中。
- outputはgitignoreのまま。生出力、transcript、APIログ、秘密をstageしない。sudo、force push、公開、競技提出は行わない。

## 1. セットアップ

repo rootへ移動する。ここからの相対パスはroot基準。

### NodeとPi package

Node26.8.1以上、27未満が必要。実評価の検証版は26.10.0。手元に無ければ、公式Node配布物をユーザーディレクトリに展開しPATHを設定する。sudoは不要。

Linux x86_64向けの例。別architectureでは対応する公式配布物を選ぶ。

```sh
mkdir -p "$HOME/.local/opt"
cd "$HOME/.local/opt"
curl -fLO https://nodejs.org/dist/v26.10.0/node-v26.10.0-linux-x64.tar.xz
curl -fLO https://nodejs.org/dist/v26.10.0/SHASUMS256.txt
grep ' node-v26.10.0-linux-x64.tar.xz$' SHASUMS256.txt | sha256sum -c -
tar -xf node-v26.10.0-linux-x64.tar.xz
export PATH="$HOME/.local/opt/node-v26.10.0-linux-x64/bin:$PATH"
# repo rootに戻る
```

既存Nodeが適合すればdownloadは不要。repoのpackage-lockでPi1.1.0、pi-subagents0.19.0を固定する。Node packagesはsetup時だけ取得し、モデル実行時にdownloadしない。

```sh
node --version
npm ci --prefix track_2a/dev/format
export PI_PACKAGE_ROOT="$PWD/track_2a/dev/format/node_modules/@earendil-works/pi-coding-agent"
export PI_SUBAGENTS_ROOT="$PWD/track_2a/dev/format/node_modules/@tintinweb/pi-subagents"
export PYTHONDONTWRITEBYTECODE=1
```

既に承認済みのPi installationがあれば、PI_PACKAGE_ROOTとPI_SUBAGENTS_ROOTをその絶対package pathに設定してnpm ciを省略できる。個人のlogin/auth/configをNodeへ渡さない。PI package pathはcodeの場所だけを指定する。Piのupgradeはinternal AuthStorage APIの互換性再確認が必要なので、この手順で勝手に変更しない。

### PythonとCSCS endpoint

runtimeはPython3.14.7、評価器venvはPython3.13.15で検証した。runtimeは同梱pypdf6.1.1を使う。tests用venvを分ける。

```sh
python3 --version
python3 -m venv output/cscs/runtime-env
output/cscs/runtime-env/bin/python -m pip install pytest
export RUN_PYTHON="$PWD/output/cscs/runtime-env/bin/python"
```

host dev runnerのendpointは `https://api.inference.cscs.ch/v1/chat/completions` に固定されている。CSCS側で非thinking `swiss-ai/Apertus-v1.5-70B` と `swiss-ai/Apertus-v1.5-8B` の利用を有効にしておく。親は70B、実pi-subagent子は8Bで、選択やfallbackはしない。

このhost runnerにBASE_URLを設定してもendpointは切り替わらない。organizer向けsubmitted runtimeのBASE_URL/API_KEY注入とは別である。proxy対応は別途未検証。liveの接続確認コマンドも課金・認証を伴うので本runbookのoffline検証では実行しない。

キーの場所は `~/.config/hackapertus-ost-cscs/api-key`、file modeは600、親directoryは700。必要なキーは利用者が既存の承認済み方法で用意する。このrunbookには中身、表示、コピー、引数や環境変数への展開手順を書かない。agentはキーを読まない。承認済みlive時だけhost Python transportが内部で使い、Node・workspace・ログへ渡さない。prepare-onlyと採点にはキーは不要。

## 2. 評価器venvと公式evaluate.py

setupに必要なpublic downloadと、モデルAPI実行は別である。既存checkout/venvがあれば再取得・再installを省略する。

```sh
python3 -m venv output/cscs/official-env
output/cscs/official-env/bin/python -m pip install \
  rapidfuzz==3.14.6 scikit-learn==1.9.1 numpy==2.5.4 pytest
export EVAL_PYTHON="$PWD/output/cscs/official-env/bin/python"

git clone https://gitlab.com/ifsoftware/hackapertus-starter.git \
  output/cscs/official-evaluator
git -C output/cscs/official-evaluator checkout --detach \
  5e6957729b77a126006049305ad1ef241211a5b4
export OFFICIAL_REPO="$PWD/output/cscs/official-evaluator"
git -C "$OFFICIAL_REPO" rev-parse HEAD
git -C "$OFFICIAL_REPO" status --porcelain -- evaluate.py
```

HEADは指定SHAに一致し、evaluate.pyの変更表示は空でなければならない。grader.pyもこの2条件を検査する。公式evaluate.pyを改変して結果を合わせない。Bの安全足切り.75は公式CLI既定.70とは別の採用gate。

公式label_ofの意味で採点する。valid label/nameを持つneutral fallbackは、内部errorがあっても公式のneutral予測として採点される。fallback件数を別に記録する。Task A evidenceは公式Hit@5で、label正解やpage一致を条件にしない。相対token/time得点は他チームの結果が必要なので、ここでは公式総合最終得点を計算しない。

## 3. baselineまたは候補を準備する

`run_batch.py`は従来output内にあった候補runnerを整理したCLI。既定はprepare-onlyであり、APIを使わない。jobを自動発見・再開しない。コードはtracked sourceだけをarchiveし、承認済み6PDFだけをlinkする。evals、gold、.gitをmodel workspaceへコピーしない。

```sh
export REPO="$PWD"
"$RUN_PYTHON" -B evals/c-system-prompt/run_batch.py \
  --repo "$REPO" --python "$RUN_PYTHON" --count 5 --start-index 1 \
  --prefix "$REPO/output/cscs/new-baseline" --prepare-only
```

候補はSYSTEMに追加するUTF-8 textとmetadataを用意し、gitにcommitしてから評価する。metadataのbaseline_prompt_sha256とcandidate_prompt_sha256が実際のpromptに一致しなければ停止する。以下は既存の不採用v2をofflineで準備する例であり、新たなlive評価を許可する例ではない。

```sh
"$RUN_PYTHON" -B evals/c-system-prompt/check_prompt_overlap.py \
  --added-text evals/c-system-prompt/prompts/v2-added.txt
"$RUN_PYTHON" -B evals/c-system-prompt/run_batch.py \
  --repo "$REPO" --python "$RUN_PYTHON" --count 5 --start-index 1 \
  --prefix "$REPO/output/cscs/new-candidate" \
  --prompt-file evals/c-system-prompt/prompts/v2-added.txt \
  --metadata evals/c-system-prompt/prompts/v2.json --prepare-only
```

全5コピーを最初のAPI呼出し前にprepareする。結果は54件/credential_reads0/remote_calls0でなければならない。指定job/logはまだ作らない。private source workspaceは/tmpに残る。全job/log/provenanceの事前存在チェックに失敗したら名前を変えて既存STOPを回避しない。

### 承認後だけliveに進む

高宮さんが対象候補と54×5等の規模を承認した場合だけ、上のcommandの `--prepare-only` を `--user-run --approval '承認メッセージの参照'` に替える。引数の文字列自体は承認を認証しない。実行者が実際の承認を確認する。

`--start-index N`は反復ordinalで、countはbatchの件数。任意の正整数を使える。explicitなjobが必要ならprefixの代わりに `--jobs PATH1 PATH2 ...` を指定し、countと個数を合わせる。API runの成功後に他の未実行反復へ進む。失敗・中断時は完了済みを再送しない。

新規書込みパスは絶対pathに正規化し、componentの末尾dot/spaceを拒否する。Python executableはvenvのsymlinkをdereferenceしない。これをresolveすると評価器のsite-packagesを失うためである。historical `format-C-r4.` はrenameせず、採点で正確な読取りpathを渡す。

Cの固定capは270POST/6,000,000tokens/job、POST前reservation262,400、output256、request60秒/socket45秒/case300秒。実績は1job約5〜6分、5回約25〜30分、5.34〜5.56百万tokens。これは観測・見積もりで、料金や残高の保証ではない。上限は5jobで最大1350POST/30百万tokens。HTTP retryはない。

各jobは `PREFIX-rN/`。隣接 `-start.txt`、`-end.txt`、`-exit-code.txt`、`-prepare.log`、`-run.log`、`-stderr.log`、`-provenance.json` に記録する。manifest/state/immutable attempts/case records/canonical/summaryはjob内にある。時刻欠測や非ゼロexitを成功に見せない。STOP時は全て保存する。

## 4. 保存済み出力をsplit別に採点する

`analyze_runs.py score`は従来のsplit採点、noise、official rescoreを1つの経路に整理した。自動APIはない。jobのmanifestをstate hashへ結び付け、case recordのhash、known usage、case集合、canonicalとcase predictionの一致を確認してから公式採点する。fenceが残るjobを正常な完了反復として扱わない。

```sh
"$EVAL_PYTHON" -B evals/c-system-prompt/analyze_runs.py score \
  --repo "$REPO" --official-repo "$OFFICIAL_REPO" --python "$EVAL_PYTHON" \
  --jobs output/cscs/format-C-r1 output/cscs/format-C-r2 \
         output/cscs/format-C-r3 output/cscs/format-C-r4. output/cscs/format-C-r5 \
  --part split --destination output/cscs/new-baseline-split
```

新規baselineなら保存した5つの正確なpathに置き換える。候補も同じscore commandで、その5つのjobを渡す。destinationはrepo/output内の新規directoryでなければならない。個別predictions/expected/scored reportはignored directoryに保存するが、stdoutは集計だけ。TEST個別ファイルを開かない。

全文54件の公式再採点なら `--part full` にする。

```sh
"$EVAL_PYTHON" -B evals/c-system-prompt/analyze_runs.py score \
  --repo "$REPO" --official-repo "$OFFICIAL_REPO" --python "$EVAL_PYTHON" \
  --jobs output/cscs/format-C-r1 output/cscs/format-C-r2 \
  --part full --destination output/cscs/new-full-rescore
```

full得点はsplit別採否の代用ではない。1反復ではSD/noiseはnull、2反復以上では `2√2 × SD / √n` をtemporal detectable widthとして記録する。SD0でも真のノイズ0とは保証しない。expected labels/referenceはtracked approved54 fixtureから取り、過去のignored gold fileは不要。

## 5. baselineと候補を比較する

```sh
"$EVAL_PYTHON" -B evals/c-system-prompt/analyze_runs.py compare \
  --repo "$REPO" --official-repo "$OFFICIAL_REPO" --python "$EVAL_PYTHON" \
  --jobs output/cscs/format-C-r1 output/cscs/format-C-r2 \
         output/cscs/format-C-r3 output/cscs/format-C-r4. output/cscs/format-C-r5 \
  --candidate-jobs output/cscs/prompt-C-v2-r1 output/cscs/prompt-C-v2-r2 \
         output/cscs/prompt-C-v2-r3 output/cscs/prompt-C-v2-r4 output/cscs/prompt-C-v2-r5 \
  --part split --destination output/cscs/new-v2-comparison
```

compareは必ずtrain/test両側を採点し、full採否は拒否する。JSONはdestinationのanalysis.json、各armのaggregate.jsonと公式reportsに保存する。重複jobを同一armの独立反復として数えない。

採用条件は両側でQ平均差≥+0.02、かつ差がその側のbaseline noise幅を超えること。Qは `(0.30 F1_A + 0.28 F1_B) / 0.58`。参考としてnoise幅+0.02の厳格解釈も別に出す。各反復のA≥.60/B≥.75も必要。machine adopt=trueだけでproductionへ反映せず、副指標を報告して承認を待つ。

F1_A/B、Hit@5、validity、fallback neutral、gold contradictionからpred entailmentへの件数、tokens、case mean/p95、API wait、command時間を比較する。bootstrapは同じsource groupsと全反復を保持し、seed20261016/20,000 drawsを使う。pool後F1と反復F1平均は非線形なのでCIを別に出す。case bootstrapと生成noiseも別である。

source auditはuser messages/pages/IDs/schema、model/cap/policyを照合する。historical predict.py hash差はSYSTEM-onlyの証明にはならず、当時のprompt/source差分とprovenanceを確認する。今回のCLI修正だけを含む新旧比較では `--allow-cli-only-hash-changes` を明示できる。許可される差はrun_comparison.pyと新CLI testだけで、差をJSONに表示する。これをtools/models/caps変更の許可に使わない。

r4のcommand開始時刻は欠測なのでnull。末尾dotのない隣接ログへ勝手に寄せたり、他回の時間から推定しない。従来の出力だけが必要な採点は数秒〜約1分、20,000 bootstrap込みの5対5比較はこの環境で数十秒程度だった。モデルtoken消費は0。

## 6. APIを使わない通し検証

setup済みの環境で、上のprepare-only、full score、split score、compareを順に実行する。毎回新しい検証destinationを指定する。live flagを付けない。

```sh
"$RUN_PYTHON" -B -m pytest -q -p no:cacheprovider \
  track_2a/dev/format track_2a/dev/cscs -k 'not test_no_split_leakage'
"$EVAL_PYTHON" -B -m pytest -q -p no:cacheprovider evals/c-system-prompt

git diff --check
git diff -- track_2a/src/predict.py
git status --short
```

EVAL_PYTHONの既存venvにpytestがない場合、今回の検証ではpytestを持つRUN_PYTHONのpurelibをPYTHONPATHに設定してEVAL_PYTHONでtestsを実行した。通常はsetupでEVALvenvにもpytestを入れる。Pi package環境変数を忘れるとSDK testsがEOFで失敗するので、最初にexportを確認する。環境設定後の再実行はofflineであり、APIの再試行ではない。

### 本環境での検証結果

2026-10-13に既存Node/Pi/venvを再利用して通した。setup用download/installは再実行していない。保存済みbaseline/v2以外のモデル評価は行っていない。

| 手順 | 結果 |
|---|---|
| baseline prepare-only 5回 | 各54件、keys0/API0、指定job未作成 |
| v2 prepare-only 5回 | prompt hash一致、各54件、keys0/API0 |
| repeat57のdirect prepare-only | 54件、keys0/API0、ordinal57を保存 |
| 新規末尾dot path | prepare前にexit2、directory未作成 |
| 既存2回full rescore | 公式採点と一致 |
| 既存5回split score | baseline train Q.748300/test Q.815517 |
| 5対5v2 compare | gain train+.019188/test-.166092、両判定不採用、r4時間null |
| track_2a tests | 242 pass、保護対象1件deselected |
| eval helper/split/overlap tests | 36 pass |
| production prompt | git diff空、v0 hash不変 |

証跡はignored `output/cscs/runbook-validation/`。初回のvenv executableをresolveする失敗も残した。absolute pathでvenvを保持する修正後にfull/split/compareを再検証した。reviewで指摘されたmanifest/ledger/canonicalの不一致も拒否するtestsを追加した。APIのretryやfence解除はしていない。

## 7. 記録・commit・STOP

結果をdocs/prompt-eval-log.mdに追記する。prompt版、正確なモデル、反復・job・時刻、Q/noise/CI/判定、足切り、副指標と悪化、欠測、usage/fenceの状態を含める。output/cscs/hillclimb-stop.mdに結果・質問・commitを書く。

stage前にstatusを確認し、自分のscript/test/docs/prompt filesだけを明示してstageする。output、reportなど他作業、generated filesはstageしない。通常commit/pushだけを使う。production prompt反映は別の明示承認が必要。

