"""Assemble a standalone page from frontend presentation assets and detached data."""
from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path
from string import Template

ASSETS = Path(__file__).resolve().parents[1] / 'frontend/presentation'


def render_frozen_forecast(review):
    if review.get('schema') != 1 or review.get('historical') is not True or review.get('routing_qualified') is not False:
        raise ValueError('Only historical unqualified sample reviews are supported')
    data = json.dumps(review, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    # Script data must not terminate its HTML element, including untrusted source labels.
    data = data.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    style = (ASSETS / 'frozen-forecast.css').read_text()
    script = (ASSETS / 'frozen-forecast.js').read_text()
    def digest(value):
        return b64encode(sha256(value.encode()).digest()).decode()
    policy = ("default-src 'none'; base-uri 'none'; form-action 'none'; "
              "style-src 'sha256-" + digest(style) + "'; script-src 'sha256-" + digest(script) +
              "' 'sha256-" + digest(data) + "'")
    return Template((ASSETS / 'frozen-forecast.html').read_text()).substitute(
        POLICY=policy, STYLE=style, DATA=data, SCRIPT=script)
