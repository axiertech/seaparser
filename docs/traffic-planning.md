# Lågprioriterad trafikbelastning för planering

Design, inte implementerad funktion. Användarens senaste beslut 2026-10-12
ersätter den tidigare önskan om deterministisk mötesanalys och löpande
trafikövervakning. Väderrouting, ström, komfort och avgångstider är huvudspår.
Ingen GPS-följning, individuell mötesprognos, kollisionsvarning eller
undanmanöverrådgivning ingår i första omfattningen.

## Separation och fryst trafikunderlag

En framtida infrastruktursadapter normaliserar färdighämtade AIS-data till ett
helt materialiserat, oföränderligt TrafficSnapshot. Transport sker före
planeringsanropet. Ruttmotorn ska inte fråga AIS-tjänster eller läsa en pågående
ström; en eventuell presentation samordnar belastningsinformation med den redan
beräknade tidsatta banan. Uppdaterad trafik blir en separat märkt informations-
version, inte tyst ändrad ruttprognos. Ingen bakgrundsövervakning startas.

Leverantörsoberoende kontrakt att verifiera före implementation:

| Objekt/fält | Betydelse och krav |
| --- | --- |
| snapshot_id/version | Identifierar fryst innehåll; fingerprint av normaliserade observationer och täckningsmetadata |
| source/license/attribution | Separat källa och återanvändningsvillkor; inga åtkomsttoken i modellen |
| observation_window | Explicit UTC-intervall för det observerade materialet, skilt från planerad framtida passagetid |
| fetched_at | När SeaParser skapade underlaget; får inte ersätta positionens datatid |
| geographic_coverage/coverage_quality | Område och tidsfönster som mottagningen faktiskt kan beskriva; unknown/limited/supported med metod och luckor |
| vessel_identity | Namnrymd + källidentitet; MMSI där den finns. Identitet och källa behövs för deduplicering, men är inte bevis på autenticitet |
| position/reference | WGS84 latitud/longitud med känd referens; eventuell omräkning till planens lokala ram sker utanför motorn |
| position_time | När positionen avser, UTC eller explicit unknown; tidpunkten får inte uppfinnas från hämtningen |
| received_at | När rapporten mottogs av källan, UTC eller unknown; skilt från position_time och fetched_at |
| sog_m_s | Fart över grund, m/s efter normalisering; missing/invalid är inte noll |
| cog_true_degrees | Kurs över grund medurs från sann nord; separat från heading och möjlig att sakna även vid känd position |
| quality_status/reasons | known/limited/stale/invalid/unknown med fältspecifika orsaker, ålder och kvalitetsmetod |

AIS-SOG/COG beskriver redan rörelse över grund. Ström får **inte** adderas till
AIS-farten. Ström används fortsatt i båtens färdmodell för vattenfart→markfart.
Detta kontrakt används här för kvalitets-/mönsterinformation, inte för att
projektera enskilda fartyg till framtida möten.

## Belastningsinformation och passagetid

Räkna observerade **unika fartyg**, inte meddelanden, per deklarerad ruttkorridor
eller segment och observationsfönster. Korridorbredd, tidsfönster, åldersgräns,
täckningskrav och klassgränser ska vara explicita, versionshanterade parametrar.
Duplicerade rapporter och aggregerade källor får inte öka antalet fartyg.

Visa observerat antal med datatid och käll-/täckningsstatus. Framtida passagetid
från ruttberäkningen visas separat. En färsk bild nu är inte en prognos över
trafiken vid senare ankomst. För ett framtida belastningsmönster krävs ett
historiskt underlag med tillräcklig tidsmässig/geografisk täckning, urvalskvalitet
och dokumenterad relevans för aktuell veckodag/tid/säsong. Visa då ett villkorat
mönster, observationstid och osäkerhet, aldrig säker kännedom om framtida fartyg.

Kombinera informationen med planerad passagetid och kända dagsljus-/mörker-,
sikt- och väderuppgifter. Saknad sikt/dagsljus/mönsterkvalitet ska synas som
okänd kontext. Inga sådana datakällor eller graderingsvikter väljs i denna
leverans. En senare graderingsmodell måste skilja belastning från säkerhetsrisk
och får inte upphäva hårda vädergränser. Låg/saknad täckning, gamla rapporter,
otillräckliga positionstider eller saknade observationer ger **okänd**, inte
fri passage. Noll observerat är endast noll rapporterat i det definierade fönstret.

## Senare syntetiska acceptansprov

När detta lågprioriterade spår blir aktuellt: prova kända antal/klassgränser,
deduplicering, gamla/okända positionstider, mottagningsfördröjning, täckningsluckor,
tom bild med svag täckning, olika planerade passagetider utan framtidsextrapolation,
historiska mönsters otillräcklighet och dagsljus-/sikt-/väderkontext. Identiska
frysta indata ska ge samma information. Kurser/farter normaliseras utan extra
ström; saknad COG får inte bli godtycklig rörelseriktning. Ursprungliga CPA-/
korsnings-/upphinnande-/mötande manöverprov utgår ur första omfattningen.
Detta är en testplan; inga AIS-tester eller AIS-analyser har körts/implementerats.
