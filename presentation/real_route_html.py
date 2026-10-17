"""Self-contained graphical review of an existing real-data route result."""
from html import escape
from infrastructure.land import FORWARD


def render(result):
    if result.get('data_quality',{}).get('weather') != 'real_frozen_with_assumptions':
        raise ValueError('Denna visning kräver verkliga vind-, våg- och strömdata')
    def path(coordinates):
        return ' '.join(f'{x:.3f},{-y:.3f}' for x,y in (FORWARD.transform(*p) for p in coordinates))
    shapes=''.join(f'<polygon points="{path(f["geometry"]["coordinates"][0])}"/>' for f in result['obstacles']['features'])
    routes=[];cards=[]
    colors=('#037e83','#b36118','#6552a4','#b33e69')
    for index,route in enumerate(result['alternatives']):
        identifier=escape(route['id'],quote=True);color=colors[index%len(colors)]
        geometry=[f for f in result['routes']['features'] if f['properties']['id']==route['id'] and f['geometry']['type']=='LineString']
        routes.append(f'<g data-route="{identifier}" style="stroke:{color}">'+''.join(
            f'<polyline points="{path(f["geometry"]["coordinates"])}" stroke-width="{5 if f["properties"]["kind"]=="accepted" else 2}" '+
            ('stroke-dasharray="9 7"' if f['properties']['kind']=='planned' else '')+'/>' for f in geometry)+'</g>')
        seconds=route['travel_seconds'];time='—' if seconds is None else f'{seconds/60:.2f} min'
        description='Beräknad med antaganden' if route['status']=='arrived' else route['status']
        objectives=(' · snabbast' if route['fastest'] else '')+(' · lägst modellkomfortkostnad' if route['comfortable'] else '')
        exposure='—' if route['comfort_exposure'] is None else f'{route["comfort_exposure"]:.1f}'
        cards.append(f'<button class="card" data-select="{identifier}" style="border-left-color:{color}"><strong>{escape(route["candidate"])} · {escape(route["departure_time"])[11:16]} UTC</strong><span>{time}{objectives}</span><span>{escape(description)} · komfortkostnad {exposure}</span><small>{escape(route["reason"] or "Hela integrerade segment har kontrollerats mot land, datastöd och valda vädergränser inom antagen modell.")}</small></button>')
    endpoints=''
    if result['alternatives']:
        points=result['alternatives'][0]['waypoints']
        for label,point in (('Start',points[0]),('Mål',points[-1])):
            x,y=FORWARD.transform(*point)
            endpoints+=f'<circle cx="{x:.3f}" cy="{-y:.3f}" r="9" fill="#163c49"/><text x="{x+18:.3f}" y="{-y+7:.3f}" font-size="24" fill="#163c49">{label}</text>'
    sampled=result['weather_at_start']
    sample_text=' · '.join(f'{label} {sampled[key]:.2f} {unit}' if sampled[key] is not None else f'{label}: okänd'
                          for label,key,unit in (('Vind','wind_m_s','m/s'),('Ström','current_m_s','m/s'),
                                                ('Hs','wave_height_m','m'),('Tm02','wave_period_seconds','s')))
    assumptions=''.join(f'<li>{escape(v)}</li>' for v in result['weather_provenance']['assumptions'].values())
    return '''<!doctype html><html lang="sv"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'">
<title>SeaParser · verkliga data vid Vinga</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef4f5;color:#173640;font:16px system-ui}main{max-width:1200px;margin:auto;padding:32px}h1{font-size:2.3rem;margin:8px 0}h2{font-size:1.15rem}.eyebrow{color:#197c80;letter-spacing:.1em;font-size:.8rem;font-weight:700}.notice{border-left:4px solid #b78023;background:#fff5db;padding:16px;line-height:1.6}.grid{display:grid;grid-template-columns:1.6fr 1fr;gap:24px;margin:24px 0}svg{width:100%;height:520px;background:#d5e9ec;border-radius:12px}polygon{fill:#d6c9ad;stroke:#8a7351;stroke-width:3}polyline{fill:none;stroke-linejoin:round}button{font:inherit;cursor:pointer}.card{display:block;text-align:left;width:100%;background:white;border:1px solid #c3d2d5;border-left:6px solid;padding:16px;border-radius:8px;margin-bottom:12px;color:inherit}.card span,.card small{display:block;margin-top:8px}.card small{line-height:1.5;color:#50646b}.selected{outline:3px solid #16777e}details{background:white;padding:18px;border-radius:8px;line-height:1.7}li{margin:12px 0}code{overflow-wrap:anywhere}.legend{font-size:.85rem;line-height:1.6}.meta{background:white;padding:16px;border-radius:8px}.muted{color:#526b72}footer{margin-top:24px;font-size:.85rem}@media(max-width:800px){main{padding:16px}.grid{grid-template-columns:1fr}svg{height:400px}}
</style><main><div class="eyebrow">SEAPARSER / UTVECKLINGSMILJÖ</div><h1>Ruttjämförelse vid Vinga</h1>
<p class="muted">MET-vind + Copernicus-vågor och ström · frysta verkliga data 13 oktober 2026 · två avgångar</p>
<div class="notice"><strong>Beräknad med uttryckliga antaganden.</strong> Källornas köridentitet, utfärdandetid och delar av tids-/masksemantiken är fortfarande overifierade. Resultatet gäller den konfigurerade modellen. Uppskattad konstantfartsbåt, '''+str(result['planning']['manifest']['boat']['configuration']['speed_knots'])+''' knop. Ingen aktuell prognos eller navigationsgaranti.</div>
<p class="meta">Vid start, '''+escape(sampled['time'][11:16])+''' UTC: '''+escape(sample_text)+'''</p>
<div class="grid"><section><svg viewBox="-740 -470 1450 970" role="img" aria-label="Verkligt OSM-land och beräknade ruttalternativ vid Vinga">'''+shapes+''.join(routes)+endpoints+'''</svg><p class="legend">Brunt: fryst OSM-land med konservativa routinghöljen och vald marginal. Streckat: planerade kandidatben. Heldraget: accepterade integrerade färdsegment. Klicka på ett alternativ för att markera dess bana.</p><button id="all">Visa alla alternativ</button></section><section><h2>Undersökta rutter och avgångar</h2>'''+''.join(cards)+'''</section></div>
<div class="meta">Valda hårda gränser: vind '''+str(result['selected_weather_limits']['wind_m_s'])+''' m/s · Hs '''+str(result['selected_weather_limits']['wave_height_m'])+''' m. Alla alternativ använder samma gränser. Komfortkostnaden är ett ej validerat exponeringsmått.</div>
<details open><summary><strong>Konfigurerade antaganden</strong></summary><ul>'''+assumptions+'''</ul></details><details><summary>Spårbarhet och begränsningar</summary><p>Verkliga frysta källor och hashvärden bevaras separat från antaganden. Ingen vind-, våg- eller strömserie är syntetisk.</p><p>Indata: <code>'''+escape(result['input_sha256'])+'''</code></p><p>MET:s källästa modellreferens: '''+escape(result['weather_provenance']['verified']['wind_model_reference_time'])+''' · antagen utfärdandetid: '''+escape(result['weather_provenance']['assumed_issued_at'])+'''</p><p>'''+escape(result['notice'])+'''</p><p>Land: © OpenStreetMap contributors, ODbL-1.0. Djup och landfullständighet är okända. Endast två genererade grafkandidater jämförs; ingen global optimalitet.</p></details><footer>Offlinegranskning. Inga nätanrop, ingen GPS/AIS. Källor och inställningar finns i tillhörande JSON-resultat och projektets dokumentation.</footer></main>
<script>for(const b of document.querySelectorAll('[data-select]'))b.addEventListener('click',()=>{for(const g of document.querySelectorAll('[data-route]'))g.style.opacity=g.dataset.route===b.dataset.select?'1':'.12';for(const c of document.querySelectorAll('[data-select]'))c.classList.toggle('selected',c===b)});document.getElementById('all').addEventListener('click',()=>{for(const g of document.querySelectorAll('[data-route]'))g.style.opacity='1';for(const c of document.querySelectorAll('[data-select]'))c.classList.remove('selected')});</script></html>'''
