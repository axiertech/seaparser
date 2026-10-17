# Godkänd aktivering – root-steg återstår

Användaren godkände offentlig syntetisk kartdemo, systemtjänst och /api/-proxy.
Filrättigheter, TLS, privata inställningar och databas får inte ändras.

Verifierat före aktivering: Tjänst-/proxyfiler från tidigare försök finns och är byteidentiska
med deploymentens sparade underlag. De återanvänds utan omskrivning vid retry.
Befintlig HTTPS-visning ger 200; tidigare 403 är löst. MIME för .mjs är javascript.

Backup: /home/web/seaparser/backups/activation-retry-20261012-81522f7/
- apache-before.conf och public-before/ är innehållsverifierade säkerhetskopior.
- frontend-ready/ innehåller endast 14 genererade publika frontendfiler.
- apache-ready.conf ändrar bara en Include-rad i SeaParsers HTTPS-vhost.
- originals.sha256 stoppar körning om ursprunglig konfiguration/index har ändrats.
- manifest.json redovisar filhashar. Inga privata inställningar/nycklar kopierades.

13 publika resurser är utlagda av seaparser; gamla index.html är fortfarande kvar.
Retry-backupen bygger på användarens nu korrigerade Apache-konfiguration:
AllowOverride None, hela hemmakatalogen nekas, endast public/ tillåts. Den gamla
snapshoten med andra Directory-regler används aldrig för retry eller rollback.
Aktiveringsskriptet ersätter index sist, efter fungerande tjänst och publik proxy.
Ingen systemkonfiguration, tjänst eller TLS har ändrats av agenten.

## Exakt root-kommando

```
/usr/bin/bash /home/web/seaparser/app/deployment/activate-demo.sh
```

Granska skriptet först. Det kontrollerar UID/ledig port/backups och att befintliga unit-/proxyfiler är vanliga filer med exakt verifierat
deploymentinnehåll och rootägare (UID0). Snapshotens deploymentidentitet och
SHA-256-kvitto verifieras före återanvändning. Avvikande filer och symlänkar stoppar före systemändringar. Alla fil- och programvägar är absoluta. Det aktiverar endast
proxy/proxy_http, kopierar den minimalt ändrade vhosten och tjänsten, kör configtest
före reload och verifierar aktiv systemtjänst, lokal health och publik health.
Index kopieras sedan och HTTP/DOM-helhetsprovet körs som seaparser mot
https://seaparser.com/: faktiskt serverade frontendfiler jämförs bytevis med build,
kartklick ger API-jobb, Leaflet-rutter och hämtad GPX. Detta är inte en visuell
browseraudit. Vid fel efter ändringsstart återställs Apache/index och API stoppas.
Ingen chmod/chown, sudo, privat konfiguration, TLS-ändring eller DB-operation ingår.

## Node EACCES: körkontext

Exakta runuser-kommandot kräver root och kan inte köras direkt som seaparser.
Dess exakta Node-del startar alla tester från repositoryt utan EACCES; offentlig
indexkontroll underkänns korrekt före återaktivering eftersom statiska sidan är kvar.
Node v22.22.1:s testkörare spawnar barnet med explicit cwd=process.cwd().
Separat probe ger spawn EACCES vid cwd=/root men version22.22.1 vid ärvd cwd
och cwd=/home/web/seaparser/app. Node-rättigheter är alltså inte ändrade.
I agentens användarkontext är UID1000, execPath=/usr/bin/node och NODE_OPTIONS/
NODE_PATH frånvarande; inga miljövärden eller privata inställningar dumpas.
Root-försökets verkliga startkatalog loggas nästa gång, därefter explicit cd till
repositoryt och kontextprobe som seaparser. Hela node --test med standardisolering
körs fortfarande; ingen flagga kringgår test eller processisolering.

## Återställning som root

```
/usr/bin/bash /home/web/seaparser/app/deployment/rollback-demo.sh
```

Återställer Apache-konfiguration och index från backup, kör configtest före reload,
stoppar/inaktiverar API och verifierar ursprungliga filhashar. Nya, orefererade
resurser och inaktiva installerade filer lämnas kvar; inga andra filer raderas.
Proxy-moduler avaktiveras inte globalt på delad Apache. Skriptet är inte en
återställning av andra administratörsändringar efter denna snapshot.

Tjänsten har en webbprocess, 2 samtidiga killbara jobbprocesser, 20 s/job,
8 jobb/300 s retention. Den binder endast 127.0.0.1:8765 och läser inte app.env.
API är offentligt med syntetiska data; jobb-id är inte autentisering. Globala
budgetar ersätter inte framtida perklient-/ingresskontroll. Omstart tappar jobb.

Publikt indexprov ska underkännas före aktivering: rollback har korrekt återställt
statiska sidan. Inga förväntade frontendbytes ändras. Fullt HTTPS-kart/API/GPX-prov
körs automatiskt först efter fungerande API/proxy och byte till nya index.html.


## Separat fryst prognosgranskning (ingen demo-/tjänsteuppgradering)

Se [vinga-frozen-review.md](../docs/vinga-frozen-review.md).
`python3 -B -m deployment.frozen_review prepare|verify|publish STAGE` är en
avgränsad tilläggsväg i befintligt atomiskt Vinga-publiceringsflöde. Endast
nya /vinga-prognosprov.html tillåts. Förberedelse/verify ändrar inget publikt;
publish är ett separat uttryckligt steg som seaparser. Använd inte root-
aktiveringsflödena ovan för denna fristående statiska granskningssida.
