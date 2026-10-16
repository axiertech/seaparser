# ARCO och historisk bindning till originalfiler

Granskning 2026-10-16. Officiell dokumentation läst i webbverktyget;
inga nya marina väderdata hämtade. Detta är källgranskning, ingen certifiering.

## Verifierad generell tjänstesemantik

[Original producer files and ARCO data](https://help.marine.copernicus.eu/en/articles/8656000-differences-between-original-producer-files-and-arco-data),
avsnitten Context, Datacube structure och Time referencing:
get bevarar producentfiler; subset väljer ur en harmoniserad ARCO-representation.
Transformeringen kan ändra koordinatnamn/orientering, metadatarepresentation,
missing-värden och tidsreferenser. För aggregerade intervall beskrivs en
standardisering till intervallets början. Detta är generell dokumentation,
inte bevis för en tidsförskjutning i våra timvisa momentanfält.

[Operational workflows](https://help.marine.copernicus.eu/en/articles/8684964-using-the-copernicus-marine-toolbox-in-operational-workflows),
avsnitten Prevent extraction of data currently being updated och Understand
the difference between subset and get: originalfiler och ARCO kan bli
tillgängliga vid olika tider eftersom ARCO kräver ett transformationssteg.
raise_if_updating stoppar uttag som berör en pågående uppdatering och gäller
ARCO, inte get. Dataset-version väljer en distributionsversion vid
produktövergångar. Dokumentationen ger ingen historisk bindning för vårt uttag.

Källorna kontrollerades som aktuell dokumentation; deras relativa uppdaterings-
etiketter används inte som prognosdatum eller fastställd dokumentversion.
Rå dokumentationshash är inte beräknad för webbverktygets svar.

## Konsekvens för vårt sparade uttag

Följande är vår slutsats från källorna och det redan inventerade underlaget:
en lista över originalfiler och dess last_modified/etag kan inte visa vilka
ARCO-revisioner som fanns vid hämtningen 2026-10-13. Ett avslutat
raise_if_updating-prov skulle inte heller identifiera originalrun eller faktisk
utfärdandetid. Ingen ny subset eller omhämtning görs för att försöka återskapa
det historiska läget.

Återanvänd dagens två CSV enligt [metadataåtkomsten](copernicus-metadata-diagnostics.md)
och de tre råfilerna enligt [inventeringen](forecast-run-inventory.md).
00/12-liknande filnamn är kandidatreferenser. Det saknas fortsatt verifierad
koppling per giltighetstimme/variabel till originalrun/revision, dokumenterad
utfärdandetid samt granskad förenlighetsregel för vind/ström/vågor.

Den befintliga nedladdningskoden anger redan raise_if_updating=True.
Kodens inställning är en granskningsuppgift, ingen retroaktiv körlogg eller
bevis för att det sparade uttaget har run-bindning. Flaggan används inte av
adaptern för att häva planning_blockers. issued_at/run_identity förblir null;
data_unavailable kvarstår.

## Källblockerare och nästa oberoende del

[Arkivartikeln](https://help.marine.copernicus.eu/en/articles/4922042-does-copernicus-marine-provide-access-to-product-archives)
gav HTTP 401 i webbverktyget. Fulltext påstås inte läst och används inte som
underlag för arkivlöften. Ingen supportkontakt eller extern kommunikation gjordes.

Nästa oberoende kontroll: verifiera att befintlig marinaudit och freeze bevarar
variablernas koordinatordning när lagringsdimensionerna permuteras. Samma
granskade koordinater och värden ska återges; inga nya källor eller adaptrar.
