# Djupgående, vertikala datum och export: offline acceptanskontrakt

Status 2026-10-16: design och granskning av befintliga gränser. Ingen djupkälla,
ny API-parameter eller klareringsmodell införs. Kravgrund:
[requirements.md](requirements.md), avsnitt Planeringsflöde och geografiskt
underlag, samt beslut 2026-10-12 i [decisions.md](decisions.md).

## Verifierat nuläge

- api/models.py PlanInput har margin_m men inget djupgående eller marginal
  under kölen. Extra fält avvisas. margin_m är horisontell polygonmarginal;
  SearchPolicy.clearance_m används för kandidatgenerering runt hinder.
  Ingen av dem får återanvändas som vertikal marginal.
- application/geographic_plan.py ger depth_status unknown och
  navigational_safety not_assessed även när en syntetisk kandidat anländer.
  regional_scene redovisar samma okända status för Vinga.
- presentation/gpx.py kräver anländ modellkandidat samt väder-/ankomstkontroll.
  Vinga-exporten beskriver okänt djup/landfullständighet; generell export
  beskriver syntetiska testdata och ingen garanti för navigerbarhet.
  Exporten har rtept, inga påhittade djup/höjder eller GPS-spår.
- application/regional_forecast.py ger inga verkliga ruttkandidater när
  prognosbevis saknas. Ett framtida godkänt prognosunderlag bevisar inte djup.
- Copernicus deptho i vågmodellens statiska fil och strömmens near-surface
  depth_m är olika variabler. Ingen är i dag kvalificerat klareringsunderlag.
  Strömmens provtagningsdjup är inte bottendjup eller båtens djupgående.

Dagens arrived betyder genomförd syntetisk modellfärd, inte godkänd verklig
passage. Okänt djup hindrar ett klareringspåstående; dagens uttryckligt märkta
syntetiska export är fortfarande möjlig. Ingen befintlig exportregel ändras.

## Föreslaget framtida fryst kontrakt

Båtens djupgående i meter och separat marginal under kölen måste vara explicita,
finita och spårbara till vald konfiguration. Inget defaultvärde som låtsas vara
verklig båtdata. Giltiga värdeintervall och förändringar med last måste bestämmas
före implementation. Horisontell säkerhetsmarginal behåller eget fält.

Djupunderlag behöver källa, oföränderlig version/hash, enhet, positiv riktning,
vertikalt referensdatum, geografiskt CRS, kvalitet/osäkerhet och dokumenterat
rumsligt stöd. Vattenstånd behöver dessutom station/modell, prognos-/runmetadata,
tidstäckning och dokumenterad rumslig representativitet. Stationsvärde får inte
spridas över hela området genom antagande. Datum är en höjdreferens här,
inte ett kalenderdatum. Okända datum får aldrig ersättas med MSL eller noll.

Kompatibilitet kräver samma verifierade vertikala referens eller en spårbar,
verifierad transformation med område, giltighet och osäkerhet. Ett liknande
namn eller gemensam enhet räcker inte. Omräkning av enhet måste ske före
kombination; tecken och djup-/höjddefinition måste bevaras.

Som enbart syntetisk referens: positivt bottendjup 5 m under ett gemensamt
nollplan och vattennivå -1 m över samma plan ger vattenkolumn 4 m.
Med djupgående 3 m och separat marginal 0,5 m återstår 0,5 m i denna idealmodell.
Detta är inte verklig klarering: vågrörelse, osäkerhet och eventuell squat
saknar ännu godkänd modell. Exakt gräns, toleranser och konservativ hantering
ska fastställas före kod, inte väljas från ett önskat positivt testresultat.

## Acceptansmatris före djupkvalificerad planering

| Fall | Krävt utfall för båda ruttmålen | Evidens/test före implementation |
| --- | --- | --- |
| Okänt djup eller saknad källa/version | Otillräckligt underlag, ingen klarering | Negativt fall med annars kompletta väderdata |
| Okänt/inkompatibelt vertikalt datum | Ingen addition av djup och vattenstånd | Två finita värden med olika/okända referenser |
| Verifierad datumtransformation | Endast inom dess granskade stöd | Oberoende referensnivåer, tecken och osäkerhetsgräns |
| Negativt vattenstånd | Minskar vattenkolumn i referensmodellen | Oberoende räkneexempel ovan; inte absolutvärde |
| cm/m eller positiv upp/ned | Explicit normalisering eller avvisning | Kända enhets-/teckenfall, ingen tyst tolkning |
| Lucka mellan prov längs färden | Otillräckligt stöd även med giltiga ändpunkter | Segment som korsar smal okänd zon |
| Vattenstånd saknas vid passagetid | Ingen extrapolation eller antagen nollnivå | Tidscellslucka och exklusiv giltighetsgräns |
| Marginal bryts på kort segment | Hård avvisning, komfort/tidsvinst får inte väga bort | Samma underlag för snabbast och bekvämast |
| Endast våtmask/landfraktion/strömdepth | Ingen klarering | Negativa fall där masken säger vatten men djup saknas |
| API/GPX för framtida kvalificerad produkt | Bevara okänd status och begränsningar | Ingen exporterbar säkerhetsgaranti genom att kasta metadata |

Matrisen är ännu inte en implementerad djupgate. Framtida djupfel bör särskiljas
från väderfel utan att ändra betydelsen av befintliga planning_blockers.
Ett nytt kontrakt ska gå genom applikations-/domängränsen utan HTTP/SQL i motorn,
binda frysta metadata och parametrar till resultatidentiteten och granskas innan
verkliga källor eller exportsemantik ändras. Inga nya juridiska, hydrografiska
eller producentpåståenden har verifierats i denna offlineleverans.

## Nästa begränsade del

Kör en offline kontraktsregression på befintlig API-gräns: extra draft-/under-keel-
fält ska avvisas före jobbstart och får inte tyst ignoreras. Kontrollera dessutom
att båda syntetiska ruttmålen behåller unknown/not_assessed och att GPX inte
fabricerar höjd/djup. Detta verifierar dagens avgränsning, inte djupkvalificering.
