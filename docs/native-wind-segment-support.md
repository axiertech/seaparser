# Hela segmentets matematiska native-hölje

Avgränsad implementation 2026-10-16, **ingen kvalificerad ruttintegration**.
`infrastructure/native_wind_geometry.py` omsluter hela geografiska boxar på den
redan granskade MET-sfären. `application/native_wind_support.py` binder ett
uttryckligen källsfäriskt segment till samtliga berörda sparade rumtidsrutor
och deras rånoder. Befintlig vindläsare och källhashar återanvänds genom
`load_native_wind`; ingen marin adapter, hämtning eller motor ändras.

Detta är ett konkret delsteg mot kravet i regional-wind-acceptance.md och
forecast-regridding-proof.md. **Det löser inte bindningen av motorns lokalt
raka WGS84/AEQD-segment till källsfären.** Ett flaggat koordinatsystem är inte
sådan evidens. WGS84/lokala/okända segmentramar avvisas; inte heller ett korrekt
namngivet källsfärssegment ger en ruttkandidat eller kvalificerad prognos.

## Matematisk representation och hölje

Indata representerar ett segment vars latitud, longitud och tid är affina på
källsfären. Det är en explicit matematisk granskningsbana, **inte en uppmätt eller
redan transformerad rutt**. Hela banan ligger i ändpunkternas latitud-/longitudbox.
Vi omsluter sedan hela boxens icke-linjära projektion; vi projicerar inte bara
ändpunkterna eller ett antal kantprov. Resultatet är konservativt och kan ta med
rånoder långt från banan, eller avvisa en bana vars snävare bild hade rymts.

För källans granskade tangentsfäriska LCC med R=6371000 m och parallell 63°
används följande härledning, med vinklar i radianer:

- n=sin(63°), rho0=R*cos(63°)/n, t0=tan(pi/4+63°/2).
- rho=rho0*exp(n*log(t0/tan(pi/4+phi/2))).
- theta=n*(lambda−15°), x=rho*sin(theta), y=rho0−rho*cos(theta).

Detta är den framåtriktade motsvarigheten till projektets oberoende
inverskonreferens. [PROJ:s LCC-dokumentation](https://proj.org/en/stable/operations/projections/lcc.html)
bekräftar parameterbetydelserna och att +R väljer sfär; den dokumentationssidan
är ingen evidens för MET/WGS84-datumöverensstämmelse.
Den matematiska regionen begränsas till latitud 50–70° och longitud 5–25°.
Källans exakta granskade projektionssträng måste matcha; andra projektioner
avvisas. Gränserna är numeriska metodgränser, inte utökad prognostäckning.

Alla intervalländar och operationer är exakta rationella tal. Varje resultat
avrundas utåt till multipler av 10^-30 i respektive storhets enhet. Detta är
**inte en vald global felmarginal på 10^-30 meter**: ackumulerade intervallfel
följer med genom hela beräkningen och är inneslutna i slutresultatet.
Beroenden mellan intervall släpps konservativt, aldrig genom uppskattad korrelation.

Transcendenta funktioner använder 48 termer med explicita svansgränser:

- pi omsluts med Machins identitet 16*atan(1/5)−4*atan(1/239), där atan-seriens
  alternerande rest ligger mellan två angränsande partialsummor.
- Sinus/cosinus använder alternerande Taylorserier på |vinkel|≤1,5. Vid den
  valda trunkeringen avtar svansen. Sinus är monoton över hela detta intervall;
  cosinus får inre max 1 om vinkelintervallet innehåller 0.
- log(z)=2*sum(u^(2k+1)/(2k+1)), u=(z−1)/(z+1), för 1/2≤z≤2.
  Absolut rest efter N termer är högst
  2*|u|^(2N+1)/((2N+1)*(1−u²)).
- exp(z), |z|≤1, använder positiv Taylorserie och rest högst första utelämnade
  termen/(1−z/(N+1)) för z≥0. Negativa argument hanteras genom reciprokt
  intervall. Monotonicitet omsluter funktionens hela inintervall.

Ingen flyttals-/biblioteksroundtrip eller provtäthet används som höljesbevis.
Biblioteket används endast i oberoende numeriska referenstester.

## Komplett råinventering, inte interpolations- eller säkerhetsbevis

Varje sluten intilliggande x-, y- och tidnodruta som tangerar den konservativa
rum/tid-boxen tas med. Vid gemensam gräns inkluderas **båda** grannrutorna,
även tidigare/nästa tidruta och hörn med eventuell framtida nollvikt. Alla
åtta råhörn per rumtidsruta och alla unika hörnnoder inventeras. Ingen regel om
bilinjär/trilinjär producentinterpolation antas av denna adjacency-inventering.
En okänd större interpolationsstencil kan kräva mer stöd och blockerar fortsatt.

Om någon del av boxen ligger utanför sparade nodgränser eller tider blir det
ingen klippt positiv inventering. Överbudget ger uttryckligt felresultat utan
trunkerade cell-/nodlistor. Saknat/icke-finit råhörn bevaras som null och gör
inventeringen ofullständig; kvarvarande komponentvärden tappas inte bort.
Slut vid sista prognosnoden kan avgränsa rörelse, men godkänner inte ankomst.
600 s vindmedels okända tidsplacering utökar inte det nominella tidsstödet.

Rapporten binder exakt segment (rationella grader och UTC-tid), metodversion,
källa/projektion, samtliga vindkällhashar, fullständig materialiserad
vindfingerprint, geometrihölje, budget och varje berört råvärde. Ändrade rådata
utan ändrat deklarerat källhashfält ändrar fortfarande input-/rapportidentitet.
Detta bevisar inte att ett direkt konstruerat objekt kommer från producenten;
scripts använder den befintliga hash-/dimensions-/semantikvaliderade läsaren.

Markandel följer varje nod separat och blir aldrig giltighetsmask. Ingen
våg-/strömmask läses eller överförs. Rapporten behåller uttryckligen:

- physical_source_support_qualified=false, local_route_geometry_binding_verified=false.
- Okänd serialiseringsfelgräns för källaxlarna och okänt datumfel till WGS84.
- Okänd vindgiltighetsmask, interpolationsregel/stencil och tidsmedlets placering.
- Okvalificerad vindram och inget säkerhetshölje. Inga påhittade komponenter.
- data_unavailable och inga snabbaste/bekvämaste kandidater; befintliga blockerare
  bevaras. Inga utfärdandetider, run-identiteter eller run-förenligheter fylls i.

## Körbart exempel och oberoende referenser

`fixtures/met-source-sphere-segment.json` är en deklarerad **matematisk bana**
57,630°/11,600° till 57,640°/11,610°, 2026-10-13 12:20–14:40 UTC. Vädervärdena
kommer från de befintliga verkliga frysta proven; själva banan är ingen verklig
navigationsrutt. Exemplet ger sex rumtidsrutor (k=0,1,2; j=2,3; i=2) och
24 unika rånoder. Rapport: `artifacts/native-wind-segment-review/report.json`.

```bash
python -B -m scripts.native_wind_segment --segment fixtures/met-source-sphere-segment.json --output artifacts/native-wind-segment-review/report.json
python -B -m unittest tests.test_native_wind_geometry tests.test_native_wind_support -v
```

Testerna kontrollerar exakta trig-/log-/exp-identiteter, källans naturliga origo,
öst/västsymmetri och tre kända native positioner genom oberoende analytisk invers
samt PROJ. En numerisk referenstolerans på 1 mikrometer är **inte** en antagen
geodetisk felgräns eller routingtolerans. Ett exakt inre vittne visar att
latitudbågen 63° mellan longitud 14° och 16° passerar y=0 medan båda ändpunkterna
har y>390 m: en box byggd bara på ändpunktsprov skulle missa kurvans inre.
Negativa fall omfattar saknat off-path-hörn, gränskontakt, tids-/rumsextrapolation,
budget, ändrad hash/värde/bana, okänd ram och tvetydig indata.

Den första angular-linjära banan kompletteras nedan med en lokalt affin bana
på samma uttryckliga källsfär. Ingen av dem får återanvändas som motorns
WGS84-geometri utan separat källbunden datum-/serialiseringsevidens.

## Lokalt affin bana på källsfären 2026-10-16

`SourceLocalSegment` och `inspect_source_local_segment` utökar samma läsare och
råinventering till en bana som är affin i lokala öst-/nordmeter och tid på en
**explicit matematisk MET-sfär**. Ramen har AEQD-origo 57,633°/11,605° och
R=6371000 m. Det är inte den befintliga WGS84-/AEQD-ramen, och inga verkliga
ruttkoordinater får byta etikett för att kringgå datumkravet. Ingen adapter,
väderinterpolation eller transformation av ruttmotorns verkliga indata införs.

[PROJ:s AEQD-dokumentation](https://proj.org/en/stable/operations/projections/aeqd.html)
anger separata sfäriska/ellipsoidiska former, origo och +R. Följande hela-hölje
är en egen analytisk härledning för den explicit deklarerade sfären:

1. En affin planbana p(t)=(1−t)a+t*b uppfyller
   norm(p(t))≤(1−t)norm(a)+t*norm(b)≤max(norm(a),norm(b)). Därför ryms **hela**
   segmentet i en disk kring origo. Maximal kvadrerad ändpunktsnorm beräknas
   exakt rationellt, utan att först avrunda en norm. Gränsen 1000 m prövas på
   den exakta kvadraten; även en godtyckligt liten överskridning avvisas.
2. Diskradien omsluts med heltals-isqrt och exakta kvadratjämförelser på
   rationella tal. Nedre/övre rotgränser ligger på 10^-30-metersnätet och deras
   kvadrater omsluter det exakta talet. Ingen antagen bibliotekssqrt-tolerans.
3. I sfärisk AEQD är avståndet r från origo den radiala geodetiska längden.
   På varje radial geodet från origo till diskens punkter gäller
   ds²=R²(dphi²+cos²(phi)*dlambda²), alltså |dphi/ds|≤1/R. Alla punkter och
   deras radialgeodeter ligger i latitudbandet phi0±r/R.
4. I detta band är cos(phi)≥c_min>0, med c_min omsluten nedåt av befintlig
   rationell cosinusintervallräkning. Därför |dlambda/ds|≤1/(R*c_min) och
   |delta lambda|≤r/(R*c_min). Bandet når inte en pol; longituden är kontinuerlig
   runt det fasta Vinga-origot. Detta omsluter **hela disken**, inte ett antal
   prov på den eller på segmentet.
5. Det omslutande latitud-/longitudintervallet förs genom befintligt helt-box-
   hölje för sfärisk LCC och samma slutna rum-/tidsinventering. All aritmetisk
   intervallavrundning följer med. Okänd datum-/källserialiseringsfelgräns är
   fortfarande null och får inte uppfattas som noll.

Diskhöljet är avsiktligt brett: två olika banor med samma största ändpunktsradie
kan få samma hölje och rånodmängd. Rapporten binder därför också de **ursprungliga
lokala ändpunkterna**, ramdefinitionen, tidsintervallet, diskens exakta
radiekvadrat, radieintervall, geografiska hölje och båda metodversionerna.
Samma disk får inte sudda ut banans identitet. Kandidat-/mask-/interpolations-/
medelperiods-/säkerhetsgrindar är oförändrade. local_to_source_sphere_enclosure_verified
avser endast denna matematiska ram; wgs84_route_binding_verified,
local_route_geometry_binding_verified och physical_source_support_qualified är false.

Exemplet `fixtures/met-source-local-segment.json` går från (−300,−200) till
(400,300) meter på källsfären, 2026-10-13 12:20–14:40 UTC. Den exakta största
radien är 500 m (3–4–5-referens), och höljet ger 12 rumtidsrutor och 36 rånoder.
Det är en granskningsbana, inte en verklig navigationsrutt.

```bash
python -B -m scripts.native_wind_segment --segment fixtures/met-source-local-segment.json --output artifacts/source-local-wind-review/report.json
python -B -m unittest tests.test_source_local_wind_support -v
```

Nio nya testmetoder omfattar exakt 3–4–5-norm, rationella/irrationella
rotgränser, origo, kardinal-/diagonalpunkter via oberoende sfärisk
3D-storcirkelreferens och PROJ, motsatta ändpunkter genom origo, oförändrat
resultat vid låg Decimal-precision, full rånodmängd, olika banor inom samma
disk, budget/lucka/tid, ram-/radieavvisning och föregående rapports identitet.
Numeriska referenstoleranser 1e-10 grad/1e-6 m gäller bara testreferensernas
flyttalsavrundning; inneslutningsbeviset bygger på olikheterna ovan och exakta
utåtriktade intervall, inte på dessa prov eller toleranser.

Det återstående huvudgapet är nu källbunden evidens för verkliga ramar,
axelserialisering, giltighetsmask och interpolations-/medelperiodssemantik.
En matematisk transformation mellan uttryckliga sfäriska ramar löser inte det.
Nästa tillåtna steg är ett konkret avgränsat proveniens-/metadataförsök med
befintliga källor och autentisering, utan nya uttag av samma marina data eller
antagna kvalificeringsflaggor. Den befintliga grafiska artefakten är oförändrad.
