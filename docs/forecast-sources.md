# Verkliga prognoskällor för Vinga, granskade 2026-10-12

Kartbakgrund och OSM-land är separata från dessa prognoser. Inga konton, köp,
nya beroenden, databasskrivningar eller publika ändringar ingår.

| Källa | Täckning/upplösning/tid | Åtkomst, licens och beslut |
| --- | --- | --- |
| SMHI SNOW1gv1, vind | Sveriges punkt-/gridprognos. Vinga-anropet returnerade 11.609723°E 57.6395°N, utanför testboxen. 86 giltighetstider, 12 okt 22Z–23 okt 00Z, varierande tidssteg. Exakt native upplösning och uppdateringstakt kunde inte verifieras i tillgänglig SNOW-dokumentation; anta inte äldre PMP-/MEPS-värden | Öppet utan konto/kostnad; CC BY 4.0 enligt SMHI, kommersiellt tillåtet med attribution/ändringsangivelse. Fryst punktreferens importerad; ej regionalt rutnät |
| MET Norway Locationforecast, vind | Norden: MEPS 2.5 km/0–60 h, uppdatering varje timme; medium range ECMWF cirka 9 km/2–10 dygn, två gånger per dygn | Öppet CC BY 4.0/NLOD, identifierad UA/cachning, ingen SLA. Alternativ; inget ytterligare prognossvar hämtat |
| MET Norway Oceanforecast, vågor/ström | Nordvästeuropa. Regionala vågor 4 km/4 uppdateringar per dygn, kustmodell 800 m/2 per dygn där täckt. Vinga svaret flyttas till 11.5955°E 57.626°N; inte bevis för modellstöd i rutten. 208 timsteg, 12 okt 21Z–21 okt 12Z | Öppet CC BY 4.0/NLOD utan konto/kostnad. Svar har Hs, från-riktning och ström mot-riktning/fart, men **ingen vågperiod**, okänt strömdjup och ingen separat modellutfärdandetid. Fryst ofullständig referens, ingen regional extrapolation |
| Copernicus Baltic PHY/WAV | Vinga inom angiven region 9–30°E/53–66°N, cirka 1 nautisk mil/2 km. PHY har bl.a. 15-min surface currents och djupnivåer; WAV har timvis Hs/Tm02/riktning. 00Z-produktion upp till 10 dygn, WAV 12Z 6 dygn, publicering 10/22 UTC | Data är kostnadsfria. Nedladdning kräver inloggning enligt officiell åtkomstdokumentation. Inga konton skapas. Licenslänken gav 403; fullständiga återdistributions-/kommersiella villkor måste läsas före import, inget dataset hämtat |
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
inte att sprida närmaste punkt över området. MET:s dokumenterade THREDDS-länk
kunde inte läsas med webverktyget; rågridåtkomst är inte verifierad i leveransen.

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
