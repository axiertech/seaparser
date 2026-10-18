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
