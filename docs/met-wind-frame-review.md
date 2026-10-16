# MET-vindens referensram: källstöd och native diagnostik

Granskning 2026-10-13. Ingen vindnormalisering eller routingimport införs.
Befintlig MET-dokumentationsgranskning har höjd 10 m, medelperiod 600 s och
FRÅN-konvention med norr=0/öster=90. Sparad faktisk DAS anger
standard_name=wind_from_direction och enhet degree.

## Kontrollerade primärkällor

[NERC:s CF-standardnamn wind_from_direction](https://vocab.nerc.ac.uk/standard_name/wind_from_direction/)
lästes i webbverktyget under detta pass. Definitionen beskriver den horisontella
luftvektorns ursprungsriktning. Vokabulärens exakta matchning till
earthrelativewinddirection stöder tolkningen som jordrelativ konvention.
Det är dokumentationsstöd; det bevisar inte producentens hela beräkning,
geodetiskt datum eller omvandling till motorns lokala AEQD-axlar. Ingen
ny certifierad reference_frame tilldelas det sparade vinduttaget.

[CF:s aktuella fullständiga tabell](https://cfconventions.org/Data/cf-standard-names/current/build/cf-standard-name-table.html)
nekades av webbverktygets svarsstorleksgräns (över 4194305 byte). Den smala
NERC-posten kunde läsas. Ingen ny MET- eller marin datahämtning gjordes och
ingen hel tabell arkiverades. Dokumentationssvar via webbverktyg har inte
beräknad råhash här; tidigare MET-dokumentationshash är fortsatt separat.

## Native meridiankonvergens över Vinga-subset

Befintlig offlineaudit beräknar nu native Lambert-konvergens vid alla 56
sparade producentnoder. Resultat: -3.0668150530393903 till
-2.9719950297439586 grader. Tecken avser PROJ:s konvergenskonvention; inga
vindvärden roteras. För en tangent sfärisk LCC med standardparallell 63 grader
är den oberoende analytiska referensen gamma=sin(63°)*(longitude-15°).
Den följer av Lambert-konens vinkel och källans explicit granskade projektion.
Testet jämför min/max från faktisk longitudmatris med numeriska faktorer inom
1e-6 grad. Detta är en numerisk regressionstolerans, inte vald routingtolerans.

Konvergensen varierar med positionen. Jordrelativa riktningar och native
gridaxlar kan därför inte identifieras som samma ram eller roteras med en
antagen global konstant. Lokal måltransformation och vektorer/interpolation
behöver separat verifiering enligt regional-wind-acceptance.md och
forecast-regridding-proof.md; en vektorrotation ändrar inte den okända
utfärdandetiden eller run-förenligheten. Alla planning_blockers kvarstår.

Kör offline: `.venv/bin/python -B -m scripts.audit_met_metadata fixtures/met-nordic-metadata`.
JSON-fältet native_meridian_convergence har scope
native_grid_orientation_diagnostic_not_wind_normalization. Samma vind-review
reproduceras oförändrad med --wind-sample. Källhashar och rådata är oförändrade.

## Oberoende tangentkonreferens 2026-10-16

`tests/test_met_native_geometry_reference.py` kompletterar PROJ-diagnostiken
med en analytisk invers utan CRS-biblioteksanrop i referensberäkningen.
För den redan granskade nordliga tangentsfären används radianer:
n=sin(63°), rho0=R*cos(63°)/n och t0=tan(pi/4+63°/2).
För källans x,y är rho=hypot(x,rho0-y), theta=atan2(x,rho0-y),
phi=2*atan(t0*(rho0/rho)^(1/n))-pi/2 och lambda=rad(15°)+theta/n.
Detta är vår härledning från tangentkonens geometri, ingen ny producentuppgift.

Alla 56 native noder jämförs både med producentens sparade lat/lon och med
PROJ-inversen. Analytisk/PROJ-vinkelavvikelse är högst testgränsen 1e-10 grad;
max sfäriskt avstånd mot de avrundade producentkoordinaterna är under 0,25 m.
Den tidigare rapportens maxavstånd reproduceras inom 1e-6 m. Dessa är
numeriska regressionstoleranser, inga accepterade routing-/datumfelgränser.

En 0,1 m framåtriktad kord längs vardera native axel verifierar dess sfäriska
bäring mot gamma respektive 90°+gamma inom 1e-5 grad vid alla noder.
Origo, öst/västsymmetri och nordlig axelordning kontrolleras separat.
Detta stärker beviset att native x/y inte är sann öst/nord. Ingen faktisk
vindvektor roteras och ingen WGS84- eller helcellsbindning intygas.

Källåtkomst under granskningen: direkta USGS PDF-försök till pp/1395/report.pdf
och pp/1453/report.pdf gav HTTP 403 i webbverktyget. ITC:s Snyder-kopia
överskred verktygets storleksgräns (23146699 byte). Fulltext har därför inte
verifierats genom dessa försök. [PROJ:s officiella LCC-sida](https://proj.org/en/stable/operations/projections/lcc.html)
kunde läsas; den beskriver sfäriskt stöd och lika standardparalleller.
Formeltestet är en självständig offlinekontroll och ersätter inte producentens
metadata, datumsemantik eller granskad vektortransformation.

Kör med projektets låsta Pythonmiljö: `python -B -m unittest discover -s tests
-p test_met_native_geometry_reference.py -v`. Fyra tester passerar; de binder
även regionalindatats exakta axlar/projektion och metadatahashar till referensen.
Alla planning_blockers och data_unavailable kvarstår.

## Kontinuerliga gränser i den deklarerade källmodellen 2026-10-16

Detta är en analytisk härledning för ideal sfärisk tangent-LCC, inte en
intervallavrundad runtimecertifierare eller ett bevis om producentmask/WGS84.
Använd inversen ovan och sätt b=rho0-y, rho²=x²+b² och n=sin(63°).
Över vårt fulla native nodområde gäller x<0, y<0, rho0>0 och n>0.
Därmed är b>0, rho>0 och cos(phi)>0 för inversens latitudgren.

Derivatorna i radianer blir:

- d(phi)/dx = -cos(phi)*x/(n*rho²), positiv.
- d(phi)/dy = cos(phi)*b/(n*rho²), positiv.
- d(lambda)/dx = b/(n*rho²), positiv.
- d(lambda)/dy = x/(n*rho²), negativ.

Tecknen gäller över varje hel nodrektangel, inte bara vid dess hörn.
För [xl,xr]×[yb,yt] ligger därför latitudminimum vid (xl,yb),
latitudmaximum vid (xr,yt), longitudminimum vid (xl,yt) och
longitudmaximum vid (xr,yb). Varje koordinats extrema nås alltså i ett
identifierat hörn för just detta område. Lat/lon-boxen är ett omslutande
koordinatintervall; dess alla punkter behöver inte ligga i den krökta cellbilden.

Två nya regressioner kontrollerar hela områdets teckenvillkor och jämför
25 PROJ-provpunkter i vardera av de 42 rutorna med analytiska hörnextremer.
1e-10 grad används endast för numerisk korsjämförelse, aldrig för att tillåta
överskridanden i routing. Kontinuitetsargumentet är derivathärledningen, inte
provpunkterna. En syntetisk rektangel över x=0 har högre latitud vid mitten av
sin övre kant än i alla hörn och visar varför hörnregeln inte får generaliseras.

Inget lokalt WGS84-segment har transformerats eller bevisats täckt. Ingen
mask-/interpolationsregel, vindvektorrotation eller hårdgränskontroll följer av
härledningen. En framtida verifierare behöver dessutom konservativ avrundning,
verifierad källdatum-/målbindning och samtliga tidigare beviskrav. Alla nuvarande
planning_blockers och data_unavailable kvarstår.

## Fördjupad tids-/ramgranskning 2026-10-16

[MET Nordic Parameters](https://github.com/metno/NWPdocs/wiki/MET-Nordic-dataset#parameters)
anger tio minuters medel för fart/riktning på 10 m och FRÅN norr/öster.
För nederbörd anges uttryckligen timmen före tidsstämpeln; någon motsvarande
placering av vindens tio minuter identifierades inte i parametertabellen.
Den får inte lånas från nederbörd eller från observationsprodukten Frost.
Produktens beskrivna nedskalning är inte automatiskt vår framtida
interpolationsregel mellan redan sparade native noder.

[MET Examples: Wind direction obtained from x y wind](https://github.com/metno/NWPdocs/wiki/Examples#wind-direction-obtained-from-x-y-wind)
beskriver lokal gridrotation för modellrelativa komponenter. Exempelfilen är
meps_subset_2_5km_20161129T00Z.nc, inte vårt MET Nordic-riktningsfält från 2026.
[FAQ](https://github.com/metno/NWPdocs/wiki/FAQ#wind-direction-obtained-from-x-y-wind)
hänvisar till samma exempel. Detta stöder att ramar måste skiljas, men varken
exempelkonstanter eller rotationsformel överförs som källbevis för vårt fält.
Ingen exempelväderfil hämtades och ingen kod från exemplet kördes.

[CF 1.7 §7.3](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.7/build/ch07s03.html)
förklarar att cellmetod beskriver sammanfattningen och cellgränser dess domän.
Ett parentetiskt interval beskriver ursprunglig provtäthet; det ensamt bestämmer
inte medelperiodens gränser. Koordinaten kan ligga vid slut eller mitt i en
period. Detta är generell metadatavägledning, ingen uppgift om MET:s produktion.

Offlinekontroll av sparad met-forecast.das: vindblocken har standard_name,
units, grid_mapping, coordinates och _ChunkSizes, men inget cell_methods.
Time-blocket har units, standard_name och _ChunkSizes men inget bounds.
Frånvaron avvisar inte råarkivets existens; den hindrar oss från att härleda
exakta medelperioder ur dessa attribut. 600 s är fortsatt dokumentationsuppgift,
inte källäst tidsgränspar. Vindens issued_at och cross-product run-förenlighet
blir inte kända genom denna granskning.

PROJECT_BLOCKER: granskade källor ger fortfarande inte en verifierad placering
av vindmedlet eller full källbunden normalisering till motorns lokala vektorer.
Fortsatt oberoende offlineverifiering: befintliga metadata-/vindtester och
hashbundna läsningar. Alla planning_blockers kvarstår, inga råfixtures ändras.
Nästa begränsade del kan granska en oberoende numerisk referens för lokal
vektortransformation, uttryckligen utan att kvalificera källans vindram eller
utfärdandetid. En sådan referens får inte förväxlas med en färdig vindadapter.

## Lokal vektoravbildning: separat sfärisk referens 2026-10-16

En framtida metod måste bestämma om en vektor avser fysisk fart i en lokal
ortonormal öst/nord-bas eller koordinathastighet i projektionsplanet. Dessa
är inte generellt samma. Ingen sådan policy ändras i denna leverans.

Egen analytisk referens för sfärisk AEQD: längs centralmeridianen norr/söder
om origo är den signerade vinkelradien c=phi-phi0. AEQD ger y=R*c och x=0.
För en liten longitudavvikelse är x=R*(c/sin(c))*cos(phi)*d(lambda).
Eftersom fysisk öströrelse är ds=R*cos(phi)*d(lambda), är den transversella
lokala differentialskalan c/sin(c), med gränsvärde 1 vid c=0. Radial nordskala
är 1. Därför är differentialen där diag(c/sin(c),1), inte generellt en ren
rotation. Detta är vår matematiska härledning, ingen producentuppgift.

Två tester i test_local_vector_reference.py jämför analytiska derivator med
symmetriska projektionsdifferenser för en syntetisk sfär med R=6371000 m.
Testpositioner ligger vid 0, ±1000 och ±1000000 m längs meridianen, med separata
basvektorer och blandad (3,-4). 1 m bassteg och numerisk jämförelsetolerans
2e-8 gäller endast regressionen. Det avlägsna fallet visar skala över 1,004 för
en enhetsvektor, vilket ingen ren rotation kan ge. Det ligger uttryckligen
utanför demonstratorns routingområde; ingen praktisk lokal felgräns härleds.

Testet använder inte WGS84, MET-vindvärden eller accepterade segment, och binder
inte MET-sfären till motorns WGS84-datum. Positiv differentialreferens kvalificerar
varken källa, mask, tidsmedel, interpolation, hårdgränsbevis eller run-förenlighet.
Ingen vektorfunktion införs i produktionskoden. Alla planning_blockers kvarstår.

## Avgränsat källdokumentationsförsök 2026-10-16 20:11 UTC

Den officiella MET Nordic-wikin och THREDDS-användardokumentationen kunde läsas
i webbverktyget. Ingen ny källbunden uppgift kvalificerade vindram, datum,
serialiseringsfel, giltighetsmask eller tidsmedlets placering för de redan
frysta råproven. Den tidigare granskningen av 10 m/600 s och FRÅN-konvention
ändras inte. Inget nytt DDS/DAS-/vind-/marinuttag gjordes.

PROJECT_BLOCKER: en separat avgränsad råtexthämtning av MET:s offentliga
https://raw.githubusercontent.com/wiki/metno/NWPdocs/Examples.md gav URLError.
Operationen hade 15 s-gräns, 131072-bytebudget och avvisade omdirigeringar.
Ingen råtext sparades eller hash påstods. Samma misslyckade operation upprepades
inte, ingen sandbox-/autentiserings-/systemändring gjordes. Privat arbetsrapport:
/home/web/seaparser/autonomy/met-wind-doc-review-20261016T2012Z/review.json.
Webbåtkomst till annan dokumentationsrepresentation är inte lyckad råhashning
eller bindning av generella kodexempel till MET Nordic-provets riktning.

Nästa oberoende funktion genomfördes i stället: grafisk inspektion av befintligt
hashbundet helt-segmenthölje och dess sparade vindstöd, utan kvalificeringslyft.
Se vinga-frozen-review.md. Återuppta källförsök först med konkret annan tillåten
metod/evidens; ingen identisk hämtning, omhämtning av marina data eller ny adapter.
