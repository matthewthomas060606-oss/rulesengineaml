import xml.etree.ElementTree as ET
import requests
SECOurl = (
    "https://www.sesam.search.admin.ch/sesam-search-web/pages/downloadXmlGesamtliste.xhtml?lang=de&action=downloadXmlGesamtlisteAction"
)
def fetchsanctionslist():
    download = requests.get(SECOurl, timeout=30)
    download.raise_for_status()
    seco_root = ET.fromstring(download.content)
    return seco_root

def detailsExtractor(target_elem):
    ssid = target_elem.get('ssid')
    identity = target_elem.find('.//identity')
    issid = identity.get('ssid')
    givenname = target_elem.find(".//name-part[@name-part-type='given-name']/value")
    familyname = target_elem.find(".//name-part[@name-part-type='family-name']/value")
    if familyname is not None and familyname.text:
        if givenname is not None and givenname.text:
            return (ssid, issid, f"{givenname.text.strip()} {familyname.text.strip()}")
    return None

def returnDetails(root):
    details = []
    for target in root.findall('.//target'):
        record = detailsExtractor(target) if target is not None else None
        if record:
           details.append(record)
    return details