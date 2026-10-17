# Backlog och nästa sammanhängande leverans

Aktuell gapöversikt 2026-10-16: [forecast-gap-status.md](forecast-gap-status.md).
Den skiljer kvarvarande källbevis från åtkomst- och leveransproblem.

Prioriteringen bygger på requirements.md, architecture.md, decisions.md och
kvarstående begränsningar i prototype/README.md. Historiska nästa-steg i
progress.md är arbetslogg, inte en aktuell komplett backlog.

| Del | Status | Avgränsning / acceptans |
| --- | --- | --- |
| Frysta prognoser och separata produktmetadata | Klar, CI godkänd på 0fd50948 | Syntetiska fixtures och komponentinterpolation, inga verkliga källor |
| Kontinuerligt datastöd över integrerade segment | Klar, CI godkänd på 8453a14 | Avvisa passerade masker, saknade interpolationsstöd och rum/tid utanför täckning; små luckor ska inte kunna hoppas över |
| Reproducerbart syntetiskt planeringsscenario | Klar, CI godkänd på ef9f261 | Offlinekommando med fryst dataset, båtmodell, parametrar och spårbar resultatidentitet; körbar referens för framtida integration |
| Kontinuerliga hårda vädergränser | Klar, CI godkänd på 5d3d710 | Konservativa cellhöljen för markvind/Hs; osäkert bevis får inte godkännas |
| HTML-granskningsvisning | Klar, CI godkänd på dacfaaf | Fem syntetiska scenarier, separerad presentation, exakt JSON-export; ingen editor vald |
| Automatisk polygonomväg i lokalt plan | Klar, CI godkänd på 3573814 | Exakta segment-/marginalpredikat och begränsad graf; kompletta tidsberoende kandidater |
| Geografiska koordinater, API och kartvisning | Implementerad teknisk demo, verifieras i leveransen | WGS84 AEQD, tunt API med separata processer, Leaflet-klick och GeoJSON; syntetisk bakgrund/hinder |
| Export av planerade vägpunkter | Implementerad GPX 1.1-demonstration | Planerade rtept, ordning/lat/lon och roundtrip testas; verklig plotterimport återstår |
| Verkliga kart-/hinder-/prognoskällor | Vinga-land/bakgrund och gemensam ruttjämförelse med verklig MET/WAV/PHY som standard, villkorad av konfigurerade utvecklingsantaganden; källkvalificering är separat | Fryst ODbL-land, konservativa routinghöljen och opt-in OSM raster; okänt djup/fullständighet. Utvecklingsrutterna skiljer verifierade källuppgifter från antaganden, utan att ersätta saknade/ogiltiga fältvärden. Kvar: vindgiltighetsmask, averaging-fönstrets placering, utfärdandetid och förenlighet med marina prognoskörningar. Befintliga marina spärrar kvarstår. Ingen publik ändring |
| Fler kandidater/avgångar med verkliga data | Implementerad avgränsad utvecklingsutökning | Uppmätt offline 2/4/8 × fyra avgångar; interaktivt högst 16 kombinationer, kalla workerprov, grafisk restid/exponeringsjämförelse. Samma vinnare redovisas. Se development-real-routing.md. Kvar: större faktiskt gemensamt område/tidsstöd med egna grid och landunderlag före höjt 900 m-tak |
| Större prognosområde och tidsstöd | Större fryst källunderlag levererat diagnostiskt | MET 132 noder, WAV/PHY egna 4×4-grid, tolv timnoder 17 okt 01–12 UTC; cacheåteranvänd WAV, budgeterad ny PHY/mask/MET. Routingområde oförändrat: 900 m. Native-representation i befintlig adapter nu verifierad som komponent för marin 2 km-disk; nytt 1,5 km-landunderlag med 24 höljen blockerar gamla starten. Kvar: tillåtna ändpunkter, begränsad kandidatsökning och samlat vind-/marin-/landstöd före större routing. Se native-marine-geometry.md |
| Djupgående och säkerhetsmarginal | [Offline acceptanskontrakt](depth-acceptance.md), implementation återstår | Explicit okänt djup; kompatibla vertikala datum krävs för tidvatten/djup |
| Tidvatten och stationsström | Adapter-/region-/licensbeslut återstår | Separata vattenståndsdatum och strömriktning/djup; ingen områdesextrapolation utan verifierad modell |
| Fler spårbara båtprofiler och manövrer | Beslut behövs före verkliga profiler | Polarrättigheter, representativa båtar och manövermodell; automatisk kryss ingår inte i nuvarande prototyp |
| Mobil presentation och visuell editor | Utvärdering återstår | Egna komponenter, responsivitet, versionshantering, export, licens och kostnad före bindande val |
| Konton, kvoter och prenumerationer | Senare, produktbeslut behövs | Definition av planuppdatering/kvotperiod, skydd av användardata och användarvillkor |
| AIS/trafikbelastningsinformation | Lågprioriterad extrafunktion, design endast | Observerat antal/historiska mönster med passagetid, dagsljus, sikt, väder, datatid och osäkerhet; aktuell bild är inte framtidsprognos. Ingen GPS/CPA/kollisionsvarning/övervakning/undanmanöver |

Arbetet ovan innebär ingen drift/publicering, merge till main, serverkonfiguration
eller ändring av befintliga databasobjekt. Synliga resultat från syntetiska
scenarier är inte navigationsunderlag. Uppdatera tabellen när en del har verifierats.

Huvudprioritet är geografisk routing runt hinder tillsammans med väderrouting,
ström, polar, komfort och avgångstider. AIS och presentationspolering kommer senare.
Planeringsflödet är kartgranskning och waypointöverföring till plotter utan GPS.
Metod, sökbegränsningar och nästa kontrakt: [geographic-routing.md](geographic-routing.md).
AIS-kontrakt/ersatt testplan: [traffic-planning.md](traffic-planning.md).
OpenWaters produktspecifika kandidatgranskning: [openwaters-review.md](openwaters-review.md).
Inga konton, token eller betalda tjänster skapas innan särskilt beslut.

Aktuell källgranskning och datagränser: [forecast-sources.md](forecast-sources.md).

Run-proveniens: [granskningskontrakt](forecast-run-provenance.md) dokumenterat offline. Källbunden evidens, historisk ARCO-bindning och förenlighetsregel återstår; designen certifierar inga befintliga prognoser.

Officiella marina [körbegrepp](marine-run-source-review.md) granskade 2026-10-16:
analyscykel, modelltid, leveransschema och överskrivning hålls separata.
Faktisk utfärdandetid och historisk ARCO-bindning är fortsatt okända.

Officiell [ARCO-granskning](arco-provenance-review.md) 2026-10-16 bekräftar
harmonisering och möjlig fördröjning mellan originalfiler och ARCO.
Dagens fillistor ger fortsatt ingen verifierad historisk urvalsbindning.

Regional vind: [acceptanskontrakt för grid/stöd](regional-wind-acceptance.md) klart som design. Native projektion/rotation, masksemantik och eventuell regridding måste verifieras före implementation; befintliga syntetiska tester kvalificerar inte MET.

Gridomvandling: [beviskontrakt](forecast-regridding-proof.md) och exakta negativa referensfall dokumenterade. Metod, toleranser och implementation återstår; ingen verklig prognos kvalificerad.

Gridomvandlingens två minimala motexempel är nu körbara mot befintlig
segmentcertifiering: källans topp/mask avvisas trots att glesare målfält
certifieras. Detta kvalificerar ingen verklig omvandlingsmetod.

Regional vind: begränsad faktisk MET-native råsubset (56 noder, fem timmar)
fryst och verifierbar offline. `met_wind_segments.py` transformerar Vinga-lokal
ruttgeometri till native LCC, interpolerar markrelativa E/N-komponenter och
beräknar konservativa gränser för ett helt segment. `within_interpolation_model`
är en diagnostisk modellgräns, inte godkänd väder- eller ruttkvalitet. Mask,
tidsmedlets exakta placering, issued_at och run-förenlighet kvarstår. Se
`docs/native-met-wind-segments.md` och `met-nordic-metadata-review.md`.

## 2026-10-17: fryst MET-vind på Vinga-segment

Ett nytt offlineprov binder den befintliga MET-råfixturen till ett uttryckligt
Vinga-lokalt segment. LCC-koordinaterna valideras mot den oberoende analytiska
referensen och de 56 frysta leverantörsnoderna; rapporten redovisar 1 m
konservativt stödsmarginal mot uppmätt maxavvikelse 0,2491 m. MET:s FROM-bäring
omvandlas till verkliga öst/nord-komponenter, interpoleras vektorvis i rum/tid,
och vindgränsen över hela segmentet får endast godkänt modellresultat när
hörnens konvexa hölje ryms under gränsen. En punkt över gränsen ger bevisat
överskridande; ett högt hörn utanför banan ger otillräckligt underlag.

Reproducerbart exempel: `fixtures/vinga-met-wind-segment.json` och
`artifacts/native-met-wind-segment/report.json`. Testgränsen 10 m/s avvisas av
fryst faktisk vind (~13,1 m/s vid segmentmitt); 18 m/s ligger inom denna
interpolationsmodells omslutning. Båda resultaten är diagnostic-only eftersom
utfärdandetid, källans vindmask, 10-minutersmedlets placering och förenlighet
med marina körningar inte är verifierade. Varken polar, ström, vågor, land- eller
djupbedömning används. Därför tillkommer ingen planeringskandidat och ingen
publik ändring.
