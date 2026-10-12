# 提出版までの作業

- [ ] 提出版作成時に英語へ翻訳し 6 ページ以内に収める。参考文献や図を含むPDF全体で数える。英語化は依頼者の指示であり、保存した公式資料に英語指定は見つからなかった。
- [ ] チーム名、メンバー、提出リビジョンと日付、提出モデル、リポジトリURLを確定する。デモは必要性を確認する。
- [ ] 別セッションの完了を待ち、確定した評価結果ファイルからApertus 8B/70BのA/B macro-F1、有効出力率、全API要求数、全入力/出力tokensを転記する。数値ごとに出典パスとJSON項目をTeXコメントに残す。現在の実行ファイル、プロセス、結果ファイルは操作しない。
- [ ] ケース全体の平均/p95時間とAPI待ちを区別して載せる。失敗分の消費を除外せず、cache/reasoningの内数を二重加算しない。replayの時間をAPI推論時間として使わない。
- [ ] 根拠の意味的な支持、公式採点との対応、Apertusの全文書対選択ページ比較を結果ファイルで確認する。未測定はTBDのまま残す。
- [ ] 同一候補の独立反復を確認する。既知devの調整結果を未知データの性能と扱わない。保護holdout (2024-06-09) は使わない。
- [ ] clean checkoutでのDocker実行、混在A/B、CPU linux/amd64、注入BASE_URL、読取専用入力、runtime downloadなしを別の許可された作業で確認する。本作業では認証・提出・公開設定を変えない。
- [ ] 公開前にライセンスと帰属表示、PDF再配布権、審査アクセスを本人が確認する。GPT開発履歴は提出モデルの性能と区別し、利用の適格性を独自に保証しない。
- [ ] 公式テンプレートに沿う提出経路として、既存track_2a/technical_report.mdとの整合を後続作業で取る。今回はreport/以外を変更しない。
- [ ] 論文図を引用するなら図を改変せず、その下の注記に補足と出典を書く。現稿の図は自作で、論文図の引用はない。
- [ ] HANDOFF.mdへの追記は本作業ではしない。必要な引き継ぎは本ファイルとSTATUS.mdに記録する。

## ビルド

TeX LiveのLuaLaTeX、luatexja、HaranoAjiフォント、BibTeXとpdfinfoが必要である。
リポジトリ直下で `make -C report check` を実行する。PDFは `report/main.pdf` にできる。
数値の出典はignored output/にあるため、clean cloneだけでは元の評価ファイルは揃わない。原稿は元ファイルを読まずビルドできる。
root .gitignoreの `*.pdf` に従いPDFをコミットしない。補助生成物とキャッシュはreport/.gitignoreで除外する。

## 公式書式の確認

OST課題は調整可能なMarkdownテンプレートを指定している。公開rawテンプレートを2026-10-12に確認し、Summary、Architecture、Use of Apertus、Data、Evaluation、Limitations、Reproducibility、Next steps、License、Referencesを原稿に反映した。
URL: https://raw.githubusercontent.com/HackApertus/project-template/main/track_2a/technical_report.md

保存版の課題・フォーム・提出方法・リポジトリ要件には、TeXクラス、段組、フォント、余白の指定は見つからなかった。A4、10pt、余白24mmは日本語作業稿の設定であり公式指定ではない。Track 1A/2BのTeamName_Report.pdf命名規則をOSTへ流用しない。
