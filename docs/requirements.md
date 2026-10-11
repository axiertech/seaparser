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
