# Backlog och nästa sammanhängande leverans

Prioriteringen bygger på requirements.md, architecture.md, decisions.md och
kvarstående begränsningar i prototype/README.md. Historiska nästa-steg i
progress.md är arbetslogg, inte en aktuell komplett backlog.

| Del | Status | Avgränsning / acceptans |
| --- | --- | --- |
| Frysta prognoser och separata produktmetadata | Klar, CI godkänd på 0fd50948 | Syntetiska fixtures och komponentinterpolation, inga verkliga källor |
| Kontinuerligt datastöd över integrerade segment | Klar, CI godkänd på 8453a14 | Avvisa passerade masker, saknade interpolationsstöd och rum/tid utanför täckning; små luckor ska inte kunna hoppas över |
| Reproducerbart syntetiskt planeringsscenario | Implementerat, CI väntar | Offlinekommando med fryst dataset, båtmodell, parametrar och spårbar resultatidentitet; körbar referens för framtida integration |
| Kontinuerliga hårda vädergränser | Återstår | Datastöd är inte bevis på kontinuerligt godtagbara vädervärden; metod och toleranser behöver verifieras |
| Geodetisk adapter och verkliga prognoser | Beslut behövs före integration | Region, källkvalitet, format, licens och eventuell kostnad behöver väljas |
| Fler spårbara båtprofiler och manövrer | Beslut behövs före verkliga profiler | Polarrättigheter, representativa båtar och manövermodell; automatisk kryss ingår inte i nuvarande prototyp |
| Mobil presentation och visuell editor | Utvärdering återstår | Egna komponenter, responsivitet, versionshantering, export, licens och kostnad före bindande val |
| Konton, kvoter och prenumerationer | Senare, produktbeslut behövs | Definition av planuppdatering/kvotperiod, skydd av användardata och användarvillkor |

Arbetet ovan innebär ingen drift/publicering, merge till main, serverkonfiguration
eller ändring av befintliga databasobjekt. Synliga resultat från syntetiska
scenarier är inte navigationsunderlag. Uppdatera tabellen när en del har verifierats.
