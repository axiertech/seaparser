# Regional prognos: aktuell gapöversikt 2026-10-16

Detta är aktuell arbetsordning efter metadata-/transportgranskningen, inte ett
kvalificeringsbeslut. Äldre försöksresultat i forecast-blockers.md är historik.
RegionalForecastInputs har verklig fryst native vind och marina produkter;
inspect_regional_inputs ger fortfarande data_unavailable och inga kandidater.

## Prioriterade bevisgap

| Prioritet / gap | Verifierat underlag | Krävs före kvalificering |
| --- | --- | --- |
| 1 Vindgeometri | MET LCC-parametrar och native axlar; rationellt helt-box-hölje för explicit källsfärisk bana; direkt lokal separerbarhet underkänd | HELA den lokalt affina ruttens transformationshölje, källbunden datum-/serialiseringsfelgräns; eventuell regridding enligt beviskontraktet |
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
källsfäriska banan och de serialiserade axlarna. physical_source_support_qualified
och local_route_geometry_binding_verified förblir false; okända fel är inte noll.

Inget datum får fyllas i från hämtningstid, creation_date, filmodifieringstid,
filnamn, katalogversion eller ett payloadflag. Vindens model_reference_time
är källäst men är inte issued_at. Marin model_reference_time, issued_at och
run_identity är fortfarande okända i regionalrapporten. Djup är unknown och
navigationssäkerhet not_assessed även om prognosgapen senare löses.

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
separata [grafiska Vinga-granskningen](vinga-frozen-review.md). Nästa steg är
ett konservativt helt-hölje för en lokalt affin bana, med tydlig skillnad
mellan en matematiskt deklarerad källsfär och ruttens WGS84-/lokala ram.
Källbunden datum-/serialiseringsevidens, mask och interpolation får aldrig
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
