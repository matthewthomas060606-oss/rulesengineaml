from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from readLog import readLogFiles

_PARTY_NAME_KEYS: tuple[str, ...] = (
    "Name",
    "name",
    "Account Name",
    "Identifier",
    "Account Id",
)

_LOG_SOURCES: tuple[dict[str, str], ...] = (
    {
        "name": "OFAC SDN",
        "publisher": "OFAC (USA)",
        "sourceUrl": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML",
        "log": "OFACsdnlog.txt",
    },
    {
        "name": "OFAC consolidated",
        "publisher": "OFAC (USA)",
        "sourceUrl": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONSOLIDATED.XML",
        "log": "OFACconslog.txt",
    },
    {
        "name": "UK consolidated",
        "publisher": "OFSI (UK)",
        "sourceUrl": "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml",
        "log": "UKlog.txt",
    },
    {
        "name": "UN consolidated",
        "publisher": "United Nations",
        "sourceUrl": "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
        "log": "UNlog.txt",
    },
    {
        "name": "EU consolidated",
        "publisher": "European Union",
        "sourceUrl": "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=n009sfr8",
        "log": "EUlog.txt",
    },
    {
        "name": "AU consolidated",
        "publisher": "DFAT (Australia)",
        "sourceUrl": "https://www.dfat.gov.au/sites/default/files/regulation8_consolidated.xlsx",
        "log": "AUlog.txt",
    },
    {
        "name": "CA consolidated",
        "publisher": "Global Affairs Canada",
        "sourceUrl": "https://www.international.gc.ca/world-monde/assets/office_docs/international_relations-relations_internationales/sanctions/sema-lmes.xml",
        "log": "CAlog.txt",
    },
    {
        "name": "SECO consolidated",
        "publisher": "SECO (Switzerland)",
        "sourceUrl": "https://www.sesam.search.admin.ch/sesam-search-web/pages/downloadXmlGesamtliste.xhtml",
        "log": "SECOlog.txt",
    },
)


def _coerce_score(value: Any) -> Optional[int]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(round(max(0.0, min(100.0, number))))


def _normalize_roles(value: Any) -> list[str]:
    if isinstance(value, list):
        roles = [str(item).strip() for item in value if str(item or "").strip()]
    elif value not in (None, "", []):
        roles = [str(value).strip()]
    else:
        roles = []
    return roles or ["Unknown"]


def _extract_name(party_map: Mapping[str, Any]) -> Optional[Any]:
    for key in _PARTY_NAME_KEYS:
        value = party_map.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize_party(party_map: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    role_candidate = party_map.get("Role", party_map.get("role"))
    if str(role_candidate or "").strip().lower() == "party":
        return None

    normalized: Dict[str, Any] = {"Role": _normalize_roles(role_candidate)}
    name_value = _extract_name(party_map)
    if name_value not in (None, ""):
        normalized["Name"] = name_value

    for key, value in party_map.items():
        if key in {"Role", "role", "Name", "name"}:
            continue
        normalized[key] = value
    return normalized


def _build_lists_used() -> list[dict[str, Any]]:
    lists: list[dict[str, Any]] = []
    for source in _LOG_SOURCES:
        last_refreshed = readLogFiles(source["log"]) or "N/A"
        lists.append(
            {
                "name": source["name"],
                "publisher": source["publisher"],
                "sourceUrl": source["sourceUrl"],
                "lastRefreshedAt": last_refreshed,
            }
        )
    return lists


def submitresponse(base, party_infos, transaction_info, engine_result, apply_rules):
    engine_result = engine_result or {}

    risk_score_points = _coerce_score(engine_result.get("riskScore"))
    top_score_points = _coerce_score(engine_result.get("topScore"))
    if risk_score_points is None:
        risk_score_points = top_score_points
    score_for_rules = risk_score_points if risk_score_points is not None else 0

    time_flagged = engine_result.get("timeflagged") or datetime.now(timezone.utc).isoformat()
    top_risk_level_value = engine_result.get("topRiskLevel", "no risk")
    overall_risk_level_value = engine_result.get("riskLevel", "no risk")
    response_code_value = engine_result.get("responseCode")

    parties: list[dict[str, Any]] = []
    for party_map in party_infos or []:
        if not isinstance(party_map, Mapping):
            continue
        normalized = _normalize_party(party_map)
        if normalized:
            parties.append(normalized)

    decision_block = {"recommendedAction": apply_rules(score_for_rules)}
    risk_summary_block = {
        "riskScore": score_for_rules,
        "riskLevel": overall_risk_level_value,
        "drivers": list(engine_result.get("drivers") or []),
        "time": time_flagged,
    }

    engine_block = {
        "topMatchScore": top_score_points if top_score_points is not None else 0,
        "topMatchRiskLevel": top_risk_level_value,
        "riskScore": score_for_rules,
        "riskLevel": overall_risk_level_value,
        "responseCode": response_code_value,
        "flagged": bool(engine_result.get("flagged")),
        "matchCounts": engine_result.get("matchCounts") or {"total": 0, "byRiskLevel": {}},
    }

    fullresponse = {
        "listsUsed": _build_lists_used(),
        "parties": parties,
        "transaction": transaction_info or {},
        "decision": decision_block,
        "riskSummary": risk_summary_block,
        "engine": engine_block,
        "matches": list(engine_result.get("matches") or []),
    }
    return fullresponse
