import xml.etree.ElementTree as ET
from countrycode import country_to_iso2
import requests
from datetime import datetime, timezone
from pathlib import Path
import logging
from config import get_config
cfg = get_config()

UN_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
UN_XML = "UN.06.10.25.xml"

def UN_fetch():
    try:
        resp = requests.get(UN_URL, timeout=120)
        resp.raise_for_status()
        xml_bytes = resp.content
        if not xml_bytes:
            raise ValueError("empty body")
        log_path = cfg.paths.DATA_DIR / "UNlog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat() + "\n")
        return ET.fromstring(xml_bytes)
    except Exception as e:
        local = Path(__file__).parent.parent / "data" / UN_XML
        if local.exists():
            logging.error("UN download failed; using backup file %s", local, exc_info=True)
            return ET.parse(str(local)).getroot()
        raise RuntimeError(f"UN download failed and no backup found at {local}: {e}")

def UN_extract(xml_root):
    records = []
    if xml_root is None:
        return records
    list_name_value = "UN"
    for individuals_container in xml_root.findall(".//INDIVIDUALS"):
        for person_element in individuals_container.findall("INDIVIDUAL"):
            list_identifier_value = ((person_element.findtext("DATAID") or "").strip()) or None
            if not list_identifier_value:
                continue
            first_name_value = ((person_element.findtext("FIRST_NAME") or "").strip()) or None
            second_name_value = ((person_element.findtext("SECOND_NAME") or "").strip()) or None
            third_name_value = ((person_element.findtext("THIRD_NAME") or "").strip()) or None
            fourth_name_value = ((person_element.findtext("FOURTH_NAME") or "").strip()) or None
            full_name_parts = [x for x in [first_name_value, second_name_value, third_name_value, fourth_name_value] if x]
            full_name_value = " ".join(full_name_parts) if full_name_parts else None
            primary_name_value = full_name_value
            primary_name_language_value = None
            primary_name_quality_value = None
            birth_year_value = None
            birth_month_value = None
            birth_day_value = None
            sex_value = None
            justification_text_value = None
            other_information_text_value = None
            nationality_value = None
            citizenship_country_value = None
            citizenship_country_iso_value = None
            address_country_value = None
            address_city_value = None
            address_state_value = None
            address_postal_code_value = None
            primary_address_value = None
            address_country_iso_value = None
            aliases_list_value = []
            alternative_addresses_value = []
            for nationality_element in person_element.findall("NATIONALITY"):
                text_value = (nationality_element.text or "").strip()
                if text_value:
                    if nationality_value:
                        nationality_value = f"{nationality_value}; {text_value}"
                    else:
                        nationality_value = text_value
            for citizenship_element in person_element.findall("CITIZENSHIP"):
                text_value = (citizenship_element.text or "").strip()
                if text_value:
                    if citizenship_country_value:
                        citizenship_country_value = f"{citizenship_country_value}; {text_value}"
                    else:
                        citizenship_country_value = text_value
            if citizenship_country_value:
                try:
                    iso2_code = country_to_iso2(citizenship_country_value)
                    if iso2_code:
                        citizenship_country_iso_value = iso2_code.upper()
                except Exception:
                    pass
            individual_dob_container = person_element.find("INDIVIDUAL_DATE_OF_BIRTH")
            if individual_dob_container is not None:
                day_text = (individual_dob_container.findtext("DAY") or "").strip()
                month_text = (individual_dob_container.findtext("MONTH") or "").strip()
                year_text = (individual_dob_container.findtext("YEAR") or "").strip()
                birth_day_value = day_text or None
                birth_month_value = month_text or None
                birth_year_value = year_text or None
            sex_text_value = (person_element.findtext("GENDER") or "").strip()
            if sex_text_value:
                sex_value = sex_text_value
            individual_pob_container = person_element.find("INDIVIDUAL_PLACE_OF_BIRTH")
            place_of_birth_value = None
            if individual_pob_container is not None:
                pob_city_value = (individual_pob_container.findtext("CITY") or "").strip()
                pob_country_value = (individual_pob_container.findtext("COUNTRY") or "").strip()
                pob_state_value = (individual_pob_container.findtext("STATE_PROVINCE") or "").strip()
                pob_note_value = (individual_pob_container.findtext("NOTE") or "").strip()
                pieces = [x for x in [pob_city_value or None, pob_state_value or None, pob_country_value or None, pob_note_value or None] if x]
                place_of_birth_value = ", ".join(pieces) if pieces else None
                if not nationality_value and pob_country_value:
                    nationality_value = pob_country_value
            individual_address_container_list = person_element.findall("INDIVIDUAL_ADDRESS")
            for address_element in individual_address_container_list:
                street_text = (address_element.findtext("STREET") or "").strip()
                city_text = (address_element.findtext("CITY") or "").strip()
                state_text = (address_element.findtext("STATE_PROVINCE") or "").strip()
                postal_text = (address_element.findtext("POSTAL_CODE") or "").strip()
                country_text = (address_element.findtext("COUNTRY") or "").strip()
                note_text = (address_element.findtext("NOTE") or "").strip()
                if street_text and not primary_address_value:
                    primary_address_value = street_text
                if city_text and not address_city_value:
                    address_city_value = city_text
                if state_text and not address_state_value:
                    address_state_value = state_text
                if postal_text and not address_postal_code_value:
                    address_postal_code_value = postal_text
                if country_text and not address_country_value:
                    address_country_value = country_text
                items = [x for x in [street_text or None, city_text or None, state_text or None, postal_text or None, country_text or None, note_text or None] if x]
                if items:
                    alternative_addresses_value.append(", ".join(items))
            if address_country_value:
                try:
                    iso2_code = country_to_iso2(address_country_value)
                    if iso2_code:
                        address_country_iso_value = iso2_code.upper()
                except Exception:
                    pass
            aliases_container_list = person_element.findall("INDIVIDUAL_ALIAS")
            for alias_element in aliases_container_list:
                alias_value = (alias_element.findtext("ALIAS_NAME") or "").strip()
                if alias_value:
                    aliases_list_value.append(alias_value)
            designation_texts = []
            for designation_element in person_element.findall("DESIGNATION"):
                t = (designation_element.text or "").strip()
                if t:
                    designation_texts.append(t)
            last_day_updated_container = person_element.find("LAST_DAY_UPDATED")
            last_updated_text_value = None
            if last_day_updated_container is not None:
                du = []
                y = (last_day_updated_container.findtext("YEAR") or "").strip()
                m = (last_day_updated_container.findtext("MONTH") or "").strip()
                d = (last_day_updated_container.findtext("DAY") or "").strip()
                if y:
                    du.append(y)
                if m:
                    du.append(m.zfill(2))
                if d:
                    du.append(d.zfill(2))
                if du:
                    last_updated_text_value = "-".join(du)
            listed_on_text_value = (person_element.findtext("LISTED_ON") or "").strip()
            additional_information_text_value = (person_element.findtext("COMMENTS1") or "").strip()
            if additional_information_text_value:
                other_information_text_value = additional_information_text_value
            if designation_texts:
                if other_information_text_value:
                    other_information_text_value = other_information_text_value + " | " + " ; ".join(designation_texts)
                else:
                    other_information_text_value = " ; ".join(designation_texts)
            record = {}
            record["UN_list_name"] = list_name_value
            record["list_name"] = list_name_value
            record["UN_reference_number"] = list_identifier_value
            record["UN_id"] = list_identifier_value
            record["list_id"] = list_identifier_value
            record["UN_full_name"] = full_name_value
            record["full_name"] = full_name_value
            record["UN_first_name"] = first_name_value
            record["first_name"] = first_name_value
            record["UN_middle_name"] = third_name_value
            record["middle_name"] = third_name_value
            record["UN_last_name"] = second_name_value or fourth_name_value
            record["last_name"] = second_name_value or fourth_name_value
            record["UN_nationality"] = nationality_value
            record["nationality"] = nationality_value
            record["UN_citizenship_country"] = citizenship_country_value
            record["citizenship_country"] = citizenship_country_value
            record["UN_citizenship_country_iso"] = citizenship_country_iso_value
            record["citizenship_country_iso"] = citizenship_country_iso_value
            record["UN_address_country"] = address_country_value
            record["address_country"] = address_country_value
            record["UN_address_city"] = address_city_value
            record["address_city"] = address_city_value
            record["UN_address_state"] = address_state_value
            record["address_state"] = address_state_value
            record["UN_address_postal_code"] = address_postal_code_value
            record["address_postal_code"] = address_postal_code_value
            record["UN_primary_address_value"] = primary_address_value
            record["primary_address_value"] = primary_address_value
            record["UN_address_country_iso"] = address_country_iso_value
            record["address_country_iso"] = address_country_iso_value
            record["UN_aliases"] = aliases_list_value
            record["aliases"] = aliases_list_value
            record["UN_all_addresses"] = alternative_addresses_value
            record["alternative_addresses"] = alternative_addresses_value
            record["UN_birth_year"] = birth_year_value
            record["birth_year"] = birth_year_value
            record["UN_birth_month"] = birth_month_value
            record["birth_month"] = birth_month_value
            record["UN_birth_day"] = birth_day_value
            record["birth_day"] = birth_day_value
            record["UN_sex"] = sex_value
            record["sex"] = sex_value
            record["UN_justification_text"] = justification_text_value
            record["justification_text"] = justification_text_value
            record["UN_other_information_text"] = other_information_text_value
            record["other_information_text"] = other_information_text_value
            record["UN_listed_on"] = listed_on_text_value or None
            record["UN_last_updated"] = last_updated_text_value or None
            records.append(record)
    for entities_container in xml_root.findall(".//ENTITIES"):
        for entity_element in entities_container.findall("ENTITY"):
            list_identifier_value = ((entity_element.findtext("REFERENCE_NUMBER") or "").strip()) or None
            if not list_identifier_value:
                continue
            name_value = ((entity_element.findtext("FIRST_NAME") or "").strip()) or None
            if not name_value:
                name_value = ((entity_element.findtext("NAME") or "").strip()) or None
            full_name_value = name_value or None
            nationality_value = None
            citizenship_country_value = None
            citizenship_country_iso_value = None
            address_country_value = None
            address_city_value = None
            address_state_value = None
            address_postal_code_value = None
            primary_address_value = None
            address_country_iso_value = None
            aliases_list_value = []
            alternative_addresses_value = []
            designation_texts = []
            for designation_element in entity_element.findall("DESIGNATION"):
                t = (designation_element.text or "").strip()
                if t:
                    designation_texts.append(t)
            additional_information_text_value = (entity_element.findtext("COMMENTS1") or "").strip()
            other_information_text_value = additional_information_text_value or None
            entity_address_container_list = entity_element.findall("ENTITY_ADDRESS")
            for address_element in entity_address_container_list:
                street_text = (address_element.findtext("STREET") or "").strip()
                city_text = (address_element.findtext("CITY") or "").strip()
                state_text = (address_element.findtext("STATE_PROVINCE") or "").strip()
                postal_text = (address_element.findtext("POSTAL_CODE") or "").strip()
                country_text = (address_element.findtext("COUNTRY") or "").strip()
                note_text = (address_element.findtext("NOTE") or "").strip()
                if street_text and not primary_address_value:
                    primary_address_value = street_text
                if city_text and not address_city_value:
                    address_city_value = city_text
                if state_text and not address_state_value:
                    address_state_value = state_text
                if postal_text and not address_postal_code_value:
                    address_postal_code_value = postal_text
                if country_text and not address_country_value:
                    address_country_value = country_text
                items = [x for x in [street_text or None, city_text or None, state_text or None, postal_text or None, country_text or None, note_text or None] if x]
                if items:
                    alternative_addresses_value.append(", ".join(items))
            if address_country_value:
                try:
                    iso2_code = country_to_iso2(address_country_value)
                    if iso2_code:
                        address_country_iso_value = iso2_code.upper()
                except Exception:
                    pass
            aliases_container_list = entity_element.findall("ENTITY_ALIAS")
            for alias_element in aliases_container_list:
                alias_value = (alias_element.findtext("ALIAS_NAME") or "").strip()
                if alias_value:
                    aliases_list_value.append(alias_value)
            last_day_updated_container = entity_element.find("LAST_DAY_UPDATED")
            last_updated_text_value = None
            if last_day_updated_container is not None:
                du = []
                y = (last_day_updated_container.findtext("YEAR") or "").strip()
                m = (last_day_updated_container.findtext("MONTH") or "").strip()
                d = (last_day_updated_container.findtext("DAY") or "").strip()
                if y:
                    du.append(y)
                if m:
                    du.append(m.zfill(2))
                if d:
                    du.append(d.zfill(2))
                if du:
                    last_updated_text_value = "-".join(du)
            listed_on_text_value = (entity_element.findtext("LISTED_ON") or "").strip()
            record = {}
            record["UN_list_name"] = list_name_value
            record["list_name"] = list_name_value
            record["UN_reference_number"] = list_identifier_value
            record["UN_id"] = list_identifier_value
            record["list_id"] = list_identifier_value
            record["UN_full_name"] = full_name_value
            record["full_name"] = full_name_value
            record["UN_nationality"] = nationality_value
            record["nationality"] = nationality_value
            record["UN_citizenship_country"] = citizenship_country_value
            record["citizenship_country"] = citizenship_country_value
            record["UN_citizenship_country_iso"] = citizenship_country_iso_value
            record["place_of_birth_text"] = place_of_birth_value
            record["citizenship_country_iso"] = citizenship_country_iso_value
            record["UN_address_country"] = address_country_value
            record["address_country"] = address_country_value
            record["UN_address_city"] = address_city_value
            record["address_city"] = address_city_value
            record["UN_address_state"] = address_state_value
            record["address_state"] = address_state_value
            record["UN_address_postal_code"] = address_postal_code_value
            record["address_postal_code"] = address_postal_code_value
            record["UN_primary_address_value"] = primary_address_value
            record["primary_address_value"] = primary_address_value
            record["UN_address_country_iso"] = address_country_iso_value
            record["address_country_iso"] = address_country_iso_value
            record["UN_aliases"] = aliases_list_value
            record["aliases"] = aliases_list_value
            record["UN_all_addresses"] = alternative_addresses_value
            record["alternative_addresses"] = alternative_addresses_value
            if designation_texts:
                if other_information_text_value:
                    other_information_text_value = other_information_text_value + " | " + " ; ".join(designation_texts)
                else:
                    other_information_text_value = " ; ".join(designation_texts)
            record["UN_justification_text"] = None
            record["justification_text"] = None
            record["UN_other_information_text"] = other_information_text_value
            record["other_information_text"] = other_information_text_value
            record["UN_listed_on"] = listed_on_text_value or None
            record["UN_last_updated"] = last_updated_text_value or None
            records.append(record)
    return records
