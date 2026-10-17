# Regional prognos: aktuell gapöversikt 2026-10-17

Detta är aktuell arbetsordning efter metadata-/transportgranskningen, inte ett
kvalificeringsbeslut. Äldre försöksresultat i forecast-blockers.md är historik.
RegionalForecastInputs har verklig fryst native vind och marina produkter;
inspect_regional_inputs ger fortfarande data_unavailable och inga kandidater.

## Prioriterade bevisgap

| Prioritet / gap | Verifierat underlag | Krävs före kvalificering |
| --- | --- | --- |
| 1 Vindgeometri | MET LCC-parametrar och native axlar; rationellt helt-box-hölje och analytiskt diskhölje för lokalt affin bana på explicit källsfär | Källbunden WGS84-/datum-/serialiseringsfelgräns för verklig ruttbindning; eventuell regridding enligt beviskontraktet |
| 1 Vindram | 10 m, 600 s medel och FRÅN-riktning granskade; konvergens varierar över uttaget | Källbunden sann/gridrelativ ram, tidsmedlets placering och verifierad konvertering/rotation före komponentinterpolation |
| 1 Vindstöd | Fem tider och segmentbunden råinventering av alla tangerande serialiserade rumtidsrutor/hörn för matematisk källsfärsbana | Källans mask-/missing-semantik och vald interpolation med hela stödet; landfraktion får inte ersätta giltighetsmask |
| 2 Marin run och utfärdande | Befintliga subsethashar, variabler och giltighet; officiella analys-/leveransscheman | Källbunden run-identitet och faktisk utfärdandetid för varje produkt samt verifierbar bindning till redan sparade ARCO-bytes |
| 3 Gemensam run-förenlighet | Gemensamt giltighetsintervall kan beräknas | Dokumenterad, granskad regel för vind/vågor/ström och evidens för hela den frysta produktuppsättningen; lika giltighet eller cykel räcker inte |
| Separat strömstöd | Strömvärden och native koordinater granskade | Källbunden våt-/giltighetsmask för strömmens eget grid; vågmask får inte överföras |

Aktuella rapportkoder är wind_native_geometry_unqualified,
wind_vector_frame_unqualified, model_issue_time_unverified,
cross_product_model_run_compatibility_unverified och
current_native_wet_mask_unverified. Vindens mask-/interpolationsgap är separata
acceptanskrav, inte nya redan implementerade rapportkoder.
Avgång utanför gemensamt tidsstöd ger dessutom departure_outside_common_validity.
Gemensamt avgångsstöd bevisar inte stöd längs hela en framtida färd.

Den separata [native-segmentinventeringen](native-wind-segment-support.md)
har egna rapportlokala blockerare och ändrar inte regionalrapportens grindar.
Dess hela icke-linjära hölje kommer från utåtriktad rationell intervallräkning,
inte nod-/kantprov. raw_inventory_complete gäller bara den explicit angivna
källsfäriska banan och de serialiserade axlarna. Lokalt affin bana har nu ett
analytiskt helt-disk-hölje på samma sfär, med ursprungliga lokala meter i
rapportbindningen; detta är inte en transformation av befintliga WGS84-rutter.
physical_source_support_qualified
och local_route_geometry_binding_verified förblir false; okända fel är inte noll.

Inget datum får fyllas i från hämtningstid, creation_date, filmodifieringstid,
filnamn, katalogversion eller ett payloadflag. Vindens model_reference_time
är källäst men är inte issued_at. Marin model_reference_time, issued_at och
run_identity är fortfarande okända i regionalrapporten. Djup är unknown och
navigationssäkerhet not_assessed även om prognosgapen senare löses.

## Källåtkomst för ett sammanhängande Vinga-fall 2026-10-17

Officiella produktmanualer bekräftar användbara produktfakta men saknar
bindningen till de frysta ARCO-cellvärdena:

- WAV-manual, Issue 2.8 (2025-11): Baltic WAM 4.7, timvisa momentanvärden,
  två leveranser per dygn senast 10/22 UTC, nio dygns prognos. Första 66 timmarna
  drivs av MetCoOp-HARMONIE. WAM använder timström från BAL PHY.
- PHY-manual, Issue 1.3 (2025-11): två 00Z/12Z-produktionscykler, publicerade
  senast 10/22 UTC; körningen börjar 12Z föregående dag respektive 00Z samma dag.
  Första 66 timmarna använder MetCoOp-HARMONIE-kontrollmedlem och senare ECMWF.
- MET-fixturens faktiska `forecast_reference_time` är 2026-10-13 00Z och
  `source=meps`; `history=Created 00:26Z` har inte dokumenterad utfärdande-
  semantik. MET Nordic `meps` kan därför inte identifieras med WAM:s exakta
  SMHI MetCoOp-HARMONIE-medlem/körning.

Manualernas produktionsschema och modellkoppling är inte run-identitet för en
ARCO-fråga. I de frysta WAV-/PHY-filerna saknas CF
`forecast_reference_time`/`forecast_period`, `issued_at`, run-ID och revision.
Det enda frysta beviset är dataset/version/service, giltighetstider, hämtningstid
och filhash. WAV-fixturens variabler har dessutom `cell_methods="time: mean"`,
medan gällande WAV-manual anger timvisa momentanvärden; bounds saknas. Denna
skillnad mellan ARCO-fil och manual är olöst och hindrar tidsmässig segment-
interpolation. PHY `uo`/`vo` saknar fortfarande verifierad tidsstödsemantik och
egen våtmask.

En ny, separat Copernicus-provbegäran avgränsades till Vinga-boxen,
2026-10-17 00–04Z, två variabelgrupper och högst 2 MB per fil / 5 MB överföring
med den befintliga Toolbox/autentiseringen. Katalogen svarade med samma WAV
202311 och PHY 202411-versioner. Felsökning 2026-10-17 reproducerade
anropet med Toolbox 2.5.0: själva WAV `dry_run` lyckas. Därefter kastar provets
egen budgetkontroll `ValueError("probe exceeds 2 MB file / 5 MB transfer cap")`.
Estimatet är 0,013297709923664122 MB fil och 40,67862595419847 MB överföring;
överföringen överskrider 5 MB-gränsen. Stegmarkören stod fortfarande på
`dry_run:waves` vid kontrollen och identifierade därför inte kaststället.
Det ursprungliga felmeddelandet sparades inte; samma anrop och efterkontroll
har nu reproducerat detta fel med privat traceback. Ingen väderfil hämtades
under reproduktionen och budgeten är oförändrad. Därför finns inget nytt uttag
eller nytt vädervärde från denna provbegäran att redovisa. En begränsad ARCO-subset skulle inte på
egen hand binda svaret till originalrun; ordinarie `get` hämtar hela WAV-
originalfilen (110 MB komprimerad enligt WAV-manualen) och överskrider den
avgränsade uttagsbudgeten. Äldre fixturer återanvänds.

Kvarvarande exakta fält och praktisk väg framåt:

1. WAV och PHY behöver källbunden modellreferens/run-ID, faktisk produktens
   publicerings-/utfärdandetid samt revision för just de valda variablerna och
   giltigheterna. Begär en per-run export/metadatafil från Copernicus som binder
   ARCO-subsethashen eller liten subset till originalkörning, alternativt ett
   källformat där run-koordinaten följer varje urval.
2. WAV behöver en källa som förenar faktiskt `cell_methods="time: mean"` med
   manualens “instantaneous”, inklusive tidsbounds/medelfönster. PHY behöver
   tidsstöd och wet/validity mask på strömmens eget native grid.
3. MET-vind behöver dokumenterad issued/published time och en källbunden
   identifikation av `meps`-körning. Run-tidarnas lika/täta värden räcker inte
   för att hävda kompatibilitet med WAM/PHY.

Ingen run-, utfärdande-, mask- eller kompatibilitetsspärr har hävts. Det finns
därför inget kvalificerat sammanhängande verkligt Vinga-fall och ingen
ruttberäkning med blandade vind-/marinbytes har körts. Befintlig MET-segment-
diagnostik och marina frysta fält förblir separata diagnostiska fixtures.

Primärkällor: [WAV PUM Issue 2.8 (2025-11)](https://documentation.marine.copernicus.eu/PUM/CMEMS-BAL-PUM-003-010.pdf),
[PHY/BGC PUM Issue 1.3 (2025-11)](https://documentation.marine.copernicus.eu/PUM/CMEMS-BAL-PUM-003-006-007.pdf),
[frysta MET-metadatadokument](met-nordic-metadata-review.md) och
[Copernicus ARCO-proveniensgranskning](arco-provenance-review.md).

## Åtkomst och leverans är andra slags hinder

Saved-auth och metadata-only fillistor lyckades 2026-10-16 08:26–08:28 UTC.
Tidigare auth-timeout är alltså inte aktuell blockerare. Fillistor identifierar
originalkandidater, storlek/mtime/ETag; de binder inte historiska ARCO-värden
till en run. Ingen verifierad transportmetod garanterar ännu originalens
NetCDF-metadata utan väderbytes. HEAD returnerar inte dessa attribut, och
lokala HDF5-läsfönster ger ingen garanti för originalens layout.
Hämta inte samma marina data igen. Återanvänd fixtures/vinga-copernicus och
dess verifierade hashvärden; skapa ingen parallell adapter.

Tidigare SSH-/CI-hinder är historik. Senast levererade 6e9a1b6 är pushad med
grön exakt CI 38957365522. Befintlig SSH-agent behöver vara tillgänglig för
projektets redan laddade nyckel; inga nya nycklar behövdes. Lokal TCP-bindning
nekas i den hanterade miljön; frontendens API-integration passerade ordinarie CI.
Leveranskontroller ändrar inga prognosblockerare. Nya commits verifieras separat.

## Nästa oberoende tillåtna arbete

Användarens aktuella prioritet är geometri/källstöd efter den levererade
separata [grafiska Vinga-granskningen](vinga-frozen-review.md). Helt-hölje för
en lokalt affin bana finns nu på den uttryckliga källsfären, fortfarande skild
från verklig WGS84-/lokal ruttbindning. Nästa del behöver konkreta avgränsade
källmetadata-/proveniensförsök med befintliga källor, utan nya uttag av samma
marina data. Källbunden datum-/serialiseringsevidens, mask och interpolation får aldrig
ersättas med en flagga eller små punktresidualer. Djupacceptansen kvarstår
separat; den utvidgar inte detta funktionssteg.

Återuppta marin metadataåtkomst först när en konkret tillåten metod eller ny
källevidens finns. Geometri-/mask-/run-granskning kan fortsätta oberoende men
får inte ersättas med fler positiva punktprov eller antaganden.

## Underlag

- [Vindacceptans](regional-wind-acceptance.md), [gridbevis](forecast-regridding-proof.md)
- [MET-metadata](met-nordic-metadata-review.md), [vindram](met-wind-frame-review.md)
- [Marina körbegrepp](marine-run-source-review.md), [ARCO-bindning](arco-provenance-review.md)
- [Metadataåtkomst](copernicus-metadata-diagnostics.md), [run-kontrakt](forecast-run-provenance.md)
- [Backlog](backlog.md), [krav](requirements.md)


## Uppföljning: regional budget och lyckat WAV-uttag 2026-10-17

Användarens utökade mandat ersätter ovanstående felsökningsbudget med
konfigurerbara GB-budgetar. [Hämtningsbudgetar och cache](copernicus-download-budgets.md)
beskriver implementation, avgränsning och verifiering. Samma WAV-urval 00–04 UTC
hämtades nu: 26 114 byte, cirka 42,6 MB uppskattad överföring. En identisk
begäran återanvände verifierad cache utan ny väderhämtning. Den tidigare
budgetblockeringen gäller därför inte det nya mandatet.

Filen saknar fortsatt run-ID/modellreferens, issued_at, revision och tidsbounds;
alla tre vågvariabler anger time: mean. Käll-/tidsstödsblockerarna och samtliga
planeringsspärrar kvarstår. Den nya filen ersätter inte befintliga frysta
planeringsfixtures och ger inget kvalificerat blandat Vinga-fall.
