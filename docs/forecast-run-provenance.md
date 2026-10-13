# Granskningskontrakt för prognoskörningars proveniens

Status 2026-10-13: design och acceptanskriterier, inte implementerad
certifiering. Befintliga planning_blockers kvarstår. Kontraktet förbereder
metadataarbete medan källåtkomst och push/CI är blockerade. Ingen ny adapter,
ny datatransport eller routingkvalificering införs.

## Begrepp och förtroendegräns

Modellens referenstid, publiceringstid, giltighetstid och hämttid lagras separat.
Ett CF-fält med forecast_reference_time får bara beskrivas som modellens
referenstid enligt dess dokumenterade betydelse. Det är inte automatiskt tiden
då produkten gjordes tillgänglig. ProductMetadata.issued_at behöver en uttrycklig,
källspecifik definition före framtida koppling; nuvarande okända värden fylls
inte i för att passera ForecastPolicy.

Run-identitet är källbunden: producent, modell/konfiguration, produkt, körning
(referenstid eller dokumenterat run-ID), ensemblemedlem där sådan finns samt
revision om källan kan ändra innehåll under samma run-ID. Samma klockslag mellan
olika modeller är inte samma körning eller bevis för förenlighet. Produktens
katalogversion identifierar inte en prognoskörning.

En framtida verifierare i infrastrukturlagret måste läsa granskade källfält och
kontrollera dem mot dokumenterad semantik. Payloadfält som verified=true,
manuellt inskriven issued_at eller en statusrapport är inte certifiering.
SHA-256 binder bevis till bytes men bevisar inte själv att ett fält är ett
äkta modellutfärdande. Ruttmotorn tar bara emot fryst normaliserat underlag;
SQL/HTTP, metadatahämtning och källspecifika tolkningar hör inte hemma där.

## Evidenspost för varje dynamisk produkt

Följande är ett föreslaget granskningsformat, inte ett accepterat importformat:

| Uppgift | Nödvändigt innehåll | Vid okänt värde |
| --- | --- | --- |
| Fryst uttag | Dataset-ID, version, del/service, variabler och originalmanifestets filhash | Ingen bindning till produkt; blockerad |
| Källartefakt | Publik metadataadress, lokalt metadatafilnamn, hash och hämttid; inga signerade URL:er eller credentials | Källfält inte granskningsbart; blockerad |
| Semantik | Exakt fält/attribut, enhet, kalender, råvärde och dokumenterad betydelse; dokumentationens version och lokal bevisreferens | Tid/run förblir okänd |
| Modellreferens | Dokumenterad referenstid med UTC-konvertering utan antagen tidszon | Okänd referenstid |
| Utfärdande | Dokumenterad publicerings-/utfärdandetid om tillgänglig, separat från referenstid | Okänd utfärdandetid; blockerad |
| Run-identitet | Producent/modell/konfiguration, källans run-ID och eventuell medlem/revision | Okänd körning; blockerad |
| Urvalsbindning | Verifierad koppling från uttagets varje giltighetstimme/variabel till originalkörning och revision | Okänd eller blandad proveniens; blockerad |
| Granskning | Verifierarversion, dokumentationsreferens, resultat och explicita felorsaker | Ingen godkänd proveniens |

Frånvaro redovisas med null och orsak, aldrig fabricerat datum eller tomt run-ID.
Transportförsök med DNS-/HTTP-fel redovisar misslyckad åtkomst; de får inte
redovisa att ett visst källfält saknas i en fil som inte har lästs.

Metadatafilens hash och originaluttagets hash har olika roller. En originallista
med namn, storlek, last_modified och etag binder inte automatiskt ARCO-värdena
till en originalfil. En koppling kräver dokumenterad urvalssemantik och faktisk
evidens för det granskade uttaget. Den får inte härledas enbart från filnamn,
samma giltighetstider, skapandetid eller katalogversion.

Om ARCO har ersatt äldre värden eller saknar historisk urvalsproveniens kan en
senare originallista inte retroaktivt intyga det tidigare uttaget. Resultatet
för befintliga fixtures blir då fortsatt okänt. Samma marina data hämtas inte
igen för att försöka skapa ett sådant bevis.

## Regional vind: MET Nordic-kandidat

Återanvänd metadata-probens fixerade forecast-endpoints och dess storleksbudget.
Dokumenterad kandidat och tidigare källgranskning finns i
[forecast-blockers.md](forecast-blockers.md); inga nya källfakta verifierades i
detta offlinearbete. Godkänd transport av DDS/DAS/ASCII är inte importgodkännande.

Före framtida vindimport krävs faktisk granskning av forecast kontra analysis,
modellreferens/run, giltighetstider, CF-tidsenheter/kalender, höjd, standard_name,
cell_methods, enheter och vindriktningens referens. CRS/projektion, koordinataxlar,
Vinga-täckning inklusive interpolationsstöd och saknade/maskerade värden måste
verifieras. Gridrelativa vektorer måste roteras med verifierad transformation
innan normalisering till sann öst/nord. Punktvind eller senaste analys får inte
spridas till en regional framtidsprognos.

Modellutfärdande och run-bindning är separata från dessa fältkontroller. Även en
korrekt vindvektor ger data_unavailable om nödvändiga metadata saknas.

## Befintligt marint uttag

Återanvänd [manifestet](../fixtures/vinga-copernicus/manifest.json) och
[referensen](../fixtures/vinga-copernicus/reference.json). Dynamiska produkter:
cmems_mod_bal_wav_anfc_PT1H-i (version 202311) och
cmems_mod_bal_phy_anfc_PT1H-i (version 202411), giltighet 12–16 UTC
2026-10-13. Båda issued_at är null. Static-vågmaskens identitet binds separat;
den är inte en tredje dynamisk prognoskörning och bevisar inte strömgridets mask.

Manifestets hashvärden och tidsstöd är redan verifierade offline. Dessa bevis
räcker inte till originalrun-bindning. Ingen identity/certification kopplas till
befintliga ProductMetadata i denna leverans.

## Förenlighetsregel före framtida implementation

En regel ska vara versionsbunden och avse en explicit produktuppsättning med
käll-/modellkonfigurationer. Den ska dokumentera vilka run-kombinationer som
accepteras, grunden för detta, tillåtna skillnader i referens-/utfärdandetid,
prognoshorisont och hur revisioner/ensemblemedlemmar hanteras. Numeriska
trösklar kan inte väljas från bekvämlighet; de kräver dokumenterad källkunskap
och maritim/metodmässig granskning. Ingen sådan tröskel är beslutad här.

Resultatet ska innehålla regelversion och bindning till varje produkt/evidenshash.
Ändrad produkt, hash, tid, run, revision eller regelversion kräver ny kontroll.
En ström/våg-kontroll får inte återanvändas som certifiering när vind läggs till.
Överlappande giltighetstider krävs för planens rum/tidstöd men räcker inte som
run-förenlighetsregel. Modellkoppling eller atmosfärisk drivning får inte antas.

Blandade körningar inom ett uttag avvisas i den första framtida implementationen.
Stöd för sådana uttag kräver separat dokumenterad regel per variabel/tid och
ska inte införas genom att välja ett representativt run-ID.

Även verifierad run-förenlighet häver bara dess egen blockerare. Okänd vind,
utfärdandetid, strömmask, routinggeometri, färskhet och datastöd prövas separat.

## Acceptans- och felmatris för framtida verifierare

| Fall | Förväntat resultat |
| --- | --- |
| Endast filnamnsdatum, mtime, creation_date, etag eller katalogversion | Okänd run/utfärdande; data_unavailable |
| Manuellt datum och payloadflag, även med lika giltighetstider | Ingen certifiering; data_unavailable |
| Källfält läst men fältbetydelse/enhet/kalender okänd | Ingen godkänd tidskonvertering; data_unavailable |
| Metadata från annan fil, region, variabel, revision eller uttagshash | Bindning avvisas; data_unavailable |
| Originallista utan bevisad historisk ARCO-urvalsbindning | Okänd uttagsproveniens; data_unavailable |
| Olika run per giltighetstimme eller variabel | Blandad körning; data_unavailable |
| Lika referenstid men skilda modeller och ingen granskad regel | Förenlighet okänd; data_unavailable |
| Vind läggs till efter godkänd ström/våg-kontroll | Ny kontroll av hela produktuppsättningen krävs |
| Alla run-bevis korrekta men vind/mask/geometri saknas | Övriga blockerare kvar; data_unavailable |
| Källan oåtkomlig | Åtkomstblockerare; inga slutsatser om innehållet |

Framtida positiva testfall ska ha oberoende referensresultat från granskad
källdokumentation och verkliga metadatafixtures. Syntetiska fall måste märkas
syntetiska och får bara verifiera kontraktets negativa/strukturella beteende.
Befintliga test_dates_and_payload_flags_do_not_certify_run_compatibility och
metadata-probens blockerartester förblir regressionsbevis för dagens avvisning.

## Utfärdandespärr i den befintliga marina adaptern

Granskning 2026-10-13 fann att detached issued_at kunde fylla ProductMetadata
och ta bort model_issue_time_unverified, trots att kompatibilitetsspärren höll
hela underlaget unroutbart. Detta motsvarade inte kontraktets förtroendegräns.
CopernicusMarineAdapter sätter nu issued_at=null och behåller båda spärrarna
oberoende av payloadens datum, run-ID, compatibility-flagga eller blockerlista.
Adaptern har ännu ingen accepterad källbunden utfärdandeverifierare; därför
finns ingen väg i detta importformat att kvalificera ett datum. Giltighetstider,
hämttid och katalogversion behåller sina separata roller och värden.

Negativa referenser prövar manuellt färskt datum, modellreferenslikt datum,
gammalt skapandedatum, ogiltig datumtext och null tillsammans med påstått
run-ID/status. Alla normaliseras med okänd utfärdandetid och båda spärrarna.
Befintligt test med tillagd syntetisk vind verifierar fortfarande att route-,
segment- och villkorskontroller avvisar run-förenlighet även utan färskhetspolicy.
Färskhetspolicy avvisar den saknade utfärdandetiden separat. Inga verkliga
prognosdatum fylls i och inget bevisformat eller ny adapter införs.

Avgångs-/exportregressionen prövar nu två avgångar och två kompletta rutter
med komfortpolicy, med/utan färskhetspolicy samt inget urval, kortast restid
och tidigast ankomst. Syntetisk testvind har separat märkt identitet utan
marina källhashar. Alla 24 kandidatbedömningar får data_unavailable med
både run- och utfärdandeorsak; tids-/komfortalternativ och globala urval
förblir null. Exporten behåller båda marina issued_at=null, planning_blockers
och faktisk uttagshash per produkt. Inga accepterade steg exporteras.
Detta verifierar avvisning genom befintlig motor/presentation, inte proveniens
eller väderkvalitet i det verkliga underlaget.
