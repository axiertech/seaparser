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
