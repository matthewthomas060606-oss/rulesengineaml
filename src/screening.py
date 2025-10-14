from datetime import datetime, timezone
from readLog import readLogFiles

def submitresponse(base, party_infos, transaction_info, engine_result, apply_rules):
    time_flagged = (engine_result or {}).get("timeflagged")
    top_risk_level_value = (engine_result or {}).get("topRiskLevel", "no risk")
    overall_risk_level_value = (engine_result or {}).get("riskLevel", "no risk")
    risk_score_points = None
    try:
        rs = (engine_result or {}).get("riskScore")
        if isinstance(rs, (int, float)):
            risk_score_points = int(round(max(0, min(100, float(rs)))))
        else:
            ts = (engine_result or {}).get("topScore")
            if isinstance(ts, (int, float)):
                risk_score_points = int(round(max(0, min(100, float(ts)))))
    except Exception:
        risk_score_points = None
    flagged_value = bool((engine_result or {}).get("flagged"))
    response_code_value = (engine_result or {}).get("responseCode")
    SECOrefreshedat, UNrefreshedat, EUrefreshedat, CArefreshedat, AUrefreshedat, UKrefreshedat, OFACsdnrefreshedat, OFACconsrefreshedat = readLogFiles("SECOlog.txt"), readLogFiles("UNlog.txt"), readLogFiles("EUlog.txt"), readLogFiles("CAlog.txt"), readLogFiles("AUlog.txt"), readLogFiles("UKlog.txt"), readLogFiles("OFACsdnlog.txt"), readLogFiles("OFACconslog.txt")
    lists_used = [
    {"name": "OFAC SDN", "publisher": "OFAC (USA)", "sourceUrl": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML", "lastRefreshedAt": OFACsdnrefreshedat},
    {"name": "OFAC consolidated", "publisher": "OFAC (USA)", "sourceUrl": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONSOLIDATED.XML", "lastRefreshedAt": OFACconsrefreshedat},
    {"name": "UK consolidated", "publisher": "OFSI (UK)", "sourceUrl": "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml", "lastRefreshedAt": UKrefreshedat},
    {"name": "UN consolidated", "publisher": "United Nations", "sourceUrl": "https://scsanctions.un.org/resources/xml/en/consolidated.xml", "lastRefreshedAt": UNrefreshedat},
    {"name": "EU consolidated", "publisher": "European Union", "sourceUrl": "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=n009sfr8", "lastRefreshedAt": EUrefreshedat},
    {"name": "AU consolidated", "publisher": "DFAT (Australia)", "sourceUrl": "https://www.dfat.gov.au/sites/default/files/regulation8_consolidated.xlsx", "lastRefreshedAt": AUrefreshedat},
    {"name": "CA consolidated", "publisher": "Global Affairs Canada", "sourceUrl": "https://www.international.gc.ca/world-monde/assets/office_docs/international_relations-relations_internationales/sanctions/sema-lmes.xml", "lastRefreshedAt": CArefreshedat},
    {"name": "SECO consolidated", "publisher": "SECO (Switzerland)", "sourceUrl": "https://www.sesam.search.admin.ch/sesam-search-web/pages/downloadXmlGesamtliste.xhtml", "lastRefreshedAt": SECOrefreshedat}
]
    ordered_parties = []
    for party_map in party_infos or []:
        if not isinstance(party_map, dict):
            continue
        if str(party_map.get("Role")).lower() == "party":
            continue
        reordered = {}
        if party_map.get("Role") is not None:
            reordered["Role"] = party_map.get("Role")
        elif party_map.get("role") is not None:
            reordered["Role"] = party_map.get("role")
        else:
            reordered["Role"] = "Unknown"
        if party_map.get("Name") not in (None, ""):
            reordered["Name"] = party_map.get("Name")
        else:
            reordered["Name"] = party_map.get("name") or party_map.get("Account Name") or party_map.get("Identifier") or party_map.get("Account Id")
        for key_name, key_value in party_map.items():
            if key_name in ("Role", "name", "Name", "role"):
                continue
            reordered[key_name] = key_value
        ordered_parties.append(reordered)
    cleaned_parties = []
    for p in ordered_parties:
        cleaned = {}
        roles_value = p.get("Role")
        cleaned["Role"] = roles_value if isinstance(roles_value, list) else ([roles_value] if roles_value not in (None, "", []) else ["Unknown"])
        if p.get("Name") not in (None, ""):
            cleaned["Name"] = p.get("Name")
        for k, v in p.items():
            if k in ("Role", "Name"):
                continue
            cleaned[k] = v
        cleaned_parties.append(cleaned)

    decision_block = {
        "recommendedAction": apply_rules(int(risk_score_points))
    }
    risk_summary_block = {
        "riskScore": int(risk_score_points),
        "riskLevel": overall_risk_level_value,
        "drivers": [],
        "time": time_flagged
    }

    fullresponse = {
        "listsUsed": lists_used,
        "parties": cleaned_parties,
        "transaction": transaction_info or {},
        "decision": decision_block,
        "riskSummary": risk_summary_block,
        "engine": {
            "topMatchScore": int((engine_result or {}).get("topScore") or 0),
            "topMatchRiskLevel": top_risk_level_value,
            "riskScore": int(risk_score_points),
            "riskLevel": overall_risk_level_value,
            "responseCode": response_code_value,
            "matchCounts": (engine_result or {}).get("matchCounts") or {"total": 0, "byRiskLevel": {}}
        },
        "matches": ((engine_result or {}).get("matches") or [])
    }
    return fullresponse
