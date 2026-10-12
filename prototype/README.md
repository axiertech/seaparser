# Fristående strömprototyp

Kör från projektroten med Python 3.10 eller senare. Bara standardbiblioteket
används; ingen installation, databasåtkomst eller nätverksåtkomst behövs.

```sh
python3 -m prototype
python3 -m unittest discover -s prototype/tests -v
```

Demot går till målet (9260, 0) meter med konstant 5 knop genom vattnet och
2 knop nordlig ström. Styrkursen blir cirka 113,578°, kurs över grund 90°,
fart över grund √21 knop och restid cirka 3927,92 s. JSON på stdout innehåller
status, restid, samtliga steg, uppslag, antaganden och syntetisk datakälla.
Den tidigare tidsbegränsade rörelsen finns kvar som `simulate(...)`.

`model.py` innehåller båtmodell, enheter och vektorer; `environment.py`
innehåller syntetiskt väder-/strömgränssnitt; `calculation.py` gör integration;
`presentation.py` exporterar resultat. Båtmodell och miljö utvärderas både vid
stegstart och predikterad mittpunkt med respektive simulerad position och
UTC-tid. Markhastigheten är vattenhastighet plus strömhastighet.
`BoatModel` (fast styrkurs), `BoatPerformance` (kompenserad färd) och `Environment`
är utbytbara protokoll utan externa beroenden.

Handräknade referenser vid 5 knop österut under 1 h:

| Ström i knop (öst, nord) | Slutposition i NM | SOG i knop | COG |
| --- | --- | --- | --- |
| (0, 0) | (5, 0) | 5 | 90° |
| (2, 0) | (7, 0) | 7 | 90° |
| (-2, 0) | (3, 0) | 3 | 90° |
| (0, 2) | (5, 2) | √29 | atan2(5, 2) ≈ 68,199° |

För tidsföränderlig östlig ström `c(t)=2*t/3600` knop blir bidraget
`integral(c dt)=1 NM` under timmen och slutpositionen (6, 0) NM.
Konstanta fall kontrolleras med 1e-8 m positionstolerans, 0,001 knop och
0,01°. Linjär tidsvariation integreras exakt av mittpunktsmetoden och
kontrolleras med 1e-8 m. Ett positionsberoende exponentiellt referensfall
kontrollerar att halverat steg minskar felet mer än tre gånger.

Saknad eller icke-finit ström avbryter som standard med `ValueError`, position,
UTC-tid och orsak. Det följer produktkravet om saknade nödvändiga data.
Endast med det aktiva valet `simulate(..., allow_missing_current=True)`
används strömförslagets fallback. Den ger explicit nollströmsantagande med orsak vid
varje berört uppslag, position och tid. Start- och slutpunkter för berörda
steg följer exporten. Helt/delvis saknade data redovisas separat; giltig
nollström ger inget sådant antagande. Saknad vindavdriftsmodell ger ett eget
antagande. `leeway=0` betyder uttryckligen vald nollavdrift.

## Begränsningar

- Lokalt plant öst/nord-system i meter; ingen latitud/longitud eller geodetik.
- `simulate` håller vald stävriktning; `sail_to_target` kompenserar för rak kurs
  över grund. ConstantBoat behåller konstant fart och använder inte vind.
  PolarBoat använder uppskattad syntetisk segelpolar enligt avsnittet nedan.
  Ingen motor-/våg-/vindavdriftsmodell eller uppmätt verklig polar.
- Analytiska syntetiska fält, ingen gridinterpolation, landmask eller verklig
  prognos. Dataleverantören måste själv markera luckor och täckningsgränser.
- Tidssteget kortas vid mål, slut och kända prognosgränser; mittpunkten räknas
  om efter förkortning. Ingen adaptiv felkontroll. Okända dataluckor mellan
  uppslag kräver ytterligare hantering och kan fortfarande missas.
  Täckningsstatus i exporten gäller uppslagen. Ett steg kan påverkas av
  fallback i mittpunktsprediktionen.
- Målfärden ger restid bara vid uppnått mål. Syntetisk rektangelkontroll finns; ingen djupkontroll,
  global ruttoptimering. Syntetisk polar och explicita kandidatrutter finns.
  Noll markfart ger odefinierad COG (`null`).
- `docs/stromhantering.md` är ett specifikationsförslag; prototypen implementerar
  ovanstående avgränsade del. AGENTS.md, krav, arkitektur, beslutslogg och
  strömförslaget har lästs inför denna bearbetning.

## Antaganden och verifiering

Båtprofilen är syntetisk och uppskattad, inte en verifierad verklig båt.
Demot väljer uttryckligen noll vindavdrift. Alla strömfält är syntetiska;
demot gör ingen prognosålders- eller navigerbarhetsbedömning. Explicit
ålderspolicy och separat ankomstkontroll beskrivs nedan. Källa och version följer varje
uppslag; tidsstämplarna beskriver utvärderingstid, inte verkliga prognosers
giltighetsintervall. Inga resultat innebär att en färd är säker.

Algoritm: explicit mittpunktsmetod, denna prototypversion 1. Standardsteg
60 s, demosteg 900 s. Ingen geografisk gridupplösning finns i de analytiska
fälten. Simulerad tid är UTC med mikrosekundsupplösning; använd hela sekunder
för referensfallen. Körningstid kan mätas lokalt med:

```sh
time python3 -m unittest discover -s prototype/tests -v
```

Testerna verifierar de fyra konstanta referensfallen, linjärt tidsberoende,
positionsberoende och konvergens, båtmodellens mittpunktsuppslag,
determinism, saknade/ogiltiga data, uttrycklig fallback, nollström,
noll markfart, signerad vindavdrift och validering. För duration 0 redovisas
datatäckning som `ej utvärderad`. Exportens `current_status` skiljer giltig
ström från `assumed_zero` utan att tolka antagandetexten.

Syntetiska data kan ange `valid_from` (inklusive) och `valid_until`
(exklusive), båda med tidszon. Uppslag utanför intervallet räknas som saknade
även om fältet returnerar en strömvektor. Gränserna följer varje uppslag i
JSON-exporten. Utelämnade gränser betyder ett analytiskt syntetiskt fält utan
tidsgräns, inte en verifierad verklig prognos. Giltighetsintervall är inte
samma sak som prognosålder; den bedöms separat med ForecastPolicy enligt nedan.

Båda integrationsfunktionerna kontrollerar att de giltiga start- och
mittpunktsuppslagens intervall täcker hela det accepterade tidssteget
`[stegstart, stegslut)`. Antagandet är att angivna tidsintervall beskriver
sammanhängande tidsmässig täckning för respektive uppslag. Ett steg får sluta
exakt vid `valid_until`: ingen rörelse efter gränsen accepteras på dessa data.
Fortsatt färd gör ett nytt uppslag vid gränsen. Utan giltiga data avbryter
`sail_to_target` med `data_unavailable` och behåller redan slutförda steg;
`simulate` ger `ValueError`. Aktivt vald nollströmsfallback i `simulate`
bevaras och redovisas vid berörda uppslag. Kända framtida `valid_from`-gränser
delar även fallbacksteg så att giltig ström kan användas från gränsen.
Gränser som först hittas vid mittpunkten föranleder omräkning; ett giltigt
mittpunktsintervall som inte täcker stegstarten avvisas konservativt.
Tidsintervall bevisar inte rumslig täckning eller frånvaro av okända luckor.

Detta är en begränsad beräkningsleverans. De bredare acceptanskriterierna
för ruttoptimering, seglingsvinklar och komfort är inte implementerade.
Syntetisk hinderkontroll beskrivs nedan.

Verifierat 2026-10-11: `python3 -m unittest discover -s prototype/tests -v`
gav 16 godkända tester (0,089 s enligt unittest). Det omfattar även
prognosens giltighetsgränser, saknad täckning vid predikterad mittpunkt,
starkare motström och en båt som ligger stilla genom vattnet men driver.
Demots JSON lästes tillbaka och slutpositionen (9260, 3704) m kontrollerades
med 1e-8 m tolerans. Körtiden är en lokal observation, inte ett prestandalöfte.

## Målfärd med kurskompensation (version 2)

```python
from datetime import datetime, timezone
from prototype.model import Vector, KNOT
from prototype.environment import Conditions, SyntheticEnvironment
from prototype.calculation import sail_to_target
from prototype.presentation import export_voyage

environment = SyntheticEnvironment(lambda p, t: Conditions(Vector(0, 2 * KNOT)))
result = sail_to_target(environment, datetime(2026, 1, 1, tzinfo=timezone.utc),
                        Vector(9260, 0), speed_knots=5)
print(export_voyage(result))
```

Antagande: uppskattad konstant fart genom vattnet, omedelbar styrning och
uttryckligen noll vindavdrift. Ingen seglingsvinkel är förbjuden i denna modell.
För enhetsvektor d mot målet och vinkelrät enhetsvektor n delas strömmen upp
som c_parallel=c·d och c_cross=c·n. Båtens vattenvektor väljs till
`d*sqrt(s²-c_cross²) - n*c_cross`. Detta väljer den lösning som ger störst
framdrift. Styrkursen är vattenvektorns riktning, exporterad per mittpunkt
som `steering_degrees`. När |c_cross|>s är önskad kurs omöjlig. Framdriften
`sqrt(s²-c_cross²)+c_parallel` måste vara större än `min_progress_m_s`
(standard 0,01 m/s). Dessa kontroller görs vid start och mittpunkt i varje steg.

Standard målpositionstolerans är 0,01 m. Start inom toleransen ger restid 0.
Annars integreras rak färd med mittpunktsmetoden. Steget begränsas av
startfartens uppskattade tid till målet. Vid överskjutning lokaliseras
målpassagen med högst 60 bisektionsiterationer och omräknade mittpunkter;
siktet är högst 0,001 m längdfel. Den beräknade slutpositionen behålls, utan
att snäppas till målet. Restiden är integrerad förfluten tid till en position
inom toleransen, inte hela distansen dividerad med initial SOG.

Status är `arrived`, `infeasible`, `data_unavailable`, `blocked` eller `limit_reached`.
`travel_seconds` är null om målet inte nåtts; `elapsed_seconds` och slutförd
bana finns även vid avbrott. Ingen väntan på bättre ström prövas. Saknad,
ogiltig eller tidsmässigt otäckande ström ger `data_unavailable`, utan fallback.
Maximal simulerad tid är som standard 86400 s och maximal mängd slutförda
steg 100000. Båda kan anges explicit. Tidsupplösningen är en mikrosekund;
för kort slutsteg ger uttryckligt avbrott.

Referenser för mål 5 NM österut och vattenfart 5 knop:

| Ström (öst, nord), knop | Restid, sekunder |
| --- | --- |
| (0, 0) | 3600 |
| (2, 0) | 18000/7 ≈ 2571,429 |
| (-2, 0) | 6000 |
| (0, 2) | 18000/√21 ≈ 3927,922 |
| (0, 6) | Kurs omöjlig, ingen restid |
| (-5, 0), (-6, 0) | Otillräcklig framdrift, ingen restid |

Konstanta referenser provas med steg 120 och 60 s, målfelet högst 0,01 m,
restidsfelet högst 0,01 s, fartfelet högst 1e-9 knop och kursfelet högst 0,001°.
Linjär medström `c(t)=2*t/3600` knop har referensrestiden
`3600*(sqrt(45)-5)/2` till 5 NM och provas med samma tidssteg och tidstolerans.
För `c(t)=2*(t/3600)²` knop väljs målet (5+2/3) NM, med exakt restid 3600 s.
Steg 240 s gav 3600,380766 s och steg 120 s gav 3600,095052 s: felet minskade
cirka fyra gånger. Testet kräver minst trefaldig förbättring och högst 0,2 s
fel vid det finare steget.

Kontroller gäller bara uppslagen. Hastiga ändringar, dataluckor och omöjliga
villkor mellan uppslag kan missas. Provuppslag under målpassagens lokalisering
kan avbryta konservativt även om en kortare färd vore möjlig. Fast tidssteg
saknar generell felgaranti; för verkliga data krävs vidare validering.

Verifierat för denna utökning: samtliga 24 tester godkändes med
`python3 -B -m unittest discover -s prototype/tests -v`.

Verifierat efter granskning av prognosgränsfixen 2026-10-12: samtliga 42 tester
godkändes med samma kommando. Regressionerna omfattar
gräns vid 45 s mellan mittpunkt och stegslut vid 60 s, mål före och exakt vid
gränsen, fortsatt färd med och utan nästa prognos samt explicit exporterad
nollströmsfallback. Även en gräns som först anges vid mittpunkten provas. Fyra ytterligare
regressionstester kontrollerar omräknad tid/position vid mittpunkten mot
x(t)=t+t²/200 (55,125 m vid 45 s), ändrad ström vid prognosbyte och en fem
sekunders lucka. Grovt/halverat steg kontrolleras. Dessa fyra tester gav sex
felutfall (inklusive subtester) mot den tidigare committade beräkningen och
passerar med fixen. Okända rumsliga/tidsmässiga luckor återstår; separat prognosålderspolicy finns nedan.

## Syntetiska hinder

`obstacles.py` definierar slutna axelparallella `Rectangle` i meter.
Både `simulate(..., obstacles=(... ,))` och `sail_to_target(...,
obstacles=(... ,))` kontrollerar varje helt integrerat segment, inte bara
uppslagspositionerna. Kant- och hörnkontakt blockeras. `margin_m` (standard 0)
expanderar rektangeln; det är ett syntetiskt avståndsantagande.

```python
from prototype.obstacles import Rectangle
result = sail_to_target(environment, datetime(2026, 1, 1, tzinfo=timezone.utc),
                        Vector(9260, 0),
                        obstacles=(Rectangle("syntetisk ö", 4000, -100, 5000, 100),))
```

Målfärd i/korsande hinder ger `blocked`, null restid och endast redan
slutförda steg. Start och avsett mål kontrolleras även vid avstånd mindre än
måltoleransen. Rörelsesimulering ger `ObstacleCollision`. Ett förkortat
slutsteg kontrolleras till sin faktiska beräknade slutposition. Geometrin
kontrollerar numeriska raka segment; fysisk bana, djup, verkliga sjökort och
ruttoptimering återstår. Uppdaterad status finns i ../docs/progress.md.


## Begränsad jämförelse av kandidatrutter

`routes.compare_routes` utvärderar kompletta `RouteCandidate(name, waypoints)`
från samma startposition och UTC-avgång till ett gemensamt mål. En tom lista av
mellanvägpunkter definierar direktvägen; den läggs inte till automatiskt.
Varje kandidat får sitt eget förlopp; inte ens gemensamma vägpunkter slår ihop
olika ankomsttider. Resultatet är `selected` med `fastest`, eller
`no_feasible_route` med alla kandidatresultat och deras avbrottsorsaker.
Endast fullständigt `arrived`-resultat kan vinna. Exakta tidslikheter väljer
först angiven kandidat, reproducerbart för samma deterministiska miljö/indata.

```python
from prototype.routes import RouteCandidate, compare_routes
from prototype.presentation import export_route_comparison

comparison = compare_routes(
    environment, departure, Vector(100, 0),
    [RouteCandidate("direct"),
     RouteCandidate("north", (Vector(30, 20), Vector(70, 20)))],
    obstacles=[Rectangle("synthetic", 40, -10, 60, 10)],
    speed_knots=1 / KNOT,
)
print(export_route_comparison(comparison))
```

Exemplet använder tidigare definierade environment/departure och importerade
Vector/Rectangle/KNOT. JSON redovisar scope, vinnarnamn, alla kandidater och varje
delsträckas uppslag, giltighet, bansegment och status. Blockerad/ofullständig
kandidat har ingen vanlig restid eller ankomsttid; redan slutförd bana bevaras.

Färdberäkningen återanvänds per delsträcka med föregående faktiska slutposition och
sista accepterade stegets end_time. Positionen flyttas inte artificiellt till
vägpunkten inom toleransen. Ny ström utvärderas vid delsträckans simulerade
position/tid; ingen återställning till avgångens prognos eller ström. Kursbyte
antas omedelbart utan svängkostnad. Hela segment testas mot samma hinder och
prognosgränsskyddet gäller även senare delsträckor. Ingen nollströmsfallback i
ruttjämförelsen. Saknade data eller omöjlig kurs gör kandidaten ogenomförbar.

Standardgränser: 100 kandidater och 32 mellanvägpunkter per kandidat, steg 60 s,
positionstolerans 0,01 m och minsta framdrift >0,01 m/s. Tid 86400 s och 100000
integrerade steg gäller hela varje kandidat, inte varje delsträcka. UTC-tider har
mikrosekundsupplösning; totalrestid är faktisk ankomst minus avgång. Per-vägpunktens
tolerans och numerisk integration påverkar restid; inga generella felgarantier.
Beräkningen är linjär i antalet undersökta kandidater/delsträckor/steg och begränsas
av dessa parametrar. Ingen geografisk grid eller global sökoptimering införs.

Regressioner kontrollerar fri direktväg (100 m / 1 m/s = 100 s), blockerad direktväg
med omväg (2*sqrt(30²+20²)+40 m), inga genomförbara alternativ, ändrad vinnare med
tidsberoende ström, korrekt fortsatt tid/position, gemensam vägpunkt med både tidig
och sen genomförbarhet, prognosslut på senare delsträcka, hela ruttens tids-/stegbudget,
validering, deterministiska likheter och JSON-export. Analytiska konstantreferenser
har tidsfel <=0,03 s; den enkla direkta referensen <=1e-6 s. Grovt/halverat steg
provas för hinder och strömval. Sökningen gäller endast den definierade
kandidatmängden. Verkliga sjökort/djup, verklig källmetadata, uppmätta polarer och validerad komfort återstår;
detta är inte navigationsstöd för verklig användning.


Mätt lokalt 2026-10-12 i referensscenariot: norr 112,11 s och söder 124,85 s
utan ström; med tidsberoende sydlig medström söder 94,40/94,07 s för steg 2/1 s.
Vinnarvalet är stabilt vid halverat steg; skillnaden i söder visar integrationens
känslighet vid den rumsliga strömdiskontinuiteten, inte en generell tidsfelgaranti.
100 jämförelser med två kandidater och steg 1 s tog 1,137 s totalt i denna körning.
Det är en lokal observation, inget prestandalöfte för andra kandidatmängder.


## Uppskattad syntetisk segelpolar och vindram

SailPolar i polar.py har identifierare seaparser-synthetic-sail, version 1,
source "Handvalda referensvärden 2026-10-12, uppskattad testdata" och estimated=True.
Tabellen är oföränderliga tuples och finns i Git. Den representerar ingen namngiven
eller uppmätt verklig båt. Ändrade värden ska få ny version. Resultatets assumptions
och varje uppslags boat_assumptions inkluderar identifierare, version, källa och
uppskattningsmarkering; vindvektor, vindram samt miljökälla/-version exporteras också.

Fart genom vatten i knop, TWS i knop relativt vatten och absolut TWA i grader:

| TWS / TWA | 45° | 60° | 90° | 120° | 150° | 180° |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 10 | 3 | 4 | 5 | 4.5 | 3.5 | 3 |
| 20 | 4.5 | 6 | 7 | 6.5 | 5 | 4.5 |

Bilineär interpolation mellan styrke-/vinkelnoder, symmetriskt mellan babord och
styrbord. Ingen extrapolation eller klampning av verkliga värden utanför tabellen.
Vinkel <45° är förbjuden; exakt 45° och 180° tillåtna. Vindstyrka utanför 0–20 knop
är data_unavailable. Noll vattenrelativ vind ger infeasible för segelfärden eftersom
ingen seglande riktning kan bestämmas. Flyttalsavrundning inom 1e-10 knop respektive
1e-10° vid exakta gränser tolereras; detta är numerik, inte ändrade seglingsgränser.

Alla vektorer är öst/nord-komponenter i m/s, i ett lokalt plan. 0° är sann nord
(+nord), 90° öst, ökande medurs. Strömriktning är alltid **mot-riktning** för vattnets
rörelse över mark. Meteorologisk vindriktning är **från-riktning**. Conditions.wind
lagrar däremot luftens **mot-vektor**. wind_from(speed_m_s, from_degrees) ger
(-speed*sin(from), -speed*cos(from)). En vind från nord har negativ nordkomponent;
en ström mot nord har positiv nordkomponent. Skillnader över 359°/1° normaliseras
cirkulärt; ingen vanlig linjär interpolation av riktningsgrader används.

Conditions.wind_reference är ground som standard eller explicit water; andra
ramar avvisas. Med markrelativ luftvektor Wg och markrelativ ström C används
**Ww = Wg - C** som sann vind relativt vattnet för polaren. Om water redan anges
ska C inte subtraheras igen. Från-riktningen är mot-vektorns bäring +180° och TWA
är minsta absoluta vinkeln mellan styrkurs och denna vattenrelativa från-riktning.
Exempel: luft (0,-4) m/s och ström (3,0) ger Ww=(-3,-4), styrka 5 m/s och
från-riktning 36,8699°. Härledningen är vanlig relativhastighet, inte ett empiriskt
samband för prestanda. Skenbar vind på båten skulle vara Ww minus båtens
vattenhastighet; den används inte av denna polar. Ström kan därmed ändra både
polarens TWS/TWA och markhastigheten. Conditions valid_from/valid_until beskriver
sammanhängande gemensam täckning för vind/ström. Deras issued_at och vågornas
egna issued_at bedöms med separat ålderspolicy; olika vind-/strömkällor kräver
ytterligare separation vid verklig dataintegration.

Den meteorologiska från-konventionen har kontrollerats mot
[ECMWFs officiella vinddefinition](https://confluence.ecmwf.int/spaces/CKB/pages/133262398/ERA5%2BHow%2Bto%2Bcalculate%2Bwind%2Bspeed%2Band%2Bwind%2Bdirection%2Bfrom%2Bu%2Band%2Bv%2Bcomponents%2Bof%2Bthe%2Bwind).
Polartabellen och valet av vattenrelativ sann vind är projektets explicita
syntetiska modell, ingen användning av ECMWF som båtprestandakälla.

## Utbytbar prestanda och kurskompensation

sail_to_target(..., boat=PolarBoat()) och compare_routes(..., boat=PolarBoat())
använder BoatPerformance.compensate(direction, position, time, weather,
min_progress_m_s). Ruttjämförelsen förmedlar bara samma modell till varje
kandidat/delsträcka; den känner inte till polarer eller kurslösningsmetod.
Utan boat väljs ConstantBoat med befintliga speed_knots-argument och tester.
Med boat bestäms farten av modellen; speed_knots är ett kompatibilitetsargument.
BoatModel.evaluate finns kvar för simulate med fast stävriktning, även PolarBoat.
ConstantBoat med icke-noll leeway används fortsatt av simulate; dess kompenserade
färd avvisar sådan inställning eftersom denna leverans antar noll avdrift.

Konstantmodellens analytiska sqrt-formel gäller endast dess kursoberoende fart.
PolarBoat löser istället F(theta)=(Vwater(theta)+C)·n=0 med tillåten vindvinkel
samt positiv framdrift över min_progress_m_s. Den prövar hela båda tillåtna
vinkelintervallen och väljer störst framdrift av alla tillåtna lokala lösningar.
Förbjuden vindvinkel kontrolleras mot styrkurs/vattenvektor, inte kurs över grund;
en stark ström kan bära båten mot vinden medan den seglar i en tillåten annan kurs.
Ingen lösning ger infeasible med uttrycklig orsak och utan restid. Ingen automatisk
kryssning, väntan, slag/gipp eller manöverkostnad införs.

På varje polarstycke är s(theta)=s0+k*(theta-lo), i m/s och radianer. Med
målbäring D och delta=theta-D blir F=-s*sin(delta)+C·n. Dess stationära punkter
uppfyller delta-atan2(k,s)=pi/2+j*pi. Vänsterledet är monotont eftersom derivatan
är 1+k²/(s²+k²) för icke-noll stycken. Därför hittas alla stationära punkter utan
ett glest vinkelgrid. Stycket delas där och varje teckenbytande rot bisekteras;
ändpunkter och stationära tangeringsrötter testas också. Högst 60 iterationer per
bisektion, tvärhastighetsresidual <=1e-9 m/s. Identiskt nollfartsstycke behandlas
via ändpunkterna. Argumentet gäller denna linjärt interpolerade, icke-negativa
polar och får inte återanvändas oförändrat för annan prestandafunktion.

Miljön och prestandan utvärderas vid faktisk simulerad position/tid vid både
stegstart och mittpunkt. Hinder, prognosgränser, ruttbudgets och målpassagetolerans
är kvar. Vind som saknas/är icke-finit ger data_unavailable för PolarBoat; ingen
vindfallback. Konstantmodellen kan fortsatt användas utan vind.

Referenser: 10 knop, TWA90 ger 5 knop och 1 NM på 720 s. TWA120 ger 4,5 knop;
2,25 knop nordlig ström tar ut dess sydkomponent vid styrkurs120 och 0,3 knop
östlig ström ger SOG=(0,3+4,5*sqrt(3)/2) knop. Samma resultat provas med både
mark- och vattenrelativ vind, steg 120/60 s, restidstolerans 0,01 s och residual
1e-9 m/s. En separat flat testpolar provar intern tangeringsrot, exakt tillåten
45°-gräns och flera alternativa rötter. En analytisk rum/tid-vindreferens
x'=.2K*x/100+.2K*t/100+5K provas med halverat steg och <=0,001 m fel.

Begränsningar: uppskattad liten tabell, omedelbar trim/styrning, symmetri,
noll avdrift, ingen sjö-/våg-/segelkonfigurationsmodell och inga verkliga polarer.
Referensramen är inte roterade GRIB-komponenter, magnetisk kurs eller vind relativt
båten. Okända dataluckor mellan uppslag och verklig källvalidering återstår. Ingen generell
felgaranti eller maritim sakkunnig validering; detta är endast testdata.


## Hårda vädergränser och syntetisk komfortexponering

WeatherPolicy(max_wind_m_s, max_wave_height_m) aktiverar samma absoluta gränser
för alla kandidater och båda målen. Gränser anges explicit; inga båtvaliderade
standardgränser erbjuds. Likhet med gränsen tillåts; strikt större värde avvisas
som weather_limit. Kandidaten har då ingen fullständig restid eller komfortpoäng
och kan inte väljas. Först filtreras genomförbarhet, sedan görs båda valen.
Komfort eller restid kan inte väga bort väder, hinder, no-go, data- eller budgetfel.

Vädergränsens vind är alltid **markrelativ** styrka i m/s, till skillnad från
polarens vattenrelativa TWS. Conditions.wind_reference=water omräknas till mark
med Wground=Wwater+Cground innan gränstestet. Vind från markdata kontrolleras
direkt. Svag vattenrelativ vind innebär inte att en hård markrelativ gräns passerar.

WaveData beskriver syntetisk signifikant våghöjd Hm0 i meter (height_m), markfast
medelperiod Tm02 i sekunder (period_seconds, period_kind=tm02) och medelvågornas
**från-riktning** (from_degrees), medurs från sann nord, i samma lokala markram
som vind/ström. Höjdgränsen gäller Hm0, inte högsta enskilda våg.
direction_reference=ground-from-true-north; andra periodtyper/ramar
avvisas. 0° betyder från nord, 90° från öst. Propagationen är åt motsatt håll.
Riktning normaliseras cirkulärt i komfortberäkningen. Perioden är inte spektral
peakperiod eller mötesperiod ombord; ingen Doppler-/encounteromräkning görs.

Enheter och vågkonvention har granskats mot
[Copernicus Marine om vågparametrar](https://help.marine.copernicus.eu/en/articles/6175153-how-to-describe-wave-height-period-and-direction-parameters) och
[deras riktningskonventioner](https://help.marine.copernicus.eu/en/articles/5046685-direction-conventions-of-currents-wave-and-wind-in-copernicus-marine-products).
Prototypens vågvärden är syntetiska, inte hämtade prognoser från dessa tjänster.

Vind/ström använder Conditions giltighetsintervall; vågor har ett **eget**
WaveData-intervall och egen source/version. Vid aktiverad policy måste båda
intervallen vara explicit kända, tidszonsmedvetna och täcka uppslagstiden
[start,end). Våghöjd måste vara finit och >=0, period finit och >0 och riktning
finit. Även noll våghöjd kräver period/riktning för den gemensamma testdatamodellen.
Saknade/ogiltiga data eller okänd/utgången giltighet ger data_unavailable utan
fallback. Aktiverad policy kräver också giltig ström och avvisar simulate-fallback
även om allow_missing_current=True. Kända våg-/vindgränser kortar steg med omräknad mittpunkt; fortsatt
färd kräver nytt giltigt uppslag. Ett rörelsesteg får sluta exakt vid gränsen,
men ankomstväder kräver separat giltigt uppslag vid denna tid; se nedan.

Komfortmodell **synthetic-wave-exposure-v1**, ej validerad för verkliga båtrörelser:

```
r(t) = (Hs/1 m)^2 * (5 s/Tm02)^2 * (1 + sin(beta)^2)
E = integral r(t) dt
beta = minsta vinkelskillnad mellan vågornas från-bäring och riktning genom vatten
```

r är dimensionslös och E anges i syntetiska exponeringssekunder. Lägre E föredras.
Högre höjd och kortare period ökar bidraget; tvärsjö vägs dubbelt mot rak fram-/
bakifrån sjö. Modellen skiljer inte framifrån från bakifrån sjö. Vattenriktning
används som proxy för båtens riktning, inte COG. Saknad sådan riktning vid rörelse
avvisas. Ingen modell av roll, stampning, acceleration, sjösjuka, skrov, fartberoende
resonans eller strömmens påverkan på vågor. Formeln är ett dokumenterat testmått,
ingen prediktion av faktisk komfort eller säkerhet och ingen medelpoäng som döljer
tidsexponering. E beräknas med mittpunktsregeln över varje accepterat steg och
summerar hela kandidatens delsträckor. Förkastade steg bidrar inte.

Bekvämaste kandidat minimerar E bland samma kompletta arrived-kandidater som
snabbaste, och bara om travel_seconds <= fastest.travel_seconds +
max_comfort_extra_seconds. Parametern är sekunder, standard 300, finit och >=0;
0 tillåter bara lika snabb färd. Vid exakt lika E väljs kortare restid, därefter
först angiven kandidat. Tids-/stegbudget för hela rutten gäller fortsatt.

```python
from prototype.environment import WaveData, Conditions, SyntheticEnvironment, wind_from
from prototype.weather import WeatherPolicy
from prototype.routes import RouteCandidate, compare_routes
from prototype.model import Vector, KNOT
from datetime import datetime, timedelta, timezone

start = datetime(2026, 1, 1, tzinfo=timezone.utc)
end = start + timedelta(seconds=1000)
def field(p, t):
    return Conditions(Vector(0, 0), wind=wind_from(4, 0),
                      valid_from=start, valid_until=end,
                      waves=WaveData(1/(1+max(0,p.north)/10), 5, 0, start, end))
result = compare_routes(
    SyntheticEnvironment(field), start, Vector(100, 0),
    [RouteCandidate("direct"), RouteCandidate("detour", (Vector(0,20), Vector(100,20)))],
    speed_knots=1/KNOT, weather_policy=WeatherPolicy(5, 1),
    max_comfort_extra_seconds=40, step_seconds=1)
```

Referens: snabbast direkt=100 s, bekvämast omväg=140 s. Direkt E=200, omväg
E=35,4923/35,5396 vid steg2/1 s mot analytiska 35,5556. Testtolerans 0,07
exponeringssekunder; halvering ändrar E mindre än 0,05 och bevarar båda valen.
Ett tidsfält Hs=.5+.002t ger integral över100 s lika med72+2/3; steg10/5 s
har grovt fel<0,01 och halvering minskar fel mer än tre gånger. Vågbyte vid45 s
från Hs1 till.5 ger E=117,5 utan att gammal prognos extrapoleras.
Exemplets vind-/våggränser är endast testparametrar, inte rekommenderade båtgränser.

JSON innehåller båda vinnarnamnen, policy, tidsmarginal, komfortmodell och varje
kandidats poäng/väderstatus. Varje Voyage inkluderar samma policy/modell och
exponering av sina accepterade steg (kan vara partiell vid avbrott). En misslyckad
RouteResult har comfort_exposure=None. WaveData och rate följer varje uppslag.

Bakåtkompatibelt matematiskt läge weather_policy=None använder tidigare ström-/
polar-/hinderkontroller men gör **ingen väderbedömning**: weather_status=not_requested,
komfortpoäng och comfortable=None. Det innebär inte verifierat godtagbart väder.
En aktiverad policy behandlar aldrig saknade data som säkra, även vid nollsträcka.

Begränsning: hårda vädergränser testas vid stegstart och predikterad mittpunkt,
inklusive omräknade/provisoriska uppslag, samt separat vid faktisk ankomst.
De bevisas inte mellan uppslag eller vid alla övriga segmentändpunkter. En omärkt datalucka eller kort farlig topp kan missas.
Provisoriska uppslag kan också ge konservativa avbrott. Hinder kontrolleras fortsatt
över hela integrerade segment. Kända prognosgränser och konfigurerad ålder
kontrolleras, men verklig källmetadata/interpolation och maritim validering återstår; ett mindre steg är ingen säkerhetsgaranti.


## Prognosålder vid planering och separat ankomstkontroll

Conditions.issued_at gäller den sammanhängande vind-/strömprognosen och
WaveData.issued_at dess oberoende vågprognos. Utfärdandetid är källans faktiska
utfärdandetid, inte valid_from, simulerad ankomst eller nedladdningstid. Alla tider
ska vara tidszonsmedvetna datetime; klockans planeringstid normaliseras till UTC.
Saknad utfärdandetid får inte ersättas med nu/start/giltighetstiden.

ForecastPolicy(max_age_seconds) är separat från WeatherPolicy och giltighet.
Gränsen är finit och >=0, i sekunder; lika ålder tillåts. För varje källa som
används beräknas age=planning_time-issued_at. Negativ ålder (utfärdad efter
planeringen), saknad tid eller överskriden maxålder ger data_unavailable och
utesluter kandidaten. Vind-/ström- och vågprognoser bedöms var för sig mot samma
konfigurerade maxålder. Framtida giltighet gör inte gammal prognos färsk.
Giltighet fortsätter däremot kontrolleras vid respektive simulerade uppslagstid.

Clock.now injiceras explicit; FixedClock ger reproducerbar planeringstid. Med
aktiverad ForecastPolicy krävs en Clock, annars konfigurationsfel ValueError.
Ingen datetime.now eller implicit avgångstid används som klocka. Ruttjämförelsen
läser den yttre klockan exakt en gång efter indatavalidering, innan simulering,
och förmedlar en fryst UTC-tid till alla kandidater/delsträckor/ankomstkontroller.
Standalone sail_to_target/simulate fångar sin klocka en gång per anrop. Utfärdandetid
kontrolleras vid varje nytt uppslag, så bytt prognoskälla/version inte ärver någon
annan prognos godkända ålder. Prognoser utfärdade efter planeringen kan inte
förutsättas tillgängliga, även om deras simulerade användningstid ligger senare.

```python
from prototype.forecast import ForecastPolicy, FixedClock

plan = datetime(2026, 1, 1, tzinfo=timezone.utc)
depart = plan + timedelta(hours=2)
issued = plan - timedelta(seconds=100)
end = depart + timedelta(hours=1)
record = Conditions(Vector(0,0), wind=wind_from(4,0),
                    valid_from=depart, valid_until=end, issued_at=issued,
                    waves=WaveData(1,5,0,depart,end,issued_at=issued))
result = compare_routes(SyntheticEnvironment(lambda p,t: record), depart,
                        Vector(100,0), [RouteCandidate("direct")], speed_knots=1/KNOT,
                        weather_policy=WeatherPolicy(5,1),
                        forecast_policy=ForecastPolicy(600), clock=FixedClock(plan))
```

Detta återanvänder importerna i väderexemplet ovan. Vid planeringen är prognosen
100 s gammal, även om färden börjar två timmar senare. Maxåldern bedöms inte vid
framtida ETA. Den är ingen begränsning av prognoshorisonten; giltighetsfönstret
måste separat täcka hela de verifierade uppslagen inklusive ankomst.

Efter rörelse till måltoleransen gör sail_to_target ett **nytt** miljöuppslag vid
sin numeriskt faktiska end_position och end_time. Ingen snapping till nominellt
mål görs. Samma aktiverade väder-/ålderspolicy används, även för nollsträckor och
mellanvägpunkter. Inga nya rörelsesegment eller komfortbidrag tillkommer av detta
punktuppslag. Det kontrollerar väder/data, inte möjlighet till ny seglingskurs efter
målet. simulate är tidsbegränsad rörelse utan destinationsresultat och redovisar
sina accepterade stegs uppslag; den intygar inte verifierat väder vid en destination.

Giltighet är [valid_from,valid_until), **även vid destinationen**. Ett färdsegment
kan sluta exakt vid valid_until utan att extrapolera efter den; för verifierat
ankomstväder behövs då nästa prognos med valid_from<=arrival_time<valid_until.
Gammal sista prognos återanvänds inte automatiskt. Om nytt uppslag saknas/är gammalt/
ogiltigt, eller vind/våggräns överskrids vid destinationen, blir resultatet
data_unavailable respektive weather_limit och kan inte väljas som snabbast eller
bekvämast. Banan och elapsed_seconds bevaras; destination_reached kan vara True
samtidigt som travel_seconds/ankomsttid för en godkänd rutt saknas.

arrival_checked_time visar faktiskt kontrollerad tid. arrival_weather_status
är passed_at_arrival bara efter godkänd väderkontroll, annars felstatus eller
not_requested. Voyage.arrival_observation sparas endast vid godkända ankomst-
kontroller och visar källa/version, rådata, giltighet och utfärdandetider.
forecast_status rapporterar separat ålderskontroll; planning_time, ForecastPolicy,
issued_at och forecast_checked följer exporten. weather_verification_scope
anger uttryckligen att ingen kontinuerlig verifiering mellan uppslag gjorts.

Bakåtkompatibla matematiska anrop utan ForecastPolicy märks forecast_status=
not_requested; saknad issued_at innebär då **inte** verifierad färskhet. Utan
WeatherPolicy är destinationsväder också not_requested. Före verklig integration
måste båda policyerna och explicit klocka användas, med tillförlitlig källmetadata.
Denna leverans kopplar ingen verklig vädertjänst. Conditions antar gemensam vind-/
strömkälla och issued_at; olika leverantörer/cykler måste separeras av framtida adapter.

Tolv nya regressionstester provar gammal prognos med framtida giltighet, färsk
prognos och exakt maxålder, oberoende vågålder, saknad/framtida/naiv tid, tidszoner,
en klockläsning för flera kandidater/delsträckor, faktisk ankomstposition/tid,
överskridande/datalucka/åldersfel endast vid destination, nästa prognos vid exakt
gräns, nollsträcka, faststyrd rörelses ålderspolicy och export. Ett tidigare test
som godkände ankomstväder exakt vid utgången vågprognos har skärpts: rörelsen når
fortfarande dit, men utan nästa giltiga observation är kandidaten nu ej genomförbar.

Gränser: punktkontroller och kända prognosgränser är inte kontinuerliga väderbevis.
Kort topp eller omärkt lucka mellan uppslag/segmentändpunkter kan fortfarande missas.
Ny ankomstkontroll täpper bara till den aktuella ändpunktsluckan; den ger ingen
maritim säkerhetsgaranti eller verifiering av verklig prognoskvalitet. Inga resultat
ersätter djup/sjökort, manövervalidering eller befälhavarens bedömning.

## Explicit jämförelse av avgångstider

`prototype.departures.compare_departures` jämför en explicit lista med samma
kandidatrutter för varje avgång. Standardgränserna är 24 avgångar, 100 rutter och
32 vägpunkter per rutt; gränserna kan konfigureras med positiva heltal. Även
iteratorer konsumeras begränsat. Tomma listor, tidszonlösa tider och dubbla
avgångsögonblick (även med olika tidszoner) avvisas. Inga nya tider/rutter söks.

```python
from prototype.departures import compare_departures
from prototype.presentation import export_departure_comparison

comparison = compare_departures(
    SyntheticEnvironment(lambda p,t: record),
    [depart, depart + timedelta(minutes=10)], Vector(100,0),
    [RouteCandidate("direct")], clock=FixedClock(plan),
    speed_knots=1/KNOT, weather_policy=WeatherPolicy(5,1),
    forecast_policy=ForecastPolicy(600), max_comfort_extra_seconds=40,
    selection_criterion="earliest_arrival")
print(export_departure_comparison(comparison))
```

Exemplet återanvänder prognosdata/importer ovan. Klockan läses **en gång** före
simuleringarna; alla rutter/delsträckor får samma frysta UTC-planeringstid.
Prognosålder bedöms mot denna tid, även vid senare avgångar. Samma miljöobjekt,
båtmodell och policyer används. Standardmodellen skapas en gång; egna modeller
återanvänds. Anroparen måste tillhandahålla ett fryst prognosunderlag och får inte
mutera miljö/modell eller hämta nya prognoser under det synkrona anropet. Wrappern
kopierar inte godtyckliga miljöobjekt och garanterar inte externa datakällors
stabilitet. Kandidater och hinder materialiseras en gång, även från iteratorer.

Varje `DepartureResult.routes` innehåller snabbaste och bekvämaste rutt samt alla
kandidaters restid, ankomsttid, komfortexponering, delsträckor, status och orsak.
Misslyckade rutter behåller partiell bana/elapsed_seconds och orsak, men saknar
godkänd restid, ETA och exponering. Hårda gränser, faktisk destinationskontroll,
hinderkontroll och prognosgränsskydd återanvänds utan lättnader. Komfortens extra
restid jämförs alltid med snabbaste rutten **för samma avgång**. Utan väderpolicy
saknas verifierad komfort/väder; utan ålderspolicy saknas verifierad färskhet.

`shortest_travel` och `earliest_arrival` är separata sammanfattningar, beräknade
från varje avgångs snabbaste genomförbara rutt. En senare avgång kan ha kortare
restid men senare ETA. `selected` är None som standard. Uttryckligt kriterium
`shortest_travel_time` eller `earliest_arrival` krävs för avgångsval; okända
kriterier avvisas. Exakta lika värden avgörs av angiven avgångs-/kandidatordning.
Ingen sammanvägd ”bästa avgång” eller global komfortoptimering införs.
`no_feasible_departure` med tomma val och individuella avbrottsorsaker redovisar
att inget undersökt alternativ klarade kontrollerna. Exporten anger begränsad
sökomfattning och bevarar varje rutts kontrollomfattning: kontroller mellan
uppslag är fortfarande inte kontinuerligt verifierade.

## Fryst prognosunderlag och adapterkontrakt

`ForecastDataset` i `prototype/forecast_data.py` är ett oföränderligt, helt
materialiserat underlag som implementerar Environment.evaluate. Det innehåller
bundle-dataset_id/version och högst ett GridProduct vardera för vind, ström och
vågor. Varje produkt har eget dataset_id/version, källa, utfärdandetid,
giltighet [valid_from,valid_until), geografisk täckning, enheter och referensram.
Metadata följer både uppslagen och resultatsammanfattningens forecast_products,
även när kandidaten avvisas innan första steget. Olika produktcykler kan kombineras
explicit; åldern kontrolleras separat mot samma frysta planeringstid. Inget
automatiskt prognosbyte eller arv av en annan produkts godkända ålder sker.

Vind/ström normaliseras till **mot-vektorer** i sanna öst/nord-axlar, m/s,
relativt mark. Vädergränsen använder markrelativ vind; polarens vattenrelativa
vind beräknas fortfarande som W_ground-C_ground. Normaliserade vågor lagrar Hs(m),
Tm02(s) och enhetsvektor för **från-riktningen** i sanna markaxlar. Från-riktning
omvandlas till kompassvinkel endast vid uppslag. Varje produkt får separat rutnät,
giltighet, täckning och mask; saknad produkt/nod eller ogiltig cell redovisas som
datalucka med produktnamn/orsak, utan att andra giltiga produkter tas bort.

Täckningen är en sluten rektangel i lokala öst/nord-metrar med **explicit WGS84-
origo** (latitud/longitud). Detta identifierar det geografiska området i
prototypens lokala referensram. Alla produkter i ett underlag måste ha samma
origo. Täckningen måste exakt motsvara rutnätets ytterkanter; okänd täckning,
okända enheter/referensramar och deklarerad giltighet utanför tidsnoderna avvisas
vid skapande. Ingen verklig projektion/geodetisk koordinattransformation ingår;
planeringspositioner måste redan vara i detta lokala koordinatsystem. Verkliga
lat/lon-raster behöver en framtida granskad transformation utanför motorn.

Interpolationen är bilinjär i öst/nord och därefter linjär i UTC-tid, komponent
för komponent (u,v), aldrig direkt i vindstyrka eller kompassvinkel. Vågornas Hs
och Tm02 interpoleras skalärt; från-riktningens enhetsvektorkomponenter
interpoleras och omvandlas med atan2. Nästan utsläckta riktningar (<1e-12 i
vektorlängd) ger en uttrycklig datalucka. 359°/1° passerar därmed norr, inte söder.
Interpolation bevarar konstanta värden exakt och håller varje komponent inom
stödvärdenas intervall, så avrundning inte skapar ett överskridande vid en konstant
hård gräns. Detta är en syntetisk interpolationsregel, inte fysisk validering av
vågspektra eller verklig väderutveckling.

Ingen extrapolation tillåts i rum eller tid. Geografiska ytterkanter ingår;
valid_until ingår inte, även vid destinationen. Alla åtta hörn i den valda
rum/tid-cellen måste vara kända, **även hörn med noll vikt** vid en exakt nod.
En None-nod gör därför hela dess interpolationsstöd otillgängligt. Markerade
invalid_cells anges som (tidsindex,nordindex,östindex); de avvisar uppslag även
på sina slutna gränser, så intilliggande giltiga celler inte kan användas för
att kringgå masken. Inget byte till närmaste giltiga nod görs. Vid interna noder
väljs cellen mot större koordinat/tid, utom sista rumskanten som använder sista
cellen. Konservativa regler kan avvisa användbara enstaka noder nära luckor.

`infrastructure/forecast_adapter.py` definierar leverantörsoberoende
ForecastAdapter.normalize(payload)->ForecastDataset. Adaptergränsen ligger
utanför ruttmotorn. Transport/autentisering/hämtning måste utföras **före**
normalisering; normalize är ren och returnerar inga callbacks eller lazy data.
Den syntetiska adapterimplementeringen tar en redan inläst mapping. Fixtureformat:

- Bundle: dataset_id, version, products.
- Varje produkt: product, dataset_id/version/source, issued_at, valid_from/until,
  coverage (gränser/origo enligt ovan), east_m/north_m, times, values och valfri
  invalid_cells. Datum är explicit tidszonsmedvetna datetime, normaliserade till UTC.
- values är [tid][nord][öst][komponent]. Vindnoder är [fart,från-kompassvinkel],
  strömnoder [fart,mot-kompassvinkel], med units ["m/s","deg"] eller ["kn","deg"].
  Referensram är ground-from-true-north respektive ground-to-true-north.
- Vågnoder är [Hs,Tm02,från-kompassvinkel], units ["m","s","deg"], referensram
  ground-from-true-north-tm02. None markerar en saknad nod. Negativa/icke-finita
  värden, okända format och ofullständiga metadata avvisas, inte repareras tyst.

Exempel på kompletta **uppskattade syntetiska testdata** finns i
`prototype/tests/test_forecast_data.py:fixture`. Skapa snapshot med
`SyntheticFixtureAdapter().normalize(payload)` en gång före compare_routes eller
compare_departures och skicka samma snapshot till hela jämförelsen. Alla nästlade
listor/masker kopieras till tuples; metadata/dataclasses är frysta. Ändring av
ursprungligt payload kan därför inte ändra underlaget. Ny prognos normaliseras
till ett **nytt** underlag/version för ett nytt planeringsanrop; det gamla förblir
oförändrat. Legacy SyntheticEnvironment för matematiska tester finns kvar och
kan inte garantera ett godtyckligt callbacks stabilitet; nya adapterflöden använder
ForecastDataset. Domänens importkontroll förbjuder nätverk/I/O i uppslagsmotorn.

Begränsning kvarstår: start-/mittpunkts-/ankomstkontroller bevisar inte kontinuerlig
täckning mellan uppslag. Ett segment kan fortfarande hoppa över en smal mask eller
vädertopp om inget uppslag träffar den. Ingen landmask, projektion eller verklig
prognostjänst har kopplats, och inga maritima säkerhetsgarantier lämnas.

## Datastöd över hela integrerade segment

ForecastDataset.validate_segment utökar tidigare punktkontroller: det accepterade
raka numeriska färdsegmentet modelleras affint i position och UTC-tid. För varje
krävd produkt delas segmentet vid alla korsade öst-/nord-/tidsplan i rutnätet.
Stödet kontrolleras på segmentets ändpunkter, korsningar och varje delintervalls
mittpunkt. Därmed testas varje traverserad interpolationscell, inklusive slutna
maskgränser. En smal markerad cell eller saknad stödnod mellan de vanliga start-/
mittpunktsuppslagen kan inte hoppas över. Ingen väderhämtning tillkommer.

simulate och sail_to_target anropar det valfria SegmentEnvironment-kontraktet
**innan** rörelsen/komforten accepteras. Vid fel avvisas hela steget, tidigare
accepterade steg bevaras och en målfärd ger data_unavailable med produkt/orsak.
Rutt-/avgångsjämförelser återanvänder samma skydd. Aktiverad WeatherPolicy kräver
stödet för ström, vind och vågor; matematiska anrop utan policy verifierar här
endast strömmens stöd. Med frysta rutnät är kontrollen strikt även om legacy-
strömfallback valts; luckor blir inte kontinuerligt godkända genom nollantagande.
Legacy SyntheticEnvironment saknar segmentkontrakt och är fortsatt punktkontrollerat.
Voyage.forecast_support_scope redovisar faktiskt tillgänglig kontrollomfattning.

Segmentet får avsluta rörelsen exakt vid valid_until, utan att extrapolera rörelse
efter gränsen. En separat ankomstkontroll är fortfarande exklusiv: vid denna tid
får den utgångna produkten inte godkännas. Geografiska kanter är slutna. För varje
produkt finns ett fast tak på4096 delintervall per segment. För många korsningar
avvisas uttryckligen; inga celler hoppas över för att hålla kontrollbudgeten.
Kontrollen gäller den integrerade raka banan i lokalt plan och flyttals-/mikrosekund-
upplösning, inte en exakt verklig båttrajektoria eller geodetisk båge.

Detta ersätter den tidigare begränsningen om missade **markerade** cellmasker i
ForecastDataset. Ett komplett interpolationsstöd är däremot inte ett bevis på
kontinuerligt tillåtna vind-/vågvärden, entydig interpolerad vågriktning eller
verklig källkvalitet. Dessa värden kontrolleras fortsatt vid ordinarie uppslag och
ankomst. Omarkerade fel/toppar och legacy-callbacks kräver fortsatt annan validering.
Åtta nya regressionstester använder tunna rum-/tidsceller, missing-noder, diagonal
passage/kantkontakt, exklusiv ankomstgräns, kontrollbudget, båda beräkningsflödena,
rutt-/avgångsval, säker omväg och halverat tidssteg.

## Reproducerbart planeringsscenario

Kör hela det syntetiska planeringsflödet offline, utan privat konfiguration:

```bash
.venv/bin/python -B -m scripts.plan_synthetic > /tmp/seaparser-plan.json
.venv/bin/python -B -m scripts.plan_synthetic --blocked-direct > /tmp/seaparser-blocked.json
.venv/bin/python -B -m scripts.plan_synthetic --boat constant --step-seconds 5
.venv/bin/python -B -m scripts.plan_synthetic --selection-criterion earliest_arrival
```

Standardbåten är den uppskattade testpolaren, inte en uppmätt båt. Fixtureversion1
(`infrastructure/synthetic_forecast.py`) använder lokalt WGS84-origo58°N/11°E,
östnoder[-50,0,20,80,100,150] m, nordnoder[-50,0,20,50] m och tidsnoder vid avgång
+0/300/600/1800 s. Markvinden är4 m/s från norr; östströmmen interpoleras från
0 till0,2 m/s mellan300 och600 s. Hs är1 m vid/under nord0 och1/3 m från nord20,
linjärt däremellan. Tm02=5 s, vågor från norr. Båda avgångarna (02:00/02:10 UTC)
använder samma planeringstid00:00, dataset och hårda gränser5 m/s/1 m; prognosen
är utfärdad100 s före planeringen, maxålder600 s. Data är handvalda testdata.

Tre rutter: direkt100 m österut; nord/syd via(20,±20),(80,±20). --blocked-direct
lägger till syntetiskt slutet hinder x40..60/y-5..5 m. Max extra komfortrestid40 s,
standardsteg10 s, måltolerans0,01 m; övriga budgetar redovisas i manifestet.
Ingen väntan eller automatisk kryssplanering. Den senare avgångens diagonaler
kan sakna tillåten polar-/strömkompensation och redovisas som infeasible.

Oberoende referens för första avgången: testpolaren vid4 m/s vattenvind ger2 m/s
vid90°,1,2 m/s vid45° och1,6 m/s vid135°. Direkt tar50 s. Omvägens referens är
20√2/1,2 +60/2 +20√2/1,6 ≈71,248 s (testtolerans0,01 s). Utan hinder är nord
bekvämare än direkt; med hinder väljs en genomförbar omväg och den senare avgången
har inget genomförbart alternativ. Halverat steg10→5 s behåller första avgångens
val, ger omvägsrestid inom0,01 s och exponering inom0,5 syntetiska exponerings-
sekunder. Dessa toleranser gäller detta kontrollerade scenario, inte all väderdata.

`application/planning.py` har ett fryst PlanRequest och run_plan-usecase. Request
kräver ForecastDataset, båda policyerna och en explicit UTC-planeringstid. Listor
för avgångar/rutter/hinder kopieras begränsat. Applikationslagret stöder här endast
de två inbyggda frysta båtmodellerna med känd serialisering; domänens utbytbara
BoatPerformance-gränssnitt behålls. En framtida egen modell behöver ett explicit,
oföränderligt serialiseringskontrakt för motsvarande spårbarhet.

Manifestet innehåller schema/algoritmversion, planeringstid, samtliga parametrar,
båtprofil/antaganden, produktmetadata och SHA-256 för dataset, båt och kompletta
indata. Datasetets hash omfattar värden och masker, inte bara id/version.
Algoritmversionen måste uppdateras när numeriskt beteende ändras. Hasharna är
reproducerbarhetsidentifierare, **inte** bevis på källans äkthet eller kvalitet.
Identiska underlag/versioner/parametrar ger byte-identisk kanonisk UTF-8-JSON på
den verifierade Pythonmiljön. Ingen rörlig väggklocka eller exekveringstid blandas
in i resultatidentiteten. Byte-identitet mellan framtida Python-/plattformversioner
är inte verifierad. Mät körtid separat; representativ observerad tid dokumenteras
i arbetsloggen utan att göra ett SLA av den.

Resultatet redovisar alla kandidater/avbrott, snabbast/bekvämast per avgång samt
kortast restid och tidigast ankomst separat. Ingen avgång väljs utan uttryckligt
kriterium. Scope och olika kontrollomfattningar följer exporten. Scenariot gör
inga HTTP-/SQL-anrop och inte heller installation, drift eller verklig navigation.

## Kontinuerliga hårda vind-/våggränser i fryst rutnät

Med ForecastDataset och WeatherPolicy används nu metoden
`segment-aabb-component-box-exact-squared-v1` före varje accepterat färdsteg.
För varje vind-/vågprodukt bildas segmentets slutna axelparallella box i öst,
nord och tid. Alla stödcellers slutna boxar som berör denna box inkluderas,
även vid cellgränser. Urvalet görs med ordnade koordinatjämförelser, **inte**
genom sampling. Det omfattar hela det affina integrerade segmentet och kan
även ta med celler/hörn utanför banan. Därför är metoden konservativ.

Beviset gäller den valda komponentinterpolationen, inklusive dess clamp:
varje nästlad lerp håller en komponent mellan sina stödvärden. I varje inkluderad
cell sätts U=max(abs(u_hörn)), V=max(abs(v_hörn)) och H=max(Hs_hörn). Då gäller
för hela cellen (och följaktligen segmentet):

- vindstyrka² <= U²+V²;
- signifikant våghöjd <= H.

Vindkravet verifieras som U²+V²<=vindgräns² med Fraction och **exakt aritmetik
för lagrade binära tal**, så avrundning av sqrt/hypot inte kan godkänna en för låg
gräns. Hs jämförs direkt med den lagrade gränsen. Gränslikhet i det certifierade
höljet godkänns; ingen
vädermarginal/epsilon upphäver ett strikt överskridande. Vind är markrelativ;
ström adderas inte till dessa normaliserade vindkomponenter. Polarens vind relativt
vatten och kursberoende kompensation fungerar som tidigare.

Utfallet är trevärdigt:

- verified: alla konservativa cellgränser är inom båda hårda gränserna och
  certifieringsstödet är känt;
- exceeded: en giltig faktisk punkt på det integrerade segmentet visar ett
  överskridande. Witness sparar produkt, position, tid, komponenter/Hs och gräns;
- unverified: otillräckligt underlag eller otillräckligt konservativt bevis.
  Ett högt hörn utanför banan betyder **inte** konstaterad överträdelse.

Ordinarie uppslag samt segmentets korsningar/delintervallspunkter kan ge ett
vittne till överträdelse; de används aldrig för att bevisa att gränserna hålls.
Ett vindmaximum inne i segmentet får därmed aldrig godkännas bara för att start,
mittpunkt och slut är under gränsen. Oavgjort bevis avvisas som weather_unverified;
dataluckor behåller data_unavailable och konstaterat överskridande weather_limit.
Ingen vanlig godkänd ETA eller komfort kan göra någon av dem valbar. Kontrollen
sker före rörelse/exponeringsuppdatering, för både snabbast och bekvämast.

Tak4096 certifieringsceller per produkt/segment ger uttryckligt unverified, inte
sampling eller överhoppade celler. Även off-path masker/luckor i den konservativa
boxen kan omöjliggöra certifiering trots att banans ordinarie datastöd är känt.
En framtida snävare metod måste verifieras separat; denna metod söker inga exakta
polynomextrema. Boxen och cellhöljena kan avvisa många i själva verket säkra
segment, särskilt i grova rutnät, vid roterande vind eller diagonala banor.

Step.weather_segment_check sparar godkända bevis; Voyage.weather_segment_failure
sparar avvisade bevis/vittnen och weather_segment_status redovisar verified,
exceeded/unverified eller incomplete. Nollsträcka är not_applicable och kräver
fortfarande faktisk ankomstkontroll. Legacy utan segmentkontrakt är not_available
med endast punktkontroller; det beskrivs inte som kontinuerligt verifierat.
Algoritmversionen i applikationsmanifestet är nu v3 och innehåller metod/celltak.

Rörelse får fortfarande sluta vid valid_until, men utgången ändpunkt används inte
som giltigt överträdelsevittne. Den separata ankomstkontrollen kräver fortsatt
valid_from<=arrival_time<valid_until. Datastöd/masker, segmentens hinderkontroll,
prognosålder och ankomstluckor behålls. Beviset gäller endast hårda vindstyrke-/
Hs-gränser för det lokala affina numeriska segmentet i deklarerad ram. Det bevisar
inte verklig källkvalitet, båttrajektoria, kontinuerlig polar-/manövergenomförbarhet,
vågornas riktningsentydighet eller exakt komfortexponering. Tm02/riktning och
komfortintegration kontrolleras fortfarande vid uppslag. Inga verkliga
prognoser, AIS, navigationsgarantier eller nya tjänster har kopplats.
