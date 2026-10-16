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

Nästa funktionssteg behöver behandla en lokalt affin bana med ett helt verifierat
transformationshölje och separat källbunden datum-/serialiseringsevidens. Det får
inte återanvända denna angular-linjära bana som om den vore motorns geometri.
