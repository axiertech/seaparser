# Trelleborg–Strömstad i befintligt PoC

Sparad verklig färd med hög osäkerhet, inte en liveprofil för fria punkter.
Återanvänder bunten `trelleborg-stromstad-20261019`, hashbundet lokalt OSM-vatten,
prognoscachen och återställningssessionens 500 m-kandidat med 16 mellanpunkter.
Ingen ny karta, ny väderkälla eller ändrad tjänstbudget behövdes.

Separat `SwedishCoastAeqdMotionFrame` gäller inom 350 km från befintligt Vinga-
origo. Lokal 1500 m- och regional 120 km-ram är oförändrade. Fysisk öst/nord-
hastighet avbildas med samma WGS84/AEQD-differential. Oberoende ellipsoidiska
förflyttningar prövar hela disken till 350 km i 15-graderssteg, med 2 µm/s
numerisk tolerans. Native-vindomslutningen behåller uttryckligt 2-Lipschitz-
antagande och 2 m gardering; täta numeriska prov är ingen källkvalificering.

`settings/trelleborg-weather-assumptions.json` binder den större ramen,
källbunten, datum och geografiska gränser. Samtliga chunkade MET-källhashar
bevaras. Reservpolicyn behåller avstånd, tidsavvikelse, sökbudget och vattenkrav;
denna profils reservgrid använder 500 m. 335 280 celler ryms inom oförändrad
miljoncellsgräns. Hela accepterade segment kontrolleras med 10 m landmarginal,
egna native-vindnoder, marina stödvittnen och valda vädergränser. Inga luckor
nollfylls eller reservförbindelser tillåts över land.

## Faktiskt beräknat resultat

- Avgång 2026-10-19 09:00 UTC; ankomst 2026-10-21 05:46:48,814044 UTC.
- Restid 161 208,814044 s: 44 h 46 min 48,814044 s.
- Fysisk mittpunktsintegrerad distans 438 695,5269904306 m.
- 2 699 accepterade segment; inga saknade vind-/ström-/vågmittpunkter.
- Vind 3,0283–10,6888 m/s; ström 0,00175–0,53644 m/s; Hs 0,0510–0,71370 m.
- Komfortexponering 355 759,5315, syntetiskt och ej validerat mått.
- En kandidat, en avgång; ingen jämförelse mellan olika vägval eller global optimalitet.

Utan ström skulle cirka 438,7 km vid 5 kn ta 47,38 h. Den verkligt simulerade
färden ryms i de 49 timmarna till 21 oktober 10:00 UTC med 15 191,185956 s
(cirka 4 h 13 min) marginal. Källans arkiverade DDS hämtades på nytt och anger
59 tidpunkter totalt, alltså ingen senare tid i just denna MET-körning.
Ingen tidsmässig prognosextrapolering eller ny prognoshämtning behövdes.
Källadress: https://thredds.met.no/thredds/dodsC/metpparchive/2026/10/19/met_forecast_1_0km_nordic_20261019T00Z.nc.dds

Första riktiga processen tog 119,05 s: inläsning 78,10 s (två nya geometrigrid,
prognoscache hit), motor 38,83 s och presentation 1,23 s. Detta är offline-
beräkning, inte kvalificering för regional interaktiv 60 s-budget.

## Presentation, API och återställning

`fixtures/trelleborg-voyage.json` innehåller sparad jämförelse, kartlinje,
källmetadata och förlustfria reservposter per segment. Samma PoC har ett nytt
scenarioval `?example=trelleborg-stromstad`. Alla 18 planerade vägpunkter finns i
särskilt märkt uppskattnings-GPX. Start, mål och avgång är låsta till den sparade
beräkningen. En fullständig datumstämpel visas för flerdygnsankomst.
Om ett framtida prov stannar före mål presenterar denna profil bara faktiskt
accepterade segment som DELRUTT med stopporsak; GPX får då inte innehålla den
osimulerade svansen. Tidigare verifierad GPX-grind är oförändrad.

API-koden erbjuder samma sparade resultat via
`/api/coastal/scenarios/trelleborg-stromstad` och dess `/routes/water-0/gpx`.
Detta kräver separat aktivering av ny API-kod; den statiska PoC-vyn använder
samma byggda JSON/GPX utan beroende av den historiskt inaktiva API-processen.
Ingen fungerande publik ny API-endpoint påstås utan HTTPS-verifiering.

Bygg med `scripts.build_poc --presentation-only`; den befintliga beräkningsbanken
återanvänds. Publicering följer `deployment.poc prepare/verify/publish` från
ren granskad checkout och sparar föregående resurser för samma moduls `rollback`.
De fem tidigare ändrade deploymentfilerna bevaras ostagade i arbetsroten.

## Verifieringskvitto

En andra process med samtliga cacheträffar tog 138,38 s (88,99 s inläsning,
47,11 s motor, 1,51 s presentation). Hela 41 MB-resultatfilen är byteidentisk
med första processen, inte bara ruttsammanfattningen. Samtliga ursprungliga
segment-/reservposter kan återställas exakt ur publiceringsvyn, och dess
fullständiga resultathash stämmer. Alla fem bevarade deploymentfiler är
byteidentiska med återställningskopiorna.

Lokalt passerade 592 Python-tester inklusive API/GPX och oberoende 350 km-
ramreferenser. Frontendverifiering inkluderar samma PoC:s scenarioval,
2700 kartpositioner, fullständigt ankomstdatum, fryst omfattning och GPX.
Sandboxens localhost-tester kräver begränsat körgodkännande; samma svit körs
utanför nätverksbegränsningen, utan ändrade rättigheter eller ägare.

`systemctl start seaparser-poc-api.service` som seaparser nekades även med
begränsat körgodkännande: `Access denied ... requires interactive authentication`.
Befintlig unit pekar på release `31ba37d5f3c2392684927afe9400fb3a98d9e0a4`.
Den statiska publiceringen ändrar inte detta. En admin behöver först aktivera
en granskad ny release för att de nya API-endpointsen ska bli publika; enbart
start av den gamla releasen publicerar inte den nya koden.

Full frontendomkörning med begränsat godkännande: 38 tester, 37 passerade,
0 fel, 1 avsiktligt överhoppat offentligt API-prov. Direkt uvicorn-prov i
sandboxen gav `could not bind on any address out of [('127.0.0.1', 0)]`, exit 3.
