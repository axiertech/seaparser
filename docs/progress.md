# SeaParser – verifierad status och arbetsordning

## Arbetsform

Lokala, reversibla leveranser inom axiertech/seaparser. Befintliga lokala
ändringar bevaras. Ingen installation, databasändring, publicering eller push.
Dokumentet uppdateras efter varje genomförd leverans. Ingen bakgrundsaktivitet
förutsätts efter att arbetet har stannat för granskning.

## Granskning 2026-10-11

AGENTS.md, samtliga docs/ vid start samt prototypens kod och tester lästa.
Utgångskontroll: `python3 -B -m unittest discover -s prototype/tests`:
24 tester godkända, 0,136 s. Detta verifierar syntetiska referenser, inte navigation.

- Rörelse: vatten- och strömvektorer summeras i lokalt öst/nord-plan;
  explicit mittpunktsmetod utvärderar position och UTC-tid på nytt.
- Kurskompensation: tvärström balanseras vid konstant vattenfart. För stark
  tvärström och otillräcklig framdrift avbryter, utan vanlig positiv restid.
- Målpassage: tolerans 0,01 m, förkortat slutsteg och bisektion vid
  överskjutning. Befintliga referenser och halverat steg passerar.
- Ingen SQL/HTTP/UI i beräkningen. Modell, miljö och JSON-presentation separerade.
- Kvarstående: vind används inte, ingen polar eller hinderkontroll vid start.
  Kontroller av miljö gäller bara uppslag; luckor mellan dem kan missas.
  Bisektion antar ett lämpligt lokalt förlopp; inga generella felgarantier.
  Målfärd är kopplad till konstantmodellen och måste generaliseras före polar.
  `steering_degrees` i äldre rörelseexport är vattenvektorns riktning och
  motsvarar stävriktning endast vid noll vindavdrift.

## Leverans 1 – granskning och syntetiska hinder (verifierad 2026-10-11)

Acceptanskriterier före implementation:

1. Hela integrerade segmentet kontrolleras mot slutna, axelparallella
   rektanglar, även när båda ändpunkterna ligger utanför hindret.
2. Kantkontakt, hörnkontakt och start/mål i hinder blockeras, utan att
   måltoleransen eller stort tidssteg kan kringgå kontrollen.
3. Rörelsesimulering ger uttryckligt fel; målfärd ger `blocked`, utan restid
   och utan att det blockerade steget läggs till slutförd bana.
4. Hinder bakom målet får inte blockera en förkortad målpassage.
5. Befintliga tester samt nya geometriska och integrerade referenser passerar.
6. Avtagande tidsberoende ström jämförs med handräknad restid, grovt och
   halverat steg; nära mål kontrolleras inom positionstolerans.

Antaganden: syntetiska statiska rektanglar, meter i lokalt plan, slutna
hindergränser. Valfri marginal expanderar rektangeln; ingen verklig
båtgeometri, sjökortsnoggrannhet eller navigerbarhet följer av detta.

Verifiering efter implementation: `python3 -B -m unittest discover -s
prototype/tests -v` gav 32 godkända tester, 0,140 s. Alla 24 tidigare tester
passerar. Åtta nya tester omfattar hela segment, riktningar, kant/hörn,
validering/marginal, strömavdriven rörelse, blockerat start/mål, stort och
mindre tidssteg, hinder bakom mål och målpassage med avtagande ström.
För avtagande ström används x/1852=7*u-u², u=t/3600, mål 5 NM och
handräknad restid 3600*(7-sqrt(29))/2. Steg 120/60 s håller 0,01 s tidstolerans.

Ingen av de integrerade blockerade förflyttningarna accepteras. `blocked`
exporteras med orsak och bara tidigare slutförda steg. Rörelsesimulering
kastar `ObstacleCollision`; målfärden returnerar status. Hinder bakom målet
kontrolleras inte som om båten fortsatt efter ankomst.

Nya filer: prototype/obstacles.py, prototype/tests/test_obstacles.py och
detta dokument. Ändrade i denna leverans: prototype/calculation.py,
prototype/README.md och docs/decisions.md. Befintliga lokala ändringar bevarade.

Begränsning: kontrollen avser den numeriska banans raka segment, inte en
okänd fysisk kurva mellan uppslag. Rektanglar med marginal är syntetiska
förbjudna områden, inte landmask, djupdata eller bevis på navigerbarhet.
Ingen omväg väljs automatiskt ännu. Leveransen stannar här för granskning.

## Nästa leveranser i beroendeordning

1. Enkel begränsad referenssökning över fördefinierade vägpunkter och hela
   alternativa färder. Behåll tidsberoende tillstånd, undvik att slå ihop
   olika ankomsttider per plats. Ange sökgränser och att ingen global optimalitet
   utanför kandidatmängden utlovas. Testa omväg och inget genomförbart alternativ.
2. Generalisera målfärdens båtprestanda och inför spårbar syntetisk polar,
   förbjudna vindvinklar och konsekventa manöverantaganden. Kurskompensation
   måste återutvärdera kursberoende fart; konstantfartsformeln räcker inte.
3. Testa rumsligt/tidsberoende vind och ström längs flerstegsrutter, giltighet,
   saknade data och halverade tidssteg mot oberoende referenser.
4. Definiera syntetiskt komfortmått och hårda vind-/sjögränser, jämför snabbast
   och bekvämast under exakt samma gränser. Testa att komfort aldrig kan väga
   bort förbjudna områden, vindvinklar, otillräckliga data eller hårda gränser.

Verkliga polarer/prognoser, geodetik, djup, sjökort, prognosålder, UI/editor,
API, databas och drift återstår. Prototypen är inte verifierad för verklig navigation.
