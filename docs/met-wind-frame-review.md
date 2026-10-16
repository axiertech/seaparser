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
