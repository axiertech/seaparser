# SeaParser – verifierad status och arbetsordning

## Arbetsform

Lokala, reversibla leveranser inom axiertech/seaparser. Befintliga lokala
ändringar bevaras. Projektinstallationer och lokala commits är godkända enligt
AGENTS.md. Databasoperationer, publicering och push kräver separat godkännande.
Dokumentet uppdateras efter varje genomförd leverans. Ingen bakgrundsaktivitet
förutsätts efter att arbetet har stannat för granskning.

## Granskning 2026-10-11

AGENTS.md, samtliga docs/ vid start samt prototypens kod och tester lästa.
Utgångskontroll: `python3 -B -m unittest discover -s prototype/tests`:
24 tester godkända, 0,136 s. Detta verifierar syntetiska referenser, inte navigation.

- Rörelse: vatten- och strömvektorer summeras i lokalt öst/nord-plan;
  explicit mittpunktsmetod utvärderar position och UTC-tid på nytt.
- Kurskompensation: tvärström balanseras vid konstant vattenfart. För stark
  tvärström och otillräcklig framdrift avbryter, utan vanlig positiv restid.
- Målpassage: tolerans 0,01 m, förkortat slutsteg och bisektion vid
  överskjutning. Befintliga referenser och halverat steg passerar.
- Ingen SQL/HTTP/UI i beräkningen. Modell, miljö och JSON-presentation separerade.
- Kvarstående: vind används inte, ingen polar eller hinderkontroll vid start.
  Kontroller av miljö gäller bara uppslag; luckor mellan dem kan missas.
  Bisektion antar ett lämpligt lokalt förlopp; inga generella felgarantier.
  Målfärd är kopplad till konstantmodellen och måste generaliseras före polar.
  `steering_degrees` i äldre rörelseexport är vattenvektorns riktning och
  motsvarar stävriktning endast vid noll vindavdrift.

## Leverans 1 – granskning och syntetiska hinder (verifierad 2026-10-11)

Acceptanskriterier före implementation:

1. Hela integrerade segmentet kontrolleras mot slutna, axelparallella
   rektanglar, även när båda ändpunkterna ligger utanför hindret.
2. Kantkontakt, hörnkontakt och start/mål i hinder blockeras, utan att
   måltoleransen eller stort tidssteg kan kringgå kontrollen.
3. Rörelsesimulering ger uttryckligt fel; målfärd ger `blocked`, utan restid
   och utan att det blockerade steget läggs till slutförd bana.
4. Hinder bakom målet får inte blockera en förkortad målpassage.
5. Befintliga tester samt nya geometriska och integrerade referenser passerar.
6. Avtagande tidsberoende ström jämförs med handräknad restid, grovt och
   halverat steg; nära mål kontrolleras inom positionstolerans.

Antaganden: syntetiska statiska rektanglar, meter i lokalt plan, slutna
hindergränser. Valfri marginal expanderar rektangeln; ingen verklig
båtgeometri, sjökortsnoggrannhet eller navigerbarhet följer av detta.

Verifiering efter implementation: `python3 -B -m unittest discover -s
prototype/tests -v` gav 32 godkända tester, 0,140 s. Alla 24 tidigare tester
passerar. Åtta nya tester omfattar hela segment, riktningar, kant/hörn,
validering/marginal, strömavdriven rörelse, blockerat start/mål, stort och
mindre tidssteg, hinder bakom mål och målpassage med avtagande ström.
För avtagande ström används x/1852=7*u-u², u=t/3600, mål 5 NM och
handräknad restid 3600*(7-sqrt(29))/2. Steg 120/60 s håller 0,01 s tidstolerans.

Ingen av de integrerade blockerade förflyttningarna accepteras. `blocked`
exporteras med orsak och bara tidigare slutförda steg. Rörelsesimulering
kastar `ObstacleCollision`; målfärden returnerar status. Hinder bakom målet
kontrolleras inte som om båten fortsatt efter ankomst.

Nya filer: prototype/obstacles.py, prototype/tests/test_obstacles.py och
detta dokument. Ändrade i denna leverans: prototype/calculation.py,
prototype/README.md och docs/decisions.md. Befintliga lokala ändringar bevarade.

Begränsning: kontrollen avser den numeriska banans raka segment, inte en
okänd fysisk kurva mellan uppslag. Rektanglar med marginal är syntetiska
förbjudna områden, inte landmask, djupdata eller bevis på navigerbarhet.
Ingen omväg väljs automatiskt ännu. Leveransen stannar här för granskning.

## Nästa leveranser i beroendeordning

1. Enkel begränsad referenssökning över fördefinierade vägpunkter och hela
   alternativa färder. Behåll tidsberoende tillstånd, undvik att slå ihop
   olika ankomsttider per plats. Ange sökgränser och att ingen global optimalitet
   utanför kandidatmängden utlovas. Testa omväg och inget genomförbart alternativ.
2. Generalisera målfärdens båtprestanda och inför spårbar syntetisk polar,
   förbjudna vindvinklar och konsekventa manöverantaganden. Kurskompensation
   måste återutvärdera kursberoende fart; konstantfartsformeln räcker inte.
3. Testa rumsligt/tidsberoende vind och ström längs flerstegsrutter, giltighet,
   saknade data och halverade tidssteg mot oberoende referenser.
4. Definiera syntetiskt komfortmått och hårda vind-/sjögränser, jämför snabbast
   och bekvämast under exakt samma gränser. Testa att komfort aldrig kan väga
   bort förbjudna områden, vindvinklar, otillräckliga data eller hårda gränser.

Verkliga polarer/prognoser, geodetik, djup, sjökort, prognosålder, UI/editor,
API, databas och drift återstår. Prototypen är inte verifierad för verklig navigation.

## Miljöförberedelse 2026-10-12

Aktuell uppgift: förbereda en isolerad, kontrollerad utvecklingsmiljö utan
installation, databasanslutning, commit eller push. Förslag och mandat finns i
[development-environment.md](development-environment.md).

AGENTS.md, docs/ och befintlig prototyp/testkod lästa. Körning sker som seaparser.
De fyra befintligt ändrade prototypfilerna lämnades orörda.
Verifierat: Python 3.14.4, Node 22.22.1 och npm 9.2.0; sex kända privata
konfigurationsnycklar har värden (värden ej utskrivna). 38 prototyptester och fyra
nya miljöskyddstester passerar. Syntax/TOML/beroendebas/domänimportkontroll och
frontendsyntax passerar. Frontend har noll produkttester. Migrationsplan körd
utan anslutning. Git diff --check passerar.

Förberett: versionsfiler, tomma beroendelås, venv-kommandon, skilda inställningar,
testroll/databasunderlag, checksumskyddade SQL-migrationer, CI och arbetsmandat.
Inte verifierat: faktisk DB-isolering/anslutning, migrationer i PostgreSQL eller
GitHub Actions. CI-revisioner ska låsas efter officiell granskning före aktivering.
Nästa steg: användaren granskar och godkänner exakt de separata åtgärder som anges
i miljöförslaget. Ingen bakgrundsaktivitet fortsätter efter denna leverans.

## Mandat och administratörsunderlag 2026-10-12

Aktuell uppgift: dokumentera användarens godkända mandat och förbereda SQL,
minsta HBA/behörigheter, exakta verifierings-/migrationskommandon och CI-beskrivning.
AGENTS.md, miljöförslag och beslutslogg uppdaterade. Administratörsunderlaget
begränsar testrollen till egen databas över IPv4-loopback och SCRAM; utvecklingens
PUBLIC-behörigheter lämnas orörda. HBA-blocket måste placeras före bredare regler.

Verifierat: npm ci med officiella npm-registret lyckades (tom beroendegraf).
make prepare-python försöktes men misslyckades: ensurepip saknas. .venv är delvis
skapad med include-system-site-packages=false, inte färdiginstallerad. Ingen sudo
eller systeminstallation gjord. Administratören behöver tillhandahålla
python3.14-venv/ensurepip innan förberedelsen kan slutföras. psql finns lokalt.
38 prototyptester och 4 miljötester passerar med befintlig Python. Syntax/TOML,
domän-/beroendekontroller, frontendsyntax och git diff --check passerar.
Frontend har fortfarande noll produkttester. Migrationsplan körd utan anslutning.
Befintliga ändringar i prototype/ jämförda med startens diff och är identiska.

SQL/HBA granskade mot officiell PostgreSQL-dokumentation; aldrig körda mot server.
CI-jobb och behörigheter dokumenterade, inte körda. Nästa steg: administratörsstöd
för venv och separat godkännande av testdatabas/HBA/lösenord samt därefter
anslutningsverifiering och testmigrationer. Push kräver fortfarande godkännande.
