# Förberedd deployment – inte aktiverad

Filerna är granskbara förslag. Ingen systemkonfiguration, systemtjänst, TLS,
åtkomsträttighet, databasmigration eller offentlig API-publicering har utförts.
Appen läser inte privat app.env och använder ingen databas.

Lokalt (endast 127.0.0.1): `.venv/bin/python -B -m uvicorn api.main:app --host 127.0.0.1 --port 8765 --workers 1`.
`npm --prefix frontend run build` skapar bara publika filer i frontend/dist.
För lokal helhetsvisning kan `scripts.local_demo` serva dessa bakom samma
loopback-origin; detta är inte Apache-deployment. Stoppa processen efter granskning.

## Samlat underlag för administratörens godkännande

1. Kontrollera att port 8765 är ledig och att HTTPS-vhosten har mod_proxy och
   mod_proxy_http: `apache2ctl -M`, `ss -ltn sport = :8765`.
2. Installera deployment/seaparser-api.service som
   /etc/systemd/system/seaparser-api.service och inkludera apache-api.conf i
   befintlig HTTPS-vhost. Proxy endast /api/ till 127.0.0.1; befintlig
   DocumentRoot /home/web/seaparser/public och TLS lämnas oförändrade.
3. Offentlig API-åtkomst (Require all granted) kräver uttryckligt godkännande.
   Detta är en syntetisk demo utan inloggning: jobb-id är inte autentisering.
   För känsliga eller riktiga användardata behövs separat identitet/åtkomstpolicy.
4. Publicera endast frontend/dist:s uttryckliga filer (index.html, map.css,
   fyra .mjs-filer och vendor/Leaflet-resurser/licens). Inget repository,
   node_modules, Python, konfiguration eller loggar i webbroten. Befintlig
   statisk demonstration ersätts först efter godkännande av denna nya visning.
5. Tidigare HTTPS-kontroll gav 403. Kontrollera Apache-användarens åtkomst till
   /home/web/seaparser/public/index.html. Föräldern seaparser är 750; ingen
   rättighet har ändrats. Administratören får utreda och välja minimal läs-/
   traverseringsåtkomst för just webbfilerna; ge inte åtkomst till config/ eller app/.
6. Efter godkännande och installation: `systemctl daemon-reload`,
   `systemctl enable --now seaparser-api`, `apache2ctl configtest`,
   `systemctl reload apache2`. Kör bara reload efter godkänt configtest.
   Verifiera lokalt /api/health och externt HTTPS/kartklick/beräkning/GPX.

Tjänsten har en webbprocess och högst två samtidiga separata beräkningsprocesser,
20 s tidsgräns/job, 8 jobb i minnet och 5 min retention räknad från skapandet.
Backend avvisar stora kroppar och obegränsade scenarier/sökparametrar. Globala
budgetar är inte ersättning för framtida ingress-/perklient-begränsning eller
autentisering. Inget hållbart jobbarkiv; omstart tappar jobb. MemoryMax/CPUQuota
är systemgränser att verifiera på servern, inte ett prestandalöfte.

Rollback: stoppa/inaktivera tjänsten, ta bort endast API-proxyinkluderingen,
configtest/reload och återställ tidigare publika frontendfiler från verifierad
export. Ingen databasrollback behövs. Kör inget ovan automatiskt.
