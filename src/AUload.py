import io, re
from pathlib import Path
import pandas as pd
import requests
from datetime import datetime, timezone
import openpyxl
from countrycode import country_to_iso2
import logging
from config import get_config
cfg = get_config()

AU_URL = "https://www.dfat.gov.au/sites/default/files/regulation8_consolidated.xlsx"
AU_XML = "AU.1.10.25.xlsx"

def AU_fetch():
    try:
        resp = requests.get(AU_URL, timeout=120)
        resp.raise_for_status()
        data = resp.content
        if not data:
            raise ValueError("empty body")
        log_path = cfg.paths.DATA_DIR / "AUlog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat() + "\n")
        return pd.read_excel(io.BytesIO(data), sheet_name=0)
    except Exception as e:
        local = Path(__file__).parent.parent / "data" / AU_XML
        if local.exists():
            logging.error("AU download failed; using backup file %s", local, exc_info=True)
            return pd.read_excel(local, sheet_name=0)
        raise RuntimeError(f"AU download failed and no backup found at {local}: {e}")

def AU_extract(excel_table_object):
    if not isinstance(excel_table_object, pd.DataFrame):
        return []

    def _dedup_keep_order(seq):
        seen = set()
        out = []
        for s in seq:
            if s is None:
                continue
            t = str(s).strip()
            if not t:
                continue
            k = t.lower()
            if k not in seen:
                seen.add(k)
                out.append(t)
        return out

    df = excel_table_object.copy()
    df.columns = [str(c).strip() for c in df.columns]

    possible_name_cols = ["Name", "Primary Name", "Full Name"]
    possible_classification_cols = ["Type", "Entity Type", "Individual/Entity", "IndividualEntityShip"]
    possible_alias_cols = ["Aliases", "Also Known As", "A.K.A.", "AKA", "Alternative Names"]
    possible_dob_cols = ["Date of Birth", "DOB", "Dates of Birth"]
    possible_pob_cols = ["Place of Birth", "POB", "Birth Place", "Town of Birth", "City of Birth", "Country of Birth"]
    possible_nationality_cols = ["Nationality", "Nationalities"]
    possible_citizenship_cols = ["Citizenship", "Citizenships"]
    possible_address_cols = ["Address", "Address Line 1", "Address Line 2", "Address Line 3", "Address Line 4", "Address Line 5", "Address Line 6", "City", "Town", "State/Province", "Province/State", "Postcode", "Postal Code", "Zip", "Country"]
    possible_program_cols = ["Regime", "Sanctions Regime", "Program", "Programme", "Regime Name"]
    possible_reason_cols = ["Reason", "Statement of Reasons", "UK Statement of Reasons", "Other Information", "Remarks"]
    possible_pub_cols = ["Last Updated", "Publication Date", "Updated", "Listed Date", "Date Listed", "Date Designated"]
    possible_effective_cols = ["Effective Date", "Start Date", "Date Designated"]
    possible_enact_cols = ["Enactment Date", "Date Designated", "Start Date"]
    possible_group_id_cols = ["Group ID", "OFSI Group ID", "GroupID"]
    possible_un_ref_cols = ["UN Reference", "UN Reference Number", "UN Ref", "UNReferenceNumber"]
    possible_email_cols = ["Email", "Email Address", "Emails"]
    possible_phone_cols = ["Phone", "Telephone", "Phone Number", "Phone Numbers", "Telephone Number"]
    possible_website_cols = ["Website", "Web", "URL"]
    possible_passport_cols = ["Passport", "Passport Number", "Passports"]
    possible_national_id_cols = ["National ID", "National Identifier", "National Identity Number", "National ID Number"]
    possible_tax_id_cols = ["Tax ID", "TIN", "Tax Identification Number"]
    possible_other_id_cols = ["Other ID", "Other Identifiers"]

    records = []

    for idx, row in df.iterrows():
        row_dict = {k: (None if pd.isna(v) else str(v).strip()) for k, v in row.items()}

        def first_nonempty(keys):
            for k in keys:
                if k in row_dict and row_dict[k]:
                    return row_dict[k]
            return None

        list_name_value = "AU"
        list_identifier_value = None
        for k in ("Unique ID", "UniqueID", "AU ID", "ID", "List ID"):
            if k in row_dict and row_dict[k]:
                list_identifier_value = row_dict[k]
                break
        if not list_identifier_value:
            list_identifier_value = f"AU-{idx+1}"

        full_name_value = first_nonempty(possible_name_cols)
        classification_value = first_nonempty(possible_classification_cols)

        aliases_raw = first_nonempty(possible_alias_cols)
        aliases_list = []
        if aliases_raw:
            split_candidates = []
            if ";" in aliases_raw:
                split_candidates = [x for x in aliases_raw.split(";")]
            elif "|" in aliases_raw:
                split_candidates = [x for x in aliases_raw.split("|")]
            elif "," in aliases_raw:
                split_candidates = [x for x in aliases_raw.split(",")]
            else:
                split_candidates = [aliases_raw]
            aliases_list = _dedup_keep_order(split_candidates)

        dob_text_value = first_nonempty(possible_dob_cols)
        birth_year_value = None
        birth_month_value = None
        birth_day_value = None
        if dob_text_value:
            t = dob_text_value.replace("\\", "/").replace("-", "/").replace(".", "/")
            parts = [p for p in t.split("/") if p.strip()]
            if len(parts) == 3:
                a, b, c = parts
                if len(c) == 4:
                    try:
                        birth_day_value = int(a)
                        birth_month_value = int(b)
                        birth_year_value = int(c)
                    except Exception:
                        birth_year_value = None
                        birth_month_value = None
                        birth_day_value = None

        place_of_birth_text_value = first_nonempty(possible_pob_cols)

        nationality_value = first_nonempty(possible_nationality_cols)
        citizenship_country_value = first_nonempty(possible_citizenship_cols)
        citizenship_country_iso_value = None

        address_lines_collected = []
        address_city_value = None
        address_state_value = None
        address_postal_code_value = None
        address_country_value = None

        for k in possible_address_cols:
            if k in row_dict and row_dict[k]:
                val = row_dict[k]
                if k in ("Address", "Address Line 1", "Address Line 2", "Address Line 3", "Address Line 4", "Address Line 5", "Address Line 6"):
                    address_lines_collected.append(val)
                elif k in ("City", "Town"):
                    if address_city_value is None:
                        address_city_value = val
                elif k in ("State/Province", "Province/State"):
                    if address_state_value is None:
                        address_state_value = val
                elif k in ("Postcode", "Postal Code", "Zip"):
                    if address_postal_code_value is None:
                        address_postal_code_value = val
                elif k == "Country":
                    if address_country_value is None:
                        address_country_value = val

        parts_for_primary = []
        for p in address_lines_collected:
            if p:
                parts_for_primary.append(p)
        if address_city_value:
            parts_for_primary.append(address_city_value)
        if address_state_value:
            parts_for_primary.append(address_state_value)
        if address_postal_code_value:
            parts_for_primary.append(address_postal_code_value)
        if address_country_value:
            parts_for_primary.append(address_country_value)
        primary_address_value_value = " | ".join([x for x in parts_for_primary if x]) if parts_for_primary else None

        alternative_addresses_value_list = []
        if primary_address_value_value:
            alternative_addresses_value_list.append(primary_address_value_value)

        address_country_iso_value = None
        address_location_value = None
        address_area_value = None
        address_details_value = " || ".join(_dedup_keep_order(alternative_addresses_value_list)) if alternative_addresses_value_list else None

        sanctions_program_name_value = first_nonempty(possible_program_cols)
        justification_text_value = first_nonempty(possible_reason_cols)

        publication_date_value = first_nonempty(possible_pub_cols)
        enactment_date_value = first_nonempty(possible_enact_cols) or publication_date_value
        effective_date_value = first_nonempty(possible_effective_cols) or enactment_date_value

        ofsi_group_id_text_value = first_nonempty(possible_group_id_cols)
        un_reference_number_text_value = first_nonempty(possible_un_ref_cols)

        contact_emails_list_value = []
        emails_val = first_nonempty(possible_email_cols)
        if emails_val:
            if ";" in emails_val:
                contact_emails_list_value = _dedup_keep_order([x for x in emails_val.split(";")])
            elif "|" in emails_val:
                contact_emails_list_value = _dedup_keep_order([x for x in emails_val.split("|")])
            elif "," in emails_val:
                contact_emails_list_value = _dedup_keep_order([x for x in emails_val.split(",")])
            else:
                contact_emails_list_value = _dedup_keep_order([emails_val])

        contact_phone_numbers_list_value = []
        phones_val = first_nonempty(possible_phone_cols)
        if phones_val:
            if ";" in phones_val:
                contact_phone_numbers_list_value = _dedup_keep_order([x for x in phones_val.split(";")])
            elif "|" in phones_val:
                contact_phone_numbers_list_value = _dedup_keep_order([x for x in phones_val.split("|")])
            elif "," in phones_val:
                contact_phone_numbers_list_value = _dedup_keep_order([x for x in phones_val.split(",")])
            else:
                contact_phone_numbers_list_value = _dedup_keep_order([phones_val])

        website_value = first_nonempty(possible_website_cols)

        passport_numbers = []
        pv = first_nonempty(possible_passport_cols)
        if pv:
            if ";" in pv:
                passport_numbers = _dedup_keep_order([x for x in pv.split(";")])
            elif "|" in pv:
                passport_numbers = _dedup_keep_order([x for x in pv.split("|")])
            elif "," in pv:
                passport_numbers = _dedup_keep_order([x for x in pv.split(",")])
            else:
                passport_numbers = _dedup_keep_order([pv])

        national_id_numbers = []
        nv = first_nonempty(possible_national_id_cols)
        if nv:
            if ";" in nv:
                national_id_numbers = _dedup_keep_order([x for x in nv.split(";")])
            elif "|" in nv:
                national_id_numbers = _dedup_keep_order([x for x in nv.split("|")])
            elif "," in nv:
                national_id_numbers = _dedup_keep_order([x for x in nv.split(",")])
            else:
                national_id_numbers = _dedup_keep_order([nv])

        tax_id_numbers = []
        tv = first_nonempty(possible_tax_id_cols)
        if tv:
            if ";" in tv:
                tax_id_numbers = _dedup_keep_order([x for x in tv.split(";")])
            elif "|" in tv:
                tax_id_numbers = _dedup_keep_order([x for x in tv.split("|")])
            elif "," in tv:
                tax_id_numbers = _dedup_keep_order([x for x in tv.split(",")])
            else:
                tax_id_numbers = _dedup_keep_order([tv])

        other_id_numbers = []
        ov = first_nonempty(possible_other_id_cols)
        if ov:
            if ";" in ov:
                other_id_numbers = _dedup_keep_order([x for x in ov.split(";")])
            elif "|" in ov:
                other_id_numbers = _dedup_keep_order([x for x in ov.split("|")])
            elif "," in ov:
                other_id_numbers = _dedup_keep_order([x for x in ov.split(",")])
            else:
                other_id_numbers = _dedup_keep_order([ov])

        other_information_parts = []
        if ofsi_group_id_text_value:
            other_information_parts.append("GroupID: " + ofsi_group_id_text_value)
        if un_reference_number_text_value:
            other_information_parts.append("UNReferenceNumber: " + un_reference_number_text_value)
        if website_value:
            other_information_parts.append("Website: " + website_value)

        consumed_keys = set()
        for group in (
            possible_name_cols, possible_classification_cols, possible_alias_cols, possible_dob_cols,
            possible_pob_cols, possible_nationality_cols, possible_citizenship_cols, possible_address_cols,
            possible_program_cols, possible_reason_cols, possible_pub_cols, possible_effective_cols,
            possible_enact_cols, possible_group_id_cols, possible_un_ref_cols, possible_email_cols,
            possible_phone_cols, possible_website_cols, possible_passport_cols, possible_national_id_cols,
            possible_tax_id_cols, possible_other_id_cols, ("Unique ID","UniqueID","AU ID","ID","List ID")
        ):
            for k in group:
                consumed_keys.add(k)

        for k, v in row_dict.items():
            if v and k not in consumed_keys:
                other_information_parts.append(f"{k}: {v}")

        justification_text_value_final = justification_text_value
        if place_of_birth_text_value and not justification_text_value_final:
            justification_text_value_final = "Place of birth: " + place_of_birth_text_value

        record_map = {
            "list_name": list_name_value,
            "list_id": list_identifier_value,
            "classification": classification_value,
            "full_name": full_name_value,
            "first_name": None,
            "middle_name": None,
            "last_name": None,
            "other_first_name": None,
            "sex": None,
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
            "address_location": None,
            "address_area": address_area_value,
            "address_city": address_city_value,
            "address_state": address_state_value,
            "address_postal_code": address_postal_code_value,
            "address_details": address_details_value,
            "justification_text": justification_text_value_final,
            "other_information_text": ("; ".join([p for p in other_information_parts if p]) if other_information_parts else None),
            "sanctions_program_name": sanctions_program_name_value,
            "publication_date": publication_date_value,
            "enactment_date": enactment_date_value,
            "effective_date": effective_date_value,
            "aliases": _dedup_keep_order(aliases_list),
            "email_addresses": _dedup_keep_order(contact_emails_list_value),
            "phone_numbers": _dedup_keep_order(contact_phone_numbers_list_value),
            "all_addresses": _dedup_keep_order(alternative_addresses_value_list),
            "alternative_cities": _dedup_keep_order([address_city_value] if address_city_value else []),
            "alternative_states": _dedup_keep_order([address_state_value] if address_state_value else []),
            "alternative_postal_codes": _dedup_keep_order([address_postal_code_value] if address_postal_code_value else []),
            "alternative_countries": _dedup_keep_order([address_country_value] if address_country_value else []),
            "alternative_country_isos": []
        }

        records.append(record_map)

    return records
