# WAV-original jämfört med ARCO 2026-10-17

Utgångspunkt: 3e40452. Den fungerande Toolbox 2.5.0-hämtningen och dess
budget-/cachehjälpare återanvändes. Ingen ny subset gjordes; ARCO-filen från
föregående leverans behölls byte för byte. Fullständigt maskinläsbart,
hemlighetsfritt [jämförelseunderlag](evidence/wav-original-arco-20261017.json)
är versionshanterat. Detta är diagnostik, inte kvalificerat planeringsunderlag.

## Hämtat original och källmetadata

Vald fil: `BAL-WAM_WAV2026101700.nc`, dataset
`cmems_mod_bal_wav_anfc_PT1H-i`, version `202311`, part `default`.
Aktuell fillista granskades för 16–17 oktober, därefter exakt en match via
Toolbox get med `filter='*/BAL-WAM_WAV2026101700.nc'`, först dry_run och sedan
get. get hämtar producentfilen hel; det gör inget område-/variabelsubset.

- Objekt: `s3://mdl-native-11/native/BALTICSEA_ANALYSISFORECAST_WAV_003_010/cmems_mod_bal_wav_anfc_PT1H-i_202311/2026/10/BAL-WAM_WAV2026101700.nc`.
- Objektstorlek och faktisk lokal fil: **113 263 050 byte**.
- ETag: `"b191864c0fe788aa5e14f5188a8cb56d-14"`.
- Objektets `last_modified_datetime`: **2026-10-17T08:02:01.166000+00:00**.
- Lokal SHA-256: `de195d6a8ecdc9b02621c838cb0afd87adb85f0c241a066f9aa8b4703e856401`.
- Hämtad: **2026-10-17T10:18:49.350172+00:00**.

Det multipart-formade ETag-värdet är objektmetadata, inte en verifierad lokal
SHA-256 eller ett modell-run-ID. Förhandskontroll och get-svar hade samma
objektmetadata och lokal filstorlek kontrollerades; ingen kryptografisk
jämförelse mot ett separat producentpublicerat innehållschecksum finns.

Budgetar: 2 GB fil, 10 GB överföring per begäran, 20 GB per körning och 1 GB
fri diskreserv, i decimal GB. För originalet är både filstorlek och uppskattad
objektöverföring 113 263 050 byte, före protokoll-/metadata-/retry-overhead.
Fri disk kontrollerades före hämtning och kopiering. Ingen budgethöjning behövdes.
Toolbox get:s storleksfält omräknas från bytes/1024²; de har annan intern
konvertering än de tidigare granskade subset-estimatorerna.

Källkatalog, avgränsad CSV-fillista, ursprungliga get-förhandsmetadata, privat
fetchlogg/traceback, originalfil och manifest finns i den privata katalogen
`/tmp/seaparser-wav-original-20261017`. Originalets cachepost ligger i samma
hashkontrollerade cache som subset-posterna, men med separat identitet som
inkluderar originalobjekt, ETag, storlek och ändringstid. Postens hash och
storlek verifierades offline efter hämtningen. Samma oförändrade originalobjekt
kan återanvändas utan väderhämtning; ändrat ETag/ändringstid ger ny identitet.
Ingen andra originalhämtning användes för att testa cachen.

## Run, referenstid, publicering och tidssemantik

Originalet har 12 × 775 × 764 noder och 22 variabler inklusive koordinater.
Tidsaxeln är heltalssekunder sedan 1970-01-01, `calendar=standard`, timvisa
värden **2026-10-17 01–12 UTC**. Namnets `00` sammanfaller alltså inte med
första giltigheten och får inte tolkas som bevis för en 00Z-modellkörning.

| Uppgift | Original | Befintligt ARCO-uttag |
|---|---|---|
| Source | FMI-WAM_CMEMS | FMI-WAM_CMEMS |
| Run-ID/revision | saknas | saknas |
| forecast_reference_time / forecast_period | saknas | saknas |
| issued_at / faktisk publicering | saknas | saknas |
| creation_date | `2026-10-17 05:06:46`, ingen angiven tidszon | saknas |
| Tidstämpelintervall | 01–12 UTC | 00–04 UTC |
| cell_methods för VHM0/VTM02/VMDR | saknas | `time: mean` |
| Tidsbounds | saknas | saknas |

`creation_date` är ett attribut i originalet, men det anger inte sin tidszon
eller dokumenterad betydelse som publicering/utfärdande. Objektets ändringstid
är en separat lagringstid. Varken den, filnamnet, hämtningstiden eller det
generella 10/22 UTC-schemat får fylla i modellreferens eller faktisk issued_at.

[WAV PUM Issue 2.8](https://documentation.marine.copernicus.eu/PUM/CMEMS-BAL-PUM-003-010.pdf),
§II.4.3, beskriver timvisa momentanvärden. Originalets CF-1.0-deklaration och
avsaknad av cell_methods är förenliga med detta för intensiva variabler:
[CF-1.0 §7.3](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.0/build/ch07s03.html)
beskriver momentanvärde som standardtolkning när mean inte anges. Det är stöd
för originalets generella punktsemantik, inte bevis för att ARCO:s uttryckliga
mean-attribut kan ignoreras eller för att tidsinterpolation är kvalificerad.

## Exakt numerisk jämförelse och dess gräns

ARCO SHA-256: `9030a4d3cb945410e3ec7d69018886e43f859d3696e973360eea96b4b65bf279`.
Dess 2 × 2 punkter återfanns exakt i originalets koordinater: latitudindex
277/278 och longitudindex 93/94 (nollbaserade). Ingen närmaste-punkt-sökning,
interpolation eller omprojektion användes.

Vid **samma giltighetstid 01–04 UTC** är samtliga **48 float32-värden** exakt
lika: 16 vardera för VHM0, VTM02 och VMDR. Största absoluta differens är noll
för alla tre. Ingen fill/NaN användes som en match. **00 UTC finns inte i detta
original** och har därför inte verifierats mot original vid samma tid.

En separat hypotes jämförde ARCO 00–04 med original 01–05 (originaltid =
ARCO-tid + 3600 s). **0 av 60 värden** var exakt lika. Största absoluta
skillnader var 0,055827945470809937 m för VHM0, 0,1443333625793457 s för VTM02
och 18,36383056640625 grader för VMDR. Riktningens differens här är en rå
absolut jämförelse, inte ett särskilt cirkulärt felmått.

[Copernicus generella ARCO-beskrivning](https://help.marine.copernicus.eu/en/articles/8656000-differences-between-original-producer-files-and-arco-data)
förklarar att aggregerade intervall kan tidsnormaliseras. Våra observationer
ger däremot inget stöd för att tillämpa en generell entimmesförskjutning här.

Verifierat: innehållshashar, exakt gridbindning och likhet mellan de två lokala
snapshotens 48 jämförbara värden vid samma tid. **Inte verifierat:** att just
detta originalobjekt/run/revision var ARCO:s källa. Identiska värden kan återstå
genom ompublicering/revision och innehåller ingen leverantörsatt lineage.
ARCO-timmen 00 är dessutom utanför originalets tidsaxel. Även en ytterligare
fil som täcker 00 skulle inte i sig lösa saknat run-ID eller publiceringstid;
ingen extra sådan fil eller nytt subset hämtades enbart för fler likhetsprov.

## Exakta frågor till Copernicus / Baltic MFC (FMI)

Detta är ett förberett frågeunderlag; ingen supportkontakt har skickats.

1. Vilket stabilt modell-run-ID, vilken modellreferenstid (UTC), revision och
   analys-/prognosstatus gäller för just originalobjektet ovan med angivet ETag?
   Är filnamnets datum/timmar en giltighetspartition, en körreferens eller något
   annat, och kan en sådan fil innehålla data från flera körningar?
2. Vad betyder originalets `creation_date=2026-10-17 05:06:46`, vilken tidszon
   har det, och var finns faktisk producentutfärdandetid och första publicering
   för originalet respektive ARCO-versionen? Förklara relationen till
   objektändringen 08:02:01.166 UTC och hur ompubliceringar identifieras.
3. Varför har ARCO VHM0/VTM02/VMDR `cell_methods="time: mean"` när originalet
   saknar det och PUM anger momentanvärden? Är mean ett felaktigt tillagt
   metadataattribut eller har värden faktiskt medelbildats? Om mean är korrekt:
   ange exakta fönster/bounds, tidstämpelns position och transformationen.
4. Ge en källbunden historisk lineage per variabel/giltighet som länkar
   ARCO-snapshotens hash/urval och hämtningstid i evidensfilen till producentens
   run/revision och originalobjektens ETag/checksum. Förklara särskilt ursprunget
   för ARCO 2026-10-17 00 UTC, som inte finns i det granskade originalet.
5. Vilka tids-/interpolationsregler är giltiga för dessa momentana eller
   medelbildade vågparametrar, och vilka exakta atmosfärs-/PHY-körningar och
   revisioner drev WAM-körningen? Generell modellkoppling räcker inte för att
   verifiera förenlighet med vårt frysta MET-/PHY-underlag.

Alla befintliga run-, utfärdande-, mask-, kompatibilitets- och planeringsspärrar
kvarstår. Originalfilen ändrar inte frysta planeringsfixtures eller routing.

## Reproduktion utan ny subset

```bash
python -B -m scripts.download_copernicus_original \
  --filename BAL-WAM_WAV2026101700.nc --output /tmp/wav-original-review
python -B -m scripts.compare_wave_original \
  --original /tmp/wav-original-review/BAL-WAM_WAV2026101700.nc \
  --arco /tmp/seaparser-wav-regional-20261017/waves.nc \
  --output /tmp/wav-comparison.json
```

Hämtaren läser aktuell objektmetadata, återanvänder verifierad cache när objektet
är oförändrat och avvisar flera träffar, budget-/disköverskridande samt ändrad
objektmetadata mellan förhandskontroll och get-svar. Rå klientfelmeddelanden
visas inte. För offlinejämförelse används redan hämtade filer direkt.
