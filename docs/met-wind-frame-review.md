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
