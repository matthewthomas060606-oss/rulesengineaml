import xml.etree.ElementTree as ET
import requests
from pathlib import Path
from countrycode import country_to_iso2
from datetime import datetime, timezone
import re
import logging
from config import get_config
cfg = get_config()


CA_URL = "https://www.international.gc.ca/world-monde/assets/office_docs/international_relations-relations_internationales/sanctions/sema-lmes.xml"
CA_XML = "CA.22.09.25.xml"


def CA_fetch():
    try:
        resp = requests.get(CA_URL, timeout=120)
        resp.raise_for_status()
        xml_bytes = resp.content
        if not xml_bytes:
            raise ValueError("empty body")
        log_path = cfg.paths.DATA_DIR / "CAlog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat() + "\n")
        return ET.fromstring(xml_bytes)
    except Exception as e:
        local = Path(__file__).parent.parent / "data" / CA_XML
        if local.exists():
            logging.error("CA download failed; using backup file", e, local)
            return ET.parse(str(local)).getroot()
        raise RuntimeError(f"CA download failed and no backup found at {local}: {e}")

def CA_extract(xml_root):
    records = []
    for record_element in xml_root.findall("record"):
        country_text = (record_element.findtext("Country") or "").strip()
        last_name_text = (record_element.findtext("LastName") or "").strip()
        given_name_text = (record_element.findtext("GivenName") or "").strip()
        entity_or_ship_text = (record_element.findtext("EntityOrShip") or "").strip()
        dob_or_build_text = (record_element.findtext("DateOfBirthOrShipBuildDate") or "").strip()
        schedule_text = (record_element.findtext("Schedule") or "").strip()
        item_text = (record_element.findtext("Item") or "").strip()
        listed_text = (record_element.findtext("DateOfListing") or "").strip()
        aliases_text = (record_element.findtext("Aliases") or "").strip()
        title_or_ship_text = (record_element.findtext("TitleOrShip") or "").strip()
        ship_imo_number_text = (record_element.findtext("ShipIMONumber") or "").strip()

        place_of_birth_text = None
        for tag in ("PlaceOfBirth", "PlaceOfBirthText", "BirthPlace", "PlaceOfBirthOrOrigin"):
            v = (record_element.findtext(tag) or "").strip()
            if v:
                place_of_birth_text = v
                break

        list_name_value = "CA"
        list_identifier_value = None
        if schedule_text or item_text:
            list_identifier_value = "CA-" + (schedule_text.replace(" ", "").replace(",", "_") if schedule_text else "S") + "-" + (item_text if item_text else "0")
        else:
            if entity_or_ship_text and given_name_text and last_name_text:
                list_identifier_value = "CA-" + (entity_or_ship_text.replace(" ", "_")) + "-" + (given_name_text.replace(" ", "_")) + "-" + (last_name_text.replace(" ", "_"))
            else:
                list_identifier_value = "CA-" + (given_name_text.replace(" ", "_") if given_name_text else "UNKNOWN") + "-" + (last_name_text.replace(" ", "_") if last_name_text else "UNKNOWN")

        full_name_value = None
        if given_name_text and last_name_text:
            full_name_value = (given_name_text + " " + last_name_text).strip()
        elif last_name_text:
            full_name_value = last_name_text
        elif given_name_text:
            full_name_value = given_name_text

        classification_value = None
        if entity_or_ship_text:
            lower_val = entity_or_ship_text.lower()
            if "individual" in lower_val or "person" in lower_val:
                classification_value = "individual"
            elif "entity" in lower_val or "organisation" in lower_val or "organization" in lower_val or "company" in lower_val:
                classification_value = "entity"
            elif "ship" in lower_val or "vessel" in lower_val:
                classification_value = "vessel"
            else:
                classification_value = None

        birth_year_value = None
        birth_month_value = None
        birth_day_value = None
        if dob_or_build_text:
            t = dob_or_build_text.strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
                try:
                    parts = t.split("-")
                    birth_year_value = int(parts[0])
                    birth_month_value = int(parts[1])
                    birth_day_value = int(parts[2])
                except Exception:
                    birth_year_value = None
                    birth_month_value = None
                    birth_day_value = None
            elif re.fullmatch(r"\d{4}", t):
                try:
                    birth_year_value = int(t)
                except Exception:
                    birth_year_value = None

        aliases_list = []
        if aliases_text:
            if ";" in aliases_text or "|" in aliases_text:
                chunks = re.split(r"\s*[;|]\s*", aliases_text)
                aliases_list = [c for c in (x.strip() for x in chunks) if c]
            else:
                aliases_list = [aliases_text]

        other_information_parts = []
        if place_of_birth_text:
            other_information_parts.append("Place of birth: " + place_of_birth_text)
        if schedule_text:
            other_information_parts.append("Schedule: " + schedule_text)
        if title_or_ship_text:
            other_information_parts.append("TitleOrShip: " + title_or_ship_text)
        if entity_or_ship_text:
            other_information_parts.append("EntityOrShip: " + entity_or_ship_text)

        sanctions_program_name_value = None
        if country_text:
            sanctions_program_name_value = "SEMA-" + country_text

        record = {
            "list_name": list_name_value,
            "list_id": item_text,
            "full_name": full_name_value or None,
            "first_name": given_name_text or None,
            "middle_name": None,
            "last_name": last_name_text or None,
            "other_first_name": None,
            "sex": None,
            "nationality": None,
            "citizenship_country": None,
            "citizenship_country_iso": None,
            "place_of_birth_text": None,
            "birth_year": birth_year_value,
            "birth_month": birth_month_value,
            "birth_day": birth_day_value,
            "primary_address_value": None,
            "address_country": country_text or None,
            "address_country_iso": None,
            "address_location": None,
            "address_area": None,
            "address_city": None,
            "address_state": None,
            "address_postal_code": None,
            "address_details": None,
            "justification_text": None,
            "other_information_text": "; ".join(other_information_parts) if other_information_parts else None,
            "sanctions_program_name": sanctions_program_name_value,
            "publication_date": listed_text or None,
            "enactment_date": listed_text or None,
            "effective_date": listed_text or None,
            "aliases": aliases_list,
            "vessel_flag": country_text if classification_value == "vessel" else None,
            "vessel_imo": ship_imo_number_text or None,
            "classification": classification_value,
            "CA_entity_type": entity_or_ship_text or None,
            "CA_reference_number": list_identifier_value
        }
        records.append(record)
    return records
