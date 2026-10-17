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


## Fördefinierade kandidatrutter 2026-10-12

- Kompletta explicita vägpunktsekvenser utvärderas oberoende från samma avgång.
  Ingen grafpruning, positionsbaserad sammanslagning eller automatisk vägpunktssökning.
- Återanvänd sail_to_target per delsträcka; verklig slutposition och ankomsttid
  förs vidare. Hela integrerade segment och prognosgränser kontrolleras som tidigare.
- Kortast beräknad totalrestid väljs bland endast arrived-kandidater. Vid exakt
  lika restid väljs först angiven kandidat. Inget globalt optimalitetslöfte.
- Samma fart, hinder, prognoser och gränser för alla; max tid/steg gäller hela
  varje kandidatrutt. Standard: 100 kandidater, 32 mellanvägpunkter per kandidat,
  86400 s och 100000 integrerade steg per kandidat. Ingen väntan eller svängkostnad.
- Syntetiskt lokalt plan och uppskattad konstant båtmodell; verklig navigation,
  polarer, prognosålder och snabbast/bekvämast-jämförelse återstår.


## Uppskattad syntetisk segelpolar 2026-10-12

- Oföränderlig polar seaparser-synthetic-sail v1 med handvalda testvärden;
  bilineär interpolation i vattenrelativ vindstyrka och absolut vindvinkel.
  Förbjudet under 45°, ingen extrapolation utanför 0–20 knop. Ingen verklig båtdata.
- Vind anges som luftens mot-vektor, explicit ground/water. Meteorologisk
  från-riktning hålls skild från strömmens mot-riktning. Wwater=Wground-Cground.
  Ingen skenbar vind används. Samma Conditions-intervall gäller vind och ström.
- BoatPerformance äger kurskompensation och antaganden. Ruttjämförelsen förmedlar
  modellen; konstantmodellens analytiska lösning bevaras endast för konstant fart.
- Polarens linjära vinkelstycken delas vid alla stationära punkter, med bisektion
  och test av tangerande/ändpunktsrötter. Störst positiv tillåten framdrift väljs;
  förbjuden vinkel bedöms mot styrkurs, inte kurs över grund. Ingen automatisk kryss.
- Metadata och vindram följer exporten. Hinder-/prognos-/budgetskydd bevaras.
  Sjö, avdrift, segelkonfiguration, verkliga polarer och prognosålder återstår.


## Gemensamma hårda vädergränser och syntetisk komfort 2026-10-12

- WeatherPolicy kräver explicit max markrelativ vind (m/s) och Hm0 (m).
  Samma policy/datakrav för snabbast och bekvämast. Strikt överskridande avvisas
  före poängval; ingen tidsvinst eller komfortvikt kan upphäva absoluta gränser.
- WaveData: Hm0 i m, Tm02 i s och markrelativ från-bäring medurs från sann nord,
  eget explicit giltighetsintervall/källa/version. Okända/ogiltiga data avvisas.
  Vindgräns använder markvind, polaren fortsatt vattenvind, med explicit omräkning.
- Exponering E=integral (Hs/1m)^2*(5s/Tm02)^2*(1+sin(beta)^2) dt,
  beta relativt vattenriktning. synthetic-wave-exposure-v1 är syntetiskt och
  ej validerat för verkliga båtrörelser, inte ett säkerhets- eller sjösjukemått.
- Komfortval endast bland fullständigt genomförbara kandidater inom snabbaste
  restid + max_comfort_extra_seconds (standard300 s). Min E, därefter min tid.
- Kontroller gäller uppslag, inte bevisad kontinuerlig vädergräns. Omärkta luckor/
  toppar mellan uppslag kan missas. Hela segmentens hinderkontroll kvar.
- Legacy utan policy märks not_requested och får inget komfortval; det är en
  matematisk beräkning utan väderbedömning. Inga verkliga båtgränser har validerats.


## Prognosålder och destinationsuppslag 2026-10-12

- Conditions/WaveData har egna issued_at, separat från [valid_from,valid_until).
  ForecastPolicy maxålder beräknas vid explicit planeringsklocka, aldrig framtida ETA.
  Framtida utfärdande, saknad tid och för gammal källa avvisas. Ingen timestampfallback.
- Yttre Clock läses en gång per ruttjämförelse; UTC-snapshot förmedlas oförändrat
  till alla kandidater/delsträckor. Framtida giltighet kan inte upphäva åldersgräns.
- Faktisk numerisk slutposition/tid får separat miljöuppslag med samma policyer.
  Vid ankomst exakt vid valid_until krävs nästa giltiga prognos. Fysisk måluppfyllelse
  hålls skild från verifierat ankomstväder och godkänd fullständig restid.
- Misslyckad destinationskontroll utesluter rutten från båda valen men behåller bana.
  Resultat/export redovisar planeringstid, policy, issued_at, ankomststatus/observation
  och begränsad kontrollomfattning. Inga kontinuerliga väderbevis mellan uppslag.
- Legacy utan ålderspolicy/väderpolicy märks not_requested och är ingen verifierad
  bedömning för verkliga prognoser. Båda krävs med tillförlitlig källmetadata inför
  framtida integration; inga externa prognoskällor kopplas i denna leverans.

## 2026-10-12: Fryst prognosunderlag före rutt-/avgångsjämförelse

Leverantörsadaptrar normaliserar färdighämtade payloads utanför beräkningsmotorn
till ett helt materialiserat, oföränderligt ForecastDataset. Varje vind-, ström-
och vågprodukt behåller egen identitet/version, källa, utfärdandetid, giltighet,
täckning, SI-enheter, referensram och dataluckor. Samma underlag används för alla
alternativ; nytt prognosunderlag innebär ett nytt explicit planeringsanrop.
Ingen nätverkshämtning eller lazy adapter körs under jämförelsen.

Första implementationen är ett syntetiskt lokalt rutnät med WGS84-origo och
komponentinterpolation i rum/tid. Extrapolation, okänd täckning, saknade stödnoder
och markerade ogiltiga celler avvisas. Vågornas riktning interpoleras cirkulärt
via enhetsvektorer; odefinierad riktning blir datalucka. Produkten är testdata,
inte en verifierad prognosadapter eller geodetisk modell. Punktkontroller ger
fortfarande inte kontinuerligt täckningsbevis mellan uppslag. Verklig integration
kräver granskad projektion, källformat och intervall-/maskvalidering.

## 2026-10-12: Segmentkontroll av prognosens interpolationsstöd

Frysta rutnätsprodukter kontrollerar varje traverserad rum/tid-cell över hela det
accepterade affina numeriska färdsegmentet. Markerade ogiltiga celler, saknade
stödnoder och rum/tid utanför täckning avvisar hela steget före positions- och
komfortuppdatering. En aktiverad väderpolicy kräver vind/ström/vågor; utan policy
kontrolleras strömmens stöd. Rörelse kan avslutas vid giltighetens exkluderade
sluttid, men separat ankomstkontroll kräver fortfarande giltiga data.
Tak4096 delintervall per produkt/segment ger uttryckligt avbrott vid exhaustion.
Detta verifierar datastöd för det lokala integrerade segmentet, inte kontinuerliga
hårda vädervärden, källnoggrannhet eller verklig navigation. Legacy miljöcallbacks
saknar detta kontrakt. Tidigare begränsning om missade markerade maskceller är
ersatt endast för frysta rutnät med aktiverad segmentkontroll.

## 2026-10-12: Reproducerbart offline-usecase för syntetisk planering

Ett fryst PlanRequest i applikationslagret kräver känt fryst dataset/båtmodell,
båda policyerna och explicit planeringstid. Usecaset återanvänder befintlig motor
för två angivna avgångar och tre kandidatrutter i den versionerade fixture-demon.
Resultatet märker uppskattad båtdata och inkluderar kanoniska SHA-256-fingeravtryck
för fullständiga indata, prognosinnehåll/masker och båtprofil samt schema-/
algoritmversion. Inget väggklocksvärde blandas i resultatidentiteten.
Determinism gäller verifierad Pythonmiljö; hash är inget autenticitet-/kvalitets-
bevis. CLI kan välja konstantmodell, syntetiskt hinder och uttryckligt avgångs-
kriterium. Inga nya beroenden, externa prognoser eller produkttjänster införs.

## 2026-10-12: Konservativ certifiering av hela segmentets hårda vädergränser

För frysta normaliserade rutnät granskas alla celler som berör segmentets slutna
rum/tid-box. Komponentinterpolationens cellhölje ger vind²<=max|u|²+max|v|² och
Hs<=maxHs. Exakt rationell kvadratjämförelse används för lagrade vindkomponenter.
Bevis kan godkänna gränslikhet; ingen epsilon tillåter överskridande. Sampling
kan ge överträdelsevittne men aldrig kontinuitetsbevis. Tre utfall: verified,
exceeded (giltig faktisk segmentpunkt) och unverified (otillräckligt underlag/
bevis). De två senare är aldrig valbara; befintliga data-/hinder-/ankomstkontroller
kvarstår. Hela stödcellens hörn kan ligga utanför banan och ge falsk avvisning,
men rapporteras då inte som konstaterad överträdelse. Tak4096 celler per produkt
avbryter uttryckligen. Scope gäller markrelativ vindstyrka och Hs i det lokala
numeriska segmentet, inte källkvalitet eller alla komfort-/manövervariabler.
Applikationens algoritmversion ändras till v3 och metod/celltak följer manifestet.

## 2026-10-12: AIS är lågprioriterad planeringsinformation

Användarens senaste beslut ersätter tidigare förslag om mötesanalys och löpande
trafikövervakning. Första omfattningen innehåller graderad information om
observerad trafikbelastning och, vid tillförlitligt underlag, historiska mönster
kopplade till planerad passagetid/dagsljus/sikt/väder. Aktuell AIS är inte känd
framtida trafik; gamla/saknade eller svagt täckta data betyder unknown.
Ingen GPS-följning, kollisionsvarning eller undanmanöverrådgivning.
Väderrouting/ström/komfort/avgångstider prioriteras. Kontrakt och senare testplan
finns i traffic-planning.md; ingen AIS-kod implementeras nu. AIS-SOG är redan
över grund och får inte få extra ström. OpenWaters är utvärderad kandidat utan
konto/token eller inköp; AIS/tidvatten/ström har separata täcknings-/licensbesked.
Stationsström kräver verifierad rumslig modell före områdesanvändning och behåller
riktning/djup; tidvatten behåller vertikalt referensdatum. Se openwaters-review.md.

## 2026-10-12: Lokal HTML-rapport och begränsad demopublicering

Granskningsvisningen återger färdiga oförändrade JSON-rapporter. Beräkning,
presentationskod och HTML/CSS-layout är separata. Fem syntetiska scenarier
visar fri väg, hinder, konstaterat överskridande, otillräckligt konservativt
bevis och vågdatalucka. Heldragen bana visar endast accepterade segment.
Ingen verifierad kandidat innebär inget bevis om andra möjliga rutter.
Kortast restid och tidigast ankomst visas separat, utan allmänt avgångsval.
Visuell editor och verkliga prognoskällor väljs inte i denna leverans.

Användaren godkänner uttryckligen att endast den genererade självförsörjande
index.html publiceras i /home/web/seaparser/public för https://seaparser.com/.
Inga repositoryfiler, inställningar, loggar eller nycklar kopieras, och
webbserverns konfiguration ändras inte. Detta utökar inte databasmandatet.

## 2026-10-12: Planeringsflöde och automatisk syntetisk polygonomväg

Användarens beslut prioriterar geografisk routing före AIS och presentationspolering.
SeaParser erbjuder sjökortsnära kartgranskning och överföring av planerade
vägpunkter till plotter, utan GPS-följning. Kartbakgrund är separat från versions-
och kvalitetsmärkt routingsunderlag för land/öar/grund/djup/restriktioner.
Hårda förbud och informationslager skiljs; okänt djup är unknown och djup/tidvatten
kräver kompatibla höjdreferenser. Verkliga källor kräver region-/licensgranskning.

Första automatiska sökning använder lokala syntetiska enkla polygoner, hela
segment och euklidisk marginal. Begränsad graf med utvidgade boxhörn genererar
kompletta vägar i geometrisk ordning; varje väg simuleras sedan med befintlig
vind/ström/polar/komfort/prognoskontroll. Ingen geografisk tillståndssammanslagning
eller global optimalitet påstås. Budgetar och söktrunkering följer resultatet.
Exakta rationella predikat avser lagrade lokala tal, inte verklig källprecision.
Geografiska koordinater, kartvisning och GPX förbereds i geographic-routing.md;
inga nya paket, verkliga källor, betalningar, publiceringar eller databasändringar.

## 2026-10-12: Sammanhängande geografisk/API/kartdemo

FastAPI med två killbara jobbprocesser och frysta scenarier; en API-worker.
WGS84 AEQD vid 58°N 11°E med 1000 m projektionstak; prognosområdet är mindre.
Leaflet 1.9.4 väljs för teknisk integration med lokal syntetisk bakgrund;
OpenSeaMap/OpenWaters granskas separat i map-sources.md, ingen livekälla vald.
GPX 1.1 exporterar planerade vägpunkter, inte GPS-spår.
Isolerade PyPI/npm-beroenden låses exakt med hashar/integritet och CI installeras
från låsfiler. Ingen editor vald. Apache/systemtjänst förbereds i deployment/
och kräver samlat administratörs-/publiceringsgodkännande innan aktivering.

## 2026-10-12: Isolerad Vinga-landgranskning

Publik syntetisk demo är användarbekräftat aktiverad och visuellt kontrollerad.
Utveckling fortsätter i separat worktree/venv för att inte ändra kod som den
aktiva beräkningsprocessen laddar. Fryst ODbL-kustutdrag och konservativa konvexa
höljen återanvänder segmentmotorn; karttiles förblir separat opt-in-presentation.
Ingen verifierad navigerbarhet/djup eller ny publik aktivering påstås.


## 2026-10-12: Begränsad regional Vinga-planering

Vinga-profilen återanvänder rutt-/väder-/polar-/komfort-/avgångsmotorn med sex
frysta landhöljen och spårbart, syntetiskt regionalt väder. Fryst planeringstid
2026-01-01, högst två grafkandidater/två avgångar och 30 s steg håller arbetet
begränsat inom API:ts befintliga separata beräkningsprocess. Ingen allmän bästa
rutt eller navigationssäkerhet utses. Karta visar vald marginal ungefärligt;
motorn använder hela segment och lokal metermarginal. Regional HTML exporteras
separat och befintlig offentlig tjänst/frontend förblir orörda.


## 2026-10-12: Verkliga punktreferenser är inte regionala prognoser

SMHI SNOW och MET Oceanforecast fryses med öppna licenser och tydlig attribution.
Punktadaptrar normaliserar tidsserier, utan att sprida flyttade kustpunkter till
ett rutnät. MET:s uppdateringstid är inte bevis för modellutfärdande och saknad
Tm02 förblir saknad. Regional planering avvisas innan motorn. Native gridimport
är nästa steg, med mask, köridentitet och faktiska referensramar/djup. Inga konton
eller köp görs. Offlineaudit kan jämföra kandidatbudget 2/8, men API:s budget
och publika syntetiska demo ändras inte.


## 2026-10-17: Verkliga data som standard med explicita utvecklingsantaganden

Användaren tillåter gemensam utvecklingsberäkning med verklig vind, vågor och
ström där saknad källmetadata hanteras med uttryckliga konfigurerade antaganden.
Det ersätter tidigare krav på full källkvalificering före varje utvecklingsrutt,
men kvalificerar inga källuppgifter. Originalens okända run/issued_at bevaras;
konfiguration, resultat och normaliserade produktmetadata skiljer antaganden
från källästa uppgifter. Ingen separat syntetisk marin demonstrationsserie byggs.

Ogiltiga värden, verklig rumtids-/interpolationstäckning, landhinder, valda hårda
vädergränser och ankomstkontroll är fortsatt avvisande. Syntetiska referensfall
behålls som tester. Standardens grafiska Vinga-rutt använder frysta verkliga
MET/WAV/PHY-filer med faktisk gemensam giltighet 2026-10-13 12–16 UTC; inget
påstående om aktuell prognos. En uppskattad konstantfartsbåt används eftersom
testsegelpolaren inte täcker den verkliga vindstyrkan. Se development-real-routing.md.


## 2026-10-17: Uppmätt begränsad kandidat-/avgångsutökning

Offlineaudit använder samma verkliga frysta MET/WAV/PHY och fyra avgångar inom
12–16 UTC, inklusive 1800 s reserv för varje rutt. 8×4 överskrider befintliga
20 s/8 MB-gränser och förblir offline. Interaktiv utveckling tillåter därför
endast 2/4/8 kandidater, högst fyra explicita avgångar och 16 kombinationer.
Kalla processprov för 4×4 och 8×2 ryms inom befintliga process-/utdatagränser.
Inga generella skydd eller 900 m-stödtak ändras. Standard förblir 2×2.

Gemensam jämförelse över undersökta avgångar använder kortast restid och lägst
komfortexponering med samma 300 s tillåtna extra restid. Per-avgångsurvalen
behålls separat. Identiska vinnare visas uttryckligen; ingen marin serie
konstrueras för att skilja dem. Källa unverified, beräkning villkorad av
antaganden och båt/komfort ej validerade. Se development-real-routing.md.

## 2026-10-17: Större fryst källunderlag före större routingområde

En separat hashbunden rådatabunt för 17 oktober återanvänder befintligt WAV-
original lokalt och hämtar enbart nya avgränsade PHY-/masksubset samt MET-native-
vind. 132 vindnoder och 4×4 egna marina noder, tolv timnoder 01–12 UTC.
Separat estimat före hämtning: 118,1 MB ny marin överföring; inget nytt WAV-uttag.

Det nya underlaget är diagnostiskt och ändrar inte standardrouting eller 900 m.
Större marina grid klarar inte befintlig lokal 1 m-axelrepresentation och större
landunderlag saknas. Ingen tolerans, mask, geografi, fysisk tidssemantik eller
källkvalificering antas bort. Samma koordinattider är inte verifierat gemensamt
fysiskt tidsstöd. Befintlig adapter/MET-läsare återanvänds; ingen andra adapter.
Se expanded-forecast-support.md för bytebudgetar, faktisk data och nästa hinder.
