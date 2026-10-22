"""Render existing reports as self-contained HTML/SVG; never calculate a voyage."""
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
from math import isfinite
from pathlib import Path
from string import Template
from urllib.parse import quote

ASSETS = Path(__file__).resolve().parents[1] / 'frontend'
COLORS = ('#0369a1', '#7c3aed', '#0f766e', '#b45309')
NAMES = {'direct': 'Direkt', 'north': 'Norr', 'south': 'Söder'}


def text(value):
    return escape(str(value), quote=True)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError('Rapporten innehåller ett ogiltigt tal')
    return value


def metric(value, suffix=''):
    return '—' if value is None else f'{number(value):.2f}'.replace('.', ',') + suffix


def instant(value):
    if value is None:
        return '—'
    time = datetime.fromisoformat(value)
    if time.tzinfo is None or time.utcoffset() is None:
        raise ValueError('Rapporttider måste ha tidszon')
    time = time.astimezone(timezone.utc)
    label = time.strftime('%Y-%m-%d %H:%M:%S')
    if time.microsecond:
        label += '.'+f'{time.microsecond:06d}'.rstrip('0')
    return f'<time datetime="{text(value)}">{label} UTC</time>'


def route_name(value):
    return text(NAMES.get(value, value))


def outcome(route):
    status = route['status']
    if status == 'weather_limit':
        return 'exceeded', 'Konstaterat överskridande'
    if status == 'weather_unverified':
        return 'unknown', 'Otillräckligt bevis för modellgränserna'
    if status == 'data_unavailable':
        return 'unknown', 'Otillräckliga data'
    if status == 'arrived' and route.get('weather_segment_status') == 'verified' and route.get('arrival_weather_status') == 'passed_at_arrival':
        return 'verified', 'Verifierade modellgränser'
    if status == 'blocked':
        return 'neutral', 'Blockerat av syntetiskt hinder'
    if status == 'infeasible':
        return 'neutral', 'Ingen tillåten färd i båtmodellen'
    if status == 'arrived' and route.get('weather_segment_status') == 'not_applicable':
        return 'neutral', 'Ankomst utan färdsegment'
    return 'unknown', 'Inte segmentverifierad'


def point(value):
    return number(value['east']), number(value['north'])


def map_svg(routes, parameters, plot_id):
    start, target = point(parameters['position']), point(parameters['target'])
    planned, accepted = [], []
    points = [start, target]
    for route in routes:
        plan = [start, *(point(p) for p in route['candidate']['waypoints']), target]
        actual = [start, *(point(step['end_position']) for leg in route['legs'] for step in leg['steps'])]
        planned.append(plan); accepted.append(actual); points.extend(plan); points.extend(actual)
    obstacles = parameters['obstacles']
    for obstacle in obstacles:
        margin = number(obstacle['margin_m'])
        points.extend(((number(obstacle['min_east'])-margin, number(obstacle['min_north'])-margin),
                       (number(obstacle['max_east'])+margin, number(obstacle['max_north'])+margin)))
    xs, ys = zip(*points)
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    width, height, pad = 720, 340, 40
    xspan, yspan = max(xmax-xmin, 20), max(ymax-ymin, 20)
    number(xspan); number(yspan)
    scale = min((width-2*pad)/xspan, (height-2*pad)/yspan)
    xoffset, yoffset = (width-(xmax-xmin)*scale)/2, (height-(ymax-ymin)*scale)/2
    def xy(p):
        return xoffset+(p[0]-xmin)*scale, height-yoffset-(p[1]-ymin)*scale
    def coords(path):
        return ' '.join(f'{number(x):.3f},{number(y):.3f}' for x,y in map(xy,path))
    shapes = []
    for obstacle in obstacles:
        low = point({'east': obstacle['min_east'], 'north': obstacle['min_north']})
        high = point({'east': obstacle['max_east'], 'north': obstacle['max_north']})
        margin = number(obstacle['margin_m'])
        x, y = xy((low[0]-margin, high[1]+margin))
        w, h = (high[0]-low[0]+2*margin)*scale, (high[1]-low[1]+2*margin)*scale
        shapes.append(f'<rect class="obstacle" x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" fill="#e6d0ad" stroke="#9a7033"><title>{text(obstacle["name"])}; marginal {metric(margin," m")}</title></rect>')
    keys=[]
    for i, route in enumerate(routes):
        color = COLORS[i % len(COLORS)]
        label = route_name(route['candidate']['name'])
        shapes.append(f'<polyline class="planned" points="{coords(planned[i])}" stroke="{color}"><title>{label}: angiven kandidat, inte verifierad bana</title></polyline>')
        if len(accepted[i])>1:
            shapes.append(f'<polyline class="accepted" points="{coords(accepted[i])}" stroke="{color}"><title>{label}: accepterad integrerad delbana</title></polyline>')
        keys.append(f'<span><i style="background:{color}"></i>{label}</span>')
    for p,label,fill in ((start,'Start','#152d3b'),(target,'Mål','#fff')):
        x,y=xy(p)
        shapes.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="5" fill="{fill}" stroke="#152d3b"/><text x="{x+8:.3f}" y="{y-9:.3f}">{label}</text>')
    shapes.append(f'<text x="12" y="24">Norr ↑ · öster → · lokala meter</text><text x="12" y="328">Öst {metric(xmin)}…{metric(xmax)} m · nord {metric(ymin)}…{metric(ymax)} m</text>')
    description = 'Streckade linjer visar angivna kandidater. Heldragna linjer visar endast accepterad integrerad delbana. Rektanglar är syntetiska hinder inklusive marginal.'
    return (f'<figure class="map"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{plot_id}-title {plot_id}-desc">'
            f'<title id="{plot_id}-title">Kandidatrutter i lokalt plan</title><desc id="{plot_id}-desc">{description}</desc>'
            + ''.join(shapes) + '</svg><div class="route-key">'+''.join(keys)+'</div>'
            f'<figcaption>{description} Ingen sjökarta. Hinder: {len(obstacles)}.</figcaption></figure>')


def route_row(route):
    category, label = outcome(route)
    reason = f'<span class="reason">{text(route["reason"])}</span>' if route['reason'] else ''
    return (f'<tr data-status="{text(route["status"])}"><td class="route-name">{route_name(route["candidate"]["name"])}</td>'
            f'<td><span class="badge {category}">{label}</span>{reason}</td>'
            f'<td class="metric">{metric(route["travel_seconds"]," s")}</td>'
            f'<td class="metric">{instant(route["arrival_time"])}</td>'
            f'<td class="metric">{metric(route["comfort_exposure"])}</td></tr>')


def audit_routes(routes):
    items=[]
    for route in routes:
        evidence=[]
        for leg in route['legs']:
            failure=leg.get('weather_segment_failure')
            if failure:
                witness=failure.get('witness')
                detail = 'Utan överträdelsevittne; konservativt bevis eller stöd otillräckligt.'
                if witness:
                    detail=(f'Vittne för {text(witness["product"])} vid {instant(witness["time"])}; '
                            f'position {metric(witness["position"]["east"])} / {metric(witness["position"]["north"])} m.')
                evidence.append(f'<p>{text(failure["status"])} · {text(failure["method"])}. {detail}</p>')
        items.append(f'<li><strong>{route_name(route["candidate"]["name"])}</strong>: {text(route.get("weather_segment_status","unknown"))}; '
                     f'ankomstkontroll {text(route.get("arrival_weather_status","unknown"))}. Accepterad tid före slut/avbrott: {metric(route["elapsed_seconds"]," s")}.'+''.join(evidence)+'</li>')
    return '<details class="audit"><summary>Kontrollstatus och avbrottsbevis</summary><ul>'+''.join(items)+'</ul></details>'


def objective(label, route):
    value='Ingen verifierad kandidat i denna rapport.' if route is None else (
        f'{route_name(route["candidate"])} · avgång {instant(route["departure_time"])}<br>'
        f'Restid {metric(route["travel_seconds"]," s")} · ankomst {instant(route["arrival_time"])}')
    return f'<div class="objective"><strong>{label}</strong><p>{value}</p></div>'


SUPPORTED_SCHEMA_VERSIONS = (1, 2)

BOAT_MODEL_LABELS = {'sailboat': 'Segelbåt (uppskattad polar)',
                     'motorboat': 'Motorbåt (uppskattad konstantfart)'}

# Schema 1 reports have no ``boat_model`` key; the boat class is the only hint.
LEGACY_BOAT_CLASS_LABELS = {'PolarBoat': 'Uppskattad segelpolar',
                            'ConstantSpeedBoat': 'Uppskattad konstantfartsmodell'}

UNKNOWN_BOAT_MODEL_LABEL = 'Uppskattad båttyp: okänd'


def reject_constant(value):
    """Reject non-finite JSON constants such as NaN and Infinity."""
    raise ValueError('Icke-finita JSON-tal stöds inte')


def boat_model_label(manifest):
    """Return the display label for the manifest boat model.

    Schema 2 stores the model name in ``manifest.boat.boat_model``. Schema 1
    reports have no such key, so the label is derived from the known boat
    class in ``manifest.boat.model``. Unknown names are shown verbatim rather
    than hidden, and an unknown or missing boat class is reported explicitly
    as unknown instead of being guessed as a constant-speed model.

    Unknown names are still marked as estimated data and are HTML-escaped,
    because the name comes from a user-supplied report file.

    Args:
        manifest: The report manifest mapping.

    Returns:
        A short human-readable, HTML-escaped label for the boat model.
    """
    boat = manifest.get('boat') or {}
    name = boat.get('boat_model')
    if name is None:
        return LEGACY_BOAT_CLASS_LABELS.get(boat.get('model'), UNKNOWN_BOAT_MODEL_LABEL)
    label = BOAT_MODEL_LABELS.get(name)
    if label is None:
        return f'Uppskattad modell: {text(name)}'
    return label


def load_report(raw):
    """Parse and validate a report, accepting every supported schema version."""
    data=json.loads(raw, parse_constant=reject_constant)
    version=data['manifest']['schema_version']
    if type(version) is not int or version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError('Rapportens schemaversion stöds inte')
    if not data['comparison']['departures']:
        raise ValueError('Rapporten saknar undersökta avgångar')
    return data


def scenario_body(title, raw, index):
    """Render one scenario section from an existing report.

    Args:
        title: Human-readable scenario title, escaped on output.
        raw: The immutable report JSON string.
        index: Zero-based scenario index used for element ids.

    Returns:
        An HTML ``<details>`` fragment for the scenario.

    Raises:
        ValueError: If the report is invalid or incomplete.
    """
    data=load_report(raw); manifest=data['manifest']; comparison=data['comparison']; parameters=manifest['parameters']
    boat=manifest['boat']; model=boat_model_label(manifest)
    if not manifest.get('boat_data_estimated'):
        model='Båtmodell: uppskattningsstatus okänd'
    meta=[('Dataset',text(manifest['dataset_id'])),('Datasetversion',text(manifest['dataset_version'])),
          ('Båtmodell',model),('Fryst planeringstid',instant(comparison['planning_time'])),
          ('Hårda gränser',metric(parameters['weather_policy']['max_wind_m_s'],' m/s markvind')+' / '+metric(parameters['weather_policy']['max_wave_height_m'],' m Hs')),
          ('Extra komfortrestid',metric(parameters['max_comfort_extra_seconds'],' s, vid samma avgång'))]
    content='<dl class="meta">'+''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k,v in meta)+'</dl>'
    content+='<div class="objectives">'+objective('Kortast beräknad restid',comparison['shortest_travel'])+objective('Tidigast beräknad ankomst',comparison['earliest_arrival'])+'</div>'
    criterion=comparison['selection_criterion']
    criteria={'earliest_arrival':'tidigast ankomst','shortest_travel_time':'kortast restid'}
    content+='<p class="empty-note">'+('Inget generellt avgångsval: inget urvalskriterium begärt.' if criterion is None else 'Uttryckligt avgångskriterium: '+text(criteria.get(criterion,criterion)))+'</p>'
    content+=f'<p class="scenario-description">{text(comparison["scope"])}</p>'
    for d,departure in enumerate(comparison['departures']):
        report=departure['routes']; routes=report['candidates']
        content+=f'<section class="departure"><header class="departure-header"><div><h3>Avgång {instant(departure["departure_time"])}</h3><p>{len(routes)} explicit angivna kandidater</p></div></header>'
        fastest,comfortable=report['fastest_candidate'],report['comfortable_candidate']
        content+='<div class="choices"><span class="choice">Snabbaste verifierade kandidat: '+('—' if fastest is None else route_name(fastest))+'</span><span class="choice">Bekvämaste verifierade kandidat: '+('—' if comfortable is None else route_name(comfortable))+'</span></div>'
        if fastest is None:
            content+='<p class="unverified-message"><strong>Ingen verifierad kandidatrutt vid denna avgång.</strong> Andra rutter och avgångstider kan vara möjliga. Utfallet gäller bara den undersökta kandidatmängden och modellens kontroller.</p>'
        content+=map_svg(routes,parameters,f's{index}-d{d}')
        content+='<div class="table-scroll"><table><caption class="empty-note">Kompletta kandidatresultat; — betyder att godkänd restid, ankomst eller exponering saknas.</caption><thead><tr><th scope="col">Rutt</th><th scope="col">Kontrollresultat</th><th scope="col">Restid</th><th scope="col">Ankomst</th><th scope="col">Syntetisk exponering</th></tr></thead><tbody>'
        content+=''.join(route_row(route) for route in routes)+'</tbody></table></div>'+audit_routes(routes)+'</section>'
    fields=[('Algoritm',text(manifest['algorithm_version'])),('Indata-SHA-256',text(manifest['input_sha256'])),
            ('Dataset-SHA-256',text(manifest['dataset_sha256'])),('Båt-SHA-256',text(manifest['boat_sha256'])),
            ('Rapport-SHA-256',sha256(raw.encode()).hexdigest()),('Kontrollomfattning',text(comparison['departures'][0]['routes']['weather_verification_scope'])),
            ('Båtantaganden',text(' '.join(boat['assumptions'])))]
    content+='<details class="audit"><summary>Versioner, antaganden och rapportidentitet</summary><dl>'+''.join(f'<dt>{k}</dt><dd class="hash">{v}</dd>' for k,v in fields)+'</dl></details>'
    content+=f'<a class="download" download="seaparser-scenario-{index}.json" href="data:application/json;charset=utf-8,{quote(raw,safe="")}">Hämta full rapport (JSON)</a>'
    return f'<details class="scenario" id="scenario-{index}"'+(' open' if index==0 else '')+f'><summary>{text(title)}</summary><div class="scenario-body">{content}</div></details>'


def render_reports(scenarios):
    """Consume immutable JSON strings; all report text escaped, no scripts/fetches."""
    bodies=[]; nav=[]
    try:
        for index,(title,raw) in enumerate(scenarios):
            if index>=10:
                raise ValueError('Högst tio rapportscenarier får visas')
            bodies.append(scenario_body(title,raw,index))
            nav.append(f'<a href="#scenario-{index}">{text(title)}</a>')
        if not bodies:
            raise ValueError('Minst en rapport krävs')
        template=Template((ASSETS/'scenario-demo.html').read_text())
        return template.substitute(STYLE=(ASSETS/'scenario-demo.css').read_text(),NAV=''.join(nav),SCENARIOS=''.join(bodies))
    except (KeyError,TypeError,AttributeError) as error:
        raise ValueError('Ofullständig eller felaktig planeringsrapport') from error


def render_report(raw, title='Offline-scenario'):
    return render_reports(((title,raw),))
