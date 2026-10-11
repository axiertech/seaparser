# Förslag: strömhantering och avdrift

Status: lokalt specifikationsförslag. AGENTS.md och befintlig docs/ saknades i
arbetsytan vid skrivning. Förslaget har därför inte stämts av mot projektets
instruktioner, datamodell eller implementation.

## Hastighet och position

För varje integrationssteg ska båtens hastighetsvektor genom vattnet kombineras
med strömvektorn vid stegets beräknade position och tid:

`v_mark(p, t) = v_vatten(p, t) + v_ström(p, t)`.

Alla vektorer ska uttryckas i samma lokala koordinatsystem: öst och nord,
med hastighet i m/s och tid i UTC. Riktningar anges mot den riktning rörelsen
sker, i grader medurs från geografisk nord. En hastighet s och riktning θ ger
`v_öst = s sin(θ)` och `v_nord = s cos(θ)`. Konvertera knop till m/s före
integration (1 knop = 1852/3600 m/s). Normalisera leverantörens riktningskonvention
innan strömdata används.

Fart över grund (SOG) är längden av v_mark. Kurs över grund (COG) beräknas som
`atan2(v_mark,öst, v_mark,nord)` och normaliseras till [0, 360). Vid nollfart
är COG odefinierad. Skilj på stävriktning, rörelseriktning genom vattnet och COG.
GPS-baserad SOG får inte användas som fart genom vattnet och sedan få ström
adderad igen.

Strömmen hämtas för den beräknade positionen och prognosens giltighetstid,
inte enbart för startpunkten eller avgångstiden. Interpolera öst- och
nordkomponenterna rumsligt och tidsmässigt inom datakällans giltiga täckning.
Interpolera inte riktningar direkt över exempelvis 359°/1°, och interpolera
inte genom land eller ogiltiga datapunkter. Bevara källa, prognosversion,
giltighetstid och kvalitetsstatus för resultatets spårbarhet.

Som föreslagen integration används mittpunktsmetoden: beräkna hastigheten vid
`(p_n, t_n)`, prediktera positionen efter ett halvt tidssteg och utvärdera både
båtmodell och ström igen vid `(p_halv, t_n + Δt/2)`. Uppdatera slutpositionen
med mittpunktens markhastighet och tiden med Δt. Förflyttningen ska omvandlas
geodetiskt till latitud/longitud; addera inte meter direkt till grader.
Steglängden ska kunna minskas vid skarpa strömgradienter och datagränser.
Val av steglängd och toleranser behöver fastställas i implementationen.

ETA ska följa den integrerade banan och faktisk ankomst till mål eller
delmål. Dividera inte hela ruttlängden med SOG när rörelsen går åt sidan.
Kontrollera den avdrivna banan mot ruttens befintliga hinder- och djupkrav.

## Avdrift för segel- och motorbåtar

Strömavdrift gäller båda båttyperna och ingår i v_ström. Vindorsakad avdrift
relativt vattnet ska ingå i v_vatten, med dokumenterad modell och indata.
Samma avdrift får inte både byggas in i båtmodellen och adderas separat.

- Segelbåt: beräkna fart genom vattnet från tillämplig polar och vindmodell.
  Låt en signerad avdriftsvinkel λ korrigera stävriktningen ψ så att
  rörelseriktningen genom vattnet är `ψ + λ`. Positiv λ betyder avdrift medurs
  från stäven. Tecken och storlek ska följa bog, vind och tillgänglig
  båtmodell. Kontrollera om polaren redan omfattar avdrift.
- Motorbåt: använd fart genom vattnet från motor-/båtprofilen. Tillämpa
  tillgänglig vindavdriftsmodell även under motorgång; båttypen innebär inte
  automatiskt noll avdrift. En separat lateral hastighet kan användas i stället
  för avdriftsvinkel om modellen levererar detta, men inte för samma effekt
  samtidigt. Vid stillaliggande genom vattnet kan ström och modellerad
  vindavdrift fortfarande flytta båten.

Saknas vindavdriftsmodell eller nödvändiga indata används som föreslagen
fallback noll vindavdrift, redovisad som ett eget antagande för berörda sträckor
och båttyper. Detta får inte dölja eventuell känd strömavdrift.

Skilj i beräkningen mellan bibehållen stävriktning och kompensation för att
hålla önskad kurs över grund. Vid kurskompensation ska båtens tvärkomponent
genom vattnet balansera strömmens tvärkomponent, inklusive vindavdrift.
För segelbåt måste den korrigerade stävriktningen åter utvärderas mot polar
och tillåtna vindvinklar. Om ingen tillåten stävriktning ger önskad kurs med
positiv framfart ska sträckan markeras som ej genomförbar under dessa villkor.
Noll eller negativ framfart mot målet får inte ge en vanlig positiv ETA.

## Saknade strömdata som antagande

Saknade, ogiltiga eller otäckande strömdata ska skiljas från en observerad
eller prognostiserad nollström. Som föreslagen fallback används
`v_ström = (0, 0)` för berörda steg, med explicit antagande:

> Strömdata saknas för delar av rutten. Där antas strömmen vara 0 m/s.
> Beräknad bana och ankomsttid bygger på detta antagande.

Antagandet ska följa resultatet i visning och export och ange berörd sträcka,
tidsintervall och orsak, exempelvis lucka i data eller prognosens slut.
Markera delvis täckning separat från helt saknade data. Använd giltiga
strömdata där de finns. Extrapolera inte tyst utanför källa eller tidsintervall.
Redovisa antagandet om ström separat från antagandet om vindavdrift.

## Planerade tester

Testerna nedan är en plan, inte körda implementationstester. Använd syntetiska
konstanta strömfält och en båtmodell med 5 knop genom vattnet. Kör grundfallen
för både segel- och motorbåt med vindavdrift uttryckligen satt till noll.
Östgående stävriktning är 90°. För positionsexemplen används ett lokalt
öst/nord-plan; integration i latitud/longitud provas separat.

| Fall | Ström | Förväntat resultat |
| --- | --- | --- |
| Medström | 2 knop österut | SOG 7 knop, COG 90°, 7 nautiska mil österut efter 1 h; ETA 1 h till mål 7 nautiska mil österut. |
| Motström | 2 knop västerut | SOG 3 knop, COG 90°, 3 nautiska mil österut efter 1 h; ETA 1 h till mål 3 nautiska mil österut. |
| Sidoström, bibehållen stävriktning | 2 knop norrut | Markvektor (5, 2) knop, SOG √29 ≈ 5,385 knop, COG ≈ 68,199°; efter 1 h ligger båten 5 nautiska mil österut och 2 norrut och har inte nått målet (5, 0). |
| Sidoström, kompenserad kurs | 2 knop norrut | För konstant tillgänglig fart 5 knop: stävriktning ≈ 113,578°, markvektor (√21, 0) knop, COG 90° och SOG ≈ 4,583 knop. |
| Motström lika stark som båtfarten | 5 knop västerut | Noll markhastighet, odefinierad COG, ingen ändlig ETA till mål österut. |
| Motström starkare än båtfarten | 6 knop västerut | Markhastighet 1 knop västerut, COG 270°, ingen framfart mot mål österut. |
| Sidoström som inte kan kompenseras | 6 knop norrut | Ingen kurskompensation möjlig vid högst 5 knop genom vattnet; önskad östgående kurs markeras ej genomförbar. |

Komplettera grundfallen med följande tester:

1. För båda båttyperna: sätt stävriktning 90°, signerad avdriftsvinkel +10°,
   fart 5 knop och ström 2 knop norrut. Förvänta v_mark i knop
   `(5 cos(10°), 2 - 5 sin(10°))`. Kontrollera separat att v_vatten före
   strömtillägg är `(5 cos(10°), -5 sin(10°))`. Prova motsatt tecken och
   segelbåtens byte av bog samt att avdrift inte räknas dubbelt.
2. För segelbåt med kurskompensation: använd en polar med kursberoende fart
   och otillåtna vindvinklar. Kontrollera att korrigerad stävriktning leder
   till ny polarutvärdering och att omöjliga lösningar identifieras.
3. För motorbåt: prova separat lateral vindavdriftsmodell samt noll fart
   genom vattnet med känd ström; förvänta att båten driver med strömmen när
   vindavdriften är noll. Saknad vindavdriftsmodell ska ge eget antagande.
4. Använd ett analytiskt strömfält som varierar med position och UTC-tid.
   Verifiera uppslag vid predikterad mittpunkt och tid, komponentinterpolation
   och att senare ruttsteg inte återanvänder startpunktens ström. Halvera
   tidssteget och kontrollera konvergens mot en oberoende referenslösning.
5. Prova helt och delvis saknade strömdata, ogiltiga värden, landmask och
   passage bortom prognosens sluttid. Förvänta nollström enbart där data
   saknas samt spårbart antagande i resultat, visning och export. Giltig
   nollström ska inte ge ett antagande om saknade data.
6. Prova omvandling av knop/m/s och riktning, bland annat 359°/1°, samt
   geodetisk förflyttning på olika latituder. Verifiera att avdriven bana
   används vid hinderkontroll och målpassage.

Föreslagna acceptanstoleranser för konstanta vektorfall: högst 0,001 knop
i hastighet och 0,01° i definierad COG. Position och ETA ska jämföras med
analytiska värden med toleranser anpassade till integrationssteg och
målpassage; fastställ dessa innan implementationstester godkänns.
