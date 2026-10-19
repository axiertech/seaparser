# Regionala fria punkter och två verkligt simulerade vägval

`application/coastal_plan.py::plan_coastal` tar uttryckliga WGS84-punkter och
tidszonsangiven avgång. Samma materialisering, CF-/MET-normalisering,
landmedvetna variabelpolicyer och färdmotor återanvänds. Inga data hämtas under
sökning eller simulering. Den bevarade Vinga–Uddevalla-bunten används direkt.

Fria punkter kan beräknas som asynkront jobb i samma PoC. 60 s är ett
prestandamål, inte en automatisk publiceringsspärr. Den publika funktionen
kräver aktivering av den isolerade PoC-API-tjänsten enligt `docs/poc.md`.
Ett förberett paket är inte en aktiverad tjänst; aktiveringskvittot och det
verkliga HTTPS-provet avgör aktuell status.

## Sökning och gränser

`settings/coastal-search.json` styr 250 m world-grid, högst en miljon gridceller,
300 000 expansioner, två kandidater, 128 mellanvägpunkter och 10 m landmarginal.
Gridcellerna är separata från den äldre synlighetsgrafens `max_nodes`.
Varken sökbudget eller marginal kan höjas i klientens begäran. Sökningen får
färre kandidater eller avbrytas; status, expansioner, nodantal, trunkering och
orsak redovisas. Inget globalt snabbaste eller bekvämaste vägval påstås.

Exakta källbundna gridpredikat kan läsas direkt med heltalsnycklar. Stöd
utanför cachen går till samma ursprungliga geometri. Linjeförenkling och
ändpunktsanslutningar använder batcher. Från en strikt vattenpunkt kan en
sammanhängande linje bara lämna komponenten genom dess fullständiga gräns;
hela linjen prövas med samma slutna marginal och mikrometergardering.
Ingen förenkling eller avrundning av frågepositioner införs.

Identiska batchfrågor återanvänds i högst 1 024 poster per vatteninstans.
Alla sökordningar och valda linjer behålls. Referensprov jämför scalar-/batch-/
gridnyckelsökning och drygt 8 000 frågor över hål, landtungor, komponenter,
slutna gränser och marginaler. Ändrad marginal och ogiltiga värden kontrolleras.

Kandidaterna simuleras oberoende med befintlig uppskattad 5 kn-båt,
60 s tidssteg, faktisk gemensam prognosgiltighet och samma absoluta
vädergränser. Ändpunkter på land ger ingen simulerad kandidat. Saknade data,
överskridna gränser och misslyckad ankomst blir inte genomförbara alternativ.
Hög osäkerhet, källposition/tid, avstånd, tidsavvikelse och vattenförbindelse
bevaras för varje berört segment. `weather_limits_verified=false` gäller alltid.

## Verkligt fall och återkörning

Två nysökta färder från de uttryckliga punkterna i
`fixtures/coastal-plan-request.json` nådde mål vid avgång 18 oktober 09:00 UTC:

| Kandidat | Distans | Restid | Syntetisk komfortexponering |
|---|---:|---:|---:|
| water-0 | 88 086,92 m | 34 106,63 s | 3 254,71 |
| water-1 | 89 688,09 m | 34 997,47 s | 3 013,72 |

Komfortmåttet är inte validerat för verkliga båtrörelser. Befintligt komfortval
tillåter 300 s extra restid; den andra kandidaten ligger utanför det intervallet
trots lägre exponering. Båda undersökta alternativen redovisas.

```sh
.venv/bin/python -B -m scripts.plan_coastal \
  /home/web/seaparser/data/vinga-uddevalla-20261018 \
  --request fixtures/coastal-plan-request.json \
  --cache /home/web/seaparser/autonomy/cache/coastal-inputs-v1 \
  --output /tmp/coastal-free-result.json
```

Det första hela jobbet tog 127,22 s. Den bevarade återhämtningskoden tog
86,75 s: 8,20 s inläsning, 18,82 s sökning, 52,73 s motor och 5,43 s
presentation, plus serialisering. Det överskrider 60 s och kvalificerar inte
interaktiv användning. Inget väder- eller landkrav har försvagats för att
försöka klara tiden. Slutlig leveransmätning redovisas i arbetsloggen.

Slutlig kod, delad cacheträff och en native-tråd som den förberedda tjänsten:
80,01 s internt, 89,40 s inklusive processuppstart. Inläsning 15,82 s,
sökning 21,81 s, motor 37,81 s och presentation 3,91 s. Högsta uppmätta
barn-RSS är 550 334 464 byte (cirka 524,8 MiB). Detta klarar varken hela
60 s-budgeten eller befintlig tjänsts 512 MiB-gräns. Resultatfilen är
25 125 746 byte och ryms i 64 MiB.

Alla två färders värden, segment och källposter är byteidentiska med den
ursprungliga fulla beräkningen. Resultatets SHA-256 är
`285318e3e0895bec2d55db6e7ce693c41df8b2128d8ee5946a5d7e953377f9a4`;
indataidentiteten är
`5a4ba8ae24c8691ced3ac6a7ec75c3dc61493cfcc5562baaf4d939647bad8fef`.

## Regionalt API och resursbudgetar 2026-10-19

`POST /api/poc/coastal/plans` tar start, mål, avgång, befintlig uppskattad
5 kn-båt och valda vädergränser. Svaret är 202 med ett jobb-ID. Klienten
visar köad/pågående status och förfluten tid medan status hämtas en gång per
sekund. Slutförda alternativ visar distans, restid, exponering, väder och
källspårbarhet; ruttval och uttryckligt uppskattad GPX använder samma jobb-ID.
Ändrade val tar bort tidigare resultat/GPX och sena svar från gamla val ignoreras.
Punkter utanför uttaget och avgångar utanför gemensam giltighet avvisas före
jobbstart. Land, otillräckligt underlag och vädergränser ger konkreta orsaker,
inte automatiskt godkända alternativ. Dataluckor använder tidigare uttryckliga
landmedvetna reservpolicyer. Hög osäkerhet och overifierade vädergränser består.

`settings/coastal-api.json` skiljer serverbudget från simulerad färdtid:
240 s hård processtid, 255 s klientpollning, 60 s prestandamål.
PoC-tjänstens factory väljer samtidigt den befintliga Vinga-PoC-profilens
60 s/64 MiB-budget; den äldre separata API-tjänsten lämnas oförändrad. Proxyanropen
är korta POST/status/GPX-anrop med befintlig 25 s-gräns; ingen proxyanslutning
hålls öppen under hela beräkningen. Ett regionalt jobb åt gången, inga
överlappande lokala/regionala jobb, två behållna resultat och 900 s TTL.
Äldsta färdiga resultat ersätts när nya jobb behöver plats; äldre GPX-länkar
kan då löpa ut. Processen dödas och inväntas vid timeout/avslut.

Servern rapporterade 4 CPU, 6 206 533 632 B RAM, cirka 1,97 GB tillgängligt,
ingen swap och cirka 75,8 GB ledigt på projektets beständiga disk.
Tjänsten får 1 GiB för API + en beräkningsprocess + behållna resultat,
200 % CPU, 32 tasks och en intern bibliotekstråd. Det tidigare gemensamma
512 MiB-utrymmet var mindre än uppmätt kombinerat behov. Endast den
befintliga gemensamma materialiseringscachen öppnas för tjänstens skrivning;
privat config förblir otillgänglig. Ingen nedladdning görs i ruttanrop.

Resultatpresentationen byggs direkt som ett JSON-träd. Samma steg/ben kopieras
inte igen genom asdict → JSON → parse. Kompakt reservspårbarhet behåller varje
källpost och segment utan en djup kopia av hela trädet; fullresultatets samma
kanoniska hash beräknas strömmande. Geometrins batchfråga söker en närmaste
kustdel inom exakt samma slutna marginal, eftersom endast existens av träff
behövs. Den insamlade kustgeometrin, gräns, gardering och gridpredikat är oförändrade.
Scalar-/batch-/gridreferenser samt hela verkliga referensresultatet jämförs.

Uppmätt referensresultat är fortsatt byteidentiskt: 25 125 746 B, SHA256
`285318e3e0895bec2d55db6e7ce693c41df8b2128d8ee5946a5d7e953377f9a4`.
Geometrisökning separat: 13,24 s med samma kandidater och 60 373 expansioner.
Fullt Vinga–Uddevalla-jobb: 74,46 s internt, 125,65 s inklusive kall
processuppstart och sidinläsning, högsta barn-RSS 495 927 296 B.
Det är mätningar, inte garanterade svarstider.

Ett verkligt ASGI → barnprocess → två färder → GPX-prov med ANDRA fria
vattenpunkter (57,6589945/11,6046274 → 58,3270690/11,8562959) tog 63,30 s
med gemensam cacheträff. API-processens högsta RSS var 102 965 248 B och
barnets 486 973 440 B; summan 589 938 688 B är ett konservativt kombinerat
övre mått eftersom topparna inte behöver vara samtidiga. Hälsokontroll tog
0,0044 s under jobbet; en andra samtidig begäran fick 429. Båda färder och
självbärande GPX kontrollerades. Kompakt JSON-resultat: 2 538 795 B.
Referensens större resultat ryms fortfarande i oförändrad 64 MiB-budget.

Publiceringsprovet i `frontend/tests/poc-live.test.mjs` kan även köras mot
aktiverad HTTPS med `SEAPARSER_COASTAL_PUBLIC_TEST=1`. Det är ett separat
verifieringssteg från lokala ASGI-/DOM-prov och rapporteras som sådant.
