# Större fryst prognosunderlag vid Vinga, 2026-10-17

Nästa avgränsade dataleverans finns i
[fixtures/vinga-expanded-20261017](../fixtures/vinga-expanded-20261017/manifest.json).
Den ersätter inte det fungerande historiska standardfallet från 13 oktober.
[Offlinegranskningen](../artifacts/expanded-forecast-support/report.json) är
reproducerbar utan nätverk och använder befintliga MET-läsare/interpolation
samt separata native-gridinventeringar. Ingen andra ruttadapter är skapad.

| Produkt | Nytt fryst underlag | Vad som är kontrollerat |
| --- | --- | --- |
| MET-vind | 132 native-noder × 12 timnoder, 17 oktober 01–12 UTC | Befintliga strikta DDS/DAS-fält, LCC-geometri, native axlar, lat/lon-bindning, källäst modellreferens 00 UTC, fullständiga finita råvärden och ordning |
| WAV | 4×4 native-noder × samma 12 timnoder | Exakta värden/tidskoordinater från redan hämtad originalfil; tre granskade variabler, nio värdekompletta nativeceller över hela koordinatfönstret |
| PHY | 4×4 egna native-noder × samma 12 timnoder | uo/vo, en källäst modellnivå på 0,5016462206840515 m, nio värdekompletta nativeceller över hela koordinatfönstret |
| Vågmask | 4×4 native-noder | Exakt koordinatmatchning med WAV och binära värden; alla 16 noder är märkta hav i denna mask |

Det är **tolv timnoder och ett koordinatspann på elva timmar**, jämfört med
fem timnoder/fyra timmar i standardfallet. Nio nativeceller per marin produkt
jämförs med en i standardfallet. Begärt marint område var 11,55–11,66°E,
57,60–57,67°N; faktiskt native stöd är snävare och redovisas med fulla axlar i
rapporten. Ström- och vågaxlar skiljer sig; vågmasken överförs aldrig till ström.
MET:s landfraktion är inte en vindgiltighetsmask. Vinduppslag vid de marina
noderna är diagnostiska punktkontroller, inte bevis för hela segment/områden.

## Åtkomst, återanvändning och budget

WAV-originalets redan verifierade cachehash är
`de195d6a8ecdc9b02621c838cb0afd87adb85f0c241a066f9aa8b4703e856401`.
Originalet på 113 263 050 byte hämtades **inte igen**. En lokal native-subset
med enbart VHM0/VTM02/VMDR gav 36 890 byte, utan interpolation, omdatering eller
nya marina överföringar. Parentmanifest och härledningsmanifest följer med;
originalets oförändrade producenttidskoordinater får ingen antagen ARCO-offset.

Separat dry-run före ny hämtning uppskattade:

- PHY: 113 387 904 överföringsbyte, 15 328 resultatbyte.
- Vågmask: 4 736 800 överföringsbyte, 13 768 resultatbyte.
- Summa uppskattad ny marin överföring: **118 124 704 byte**.

Faktiska resultatfiler blev 27 546 respektive 17 928 byte. MET:s sex begränsade
svar omfattade totalt 88 399 byte. Överföring är en Toolbox-uppskattning, inte
en uppmätt nätverksräknare. Resultatstorlek och överföring är separata mått.

Före uttaget fanns cirka 2,0 GB ledigt på /tmp och 72 GB på /home-volymen.
Befintliga budgetar 10 GB per överföring, 20 GB totalt och 1 GB diskreserv
behölls. Resultatfilbudgeten begränsades till 0,05 GB. Hämtaren återanvänder
befintlig låst cache och hashmanifest; inga identiska marina subset upprepades.
Tidsgränsen för den nya marina hämtningen var 240 s; faktisk körning 33 s.
Ingen installation, betald resurs, databasoperation eller publicering ingick.

Första estimatet stoppades av TypeError: den faktiska PHY-katalogen hade en
explicit nedåtgående lista med djupnivåer, utan `minimum_value`. Hämtaren läser
nu listan, avvisar ogiltiga/motstridiga axlar och kontrollerar att ytintervallet
inte omfattar flera nivåer. Nivån kommer från katalogen, inte från ett antagande.
Det rättade estimatet utfördes före väderhämtning. `--estimate-only` kan nu
användas utan att ladda ned eller kopiera väderfiler.

## Kvarvarande hinder före större routing

**Ingen höjning av 900 m-taket är gjord.** Inga nya data används som standard i
API eller karta. De stora marina griden avvisas av befintlig adapters 1 m-gräns
för en representation med räta lokala öst-/nordaxlar. Toleransen har inte höjts.
Större routing kräver en verifierad geometrirepresentation i befintlig adapter,
hela segmentens rumtids-/interpolationsstöd och motsvarande större landunderlag.

`source_qualification=unverified`, okända utfärdandetider och run-förenlighet
bevaras. Original-WAV saknar ARCO-fixturens `time: mean`-attribut; tidskoordinater
med samma etiketter certifierar inte samma fysiska tidsstöd. Rapporten kallar
överlappet `common_coordinate_window`, med `temporal_support_qualified=false`.
`full_space_time_support_verified=false` och `routing_enabled=false` gäller.
Granskningen är diagnostic_only och tillämpar inga utvecklingsantaganden.
Det befintliga routingsvaret behåller conditional_on_assumptions och separata
assumed_fields. Modelltid, hämtningstid och antagen utfärdandetid blandas inte.

Vågmaskens havsvärden är inget navigerbarhets- eller djupbevis. Strömmens egen
mask, vindens giltighetsmask/medelfönster och källbunden run-/utfärdandeevidens
återstår. Större landunderlag och lokala projektions-/geometrigränser måste
verifieras innan området kan användas för nya rutter. Uppskattad båt och ej
validerat komfortmått påverkas inte av denna dataleverans.

## Offlinekontroll

```bash
.venv/bin/python -B -m scripts.inspect_expanded_forecast --output artifacts/expanded-forecast-support/report.json
```

`extract_cached_wave` och `capture_met_window` är transport-/subsetverktyg,
inte ruttadaptrar. Extraktion fångar och hashkontrollerar originalets bytes före
läsning; befintliga snapshots får inte hämtas på nytt. MET-läsaren har explicita
begränsade dimensioner och en uttrycklig förväntad modellreferens för det nya
arkivfallet. Standardens strikta referenspin till 13 oktober är kvar; den nya
fixturen avvisas om läsaren anropas med standardpinnen.
