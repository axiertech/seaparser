# PoC-logotyp och favicon

Grafikbranch: `development/poc-branding`, separat worktree
`/tmp/seaparser-poc-graphics`. Ingen beräkningslogik ändras.

Uppladdade filer hittades under
`/home/web/seaparser/worktrees/development/frontend/assets/logos/`:

- `seaparser-logo.svg` – används i PoC-sidhuvudet, oförändrad 206:78-proportion.
- `seaparser_logo.png` – originalet bevaras på uppladdningsplatsen.
- `favicon.ico` – flerstorleksikon för webbläsaren.
- `favicon-256.png` – alternativ PNG-favicon, 256 × 256.

Sidhuvudets SVG visas 180 px bred på desktop och 132 px vid högst 700 px
skärmbredd, med automatisk höjd. Alternativtext: SeaParser. Rubriken är
”SeaParser, ruttplanering för OffShore”. Sidans befintliga datadatum,
osäkerhetsbesked, kartkontroller och ruttfunktioner är kvar.

Både fullbygge och `scripts.build_poc --presentation-only` kopierar exakt
tre utvalda publika resurser under deras faktiska filnamn. De ingår i
byggkvittots SHA-256-lista och den explicita publiceringslistan. Inget
helt `frontend/assets/`-träd publiceras automatiskt.

## Samordnad publicering

Denna grafikleverans publiceras inte från en äldre prognosbank medan
autonomipasset arbetar. Vid dess nästa färdiga leveransgräns integreras
källändringarna på aktuell arbetsbranch. Ta inte med grafikbranchens äldre
genererade `artifacts/poc-site/` till den aktiva branchen. Med rent index och
granskade aktuella ändringar kan källpatchen hämtas så här:

```sh
git fetch origin development/poc-branding
git diff --binary 7d709246f3291fc93013e1b0e8f850563f93b441 origin/development/poc-branding -- frontend/assets/logos frontend/poc/index.html frontend/poc/poc.css frontend/tests/poc.test.mjs scripts/build_poc.py deployment/poc.py | git apply --3way --index
.venv/bin/python -B -m scripts.build_poc --presentation-only
```

Eventuella källkonflikter granskas; inga nya funktioner skrivs över.
Presentationsbygget kontrollerar och behåller den då aktuella prognosbanken,
uppdaterar dess presentationsfiler och skapar ett nytt hashkvitto.
Kör relevanta tester och skapa en granskad integrerad commit före befintlig
`deployment.poc prepare/verify/publish`, med ny rollbackstage och exakt CI.
Den integrerade publiceringscommitten använder `[verify-poc-public]` efter
publicering så befintlig CI kontrollerar alla aktuella resurser över HTTPS.

Grafikbranchens egna byggfiler och CI visar att presentationen är förberedd;
de är inte ett kvitto på ändrad publik webb. Inga tjänster eller API behöver
aktiveras för logotyp, favicon eller rubrik.

Vid publicering från grafikworktreet måste alla resurser utanför `index.html`,
`poc.css` och de tre namngivna grafikfilerna först matcha den aktuella publika
versionens hashvärden. Avbryt vid skillnader och integrera mot den nya versionen.
Det befintliga publiceringsflödets kontroll av hela publika trädet mellan
förberedelse och aktivering skyddar också mot en samtidig ny leverans.
Efteråt måste autonomipassets kommande PoC-byggen ta in källpatchen ovan så att
nya prognosleveranser behåller sidhuvud och favicon. Faktiskt publiceringskvitto,
återställning och samordningsstatus finns i `autonomy/poc-branding-handoff.md`
under `/home/web/seaparser`.
