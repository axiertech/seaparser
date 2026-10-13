# Beviskontrakt före gridomvandling av prognoser

Status 2026-10-13: avgränsad design, ingen metod/tolerans eller adapter vald.
MET:s verifierade koordinatdiagnostik visar att native LCC inte direkt kan
representeras i motorns separerbara lokala axlar. Befintlig segmentcertifiering
bevisar gränser för det representerade GridProduct, inte för en okänd omvandling.
Se [regional-wind-acceptance.md](regional-wind-acceptance.md).

## Två skilda skyldigheter

En framtida omvandling måste dels producera dokumenterade uppskattade värden
för simulering, dels bevisa att nödvändigt källstöd och hårda gränser täcker
varje accepterad målcell/segment. Små nodfel eller en visuellt jämn vindkarta
uppfyller inte den andra skyldigheten. Felgränser för geometri och komponenter
måste vara verifierade, inte bara valda för att ett exempel ska passera.

Varje målcell i rum/tid behöver en versionsbunden koppling till alla källceller
som kan stödja dess hela transformerade utsträckning, inklusive gränser och
osäkerhetsmarginal. Ett ändligt antal provpunkter får inte vara det enda beviset
för en icke-linjärt transformerad cellkant. Okänd transformation eller ofullständig
cellmängd ger otillräckligt underlag. Överbudgetarbete får inte tyst trunkeras.

Källmasker, saknade hörn och giltighetsluckor ska prövas för hela stödmängden.
En maskad källcell mitt inne i en målcell får inte försvinna för att målhörnen
är giltiga. Källornas produktmasker förblir separata; en vågmask blir inte vind-
eller strömmask. Färre målgridnoder får inte skapa längre tids-/rumstäckning.

## Hårdgränser och interpolerade värden

Befintlig vindcertifiering använder komponenthöljen över målcellens hörn och
jämför kvadrerad norm exakt på lagrade tal. Hs använder ett övre cellhölje.
Efter omvandling räcker dessa målknutar endast till bevis om målfältet.
För att dessutom bevara källfältets gränser måste en framtida metod leverera
verifierade höljen för hela källstödet och omvandlingens fel.

För normaliserade källkomponenter med verifierad interpolation kan ett sådant
hölje prövas som U²+V² <= L², där U/V begränsar absoluta komponenter för hela
stödet inklusive transformations-/interpolationsfel. Hs behöver motsvarande
övre gräns. Detta är ett beviskrav, inte ett beslut att varje källprodukt har
just denna interpolation eller att en rotation är konstant över cellen.

En ren, exakt ortogonal rotation bevarar vektornormen vid en punkt. Det bevisar
inte att interpolation efter rumsligt varierande rotation bevarar samma
komponenthölje över en cell. Varken normbevarande eller komponentinterpolation
får antas utan verifierad ram, geometri och källsemantik.

Uppskattad vind för fart/komfort och konservativa säkerhetshöljen måste hållas
isär. Ett källmax får inte injiceras som en fiktiv vindkomponent för att använda
nuvarande GridProduct-certifiering; det ändrar den simulerade miljön.
Om nuvarande modell inte kan bära ett nödvändigt bevis ska routing förbli
unavailable tills ett granskat kontrakt är implementerat. Inga nya tomma lager
eller parallella adapterspår behövs för denna design.

## Oberoende minimala motexempel

[regridding-counterexamples.json](../fixtures/regridding-counterexamples.json)
är syntetisk, exakt rationell analys utan käll-/väderdata. Den illustrerar:

1. Native u-knutar (0,0), (1/2,20), (1,0), med v=0 och linjära delsegment.
   Ett målgrid som endast provtar ändpunkterna blir noll över intervallet.
   Källans topp 20 överstiger gränsen 10 trots godkända målknutar.
2. Giltiga ändpunkter 0 och 1 döljer en förbjuden sluten källregion [2/5,3/5].
   Noll maskträffar vid ändpunktsprov bevisar inte hela målcellen som giltig.

Motexemplen gäller oavsett köridentitet och gör inga anspråk på faktisk MET-
eller Copernicus-omvandling. De motiverar att en framtida verifierare behöver
referenstester mot källfältets kända resultat, inte bara målgridets egna värden.

## Bindning och acceptans före implementation

Beviset ska binda käll-/målgrid, källhashar, källmasker, tidsstöd, CRS/datum,
normaliserings- och omvandlingsversion samt verifierade felgränser. Ändring av
något underlag kräver ny kontroll. Run-proveniens och utfärdande prövas separat
enligt [forecast-run-provenance.md](forecast-run-provenance.md).

Acceptans kräver både positiva oberoende geometri-/fältreferenser och negativa
fall för dold topp, dold mask, cellgränskontakt, saknat stödhörn, tidslucka,
variabel rotation, ändrad hash och överbudget. Osäkert hölje är otillräckligt
bevis, inte en observerad överträdelse eller en säker rutt. Båda ruttmål och
alla avgångar ska använda samma frysta bevis och samma absoluta begränsningar.
Alla nuvarande planning_blockers kvarstår. Ingen vind eller marin prognos
kvalificeras av detta kontrakt.
