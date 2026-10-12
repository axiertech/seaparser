# Godkänd publicering: Vinga-land och syntetiskt väder

Användaren har godkänt offentlig publicering. Ny startsida blir Vinga med verkligt
fryst OSM-land, konservativa höljen och tydligt syntetiskt väder. Den tidigare
syntetiska demonstrationen förblir åtkomlig på `/synthetic.html`; Vinga finns även
på `/vinga.html`. Verkliga prognosreferenser kopplas inte till API eller UI.

Fortsätt använda befintlig systemtjänst/proxy med innehålls- och ägarskapskontroll.
Apache-vhost, proxy, korrigerade Directory-block, TLS och privata filer ändras
inte. Inga moduler aktiveras; redan aktiva proxy/proxy_http måste verifieras.
Port 8765 måste tillhöra befintlig seaparser-api.service, inte vara ledig.
Systemtjänstens WorkingDirectory ändras till en separat verifierad release i
`/home/web/seaparser/releases/vinga-<commit>`, som återanvänder befintlig exakt
låst Pythonmiljö. Aktiva checkouten och tidigare lokala ändringar bevaras.

## Förberedelse som seaparser

Efter granskad ren commit, tester och CI:

```
cd /tmp/seaparser-real-map-data
make land-preview
/home/web/seaparser/app/.venv/bin/python -B -m deployment.prepare_vinga /tmp/seaparser-vinga-publication
```

Förberedelsen arkiverar endast Git-tracked releasekod, aldrig `.git`, privat
konfiguration eller ignorerade nycklar/loggar. Webbpaktetet är separat allowlist:
20 publika frontend-/licens-/kartdatafiler. Manifestet registrerar källcommit,
releaseinnehåll, föregående publicering, tjänst-/Apachehashar och filattribut.
Ingen publicering eller systemändring görs i förberedelsesteget.

## Exakt root-kommando

```
/usr/bin/bash /tmp/seaparser-real-map-data/deployment/activate-vinga.sh /tmp/seaparser-vinga-publication
```

Rootflödet kontrollerar ren rätt commit, oförändrat förberett innehåll och aktuell
publicering/systemkonfiguration samt portens ägare och Apache-moduler. Configtest
körs före ändringar och efter publicering; Apache behöver ingen reload eftersom
konfigurationen är oförändrad. Backup skapas och innehållsverifieras i
`/home/web/seaparser/backups/vinga-<commit>` före någon ändring. Befintlig exakt
backup/release kan återanvändas efter rollback; avvikande innehåll stoppar.

Release installeras utan att skriva över befintlig avvikande release. Root kopierar
verifierad tjänstfil, kör daemon-reload/restart, is-active och lokal health.
Publika filer byts atomiskt som seaparser; ägare/grupp/mode måste matcha tidigare
fil eller normal ny publik fil (1000/1000/0644). Ingen rättighetsändring används
för att korrigera avvikelse. Index byts sist. Backupens tidigare index är en
fullt fungerande syntetisk sida, inte den äldre statiska rollback-sidan.

Hela Node/HTTP/DOM-provet körs som seaparser från explicit läsbar projektkatalog
mot HTTPS, med båda profilerna. Filer jämförs bytevis, kartklick ger API-jobb,
omväg/ankomst/marginal/GPX visas; väderöverskridande och missing-waves avvisas utan
export. Inga tiles hämtas i automatiska testet. Aktiv processs cwd verifieras mot
release, publiceringsfiler och oförändrad Apache kontrolleras; först därefter
skrivs activation-success.json med commit och verifieringsstatus i backupen.
Detta är DOM-/HTTP-verifiering; manuell visuell granskning är separat.

## Återställning

```
/usr/bin/bash /tmp/seaparser-real-map-data/deployment/rollback-vinga.sh /tmp/seaparser-vinga-publication
```

Vid aktiveringsfel försöker samma återställning automatiskt. Tidigare publika
bytes och filattribut återställs atomiskt, verifierat nyskapade egna filer tas
bort, tidigare tjänstfil återläggs och tidigare API startas. Apache återställs
inte över administratörsändringar: dess vhost/proxy har inte ändrats av flödet.
Avvikande nya filer stoppar borttagning. Release/backup raderas inte.

Agenten kör som UID1000 utan sudo; root-steget kan därför inte utföras i den
aktiva agentmiljön. Ny offentlig commit och HTTPS-resultat får inte påstås före
rootsteget och godkända verifieringar. Backupens activation-success.json och
systemd WorkingDirectory identifierar publicerad commit.
