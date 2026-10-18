"""GPX 1.1 planned routes, never fabricated GPS tracks."""
from xml.etree.ElementTree import Element,SubElement,tostring


def export_estimated_coastal_gpx(view,route_id):
    """Explicit estimate export; the existing verified-result gate stays intact."""
    import json
    route=next((r for r in view['routes'] if r['id']==route_id),None)
    if (view.get('profile')!='vinga-uddevalla' or view.get('result_qualification')!='estimated_high_uncertainty' or view.get('weather_limits_verified') is not False
            or route is None or route['status']!='arrived' or route['arrival_weather_status']!='passed_at_arrival'
            or route.get('result_qualification')!='estimated_high_uncertainty'
            or route.get('weather_limits_verified') is not False):
        raise ValueError('Explicit arrived coastal estimate required')
    root=Element('gpx',{'xmlns':'http://www.topografix.com/GPX/1/1','xmlns:sp':'https://seaparser.com/ns/estimate/1',
                        'version':'1.1','creator':'SeaParser coastal development estimate'})
    meta=SubElement(root,'metadata')
    SubElement(meta,'name').text='Vinga–Uddevalla · UPPSKATTNING · HÖG OSÄKERHET'
    SubElement(meta,'desc').text='Verkliga frysta prognoser 18–19 oktober 2026 med landmedvetna reservdata. Vädergränser EJ verifierade. Uppskattad 5 kn-båt. Djup och landfullständighet okända. Ej navigationsunderlag eller GPS-spår.'
    extensions=SubElement(meta,'extensions')
    SubElement(extensions,'sp:qualification').text='estimated_high_uncertainty'
    SubElement(extensions,'sp:weather_limits_verified').text='false'
    SubElement(extensions,'sp:input_sha256').text=view['input_sha256']
    # Self-contained evidence, including variable, source position/time/value,
    # water connection, distance/time offset and every affected segment/sample.
    evidence={k:view[k] for k in ('provenance','configuration','reserve_evidence','land_margin_m','source_value_bounds')}
    evidence['route_summary']={k:v for k,v in route.items() if k not in ('path','waypoints')}
    SubElement(extensions,'sp:evidence_json').text=json.dumps(evidence,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    rte=SubElement(root,'rte');SubElement(rte,'name').text=route_id+' · HÖG OSÄKERHET'
    SubElement(rte,'desc').text='Planerade vägpunkter från en uppskattad modellfärd. Vädergränser ej verifierade.'
    for i,(lon,lat) in enumerate(route['waypoints']):
        point=SubElement(rte,'rtept',{'lon':format(lon,'.10f'),'lat':format(lat,'.10f')})
        SubElement(point,'name').text=f'WP {i+1} · uppskattning'
    return tostring(root,encoding='utf-8',xml_declaration=True)


def export_gpx(result,route_id):
    route=next((r for r in result['alternatives'] if r['id']==route_id),None)
    if (route is None or route['status'] != 'arrived'
            or route.get('weather_segment_status') not in ('verified','not_applicable')
            or route.get('arrival_weather_status') != 'passed_at_arrival'):
        raise ValueError('Endast genomförda modellkandidater kan exporteras')
    root=Element('gpx',{'xmlns':'http://www.topografix.com/GPX/1/1','version':'1.1','creator':'SeaParser development review'})
    meta=SubElement(root,'metadata');SubElement(meta,'desc').text='Uppskattade syntetiska testdata; granska mot officiellt sjökort och i plottern. Ej GPS-spår.'
    if result.get('profile')=='vinga':
        copyright=SubElement(meta,'copyright',{'author':'OpenStreetMap contributors'})
        SubElement(copyright,'license').text='https://opendatacommons.org/licenses/odbl/1-0/'
        meta.find('desc').text='Vinga: OSM-land / ODbL; syntetiskt väder och uppskattad båt. Djup och landfullständighet okända. Ej navigationssäkert. Ej GPS-spår. Landversion: '+result['land']['version']+'; SHA256: '+result['land']['sha256']
    if result.get('result_qualification')=='conditional_on_assumptions':
        meta.find('desc').text='Verkliga historiska MET/WAV/PHY-data; beräknad med antaganden och uppskattad båt. Djup och landfullständighet okända. Ej navigationssäkert. Ej GPS-spår. Landversion: '+result['land']['version']+'; SHA256: '+result['land']['sha256']+'; Antaganden: '+', '.join(result['weather_provenance']['assumptions'])
    rte=SubElement(root,'rte');SubElement(rte,'name').text=route_id
    SubElement(rte,'desc').text='Planerade vägpunkter; ingen garanti för navigerbarhet. '+result['input_sha256']
    for index,(longitude,latitude) in enumerate(route['waypoints']):
        point=SubElement(rte,'rtept',{'lat':format(latitude,'.10f'),'lon':format(longitude,'.10f')})
        SubElement(point,'name').text=f'WP {index+1}'
    return tostring(root,encoding='utf-8',xml_declaration=True)
