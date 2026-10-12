"""Regional gate before planning: incomplete POINT sources cannot become a grid."""
from dataclasses import asdict
from infrastructure.point_forecast import SnowPointAdapter,MetOceanPointAdapter


def inspect_reference(reference):
    adapters={'snow1gv1':SnowPointAdapter(),'met-ocean-2.0':MetOceanPointAdapter()}
    from infrastructure.point_forecast import timestamp
    records=[]
    for source in reference['sources']:
        records.extend(adapters[source['adapter']].normalize(source['payload'],retrieved_at=timestamp(source['retrieved_at']),source_url=source['url']))
    return tuple(records)


def plan_reference(reference):
    records=inspect_reference(reference)
    # This input contract consists only of point forecasts. It supplies no
    # spatial grid/support polygon, so it cannot authorize a regional voyage.
    return {'status':'data_unavailable',
            'reason':'Regional prognostäckning ej verifierad: endast flyttade punktprognoser; vågperiod och marin utfärdandetid saknas. Inga nollvärden eller regional extrapolation.',
            'fastest_candidate':None,'comfortable_candidate':None,
            'navigational_safety':'not_assessed','depth_status':'unknown',
            'products':[asdict(r) for r in records],
            'search_scope':'Ingen verklig rutt jämförs innan regionalt prognosunderlag verifierats. Syntetisk Vinga-profil söker högst två grafkandidater; inga globala optimum garanteras.'}
