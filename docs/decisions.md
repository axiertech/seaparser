# Beslutslogg

## Bekräftat 2026-10-11

- Privat projekt hos axiertech, fristående från Splitgrid.
- Repository: `axiertech/seaparser`.
- Hemmakatalog: `/home/web/seaparser`; kod: `app/`; privat konfiguration: `config/app.env`.
- Linux-användaren seaparser saknar sudo. Config-katalog har 700 och filen 600.
- Ubuntu 26.04.1 LTS, Git 2.53.0, Node.js 22.22.1, npm 9.2.0 och Codex CLI 0.162.1 har rapporterats.
- Codex-inloggning med ChatGPT samt SSH-kloning av repositoryt har lyckats.
- PostGIS rapporteras aktivt. Databasanslutning behöver verifieras efter ändrade namnuppgifter.
- Kod, layout, konfiguration och databasåtkomst ska separeras.
- Designer ska kunna ändra befintlig layout visuellt utan programmerare.
- Modellbehov utvärderas veckovis och under aktivt arbete vid behov. Dyrare alternativ rekommenderas med konkret motivering.

## Avgränsad beräkningsprototyp 2026-10-11

- Python med enbart standardbiblioteket, lokalt öst/nord-plan i meter och UTC.
- Explicit mittpunktsintegration av båtens vattenhastighet plus ström vid
  simulerad position och tid. Syntetisk, uppskattad konstant båtprofil.
- Saknad, ogiltig eller tidsmässigt otäckande ström avbryter som standard.
  Nollström som fallback måste väljas aktivt och redovisas per uppslag.
- Det lokala strömförslaget i `stromhantering.md` har lästs tillsammans med
  grundkraven. Geodetik, kurskompensation, polarer, interpolation, ETA och
  hinderkontroll skjuts upp; detta är en rörelseprototyp, inte ruttplanering.
- Körinstruktioner, referenser och toleranser finns i `../prototype/README.md`.

## Föreslaget, ännu inte beslutat

- Python/FastAPI, PostgreSQL/PostGIS och React/TypeScript.
- Beräkningsprototyp före konton och betalning.
- Mobilanpassad webbapp som första plattform.

## Öppna beslut före implementation

- Första verkliga testregion och representativa resor.
- Databasnamn och roll är verifierade som seaparser 2026-10-12; anslutningsvärden hålls privata.
- Visuell layouteditor och dess licens, kostnad, export och komponentintegration.
- Första båtprofiler och rättigheter till polarer.
- Prognos- och geografiska datakällor samt kvalitet och licenser.
- Numeriska toleranser, komfortmått och absoluta begränsningar.
- Routingalgoritm efter referenstester.
- Exakt definition av abonnemangens uppdateringar.
- Docker eller annan reproducerbar drift och tillåtna serveroperationer.
- Godkännande av första GitHub-publiceringen av dessa grundfiler.

## Målfärd i lokalt plan 2026-10-11

- Den tidigare rörelseprototypen har utökats med rak färd till mål, kompenserad
  styrkurs och restid. Tidigare uppskjutande av kurskompensation/ETA ovan
  beskriver första leveransen och ersätts för denna avgränsade modell.
- Fart genom vattnet antas konstant och vindavdrift uttryckligen noll.
  Styrningen antas omedelbar; ingen polar eller seglingsvinkelkontroll finns.
- Målpositionstolerans 0,01 m, minsta framdrift större än 0,01 m/s,
  tidsgräns 86400 s och steggräns 100000 som konfigurerbara standardvärden.
- Saknade strömdata, omöjlig kurs, otillräcklig framdrift och körgräns ger
  uttryckliga avbrottsstatusar utan vanlig restid. Ingen väntan optimeras.
- Referenser, halverade tidssteg och kvarvarande numeriska begränsningar
  dokumenteras i prototype/README.md. Hinderkontroll, segelpolar, geodetik
  och ruttoptimering återstår. Ingen installation, databas eller publicering.

## Syntetisk hinderkontroll 2026-10-11

- Slutna axelparallella rektanglar i lokalt plan, med valfri explicit marginal.
  Hela integrerade färdsegment testas geometriskt; kantkontakt blockeras.
- Samma kontroll används i tidsbegränsad rörelse och målfärd. Målfärd ger
  `blocked` utan restid; blockerade steg accepteras inte som färd.
- Detta ersätter tidigare uppskjutande av hinderkontroll endast för
  syntetiska rektanglar. Djup, sjökort och verklig navigerbarhet återstår.
- Leveransstatus, acceptanskriterier och nästa uppgifter hålls i progress.md.

## Kontrollerat utvecklingsmandat 2026-10-12 (historik)

- Projektändringar, tester/offlinekontroller, egna granskade lokala commits,
  .venv och låsfilstyrd npm ci godkända av användaren. AGENTS.md uppdaterad.
- Inga systempaket/sudo. Databasoperationer och push ännu inte godkända.
- Testdatabas/roll föreslås som seaparser_test, lokal SCRAM över IPv4-loopback
  och explicit HBA-reject för testrollen mot andra databaser/anslutningsvägar.
  Utvecklingsdatabasens PUBLIC-rättigheter ändras inte i administratörsunderlaget.
- SQL, HBA och verifieringsordning finns i database-test-runbook.md; inget kördes
  mot PostgreSQL. PostGIS behövs inte för den aktuella schemabaslinjen.

## En utvecklingsmiljö 2026-10-12 – ersätter tidigare testmiljöförslag

- Endast development, databas och roll seaparser. Ingen separat testdatabas,
  testroll eller testlösenord ska krävas eller skapas.
- Enhetstester är databasfria. Databastester använder rollback/testegna objekt
  och får inte tömma eller ändra befintliga data eller sekvenser.
- Skrivskyddad diagnostik är godkänd med projektrollen och privat konfiguration;
  hemligheter får inte visas eller hamna i Git. Första migrationen godkändes och
  tillämpades senare samma dag; framtida migrationer och push kräver godkännande.
- Inför drift separeras miljön och en ny driftroll skapas med minsta rättigheter.
