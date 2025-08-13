import logging
from pathlib import Path
from isoparser import parse, buildbase
from links import detailsExtractor, fetchsanctionslist, returnDetails
from database import createdatabase, returnDetails2
from screening import submitresponse
from matcher import matching
import json

#Sample ISO20022 file
xmlpath = Path(__file__).parent.parent/"data"/"ind.xml"

def main(xmlpath):
    gui = Path(__file__).parent.parent / "iso-viewer" / "public"  # <-- adjust to your viewer path
    gui.mkdir(parents=True, exist_ok=True)
    dbpath = Path(__file__).parent.parent/"data"/"sanctions.db"
    latestpath = Path(__file__).parent.parent/"data"/"latest.json"
    historypath = Path(__file__).parent.parent/"data"/"history.jsonl"
    #Returns iso details
    parsed = parse(xmlpath)
    base = buildbase(parsed)
    dbtr = next(p for p in parsed["parties"] if p["role"]=="Debtor")["name"]
    cdtr = next(p for p in parsed["parties"] if p["role"]=="Creditor")["name"]
    if dbpath.exists():
        #Uses existing database (will implement updating later)
        print("Database exists.")
        pass
    else:
        #Creates Database
        root = fetchsanctionslist() 
        details = returnDetails(root)
        createdatabase(details)
    #Screens names and matches them against database (Database only contains SECO right now, Matching is very simple)
    TableData = returnDetails2()
    match = matching(dbtr, cdtr, TableData)
    if match["flagged"]:
        response = submitresponse(base, match)
        print(json.dumps(response, indent=2, ensure_ascii=False))
        logging.info(response)
        (gui / "latest.json").write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
        with (gui / "history.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(response, ensure_ascii=False) + "\n")
    return response

if __name__ == "__main__":
    #Trial run of flagging
    main(xmlpath)
