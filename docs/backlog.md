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
| Geodetisk adapter och verkliga prognoser | Beslut behövs före integration | Region, källkvalitet, format, licens och eventuell kostnad behöver väljas |
| Tidvatten och stationsström | Adapter-/region-/licensbeslut återstår | Separata vattenståndsdatum och strömriktning/djup; ingen områdesextrapolation utan verifierad modell |
| Fler spårbara båtprofiler och manövrer | Beslut behövs före verkliga profiler | Polarrättigheter, representativa båtar och manövermodell; automatisk kryss ingår inte i nuvarande prototyp |
| Mobil presentation och visuell editor | Utvärdering återstår | Egna komponenter, responsivitet, versionshantering, export, licens och kostnad före bindande val |
| Konton, kvoter och prenumerationer | Senare, produktbeslut behövs | Definition av planuppdatering/kvotperiod, skydd av användardata och användarvillkor |
| AIS/trafikbelastningsinformation | Lågprioriterad extrafunktion, design endast | Observerat antal/historiska mönster med passagetid, dagsljus, sikt, väder, datatid och osäkerhet; aktuell bild är inte framtidsprognos. Ingen GPS/CPA/kollisionsvarning/övervakning/undanmanöver |

Arbetet ovan innebär ingen drift/publicering, merge till main, serverkonfiguration
eller ändring av befintliga databasobjekt. Synliga resultat från syntetiska
scenarier är inte navigationsunderlag. Uppdatera tabellen när en del har verifierats.

Huvudprioritet är fortsatt väderrouting, ström, komfort och avgångstider.
AIS-kontrakt/ersatt testplan: [traffic-planning.md](traffic-planning.md).
OpenWaters produktspecifika kandidatgranskning: [openwaters-review.md](openwaters-review.md).
Inga konton, token eller betalda tjänster skapas innan särskilt beslut.
