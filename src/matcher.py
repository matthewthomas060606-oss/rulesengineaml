import difflib, pandas as pd, sqlite3
from typing import List
from pathlib import Path
from sqlalchemy import false, true

def matching(dbtrfullname, cdtrfullname, details):
    db_path = Path(__file__).parent.parent/"data"/"sanctions.db"
    connection = sqlite3.connect(db_path)
    allnames = [full for _, _, full in details]
    dbtrmatches = difflib.get_close_matches(
        dbtrfullname,
        allnames,
        n=10,
        cutoff=0.9
    )
    cdtrmatches = difflib.get_close_matches(
        cdtrfullname,
        allnames,
        n=10,
        cutoff=0.9
    )
    df = pd.read_sql_query("SELECT * FROM sanctionslist", connection, index_col=None)
    print(df)
    debtorssids   = [ tssid for (tssid, _, name) in details if name in dbtrmatches ]
    creditorssids = [ tssid for (tssid, _, name) in details if name in cdtrmatches ]
    debtorrows   = df[df['ssid'].isin(debtorssids)]
    creditorrows = df[df['ssid'].isin(creditorssids)]
    print("DEBTOR ROWS:\n", debtorrows)
    print("CREDITOR ROWS:\n", creditorrows)
    hits = []
    for ssid, _, name in details:
        if name in dbtrmatches:
            hits.append({"role": "Debtor",   "name": name, "ssid": ssid})
        if name in cdtrmatches:
            hits.append({"role": "Creditor", "name": name, "ssid": ssid})
    if hits:
        code = "FLAGGED"
        flagged = True
    else:
        code = "NOFLAG"
        flagged = False
    response = {"responseCode":code, "flagged":flagged, "matches":hits}
    seen = set()
    unique = []
    for h in response["matches"]:
        key = (h["role"], h["name"], h["ssid"])
        if key not in seen:
            seen.add(key)
            unique.append(h)
    response["matches"] = unique
    return response