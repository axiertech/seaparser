# Verkliga prognoskällor för Vinga, granskade 2026-10-12

Kartbakgrund och OSM-land är separata från dessa prognoser. Inga konton, köp,
nya beroenden, databasskrivningar eller publika ändringar ingår.

| Källa | Täckning/upplösning/tid | Åtkomst, licens och beslut |
| --- | --- | --- |
| SMHI SNOW1gv1, vind | Sveriges punkt-/gridprognos. Vinga-anropet returnerade 11.609723°E 57.6395°N, utanför testboxen. 86 giltighetstider, 12 okt 22Z–23 okt 00Z, varierande tidssteg. Exakt native upplösning och uppdateringstakt kunde inte verifieras i tillgänglig SNOW-dokumentation; anta inte äldre PMP-/MEPS-värden | Öppet utan konto/kostnad; CC BY 4.0 enligt SMHI, kommersiellt tillåtet med attribution/ändringsangivelse. Fryst punktreferens importerad; ej regionalt rutnät |
| MET Norway Locationforecast, vind | Norden: MEPS 2.5 km/0–60 h, uppdatering varje timme; medium range ECMWF cirka 9 km/2–10 dygn, två gånger per dygn | Öppet CC BY 4.0/NLOD, identifierad UA/cachning, ingen SLA. Alternativ; inget ytterligare prognossvar hämtat |
| MET Norway Oceanforecast, vågor/ström | Nordvästeuropa. Regionala vågor 4 km/4 uppdateringar per dygn, kustmodell 800 m/2 per dygn där täckt. Vinga svaret flyttas till 11.5955°E 57.626°N; inte bevis för modellstöd i rutten. 208 timsteg, 12 okt 21Z–21 okt 12Z | Öppet CC BY 4.0/NLOD utan konto/kostnad. Svar har Hs, från-riktning och ström mot-riktning/fart, men **ingen vågperiod**, okänt strömdjup och ingen separat modellutfärdandetid. Fryst ofullständig referens, ingen regional extrapolation |
| Copernicus Baltic PHY/WAV | Vinga inom angiven region 9–30°E/53–66°N, cirka 1 nautisk mil/2 km. PHY har bl.a. 15-min surface currents och djupnivåer; WAV har timvis Hs/Tm02/riktning. 00Z-produktion upp till 10 dygn, WAV 12Z 6 dygn, publicering 10/22 UTC | Officiell hjälp säger att åtkomst är kostnadsfri även kommersiellt, med korrekt acknowledgment/citation/credit och relevanta produkt-DOI:n. Nedladdning/processning kräver inloggning (Copernicus Marine eller CDSE). Ingen inloggning eller nedladdning har gjorts. Kontrollera aktuell produkts licens och metadata före import |
| Open-Meteo Marine | Globala/regionala alternativ, EWAM cirka 5 km/timvis/8 dygn/12 h uppdatering; globala strömmar cirka 8 km/timvis/10 dygn/24 h. Leverantören varnar för kustnavigation | Data CC BY 4.0, men hosted gratis-API är endast icke-kommersiellt. SeaParser-produktutveckling antas kommersiell; inget anrop, konto eller abonnemang. Data/licens ger inte fri rätt till hosted kommersiell trafik |

Officiella källor:
[SMHI API-katalog](https://www.smhi.se/data/sok-oppna-data-i-utforskaren/meteorologisk-prognos-api),
[SNOW tidsmetadata](https://opendata.smhi.se/metfcst/snow1gv1/get_multipoint_forecast),
[SMHI villkor](https://www.smhi.se/data/om-smhis-data/villkor-for-anvandning),
[MET vindmodell](https://docs.api.met.no/doc/locationforecast/datamodel),
[MET havmodell](https://docs.api.met.no/doc/oceanforecast/datamodel),
[MET punktkontrakt](https://api.met.no/weatherapi/oceanforecast/2.0/documentation),
[MET JSON/tidsmetadata](https://docs.api.met.no/doc/ForecastJSON),
[MET licens](https://api.met.no/doc/License),
[MET tjänstevillkor](https://api.met.no/doc/TermsOfService),
[Copernicus PHY-manual](https://documentation.marine.copernicus.eu/PUM/CMEMS-BAL-PUM-003-006-007.pdf),
[Copernicus WAV](https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_WAV_003_010/description),
[Copernicus åtkomst](https://help.marine.copernicus.eu/en/articles/4220332-how-to-register-for-copernicus-marine-service),
[Copernicus citering och attribution](https://help.marine.copernicus.eu/en/articles/4444611-citing-copernicus-marine-products-and-services),
[MET THREDDS-katalogöversikt](https://api.met.no/product/THREDDS),
[MET Oceanforecast-dokumentation](https://api.met.no/weatherapi/oceanforecast/2.0/documentation),
[Open-Meteo modelltabell](https://open-meteo.com/en/docs/marine-weather-api),
[Open-Meteo tjänstevillkor](https://open-meteo.com/en/terms).
Copernicus PHY-manualen innehåller även äldre 9-dygnstabell; faktisk run/version
måste verifieras före användning. Native wet mask, kustprecision, djupnivå och
Tm02 får inte ersättas med en grov regions bounding box eller annan vågperiod.

## Fryst referens och adapterkontrakt

`fixtures/vinga-point-forecast-reference.json` innehåller de två verkliga svaren,
URL, hämtningstid (UTC filsluttid för svar), råsvarens SHA256 och attribution.
Svaren innehåller inga nycklar, personuppgifter eller autentisering. De sparas
för reproducerbar offlinegranskning, inte för aktuell användarplanering.

`PointForecastAdapter` normaliserar till provideroberoende oföränderliga
`PointForecast`-poster. Den kompletterar befintliga rutnätsadaptrar; punktposter
är **inte** `ForecastDataset/GridProduct` och ingen låtsad täckning skapas.
SMHI createdTime är prognosens skapandetid/utfärdandebasis; referenceTime är
prognosens start och bevaras i råsvaret. MET updated_at är dokumenterat senaste
datauppdatering, inte separat modellutfärdande: issued_at förblir okänd.

Vind: m/s, FRÅN sann nord medurs, relativ mark, konverteras till mot-vektor
öst/nord. Ström: m/s, MOT sann nord medurs, relativ mark, djup okänt i svaret.
Vågor: Hs(m), FRÅN-riktning som komponenter; Tm02(s) är uttryckligen None.
Tidinterpolation sker linjärt på komponenter endast vid **den returnerade
punkten** och inom [första,sista) giltighet. Saknade stödpunkter/komponenter
avvisas, ingen riktningsinterpolation direkt över 359°/1° eller extrapolation.
Utfärdande och maxålder kontrolleras vid explicit planeringstid, inte ETA.
Inga nätverksanrop görs i adaptrarna, interpolationen eller ruttjämförelserna.

`.venv/bin/python -B -m scripts.forecast_reference` ger en spårbar granskning
med `data_unavailable`: regional täckning saknas, vågperiod och marin
utfärdandetid saknas. Ingen snabbaste/bekvämaste verklig rutt eller GPX utses.
Det är ett verifierat avvisande **före** motorn, inte en genomförd verklig färd.
Den tidigare syntetiska API/kart/GPX-fixturen och dess motortester bevaras.
Nästa steg är native griddat underlag med mask, utfärdande, Tm02 och strömdjup,
inte att sprida närmaste punkt över området. MET:s officiella Oceanforecast-
dokumentation hänvisar råa modeller till NetCDF/OPeNDAP på THREDDS, men den
länkade katalogsökvägen gav HTTP 404 vid kontroll 2026-10-13. Den officiella
THREDDS-översikten beskriver arkivdata för aktuella/historiska ocean- och
isprognoser. Rätt Vinga-dataset, körmetadata, variabler och native mask har ännu
inte verifierats mot en åtkomlig katalog/fil.

Copernicus Marine uppger numera att dataåtkomst är kostnadsfri även för
kommersiella syften, med korrekt attribution och produkt-DOI. Nedladdning kräver
inloggning. Ingen Copernicus/CDSE-inloggning eller nedladdning har gjorts;
produktens aktuella licens, dataset och metadata behöver fortfarande granskas
före import.

## Copernicus Marine-förhandsgranskning 2026-10-13

Aktuell katalog visar två aktiva forecast-produkter för Östersjön/Kattegatt/
Skagerrak. Vinga ligger inom bådas publicerade område. Vågproduktens DOI är
`10.48670/moi-00011`, produkt-ID
`BALTICSEA_ANALYSISFORECAST_WAV_003_010` och timdataset
`cmems_mod_bal_wav_anfc_PT1H-i`. Katalogen anger WAM 4.7, cirka 1 nautisk mil
(2 km), timvis data och två körningar per dygn: 00Z med 10 dygn respektive 12Z
med 6 dygn. Variablerna omfattar signifikant våghöjd, period och riktning för
total sjö/vindsjö/svall samt binär havs/landmask och batymetri. Exakt NetCDF-
variabelnamn, enheter, giltighetskoordinater och datasetversion ska bekräftas i
datasetmetadata och hämtad fil före adaptering.

Fysikproduktens DOI är `10.48670/moi-00010`, produkt-ID
`BALTICSEA_ANALYSISFORECAST_PHY_003_006` och timdataset
`cmems_mod_bal_phy_anfc_PT1H-i`. Katalogen anger NEMO 4.2.1, cirka 1 nautisk
mile, 56 vertikala nivåer, horisontell ström och 00Z/12Z forecast med 10/6
dygns horisont. Katalogen bekräftar nivåer men inte djupkoordinatens tecken,
referens, ytligaste nivå, units eller om giltighet/runmetadata matchar vågfilen;
detta måste inspekteras i faktisk fil. Ström på ytlagret är inte en verifierad
modell av ström vid båtens hela djupgående.

Avgränsat första uttag: båda timdataseten, lon 11.58–11.63°E, lat
57.62–57.65°N, giltighet 2026-10-13 12:00–16:00 UTC. Detta är en liten
4-timmars Vinga-ruta för schema-/datakontroll, inte en verifierad helruttprognos.
Ändra inte tidsfönstret för att dölja att det saknas stöd; använd metadata för
att välja en gemensam framtida period om detta uttag inte längre är tillgängligt.
Behåll den ursprungliga NetCDF-filen och dess SHA-256. Kontrollera initiering/run,
valid time, CRS/koordinater, geometri, enheter, fill values, havs-/landmask,
vågperiod Tm02, ytligaste strömnivå och båda produkternas samtidiga tidsstöd.

Copernicus har också Baltic L3 NRT-satellitvind (`WIND_BAL_PHY_HR_L3_NRT_012_102`,
DOI `10.48670/mds-00332`): dagliga 1 km havsytobservationer med oregelbunden
uppdatering. Katalogens senaste giltighet var 29 september 2026. Det är inte en
vindprognos och får inte användas som framtida ruttväder. Global scatterometer-
vind är också observationer (daglig, cirka 0.125°), inte forecast. Någon
Copernicus atmosfärisk vindprognos för rutten har inte verifierats. MET:s
Locationforecast ger punktvind; MET:s råa nordiska grid är en kandidat, men den
tidigare länkade THREDDS-katalogvägen gav 404. Därför kan inte en fullständig
verklig vind/våg/ström-rutt ännu godkännas.

Kommersiell användning är enligt Copernicus hjälpdokumentation avgiftsfri med
föreskriven attribution/citering och produkt-DOI. Attribution vid användning:
`Generated using E.U. Copernicus Marine Service Information; DOI: 10.48670/moi-00010, 10.48670/moi-00011`.
Kontrollera produktsidan/licensen före vidare distribution.

## Fryst, avgränsat Copernicus-uttag 2026-10-13

Toolbox 2.5.0 använde den redan sparade autentiseringen. Två dynamiska uttag
hämtades i samma anropade giltighetsfönster, 2026-10-13 12:00–16:00 UTC, inom
11.58–11.63°E och 57.62–57.65°N. Ett tredje uttag hämtade produktens statiska
mask och batymetri. Ingen autentisering eller credential kopierades till
repositoryt. Data är små (vardera under 30 KB) och ligger frysta i
`fixtures/vinga-copernicus/`; manifestet innehåller exakt produkt/dataset/version,
subset, UTC hämtningstid, käll-URL och SHA-256. Attribution finns i manifestet.

Vågfilen är `cmems_mod_bal_wav_anfc_PT1H-i`, version `202311`, variablerna
`VHM0` (m), `VTM02` (s, Tm02) och `VMDR` (grader, vågornas från-riktning).
Strömfilen är `cmems_mod_bal_phy_anfc_PT1H-i`, version `202411`, variablerna
`uo`/`vo` (m/s, öst/nord, mot-riktning), på dokumenterad ytligaste modellnivå
0.501646 m positiv nedåt. Båda innehåller fem gemensamma giltighetstider
12, 13, 14, 15 och 16 UTC. Interpolationsgiltigheten är halvöppen
`[12:00,16:00)`; sista tidpunkten är endast övre gräns, inte giltig observation.

Nätfilerna innehåller giltighetstid men ingen identifierbar modellkörtid eller
prognosutfärdandetid. Hämtningstid och kataloguppdatering är inte utfärdandetid;
`issued_at` sparas därför som okänd. Copernicus-forecast och värdena kan granskas,
men friskhetskontrollen avvisar dem tills verklig köridentitet/utfärdande hittas.
Vindprognos saknas fortsatt. Därför kan detta underlag **inte** ge verklig
regional ruttplanering, snabbaste/bekvämaste alternativ eller GPX.

Den statiska delen (`cmems_mod_bal_wav_anfc_static`, version `202311`, del
`bathy`) har 2×2 binära havsmaskceller och djupvärden 16–25 m. De fyra vågnoderna
är märkta hav. Djupvariabeln är `deptho` i meter med standardnamnet
`sea_floor_depth_below_geoid`; detta är modellbatymetri och används inte för
att godkänna säkerhetsmarginal, djupgående, landrutt eller tidvatten. Dess
vertikala datum/kompatibilitet och fullständighet för navigation har inte
validerats. Strömgriden är förskjuten ungefär 12 m från våg/maskgriden och får
inte ärva deras mask genom närmaste-granne-interpolation.

Den providerbegränsade CF-adaptern kontrollerar standardnamn/enheter, separata
grider och giltighet, omvandlar `uo`/`vo` direkt till öst/nordvektorer och
`VMDR` från-riktning till komponenter. Den accepterar endast de fyra statiska
maskceller som ligger exakt på våggriden; maskland blir datalucka. Lokala
WGS84/AEQD-axlar är centrerade på 57.633°N, 11.605°E och projektionens avvikelse
från separabla gridaxlar begränsas till 1 m. Adaptern hämtar inte nätverk. Den
skapar bara current- och waves-produkter, utan wind; freshness- och
täckningskontrollen avvisar fortfarande en rutt. Griden med 2×2 celler är en
fält-/adapterverifiering, inte ett kontinuerligt kust- eller landmaskbevis.

Offlinekontroll:

```bash
.venv/bin/python -B -m scripts.audit_copernicus fixtures/vinga-copernicus
```

Den läser frysta NetCDF-filer, verifierar hash, koordinater, variabler, tidsaxel
och mask och rapporterar `fields_verified`; det är uttryckligen inte
`route_verified`. Prognosutfärdande och regional vindgrid är nästa blockerare.

### Privat autentisering på servern

Copernicus Marine Toolbox 2.5.0 är senaste stabila versionen enligt officiella
PyPI 2026-10-13. För att skapa dess standardcredentials ska ägaren logga in på
servern som Linux-användaren `seaparser` och köra interaktivt:

```bash
cd /tmp/seaparser-real-map-data
.venv/bin/python -m pip install --index-url https://pypi.org/simple 'copernicusmarine==2.5.0'
umask 077
.venv/bin/copernicusmarine login
chmod 600 /home/web/seaparser/.copernicusmarine/.copernicusmarine-credentials
```

Skriv användarnamn/e-post och lösenord endast vid Toolboxens interaktiva
prompt i den privata SSH-terminalen; lösenordet ekas inte. Det hamnar då i
`/home/web/seaparser/.copernicusmarine/.copernicusmarine-credentials`, inte i shellhistorik,
miljövariabler eller Git. Skicka aldrig värden eller terminaldump hit. Kontrollera
inloggningen utan att visa konfigurationen:

```bash
.venv/bin/copernicusmarine login --check-credentials-valid
```

Nedladdningen kräver även DNS/HTTPS från servern till Copernicus auth- och
datatjänsterna. Aktuell agent-sandbox kan inte lösa externa DNS-namn, så toolbox,
inloggning och filhämtning har ännu inte körts där. När autentiseringen finns kan
subset hämtas från ovanstående dataset och bounding box med `copernicusmarine
subset`; välj endast den gemensamma giltiga tiden i dessa fyra timmar. Adapter,
datavalidering och ruttutvärdering ska implementeras först efter granskning av de
faktiska NetCDF-metadata och värdena.

## Kandidatbegränsning

`.venv/bin/python -B -m scripts.audit_candidates` jämför 2 och 8 kandidater
på samma syntetiska Vinga-dataset, klocka, polar, marginal och avgångar.
Endast offlineaudit får ändra denna parameter; API:t avvisar extra fält.
Fryst resultat: `fixtures/vinga-candidate-audit.json`. I just denna fixture
ändras varken snabbast eller bekvämast vid båda avgångar:
878.214920 s / exponering 1499.690716 respektive 845.858496 s / 1434.348747.
Båda sökningarna är trunkerade. Resultatet bevisar inte konvergens/global
optimalitet; andra vind-/ström-/vågfält kan flytta bästa kandidat utanför de
första två geometriska grafvägarna. Komfort jämförs fortfarande med snabbaste
undersökta rutt för samma avgång, med samma extra restidsgräns och hårda gränser.
Ingen kandidatkänslighet för verkliga prognoser påstås: de avvisas redan för
ofullständigt regionalt underlag.

## Avgränsad hämtning och offlineaudit efter installerad Toolbox

Användaren har installerat Toolbox 2.5.0 och verifierat autentisering i worktreets
`.venv`. Sparad autentisering återanvänds; inga credentials läses av projektkoden
eller inkluderas i script, Git, argument eller loggar. Toolboxens faktiska
standardfil ligger under `$HOME/.copernicusmarine/` (sökvägen ovan korrigerad).

Exakt kommando i vanlig SSH-terminal, som `seaparser`:

```bash
chmod 600 /home/web/seaparser/.copernicusmarine/.copernicusmarine-credentials
bash /tmp/seaparser-real-map-data/scripts/download-copernicus.sh
```

Scriptet startar endast datatransport och offlineaudit, aldrig en Codex-session,
databasoperation eller ruttplanering. Lås hindrar samtidiga nedladdningar.
Varje försök har starttid, explicit 10-minuters slutgräns (högst 10 s TERM-grace),
avslut och exitkod i `/home/web/seaparser/autonomy/copernicus/<UTC>-<pid>.log`
och `.exit`. Data och rapporter ligger i motsvarande katalog. Scriptet använder
worktreets absoluta `.venv/bin/python` och är oberoende av terminalens cwd.

Tre separata NetCDF-filer: timvågor VHM0/VTM02/VMDR, timström uo/vo på
katalogens gemensamma ytligaste djupnivå samt **separat statisk vågmask** från
`cmems_mod_bal_wav_anfc_static`. Den officiella WAV-manualen placerar `mask`
(sea=1/land=0) i static-datasetet, inte i timdatasetet. Filerna hämtas med
strict-inside för den tidigare boxen/tiden; boxen utökas inte för att dölja
saknat gridstöd. Aktuell katalogversion, del och service binds uttryckligen,
och CF standard_name/uniter kontrolleras före hämtning. Preflight avvisar
okänd storlek eller uppskattning över 10 MB per fil/100 MB transfer. Samma
10 MB-gräns kontrolleras efter hämtning. Ingen original helregionsfil laddas ner.

SHA-256, hämttid, dataset/version/del/service, variabler och exakt begäran sparas
i `manifest.json`; credentialvärden eller auth-URL:er ingår inte. Om ett senare
steg misslyckas bevaras redan hämtade filer och deras partiella manifest. Nästa
försök får en ny katalog och skriver inte över tidigare data.

`scripts.audit_copernicus` verifierar filhashar, CF-metadata, fem exakt begärda
UTC-timsteg, native stigande koordinater, maskens exakta våggrid, komponenternas
dimensioner, explicit positivt-nedåt ytströmdjup och fill-value/datastöd.
Vågkomponenterna blir Hs/Tm02 och enhetsvektor för FRÅN-riktning; strömmens
öst/nord MOT-vektor behålls. Maskerade/icke-finita värden blir explicita luckor.
Rapporten anger `adapter_sample_checks=passed` endast om faktiska filkontroller
passerar. `audit.json` ger alltid `regional_routing_unavailable`: inget native
lon/lat-grid omvandlas till ett lokalt rektangulärt routinggrid. Vind, strömmask,
run-förenlighet, källkvalitet och geografisk adapter återstår. Saknad CF
forecast_reference_time förblir okänd; hämttid/skapandetid används inte som
modellutfärdande. Vågmask överförs aldrig till ett annat strömgrid.

Offlineadapterns komponentkontrakt och NetCDF-verifieraren har tester med
**syntetiska** små filer, inte påstådda Copernicus-nedladdningar. xarray/numpy
används endast i hämt-/auditmiljön från den installerade Toolboxen. API,
ruttmotor, primär beroendelåsning och publik drift ändras inte. Fyra NetCDF-tester
hoppar över sig i miljöer utan dessa extras; övriga kontrakttester är
beroendefria och körs i vanlig CI. Toolbox 2.5.0 kontrolleras före hämtning.

Agentförsök 2026-10-13 04:55:17–04:55:19 UTC: exit 1, `gaierror` från
Copernicus STAC-DNS; inga data hämtades och ingen faktisk marin filadapter
verifierades. Åtkomst måste prövas med kommandot ovan i vanlig terminal.
Regional vindprognos är fortfarande en separat blockerare.

Officiell implementation/kontrakt:
[Toolbox Python interface](https://toolbox-docs.marine.copernicus.eu/en/stable/python-interface.html),
[WAV-manual, variabler och static-mask](https://documentation.marine.copernicus.eu/PUM/CMEMS-BAL-PUM-003-010.pdf).
