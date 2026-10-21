# Arbetsinstruktioner

## Projekt och behörigheter

Arbeta bara med SeaParser och repositoryt `axiertech/seaparser`. Projektet är fristående från Splitgrid.

På servern ligger koden i `/home/web/seaparser/app`. Använd Linux-användaren `seaparser`, utan sudo. Privata inställningar ligger i `/home/web/seaparser/config/app.env`.

Läs krav, arkitektur och beslutslogg innan ändringar. Dokumentera antaganden. Skapa inte nya betalda resurser, publicera inte och pusha inte till GitHub utan användarens godkännande. Förbered först en konkret ändring med relevant verifiering. Ge aldrig sken av att en operation är utförd om den inte verifierats.

## Hemligheter

Skriv inte ut konfigurationsfilen, lösenord, API-nycklar, privata SSH-nycklar eller autentiseringstoken. Ta inte med dem i Git, dokumentation, terminalutskrifter eller testdata. Kontrollera anslutning utan att logga anslutningssträngar. Läs bara nödvändiga konfigurationsvärden i programmet.

## Arkitektur och kvalitet

Håll layout, API, applikationslogik, domän och infrastrukturlager separerade. Ruttmotorn får inte göra SQL-anrop, HTTP-anrop eller innehålla UI-logik. Använd abstraktioner för väderdata och båtprestanda där de gör komponenter utbytbara. Undvik tomma lager och förtida mikrotjänster.

Designern ska kunna ändra befintliga sidors layout och tema visuellt utan kod. React och CSS ensamma uppfyller inte kravet. Välj inte visuell editor innan egna komponenter, responsivitet, versionshantering, export, licens och kostnad har utvärderats.

Verifiera aktuella officiella biblioteksversioner före installation. Versionsstyr beroenden med låsfiler. Databasändringar ska ha migrationer. Skriv tester som kontrollerar krav och kända resultat, inte bara speglar implementationen.

Okända eller gamla prognoser får inte behandlas som säkra. Landmask är inte bevis på navigerbarhet. Absoluta gränser får inte vägas bort av komfortpoäng eller tidsvinst. Märk uppskattade båtdata tydligt.

## Arbetssätt

Planera nästa begränsade leverans, implementera, verifiera och redovisa resultat samt kvarvarande osäkerhet. Ingen självgående bakgrundsaktivitet eller serveråtkomst från en annan chatt ska förutsättas.

Rekommendera starkare eller annan AI-modell när en konkret uppgift motiverar det. Ange förväntad nytta och verifierad kostnad om tillgänglig. Byt inte modell eller köp tjänster automatiskt. AI-modeller ersätter inte tester eller maritim sakkunnig validering.

## Godkänt utvecklingsmandat 2026-10-12

Agenten får självständigt ändra SeaParsers projektfiler, köra tester och
lokala offlinekontroller samt göra lokala commits av egna granskade ändringar.
Bevara andra lokala ändringar; använd aldrig generell staging som tar med dem.

Agenten får skapa projektets .venv och installera projektberoenden där samt
köra npm ci med repositoryts låsfil i frontend/. Använd officiella paketregister
(PyPI och npm), verifiera officiella versioner före nya paketinstallationer och
versionsstyr exakta beroenden med låsfiler. Installera inte globalt, ändra inte
systempaket och använd inte sudo. Om systemstöd saknas: redovisa hindret.

Skrivskyddad databasdiagnostik med projektrollen och privat konfiguration är
godkänd. Använd endast databas och roll seaparser, aldrig administratörsuppgifter.
Projektet har en utvecklingsmiljö; separat testdatabas/testroll eller testlösenord
ska inte krävas eller skapas. Enhetstester körs utan databas. Databastester får
aldrig tömma befintliga tabeller: använd rollback och testegna objekt, utan
ändringar av befintliga rader, sekvenser eller externa sidoeffekter.
Inför drift ska miljön separeras och en ny driftroll skapas med minsta rättigheter.

Databasskapande, migrationer mot databas, ändringar av
serverns anslutningsregler och privata konfigurationsfiler kräver separat
uttryckligt godkännande. Publicering och nya betalda resurser ingår inte.
Push omfattas endast av arbetsbranchmandatet nedan.
Uppdatera arbetsloggen med aktuell uppgift, verifierat resultat och nästa steg.
Mandatet gäller arbete i aktiva sessioner, inte fristående bakgrundsaktivitet.

## Godkänt arbetsbranchmandat 2026-10-12

Agenten får självständigt pusha granskade lokala commits till
`axiertech/seaparser` på en arbetsbranch under `development/`.
Kör alla relevanta tester och kontroller före push. Granska commitinnehållet
så att inga hemligheter eller orelaterade ändringar ingår; bevara andra lokala
ändringar ostagade. Kontrollera GitHub CI efter push och rapportera branch,
commit-id och verifierat resultat.

Force-push, radering av branches och merge till main kräver användarens
uttryckliga godkännande. Mandatet ändrar inte databasbehörigheter eller
övriga begränsningar och gäller arbete i aktiva sessioner.

## Sammanhängande backlogarbete 2026-10-12

Fortsätt självständigt genom projektets dokumenterade backlog i aktiva sessioner.
För varje del: implementera, granska diffen, kör relevanta tester och kontroller,
uppdatera status, skapa commit och pusha till en development/-branch enligt
arbetsbranchmandatet. Kontrollera GitHub CI för exakt commit och rätta fel innan
nästa del. Fortsätt med nästa rimliga uppgift när kontrollerna passerar; stanna
inte för godkännande mellan redan auktoriserade deluppgifter.

Redovisa samlat efter en större sammanhängande leverans eller när ett verkligt
hinder kräver användarens beslut. Fråga vid nya kostnader, utökade behörigheter,
destruktiva databasändringar eller produktbeslut som väsentligt ändrar omfattning.
Befintligt installations-/databasmandat gäller oförändrat; merge till main,
force-push och branchradering kräver fortfarande uttryckligt godkännande.
Bevara orelaterade lokala ändringar och undvik generell staging. Ingen
fristående bakgrundsaktivitet följer av detta arbetssätt.

## Usage-styrning

Automatiska gränser vid 5 % och 1 % är **inte implementerade**. Använd i
stället en uttrycklig tidsgräns och avgränsade arbetsuppgifter. Spara en kort
överlämning efter varje sammanhängande leverans. Vid `usage_exhausted` ska inga
nya modellanrop göras; skriv en lokal slutrapport med Git-status och senast
verifierade kontroller utifrån redan tillgängligt resultat. Återställ inte kvot
och byt inte modell automatiskt.

Använd inte uppskattad tokenförbrukning som kontokvot. Den installerade Codex
CLI:n exponerar via app-serverns JSON-RPC det dokumenterade
`account/rateLimits/read`-anropet, inklusive `usedPercent` när tjänsten lämnar
det. Detta innebär inte att 5/1-procentsautomation är implementerad eller att
kontokvot är tillgänglig i varje körmiljö. JSON-utdata från andra kommandon är
inte kvotdata utan dokumenterat stöd.

## Code style (2026-10-21)

Two rules apply to all new Python code in SeaParser and `~/autonomy`:

### 1. Prefer module-level functions over nested closures

PEP 8 and general Python practice favour module-level functions because
they are testable in isolation, discoverable, and reusable. Use a nested
function or closure only when:

- the nested function captures loop variables that would otherwise be
  rebound (late binding in `for` loops), or
- it is a decorator, or
- it is a one-line helper used at exactly one call site and the closure
  genuinely improves readability.

Never use a nested function to avoid thinking about module structure. If
a helper is used in two places, or is longer than ~10 lines, move it to
module level.

### 2. Every function and method has a docstring

Use a one-line docstring for simple functions and a multi-line docstring
(Args / Returns / Raises) for anything non-obvious. Classes and modules
get docstrings too. Inline comments are for "why"; docstrings are for
"what".

The reviewer (`application/deepseek_review.py`) treats a missing
docstring on a new or changed function as a `warning` finding, and a
nested function that could be moved to module level as a `nit`.
