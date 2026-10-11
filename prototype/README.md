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
`BoatModel` och `Environment` är utbytbara protokoll utan externa beroenden.

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
- Konstant tillgänglig båtfart; `simulate` håller stävriktningen medan
  `sail_to_target` kompenserar ström för rak kurs till målet. Ingen polar,
  motormodell eller fysikalisk vindmodell. Vind kan levereras
  via miljögränssnittet men används inte av konstantmodellen.
- Analytiska syntetiska fält, ingen gridinterpolation, landmask eller verklig
  prognos. Dataleverantören måste själv markera luckor och täckningsgränser.
- Fast tidssteg, sista steget kortas. Ingen adaptiv felkontroll eller uppdelning
  vid datagränser; luckor mellan uppslag kan missas. Täckningsstatus gäller
  endast uppslagen. Ett steg kan påverkas av fallback i mittpunktsprediktionen.
- Målfärden ger restid bara vid uppnått mål. Syntetisk rektangelkontroll finns; ingen djupkontroll,
  segelpolar eller ruttoptimering. Noll markfart ger odefinierad COG (`null`).
- `docs/stromhantering.md` är ett specifikationsförslag; prototypen implementerar
  ovanstående avgränsade del. AGENTS.md, krav, arkitektur, beslutslogg och
  strömförslaget har lästs inför denna bearbetning.

## Antaganden och verifiering

Båtprofilen är syntetisk och uppskattad, inte en verifierad verklig båt.
Demot väljer uttryckligen noll vindavdrift. Alla strömfält är syntetiska;
ingen prognosålder eller navigerbarhet bedöms. Källa och version följer varje
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
samma sak som prognosålder; bedömning av prognosålder återstår.

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
