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
