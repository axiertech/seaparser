"""Shared bounded development inputs; offline audit may exceed only evaluation count."""
VINGA_OFFSETS = (0, 600, 3600, 10800)
MAX_EVALUATIONS = 16


def validate_budget(profile, candidate_limit, offsets, *, offline=False):
    limit = (2 if profile in ('vinga','vinga-native','vinga-poc') else 8) if candidate_limit is None else candidate_limit
    if type(limit) is not int or limit not in (2, 4, 8):
        raise ValueError('Kandidatbudget måste vara 2, 4 eller 8')
    allowed = VINGA_OFFSETS if profile in ('vinga','vinga-native','vinga-poc') else (0, 600)
    if (not isinstance(offsets, (list, tuple)) or not 1 <= len(offsets) <= len(allowed)
            or any(type(o) is not int or o not in allowed for o in offsets)
            or len(set(offsets)) != len(offsets)):
        raise ValueError('Unika avgångsoffset inom profilens uttryckliga tidsval krävs')
    if profile not in ('vinga','vinga-native','vinga-poc') and limit != 8:
        raise ValueError('Syntetiskt referensfall behåller åtta kandidater')
    if not offline and limit * len(offsets) > MAX_EVALUATIONS:
        raise ValueError('Högst 16 rutt-/avgångskombinationer; välj färre kandidater eller avgångar')
    return limit
