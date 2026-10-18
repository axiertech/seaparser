"""Shared bounded development inputs; offline audit may exceed only evaluation count."""
VINGA_OFFSETS = (0, 600, 3600, 10800)
MAX_EVALUATIONS = 16


def resource_budget(profile='local',path=None):
    """Small explicit server-side profile file; never accepts client overrides."""
    import json
    from pathlib import Path
    values=json.loads((path or Path(__file__).resolve().parents[1]/'settings/resource-budgets.json').read_text())[profile]
    names={'voyage_seconds','step_seconds','max_steps','max_waypoints','max_nodes','max_expansions','max_obstacles','job_seconds','result_bytes'}
    if set(values)!=names or any(type(v) is not int or v<=0 for v in values.values()):
        raise ValueError('Explicit positive integer resource budgets required')
    if values['max_nodes']<2 or values['step_seconds']>values['voyage_seconds'] or values['max_steps']*values['step_seconds']<values['voyage_seconds']:
        raise ValueError('Resource budgets cannot cover their simulated voyage duration')
    return values


def available_voyage_seconds(budget,departure,offsets,valid_until):
    """Simulated duration is bounded by actual data, independently of CPU time.

    Reserve one second before the exclusive source end. A later explicit
    temporal reserve policy may extend source support and must be recorded.
    """
    remaining=min((valid_until-departure).total_seconds()-o for o in offsets)-1
    if remaining<=0:raise ValueError('Avgången saknar gemensamt prognosstöd före exklusivt slut')
    return min(budget['voyage_seconds'],remaining)


def validate_budget(profile, candidate_limit, offsets, *, offline=False):
    limit = (2 if profile in ('vinga','vinga-native','vinga-poc') else 8) if candidate_limit is None else candidate_limit
    if type(limit) is not int or limit not in (2, 4, 8):
        raise ValueError('Kandidatbudget måste vara 2, 4 eller 8')
    allowed = VINGA_OFFSETS if profile in ('vinga','vinga-native','vinga-poc') else (0, 600)
    if (not isinstance(offsets, (list, tuple)) or not 1 <= len(offsets) <= len(allowed)
            or any(type(o) is not int or o not in allowed for o in offsets)
            or len(set(offsets)) != len(offsets)):
        raise ValueError('Avgången saknar prognosdata i profilens tillåtna tidsval; välj en av de angivna unika avgångarna')
    if profile not in ('vinga','vinga-native','vinga-poc') and limit != 8:
        raise ValueError('Syntetiskt referensfall behåller åtta kandidater')
    if not offline and limit * len(offsets) > MAX_EVALUATIONS:
        raise ValueError('Högst 16 rutt-/avgångskombinationer; välj färre kandidater eller avgångar')
    return limit
