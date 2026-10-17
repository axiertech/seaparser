# Native marin geometri och större landgranskning

`CopernicusMarineAdapter.normalize(..., native_radius_m=...)` kan nu behålla
WAV/PHY på respektive egna latitud-/longitudaxlar. Samma fält-, djup-, mask- och
metadatanormalisering används i båda representationslägena; ingen andra adapter
eller omgridning är införd. Standardläget och dess 1 m-gräns för räta lokala
axlar är oförändrade.

[Granskningssidan](../artifacts/native-marine-review/index.html) visar det nya
landunderlagets avvisning av den gamla startpunkten. Den är **inte en godkänd
rutt**. [Komponentrapporten](../artifacts/native-marine-review/report.json)
och ett [separat uttryckligen angivet segmentprov](../artifacts/native-marine-review/specified-route.json)
visar vilka kontroller som faktiskt utförts. Ingen större routing är aktiverad.

## Geometriskt stöd utan räta axlar

Punktuppslag transformerar lokal WGS84-AEQD till geografiska koordinater och
interpolerar vektorkomponenter i produktens egna åtta rumtidshörn. Vågornas
FRÅN-riktning interpoleras som komponenter, inte som skalära grader. Ström och
vågor har separata axlar och stöd. Saknade hörn, ogiltiga värden, maskluckor,
extrapolation och exklusiv slutgiltighet avvisas.

Hela segmentets lokala räta bana ligger i en disk om båda ändpunkterna ligger
i disken, eftersom disken är konvex. WGS84:s ytelement ger
`ds²=M² dφ² + (N cosφ)² dλ²`. Med a=6378137 m och
f=1/298,257223563 gäller M≥a(1−e²)>6 300 000 m och N≥a>6 300 000 m.
Därmed omsluts alla geodesiska radier från AEQD-origo av:

- |Δφ| ≤ (r+1 m)/6 300 000.
- |Δλ| ≤ (r+1 m)/(6 300 000 cos(|φ₀|+|Δφ|max)).

Först omsluts latituden, därefter longituden med det minsta cosinusvärdet i
latitudintervallet. Gränserna rundas utåt; 1 m är separat numerisk stödreserv,
inte höjd tolerans för den gamla räta-axlar-representationen. Det analytiska
argumentet avser hela disken, inte en samling provpunkter. Tester mot geodesiska
referenser är numeriska regressionsprov, inte själva områdesbeviset.

[PROJ:s AEQD-definition](https://proj.org/en/stable/operations/projections/aeqd.html)
och [ellipsoidparametrar](https://proj.org/en/stable/usage/ellipsoids.html)
anger den använda projektionen och WGS84-parametrarna. Detta är ett bevis inom
den deklarerade koordinat-/interpolationsmodellen, inte käll-/datumkvalificering
eller maritim validering.

Varje native-grid måste omsluta hela denna skyddade box. Segmentkontrollen
kräver alla hörn i samtliga berörda nativeceller över hela diskboxen och hela
tidsintervallet. Den kan avvisa ett segment på grund av en lucka utanför själva
banan; detta konservativa resultat får inte klippas till ett positivt bevis.
Arbetsbudgeten hålls begränsad av befintlig certifieringsbudget, och inga
rumtidsceller hoppas över. Hs-gränsen jämförs exakt med det största källhörnet
via Fraction. Ett för högt hörn ger otillräckligt bevis; endast ett faktiskt
överskridande vid uppslag blir ett vittne. Komfort eller restid kan inte väga
bort detta.

Den frysta 17-oktober-bunten klarar det marina geometriska stödet för 2 000 m
radie. Ett 3 000 m långt segment över 1 200 s passerar hela denna omslutnings
rådatastöd. Källornas mask-/tids-/run-spärrar följer ändå med; ingen issued_at
antas eller skrivs tillbaka i adaptern. Native-läget accepterar högst 5 000 m
som komponentbudget, men avvisar exempelvis 5 000 m för denna verkliga bunt
när dess egna grid inte räcker. Detta ändrar inte routingens 900 m-tak.

## Större landunderlag och ett konkret stopp

Ett enda nytt OSM-uttag inom 11,55–11,66°E, 57,60–57,67°N gav 3 298 228 byte,
under 5 MB-gränsen. Råfilens SHA-256 är
`8aa06fc3b07c1e6bd8512084209b2e59cab6f3d547f8c873dbdeebf119ba8037`.
Den bevaras lokalt i `/tmp/seaparser-expanded-land-20261017/source.osm`.
Ingen marin data hämtades på nytt.

Offlineimporten gav [24 slutna ringar](../fixtures/vinga-land-expanded-20261017.geojson)
vars projicerade boxar berör en granskningsruta med radie 1 500 m och 10 m
marginal. Hela ringarna bevaras; inga kustsegment klipps bort. Öppna kedjor
som kan beröra rutan avvisas. Tre öppna kedjor ligger utanför denna yta.
Samtliga källnoder i de valda ringarna omsluts av befintliga konservativa
konvexa höljen. ODbL-attribution, way-versioner/tider, källa, hash, urvalsyta,
okänd fullständighet och okänt djup följer med. Det är inget navigerbarhetsbevis.

Den gamla lokala startpunkten (300,−400) ligger i höljet `osm-23053759`, som
inte ingår i det äldre sexpolygonutdraget. Den nya 17-oktober-kompositionen
använder därför det nya landunderlaget och avvisar punkten med endpoint_blocked.
Den får inte fortsätta med det gamla landutdraget för att få en ankomst.
Den äldre 13-oktober-jämförelsen behålls som uttryckligen historisk, villkorad
modell med sitt frysta landunderlag; den utgör inte bevis mot den nya källan.
Publik webbrot och tjänst är orörda.

## Komposition och nästa steg

Det namngivna alternativet
[development-weather-native-assumptions.json](../settings/development-weather-native-assumptions.json)
använder 17-oktober-bunten men behåller support_radius_m=900. Bara redan namngivna
metadataantaganden tillämpas, på frysta produktkopior. Originalens issued_at=None,
source_qualification=unverified och källhashar förblir separata från assumed_fields
samt result_qualification=conditional_on_assumptions. Ursprungliga WAV-etiketter
flyttas inte och fysisk tidsmedelssemantik kvalificeras inte.

Ett separat, uttryckligen angivet segment från (500,0) till (500,350) har
simulerats med samma motor, alla 24 landhöljen, verkligt native-väder och hårda
väder-/ankomstkontroller. Det anländer inom modellen på 144,521 s. Det är ett
kompositionsprov, inte resultat av automatisk kandidatsökning eller ett
navigationsråd. Båtprestanda är uppskattad och komfortmåttet ej validerat.

Reproducera utan nät eller publicering:

```bash
.venv/bin/python -B -m scripts.native_marine_review --output artifacts/native-marine-review
```

Innan större routing: välj ändpunkter som det nya landunderlaget tillåter,
hantera dess fler hinder med uppmätt begränsad kandidatsökning, verifiera hela
vind-/marin-/landstödet och koordinatramen för integrerad rörelse. Först därefter
kan 900 m-taket prövas för en avgränsad utökning. Native-maringeometrin är inte
ett generellt undantag från källspärrar, land, prognosålder eller absoluta gränser.
