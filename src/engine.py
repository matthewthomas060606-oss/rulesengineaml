from pathlib import Path
import sqlite3
import time
from turtle import Screen
from typing import List
from isoparser import parse, buildbase
from returnitems import returnitems
from database import createdatabase, returnDetails2_fts_multi, returnDetails2
from OFACload import OFAC_fetch_cons, OFAC_fetch_sdn, OFAC_extract
from UKload import UK_fetch, UK_extract
from UNload import UN_fetch, UN_extract
from EUCFSLload import EU_fetch, EU_extract
from AUload import AU_fetch, AU_extract
from CAload import CA_fetch, CA_extract
from SECOload import SECO_fetch, SECO_extract
from matcher import matching
from screening import submitresponse
from config import get_config, ScreeningConfig
from rules import apply_rules
import json

cfg = get_config()

def _ensure_db_ready() -> None:
    p = cfg.paths.DB_PATH
    if p.exists():
        return
    refresh_lists()

def screen_xml_bytes(xml_bytes: bytes):
    GUI_PATH = cfg.paths.GUI_PATH
    parsed = parse(xml_bytes)
    base = buildbase(parsed)
    party_infos, transaction_info = returnitems(parsed, base)
    _ensure_db_ready()
    queries: List[str] = []
    queries: List[object] = []
    for p in (party_infos or []):
        nm = (p.get("Name") or "").strip()
        if nm:
            queries.append(nm)
        addr = (p.get("Address Line") or "").strip()
        if addr:
            queries.append({"field": "address", "value": addr})
    table_data = returnDetails2_fts_multi(queries, list_filter=None, limit=65000)
    #Will return every single row and do a thorough search; Takes a lot longer
   #table_data = returnDetails2()
    engine_result = matching(party_infos, transaction_info, table_data, ScreeningConfig)
    response = submitresponse(base, party_infos, transaction_info, engine_result, apply_rules)
    formattedresponse = json.dumps(response, indent=2, ensure_ascii=False)
    (GUI_PATH / "latest.json").write_text(formattedresponse, encoding="utf-8")
    with (GUI_PATH / "history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(response, ensure_ascii=False) + "\n")
    return response

def response_code_from_result(result: dict) -> str:
    code = (((result or {}).get("engine") or {}).get("responseCode") or "").strip()
    if code:
        return code

def refresh_lists() -> int:
    details: List[dict] = []
    details.extend(OFAC_extract(OFAC_fetch_cons()))
    details.extend(OFAC_extract(OFAC_fetch_sdn()))
    details.extend(UK_extract(UK_fetch()))
    details.extend(UN_extract(UN_fetch()))
    details.extend(EU_extract(EU_fetch()))
    details.extend(AU_extract(AU_fetch()))
    details.extend(CA_extract(CA_fetch()))
    details.extend(SECO_extract(SECO_fetch()))
    createdatabase(details)
    conn = sqlite3.connect(cfg.paths.DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sanctionslist")
        n = int(cur.fetchone()[0] or 0)
        cur.execute("CREATE TABLE IF NOT EXISTS sanctions_meta (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute(
            "INSERT INTO sanctions_meta(key,value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            ("last_built_epoch", str(int(time.time())))
        )
        conn.commit()
        return n
    finally:
        conn.close()









