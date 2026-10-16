# 技術レポートの作業状況

## 成果と検証

- 原稿は `report/main.tex`、文献は `report/refs.bib`、自作図は `report/figures/pipeline.tex` である。
- PDFは `report/main.pdf` (絶対パス `/home/yasuhito/Work/hackapertus-ost/report/main.pdf`) である。
- LuaLaTeX + luatexja + BibTeXでビルドし、`pdfinfo` で **5ページ、A4** を確認した。日本語の作業稿であり、完成した提出版ではない。
- `make -C report check` が成功した。最終ログに未定義参照、文字欠落、Overfullの警告はない。全ページを画像化して確認し、図表と参考文献の配置を確認した。
- `report/TODO.md` に「提出版作成時に英語へ翻訳し 6 ページ以内に収める」を記載した。
- PDFはroot `.gitignore` の `*.pdf` に従いコミットしていない。補助生成物、ビルドログ、TeXキャッシュ、確認画像も除外した。
- 初稿とビルド設定のコミットは `7ffb2a851baa0735cb7edf8f293a95e6fe33715f` である。今回の改訂コミットは `git log -1 --format=%H -- report/STATUS.md` で取得できる(自分自身のハッシュはファイル内に固定できない)。
- 初稿では `git add report/` のみを使った。今回の改訂では `report/main.tex`、`report/TODO.md`、`report/STATUS.md` を個別にstageし、コミットする。`report/RULES-CHECK.md` はコミットしない。pushの可否はfetch後に判定し、結果は同ファイルに記録する。

## 骨子

1. 概要 (Summary): 冊子または参照文と主張のNLI、source IDから原文を復元する設計を述べる。
2. アーキテクチャ (Architecture): PDF抽出、案件ページ選択、区間ID、モデル応答、引用復元と検証を述べる。
3. Apertusの使い方 (Use of Apertus): v1.5モデル、接続設定、prompt、usageとケース処理時間を述べる。
4. データ (Data): 公開データ、固定dev54、goldの分離、既知データの偏り、保護holdoutとの区別を述べる。
5. 評価 (Evaluation): 旧Apertusの中断消費を記録し、新Apertus評価の空欄を示す。
6. 制約 (Limitations): 逐語引用と意味的な支持の違い、ページ選択の制約、計測と公式評価の差を述べる。
7. 再現手順 (Reproducibility): Docker契約、明示的なopenai backend、最終確認が必要な手順を述べる。
8. 今後の作業 (Next steps): Apertus比較、全消費計測、提出経路、独立反復の順に残る作業を述べる。
9. ライセンス (License): コードと文書のライセンス、データカードのMIT表記、冊子再配布権の確認を述べる。
10. 参考文献 (References): 公式課題、Solution API Guide、公開データ、公式レポートテンプレートを列挙する。

## 適用した公式ルール

出典は2026-10-12取得のローカルarchiveを基本とした。索引 `docs/rules/INDEX.md` と当時の `HANDOFF.md`(2026-10-16に削除、git履歴に残る)を読み、OSTの資料を優先した。他トラックの規則は流用していない。

| 適用内容 | 出典ファイル |
| --- | --- |
| 提出レポートはPDF、最大6ページ、token usageとinference timeを含む。GitHub URLにはentailment CLIと引用箇所が必要。 | `docs/rules/web/hackapertus-submission-form-7.md` |
| 調整可能なtechnical_report.mdテンプレートを使う。文脈準備、再現性、Apertus、macro-F1、根拠と効率を説明する。 | `docs/rules/notion/Track-2A-OST-3deb4fec.md` |
| テンプレートの8節とLicense/Referencesを反映する。 | 上記OST課題がリンクする公開raw `https://raw.githubusercontent.com/HackApertus/project-template/main/track_2a/technical_report.md` を2026-10-12に追加確認。保存済みの旧 `track_2a/technical_report.md` の実験記述は転用しない。 |
| A/B混在JSONL、0/1/2ラベル、Aの原文言語の逐語根拠、物理ページ1始まり、各約5000文字以内、先頭5件。B根拠は任意、返すならpage=null。 | `docs/rules/notion/solution-api-guide-ef5b4fec.md` |
| Apertus v1.5のみ、注入BASE_URL/API_KEY、CPU linux/amd64、読取専用入力、実行時ダウンロードなし、イメージにキーを入れない。原稿では要求と未検証事項を区別する。 | `docs/rules/notion/solution-api-guide-ef5b4fec.md` |
| 提出は公式WebサイトでありDevpostではない。Docker CLIで審査時にend-to-end実行できること。締切は10月16日12:00 CEST。実際の提出はしていない。 | `docs/rules/notion/How-to-Submit-a-Project-c91b4fec.md` |
| track_2a/を保持し、既存テンプレートと後で整合を取る。make runをclean checkoutで検証する。今回report/以外は変更しない。 | `docs/rules/repositories/project-template-README.md`、`docs/rules/repositories/project-template-track_2a-README.md` |
| 公開データのMIT表記とOST作成者への帰属を記す。PDFの再配布権は別途確認する。 | `docs/rules/repositories/OSTswiss-MNLIoverSwissVotingBooklets-README.md` |

保存版と確認した公式Markdownテンプレートに、TeXクラス、段組、フォント、余白の指定は見つからなかった。A4、10pt、余白24mmは作業稿の設定である。英語化は依頼者の指示で、確認した公式資料の要件とは区別する。ページ上限は最終英語版に適用する。

## 数字の出典

- `output/cscs/preparation-v2/legacy-usage-audit.json`: 旧中断バッチの全要求・全tokensと出力有効フラグ。これは性能評価ではない。
- `HANDOFF.md`: 旧バッチのモデルと停止経緯、固定devの投票日、実装と既知の限界の説明。実験の成績・消費数値は上記JSONから取った。

source IDは原文の所在を示すが、根拠の意味的な支持を保証しない。既知dev54の結果を、未知データの評価、独立反復、公式根拠採点と混同しない。

## 結果待ちの空欄

- Apertus v1.5 8B/70Bのdev54結果全体。
- 各モデルのTask A/B macro-F1、有効出力率。
- 各モデルの全API要求数、全入力/出力tokens(失敗分込み)。
- 各モデルのケース全体時間の平均/p95。API待ちとは区別する。
- 各モデルの根拠の意味的な支持の評価。
- Apertusの全文書対選択ページ比較。
- clean checkoutでのmake run検証。

実験結果以外のTBDはチーム名とメンバー、最終リビジョンと日付、リポジトリURLと最終コミット、デモ、提出モデルの選択である。表の空欄は行とモデルの見出しで識別できる。

## 作業範囲

別セッションのdev54実行、run.sh、現在の結果ファイルやプロセスは操作していない。キー本体の読取・表示・コピーはせず、保護holdout (2024-06-09) のデータも使っていない。提出、公開、認証設定の変更はしていない。pushは他セッションの未pushコミットを含まずfast-forwardになる場合だけ行い、結果をRULES-CHECK.mdに記録する。HANDOFF.mdへの追記はせず、引き継ぎ事項はTODO.mdに記録した。論文図の引用はなく、自作図のみである。
