# Arkitektur

## Grundprincip

En modulär applikation med separat beräkningsprocess. Ingen mikrotjänstplattform behövs i första leveransen. AI används för utveckling och granskning; själva ruttberäkningen utförs av en deterministisk motor.

## Föreslagen teknik

Python för motor och backend, FastAPI för API, PostgreSQL/PostGIS för beständig och geografisk lagring samt React/TypeScript för frontend. Detta är föreslagen inriktning, inte en installerad eller versionslåst stack. Visuell layouteditor återstår att välja. Containerdrift utvärderas mot serverns förutsättningar och behörigheter innan installation.

## Ansvar

Frontend presenterar komponenter och samlar användarval. API validerar anrop och kontrollerar identitet och behörighet. Applikationslagret samordnar användningsfall. Domänen innehåller båtprestanda, begränsningar och ruttberäkning. Infrastrukturen implementerar väderhämtning, databasåtkomst och jobbhantering.

Domänen känner inte till API-ramverk, databassessioner, leverantörers JSON-format eller layouteditor. Infrastrukturen omvandlar externa data till dokumenterade interna modeller.

## Data och konfiguration

Hemligheter och miljöinställningar ligger utanför repositoryt i `/home/web/seaparser/config/app.env`. Filformatet läses av en definierad konfigurationsladdare; filen ska inte förutsättas vara ett shellscript. Tomma nödvändiga värden ska ge tydliga fel utan hemligheter. Gemensamma icke-hemliga standardvärden versionshanteras. Båtprofiler och användarpreferenser lagras som applikationsdata.

Varje ruttresultat ska identifiera indata, båtmodell, prognoskälla och prognosversion, körningstid, giltighetstider, algoritmversion och begränsningar. Gemensamma prognosfält kan återanvändas mellan användare. Lagringsformat för stora prognosfält väljs efter mätning; alla rutnätsvärden ska inte automatiskt bli separata databasrader.

## Routing

Algoritmvalet är öppet. Jämför en enkel verifierbar referens med tidsutvidgad graf eller isokronbaserad sökning. Enbart bästa ankomst per geografisk punkt är inte ett tillräckligt tillstånd när tid, komfort eller manöverkostnader påverkar fortsatt resa. Dokumentera approximationer, tidssteg, upplösning och eventuell väntan innan optimering.

## Layout utan programmerare

Bygg funktionella komponenter med dokumenterade inställningar. En visuell editor ska kunna komponera dem, styra responsiva layouter och använda ett gemensamt tema. Förhandsgranskning och publicerad layout ska hållas åtskilda. Layoutversioner ska kunna återställas och egna komponenter behålla sin kod och API-koppling oberoende av editorn. Export eller egen lagring ska utvärderas innan bindande verktygsval.

## Uppgraderingar

Låsfiler och fasta deploymentversioner, kontrollerade beroendeuppdateringar, automatiska tester och versionshanterade migrationer. Driftplanen ska omfatta hälsokontroller och återställning. En kodrollback återställer inte automatiskt databasen; migrationer måste planeras separat.

Utveckling använder endast databas och roll seaparser. Enhetstester kräver ingen
databas. Databastester begränsas till rollback och testegna objekt. Inför drift
ska miljön separeras och en ny driftroll skapas; utvecklingsuppgifter återanvänds inte.

Prognosadaptrar ligger i infrastrukturlagret och normaliserar färdighämtade
externa payloads till domänens ForecastDataset. Underlaget är en helt
materialiserad, fryst uppsättning GridProduct med separat ProductMetadata för
vind/ström/vågor. Det implementerar miljögränssnittet utan SQL, HTTP eller lazy
callbacks. Rutt-/avgångsmotorn får samma underlag hela jämförelsen; byte av
prognos sker endast genom ett nytt explicit underlag/anrop. Transport ingår inte
i den syntetiska adaptern. Lokalt geografiskt origo, enheter, referensramar,
interpolationsregel och gap/masker valideras före planering. För frysta rutnät
kontrolleras dessutom interpolationsstöd längs hela accepterade integrerade
segment. Hårda vädervärden verifieras fortfarande endast vid uppslag och ankomst.

application/planning.py samordnar ett fryst PlanRequest till domänens
avgångsjämförelse och ett reproducerbart JSON-resultat med indata-/dataset-/
båtfingeravtryck. scripts/plan_synthetic.py komponerar syntetisk adapter och
usecase samt sköter CLI-presentation. Ingen transport eller databas ingår.
Algoritm-/schemaversion och alla parametrar följer resultatet; observerad
exekveringstid hålls separat från den deterministiska resultatidentiteten.
