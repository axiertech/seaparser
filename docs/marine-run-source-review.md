# Marina körbegrepp: officiell källgranskning

Granskat 2026-10-16. Omfattning: produktmanualernas generella semantik,
inte certifiering av befintliga ARCO-värden. Inga marina väderdata hämtades.

## PHY: analyscykel, modellstart och leverans är separata tider

[PHY/BGC PUM, issue 1.3, 11/2025](https://documentation.marine.copernicus.eu/PUM/CMEMS-BAL-PUM-003-006-007.pdf),
§II.3.6, tryckta sidor 23–24 (PDF-sidor 23–24): 00Z-analysen börjar modellens
tidsserie vid föregående dags 12Z; 12Z-analysen börjar vid samma dags 00Z.
Det är modelltid. Den faktiska produktionen väntar på atmosfärsprognosen.
Leverans anges senast 10 respektive 22 UTC för 00Z respektive 12Z analys.
Schemat är ingen observation av faktisk publicering för ett visst uttag.

§II.1, sidor 11–12, och ändringshistoriken sida 9 beskriver nio prognosdygn
och tolv föregående timmar som räknas om och skrivs över vid varje produktion.
Det ger ett dokumenterat skäl att kräva historisk urvalsbindning.

## WAV: uppdateringsschema och drivning

[WAV PUM, issue 2.8, 11/2025](https://documentation.marine.copernicus.eu/PUM/CMEMS-BAL-PUM-003-010.pdf),
§II.4.1, sida 13: uppdatering två gånger dagligen, 10 och 22 UTC, med
216 timmars prognos. §II.3, sida 12 beskriver MetCoOp-HARMONIE de första
66 timmarna, därefter ECMWF, och PHY som källa för ström, is och vattenstånd.
Dokumenterad modellkoppling identifierar inte vilka faktiska körningar som
ingick i våra sparade värden.

Annex VI, sida 20 visar ett creation_date-exempel. Ett exempelattribut är
ingen verifierad publiceringstid för våra filer. Manualens versionsdatum
och katalogversionen 202311 får inte heller bli ett run-ID.

## Slutsats för det befintliga uttaget

Antagande: ingen likhet mellan produktionsschema och faktisk publicering,
ingen retroaktiv bindning från dagens metadata till historiska ARCO-bytes.
Detta är vår konservativa granskningsregel, inte ett påstående från manualerna.

Återanvänd [inventeringen](forecast-run-inventory.md) och
[run-kontraktet](forecast-run-provenance.md). Saknat bevis är fortfarande:
originalrun/revision för varje variabel och giltighetstimme, dokumenterad
utfärdandetid, historisk ARCO-urvalsbindning och granskad förenlighetsregel för
hela vind/ström/våg-uppsättningen. Manualgranskningen ändrar inget av dessa
värden. issued_at/run_identity förblir null och data_unavailable kvarstår.

Nästa oberoende arbete: verifiera vindens native geometri/vektorram mot
det befintliga RegionalForecastInputs utan regridding eller antagen
datumekvivalens. Körscheman får inte användas för att häva planning_blockers.
