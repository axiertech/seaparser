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

Databasskapande, databasanslutningar, migrationer mot databas, ändringar av
serverns anslutningsregler och privata konfigurationsfiler kräver separat
uttryckligt godkännande. Push, publicering och nya betalda resurser ingår inte.
Uppdatera arbetsloggen med aktuell uppgift, verifierat resultat och nästa steg.
Mandatet gäller arbete i aktiva sessioner, inte fristående bakgrundsaktivitet.
