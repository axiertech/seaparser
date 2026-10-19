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
4. Genomförd 2026-10-12: hårda markrelativa vind-/Hm0-gränser och syntetisk
   tidsexponering med snabbast/bekvämast-val inom begränsad extra restid.
   Uppslagsbaserade kontroller är ingen kontinuerlig eller maritim säkerhetsgaranti.

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


## Gemensamma vädergränser och syntetiskt komfortval 2026-10-12

Aktuell uppgift: konfigurerbara hårda vind-/våggränser, explicita vågdata och enkelt
komfortmått med begränsad extra restid. Krav, arkitektur och beslutslogg granskade.
Ingen databasanslutning, server-/privat konfigurationsändring eller installation.

WeatherPolicy kräver max markrelativ vind i m/s och max signifikant våghöjd Hm0
i m. Vattenrelativ vind omräknas Wground=Wwater+Cground för vädergränsen;
polarens TWS är fortsatt Wwater. Samma policy/krav gäller alla kandidater och båda
urvalen. Överskridande ger weather_limit före poängval; saknade/ogiltiga data eller
okänd/utgången giltighet ger data_unavailable. Aktiverad policy kräver giltig ström
utan simulate-fallback. Även nollsträcka måste passera väderkontroll.

WaveData anger Hm0 m, markfast Tm02 s och medelvågornas från-bäring medurs från sann
nord, eget [valid_from,valid_until)-intervall, källa/version och explicita ram-/
periodetiketter. Andra periodtyper/ramar avvisas. Konvention/enheter granskade mot
Copernicus Marines officiella dokumentation; inga verkliga väderdata hämtades.
Båda giltighetsintervallen måste vara explicit kända när policy aktiveras. Vågornas
kända prognosgränser kortar steg och räknar om mittpunkten; byte kräver nytt uppslag.

Komfortmodell synthetic-wave-exposure-v1: r=(Hs/1m)^2*(5s/Tm02)^2*(1+sin(beta)^2),
med beta relativt båtens riktning genom vatten. E=integral r dt över accepterade
steg/delsträckor, i syntetiska exponeringssekunder. Modellen är ej validerad för
verkliga båtrörelser. Ingen encounter-/resonans-/roll-/stampnings-/sjösjukemodell.
Lägre E föredras. Misslyckade rutter saknar fullständig poäng och kan aldrig väljas.
Bekvämaste väljs endast bland samma arrived-kandidater som snabbaste, inom
fastest_time + max_comfort_extra_seconds (standard300 s, finit och >=0). Vid lika
E väljs kortare tid och därefter först angiven kandidat. Alla ruttbudgets kvar.

Verifierat: make check passerar med 91 prototyp- och 17 övriga Python-tester
(108 totalt). Alla 90 tidigare och 18 nya väder-/komforttester passerar. Nya fall
omfattar olika snabbaste/bekvämaste kandidater, tidsmarginal, absoluta gränser trots
snabb/lågpoängsrutt, gränslikhet, mark/vattenvind, dataluckor vid start/mittpunkt,
oberoende våggiltighet, prognosbyte, tidsintegral, halverat steg och exportmetadata.
Aktiverad väderpolicy avvisar även explicit strömfallback; legacy utan policy
märks not_requested, ingen komfortpoäng/val eller verifierad väderbedömning.

Referensfallet med 1 m/s: direkt100 s/E200; omväg140 s/E35,4923 respektive35,5396
vid steg2/1 s, mot analytiska E35,5556. Extra marginal40 s tillåter omvägen;
39 eller0 s behåller direktvalet. Fel<=0,07 exponering-s och skillnad<0,05 vid
halvering; vinnarval stabilt. Tidsfält Hs=.5+.002t ger E=72+2/3 på100 s;
steg10/5 s ger grovt fel<0,01 och mer än trefaldig felminskning. Vågbyte vid45 s
från Hs1 till.5 ger E117,5. Exempelgränser är testdata, inte båtvaliderade råd.

Syntax/TOML/beroenden/domänimporter/Actions-SHA och frontendsyntax passerar.
Frontend har0 produkttester. Migrations- och PostgreSQL-testplan passerar offline
utan konfigurationsläsning/anslutning; git diff --check passerar. Resultat/export
redovisar policy, tidsmarginal, båda valen, vågkälla/giltighet och syntetisk modell.
Tidigare76 fristående loggrader bevaras ostagade. Lokal commit, ingen push.

Begränsningar: hårda gränser testas vid start/mittpunkt och provisoriska uppslag,
inte bevisat mellan alla uppslag eller vid samtliga segmentändpunkter. Omärkta
luckor/farliga toppar kan missas; provisoriska uppslag kan avbryta konservativt.
Hela segmentens hinderkontroll och polarens no-go är kvar. Tidsstegshalvering är
ingen säkerhetsgaranti. Prognosålder, verklig datainterpolation och maritim
sakkunnig validering återstår. Nästa steg: fördjupa intervall-/datakvalitetskontroller
och validera antaganden innan verkliga prognoser eller användargränser används.


## Prognosålder och faktisk destinationskontroll 2026-10-12

Aktuell uppgift: datakvalitet före framtida integration med verkliga prognoser.
Krav, arkitektur och beslutslogg granskade. Ingen databasanslutning/ändring,
installation eller privat/serverkonfigurationsändring.

Conditions och WaveData har issued_at separat från giltighetsintervallet.
ForecastPolicy(max_age_seconds) jämför varje källas utfärdandetid mot en explicit
planeringstid, inte simulerad avgång/ankomst. Maxålder är finit och >=0, likhet
med gränsen tillåts. Saknad/ogiltig/framtida utfärdandetid eller för gammal källa
ger data_unavailable. Framtida giltighet upphäver aldrig åldersgränsen. Ingen
fallback till start/nu/giltighet/nedladdningstid för saknad utfärdandetid.

Clock injiceras; FixedClock ger reproducerbar UTC-tid. Yttre klockan läses en gång
per jämförelse och snapshot förmedlas till alla kandidater och delsträckor.
Standalone färd/rörelse fångar en tid per anrop. Aktiverad ålderspolicy utan klocka
är ett explicit konfigurationsfel. Utfärdandetid valideras vid varje uppslag,
inklusive prognosbyte och ankomst, mot samma planeringstid.

Färdberäkningen gör ett separat miljöuppslag vid numeriskt faktisk slutposition
och ankomsttid, även inom måltoleransen och för nollsträckor. Ingen snapping till
nominellt mål. Samma begärda väder-/ålderspolicyer gäller. [valid_from,valid_until)
gäller även destinationen: rörelse får sluta vid valid_until men ankomstväder
kräver nästa giltiga prognos vid exakt gräns. Annars utesluts kandidaten från
både snabbast och bekvämast. Bana/elapsed_seconds och destination_reached bevaras,
men godkänd restid/ankomst/komfortpoäng saknas. Faktisk ankomstkontrollstid,
väderstatus, godkänd observation och prognosåldersstatus exporteras separat.

Verifierat: make check passerar med103 prototyp- och17 övriga Python-tester
(120 totalt). Tolv nya regressionstester täcker gamla prognoser med framtida
giltighet, färska prognoser, exakt maxålder och oberoende vågålder, saknad/framtida/
naiv tid, UTC-normalisering, en klockläsning över kandidater/delsträckor, faktisk
ankomstposition/tid, destinationsöverskridande/datalucka/åldersfel, ny prognos vid
exakt gräns, nollsträcka, tidsbegränsad rörelse och export. Ett tidigare testfall
om ankomst exakt vid utgången vågprognos har avsiktligt skärpts; inget skydd tas bort.

Oberoende referens: planeringstid2026-01-01 00:00 UTC, utfärdad600 s tidigare,
avgång två timmar senare och100 s färd. Åldern är600 s vid planeringen, inte
7900 s vid ankomst. Utfärdad601 s tidigare avvisas trots samma framtida giltighet.
Destinationsfel vid100 m/100 s behåller fysisk ankomst men ger ingen vald rutt.
En senare140 s-kandidat kan passera samma destination när ett kort farligt
väderfönster upphört; den tidiga100 s-kandidaten väljs aldrig av något av målen.

Syntax/TOML/beroendebas/domänimporter/Actions-SHA och frontendsyntax passerar.
Frontend har0 produkttester. Migrations- och PostgreSQL-testplan passerar offline
utan privat konfigurationsläsning/anslutning. git diff --check passerar.
Tidigare76 fristående loggrader bevaras ostagade; egen lokal commit, ingen push.

Begränsningar: ålder är metadata-/policykontroll, inte verklig prognosnoggrannhet.
Gemensam issued_at för vind/ström antar en sammanhängande källa; olika produkter
måste separeras i framtida adapter. Legacy utan policy märks not_requested, inte
verifierat färskt/godtagbart väder. Båda policyer och tillförlitlig källmetadata
krävs inför verklig integration. Punktuppslag och ny destinationskontroll ger
fortfarande ingen kontinuerlig verifiering mellan uppslag eller över alla andra
segmentändpunkter. Omärkta luckor/toppar kan missas. Exportens kontrollomfattning
säger detta uttryckligt. Inga verkliga vädertjänster kopplade eller maritima
säkerhetsgarantier införda. Nästa steg: käll-/adapterkontrakt och kontrollerad
intervall-/interpolationsvalidering innan verkliga prognoser används.

## Explicit avgångsjämförelse 2026-10-12

Aktuell uppgift: jämför en begränsad explicit lista av avgångstider med samma
kandidatrutter. compare_departures återanvänder hela ruttberäkningen, en gemensam
båtmodell, prognosmiljö och hårda gränser. Planeringsklockan läses exakt en gång;
alla avgångar/delsträckor får samma frysta UTC-tid för ålderskontroll. Miljö och
modell måste vara oförändrade under anropet; inga prognoser hämtas. Kandidater och
hinder materialiseras en gång så iteratorer fungerar för samtliga avgångar.

Varje avgång redovisar snabbaste/bekvämaste rutt och alla kandidaters restid, ETA,
syntetisk exponering, partiell bana och avbrottsorsak. Komfortens extra tidsgräns
jämförs med snabbaste rutten för samma avgång. Separata sammanfattningar visar
kortast restid och tidigast ankomst; selected är tomt utan uttryckligt kriterium
shortest_travel_time eller earliest_arrival. Inget generellt bästa avgångsval.
Inga genomförbara alternativ ger no_feasible_departure och individuella orsaker.
Standardtak är24 avgångar/100 rutter/32 vägpunkter; tomma/duplicerade/naiva tider
avvisas. Resultat/export säger uttryckligen att bara angivna tider/rutter undersöks.

Verifierat: make check passerar med111 prototyp- och17 övriga Python-tester
(128 totalt). Åtta nya tester täcker kortast restid kontra tidigast ETA,
väderberoende ruttval och felbevis i export, komfortens avgångsegna referens,
alla alternativ avvisade av hård gräns, en klockläsning och gemensamma policyer,
begränsade/unika iteratorindata och deterministiska lika värden, återanvändning av
hinderiterator samt saknad klocka/tidszon. Oberoende restidsreferens:100 m vid
1 m/s tar100 s; en avgång200 s senare med0,5 m/s medström tar66,6667 s men
ankommer senare. Senare farliga vågor över direktvägen gör omvägen snabbast.

Syntax/TOML/beroendebas/domänimporter/Actions-SHA/frontendsyntax passerar;
frontend har0 produkttester. Migrationsplan och PostgreSQL-testplan passerar
offline utan konfigurationsläsning/anslutning. git diff --check passerar.
En testfixture hade först fel konstruktorsignatur för rektangelhindret;
den korrigerades och hela kontrollsviten kördes om med godkänt resultat.

Begränsningar: fryst underlag är anroparens kontrakt; godtyckliga miljöobjekt
kopieras inte och en extern muterande källa kan inte garanteras stabil. Policyer
måste aktiveras för verifierad ålder/väder/komfort. Väder mellan uppslag är ännu
inte kontinuerligt verifierat. Ingen automatisk tids-/ruttsökning, global
optimalitet eller global komfortoptimering; syntetiskt komfortmått saknar fysisk
validering. Tidigare76 orelaterade loggrader bevaras ostagade. Lokal commit av
leveransen; ingen databasändring eller push. Nästa steg: stabilt prognosadapter-
kontrakt och intervallvalidering före verkliga prognoser.

## Arbetsbranch och pushmandat 2026-10-12

Användaren godkänner självständig push av granskade lokala commits till
axiertech/seaparser på development/-branch. AGENTS.md uppdaterad med krav på
relevanta kontroller före push, hemlighets-/innehållsgranskning och GitHub CI efter
push. Force-push, branchradering och merge till main kräver separat godkännande.

Förberedelse verifierad: make check passerar med128 Python-tester (111 prototyp,
17 övriga); syntax/konfiguration/domängränser/Actions-SHA och frontendkontroller
passerar. Frontend har0 produkttester. Migrationsplan/PostgreSQL-testplan passerar
offline utan anslutning. Hemlighetsmönster kontrollerade i leveransens sju filer
utan utskrift av värden; manuell diffgranskning och git diff --check passerar.
Endast avgångsleveransen och mandat/logg ingår. Tidigare76 lokala loggrader
bevaras ostagade. Arbetsbranch: development/departure-comparison.
Nästa steg: normal push av arbetsbranchen och kontroll av CI på exakt commit-SHA;
ingen force-push, main-merge, branchradering eller databasändring.

## Fryst prognosunderlag och adapterkontrakt 2026-10-12

Aktuell uppgift: oföränderligt leverantörsoberoende prognosunderlag på
arbetsbranchen development/forecast-data. ForecastDataset/GridProduct/
ProductMetadata/Coverage införda med separata dataset/version/källa/utfärdandetid/
giltighet/geografisk täckning/enheter/referensramar för vind, ström och vågor.
Normalisering ligger i infrastructure/forecast_adapter.py, utanför motorn.
ForecastAdapter.normalize returnerar ett materialiserat underlag; transport,
autentisering och verkliga leverantörer ingår inte. Syntetiska fixtures är
uppskattade testdata. Metadata följer uppslag och resultatsammanfattning även
för avvisade rutter utan accepterade färdsteg.

Underlagets nästlade värden/axlar/tider/masker kopieras till tuples och metadata
är frysta. Ursprungliga mutable indata kan inte ändra ett skapat underlag.
Ny prognos kräver explicit nytt underlag/anrop; alla alternativ inom en
jämförelse får samma dataset. Produkter får separat geografiskt/tidsmässigt
stöd och dataluckor, med gemensamt explicit WGS84-origo för lokala öst/nord-metrar.
Vind/ström normaliseras till markrelativa SI-motvektorer; vindens externa
från-konvention skiljs från strömmens mot-konvention. Vågornas Tm02/från-vektor
har egen metadata. Polarens vind förblir W_ground-C_ground.

Bilinjära vektorkomponenter i rum och linjär UTC-tidsinterpolation dokumenterad;
vågornas riktning interpoleras via enhetsvektorer. Odefinierad riktning ger gap.
Extrapolation, okänd täckning, saknade stödnoder och markerade ogiltiga celler
inklusive deras gränser avvisas. Giltighet är halvöppen även vid destination.
Separata utfärdandetider kontrolleras mot den gemensamma frysta planeringstiden.
Ett avrundningsfel upptäcktes i första viktade summan: konstant våghöjd kunde
bli marginellt över gränsen. Stabil interpolation bevarar nu konstanta värden
exakt och håller komponenterna inom stödintervallet; regressionstest tillagt.

Verifierat: make check passerar med127 prototyp- och17 övriga Python-tester
(144 totalt). Alla tidigare tester bevarade,16 nya tester täcker oberoende
linjär referens (u=2,08/v=-1,745), enheter och från/mot,359°/1°, odefinierad
vågriktning, separata gap/täckningar, masker/gränser, extrapolation, felaktiga
metadata, immutabilitet även efter mutation av originalpayload, separata åldrar/
giltighet och ankomstgräns, explicit prognosbyte, gemensamt dataset i rutter/
avgångar/export, saknad produkt, nätverks-/adapterförbud under jämförelse samt
exakt hård gräns. Standardkonstantfält ger100 s för100 m; nytt strömunderlag
med0,5 m/s medström ger66,6667 s utan att det gamla underlaget ändras.
Syntax/TOML/domänimporter/beroenden/Actions-SHA/frontendsyntax passerar;
frontend har0 produkttester. Migrations-/PostgreSQL-testplan passerar offline,
utan privat konfiguration eller anslutning. git diff --check passerar.

Begränsningar: lokalt plan med geografiskt origo, ingen verklig projektion eller
leverantörsintegration. Interpolationsregler är syntetiska, inte fysiskt/maritimt
validerade. Punktuppslag ger fortfarande inget kontinuerligt täckningsbevis;
smala cellmasker/vädertoppar kan missas mellan uppslag. Legacy callbacks kan
inte garanteras frysta; adapterflöden använder ForecastDataset. Inga betalda
tjänster, databasändringar eller main-merge. Tidigare76 orelaterade loggrader
bevaras ostagade. Nästa steg: granskad commit, normal push enligt arbetsbranch-
mandatet och verifiering av GitHub CI för exakt SHA.

## Sammanhängande backlogarbete 2026-10-12

AGENTS.md uppdaterad med användarens mandat att fortsätta mellan auktoriserade
deluppgifter efter granskning/tester/commit/push och godkänd CI. Ny sammanställd
backlog i docs/backlog.md prioriterar segmentens datastöd och ett reproducerbart
syntetiskt planeringsscenario. Verkliga datakällor, polarer och editorval kräver
fortsatt produktbeslut; inga kostnader eller server-/databasbehörigheter utökas.
Verifierat: make check,144 Python-tester och övriga offline-/frontendkontroller
passerar. Föregående prognosunderlags CI är success på0fd50948. Tidigare76 lokala
loggrader bevaras ostagade. Arbetsbranch development/forecast-validation.
Nästa del efter denna commits CI: kontinuerligt datastöd över integrerade segment.

## Segmentens prognosstöd 2026-10-12

Föregående mandat/backlog-commit e4ff070 har godkänd GitHub CI.
Nästa backlogdel implementerad: ForecastDataset verifierar interpolationsstödet
över hela accepterade affina numeriska färdsegment, genom korsade rum/tid-cellplan.
Saknade stödnoder, masker inklusive gränser och extrapolation avvisar hela steget
innan position/komfort uppdateras. Aktiverad WeatherPolicy kräver alla tre
produkterna; matematiska anrop utan policy kontrollerar strömstöd. Legacy
callbacks är fortsatt punktkontrollerade. Ingen nätverkshämtning tillkommer.
Datastöd skiljs uttryckligen från kontinuerligt godkända vädervärden i export.

Verifierat: make check med135 prototyp- och17 övriga Python-tester (152 totalt),
alla godkända; åtta nya tester täcker smala rum-/tidsgap, missing-noder, diagonal/
kantpassage, täckning/sluttid, simulering och samtliga jämförelsealternativ,
kontrolltak4096, halverat steg och komplett säker omväg.100 m vid1 m/s ger100 s
även med halverat steg; en1 m bred mask mellan ordinarie uppslag avvisas utan
accepterad rörelse eller exponering. Rörelse fram till valid_until bevaras,
medan ankomstkontrollen fortsatt avvisar utgångna data.

Syntax/konfiguration/importgränser/Actions-SHA och frontendkontroller passerar;
frontend har0 produkttester. git diff --check passerar. Begränsning: kontrollerad
lokal numerisk bana/datastöd är inte verifierade kontinuerliga hårda vädervärden
eller verklig båttrajektoria. Inga server-/databasändringar eller nya tjänster.
Tidigare76 lokala loggrader bevaras ostagade. Nästa del efter granskning/push och
godkänd CI: reproducerbart syntetiskt planeringsscenario med spårbara indata.

## Reproducerbart syntetiskt planeringsscenario 2026-10-12

Segmentkontrollens commit8453a14 har godkänd GitHub CI; fortsatt enligt backlog.
application/planning.py samordnar fryst PlanRequest och oförändrade domänflöden.
Versionerad syntetisk fixture och scripts.plan_synthetic ger ett helt offline
scenario med två avgångar/tre rutter, testpolar eller konstantmodell, valfritt
syntetiskt hinder och uttryckligt avgångskriterium. Inga privata inställningar,
nätverks-/SQL-anrop eller installationer. Manifest anger algoritm/schema,
samtliga parametrar inklusive cellkontrolltak, båtprofil/antaganden, produktmetadata
och SHA-256 för hela datasetinnehållet, båten och indata. Ursprungliga listor
kopieras begränsat; båda policyerna är obligatoriska i detta usecase.

Verifierat: make check,135 prototyp- och24 övriga tester (159 totalt), alla
godkända. Sju nya tester täcker oberoende polarrestider, snabbast/bekvämast,
blockerad direktväg/senare infeasibility, byte-identisk JSON utan nätverk,
fingeravtryck vid ändring av data under oförändrad etikett samt båt/parametrar/
policy/tid/rutter, fryst request/begränsningar, CLI/felstatus och halverat steg.
Första avgången: direkt50 s/E100, nord71,247896 s/E35,9940 vid10 s-steg;
analytisk omväg20sqrt(2)/1,2 +60/2 +20sqrt(2)/1,6 ≈71,248 s. Halverat steg
behåller val och uppfyller0,01 s/0,5 exponeringssekunder. Senare avgång får
kortare restid men senare ETA; diagonaler kan sakna tillåten kompensationskurs.
Ingen generell bästa avgång väljs. Observationsmätning av demo-körningen:
0,1284 s och287394 resultatbytes före slutlig manifestkomplettering; inte ett SLA.

Syntax/konfiguration/importgränser/Actions-SHA och frontendkontroller passerar;
frontend har0 produkttester. Migrations-/PostgreSQL-testplan passerar offline
utan anslutning. git diff --check passerar. Egna filer/hemligheter granskas före
commit; tidigare76 orelaterade loggrader bevaras ostagade. Begränsningar: endast
inbyggda frysta båtmodeller har serialiserare; domänens utbytbarhet behålls.
Hash identifierar innehåll, inte källans äkthet/kvalitet. Byte-identitet gäller
verifierad Pythonmiljö. Vädervärden mellan uppslag är fortsatt inte kontinuerligt
verifierade. Inga verkliga tjänster, databasändringar eller merge till main.
Nästa steg: granskad push/CI och samlad status för den sammanhängande leveransen.

## Samlad backlogleverans och verifierad CI 2026-10-12

Sammanhängande leverans på development/forecast-validation:
- e4ff070: AGENTS.md:s fortlöpande arbetsmandat och dokumenterad backlog.
  CI38277173226 completed/success.
- 8453a14: datastöd över hela integrerade segment,152 godkända Python-tester.
  CI38277785528 completed/success.
- ef9f261: reproducerbart offline-usecase/testscenario med spårbara manifest,
  159 godkända Python-tester (135 prototyp +24 övriga).
  CI38278939482 completed/success på exakt ef9f261697b3277b11492501b90c0cd5adf7b471.

Samtliga relevanta lokala kontroller och GitHub CI passerade före nästa del;
inga CI-fel behövde rättas. Stagade filer/diff granskade och kontrollerade för
hemlighetsmönster. Frontendsyntax passerar, frontend har0 produkttester.
Migrations-/PostgreSQL-plan kördes endast offline. Inga betalda resurser,
installationer, databasändringar eller main-merge. Backlogstatus uppdaterad med
verifierade commits. Tidigare76 orelaterade loggrader är fortsatt ostagade.

Nästa sammanhängande del: metod och regressioner för kontinuerliga hårda
vädergränser över frysta rutnät. Kontrollerat interpolationsstöd är ännu inte
kontinuerligt verifierade vind-/vågvärden eller verklig prognoskvalitet.
Verklig region/källa/licens, båtprofiler och editorval kräver separat produkt-
beslut innan bindande integration. Ingen fristående bakgrundsaktivitet startas.

## Konservativa hårda vädergränser över hela segment 2026-10-12

På development/segment-weather implementeras frysta rutnätets kontinuerliga
vind-/Hs-gränser med segment-aabb-component-box-exact-squared-v1. Alla stödcellers
slutna rum/tid-boxar som berör segmentets omslutande box ingår, via ordnade
koordinatjämförelser och inte sampling. Komponent-clamp ger |W|²<=U²+V² och
Hs<=maxHs; exakt rationell kvadratjämförelse för lagrade binära vindkomponenter
undviker avrundningsgodkännande. Gränslikhet i bevisat hölje är tillåten, inte
epsilon-överskridande. Markvind hålls skild från polarens vattenvind.

Tre utfall/proveniens: verified, exceeded med giltigt segmentvittne och
unverified (otillräckligt stöd eller bevis). Högt off-path hörn är inte ett
konstaterat överskridande. Failed proof ger weather_unverified, verkligt vittne
weather_limit och dataluckor behåller data_unavailable. Inget av dessa kan väljas
som snabbast/bekvämast; kontrollerna sker före rörelse/exponering. Step sparar
bevis och Voyage avvisningsbevis/vittne/status; nollsträcka not_applicable.
Celltak4096 per produkt avbryter med unverified. Ankomstgräns, datamasker,
hinderkontroll och prognosålder bevaras. Algoritmmanifest v3 inkluderar metod/tak.

Verifierat: make check med146 prototyp- och24 övriga Python-tester (170 totalt),
alla godkända. Elva nya tester täcker smala rum-/tidstoppar mellan ordinarie
uppslag, exakta (3,4)/5- och Hs1-gränser, strikt lägre gräns, höga off-path-hörn,
cellgränser, masker/gap, certifieringsbudget, båda beräkningsflöden och avvisade
avgångsval/export samt accepterade bevis/nollsträcka. Oberoende vindreferens:
u=8s(1-s),v=2(1-s); max ligger vid s=(2+sqrt(2))/8. Start/mitt/slut kan missa
överskridandet av2,25 m/s, men höljet ger aldrig godkännande. Sampling kan bevisa
överskridande, inte kontinuitet. Tidigare159 tester bevarade.

Syntax/konfiguration/domänimporter/Actions-SHA/frontendkontroller passerar;
frontend har0 produkttester. Migrations-/PostgreSQL-plan endast offline, utan
konfigurationsläsning/anslutning. git diff --check passerar. Box/cellhörn utanför
banan kan ge falsk avvisning; ingen exakt extremvärdessökning införs. Scope gäller
lokalt affint numeriskt segment, markvind/Hs och deklarerad interpolation, inte
verklig källkvalitet, alla manövrer eller kontinuerlig komfort/riktningsentydighet.

Användarens steering: AIS blir lågprioriterad planeringsinformation om observerad
trafikbelastning. Tidigare mötesanalys/löpande övervakning utgår; inga GPS-/kollisions-
eller undanmanöverfunktioner. Nästa del efter granskad commit/push och godkänd CI:
uppdatera krav/backlog och separata OpenWaters-kandidatvillkor enligt denna scope.
Inga nya konton/token/tjänster, server-/databasändringar eller main-merge.
Tidigare76 orelaterade lokala loggrader bevaras ostagade.

## Verifierad väder-CI och reviderad trafik-/tidvattenbacklog 2026-10-12

Huvudleverans5d3d7104ddc6a010013c18e64e216769e4ac62f6 är pushad på
development/segment-weather. GitHub CI38283470673 completed/success. Lokalt
170 Python-tester godkända (146 prototyp +24 övriga); tidigare tester bevarade.

Användarens senaste AIS-beslut ersätter tidigare mötesanalys/övervakningsförslag:
SeaParser är en planeringsapplikation, med AIS som lågprioriterad extra för
observerad trafikbelastning och tillförlitliga historiska mönster. Krav/backlog
uppdaterade med passagetid, dagsljus, sikt, väder, datatid/täckning/osäkerhet.
Ingen aktuell bild beskrivs som känd framtida trafik. Gamla/saknade/svagt täckta
data ger unknown, inte fri passage. Ingen GPS/CPA/kollisionsvarning eller
undanmanöver. TrafficSnapshot/observationskontrakt och senare syntetisk testplan
är dokumenterade, inte implementerade. Inga AIS-tester påstås körda.

Tidvattenkrav behåller vertikalt referensdatum; stationsström behåller rå fart/
riktning/djup/bin och får inte extrapoleras regionalt utan verifierad modell.
OpenWaters officiella API/käll-/licensdokument granskade separat för AIS,
tidvatten och ström med länkar i openwaters-review.md. Regional kvalitet för
ännu ej vald testregion är inte verifierad; kommersiella rättigheter kräver
produktspecifika besked. AIS-tierkapacitet har olöst8-vs32-dokumentationsskillnad.
Inga konton/token/tjänster, leverantörskontakter eller dataintegrationer skapade.

Dokumentationsdiff och lokala länkar verifierade; endast denna scope och egen
loggpost stagas. Kod oförändrad sedan väderleveransens170 godkända tester/CI.
Nästa verifiering: normal push och GitHub CI på slutlig dokumentations-SHA.
Orelaterade76 lokala loggrader bevaras ostagade. Inga databasanrop/ändringar,
serverkonfigurationsändringar, betalda resurser eller main-merge.
Huvudprioriteten förblir väderrouting, ström, komfort och avgångstider.

## 2026-10-12: HTML-visning av frysta syntetiska scenarier

Leverans på development/scenario-demo från development/segment-weather.
Separat HTML/CSS-layout och presentationslager visar kandidater, endast
accepterade delbanor, hinder, avgång, restid, ankomst och syntetisk komfort.
Fem scenarier skiljer verifierade modellgränser, konstaterat överskridande och
otillräckligt bevis/data. Ingen verifierad rutt betyder inte att andra rutter
är omöjliga. Datasetversion, fryst klocka, uppskattad båt och SHA-256 visas;
JSON-exporten bevarar ursprunglig rapport. Ingen editor vald; AIS lågprioriterat.

Verifierat: make check passerar 178 Python-tester (146 domän +32 övriga,
inklusive 8 rapport/exporttester), AST/domängränser och lokala HTML/CSS-kontroller.
Node-testkörningen har 0 tester, inte 178 frontendtester. Diff granskad;
inga nya paket, nätverksanrop i beräkningen, databasändringar eller main-merge.
Äldre 76 lokala arbetsloggrader bevaras separat och ingår inte i leveransen.

Endast genererad index.html kopierad till /home/web/seaparser/public.
Storlek 1002510 byte; SHA-256 f6499d63fdf3e84381810538570cbb3f98862e69cecaa855127072b7e9af51e2
överensstämmer med exporten. Inga konfigurationsfiler/loggar/nycklar kopierade.
HTTPS på https://seaparser.com/ och /index.html svarar 403; offentlig åtkomst
är alltså inte verifierad som fungerande. Föräldrakatalogen seaparser har 750,
public 755, index.html 644. Detta kan orsaka åtkomstfelet men är inte bevisad
serverdiagnos. Inga rättigheter eller webbserverinställningar ändrade.
Nästa steg: verifiera push-CI och rapportera åtkomsthindret för serveransvarig.

## 2026-10-12: Planeringskrav och automatisk syntetisk polygonrouting

Leverans på development/polygon-routing från development/scenario-demo.
Produktkrav/backlog prioriterar geografisk routing före AIS/presentationspolering;
planeringsflödet är sjökortsnära granskning och waypointöverföring till plotter,
utan GPS-följning. Kartbakgrund separeras från versions-/kvalitetsmärkt
hinderunderlag för land/öar/grund/djup/restriktioner. Djupgående och marginal
planeras; okänt djup är unknown och tidvatten kräver kompatibla höjdreferenser.
Geografiska koordinater, karta och GPX är förberedda som nästa leveranser;
verkliga källor kräver täcknings-/licens-/kostnadsgranskning före integration.

Implementerat: frysta enkla, även konkava, syntetiska polygoner; exakta rationella
predikat för hela slutna segment och euklidisk marginal på lagrade lokala tal.
Hårda förbud skiljs från informationspolygoner. Begränsad synlighetsgraf vid
utvidgade boxhörn genererar kompletta vägar i geometrisk ordning. Befintlig
vind/ström/polar/komfort och tidsberoende rutt-/avgångsmotor utvärderar samtliga
kandidater med samma frysta dataset; ingen sammanslagning av geografiska tillstånd.
Numeriska färdsegment och faktisk ankomst kontrolleras fortsatt. Sökbudget,
trunkering och orsak följer JSON; ingen global geometrisk/väderoptimalitet.
Metod och avgränsningar finns i geographic-routing.md. CLI: scripts.plan_polygon.

Verifierat: make check passerar 193 Python-tester (158 domän +35 övriga),
inklusive 15 nya geometriska/sök-/integrationsreferenser; Node har 0 tester,
HTML/CSS-, syntax-, konfigurations-, låsfil- och domängränskontroller passerar.
Tester omfattar konkavitet, kant-/marginalkontakt, 3–4–5- och diagonalreferenser,
hela segment, flera hinder, sökbudget och begränsad generatorläsning. Tidsberoende
ström ger längre geometrisk väg som snabbare alternativ. Fryst prognos/polar,
väderöverskridande/dataluckor och ankomstkontroll verifieras med automatgenererade
vägar. Två CLI-körningar ger byteidentisk JSON. Diff/whitespace granskade.
Äldre 76 lokala arbetsloggrader bevaras och tas inte med i committen.
Inga nya paket/konton/betalningar, databasändringar, publiceringar eller main-merge.
Nästa steg: verifiera push-CI för exakt commit; därefter begränsad geografisk
koordinatadapter och waypointexport enligt dokumenterade kontrakt.

## 2026-10-12: Geografiska koordinater → API → interaktiv karta → GPX

Sammanhängande leverans på development/geographic-api-map från polygonroutingen
3573814 (CI godkänd). WGS84 AEQD vid 58°N 11°E, högst 1000 m projektionstöd;
syntetiskt prognosområde -50…150 m öst/-50…50 m nord. Referenstoleranser och
axelordning är dokumenterade i geographic-api-demo.md. Befintlig motor,
polygon-/marginal-, prognos-, väder- och ankomstkontroller behålls.

FastAPI validerar och lämnar planering till applikationslagret och separata
killbara barnprocesser: 2 aktiva jobb, 20 s/job, 8 jobb/300 s, 8192 byte kropp
samt fasta domänbudgetar. Leaflet visar geografiska kartval, kompletta kandidater,
accepterade delbanor, hinder/marginal, vägpunkter, resultat och avbrottsorsaker.
GPX 1.1 rte/rtept exporterar planerade modellvägpunkter med rätt lat/lon/ordning,
ingen GPS/AIS. Syntetisk lokal bakgrund väljs för demon; OpenSeaMap/OpenWaters
utvärderade från aktuella officiella sidor i map-sources.md, inget verkligt
routingunderlag eller hosted tile-policy antas utifrån kartbilder.

Verifierat: riktade tester under utvecklingen och en slutlig make check efter
ändringar passerar 201 Python-tester (158 domän +43 övriga) och 4 frontendtester.
Helhetsprovet kör faktiskt loopback-FastAPI och barnprocess, kartklick och riktig
Leaflet i jsdom, ruttvisning och hämtad GPX. Detta är inte en visuell browseraudit.
Koordinatreferenser omfattar separat geod-direktlösning och meridianintegral;
API-tester avvisar ogiltiga positioner/gränser/stora kroppar, 429, väderfel och
GPX för avbrutna rutter. Tidsgräns dödar/återtar process, även vid avbrott under
start. Lås-/pip-/HTML/CSS-/domängränskontroller passerar. Beroenden installerade
endast i .venv/frontend, exakta officiellt verifierade versioner/hasher/integritet.

Deployment/systemtjänst och Apache-proxy är konkreta filer i deployment/.
systemd-analyze verify passerar; en varning gäller värdens befintliga XFS-slice,
inte den nya filen. Inget installerat/aktiverat i systemet. Ny frontendbuild
ligger bara i frontend/dist, inte i public. API endast tillfälligt på loopback
under avslutade tester; inga tjänster lämnas igång. Ingen databasändring,
ny extern publicering, kostnad eller main-merge. Äldre 76 lokala arbetsloggrader
bevaras separat. Nästa steg: verifiera push-CI för exakt commit; offentlig demo
kräver samlat administratörs-/publiceringsgodkännande enligt deployment/README.md.

### CI-korrigering för geografisk demo

Första pushen 0eb899b avvisades före jobbstart (run 38293317529, inga jobb/checks).
Workflow hade ett ociterat installationskommando med kolon följt av mellanslag
(--only-binary=:all: -r), vilket är ogiltigt som YAML-plain scalar. Kommandot
är ändrat till YAML-block. Lokal workflowkontroll upptäcker nu samma feltyp.
Riktad verifiering med scripts.check passerar 201 Python-tester och samtliga
backend-/lås-/domänkontroller. Kartkoden är oförändrad från godkänd lokal
helhetskontroll. Uppföljningscommit pushas utan force-push; exakt CI följs igen.

### CI:s npm-version

Run 38293506158 startade men npm ci avvisades med EBADENGINE: runnerns npm var
10.9.4 medan projektets låsta version är 9.2.0. CI kör nu exakt npm 9.2.0 med
npm exec i isolerad verktygscache, från repositoryroten, utan global installation
eller ändrade projektversioner. Officiell registryversion/Node-kompatibilitet
verifierad. Exakta CI-kommandon för npm ci, check och test passerar lokalt,
inklusive alla 4 frontendtester och kart/API/GPX-flödet. Backend är oförändrad
från 201 godkända tester. Ny korrigeringscommit följs med förnyad exakt CI-kontroll.

## 2026-10-12: Godkänd offentlig aktivering – root-steg förberedda

Användaren godkänner systemtjänst, SeaParser-/api/-proxy och interaktiv frontend.
Ingen ändring av rättigheter/TLS/privat konfiguration/databas tillåts; 403 är löst.
Verifierat som seaparser: port8765 ledig, proxy/proxy_http ej laddade men tillgängliga,
seaparser-api ej installerad. Befintlig HTTPS-visning svarar200 och är byteidentisk
med backup. Publik JavaScript-MIME är korrekt.

Backup utanför webbroten: /home/web/seaparser/backups/activation-20261012-c6b0b4f/.
SeaParsers Apache-konfiguration och hela tidigare publika visningen kopierade och
hashverifierade innan förändring. apache-ready.conf ändrar endast en Include-rad
i rätt HTTPS-vhost; TLS och övrig konfiguration bevaras. originals.sha256 stoppar
aktivering vid ändrad ursprunglig Apache/index. Inga nycklar/app.env kopierades.
13 genererade publika resurser kopierade av seaparser och byteverifierade via HTTPS;
gamla index.html behålls tills root-skriptets API/proxykontroller passerar.

deployment/activate-demo.sh har exakta absoluta vägar, port/hash-/root-kontroll,
modulaktivering, systemtjänst, configtest före reload, lokal/publik health,
indexbyte sist och faktiskt publikt kartklick/API/Leaflet/GPX-prov via HTTP/DOM.
Vid fel efter ändringsstart återställs Apache/index och tjänsten stoppas.
deployment/rollback-demo.sh återställer samma filer med configtest före reload;
ingen chmod/chown eller radering/global avaktivering av moduler. Underlag i
 deployment/README.md. Root-skripten har inte körts av agenten.

Verifierat: bash-syntax och slutlig make check, 201 Python +4 frontendtester godkända.
Nya HTTP/DOM-verifieringsläget passerar mot en tillfällig loopback-demoserver,
som sedan stoppats; ingen visuell browseraudit. Äldre 76 lokala loggrader bevaras.
Kvarstår: administratören kör exakt root-kommandot; därefter verifieras aktiv
systemtjänst och faktiskt publikt API-/kart-/GPX-flöde. Ingen root-/TLS-/DB-ändring
har utförts och offentlig API-aktivering får inte rapporteras som klar ännu.

## 2026-10-12: Deployment-retry och Node EACCES

Aktuell branch development/geographic-api-map och äldre 76 ostagade loggrader
kontrollerade/bevarade. Exakta yttre runuser-kommandot kräver root; agenten är
UID1000 och kan inte köra det. Exakta inre env/node --test-kommandot från app/
startar alla tester utan EACCES. Publikt kartprov underkänns korrekt eftersom
rollback återställt gamla index.html; det rapporteras inte som godkänt.

Utanför sandboxen verifierat: spawnSync /usr/bin/node --version fungerar med
ärvd cwd och explicit app/, men explicit cwd=/root ger EACCES. Node v22.22.1:s
inbyggda testkörare anger uttryckligen cwd=process.cwd() vid spawn. Agentkontext:
uid1000, execPath=/usr/bin/node, cwd=app/, NODE_OPTIONS/NODE_PATH frånvarande.
Inga kompletta miljöer/hemligheter dumpade. Root-försökets verkliga cwd loggas
nästa gång; activate-demo.sh byter uttryckligen till app/ och kör kontextprobe
samt hela oförkortade node --test med standardisolering. Inga Node-rättigheter
ändrade, inga test-/isoleringsflaggor används för att kringgå felet.

Aktuell Apache innehåller användarens korrigerade Directory-block: AllowOverride
None, hemmakatalog nekad och endast public tillåten. Ny byteverifierad retry-
backup: /home/web/seaparser/backups/activation-retry-20261012-81522f7/.
Kandidaten skiljer endast en API-Include-rad. Retry/rollback använder denna
snapshot och återinför aldrig gamla bredare regler. TLS/privata filer/DB orörda.
Befintliga service/proxyfiler är byteidentiska med föregående deploymentunderlag;
preflight tillåter saknad eller exakt identifierad vanlig fil, stoppar vid
avvikelse/symlänk och skriver inte om identiska installerade filer.

Verifierat: tre nya oberoende retry-/konfigurationsreferenser och full make check:
204 Python (158 domän +46 övriga), 4 frontendtester, bash-syntax/domän-/lås-/
konfigurationskontroller godkända. Hela HTTP/DOM-kart/API/GPX-provet passerar mot
avslutad loopback-demo. Publik slutverifiering kräver nästa root-aktivering och
kvarstår uttryckligen. Korrigeringen pushas och exakt CI följs. Root-kommandot
är /usr/bin/bash /home/web/seaparser/app/deployment/activate-demo.sh.

## 2026-10-12: Slutligt retry-underlag med ägarskap och aktiveringsordning

Användaren bekräftar exakt deploymenttest utan EACCES: 3 tester passerar och
indexkontroll avvisar korrekt den gamla statiska sidan efter rollback.
Förväntad frontend/testbytes och Node-rättigheter är oförändrade.
Skriptets ordning är verifierad: API/proxy, health, nytt index och därefter
hela HTTPS-kart/API/GPX-provet med node --test; inget publikt prov kringgås.

Skrivskyddat verifierat utanför sandboxen: kvarvarande /etc/apache2/seaparser-api.conf
och /etc/systemd/system/seaparser-api.service är vanliga rootägda filer (UID0/GID0,
644) med tidigare verifierat deploymentinnehåll. Tjänsten är inactive och port8765
ledig. Apache matchar korrigerad retry-backup och behåller AllowOverride None,
Require all denied för hemmakatalog samt grant endast för public/.

Preflight kräver nu också rootägarskap för befintliga installerade filer samt
snapshotens fasta deploymentidentitet och SHA-256-kvitto. Kandidatens Apache
måste vara exakt backup plus en Include-rad. Fel ägare, innehåll, symlänk eller
kvitto stoppar före systemändringar. Identiska filer återanvänds utan omskrivning.
Backupen ligger fortsatt i activation-retry-20261012-81522f7; inga nya snapshots
skriver över korrigerade regler. Privata filer, TLS och databas lämnas orörda.

Verifierat: 4 riktade deploymentreferenser och full make check, 205 Python
(158 domän +47 övriga) samt 4 frontendtester godkända; bash-/lås-/domänkontroller
passerar. Commitinnehåll granskas och push-CI följs. Tidigare 76 lokala loggrader
bevaras ostagade. Nytt samlat root-försök: /usr/bin/bash
/home/web/seaparser/app/deployment/activate-demo.sh. Offentlig slutverifiering
kvarstår tills detta körts; agenten har inte rootbehörighet eller aktiverat tjänsten.

## 2026-10-12: Bekräftad aktivering och isolerad verklig landgranskning

Användaren bekräftar att offentlig aktivering och visuell kontroll lyckats.
Detta är användarbekräftat; ingen ny serverkonfiguration eller återaktivering
utfördes i denna leverans. Privat konfiguration, TLS, rättigheter och databas
är oförändrade.

Arbetet ligger på development/real-map-data i /tmp/seaparser-real-map-data,
med egen venv/node_modules. Aktiv checkout och dess orelaterade lokala
progress-ändringar bevaras. Vinga-utdraget fryser sex OSM-landringar med
källhash/version/tid och ODbL-attribution. Separat granskningsexport visar
land, konservativa routinghöljen och opt-in OSM-bakgrund. Okänt djup och okänd
fullständighet markeras. Befintlig syntetisk demo behålls oförändrad.

Riktade sex tester passerar: oberoende hullreferens, punktinneslutning,
hela segment/marginal/omväg, WGS84 mot geodesisk referens, öppna ringar,
frysta indata och offentlig exportallowlist. Hela sviten och CI följer nedan.
Nästa steg: integrera fryst regionalt prognosunderlag/API-ruttjämförelse;
land-/bakgrundsgranskningen ändrar inte den publika demonstrationen.

Verifiering: 211 Python-tester (158 domän + 53 övriga) och 5 frontendtester
passerade. Första sandboxkörningen stoppades i frontendprocessen. En efterföljande
körning hittade att egna granskningsfiler låg i syntetiska dist; detta rättades
med separat frontend/land-dist, utan att ändra regressionstestets allowlist.
Full `make check` passerade efter denna rättning (exit 0). `make land-preview` genererar
endast publika granskningsresurser; inget kopierades till /home/web/seaparser/public.

## 2026-10-12: Regional Vinga-planering via API, karta och GPX

development/real-map-data fortsätter i /tmp/seaparser-real-map-data. Läste
AGENTS.md och backlog; aktiva /home/web/seaparser/app, offentlig webbrot,
privata filer, rättigheter, TLS, tjänst och databas lämnas orörda. Tidigare
lokal progress-ändring i aktiva checkouten bevaras.

Profilen vinga kopplar sex frysta OSM-landhöljen till befintlig motor och fryst
seaparser-estimated-vinga-weather / vinga-v1-baseline (uppskattat syntetiskt
väder, inte aktuell prognos). Samma frysta planeringstid, dataset, polar och
hårda gränser används för två avgångar. Begränsad graf söker högst två
kandidater/1000 expansioner; 30 s integration med tidigare hela-segmentbevis.
Top-level-identitet inkluderar landfilens SHA, väder/routingindata och projektion.
Djup och landfullständighet är fortsatt unknown; navigational_safety är
not_assessed även för en genomförd kandidat med verifierade modellgränser.

`make land-preview` bygger en separat publik allowlist i frontend/land-dist.
Lokalt: `.venv/bin/python -B -m scripts.local_demo --profile vinga --port 8766`
(ledig port), därefter http://127.0.0.1:8766/vinga.html. Endast loopback.
Kartan skiljer ursprungliga landringar, konservativa höljen och opt-in-bakgrund.
Vald marginal visas från början och vid ändring/zoom som ungefärlig kantbredd;
beräkningens avståndskontroll sker i lokala meter. GPX märks med syntetiskt
väder, okända djup/fullständighet, landversion/SHA och ODbL-attribution.

Riktade 12 Python-tester passerar (land/region/API). De kontrollerar att direktväg
korsar land, att hela planerade och accepterade omvägssegment undviker land med
10 m marginal, godkända ankomster vid båda avgångar, GPX-koordinater/varningar,
väderöverskridande och dataluckor utan export, blockerad landposition utan rutt,
region-/arbetsgränser och frysta metadata. Lokal HTTP/kartintegration passerar:
serverar genererade HTML/JS/data, kartklick → process → rutt → GPX, därefter
väderavvisning utan exportlänk. Ingen tilehämtning sker i automatiska tester.
Första karttestet förbrukade 120 accelererade pollingförsök innan regionala
jobbet var klart; rättades till klientens ordinarie 250 ms intervall. Ingen
produktgräns eller testförväntan kring väder/ankomst/export sänktes.
Full kontroll och exakt GitHub-CI verifieras före slutredovisning.

Begränsningar: konvexa höljen kan stänga verkliga passager, källfullständighet
är okänd, inga djup/grund/restriktioner utöver fryst land finns. Två grafkandidater
är ingen global bästa väderrutt. Syntetisk komfort/polar och lokalt plan är
uppskattade testmodeller. Ingen navigationssäkerhet eller plotterkompatibilitet
påstås. Offentlig demonstration byts inte ut i leveransen.

Slutkontroll: `make check` exit 0, 217 Python-tester (158 domän + 59 övriga)
och 6 frontendtester godkända. `git diff --check` passerade. Åtta offentliga
HTML/JS/CSS-filer jämfördes byte för byte med aktiva tidigare byggartefakter:
identiska. Aktiv checkout har fortsatt endast sin tidigare docs/progress.md-
ändring. Leveransens diff granskas och hemlighetskontrolleras före staging/commit;
GitHub-CI för exakt pushad commit rapporteras i slutredovisningen.

## 2026-10-12: Verkliga Vinga-prognosreferenser och uttrycklig kvalitetsgräns

Läste AGENTS.md, backlog och kartkällornas dokumentation. Fortsatt i isolerad
checkout på development/real-map-data. Aktiva publika demonstrationens kod,
webbrot, tjänst, privata filer, rättigheter, TLS och databas är orörda.

Officiell granskning jämför SMHI SNOW, MET vind/hav, Copernicus Baltic PHY/WAV
och Open-Meteo: docs/forecast-sources.md. SMHI/MET öppna punktdata kan sparas
med CC BY-attribution utan konto/kostnad; två begränsade HTTPS-anrop gjordes.
Open-Meteos gratis hosted API tillåter inte kommersiell produktutveckling,
så inget anrop gjordes. Copernicus behöver inloggning för nedladdning enligt
aktuell dokumentation, och licenslänken gav 403; ingen import eller konto.
THREDDS-länken gick inte att verifiera med webverktyget. Gridåtkomst återstår.

Fryst verklig referens: fixtures/vinga-point-forecast-reference.json, med
råsvar, URL, UTC hämttid (lokal svarsfils sluttid), rå SHA256 och attribution.
SMHI vindpunkten ligger 11.609723/57.6395; MET havpunkten 11.5955/57.626,
båda utanför Vingas testbox. SNOW createdTime bevaras som prognosskapande
utfärdandebasis, referenceTime som starttid i råsvaret. MET updated_at bevaras
som datauppdatering; modellens utfärdandetid är uttryckligen okänd.

Utbytbara offlinepunktadaptrar normaliserar markrelativa vind-/strömvektorer
från/mot-konventioner till öst/nord, våghöjd/från-komponenter och dataluckor.
Tm02 saknas i havsvaret och förblir None; ingen nollström eller vågperiod
uppfinns. Strömdjup förblir ospecificerat. Punktadaptrar kompletterar befintliga
rutnätsadaptrar; inget artificiellt regionalt rutnät skapas från punktdata.
Tidinterpolation tillåts endast vid faktisk returnerad punkt och inom giltighet.
`python -B -m scripts.forecast_reference` avvisar regional planering före motorn
som data_unavailable; inget snabbaste/bekvämaste verkligt alternativ utses.
Detta är verkliga men otillräckliga prognosreferenser, inte fungerande verklig
regional väderrouting. Native maskat grid med Tm02/utfärdande/strömdjup krävs.

Fem nya tester kontrollerar verklig inläsning, inputimmutabilitet, oberoende
359°/1°-komponentinterpolation, ström mot-riktning, explicit ålder vid planering,
gammalt/färskt/saknat utfärdande, giltighetsgräns, dataluckor/enheter och avvisad
regional extrapolation/planering. Hela `make check` passerar: 222 Python-tester
(158 domän + 64 övriga) samt 6 frontendtester. Senare typkontroll av punkt/ålder
verifierades med riktade fem tester utan ändring i motor/API/frontend.

Offline kandidatgränsaudit (scripts.audit_candidates) använder samma syntetiska
Vinga-dataset, frysta klocka, polar, hinder/marginal och avgångar med 2 respektive
8 kandidater; API-gränsen ändras inte. Bästa restid/exponering är oförändrade i
just denna fixture: 878.214920 s/1499.690716 och 845.858496 s/1434.348747.
Båda sökningarna är trunkerade; inget globalt optimum/konvergens påstås.
Fryst granskningsresultat finns i fixtures/vinga-candidate-audit.json.
Ingen kandidatjämförelse för verkliga prognoser påstås innan datagränsen passerar.

Diff och hemlighetskontroll genomförs före commit/push; exakt CI rapporteras
vid slutredovisning. Tidigare lokal progress-ändring i aktiva checkouten bevaras.

## 2026-10-13: Godkänd Vinga-publicering förbereds, root-steg återstår

Användaren godkände Vinga-planering med verkligt land och tydligt syntetiskt
väder. Blockerad verklig prognosrouting aktiveras inte. Den tidigare syntetiska
visningen bevaras som synthetic.html. Läste AGENTS.md och deployment/README.md.
Befintlig rootägd tjänst/proxy matchar projektunderlaget; korrigerade Directory-
block har AllowOverride None, hemkatalogen nekas och endast public tillåts.
De ändras inte. Agenten är UID1000, utan sudo; system-bus är blockerad i sandbox.

Ny begränsad uppgradering i deployment/VINGA.md: separat innehållsverifierad
release, backup av hela aktuella publika visningen/tjänst/vhost/proxy före ändring,
service restart med samma beroenden, atomiska publiceringsbyten som seaparser
som bevarar ägare/grupp/mode. Index byts sist efter API health. Ingen chmod,
chown, TLS-/privat-/DB-ändring eller Apachekonfigurationsändring. Traps återställer
befintlig fungerande demo/API vid fel. Backup/release återanvänds endast vid
exakt verifierat innehåll. Avvikande symlänk/filer/adminändring stoppar.

HTTPS-testläget utökas med Vinga och tidigare syntetisk sida, faktiskt serverade
resurser, kartklick, synlig marginal, ankomst, GPX, väderavvisning och waves-lucka
utan export. Fyra nya temporära tester verifierar atomiskt byte, filattribut,
symlänks-/pendingfilskydd, Apacheändringsskydd och full publik rollback.
Verifiering, commit/CI och konkret förberedelsereceipt följer innan rootkommando.
Gridprognosutredningen är inte ersatt eller aktiverad; nya publiceringsuppdraget
prioriteras enligt användarens styrning.

Slutkontroll för publiceringsleveransen: 226 Python-tester (158 domän + 68 övriga)
och 6 frontendtester passerade, inklusive bägge lokala kartflöden och vågdatalucka.
Ny processs release-cwd verifieras även efter rootaktivering. Bashsyntax, Python-
syntax och riktade rollbacktester passerar. Rootaktivering är inte utförd;
publik HTTPS-Vinga kan verifieras först efter det förberedda rootkommandot.

## 2026-10-13: Vinga-aktivering verifierad, prognosblockerare omprövade

Arbete återupptaget i `/tmp/seaparser-real-map-data` efter kontroll av
AGENTS.md, status och commit. Branch `development/real-map-data`, commit
`5aa34e1e374ecae5f1fdc601a551c38feaa8546d`; arbetskatalogen var ren.

Den tidigare Vinga-noteringen ovan ersätts av aktiveringskvittot
`/home/web/seaparser/backups/vinga-5aa34e1e374ecae5f1fdc601a551c38feaa8546d/activation-success.json`:
`https_flow: passed`, commit `5aa34e1`, URL `https://seaparser.com/`.
Kvittot skrevs 2026-10-13 00:10:56 CEST. Förberett publiceringspaket passerar
`prepare_vinga --verify`; tidigare slutkontroll 226 Python- och 6 frontendtester
är dokumenterad som godkänd. Aktuell systemd-/publik DNS-verifiering kunde inte
göras från denna körmiljö (system-bus nekas, DNS-upplösning misslyckas), och
GitHub CLI saknas; inget nytt rootsteg eller nytt testpaket kördes.

Prognoskällorna granskades mot aktuell officiell dokumentation. Copernicus Marine
anger kostnadsfri åtkomst även för kommersiella ändamål, med attribution/citering
och produkt-DOI; nedladdning kräver autentisering. Inget konto eller dataset
skapades/hämtades. MET:s officiella Oceanforecast-dokumentation anger råa
NetCDF/OPeNDAP-modeller på THREDDS, men länkad katalogsökväg ger 404. THREDDS-
översikten anger att arkivet innehåller historiska och aktuella ocean-/isdata;
åtkomligt Vinga-dataset, mask och metadata återstår. Regional verklig planering
är fortsatt `data_unavailable`: punktreferenserna saknar regional täckning,
marin utfärdandetid och Tm02. Ingen osäker extrapolation aktiveras.

Uppdaterat `docs/forecast-sources.md` med dessa källvillkor och kvarstående steg.
Nästa konkreta steg: verifiera ett åtkomligt native forecast-grid med giltig
köridentitet, wet mask, wave period och strömdjup; därefter mappa till befintlig
ForecastDataset och låta befintlig täcknings-/vädercertifiering avvisa luckor.

## 2026-10-13: Copernicus-dataförberedelse och autentiseringsblockerare

Aktiv branch `development/real-map-data`, startcommit `593317e`.
Copernicus-katalogen verifierad mot officiella sidor: vågprodukt
`BALTICSEA_ANALYSISFORECAST_WAV_003_010` / dataset
`cmems_mod_bal_wav_anfc_PT1H-i` (DOI `10.48670/moi-00011`); fysikprodukt
`BALTICSEA_ANALYSISFORECAST_PHY_003_006` / dataset
`cmems_mod_bal_phy_anfc_PT1H-i` (DOI `10.48670/moi-00010`). Vinga täcks av
produktområdena; katalogen anger 1 nm, timvisa 00Z/12Z forecast, vågperiod,
mask/batymetri i vågprodukten och 56 vertikala strömnivåer i fysikprodukten.
Faktiska variabelnamn/uniter, validity/run-förenlighet, våg-Tm02 och maskvärden
har inte verifierats i en hämtad fil.

Avgränsad hämtning förberedd till 11.58–11.63°E, 57.62–57.65°N,
2026-10-13 12–16 UTC. Copernicus L3 NRT vind är daglig satellitobservation,
inte framtida vindprognos; full verklig rutt kräver separat forecast-wind-grid.
MET:s punktvind bevisar inte rumslig täckning. Kvarvarande luckor: gemensam
wet mask/tidskörning, värden/enheter/strömdjup samt användbar vindprognos.

Autentiseringssteg är dokumenterat i `docs/forecast-sources.md`: Toolbox 2.5.0
som seaparser, inloggning i dold interaktiv SSH-prompt och credentials i
`/home/web/seaparser/.copernicusmarine-credentials` med läge 0600. Ingen credential
har lästs eller skapats. Sandboxens DNS stoppar PyPI/Copernicus-nedladdning;
Toolbox 2.5.0 kunde därför inte installeras, och dataset, adapter och rutttester
kan inte verifieras förrän autentisering och datafiler är åtkomliga.

## 2026-10-13: Avgränsad Copernicus-hämtning och CF/offlineaudit

Worktree `/tmp/seaparser-real-map-data`, branch `development/real-map-data`,
startcommit `5756c14861be77f9807f9e6cb59b18e8a27f229a`. Användaren har installerat
Toolbox 2.5.0 och verifierat sparad autentisering; installerad version har
kontrollerats utan att credentials lästs. Rätt standardkatalog korrigerad i
forecast-sources.md. Försöket 04:55:17–04:55:19 UTC avvisades av STAC-DNS
(gaierror, exit 1); inga verkliga filer hämtades eller verifierades.

Förberett exakt `bash /tmp/seaparser-real-map-data/scripts/download-copernicus.sh`
för vanlig SSH-terminal. Sparad autentisering återanvänds; avgränsad Vinga-box,
2026-10-13 12–16 UTC, ytligaste katalogdjup, timvågor/ström och separat native
static-vågmask. Katalogversion/del/service binds och CF-namn/enheter verifieras,
strict-inside förbjuder tyst boxutvidgning. Preflight begränsar uppskattad
filstorlek/transfer; lås och timeout begränsar samtidighet/tid. Privata filer,
SHA-256-manifest, start/avslut/exit och offlineaudit sparas under
`/home/web/seaparser/autonomy/copernicus/` utanför Git.

Komponentadaptern och offlineaudit kontrollerar Tm02, från-riktning,
öst/nordström, enheter, masker/luckor, explicit strömdjup, koordinater, exakt
fem timsteg och filhashar. Tolv nya tester passerar; fyra använder syntetiska
NetCDF-filer via den lokalt installerade Toolboxmiljön. Dessa fyra hoppar över
sig när extras saknas i vanlig CI. Inga verkliga filvärden eller native
geografiska routinggrid påstås verifierade. Okänd modellutfärdandetid förblir
okänd, inget regionalt ForecastDataset skapas och regional vind kvarstår separat.

Slutlig lokal kontroll: 158 prototyp- och 80 applikations/infrastrukturtester
passerar, syntax/domängränser/installerade låsningar/pip check godkända.
Frontend statisk kontroll och urval utan lokalt API passerar. Full `make check`
blockeras i kartintegration: uvicorn får inte binda 127.0.0.1 i agentmiljön
(exit 3); inget frontendfel döljs eller test ändras för att kringgå detta.
Slutlogg `/home/web/seaparser/autonomy/logs/copernicus-python-final.log`.
GitHub nås via axiertech-connectorn för branchpublicering/CI-verifiering;
terminalens GitHub-DNS är blockerad. Exakta publicerings-/CI-kvitton lagras
separat under autonomy/logs efter publiceringen.

Autonom körning: separat underlag i `/home/web/seaparser/autonomy/`, ingen
startad tmux-server/socket eller andra utvecklingssession. Skrivskyddat
foreground-statusprov 04:49:45–04:50:05 UTC gav exit 0. Det verifierar inte
SSH-överlevnad. Exakt terminalstart för endast frånkopplingsprov:
`bash /home/web/seaparser/autonomy/start-probe.sh`; framtida explicit socket
`/home/web/seaparser/autonomy/tmux.sock`. Längre bakgrundsarbete aktiveras inte
före verifierat SSH-prov och avslutad/överlämnad prognossession.

# Copernicus-avgränsat prognosuttag 2026-10-13

Tidigare nätverksförsök i sandboxen stoppades av nätverksbegränsning. Därefter
hämtades avgränsade Copernicus-data via godkänd nätverkskörning med Toolboxens
redan sparade autentisering; inga credential-värden lästes ut eller sparades.
Fryst fixture under `fixtures/vinga-copernicus/` innehåller vågprognos,
ytström och statisk mask/batymetri med dataset/version, subset, hämtningstid,
källor, attribution och SHA-256. Kontroll av hela filerna och reproducerbar
normalisering passerar.

CF-adaptern levererar endast vågor och ytström efter kontroll av grid,
standardnamn, enheter, mask och giltighetsintervall. Den interpolerar inte
över saknade celler eller utanför grid/tid och lämnar issue time okänd. Den
vägrar därför ruttberäkning utan färskhetsunderlag; vind saknas fortsatt.
Två gånger två celler och den statiska bathymetrin är inte ett komplett
routingsunderlag. Djup, navigerbarhet och regional verklig väderrutt är inte
verifierade. Exakt avgränsning och kommandon finns i
[`forecast-sources.md`](forecast-sources.md).

Verifiering 2026-10-13: fryst audit och byte-identisk regenerering passerar;
20 riktade Copernicus-tester passerar; `make check` passerar med 88 Python- och
6 frontendtester. Loopback-integrationen krävde körning utanför sandboxen;
utan den tillåtelsen nekades lokal API-bindning och testet kunde inte starta.
Nästa steg: verifiera prognosens officiella utfärdandetid och hitta ett
regionalt vindunderlag innan någon verklig regional väderrutt kan godkännas.

## 2026-10-13: Gemensam adapter granskad och run-spärr förstärkt

Utgångspunkt autonomy/CURRENT-STATUS.md. Vid start var worktreet rent på
`c4e8f7f629b70438f1c19612552f68c2b99f07e8`, som redan hade sammanfört de
lokala ändringarna efter `d0bd906`. CI 38350537720 verifierades success för
exakt c4e8f7f. Inga nya Copernicus-uttag eller dubbla adaptrar skapades.
Alla tre frysta filhashar och byte-identisk JSON-regenerering passerar.

Granskningen fann att kompatibilitet mellan prognoskörningar endast fanns i
auditrapporten. ProductMetadata bär nu frysta planning_blockers; Copernicus
sätter explicit oförenlighets-/utfärdandespärr som inte går att häva genom ett
payloadflag eller manuella datum. Färd- och segmentberäkning avvisar detta även
utan valbar freshness-policy. Direkt offlineprovtagning bevaras för granskning.
Gemensamma giltighetstider krävs och obligatoriska giltighetsdatum kan inte vara
None. Ingen verklig väderrutt eller publik ändring följer av detta.

Samlade kontroller: 158 prototyp- och 91 övriga Python-tester passerar (249 totalt),
inklusive 51 riktade import/adapter/domäntester. Syntax, domängränser, låsningar
samt pip check passerar. Full make check når frontendintegration men lokal
API-bindning nekas av sandboxen. Ingen testkontroll har tagits bort; exakt nya
committens fulla frontendkontroll verifieras med CI före fortsatt leverans.
Logg: /home/web/seaparser/autonomy/logs/adapter-review-check.log.

Nästa begränsade uppgift efter godkänd CI: metadata för original Copernicus-
prognosfiler och dokumenterat MET Nordic forecast-grid. Behåll de befintliga
marina filerna; hämta inte samma subset igen. Regional vind, utfärdandetid,
run-förenlighet och strömmask är separata blockerare. Överlämningskvittot i
/home/web/seaparser/autonomy/ anger slutcommit, lokala ändringar och nästa steg.

## 2026-10-13: Run-spärrens CI godkänd, metadataarbete fortsatt

Commit e0e61a844a3c8d0fbacc924cc6012ba971b2ef79 publicerades på
`development/real-map-data` via GitHub-connector med vanlig fast-forward.
CI 38351219008 completed/success för exakt commit, inklusive full kartintegration
som lokal sandbox inte kunde starta. Därefter fortsatte arbetet med de separata
prognosblockerarna enligt mandatet.

MET Nordic Forecast identifierat i officiell MET-wiki som regionalt deterministiskt
vindunderlag, med konkret forecast-sökväg och dokumenterade vind-/CRS-konventioner.
Faktiska forecast-metadata och Vinga-täckning är inte verifierade. Officiell
Copernicus-dokumentation skiljer mellan originalproducerade filer och ARCO:
ytt identiskt subset är inte lösningen på saknad run-proveniens.

Förberett scripts.probe_forecast_metadata för enbart små metadataanrop och
Copernicus-filelist med dry_run/create_file_list, inga weather-värden eller
nytt Copernicus-uttag. Agentförsök 05:28:42–05:28:44 UTC gav exit 2 med nätverksfel;
rapport i autonomy/forecast-metadata-probe-20261013/report.json. Fyra nya
säkerhets-/budget-/oberoende-anropstester passerar. Fortsatt blockerare och
exakt SSH-terminalkommando dokumenteras i docs/forecast-blockers.md.
Slutlig överlämning i autonomy/HANDOFF.md anger exakt slutcommit, arbetskatalog,
lokala ändringar och nästa begränsade uppgift. Ingen publik drift ändrad och
ingen ny eller parallell Codex-utvecklingskörning startad.


## 2026-10-13: Begränsat autonomt delpass – robust metadataprobe

Startade på rent bd5600c, development/real-map-data, som seaparser.
Metadataförsök 07:15:54–07:15:56 UTC gav exit 2: MET URLError (tre anrop),
Copernicus gaierror. Inga nya marina data eller vindvärden hämtades.
Rapport: autonomy/forecast-metadata-20261013T0717Z/report.json.

Proben fortsätter nu med nästa marina produkt efter ett produktfel och behåller
lyckad transportproveniens. Tom/ogiltig CSV får inte metadata_complete=true.
Sju probetester verifierar detta samt att komplett transport behåller
planeringsblockerarna. Ingen run-identitet eller utfärdandetid antas.

Samlade Pythonkontroller: 158+98=256 tester passerar, inklusive befintliga
Copernicus- och planeringsspärrstester. Syntax, domängränser, låsningar och
pip check passerar. Publiceringstesterna gör nu sin 022-umask explicit och
återställer tidigare umask; produktion och publik demonstration är orörda.
Första samlade körningen upptäckte tre befintliga umaskberoende testfel under
passets privata 077-umask; den korrigerade samlade körningen passerar.

Alla tre frysta marina SHA-256 matchar manifestet; adapter_sample_checks=passed.
Auditen lämnar regional_routing_unavailable. Frontend run check passerar;
frontend test passerar land-review men kartintegration kan inte starta lokal
API-process. Separat socketprov ger PermissionError, Operation not permitted
redan vid socket.socket(). CI måste verifiera full integration för exakt commit.
Ingen testspärr tas bort. Loggar: autonomy/logs/metadata-probe-*20261013*.

Nästa oberoende del: granskningskontrakt för faktisk källbunden run-proveniens
eller offline metadataanalys, medan åtkomst till regional vind/marina
originalmetadata fortfarande är blockerad. Kontrollera denna commits push/CI
före nästa kodleverans. Hämta inte befintliga marina fixtures igen.

## 2026-10-13 21:41 UTC: MET-metadataformat och nytt källförsök

Aktivt auktoriserat pass, arbetsrot /tmp/seaparser-real-map-data på
 development/real-map-data. Metadataförsök 21:41:51–21:41:52 UTC gav exit 2:
MET tre URLError, Copernicus preflight gaierror. Rapport finns i
/home/web/seaparser/autonomy/forecast-metadata-20261013T2143Z/report.json.
Ingen ny marin data hämtades och feltyperna bevisar inte att data saknas.

Oberoende förbättring: MET DAS kräver Attributes-envelope; DDS och tids-ASCII
kräver Dataset-envelope. Fel sorts DAP-svar avvisas. Detta är en begränsad
transportkontroll, inte en fullständig DAP-parser eller run-verifiering.
Antagande: befintliga granskade endpoints behåller respektive DAP-envelope.
Åtta probetester passerar, inklusive båda felriktningarna och kvarvarande spärrar.
Full scripts/check.py passerar: 158+99 Python-tester, syntax, beroendelåsning,
pip check och domängränser. Frontend run check passerar. Alla tre frysta marina
hashar matchar manifestet; adapter_sample_checks=passed och routing unavailable.

Git ls-remote misslyckades med exit 128: Bad owner or permissions on
/etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf. Systemfilen är orörd.
GitHub-connectorns repo/CI-anrop ger Unknown tool; ny CI är overifierad.
Nästa uppgift: källbundet offlinekontrakt för modellrun-proveniens eller faktisk
metadataåtkomst när miljön medger det. Samma marina fixtures återanvänds och
alla planning_blockers kvarstår. Publik demonstration är orörd.

Frontend test: första körning exit 1; socket.socket() gav PermissionError i
sandboxen. Godkänt sandboxundantag för befintliga lokala tester gav exit 0,
sex frontendtester passerar inklusive syntetisk och Vinga API/karta/GPX.
Loggar: autonomy/logs/met-envelope-{check,frontend,frontend-recheck,fixture}-20261013T2143Z.*.

## 2026-10-13 21:47 UTC: granskningskontrakt för run-proveniens

Dokumenterat forecast-run-provenance.md med källbunden evidens, åtskilda tidsbegrepp,
historisk ARCO-urvalsbindning, blandade run/revisioner, regional vindgranskning
och negativ acceptansmatris. Design endast: ingen certifierare, adapter eller
ändrad planeringsspärr. Inga nya källfakta påstås verifierade offline och inga
numeriska förenlighetströsklar antas. Backlog/blockerardokument länkar kontraktet.

Verifiering: nio Copernicus-adaptertester och åtta metadata-probetester passerar;
dokumentets interna länkar och alla tre marina SHA-256 verifierade; diff check
passerar. Dokumentationsändring kräver inte ny full frontendkörning; föregående
kodleverans f589b8b har 257 Python- och sex frontendtester godkända lokalt.
Push/CI för den leveransen fortsatt blockerade av SSH-systemkonfiguration och
Unknown tool från GitHub-connectorn; denna dokumentation är oberoende arbete.
Nästa steg: gå igenom befintlig offlineaudit mot kontraktets evidensfält och
redovisa exakt vilken evidens som saknas, utan ny datatransport eller hävda spärrar.

## 2026-10-13 21:50 UTC: offline marin evidensinventering

Inventerat befintliga NetCDF-dimensioner, variabel-/attributnamn, utvalda
källattribut och råa tidskoordinater till run-metadata-inventory.json.
forecast-run-inventory.md redovisar faktiska fält och gap mot provenienskontraktet.
Båda dynamiska filer saknar forecast_reference_time/run-ID; strömfilens
creation_date=2024-11-25 17:05:11 används inte som utfärdande. Alla planning_blockers
kvarstår. Auditens framtida koppling forecast_reference_time -> issued_at
identifierad som semantikfråga; ingen kod eller befintlig referens ändras nu.

Offlineaudit passerar, alla tre hashvärden matchar, issued_at förblir null och
freeze regenererar exakt samma JSON-innehåll som reference.json. Befintliga
Copernicus-importtester körda, se autonomy/logs/run-inventory-tests-20261013T2150Z.log.
Inventerings-JSON/länkar och diff check kontrollerade. Inga nya beroenden,
väderuttag, adapterspår, databasoperationer eller publika ändringar.
Nästa oberoende del: precisera regional vinds rumsliga/maskade interpolationsstöd
innan framtida MET-import; källmetadata och push/CI fortfarande blockerade.

## 2026-10-13: regionalt vindstöd – begränsat acceptanskontrakt

regional-wind-acceptance.md beskriver befintligt 2×2×2-komponentstöd, stängda
maskgränser, segmentkontroll och separat hårdgränscertifiering. Native CRS,
rotation och lokal gridseparerbarhet måste verifieras före import. Copernicus
1 m nodtolerans överförs inte till MET eller hela-cell-bevis. Regriddingmetod
eller tolerans beslutas inte utan källmetadata/referenser. Vindmaskens betydelse
hålls separat från hav/landmask och navigerbarhet. Ingen ny adapter/kod/transport.

36 prognosdata-/kvalitets-/segmenttester och 11 hårdvädersegmenttester passerar;
dokumentlänkar och namngivna regressionstester verifierade. Logg:
autonomy/logs/wind-contract-tests-20261013T2152Z.log. Diff check passerar.
Källåtkomst och push/CI fortfarande blockerade; planning_blockers oförändrade.
Nästa oberoende uppgift: granska konkret provensbudget och säker avvisning i
befintlig metadata-probe (inklusive felrespons/redirect), utan nya datakällor.

## 2026-10-13: MET-redirect avvisas före destinationshämtning

Granskning fann att urllibs standardredirect kunde lämna den fasta URL-listan
för metadata. MET använder nu en separat opener som avvisar redirects före
nytt HTTP-anrop. Alla redirects kräver källgranskning, även tillbaka till en
metadata-URL. Feltexten innehåller inte destination eller privat query.
Detta kan avvisa en legitim källredirect tills den granskas; inget nytt endpoint
eller undantag antas. DDS/DAS/ASCII-budget och formatkontroller kvarstår.

Tio riktade probetester passerar. HTTPRedirectHandlers faktiska felhantering
för 301/302/303/307/308 testas offline: destinationsopener anropas aldrig.
Separat test visar att ett redirectfel bevarar oberoende MET-resultat och alla
tre planeringsblockerare. Den verkliga MET-openern har enbart den avvisande
redirect-handlern. Inget nätverksförsök eller nytt väderuttag görs i dessa tester.
Ingen routing, adapter, databas eller publik demonstration ändras.

Full scripts/check.py passerar: 158+101=259 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar; full frontendintegration
var oförändrad och godkänd med sex tester i passets första kodleverans.
Alla tre marina hashvärden matchar fortfarande manifestet. Logg:
autonomy/logs/met-redirect-check-20261013T2154Z.log.
Nästa oberoende granskning: metadata-probens CSV/bytesbudget och partiella
transportproveniens; inga nya källor eller hävda planning_blockers.

## 2026-10-13: CSV-läsbudget och partiell transportproveniens

Metadata-probens marina CSV-läsning begränsas nu till 512001 bytes och
kontrollerar faktiskt läst antal mot 512000-bytebudgeten. Stat-kontrollen kvarstår
men räcker inte ensam när en fil växer. Överbudgetdata får ingen godkänd hash/
filräkning i rapporten. Toolboxens skapande av listfilen sker före denna kontroll;
ändringen begränsar lokal läsning, inte bibliotekets interna nätverksöverföring.

Ett under-budget-svar behåller bytes/SHA-256 även vid felaktig CSV/header/UTF-8.
Status är fortsatt blocked, file_count saknas och model_issue_time är null.
Hashen är transportbevis, inte lyckad validering eller run-identitet.
CSV läses med StringIO(newline='') så parsern får ursprungliga radgränser.
Tolv riktade probetester passerar, inklusive simulerad filväxt mellan stat/läsning
och hashproveniens för ogiltig header. Inga nya metadata-/väderanrop i testerna.
Planning_blockers och data_unavailable kvarstår. Publik demonstration är orörd.

Full scripts/check.py passerar: 158+103=261 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Logg:
autonomy/logs/metadata-budget-check-20261013T2156Z.log.
Nästa oberoende del: auditens dokumenterade modellreferens/issued_at-semantik,
med konservativ avvisning och syntetiska CF-regressioner före framtida certifiering.

## 2026-10-13: CF-modellreferens skiljs från utfärdandetid

scripts.audit_copernicus placerar inte längre forecast_reference_time i issued_at.
Dekodat scalar-värde redovisas i separat forecast_reference_time för granskning;
issued_at förblir null tills källspecifikt utfärdandebevis verifierats. Rapportens
schema 1 får ett additivt diagnostikfält; fryst adapterpayload ändras inte.
Tvetydiga/odekodade referenser förblir okända. Ingen run-certifiering införs.

Tio Copernicus-importtester passerar. Nya syntetiska NetCDF-fall visar att även
lika modellreferenstid plus creation_date för ström/vågor behåller båda
utfärdandespärrarna och run-förenlighetsspärren. Dubbla referenser/numeriskt
odekodat värde ger ingen referenstid. Befintliga råfiler regenererar exakt
samma reference.json-innehåll. Inga marina data hämtade eller befintliga filer
ändrade; publik demonstration och databas är orörda.

Full scripts/check.py passerar: 158+105=263 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Logg:
autonomy/logs/reference-time-check-20261013T2158Z.log.
Nästa oberoende granskning: CF-giltighetens precision/kalender före
normalisering till sekunder; kontrollera att verkliga tidsluckor inte döljs.

## 2026-10-13: CF-giltighet utan dold sekundtrunkering

Auditens exakta timsteg kontrolleras nu mot ursprungliga dekodade datetime-värden
innan normalisering till sekunder godkänns. Icke-datetime-giltighet avvisas;
subsekundförskjutning får inte bli ett till synes korrekt timsteg. Ingen
tidsmässig tolerans antas. Modellreferensdiagnostik bevarar delsekunder, medan
hela sekunder behåller tidigare format. Utfärdandetid/run förblir overifierade.

Tolv importtester passerar, inklusive förskjutning av en inre tid och av alla
tider med 250 ms samt bevarad .250-sekundprecision i syntetisk modellreferens.
Första riktade körningen fann en formateringsregression (auto gav minutformat);
formatet korrigerades och slutkörningen passerar. Befintliga verkliga marina
tider kontrollerade utan nätverk: alla fem ligger exakt på hela sekunder i
båda dynamiska produkter. Befintlig reference regenereras identiskt.
Inga nya marina filer, adaptrar, beroenden, databasoperationer eller publik ändring.
Logg autonomy/logs/cf-precision-targeted-20261013T2200Z.log.

Full scripts/check.py passerar: 158+107=265 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Logg:
autonomy/logs/cf-precision-check-20261013T2200Z.log.
Nästa oberoende möjlighet: ett avgränsat metadata-only åtkomstförsök med
sandboxundantag prövat av auto-review, eftersom tidigare fel var från den
begränsade nätverksmiljön; ingen ny marin väderfil får hämtas. Vid avslag eller
fortsatt källfel: dokumentera exakt resultat och fortsätt offlinegranskning.

## 2026-10-13: MET-metadata nådd med godkänt sandboxundantag

Granskat metadata-only försök gav tre faktiska MET-svar: DDS/DAS/tids-ASCII.
Metadatafixture och granskning finns i fixtures/met-nordic-metadata och
met-nordic-metadata-review.md. 1796×2321 Lambert-grid med sfärradie 6371000 m,
59 timsteg och explicit modellreferens 2026-10-13 00Z återfunna. Ingen faktisk
höjdkoordinat/cell_methods, regional cellgeometri eller utfärdande verifierade.
Inga vindvärden eller nya marina data hämtade. Alla planning_blockers kvarstår.
Nästa steg är begränsad native koordinatgranskning, inte vindadapter/routing.

Övergripande metadataförsök slutade exit 124 vid 180 s-gränsen under Copernicus-
steget. Ingen marin CSV eller report.json skapades; orsaken inom det steget är
inte verifierad. MET:s tre lyckade svar bevarades och hash-/bytekontrollerades.
Partiell arbetsrapport autonomy/met-source-partial-result-20261013T2205Z.json.
Tolv metadata-probetester passerar; lokala dokumentlänkar kontrollerade.
Tidigare kodcommit 080483b har 265 Python-tester och frontend check godkända.
Ingen kod ändras i denna metadata-/dokumentationsleverans.

## 2026-10-13: verkliga MET-koordinater och lokalt representationshinder

Auto-review-godkända koordinatanrop gav native x/y (43241 bytes) och ett
8×7 lat/lon-subset (2120 bytes). URL-kodning rättade ett första HTTPError.
Svar/hashmanifest och geometry-review.json återanvänds i MET-metadatafixturen.
Decimal-axlar har exakt 1000 m intervall. 56 källreferensnoder jämfördes med
sfärisk LCC: maxavvikelse 0.249077 m. Lokal AEQD-diagnostik visar minst
184.738574 m maxfel för varje separerbar östaxel över detta subset; direkt
lokal gridrepresentation är blockerad. Datumekvivalens/routingstöd certifieras inte.
Ingen vinddata/adapter eller ny marin data. Alla planning_blockers kvarstår.
Nästa oberoende förbättring: checkpoint av metadata-probens delrapport före
potentiellt långsamma anrop, så timeout inte tappar lyckad proveniens.

Verifiering: fem MET-källhashar/byteantal, geometrierapportens hash, 56 nodreferenser,
rapportens nedre felgräns och dokumentlänkar kontrollerade. Tolv befintliga
metadata-probetester passerar. Logg autonomy/logs/met-coordinate-tests-20261013T2211Z.log;
verifieringskvitto autonomy/met-coordinate-verification-20261013T2211Z.json.
Ingen applikationskod ändrad; tidigare 080483b har 265 Python-tester och
frontend check godkända. Geometridiagnostiken kvalificerar inte verklig routing.

## 2026-10-13: successiva metadata-checkpoints före långsamma steg

probe_forecast_metadata skriver report.json före transportstart, före/efter
varje MET-anrop, före Copernicus preflight och före/efter varje marin produkt.
Varje skrivning sker till temporär fil som ersätter rapporten atomiskt; läsaren
får föregående eller nytt fullständigt JSON, inte en avsiktligt halvskriven rapport.
Detta är processavbrottstålighet, inte ett påstående om hållbarhet vid strömavbrott.

attempt_status=in_progress, active_step och finished_at=null anger ofullständigt
försök; det bevisar inte i sig timeout eller att processen fortfarande kör.
Extern exitkod behövs för avslutsorsaken. metadata_complete förblir false tills
samtliga steg avslutats och transportkriterier passerar. Slutrapport anger
attempt_status=finished även vid källfel, med metadata_complete=false vid luckor.
In_progress för en marin produkt får aldrig räknas som lyckad listning.

Fjorton probetester passerar. Simulerat avbrott före första MET-svaret ger
läsbar initial checkpoint; avbrott under andra marina produkten bevarar samtliga
MET-resultat och första marina produktens hash. Alla planning_blockers kvarstår.
Inga nya nätverksanrop/väderfiler, beroenden, adaptrar, databas eller publik ändring.

Full scripts/check.py passerar: 158+109=267 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Tre marina och fem
MET-källhashar är oförändrade. Loggar:
autonomy/logs/metadata-checkpoint-check-20261013T2213Z.log och
metadata-checkpoint-targeted-20261013T2213Z.log.
Nästa begränsade del kan pröva endast marin metadata-listning med progress-
checkpoints och kort tidsgräns, utan upprepning av MET eller marina väderuttag.

## 2026-10-13: oberoende marina metadataförsök och produktval

Ett metadata-only försök utan MET gav exit 124 efter 75 s med bevarad
checkpoint active_step=copernicus:waves. Samma befintliga metadatafunktion kan
nu välja product=waves eller current separat; andra val avvisas före transport.
Default är fortsatt båda produkter. Dataset/version, create_file_list+dry_run,
512 KB-läsbudget och checkpoints ändras inte. Ingen ny adapter eller källväg.
Ett separat current-försök gav exit 124 efter 60 s med active_step=copernicus:current.
Inga CSV eller NetCDF-filer skapades i något försök. Auto-review godkände de
avgränsade anropen, inga avslag. Källans innehåll eller intern timeoutorsak
är inte verifierad; checkpoints anger yttre produktanrop, inte bibliotekets delsteg.

Arbetsrapporter: autonomy/marine-metadata-20261013T2215Z/report.json och
current-metadata-20261013T2216Z/report.json. Extern exitkod/gräns samt checkpoint-
hash i respektive execution-result.json och independent-marine-result-20261013T2218Z.json.
In_progress i rapporten betyder ofullständigt försök; efter verifierad exit 124
påstås ingen fortsatt aktivitet. Ingen bakgrundsprocess lämnas kvar.

Sexton probetester passerar, inklusive att varje val bara anropar sin produkt
med dry_run och okänt val avvisas före DNS. Full scripts/check.py passerar:
158+111=269 Python-tester, syntax, låsfiler, pip check/domängränser.
Frontend run check passerar. Logg autonomy/logs/independent-marine-check-20261013T2217Z.log.
Alla planning_blockers/data_unavailable kvarstår; marina fixtures och publik demo orörda.
Nästa oberoende diagnostik: isolera bibliotekets skrivskyddade konfigurations-/
katalogdelsteg med en egen liten tidsbudget; återupprepa inte hela listan utan ny evidens.

## 2026-10-13: isolerade Copernicus konfigurations-/katalog-/authsteg

Avgränsade steg med auto-review: versionskonfiguration exit 0 (~0.12 s),
vågkatalogmetadata exit 0 (~0.32 s, låst 202311 finns), ordinarie saved-auth-
validering exit 124 efter 25 s. Inga authvärden, privata URL:er eller fulla
felmeddelanden loggade; inga authfiler ändrade. Inga väderfiler eller listningar.
Dokumenterad kodordning gör authvalidering till konkret kandidat för tidigare
get-fördröjning, inte verifierad root cause eller bevis på ogiltiga uppgifter.
Detaljer/rapporter: [copernicus-metadata-diagnostics.md](copernicus-metadata-diagnostics.md). Alla planning_blockers
kvarstår, ingen katalogversion eller timeout används som run-bevis.
Nästa oberoende del: faktisk officiell MET-höjd-/medelperiodsemantik.

Sexton metadata-probetester passerar; diff check passerar. Ingen kod ändrad i
leveransen; föregående 02ff72a har 269 Python-tester/frontend check godkända.
Logg autonomy/logs/marine-stage-tests-20261013T2223Z.log.

## 2026-10-13: officiell MET-vindsemantik kontrollerad

MET Nordic-dokumentation beskriver vindfälten vid 10 m som 600 s medelvärden
med FRÅN-riktning norr=0°, öster=90°. Detta stämmer med befintlig DAS-identitet/
enheter. Dokumenthash och DAS-hash binds i wind-semantics-review.json; hela
artikeln kopieras inte. Medelfönstrets placering/höjdreferens förblir null.
600 s medel är separat från källans 3600 s prognossteg och får inte bli byvind
eller momentant timmax. Inga CF-bounds/height-attribut fabriceras.
Alla planning_blockers kvarstår; ingen vindimport/adapter eller nya väderdata.
Detaljer: met-nordic-metadata-review.md. Nästa del: regriddingens beviskontrakt.

Verifiering: 16 prognosdatatester och 9 Copernicus-adaptertester passerar.
Strukturerad semantik, dokument-/DAS-/granskningshashbindning, åtta källhashar
och dokumentlänkar kontrollerade; diff check passerar. Logg:
autonomy/logs/met-semantics-tests-20261013T2228Z.log. Ingen kodändring;
senaste kodcommit 02ff72a har 269 Python-tester/frontend check godkända.

## 2026-10-13: beviskontrakt före gridomvandling

forecast-regridding-proof.md skiljer uppskattade simuleringstal från konservativa
hårdgränshöljen, kräver hela transformerade cellstöd och källmask-/tidsstöd samt
versions-/hashbindning. Ingen omvandlingsmetod/tolerans eller adapter vald.
Exakta syntetiska motexempel i regridding-counterexamples.json visar dold 20 m/s-
topp bakom nollmålknutar (gräns 10) samt maskat inre intervall bakom giltiga
ändpunkter. Fraction-verifiering och befintliga segmentregressioner körda.
Alla planning_blockers kvarstår; inga käll-/väderanrop eller publika ändringar.

Verifiering: två exakta Fraction-motexempel, 11 segmentvädertester och 8 datastöds-
segmenttester passerar. Dokumentlänkar och diff check kontrollerade. Logg:
autonomy/logs/regridding-proof-tests-20261013T2231Z.log. Ingen kodändring;
senaste kodcommit 02ff72a har 269 Python-tester/frontend check godkända.

## 2026-10-13: reproducerbar MET-offlineaudit utan ny adapter

scripts.audit_met_metadata återanvänder granskad femfilsfixture, begränsar
läsning, verifierar hash/bytes och exakt Decimal-axel-/tidsstöd samt subsetkartor.
Geometrin räknas om mot 56 producentnoder; rapport innehåller native axlar,
giltighet och lokalt separerbarhetsfel. Ingen HTTP, vindimport eller ny domänmodell.
Manifestflaggor/datum kan inte ge routinggodkännande; issued_at förblir null.

Fem nya regressioner passerar: oberoende koordinatreferens, hashfel, felaktigt
axelsteg trots ny hash, annan projektion och falska routing/datumflaggor.
Full scripts/check.py passerar: 158+116=274 Python-tester, syntax, låsfiler,
pip check/domängränser. Frontend run check passerar. Åtta källhashar oförändrade.
Loggar autonomy/logs/met-offline-{check,targeted}-20261013T2236Z.log och
met-offline-audit-20261013T2235Z.json. Körkommando i met-nordic-metadata-review.md.
Alla planning_blockers kvarstår, inga paket/nätverksanrop/publiceringsändringar.
Nästa oberoende del: precisera tids-/referensdiagnostik och säkra felgränser i
offlineaudit, eller negativa källstödstester enligt regriddingkontraktet.

## 2026-10-13 22:40 UTC – MET-tidsstruktur offline

Förstärkt den befintliga metadataauditens DDS/DAS/ASCII-kontroller, utan ny
adapter eller datahämtning. Källans modellreferens redovisas separat från
utfärdandetid. Fem nya negativa regressioner kontrollerar fel tidsenhet, DDS-
dimensioner, saknad/dubbel skalär och ändrad källreferens även med nya hashar.
Alla planning_blockers kvarstår; issued_at=null och data_unavailable.
Verifiering: tio riktade tester och full scripts/check.py passerar
(158+121=279 Python-tester, syntax, pip check, låsfiler och domängränser).
Frontend run check passerar. Fem MET-källfiler och tre marina NetCDF-filer
är oförändrade. Loggar: autonomy/logs/met-time-structure-check-20261013T2240Z.log
och met-time-structure-frontend-20261013T2242Z.log; JSON-diagnostik
met-time-structure-audit-20261013T2240Z.json. Nästa oberoende del:
negativa källstödstester enligt regriddingkontraktet eller auditens felgränser.

## 2026-10-13 22:43 UTC – käll-/målbevisets negativa referenser

Två nya domänregressioner återanvänder regridding-counterexamples.json och
befintlig GridProduct/segmentcertifiering. Glesare målfält blir verified;
källans topp ger exceeded med 20 m/s-vittne, dold sluten mask ger
unverified/data_unavailable. Båda maskgränserna och mittpunkten avvisas.
Inga runtime-/adapterändringar, nya beroenden eller datahämtningar. Samtliga
planning_blockers kvarstår.
Verifiering: båda riktade testerna och full scripts/check.py passerar
(160+121=281 Python-tester, syntax, låsfiler, pip check och domängränser).
Frontend run check passerar; källfixtures är oförändrade. Loggar:
autonomy/logs/regridding-reference-{check,frontend}-20261013T2243Z.log.
Nästa avgränsade källdel: en liten MET-native vind-/landfraktionssubset för
källgranskning, med explicita budgetar och fortsatt data_unavailable; ingen
marin återhämtning eller automatisk routingskvalificering.

## 2026-10-13 – faktisk begränsad MET-vindsubset

Frysning av 56 native noder, fem timmar 12–16 UTC och två vindvariabler samt
landfraktion/modellreferens lyckades: 7604 byte under 128 KB-budget. Råvärden,
manifest och offline-review sparade separat. Befintlig MET-audit kontrollerar
ordnade fält, dimensioner, koordinat-/tidskartor, finita värden, fysiska gränser
och källhash. Ingen marin återhämtning eller parallell adapter. Fart 11.273894–
17.250252 m/s; landfraktion inte giltighetsmask. Samtliga planning_blockers
kvarstår; utfärdandetid/run-förenlighet fortfarande okända.
Verifiering: åtta nya riktade tester och full scripts/check.py passerar
(160+129=289 Python-tester, syntax, pip check, låsfiler och domängränser).
Frontend run check passerar. Åtta tidigare källhashar verifierade oförändrade.
Loggar autonomy/logs/met-wind-sample-{check,frontend}-20261013T2247Z.log.
Nästa oberoende del: offline fel-/nodbudgeter och verifiering av källstöd
eller dokumenterad referensram/normalisering, utan att kvalificera routing.

## 2026-10-13 22:50 UTC – MET-auditens fel-/läsgränser

Befintlig offlineaudit avvisar ogiltiga läsgränser, manifeststrukturer och
tal innan fortsatt bearbetning. CLI ger data_unavailable/exit 1 med endast
felklass och utan rådata/filvägar. Sju nya negativa tester inkluderar faktisk
128000/128001-bytegräns, falskt höjd manifestbudget, NaN/Infinity/extremexponent,
saknad subset och saknad källa via verkligt subprocess-anrop. Alla 25 riktade
MET-tester passerar. Inga källanrop eller adapter-/runtimeändringar; spärrar kvar.
Full scripts/check.py passerar: 160+136=296 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Giltig vind-review
reproduceras oförändrad; nio källhashar verifierade. Loggar autonomy/logs/
met-audit-failures-{check,frontend}-20261013T2250Z.log. Nästa oberoende del:
referensrams-/normaliseringsdiagnostik på sparade vindvärden, med fortsatt
separata beviskrav för geometri, maskstöd, utfärdandetid och run-förenlighet.

## 2026-10-13 22:53 UTC – vindreferensram och native konvergens

NERC:s smala CF-post stöder FRÅN-/jordrelativ dokumentation; full CF-tabell
överskred webbverktygets svarsstorleksgräns. Ingen full producent-/målram
certifieras. Befintlig offlineaudit redovisar native LCC-meridiankonvergens
över 56 faktiskt sparade noder: -3.066815 till -2.971995 grader, med varierande
rotation. En oberoende tangent-kon-referens verifierar numeriken; ingen
vind roteras/importeras. 26 riktade MET-tester passerar; spärrar kvarstår.
Se met-wind-frame-review.md för källor, derivation, tolerans och avgränsning.
Full scripts/check.py passerar: 160+137=297 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Alla nio källhashar
och sparad vind-review oförändrade. Loggar autonomy/logs/met-frame-
{targeted-20261013T2253Z,check-20261013T2254Z,frontend-20261013T2254Z}.log.
Nästa oberoende del: granska/regressionstesta run-spärrarnas motstånd mot
ifyllda datum och payloadflaggor i befintlig marin adapter; återanvänd fixtures.

## 2026-10-13 22:57 UTC – marin utfärdandespärr

Rättat befintlig CopernicusMarineAdapter: detached issued_at kunde tidigare
fyllas och häva sin egen blockerare, medan run-spärren alltjämt hindrade routing.
Nu blir issued_at alltid null och både utfärdande-/run-spärr kvarstår tills
källbunden verifierare är implementerad. Ny negativ matris med fem datumfall
och run-/statusflaggor; tio riktade adaptertester passerar. Ingen marin
återhämtning, ny adapter eller förändring av giltighet/hämttid/katalogversion.
Full scripts/check.py passerar: 160+138=298 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar; nio källhashar
verifierade oförändrade. Loggar autonomy/logs/marine-issuance-gate-
{check,frontend}-20261013T2257Z.log. Nästa oberoende del: verifiera att
båda ruttmål och alla avgångar håller samma proveniensspärr efter import,
med syntetisk vind enbart i negativa tester för att isolera marin proveniens.

## 2026-10-13 22:59 UTC – marina spärrar genom avgång och export

Ny integrationsregression för två avgångar/två rutter, komfortpolicy, valfri
färskhetspolicy och tre avgångsurval. Alla 24 kandidatbedömningar avvisas med
run-/utfärdandeorsak; inga tids-/komfortval eller accepterade steg. JSON behåller
issued_at=null, blockerare och marina källhashar. Syntetisk vind är separat
testidentitet. Elva riktade adaptertester passerar. Ingen produktionskod ändrad.
Full scripts/check.py passerar: 160+139=299 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Nio källhashar
verifierade oförändrade. Loggar autonomy/logs/marine-departure-gate-
{check,frontend}-20261013T2300Z.log. Nästa oberoende del: bevara och
regressionstesta saknat/maskat komponentstöd i befintlig marin adapter;
produktmasker hålls separata och verklig routing förblir spärrad.

## 2026-10-13 23:02 UTC – marina stödhörn och produktmasker

Tre nya negativa adapterregressioner prövar alla fem dynamiska komponenters
saknade stödhörn samt vågmaskens land/okända värden. Interpolation avvisas
utan nollersättning; den andra produktens värden bevaras. Vågmask påverkar
inte strömvärden och kvalificerar inte strömproveniens. Fjorton riktade tester
passerar. Ingen produktionskod eller råfixture ändrad; alla spärrar kvarstår.
Full scripts/check.py passerar: 160+142=302 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Nio källhashar
verifierade oförändrade. Loggar autonomy/logs/marine-support-
{check,frontend}-20261013T2303Z.log. Nästa oberoende del: precisera faktiska
marin-/vindgridens rumsliga bindning i offlinegranskningen; endast diagnostik,
med explicit kvarstående datum-/geometri-/cellstöds- och run-spärrar.

## 2026-10-13 23:06 UTC – separata grid och numeriska utbredningar

Befintliga auditer komponerade offline för källbundna koordinattal: samtliga
åtta marina noder är numeriskt inom MET-subsettens lat/lon-extremer, men
våg/strömgriden är olika. Ingen datumlikvärdighet, cell-/segmenttäckning,
masköverföring eller regridding antas. Nio hashreferenser redovisas separat;
alla spärrar kvarstår. Fyra riktade tester passerar inklusive ändrade bytes,
överbudget och fel manifest. Ingen ny hämtning/decoder/adapter.
Full scripts/check.py passerar: 160+146=306 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Sammansatt audit
kontrollerar nio källhashar; råfixtures och tidigare vind-review oförändrade.
Loggar autonomy/logs/coordinate-extents-{check,frontend}-20261013T2307Z.log
och coordinate-extents-audit-20261013T2307Z.json. Nästa oberoende del:
precisera dokumenterade marine run-/utfärdandebegrepp från officiella
produktmanualer, utan att intyga bindning till det historiska ARCO-uttaget.

## 2026-10-14 – rättning av CI för 6a13485 / 38507580572

Kontrollerat först att femtimmarspasset är avslutat: finished_with_blocker,
ingen tmux-server och inget aktivt run-/launch-lås. Äldre interaktiva Codex-
sessioner och en kvarhängande testprocess från 12 oktober observerades; inget
aktivt utvecklingspass identifierades. Inga andra processer stoppades.

Användarens CI-fel reproducerades i ny CPython 3.14.4-venv med enbart tidigare
requirements.lock: två koordinattester gav ModuleNotFoundError för numpy.
Den vanliga utvecklingsmiljön hade extra Toolbox-beroenden som dolde felet.
Auditberoenden numpy 2.5.4, xarray 2026.9.0, h5netcdf 1.8.1 och h5py 3.16.0
deklareras nu som testberoenden; dessa och packaging/pandas/python-dateutil/six
hashlåses från officiella PyPI-wheels. Alla åtta releaseversioner verifierades
på PyPI. Befintliga låsta paketversioner och hashvärden är oförändrade.
Audit och fixture-export väljer explicit HDF5-dekodern h5netcdf. Två äldre
beroendevillkorade NetCDF-skips är borttagna. CI:s befintliga installation av
hela låsfilen och scripts.check-discovery kör båda integrationsmodulerna.
Karttesternas Pythonval accepterar PYTHON så även deras API körs i ren venv.

Verifiering: den rena miljön innehåller exakt 26 låsta paket samt venvs pip,
include-system-site-packages=false; ingen Toolbox eller extra NetCDF-backend.
Fyra koordinattester och tolv Copernicus-tester passerar utan skips.
Samlade make check med PYTHON=/tmp/seaparser-ci-clean/bin/python passerar:
160+146=306 Python-tester, syntax, låsningar, pip check, domängränser,
frontendkontroll och sex frontendtester, inga skips. Frontend installerades
med npm ci --ignore-scripts. Första frontendkörningen i sandboxen fallerade;
hela sviten passerade utanför sandboxen med lokalt loopback-API.
Loggar /tmp/seaparser-ci-{missing-deps,clean-install-fixed,clean-check-final}.log.
Diff granskad; ingen ny funktion, råfixture, routingkvalificering, publicering
eller databasändring. Nästa steg: push och kontrollera Actions för exakt ny
commit. GitHub-anslutningens läsverktyg svarar Unknown tool och oautentiserad
Actions-API ger 404 för privat repository; godkänd CI får inte antas.

## 2026-10-15 – regional koppling av fryst native vind och marin data

Användaren verifierade CI completed/success för exakt c5c317c947fbaecf19a69b889013219e2b8aae72,
körning https://github.com/axiertech/seaparser/actions/runs/38532032973.
Process-/låskontroll före ändringar visade inget annat aktivt utvecklingspass;
äldre interaktiva sessioner och kvarhängande gammalt test observerades, inga
processer stoppades. Publik demonstration lämnas oförändrad.

Implementerat scripts.regional_forecast som läser befintliga hashkontrollerade
MET-/Copernicus-källor till RegionalForecastInputs i applikationslagret.
Vindens 5×8×7 hastigheter/riktningar, native x/y, UTC-tider och landfraktion
materialiseras som frysta tupler med ursprungliga Decimal-värden; ingen
regridding, vektorrotation eller antagen WGS84-likvärdighet. Befintlig
MET-parser återanvänds; tidigare auditrapport är oförändrad. Marina värden
normaliseras med befintlig adapter direkt från NetCDF, inte detached reference.json.
Alla nio källhashar binds tillsammans med faktiska värden i ett deterministiskt
indatafingeravtryck. Samma instans kan användas i nästa integrationssteg.

Gemensamt tidsstöd är 2026-10-13 12:00–16:00 UTC med exkluderad sluttid;
det är inte ett rumsligt täcknings- eller run-förenlighetsbevis. Källbunden
MET-modellreferens är 00:00 UTC; marina CF-modellreferenser/run-identiteter
och samtliga utfärdandetider förblir okända. Båda ruttval förblir null och
status data_unavailable. Spärrar för native vindgeometri/vektorram, marin
körförenlighet/utfärdande och strömmask kvarstår. Ingen regional rutt beräknas.

Kör: /tmp/seaparser-ci-clean/bin/python -B -m scripts.regional_forecast
--departure 2026-10-13T12:00:00Z. Rapport /tmp/seaparser-regional-inputs.json.
Åtta nya tester verifierar verkliga hörnvärden/ordning, oföränderlighet,
sluttidsavvisning, källbytesfel, ignorerade detached datum/flaggor,
reproducerbar CLI och fingeravtryck som även omfattar vindvärden.
Verifiering i ren låst miljö: full scripts.check passerar 160+154=314
Python-tester, syntax, pip check, låsningar och domängränser. Samlade make check
passerade före sista tillagda fingerprinttestet, inklusive sex frontendtester
utan skips; Pythonkontrollen kördes om efter tillägget. Loggar
/tmp/seaparser-regional-{check,python-final}.log. Diff granskad; inga nya
beroenden, databasändringar, externa hämtningar eller publicerade ändringar.

Nästa steg efter push och godkänd CI: verifiera källgridets faktiska
geometriska/vektoriella koppling till lokala ruttsegment; använd det nya
indataobjektet. Marin historisk run-bindning behöver producentunderlag;
gemensamma tider eller katalogversioner får inte ersätta det. GitHub-verktyget
svarar fortfarande Unknown tool vid läsförsök; ny commits CI får inte antas.

## 2026-10-16 – officiella marina körbegrepp

Begränsad dokumentationsleverans: marine-run-source-review.md granskar
PHY/BGC PUM 1.3 och WAV PUM 2.8 (11/2025), med sektion-/sidreferenser.
Analyscykel, modelltid och leveransschema hålls separata. Dokumenterad
överskrivning motiverar fortsatt krav på historisk ARCO-urvalsbindning.
Ingen faktisk utfärdandetid eller förenlighet för våra fixtures är bevisad;
alla planning_blockers och data_unavailable kvarstår. Inga nya marina
väderdata, adaptrar, beroenden, databasoperationer eller publika ändringar.

Verifiering: 8 riktade regionala tester och full scripts.check passerar
160+154=314 Python-tester, syntax, pip check, låsfiler och domängränser.
Frontend resurskontroll passerar. Tre marina råhashar och lokala dokumentlänkar
kontrollerade; regional CLI behåller null för marin run/utfärdande.
Frontendintegrationens första försök fallerade i sandboxen; separat socketprov
gav PermissionError errno 1. Befintlig loopbacksvit passerar med godkänt
undantag: sex frontendtester, inga skips, exit 0.
Loggar: /home/web/seaparser/autonomy/logs/marine-run-review-*-20261016.*.
Nästa oberoende arbete: native vindgeometri/vektorram med befintliga frysta
regionala indata. CI-läsverktyget gav Unknown tool, ingen ny CI påstås här.

## 2026-10-16 – oberoende native vindgeometri

Fyra nya referenstester härleder inversen för den granskade sfäriska
Lambert-tangentkonen utan PROJ i referensformeln. Alla 56 noder jämförs
med producentens sparade lat/lon och PROJ-inversen. Origo/symmetri/axelordning
och sfäriska native axelbäringar kontrolleras separat. RegionalForecastInputs
binds till exakt samma axlar/projektion/metadatahashar. Detta stärker
geometriregressionen utan att normalisera vind eller intyga datum/helceller.
Alla planning_blockers och data_unavailable kvarstår. Inga nya källbytes,
adaptrar, beroenden, databasoperationer eller publika ändringar.

PROJECT_BLOCKER: direkta USGS PDF-anrop gav HTTP 403; ITC-kopian överskred
webbverktygets storleksgräns. Fortsatte med självständig analytisk offlinekontroll;
fulltext påstås inte läst. PROJ:s officiella LCC-sida lästes. Detaljer och
numeriska regressionstoleranser finns i met-wind-frame-review.md.

Verifiering: fyra riktade tester och slutlig full scripts.check exit 0:
160+158=318 Python-tester, syntax, pip check, låsfiler och domängränser.
Alla nio källhashar samt dokumentlänkar kontrollerade, diff check godkänd.
Frontend är oförändrad; föregående delpass samma dag verifierade sex
frontendtester utan skips samt frontend resurskontroll. Ingen omkörning krävs
för denna rena referenstest-/dokumentationsändring. Loggar:
autonomy/logs/native-cone-{targeted,check-final}-20261016.log.
Nästa oberoende del: strikt källsemantik för vindens faktiska DAS-fält,
med negativa ändrade-enheter-/standardnamnfall även vid uppdaterad hash.

## 2026-10-16 – strikt källsemantik för native vind

Faktisk granskningslucka rättad i befintlig MET-offlineaudit: ändrade DAS-enheter,
FRÅN/MOT-standardnamn och andra semantiska attribut kunde accepteras när en
fixturekopias manifesthash uppdaterades. field_metadata kräver nu exakt de
granskade tre fältens attribut, utan dubbletter/okända tolkningar. Det fasta
uttaget granskas, ingen ny allmän DAP-parser eller adapter skapas.
Fyra nya negativa testmatriser var röda före rättningen och passerar efter den;
alla 34 riktade MET-tester passerar. Originalets regionalrapport är exakt
oförändrad mot föregående delpass, med nio hashbindningar och alla spärrar.
Inga nya källhämtningar, beroenden, databasoperationer eller publika ändringar.
Detaljer: met-nordic-metadata-review.md. Fortsatt data_unavailable.

Slutlig verifiering: full scripts.check exit 0, 160+162=322 Python-tester,
syntax, pip check, låsfiler och domängränser. Diff granskad och --check godkänd.
Loggar autonomy/logs/met-fields-{red,targeted,check}-20261016.log; red-loggen
visar den tidigare luckan, inte ett kvarvarande testfel. Frontend oförändrad;
sex frontendtester och resurskontroll passerade tidigare i samma aktiva pass.
Nästa oberoende del: granska koordinat-/projektionsattributens konsistens,
särskilt numeriska CF-parametrar kontra proj4, utan datum-/routingcertifiering.

## 2026-10-16 – konsistenta koordinat- och projektionsattribut

Rättad faktisk lucka i MET-offlineaudit: proj4 kunde finnas i ett omdöpt block
samtidigt som numeriska CF-parametrar eller koordinatenheter motsade den
använda geometrin. Befintlig attributkontroll återanvänds nu för fyra
koordinatblock och det explicit länkade projection_lcc-blocket. Exakta granskade
värden/typer och frånvaro av dubbletter/extra tolkningar krävs.
Fyra nya negativa testmatriser gav femton röda motsägelsefall före fix;
alla 38 riktade MET-tester passerar efter fix. Originalets regionalrapport
är exakt oförändrad, inklusive nio hashbindningar och samtliga blockerare.
Ingen ny parser/adapter, datumtransformation, datahämtning, beroende,
databasoperation eller publik demoändring. Fortsatt data_unavailable.

Slutlig verifiering: full scripts.check exit 0, 160+166=326 Python-tester,
syntax, pip check, låsfiler och domängränser. Diff granskad, --check godkänd.
Loggar autonomy/logs/met-crs-{red,targeted,check}-20261016.log. Frontend
oförändrad; sex tester och resurskontroll verifierades tidigare i samma pass.
Nästa oberoende del: säkra att native axlar/tider vid materialisering läses
från samma hashkontrollerade källsnapshot som metadataauditen; granska dagens
omläsning före vidare geometri-/vektorarbete. Inga run-/datumantaganden.

## 2026-10-16 – hashbundna metadata vid vindmaterialisering

Rättad konkret omläsningslucka i read_wind_sample. Native axlar och tider
hämtas nu från exakt de källtexter som metadataauditen redan hash-/byte-/
semantikkontrollerat. Intern helper delar kontrollerad läsning, publika
rapportformatet är oförändrat. Ingen atomisk flerfilssnapshot påstås.
Tre nya tester var röda före fix: samordnade ändrade vind-/metadata-kartor
kunde bära gamla metadatahashar, och borttagna källor krävde onödig omläsning.
Alla 41 riktade MET-tester passerar efter fix. Originalets regionalrapport
inklusive nio källhashar och alla blockerare är exakt oförändrad.
Inga nya källanrop, marina data, adaptrar, beroenden, databasoperationer eller
publika ändringar. Fortsatt data_unavailable, ingen run-/datumcertifiering.

Slutlig verifiering: full scripts.check exit 0 med 160+169=329 Python-tester,
syntax, pip check, låsfiler och domängränser. Diff granskad och --check godkänd.
Loggar autonomy/logs/met-snapshot-{red,targeted,check}-20261016.log. Frontend
oförändrad; sex tester och resurskontroll verifierades tidigare i samma pass.
Nästa oberoende del: granska hashkontroll kontra NetCDF-omläsning i befintliga
marina audit/freeze; samma råfiler ska återanvändas och inga nya adaptrar behövs.

## 2026-10-16 – hashbundna marina audit-/freeze-bytes

Rättad konkret omläsningslucka i befintlig Copernicus-kedja. Audit dekodade
filvägar efter hashkontroll; freeze öppnade både manifest och NetCDF på nytt.
Ny audit_snapshot returnerar granskad rapport, inläst manifest och exakt samma
kontrollerade bytes till befintlig freeze. Samma h5netcdf-dekoder via BytesIO;
ingen ny adapter. Befintlig 10 MB-källbudget verkställs med begränsad faktisk
läsning före hashning/dekodning. Okänd run/utfärdande är fortsatt okänd.
Tre nya röda regressioner före fix visar ändrade vågvärden vid audit/freeze
samt bytt manifestversion efter auditstart. Dessa passerar efter fix.
Originalets frysta providerpayload/reference.json och regionalrapport med
nio källhashar reproduceras exakt. Ett fjärde test verifierar överbudgetavvisning
före decoder. Inga nya marina hämtningar, beroenden, databas-/publika ändringar.
Alla planning_blockers och data_unavailable kvarstår. Detaljer i
forecast-run-provenance.md; ingen atomisk flerfilssnapshot påstås.

Slutlig verifiering: full scripts.check exit 0, 160+173=333 Python-tester,
syntax, pip check, låsfiler/domängränser. 35 riktade Copernicus-tester passerade
före sista budgettestet; det fjärde nya testet ingår i fullsviten och passerar.
Diff granskad, --check godkänd. Loggar autonomy/logs/marine-snapshot-
{red,targeted,check}-20261016.log. Frontend oförändrad; sex tester och
resurskontroll passerade tidigare i samma pass.
Nästa oberoende del: koppla regionala marina modellreferenser/hashar och
normaliserade värden till samma audit_snapshot i stället för separata
load_regional_inputs-audit/freeze-anrop. Behåll samtliga avvisningsregler.

## 2026-10-16 – sammanhållen regional marin inläsning

Rättad fortsatt samordningslucka: load_regional_inputs gjorde separat marinaudit
och freeze. Ny freeze_with_audit returnerar payload och rapport från samma
kontrollerade bytes/manifest; regionala modellreferenser, råhashlista och
produktvärden binds till detta underlag. Befintlig freeze och dess CLI är
oförändrade utåt. Inga detached rapporter tas emot som certifiering.
Två nya regionala fixturekopietester var röda före fix och passerar nu:
bytta vågvärden/modellreferens/manifesthash efter auditstart samt borttagna
källor efter kontrollerad läsning. Alla tio riktade regionala tester passerar.
Originalets providerpayload/reference.json och regionalrapport med nio hashar
reproduceras exakt. Samtliga planning_blockers/data_unavailable kvarstår.
Inga nya källhämtningar, marina råfiler, adaptrar, beroenden, databasoperationer
eller publika ändringar. Detaljer: forecast-run-provenance.md.

Slutlig verifiering: full scripts.check exit 0, 160+175=335 Python-tester,
syntax, pip check, låsfiler/domängränser. Diff granskad, --check godkänd.
Loggar autonomy/logs/regional-snapshot-{red,targeted,check}-20261016.log.
Frontend oförändrad; sex tester och resurskontroll verifierades tidigare i passet.
Nästa oberoende del: ett kort nytt metadata-only saved-auth-åtkomstprov med
befintlig Toolbox, eftersom senaste dokumenterade försök är från 2026-10-13.
Ingen ny marin väderfil eller hel fillistning före ny åtkomstevidens. Vid
källblockerare: dokumentera faktisk extern exit och fortsätt offlinekontrakt.

## 2026-10-16 – marin metadataåtkomst åter verifierad

Ordinarie saved-auth-validering exit 0 på cirka 2,18 s. Separata befintliga
metadata-only waves/current-listningar slutfördes på cirka fyra sekunder vardera
utan NetCDF-hämtning. Ursprungliga exit 2/blocked berodde på vår storleksvalidator:
Toolbox skriver heltalsstorlek med .0. Rättad exakt decimalregex utan float-
konvertering; bråk/negativa/NaN/Infinity/exponenter avvisas. Sexton riktade
probetester passerar, utökad matris var röd före fix. Sparade CSV återvalideras
offline via befintlig funktion: två poster per produkt, utan nya nätverksanrop.
Detaljer/hashar/filnamn i copernicus-metadata-diagnostics.md. Originalrapporterna
bevarar faktiskt blocked; separat offlinekvitto skiljer korrigerad validering.
Filnamnen bevisar inte historisk ARCO-bindning, utfärdande eller run-förenlighet.
Alla planning_blockers/data_unavailable kvarstår; inga nya adaptrar/beroenden,
authändringar, databasoperationer eller publika demoändringar.

Slutlig verifiering: full scripts.check exit 0, 160+175=335 Python-tester,
syntax, pip check, låsfiler/domängränser. Diff granskad, --check godkänd.
Loggar autonomy/logs/metadata-size-{red,targeted,check}-20261016.log.
Frontend oförändrad; sex tester och resurskontroll verifierades tidigare i passet.
Nästa oberoende del: officiell dokumentation om originalfil-/ARCO-urvalssemantik
och historisk bindning för redan sparat uttag; inga nya marina väderdata eller
påståenden baserade på filnamn/last_modified/etag. Befintliga CSV återanvänds.

## 2026-10-16 – officiell ARCO-proveniensgranskning

Ny arco-provenance-review.md sammanställer två faktiskt lästa officiella
Copernicus-artiklar. Originalfiler och ARCO har skilda representations-/
uppdateringssteg; generell harmonisering är inte ett specifikt tidsändringsbevis
för våra momentanfält. raise_if_updating finns redan i nedladdningskoden men
är inget historiskt run-/utfärdandebevis. Dagens CSV återanvänds utan nya
metadata-/väderanrop. Ingen koppling till vårt historiska ARCO-urval bevisad;
alla planning_blockers/data_unavailable kvarstår.
PROJECT_BLOCKER: arkivartikeln gav HTTP 401. Fortsatte med två andra officiella
källor och offline verifiering; fulltext påstås inte läst. Ingen extern kontakt.
Åtta regionala regressioner passerar; nio källhashar och dokumentlänkar
kontrollerade, diff --check godkänd. Ingen produktionskod ändrad, senaste
kodcommit 756d792 har 335 Python-tester godkända. Frontend oförändrad;
sex tester/resurskontroll verifierades tidigare i passet. Logg
autonomy/logs/arco-review-regional-20261016.log.
Nästa oberoende del: bevara koordinatordning vid permuterade NetCDF-
lagringsdimensioner genom befintlig audit/freeze. Inga nya adaptrar behövs.

## 2026-10-16 – bevarad marin koordinatordning

Rättat verkligt fel i befintlig freeze: godkänd audit transponerade efter
koordinatnamn men JSON-materialiseringen läste lagringsordningen direkt.
Freeze transponerar nu explicit till tid/lat/lon och statisk lat/lon efter
valt strömdjup. En ny regression med tre produktfall reverserar dimensionerna
i fixturekopior. Före fix ett geografiskt värdefel och två formfel; efter fix
passerar alla 37 riktade Copernicus-tester. Originalets regionalrapport med
nio källhashar är exakt oförändrad. Inga nya marina data, adaptrar, beroenden,
databasoperationer eller publika ändringar. Alla planning_blockers och
data_unavailable kvarstår; ingen regridding/run-certifiering.

Slutlig verifiering: full scripts.check exit 0 med 160+176=336 Python-tester,
syntax, pip check, låsfiler/domängränser. Diff granskad, --check godkänd.
Loggar autonomy/logs/marine-axis-{red,targeted,check}-20261016.log.
Frontend oförändrad; sex tester/resurskontroll verifierades tidigare i passet.
Nästa oberoende del: precisera native vindcellernas källstöd och analytiska
LCC-geometri, utan antagen WGS84-likvärdighet eller dold regridding. Befintliga
punktreferenser bevisar ännu inte hela celler/segment.

## 2026-10-16 – native vindens nodrutestöd

Befintlig vind-audit får additiv native_cell_inventory med källans x/y/tids-
gränser och 42 rumsliga/168 rumtidsrutor. Detta är rå nodadjacens, inte
producerad cellgiltighet, vald interpolation eller verifierat lokalt segmentstöd;
alla tre verified-fält är false och samtliga prognosspärrar kvarstår.
Kontraktet skiljer nodrektangel från utökat område och kräver senare mask-/
interpolations-/datum-/helsegmentsbevis. Ingen adapter/regridding införs.
Två nya regressioner verifierar kända rutor/gränser och avvisning av saknat
råstöd även med uppdaterad testhash. Tio riktade vindtester passerar. Första
körningen fann en ny diagnostikformatskillnad för Decimal-epoker; formatet
rättades till exakt decimalnotation och slutkörningen passerar.
Inga nya källhämtningar, marina rådata, beroenden, databas-/publika ändringar.

Slutlig verifiering: full scripts.check exit 0, 160+178=338 Python-tester,
syntax, pip check, låsfiler/domängränser. Diff granskad, --check godkänd.
Originalets regionalrapport och nio källhashar exakt oförändrade. Loggar
autonomy/logs/native-cells-{targeted,check}-20261016.log. Frontend oförändrad;
sex tester/resurskontroll verifierades tidigare i passet.
Nästa oberoende del: analytiska kontinuerliga lat/lon-gränser för native
nodrektanglar på deklarerad sfärisk LCC; kontrollera derivattecken inom
hela sourceområdet. Ingen WGS84-/rutt-/maskcertifiering får härledas därav.

## 2026-10-16 – analytiska native rektangelgränser

Dokumenterad egen derivathärledning för ideal deklarerad sfärisk tangent-LCC.
Över aktuellt x<0/b=rho0-y>0-område är latitud växande i x/y och longitud
växande i x, avtagande i y. Koordinatgränser för varje hel native nodrektangel
nås därmed i angivna hörn. Detta är matematisk källmodell, ingen numeriskt
intervallavrundad certifierare eller lokal WGS84-/routing-/maskkvalificering.
Två nya regressioner kontrollerar områdesvillkor och 25 PROJ-provpunkter i
vardera 42 rutor samt ett syntetiskt x=0-motexempel där hörnregeln fallerar.
Provpunkterna är korsjämförelse, inte kontinuitetsbevis; härledningen är separat.
Sex riktade geometritester passerar. Ingen produktionskod, råfixture, beroende,
adapter, databaskoppling eller publik demo ändrad. Alla prognosspärrar kvarstår.

Slutlig verifiering: full scripts.check exit 0 med 160+180=340 Python-tester,
syntax, pip check, låsfiler/domängränser. Diff granskad, --check godkänd.
Loggar autonomy/logs/native-bounds-{targeted,check}-20261016.log. Frontend
oförändrad; sex tester/resurskontroll verifierades tidigare i passet.
Nästa oberoende del: inventera native koordinaters deklarerade Float32-
precision kontra sparad ASCII/Decimal-representation. Kvantifiera skillnad
utan att kalla den datum-/routingtolerans eller korrigera källvärden automatiskt.

## 2026-10-16 – native koordinaters representationsprecision

Offlineinventering av deklarerad Float32 kontra sparad ASCII/Decimal med
struct och exakt Fraction-jämförelse. Max diagnostisk x-skillnad full axel
1/80 m, vindsubset 1/320 m; y exakt representerbar. Full x-binary32-grannsteg
varierar 999,984375–1000,015625 m, medan originalets ASCII-steg är exakt 1000 m.
Inga producentbytes påstås återvunna och ingen verklig koordinat-/datumfelgräns
härleds utan serialiseringsevidens. Två nya regressioner passerar och verifierar
att regionala axlar och källhash behålls utan tyst avrundning. Ingen
produktionskod, råfixture, adapter, beroende, databas-/publik ändring.
Alla planning_blockers/data_unavailable kvarstår. Detaljer i
met-nordic-metadata-review.md.

Slutlig verifiering: full scripts.check exit 0 med 160+182=342 Python-tester,
syntax, pip check, låsfiler/domängränser. Diff granskad, --check godkänd.
Loggar autonomy/logs/native-precision-{targeted,check}-20261016.log. Frontend
oförändrad; sex tester/resurskontroll verifierades tidigare i passet.
Nästa oberoende del: granska om originalfilernas källmetadata kan nås med
en strikt metadata-only metod och hård bytebudget, utan nya vädervärden eller
återhämtning av marina data. Utvärdera metoden före nätverksanrop; annars
fortsätt med offlinekontrakt för osäker koordinat-/runbindning.

## 2026-10-16 – metodgräns för originalmetadata

Granskad Toolbox-kod ger objektmetadata via HEAD men ingen separat NetCDF-
attributexport i granskade get-kodvägar. Officiell Toolbox-/h5py-dokumentation
läst. PROJECT_BLOCKER: ingen verifierad transportmetod som garanterar enbart
originalmetadata utan väderbytes. Inga nya källanrop genomfördes.
Fortsatte offline: lässpårning av tre hashkontrollerade subsetfiler och ett
syntetiskt kompakt HDF5-motexempel. Lokal metadataåtkomst överlappade inga
inventerade våg-/strömchunkar, men ett kompakt syntetiskt fält visar att
units-attributläsning kan transportera väderbytes i samma läsfönster.
En ny riktad regression passerar. Detaljer och omfattning i
copernicus-metadata-diagnostics.md. Ingen produktionskod, råfixture, adapter,
beroende, databas-/publik ändring. Alla prognosspärrar/data_unavailable kvarstår.

Slutlig verifiering: full scripts.check exit 0 med 160+183=343 Python-tester,
syntax, pip check, låsfiler/domängränser. Diff granskad, --check godkänd.
Loggar autonomy/logs/metadata-method-{targeted,check}-20261016.log. Frontend
oförändrad; sex tester/resurskontroll verifierades tidigare i passet.
Nästa oberoende del: samlad prognosgaprapport från aktuella verkliga indata,
med explicita evidenskrav för native vindgeometri/ram/mask, marin utfärdande,
historisk run-bindning och hela produktuppsättningens förenlighet. Identifiera
nästa meningsfulla offline/backlogdel utifrån krav, utan upprepade källprov
när ingen ny åtkomstevidens finns.

## 2026-10-16: samlad aktuell prognosgaprapport

Granskat RegionalForecastInputs och befintliga käll-/transportfynd. Ny
forecast-gap-status.md anger verifierat underlag och nödvändiga bevis per
vindgeometri/ram/stöd, marin run/utfärdande och gemensam förenlighet.
Källgap skiljs från lyckad auth/listning och misslyckad push/overifierad CI.
Historiska försöksavsnitt bevarade, aktuell översikt länkad först.
Ingen kod, råfixture eller planeringsspärr ändrad. Nästa oberoende backlogdel:
offline kontraktsgranskning av okänt djup/vertikala datum vid API-/GPX-gräns.

## 2026-10-16: djupkontrakt vid API-/GPX-gräns

Granskat PlanInput, geografiska resultat, regional prognosgräns och GPX.
Dokumenterat nuläge och offline acceptansmatris i depth-acceptance.md:
horisontell marginal skiljs från djupgående/marginal under kölen; okända
vertikala datum får inte adderas. Syntetisk arrived/export bevisar ingen
klarering. Ingen produktionskod, källa, prognosspärr eller publik demo ändrad.
Nästa del: riktad regression av avvisade extra djupfält före jobbstart samt
bevarad unknown/not_assessed och frånvaro av fabricerade GPX-höjder.

## 2026-10-16: djupfält får inte tyst ignoreras

Ny negativ API-regression prövar fyra extra djupfält över båda profilerna:
422 med fältspecifik extra_forbidden och inga skapade jobb/tasks. Utökade
befintliga end-to-end-tester behåller unknown/not_assessed när snabbast och
bekvämast finns och kräver GPX utan fabricerade höjder/extensions med kvarvarande
begränsningstext. 14 riktade tester passerar. Ingen produktionskod, fixture,
prognosspärr, källa, databas eller publik demo ändrad. Nästa del: källnära
granskning av MET-vindens tidsmedel/ram i officiell dokumentation, utan datauttag.

Full scripts.check exit 0: 160+184=344 Python-tester, syntax, pip check,
låsfiler och domängränser. Loggar autonomy/logs/depth-boundary-{targeted,check}-20261016.log.

## 2026-10-16: MET-vindens tidsmedel och ram avgränsade

Officiella MET Nordic Parameters, Examples, FAQ samt CF 1.7 §7.3 lästa.
Vindmedlets placering förblir okänd; nederbörds-/observationskonventioner får
inte överföras. Rotationsexemplet använder äldre MEPS-komponenter, inte vårt
MET Nordic-riktningsfält. CF interval är provtäthet, inte fulla tidsgränser.
Sparad DAS saknar vind-cell_methods och time-bounds. Dokumenterat i
met-wind-frame-review.md. PROJECT_BLOCKER kvarstår för tidsplacering/full
ramnormalisering. Fortsatte befintliga offline metadata-/vindtester; inga nya
väderbytes, paket, adaptrar, databas- eller publika ändringar.

## 2026-10-16: oberoende lokal vektorreferens

Konkret risk: koordinathastighet i AEQD är inte generellt fysisk öst/nord-fart
med enbart rotation. Härlett sfärisk centralmeridiandifferential
 diag(c/sin(c),1) och jämfört med symmetriska biblioteksdifferenser vid
0/±1 km/±1000 km. Två numeriska referenstester passerar; avlägsna fall är
syntetiska stresstester utanför routingområdet. Detaljer/toleranser i
met-wind-frame-review.md. Ingen produktionsfunktion, rådata, adapter eller
källdatum-/vindkvalificering införs; alla planeringsspärrar kvarstår.

Full scripts.check exit 0: 160+186=346 tester och samlade kontroller godkända.
Logg autonomy/logs/local-vector-check-20261016.log. Nästa konkret granskning:
MET-tidsattributens tillåtna innehåll och negativt test för ogranskad skalning/
tillägg; befintlig tidsparser är mindre strikt än vind-/geometriblocken.

## 2026-10-16: MET-tidssemantik kan inte ändras genom ny hash

Reproducerat att extra tidsattribut och ändrad chunkmetadata accepterades med
uppdaterad hash. Före-fix-logg: met-time-attributes-before-20261016.log,
12 subfall nådde saknad vindfil och tre saknade förväntad avvisning. Återanvänt
reviewed_attributes för exakt time/forecast_reference_time-layout. Två nya
regressioner kontrollerar tidig avvisning, 34 riktade tester passerar. Ingen
råfixture/utfärdandetid/planeringsspärr ändrad. Detaljer i
met-nordic-metadata-review.md. Nästa del: granska manifestets identitetsbindning
för native vind och källmetadata, särskilt dubbletter och motsägande produkt/run-
referenser; endast konkreta brister ska leda till kodändring.

Full scripts.check exit 0: 160+188=348 tester, syntax, pip check, låsfiler och
domängränser godkända. Loggar autonomy/logs/met-time-attributes-{before,targeted,check}-20261016.log.

## 2026-10-16: entydiga MET-manifest

Reproducerat fyra tvetydiga JSON-dubbletter som accepterades med sista värdet:
schema, filhash, vindhash och nästlat subsetindex. Gemensam bounded
read_manifest för befintlig metadata-/vindläsning avvisar nu dubbletter på alla
objektnivåer med fast, värdefri feldiagnostik. Två nya regressioner och 30 riktade
tester passerar. Inga råfixtures/adaptrar/datum/planeringsspärrar ändrade.
Nästa oberoende del: granska motsvarande marina manifestläsning för faktisk
identitetstvetydighet; återanvänd befintlig adapter och samma marina råbytes.

Full scripts.check exit 0: 160+190=350 tester samt syntax, pip check, låsfiler
 och domängränser godkända. Loggar autonomy/logs/met-manifest-{before,targeted,check}-20261016.log.

## 2026-10-16: marina manifest får inte ha tvetydiga nycklar

Reproducerat fyra accepterade dubbletter i marina manifest: schema, filhash,
produkt och dataset_id. Delat liten JSON-avkodare mellan befintliga auditverktyg;
MET behåller bounded_read och marin audit behåller samma råbytebilder/freeze.
Två nya regressioner och sex riktade tester passerar. Ingen adapter, råfixture,
utfärdandetid, planeringsspärr, databas eller publik demonstration ändrad.
Nästa begränsade granskning: marina manifestets form/produkt-/filbindning och
läsbudget före NetCDF-I/O; börja med konkreta negativa offlinefall.

Full scripts.check exit 0: 160+192=352 tester samt samlade kontroller godkända.
Loggar autonomy/logs/marine-manifest-{before,targeted,check}-20261016.log.

## 2026-10-16: begränsad och källbunden marin manifestläsning

Tre nya regressioner reproducerade felaktig form/bool-schema, fem produkt-/
filidentitetskonflikter och obegränsad manifestläsning. Tidig objekt-/list-/
postvalidering, 512 kB-bytebudget, unika granskade filer och bundleidentitet
införda i befintlig audit_snapshot. Katalogversion är ingen run-identitet.
18 riktade audit/freeze/snapshot/axelordnings/regionaltester passerar.
Inga råfixtures/adaptrar/utfärdandetider/planeringsspärrar/databas/publik demo
ändrade. Nästa del: granska att källäst marin tid/koordinatsemantik inte kan
ändras med uppdaterad hash; börja med konkreta offlinefall, inga nya datauttag.

Första fullkontrollen visade att äldre syntetiska NetCDF-testfabriken saknade
produktidentitetsfält. Uppdaterad med komplett deklarerad importidentitet,
uttryckligen fortsatt syntetiska bytes; befintliga CF-/giltighetsassertioner
behållna och når åter rätt kontroller. 17 import-/manifesttester passerar.
Första fulloggen behålls som evidens; fullkontroll körs om efter testfix.

Slutlig full scripts.check exit 0: 160+195=355 tester och samlade kontroller
godkända. Slutlogg autonomy/logs/marine-manifest-shape-check-fixed-20261016.log.

## 2026-10-16: marin tidsmedelsemantik bevarad i audit

Faktisk råmetadata visar time: mean på alla tre vågfält men inte strömfält;
time saknar bounds/climatology. Tidigare audit accepterade nio semantikändringar
med ny hash. Avgränsad auditkontroll av granskat cell_methods-innehåll och
frånvaro av nya tidsdomäner införda. Rapport bevarar cell_methods och redovisar
temporal_support unverified/time_bounds null. Tre nya regressioner och
23 riktade tester passerar. Syntetisk testfabrik har explicit vågmedel. Inga
råfixtures, adaptrar, referenspayload, utfärdandetider eller prognosspärrar ändrade.
Nästa begränsade del: granska den frysta referenspayloadens borttappade cell_methods
som separat kontraktsgap, utan att ändra data_unavailable eller anta tidsgränser.


## 2026-10-16: återhämtad marin tidssemantik och samlad leveransgranskning

De fem kvarvarande filerna granskade och färdigställda utan återställning.
Tidssemantiktesterna omfattar tolv negativa mutationer: ändrat/borttaget
vågmedel, båda strömkomponenterna och bounds/climatology på båda tidsaxlarna.
Audit bevarar källäst cell_methods; okända medelperioder/utfärdanden förblir
okända. Det frysta referenspayloadets vidare tidssemantikkontrakt är fortsatt
ett integrationsgap, inte en kvalificerad ögonblicksprognos.

Samlad diff från e117b3b granskad: hashbundna snapshots används genom
MET-/marinmaterialisering, geografisk axelordning bevaras, tvetydiga manifest
och ogranskade tids-/fältmetadata avvisas. Ruttkvalificering och publikt
beteende ändras inte; inga nya väderuttag eller adaptrar. Inga ytterligare
leveransfel identifierades i denna granskning.

Låsta Pythonberoenden verifierade med pip --require-hashes --only-binary=:all:
i /tmp/seaparser-ci-clean, Python 3.14.4. npm ci --ignore-scripts passerade med
Node 22.22.1/npm 9.2.0. Riktad Copernicus-körning: 45 tester godkända.
En samlad make check: 160+198=358 Python-tester, syntax, beroenden, arkitektur
och frontend statisk kontroll godkända; frontend landtest godkänt. Kartans två
API-integrationer blockerades av miljöns socketbegränsning: uvicorn kan inte
binda 127.0.0.1:0 (exit 3). Tre övriga karttester passerade vid riktad diagnos.
Fullkörningen upprepas inte; ordinarie CI får pröva integrationerna utan denna
miljöbegränsning. Full logg: /tmp/seaparser-recovery-full-check.log.

SSH-åtkomst till development/real-map-data verifierad med projektets befintliga
nyckel, utan att visa hemligheter. GitHub-anslutningen kan läsa privata
Actions-resultat; tidigare publickey/Unknown tool är inte aktuella hinder.
Push och CI-resultat redovisas separat först efter faktisk verifiering.

## 2026-10-16: Separat grafisk granskning av frysta Vinga-prov

Aktiv uppgift: användarens första funktionsmål för det nya passet. Antagande:
provvisningen använder varje källas egna koordinater och sparade tidpunkter;
visuell jämförelse innebär ingen datum-, mask- eller ruttkvalificering.
Infört fristående HTML med källval, tidsreglage, punktval, värdeskalor, tidsserier,
enheter, koordinatgränser, separata maskstatusar och synliga källhashar.
Befintliga snapshotläsare återanvänds utan nya uttag eller parallella adaptrar.
Artefakt och publiceringsunderlag: `artifacts/vinga-frozen-review/` respektive
`docs/vinga-frozen-review.md`. Ingen publicering. Riktade Python- och DOM-tester
passerar; samlade leveranskontroller och exakt remote-CI redovisas vid commit.
Nästa funktionsmål: konservativ native vindgeometri/källstöd för hela segment,
utan att lösa okända datum, vektorramar, tidsmedel, masker eller run-förenlighet
med antaganden. Se aktuell gapöversikt; kvalificering förblir blockerad.
Leveransverifiering: Python 3.14.4, samtliga 26 installerade låsta paket matchar
requirements.lock; scripts.check passerar 160 domäntester + 204 integrationstester.
Efter sista proveniensfältet passerar de sex riktade Python-testerna och fyra
DOM-tester igen. npm ci --ignore-scripts --offline och frontend check passerar.
PROJECT_BLOCKER: lokal API-testserver kan inte binda TCP 127.0.0.1:0:
PermissionError errno 1, Operation not permitted. Befintlig frontend map.test.mjs
faller lokalt; ingen upprepad full körning eller publik demo används. Exakt CI
ska verifiera API-integrationen. Manuell visuell webbläsargranskning återstår.

## 2026-10-16: Konservativt native-hölje och segmentbunden råinventering

Förra leveransen 6e9a1b6 är pushad med grön exakt CI 38957365522.
Nästa begränsade funktionssteg implementerar rationella utåtriktade intervall
för HELA boxars sfäriska LCC-bild och binder en explicit källsfärisk,
angular-linjär granskningsbana till samtliga tangerande serialiserade
rumtidsrutor och råhörn. Antagandet är en matematisk bana på källsfären,
inte en redan datumtransformerad WGS84-/lokal rutt. Ingen payloadflag ger
kvalificering. Det exakta naturliga origo och en latitudbåges inre y=0
(vardera ändpunkt >390 m) ger oberoende referenser mot ändpunktsprovtagning.

Befintlig NativeWindSample och hashvaliderade läsare återanvänds; ingen ny
adapter, hämtning, marin masköverföring eller motorändring. Exempel: sex
rumtidsrutor och 24 unika rånoder. Budget/utanför/luckor kan inte ge klippt
positiv täckning. Källa, faktisk materialiserad indata, segment, hölje och
budget binds till rapporthash. Datumsamband, källaxlarnas serialiseringsfel,
vektorram, mask, interpolation, medelplacering och säkerhetshölje förblir
okända/blockerade. Inga verkliga ruttkandidater skapas.

Kod/underlag: docs/native-wind-segment-support.md och
artifacts/native-wind-segment-review/report.json. 17 nya riktade tester
passerar; samlade låsta kontroller och exakt commit/CI verifieras vid leverans.
Nästa mål: motsvarande hela-hölje för en lokalt affin bana, utan antaget
datum-/serialiseringsstöd; därefter fortsatt källspecifik mask-/semantikbindning.
Samlad leveranskontroll: /tmp/seaparser-ci-clean Python 3.14.4 matchar samtliga
26 låspaket; scripts.check passerar 160 domäntester + 221 integrationstester.
Rapportflaggorna för aritmetik/okvalificerat fysiskt stöd tillades därefter;
riktade tester ska verifieras igen utan en omotiverad ny full körning.
Frontend och dess beroenden är oförändrade; tidigare lokala TCP-hinder upprepas
inte. Exakt ny remote-CI kontrolleras efter push.

## 2026-10-16: Helt hölje för lokalt affin källsfärsbana

Föregående e863206 är pushad med grön exakt CI 38958954070. Nu implementeras
helt segmenthölje i explicit sfärisk AEQD kring Vinga: exakt kvadrerad
ändpunktsradie, rationellt omsluten kvadratrot och ett analytiskt geodesiskt
diskhölje från sfärens metrik. Det geografiska höljet går genom befintlig
rationell LCC-inneslutning och samma fullständiga råinventering. Ingen
kantprovtagning, ny adapter, databas-/nätverksläsning eller motorändring.

Antagande: lokala meter avser uttryckligen den matematiska MET-sfären, inte
WGS84-ramen. Ursprungliga lokala koordinater, tider, ram-/metoddefinitioner,
disk och hela källstödet hashbinds. Verklig ruttbindning, källaxlarnas
serialiseringsfel, datum, vektorram, mask, interpolation, medelplacering och
säkerhetshölje förblir okända/blockerade. Båda ruttkandidaterna är null.
Exemplet ger 12 rumtidsrutor/36 rånoder; tidigare angular-linjära rapport är
oförändrad. Nio nya tester + 17 tidigare riktade tester passerar. Samlade
låsta kontroller och exakt commit/CI verifieras vid leverans.

Rapport: artifacts/source-local-wind-review/report.json. Byggkommando och
härledning i docs/native-wind-segment-support.md. Nästa del behöver konkret
källbunden metadata-/proveniensevidens för de kvarstående verkliga gapen,
inte fler antagna ramomvandlingar eller dokumentations-/testfyllnad.
Leveransverifiering: samtliga 26 installerade Python-låspaket matchar;
scripts.check passerar 160 domäntester + 230 integrationstester. Föregående
JSON-rapport återges exakt trots gemensam inventeringsrefaktor. Frontend,
beroenden och grafisk artefakt är oförändrade; känt TCP-hinder upprepas inte.
Exakt remote-CI verifieras efter push.

## 2026-10-16: Grafisk segmentstödsgranskning och korrigerad strömtidssemantik

Föregående feb67ff är pushad med grön exakt CI 38960005560. Ett begränsat
MET-dokumentationsförsök gav inte ny källbunden kvalificering; råtexthämtning
av primär Examples.md gav PROJECT_BLOCKER: URLError (källa/operation/budget
redovisas i met-wind-frame-review.md). Ingen identisk retry, marin datahämtning,
sandbox-/systemändring eller adapter. Oberoende funktion valdes inom prioriteten.

Vindfliken i den fristående grafiska artefakten kan nu visa hela provsegmentets
omslutande område och de sparade stödnoderna vid vald tid. 9 platser × 4 tider
är 36 prov; 16 UTC ger noll markeringar för denna bana. Byte till vågor/ström
visar aldrig vindens hölje/stöd. Punktval och käll-/rapporthashar ger granskbar
bindning. Samma fångade vindsnapshot materialiseras för presentation och
segmentrapport; ingen omläsning eller parallell adapter. Matematisk bana och
okvalificerat verkligt ruttstöd förblir åtskilda. Inga positiva ruttkandidater.

En faktisk presentationsbugg rättas: tidigare text sade att strömmen deklarerar
tidsmedel, trots att dess frysta cell_methods saknas. Nu bevaras detta som okänt,
medan vågornas deklarerade tidsmedel fortsatt visas utan påhittad längd/placering.
Råfixtures är orörda. Nya Python-/DOM-regressioner verifierar källbindning,
ingen omläsning, tids-/produktseparation och bevarade kvalificeringsgrindar.
Artefakt artifacts/vinga-frozen-review/index.html och kvitto regenererade;
ingen publicering. Samlade låsta kontroller och exakt commit/CI vid leverans.
Verifierat: samtliga 26 Python-låspaket matchar; scripts.check passerar 160+233
tester. Efter sista läsbarhetsfrasen passerar nio riktade Python-tester och sex
DOM-interaktionstester igen. Frontend check och separat land-DOM-test passerar.
Befintligt TCP-hinder upprepas inte; ordinarie exakt CI ska verifiera API.
Nästa mål: bara konkret annan tillåten källmetadata-/proveniensmetod; behåll
osäkerhetsgrindarna. Manuell visuell browsergranskning återstår.

## 2026-10-16: Valbar grafisk provbana och negativa stödfall

Lokalt HTML-bygge kan välja befintligt källsfärsformat med --segment och en
begränsad inventeringsbudget. JSON läses en gång och dess exakta bytehash binds
till rapportvisning och reproducerbart, sökvägsciterat byggkvitto. Okänd WGS84-ram
avvisas innan befintlig artefakt skrivs över. Presentation och filorkestrering
behåller sina lager; ingen ny adapter eller väderdatahämtning.

Separat artifacts/vinga-outside-review/index.html visar en matematisk bana som
lämnar både rumsligt och tidsmässigt stöd. Hela höljet visas med utökade axlar och
separata sparade koordinatgränser; ingen klippning eller partiell inventering ger
positiva stödringar. Råprov finns kvar på egna grid. Budget-/luckfel förklaras
också utan positivt stöd. Inga kvalificeringsgrindar ändras och inget publiceras.
Riktat verifierat: 32 Python-tester och 8 DOM-interaktionstester passerar.
Samlade låsta kontroller och exakt commit/CI dokumenteras vid leverans.
Nästa funktionssteg kräver fortsatt konkret källstöd för verklig ruttbindning;
matematisk källsfärsgranskning ersätter inte saknad datum-/ram-/masksemantik.
Verifierat vid leverans: låsta scripts.check passerar 160 domän- och 238
integrationstester; frontend check passerar. De åtta riktade DOM-testerna är gröna.
Lokal TCP-bindning provas inte om; API-integration verifieras i ordinarie CI.


## 2026-10-17: fryst Vinga-granskning förberedd för separat URL

Deploymentflödets befintliga atomiska Vinga-kopiering återanvänds för en
allowlist med endast vinga-prognosprov.html. Prepare/verify ändrar inget
publikt; senare publish vägrar befintlig adress, ändrad checkout, extra
resurser och ändrat demo-innehåll. Manifest/kvittot förblir utanför public/.
Historiska verkliga prov och ej kvalificerad routing verifieras mot exakt
rendering och CSP. Ingen riktig webbläsare/browserverktyg finns här;
visuell desktop/mobilgranskning kvarstår. Inget publicerat eller omstartat.

Verifiering: 20 riktade Python-tester och fristående HTML:ens DOM-test gröna.
Samlad kontroll: 160+244=404 Python-tester, beroende-/arkitekturkontroll,
frontend statisk kontroll samt DOM-/landtester godkända. Befintligt karttest
kan inte starta sin lokala API-process i denna hanterade miljö; exakt
socketdiagnos och full logg sparas utanför repositoryt. CI verifierar
hela körningen före leverans; ingen ny full lokal körning utan ändring.

## 2026-10-17: Native MET-vind kopplad till ett fryst Vinga-segment

Infört en avgränsad offlineadapter över befintlig hashfryst MET-native-fixture.
Den bevarar source-LCC-axlarna, omvandlar CF `wind_from_direction` till
geografiska E/N-komponenter, interpolerar komponenterna i rum och tid och
mappar vindvektorn till Vingas WGS84-AEQD-ruttkoordinater. Hela lokala segmentet
omsluts med geodetiska intervallgränser, därefter en rationell LCC-box och alla
tangerande native cellhörn. En punkt över testgränsen bevisar överskridande;
hörnhöljet måste rymmas under gränsen för `within_interpolation_model`; annars
redovisas otillräckligt underlag.

Reproducerbart fall: `fixtures/vinga-met-wind-segment.json`, rapport
`artifacts/native-met-wind-segment/report.json`. Den frysta faktiska vinden ger
13,13 m/s vid segmentmitt: testgräns 10 m/s överskrids; konservativ gräns
18 m/s ryms inom den definierade interpolationsmodellen. Uppmätt koordinatstöd
vid 56 källnoder har maxavvikelse 0,2491 m; segmenthöljet lägger till 1 m.
Det är inte global datum-/källnoggrannhet. Utfärdandetid, vindmask,
tidsmedlets exakta placering och förenlighet med marina körningar är fortfarande
okända. Därför finns ingen kvalificerad rutt eller planeringskandidat. Ingen
syntetisk ström, våg eller polar användes; djup/landfullständighet okända.

Verifiering: `tests.test_met_wind_segments` (14) och den fulla `scripts.check`-
sviten (160 domän- och 258 integrationstester), låsfiler, arkitektur och
beroenden godkända. Frontendens
statiska kontroll och samtliga 14 frontendtester passerade; karttesterna kördes
utanför sandboxen eftersom de startar en lokal API-process. Ingen publik demo
eller databas ändrad. CI kontrolleras efter push.
# Native MET and marine Vinga provenance check — 2026-10-17

Started from `development/real-map-data` at `df531d2`; worktree was clean.
Reviewed the already frozen MET native-wind sample and Copernicus WAV/PHY
fixtures; no existing data or public demonstration was changed.

Checked current official Copernicus WAV PUM Issue 2.8 and PHY/BGC PUM Issue
1.3 (both November 2025). They document 00Z/12Z products, publication targets
10/22 UTC, WAM forcing from MetCoOp-HARMONIE and WAM use of BAL PHY surface
currents. Those model/product facts do not bind the existing ARCO field values
to an actual run or published time. The frozen files contain no run/reference
coordinate, issue time, or revision. WAV metadata `cell_methods="time: mean"`
conflicts with the manual's hourly-instantaneous description and has no time
bounds; PHY current support/mask metadata is also incomplete. MET carries a
model-reference time, not verified issue time; `source=meps` is not proven to
identify the exact MetCoOp-HARMONIE forcing member.

A new source probe was bounded to the Vinga box, five hours, the two reviewed
products, 2 MB per file and 5 MB total, using existing Toolbox authentication.
The catalog returned the existing reviewed versions (WAV 202311, PHY 202411).
The WAV dry-run returned `ValueError` before any weather bytes were downloaded;
the client message was intentionally suppressed. No new forecast files were
created. An ARCO subset alone would not cure run provenance; retrieving the
WAV original is 110 MB compressed per current official manual and outside this
small probe.

Result: keep `data_unavailable`; no mixed-source route computation or marine
planning-gate changes. Exact missing fields and source-backed way forward are
recorded in `docs/forecast-gap-status.md`. Separate native-wind and marine
fixtures remain intact. No synthetic waves/current were introduced.

Verification: source manuals read; current catalog query succeeded; bounded
probe stopped before file retrieval. `scripts.check` passed all 160 domain and
258 integration tests; `npm --prefix frontend run check` and all 14 frontend
tests passed. `git diff --check` passed. These checks preserve the existing
fail-closed input behavior. Next: commit this narrowly scoped blocker/status
update, push the development branch and verify CI. No DB, deployment or public
demo changes.


## 2026-10-17: WAV dry_run ValueError isolated without downloading weather

Task: identify and reproduce the previously reported WAV ValueError, keep the
2 MB file / 5 MB transfer probe cap and all planning gates intact.

Located the original call in `/tmp/seaparser-met-copernicus-probe.py`:
`marine.subset(**req, dry_run=True)` followed by the local budget check.
Request: dataset `cmems_mod_bal_wav_anfc_PT1H-i`, version `202311`, part
`default`, service `arco-geo-series`, variables VHM0/VTM02/VMDR, longitude
11.58–11.63, latitude 57.62–57.65, strict-inside, 2026-10-17 00:00–04:00 UTC,
NetCDF, progress disabled, raise_if_updating=True. Output target was
`/tmp/seaparser-met-copernicus-probe-data-3/waves.nc`.

Three network-enabled dry-run repetitions succeeded with Toolbox 2.5.0.
The final repetition also executed the original budget check and reproduced
`ValueError('probe exceeds 2 MB file / 5 MB transfer cap')` after dry_run,
with 0.013297709923664122 MB file / 40.67862595419847 MB transfer estimates.
The old stage remained dry_run:waves during the check, so the earlier status
incorrectly attributed the exception to the client call. The original traceback
was discarded; this identifies the reproducible failure path, without claiming
to recover that discarded evidence or a historical transfer estimate.

Private reproduction script, exact request, numeric result and traceback are
under `/tmp/seaparser-wav-error-20261017` (directory 0700, files 0600);
script `/tmp/seaparser-wav-reproduce.py` is 0600. No credentials or signed URLs
were emitted or committed. An initial sandbox-only attempt failed in metadata
network access; the network-enabled reproduction resolved that limitation.
No subset download was invoked, no original get was invoked, no dependencies,
DB, deployment or planning code changed. The budget rejection is correct;
there is no faulty subset argument to fix on the observed evidence.

Verification: exact live dry-run plus original postcondition, private traceback
and file permissions, and git diff --check. Documentation-only change, so no
full test suite was run. Next: source-backed provenance/time-support/mask work
within existing limits; do not increase the transfer cap to bypass this result.


## 2026-10-17: Regional download budgets, cache and completed WAV metadata probe

User authorized configurable GB-scale regional forecast budgets, routine
adjustments within free data work, scoped WAV retrieval and metadata analysis;
no purchases or planning-gate changes. This supersedes the diagnostic 2/5 MB
limit documented above. Implemented in the existing Copernicus downloader,
with a standard-library budget/cache helper; no new packages or adapters.

Defaults: 2 decimal GB result per request, 10 GB estimated transfer per request,
20 GB estimated transfer per invocation, 1 GB disk reserve. CLI bounds area,
time, reviewed product variables and current depth. Check finite estimates,
individual and cumulative transfer budgets, output size and free cache/output
disk. Actual traffic is not measured; manifest distinguishes estimates from
actual result bytes. Streaming hashes avoid loading GB files just to hash.

Cache identity includes the exact source selection and bounds, with canonical
UTC times. Hash/size/age checks, per-request process locks and staging exclude
incomplete or damaged downloads. Six-hour snapshot reuse is configurable;
retrieval time is preserved and never treated as issuance/model-run evidence.
The shell wrapper forwards options and has a configurable one-hour timeout;
custom subsets remain diagnostic and cannot pass as full audited bundles.

WAV live retrieval succeeded: 202311/default/arco-geo-series, Vinga box,
2026-10-17 00–04 UTC, VHM0/VTM02/VMDR, no depth axis. Result 26114 bytes,
SHA-256 9030a4d3cb945410e3ec7d69018886e43f859d3696e973360eea96b4b65bf279.
Private result/manifest/metadata: /tmp/seaparser-wav-regional-20261017.
Estimated transfer approximately 42.6 MB, estimated result approximately
13.9 kB. The already existing inspect file covered October 13, so could not
replace this request. A second identical live request verified CACHE_HIT,
zero new estimated weather transfer and the same result hash.

Metadata: 5 hourly times x 2 latitudes x 2 longitudes per variable; no missing
or nonfinite samples among 60 variable values. Still no forecast_reference_time,
forecast_period, issued_at, run ID or revision. All three wave variables retain
cell_methods=time: mean and no bounds. Existing provenance/time-support/mask
and planning gates remain unchanged; no regional route run, DB or deployment.
Assumption: GB defaults are operational diagnostic budgets, not guarantees of
actual transfer, temporary disk or memory use, and not source qualification.

Verification: offline budget/cache/scope regressions including pre-download
rejection, integrity/expiry and a duplicate-request workflow; existing import
regressions; live download and cache-hit checks; shell syntax and diff check.
Python project check passed 160 domain and 264 integration tests before final
small diagnostic/UTC-normalization refinements; focused tests rechecked after
them. See copernicus-download-budgets.md for commands and remaining limits.
Next: reviewed commit/push and exact-commit CI, then source-backed run and
time-support evidence rather than bypassing planning gates.


## 2026-10-17: WAV original retrieved and compared with existing ARCO snapshot

Scope from user: start at 3e40452, reuse download/cache, obtain a relevant
producer original and source metadata within configured budgets, inspect run,
reference/issue/publication times and time semantics, compare without claiming
lineage from numerical similarity, preserve all planning gates. No subset was
repeated and no external support message was sent.

Current metadata-only catalogue/listing identified BAL-WAM_WAV2026101700.nc.
A one-file get dry-run and actual get retrieved 113263050 bytes within default
2/10/20 decimal GB file/per-request/session budgets and 1 GB disk reserve.
Object ETag, last-modified metadata, local SHA-256 and retrieval time are
recorded in docs/wav-original-review.md and docs/evidence/wav-original-arco-20261017.json.
Private source catalogue/list/headers/traceback/original/manifest remain under
/tmp/seaparser-wav-original-20261017. Original cache admission/integrity was
verified; identity includes remote ETag/size/mtime and uses the existing
budget/cache helper. No second original download was used as a cache test.

Added a narrowly scoped WAV-original downloader around Toolbox get; no new
adapter or dependency. It rejects wildcard filenames, multiple candidates,
budget/disk violations and mismatched source metadata, then stages and hashes
before cache admission. The first preflight rejected Toolbox's quoted ETag;
fixed the format validator and added quoted-ETag coverage before retrying.
No weather bytes were fetched by that rejected preflight.

Added an offline comparison CLI restricted to reviewed unpacked float32 fields,
exact native coordinate matches and explicit equal-time/+3600s hypotheses.
Original: 12x775x764, valid 2026-10-17 01–12 UTC, 22 variables; creation_date
2026-10-17 05:06:46 has no timezone or established issuance meaning. No run ID,
forecast_reference_time/forecast_period, revision or actual publication time.
Original wave variables have no cell_methods/bounds; PUM and CF-1.0 intensive
field defaults support point interpretation, but cannot override ARCO's mean.

At common times 01–04 UTC, 48/48 values across 3 variables and 4 exactly matched
nodes are identical. ARCO 00 is outside this original's valid-time range.
The +1-hour comparison has 0/60 exact matches, so this case does not support
an assumed shift. Equality is a local content witness, not source-certified
run/revision lineage. Numeric report flags all qualifications false; no
planning code, frozen fixtures, DB or deployment changed.

Provider clarification is now concrete: exact run/reference/revision/status for
this object/ETag; creation_date timezone/meaning and actual publication records;
why ARCO has time: mean vs instantaneous producer semantics, including bounds
or a corrected attribute; historical ARCO-to-original lineage per variable/time
including 00 UTC; exact forcing-run identities and valid temporal support rules.

Verification: focused budget/original/cache/comparison tests include exact-file
selection, no download after budget rejection, changed-object rejection,
quoted ETags, cache reuse, missing-value exclusion, nearby-node rejection and
both independent temporal witnesses. Final real-file offline comparison
reproduces every base field of the versioned evidence. Full Python project
checks and final focused results recorded below after completion.
Next: commit/push and exact-commit CI; source/provider evidence is needed to
resolve run/issuance/ARCO-mean ambiguities. Do not derive these from file names,
creation_date, S3 mtime, matching values or general production schedules.


Final local verification for this delivery: scripts.check passed 160 domain
and 274 integration tests; 17 focused tests passed after the final whole-second
time-axis guard, including rejection of fractional timestamps instead of
rounding into false matches. Final real-file comparison remained identical.
Syntax parsing and git diff --check passed. No dependency installation, live
DB, public deployment or additional weather download was involved.


## 2026-10-17: Default real MET/WAV/PHY route comparison with explicit development assumptions

User explicitly authorized joint development routing with real wind, waves and
current, configured assumptions for missing source metadata, and separation of
verified evidence from assumptions. The single development environment remains;
no synthetic marine replacement scenario, purchases, new fetches, DB or public
deployment are included.

Standard Vinga API/scene/client/local-server now uses the existing frozen real
MET native wind and Copernicus WAV/PHY snapshots, with actual common validity
2026-10-13 12–16 UTC. Historical data are clearly labeled; the October 17 WAV
snapshot was not retimed or mixed with older wind/current. Each comparison
uses identical immutable inputs. configuration in
settings/development-weather-assumptions.json requires named explanations for
issuance/run compatibility, native wind geometry/frame/mask/averaging and
marine mask/time-support assumptions. Unknown new blockers are not generically
ignored. Raw source metadata/strict adapters stay unchanged, while conditional
product copies mark assumed_fields and the original null issuance is retained
in weather_provenance. Every route and manifest says conditional_on_assumptions;
source qualification stays unverified. GPX and UI preserve these distinctions.

Native wind stays on its original grid, with full-area support enclosure and
conservative actual source-component bounds. Marine grids keep their own masks,
missing nodes and continuous segment checks. Actual data outside coverage,
invalid values, land/selected margin, chosen wind/Hs limits and arrival checks
still reject a route. The existing test sail polar does not cover the actual
wind strength; the explicit estimated constant-speed model defaults to 5 knots,
without fabricating a new polar or marine weather values. Comfort remains an
unvalidated exposure metric.

The old default western start lay outside actual marine support. The graphical
case now runs from Vinga local (300,-400) to (300,400), around real frozen land.
Uniform-cost geometry enumeration exhausted its queue before reaching the new
detours. Replaced queue ordering with admissible Euclidean A*, preserving full
simple paths, both alternatives and the same 1000 queue/expansion, 26 node,
2 candidate and 8 waypoint budgets. It finds two candidates in 47 expansions;
subsequent real-weather integration yields four arrived alternatives for 12:00
and 12:10 departures. Typical model travel time is about 356 seconds. Both
objectives select auto-0 in this actual case; no synthetic variation was added
to force a different winner.

Concrete visible artifact: artifacts/real-route-review/index.html, portable,
self-contained interactive SVG/card comparison with actual start weather and
all assumption explanations. Matching full result.json, source hashes and
configuration hash are included. Existing Leaflet UI supports new endpoint
choices and selected real weather limits; its default cannot switch to a
synthetic marine scenario. Explicit synthetic profile/reference tests remain.
See docs/development-real-routing.md for reproduction and limits.

Validation so far: real-value reference assertions, deterministic actual four-
route result/artifact reproduction, absent-assumption rejection, missing/NaN
marine nodes, native/marine space-time limits, lower wind and Hs rejection,
land endpoints/full segments, and unchanged analytic synthetic routing cases.
Local frontend API/Leaflet/GPX flow passed all 14 existing tests after making
the synthetic reference scene query explicit; the new offline graphic DOM test
also passed. Sandbox cannot bind the loopback API, so the integration run used
authorized local TCP outside the sandbox, without publication. Full Python
check results and final exact-commit CI are reported on completion below.


Final local validation: scripts.check passed 160 domain and 281 integration
cases. After the final native-source hash clarification and unknown-new-wind-
blocker guard, all 7 focused real-weather/coverage/mask/assumption/artifact tests
passed. Frontend check passed; all 15 final frontend tests passed, including
loopback API/Leaflet/GPX and the standalone SVG selection/reset test. The real
artifact reproduces byte for byte from current frozen inputs/configuration;
its four routes arrive in 355.715161, 356.460378, 356.039849 and 356.786339 s.
Actual start values: wind 12.94228595093238 m/s, current 0.372219587341769 m/s,
Hs 1.1409889496350858 m, Tm02 2.873840543144118 s. Config/selected weather limits
and each raw source hash remain in the report. Diff and targeted secret checks
passed. No publication or new weather download was performed.

Release step: reviewed commit to development/real-map-data and exact-commit CI.
Next product work: improve source qualification/temporal semantics and boat
performance while keeping the usable real-data development comparison visible;
metadata evidence and assumptions must continue to be distinguished.


## 2026-10-17: Approved single-page real-route publication

User explicitly approved publishing artifacts/real-route-review/index.html to
https://seaparser.com/vinga-ruttjamforelse.html with the existing publication
flow, preserving older pages and without another approval round. Extended
its fixed standalone-review allowlist with --review routes, reusing identical
atomic copy, clean-checkout, source/render validation and before/after public
hash guards. Only the standalone HTML is allowed; JSON, config and source
files are excluded. The historical date (13 October 2026), four route selectors,
reset control and unified open assumptions explanation are already in the
reviewed HTML; no content/rendering changes were necessary.

Relevant verification before release: 12 route/frozen-review/atomic-publication
tests passed, including preservation of old pages and rejection of extra files,
altered date/assumption content and existing target; git diff --check passed.
Next: exact-commit CI, prepare/verify/publish as seaparser, then verify HTTPS,
exact returned bytes and interaction controls against the deployed response.
No service, Apache, database, weather or routing changes are part of this step.


Publication completed and verified: https://seaparser.com/vinga-ruttjamforelse.html
returned HTTP 200, text/html, validated TLS certificate (curl verify result 0),
and byte-for-byte approved artifact SHA-256
871adb4e6031b4734e35687d06be481d16d2a8dd45bc78078aabe183f6b51950.
The public tree contains exactly the previous 21 unchanged files plus this one
HTML file. No JSON/config/resources were added. Historical date 2026-10-13 is
visible. DOM execution of the exact HTTPS response passed all four named route
selectors, reset, the single initially open eight-item assumptions explanation,
and labeled SVG/native controls; no external resources are requested. No
visual-browser audit is claimed. No response CSP header overrides the reviewed
page policy. Sandbox DNS failed; the authorized network check succeeded.

Release da9a958 passed exact CI 39028331617 before activation. Private staging
and final verification receipt: /tmp/seaparser-route-publication-da9a958/
verified-publication-result.json. Next: preserve the published snapshot and
continue real-data development/source qualification separately. No further
activation or service changes are needed for this page.

## 2026-10-17: begränsad kandidat-/avgångsutökning med verkliga data

Arbetsrot `/tmp/seaparser-real-map-data`, branch `development/real-map-data`,
utgångspunkt 8de1620556373440d70aa2b9902d71064222e536. Nästa begränsade leverans
är implementerad: offlineaudit 2/4/8 kandidater × fyra explicita avgångar,
interaktiv utvecklingsbudget högst 16 kombinationer och en grafisk jämförelse
med karta, klickbart restids-/exponeringsdiagram och gemensamma vinnare.
`artifacts/real-route-budget/` innehåller HTML, fullständigt JSON, audit och
kalla workerprov. Befintlig offlinevisning för 2×2 är regenererad; ingen publik
webbrot eller tjänst är ändrad.

Slutlig varm audit: 6,677 / 11,261 / 22,180 s för 2/4/8 × fyra avgångar.
8×4 ger 8 430 172 resultatbyte och stannar offline. Kalla 4×4/8×2-workerprov
ryms inom oförändrade 20 s / 8 MB (14,21 / 15,24 s). Samma frysta dataset,
A*-graf, cache, 1000-posters sökbudget och fullständiga segment-/ankomstskydd
används. Alla sökningar trunkeras vid kandidatbudget; ingen global optimalitet.
Auto-0 kl. 12:00 UTC vinner både restid och komfortexponering. Ingen syntetisk
marin serie eller väderändring skapad. Källor förblir unverified och beräkningar
conditional_on_assumptions med assumed_fields separat. 900 m-taket är oförändrat.

Verifiering: låsta 26 Python-/40 npm-paketversioner kontrollerade, Python 3.14.4,
Node 22.22.1, npm 9.2.0. Samlad `scripts.check`: 160 domäntester + 288 övriga
tester godkända. Därefter nytt riktat ASGI/API-/processprov för 4×4 godkänt
(18,244 s inklusive testuppsättning); avvisar även 8×4 före jobbskapande.
Frontendens resurskontroll och fyra serveroberoende testfiler godkända,
inklusive nya diagram-/formulärtester. Relevanta nya gränsfall: 16 kombinationer,
strikta heltal/unika avgångar, exklusivt tidsstöd inklusive full ruttbudget,
kända globala komfort-/restidsurval och avvisad ofullständig ankomst.

PROJECT_BLOCKER: lokal `npm --prefix frontend test` fallerar i
`tests/map.test.mjs`; separat TCP-bindningsdiagnos ger
`PermissionError: [Errno 1] Operation not permitted` för 127.0.0.1:0.
Ingen upprepning eller publik demo som ersättning. Ordinarie GitHub CI för
exakt pushad SHA ska verifiera hela frontendintegrationen. Ingen ny hämtning,
installation, databasoperation, kostnad eller publicering i leveransen.

Nästa funktion efter godkänd exakt CI: större faktiskt gemensamt geografiskt
område och tidsstöd med egna grid samt landunderlag. Kontrollera disk och
överföringsestimat separat från resultatstorlek, återanvänd hashmanifest/cache,
ingen dubbelextraktion och ingen andra adapter. Höj inte 900 m före verifierat
helt rumtidsstöd. Kvarvarande marina proveniens-/mask-/utfärdandegap är oförändrade.

## 2026-10-17: större fryst vind-/marinbunt med cacheåteranvändning

Arbetsrot /tmp/seaparser-real-map-data, development/real-map-data, utgångspunkt
63a15cb6d013e543b12f2045b4485602067963cd (exakt CI success run 39030709333).
Nästa begränsade dataleverans: fixtures/vinga-expanded-20261017, med MET-native-
vind 132 noder och WAV/PHY på egna 4×4-grid, tolv timnoder 17 oktober 01–12 UTC.
Vågmask på exakt vågornas egna koordinater. Granskningsartefakt
artifacts/expanded-forecast-support/report.json. Befintlig adapter och MET-
materialisering återanvänds; ingen andra adapter och ingen syntetisk marin serie.

WAV-originalets befintliga 113 MB-cache återanvändes lokalt, utan nytt WAV-uttag.
Ny lokal vågfil 36 890 byte; exakt värde-/koordinatbevarande, inga tidsförskjutningar.
Efter separat estimat hämtades nya geografiskt/tids-/djup-/variabelavgränsade
PHY-/masksubset: uppskattad överföring 113 387 904 + 4 736 800 = 118 124 704 byte,
faktiska filer 27 546 + 17 928 byte. Befintliga 10/20 GB-överföringstak och
1 GB diskreserv kvar; filbudget nedåtbegränsad till 0,05 GB. /tmp hade cirka
2 GB ledigt, /home cirka 72 GB före uttaget. MET:s sex begränsade svar blev
88 399 byte totalt. Befintliga cacheposter/hashmanifest bevarade; inget identiskt
subsetuttag upprepades. Ingen installation eller ny betald resurs.

PROJECT_BLOCKER (löst): första PHY-estimatet gav TypeError eftersom katalogens
djup är en explicit lista utan minimum_value. Skrivskyddad koordinatdiagnostik
identifierade orsaken; hämtaren hanterar nu källästa listor med finita, entydiga
och förenliga nivåer och avvisar flera nivåer i ytintervallet. Nytt separat
estimat passerade före hämtning. Ytligaste källästa nivå är 0,5016462206840515 m.
--estimate-only hämtar/kopierar aldrig väderfiler. Ingen blind återkörning.

Verifierat: samlad scripts.check med låsta beroenden, 160 + 298 = 458 tester.
Därefter åtta riktade tester efter manifest-/bytebudgethärdning och ett riktat
reproducerbarhetsprov efter förtydligad blockerarkod. Kända referensfall kontrollerar
exakta nativevärden/tider, korrupt cache, ofullständigt tidsstöd, saknat hörn,
egen maskgeometri och förbud mot att ge ström vågmask. Ny verklig fryst bunt
kontrolleras offline; standardens 13-oktober-referenspin avvisar 17-oktober-data.
Oförändrad standardrouting och dess API-/process-/ankomsttester passerade.
Lokal frontendintegration upprepas inte mot känt TCP-bindningshinder; exakt CI
ska verifiera hela frontendflödet efter push. Ingen publik demo används som ersättning.

Större routing är INTE aktiverad. 900 m-taket, lokal 1 m-representationsgräns,
hårda väder-/land-/datastöd-/ankomstkontroller och befintliga antaganden oförändrade.
De nya stora marina griden avvisas av befintlig räta-axlar-representation.
Alla nio celler per produkt har kompletta granskade värden vid samtliga timnoder,
men detta är inte mask-/tids-/navigerbarhetsbevis. Endast gemensamma koordinat-
etiketter 01–12 UTC redovisas; original-WAV och ARCO:s time:mean jämställs inte.
Källor unverified, utfärdandetider okända. Det nya resultatet är diagnostic_only;
standardens routing förblir conditional_on_assumptions med assumed_fields separat.

Nästa funktion: verifierad native-geometrirepresentation i befintlig marinadapter
samt större landunderlag, sedan helt rumtids-/segmentstöd före höjt routingområde.
Återanvänd den nu frysta 17-oktober-bunten; hämta inte om dessa subset. Fortsatta
källgap: egna ström-/vindmasker, tidsmedelssemantik, run-/utfärdandeevidens.
Inga databasoperationer, privata konfigurationsändringar eller publiceringar.

## 2026-10-17: native marin geometri, större land och konkret startblockering

Utgångspunkt f6773f9ec6ecdfdb5fc3365d23da4cd2a9bf7888, exakt CI success run
39031990979. Arbetsrot /tmp/seaparser-real-map-data, development/real-map-data.
CopernicusMarineAdapter har nu ett explicit native-läge som återanvänder samma
fält-/djup-/mask-/metadatanormalisering. Egna lat/lon-axlar, direkt punktinterpolation
och konservativ hel-disk-/tidskontroll ersätter inte standardens 1 m-läge.
Ingen andra adapter, omgridning eller ny marin hämtning. NativeMarineDataset är
en fryst representation/miljö, utan transport, SQL, filåtkomst eller callbacks.

Analytiskt WGS84-diskhölje använder M,N>6300000 m, utåtrundning och 1 m numerisk
stödreserv. Alla hörn i berörda nativeceller över hela boxen/tiden krävs; luckor
kan ge konservativt avslag utanför banan. Hs certifieras mot exakt källhörnsmaximum,
inte provpunkter eller komfort. Komponentprov för marinen: 2000 m-disk, ett
3000 m långt lokalt segment under 1200 s. Källornas mask-/tids-/run-blockerare
och issued_at=None kvarstår. Ingen käll- eller fysisk tidskvalificering.

Ett enda avgränsat OSM-uttag gav 3298228 byte under 5 MB/30 s-gränsen. Offline
assembly gav 24 slutna ringar/höljen för 1500 m granskning plus 10 m urvalsmarginal;
3 öppna kedjor ligger utanför ytan. Relevanta öppna kedjor, saknade noder eller
ambigua identiteter avvisas. Källa/ODbL/versionsdata/hash/urvalsyta och okänt
fullständighet/djup bevaras. Källa i /tmp/seaparser-expanded-land-20261017;
fryst relevant geometri fixtures/vinga-land-expanded-20261017.geojson.
Ingen ny betald resurs, global installation eller privat konfigurationsändring.

Viktigt fynd: gamla startpunkten (300,-400) ligger i nya höljet osm-23053759.
Ny 17-oktober-komposition använder därför nya landunderlaget och ger
endpoint_blocked, inga kandidater och ingen plan. Den får inte fortsätta på
äldre sexpolygonutdraget för att visa ankomst. Explicit landgranskningsprojektion
för större lagrade höljen är separat; gamla ruttkoordinaters gränser tas inte bort.

Separat angivet kompositionsprov (500,0)→(500,350), alla 24 landhöljen, samma
ruttmotor och verkliga MET/WAV/PHY: villkorad ankomst 144,521 s, segmentgränser
uppfyllda inom modellen och ankomst kontrollerad. Detta är ett specificerat
segment, inte automatisk sökning eller navigationsråd. Uppskattad båt/ej validerad
komfort. Båda exemplen använder namngiven development-weather-native-assumptions.json
med support_radius_m=900. Originalfakta och assumed_fields hålls åtskilda;
source_qualification=unverified/result_qualification=conditional_on_assumptions.
Ordinarie API:s historiska konfiguration och 900 m-taket oförändrade; publik
tjänst/webbrot orörd.

Artefakt artifacts/native-marine-review/index.html, report.json, result.json och
specified-route.json. Offlinekommando: python -B -m scripts.native_marine_review
--output artifacts/native-marine-review. Datum i grafiken kommer nu från
faktiska indata; befintlig 13-oktober-visning är byteidentisk i regressionstestet.
Dokument: docs/native-marine-geometry.md med bevis, källor och begränsningar.

Verifierat: 30 riktade adapter-/kompositions-/land-/utvecklingsvädertester; samlad
scripts.check 160+307=467 tester, låsta beroenden och domängränser godkända.
Riktat linjärt referensprov efter läsbarhetsrefaktor och slutlig riktad kontroll
av blockerad presentation/landidentiteter. Lokal känd TCP-blockering kringgås
inte; exakt GitHub CI verifieras efter push. Loggar /tmp/seaparser-native-marine-check.log,
/tmp/seaparser-native-composition-targeted-final.log och /tmp/seaparser-native-last-targeted.log.

Nästa funktion: tillåtna ändpunkter och uppmätt begränsad nod-/kandidatgenerering
med alla nya hinder kvar som hårda segmentkontroller, därefter samlat vind-/marin-/
land-/rörelseramsstöd före större routing. Ingen allmän optimalitet, inga borttagna
process-/sök-/väder-/mask-/ankomstskydd och ingen höjning av 900 m för att passera.
Återanvänd frysta 17-oktober-data och nytt land; hämta inte om dem.

## 2026-10-17: Native kandidataudit med alla24 landhinder

Fria ändpunkter(500,0)–(500,350), samma frysta17-oktober-MET/WAV/PHY, 2/4/8kandidater och fyra avgångar. Explicit offlinebudget66noder rymmer60noder; 26 stoppar. Exakt Fraction-boxavvisning och begränsad256geometri-LRU bevarar slutna hinder-/marginalpredikat, inga hinder tas bort. Grafprov90,840s före,11,581s efter; samma kandidater.

Auditen13,506/13,128/14,630s ger8/16/32 ankomster, alla med fulla segment-/ankomstkontroller. Samma vinnare auto-0 kl04:00,136,813299s och60,3404 exponering. Grafisk artefakt artifacts/native-candidate-budget/index.html; audit/result/workers JSON. Källor unverified, resultat conditional_on_assumptions och antagna fält separat. Båt uppskattad/komfort ej validerad, djup/landfullständighet okända.

Kalla processprov:2×4=14,894s och8×2=15,965s passerar20s/8MB;4×4 överskrider20s medan riktad lokal kontroll överlappar. Ingen interaktiv nodutökning; generella process-/sökgränser och900m kvar. Ingen hämtning/publicering/DB-ändring. Samlade kontroller godkända:161+310=471tester, låsta beroenden/syntax/domängränser. 16riktade tester godkända före fullkontroll. Loggar /tmp/seaparser-native-budget-check.log och /tmp/seaparser-native-budget-final-targeted.log. ExaktCI ska verifieras efter granskad commit/push. Nästa funktion: explicit valbar utvecklingskomposition först efter robust uppmätt processbudget, sedan helt större vind-/marin-/land-/rörelseramsstöd.

## 2026-10-17: Valbar native-profil med stödd kandidatgraf

Exakt Fraction-medlemskap begränsar enbart kandidatnoder till sluten900m-disk. Alla24hinder är kvar för varje grafkant och integrerad färd. Ändpunkter utanför disken avvisas; ett analytiskt långtväggsfall visar att externa hinderhörn aldrig tar bort hindret. 21noder ryms inom26gränsen och samma första8kandidater som förra60nodsgrafen fås, grafprov0,718s.

Ny explicit enumprofil vinga-native binder fasta17-oktober-antaganden/väder och nya landunderlaget. Standard13okt/publik tjänst oförändrade. Befintlig karta/form/GPX återanvänds med native.html och lokal granskningsprofil; avgångsetiketter härleds från faktisk scendeparture. API behåller16kombinationer,26noder,1000expansioner/köposter,20s/8MB och2aktiva processer. 900m oförändrat; ingen ny hämtning/adapter/DB/publicering.

Audit2/4/8×4 på3,533/2,829/4,339s; samma vinnare auto-0 kl04:00,136,813299s och60,3404exponering. Sekventiella kalla STANDARDarbetare2×4/4×4/8×2 på6,921/10,673/8,089s, alla under20s/8MB. Artefakter artifacts/supported-native-routes/{index.html,audit.json,result.json,workers.json}; docs/supported-native-routing.md. Fulla segment, absoluta valda gränser, datastöd och ankomst bevarade. Källor unverified, resultat conditional_on_assumptions, antagna fält separat; uppskattad båt/ej validerad komfort.

Riktat API-/geometriprov fångade först1e-9m skillnad från WGS84-rundresa i jämförelsetest; testet rättat att använda samma transformerade ändpunkter. Det kända TCP-hindret gör lokal fullfrontendintegration otillförlitlig; bred frontendtestkörning exit1 i mapfil, ingen publik ersättning. JSsyntax/build/check och riktad DOM-budgettest passerar; full API-/Leaflet-/GPX-integration med native ingår i ordinarieCI. Samlade låsta kontroller godkända:162+313=475tester, syntax/lås/domängränser; omverifierade40npmversioner motlåset. Logg /tmp/seaparser-supported-native-check.log. Efter korrigerad rundresejämförelse passerar även riktat grafprov. ExaktCI ska verifieras efter push. Nästa geografiska mål: helt kombinerat större rumtids-/land-/rörelseramsstöd före900m-höjning.


## 2026-10-17: återhämtad rörelseram och grafisk jämförelse

Alla fem föregående commits (63a15cb, f6773f9, a3cb75e, d640f46, cb1600e)
verifierade som redan pushade via arbetsbranchens faktiska GitHub-SHA cb1600e.
Usage-avbrutna nio filer granskade och bevarade. Gemensamt körlås hålls under
återhämtning; senaste worker avslutad, inget nytt autonomipass.

Fysisk E/N-vind/ström/vattenfart i m/s separeras från WGS84-AEQD-positionsrate.
Inverse differential används för strömkompenserad fysisk kurs; J används vid
förutsagd och faktisk mittpunkt för positionsändring. SI-/ramkrav valideras.
Oberoende geodetiska, analytiska och konvergensregressioner godkända.
Alternativet kopplat till export med --motion-frame, explicit källantagande
och algoritmidentitet; äldre profiler/artefakter bevaras.

artifacts/motion-route-review visar verkliga 17-oktober-data, 24 hinder och
16 alternativ, rörelseramsförklaring och fortsatt villkorad kvalificering.
Se motion-frames.md. Befintligt atomiskt publiceringsflöde utökat med fast
ny adress /vinga-ruttjamforelse-ramar.html; äldre sidor skrivs inte över.
Leveranskontroller och exakt CI/publiceringskvitto redovisas efter verifiering.
SSH-konfiguration/DNS blockerade terminalens remoteåtkomst; GitHub-anslutningen
fungerar och används utan systemändring eller visning av hemligheter.

## 2026-10-17 – sammanhängande PoC vid Vinga

Återhämtningen är redan levererad som 2e0e0f8 (push och exakt grön CI
39054592940); inga nio kvarvarande filer återstod. Ny huvudprioritet i AGENTS
/backlog: fungerande PoC framför fler detaljgranskningar. Ny PoC-profil återanvänder
projekterad fysisk rörelse och verkliga frysta MET/WAV/PHY utan nya datauttag.
Gemensam karta, val, jämförelse, distans/väder och GPX, med utfällbara antaganden.
En uttrycklig statisk katalog gör flödet användbart på befintlig webb utan
root-ändring av äldre API-tjänst. Fria kartpunkter kräver aktiverat nytt API;
publicerat urval har tre punkter och fyra avgångar. Se docs/poc.md för omfattning,
publiceringskommandon och återställning. Befintliga offentliga sidor bevaras.
Samlade lokala låsfilskontroller kördes: 166 domäntester och 328 övriga tester.
Fyra publiceringsprov träffade en tillfälligt osynkroniserad asset/byggkvittokopia
under sista metadataredigeringen; kvittot synkroniserades och alla fyra passerade.
Ett befintligt 16-kombinationsprov slog i tidsgränsen under samtidig körbelastning;
separat omprov passerade, oförändrad 20-sekundersgräns. Nya riktiga PoC-workerprovet
passerade också. Fulla frontendkontroller och exakt CI avslutar leveransen.
Frontendens statiska kontroller och fem av sex testfiler passerade, inklusive det
nya sammanhängande PoC-provet. Den socketberoende `map.test.mjs` kunde inte
levereras grönt i den isolerade körmiljön; exakt CI kör samma fulla testsvit.

## 2026-10-17 – fria kartklick i PoC

Utgår från b2a2d239. Egna start-/målpunkter kopplas till befintlig PoC-profil,
med tydlig 900m-täckning, korrekt formulärsynkronisering, tids-/täckningsbesked
utan gamla GPX-länkar och bibehållna land-/vädergränser. Riktig worker med egna
koordinater passerar. Ny sammanhängande Leaflet/API/jämförelse/GPX-regression
används både i CI och efter API-aktivering. Befintlig API-tjänst kräver rootbyte
av release och Pythonmiljö. Avgränsat underlag för separat PoC-tjänst på localhost:8766, två proxyregler
för /api/poc/, låst miljö, backup och automatisk återställning förbereds.
Äldre API-process och publika sidor bevaras; inga TLS-/DocumentRoot-/DB-ändringar. Se docs/poc.md.
Lokala samlade kontroller: 166+330 Python-tester godkända vid körningen;
därefter de tre uppdaterade aktiveringsproven gröna. Fem frontendtestfiler gröna;
två riktiga HTTP-serverprov blockeras lokalt av socketförbud och körs i exakt CI.
API-aktiveringen måste utföras som root i vanlig terminal; förberett är inte startat.

## 2026-10-18 – regionalt Vinga–Uddevalla-uttag i samma PoC

Återanvända, hashkontrollerade MET-/Copernicus-filer ger 31 gemensamma
timsteg 18 oktober 09 UTC–19 oktober 15 UTC. OSM-uttaget innehåller
585179 noder och 12001 kustvägar. Ingen upprepad väderhämtning.
Målets egna våg- och strömstenciler saknar ett hörn vid samtliga tider;
även omgivande Uddevalla-celler saknar bilinjärt stöd. Dataförkontrollen
stoppar därför före ruttmotorn: inga tillverkade restider, komforttal eller GPX.
Samma PoC får ett valbart regionalt exempel, fria kartpunkter för datastöds-
kontroll, verkliga provvärden, giltigheter och synliga luckor. Befintlig
Vinga-beräkning, export och tidigare sidor behålls. Kusturvalet är enbart
visning; öppna kustkedjor görs inte till falska routingpolygoner.
Full regional routing kräver källdata med stöd i fjordarna samt regional
landtopologi och segmentkontroll; högre sökbudget ensam löser inte dataluckan.

## 2026-10-18 – granskade regionala grundkomponenter

Femtimmarspassets första begränsade leverans startade 12:35:09 UTC.
Exakt e1c0bd4914aeffb623c0c65ecc2695e3136e4aaf verifierad COMPLETED/SUCCESS
i GitHub-run 39127363912, inklusive frontend och publicerade HTTPS-resurser.
De tio överlämnade filerna har bevarats och granskats. Shapely 2.2.0 med
Linux CPython 3.14-hjulhash verifierad mot officiella PyPI och låst.
Riktad OSM-vattenmaterialisering, hela-segment-/marginalkontroller,
uttryckliga reservpolicyer/proveniens samt deterministisk geometrisk
kandidatsökning är färdigställda som komponenter. Reservvindens källpositioner
binds till dess faktiska native-axlar; ogiltiga värden kan inte döljas som luckor.
Sökgränser rapporteras även när flera försök ger samma kandidat.

Återanvänd regional bunt, 67 MiB, utan nya uttag eller dataöverskrivning.
Faktiska ändpunktsprov hittar vattenförbundna marina källor på 0,5–1,2 km.
Ett högst 250 m-stödprov längs den sparade cirka 88,96 km-kandidaten hittar
25 provpunkter per marin produkt utan rak landfri reservförbindelse.
PROJECT_BLOCKER: reservmetoden behöver uttryckliga kontrollerade vattenvägar
runt uddar innan hela regionala färden kan simuleras. Det är ett datastödsprov
med idealiserad 5 kn-tid, ingen verklig restid eller vädergränsverifiering.

Lokalt passerade 528 Python-prov i samlad lås-/syntax-/arkitekturkontroll,
följt av 20 riktade prov mot slutlig kod inklusive två tillagda regressioner.
Frontend och exakt leverans-CI redovisas i överlämningen efter körning.
Ingen ny publik aktivering i denna grundleverans. Nästa del: kontrollerad
vattenförbindelse, därefter befintlig färdmotor, regional rörelseram och
synliga uppskattade segment/jämförelse/GPX i samma PoC. Se coastal-reserve.md.

## 2026-10-18 – reservförbindelser genom sammanhängande vatten

Andra begränsade delen i samma aktiva pass, från 12:53:40 UTC. Den tidigare
grundleveransen 65c5f009d92cd0297b2a135f6c176bbe2f18a284 har exakt grön CI.
Ny explicit variabelpolicy aktiverar kontrollerade vattenvägar för vågor/ström
och stänger vindreserv. Samma rena geometrisökning och hela landsegment används;
avståndstaket gäller funnen vattenväg. Källförsök, celler, expansioner, grid och
marginal är konfigurerade. Källa/tid/värde, vatten-/direktavstånd, förbindelsens
WGS84-punkter och begränsad sökning följer varje reservpost, med hög osäkerhet.

Verkligt stödprov med bevarade data och kandidat ger 820 produktuppslag vid
410 geometriska provpunkter, utan kvarvarande luckor. De tidigare 25 luckorna
per marin produkt är lösta i detta stödprov. 517 variabelposter har konkreta
vattenförbindelser som separat återkontrollerats mot land och rapporterad längd.
Största vattenavstånd 4 273,42 m, största absoluta tidsavvikelse 1 798,88 s;
78 poster redovisar begränsad källsökning. Kallt prov 22,49 s, omprov med extra
förbindelsekontroll 14,77 s. Detta bevisar inte regional färdtid eller allmänt
datastöd: provtiderna är fortfarande idealiserade utan strömpåverkan.

24 riktade prov och samlade 534 Pythonprov godkända med låsta beroenden,
syntax-/arkitekturkontroller. Ingen ny installation, källa, datahämtning,
publicering eller ändring av aktiv startare/lås. Befintlig PoC är oförändrad.
Exakt CI redovisas i överlämningen efter push. Nästa funktionsdel: komposition
av befintlig normalisering och färdmotor, regional rörelseram/segmentkontroll
samt per-segment-osäkerhet och uppskattningsstatus i karta/jämförelse/GPX.

## 2026-10-18 – verklig regional uppskattad färd

Tredje begränsade delen i samma pass, från 13:11 UTC. Samma CF-/MET-normalisering
och befintlig färdmotor komponerar nu regional vind, vågor och ström med
landmedvetna reservuppslag. Råbunten återanvänds utan nya uttag eller omskriven
inventering. Regional WGS84-/AEQD-rörelseram är separat från äldre lokala gränser.
Hela landsegment, 10 m marginal, källstödsvittnen, valda vädergränser, tidsstöd
och separat ankomstkontroll finns kvar. En särskild regional omslutning av
native-koordinater är ett uttryckligt numeriskt modellantagande, inte källverifiering.

Den verkliga sparade Vinga–Uddevalla-kandidaten når mål: 88 955,90 m fysisk
distans, 34 452,631393 s (cirka 9 h 34 min), syntetisk komfortexponering 3 449,09.
592 accepterade segment över 33 ben; inga saknade mittpunktsvärden.
8 232 reservposter är bundna till segmentens provpositioner/tider. Källmetadata
med issued_at=null, specifika källantaganden och modellantaganden hålls separata.
Resultatet är estimated_high_uncertainty, weather_limits_verified=false och
motorns weather_segment_status=not_available. Inga gamla UI-/GPX-grindar lyfts.

Första körningen överskred 60 s med 93,15 s. Begränsad memoization av identiska
uppslag gav 46,68 s i ny process, exakt samma restid/komfort: inläsning 12,03 s,
motor 30,99 s, presentation 2,47 s, plus slutlig serialisering. Detta avser
sparad geometri; ny fri-punkt-sökning och fler alternativ behöver samlad budget.
Avslutande CLI-prov gav identiskt färdresultat men 62,10 s. PROJECT_BLOCKER:
regionala 60 s är inte robust kvalificerat. Beständig återanvändning och mätt
kandidatsökning behövs före interaktiv aktivering; leveransen är offline.

540 Pythonprov godkända i samlad lås-/syntax-/arkitekturkontroll. Riktade prov
prövar analytisk färdtid/komfort, determinism, hårda hinder-/väder-/datagränser
och oberoende regionala geodetiska referenser. Kommandorad i scripts/simulate_coastal.py;
se coastal-voyage.md. Exakt CI redovisas i överlämningen efter push.
Ingen ny publicering. Nästa: regional scen och uppskattningspresentation i samma
PoC, GPX med explicit osäkerhet, fria kartpunkter och mätt kandidat-/jobb-/cachebudget.

## 2026-10-18: Beständig regional materialisering med oförändrat färdresultat

Ny uttryckligt vald indatacache återanvänder befintliga MET-/NetCDF-läsare före
samma normalisering. Säker JSON bevarar exakta Decimal-värden, marina null och
källmetadata/antaganden. Identiteten binder källbytes/manifest, begäran,
läsarvalidering och beroendelås; varje träff hashar råkällorna. Processlås,
atomisk upptagning och innehållshash skyddar återanvändningen. 64 MiB/post,
256 MiB totalt och 256 MiB diskreserv; ingen automatisk radering eller transport.

Slutlig verklig kall process tog 67,27 s med miss, inläsning 13,61 s. Ny process med
beständig träff tog 41,82 s, inläsning 6,49 s. Tidigare par gav 55,45/38,14 s.
Kallstarten överskrider 60 s; motorvariation särredovisas och gränsen är inte robust.
Inga motorresultat eller geometribeslut lagras beständigt. Hela färdresultatet
är byteidentiskt med tidigare okachad körning: 13 071 350 byte, SHA-256
8853ec2a853c7363a34db10ad3c4bec968297fcd00de984df0c84e2324a9e4ae.
Alla 30 bevarade råfiler har oförändrade för-sessionen-tider. Inga nya uttag.

Riktade prov täcker korrupt cache, ändrade källbytes, disk-/bytebudget,
misslyckad upptagning och exakta Decimal-/null-/metadata genom beständig träff.
Se materialized-cache.md. Samlad leveranskontroll och exakt CI redovisas vid
push/överlämning. Den regionala fria-punkt-/fleralternativsbudgeten är fortsatt
PROJECT_BLOCKER före interaktiv aktivering. Nästa: regional scen, jämförelse
och särskilt märkt GPX i samma PoC, därefter samlad kandidat-/jobbprestanda.

## 2026-10-18: Regional faktisk modellfärd i samma PoC och uppskattnings-GPX

Vinga–Uddevalla-vyn öppnar nu den faktiskt simulerade 18-oktober-färden med
orange streckad linje, hög osäkerhet, 88,96 km/9 h 34 min, faktisk vind/Hs/ström
och oförändrad syntetisk komfortmetrik. Ett simulerat alternativ redovisas
uttryckligt; regional jämförelse mellan flera vägval och fri-punkt-färd återstår.
Ändrade kartpunkter, koordinater eller tider tar bort sparad färd och GPX.

8 232 reservposter för 592 segment bevaras förlustfritt i cirka 1,42 MB JSON,
med valbart segments källposition/tid/värde, avstånd, tidsavvikelse och hela
vattenförbindelsen. Återställning verifieras mot originalsimuleringens kända
segmenthash. Utfärdanden som null, källantaganden och modellantaganden skiljs.
GPX är fristående med samma evidens, ruttsammanfattning och 34 planerade
vägpunkter; huvudtext/metadata anger HÖG OSÄKERHET och ej verifierade vädergränser.
Tidigare GPX-grind för verifierat segmentstöd är oförändrad och testas fortsatt.

Presentationsbygget återanvänder den kontrollerade befintliga banken. Ny statisk
publicering använder samma allowlist-/backup-/hash-/rollbackflöde; ingen API-
aktivering eller nya datauttag behövs. Kall 67,27 s och fria punkt-/alternativ-
budgeten är fortsatt PROJECT_BLOCKER för regional liveprofil. Se coastal-presentation.md.
Riktade Python-/Leaflet-/UI-prov passerar; samlade kontroller, exakt CI och faktisk
publiceringsstatus förs till överlämning/URL-logg vid leverans.

## 2026-10-18: Nästa begränsade regionala prestandadel

Exakt CI för d9fd35df27ae88c15f30a461eee526cb2dcc24d1 återverifierad
completed/success, inklusive publika PoC-hashar. Profilering av bevarad verklig
färd visar att reservförbindelsernas geometrisökning dominerar. Förberedda
vattenkomponenter, instansbunden exakt medlemskaps-LRU och återanvända
gridpunkter minskar upprepat arbete utan ändrade sökresultat/kontroller.
31 riktade prov passerar. Slutlig tom cache 43,76 s, ny process/träff 39,39 s;
hela resultatfilen har fortsatt SHA-256 8853ec2a853c7363a34db10ad3c4bec968297fcd00de984df0c84e2324a9e4ae.
Källa och cache återanvänds; inget nytt uttag. Se materialized-cache.md.

PROJECT_BLOCKER: samlad budget för ny sökning med fria punkter och flera
verkligt simulerade alternativ är ännu inte kvalificerad. Nästa funktion
komponerar detta med befintlig motor/normalisering och mäter hela jobbet;
ingen API-aktivering eller ändring av den publicerade sparade färden ingår här.
Samlade lokala kontroller passerar: 556 Python-tester, frontendstruktur och
30 frontendtester, med låsta beroenden och oförändrade tidsgränser.
Exakt leverans-CI redovisas i sessionens överlämning.

## 2026-10-18: Fria regionala punkter och två kompletta offlinefärder

De åtta bevarade arbetsfilerna är färdigställda som en sammanhängande
offlinekomposition. Fria WGS84-ändpunkter, uttrycklig avgång och valda gränser
går genom samma frysta normalisering och färdmotor. Versionerad sökbudget
begränsar grid, expansioner, kandidater, vägpunkter och marginal. Två faktiska
Vinga–Uddevalla-alternativ når mål: 88,09/89,69 km, 34 106,63/34 997,47 s och
syntetisk komfortexponering 3 254,71/3 013,72. Ingen global optimalitet påstås.

Exakta batchade gränskontroller, direkta gridnycklar, batchade ändpunkter,
begränsad identisk frågeåteranvändning och JSON-nativt resultatträd bevarar
hela resultatfilen byteidentiskt: 25 125 746 byte, SHA-256
285318e3e0895bec2d55db6e7ce693c41df8b2128d8ee5946a5d7e953377f9a4.
Samtliga käll-/reservposter och osäkerhetssegment kvar; inga nya uttag.

Slutligt prov med delad cacheträff och tjänstens en-trådsinställning:
80,01 s internt / 89,40 s inklusive uppstart, motor 37,81 s och topp-RSS
550 334 464 byte. Resultatstorleken klarar 64 MiB. PROJECT_BLOCKER:
hela 60 s och 512 MiB är fortfarande inte kvalificerade; ingen ny API-/UI-
aktivering eller publicering i denna del. Nästa: minska kvarvarande fulla
presentationskopior och geometritid, sedan verifiera hela API-processen.

Se coastal-free-planning.md för återkörning, bevisstatus och begränsningar.
Riktade krav-/referensprov passerar. Samlade lokala kontroller passerar:
562 Python-tester, frontendkontroll och 30 frontendtester med låsta beroenden.
Exakt CI redovisas i sessionens överlämning. Den separat publicerade grafiken bevaras och dess
källpatch ska integreras före nästa publika presentationsbygge.

## 2026-10-19: bounded Trelleborg–Strömstad source acquisition

New active pass: 07:54:32–12:54:32 UTC, unchanged absolute deadline; no subagents.
The existing capture/reader accepts exact hourly windows up to the native MET
59-step horizon. Longer requests are split into six-step hash-indexed files;
interrupted chunks are reused, and the reader rejects gaps, overlap, altered
bytes, shape/axis/unit changes and invalid values. Existing 31-step bundles
retain their single-file format. Cache identity covers every indexed chunk.
The capture wrapper records command/PID and obeys the earlier of one hour or
session deadline minus shutdown allowance. Public responses require disk reserve.

Pinned request: settings/trelleborg-stromstad-capture.json, bbox
10.5,55.2–13.5,59.15; 2026-10-19 09Z through 2026-10-21 10Z (50 steps).
New run/region are absent from the old Vinga bundle, which is preserved.
Actual wind and Baltic WAV/PHY/static data were acquired under the shared data
root; marine estimated transfer 832,446,400 bytes, output about 26 MB. The
50-step MET capture is about 83 MB. Both public Overpass instances failed
locally (alternative HTTP 500); no land is inferred or bypassed. The existing
CI public-source capture path now accepts [capture-trelleborg-land], uses the
same immutable request and returns only public source blobs. No marine
authentication or new account is supplied to CI.

Official coverage checked 2026-10-19:
https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_PHY_003_006/description
https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_WAV_003_010/description
Both include Danish Belts, Kattegat and Skagerrak; this does not qualify local
wet support, metadata or navigability. Offshore coverage is not assumed.
Alternative Overpass endpoint is listed by
https://wiki.openstreetmap.org/wiki/Overpass_API .

17 focused tests pass, including chunk partition, physical values, exact time
window, gap rejection and cache identity; the real legacy 31-step reader also
passes. Full offline checks and exact commit CI are recorded in autonomy logs.
Current public health is ok, zero local/regional jobs; regional scene still
exposes only the old Vinga–Uddevalla bundle. systemd WorkingDirectory is the
31ba37d5 release. No new scenario or new API release is published by this step.
Next: obtain/polygonize coastline, measure expanded materialization and frame/
search budgets, then simulate and expose full or explicitly partial routes in
the same PoC. Data-only capture is not a functioning scenario.

The initial full offline run exposed an existing test isolation defect: the
rollback unit test inspected the now-active host PoC cgroup despite mocked
systemd state. Its cgroup fixture is now isolated and explicitly checks both
empty and populated process lists; production rollback checks are unchanged.
The corrected five-test activation suite passes. A complete final rerun follows
this correction, including the existing frontend checks/tests.

Final local validation: 167 domain + 408 application/infrastructure tests pass;
syntax, architecture, pinned dependency and frontend static checks pass. Nine
frontend test files passed in the restricted environment; the two socket-based
files passed when local HTTP sockets were permitted (7 tests passed, 1 optional
public test skipped). No new dependencies were installed. Final logs:
scenario-capture-final-check-20261019.log and
scenario-capture-socket-tests-20261019.log under autonomy/logs/.

## 2026-10-19: Compact Trelleborg source loading

Reused the existing 50-hour Trelleborg–Strömstad raw bundle without any new
extraction. Native wind retains validated exact decimal row tokens, with a
bounded expansion cache; NumPy conversion now proceeds row by row so it cannot
retain millions of temporary Decimal objects. Persistent materialization uses
lossless bounded compressed JSON and avoids a second cold deserialization.
Existing 64 MiB entry / 256 MiB total cache and 1 GiB service limits remain.

Actual full-source preflight (not a route/API qualification), one library thread,
1100 MiB address-space cap: cold 45.52 s / 789.2 MiB peak RSS; warm new process
8.62 s / 614.2 MiB. Both loaded 50×455×208 wind nodes, all three marine products
and finite wind components. Cache entry 61,470,327 bytes. Earlier failed
intermediate entries from this pass were preserved with verified hashes under
`/home/web/seaparser/data/materialization-preflight-preserved-20261019T1146/`;
pre-existing cache and all raw sources were retained.

OSM admission and the water builder release processed XML elements instead of
retaining the complete tree. Missing references, Overpass remarks and incomplete
XML remain failures. A 240-second profile of the original full water build
localized the remaining runtime blocker to union and negative buffering; no
water geometry or route is claimed. All original topology and land guards remain.

579 Python tests pass, including exact precision/scale/signed-zero roundtrips,
compression framing and decoded budgets, ragged-grid rejection and incomplete
coastline admission. No dependency installation, service change or publication.
At the live check, the static PoC and legacy API returned HTTP 200; the PoC API
returned 503 and its existing 31ba37d5 unit was inactive. Admin must restart the
existing unit (not rerun its installer). Next: finish land materialization, then
qualify the larger motion/search frame and full or explicitly partial route in
the same PoC before proceeding to either offshore scenario.

Real streamed XML inventory: 14.70 s / 262.6 MiB peak RSS under a 700 MiB
address-space cap, 1,030,000 nodes / 19,848 ways / 14,125 closed ways; counts
matched the preserved inventory and source hash was unchanged. This verifies
admission memory, not completed polygonization or navigability.

Frontend static check and all 37 frontend tests completed: 36 passed, zero
failed, one optional public test skipped. Local real-worker map/API/GPX tests
passed; this does not imply that the inactive public PoC API was activated.
