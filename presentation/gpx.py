"""GPX 1.1 planned routes, never fabricated GPS tracks."""
from xml.etree.ElementTree import Element,SubElement,tostring


def export_gpx(result,route_id):
    route=next((r for r in result['alternatives'] if r['id']==route_id),None)
    if (route is None or route['status'] != 'arrived'
            or route.get('weather_segment_status') not in ('verified','not_applicable')
            or route.get('arrival_weather_status') != 'passed_at_arrival'):
        raise ValueError('Endast genomförda modellkandidater kan exporteras')
    root=Element('gpx',{'xmlns':'http://www.topografix.com/GPX/1/1','version':'1.1','creator':'SeaParser synthetic review'})
    meta=SubElement(root,'metadata');SubElement(meta,'desc').text='Uppskattade syntetiska testdata; granska mot officiellt sjökort och i plottern. Ej GPS-spår.'
    if result.get('profile')=='vinga':
        copyright=SubElement(meta,'copyright',{'author':'OpenStreetMap contributors'})
        SubElement(copyright,'license').text='https://opendatacommons.org/licenses/odbl/1-0/'
        meta.find('desc').text='Vinga: OSM-land / ODbL; syntetiskt väder och uppskattad båt. Djup och landfullständighet okända. Ej navigationssäkert. Ej GPS-spår. Landversion: '+result['land']['version']+'; SHA256: '+result['land']['sha256']
    rte=SubElement(root,'rte');SubElement(rte,'name').text=route_id
    SubElement(rte,'desc').text='Planerade vägpunkter; ingen garanti för navigerbarhet. '+result['input_sha256']
    for index,(longitude,latitude) in enumerate(route['waypoints']):
        point=SubElement(rte,'rtept',{'lat':format(latitude,'.10f'),'lon':format(longitude,'.10f')})
        SubElement(point,'name').text=f'WP {index+1}'
    return tostring(root,encoding='utf-8',xml_declaration=True)
