import xml.etree.ElementTree as ET, requests, io, time, schedule, regex as re, unidecode, rapidfuzz, logging
from pathlib import Path
from sqlalchemy import create_engine
isons = {"ns": "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.09"}

def parse(xmlpath):
    tree = ET.parse(xmlpath)
    root = tree.getroot()
    dbtrfullname = root.find('.//ns:Dbtr/ns:Nm', isons).text
    cdtrfullname = root.find('.//ns:Cdtr/ns:Nm', isons).text
    print("Debtor name:", dbtrfullname)
    print("Creditor name:", cdtrfullname)
    return dbtrfullname, cdtrfullname
