import os
import json

RISKLEVEL_DEFAULT = { #Change Risk Levels
    "veryHighFrom": 0.90,
    "highFrom": 0.70,
    "moderateFrom": 0.25,
    "slightAbove": 0.10,
}

RESPONSECODE_DEFAULT = { #Change Response Codes
    "very high risk": "VERY_HIGH_RISK",
    "high risk": "HIGH_RISK",
    "moderate risk": "MODERATE_RISK",
    "slight risk": "SLIGHT_RISK",
    "no risk": "NONE",
}


def _load_rules(default: dict) -> dict:
    return dict(default)


def _as_int_or_none(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def get_risklevel_rules() -> dict:
    return _load_rules(RISKLEVEL_DEFAULT)

def _as_float(v, fallback: float | None = None) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return fallback

def risk_from_score(score_value: float) -> str:
    r = get_risklevel_rules()
    very_high = _as_float(r.get("veryHighFrom"))
    high = _as_float(r.get("highFrom"))
    moderate = _as_float(r.get("moderateFrom"))
    slight = _as_float(r.get("slightAbove"))

    try:
        s = float(score_value)
    except (TypeError, ValueError):
        s = 0.0

    if very_high is not None and s >= very_high:
        return "very high risk"
    if high is not None and s >= high:
        return "high risk"
    if moderate is not None and s >= moderate:
        return "moderate risk"
    if slight is not None and s > slight:
        return "slight risk"
    return "no risk"

def apply_risklevel_rules(score_value: float) -> str:
    return risk_from_score(score_value)

def get_responsecode_rules() -> dict:
    return _load_rules(RESPONSECODE_DEFAULT)

def apply_responsecode_rules(overall_risk_level: str) -> str:
    mapping = get_responsecode_rules()
    key = (overall_risk_level or "").strip().lower()
    return mapping.get(key, "UNKNOWN")
