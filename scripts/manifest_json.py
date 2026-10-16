"""Unambiguous JSON decoding shared by frozen forecast audit tools."""
import json


def manifest_json(data):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                # Keep arbitrary source keys and values out of diagnostics.
                raise ValueError('Duplicate manifest key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique_object)
