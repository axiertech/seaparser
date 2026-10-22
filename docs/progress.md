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

## Miljö- och anslutningsverifiering 2026-10-12

Aktuell uppgift: verifiera uppdaterad venv/Python/pip, köra alla befintliga
tester och göra uttryckligen godkänd skrivskyddad databasdiagnostik med vanliga
projektroller. Inga administratörsuppgifter, databasändringar eller migrationer.

Verifierat som Linux-användaren seaparser:

- Python 3.14.4 uppfyller projektets krav >=3.14,<3.15. Projektets interpreter
  är `/home/web/seaparser/app/.venv/bin/python`, med separat prefix från `/usr`.
  Systempaket och användarens site-packages är avstängda.
- Pip saknades initialt trots att ensurepip nu finns. `make prepare-python`
  slutförde miljön enligt befintligt mandat. Pip 25.1.1 finns i projektets venv;
  `pip check` passerar. Den tomma, hashstyrda requirements.lock behandlades
  utan externa projektpaket; `pip list` visar endast pip.
- `make check` passerar: 38 prototyptester och 4 konfigurationstester,
  syntax/TOML, beroendebas och domängränser. Frontendsyntax passerar och
  `node --test` avslutas korrekt med 0 tester; inga frontendprodukttester finns.
- psql-klienten är PostgreSQL 18.6. Detta verifierar inte serverversionen.

Utvecklingskonfigurationen kunde laddas med projektets skyddade laddare, som
kräver databasnamn och roll seaparser. Det är konfigurationsvalidering, inte
verifierad serveridentitet. Anslutningsförsök med psql -X -w och
default_transaction_read_only=on misslyckades före någon SQL-körning.
Separat TCP-diagnostik mot samma konfigurerade mål gav PermissionError,
errno 1 (operation inte tillåten i körmiljön). Ingen rå privat feltext,
anslutningssträng eller något lösenord har skrivits ut.

Databasnamn på servern, aktuell databasroll, PostGIS, rollmedlemskap samt
databas-, schema- och tabellbehörigheter är därför **inte verifierade**.
Vid denna tidigare kontroll kunde den då föreslagna testmiljön inte verifieras.
Förslaget och dess administratörskommandon har nu ersatts av beslutet nedan.

## En utvecklingsmiljö – genomförd uppdatering 2026-10-12

AGENTS.md, konfigurationsladdare, exempelkonfiguration, tester, migrationsplan,
CI och dokumentation är uppdaterade till endast development och seaparser.
Separat testkonfiguration, SQL för testdatabasskapande, HBA-underlag och
migrationsjobbet i CI är borttagna. Inget separat testlösenord krävs.
Tidigare testmiljöinstruktioner ovan är historik, inte aktuella nästa steg.
Privat konfiguration är orörd och Git-skyddet för hemligheter finns kvar.

Enhetstester använder explicit syntetisk inmatning som ersätter privat fil helt.
Fel och objektvisning döljer lösenord; fel miljö/identitet och äldre testnycklar
avvisas. Databastester får endast använda rollback/testegna objekt, utan att
ändra befintliga data, sekvenser eller externa sidoeffekter. Inga skrivande
integrationstester har införts eller körts.

Verifierat: make check passerar med 38 prototyp- och 4 konfigurationstester.
Frontendens syntax passerar; testkommandot hittar fortfarande 0 tester.
make migration-plan passerar utan konfigurationsläsning eller anslutning.
Git diff --check passerar. Befintliga prototype/-ändringar lämnades orörda.

Nytt kommando: `.venv/bin/python -B -m scripts.diagnose_database`.
Det använder enbart projektrollen, ren psql-miljö, lästimeout och
BEGIN READ ONLY/ROLLBACK. Rå feltext och privata värden visas inte.
Försöket stoppades av PermissionError errno=1 vid TCP-anslutningen, innan
PostgreSQL nåddes. Detta bevisar ett hinder i körmiljön, inte ett fel i
PostgreSQL-autentisering eller HBA. Sessionens policy har sandbox_approval
avstängt och tillåter därför ingen tillståndsbegäran för körning utanför sandboxen.
Serveridentitet, PostGIS och behörigheter är fortfarande inte verifierade.

Nästa steg: kör det förberedda diagnostikkommandot som seaparser i en tillåten
körmiljö, eller ge en ny session begränsad nätverksåtkomst för samma skrivskyddade
kontroll. Granska resultatet innan något migrationsgodkännande.
Inför drift separeras miljön och en ny driftroll skapas med minsta rättigheter.
Inga databaser, privata filer eller migrationsfiler ändrade; ingen migration eller push.

### Förnyat anslutningstest 2026-10-12

På användarens begäran kördes `.venv/bin/python -B -m scripts.diagnose_database`
igen. Resultat: `Anslutning nekad av körmiljön; PermissionError errno=1`
(exitkod 1). TCP-anslutningen blockeras fortfarande före PostgreSQL; databasens
anslutning och autentisering kunde inte verifieras. Nästa steg är att köra samma
skrivskyddade kommando som seaparser i en körmiljö med tillåten nätverksåtkomst.

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

## 2026-10-14: Usage-gränser och överlämning

Automatisk hantering vid 5 % och 1 % är inte implementerad. Tills vidare används
tidsgräns och avgränsade arbetsuppgifter, med en kort lokal överlämning efter
varje sammanhängande leverans. Vid `usage_exhausted` ska inga nya modellanrop
startas; slutrapporten ska ange Git-status och senast verifierade kontroller.
Kvotåterställning och automatiskt modellbyte är inte tillåtet. Tokenförbrukning
per körning är inte kontokvot.

Kontrollerat den här sessionen: installerad Codex CLI är 0.162.1. Dess
`app-server generate-json-schema --experimental`-utdata innehåller
`account/rateLimits/read`, `account/rateLimits/updated` och `usedPercent`.
OpenAI:s app-server-dokumentation beskriver samma JSON-RPC-anrop och svarsfält.
Alltså finns ett dokumenterat maskinläsbart gränssnitt i den installerade
versionen; denna kontroll läste inte den faktiska kontokvoten och bevisar inte
att tjänsteåtkomst finns i alla körmiljöer. Ingen automatik för 5/1-procent är
implementerad.

Nästa steg: vid nästa aktiva arbetspass fortsätt den dokumenterade backloggen
inom en uttrycklig tidsgräns; vid `usage_exhausted`, skapa rapporten från
tillgänglig lokal status och avsluta utan fler modellanrop. Om senare önskas,
kan app-serverns kvot-RPC utvärderas separat för säker/robust tröskelstyrning.

## 2026-10-20: DeepSeek-klient i infrastrukturlagret

- `infrastructure/deepseek.py` (DeepSeekClient) anropar DeepSeeks
  OpenAI-kompatibla API via `base_url=https://api.deepseek.com`.
  Ingen domän-, API- eller UI-logik; ruttmotorn anropar aldrig klienten.
- `infrastructure/settings.py` har `DeepSeekSettings` (api_key med
  repr=False) och `load_deepseek()` som läser `DEEPSEEK_API_KEY` och
  `DEEPSEEK_MODEL` via samma begränsade KEY=value-läsare som DB-konfig.
- `openai==3.35.1` med transitiva beroenden (`httpx2`, `httpcore2`,
  `jiter`) är hash-låsta i `requirements.lock`; `scripts/check.py`
  godkänner beroendebasen och domängränserna.
- 8 databasfria tester i `tests/test_deepseek_client.py`; inga
  nätverksanrop. Verifierat att `repr()` inte läcker nyckeln.
- `scripts/deepseek_smoke.py` är ett manuellt rökprov utanför
  `make check`. Varje anrop är betalt; kräver saldo hos DeepSeek.
- 2026-10-20: Inget saldo finns ännu, så ett riktigt API-anrop ger
  `APIStatusError`. HTTP-lagret, base_url och auth-formatet är ändå
  verifierat. Modellnamn (`deepseek-chat`) kan behöva justeras när
  saldo finns, om DeepSeek då rapporterar okänt modellnamn.
