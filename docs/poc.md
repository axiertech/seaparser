# SeaParser PoC vid Vinga

Mål: ett sammanhängande användarflöde med verkliga frysta prognoser och befintlig
ruttmotor. Start/mål, avgång, befintlig uppskattad 5-knopsprofil, vädergränser,
snabbaste/bekvämaste funna alternativ, karta, distans/väder och GPX finns tillsammans.
Layout ligger i `frontend/poc/`; gemensam kart-/formlogik i `frontend/map/`.

## Publicerad avgränsning

Den installerade API-tjänsten är en äldre release och ändras inte av statisk
publicering. `/poc/` kan därför använda ett uttryckligt förberäknat urval: tre
markerade vattenpunkter, sex riktningar, fyra frysta avgångar den 17 oktober 2026,
tre vädergränsval. Alla 18 fall är faktiskt beräknade med den befintliga motorn,
fyra kandidater per avgång, projekterad fysisk rörelse, 24 landpolygoner och
900 m datastöd. Ingen beräkning eller väderimputation sker i webbläsaren.
Det strikta vågvalet visar avvisade alternativ utan GPX. Både snabbaste och
bekvämaste kan vara samma alternativ; inga påhittade skillnader visas.

Gränssnittet använder live-API endast om `/api/scene?profile=vinga-poc` faktiskt
stöder profilen och fysisk rörelseram. Då går även fria punkter inom stödet att
beräkna, med befintliga budgetar (20 s, 16 kombinationer). Aktivering av en ny
systemtjänstrelease kräver separat hantering av befintligt administratörsflöde.
Den publicerade katalogen ger inte obegränsad liveplanering.

Historiska MET/Copernicus-data är verkliga, men metadataantaganden i
`settings/development-weather-projected-assumptions.json` är inte källbevis.
Utfärdande, prognoskörningarnas förenlighet, ramar/masker/tidssemantik och
båtmodell redovisas utfällbart. Land-/datastöd-/värde-/vädergränser består.
Djup och navigerbarhet är inte kvalificerade. GPX innehåller planerade waypoints.

## Bygg, publicera och återställ

Kör som seaparser i `/tmp/seaparser-real-map-data`:

```sh
.venv/bin/python -B -m scripts.build_poc
```

Detta gör inga nätuttag och skriver inte publikt. `artifacts/poc-site/` har en
hashad fillista. Publiceringen återanvänder befintliga atomiska kopior och
backupkontroller, men är begränsad till `/poc/`; tidigare sidor bevaras.
Efter granskad ren commit, använd en ny stagekatalog för varje publicering:

```sh
.venv/bin/python -B -m deployment.poc prepare /home/web/seaparser/backups/poc-STAGE
.venv/bin/python -B -m deployment.poc verify /home/web/seaparser/backups/poc-STAGE
.venv/bin/python -B -m deployment.poc publish /home/web/seaparser/backups/poc-STAGE
```

URL: `https://seaparser.com/poc/`. Endast tillåtna statiska resurser kopieras;
byggkvitto, konfiguration, sessionsfiler och hemligheter ingår inte.
Återställ med samma stage utan att återställa projektfiler:

```sh
.venv/bin/python -B -m deployment.poc rollback /home/web/seaparser/backups/poc-STAGE
```

Kontrollera efteråt HTTPS, script/CSS, katalog, ett ruttresultat och dess GPX mot
byggkvitto. Ett publiceringskvitto med `https_verified=false` är inte extern
HTTPS-verifiering. Körmiljön kan blockera nätverkssocketar; CI eller vanlig
SSH-terminal behövs då för den externa kontrollen.

Den uttryckliga publiceringscommitens meddelande innehåller `[verify-poc-public]`.
Då avslutar befintlig CI med en skrivskyddad HTTPS-kontroll av samtliga 228
publicerade filer mot exakt commits byggkvitto. Det möjliggör extern kontroll
när den lokala körmiljön förbjuder socketar. Publicera det granskade statiska
underlaget före denna push; vid CI-fel finns den avgränsade återställningen ovan.
Andra commits får inget generellt beroende på den publika servern.
