# C system prompt: proposed inputs for approval

STOP: proposed review only. No split, grader changes, prompt edits, or new inference have been run.

All 54 already-seen approved development cases are retained, not selected by current failures. Source: saved C-r1 manifest frozen[0..53]. Expected labels remain scoring-only; no competitive holdout is accessed. The linked full source is local saved development input, not new data.

Each case has claim, source language, task and full frozen source/context in output/cscs/format-C-r1/manifest.json. Review those exact inputs before accepting this eval. No API outputs or logs are copied here.

## 00 ost-dev54-0117-B
- Date/task: 2020-09-27 / B
- Languages: de / de
- Claim: Laut der Zusammenfassung treten die sechs übrigen bilateralen Abkommen automatisch ausser Kraft, wenn das Personenfreizügigkeitsabkommen gekündigt wird.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[0].case`, `.pages`, `.messages`.
- Provenance group: source_row 117; preserve associated A/B and overlapping source/vote/booklet together.

## 01 ost-dev54-0117-A
- Date/task: 2020-09-27 / A
- Languages: de / de
- Claim: Laut der Zusammenfassung treten die sechs übrigen bilateralen Abkommen automatisch ausser Kraft, wenn das Personenfreizügigkeitsabkommen gekündigt wird.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[1].case`, `.pages`, `.messages`.
- Provenance group: source_row 117; preserve associated A/B and overlapping source/vote/booklet together.

## 02 ost-dev54-0557-B
- Date/task: 2021-03-07 / B
- Languages: de / de
- Claim: Dem Abstimmungstext zufolge soll das Verhältnis zwischen dem höchsten und dem niedrigsten Lohn in einem Unternehmen auf 1:12 beschränkt werden.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[2].case`, `.pages`, `.messages`.
- Provenance group: source_row 557; preserve associated A/B and overlapping source/vote/booklet together.

## 03 ost-dev54-0557-A
- Date/task: 2021-03-07 / A
- Languages: de / de
- Claim: Dem Abstimmungstext zufolge soll das Verhältnis zwischen dem höchsten und dem niedrigsten Lohn in einem Unternehmen auf 1:12 beschränkt werden.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[3].case`, `.pages`, `.messages`.
- Provenance group: source_row 557; preserve associated A/B and overlapping source/vote/booklet together.

## 04 ost-dev54-1117-B
- Date/task: 2020-09-27 / B
- Languages: de / de
- Claim: Laut dem Abstimmungstext gilt die steuerliche Berücksichtigung der Kosten für die Betreuung durch Dritte für jedes Kind, das noch keine 16 Jahre alt ist.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[4].case`, `.pages`, `.messages`.
- Provenance group: source_row 1117; preserve associated A/B and overlapping source/vote/booklet together.

## 05 ost-dev54-1117-A
- Date/task: 2020-09-27 / A
- Languages: de / de
- Claim: Laut dem Abstimmungstext gilt die steuerliche Berücksichtigung der Kosten für die Betreuung durch Dritte für jedes Kind, das noch keine 16 Jahre alt ist.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[5].case`, `.pages`, `.messages`.
- Provenance group: source_row 1117; preserve associated A/B and overlapping source/vote/booklet together.

## 06 ost-dev54-0315-B
- Date/task: 2021-03-07 / B
- Languages: fr / de
- Claim: Si le vote est approuvé, les droits de douane sur tous les principaux produits suisses exportés vers l’Indonésie seront éliminés.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[6].case`, `.pages`, `.messages`.
- Provenance group: source_row 315; preserve associated A/B and overlapping source/vote/booklet together.

## 07 ost-dev54-0315-A
- Date/task: 2021-03-07 / A
- Languages: fr / de
- Claim: Si le vote est approuvé, les droits de douane sur tous les principaux produits suisses exportés vers l’Indonésie seront éliminés.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[7].case`, `.pages`, `.messages`.
- Provenance group: source_row 315; preserve associated A/B and overlapping source/vote/booklet together.

## 08 ost-dev54-0716-B
- Date/task: 2020-09-27 / B
- Languages: fr / de
- Claim: Si la votation est approuvée, la Suisse interdira l’usage de pesticides de synthèse dans l’agriculture à compter de 2025.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[8].case`, `.pages`, `.messages`.
- Provenance group: source_row 716; preserve associated A/B and overlapping source/vote/booklet together.

## 09 ost-dev54-0716-A
- Date/task: 2020-09-27 / A
- Languages: fr / de
- Claim: Si la votation est approuvée, la Suisse interdira l’usage de pesticides de synthèse dans l’agriculture à compter de 2025.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[9].case`, `.pages`, `.messages`.
- Provenance group: source_row 716; preserve associated A/B and overlapping source/vote/booklet together.

## 10 ost-dev54-1316-B
- Date/task: 2020-09-27 / B
- Languages: fr / de
- Claim: Le résumé précise que la déduction maximale pour la garde par un tiers passera de 25 000 à 10 100 francs par enfant.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[10].case`, `.pages`, `.messages`.
- Provenance group: source_row 1316; preserve associated A/B and overlapping source/vote/booklet together.

## 11 ost-dev54-1316-A
- Date/task: 2020-09-27 / A
- Languages: fr / de
- Claim: Le résumé précise que la déduction maximale pour la garde par un tiers passera de 25 000 à 10 100 francs par enfant.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[11].case`, `.pages`, `.messages`.
- Provenance group: source_row 1316; preserve associated A/B and overlapping source/vote/booklet together.

## 12 ost-dev54-0475-B
- Date/task: 2021-03-07 / B
- Languages: it / de
- Claim: Nel riassunto si dichiara che l’E-ID è facoltativa e che il Bund controlla l’identità del richiedente prima di autorizzare il provider a emettere l’E-ID.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[12].case`, `.pages`, `.messages`.
- Provenance group: source_row 475; preserve associated A/B and overlapping source/vote/booklet together.

## 13 ost-dev54-0475-A
- Date/task: 2021-03-07 / A
- Languages: it / de
- Claim: Nel riassunto si dichiara che l’E-ID è facoltativa e che il Bund controlla l’identità del richiedente prima di autorizzare il provider a emettere l’E-ID.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[13].case`, `.pages`, `.messages`.
- Provenance group: source_row 475; preserve associated A/B and overlapping source/vote/booklet together.

## 14 ost-dev54-0830-B
- Date/task: 2020-09-27 / B
- Languages: it / de
- Claim: Se la votazione verrà approvata, la Svizzera introdurrà un nuovo regime fiscale per le imprese multinazionali a partire dal 2025.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[14].case`, `.pages`, `.messages`.
- Provenance group: source_row 830; preserve associated A/B and overlapping source/vote/booklet together.

## 15 ost-dev54-0830-A
- Date/task: 2020-09-27 / A
- Languages: it / de
- Claim: Se la votazione verrà approvata, la Svizzera introdurrà un nuovo regime fiscale per le imprese multinazionali a partire dal 2025.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[15].case`, `.pages`, `.messages`.
- Provenance group: source_row 830; preserve associated A/B and overlapping source/vote/booklet together.

## 16 ost-dev54-1412-B
- Date/task: 2020-09-27 / B
- Languages: it / de
- Claim: Nel riassunto si sostiene che la revoca dell’accordo sulla libera circolazione delle persone non farebbe decadere automaticamente gli altri sei accordi delle Bilaterali I, dato che non è prevista alcuna clausola ghigliottina.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[16].case`, `.pages`, `.messages`.
- Provenance group: source_row 1412; preserve associated A/B and overlapping source/vote/booklet together.

## 17 ost-dev54-1412-A
- Date/task: 2020-09-27 / A
- Languages: it / de
- Claim: Nel riassunto si sostiene che la revoca dell’accordo sulla libera circolazione delle persone non farebbe decadere automaticamente gli altri sei accordi delle Bilaterali I, dato che non è prevista alcuna clausola ghigliottina.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[17].case`, `.pages`, `.messages`.
- Provenance group: source_row 1412; preserve associated A/B and overlapping source/vote/booklet together.

## 18 ost-dev54-0073-B
- Date/task: 2020-09-27 / B
- Languages: de / fr
- Claim: Das Komitee vertritt die Auffassung, dass die neuen Kinderabzüge bei der direkten Bundessteuer nahezu ausschliesslich wohlhabenden Familien zugutekämen – konkret nur 6 % der Schweizer Haushalte.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[18].case`, `.pages`, `.messages`.
- Provenance group: source_row 73; preserve associated A/B and overlapping source/vote/booklet together.

## 19 ost-dev54-0073-A
- Date/task: 2020-09-27 / A
- Languages: de / fr
- Claim: Das Komitee vertritt die Auffassung, dass die neuen Kinderabzüge bei der direkten Bundessteuer nahezu ausschliesslich wohlhabenden Familien zugutekämen – konkret nur 6 % der Schweizer Haushalte.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[19].case`, `.pages`, `.messages`.
- Provenance group: source_row 73; preserve associated A/B and overlapping source/vote/booklet together.

## 20 ost-dev54-0508-B
- Date/task: 2020-09-27 / B
- Languages: de / fr
- Claim: Der Bundesrat ist der Ansicht, dass das Rentenalter für Frauen und Männer auf 67 Jahre angehoben werden muss, damit die AHV langfristig finanziell nachhaltig bleibt.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[20].case`, `.pages`, `.messages`.
- Provenance group: source_row 508; preserve associated A/B and overlapping source/vote/booklet together.

## 21 ost-dev54-0508-A
- Date/task: 2020-09-27 / A
- Languages: de / fr
- Claim: Der Bundesrat ist der Ansicht, dass das Rentenalter für Frauen und Männer auf 67 Jahre angehoben werden muss, damit die AHV langfristig finanziell nachhaltig bleibt.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[21].case`, `.pages`, `.messages`.
- Provenance group: source_row 508; preserve associated A/B and overlapping source/vote/booklet together.

## 22 ost-dev54-1142-B
- Date/task: 2020-09-27 / B
- Languages: de / fr
- Claim: Der Zusammenfassung zufolge sieht der Vorschlag vier Wochen bezahlten Vaterschaftsurlaub vor, die innerhalb der ersten sechs Monate nach der Geburt des Kindes genommen werden müssen.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[22].case`, `.pages`, `.messages`.
- Provenance group: source_row 1142; preserve associated A/B and overlapping source/vote/booklet together.

## 23 ost-dev54-1142-A
- Date/task: 2020-09-27 / A
- Languages: de / fr
- Claim: Der Zusammenfassung zufolge sieht der Vorschlag vier Wochen bezahlten Vaterschaftsurlaub vor, die innerhalb der ersten sechs Monate nach der Geburt des Kindes genommen werden müssen.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[23].case`, `.pages`, `.messages`.
- Provenance group: source_row 1142; preserve associated A/B and overlapping source/vote/booklet together.

## 24 ost-dev54-0240-B
- Date/task: 2020-09-27 / B
- Languages: fr / fr
- Claim: Le comité estime que les PME ne disposent pas des ressources financières et organisationnelles nécessaires pour instaurer un congé de paternité de deux semaines, les remplacements de courte durée étant coûteux et complexes.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[24].case`, `.pages`, `.messages`.
- Provenance group: source_row 240; preserve associated A/B and overlapping source/vote/booklet together.

## 25 ost-dev54-0240-A
- Date/task: 2020-09-27 / A
- Languages: fr / fr
- Claim: Le comité estime que les PME ne disposent pas des ressources financières et organisationnelles nécessaires pour instaurer un congé de paternité de deux semaines, les remplacements de courte durée étant coûteux et complexes.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[25].case`, `.pages`, `.messages`.
- Provenance group: source_row 240; preserve associated A/B and overlapping source/vote/booklet together.

## 26 ost-dev54-0826-B
- Date/task: 2020-09-27 / B
- Languages: fr / fr
- Claim: Le Conseil fédéral préconise que les cantons consacrent davantage de ressources à la rénovation des infrastructures ferroviaires régionales d’ici 2028.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[26].case`, `.pages`, `.messages`.
- Provenance group: source_row 826; preserve associated A/B and overlapping source/vote/booklet together.

## 27 ost-dev54-0826-A
- Date/task: 2020-09-27 / A
- Languages: fr / fr
- Claim: Le Conseil fédéral préconise que les cantons consacrent davantage de ressources à la rénovation des infrastructures ferroviaires régionales d’ici 2028.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[27].case`, `.pages`, `.messages`.
- Provenance group: source_row 826; preserve associated A/B and overlapping source/vote/booklet together.

## 28 ost-dev54-1306-B
- Date/task: 2021-03-07 / B
- Languages: fr / fr
- Claim: D’après le texte soumis au vote, l’interdiction de se couvrir le visage s’applique aussi dans les lieux de culte.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[28].case`, `.pages`, `.messages`.
- Provenance group: source_row 1306; preserve associated A/B and overlapping source/vote/booklet together.

## 29 ost-dev54-1306-A
- Date/task: 2021-03-07 / A
- Languages: fr / fr
- Claim: D’après le texte soumis au vote, l’interdiction de se couvrir le visage s’applique aussi dans les lieux de culte.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[29].case`, `.pages`, `.messages`.
- Provenance group: source_row 1306; preserve associated A/B and overlapping source/vote/booklet together.

## 30 ost-dev54-0346-B
- Date/task: 2020-09-27 / B
- Languages: it / fr
- Claim: Se il voto sarà approvato, la deduzione massima per le spese di custodia dei bambini da parte di terzi nell’ambito dell’imposta federale diretta aumenterà da 10'100 a 25'000 franchi per bambino.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[30].case`, `.pages`, `.messages`.
- Provenance group: source_row 346; preserve associated A/B and overlapping source/vote/booklet together.

## 31 ost-dev54-0346-A
- Date/task: 2020-09-27 / A
- Languages: it / fr
- Claim: Se il voto sarà approvato, la deduzione massima per le spese di custodia dei bambini da parte di terzi nell’ambito dell’imposta federale diretta aumenterà da 10'100 a 25'000 franchi per bambino.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[31].case`, `.pages`, `.messages`.
- Provenance group: source_row 346; preserve associated A/B and overlapping source/vote/booklet together.

## 32 ost-dev54-0835-B
- Date/task: 2020-09-27 / B
- Languages: it / fr
- Claim: Se il voto verrà approvato, il Giappone adotterà una nuova legge sulla privacy dei dati digitali che permetterà alle aziende di condividere le informazioni degli utenti con i partner commerciali senza un consenso esplicito.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[32].case`, `.pages`, `.messages`.
- Provenance group: source_row 835; preserve associated A/B and overlapping source/vote/booklet together.

## 33 ost-dev54-0835-A
- Date/task: 2020-09-27 / A
- Languages: it / fr
- Claim: Se il voto verrà approvato, il Giappone adotterà una nuova legge sulla privacy dei dati digitali che permetterà alle aziende di condividere le informazioni degli utenti con i partner commerciali senza un consenso esplicito.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[33].case`, `.pages`, `.messages`.
- Provenance group: source_row 835; preserve associated A/B and overlapping source/vote/booklet together.

## 34 ost-dev54-1387-B
- Date/task: 2020-09-27 / B
- Languages: it / fr
- Claim: Il riassunto afferma che il costruttore aggiudicatario si impegnerà ad affidare mandati in Svizzera per un valore pari al 30% del prezzo d’acquisto.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[34].case`, `.pages`, `.messages`.
- Provenance group: source_row 1387; preserve associated A/B and overlapping source/vote/booklet together.

## 35 ost-dev54-1387-A
- Date/task: 2020-09-27 / A
- Languages: it / fr
- Claim: Il riassunto afferma che il costruttore aggiudicatario si impegnerà ad affidare mandati in Svizzera per un valore pari al 30% del prezzo d’acquisto.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[35].case`, `.pages`, `.messages`.
- Provenance group: source_row 1387; preserve associated A/B and overlapping source/vote/booklet together.

## 36 ost-dev54-0092-B
- Date/task: 2020-09-27 / B
- Languages: de / it
- Claim: Der Bundesrat ist der Ansicht, dass es keine brauchbare Alternative zu den Kampfjets gibt, weil sogenannte leichte Kampfjets, also bewaffnete Schulflugzeuge, weder für den täglichen Luftpolizeidienst noch für Einsätze in Krisensituationen geeignet sind.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[36].case`, `.pages`, `.messages`.
- Provenance group: source_row 92; preserve associated A/B and overlapping source/vote/booklet together.

## 37 ost-dev54-0092-A
- Date/task: 2020-09-27 / A
- Languages: de / it
- Claim: Der Bundesrat ist der Ansicht, dass es keine brauchbare Alternative zu den Kampfjets gibt, weil sogenannte leichte Kampfjets, also bewaffnete Schulflugzeuge, weder für den täglichen Luftpolizeidienst noch für Einsätze in Krisensituationen geeignet sind.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[37].case`, `.pages`, `.messages`.
- Provenance group: source_row 92; preserve associated A/B and overlapping source/vote/booklet together.

## 38 ost-dev54-0601-B
- Date/task: 2021-03-07 / B
- Languages: de / it
- Claim: Laut der Zusammenfassung wurde die Mindestlohn-Initiative von der Bevölkerung abgelehnt.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[38].case`, `.pages`, `.messages`.
- Provenance group: source_row 601; preserve associated A/B and overlapping source/vote/booklet together.

## 39 ost-dev54-0601-A
- Date/task: 2021-03-07 / A
- Languages: de / it
- Claim: Laut der Zusammenfassung wurde die Mindestlohn-Initiative von der Bevölkerung abgelehnt.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[39].case`, `.pages`, `.messages`.
- Provenance group: source_row 601; preserve associated A/B and overlapping source/vote/booklet together.

## 40 ost-dev54-1140-B
- Date/task: 2021-03-07 / B
- Languages: de / it
- Claim: Das Komitee vertritt die Auffassung, dass es ein Fortschritt ist, die Vergabe von Identitäten privaten Unternehmen wie Banken und Versicherungen zu übertragen, da dies die Effizienz erhöht und die Bürgerinnen und Bürger besser vor dem Missbrauch ihrer Daten schützt. Deshalb empfiehlt es, mit Ja zu stimmen.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[40].case`, `.pages`, `.messages`.
- Provenance group: source_row 1140; preserve associated A/B and overlapping source/vote/booklet together.

## 41 ost-dev54-1140-A
- Date/task: 2021-03-07 / A
- Languages: de / it
- Claim: Das Komitee vertritt die Auffassung, dass es ein Fortschritt ist, die Vergabe von Identitäten privaten Unternehmen wie Banken und Versicherungen zu übertragen, da dies die Effizienz erhöht und die Bürgerinnen und Bürger besser vor dem Missbrauch ihrer Daten schützt. Deshalb empfiehlt es, mit Ja zu stimmen.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[41].case`, `.pages`, `.messages`.
- Provenance group: source_row 1140; preserve associated A/B and overlapping source/vote/booklet together.

## 42 ost-dev54-0302-B
- Date/task: 2021-03-07 / B
- Languages: fr / it
- Claim: Si le vote est adopté, les droits de douane sur les importations d’huile de palme indonésienne ne seront pas supprimés, mais réduits de 20 à 40 % environ, dans la limite de 12 500 tonnes par an.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[42].case`, `.pages`, `.messages`.
- Provenance group: source_row 302; preserve associated A/B and overlapping source/vote/booklet together.

## 43 ost-dev54-0302-A
- Date/task: 2021-03-07 / A
- Languages: fr / it
- Claim: Si le vote est adopté, les droits de douane sur les importations d’huile de palme indonésienne ne seront pas supprimés, mais réduits de 20 à 40 % environ, dans la limite de 12 500 tonnes par an.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[43].case`, `.pages`, `.messages`.
- Provenance group: source_row 302; preserve associated A/B and overlapping source/vote/booklet together.

## 44 ost-dev54-0816-B
- Date/task: 2020-09-27 / B
- Languages: fr / it
- Claim: Le Conseil fédéral recommande que la Suisse adhère à l’Union européenne avant 2030.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[44].case`, `.pages`, `.messages`.
- Provenance group: source_row 816; preserve associated A/B and overlapping source/vote/booklet together.

## 45 ost-dev54-0816-A
- Date/task: 2020-09-27 / A
- Languages: fr / it
- Claim: Le Conseil fédéral recommande que la Suisse adhère à l’Union européenne avant 2030.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[45].case`, `.pages`, `.messages`.
- Provenance group: source_row 816; preserve associated A/B and overlapping source/vote/booklet together.

## 46 ost-dev54-1295-B
- Date/task: 2021-03-07 / B
- Languages: fr / it
- Claim: Selon le texte soumis au vote, l’interdiction de se couvrir le visage concerne aussi les lieux de culte.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[46].case`, `.pages`, `.messages`.
- Provenance group: source_row 1295; preserve associated A/B and overlapping source/vote/booklet together.

## 47 ost-dev54-1295-A
- Date/task: 2021-03-07 / A
- Languages: fr / it
- Claim: Selon le texte soumis au vote, l’interdiction de se couvrir le visage concerne aussi les lieux de culte.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim. Claim and source use different languages; preserve meaning across languages.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[47].case`, `.pages`, `.messages`.
- Provenance group: source_row 1295; preserve associated A/B and overlapping source/vote/booklet together.

## 48 ost-dev54-0347-B
- Date/task: 2020-09-27 / B
- Languages: it / it
- Claim: Se la votazione viene approvata, i Cantoni potranno gestire il numero di lupi per prevenire danni alle greggi di pecore e capre.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[48].case`, `.pages`, `.messages`.
- Provenance group: source_row 347; preserve associated A/B and overlapping source/vote/booklet together.

## 49 ost-dev54-0347-A
- Date/task: 2020-09-27 / A
- Languages: it / it
- Claim: Se la votazione viene approvata, i Cantoni potranno gestire il numero di lupi per prevenire danni alle greggi di pecore e capre.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[49].case`, `.pages`, `.messages`.
- Provenance group: source_row 347; preserve associated A/B and overlapping source/vote/booklet together.

## 50 ost-dev54-0924-B
- Date/task: 2021-03-07 / B
- Languages: it / it
- Claim: Nel riassunto si sostiene che nel 2022 il popolo svizzero abbia approvato l’iniziativa popolare «Sì al divieto dell’importazione di carne contenente ormoni di crescita».
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[50].case`, `.pages`, `.messages`.
- Provenance group: source_row 924; preserve associated A/B and overlapping source/vote/booklet together.

## 51 ost-dev54-0924-A
- Date/task: 2021-03-07 / A
- Languages: it / it
- Claim: Nel riassunto si sostiene che nel 2022 il popolo svizzero abbia approvato l’iniziativa popolare «Sì al divieto dell’importazione di carne contenente ormoni di crescita».
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[51].case`, `.pages`, `.messages`.
- Provenance group: source_row 924; preserve associated A/B and overlapping source/vote/booklet together.

## 52 ost-dev54-1486-B
- Date/task: 2020-09-27 / B
- Languages: it / it
- Claim: Nel testo di voto si afferma che l’Assemblea federale raccomanda al Popolo e ai Cantoni di approvare l’iniziativa.
- Why hard: Classify only from the supplied reference, distinguishing direct support, direct opposition and missing information.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[52].case`, `.pages`, `.messages`.
- Provenance group: source_row 1486; preserve associated A/B and overlapping source/vote/booklet together.

## 53 ost-dev54-1486-A
- Date/task: 2020-09-27 / A
- Languages: it / it
- Claim: Nel testo di voto si afferma che l’Assemblea federale raccomanda al Popolo e ai Cantoni di approvare l’iniziativa.
- Why hard: Identify the relevant physical PDF pages and attributed source statements before classifying the claim.
- Full frozen input: `output/cscs/format-C-r1/manifest.json` → `frozen[53].case`, `.pages`, `.messages`.
- Provenance group: source_row 1486; preserve associated A/B and overlapping source/vote/booklet together.

