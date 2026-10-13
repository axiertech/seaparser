# Backlog och nästa sammanhängande leverans

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
| Verkliga kart-/hinder-/prognoskällor | Vinga-land/bakgrund och regional syntetisk väderplanering implementerade för granskning | Fryst ODbL-land, konservativa routinghöljen och opt-in OSM raster; okänt djup/fullständighet. Regionalt fryst syntetiskt väder/API/karta/GPX; SMHI/MET punktreferenser och offlineadaptrar granskade; verklig regional routing avvisas tills native maskat grid/Tm02/utfärdande finns. Befintligt Copernicus-bundle och gemensam adapter verifierade offline; explicit planeringsspärr för okänd utfärdandetid/run-förenlighet. Regional vind, marin run-proveniens och strömmask återstår. Ingen publik ändring |
| Djupgående och säkerhetsmarginal | Planerad, före djupbaserad navigerbarhet | Explicit okänt djup; kompatibla vertikala datum krävs för tidvatten/djup |
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

Regional vind: [acceptanskontrakt för grid/stöd](regional-wind-acceptance.md) klart som design. Native projektion/rotation, masksemantik och eventuell regridding måste verifieras före implementation; befintliga syntetiska tester kvalificerar inte MET.

Gridomvandling: [beviskontrakt](forecast-regridding-proof.md) och exakta negativa referensfall dokumenterade. Metod, toleranser och implementation återstår; ingen verklig prognos kvalificerad.

Gridomvandlingens två minimala motexempel är nu körbara mot befintlig
segmentcertifiering: källans topp/mask avvisas trots att glesare målfält
certifieras. Detta kvalificerar ingen verklig omvandlingsmetod.
