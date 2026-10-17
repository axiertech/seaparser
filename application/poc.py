"""PoC choices and display metrics from accepted physical motion samples."""
from datetime import datetime,timedelta,timezone
from math import hypot,isfinite
from infrastructure.land import to_geo,FORWARD
from prototype.model import Vector

POINTS=(('a','Punkt A · söder',(500,0)),('b','Punkt B · norr',(500,350)),
        ('c','Punkt C · väster',(100,350)))
DEPARTURES=(0,600,3600,10800)
WEATHER_PRESETS=(('normal','Vind ≤18 m/s · vågor ≤3 m',18,3),
                 ('wind','Vind ≤12 m/s · vågor ≤3 m',12,3),
                 ('waves','Vind ≤18 m/s · vågor ≤0,1 m',18,.1))


def scene_options():
    base=datetime(2026,10,17,1,tzinfo=timezone.utc)
    return {'boat_profiles':[{'id':'constant-5kn','label':'Konstantfart 5 kn · uppskattad båtmodell',
                            'speed_knots':5,'estimated':True}],
            'places':[dict(id=i,label=label,longitude=to_geo(Vector(*p))[0],latitude=to_geo(Vector(*p))[1])
                      for i,label,p in POINTS],
            'departure_options':[dict(offset_seconds=s,time=(base+timedelta(seconds=s)).isoformat()) for s in DEPARTURES],
            'weather_presets':[dict(id=i,label=label,max_wind_m_s=w,max_wave_height_m=h) for i,label,w,h in WEATHER_PRESETS]}


def route_metrics(route):
    samples=[];distance=0
    for leg in route['legs']:
        for step in leg['steps']:
            middle=step['midpoint'];g=middle['ground']
            seconds=(datetime.fromisoformat(step['end_time'])-datetime.fromisoformat(step['start']['time'])).total_seconds()
            distance+=hypot(g['east'],g['north'])*seconds
            samples.append(middle)
    def span(name):
        values=[];missing=0
        for m in samples:
            field=m.get(name)
            if field is None:missing+=1;continue
            values.append(field['height_m'] if name=='waves' else hypot(field['east'],field['north']))
        return dict(min=min(values) if values else None,max=max(values) if values else None,
                    missing_samples=missing,sample_count=len(samples))
    return {'distance_m':distance if samples else None,
            'weather_summary':{'wind_m_s':span('wind'),'current_m_s':span('current'),'wave_height_m':span('waves')},
            'distance_scope':'Midpoint integration of physical ground speed; partial for unsuccessful routes'}


def local_position(latitude,longitude):
    if any(type(v) not in (int,float) or not isfinite(v) for v in (latitude,longitude)) or not -90<=latitude<=90 or not -180<=longitude<=180:
        raise ValueError('Ogiltiga WGS84-koordinater')
    point=Vector(*FORWARD.transform(longitude,latitude,errcheck=True))
    if point.speed>900:
        raise ValueError('Punkten ligger utanför PoC-områdets 900 m')
    return point
