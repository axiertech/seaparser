# Begränsad kandidataudit med 17-oktoberdata

[Grafisk jämförelse](../artifacts/native-candidate-budget/index.html) och
[auditrapport](../artifacts/native-candidate-budget/audit.json) använder samma
frysta verkliga MET/WAV/PHY-bunt, explicit namngivna utvecklingsantaganden och
samtliga 24 hinder från det nya OSM-underlaget. Inga nya väderuttag ingår.
Start (500,0) och mål (500,350) är uttryckligt valda punkter som det nya
landunderlaget tillåter. Den gamla blockerade starten återanvänds inte.

## Budget och resultat

Oförändrad 26-nodsbudget stoppar vid 27 noder. Den uttryckliga **offlinebudgeten
66 noder** rymmer grafens 60 noder. A* prövar 2/4/8 kompletta kandidater,
högst 8 waypoints och 1000 expansioner/köposter, över avgångarna 01:00, 01:10,
02:00 och 04:00 UTC den 17 oktober. Hela den befintliga 1800 s-ruttbudgeten
måste rymmas före den exklusiva gemensamma slutetiketten 12:00 UTC. Fysisk
medelvärdessemantik och körförenlighet är fortfarande antaganden, inte verifierade
källfakta.

| Kandidater × avgångar | Uppmätt beräkning | Resultatstorlek |
| --- | --- | --- |
| 2 × 4 | 13,506 s | 786 431 byte |
| 4 × 4 | 13,128 s | 1 631 280 byte |
| 8 × 4 | 14,630 s | 3 771 199 byte |

Tiderna omfattar sekventiell resultatkomposition före slutlig JSON-kodning.
Första fallet har kall applikationscache; senare fall varm. Separata kalla
processprov för 2×4, 4×4 och 8×2 finns i
[workers.json](../artifacts/native-candidate-budget/workers.json), med oförändrad
20 s-gräns och 8 MB resultatgräns. 2×4 klarade 14,894 s och 8×2
15,965 s. **4×4 avbröts vid tidsgränsen** (20,626 s inklusive avslut).
En separat riktad lokal kontroll överlappade processproven; värdlasten var inte
isolerad. Det motiverar att behålla befintlig spärr, inte att höja den.
Mätningen är ingen latensgaranti för andra
ändpunkter, samtidiga jobb eller andra datorer. Ingen interaktiv utökning är
aktiverad: API:s nodbudget, två samtidiga processer, tids-/resultatgränser och
högst 16 kombinationer kvarstår. 8×4 är en uttrycklig offlineaudit.

Samtliga 32 undersökta alternativ i det största fallet anländer inom modellen.
Samma alternativ vinner båda kriterierna i alla tre budgetarna: `auto-0` klockan
04:00, restid **136,813299 s**, komfortexponering **60,340387** (avrundad; exakt
värde i JSON). Ingen syntetisk väderserie har konstruerats. Valet av bekvämaste
alternativ tillåter högst 300 s extra restid jämfört med kortast restid över
undersökta avgångar. Det är inte tidigast ankomst.

Sökningen är trunkerad vid kandidatbudgeten och detta visas i rapporten/sidan.
Grafens euklidiska ordning är inte väderoptimalitet; fler kandidater är ingen
garanti för bättre rutt. Hela integrerade segment kontrolleras mot alla hårda
hinder, datastöd och valda absoluta vädergränser; faktisk ankomst kontrolleras
separat. Utvecklingens 900 m-tak är oförändrat. Båten är uppskattad,
komfortmodellen ej validerad och landfullständighet/djup okända.

## Exakt och begränsad geometrisk acceleration

`Polygon.intersects` kan avvisa ett segment endast om dess box är strikt
separerad från polygonens box utökad med marginalen på minst en koordinataxel.
En euklidisk marginal ligger inom denna utökade box. Alla gränser och
jämförelser använder Fraction på lagrade tal; avrundade flyttalsboxar används
inte. Likhet fortsätter till befintliga slutna kant-/avståndspredikat.
Återstående kontroll är oförändrad. Sub-ULP-marginaler och slutna kontakter har
analytiska regressionsfall.

En LRU-cache med högst 256 frysta geometrier bevarar exakta hörn och boxgränser.
Inga hinderbeslut, marginaler, resultat eller tidsberoende tillstånd cachelagras.
Grafen med 60 noder/åtta kandidater tog i inledande prov 90,840 s utan denna
acceleration, 13,040 s med exakt box och 11,581 s med box plus begränsad cache.
Kandidatpunkter/ordning är desamma i dessa prov. Tiderna är observationer av
enskilda sekventiella prov, inte ett generellt prestandalöfte.

`audit_node_limit` är ett internt, explicit offlineargument som bara tillåter
26 eller 66 och kräver native-bunten samt en 2/4/8-kandidataudit. HTTP-modellen
accepterar varken denna inställning eller godtyckliga konfigurationssökvägar.
Ingen generell domängräns har höjts eller tagits bort.

Källorna behåller `source_qualification=unverified`; resultat är
`conditional_on_assumptions`, med `assumed_fields` separat. Källäst modellreferens,
hämtning och antagen utfärdandetid hålls isär. Originalens okända issued_at är
fortfarande okänd. Strikt planering kvalificeras inte av dessa prov.

```bash
.venv/bin/python -B -m scripts.audit_native_candidates --output artifacts/native-candidate-budget
.venv/bin/python -B -m scripts.audit_native_candidates --workers --output artifacts/native-candidate-budget
```

Nästa steg är en explicit valbar utvecklingskomposition med verifierad
processbudget och grafisk integration, därefter samlat större rumtids-/landstöd
innan någon utökning av 900 m. Ingen offentlig driftsättning ingår.
