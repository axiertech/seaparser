# Lokal granskning av frysta Vinga-prov

Separat granskningsartefakt: `artifacts/vinga-frozen-review/index.html`.
Öppna filen direkt i webbläsaren; ingen server, API, databas, internetanslutning
eller installation behövs för visningen. Sidan avser **13 oktober 2026
12:00–16:00 UTC**, inte aktuell prognos. Den innehåller verkliga redan sparade
prov, inte syntetiska prognoser eller en kvalificerad ruttberäkning.

## Bygg och verifiera

Från repositoryroten med Python 3.14.4 och `requirements.lock` installerad:

```bash
python -B -m scripts.export_frozen_forecast --output artifacts/vinga-frozen-review/index.html
sha256sum artifacts/vinga-frozen-review/index.html
python -B -m unittest tests.test_frozen_forecast_review -v
node --test frontend/tests/frozen-forecast.test.mjs
```

`index.receipt.json` innehåller byggkommando, SHA-256 för HTML och data samt
`published: false`. Bygget är deterministiskt, utan byggtid eller nätverk.
Källfilernas hashvärden finns dessutom i sidan. Testet jämför den versionsstyrda
artefakten med en ny rendering från nuvarande hashvaliderade källor.

Frontendens HTML, CSS och JavaScript finns i `frontend/presentation/`.
`scripts/export_frozen_forecast.py` orkestrerar befintliga läsare:
`read_wind_sample` och `freeze_with_audit`. Ingen ny adapter eller datahämtning
införs. Vindkoordinaterna kommer från samma hashvaliderade metadatasnapshot som
vindläsarens granskning; de läses inte om efter granskningen.
`presentation/frozen_forecast_html.py` sätter samman frikopplade data och layout.

## Granskningsfunktioner och begränsningar

- Eget diagram för varje källa: vind 7 × 8 punkter i Lambert-källkoordinater;
  vågor respektive ström 2 × 2 punkter på sina **olika** latitud-/longitudgrid.
  Nodgränser, fulla koordinater och enheter visas; gränserna bevisar inte hela
  cellers täckning. Ingen datumtransformation eller geografisk överlagring antas.
- Separata val för källa, storhet, UTC-tid och punkt. Klickbara/tangentbordsvalbara
  punkter, tidsreglage samt råvärdestabell och punktdiagram över tid. Ingen
  interpolation, ifylld prognosyta eller vindpilsrotation. Färgskalan hålls fast
  över alla tider inom vald storhet, inte mellan källor/storheter.
- Saknade råvärden, landmarkeringar och okänd mask skiljs åt. De faktiska frysta
  proven har inga saknade värden och vågmasken har fyra havspunkter; det är inte
  bevis för att ström eller vind har kvalificerat stöd. Vindens markandel visas
  separat och är aldrig giltighetsmask. Strömmen lånar inte vågmasken.
- Utfärdandetider, marina modellreferenser och verifierade run-identiteter är
  uttryckligen okända. Vindens modellreferens visas som referens, inte utfärdande.
  Katalogversion är inte köridentitet. Run-förenlighet är inte verifierad.
- Vindens dokumenterade 600 s medel har okänd tidsplacering. Marina källor anger
  tidsmedel men saknar verifierad längd/placering. Tm02 är vågens spektralperiod,
  inte ett sådant tidsmedel. Vindram och omvandling till ruttens ram kvalificeras
  inte; marina CF-komponenter och riktningar märks med sin källsemantik.
- Layouten är responsiv men introducerar inget val av visuell editor. Det
  befintliga kravet på visuell redigering av produktens layout kvarstår.

Automatiserade DOM-tester kör interaktionen mot den verkliga självständiga
HTML-filen och prövar även injicerade luckor, nollvärden och separata maskstatusar.
De ersätter inte en manuell visuell granskning i riktiga desktop-/mobilwebbläsare.

## Publiceringsunderlag – inte publicerat

Artefakten är helt fristående med inbäddade data, CSS och JavaScript. CSP tillåter
endast de hashbundna inbäddade resurserna och blockerar nätverksanrop. Källänkar
är explicita användarval. Inga externa karttiles, lokalisering eller API-anrop.
Källattribution och licenslänkar för MET Norway och Copernicus Marine finns i
sidan. JSON skyddas mot avslutande script-taggar och etiketter skrivs som text.

Vid senare uttryckligen godkänd publicering: använd endast denna HTML-fil efter
kontroll mot kvittots hash, välj en separat granskningsadress, behåll varningen
om historiska data och gör manuell visuell/tangentbords-/mobilgranskning före
aktivering. Ingen befintlig demonstrationssida ska ersättas. Leveransen har
inte ändrat publik webbrot, tjänst, serverkonfiguration eller publiceringsskript.
