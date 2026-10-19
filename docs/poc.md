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

## Fria kartklick och aktivering av befintligt API

Fria WGS84-punkter inom markerad 900 m-täckning använder samma beräkning,
ruttjämförelse och GPX. Egna punkter visas som sådana i formuläret. Punkter
utanför stödet eller avgångar utan tillgängliga tidsval ger tydliga besked;
land, hårda vädergränser och beräkningsbudgetar är oförändrade.

Den installerade systemd-tjänsten kör en äldre release och annan låsfil.
`deployment.poc_api` förbereder en separat arkiverad commit i `releases/poc-SHA`,
bevarar den befintliga tjänsten och använder en separat beständig miljö i
`venvs/poc-0928bea0ada2` med verifierade låsta versioner. Miljön återanvänds från
den redan verifierade arbetsmiljön med samma låsfil. Den äldre API-miljön bevaras. Vetenskapliga
bibliotek begränsas till en intern tråd så tjänstens befintliga processgräns
behålls. Inga paket installeras globalt. Befintlig API-tjänst, TLS, DocumentRoot, databas och tidigare publika filer
ändras inte. Två proxyregler för `/api/poc/` läggs före befintliga `/api/`-regler;
PoC-tjänsten lyssnar separat på localhost:8766.

Efter granskad ren commit, publicering av avsedda PoC-resurser och verifierad CI:

```sh
.venv/bin/python -B -m deployment.poc_api prepare /home/web/seaparser/backups/poc-live-api-20261017
```

Exakt CI-kvitto (`ci-success.json`) måste därefter finnas i stage innan aktivering.
Kör som **root i vanlig SSH-terminal** (inte som seaparser):

```sh
/bin/bash /home/web/seaparser/backups/poc-live-api-20261017/activate.sh
```

Kommandot tar gemensamt lås, kontrollerar commit/renhet, release, miljö och
befintlig tjänst, startar en separat PoC-tjänst med granskad kod-/Python-sökväg och trådgränser,
laddar om proxyreglerna och kör samma riktiga kartklick/API/jämförelse/GPX-prov som CI,
nu mot `https://seaparser.com/poc/`. Fel efter aktiveringen stoppar PoC-tjänsten och återställer tidigare
proxyregler automatiskt; den äldre API-processen startas inte om och inga offentliga filer behöver återställas av API-steget.
Kvitto `activation-success.json` skapas först när det publika flödet passerat.
Förberedd release är inte en aktiverad tjänst. Manuell API-återställning:

```sh
/bin/bash /home/web/seaparser/backups/poc-live-api-20261017/activate.sh --rollback
```


Regionala fria punkter använder samma isolerade PoC-API efter aktivering.
Se `coastal-free-planning.md` för uppmätta resurser och `settings/coastal-api.json`:
60 s är ett mål, 240 s är processgräns, statuspollning får 255 s och proxyns
25 s gäller varje kort HTTP-anrop. En regional beräkning åt gången och 1 GiB
för API + barnprocess + resultat. Endast den gemensamma befintliga cachen är
skrivbar utanför tjänstens privata temporärkatalog. Aktiveringens HTTPS-prov
kontrollerar både befintliga Vinga-flödet och regionala fria kartpunkter/GPX.
Exakt förberedd release och root-kommando redovisas i aktuell överlämning;
återanvänd inte äldre aktiveringspaket med inaktuell commit/låsfil.

Aktiveringsreparation 2026-10-19: det tidigare provets fasta 30 s väntan
avbröt klienten före Vinga-jobbets 60 s processgräns. Serverjobbet fortsatte
och kunde därför blockera nästa regionala prov. Proven väntar nu på
klientens verkliga slutförande med serverns annonserade pollbudget (70 s
Vinga, 255 s regionalt), med bibehållna resultat- och GPX-assertions.
Vid avbrott används DELETE på jobbets statusadress. API:t svarar först efter
att barnprocessen har avslutats och reapats; UI och test väntar på städningen
före nästa jobb/DOM-stängning. Sena svar får inte skriva till stängd DOM.
Health redovisar aktiva lokala/regionala jobb, och varje prov kräver tom kapacitet.

Återställning stoppar PoC-tjänsten innan unit-filen tas bort, återställer
proxy, kör daemon-reload och kontrollerar både filhashar och systemd-manager
(not-found, inaktiv, PID 0), tom PoC-cgroup och port 8766 utan lyssnare.
Äldre API-health och Apache-omladdning måste också lyckas innan ett nytt
rollback-success.json skrivs. activation.log innehåller hela aktiveringsflödet;
restoration-check.json skiljer verifierad återställning från enbart återställda filer.
Samma återställningskontroll körs före en ny aktivering. Ingen root-aktivering
utförs från den hanterade utvecklingsmiljön.
