import xml.etree.ElementTree as ET
from countrycode import country_to_iso2
import requests
from datetime import datetime, timezone
from pathlib import Path
import logging
from config import get_config
cfg = get_config()

UK_URL = "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml"
UK_XML = "UK.08.10.25.xml"

def UK_fetch():
    try:
        resp = requests.get(UK_URL, timeout=120)
        resp.raise_for_status()
        xml_bytes = resp.content
        if not xml_bytes:
            raise ValueError("empty body")
        log_path = cfg.paths.DATA_DIR / "UKlog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat() + "\n")
        return ET.fromstring(xml_bytes)
    except Exception as e:
        local = Path(__file__).parent.parent / "data" / UK_XML
        if local.exists():
            logging.error("UK download failed; using backup file %s", local, exc_info=True)
            return ET.parse(str(local)).getroot()
        raise RuntimeError(f"UK download failed and no backup found at {local}: {e}")

def UK_extract(xml_root):
    records = []
    for designation_element in xml_root.findall("Designation"):
        list_name_value = "UK"
        list_identifier_value = (designation_element.findtext("UniqueID") or "").strip()
        if not list_identifier_value:
            continue
        last_updated_text_value = (designation_element.findtext("LastUpdated") or "").strip()
        date_designated_text_value = (designation_element.findtext("DateDesignated") or "").strip()
        ofsi_group_id_text_value = (designation_element.findtext("OFSIGroupID") or "").strip()
        un_reference_number_text_value = (designation_element.findtext("UNReferenceNumber") or "").strip()
        regime_name_text_value = (designation_element.findtext("RegimeName") or "").strip()
        individual_entity_ship_text_value = (designation_element.findtext("IndividualEntityShip") or "").strip()
        designation_source_text_value = (designation_element.findtext("DesignationSource") or "").strip()
        sanctions_imposed_text_value = (designation_element.findtext("SanctionsImposed") or "").strip()
        sanctions_imposed_indicators_text_value = (designation_element.findtext("SanctionsImposedIndicators") or "").strip()
        other_information_text_value_raw = (designation_element.findtext("OtherInformation") or "").strip()
        uk_statement_of_reasons_text_value = (designation_element.findtext("UKStatementofReasons") or "").strip()
        publication_date_value = last_updated_text_value or None
        enactment_date_value = date_designated_text_value or None
        effective_date_value = date_designated_text_value or None
        sanctions_program_name_value = regime_name_text_value or None
        justification_text_value = uk_statement_of_reasons_text_value or None
        other_information_text_parts = []
        if ofsi_group_id_text_value:
            other_information_text_parts.append("OFSIGroupID: " + ofsi_group_id_text_value)
        if un_reference_number_text_value:
            other_information_text_parts.append("UNReferenceNumber: " + un_reference_number_text_value)
        if designation_source_text_value:
            other_information_text_parts.append("DesignationSource: " + designation_source_text_value)
        if individual_entity_ship_text_value:
            other_information_text_parts.append("SubjectType: " + individual_entity_ship_text_value)
        if sanctions_imposed_text_value:
            other_information_text_parts.append("SanctionsImposed: " + sanctions_imposed_text_value)
        indicators_node = designation_element.find("SanctionsImposedIndicators")
        if indicators_node is not None:
            true_flags_collected = []
            for child in list(indicators_node):
                child_text_value = (child.text or "").strip().lower()
                if child_text_value == "true":
                    tag_name_text = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    readable_name_text = "".join((" " + c if c.isupper() else c) for c in tag_name_text).strip().title()
                    true_flags_collected.append(readable_name_text)
            if true_flags_collected:
                other_information_text_parts.append("SanctionsIndicators: " + "|".join(true_flags_collected))
        if other_information_text_value_raw:
            other_information_text_parts.append(other_information_text_value_raw)
        primary_name_value = None
        primary_name_language_value = None
        primary_name_quality_value = None
        first_spelling_variant_value = None
        full_name_value = None
        first_name_value = None
        middle_name_value = None
        last_name_value = None
        other_first_name_value = None
        aliases_list = []
        names_container = designation_element.find("Names")
        chosen_primary_name_node = None
        if names_container is not None:
            primary_name_candidates = []
            for name_node in names_container.findall("Name"):
                name_type_text_value = (name_node.findtext("NameType") or "").strip().lower()
                has_bits = False
                for i_index in ("Name1", "Name2", "Name3", "Name4", "Name5", "Name6"):
                    if (name_node.findtext(i_index) or "").strip():
                        has_bits = True
                        break
                if name_type_text_value == "primary name" and has_bits:
                    primary_name_candidates.append(name_node)
            if primary_name_candidates:
                chosen_primary_name_node = primary_name_candidates[0]
            else:
                any_with_bits = []
                for name_node in names_container.findall("Name"):
                    has_bits = False
                    for i_index in ("Name1", "Name2", "Name3", "Name4", "Name5", "Name6"):
                        if (name_node.findtext(i_index) or "").strip():
                            has_bits = True
                            break
                    if has_bits:
                        any_with_bits.append(name_node)
                if any_with_bits:
                    chosen_primary_name_node = any_with_bits[0]
                else:
                    chosen_primary_name_node = names_container.find("Name")
            if chosen_primary_name_node is not None:
                n1 = (chosen_primary_name_node.findtext("Name1") or "").strip()
                n2 = (chosen_primary_name_node.findtext("Name2") or "").strip()
                n3 = (chosen_primary_name_node.findtext("Name3") or "").strip()
                n4 = (chosen_primary_name_node.findtext("Name4") or "").strip()
                n5 = (chosen_primary_name_node.findtext("Name5") or "").strip()
                n6 = (chosen_primary_name_node.findtext("Name6") or "").strip()
                assembled_name_parts_list = []
                if n1: assembled_name_parts_list.append(n1)
                if n2: assembled_name_parts_list.append(n2)
                if n3: assembled_name_parts_list.append(n3)
                if n4: assembled_name_parts_list.append(n4)
                if n5: assembled_name_parts_list.append(n5)
                if n6: assembled_name_parts_list.append(n6)
                assembled_full_name_value = " ".join(x for x in assembled_name_parts_list if x)
                if assembled_full_name_value:
                    full_name_value = assembled_full_name_value
                    primary_name_value = assembled_full_name_value
                    primary_name_quality_value = "primary"
                for alias_node in names_container.findall("Name"):
                    if alias_node is chosen_primary_name_node:
                        continue
                    a1 = (alias_node.findtext("Name1") or "").strip()
                    a2 = (alias_node.findtext("Name2") or "").strip()
                    a3 = (alias_node.findtext("Name3") or "").strip()
                    a4 = (alias_node.findtext("Name4") or "").strip()
                    a5 = (alias_node.findtext("Name5") or "").strip()
                    a6 = (alias_node.findtext("Name6") or "").strip()
                    alias_parts_values = []
                    if a1: alias_parts_values.append(a1)
                    if a2: alias_parts_values.append(a2)
                    if a3: alias_parts_values.append(a3)
                    if a4: alias_parts_values.append(a4)
                    if a5: alias_parts_values.append(a5)
                    if a6: alias_parts_values.append(a6)
                    alias_assembled_value = " ".join(x for x in alias_parts_values if x)
                    if alias_assembled_value and alias_assembled_value not in aliases_list:
                        aliases_list.append(alias_assembled_value)
        non_latin_names_container = designation_element.find("NonLatinNames")
        if non_latin_names_container is not None:
            for nonlatin_node in non_latin_names_container.findall("NonLatinName"):
                script_text_value = (nonlatin_node.findtext("NameNonLatinScript") or "").strip()
                if script_text_value and script_text_value not in aliases_list:
                    aliases_list.append(script_text_value)
        if not first_name_value and not middle_name_value and not last_name_value and chosen_primary_name_node is not None and (individual_entity_ship_text_value or "").strip().lower() == "individual":
            n1 = (chosen_primary_name_node.findtext("Name1") or "").strip()
            n2 = (chosen_primary_name_node.findtext("Name2") or "").strip()
            n3 = (chosen_primary_name_node.findtext("Name3") or "").strip()
            n4 = (chosen_primary_name_node.findtext("Name4") or "").strip()
            n5 = (chosen_primary_name_node.findtext("Name5") or "").strip()
            n6 = (chosen_primary_name_node.findtext("Name6") or "").strip()
            first_name_value = n1 or None
            middle_collect_values = []
            if n2: middle_collect_values.append(n2)
            if n3: middle_collect_values.append(n3)
            if n4: middle_collect_values.append(n4)
            if n5: middle_collect_values.append(n5)
            middle_name_value = (" ".join(middle_collect_values)).strip() if middle_collect_values else None
            last_name_value = n6 or None
        if full_name_value and not first_name_value:
            tokens_for_name_split = [t for t in full_name_value.split() if t]
            if len(tokens_for_name_split) == 1:
                first_name_value = tokens_for_name_split[0]
            elif len(tokens_for_name_split) == 2:
                first_name_value = tokens_for_name_split[0]
                last_name_value = tokens_for_name_split[1]
            elif len(tokens_for_name_split) >= 3:
                first_name_value = tokens_for_name_split[0]
                last_name_value = tokens_for_name_split[-1]
                inner_middle_value = " ".join(tokens_for_name_split[1:-1]).strip()
                middle_name_value = inner_middle_value if inner_middle_value else None
        primary_address_value_value = None
        address_country_value = None
        address_country_iso_value = None
        address_city_value = None
        address_state_value = None
        address_postal_code_value = None
        address_area_value = None
        address_location_value = None
        address_details_value = None
        alternative_addresses_value_list = []
        alternative_cities_list = []
        alternative_states_list = []
        alternative_postal_codes_list = []
        alternative_countries_list = []
        alternative_country_isos_list = []
        addresses_container = designation_element.find("Addresses")
        if addresses_container is not None:
            for address_node in addresses_container.findall("Address"):
                address_line_1_value = (address_node.findtext("AddressLine1") or "").strip()
                address_line_2_value = (address_node.findtext("AddressLine2") or "").strip()
                address_line_3_value = (address_node.findtext("AddressLine3") or "").strip()
                address_line_4_value = (address_node.findtext("AddressLine4") or "").strip()
                address_line_5_value = (address_node.findtext("AddressLine5") or "").strip()
                address_line_6_value = (address_node.findtext("AddressLine6") or "").strip()
                address_postal_code_text_value = (address_node.findtext("AddressPostalCode") or "").strip()
                address_country_text_value = (address_node.findtext("AddressCountry") or "").strip()
                parts_for_primary = []
                if address_line_1_value: parts_for_primary.append(address_line_1_value)
                if address_line_2_value: parts_for_primary.append(address_line_2_value)
                if address_line_3_value: parts_for_primary.append(address_line_3_value)
                if address_line_4_value: parts_for_primary.append(address_line_4_value)
                if address_line_5_value: parts_for_primary.append(address_line_5_value)
                if address_line_6_value: parts_for_primary.append(address_line_6_value)
                if address_postal_code_text_value: parts_for_primary.append(address_postal_code_text_value)
                if address_country_text_value: parts_for_primary.append(address_country_text_value)
                assembled_address_text_value = " | ".join(x for x in parts_for_primary if x)
                if assembled_address_text_value:
                    alternative_addresses_value_list.append(assembled_address_text_value)
                    if primary_address_value_value is None:
                        primary_address_value_value = assembled_address_text_value
                if address_line_5_value:
                    alternative_cities_list.append(address_line_5_value)
                    if address_city_value is None:
                        address_city_value = address_line_5_value
                if address_line_6_value:
                    alternative_states_list.append(address_line_6_value)
                    if address_state_value is None:
                        address_state_value = address_line_6_value
                if address_postal_code_text_value:
                    alternative_postal_codes_list.append(address_postal_code_text_value)
                    if address_postal_code_value is None:
                        address_postal_code_value = address_postal_code_text_value
                if address_country_text_value:
                    alternative_countries_list.append(address_country_text_value)
                    if address_country_value is None:
                        address_country_value = address_country_text_value
            if alternative_addresses_value_list:
                address_details_value = " || ".join(alternative_addresses_value_list)
        contact_phone_numbers_list_value = []
        phones_container = designation_element.find("PhoneNumbers")
        if phones_container is not None:
            for phone_node in phones_container.findall("PhoneNumber"):
                phone_text_value = (phone_node.text or "").strip()
                if phone_text_value:
                    contact_phone_numbers_list_value.append(phone_text_value)
        contact_emails_list_value = []
        emails_container = designation_element.find("EmailAddresses")
        if emails_container is not None:
            for email_node in emails_container.findall("EmailAddress"):
                email_text_value = (email_node.text or "").strip()
                if email_text_value:
                    contact_emails_list_value.append(email_text_value)
        sex_value = None
        nationality_value = None
        citizenship_country_value = None
        citizenship_country_iso_value = None
        place_of_birth_text_value = None
        birth_year_value = None
        birth_month_value = None
        birth_day_value = None
        passport_details_value = None
        national_identifier_details_value = None
        website_value = None
        phone_number_value = None
        email_address_value = None
        business_registration_number_value = None
        individual_node = designation_element.find("./IndividualDetails/Individual")
        if individual_node is not None:
            dob_text_value = (individual_node.findtext("DOBs/DOB") or "").strip()
            if dob_text_value:
                parts_for_date = dob_text_value.split("/")
                if len(parts_for_date) == 3 and all(parts_for_date):
                    try:
                        birth_day_value = int(parts_for_date[0])
                        birth_month_value = int(parts_for_date[1])
                        birth_year_value = int(parts_for_date[2])
                    except Exception:
                        pass
            sex_extracted_value = (individual_node.findtext("Genders/Gender") or "").strip()
            if sex_extracted_value:
                sex_value = sex_extracted_value
            pob_town_value = (individual_node.findtext("BirthDetails/Location/TownOfBirth") or "").strip()
            pob_country_value = (individual_node.findtext("BirthDetails/Location/CountryOfBirth") or "").strip()
            if pob_town_value or pob_country_value:
                place_of_birth_text_value = ", ".join([p for p in (pob_town_value, pob_country_value) if p])
            positions_container = individual_node.find("Positions")
            if positions_container is not None:
                positions_collected = []
                for pos_node in positions_container.findall("Position"):
                    pos_text_value = (pos_node.text or "").strip()
                    if pos_text_value:
                        positions_collected.append(pos_text_value)
                if positions_collected:
                    other_information_text_parts.append("Positions: " + " | ".join(positions_collected))
        def _dedup_keep_order(seq):
            seen = set()
            out = []
            for s in seq:
                if not s:
                    continue
                key = s.strip().lower()
                if key not in seen:
                    seen.add(key)
                    out.append(s.strip())
            return out
        record_map = {
            "list_name": list_name_value,
            "list_id": list_identifier_value,
            "classification": individual_entity_ship_text_value or None,
            "full_name": full_name_value,
            "first_name": first_name_value,
            "middle_name": middle_name_value,
            "last_name": last_name_value,
            "other_first_name": other_first_name_value,
            "sex": sex_value,
            "nationality": nationality_value,
            "citizenship_country": citizenship_country_value,
            "citizenship_country_iso": citizenship_country_iso_value,
            "place_of_birth_text": place_of_birth_text_value,
            "birth_year": birth_year_value,
            "birth_month": birth_month_value,
            "birth_day": birth_day_value,
            "primary_address_value": primary_address_value_value,
            "address_country": address_country_value,
            "address_country_iso": address_country_iso_value,
            "address_location": address_location_value,
            "address_area": address_area_value,
            "address_city": address_city_value,
            "address_state": address_state_value,
            "address_postal_code": address_postal_code_value,
            "address_details": address_details_value,
            "justification_text": justification_text_value,
            "other_information_text": ("; ".join([p for p in other_information_text_parts if p]) if other_information_text_parts else None),
            "sanctions_program_name": sanctions_program_name_value,
            "publication_date": publication_date_value,
            "enactment_date": enactment_date_value,
            "effective_date": effective_date_value,
            "aliases": _dedup_keep_order(aliases_list),
            "email_addresses": _dedup_keep_order(contact_emails_list_value),
            "phone_numbers": _dedup_keep_order(contact_phone_numbers_list_value),
            "all_addresses": _dedup_keep_order(alternative_addresses_value_list),
            "alternative_cities": _dedup_keep_order(alternative_cities_list),
            "alternative_states": _dedup_keep_order(alternative_states_list),
            "alternative_postal_codes": _dedup_keep_order(alternative_postal_codes_list),
            "alternative_countries": _dedup_keep_order(alternative_countries_list),
            "alternative_country_isos": _dedup_keep_order(alternative_country_isos_list)
        }
        records.append(record_map)
    return records
