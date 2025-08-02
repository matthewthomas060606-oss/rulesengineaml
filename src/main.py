import xml.etree.ElementTree as ET, requests, io, time, schedule, regex as re, unidecode, rapidfuzz, logging, flask
import json
from pathlib import Path
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
from isoparser import parse
from links import fetchsanctionslist, detailsExtractor, returnDetails
from database import createdatabase
from matcher import matching

def main():
    xmlpath = Path(__file__).parent.parent/"data"/"ind.xml"
    dbtrfullname, cdtrfullname = parse(xmlpath)
    secoroot = fetchsanctionslist()
    details = returnDetails(secoroot)
    createdatabase(details)
    response = matching(dbtrfullname, cdtrfullname, details)
    print(json.dumps(response, indent=2))

if __name__ == "__main__":
    main()