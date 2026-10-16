# Regional prognos: aktuell gapöversikt 2026-10-16

Detta är aktuell arbetsordning efter metadata-/transportgranskningen, inte ett
kvalificeringsbeslut. Äldre försöksresultat i forecast-blockers.md är historik.
RegionalForecastInputs har verklig fryst native vind och marina produkter;
inspect_regional_inputs ger fortfarande data_unavailable och inga kandidater.

## Prioriterade bevisgap

| Prioritet / gap | Verifierat underlag | Krävs före kvalificering |
| --- | --- | --- |
| 1 Vindgeometri | MET LCC-parametrar och native axlar; 42 nodrutor/168 rumtidsrutor; direkt lokal separerbarhet underkänd | Granskad representation för hela segment/celler, datumtransformation och konservativa felgränser; eventuell regridding enligt beviskontraktet |
| 1 Vindram | 10 m, 600 s medel och FRÅN-riktning granskade; konvergens varierar över uttaget | Källbunden sann/gridrelativ ram, tidsmedlets placering och verifierad konvertering/rotation före komponentinterpolation |
| 1 Vindstöd | Finita råvärden, fem tider och native adjacency verifierade | Källans mask-/missing-semantik och vald interpolation med hela stödet; landfraktion får inte ersätta giltighetsmask |
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

Push har misslyckats med Permission denied (publickey). CI-verktyget har gett
Unknown tool; CI för lokala nya commits är overifierad. Dessa leveranshinder
är inte prognosbevis och ändrar inga planning_blockers. Exakt commit/push/CI
hör till respektive delrapport; denna översikt hävdar ingen remoteleverans.

## Nästa oberoende tillåtna arbete

Granska kontraktet för djupgående/säkerhetsmarginal mot befintlig geografisk
API-/GPX-gräns: var visas okänt djup, vilka metadata krävs för kompatibla
vertikala datum och hur hålls båda ruttmålen blockerade vid otillräckligt
underlag? Förbered en begränsad offline acceptansmatris före eventuell kod.
Detta är en dokumenterad backlogdel och kvalificerar inga verkliga djupdata.
Ingen databas, ny källa eller publik demonstration behöver ändras.

Återuppta marin metadataåtkomst först när en konkret tillåten metod eller ny
källevidens finns. Geometri-/mask-/run-granskning kan fortsätta oberoende men
får inte ersättas med fler positiva punktprov eller antaganden.

## Underlag

- [Vindacceptans](regional-wind-acceptance.md), [gridbevis](forecast-regridding-proof.md)
- [MET-metadata](met-nordic-metadata-review.md), [vindram](met-wind-frame-review.md)
- [Marina körbegrepp](marine-run-source-review.md), [ARCO-bindning](arco-provenance-review.md)
- [Metadataåtkomst](copernicus-metadata-diagnostics.md), [run-kontrakt](forecast-run-provenance.md)
- [Backlog](backlog.md), [krav](requirements.md)
