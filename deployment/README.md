# Godkänd aktivering – root-steg återstår

Användaren godkände offentlig syntetisk kartdemo, systemtjänst och /api/-proxy.
Filrättigheter, TLS, privata inställningar och databas får inte ändras.

Verifierat före aktivering: 8765 ledig, Apache proxy/proxy_http saknas som laddade
moduler men deras moduldefinitioner finns. Systemtjänsten är inte installerad.
Befintlig HTTPS-visning ger 200; tidigare 403 är löst. MIME för .mjs är javascript.

Backup: /home/web/seaparser/backups/activation-20261012-c6b0b4f/
- apache-before.conf och public-before/ är innehållsverifierade säkerhetskopior.
- frontend-ready/ innehåller endast 14 genererade publika frontendfiler.
- apache-ready.conf ändrar bara en Include-rad i SeaParsers HTTPS-vhost.
- originals.sha256 stoppar körning om ursprunglig konfiguration/index har ändrats.
- manifest.json redovisar filhashar. Inga privata inställningar/nycklar kopierades.

13 publika resurser är utlagda av seaparser; gamla index.html är fortfarande kvar.
Aktiveringsskriptet ersätter index sist, efter fungerande tjänst och publik proxy.
Ingen systemkonfiguration, tjänst eller TLS har ändrats av agenten.

## Exakt root-kommando

```
/usr/bin/bash /home/web/seaparser/app/deployment/activate-demo.sh
```

Granska skriptet först. Det kontrollerar UID/ledig port/backups och att unit/proxyfil
inte redan finns. Alla fil- och programvägar är absoluta. Det aktiverar endast
proxy/proxy_http, kopierar den minimalt ändrade vhosten och tjänsten, kör configtest
före reload och verifierar aktiv systemtjänst, lokal health och publik health.
Index kopieras sedan och HTTP/DOM-helhetsprovet körs som seaparser mot
https://seaparser.com/: faktiskt serverade frontendfiler jämförs bytevis med build,
kartklick ger API-jobb, Leaflet-rutter och hämtad GPX. Detta är inte en visuell
browseraudit. Vid fel efter ändringsstart återställs Apache/index och API stoppas.
Ingen chmod/chown, sudo, privat konfiguration, TLS-ändring eller DB-operation ingår.

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
