# Offlinevisning för granskning

`make check` verifierar lokala HTML/CSS-resurser och Python-tester för rapport,
export, säker textåtergivning och kontrollstatus. Node-testkörningen har ännu
0 tester; de åtta visningstesterna ligger i tests/test_scenario_html.py.
Inga frontendberoenden har tillkommit; package-lock.json låser beroendegrafen.

Generera en självförsörjande visning med fem reproducerbara scenarier:

```
.venv/bin/python -B -m scripts.export_scenario_html --output /tmp/seaparser-demo-index.html
```

En befintlig JSON-rapport kan visas med `--report rapport.json`. Varje scenario
kan exporteras som exakt ursprunglig JSON via nedladdningslänken; rapportens
SHA-256 visas för kontroll. HTML innehåller inbäddad CSS och SVG, inga skript,
nätverksanrop, externa typsnitt eller kartresurser. Publicera endast målfilen.

Layout/CSS finns i scenario-demo.html och scenario-demo.css. Presentationen i
presentation/scenario_html.py läser färdiga rapporter och beräknar inga rutter.
Orkestrering sker i scripts/export_scenario_html.py. Streckade linjer visar hela
kandidaten; heldragna linjer endast accepterade integrerade segment.

Kontroller gäller den numeriska modellen och explicit undersökta alternativ.
Konstaterat överskridande skiljs från otillräckligt konservativt bevis eller
saknade data. Ingen verifierad kandidat är inte bevis för att andra rutter är
omöjliga. Markvind/Hs certifieras konservativt; komfort är syntetisk och ej
validerad. Syntetiska koordinater/hinder är ingen sjökarta. Uppskattad polar,
fryst planeringstid, datasetversion, avbrottsorsaker och ankomstkontroll visas.

Detta är ett granskningsverktyg. Visuell editor väljs separat efter utvärdering;
HTML/CSS uppfyller inte ensamt kravet på visuell redigering. AIS är fortsatt
lågprioriterat. Ingen GPS, övervakning eller kollisionsrådgivning ingår.
