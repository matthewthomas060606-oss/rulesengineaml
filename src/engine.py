import sqlite3
import time
import json
from pathlib import Path
from typing import Any, Callable, List, Sequence, Tuple

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

cfg = get_config()

SanctionsLoader = Tuple[Callable[[], Any], Callable[[Any], List[dict]]]

SANCTIONS_LOADERS: Sequence[SanctionsLoader] = (
    (OFAC_fetch_cons, OFAC_extract),
    (OFAC_fetch_sdn, OFAC_extract),
    (UK_fetch, UK_extract),
    (UN_fetch, UN_extract),
    (EU_fetch, EU_extract),
    (AU_fetch, AU_extract),
    (CA_fetch, CA_extract),
    (SECO_fetch, SECO_extract),
)

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
    for party in (party_infos or []):
        name = (party.get("Name") or "").strip()
        if name:
            queries.append(name)
    if not queries and (transaction_info or {}).get("EndToEndId"):
        queries.append(str(transaction_info["EndToEndId"]))
    table_data = returnDetails2_fts_multi(queries, None, limit=300)
    if not table_data:
        table_data = returnDetails2()
    engine_result = matching(party_infos, transaction_info, table_data, ScreeningConfig)
    response = submitresponse(base, party_infos, transaction_info, engine_result, apply_rules)
    _persist_response(GUI_PATH, response)
    return response

def response_code_from_result(result: dict) -> str:
    code = (((result or {}).get("engine") or {}).get("responseCode") or "").strip()
    if code:
        return code

def refresh_lists() -> int:
    details: List[dict] = []
    for fetch, extract in SANCTIONS_LOADERS:
        source = fetch()
        extracted = extract(source) or []
        details.extend(extracted)
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


def _persist_response(gui_path: Path, response: dict) -> None:
    formatted = json.dumps(response, indent=2, ensure_ascii=False)
    (gui_path / "latest.json").write_text(formatted, encoding="utf-8")
    with (gui_path / "history.jsonl").open("a", encoding="utf-8") as history_file:
        history_file.write(json.dumps(response, ensure_ascii=False) + "\n")
