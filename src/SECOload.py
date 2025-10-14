import xml.etree.ElementTree as ET
import requests
from countrycode import country_to_iso2
from pathlib import Path
import re
import logging
from datetime import datetime, timezone
from config import get_config
cfg = get_config()

SECO_URL = "https://www.sesam.search.admin.ch/sesam-search-web/pages/downloadXmlGesamtliste.xhtml?action=downloadXmlGesamtlisteAction&lang=en"
SECO_XML = "SECO.8.10.25.xml"

def SECO_fetch():
    try:
        resp = requests.get(SECO_URL, timeout=120)
        resp.raise_for_status()
        xml_bytes = resp.content
        if not xml_bytes:
            raise ValueError("empty body")
        log_path = cfg.paths.DATA_DIR / "SECOlog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat() + "\n")
        return ET.fromstring(xml_bytes)
    except Exception as e:
        local = Path(__file__).parent.parent / "data" / SECO_XML
        if local.exists():
            logging.error("SECO download failed; using backup file", e, local)
            return ET.parse(str(local)).getroot()
        raise RuntimeError(f"SECO download failed and no backup found at {local}: {e}")

def SECO_extract(xml_root):
    records = []
    if xml_root is None:
        return records

    sanctions_set_name_by_id = {}
    program_name_by_set_id = {}
    program_origin_by_set_id = {}
    version_date_by_program_ssid = {}

    for sanctions_program_element in xml_root.findall(".//sanctions-program"):
        program_ssid_text = sanctions_program_element.get("ssid") or ""
        version_date_text = sanctions_program_element.get("version-date") or ""
        if program_ssid_text:
            version_date_by_program_ssid[program_ssid_text] = version_date_text
        for program_name_element in sanctions_program_element.findall("./program-name"):
            program_name_text_value = (program_name_element.text or "").strip()
            program_name_lang_value = program_name_element.get("lang") or ""
            for sanctions_set_element in sanctions_program_element.findall("./sanctions-set"):
                set_ssid_text_value = sanctions_set_element.get("ssid") or ""
                if set_ssid_text_value:
                    sanctions_set_name_by_id[set_ssid_text_value] = (sanctions_set_element.text or "").strip() or program_name_text_value
                    program_name_by_set_id[set_ssid_text_value] = program_name_text_value
        origin_text_value = None
        for origin_element in sanctions_program_element.findall("./origin"):
            origin_text_value = (origin_element.text or "").strip() or origin_text_value
        if origin_text_value:
            for sanctions_set_element in sanctions_program_element.findall("./sanctions-set"):
                set_ssid_text_value = sanctions_set_element.get("ssid") or ""
                if set_ssid_text_value:
                    program_origin_by_set_id[set_ssid_text_value] = origin_text_value

    place_by_id = {}
    for place_element in xml_root.findall(".//place"):
        place_ssid_text = place_element.get("ssid") or ""
        location_text_value = None
        area_text_value = None
        country_text_value = None
        country_iso_text_value = None
        for child in list(place_element):
            child_local_name = child.tag.split("}")[-1] if isinstance(child.tag, str) else child.tag
            if child_local_name == "location" and child.text and child.text.strip():
                location_text_value = child.text.strip()
            elif child_local_name == "area" and child.text and child.text.strip():
                area_text_value = child.text.strip()
            elif child_local_name == "country":
                if child.text and child.text.strip():
                    country_text_value = child.text.strip()
                iso_attr = child.get("iso-code")
                if iso_attr:
                    country_iso_text_value = iso_attr.strip().upper()
        if place_ssid_text:
            place_by_id[place_ssid_text] = {
                "location": location_text_value,
                "area": area_text_value,
                "country": country_text_value,
                "country_iso": country_iso_text_value
            }

    for target_element in xml_root.findall(".//target"):
        list_name_value = "SECO"
        target_ssid_text = target_element.get("ssid") or ""
        if not target_ssid_text:
            continue

        sanctions_set_ids = []
        for set_id_element in target_element.findall("./sanctions-set-id"):
            set_id_text = (set_id_element.text or "").strip()
            if set_id_text:
                sanctions_set_ids.append(set_id_text)

        foreign_identifier_text_value = None
        foreign_identifier_element = target_element.find("./foreign-identifier")
        if foreign_identifier_element is not None and foreign_identifier_element.text and foreign_identifier_element.text.strip():
            foreign_identifier_text_value = foreign_identifier_element.text.strip()

        subject_type_value = None
        subject_sex_value = None
        identity_elements = []
        container_local_name = None

        individual_element = target_element.find("./individual")
        entity_element = target_element.find("./entity")
        object_element = target_element.find("./object")

        if individual_element is not None:
            subject_type_value = "Individual"
            subject_sex_value = individual_element.get("sex") or None
            identity_elements = individual_element.findall("./identity")
            container_local_name = "individual"
        elif entity_element is not None:
            subject_type_value = "Entity"
            identity_elements = entity_element.findall("./identity")
            container_local_name = "entity"
        elif object_element is not None:
            subject_type_value = "Object"
            identity_elements = object_element.findall("./identity")
            container_local_name = "object"

        primary_name_value = None
        primary_name_language_value = None
        primary_name_quality_value = None
        first_name_value = None
        middle_name_value = None
        last_name_value = None
        other_first_name_value = None
        first_spelling_variant_value = None
        aliases_list = []
        justification_text_value = None
        other_information_text_value = None
        nationality_country_value = None
        citizenship_country_value = None
        citizenship_country_iso_value = None
        birth_year_value = None
        birth_month_value = None
        birth_day_value = None
        primary_address_value = None
        address_city_value = None
        address_state_value = None
        address_postal_code_value = None
        address_country_value = None
        address_country_iso_value = None
        alternative_addresses_values = []
        contact_emails_values = []
        contact_phone_numbers_values = []
        contact_fax_numbers_values = []
        contact_websites_values = []
        bic_codes_values = []
        iban_numbers_values = []
        ssn_numbers_values = []
        passport_numbers_values = []
        national_id_numbers_values = []
        tax_id_numbers_values = []
        other_id_numbers_values = []
        sanctions_program_name_value = None
        publication_date_value = None
        enactment_date_value = None
        effective_date_value = None
        seco_entity_type_value = None
        seco_primary_name_language_value = None
        seco_primary_name_quality_value = None
        place_of_birth_text_value = None

        if container_local_name == "object":
            seco_entity_type_value = object_element.get("type") or None

        latest_enactment_date_raw = None
        latest_publication_date_raw = None
        latest_effective_date_raw = None
        for modification_element in target_element.findall("./modification"):
            enact_attr = modification_element.get("enactment-date")
            pub_attr = modification_element.get("publication-date")
            eff_attr = modification_element.get("effective-date")
            if enact_attr:
                latest_enactment_date_raw = enact_attr
            if pub_attr:
                latest_publication_date_raw = pub_attr
            if eff_attr:
                latest_effective_date_raw = eff_attr
        publication_date_value = latest_publication_date_raw
        enactment_date_value = latest_enactment_date_raw
        effective_date_value = latest_effective_date_raw

        for identity_element in identity_elements:
            is_main_identity = (identity_element.get("main") or "").strip().lower() in ("true", "1", "")
            for name_element in identity_element.findall("./name"):
                name_type_attr = (name_element.get("name-type") or "").strip()
                name_quality_attr = (name_element.get("quality") or "").strip() or None
                name_lang_attr = (name_element.get("lang") or "").strip() or None

                given_name_variants = []
                further_given_name_variants = []
                father_name_variants = []
                family_name_variants = []
                whole_name_variants = []
                name_parts_linear = []

                for name_part_element in name_element.findall("./name-part"):
                    name_part_type_attr = (name_part_element.get("name-part-type") or "").strip()
                    value_element = name_part_element.find("./value")
                    if value_element is not None:
                        spelling_elements = value_element.findall("./spelling-variant")
                        if spelling_elements:
                            for s_el in spelling_elements:
                                if s_el is not None and s_el.text and s_el.text.strip():
                                    text_variant_value = s_el.text.strip()
                                    name_parts_linear.append(text_variant_value)
                                    if first_spelling_variant_value is None:
                                        first_spelling_variant_value = text_variant_value
                                    if name_part_type_attr == "given-name":
                                        given_name_variants.append(text_variant_value)
                                    elif name_part_type_attr == "further-given-name":
                                        further_given_name_variants.append(text_variant_value)
                                    elif name_part_type_attr == "father-name":
                                        father_name_variants.append(text_variant_value)
                                    elif name_part_type_attr == "family-name":
                                        family_name_variants.append(text_variant_value)
                                    elif name_part_type_attr == "whole-name":
                                        whole_name_variants.append(text_variant_value)
                        else:
                            if value_element.text and value_element.text.strip():
                                value_text = value_element.text.strip()
                                name_parts_linear.append(value_text)
                                if first_spelling_variant_value is None:
                                    first_spelling_variant_value = value_text
                                if name_part_type_attr == "given-name":
                                    given_name_variants.append(value_text)
                                elif name_part_type_attr == "further-given-name":
                                    further_given_name_variants.append(value_text)
                                elif name_part_type_attr == "father-name":
                                    father_name_variants.append(value_text)
                                elif name_part_type_attr == "family-name":
                                    family_name_variants.append(value_text)
                                elif name_part_type_attr == "whole-name":
                                    whole_name_variants.append(value_text)

                joined_full_name = " ".join([p for p in name_parts_linear if p]) if name_parts_linear else None
                joined_whole = " ".join([p for p in whole_name_variants if p]) if whole_name_variants else None
                joined_given = " ".join([p for p in given_name_variants if p]) if given_name_variants else None
                joined_further = " ".join([p for p in further_given_name_variants if p]) if further_given_name_variants else None
                joined_father = " ".join([p for p in father_name_variants if p]) if father_name_variants else None
                joined_family = " ".join([p for p in family_name_variants if p]) if family_name_variants else None

                if name_type_attr == "primary-name" or is_main_identity:
                    if primary_name_value is None:
                        if joined_whole:
                            primary_name_value = joined_whole
                        elif joined_full_name:
                            primary_name_value = joined_full_name
                        else:
                            primary_name_value = None
                        first_name_value = first_name_value or joined_given
                        middle_candidate_values = []
                        if joined_further:
                            middle_candidate_values.append(joined_further)
                        if joined_father:
                            middle_candidate_values.append(joined_father)
                        if middle_candidate_values:
                            middle_name_value = middle_name_value or " ".join([m for m in middle_candidate_values if m])
                        last_name_value = last_name_value or joined_family
                        other_first_name_value = other_first_name_value or None
                        primary_name_language_value = name_lang_attr or primary_name_language_value
                        primary_name_quality_value = name_quality_attr or primary_name_quality_value
                        seco_primary_name_language_value = primary_name_language_value
                        seco_primary_name_quality_value = primary_name_quality_value
                else:
                    if joined_whole:
                        if joined_whole not in aliases_list:
                            aliases_list.append(joined_whole)
                    elif joined_full_name:
                        if joined_full_name not in aliases_list:
                            aliases_list.append(joined_full_name)

                if given_name_variants or further_given_name_variants or father_name_variants or family_name_variants:
                    combined_middle_variants = []
                    if further_given_name_variants and father_name_variants:
                        for a in further_given_name_variants:
                            for b in father_name_variants:
                                combined_value_mid = " ".join([x for x in [a, b] if x])
                                if combined_value_mid:
                                    combined_middle_variants.append(combined_value_mid)
                    for a in further_given_name_variants:
                        if a and a not in combined_middle_variants:
                            combined_middle_variants.append(a)
                    for b in father_name_variants:
                        if b and b not in combined_middle_variants:
                            combined_middle_variants.append(b)
                    if not combined_middle_variants:
                        combined_middle_variants.append("")

                    base_given_variants = given_name_variants if given_name_variants else [""]
                    base_family_variants = family_name_variants if family_name_variants else [""]

                    for g in base_given_variants:
                        for m in combined_middle_variants:
                            for f in base_family_variants:
                                parts_to_join = []
                                if g:
                                    parts_to_join.append(g)
                                if m:
                                    parts_to_join.append(m)
                                if f:
                                    parts_to_join.append(f)
                                assembled_alias_value = " ".join(parts_to_join).strip()
                                if assembled_alias_value:
                                    if primary_name_value is None or assembled_alias_value != primary_name_value:
                                        if assembled_alias_value not in aliases_list:
                                            aliases_list.append(assembled_alias_value)

            for nationality_element in identity_element.findall("./nationality"):
                country_element = nationality_element.find("./country")
                if country_element is not None:
                    nationality_country_value = nationality_country_value or ((country_element.text or "").strip() or None)
                    iso_attr = country_element.get("iso-code")
                    if iso_attr and not citizenship_country_iso_value:
                        citizenship_country_iso_value = iso_attr.strip().upper()
                    if nationality_country_value and not citizenship_country_value:
                        citizenship_country_value = nationality_country_value

            for date_element in identity_element.findall("./day-month-year"):
                day_attr = date_element.get("day")
                month_attr = date_element.get("month")
                year_attr = date_element.get("year")
                if year_attr and not birth_year_value:
                    birth_year_value = str(year_attr).strip()
                if month_attr and not birth_month_value:
                    birth_month_value = str(month_attr).strip()
                if day_attr and not birth_day_value:
                    birth_day_value = str(day_attr).strip()

            for pob_element in identity_element.findall("./place-of-birth"):
                place_id_attr = pob_element.get("place-id")
                if place_id_attr and place_id_attr in place_by_id:
                    place_info = place_by_id.get(place_id_attr) or {}
                    if (place_info.get("country") or None) and not address_country_value:
                        address_country_value = place_info.get("country")
                    if (place_info.get("country_iso") or None) and not address_country_iso_value:
                        address_country_iso_value = place_info.get("country_iso")
                    if place_of_birth_text_value is None:
                        pob_parts = []
                        if place_info.get("location"):
                            pob_parts.append(place_info.get("location"))
                        if place_info.get("area"):
                            pob_parts.append(place_info.get("area"))
                        if place_info.get("country"):
                            pob_parts.append(place_info.get("country"))
                        if pob_parts:
                            place_of_birth_text_value = ", ".join([p for p in pob_parts if p])

            for address_element in identity_element.findall("./address"):
                address_details_text = None
                p_o_box_text = None
                zip_code_text = None
                remark_text = None
                care_of_text = None
                place_id_attr = address_element.get("place-id")
                for a_child in list(address_element):
                    local_n = a_child.tag.split("}")[-1] if isinstance(a_child.tag, str) else a_child.tag
                    if local_n == "address-details" and a_child.text and a_child.text.strip():
                        address_details_text = a_child.text.strip()
                    elif local_n == "p-o-box" and a_child.text and a_child.text.strip():
                        p_o_box_text = a_child.text.strip()
                    elif local_n == "zip-code" and a_child.text and a_child.text.strip():
                        zip_code_text = a_child.text.strip()
                    elif local_n == "remark" and a_child.text and a_child.text.strip():
                        remark_text = a_child.text.strip()
                    elif local_n == "c-o" and a_child.text and a_child.text.strip():
                        care_of_text = a_child.text.strip()
                country_text_local = None
                country_iso_text_local = None
                location_text_local = None
                area_text_local = None
                if place_id_attr and place_id_attr in place_by_id:
                    place_info = place_by_id.get(place_id_attr) or {}
                    location_text_local = place_info.get("location")
                    area_text_local = place_info.get("area")
                    country_text_local = place_info.get("country")
                    country_iso_text_local = place_info.get("country_iso")
                formatted_address_value = None
                parts_for_primary_address = []
                if address_details_text:
                    parts_for_primary_address.append(address_details_text)
                if p_o_box_text:
                    parts_for_primary_address.append(p_o_box_text)
                if care_of_text:
                    parts_for_primary_address.append(care_of_text)
                if remark_text:
                    parts_for_primary_address.append(remark_text)
                if parts_for_primary_address:
                    formatted_address_value = ", ".join(parts_for_primary_address)
                if primary_address_value is None and formatted_address_value:
                    primary_address_value = formatted_address_value
                if address_city_value is None and location_text_local:
                    address_city_value = location_text_local
                if address_state_value is None and area_text_local:
                    address_state_value = area_text_local
                if address_postal_code_value is None and zip_code_text:
                    address_postal_code_value = zip_code_text
                if address_country_value is None and country_text_local:
                    address_country_value = country_text_local
                if address_country_iso_value is None and country_iso_text_local:
                    address_country_iso_value = country_iso_text_local
                alt_parts = []
                if formatted_address_value:
                    alt_parts.append(formatted_address_value)
                if location_text_local:
                    alt_parts.append(location_text_local)
                if area_text_local:
                    alt_parts.append(area_text_local)
                if country_text_local:
                    alt_parts.append(country_text_local)
                if zip_code_text:
                    alt_parts.append(zip_code_text)
                if alt_parts:
                    alternative_addresses_values.append(" | ".join([p for p in alt_parts if p]))

            for identification_document_element in identity_element.findall("./identification-document"):
                document_type_attr = (identification_document_element.get("document-type") or "").strip().lower()
                number_text = None
                issuer_text = None
                for x in list(identification_document_element):
                    xn = x.tag.split("}")[-1] if isinstance(x.tag, str) else x.tag
                    if xn == "number" and x.text and x.text.strip():
                        number_text = x.text.strip()
                    elif xn == "issuer" and x.text and x.text.strip():
                        issuer_text = x.text.strip()
                if number_text:
                    number_entry_text = number_text
                    if issuer_text:
                        number_entry_text = number_entry_text + " (" + issuer_text + ")"
                    if "passport" in document_type_attr:
                        passport_numbers_values.append(number_entry_text)
                    elif "id" in document_type_attr or "identity" in document_type_attr or "driving" in document_type_attr or "permit" in document_type_attr:
                        national_id_numbers_values.append(number_entry_text)
                    else:
                        other_id_numbers_values.append(number_entry_text)

            justification_elements = []
            other_info_elements = []
            parent_for_info = target_element
            if parent_for_info is not None:
                justification_elements = (parent_for_info.findall("./justification") or [])
                other_info_elements = (parent_for_info.findall("./other-information") or [])
            for j in justification_elements:
                if j.text and j.text.strip():
                    if justification_text_value is None:
                        justification_text_value = j.text.strip()
                    else:
                        justification_text_value = justification_text_value + " | " + j.text.strip()
        for o in other_info_elements:
                        if o.text and o.text.strip():
                            if other_information_text_value is None:
                                other_information_text_value = o.text.strip()
                            else:
                                other_information_text_value = other_information_text_value + " | " + o.text.strip()
                            tmp_text = o.text.strip()
                            for m in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", tmp_text):
                                if m not in contact_emails_values:
                                    contact_emails_values.append(m)
                            for m in re.findall(r"(?:https?://|www\.)[^\s;]+", tmp_text):
                                if m not in contact_websites_values:
                                    contact_websites_values.append(m)
                            for m in re.findall(r"(?:\+?\d[\d\-\s().]{6,}\d)", tmp_text):
                                v = m.strip()
                                if v not in contact_phone_numbers_values:
                                    contact_phone_numbers_values.append(v)

        for generic_attribute_element in target_element.findall("./generic-attribute"):
            generic_name_attr_original = (generic_attribute_element.get("name") or "").strip()
            generic_name_attr = generic_name_attr_original.lower()
            generic_text_value = (generic_attribute_element.text or "").strip()
            if not generic_text_value:
                continue
            if generic_name_attr in ("email", "e-mail", "mail", "email-address", "e_mail", "adresse e-mail", "e-mail adresse", "e-mail-adresse", "courriel", "posta elettronica", "mailadresse"):
                contact_emails_values.append(generic_text_value)
            elif generic_name_attr in ("phone", "telephone", "tel", "mobile", "mob", "phone-number", "phone no", "phone number", "cell", "cellphone", "cell phone", "gsm", "landline", "telephone", "tel", "telefon", "handy", "telefono", "cellulare"):
                contact_phone_numbers_values.append(generic_text_value)
            elif generic_name_attr in ("fax", "fax-number", "telefax", "telecopieur"):
                contact_fax_numbers_values.append(generic_text_value)
            elif generic_name_attr in ("url", "website", "web", "site", "homepage", "home-page", "site web", "site internet", "sito web", "sito internet", "internet", "www", "www-address", "website-address"):
                contact_websites_values.append(generic_text_value)
            elif generic_name_attr in ("bic", "swift"):
                bic_codes_values.append(generic_text_value)
            elif generic_name_attr in ("iban",):
                iban_numbers_values.append(generic_text_value)
            elif generic_name_attr in ("ssn", "social-security-number", "nin"):
                ssn_numbers_values.append(generic_text_value)
            elif generic_name_attr in ("tax-id", "tin", "tax-number"):
                tax_id_numbers_values.append(generic_text_value)
            else:
                value_lower = generic_text_value.lower()
                if ("fax" in generic_name_attr) or ("fax" in value_lower) or ("telecopieur" in generic_name_attr):
                    contact_fax_numbers_values.append(generic_text_value)
                elif ("phone" in generic_name_attr) or ("telephone" in generic_name_attr) or ("tel" in generic_name_attr) or ("mobile" in generic_name_attr) or ("cell" in generic_name_attr) or ("gsm" in generic_name_attr) or ("telephone" in generic_name_attr) or ("telefon" in generic_name_attr) or ("handy" in generic_name_attr):
                    contact_phone_numbers_values.append(generic_text_value)
                elif re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", generic_text_value):
                    contact_emails_values.append(generic_text_value)
                elif re.match(r"^(?:https?://|www\.)\S+$", generic_text_value):
                    contact_websites_values.append(generic_text_value)
                elif re.match(r"^\+?[0-9][0-9\s().\-]{5,}$", generic_text_value):
                    contact_phone_numbers_values.append(generic_text_value)
                else:
                    other_id_numbers_values.append(generic_text_value)

        if not primary_name_value:
            assembled = []
            if first_name_value:
                assembled.append(first_name_value)
            if middle_name_value:
                assembled.append(middle_name_value)
            if last_name_value:
                assembled.append(last_name_value)
            if assembled:
                primary_name_value = " ".join(assembled)

        sanctions_program_candidates = []
        for set_id in sanctions_set_ids:
            nm = program_name_by_set_id.get(set_id) or sanctions_set_name_by_id.get(set_id)
            if nm:
                sanctions_program_candidates.append(nm)
        if sanctions_program_candidates:
            sanctions_program_name_value = "; ".join([s for s in sanctions_program_candidates if s])

        classification_value = subject_type_value or None
        if classification_value == "Object":
            object_type_text = (seco_entity_type_value or "").strip().lower()
            if "vessel" in object_type_text or "ship" in object_type_text or "imo" in object_type_text:
                classification_value = "Vessel"
            elif "aircraft" in object_type_text or "plane" in object_type_text:
                classification_value = "Aircraft"
            else:
                classification_value = "Entity"

        record = {
            "list_name": list_name_value,
            "SECO_ssid": str(target_ssid_text),
            "SECO_entity_type": seco_entity_type_value,
            "primary_name": primary_name_value,
            "primary_name_language": seco_primary_name_language_value or primary_name_language_value,
            "primary_name_quality": seco_primary_name_quality_value or primary_name_quality_value,
            "first_spelling_variant_value": first_spelling_variant_value,
            "full_name": primary_name_value,
            "first_name": first_name_value,
            "middle_name": middle_name_value,
            "last_name": last_name_value,
            "other_first_name": other_first_name_value,
            "sex": subject_sex_value,
            "nationality": nationality_country_value,
            "citizenship_country": citizenship_country_value or nationality_country_value,
            "citizenship_country_iso": citizenship_country_iso_value,
            "primary_address_value": primary_address_value,
            "address_city": address_city_value,
            "address_state": address_state_value,
            "address_postal_code": address_postal_code_value,
            "address_country": address_country_value,
            "address_country_iso": address_country_iso_value,
            "alternative_addresses": alternative_addresses_values if alternative_addresses_values else None,
            "aliases": aliases_list if aliases_list else None,
            "justification_text": justification_text_value,
            "other_information_text": other_information_text_value,
            "sanctions_program_name": sanctions_program_name_value,
            "publication_date": publication_date_value,
            "enactment_date": enactment_date_value,
            "effective_date": effective_date_value,
            "email_address": contact_emails_values if contact_emails_values else None,
            "phone_numbers": contact_phone_numbers_values if contact_phone_numbers_values else None,
            "fax_numbers": contact_fax_numbers_values if contact_fax_numbers_values else None,
            "website": contact_websites_values if contact_websites_values else None,
            "bic": bic_codes_values if bic_codes_values else None,
            "iban_numbers": iban_numbers_values if iban_numbers_values else None,
            "ssn_numbers": ssn_numbers_values if ssn_numbers_values else None,
            "passport_numbers": passport_numbers_values if passport_numbers_values else None,
            "national_id_numbers": national_id_numbers_values if national_id_numbers_values else None,
            "tax_id_numbers": tax_id_numbers_values if tax_id_numbers_values else None,
            "other_id_numbers": other_id_numbers_values if other_id_numbers_values else None,
            "classification": classification_value,
            "global_id": "SECO-" + str(target_ssid_text),
            "place_of_birth_text": place_of_birth_text_value
        }
        records.append(record)

    return records
