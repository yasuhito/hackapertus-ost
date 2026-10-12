# 引き継ぎ：Hack Apertus Track 2A — OST

この文書だけで作業を再開できるよう、目的・公式契約・現状・未対応事項をまとめる。規則アーカイブは **2026-10-12 取得時点**。既存の `STATUS.md` とルート `README.md` にある「ローカル git のみ／remote なし」は古い記述であり、現在は **master を remote に push 済み**。

## 1. オーナーと作業上の制約（最優先）

- オーナーは **高宮さん**。返答・相談は **日本語**。
- コーディングは **pi を使い、高宮さんのサブスクリプションだけで行う**。pi のために API クレジットを使わない。
- **明示的な「yes／承認」なしに登録、sign-up、提出、支払いをしない**。API キー取得、無料クレジット申請、公開設定変更なども勝手に進めない。
- 推論用 Apertus API と、開発エージェント pi の利用料金は別物。推論 API の利用・課金も事前に確認する。キーや `.env` は git・Docker image に入れない。
- private repo への push は大会への提出ではない。規約同意・権利保証・公開・提出の判断は高宮さんに確認する。

## 2. 目的・期限・提出先

スイス連邦の公式投票冊子（Abstimmungsbüchlein）と自然言語の claim の関係を、Apertus により **entailment / neutral / contradiction** に分類し、原文根拠を返す多言語 NLI アプリを作る。外部世界での真偽判定や一般 QA ではなく、**与えられた文書に基づく推論**である。DE・FR・IT の全組合せ（冊子と claim が異言語の場合を含む）に対応し、全文入力と検索・圧縮入力の品質／効率を比較する。

- **締切：2026-10-16 19:00 JST（同日 12:00 CEST）。延長なし。**
- **提出は https://hackapertus.ch/online-hack/submissions のみ。Devpost では提出しない。**
- Track 2A — OST を選び、必要項目をすべて埋める。1 project につき1提出。
- 成果物：再現可能な GitHub repo（entailment CLI・引用根拠を含む）と **6ページ以内の技術報告 PDF**（token usage・inference time を含む）。`track_2a/technical_report.md` は元原稿であり、PDF 完成品ではない。

## 3. 公式仕様：現在の実装と混同しない

### JSONL 入出力

Docker entrypoint は次を受け付ける：

```sh
<entrypoint> --input /data/cases.jsonl --output /output/predictions.jsonl
```

1行につき完全な JSON object。入力 ID ごとに1応答を返し（順序不問）、成功時 exit code 0。欠落・不正応答は誤答。各 request は `booklet` と `reference` の **どちらか一方だけ**を持ち、混在ファイルにも対応する。

- **A / advanced / Document**：PDF と `vote`（文書の言語での投票案名）から関連箇所を探して分類する。まず全文 baseline を作る。
- **B / beginner / Reference**：渡された reference passage と claim を直接比較する。
- `id` は一意な文字列で、そのまま返す。`claim.language` と source の `language` は `de` / `fr` / `it`。PDF path は `/data` 基準（例：`booklets/example.pdf`）。

公式形式の入力例（内容は形式説明用）：

```json
{"id":"case-A","booklet":{"path":"booklets/example.pdf","language":"it"},"vote":"Nome della proposta","claim":{"text":"Der Bundesrat unterstützt die Vorlage.","language":"de"}}
{"id":"case-B","reference":{"text":"Le Conseil fédéral recommande de rejeter l’initiative.","language":"fr"},"vote":"Nom de la proposition","claim":{"text":"Il Consiglio federale raccomanda di accettare l’iniziativa.","language":"it"}}
```

応答の形（数値・引用は形式説明用）：

```json
{"id":"case-A","label":0,"label_name":"entailment","evidence":[{"page":7,"text":"原文の引用"}],"metrics":{"input_tokens":8431,"output_tokens":112,"inference_time_ms":1820}}
```

| label | label_name | 意味 |
| --- | --- | --- |
| 0 | entailment | 文書が claim を支持する |
| 1 | neutral | 支持も反証もする情報が足りない |
| 2 | contradiction | 文書が claim と矛盾する |

### 根拠の規則

- A の label 0/2 は最低1件の evidence が必要。**物理 PDF の1始まりページ番号**と、**source の原言語の逐語引用**（またはそのページのテキスト）を返す。翻訳・言い換えは不可。
- 1 evidence は約1ページ以内、**5,000文字まで**。超過は評価対象外。**先頭5件だけ採点**される。最も関連する引用を先に置く。
- neutral は `evidence: []` でよい。
- 複数箇所が必要なら別々の evidence として返す。冒頭要約より、`vote` に対応する詳細説明箇所を優先する。同じ事実が複数箇所にある場合は各箇所を引用する。
- **B の evidence は任意で採点されない。出す場合の page は `null`**（Solution API Guide）。古いスライド／現コードの beginner page=1 と区別する。
- 公式の引用照合は改行・空白・行末ハイフン等の抽出差を許容する。gold passage に短い引用が含まれる、または引用ページ内に gold passage が含まれる場合も対象。

### 評価

- 非公開 held-out benchmark の **3クラス macro-F1**（各クラス F1 の単純平均）が主指標。beginner/B と advanced/A を別々に報告。
- アーカイブした OST starter README には有効提出の最低値 **B: 0.70、A: 0.60** が記載されている。現在の mock はこれを満たさない。
- 根拠の gold passage match、advanced の page match、根拠の関連性・正しさ。
- input/context token 数（合計）、output token 数（reasoning token を含め全 call を合計）。自己申告は主催者の **token-counting proxy** と照合され、**主催者側のカウントが優先**。
- case wall-clock latency（ms）の **mean / p95**。公式の相対 token/time score は他チームと proxy の情報が必要で、ローカルだけでは再現できない。
- **DE / FR / IT 別、同言語 vs cross-lingual 別**の分析。claim/reference 言語別や全言語ペアの分析も実験で残す。
- starter のローカル評価はまだ page check をしないと明記されている。ローカル点数を公式点数と呼ばない。

## 4. 重要な参加・実行・権利規則

- **Apertus v1.5 を primary model とする**（8B / 70B）。OST Solution API Guide は推論に Apertus v1.5 のみを要求する。**商用・非公開モデルは使わない**。Track 2 共通説明では他の open-weights model を開発補助（自動 judge 等）に使えるが、その役割を報告書で明示する。提出推論に他モデルを混ぜてよいとは解釈しない。
- テンプレートの **`track_2a/` を改名・移動しない**。必要なファイル・定義を保持する。`data/` は **100 MB 以下**。
- clean checkout から **Docker の `make run` で end-to-end** 実行可能にする。ホスト上の事前インストールに依存しない。runtime・hardware・API key・model weights 要件を記載する。
- OST API Guide は **linux/amd64、評価 container は GPU なし**を指定。`/data` は read-only、出力は `/output`、cache は `/tmp` 等。依存物と必要なローカル weights は image に含め、runtime download はしない。
- 評価時に主催者が **`BASE_URL` / `API_KEY`** で proxy URL と team key を注入する。環境変数優先で読み、**すべての remote model call をその `BASE_URL` に通す**。開発用公式 endpoint は `https://api.inference.cscs.ch/v1`（キーは別途必要）。ローカル parsing / OCR / embeddings は許容される。
- 提出時、Hackathon Output は公開され、**コード・model weights は Apache-2.0、文書・非コード資料は CC-BY-4.0** の **撤回不能**なライセンスになる。提出 dataset は CDLA-Permissive-2.0。著作権は本人に残るが、提出後の削除でもライセンスは消えない。第三者データを勝手に再ライセンスできるわけではなく、互換性・出典を確認する。
- 提出者は、**本人／チームが開催期間中に作った仕事**であること、第三者素材のライセンス遵守、機密・専有・営業秘密を含まないこと、権利侵害がないことを保証する。**勤務先・大学等の権利請求がない／必要な確認済みであること**を高宮さんに確認する。既存 IP は分離し、必要な部分を公開できるか確認する。

## 5. repo と環境

| 場所 | path / URL |
| --- | --- |
| 高宮さんの gmktec | `~/Work/hackapertus-ost` |
| GitHub | `https://github.com/yasuhito/hackapertus-ost`（private） |
| branch | `master`（通常の push 済み、origin は上記 repo） |
| box の repo | `/workspace/hackapertus-ost` |
| box の冊子 PDF | `/workspace/ost-booklets`（repo 外、gitignored 扱い） |

主な実装・資料：

- `track_2a/src/predict.py`：JSONL CLI、pypdf 抽出、ページ marker、全文 prompt、Apertus OpenAI-compatible client、mock、出力検証。
- `track_2a/src/score.py`：ID 整列のローカル scorer。順序非依存。missing / duplicate / malformed / error を誤答にする。
- `track_2a/tests/test_pipeline.py`：16テスト（PDF extraction・ローカル HTTP protocol テストを含む）。
- `track_2a/scripts/download_dataset.py`：checksum 検証付き dataset 再取得。
- `track_2a/scripts/download_booklets.py`：連邦官房 URL の冊子取得。URL SHA256 の先頭16桁を PDF 名に使用。
- `track_2a/scripts/prepare_data.py`：投票冊子公開日単位の train/dev 分割と advanced cases 生成。
- `track_2a/data/source.jsonl`：HF `OSTswiss/MNLIoverSwissVotingBooklets` の **`v1.1.jsonl`、1,488行、12,742,710 bytes**。public / ungated、**公式 split は train のみ**。公式 dev/test を取得したわけではない。
- `track_2a/data/{train,dev}_{cases,gold}.jsonl`、`dev_advanced_{cases,gold}.jsonl`：ローカル生成物。gold を予測器に渡さない。
- `track_2a/data/dataset_stats.json`：分割・言語・ラベル統計。`sha256('ost-dev-v1:' + booklet_publish_date)` の順に日付グループの約20%を dev にする。**train 1,157 / dev 331**、同日付の言語違いを分離しない。
- label 件数：0=495 / 1=498 / 2=495。claim 言語 DE=495 / FR=497 / IT=496、reference 言語 DE=455 / FR=569 / IT=464。
- **60冊子 PDF、合計75,379,251 bytes（約75 MB）**を box に取得済み。repo 内データは約38 MB。PDF 自体は git に入れない。
- `track_2a/docs/{architecture.md,task_spec.txt,dataset_readme.md,booklet_manifest.json}`：設計、OST スライド抽出、dataset 説明、冊子情報。
- `Dockerfile`、ルート `Makefile`、`track_2a/Makefile`：CPU client image と実行ターゲット（track 側はルートへ委譲）。
- `track_2a/technical_report.md`：報告原稿。`track_2a/data/results/`：既存 mock dev 結果。

現 CLI は PDF を cache し、全文を `[PAGE N]` 付きで1回の LLM call に渡す。検索・圧縮・truncation・OCR は未実装。0/2 の evidence を抽出原文の厳密な substring として確認する。不正入力、引用不正、PDF 不在、API failure は neutral placeholder と `error` を返す。**mock への自動 fallback はない**。

## 6. 再開用コマンド（ここでは実行手順の記載のみ）

以下は repo root で実行する。box なら `cd /workspace/hackapertus-ost`、gmktec なら `cd ~/Work/hackapertus-ost`。

### セットアップ・テスト・mock smoke

```sh
python3 -m venv .venv
.venv/bin/pip install -r track_2a/requirements.txt
make test PYTHON=.venv/bin/python
make run-local PYTHON=.venv/bin/python LLM_BACKEND=mock
# 出力：output/predictions.jsonl
```

既存記録では **16 tests pass**、non-Docker `make run-local` 確認済み。今回の引き継ぎ文書作成で再実行したという意味ではない。

### gmktec で冊子を再取得し、絶対 path を作り直す正確なコマンド

```sh
cd ~/Work/hackapertus-ost
make download PYTHON=.venv/bin/python BOOKLET_DIR="$HOME/Work/ost-booklets"
make prepare PYTHON=.venv/bin/python BOOKLET_DIR="$HOME/Work/ost-booklets"
```

`make download` は dataset と PDF の両方を取得する。既存 PDF は再利用する。直接 PDF だけ取得するなら：

```sh
.venv/bin/python track_2a/scripts/download_booklets.py \
  --source track_2a/data/source.jsonl --output-dir "$HOME/Work/ost-booklets"
```

box の再生成は `make prepare PYTHON=.venv/bin/python BOOKLET_DIR=/workspace/ost-booklets`。advanced dev cases は **絶対 path** を持つため、別ホストでは必ず再生成する。

### 全 dev の mock 評価（beginner 331 + advanced 331）

```sh
make dev-eval PYTHON=.venv/bin/python
# output/dev_predictions.jsonl, output/dev_score.json
# output/dev_advanced_predictions.jsonl, output/dev_advanced_score.json
```

このターゲットは **常に `--backend mock`**。環境変数だけでは real Apertus 評価にならない。単独 scorer の呼び方：

```sh
.venv/bin/python track_2a/src/score.py \
  --gold track_2a/data/dev_gold.jsonl \
  --predictions output/dev_predictions.jsonl --output output/dev_score.json
```

既存 mock 結果は両タスク **macro-F1 0.174107、invalid 0**。beginner の厳密 evidence match は **0/214**。これは wiring 確認のみで Apertus の品質・速度を示さない。

### Docker（未検証）

```sh
make run
# 現在のデフォルトは安全な mock smoke
make run INPUT_DIR=/data OUTPUT_DIR=/output BOOKLET_DIR=/path/to/booklets \
  LLM_BACKEND=openai
```

mount：input `/data`、output `/output`、PDF `/booklets`。PDF path は `/booklets/name.pdf`、または入力 JSONL の親からの相対 path にする。box の絶対 path を持つ advanced dev cases をそのまま container で使っても動かない。さらに現在の input directory mount には gold も含まれるため、審査用は **cases/PDF のみの directory**を準備し、gold を container 外に置く。

## 7. モデルアクセス・費用・VRAM

**Public AI の API キーは未取得。real Apertus inference／有料 API call は未実施。**

現在のコードが読む環境変数（公式 `BASE_URL` / `API_KEY` とはまだ異なる）：

| 変数名 | 現在の default / 用途 |
| --- | --- |
| `LLM_BACKEND` | CLI default `openai`、Makefile default `mock` |
| `LLM_BASE_URL` | `https://api.publicai.co/v1` |
| `LLM_MODEL` または `LLM_NAME` | `swiss-ai/apertus-v1.5-8b`（前者優先） |
| `LLM_API_KEY` または `PUBLICAI_API_KEY` | 前者優先。Public AI は必須、local vLLM は任意 |
| `LLM_USER_AGENT` | `HackApertus-OST/1.0 (Track-2A)` |
| `LLM_TIMEOUT` | `180` 秒 |
| `LLM_MAX_OUTPUT_TOKENS` | `2048` |

70B の Public AI model 名は `swiss-ai/apertus-v1.5-70b`。承認済みの **既存 local vLLM server** に接続するなら、`LLM_BASE_URL=http://localhost:8000/v1` と `LLM_MODEL=<served Apertus model name>` を指定する。Docker 内 localhost は container 自身なので、到達可能な host/network address を使う。現 Docker image は client のみで weights/server は含まない。

VRAM の目安（context / KV cache / concurrency / serving overhead で増える。保証値ではない）：

- **8B：bf16 約24 GB、FP8 約12–16 GB、4bit 約8 GB**。
- **70B：4bit でも48 GB以上**を目安にする。

Public AI の検討用価格（USD / 100万 tokens、input / output）：

- **8B：$0.10 / $0.20**。
- **70B：$0.82 / $2.92**。

価格は利用前に確認し、API call は高宮さんの承認後のみ。pi にこれらの API クレジットを流用しない。

## 8. 既知の不足・公式契約との差分

1. **gold page number がない**。dataset の `reference_string` は pypdf 抽出と完全一致せず、advanced 非 neutral **214件すべて evidence 評価対象外**。local advanced evidence rate は `null`（0点や成功ではない）。検証済み page/span mapping を作る必要がある。
2. **Docker は未実行検証**（box に Docker がない）。clean checkout / linux/amd64 / mount / permission / mixed A+B / proxy injection を別の対応ホストで確認する。
3. **real Apertus run がない**。8B/70B の NLI、長文 context limit、JSON 成功率、実 token 数、latency は不明。
4. **環境変数の不一致**：現コードと Makefile は `BASE_URL` / `API_KEY` を読まず／渡さず、`LLM_*` を使う。公式 proxy を通せるように直すことが提出の blocker。
5. **B evidence の不一致**：現 decode は B にも0/2の evidence と page=1 を要求し、scorer も B evidence を採点する。公式 API Guide の B optional / page=null に合わせる必要がある。
6. **local scorer は公式評価器ではない**：厳密な gold 全文一致・全 gold passage 要求で、evidence/metrics 不正も分類の誤答にする。公式 starter は label 採点と evidence 採点を分離し、fuzzy overlap を使う。現 decoder は5,000文字・先頭5件制限も enforce していない。
7. 現 counters は endpoint `usage` があれば使用し、なければ **ceil(UTF-8 bytes / 4)** の推定。mock も推定で、公式 token-counting proxy の値ではない。複数 call 化したら全 call と reasoning を含む合算が必要。
8. 全文 prompt のみで retrieval/compression/cross-lingual 専用処理はまだない。現生成 B cases は `vote` と公式の nested `language` を欠くため、公式形のテストも追加する。mock を最終モデルとして提出しない。

## 9. 残りのロードマップ（期限内、承認境界を守る）

1. 公式 API 契約との差分（proxy env、B evidence、採点規則、入力メタデータ）を先に解消する。
2. 承認済み endpoint または local vLLM を確保し、**8B / 70B の dev baseline** を同一 split で実行。B と全文 A を別々に記録し、モデル名・設定・token・mean/p95・言語別・same/cross の結果を残す。
3. gold page/span を手動検証し、A evidence 指標を測れるようにする。抽出の空白・改行・ハイフン差の扱いを明示する。
4. `vote` に沿う chunk retrieval / selected context / compression で context を削減。全文 baseline と macro-F1・evidence・token・latency を比較し、根拠の原文と物理 page を保持する。
5. **cross-lingual handling**：DE/FR/IT 全組合せの retrieval miss、否定・数値・話者帰属・政治的推奨の取り違えを分析。claim の変換を使っても evidence は原文のまま返す。
6. 対応ホストで Docker clean-checkout `make run` を end-to-end 確認。最終評価で real Apertus と injected proxy を使い、gold leakage を防ぐ。
7. **6ページ以内 PDF** に設計・context 処理・Apertus 利用・実験・token/time・再現手順・制限・教訓をまとめる。ライセンス／権利保証と審査者の repo アクセスを高宮さんに確認する。
8. **高宮さんの明示承認後のみ**、締切前に公式 website から提出する。勝手な登録・提出・支払い・公開はしない。

## 10. 規則アーカイブの入口

`docs/rules/` は無認証の公開資料保存。HTML / PDF 原本と全文 Markdown、取得元・日時・manifest・`SHA256SUMS` を保持している。登録や form 提出は行っていない。

優先して読むファイル：

- `docs/rules/INDEX.md`：全体の provenance と一覧。43 accessible Notion pages、全5 academia challenges、提出 form 全10分岐を保存。
- `docs/rules/notion/Track-2A-OST-3deb4fec.md`：課題の目的・言語・成果物。
- `docs/rules/notion/solution-api-guide-ef5b4fec.md`：最新の具体的な input/output・evidence・proxy・Docker 契約。
- `docs/rules/repositories/ost-starter-README.md`：評価閾値、fuzzy evidence、proxy と local evaluation の違い。
- `docs/rules/attachments/28ede48885-HackApertusTrack2AMNLIOverSwissVotingBooklets.pdf`、`attachments/1a1d81e7a4-hackapertus-qa.pdf`：OST 説明・Q&A。旧スライドだけで契約を決めない。
- `docs/rules/notion/How-to-Submit-a-Project-c91b4fec.md`、`docs/rules/web/hackapertus-submission-form-7.md`：締切・提出場所・OST form（6ページ PDF）。
- `docs/rules/web/hackapertus-terms-and-conditions.md`：特に section 6 の不可撤回ライセンスと権利保証。
- `docs/rules/repositories/project-template-track_2a-README.md`：layout・Docker・100 MB。
- `docs/rules/NOT_FETCHED.md`：未取得物を正直に記録。

**NOT_FETCHED は「規則がすべて取得済みだから無視してよい」という意味ではない**。未取得は任意の social-preview image **10件**（署名 URL なし／HTTP 400）と、active collection にない古い Notion database reference **17件**（block 空／sync HTTP 403、title 不明）。発見済み PDF と accessible rule pages は取得済みだが、 inaccessible reference の内容は推測しない。署名 URL は期限切れになり得るのでローカル原本を読む。
