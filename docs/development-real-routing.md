# Gemensam ruttjämförelse med verkliga data i utveckling

Användarbeslut 2026-10-17: verklig vind, vågor och ström är standard. Saknad
källmetadata får i utvecklingsmiljön hanteras med uttryckliga, konfigurerade
antaganden. Källuppgifter får inte märkas verifierade genom detta beslut.
Syntetiska marina ersättningsscenarier ingår inte i standardflödet; de befintliga
syntetiska referensfallen behålls för tester med kända resultat.

## Synligt resultat

Öppna [den fristående grafiska ruttjämförelsen](../artifacts/real-route-review/index.html).
Den behöver ingen server eller nätåtkomst och har fyra valbara ruttkort och
färgade banor över verkligt fryst OSM-land. Streckat visar planerade ben,
heldraget accepterade integrerade segment. Fullt spårbart
[JSON-resultat](../artifacts/real-route-review/result.json) följer med.

Regenerera samma leverans:

```bash
.venv/bin/python -B -m scripts.export_real_routes --output artifacts/real-route-review
```

För kartklick, egna ändpunkter och nya vädergränser:

```bash
npm --prefix frontend run build
.venv/bin/python -B -m scripts.land_preview --bundle --output frontend/land-dist
.venv/bin/python -B -m scripts.local_demo
```

Öppna `http://127.0.0.1:8765/vinga.html`. API, kartklient och lokal server har
Vinga med verkliga data som standard. Inget av kommandona publicerar något.
Bakgrundsplattor laddas endast efter befintligt aktivt användarval.

## Vad som faktiskt används

Vind: den frysta MET Nordic native-fixturen med 5 × 8 × 7 verkliga styrke-/
riktningsvärden. Vågor och ström: befintliga hashverifierade Copernicus WAV/PHY-
NetCDF-filer i `fixtures/vinga-copernicus`. Ingen ny hämtning behövdes och inga
vädervärden flyttades i rum eller tid. Gemensamt tidsstöd är **2026-10-13
12:00–16:00 UTC**, med exklusiv sluttid. Det är historiska prognosdata, inte
aktuellt väder. WAV-uttaget från 17 oktober blandas inte med vind/ström från 13
oktober och har inte omdaterats för att skapa ett artificiellt överlapp.

Standardfallet går från lokal position (300, -400) till (300, 400) vid Vinga,
med två omvägar runt land och avgångar 12:00 respektive 12:10 UTC. De gamla
västra ändpunkterna låg utanför de verkliga marina gridens stöd och används
inte som standard. Användarval utanför stöd avvisas fortfarande.

Båtprestanda är separat från väderdatan: en tydligt uppskattad konstantfarts-
modell, 5 knop genom vattnet, väljs i konfigurationen. Den befintliga testpolaren
slutar vid 20 knop vind och kan inte extrapoleras för den verkliga vinden i
fallet. Ingen ny påhittad segelpolar införs för att få en rutt. Ingen vinddriven
båtfartsmodell eller bränslemodell påstås verifierad. Vind påverkar fortfarande
vädergränsen, ström påverkar rörelse/ETA, och vågor påverkar vädergräns och
befintligt ej validerat komfortmått.

## Konfiguration och redovisning

[settings/development-weather-assumptions.json](../settings/development-weather-assumptions.json)
anger utvecklingsläge, historisk planeringsklocka/avgång, **antagen**
utfärdandetid för ålderskontroll, maxålder, stödområde, båtmodellens fart,
vädergränser och förklaring av varje specifikt metadataantagande.

Alla kända gap måste namnges: utfärdandetid, körförenlighet, strömmens mask,
vindens geometri/vektorram/giltighetsmask/medelfönster samt marin tidssemantik.
Saknad/tom förklaring eller okänt tillkommet block skapar inget generellt
undantag. API:t låter användaren välja vind-/våggränser, men inte smyga in
privata konfigurationsfiler, ge djupdata verifierad status eller byta till ett
syntetiskt marint scenario.

Resultatets `weather_provenance.verified` innehåller källäst modellreferens för
MET, oförändrade källhashar och originalens marina metadata med issued_at=null.
`actual_source_issued_at` förblir null för alla tre produkter. `assumptions` och
`assumed_issued_at` är separata, med konfigurationens hash. Alla normaliserade
produktmetadata som används villkorligt får `assumed_fields`, inklusive
issued_at. Manifest och varje rutt har `conditional_on_assumptions` och
källkvalificeringen förblir `unverified`. Även GPX beskriver att resultatet är
villkorat av antaganden. Uppfyllda modellgränser är inte en källcertifiering.

De ursprungliga adaptrarna, originalgranskningen och den strikta diagnostiken
behåller saknade metadata och blockerare. Endast den uttryckliga utvecklings-
kompositionen tillämpar antagandena på egna frysta produktkopior. Okända fakta
skrivs alltså inte tillbaka till källor eller till frysta verifieringsfixtures.

## Kontroller som finns kvar

- Finita värden, fysisk våghöjd/period, riktningar och kompletta native-noder
  valideras; en lucka eller NaN får inte ersättas med noll eller syntetiska data.
- Vinden interpoleras på MET:s egna grid. Hela den konfigurerade lokala disken
  omsluts i native LCC med befintlig 1 m stödsmarginal. Mask-/datumtolkningen
  är uttryckligen antagen. Landfraktion används inte som vindmask.
- Marine produkter kontrollerar sina egna rumtidsgrid och stöd längs hela
  segment; vågmasken kopieras inte till ström. Ingen extrapolation sker.
- Vindgränsen använder ett konservativt komponenthölje från verkliga native-
  noder. Avrundning klampas till detta hölje. Hs kontrolleras med befintliga
  marina cellhöljen. För stor omslutning ger otillräckligt bevis, inte tillåtelse.
- Alla hårda OSM-landhinder och vald marginal kontrolleras över hela segment.
  Hårda vädergränser och ankomstkontroll kan inte vägas bort av komfort/tid.
- Samma frysta underlag och antaganden används vid alla valda avgångar.
  Högst åtta kandidater, fyra avgångar och 16 kombinationer i interaktiv utveckling.
  Åtta mellanvägpunkter, 1000 kö-/expansionsposter, 26 grafnoder,
  2000 integreringssteg och 1800 s per rutt behålls.

Grafkön använder nu A* med euklidiskt återstående avstånd som undre gräns,
utan att slå ihop tidsberoende tillstånd eller ta bort alternativa grafvägar.
Det gör omvägarna nåbara inom befintlig köbudget; geometrisk längd är fortfarande
inte väderrestid. Modellkontrollerna avgör sedan vilka kandidater som genomförs.
Sökbegränsning och ofullständighet redovisas fortfarande.

Djup och landunderlagets fullständighet är fortsatt okända. Användning av
verkliga prognosvärden och uttryckliga antaganden är ingen navigationsgaranti.


## Uppmätt utökning 2026-10-17

[Utökad grafisk jämförelse](../artifacts/real-route-budget/index.html) visar
fyra kandidater vid 12:00, 12:10, 13:00 och 15:00 UTC, totalt 16 alternativ.
Karta och klickbart diagram kopplar restid till komfortexponering. Gemensamma
vinnare jämförs över dessa explicita avgångar, och korten behåller vinnare per
avgång. Komfortvalet får högst 300 s extra restid jämfört med snabbaste
undersökta alternativ över samtliga avgångar. Det är kortast restid, inte
ett allmänt råd om avgång eller tidigast ankomst. Exakta lika resultat följer
angiven avgångs-/kandidatordning.

Fler geometriska vägar ändrade inte vinnaren: **auto-0 vid 12:00 UTC** är
både snabbast och har lägst exponeringskostnad över alla undersökta avgångar.
Restid 355,715161 s och komfortexponering 1862,0702 i modellens ej validerade
mått. Samma kandidat vinner också båda kriterierna vid varje avgång. Ingen
syntetisk marin serie eller väderändring har skapats för att skilja vinnarna.
Alla sökningar är trunkerade vid kandidatbudgeten; ingen global optimalitet.

Reproducera utan nätåtkomst:

```bash
.venv/bin/python -B -m scripts.audit_candidates --output artifacts/real-route-budget/audit.json
.venv/bin/python -B -m scripts.audit_candidates --workers --output artifacts/real-route-budget/workers.json
.venv/bin/python -B -m scripts.export_real_routes --output artifacts/real-route-budget --candidates 4 --departures 0 600 3600 10800
```

Auditen prövar 2/4/8 kandidater vid samma fyra avgångar på samma frysta underlag,
med faktisk väggtid separat från resultatidentiteten, sökbudget/trunkering,
alla alternativs status, restid och komfortexponering. Den körs sekventiellt
med varm indatacache; slutlig JSON-kodning och processstart ingår endast i
`workers.json`.

| Kandidater × fyra avgångar | Beräkningstid | Resultatbyte | Grafexpansioner | Trunkering |
| --- | ---: | ---: | ---: | --- |
| 2×4 | 6,677 s | 1 964 132 | 47 | max_candidates |
| 4×4 | 11,261 s | 4 143 644 | 57 | max_candidates |
| 8×4 | 22,180 s | 8 430 172 | 72 | max_candidates |

Samma datasethash användes i alla tre budgetar. Varken 1000-posters sökbudget
eller övriga geometriska gränser höjdes.
Åtta kandidater × fyra avgångar kräver över 20 s och över 8 MB och tillåts därför
**endast i offlineaudit**, inte som API-val. Oförändrade API-skydd är 20 s,
8 000 000 utbytesbyte, två aktiva processer och åtta sparade jobb.
Kalla workerprov gav 4×4: 14,21 s / 4 143 670 byte; 8×2: 15,24 s /
4 276 984 byte. Det är mätningar för standardändpunkter och 10 m marginal,
inte prestandagarantier för andra vägar eller samtidig last. Jobb som når
processgränserna avvisas fortfarande.

API och lokal kartklient erbjuder kandidatbudget 2/4/8 och unika avgångsoffset
0/600/3600/10800 s, högst fyra avgångar och **16 kombinationer**. Standardvalet
är fortfarande två kandidater och två avgångar. Det syntetiska referensfallet
behåller sina tidigare åtta kandidater/två avgångar. Applikationen kräver att
avgång plus hela 1800 s-ruttbudgeten ryms före det gemensamma exklusiva slutet;
segment- och ankomstkontrollerna gäller dessutom varje färd. Geografiskt stöd
är oförändrat: 900 m-tak och egna marina grid/masker. Ingen hämtning eller
publik driftsättning ingår i denna leverans.
