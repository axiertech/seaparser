# Uppskattad regional färdsimulering

Vinga–Uddevalla kan nu simuleras offline med den befintliga färdmotorn,
verkliga frysta MET/WAV/PHY-värden och kontrollerade reservförbindelser genom
vatten. Detta är ännu inte en aktiverad regional API-/PoC-profil.

Den bevarade bunten `/home/web/seaparser/data/vinga-uddevalla-20261018` återanvänds.
`freeze_coastal_with_audit` använder befintlig hash-/CF-kontroll och samma
NetCDF-materialiserare, utan att skriva om inventeringen. Samma
`CopernicusMarineAdapter` normaliserar egna våg-/strömgrid till `MarineReserve`.
Ingen andra adapter eller vädermotor har byggts. MET-native-läsaren och
interpolationen återanvänds. Äldre normaliseringslägen och områdesgränser består.

`CoastalForecast` komponerar det materialiserade underlaget utan fil-/HTTP-/SQL-
åtkomst under färden. `compare_routes` och `sail_to_target` gör samma
strömkompensation, mittpunktsintegration, absoluta uppslagsgränser, syntetiska
komfortberäkning, tids-/stegkontroll och separat ankomstkontroll som tidigare.
En `CoastalObstacle` kontrollerar hela slutna accepterade segment och 10 m
landmarginal mot det hashbundna OSM-vattnet. Även predikterade provpunkter på land
avvisas som hinder. Djup och landfullständighet är fortfarande okända.

## Regional rörelse och stöd

Den separata `RegionalAeqdMotionFrame` använder befintlig WGS84-/AEQD-differential
inom explicit 120 km. Fysiska vind-, ström- och båthastigheter stannar i sanna
öst/nord-komponenter; endast positionsderivatan och kursriktningen avbildas.
Äldre 1 500 m-klass och 900 m-profiler har inte fått högre gränser.
Oberoende ellipsoidiska geodetiska förflyttningar prövar regionala punkter upp
till cirka 114 km, med 2 µm/s tolerans för differentialen vid testets korta steg.

Vindens native-koordinatbild av varje högst 1 000 m integrerat segment omsluts
med en särskild konfigurerad utvecklingsmodell: AEQD→MET antas 2-Lipschitz inom
120 km och ges 2 m extra gardering. Hela omslutningen måste ligga inom egna
native-axlar och innehålla finita stödnoder över segmentets tidsintervall.
Modellen har täta numeriska referensprov, men är ett uttryckligt modellantagande,
inte källverifierad datumekvivalens eller ett generellt geometribevis.

För varje marin produkt väljs en konkret stödjande källa vid segmentmitt.
Dess kontrollerade vattenväg plus halva segmentlängden måste rymmas inom
konfigurerat källavstånd. Källtiden måste klara tidsavvikelsen vid båda
segmentändarna. Då finns en tillåten förbindelse från varje punkt av det
landfria segmentet via mittpunkten till källan. Uppslag vid start, faktisk
mittpunkt och slut behåller sina egna värden och källposter. Söktrunkering och
uppskattningar döljs inte. Ingen reservnod tillförs över land.

Valda gränser kan inte vägas bort av komfort. Utöver motorns uppslagskontroller
kräver hela-segment-kontrollen konservativa källhöljen för markvind och Hs.
Alla finita normaliserade källnoder ingår, vilket kan ge konservativ avvisning
även om lokala uppslag är lägre. Ett otillräckligt hölje anges som otillräckligt
underlag, inte som konstaterat överskridande. Vindhöljet använder exakt kvadrat-
jämförelse av de största absoluta komponenterna. I det verkliga fallet är de
6,56855 och 6,66232 m/s, och hela källans största Hs är 0,563827 m.

## Källor, antaganden och resultat

`settings/coastal-weather-assumptions.json` binder bunt, planeringsklocka,
antagen utfärdandetid, maxålder, arbetsram och specifika antaganden.
Originalens tre `issued_at` förblir `null` i `provenance.source_metadata`.
Utvecklingsutfärdandet används bara med uttryckliga `assumed_fields` i
kompositionen; källans tider, hashar, versioner, kör-/mask-/tidsluckor och
modellantaganden hålls separerade. Reservpolicyerna versionsstyrs per variabel
enligt coastal-reserve.md. Båtmodellen är befintlig uppskattad konstantfart 5 kn;
komfortmåttet är oförändrat och inte validerat för verkliga båtrörelser.

Resultatet har `result_qualification=estimated_high_uncertainty` och
`weather_limits_verified=false`. Motorns `weather_segment_status` förblir
`not_available`; inga uppskattningar ges status `verified` för att kringgå
befintliga export-/UI-grindar. De grindarna kräver en uttrycklig uppskattnings-
presentation i nästa steg. Per accepterat segment anges kandidat, ben, steg,
provposition/tid och variablernas källposition/tid/värde, avstånd, tidsavvikelse,
vattenförbindelse och eventuell söktrunkering. Identiteten inkluderar källor,
antaganden, faktisk avgång, ändpunkter, vald väderpolicy, båt, resurser och algoritm.

Verifierat verkligt fall med den tidigare sparade 250 m-kandidaten:

| Mått | Beräknat resultat |
|---|---:|
| Avgång | 2026-10-18 09:00 UTC |
| Ankomst | 2026-10-18 18:34:12,631393 UTC |
| Restid | 34 452,631393 s, cirka 9 h 34 min |
| Fysisk distans via befintlig mittpunktsmetrik | 88 955,90 m |
| Syntetisk komfortexponering | 3 449,09, ej validerat mått |
| Accepterade segment / färdben | 592 / 33 |
| Vind vid mittpunkter | 0,385–4,416 m/s |
| Ström vid mittpunkter | 0,00498–0,2364 m/s |
| Hs vid mittpunkter | 0,00777–0,2339 m |
| Saknade mittpunktsvärden | 0 |
| Reservposter i segmentens provpunkter | 8 232 |

Första fulla körningen tog 93,15 s och överskred regionala 60 s-budgeten.
Begränsad memoization av identiska frysta uppslag ändrar inte värden eller
sökordning. Därefter tog en ny process 46,68 s: inläsning 12,03 s, befintlig
motor 30,99 s och presentation 2,47 s, plus slutlig serialisering. Restid och
komfort var exakt oförändrade. Detta avser en redan bevarad geometrikandidat,
inte ny sökning för fria punkter eller flera kandidater/avgångar. Den generella
interaktiva regionala latensen är ännu inte kvalificerad.

Det avslutande kommandoradsprovet gav samma restid, distans och komfort men tog
62,10 s (13,81 s inläsning, 41,73 s motor, 5,96 s presentation). Det överskrider
60 s och visar att den enskilda 46,68 s-körningen inte är en robust leveransbudget.
PROJECT_BLOCKER: interaktiv koppling behöver beständig återanvändning och mätt
kandidatsökning innan aktivering. Den verifierade leveransen är därför offline.

Reproducerbar körning utan nya uttag eller ändring av rådata:

```sh
.venv/bin/python -B -m scripts.simulate_coastal \
  /home/web/seaparser/data/vinga-uddevalla-20261018 \
  --candidate /tmp/seaparser-uddevalla-candidates.json \
  --output /tmp/seaparser-coastal-voyage.json
```

Nästa leverans kopplar regional scen/beräkning till samma PoC, med synlig hög
osäkerhet i karta, jämförelse och särskilt märkt GPX. Fria ändpunkter behöver
budgeterad kandidatsökning och beständig återanvändning. Befintlig webb/API
har inte aktiverats om i denna leverans och tidigare sidor är bevarade.
