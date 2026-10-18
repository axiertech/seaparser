# Regionala fria punkter och två verkligt simulerade vägval

`application/coastal_plan.py::plan_coastal` tar uttryckliga WGS84-punkter och
tidszonsangiven avgång. Samma materialisering, CF-/MET-normalisering,
landmedvetna variabelpolicyer och färdmotor återanvänds. Inga data hämtas under
sökning eller simulering. Den bevarade Vinga–Uddevalla-bunten används direkt.

Detta är en fungerande offlinekomposition. Den regionala API-/UI-kopplingen
är ännu inte aktiverad eller kvalificerad för 60 s. Budgetfält i rapporten är
konfigurerade gränser, inte bevis för uppnådd interaktiv latens.

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

PROJECT_BLOCKER: interaktiv användning kräver ytterligare minskad total tid
och minne. Nästa konkreta optimering är presentationens kvarvarande fulla
dataclass-/JSON-kopior och geometrisökningens batchkostnad; därefter mäts
hela killbara API-jobbet och fria andra punkter innan aktivering.
