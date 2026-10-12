# SeaParser – verifierad status och arbetsordning

## Arbetsform

Lokala, reversibla leveranser inom axiertech/seaparser. Befintliga lokala
ändringar bevaras. Projektinstallationer och lokala commits är godkända enligt
AGENTS.md. Skrivskyddad databasdiagnostik är godkänd; databasändringar,
publicering och push kräver separat godkännande.

Aktuellt beslut 2026-10-12: en utvecklingsmiljö, databas och roll seaparser.
Tidigare avsnitt om separat testmiljö är historik och gäller inte längre.
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

1. Genomförd 2026-10-12: komplett jämförelse av fördefinierade kandidatrutter
   med tidsberoende tillstånd, omväg och inget genomförbart alternativ.
   Se ruttjämförelseleveransen nedan; global optimalitet utlovas inte.
2. Genomförd 2026-10-12: utbytbar båtprestanda och spårbar uppskattad syntetisk
   polar med förbjudna vinklar och kursberoende kompensation. Automatisk kryssning
   och manövermodell ingår inte; se polarleveransen nedan.
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

## Första databasmigrationen – verifierad 2026-10-12

Uppgift: dokumentera diagnostik, utreda anslutningshindret och införa versionerade
migrationer med status och samtidighetsskydd. Användaren godkände uttryckligen
endast första migrationen i utvecklingsdatabasen. Inga privata filer ändrades.
Antagande: framtida migrationer körs genom samma verktyg och granskas separat.

Användaren rapporterade lyckad terminaldiagnostik. Egen kontroll som seaparser
reproducerade PermissionError errno=1 i sandboxens TCP-kontroll. Efter begränsat
körgodkännande lyckades exakt samma diagnostik utanför sandboxen. Skillnaden är
körmiljöns nätverksskydd, inte ett påvisat HBA- eller autentiseringsfel. Tidigare
uppgift om att tillståndsbegäran var avstängd gäller den tidigare sessionen;
den aktuella sessionen tillät begränsade godkännanden. Inga serverregler ändrades.

Egen skrivskyddad verifiering: databas och roll seaparser; PostgreSQL 18.6;
PostGIS 3.6.2; CREATE/USAGE i public; rollen är inte superuser och har inga
rollmedlemskap eller CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS-rättigheter.
spatial_ref_sys har SELECT men inte INSERT/UPDATE/DELETE för projektrollen.

Första filen 0001_baseline.sql skapar endast public.seaparser_migrations.
Verktyget registrerar version/checksum/tid i samma transaktion. Ingen separat
schemaskapning eller ändring av befintliga objekt. Status är skrivskyddad;
try-advisory-transaktionslås avvisar samtidiga verktygskörningar. Okända versioner,
ändrade tillämpade filer och befintlig historik utan baslinje avvisas före skrivning.
Timeout och fel ger rollback. Ingen automatisk downgrade.

Verifierat med `.venv/bin/python -B -m scripts.migrate --environment development`:
status före körning: 0001_baseline pending. Första --apply lyckades. Andra --apply
och slutlig --status gav identisk applied-rad, inklusive checksum och tid:
SHA-256 dae062b34f3332abb78d29034995a9d629bb255ce22a1af96501716d3e397155,
applied_at 2026-10-12 11:27:23.165308+02. Andra körningens SQL-väg gör ingen DDL
eller INSERT/UPDATE för tillämpad version. Slutlig diagnostik visar endast den nya
migrationstabellen utöver tidigare spatial_ref_sys i public; inget seaparser-schema.
Ingen SQL för att ändra spatial_ref_sys eller andra befintliga objekt kördes.

`make check` passerar: 38 prototyptester, 4 befintliga konfigurationstester och
4 nya migrationsskyddstester; syntax/TOML/beroenden/domängränser passerar.
Frontendens syntax passerar, node --test hittar 0 tester. Inga paket installerades.
Git diff --check passerar. Ändringarna granskas och ingår i lokal commit;
tidigare lokala ändringar bevaras och dokumentets tidigare tillägg lämnas ostagade.
Ingen push eller publicering. Nästa steg: separat granskning/godkännande av
framtida produktmigrationer. Samtidighets- och checksumfel har offlinekontroller;
felvägarna har inte provocerats mot utvecklingsdatabasen i denna leverans.


## Korrigeringsleverans – en utvecklingsdatabas 2026-10-12

Aktuell uppgift: föra in beslutet om endast development och seaparser i en egen
commit utan prototyparbetet. Konfiguration, CI, instruktioner och AGENTS.md granskade.
Separat testkonfiguration, databas-/roll-/HBA-underlag och CI-migrationsjobb tas bort.
Offlinekontroller och enhetstester ansluter inte till någon databas. Skrivskyddad
diagnostik använder endast projektrollen och privat konfiguration utan shell source.

Explicit syntetisk testinmatning ersätter privat fil helt. Fel miljö eller databas/
roll avvisas. Gamla TEST_DB_*-nycklar avvisas både i explicit inmatning och fil;
regressionstest för filfallet tillagt. Lösenord döljs i repr och fel. .gitignore är
oförändrad; git check-ignore bekräftar skydd för .env, app.env, config/, .pem och .key.
Ingen privat fil lästes för dessa kontroller och inga databasoperationer kördes.

Databastester får inte tömma tabeller eller ändra befintliga rader, sekvenser eller
externa sidoeffekter; rollback och testegna objekt krävs. Ingen skrivande testsvit
har införts. Första migrationens tidigare godkännande/resultat återges korrekt;
framtida migrationer, privata filändringar och push kräver separat godkännande.

Verifierat: make check i arbetskatalogen passerar med 38 prototyp- och 9 övriga
Python-tester (47 totalt), frontendens syntax passerar och frontend har 0 tester.
make migration-plan och git diff --check passerar. En separat kopia av exakt
commitkandidaten passerar samma kontroller med 32 prototyp- och 9 övriga tester
(41 totalt), utan ostagade prototypändringar. CI har inte körts på GitHub; actionrevisioner
ska granskas/låsas före aktivering. Inga nya beroenden eller resurser införs.
Tidigare fristående miljö-/anslutningsloggar och fyra prototype/-filer lämnas ostagade.
Nästa steg: separat granskning av dessa kvarvarande ändringar. Ingen push.


## Miljöskydd – TLS, testplan och Actions 2026-10-12

Aktuell uppgift: stärka befintlig utvecklingsmiljö utan serverändringar eller
integrationstestkörning. DB_SSLMODE har standard require; endast require,
verify-ca och verify-full accepteras. Explicit CA-sökväg krävs för verifierande
lägen. Unix-sockets avvisas; ren gemensam libpq-miljö kan inte ärva svagare PG*.
GSS-kryptering stängs av för att verkligen kräva TLS. verify-full med betrodd CA
och korrekt servernamn dokumenteras i database-test-runbook.md. Privata filer,
server-TLS och databasen har inte ändrats eller anslutits i denna leverans.
TLS-handshake/certifikat mot servern är inte verifierade.

Förberedda integrationstester återanvänder migrationsgeneratorn med endast
testegna migrationer, slumpnamngivet transaktionsbundet schema och separat
advisory-låsnyckel. Förkontroll av identitet och aktiva DDL-eventtriggers; sådana
triggers stoppar testet. Alla skrivningar rullas tillbaka, även vid avsiktligt fel.
Låshållaren stängs även vid fel/timeout och separat läskontroll bekräftar städning.
Ingen COMMIT, DROP, befintlig historik, sekvens eller produktrad berörs. Plan och
begränsningar redovisade före körning; endast offlineplan körd, inte --run.

Actions låsta till fullständiga SHA inom tidigare huvudversioner. Officiella
release-/commitlänkar, releaseanteckningar, commitdiffar och action.yml granskade;
omfattning och begränsningar finns i actions-review.md. Detta är ingen fullständig
säkerhetsrevision av bundlade beroenden. CI på GitHub är inte körd.
Offlinekontrollen avvisar uses-referenser utan fullständig SHA.

Verifierat: isolerad kopia av miljöcommitkandidaten ger 32 befintliga prototyptester
plus 17 övriga tester (49 totalt), syntax/TOML/domängränser/beroendebas och
Actions-SHA-kontroll godkända. Fem nya TLS-tester provar även båda CLI-kopplingarna;
tre nya tester verifierar integrationstestplanens opt-in och objekts-/låsisolering.
Frontendens syntax passerar; 0 produkttester. make migration-plan och testplan
passerar offline. git diff --check och hemligheters ignore-regler passerar.
Antagande: servern stöder TLS redan; om inte måste anslutning nekas tills separat
serveråtgärd godkänns. Nästa steg: granska isoleringsplanen och godkänn separat
framtida integrationstestkörning. Prototypfixen får egen commit. Ingen push.


## Prognosgränsfix – granskad och verifierad 2026-10-12

De fyra kvarvarande prototype/-filerna granskade och avgränsade till samma fix.
Tidigare kunde ett 60 s-steg med giltigt start-/mittpunktsuppslag röra sig förbi
prognosens slut vid 45 s. Båda integratorerna kortar nu vid kända gränser och
räknar om mittpunktens tid och position. Ett accepterat steg kan sluta exakt vid
valid_until; fortsatt färd kräver nytt giltigt uppslag eller uttryckligt vald
nollströmsfallback i simulate. Målfärden ger data_unavailable utan restid och
behåller endast slutförda steg när nästa prognos saknas. Hinderkontrollen används
även för förkortade segment. Inga databas-/HTTP-/UI-beroenden i beräkningen.

De sex tidigare ostagade regressionstesterna och fyra fördjupade tester verifierar
mål före/vid gränsen, gräns upptäckt först vid mittpunkt, omräknad tid/position,
ändrad ström efter prognosbyte, fortsatt giltig prognos, fem sekunders datalucka
samt redovisad fallback före/efter prognosintervall. Oberoende referens:
x'=1+t/100 ger x(45)=55,125 m; 1 m/s i 45 s och därefter 3 m/s i 15 s ger 90 m.
Grovt och halverat steg provas. Fyra fördjupade tester mot tidigare committad
beräkning gav sex felutfall inklusive subtester och noll körfel; samtliga passerar
med fixen. Referenstolerans 1e-8 m för analytiska förflyttningar.

Verifierat: make check passerar med 42 prototyp- och 17 övriga Python-tester
(59 totalt), syntax/TOML/beroenden/domängränser och Actions-SHA-kontroll.
Frontendens syntax passerar, 0 produkttester. Migrations-/integrationstestplan
är offline; ingen databasanslutning eller TLS-handshake har körts. git diff --check
passerar. Fix och miljöskydd får separata lokala commits; tidigare fristående
miljö-/anslutningsloggar i detta dokument lämnas ostagade. Ingen push.

Antagande: uppslagens giltighetsintervall beskriver sammanhängande tidsmässig
täckning. Okända luckor mellan uppslag, rumslig täckning och prognosålder är
fortfarande inte bevisade; tidsgränskontrollen är ingen verklig navigationsvalidering.
Nästa steg: separat granskning av kvarvarande loggar och godkännande av den
förberedda, isolerade PostgreSQL-testplanen innan någon integrationskörning.


## Databastester och begränsad ruttjämförelse 2026-10-12

Användaren bekräftar att databasdiagnostik samt PostgreSQL-tester för rollback
vid migrationsfel, avvisning vid samtidigt lås och städning har lyckats.
Detta dokumenterar användarens verifiering; ingen rå körlogg granskades och
agenten har inte återkört databaskommandon i denna leverans. Använt TLS-/CA-läge
anges inte i bekräftelsen. Serverkonfiguration, privata filer och databasen orörda.

Aktuell uppgift: nästa begränsade referensleverans med kompletta explicita
kandidatrutter via fördefinierade vägpunkter runt syntetiska hinder. Acceptans:
fri direktväg, blockerad direktväg med omväg, inget genomförbart alternativ och
tidsberoende ström som ändrar vinnare; ingen geografisk sammanslagning av tillstånd.

Implementerat i prototype/routes.py: varje kandidat startar oberoende från samma
position/tid; sail_to_target återanvänds för varje delsträcka med faktisk
slutposition och ankomsttid. Ingen snapping till vägpunkt eller återställning av
ström/prognostid. Samma integrerade segmentkontroll, prognosgränsskydd och
absoluta kurs-/framdriftsgränser gäller. Endast kompletta arrived-kandidater får
positiv totalrestid/ankomst och kan vinna. Avbrott behåller slutförda delsträckor
med status och orsak. Ingen genomförbar kandidat ger no_feasible_route.

Samma fart, data, hinder och budgets för alla kandidater. Max 100 kandidater,
32 mellanvägpunkter, 86400 s och 100000 steg per komplett kandidat som standard.
Ingen väntan/svängkostnad eller automatisk waypointgenerering. Exakt lika
restid väljer först angiven kandidat. JSON-export redovisar scope och alla utfall;
domänen har inga I/O-, SQL-, HTTP- eller UI-beroenden och omfattas av importskyddet.

Verifierat: make check passerar med 54 prototyp- och 17 övriga tester (71 totalt).
Tolv nya kravbaserade ruttester inkluderar senare genomförbar ankomst vid samma
geografiska waypoint (får inte prunas), fortsatt verklig tid/position, slutande
prognos på andra delsträckan, hela ruttens budget, determinism och export.
Analytiska referenser: 100 m/1 m/s=100 s (<=1e-6 s); omväg
2*sqrt(30²+20²)+40 m och tidsberoende x=t+t²/200 (<=0,03 s).
Utan ström väljs norr (112,11 s) framför söder (124,85 s); med tidsberoende ström
väljs söder (94,40/94,07 s vid steg 2/1 s). Halverat steg bevarar vinnare; den
rumsliga diskontinuiteten ger fortfarande numerisk tidskänslighet. Lokalt tog
100 tvåkandidatjämförelser med steg 1 s totalt 1,137 s; inget generellt prestandalöfte.

Syntax/TOML/beroenden/domängränser och Actions-SHA-kontroll passerar.
Frontendens syntax passerar och produkttester saknas (0). Migrationsplan och
integrationstestplan passerar offline utan konfigurationsläsning/anslutning;
git diff --check passerar. Ingen ny installation, databasändring eller push.
Befintliga 76 fristående miljö-/anslutningsloggrader bevaras ostagade.

Antaganden: deterministisk syntetisk miljö, lokalt meterplan, uppskattad konstant
båtprestanda och omedelbara kursbyten. Resultatet gäller endast angiven
kandidatmängd, inte global optimalitet eller verklig navigerbarhet. Tolerans
0,01 m per waypoint och mikrosekundsupplösning påverkar fortsatt färd.
Nästa steg: spårbar syntetisk polar/vind och sedan hårda vädergränser/komfort,
se beslutslogg och tidigare beroendeordning. Ingen bakgrundsaktivitet.


## Spårbar syntetisk segelpolar – verifierad 2026-10-12

Aktuell uppgift: uppskattad testpolar, explicit vindkonvention/referensram och
utbytbar prestanda för färd/ruttjämförelse. Krav/arkitektur/beslutslogg lästa.
Inga databasoperationer, installationer eller privata konfigurationsändringar.

SailPolar seaparser-synthetic-sail v1 består av oföränderliga axlar/rader med
handvalda referenser, källa och estimated=True. 0/10/20 knop vattenrelativ vind,
45/60/90/120/150/180° absolut TWA; bilineär interpolation, ingen extrapolation.
Vinklar under45° förbjudna. Polaren är uppskattad testdata, inte en uppmätt båt.
Metadata och vindram/vektor följer resultatexporten. Tabell och detaljer i
prototype/README.md. Meteorologisk från-konvention granskad mot officiell ECMWF.

Vind/ström lagras som mot-vektorer i lokalt sann-nord/öst-plan i m/s. Vindens
meteorologiska från-bäring skiljs explicit från strömmens mot-bäring. Conditions
anger ground (standard) eller water. Wwater=Wground-Cground, ingen dubbel
subtraktion för water. Polaren använder sann vattenrelativ vind, inte skenbar
vind relativt båten. Gemensam giltighetstid för vind/ström; prognosålder saknas.

BoatPerformance äger compensate och modellantaganden. Ruttjämförelsen förmedlar
samma modell utan kännedom om polartabell eller lösningsmetod. Konstantmodellen
behåller analytisk kompensation och alla tidigare tester. PolarBoat söker rötter
på alla tillåtna linjära vinkelstycken, delar vid samtliga stationära punkter och
prövar tangerings-/ändpunktsrötter. 60 bisektionsiterationer och residual<=1e-9 m/s;
störst positiv framdrift väljs. Ingen konstantfartsformel används för polaren.
No-go gäller styrkurs/vattenriktning, inte COG. Ingen tillåten lösning ger infeasible
utan restid. Ingen automatisk kryss, väntan eller manöverkostnad. Saknad/ogiltig/
för stark vind ger data_unavailable. Noll vattenrelativ vind ger infeasible.

Verifierat: make check passerar med 73 prototyp- och 17 övriga Python-tester
(90 totalt). Alla 71 tidigare tester och 19 nya polar-/prestandatester passerar.
Nya referenser omfattar tabellceller, bilineär interpolation, ändpunkter/no-go,
359°/1° för vind och styrning, från/mot-tecken, mark/vattenomräkning, symmetri,
annan oberoende BoatPerformance, flera rötter, intern tangering, för stark sid-/
motström och strömdriven COG mot vinden med tillåten segelkurs. Vindomslag vid45 s
avbryter vid prognosgränsen utan kryssning. Hinder/prognosgräns-/ruttbudgets bevaras.

Oberoende referenser: TWA90/TWS10 ->5 knop ->720 s per NM. TWA120/TWS10 ->4,5 knop,
Cnorth=2,25 knop ger styrkurs120; Ceast=0,3 knop ger SOG=0,3+4,5*sqrt(3)/2 knop.
Mark- och vattenvind ger samma resultat, steg120/60 s och restidsfel<=0,01 s.
C=(3,0), Wground=(0,-4) m/s ger Wwater=(-3,-4), styrka5 och från36,8699°.
Rum/tid-variation provas mot analytisk x'=.2K*x/100+.2K*t/100+5K; halverat steg
minskar fel mer än tre gånger och grovt steg har fel<0,001 m.

Syntax/TOML/beroendebas/domänimporter/Actions-SHA passerar; nya polar-/segelfiler
omfattas av importskyddet. Frontendsyntax passerar, 0 produkttester. Migrations-
och PostgreSQL-testplan passerar offline utan anslutning. git diff --check passerar.
Tidigare 76 fristående loggrader bevaras ostagade; egen lokal commit, ingen push.

Begränsningar/antaganden: syntetisk liten symmetrisk polar, noll vindavdrift,
omedelbar styrning/trim, inga segelval, vågor, verkliga polarer eller prognosålder.
Rotargumentet gäller endast denna styckvis linjära positiva prestanda, inte andra
modeller. Numeriska toleranser vid axlar är1e-10 knop/grader; fullständiga dynamiska
felgarantier och maritim sakkunnig validering saknas. Nästa steg: definiera hårda
vind-/sjögränser och syntetiskt komfortmått under samma absoluta begränsningar.
