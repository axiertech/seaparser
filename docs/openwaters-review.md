# OpenWaters som adapterkandidat

Officiell dokumentation granskad 2026-10-12. Kandidatgranskning, ingen vald
leverantör, liveintegration eller regional kvalitetscertifiering. AIS är en
lågprioriterad planeringsextra; inget konto/token/tjänstköp eller sändning av
positionsdata har gjorts. Endast offentliga dokumentationssidor lästes.

## AIS: observerad trafik och begränsningar

OpenWaters anger norska kust-/EEZ-källor, Fintraffic i finska vatten och globala
aggregatorer/frivilliga mottagare. Detta verifierar källornas angivna räckvidd,
**inte** fullständig svensk eller ruttlokal täckning. Data har källspecifik licens:
NLOD för norska källor, CC BY för Fintraffic, egna villkor för AISHub och oklara
återanvändningsvillkor för aisstream. Aggregatet får inte antas vara CC0 eller
kommersiellt fritt. [Officiell AIS-käll-/licensbeskrivning](https://openwaters.io/ais/).

NLOD och CC BY medger återanvändning med sina krav på attribution och villkor;
CC BY inkluderar kommersiell användning. Detta ger ingen rätt till hela
OpenWaters-aggregatet eller alla tjänstenivåer.
[NLOD 2.0](https://data.norge.no/nlod/en/2.0),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

AIS-sidan skiljer personlig fri användning från en kommersiell betald nivå.
SeaParser behöver klarlagda avtals-/prisvillkor innan produktintegration; pris
är inte verifierat och ingen kontakt/beställning är gjord.
[Officiella AIS-nivåer](https://openwaters.io/ais/).

API-referensen anger anonym nivå med2 strömmar/adress,20 meddelanden/s,100
kvadratgrader och HTTP120 anrop/minut. Överskriden meddelandetakt kan gallra
strömmen. Täckningskartorna gäller de senaste7 fullständiga UTC-dygnen och kan
inte bevisa att tyst område är trafikfritt. Marknadssidan anger8 totala strömmar/
adress medan API-referensen anger32; skillnaden är **olöst**, inte verifierad
kapacitet. Inget streamanrop kördes. [AIS API](https://openwaters.io/api/ais/),
[AIS-nivåer](https://openwaters.io/ais/).

SeaParsers bedömning: eventuell adapter måste bevara källa/licens, datatid,
mottagningstid, SOG/COG och kvalitetsstatus. seen/age_s får inte automatiskt bli
position_time. Regional täckning och gallring behöver kontrolleras per planerad
korridor/fönster innan antal kan graderas. Saknad/låg täckning är unknown.
Ingen CPA-/mötesanalys eller löpande övervakning kopplas till denna kandidat.

## Tidvatten: stationer och referensdatum

API:t ger harmoniska stationsprognoser, även via närmaste station till en punkt,
och har parametrar för vertikalt datum och enhet. Det är öppet utan autentisering,
med100 anrop/minut och10000/dygn per adress. [Tides API](https://openwaters.io/api/tides/).

Katalogen beskriver NOAA främst för USA/territorier och TICON som global källa.
Det fastställer inte täckning/kvalitet för en ännu ej vald svensk testregion.
[Officiell stationsdatabas](https://github.com/openwatersio/slackwater-database).

Kodens MIT-licens är skild från datasetlicenser. OpenWaters allmänna licenssida
nämner CC0/ODbL samt tredjeparter och kräver kontroll av respektive datasets
villkor. Kommersiell användning för valda tidvattenstationer är därför **inte
klarlagd** i denna granskning. [Licensöversikt](https://openwaters.io/license/).

SeaParsers adapterkrav: station/id, modellversion, UTC-prognostid/giltighet,
kända enheter och **det faktiska vertikala referensdatumet** följer varje nivå.
Hämtningstid är inte utfärdandetid; okänd sådan metadata märks okänd. Ingen
implicit datumomräkning eller slutsats om djup under köl görs. Innan integration
behövs regional stationsinventering, licens-/datumkontroll och referensprov mot
officiella nivåer, inklusive tidszoner och stationsavstånd. Ingen station hämtades.

## Ström: stationsmodell och djup

API:t beskriver signerad fart i knop längs flodaxeln, sann flood-/ebbDirection
när sådan finns, samt djupbins med primärbin som standard. Tidslinjen har10 min-
intervall. Samma100/min och10000/dygn gäller som för tidvatten. CHS-stationer kan
listas men deras prediktioner avvisas med451 på grund av återdistributionsvillkor;
saknad modell ger404. [Currents API](https://openwaters.io/api/currents/).

Regional strömtäckning är inte fastställd för SeaParser. Stationsförekomst eller
närmaste station är inget bevis på en geografiskt täckande strömmodell. Valda
stationskällors kommersiella rättigheter måste kontrolleras separat; tidvattnets
licensbesked får inte återanvändas som ett strömbesked. Allmänna kodlicensen räcker
inte. [Licensöversikt](https://openwaters.io/license/),
[Currents API](https://openwaters.io/api/currents/).

SeaParsers adapterkrav: bevara station, rå signerad fart/enhet, fas och publicerad
mot-riktning samt bin, djup/enhet och djupreferens. Saknad riktning/djup förblir
okänd; primärbin får inte antas vara yta. Stationsdata får inte fylla ett rutt-
rutnät utan en separat verifierad rumslig modell. Befintligt syntetiskt rutnät
är inte en sådan verklig modell. Ingen strömadapter eller regional extrapolation
är implementerad. Modellens utfärdandetid/kvalitet måste också klarläggas.

## Beslutsläge

Tekniskt dokumenterade kandidater finns för tre separata produkter, men
regional kvalitet och produktspecifika kommersiella rättigheter återstår.
Nästa beslut kräver vald region/resor och tillåtna stations-/AIS-källor; inga
kostnader/utökade behörigheter tas på förhand. Huvudspåret förblir väder, ström,
komfort och avgångstider. Trafikbelastning väntar som lågprioriterad extrafunktion.
