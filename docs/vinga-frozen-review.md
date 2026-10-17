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
- Vindens dokumenterade 600 s medel har okänd tidsplacering. Vågor anger
  tidsmedel men saknar verifierad längd/placering; strömmen saknar sådan uppgift. Tm02 är vågens spektralperiod,
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

## Grafisk granskning av provsegmentets underlag

På vindfliken finns nu valet **Visa underlag för provsegmentet**. Den inbäddade
matematiska källsfärsbanan går från (−300,−200) till (400,300) lokala meter,
12:20–14:40 UTC den 13 oktober 2026. Ett streckat område visar hela banans
konservativa inneslutning i vindens egna koordinater. Det är inte banans faktiska
form eller en verklig WGS84-rutt. Lila ringar markerar de rånoder som ingår i
inventeringen för vald sparad tid. Punktvalet förklarar om punkten ingår.

Underlaget har 9 platser vid 4 sparade tider, sammanlagt 36 prov, samt de
12 rumtidsrutor som framgår av den maskinläsbara rapporten. Grannpunkter och
sparade tider utanför själva passagen behövs för den konservativa granskningen.
Vid 16 UTC finns inga markerade stödnoder för denna bana; vindens övriga
prov kan fortfarande granskas. Vid byte till vågor eller ström döljs både
hölje och markeringar. Ingen annan produkts mask eller koordinater överförs.

Segmentrapporten genereras av samma `inspect_source_local_segment` som CLI,
från **samma redan infångade hashvaliderade vindsnapshot** som värdevisningen.
Inga vindfiler öppnas igen efter den inledande läsningen. Rapportens och hela
vindindatans SHA-256 finns under granskningsbanans spårbarhet. Frontend visar
bara överlagringen när källhasharna matchar och kvalificeringsgrindarna är
fortsatt stängda. Detta gör inte stödets producentmask, interpolation,
datum-/serialiseringsfel, vindram, medelplacering eller säkerhetshölje kända.

Samtidigt rättas en felaktig presentationsfras: vågorna deklarerar tidsmedel,
men de frysta strömfälten gör det **inte**. Strömmens medelprocess, längd och
placering är fortsatt okända. Källäst skillnad följer även som
source_time_means i de frikopplade presentationsdata. Råfixtures är oförändrade.
Ingen ny kvalificering, rådatahämtning eller publik ändring.

Regressioner verifierar överlagringens tids-/produktseparation, punktmedlemskap,
avvisning av blandade källhashar/kvalificeringsflaggor, faktiskt råvärdesinnehåll,
samt att segmentrapporten fortfarande kan byggas när de redan infångade
vindfilerna tas bort. Byggkommando och kvitto ovan gäller även denna version.

## Valbar provbana och ofullständigt stöd

Bygget accepterar `--segment FIL.json` med något av de två befintliga,
uttryckliga matematiska källsfärsformaten. WGS84 är inte ett godkänt format.
Den valda filen läses en gång; dess exakta bytehash följer både HTML och
byggkvittot. `--segment-max-cells` begränsar inventeringen (1–512).
Kvittots byggkommando bevarar även valda argument och citerar sökvägar.

Ett separat negativt exempel byggs från repositoryts rot med låst Pythonmiljö:

```sh
python -B -m scripts.export_frozen_forecast --segment fixtures/met-source-segment-outside.json --output artifacts/vinga-outside-review/index.html
```

Öppna `artifacts/vinga-outside-review/index.html` lokalt. Banan lämnar både
sparade koordinatgränser och tider. Vid aktiverad överlagring visas hela höljet,
utökade axlar och en grå ram för de faktiskt sparade nodgränserna. Inga positiva
stödmarkeringar visas, inte heller vid en överlappande tid eller punkt.
Arbetsgräns och saknade värden förklaras på samma sätt som ofullständigt stöd.
Den vanliga råprovvisningen är fortfarande tillgänglig på respektive eget grid.
Detta är en matematisk frågefixture, inga nya väderdata eller kvalificerade rutter.

Varje artefakts aktuella SHA-256 finns i dess `index.receipt.json`; kontrollera
filhashen mot detta före senare godkänd publicering. Båda byggena är fristående
och förblir opublicerade. Manuell visuell browsergranskning återstår.


## Separat webbpublicering av granskningen

Föreslagen adress: https://seaparser.com/vinga-prognosprov.html
Befintlig startsida, Vinga-demo, API och systemtjänst behålls.
`deployment.frozen_review` återanvänder befintliga Vinga-flödets
`atomic_public_copy`, hashkontroller och manifestprincip, avgränsat till en
enda ny statisk fil. Kör inte activate-vinga.sh för denna tilläggssida: det
flödet byter startsida och tjänst och är avsett för annan aktivering.

Efter granskad ren commit förbereds en ny katalog utanför public/:

```sh
cd /tmp/seaparser-real-map-data
/usr/bin/python3 -B -m deployment.frozen_review prepare /home/web/seaparser/backups/vinga-prognosprov-STAGE
/usr/bin/python3 -B -m deployment.frozen_review verify /home/web/seaparser/backups/vinga-prognosprov-STAGE
```

Byt STAGE mot en ny identifierare. Det faktiska förberedda underlagets
absoluta sökväg och exakta aktiveringskommando lämnas i leveranskvittot.
Endast `public-ready/vinga-prognosprov.html` får ingå. Rå-NetCDF, repository,
manifest, byggkvitto, arbetsloggar och konfiguration publiceras inte.
Artefaktens SHA-256 kontrolleras mot byggkvittot; HTML måste motsvara den
granskade layouten inklusive historik-/routingvarning, tre produkter och
CSP:s hashbundna resurser. Inget nätverk behövs för visningen.

Senare uttrycklig aktivering, som seaparser, använder `publish` i stället för
`verify` med samma katalog. Den vägrar skriva över befintlig separat adress,
kontrollerar att granskad checkout och hela tidigare publiceringen är
oförändrade, och kopierar bara den nya filen atomiskt med 0644-attribut.
Inga root-steg, Apacheändringar, reload/restart eller databasanrop behövs.
`publication-result.json` skrivs först efter lokal innehållsverifiering och
anger uttryckligen att HTTPS ännu inte är verifierat. Ändrad publik snapshot
kräver ny förberedelse; skriv inte över någon extern ändring.

Efter aktivering: hämta exakt den nya URL:en och jämför SHA-256 med manifestet,
kontrollera HTML/MIME och öppna desktop/mobil i webbläsare. Prova produkt-,
tids- och punktval, tangentbord, provsegment och varningar. Kontrollera även
att tidigare demo är oförändrad. Ingen aktivering har gjorts av förberedelsen.

I agentmiljön 2026-10-17 saknas browserverktyg och installerad Chromium,
Chrome/Firefox/Playwright. DOM-tester är körbara men ersätter inte visuell
browser- och mobilgranskning. Detta redovisas som återstående manuell kontroll,
inte som ett godkänt browserprov.
