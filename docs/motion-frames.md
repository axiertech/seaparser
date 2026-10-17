# Fysisk rörelse och kartposition i Vinga-granskningen

Återhämtning från cb1600e. De nio avbrutna filerna bevaras och färdigställs
som en uttrycklig alternativ komposition; äldre standardprofiler och sidor
ändras inte. Ny granskningsadress: /vinga-ruttjamforelse-ramar.html.

## Ramar och enheter

Vind och ström är fysiska markrelativa TILL-komponenter i sann öst/nord, m/s.
MET:s FRÅN-riktning omvandlas en gång; dess sanna ram och överensstämmelse
med WGS84 är fortsatt ett namngivet källantagande. Copernicus använder sina
CF-deklarerade öst-/nordkomponenter. Källornas egna grid och masker kvarstår.
Båtfart 5 knop omräknas en gång till fysisk m/s genom vattnet. Båten
kompenserar ström i samma fysiska bas. Vind, vattenfart och ström avbildas
inte separat som om de vore kartans hastighetskomponenter. Vågriktning och
båtens kurs som används av komfortmodellen behåller samma fysiska nordreferens.

Positioner, målriktning och hinder är WGS84-AEQD-meter kring Vinga. Om J är
projektionens differential för fysisk öst/nord-förflyttning ges den fysiska
målriktningen av normaliserad J^-1 gånger kartans riktning. Efter fysisk
strömkompensation avbildas hastigheten över grund med J till positionsderivata
i kartmeter/sekund. Både förutsagd mittpunkt och accepterad ändpunkt använder
rätt derivata vid respektive position. Halvkonfigurerad rörelseram avvisas.

PROJ:s råderivator är normaliserade med WGS84:s a och vinklar i radianer.
Fysisk öst-/nordskala använder prime vertical- respektive meridianradie,
inte en ren rotationsmatris. Numeriska PROJ-faktorer, ändliga/icke-singulära
derivator och stödradie kontrolleras. Den befintliga 900 m-gränsen höjs inte.
Detta är punktkinematik och den diskreta mittpunktsmodellens affina segment,
inte en rigorös felgräns för en verklig kontinuerlig färd. Källkvalificering,
tidsmedel, masker, run-förenlighet, djup och navigationssäkerhet kvarstår okända.

## Verifiering

Analytisk skalad/roterad referens visar att 100 kartmeter tar 62,5 s med
1 m/s fysisk vattenfart och 0,6 m/s sidoström. Positionsberoende känt
logaritmiskt fall verifierar mittpunktskonvergens. Separata WGS84-Geod-
förflyttningar i fysisk öst/nord och blandad riktning jämför J vid origo,
500/350 m, -600/-600 m och 900 m-gränsen. 2e-7 m/s är numerisk
regressionstolerans, inte en certifierad käll- eller integrationsfelgräns.
Vind-/strömnoder ändras inte av rörelseavbildningen; felaktiga enheter avvisas.

## Reproducerbar grafisk leverans

```sh
/tmp/seaparser-ci-clean/bin/python -B -m scripts.export_real_routes --motion-frame --candidates 4 --departures 0 600 3600 10800 --output artifacts/motion-route-review
```

Samma verkliga 17-oktober-prognoser och samtliga 24 hinder används, med
21 kandidatnoder, oförändrade gränser och 16 undersökta alternativ. Båda
kriteriernas vinnare är auto-0 kl 04:00: restid 136,815740 s och
komfortexponering cirka 60,3428. Detta är en villkorad jämförelse inom
undersökt graf/budget, ingen global optimalitet eller godkänd navigation.
Den äldre motsvarigheten utan avbildningen finns kvar för spårbar jämförelse.

Publicering återanvänder deployment.frozen_review med --review routes-motion.
Endast nya vinga-ruttjamforelse-ramar.html kopieras. Befintlig startsida,
prognosgranskning, ruttjämförelse och API/tjänst lämnas oförändrade.
Bygg/källresultat stannar utanför webbroot; gammal adress skrivs aldrig över.
