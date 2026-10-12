# Produktkrav

## Mål

Planeringsstöd för fritidsbåtar som jämför vägval och avgångstider med hänsyn till båtens prestanda, tidsberoende väder och användarens komfortpreferenser. Appen ersätter inte officiella sjökort, navigationsvarningar, instrument eller befälhavarens bedömning.

## Funktioner

- Snabbaste och bekvämaste alternativ med samma absoluta begränsningar.
- Familjeläge samt Leisure/Racing-profiler. Racing får inte automatiskt upphäva absoluta gränser.
- Jämförelse av avgångstider, inklusive resultatet att inget undersökt alternativ uppfyller kriterierna.
- Standardprofiler för flera segelbåtar med spårbara polarer samt import och anpassning av egen båt och segelkonfiguration.
- Motorbåtsmodell med separata kriterier. Bränsle, räckvidd och påverkan av sjö behöver specificeras.
- Vind, vågor och strömmar utvärderade längs hela färden med tillhörande giltighetstider.
- Varningar och avrådan vid överskridna gränser eller otillräckliga data.
- Mobilanpassad presentation med karta, alternativ och tidslinje.
- Designer ska visuellt kunna ändra befintliga sidor och tema utan programmerare. Nya komponentbeteenden kräver utveckling.
- Konton, skydd av användardata, versionshanterade användarvillkor och prenumerationsförberedd struktur.
- Free: högst en planuppdatering per dygn. Premium: fyra. Pro: adaptivt. Definitionen av uppdatering och kvotperiod återstår att fastställa.

## Första leveransen

En prototyp med ett begränsat syntetiskt vattenområde, kontrollerade prognoser och en tydligt märkt uppskattad segelbåtsprofil. Den utgör inte en navigationsprodukt.

Acceptanskriterier:

- Identiska indata och versioner ger identiska resultat.
- Konstant fart utan hinder ger restid som stämmer med distans/fart inom dokumenterad tolerans.
- Prognosförändringar utvärderas vid simulerad tid och position, inte bara vid avgång.
- Förbjudna områden korsas inte av något segment, även när ändpunkterna ligger utanför området.
- Båten kan inte segla direkt i förbjudna vindvinklar; manövrer behandlas konsekvent.
- Överskridna hårda gränser kan aldrig kompenseras med kortare restid.
- Saknade nödvändiga data ger ett uttryckligt fel eller ej genomförbart resultat.
- Ett kontrollerat scenario visar olika snabbaste och bekvämaste alternativ och förklarar skillnaden.
- Beräkningstid, geografisk upplösning, tidssteg och toleranser dokumenteras.

Numeriska toleranser och prestandamål fastställs före respektive test. Verifiera först en enkel referenslösning innan en snabbare sökalgoritm införs.

## Prioritering och senare trafik-/tidvattenunderlag 2026-10-12

SeaParser är en planeringsapplikation. Väderrouting, ström, komfort och jämförelse
av avgångstider prioriteras före AIS. Trafikbelastningsinformation är en
lågprioriterad extrafunktion, inte en navigations- eller övervakningsprodukt.

För en planerad rutt ska senare trafikstöd redovisa observerat antal unika fartyg
inom ett definierat observationsfönster och ruttområde. Trafikmönster får användas
endast med tillförlitligt historiskt underlag. Information ska sättas i samband
med planerad passagetid, dagsljus/mörker, sikt och väder, med datatid, täckning och
osäkerhet synliga. Graderingen kan vara låg/måttlig/hög/okänd observerad eller
historiskt förväntad belastning; metod och trösklar måste fastställas före
implementation. Aktuell AIS-bild får inte beskrivas som känd framtida trafik.
Gamla, saknade eller låg-täckande data ger okänd trafikbild, inte låg belastning
eller fri passage. Även noll observerade AIS-fartyg är ingen garanti om andra båtar.

Fryst ruttplanering ska vara oberoende av AIS-hämtning. Ett eventuellt fryst
trafikunderlag används för planeringsinformation, utan att ändra prognoser eller
hårda vädergränser under jämförelsen. Första omfattningen innehåller ingen GPS-
följning, löpande trafikövervakning, mötes-/CPA-analys, kollisionsvarning eller
undanmanöverrådgivning. Tidigare förslag om sådana funktioner är ersatta av
belastningsinformationen. AIS-underlag/adapterkontrakt finns som design i
[traffic-planning.md](traffic-planning.md); ingen AIS-kod är implementerad.

Tidvatten ska behandlas som separat vattenståndsunderlag med station, källa,
modell/version, prognostid/giltighet, enhet och vertikalt referensdatum. Datum får
inte tappas eller ersättas med antaget MSL/sjökortsdatum. Tidvattennivå ensam
bevisar inte navigerbarhet eller fri höjd/djup. Stationsström ska behålla mätt/
predikterad riktning, fas/signering, djup/bin och djupreferens. Den får inte
extrapoleras till ett helt område utan en verifierad rumslig modell. Okänd
riktning/djup eller inkompatibla datum ger otillräckligt underlag.

OpenWaters utvärderas som kandidat, med regional täckning, datalicens,
kommersiell användning och driftsbegränsningar separat för AIS, tidvatten och
ström. [openwaters-review.md](openwaters-review.md) redovisar vad som är verifierat
i officiell dokumentation och vad som återstår. Ingen leverantör är vald och
inga nya konton, token, betalda tjänster eller integrationer ingår nu.

## Planeringsflöde och geografiskt underlag 2026-10-12

SeaParser är ett planeringsverktyg med sjökortsnära kartpresentation. Användaren
jämför och granskar rutten och för över planerade vägpunkter till sin plotter.
GPS-följning ingår inte. Kartpresentationen ersätter inte officiella sjökort.
Geografisk routing runt hinder prioriteras före AIS och vidare presentationspolering.

Kartbakgrund och routingsunderlag är separata produkter. En snygg eller detaljerad
karta är inget bevis för att ruttmotorn känner land, farliga djup eller restriktioner.
Routing ska ha versionsbundna polygoner för land, öar, grund, djupområden och
restriktioner. Varje underlag ska ange källa, version, täckning, koordinatreferens,
giltighet/uppdateringstid och kvalitetsstatus (verifierad, uppskattad eller okänd).
Hårt förbjudna områden ska blockera hela färdsegment inklusive konfigurerad
säkerhetsmarginal. Informationslager ska märkas tydligt och får inte automatiskt
bli förbud eller bevis för fri passage. Okända områden eller okända djup ska visas
som uttryckligen okända; frånvaro av hinder är inget navigerbarhetsbevis.

Planera båtens djupgående och separat säkerhetsmarginal under kölen. Djupdata ska
ange enhet, vertikalt datum, källa/version, kvalitet och täckning. Tidvatten och
djup får endast kombineras när referenserna är kompatibla eller en spårbar,
verifierad transformation finns. Okänt datum/djup ger otillräckligt underlag;
ingen antagen nollnivå. Vågor, osäkerhet och eventuell squat kräver senare modell
innan verklig klarering kan intygas. Hinder-/djuppolicy gäller båda ruttmålen.

Nästa begränsade leverans är automatisk omväg runt syntetiska enkla polygoner i
befintligt lokalt öst/nord-plan, med hela-segment-kontroll och marginal i meter.
Geometriska referenstester ska vara oberoende av sökalgoritmen. Genererade
kandidater ska simuleras med befintlig tidsberoende vind, ström, polar, komfort,
prognos- och väderkontroll. Geometriskt kortast väg är inte nödvändigtvis snabbast
väderrutt. Sökgränser och ofullständig sökning ska redovisas; frånvaro av verifierad
kandidat innebär inte att alla möjliga rutter är prövade.

Därefter förbereds geografiska koordinater, sjökortsnära kartvisning och export
av granskade planerade vägpunkter (exempelvis GPX). Datum/projektion, axelordning,
enheter, geografisk utsträckning och segmentmodell måste valideras separat.
Export ska bevara waypointordning och skilja planerad bana från GPS-spår; plotterns
import och rutten ska granskas av användaren. Verkliga kart-/hinderkällor kräver
separat utvärdering av region, täckning, upplösning, kvalitet, uppdateringar,
kommersiella rättigheter, attribution, cachning/offline/export och kostnad före
integration. Ingen leverantör, visuell editor eller betald resurs väljs nu.
