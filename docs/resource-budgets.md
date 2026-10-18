# Resursbudgetar och faktisk täckning

Profiler anges direkt i `settings/resource-budgets.json`; de är serverkonfiguration,
inte fritt klientval. Profiler är kapacitet, inte bevis på att data eller routing
stöder motsvarande område. Färdtid och väggklocktid för beräkningen är separata.

| Gräns | Värde / plats | Syfte och faktisk begränsning |
|---|---|---|
| Resultatfil / överföring | 2 GB / 10 GB per uttag, 20 GB per session; `scripts/download_copernicus.py` CLI | Konfigurerbara decimal-GB. Skiljer beräknad nätöverföring från slutfil. Får höjas uttryckligen; ledigt diskutrymme kontrolleras med reserv. |
| Diskreserv | 1 GB, `scripts/copernicus_budget.DownloadBudget` | Kräver utrymme för staging och kopia, utöver reserv. |
| Avkodning | 64 MiB per hyperslab, `--decode-chunk-mb` | Regional NetCDF-statistik läses styckevis, även om filen är flera GB. Allt rådata materialiseras inte för luckräkning. |
| MET-/OSM-svar | 32 MB / 512 MB, `scripts/fetch_uddevalla.py` CLI | Transportbudget, inte geografiskt stöd. OSM serverminne är separat 512 MiB. |
| Simulerad färdtid | 7 dygn lokal/regional, 30 dygn offshore; JSON `voyage_seconds` | Begränsas av faktiskt gemensamt prognosslut minus en sekund. Ingen tyst tidsextrapolation. Den gamla generella 1800-sekundersgränsen är borttagen från ordinarie verklig beräkning. |
| Tidssteg / stegantal | 30/60/300 s; 100000/200000/200000 | Lokala/regionala/offshore-profiler. Hela steg och segment behåller land- och väderkontroll. Större steg är ingen dispens från gränser. |
| Servertid | 20/60/90 s; JSON `job_seconds` | Separat avbrytbar barnprocess. PoC-server använder regional beräkningsbudget. Klienten får pollningsbudget från servern, inte från simulerad restid. |
| Resultat-JSON | 8 MB / 64 MiB / 64 MiB; `result_bytes` | Barnprocessens stdout läses i högst 64 KiB stycken och stoppas vid bytegränsen. GB-prognoser ska inte skickas som ruttresultat. |
| Kandidatnoder | 26/1024/2048 | Explicit `SearchPolicy.max_nodes`; tidigare dold maxgräns 258 borttagen. Synlighetsgrafen är kvadratisk och dessa tal är kapacitet, inte uppmätt prestandalöfte. |
| Expansioner / vägpunkter | 1000/1000000/2000000; 8/128/256 | Explicit sökpolicy. Uppnådd nod-/expansions-/kandidatgräns rapporteras som trunkering, inte som globalt optimalt eller omöjligt vägval. |
| Hinderantal | 64/20000/50000; `max_obstacles` | Explicit sökpolicy, ingen tyst bortfiltrering av hårda hinder. Sökdiskradie kräver positivt finit värde; tidigare 10-km-budgettak borttaget. |
| Aktiva jobb / jobbminne | 2 / 8 jobb, 300 s TTL; `JobStore` | Redan konfigurerbara konstruktorvärden. Normala ruttjobb gör inga väderhämtningar. |
| Kandidater / avgångar | Lokalt 2/4/8, max 16 kombinationer, fyra frysta tidsval; `application/geographic_budget.py` | Skyddar befintlig lokal API-profil. Regionala profilval och sökstrategi måste kopplas med aktuellt datastöd, inte bara nya tal. |
| HTTP-begäran | 8192 byte / 5 s, `api/limits.py` | Ruttparametrar, inte uppladdning av hela grid. |
| Äldre NetCDF-diagnostik | 10 MB / 100000 värden, `scripts/audit_copernicus.inspect_file` | Fryst småfixturkontroll, inte den regionala transportens gräns. Regional avkodning går via `inspect_marine` och styckevis statistik. |
| Äldre vinddiagnostik | 128 KB, 1024 rumspunkter, 25 tider; `scripts/audit_met_metadata.read_wind_sample` | Fryst lokalt referensprov. Regionalt uttag läser 83×138×31 med samma metadata-/talvalidering. MET-källkontraktet har 59 timsteg, inte flera veckor. |
| Native marin modell | Axlar ≤64, tider ≤25, disk ≤5 km; `infrastructure/native_marine.py` | Äldre hel-diskmodell omfattar även land och kan inte bara förstoras för fjordar. Regionalt uttag har 69×43×31. Kräver segmentstöd/reservpolicy, inte bara högre minnesbudget. |
| Geografisk modell | PoC 900 m, AEQD-rörelse 1500 m, native vindhölje 1000 m; respektive adapter | Befintligt kvalificerat modellområde. Utvidgas med explicit regional rörelse-/segmentmodell i nästa leverans; JSON-budgeten låtsas inte upphäva dessa spärrar. |
| Polygoner | 3–128 hörn; `prototype/polygon.py` | Exakt enkelhetskontroll med kvadratisk kostnad. Öppna kustkedjor får inte slutas med påhittade raka linjer. Regional landtopologi behöver separat materialiseras från befintligt uttag. |

De äldre referensgranskningarna behåller 1800 s och ursprungliga steggränser
för jämförbarhet. Det begränsar inte ordinarie verklig beräkning. Faktisk
simulerad gräns och serverbudget redovisas separat i nya ruttresultat.

Konfigurerad offshorekapacitet betyder inte att offshoreprofiler är levererade.
Ingen global skalbarhet eller kall/varm prestanda är ännu uppmätt för dem.

Den nya separata kustkompositionen har nu en uttrycklig 120 km-rörelseram och
segmentmodell för regionala uppskattningar; äldre 900/1 000/1 500 m-profiler
behåller sina gränser. Se coastal-voyage.md. Ett verkligt fall med redan sparad
geometrikandidat tog efter uppslagsmemoization 46,68 s inklusive inläsning och
presentation. Ny sökning för fria punkter, fler kandidater/avgångar och kall
gemensam cache ingår inte i det måttet. Regionala 60 s/64 MiB-gränser är kvar;
de behöver verifieras i den samlade interaktiva kopplingen innan aktivering.
Avslutande CLI-prov tog 62,10 s med oförändrat färdresultat. Den nu observerade
variationen 46,68–62,10 s innebär att 60 s ännu inte är robust kvalificerat,
även utan ny geometrisökning. Beständig återanvändning är ett konkret nästa steg.

Beständig materialiseringscache är nu levererad separat från hämtningscachen:
64 MiB/post, 256 MiB totalt och 256 MiB diskreserv. Verkliga nya processer gav
67,27 s vid miss och 41,82 s vid träff med byteidentiskt färdresultat; inläsning
13,61 respektive 6,49 s. Kallstarten överskrider 60 s. Se materialized-cache.md. Ingen budget höjs och
hela interaktiva jobbet med fri sökning/flera alternativ återstår att mäta.
