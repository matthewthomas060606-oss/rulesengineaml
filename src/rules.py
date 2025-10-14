import os
import json
from pathlib import Path

RULES_PATH = Path(os.getenv("AML_RULES_PATH", Path(__file__).parent / "rules.json"))

DEFAULT = {"releaseBelow": 25, "reviewFrom": 25, "escalateFrom": None}

def get_rules():
    if RULES_PATH.exists():
        try:
            return {**DEFAULT, **json.loads(RULES_PATH.read_text())}
        except Exception:
            pass
    return DEFAULT

def _as_int_or_none(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None

def apply_rules(riskScore):
    rules = get_rules()

    esc = _as_int_or_none(rules.get("escalateFrom"))
    rev = _as_int_or_none(rules.get("reviewFrom"))
    rel = _as_int_or_none(rules.get("releaseBelow"))

    if esc is not None and riskScore >= esc:
        action = "Escalate"
    elif rev is not None and riskScore >= rev:
        action = "Review"
    elif rel is not None and riskScore <= rel:
        action = "Release"
    else:
        action = "N/A"

    return action