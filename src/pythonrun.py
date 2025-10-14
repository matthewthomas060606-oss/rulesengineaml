import logging
from pathlib import Path
from isoparser import parse, buildbase
import xml.etree.ElementTree as ET
from returnitems import returnitems
from OFACload import OFAC_fetch_cons, OFAC_fetch_sdn, OFAC_extract
from UKload import UK_fetch, UK_extract
from UNload import UN_fetch, UN_extract
from EUCFSLload import EU_fetch, EU_extract
from AUload import AU_fetch, AU_extract
from CAload import CA_fetch, CA_extract
from SECOload import SECO_fetch, SECO_extract
from database import createdatabase, returnDetails2, returnDetails2_fts, returnDetails2_fts_multi
from screening import submitresponse
from matcher import matching
import json, sqlite3, os
from config import ScreeningConfig
from rules import apply_rules
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "ind.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "catm.003.001.14.sample.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "acmt_sample.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "pain.001.001.12-example.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "camt.003.001.08.maximal.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "setr.001.001.04_example.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "tsrv.014.001.01-example.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "seev.015.001.01-maximal.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "pacs.029.001.02-maximal.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "pacs.002.001.12-maximal.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "secl.009.001.03-maximal.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "pain.013.001.11-maximal.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "camt.052.001.13-maximal.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "catp.007.001.03-ATMInquiryResponseV03-sample.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "flag2.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "colr.014-example.xml"
# xmlpath = Path(__file__).parent.parent / "data" / "iso" / "unrecognized.xml"
xmlpath = Path(__file__).parent.parent / "data" / "iso" / "statetest.xml"

def main(xmlpath):
    #Reads xml from path
    xmlbytes = Path(xmlpath).read_bytes()
    #gui
    gui = Path(__file__).parent.parent / "iso-viewer" / "public"
    gui.mkdir(parents=True, exist_ok=True)

    dbpath = Path(__file__).parent.parent / "data" / "sanctions.db"
    latestpath = Path(__file__).parent.parent / "data" / "latest.json"
    historypath = Path(__file__).parent.parent / "data" / "history.jsonl"

    #Parses ISO20022 and returns fields contained in XML
    parsed = parse(xmlbytes)
    base = buildbase(parsed)
    #Info in xml returned to readable format
    party_infos, txinfo = returnitems(parsed, base)
    refreshed = False
    #Builds database if it doesn't exist
    if dbpath.exists():
        pass
    else:
        details = []
        #Downloads and processes lists
        #Then extends database with info
        root_ofaccons = OFAC_fetch_cons()
        root_ofacsdn = OFAC_fetch_sdn()
        details.extend(OFAC_extract(root_ofaccons))
        details.extend(OFAC_extract(root_ofacsdn))
        root_uk = UK_fetch()
        details.extend(UK_extract(root_uk))
        root_un = UN_fetch()
        details.extend(UN_extract(root_un))
        root_eu = EU_fetch()
        details.extend(EU_extract(root_eu))
        root_au = AU_fetch()
        details.extend(AU_extract(root_au))
        root_ca = CA_fetch()
        details.extend(CA_extract(root_ca))
        root_seco = SECO_fetch()
        details.extend(SECO_extract(root_seco))
        createdatabase(details)
    
        refreshed = True
    queries = [ (p.get("Name") or "").strip() for p in (party_infos or []) ]
    TableData = returnDetails2_fts_multi(queries, None, 300) or returnDetails2()

    if refreshed or os.getenv("AML_EXPORT_ALL") == "1":
        try:
            conn = sqlite3.connect(dbpath)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            rows = cur.execute("SELECT * FROM sanctionsdetails").fetchall()
            sanctions_export = [dict(r) for r in rows]
            (gui / "sanctions_index.json").write_text(json.dumps(sanctions_export, ensure_ascii=False), encoding="utf-8")
            conn.close()
        except Exception as e:
            (gui / "sanctions_index.json").write_text(json.dumps({"error": str(e)}), encoding="utf-8")
    #Screens ISO20022 information against sanctions database information
    match = matching(party_infos, txinfo, TableData, ScreeningConfig)
    #Formulates final response
    response = submitresponse(base, party_infos, txinfo, match, apply_rules)

    payload = json.dumps(response, indent=2, ensure_ascii=False)
    print(payload)
    logging.info(payload)
    (gui / "latest.json").write_text(payload, encoding="utf-8")
    with (gui / "history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(response, ensure_ascii=False) + "\n")
    #Returns response
    return response

if __name__ == "__main__":
    main(xmlpath)
