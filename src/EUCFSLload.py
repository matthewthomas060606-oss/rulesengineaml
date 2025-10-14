import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timezone
from countrycode import country_to_iso2
from pathlib import Path
import logging
from config import get_config
cfg = get_config()

EU_URL = "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=n009sfr8"
EU_XML = "EU.26.10.25.xml"

def EU_fetch():
    try:
        resp = requests.get(EU_URL, timeout=120)
        resp.raise_for_status()
        xml_bytes = resp.content
        if not xml_bytes:
            raise ValueError("empty body")
        log_path = cfg.paths.DATA_DIR / "EUlog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat() + "\n")
        return ET.fromstring(xml_bytes)
    except Exception as e:
        local = Path(__file__).parent.parent / "data" / EU_XML
        if local.exists():
            logging.error("EU download failed; using backup file %s", local, exc_info=True)
            return ET.parse(str(local)).getroot()
        raise RuntimeError(f"EU download failed and no backup found at {local}: {e}")


def EU_extract(xml_root):
    records = []
    namespace_agnostic = True
    for sanction_entity_element in xml_root.iter():
        tag_value = sanction_entity_element.tag
        local_tag_name = tag_value.split("}")[-1].lower() if isinstance(tag_value, str) else ""
        if local_tag_name != "sanctionentity":
            continue
        list_name_value = "EU"
        eu_reference_number_value = (sanction_entity_element.get("euReferenceNumber") or "").strip()
        logical_identifier_value = (sanction_entity_element.get("logicalId") or "").strip()
        list_identifier_value = eu_reference_number_value or logical_identifier_value
        if not list_identifier_value:
            continue

        primary_name_value = None
        primary_name_language_value = None
        primary_name_quality_value = None
        first_spelling_variant_value = None
        full_name_value = None
        first_name_value = None
        middle_name_value = None
        last_name_value = None
        other_first_name_value = None
        sex_value = None
        nationality_value = None
        citizenship_country_value = None
        citizenship_country_iso_value = None
        address_country_value = None
        address_country_iso_value = None
        address_city_value = None
        address_state_value = None
        address_postal_code_value = None
        address_area_value = None
        address_location_value = None
        address_details_value = None
        primary_address_value_value = None
        place_of_birth_text_value = None
        birth_year_value = None
        birth_month_value = None
        birth_day_value = None
        justification_text_value = None
        other_information_text_parts = []
        sanctions_program_name_value = None
        publication_date_value = None
        enactment_date_value = None
        effective_date_value = None
        email_address_value = None
        website_value = None
        phone_number_value = None
        passport_details_value = None
        national_identifier_details_value = None
        business_registration_number_value = None
        original_script_name_value = None
        vessel_flag_value = None
        vessel_imo_value = None
        aliases_list = []
        alternative_addresses_list = []

        for child in sanction_entity_element:
            child_tag_name = child.tag.split("}")[-1].lower() if isinstance(child.tag, str) else ""
            if child_tag_name == "remark":
                text_value = (child.text or "").strip()
                if text_value:
                    if justification_text_value is None:
                        justification_text_value = text_value
                    else:
                        other_information_text_parts.append(text_value)
            elif child_tag_name == "regulation":
                regulation_type_value = (child.get("regulationType") or "").strip()
                organisation_type_value = (child.get("organisationType") or "").strip()
                publication_date_attr_value = (child.get("publicationDate") or "").strip()
                entry_into_force_date_attr_value = (child.get("entryIntoForceDate") or "").strip()
                number_title_value = (child.get("numberTitle") or "").strip()
                programme_value = (child.get("programme") or "").strip()
                logical_id_regulation_value = (child.get("logicalId") or "").strip()
                if programme_value:
                    sanctions_program_name_value = programme_value
                if publication_date_attr_value:
                    publication_date_value = publication_date_attr_value
                if entry_into_force_date_attr_value:
                    enactment_date_value = entry_into_force_date_attr_value
                    if effective_date_value in (None, ""):
                        effective_date_value = entry_into_force_date_attr_value
                publication_url_value = None
                for reg_child in child:
                    reg_child_tag_name = reg_child.tag.split("}")[-1].lower() if isinstance(reg_child.tag, str) else ""
                    if reg_child_tag_name == "publicationurl":
                        publication_url_value = (reg_child.text or "").strip()
                assembled_regulation_info = []
                if regulation_type_value:
                    assembled_regulation_info.append("regulationType=" + regulation_type_value)
                if organisation_type_value:
                    assembled_regulation_info.append("organisationType=" + organisation_type_value)
                if number_title_value:
                    assembled_regulation_info.append("numberTitle=" + number_title_value)
                if logical_id_regulation_value:
                    assembled_regulation_info.append("regulationId=" + logical_id_regulation_value)
                if publication_url_value:
                    assembled_regulation_info.append("publicationUrl=" + publication_url_value)
                if assembled_regulation_info:
                    other_information_text_parts.append("; ".join(assembled_regulation_info))
            elif child_tag_name == "subjecttype":
                subject_type_code_value = (child.get("code") or "").strip()
                classification_code_value = (child.get("classificationCode") or "").strip()
                if subject_type_code_value:
                    other_information_text_parts.append("subjectType=" + subject_type_code_value)
                if classification_code_value:
                    other_information_text_parts.append("classificationCode=" + classification_code_value)
            elif child_tag_name == "namealias":
                gender_attr_value = (child.get("gender") or "").strip()
                if gender_attr_value:
                    sex_value = gender_attr_value
                name_language_attr_value = (child.get("nameLanguage") or "").strip()
                if name_language_attr_value:
                    primary_name_language_value = name_language_attr_value
                regulation_language_attr_value = (child.get("regulationLanguage") or "").strip()
                strong_attr_value = (child.get("strong") or "").strip().lower()
                is_strong_value = strong_attr_value in ("true", "1", "yes", "y")
                title_attr_value = (child.get("title") or "").strip()
                function_attr_value = (child.get("function") or "").strip()
                first_attr_value = (child.get("firstName") or "").strip()
                middle_attr_value = (child.get("middleName") or "").strip()
                last_attr_value = (child.get("lastName") or "").strip()
                whole_name_attr_value = (child.get("wholeName") or "").strip()
                assembled_alias_value = None
                if whole_name_attr_value:
                    assembled_alias_value = whole_name_attr_value
                else:
                    name_parts_for_alias = []
                    if first_attr_value:
                        name_parts_for_alias.append(first_attr_value)
                    if middle_attr_value:
                        name_parts_for_alias.append(middle_attr_value)
                    if last_attr_value:
                        name_parts_for_alias.append(last_attr_value)
                    if name_parts_for_alias:
                        assembled_alias_value = " ".join(name_parts_for_alias)
                if assembled_alias_value:
                    if primary_name_value is None and is_strong_value:
                        primary_name_value = assembled_alias_value
                        primary_name_quality_value = "strong"
                    aliases_list.append(assembled_alias_value)
                if first_attr_value and first_name_value is None:
                    first_name_value = first_attr_value
                if middle_attr_value and middle_name_value is None:
                    middle_name_value = middle_attr_value
                if last_attr_value and last_name_value is None:
                    last_name_value = last_attr_value
                for regsum in child:
                    regsum_tag_name = regsum.tag.split("}")[-1].lower() if isinstance(regsum.tag, str) else ""
                    if regsum_tag_name == "regulationsummary":
                        regsum_publication_date_value = (regsum.get("publicationDate") or "").strip()
                        regsum_number_title_value = (regsum.get("numberTitle") or "").strip()
                        regsum_publication_url_value = (regsum.get("publicationUrl") or "").strip()
                        if regsum_publication_date_value and publication_date_value in (None, ""):
                            publication_date_value = regsum_publication_date_value
                        assembled_rs = []
                        if regsum_number_title_value:
                            assembled_rs.append("nameAliasReg=" + regsum_number_title_value)
                        if regsum_publication_url_value:
                            assembled_rs.append("nameAliasUrl=" + regsum_publication_url_value)
                        if regulation_language_attr_value:
                            assembled_rs.append("nameAliasRegLang=" + regulation_language_attr_value)
                        if title_attr_value:
                            assembled_rs.append("title=" + title_attr_value)
                        if function_attr_value:
                            assembled_rs.append("function=" + function_attr_value)
                        if assembled_rs:
                            other_information_text_parts.append("; ".join(assembled_rs))
            elif child_tag_name == "citizenship":
                citizenship_country_iso_attr_value = (child.get("countryIso2Code") or "").strip()
                citizenship_country_desc_attr_value = (child.get("countryDescription") or "").strip()
                region_attr_value = (child.get("region") or "").strip()
                if citizenship_country_desc_attr_value and citizenship_country_value in (None, ""):
                    citizenship_country_value = citizenship_country_desc_attr_value
                if citizenship_country_iso_attr_value and citizenship_country_iso_value in (None, ""):
                    citizenship_country_iso_value = citizenship_country_iso_attr_value
                if nationality_value in (None, "") and citizenship_country_desc_attr_value:
                    nationality_value = citizenship_country_desc_attr_value
                if region_attr_value:
                    other_information_text_parts.append("citizenshipRegion=" + region_attr_value)
                for regsum in child:
                    regsum_tag_name = regsum.tag.split("}")[-1].lower() if isinstance(regsum.tag, str) else ""
                    if regsum_tag_name == "regulationsummary":
                        vpub = (regsum.get("publicationDate") or "").strip()
                        vtitle = (regsum.get("numberTitle") or "").strip()
                        vurl = (regsum.get("publicationUrl") or "").strip()
                        assembled_rs = []
                        if vpub:
                            assembled_rs.append("citizenshipPubDate=" + vpub)
                        if vtitle:
                            assembled_rs.append("citizenshipReg=" + vtitle)
                        if vurl:
                            assembled_rs.append("citizenshipUrl=" + vurl)
                        if assembled_rs:
                            other_information_text_parts.append("; ".join(assembled_rs))
            elif child_tag_name == "birthdate":
                circa_attr_value = (child.get("circa") or "").strip()
                calendar_type_attr_value = (child.get("calendarType") or "").strip()
                city_attr_value = (child.get("city") or "").strip()
                region_attr_value = (child.get("region") or "").strip()
                place_attr_value = (child.get("place") or "").strip()
                zip_code_attr_value = (child.get("zipCode") or "").strip()
                country_iso_attr_value = (child.get("countryIso2Code") or "").strip()
                country_desc_attr_value = (child.get("countryDescription") or "").strip()
                birthdate_attr_value = (child.get("birthdate") or "").strip()
                day_of_month_attr_value = (child.get("dayOfMonth") or "").strip()
                month_of_year_attr_value = (child.get("monthOfYear") or "").strip()
                year_attr_value = (child.get("year") or "").strip()
                if year_attr_value and birth_year_value in (None, ""):
                    birth_year_value = year_attr_value
                if month_of_year_attr_value and birth_month_value in (None, ""):
                    birth_month_value = month_of_year_attr_value.zfill(2) if month_of_year_attr_value.isdigit() else month_of_year_attr_value
                if day_of_month_attr_value and birth_day_value in (None, ""):
                    birth_day_value = day_of_month_attr_value.zfill(2) if day_of_month_attr_value.isdigit() else day_of_month_attr_value
                if birthdate_attr_value and len(birthdate_attr_value) >= 4 and birth_year_value in (None, ""):
                    birth_year_value = birthdate_attr_value[0:4]
                    if len(birthdate_attr_value) >= 7 and birthdate_attr_value[4] == "-" and birthdate_attr_value[5:7].isdigit():
                        birth_month_value = birthdate_attr_value[5:7]
                        if len(birthdate_attr_value) >= 10 and birthdate_attr_value[7] == "-" and birthdate_attr_value[8:10].isdigit():
                            birth_day_value = birthdate_attr_value[8:10]
                if city_attr_value and address_location_value in (None, ""):
                    address_location_value = city_attr_value
                if region_attr_value and address_area_value in (None, ""):
                    address_area_value = region_attr_value
                if place_attr_value and address_state_value in (None, ""):
                    address_state_value = place_attr_value
                if zip_code_attr_value and address_postal_code_value in (None, ""):
                    address_postal_code_value = zip_code_attr_value
                if country_desc_attr_value and address_country_value in (None, ""):
                    address_country_value = country_desc_attr_value
                if country_iso_attr_value and address_country_iso_value in (None, ""):
                    address_country_iso_value = country_iso_attr_value
                text_birth_parts = []
                if city_attr_value:
                    text_birth_parts.append(city_attr_value)
                if region_attr_value:
                    text_birth_parts.append(region_attr_value)
                if place_attr_value:
                    text_birth_parts.append(place_attr_value)
                if country_desc_attr_value:
                    text_birth_parts.append(country_desc_attr_value)
                if text_birth_parts and place_of_birth_text_value in (None, ""):
                    place_of_birth_text_value = ", ".join(text_birth_parts)
                assembled_bd = []
                if circa_attr_value:
                    assembled_bd.append("circa=" + circa_attr_value)
                if calendar_type_attr_value:
                    assembled_bd.append("calendarType=" + calendar_type_attr_value)
                if assembled_bd:
                    other_information_text_parts.append("; ".join(assembled_bd))
                for regsum in child:
                    regsum_tag_name = regsum.tag.split("}")[-1].lower() if isinstance(regsum.tag, str) else ""
                    if regsum_tag_name == "regulationsummary":
                        vpub = (regsum.get("publicationDate") or "").strip()
                        vtitle = (regsum.get("numberTitle") or "").strip()
                        vurl = (regsum.get("publicationUrl") or "").strip()
                        assembled_rs = []
                        if vpub:
                            assembled_rs.append("birthPubDate=" + vpub)
                        if vtitle:
                            assembled_rs.append("birthReg=" + vtitle)
                        if vurl:
                            assembled_rs.append("birthUrl=" + vurl)
                        if assembled_rs:
                            other_information_text_parts.append("; ".join(assembled_rs))
            elif child_tag_name == "address":
                city_attr_value = (child.get("city") or "").strip()
                street_attr_value = (child.get("street") or "").strip()
                po_box_attr_value = (child.get("poBox") or "").strip()
                zip_code_attr_value = (child.get("zipCode") or "").strip()
                region_attr_value = (child.get("region") or "").strip()
                place_attr_value = (child.get("place") or "").strip()
                country_iso_attr_value = (child.get("countryIso2Code") or "").strip()
                country_desc_attr_value = (child.get("countryDescription") or "").strip()
                assembled_details_parts = []
                if street_attr_value:
                    assembled_details_parts.append(street_attr_value)
                if po_box_attr_value:
                    assembled_details_parts.append("PO Box " + po_box_attr_value)
                if assembled_details_parts:
                    address_details_value = ", ".join(assembled_details_parts)
                if city_attr_value:
                    address_city_value = city_attr_value
                    if address_location_value in (None, ""):
                        address_location_value = city_attr_value
                if zip_code_attr_value:
                    address_postal_code_value = zip_code_attr_value
                if region_attr_value and address_area_value in (None, ""):
                    address_area_value = region_attr_value
                if place_attr_value and address_state_value in (None, ""):
                    address_state_value = place_attr_value
                if country_desc_attr_value and address_country_value in (None, ""):
                    address_country_value = country_desc_attr_value
                if country_iso_attr_value and address_country_iso_value in (None, ""):
                    address_country_iso_value = country_iso_attr_value
                assembled_full_address = []
                if street_attr_value:
                    assembled_full_address.append(street_attr_value)
                if city_attr_value:
                    assembled_full_address.append(city_attr_value)
                if region_attr_value:
                    assembled_full_address.append(region_attr_value)
                if place_attr_value:
                    assembled_full_address.append(place_attr_value)
                if zip_code_attr_value:
                    assembled_full_address.append(zip_code_attr_value)
                if country_desc_attr_value:
                    assembled_full_address.append(country_desc_attr_value)
                if assembled_full_address and primary_address_value_value in (None, ""):
                    primary_address_value_value = ", ".join(assembled_full_address)
                all_addr_text = ", ".join([x for x in assembled_full_address if x])
                if all_addr_text:
                    alternative_addresses_list.append(all_addr_text)
            elif child_tag_name == "identification":
                for id_child in child:
                    id_child_tag_name = id_child.tag.split("}")[-1].lower() if isinstance(id_child.tag, str) else ""
                    if id_child_tag_name == "documentation":
                        doc_type_value = (id_child.get("type") or "").strip()
                        doc_number_value = (id_child.get("number") or "").strip()
                        doc_country_iso_value = (id_child.get("countryIso2Code") or "").strip()
                        doc_country_desc_value = (id_child.get("countryDescription") or "").strip()
                        note_text_value = (id_child.get("comment") or "").strip()
                        assembled_doc_parts = []
                        if doc_type_value:
                            assembled_doc_parts.append("type=" + doc_type_value)
                        if doc_number_value:
                            assembled_doc_parts.append("number=" + doc_number_value)
                        if doc_country_desc_value:
                            assembled_doc_parts.append("country=" + doc_country_desc_value)
                        if doc_country_iso_value:
                            assembled_doc_parts.append("iso2=" + doc_country_iso_value)
                        if note_text_value:
                            assembled_doc_parts.append("note=" + note_text_value)
                        if assembled_doc_parts:
                            other_information_text_parts.append("document: " + "; ".join(assembled_doc_parts))
                        if doc_type_value.lower() == "passport" and doc_number_value:
                            passport_details_value = doc_number_value
                        if doc_type_value.lower() in ("national id", "national identification", "id card") and doc_number_value:
                            national_identifier_details_value = doc_number_value
            elif child_tag_name == "contactinfo":
                for contact_child in child:
                    contact_child_tag_name = contact_child.tag.split("}")[-1].lower() if isinstance(contact_child.tag, str) else ""
                    if contact_child_tag_name == "email":
                        email_text_value = (contact_child.text or "").strip()
                        if email_text_value:
                            email_address_value = email_text_value
                    elif contact_child_tag_name == "website":
                        website_text_value = (contact_child.text or "").strip()
                        if website_text_value:
                            website_value = website_text_value
                    elif contact_child_tag_name == "phone":
                        phone_text_value = (contact_child.text or "").strip()
                        if phone_text_value:
                            phone_number_value = phone_text_value

        if primary_name_value:
            full_name_value = primary_name_value
        else:
            if full_name_value in (None, ""):
                candidate_name_parts = []
                if first_name_value:
                    candidate_name_parts.append(first_name_value)
                if middle_name_value:
                    candidate_name_parts.append(middle_name_value)
                if last_name_value:
                    candidate_name_parts.append(last_name_value)
                if candidate_name_parts:
                    full_name_value = " ".join(candidate_name_parts)

        record = {}
        record["list_name"] = list_name_value
        record["list_id"] = logical_identifier_value
        record["primary_name"] = primary_name_value or full_name_value
        record["primary_name_language"] = primary_name_language_value
        record["primary_name_quality"] = primary_name_quality_value
        record["first_spelling_variant_value"] = first_spelling_variant_value
        record["full_name"] = full_name_value
        record["first_name"] = first_name_value
        record["middle_name"] = middle_name_value
        record["last_name"] = last_name_value
        record["other_first_name"] = other_first_name_value
        record["sex"] = sex_value
        record["nationality"] = nationality_value
        record["citizenship_country"] = citizenship_country_value
        record["citizenship_country_iso"] = citizenship_country_iso_value
        record["place_of_birth_text"] = place_of_birth_text_value
        record["birth_year"] = birth_year_value
        record["birth_month"] = birth_month_value
        record["birth_day"] = birth_day_value
        record["primary_address_value"] = primary_address_value_value
        record["address_country"] = address_country_value
        record["address_country_iso"] = address_country_iso_value
        record["address_location"] = address_location_value
        record["address_area"] = address_area_value
        record["address_city"] = address_city_value
        record["address_state"] = address_state_value
        record["address_postal_code"] = address_postal_code_value
        record["address_details"] = address_details_value
        record["justification_text"] = justification_text_value
        record["other_information_text"] = "; ".join([t for t in other_information_text_parts if t]) if other_information_text_parts else None
        record["sanctions_program_name"] = sanctions_program_name_value
        record["publication_date"] = publication_date_value
        record["enactment_date"] = enactment_date_value
        record["effective_date"] = effective_date_value
        record["email_address"] = email_address_value
        record["website"] = website_value
        record["phone_number"] = phone_number_value
        record["passport_details"] = passport_details_value
        record["national_identification_details"] = national_identifier_details_value
        record["business_registration_number"] = business_registration_number_value
        record["original_script_name"] = original_script_name_value
        record["vessel_flag"] = vessel_flag_value
        record["vessel_imo"] = vessel_imo_value
        record["aliases"] = aliases_list
        record["EU_all_addresses"] = alternative_addresses_list

        records.append(record)
    return records
