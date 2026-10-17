# Valbar utvecklingsrouting på 17-oktoberdata

Den nya profilen `vinga-native` väljer en fast, versionsbunden utvecklings-
konfiguration med frysta verkliga MET/WAV/PHY-data från 17 oktober. Den använder
samtliga 24 hinder från det utökade OSM-utdraget. Standardprofilen `vinga`, den
äldre historiska 13-oktobermodellen och publik tjänst är oförändrade.

[Grafisk jämförelse](../artifacts/supported-native-routes/index.html) visar fyra
kandidater över fyra avgångar. [Offlineaudit](../artifacts/supported-native-routes/audit.json)
prövar även 2 och 8 kandidater; 8×4 är endast offline. [Kalla standardprocessprov](../artifacts/supported-native-routes/workers.json)
verifierar de tillåtna kombinationerna för uttryckliga fria ändpunkter
(500,0) och (500,350). Den gamla startpunkten (300,−400) blockeras fortfarande
av det nya landunderlaget och ger inga alternativ.

## Stödd disk och oförändrade gränser

Kandidatnoder får bara ligga inom den slutna 900 m-disken vid det lokala
WGS84-AEQD-origot. Medlemskap jämförs exakt som `east²+north² ≤ radius²` med
Fraction på lagrade tal. Ändpunkter utanför disken ger uttryckligt stopp.
Ett helt rakt grafsegment mellan två punkter i disken ligger i disken eftersom
den är konvex. Detta är en begränsning av kandidatgrafen, inte ett nytt bevis
för källa, verklig navigerbarhet eller integrerad båtbanas giltighet.

Samtliga hårda hinder kontrolleras fortfarande mot varje möjlig grafkant och
mot den integrerade färden, inklusive hinder vars egna boxhörn ligger utanför
disken. Inga hinder tas bort eller klipps. Ett analytiskt väggfall prövar detta:
alla hörn ligger utanför disken men väggen genom disken blockerar färden.
Datastöd, hela segment, absoluta vind-/våggränser och ankomst kontrolleras
separat av befintlig motor. Integrerad avdrift utanför stöd godkänns inte av
att grafens waypoints ligger innanför.

För dessa ändpunkter återstår 21 av 60 kandidatnoder. Det ryms inom befintlig
26-nodsgräns och gav samma åtta undersökta kandidater/ordning/längder som det
föregående 66-nodsprovet. Uppmätt grafberäkning: 0,718 s. Sökningen är fortfarande
begränsad till boxhörn och inte komplett för alla möjliga vägar genom området.

API behåller högst 16 kandidat-/avgångskombinationer, 26 noder, 1000 expansioner/
köposter, 8 waypoints, 1800 s per färd, 2000 integrationssteg, 20 s processgräns,
8 MB resultat och två aktiva processer. Ingen generell gräns har höjts.
Det går inte att skicka godtycklig konfigurationssökväg, nodradie eller
syntetisk marin serie genom HTTP-modellen. Profilvalet är en explicit enum.

Avgångarna är 01:00, 01:10, 02:00 och 04:00 UTC. Hela 1800 s-budgeten måste
rymmas i gemensamma källetiketter 01:00–12:00 UTC, med exklusivt slut.
Tidsmedlets fysiska placering och körförenlighet förblir antaganden.

## Uppmätta resultat

| Kandidater × avgångar | Offlinekomposition | Kall standardprocess |
| --- | --- | --- |
| 2 × 4 | 3,533 s | 6,921 s |
| 4 × 4 | 2,829 s | 10,673 s |
| 8 × 4 | 4,339 s | endast offline |
| 8 × 2 | separat API-kombination | 8,089 s |

Processproven kördes sekventiellt innan riktade tester startades. Detta är
observationer för frysta data och dessa ändpunkter, inte garantier för andra
rutter, värdlast eller två samtidiga jobb. Timeout och misslyckade jobb får
aldrig ge ett godkänt ruttresultat.

I samtliga tre offlinebudgetar vinner samma undersökta alternativ båda kriterierna:
`auto-0` klockan 04:00, restid 136,813299 s och komfortexponering cirka 60,3404.
Grafisk visning redovisar detta, trunkering och exponering. Geometrisk ordning
är inte väderoptimalitet. Komfortvalet tillåter högst 300 s extra restid över
kortast restid bland undersökta avgångar; det är inte tidigast ankomst.
Ingen marin serie har skapats för att skilja vinnarna.

Källorna är fortfarande `unverified`. Resultat är `conditional_on_assumptions`
och `assumed_fields` hålls separat från källästa fakta. Modellreferens,
hämtningstid och antagen utfärdandetid är olika saker. Originalens run/issued_at,
mask-/tidsblockerare, landfullständighet och djup kvalificeras inte. Båten är
uppskattad, komfortmåttet ej validerat och landmask inget navigerbarhetsbevis.

## Lokal granskning utan publicering

```bash
npm --prefix frontend run build
.venv/bin/python -B -m scripts.local_demo --profile vinga-native
```

Öppna lokal loopbackadress på port 8765. `frontend/dist/native.html` använder
befintlig Leaflet-karta, kartklick, budgetval, rätt avgångsetiketter från scenens
tid, alternativkort och planerad GPX. Den nya sidan skapas från samma HTML-
layout som standardprofilen. Ingen ny visuell editor, kartleverantör eller
extern resurs behövs. Hanterad miljö kan blockera TCP-bindning; full
webbläsar-/API-integration verifieras då av ordinarie CI, aldrig publik demo.

Offline utan TCP:

```bash
.venv/bin/python -B -m scripts.audit_supported_routes --output artifacts/supported-native-routes
.venv/bin/python -B -m scripts.audit_supported_routes --workers --output artifacts/supported-native-routes
```

Nästa geografiska mål är helt kombinerat vind-/marin-/land-/rörelseramsstöd
för ett avgränsat större område. 900 m får inte höjas med enbart det tidigare
marina komponentprovet. Befintliga frysta data/cache ska återanvändas.
