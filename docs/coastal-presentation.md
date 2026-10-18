# Vinga–Uddevalla i samma PoC

Välj Vinga–Uddevalla på samma `/poc/index.html`, eller öppna
`/poc/index.html?example=vinga-uddevalla`. Den faktiskt simulerade färden för
18 oktober 2026 09:00 UTC visas med orange streckad linje, distans, restid,
ankomst, vind/Hs/ström och det befintliga syntetiska komfortmåttet.

Detta är en sparad modellfärd, inte en ny regional beräkning i webbläsaren.
Ett faktiskt simulerat alternativ finns: 88,96 km, 9 h 34 min. Jämförelse mellan
flera regionala vägval och fria punkters färdsimulering återstår. De befintliga
Vinga-alternativen/liveflödet och tidigare publika sidor bevaras.

Hela den regionala färden märks **hög osäkerhet**, i karta, jämförelse, ruttkort
och GPX. `weather_limits_verified=false` och motorns
`weather_segment_status=not_available` behålls. GPX har en separat uttrycklig
uppskattningsexport; den tidigare exportens krav på verifierat segmentstöd
försvagas inte. Saknat stöd eller misslyckad ankomst blir inte exportbart.

Fria kartpunkter kan fortfarande kontrolleras mot de strikta native-gridens
datastöd. Ändrad punkt, koordinatinmatning eller provtid tar bort den sparade
färden och GPX-länken. Knappen för den simulerade färden återställer tydligt
dess ursprungliga punkter och avgång. Ett sent svar för tidigare val får inte
visa en färd efter ändrade val. Vatten-/landkontroller och valda vädergränser
är kvar i den ursprungliga simuleringskompositionen, se coastal-voyage.md.

## Källor och segment

`application/coastal_presentation.py` presenterar resultatet från samma
befintliga motor. Vind-/ström-/vågmetrik hämtas från dess verkliga simulerade
mittpunkter; inga nya vädervärden skapas. Källmetadata med okända utfärdanden
och antaganden om utfärdande/modell hålls separata. Reservpolicyer visas per
variabel, inklusive vattenförbindelse- och sökbudgetar.

Alla 8 232 reservposter för 592 accepterade segment bevaras utan
informationsförlust. Upprepade källor och vattenförbindelser lagras i tabeller,
med referenser från respektive segments start/mitt/slut. Varje post kan
återställas med exakt variabel, källposition/tid/värde, provposition/tid,
avstånd, tidsavvikelse och hela kontrollerade vattenförbindelsen.
Gränssnittet visar valbart segment och erbjuder hela underlaget som JSON.

Återställda segment har samma SHA-256 som den bevarade fulla simuleringens
ursprungliga `estimated_segments`:
`f6a577c38dd2a9ad27767dcbaba51baa49fdc487796b7a68c74100ffbb1b8d9e`.
Hashformat är `application.planning.canonical`, UTF-8 utan avslutande radbrytning.
Originalfärden och samtliga råfiler bevaras utanför publika resurser.

`fixtures/coastal-voyage.json` är cirka 1,42 MB och kopieras till PoC-bygget.
Den särskilt märkta GPX-filen är fristående: den innehåller samma käll-/segment-
tabeller, antaganden och ruttsammanfattning i namnrymdsförsedda extensions,
samt 34 planerade vägpunkter. Inget GPS-spår eller påhittade positionstider skapas.
Färdens faktiska provtider finns i extensions. GPX:s huvudtext och metadata
anger hög osäkerhet och ej verifierade vädergränser.

## Bygge och publicering

`scripts.build_poc --presentation-only` kontrollerar befintliga bygghashar och
återanvänder hela tidigare beräkningsbanken. Därefter uppdateras enbart
presentationsresurser, det spårbara kustresultatet och dess GPX samt kvittot.
Fullbygget genererar samma nya kustresurser. Inga nya väderuttag sker.

Den befintliga `deployment.poc`-allowlisten omfattar de namngivna nya filerna
och explicit märkta kust-GPX. Förberedelse, hashkontroll, atomisk publicering
och återställning bevarar tidigare sidor. Detta steg ändrar ingen API-process,
systemtjänst, proxyregel eller databas.

PROJECT_BLOCKER: den regionala fria-punkt-/fleralternativsberäkningen behöver
fortsatt mätas mot oförändrad 60 s/64 MiB-resultatbudget. Kallkörningen 67,27 s
från föregående leverans är inte en godkänd interaktiv latens. Den synliga
sparade färden är en avgränsad användbar leverans, inte en färdig regional liveprofil.
