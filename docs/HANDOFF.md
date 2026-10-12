# OST Track 2A 引き継ぎ

## まず守ること

- オーナーは **高宮さん**。返答・相談は日本語で行う。
- **登録、参加申し込み、提出、サインアップ、支払い、API キー取得は、高宮さんの明示的な「はい」があるまで行わない。** 有料推論も例外ではない。
- 本書の読者は **gmktec 上で直接作業する Codex**。作業リポジトリは **`~/Work/hackapertus-ost`**。GitHub は **`yasuhito/hackapertus-ost`（private）**、ブランチは **`master`**、リモートへ push 済み。以下のコマンド・相対パスはすべてこのリポジトリを基準とする。
- `STATUS.md` と `README.md` には古い保存場所や「remote 未設定」の記述が残る。現状の作業場所・リモートについては本書を優先する。private のままで審査員がアクセスできるとは限らないので、提出前にアクセス方法を確認する。公開変更も勝手に行わない。

## 目的・締切・提出物

スイス連邦の公式投票冊子と自然言語の主張を比較し、**文書に基づく NLI（含意／中立／矛盾）**を Apertus で判定する。現実世界の真偽判定や一般 QA ではない。独語・仏語・伊語の全組み合わせ（冊子と主張の言語が異なる場合を含む）を扱い、根拠と効率を測る。

**締切は 2026-10-16 19:00 JST（12:00 CEST）、延長なし。提出は https://hackapertus.ch/online-hack/submissions のみ。Devpost では提出しない。** 1 プロジェクトにつき 1 回、フォームの Track 2A - OST を選択する。提出そのものは必ず高宮さんの許可を得る。

必要物は、実行可能な GitHub リポジトリ（NLI CLI・引用根拠を含む）と **6 ページ以内の PDF 技術レポート**。レポートには設計、PDF 解析・文脈準備、Apertus の利用、評価と結果、token usage・inference time、再現手順、制約を含める。`track_2a/technical_report.md` は下書きであり、提出用 PDF は未完成。

## 重要ルール

- 主モデルは **Apertus v1.5（8B / 70B）**。商用モデルを解法に使わない。一般 Track 2 の説明では開放重みモデルによる開発補助を認めるが、OST の最新 API ガイドはモデル呼び出しを Apertus v1.5 に限定している。補助モデルの使用は慎重に確認し、役割を報告する。
- テンプレートの **`track_2a/` を改名・移動しない**。`src/`、`data/`、`docs/`、`Makefile`、`technical_report.md` を保持する。`data/` は 100 MB 以下。
- clean checkout から **Docker による `make run` が end-to-end で動く**必要がある。ローカルに事前導入した依存や重みに頼らない。OST API ガイドは linux/amd64・GPU なしのクライアント、入力 read-only、出力とキャッシュは書き込み可能な領域、必要なローカル重みはイメージ内、実行時ダウンロードなし、秘密鍵をイメージに入れないことを要求する。
- 提出時、コード・重みは **Apache-2.0**、文書・テキスト等は **CC-BY-4.0**、提出データセットは **CDLA-Permissive-2.0** による公開ライセンスが付与される。全世界・無償・非独占・**撤回不能**。著作権は保持するが、後から提出を消しても許諾は消えない。第三者データの権利・帰属表示は別途確認する。
- 提出者は、成果物が本人・チームの作品で**イベント期間中に作られた**こと、第三者ライセンスが整合すること、機密・営業秘密・権利侵害がないこと、雇用主・大学等の権利主張を確認し公開許諾できることを保証する。高宮さんに確認せず保証や規約同意を代行しない。
- 予測を権威ある政治的助言として提示しない。根拠を追跡可能にする。

## 入出力と公式評価

JSONL は **1 行 1 JSON オブジェクト**。各入力 ID を変更せず、1 件につき 1 応答を出す。順序は任意、成功時は終了コード 0。欠落・不正応答は誤答。混在入力も処理する。

### 入力

- **beginner = B: Reference**：与えられた短い参照文と主張を直接比較する。
- **advanced = A: Document**：冊子 PDF 内から該当する投票案件・根拠を探して主張を判定する。`vote` で冊子内の案件を識別する。
- 公式の各要求は `booklet` または `reference` のいずれか一方。`claim.language` と source の `language` は `de` / `fr` / `it`。

```json
{"id":"B-1","vote":"案件名","reference":{"text":"参照文","language":"de"},"claim":{"text":"主張","language":"fr"}}
{"id":"A-1","vote":"案件名","booklet":{"path":"booklets/example.pdf","language":"it"},"claim":{"text":"主張","language":"de"}}
```

### 出力

```json
{"id":"A-1","label":0,"label_name":"entailment","evidence":[{"page":7,"text":"原文からの逐語引用"}],"metrics":{"input_tokens":8431,"output_tokens":112,"inference_time_ms":1820}}
```

ラベルは **0 = entailment（含意）、1 = neutral（情報不足）、2 = contradiction（矛盾）**。

**最新の公式 Solution API Guide の根拠ルール：**

- A の 0 / 2 には少なくとも 1 件の根拠が必要。PDF の物理ページ番号は **1 始まり**。原文言語の逐語引用またはそのページのテキストを返し、翻訳・言い換えは禁止。
- 1 項目は約 1 ページ（5,000 文字）以内。長すぎる項目は無効。採点対象は**先頭 5 項目だけ**。重要な根拠を先に置く。複数箇所が必要なら別々に列挙する。
- 冒頭要約だけでなく対象案件の詳細節を探す。同じ事実が複数箇所にあるなら各箇所を引用する。PDF 抽出による改行・ハイフンの差は公式照合で許容される。
- neutral の根拠は空配列でよい。**B の根拠は任意・採点なし。返す場合の page は `null`。**

**評価：** 非公開 held-out benchmark の 3 クラス等重み **macro-F1**（beginner / advanced を分けて報告）、根拠の正確性・参照文照合（A はページも一致）、入力／文脈 token 総数、出力 token（reasoning を含め全呼び出しを合算）、ケース wall-clock 時間の **平均 / p95**。DE / FR / IT 別および同言語／cross-lingual 別の成績も見る。token 数は自己申告より**主催者の token-counting proxy の計測が優先**される。

古いスライドは B も含め根拠必須のように読めるが、最新ガイドの B の例外に注意する。現在のローカル scorer は公式 evaluator と同一ではない。

## 現在あるもの

| パス | 内容 |
| --- | --- |
| `track_2a/src/predict.py` | CLI、pypdf による全ページ抽出・キャッシュ、ページマーカー、Apertus 用プロンプト、OpenAI 互換 HTTP クライアント、mock backend、出力検証 |
| `track_2a/src/score.py` | ID による整列、全体／タスク／主張言語／参照言語／同・異言語 macro-F1、厳密な根拠・ページ照合、token 合計、平均・nearest-rank p95 |
| `track_2a/tests/test_pipeline.py` | 16 テスト。PDF 抽出・ローカル HTTP プロトコル試験も含む |
| `track_2a/scripts/` | データ取得、PDF 取得、日付単位の train/dev 準備 |
| `track_2a/data/source.jsonl` | HF の `v1.1.jsonl` 原本（約 12.7 MB） |
| `track_2a/data/*cases.jsonl`, `*gold.jsonl` | 派生入力と正解。推論に gold を渡さない |
| `track_2a/data/dataset_stats.json` | 件数、分割方針、checksum |
| `track_2a/data/results/` | 保存済み mock 評価レポート（予測ファイルは gitignore） |
| `track_2a/docs/architecture.md`, `task_spec.txt`, `dataset_readme.md`, `booklet_manifest.json` | 設計、スライド抽出、データ説明、PDF 来歴 |
| `Dockerfile`, `Makefile`, `track_2a/Makefile` | コンテナと実行・評価ターゲット |
| `docs/rules/` | 公式規則のローカルアーカイブ |

CLI はケースごとに全冊子を文脈へ入れる。**retrieval・圧縮・自動切り詰めは未実装**。mock は主張そのものが参照内にあれば含意、それ以外は中立で、gold は読まない。API 障害、不正 JSON、PDF 不在、不正引用等は `error` 付きのスキーマ上 valid な中立 placeholder を出す。scorer はそれを gold が中立でも誤答とする。mock への暗黙フォールバックはない。

過去の実行では 16 pytest が通り、beginner 331 + advanced 331 ケースを mock で処理して invalid 0、双方 macro-F1 **0.174107**。beginner 根拠一致は **0/214**。これは配線確認であり、Apertus の精度を示さない。

## データと PDF の復元

公開・ungated の https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets を使用。**v1.1.jsonl は 1,488 行、公式 split は train のみ**。test は使用していない。

- ラベル件数：含意 495、中立 498、矛盾 495。
- claim DE/FR/IT：495/497/496、reference DE/FR/IT：455/569/464。
- `booklet_publish_date` の SHA256 による固定の日付グループ分割：**train 1,157 / dev 331**。同じ投票日の全言語を同一側に置く。
- 元データには **gold のページ番号がない**。reference_string が pypdf 抽出に完全一致しないため、現状 advanced の非中立 214 行は根拠評価から除外し、根拠スコアは `null`。捏造しない。
- **冊子 PDF は 60 ファイル、75,379,251 bytes（約 75 MB）。リポジトリに含まれない。** 以前の取得実績があっても、この作業機での存在を前提にしない。

gmktec での初回セットアップと PDF 取得は次のとおり。`booklets/` は `.gitignore` に登録済みで、このリポジトリ直下のローカル保存先となる。取得先は必ず `--output-dir` で明示する。

```sh
cd ~/Work/hackapertus-ost
python3 -m venv .venv
.venv/bin/pip install -r track_2a/requirements.txt
.venv/bin/python track_2a/scripts/download_booklets.py \
  --source track_2a/data/source.jsonl --output-dir booklets
make prepare PYTHON=.venv/bin/python BOOKLET_DIR="$PWD/booklets"
```

取得スクリプトはデータの `booklet_url` 60 個を www.bk.admin.ch から取得し、**URL の SHA256 先頭 16 桁 + `.pdf`** をファイル名にする。`booklets/manifest.json` に URL・path・bytes・checksum を保存する。結果の downloaded が 60/60 か確認する（個別失敗があってもスクリプトは必ずしも異常終了しない）。データ自体も取り直すなら `make download PYTHON=.venv/bin/python BOOKLET_DIR="$PWD/booklets"`（原本 checksum 検証あり）。

**CLI が PDF を見つける方法：** `booklet.path` の絶対パスはそのまま、相対パスは**入力 JSONL の親ディレクトリ基準**で解決する。CLI は `BOOKLET_DIR` を直接読まない。`make prepare` が指定ディレクトリを使い、`dev_advanced_cases.jsonl` 内へローカルの絶対パスを生成する。保存済みケースには以前の環境の絶対パスが残るので、**取得後・移動後は必ず prepare を再実行**する。

Docker では Makefile が入力・出力・PDF をそれぞれコンテナ内の標準マウント先に配置する。ローカル用の絶対パス入り advanced ケースをそのまま使ってもコンテナからは見えない。コンテナ用ケースには入力マウント配下の相対 `booklet.path` を使うか、PDF マウントに対応するパスを生成する必要がある。

## テスト・mock 評価（実モデル・課金なし）

上記 PDF 取得と prepare の後、リポジトリ直下で：

```sh
make test PYTHON=.venv/bin/python
make run-local PYTHON=.venv/bin/python LLM_BACKEND=mock
make dev-eval PYTHON=.venv/bin/python
```

`make test` は一時ディレクトリに小さな PDF を生成するため、取得済み冊子や `BOOKLET_DIR` を使わない。実冊子を使う advanced 評価は、上記 `make prepare ... BOOKLET_DIR="$PWD/booklets"` で生成した `track_2a/data/dev_advanced_cases.jsonl` の `booklet.path` を経由して `~/Work/hackapertus-ost/booklets/` を参照する。`make dev-eval` に `BOOKLET_DIR` を渡すだけではパスは更新されない。

`run-local` の出力は `output/predictions.jsonl`。`dev-eval` は backend を mock に固定して両タスクを実行し、以下を生成する：

- `output/dev_predictions.jsonl`、`output/dev_score.json`
- `output/dev_advanced_predictions.jsonl`、`output/dev_advanced_score.json`

単独採点の正確なコマンド：

```sh
.venv/bin/python track_2a/src/score.py \
  --gold track_2a/data/dev_gold.jsonl \
  --predictions output/dev_predictions.jsonl --output output/dev_score.json
```

Docker smoke test は `make run`（デフォルト mock）。実モデルでの提出経路とは別であり、このまま提出してはいけない。

## モデルアクセス・費用・VRAM

**Public AI は https://api.publicai.co/v1、キーは未取得。実 Apertus 推論も有料 API 呼び出しも未実施。** 登録・支払いの承認なしに取得しない。

コードが現在読む変数は以下（公式契約との違いは次節）：

| 変数 | 既定値・用途 |
| --- | --- |
| `LLM_BACKEND` | CLI の既定は `openai`、Makefile の既定は `mock`。`--backend` で指定可 |
| `LLM_BASE_URL` | `https://api.publicai.co/v1` |
| `LLM_MODEL` または `LLM_NAME` | 優先順は左から。既定 `swiss-ai/apertus-v1.5-8b`、70B は `swiss-ai/apertus-v1.5-70b` |
| `LLM_API_KEY` または `PUBLICAI_API_KEY` | 左が優先。Public AI には必須、local vLLM では任意 |
| `LLM_USER_AGENT` | `HackApertus-OST/1.0 (Track-2A)` |
| `LLM_TIMEOUT` | 180 秒 |
| `LLM_MAX_OUTPUT_TOKENS` | 2048 |

既に起動済みの local vLLM があれば `LLM_BASE_URL=http://localhost:8000/v1` と `LLM_MODEL` にその served Apertus 名を設定する。サーバー起動・重み配置はクライアントイメージの外で行う。Docker 内の localhost はコンテナ自身なので、実際に到達できるホストアドレスが必要。

承認済み・起動済みサーバーを使う dev baseline の例：

```sh
LLM_BASE_URL=http://localhost:8000/v1 \
LLM_MODEL=swiss-ai/apertus-v1.5-8b \
.venv/bin/python track_2a/src/predict.py --backend openai \
  --input track_2a/data/dev_cases.jsonl --output output/apertus8b_dev_predictions.jsonl
```

Public AI の費用目安（100 万 token あたり入力／出力）：**8B $0.10 / $0.20、70B $0.82 / $2.92**。利用前に最新価格を確認する。VRAM の目安は **8B: bf16 約 24 GB、FP8 12–16 GB、4bit 約 8 GB；70B: 4bit でも 48 GB 以上**。文脈長・KV cache・並列数・量子化方式で増えるので、動作保証値ではない。

## 未解決・公式契約との差分

1. **gold page 不在**：PDF の原文 span とページの対応を手作業で検証・付与する必要がある。
2. **Docker 未実行検証**：Dockerfile と Makefile はあるが build/run を検証済みとは言えない。
3. **実 Apertus 未実行**：品質・context limit・モデル名・tokenization・時間・コストは未確認。
4. **最新公式 API 契約の環境変数**は `BASE_URL` / `API_KEY`。審査では proxy URL と team key が注入され、**すべてのリモートモデル呼び出しは BASE_URL 経由**である必要がある。現コードと Makefile は `LLM_*` / `PUBLICAI_API_KEY` しか扱わないので、優先順位を含め対応を実装して Docker でも引き渡す必要がある。開発用公式 endpoint はガイドでは `https://api.inference.cscs.ch/v1` とされるが、その鍵の取得状況は未確認。
5. **根拠の仕様差**：現 CLI は B でも 0/2 の引用を必須として page=1 を返す。公式は B の根拠任意・page=null。現 CLI に 5,000 文字上限・先頭 5 件への最適化はない。ローカル scorer は B も採点し、A も改行等を許容しない完全一致なので、公式 evaluator の代用と断言しない。
6. 現 token 数は endpoint usage があればそれを使い、なければ UTF-8 bytes/4 の切り上げ推定。mock も推定にすぎない。現 latency 集計は valid prediction のみ。公式 proxy の最終数値や失敗例を含む審査集計と同一とは限らない。
7. 現 prepare の生成入力は旧スライドに近い最小形式で、公式例の language フィールド等が省かれている。提出前に最新ガイドの混在ケース・言語フィールド・read-only 入力で契約試験する。

## 次の進め方

1. PDF を復元、prepare、テストと mock 評価で足場を確認。公式 API 変数・B 根拠・A 長さ制限等の契約差を先に解消する。
2. 高宮さん承認済みのアクセスを確保し、**8B / 70B の dev baseline**を両タスクで測る。mock と区別して結果・設定・token・時間を保存する。
3. 全文 baseline と比較し、投票案件単位・ページ／段落単位の **retrieval / compression** で文脈 token を減らす。根拠の原文と元ページへの対応は保つ。
4. **cross-lingual** 検索・推論を改善する。検索用の翻訳等を検討しても、出力根拠は必ず元言語。否定・数値・条件・発言主体を区別し、言語別／同異言語の結果を測る。
5. gold page/span を検証し、公式基準に近い evidence 評価を追加。Docker clean checkout の `make run`、実 endpoint/proxy、混在 A/B を end-to-end 検証する。
6. **6 ページ以内の PDF レポート**を完成させ、ライセンス・期間内制作・雇用主等の権利・審査アクセスを高宮さんに確認する。
7. 高宮さんの明示許可後のみ、締切前に公式サイトで 1 回提出する。

## 規則アーカイブの読み方

`docs/rules/` は **2026-10-12 の公開・未認証スナップショット**。登録・フォーム送信はしていない。`INDEX.md` が取得元とローカルファイルの索引、`SHA256SUMS` と各 manifest が来歴確認用。HTML/PDF 原本、Markdown 全文、Notion API 応答も保存してある。

優先して読むファイル：

- `docs/rules/notion/Track-2A-OST-3deb4fec.md`：目的、言語、評価。
- `docs/rules/notion/solution-api-guide-ef5b4fec.md`：最新の JSONL・根拠・モデル・proxy・Docker 契約。
- `docs/rules/attachments/28ede48885-HackApertusTrack2AMNLIOverSwissVotingBooklets.pdf` と `1a1d81e7a4-hackapertus-qa.pdf`（同ディレクトリ）：OST 説明・Q&A。
- `docs/rules/notion/How-to-Submit-a-Project-c91b4fec.md`：締切・提出経路。
- `docs/rules/web/hackapertus-submission-form-7.md`：OST 提出項目・6 ページ PDF。
- `docs/rules/web/hackapertus-terms-and-conditions.md`：特に第 6 節のライセンスと保証。
- `docs/rules/repositories/`：テンプレート・OST starter・HF データカード。

**`docs/rules/NOT_FETCHED.md`** には、任意の social-preview 画像 10 件（署名 URL 取得不能・公開 endpoint HTTP 400）と、active collection にない古い Notion database 参照 17 件（空応答・HTTP 403、題名不明）を記録している。要求されたアクセス可能な規則ページと発見された PDF は保存済みだが、未取得項目を「読んだ」と扱わない。署名 URL は期限切れになるため、資料はまず保存済みローカルファイルを読む。
