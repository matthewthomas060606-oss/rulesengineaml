

def submitresponse(base, response):
   screening = {
    "listsUsed": [{
        "name": "SECO consolidated",
        "publisher": "SECO (Switzerland)",
        "sourceUrl": "https://www.sesam.search.admin.ch/sesam-search-web/pages/downloadXmlGesamtliste.xhtml",
        "lastRefreshedAt": response["timeflagged"]
    }],
    "nameScreeningResults": [{
        "partyRole": hit["role"],
        "inputName": hit["name"],
        "engine": "difflib",
        "algorithm": "closest_match",
        "threshold": 0.90,
        "matches": [{"listId": hit["ssid"], "displayName": hit["name"], "score": 1.00}]
    } for hit in response["matches"]],
    "pepScreeningResults": [],
    "adverseMediaResults": [],
    "geoRiskChecks": [],
    "purposeChecks": [{"rule": "GIFT_keyword", "passed": True, "notes": "Informational"}]
    }
   decision = {
        "automatedStatus": response["responseCode"],
        "recommendedAction": "Escalate" if response["flagged"] else "Release",
        "reasonCodes": ["SANCTIONS_MATCH"] if response["flagged"] else [],
        "explanations": ["Name match at/above threshold on SECO list."] if response["flagged"] else []
    }

   riskSummary = {
        "riskScore": 95 if response["flagged"] else 5,
        "riskLevel": "High" if response["flagged"] else "Low",
        "drivers": ["Sanctions name match"] if response["flagged"] else []
    }

   audit = {
        "screeningRunAt": response["timeflagged"],
        "engineVersion": "0.1",
        "rulesFired": ["difflib>=0.90"],
        "executionMs": 0,
        "rawEngineResponse": response
    }

   fullresponse = { **base, "riskSummary": riskSummary, "decision": decision, "audit": audit }
   return fullresponse
