# Beständig regional indatacache

`application/coastal_inputs.py` återanvänder de befintliga frysta MET- och
NetCDF-läsarna. Materialiseringen lagras före samma Copernicus-normalisering;
väder-/reservpolicy, vattengeometri, segmentkontroller och färdmotor körs
fortfarande. Det är ingen resultatcache eller ny väderadapter.

Aktivera uttryckligen med `--cache` i `scripts.simulate_coastal`. Bibliotekets
standard är ingen beständig skrivning. Följande utvecklingskatalog överlever
process- och delpassbyten utan att skriva i den bevarade råbunten:

```sh
.venv/bin/python -B -m scripts.simulate_coastal \
  /home/web/seaparser/data/vinga-uddevalla-20261018 \
  --candidate /tmp/seaparser-uddevalla-candidates.json \
  --cache /home/web/seaparser/autonomy/cache/coastal-inputs-v1 \
  --output /tmp/seaparser-coastal-cached.json
```

Identiteten binder schema, begäran, samtliga använda väderkällors och
manifestens SHA-256, läsarnas valideringskod och beroendelås. Källbytes hashas
på varje anrop; filernas ändringstid räcker inte. Vid miss körs originalens
kontroller och källorna kontrolleras igen före upptagning. Symlänkar och
källfiler över 64 MiB avvisas. Land-/vattenunderlag valideras fortfarande av
den befintliga kompositionen och materialiseras inte om i denna cache.

JSON lagrar vindens Decimal-värden som exakta strängar, inklusive precision
och exponent. Ingen pickle, nollutfyllnad eller floatavrundning av dessa
indata används. Marina null-värden, faktiska utfärdandetider som null och
separata granskningsmetadata bevaras. Cachen är aldrig bevis för prognosens
aktualitet eller för verifierade vädergränser. Ålder och antaganden bedöms
som tidigare efter inläsning.

`infrastructure/materialized_cache.py` använder processlås för en byggare,
temporär fil, fsync och atomiskt namnbyte. Postens nyckel och innehållshash
kontrolleras vid träff. Korruption ger fel och ersätts inte tyst med nya data.
Budgetar: högst 64 MiB per post, 256 MiB totalt och 256 MiB fri diskreserv.
Vid miss krävs utrymme för maximal post plus reserv före materialisering;
faktisk post och total storlek kontrolleras före skrivning. Ingen automatisk
radering, bakgrundshämtning eller ändring av startarens lås införs.

Befintlig versions-/begäransbunden Copernicus-hämtningscache är kvar enligt
copernicus-download-budgets.md. Denna leverans återanvände samma 30 råfiler
utan uttag eller omskrivning. Materialiseringscachen återanvänder identiska
ingångar mellan processer; normaliserade delgrid från delvis överlappande
buntar sammanslås ännu inte.

Verifierat i nya processer 18 oktober 2026, med bevarad geometrikandidat:

| Körning | Totalt | Inläsning | Motor | Presentation |
|---|---:|---:|---:|---:|
| Kall materialiseringscache, miss | 55,45 s | 15,17 s | 37,11 s | 2,46 s |
| Ny process, beständig träff | 38,14 s | 7,57 s | 27,69 s | 2,15 s |
| Slutlig kod, ny miss | 67,27 s | 13,61 s | 49,29 s | 3,19 s |
| Slutlig kod, ny process/träff | 41,82 s | 6,49 s | 31,84 s | 2,36 s |

Slutlig JSON-skrivning ingår i totalen. Motorvariation är inte en separat
cachevinst: endast indata materialiseras beständigt. Hela resultatfilen från
tidigare körning utan cache och de nya körningarna är byteidentisk:
13 071 350 byte, SHA-256
`8853ec2a853c7363a34db10ad3c4bec968297fcd00de984df0c84e2324a9e4ae`.
Indatahash är fortfarande
`3298152076402d177a4686e0df5adbec1b6a17a5e013fb1fd608e65bf7ef5e0d`.
Uppskattning/hög osäkerhet och ej verifierade vädergränser är oförändrade.

Slutprovets kalla 67,27 s överskrider regionala 60 s. Cachen är alltså ingen
robust kvalificering av den gränsen. Detta kvalificerar inte fria kartpunkter, flera alternativ,
hela API-jobbets 60 s/64 MiB-budget eller andra havsområden. Regional
interaktiv aktivering och samma PoC:s uppskattningspresentation återstår.

## Exakta vattenkomponenter och gridpunkter under en beräkning

`CoastalWater` återanvänder vattenkomponenternas medlemskap för exakta
positioner i en instansbunden LRU med högst 16 384 poster. Polygonerna är
förberedda även för första frågan: `polygon.contains(point)` behåller samma
strikta gränsregel som `point.within(polygon)`. Frågor om samma
källposition behöver inte gå igenom hela den stora kustpolygonen igen.
Varje konkret förbindelse behåller sin slutna segment-/marginalkontroll,
avståndsgräns och egen begränsade sökning. Komponentmedlemskap bevisar
fortfarande inte att det raka segmentet är landfritt. Andra vattenunderlag
har separata cachear. Sökargument valideras vid varje anrop.

Den rena befintliga kandidatgeneratorn återanvänder också oföränderliga
`Vector`-objekt för exakt samma gridnyckel inom en sökning. Det minskar
upprepade allokeringar utan ändrad sökordning, kantpredikat, kostnad eller
budget. Ingen avrundning eller sammanslagning av frågepositioner införs.
Inget uppskattat vädervärde eller vädergränsresultat lagras i dessa cachear.

Slutlig verklig körning 18 oktober 2026, nya processer och samma bevarade
Vinga–Uddevalla-kandidat:

| Cache | Totalt | Inläsning | Motor | Presentation |
|---|---:|---:|---:|---:|
| Tom materialiserings-/geometricache | 43,76 s | 21,69 s | 19,63 s | 1,89 s |
| Ny process, beständig träff | 39,39 s | 7,16 s | 27,43 s | 2,62 s |

Båda resultatfilerna är byteidentiska med originalet ovan, inklusive alla
reservförbindelser, segment, värden och källposter. Motorvariation mellan
processerna kvarstår; detta är ingen garanterad latens eller kvalificering av
hela fria-punkt-flödet. Ny geometrisökning och flera alternativ ingår inte.
Inga nya rådatauttag eller publik API-aktivering genomfördes.

## Kompakt större källmaterialisering 2026-10-19

Det utökade Trelleborg-uttaget har 50×455×208 noder per vindfält.
`DecimalRow` behåller varje validerat Decimal-värdes exakta strängform i
oföränderliga rader; högst 128 rader expanderas till Decimal-objekt samtidigt.
Sekvensåtkomst och NumPy-konvertering ger samma numeriska värden, inklusive
skala, exponent och tecknet på noll. Alla källans form-, tids-, enhets-, hash-
och fysikgränskontroller körs före materialisering. Inget nytt vindgrid införs.

Cacheidentitetens schema 3 lagrar decimalrader och den befintliga marina
payloaden som förlustfritt zlib-komprimerad JSON i base64. Den befintliga
postgränsen 64 MiB och totala 256 MiB-gränsen är oförändrade. Dekodning är
begränsad till 64 MiB per vindfält och 128 MiB marin JSON; avklippta eller
påbyggda kompressionsströmmar avvisas. Dessa är bytebudgetar för materialiserade
indata, inte utökad vädertäckning eller ändrade vädergränser.

Vid kall cache återanvänds de redan validerade indataobjekten efter atomisk
cacheupptagning, utan att först serialisera upp dem en andra gång. Vid träff
körs samma källfingeravtryck och innehållsintegritetskontroll som tidigare.
Äldre cacheposter och rådata bevaras. Nytt schema ändrar endast lagring och
minnesanvändning; routing, reservmetoder och vädercertifiering är oförändrade.

Verkligt Trelleborg-prov 19 oktober, separata processer och samma färdiga råfiler:

| Indataläge | Laddning | Inklusive vindnormalisering | Topp-RSS |
|---|---:|---:|---:|
| Kall, cachemiss | 40,33 s | 45,52 s | 789,2 MiB |
| Ny process, cacheträff | 3,47 s | 8,62 s | 614,2 MiB |

Båda kördes med 1100 MiB adressrymdsgräns, en bibliotekstråd och 180 s timeout.
De materialiserade samtliga 50×455×208 noder, tre marina produkter och
75 712 000 byte finita vindkomponenter. Ny cachepost: 61 470 327 byte
(58,62 MiB). Detta är ett mätt indataprov; full ruttberäkning, landgeometri,
API-processens samlade minne och nya områdets rörelseram är ännu inte
kvalificerade. Ingen ökning av PoC-tjänstens 1 GiB-gräns görs.

Den stora OSM-filens separata strömmande inventering tar 14,70 s med
262,6 MiB topp-RSS under 700 MiB adressrymdsgräns. Samtliga 1 030 000 noder,
19 848 ways och 14 125 individuellt slutna ways matchar bevarad inventering;
källhashen är oförändrad. Detta är inte färdig polygonisering eller bevis på
navigerbarhet. Den negativa landmarginalbuffringen kvarstår som nästa hinder.

## Stora kustfält: samma data med begränsade temporära buffertar

Cacheschema 4 delar marina `data`-fält per yttersta arrayelement: tidsplan för
prognoser, rader för statiska fält. Källmetadata lagras separat. Alla delar har
strikt zlib-framing; den summerade storleken räknar exakt den ursprungliga
kompakta JSON-payloadens metadata, hakparenteser, kommatecken och värden.
Gränsen är fortfarande **128 MiB totalt**, inte 128 MiB per del. Förlorade
fält, ändrade platshållare och avvikande deklarerad avkodad storlek avvisas.
Ingen ny adapter, källhämtning eller automatisk radering införs. Äldre poster
bevaras; schema och kodfingerprint ger en ny separat post.

Vindkomponenter beräknas radvis med tidigare taloperationer och kontroller;
endast slutliga komponentarrayer är stora. Kustläget i samma Copernicus-adapter
konsumerar samma normaliserade noder radvis till oföränderliga arrayer. Äldre
lokal/native-utdata förblir fullständigt frysta tuple-strukturer. Form, CF,
mask, riktning, källvärden och sena fel kontrolleras fortfarande. Råa marina
listor frigörs före vindnormalisering, efter att proveniensens källhashar sparats.

Det verkliga Trelleborg-underlagets avkodade marina payload är byteidentisk
med tidigare schema: 73 513 511 byte, SHA-256
`59a6497cf5e3d24c5b660ee0fd4b4f9db819d82b36456932041c9fa28d785b89`.
Detta bevarar även null, signerad nolla, metadata och axel-/tidsordning.
Ingen vädergräns eller reservmetod ändras av minnesoptimeringen.

Tjänstens 1 GiB-gräns är oförändrad. Offlineprov skiljer virtuell adressrymd
från faktiskt resident minne: 1100 MiB AS gav fortfarande allokeringsfel trots
lägre RSS. Det följande provet tillåter högst 1500 MiB virtuell adressrymd men
stoppar samma enda process vid **900 MiB RSS**, med 180 s yttre timeout och
en intern beräkningstråd. Detta är en mätgräns, ingen ändring av API-tjänsten
eller bevis för hela ruttjobbets minnes-/tidsbudget.

Slutligt verkligt samlat prov 19 oktober 2026: land + cacheträff + normaliserad
ström/våg/vind tog 60,18 s och 830,8 MiB topp-RSS. Båda föreslagna ändpunkter
klarade oförändrad 10 m landmarginal. Före frigjord rå payload var motsvarande
prov 63,81 s / 895,2 MiB. Ny kall cache utan land tog 50,54 s inklusive
vindnormalisering / 768,4 MiB. Dessa delprov omfattar inte sökning,
färdsimulering, resultat, parent-API eller samtidiga jobb. Det större scenariot
är alltså ännu inte interaktivt kvalificerat.
