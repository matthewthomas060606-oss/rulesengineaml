import sqlite3
from pathlib import Path
import json
import re
import os
import unicodedata
from countrycode import country_to_iso2

def normalize_sanctions_record(rec):
    def first(keys):
        for k in keys:
            v = rec.get(k)
            if v not in (None, ""):
                return v
        return None
    def clean_text(v):
        if v in (None, ""):
            return None
        if not isinstance(v, str):
            v = str(v)
        v = unicodedata.normalize("NFKC", v)
        v = v.replace("\u00A0", " ")
        v = re.sub(r"\s+", " ", v).strip()
        return v if v else None
    def clean_upper(v):
        t = clean_text(v)
        return t.upper() if t else None
    def iso2(v):
        t = clean_text(v)
        if not t:
            return None
        if len(t) == 2 and t.isalpha():
            return t.upper()
        try:
            c = country_to_iso2(t)
            if c and isinstance(c, str) and len(c) == 2:
                return c.upper()
        except Exception:
            return None
        return None
    def split_aliases(v):
        if v in (None, ""):
            return []
        out = []
        if isinstance(v, list):
            for x in v:
                if isinstance(x, str):
                    cx = clean_text(x)
                    if cx:
                        out.append(cx)
        elif isinstance(v, str):
            parts = re.split(r"[;,|]\s*|\s{2,}", v)
            for p in parts:
                cp = clean_text(p)
                if cp:
                    out.append(cp)
        seen = set()
        dedup = []
        for a in out:
            low = a.lower()
            if low not in seen:
                seen.add(low)
                dedup.append(a)
        return dedup
    def to_list(v):
        if v in (None, ""):
            return []
        if isinstance(v, list):
            out = []
            for s in v:
                if isinstance(s, dict):
                    try:
                        s = json.dumps(s, ensure_ascii=False)
                    except Exception:
                        s = str(s)
                if isinstance(s, str) and s.strip():
                    out.append(s.strip())
            return out
        if isinstance(v, str):
            return [s.strip() for s in re.split(r"[;,|]\s*", v) if s.strip()]
        return []

    list_name = clean_text(first(["list_name","ListName","source_list","OFAC_list_name","SECO_list_name","EU_list_name","UN_list_name","AU_list_name","CA_list_name","UK_list_name","HMT_list_name"]))
    list_id = clean_text(first([
        "list_id","id","ID","reference_number","referenceId",
        "OFAC_list_id","ofac_list_id","OFAC_id","OFAC_reference_number",
        "SECO_list_id","SECO_id","SECO_reference_number","SECO_ssid",
        "UK_id","UK_reference_number","HMT_id",
        "EU_id","EU_reference_number","EU_list_id",
        "UN_id","UN_reference_number","UN_list_id",
        "AU_id","AU_reference_number","AU_list_id",
        "CA_id","CA_reference_number","CA_list_id"
    ]))
    if not list_id:
        return None

    full_name = clean_text(first(["full_name","primary_name","name","OFAC_primary_name","OFAC_full_name","SECO_full_name","SECO_primary_name","SECO_whole_name","subject_whole_name","UK_full_name","EU_full_name","UN_full_name","AU_full_name","CA_full_name"]))
    first_name = clean_text(first(["first_name","given_name","OFAC_first_name","SECO_first_name","SECO_given_name","subject_given_name","UK_first_name","EU_first_name","UN_first_name","AU_first_name","CA_first_name"]))
    middle_name = clean_text(first(["middle_name","middle","OFAC_middle_name","SECO_middle_name","subject_middle_name","UN_middle_name","EU_middle_name"]))
    last_name = clean_text(first(["last_name","family_name","surname","OFAC_last_name","SECO_last_name","SECO_family_name","subject_family_name","UK_last_name","EU_last_name","UN_last_name","AU_last_name","CA_last_name"]))
    other_first_name = clean_text(first(["other_first_name","additional_given_name","further_given_name","OFAC_other_first_name","SECO_further_given_name","subject_further_given_name"]))

    nationality = clean_text(first(["nationality","nationality_country","country_of_nationality","OFAC_nationality","SECO_nationality","subject_nationality","UK_nationality","EU_nationality","UN_nationality","AU_nationality","CA_nationality"]))
    citizenship_country = clean_text(first(["citizenship_country","citizenship","country_of_citizenship","OFAC_citizenship","SECO_citizenship_country","subject_citizenship_country","UK_citizenship_country","EU_citizenship_country","UN_citizenship_country","AU_citizenship_country","CA_citizenship_country"]))
    citizenship_country_iso = clean_upper(first(["citizenship_country_iso","OFAC_citizenship_country_iso","SECO_citizenship_country_iso"]))
    if not citizenship_country_iso:
        citizenship_country_iso = iso2(citizenship_country)

    address_country = clean_text(first(["address_country","OFAC_address_country","OFAC_country","SECO_country","subject_country","UK_address_country","EU_address_country","UN_address_country","AU_address_country","CA_address_country"]))
    address_city = clean_text(first(["address_city","OFAC_address_city","SECO_city","subject_city","EU_address_city","UN_address_city","AU_address_city","CA_address_city"]))
    address_state = clean_text(first(["address_state","OFAC_address_state","SECO_state","subject_state","EU_address_state","UN_address_state","AU_address_state","CA_address_state"]))
    address_postal_code = clean_text(first(["address_postal_code","OFAC_address_postal_code","OFAC_postal_code","SECO_postal_code","subject_postal_code","EU_address_postal_code","UN_address_postal_code","AU_address_postal_code","CA_address_postal_code"]))
    primary_address_value = clean_text(first(["primary_address_value","OFAC_primary_address_value","SECO_primary_address_value",
    "subject_primary_address_value","EU_primary_address_value","UN_primary_address_value","AU_primary_address_value","CA_primary_address_value"]))
    address_country_iso = clean_upper(first(["address_country_iso","OFAC_address_country_iso","SECO_address_country_iso","EU_address_country_iso","UN_address_country_iso","AU_address_country_iso","CA_address_country_iso","UK_address_country_iso"]))
    if not address_country_iso:
        address_country_iso = iso2(address_country)

    aliases_raw = first(["aliases","alias_list","OFAC_aliases","SECO_aliases","UK_aliases","EU_aliases","UN_aliases","AU_aliases","CA_aliases"])
    aliases_list = split_aliases(aliases_raw)
    aliases_json = json.dumps(aliases_list, ensure_ascii=False)

    alternative_addresses_list = to_list(first([
        "alternative_addresses","all_addresses","OFAC_alternative_addresses","SECO_all_addresses","EU_all_addresses","UN_all_addresses","AU_all_addresses","CA_all_addresses","UK_all_addresses"
    ]))
    alternative_addresses_json = json.dumps(alternative_addresses_list, ensure_ascii=False)

    alternative_cities_list = to_list(first([
        "alternative_cities","all_cities","OFAC_all_cities","SECO_all_cities","EU_all_cities","UN_all_cities","AU_all_cities","CA_all_cities","UK_all_cities"
    ]))
    alternative_states_list = to_list(first([
        "alternative_states","all_states","OFAC_all_states","SECO_all_states","EU_all_states","UN_all_states","AU_all_states","CA_all_states","UK_all_states"
    ]))
    alternative_postal_codes_list = to_list(first([
        "alternative_postal_codes","all_postal_codes","OFAC_all_postal_codes","SECO_all_postal_codes","EU_all_postal_codes","UN_all_postal_codes","AU_all_postal_codes","CA_all_postal_codes","UK_all_postal_codes"
    ]))
    alternative_countries_list = to_list(first([
        "alternative_countries","all_countries","OFAC_all_countries","SECO_all_countries","EU_all_countries","UN_all_countries","AU_all_countries","CA_all_countries","UK_all_countries"
    ]))
    alternative_country_isos_list = to_list(first([
        "alternative_country_isos","all_country_isos","OFAC_all_country_isos","SECO_all_country_isos","EU_all_country_isos","UN_all_country_isos","AU_all_country_isos","CA_all_country_isos","UK_all_country_isos"
    ]))
    if not alternative_country_isos_list and alternative_countries_list:
        tmp = []
        for c in alternative_countries_list:
            cc = iso2(c)
            if cc:
                tmp.append(cc)
        alternative_country_isos_list = tmp

    alternative_cities_json = json.dumps(alternative_cities_list, ensure_ascii=False)
    alternative_states_json = json.dumps(alternative_states_list, ensure_ascii=False)
    alternative_postal_codes_json = json.dumps(alternative_postal_codes_list, ensure_ascii=False)
    alternative_countries_json = json.dumps(alternative_countries_list, ensure_ascii=False)
    alternative_country_isos_json = json.dumps(alternative_country_isos_list, ensure_ascii=False)

    global_id = clean_text(first(["global_id","OFAC_global_id","SECO_global_id","UK_global_id","EU_global_id","UN_global_id","AU_global_id","CA_global_id"]))
    if not global_id and list_name and list_id:
        global_id = f"{list_name}-{list_id}"

    primary_name = clean_text(first(["primary_name","full_name","name","OFAC_primary_name","SECO_primary_name","SECO_whole_name","subject_whole_name","EU_primary_name","UN_full_name","UK_full_name","AU_full_name","CA_full_name"])) or full_name
    primary_name_language = clean_text(first(["primary_name_language","SECO_primary_name_language","subject_primary_name_language","EU_primary_name_language"]))
    primary_name_quality = clean_text(first(["primary_name_quality","SECO_primary_name_quality","subject_primary_name_quality","EU_primary_name_quality"]))
    first_spelling_variant_value = clean_text(first(["first_spelling_variant_value","SECO_first_spelling_variant_value","subject_first_spelling_variant_value","OFAC_first_spelling_variant_value","EU_first_spelling_variant_value"]))
    birth_year = clean_text(first(["birth_year","year_of_birth","OFAC_birth_year","SECO_birth_year","subject_birth_year","EU_birth_year","UN_birth_year","AU_birth_year","CA_birth_year"]))
    birth_month = clean_text(first(["birth_month","month_of_birth","OFAC_birth_month","SECO_birth_month","subject_birth_month","EU_birth_month","UN_birth_month","AU_birth_month","CA_birth_month"]))
    birth_day = clean_text(first(["birth_day","day_of_birth","OFAC_birth_day","SECO_birth_day","subject_birth_day","EU_birth_day","UN_birth_day","AU_birth_day","CA_birth_day"]))
    place_of_birth = clean_text(first(["place_of_birth","place_of_birth_text","UN_place_of_birth","EU_place_of_birth","AU_place_of_birth","CA_place_of_birth","UK_place_of_birth"]))
    sex = clean_text(first(["sex","gender","OFAC_sex","SECO_sex","subject_sex","EU_sex","UN_sex","AU_sex","CA_sex"]))

    justification_text = clean_text(first(["justification_text","SECO_justification_text","subject_justification_text","EU_justification_text","UN_justification_text","AU_justification_text","CA_justification_text","OFAC_justification_text"]))
    other_information_text = clean_text(first([
        "other_information_text","SECO_other_information_text","subject_other_information_text",
        "EU_other_information_text","UN_other_information_text","AU_other_information_text","CA_other_information_text",
        "OFAC_other_information_text","OFAC_remarks_raw"
    ]))
    if not other_information_text:
        notes = []
        measures = []
        m1 = rec.get("OFAC_sanctions_measures")
        m2 = rec.get("sanctions_measures")
        if isinstance(m1, str) and m1.strip():
            measures = [m1.strip()]
        if isinstance(m2, str) and m2.strip():
            measures = measures + [m2.strip()]
        directives = []
        rels = []
        rdet = rec.get("OFAC_relationships") or []
        for r in rdet:
            if isinstance(r, dict):
                a = clean_text(f'{r.get("type")} {r.get("from_profile_id") or ""}->{r.get("to_profile_id") or ""}')
                if a:
                    rels.append(a)
        events = []
        ebag = rec.get("OFAC_entry_events") or []
        for e in ebag:
            if isinstance(e, dict):
                a = clean_text(f'{e.get("type")} {e.get("date")}')
                if a:
                    events.append(a)
        docs = []
        idd = rec.get("OFAC_identity_documents") or []
        for d in idd:
            if isinstance(d, dict):
                a = clean_text(" ".join([str(d.get("type") or ""), str(d.get("number") or "")]))
                if a:
                    docs.append(a)
        extra_addrs = []
        if alternative_addresses_list:
            extra_addrs = [clean_text(x) for x in alternative_addresses_list if clean_text(x)]
        parts = []
        if measures:
            parts.append("Measures: " + "; ".join(measures))
        if directives:
            parts.append("Directives: " + "; ".join(directives))
        if events:
            parts.append("Events: " + " | ".join(events))
        if rels:
            parts.append("Relationships: " + " | ".join(rels))
        if docs:
            parts.append("Documents: " + " | ".join(docs))
        if notes:
            parts.append("Notes: " + " | ".join(notes))
        if extra_addrs:
            parts.append("Other Addresses: " + " || ".join(extra_addrs))
        other_information_text = clean_text("; ".join([p for p in parts if p])) or None

    sanctions_program_name = clean_text(first(["sanctions_program_name","program_name","programme","program","OFAC_sanctions_program_name","SECO_sanctions_program_name","sanctions_set","UK_sanctions_program_name","EU_sanctions_program_name","UN_sanctions_program_name","AU_sanctions_program_name","CA_sanctions_program_name"]))
    publication_date = clean_text(first(["publication_date","published_at","date_published","OFAC_publication_date","SECO_publication_date","SECO_publication","EU_publication_date","UN_publication_date","AU_publication_date","CA_publication_date"]))
    enactment_date = clean_text(first(["enactment_date","date_enacted","OFAC_enactment_date","SECO_enactment_date","SECO_enactment","EU_enactment_date","UN_enactment_date","AU_enactment_date","CA_enactment_date"]))
    effective_date = clean_text(first(["effective_date","date_effective","OFAC_effective_date","SECO_effective_date","SECO_effective","EU_effective_date","UN_effective_date","AU_effective_date","CA_effective_date"]))

    contact_emails_list = to_list(first(["email_address","emails","email_addresses","contact_emails","OFAC_emails"]))
    contact_phone_numbers_list = to_list(first(["phone_numbers","phones","contact_phones","contact_phone_numbers","OFAC_phone_numbers"]))
    contact_fax_numbers_list = to_list(first(["fax_numbers","contact_faxes","contact_fax_numbers","OFAC_fax_numbers"]))
    contact_websites_list = to_list(first(["website","websites","urls","website_urls","contact_websites","OFAC_websites"]))
    bic_codes_list = to_list(first(["bic","bic_codes","bics","swift_codes","OFAC_bic_codes"]))
    iban_numbers_list = to_list(first(["iban_numbers","ibans","OFAC_iban_numbers"]))
    ssn_numbers_list = to_list(first(["ssn_numbers","social_security_numbers","national_insurance_numbers","OFAC_ssn_numbers"]))
    passport_numbers_list = to_list(first(["passport_numbers","passport_ids","OFAC_passport_numbers"]))
    national_id_numbers_list = to_list(first(["national_id_numbers","national_identification_numbers","id_numbers","OFAC_national_id_numbers"]))
    tax_id_numbers_list = to_list(first(["tax_id_numbers","TINs","tax_numbers","OFAC_tax_id_numbers"]))
    other_id_numbers_list = to_list(first(["other_id_numbers","other_identifiers","OFAC_other_id_numbers"]))

    contact_emails_json = json.dumps(contact_emails_list, ensure_ascii=False)
    contact_phone_numbers_json = json.dumps(contact_phone_numbers_list, ensure_ascii=False)
    contact_fax_numbers_json = json.dumps(contact_fax_numbers_list, ensure_ascii=False)
    contact_websites_json = json.dumps(contact_websites_list, ensure_ascii=False)
    bic_codes_json = json.dumps(bic_codes_list, ensure_ascii=False)
    iban_numbers_json = json.dumps(iban_numbers_list, ensure_ascii=False)
    ssn_numbers_json = json.dumps(ssn_numbers_list, ensure_ascii=False)
    passport_numbers_json = json.dumps(passport_numbers_list, ensure_ascii=False)
    national_id_numbers_json = json.dumps(national_id_numbers_list, ensure_ascii=False)
    tax_id_numbers_json = json.dumps(tax_id_numbers_list, ensure_ascii=False)
    other_id_numbers_json = json.dumps(other_id_numbers_list, ensure_ascii=False)

    classification = clean_text(first(["classification","entity_classification","subject_entity_type","subject_type","entity_type","OFAC_entity_type","SECO_entity_type","UN_entity_type","EU_entity_type","UK_entity_type","CA_entity_type","EntityOrShip","entity_or_ship"]))
    if not classification:
        vessel_hint = any([clean_text(rec.get("OFAC_vessel_type")), clean_text(rec.get("OFAC_vessel_mmsi"))]) or bool(re.search(r"\b(IMO|MMSI|MT|MV|TANKER|VESSEL|SHIP)\b", (full_name or "") + " " + (other_information_text or ""), re.IGNORECASE))
        aircraft_hint = bool(clean_text(rec.get("OFAC_aircraft_type"))) or bool(re.search(r"\b(AIRCRAFT|TAIL|REG)\b", (full_name or "") + " " + (other_information_text or ""), re.IGNORECASE))
        individual_hint = any([birth_year, birth_month, birth_day, sex, nationality, citizenship_country])
        if vessel_hint:
            classification = "Vessel"
        elif aircraft_hint:
            classification = "Aircraft"
        elif individual_hint:
            classification = "Individual"
        else:
            classification = "Entity"

    def to_ascii(s):
        if not s:
            return None
        n = unicodedata.normalize("NFKD", s)
        b = n.encode("ascii", "ignore")
        return b.decode("ascii").strip().lower() or None
    def token_str(s):
        a = to_ascii(s) or ""
        toks = re.findall(r"[0-9a-zA-Z]+", a)
        return " ".join(toks) if toks else None
    def soundex(s):
        if not s:
            return None
        s = re.sub(r"[^A-Za-z]", "", (to_ascii(s) or "").upper())
        if not s:
            return None
        first = s[0]
        mapping = {"BFPV":"1","CGJKQSXZ":"2","DT":"3","L":"4","MN":"5","R":"6"}
        def code(ch):
            for k,v in mapping.items():
                if ch in k:
                    return v
            return ""
        digits = ""
        prev = ""
        for ch in s[1:]:
            d = code(ch)
            if d != prev:
                digits += d
                prev = d
        digits = digits.replace("0","")
        snd = (first + digits + "000")[:4]
        return snd

    primary_name_ascii = to_ascii(primary_name)
    primary_name_tokens = token_str(primary_name)
    aliases_ascii = [to_ascii(a) for a in aliases_list if to_ascii(a)]
    aliases_tokens = [token_str(a) for a in aliases_list if token_str(a)]
    primary_name_soundex = soundex(primary_name)
    aliases_soundex = [soundex(a) for a in aliases_list if soundex(a)]
    birth_date = None
    if birth_year and birth_month and birth_day:
        birth_date = f"{birth_year.zfill(4)}-{birth_month.zfill(2)}-{birth_day.zfill(2)}"

    source_url = clean_text(first(["source_url","sourceUrl","SourceURL"]))
    source_etag = clean_text(first(["source_etag","source_hash","etag","ETag"]))
    valid_from = clean_text(first(["valid_from","ValidFrom","date_from"]))
    valid_to = clean_text(first(["valid_to","ValidTo","date_to"]))
    record_status = clean_text(first(["record_status","status"]))

    return {
        "list_row": (
            list_name, list_id, classification, full_name, first_name, middle_name, last_name, other_first_name,
            nationality, citizenship_country, citizenship_country_iso,
            primary_address_value, address_city, address_state, address_postal_code, address_country, address_country_iso,
            alternative_addresses_json, aliases_json,
            json.dumps({
                "alternative_cities": alternative_cities_list,
                "alternative_states": alternative_states_list,
                "alternative_postal_codes": alternative_postal_codes_list,
                "alternative_countries": alternative_countries_list,
                "alternative_country_isos": alternative_country_isos_list
            }, ensure_ascii=False),
            alternative_cities_json, alternative_states_json, alternative_postal_codes_json, alternative_countries_json, alternative_country_isos_json,
            global_id
        ),
        "details_row": (
            list_name, list_id, primary_name, primary_name_language, primary_name_quality,
            first_spelling_variant_value, birth_year, birth_month, birth_day, place_of_birth, sex,
            nationality, citizenship_country, citizenship_country_iso,
            primary_address_value, address_city, address_state, address_postal_code, address_country, address_country_iso,
            alternative_addresses_json,
            justification_text, other_information_text, sanctions_program_name,
            publication_date, enactment_date or publication_date, effective_date or publication_date, aliases_json,
            json.dumps({
                "alternative_cities": alternative_cities_list,
                "alternative_states": alternative_states_list,
                "alternative_postal_codes": alternative_postal_codes_list,
                "alternative_countries": alternative_countries_list,
                "alternative_country_isos": alternative_country_isos_list
            }, ensure_ascii=False),
            alternative_cities_json, alternative_states_json, alternative_postal_codes_json, alternative_countries_json, alternative_country_isos_json,
            global_id,
            classification, contact_emails_json, contact_phone_numbers_json, contact_fax_numbers_json, contact_websites_json,
            bic_codes_json, iban_numbers_json, ssn_numbers_json, passport_numbers_json, national_id_numbers_json, tax_id_numbers_json, other_id_numbers_json
        ),
        "aux": {
            "list_name": list_name,
            "list_id": list_id,
            "primary_name": primary_name,
            "primary_name_ascii": primary_name_ascii,
            "primary_name_tokens": primary_name_tokens,
            "primary_name_soundex": primary_name_soundex,
            "aliases_list": aliases_list,
            "aliases_ascii": aliases_ascii,
            "aliases_tokens": aliases_tokens,
            "aliases_soundex": aliases_soundex,
            "birth_year": birth_year,
            "birth_month": birth_month,
            "birth_day": birth_day,
            "birth_date": birth_date,
            "place_of_birth": place_of_birth,
            "sex": sex,
            "nationality": nationality,
            "citizenship_country": citizenship_country,
            "citizenship_country_iso": citizenship_country_iso,
            "address_country_iso": address_country_iso,
            "classification": classification,
            "global_id": global_id,
            "contact_emails_list": contact_emails_list,
            "contact_phone_numbers_list": contact_phone_numbers_list,
            "contact_fax_numbers_list": contact_fax_numbers_list,
            "contact_websites_list": contact_websites_list,
            "bic_codes_list": bic_codes_list,
            "iban_numbers_list": iban_numbers_list,
            "ssn_numbers_list": ssn_numbers_list,
            "passport_numbers_list": passport_numbers_list,
            "national_id_numbers_list": national_id_numbers_list,
            "tax_id_numbers_list": tax_id_numbers_list,
            "other_id_numbers_list": other_id_numbers_list,
            "source_url": source_url,
            "source_etag": source_etag,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "record_status": record_status
        }
    }

def _ensure_fts(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sanctionslist'")
    if not cur.fetchone():
        return

    def create_fts():
        try:
            cur.execute(
                "CREATE VIRTUAL TABLE sanctions_fts "
                "USING fts5(list_name, list_id, name, aliases, "
                "tokenize = 'unicode61 remove_diacritics 2 tokenchars .-_')"
            )
        except sqlite3.OperationalError:
            cur.execute(
                "CREATE VIRTUAL TABLE sanctions_fts "
                "USING fts4(list_name, list_id, name, aliases)"
            )

    cur.execute("CREATE TABLE IF NOT EXISTS sanctions_meta (key TEXT PRIMARY KEY, value TEXT)")

    cur.execute("""
        SELECT
            COUNT(*) AS c,
            COALESCE(SUM(
                length(COALESCE(full_name,'')) +
                length(COALESCE(first_name,'')) +
                length(COALESCE(middle_name,'')) +
                length(COALESCE(last_name,'')) +
                length(COALESCE(other_first_name,'')) +
                length(COALESCE(aliases,'')) +
                length(COALESCE(list_id,'')) +
                length(COALESCE(list_name,''))
            ), 0) AS s
        FROM sanctionslist
    """)
    row = cur.fetchone()
    total_rows = int(row[0] or 0)
    sum_lengths = int(row[1] or 0)
    current_fp = f"{total_rows}:{sum_lengths}"
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='sanctions_fts'")
    row = cur.fetchone()
    need_rebuild = False
    if not row:
        create_fts()
        need_rebuild = True
    else:
        sql = row[0] or ""
        needed_cols = ("list_name", "list_id", "name", "aliases")
        if not all(c in sql for c in needed_cols):
            cur.execute("DROP TABLE IF EXISTS sanctions_fts")
            create_fts()
            need_rebuild = True

    if not need_rebuild:
        try:
            cur.execute("SELECT COUNT(*) FROM sanctions_fts")
            fts_count = int((cur.fetchone() or (0,))[0] or 0)
        except sqlite3.OperationalError:
            fts_count = -1
        cur.execute("SELECT value FROM sanctions_meta WHERE key='sanctions_fts_fingerprint'")
        prev_fp_row = cur.fetchone()
        prev_fp = prev_fp_row[0] if prev_fp_row else None

        if fts_count == total_rows and prev_fp == current_fp and total_rows > 0:
            return 
        else:
            need_rebuild = True

    if not need_rebuild:
        return
    cur.execute("DELETE FROM sanctions_fts")
    cur.execute("""
        SELECT
            list_name,
            list_id,
            full_name,
            first_name,
            middle_name,
            last_name,
            other_first_name,
            aliases
        FROM sanctionslist
    """)
    rows = cur.fetchall()

    insert_sql = "INSERT INTO sanctions_fts(list_name, list_id, name, aliases) VALUES (?,?,?,?)"

    for (list_name, list_id, full_name, first_name, middle_name, last_name, other_first_name, aliases) in rows:
        parts = []
        if full_name:
            parts.append(str(full_name))
        nm = " ".join([p for p in (first_name, middle_name, last_name, other_first_name) if p])
        if nm:
            parts.append(nm)
        name_text = " ".join(parts).strip()

        alias_text = ""
        if aliases:
            try:
                arr = json.loads(aliases)
                if isinstance(arr, dict):
                    arr = list(arr.values())
                if isinstance(arr, list):
                    alias_text = " ".join([str(a).strip() for a in arr if str(a).strip()])
                else:
                    alias_text = str(aliases)
            except Exception:
                alias_text = str(aliases)

        cur.execute(
            insert_sql,
            (
                str(list_name or ""),
                str(list_id or ""),
                str(name_text or ""),
                str(alias_text or "")
            )
        )
    cur.execute("UPDATE sanctions_meta SET value=? WHERE key='sanctions_fts_fingerprint'", (current_fp,))
    if cur.rowcount == 0:
        cur.execute("INSERT INTO sanctions_meta(key, value) VALUES(?, ?)", ("sanctions_fts_fingerprint", current_fp))

    conn.commit()

def returnDetails2_fts(name, country_iso=None, limit=1000):
    dbpath = Path(__file__).parent.parent / "data" / "sanctions.db"
    conn = sqlite3.connect(dbpath)
    cur = conn.cursor()
    _ensure_fts(conn)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sanctions_fts'")
    has_fts = bool(cur.fetchone())

    name = (name or "").strip().lower()
    tokens = [t for t in re.split(r"[^0-9a-zA-Z]+", name) if t]
    if not tokens:
        conn.close()
        return []

    if has_fts:
        terms = []
        for t in tokens:
            if len(t) >= 3:
                terms.append(f"name:{t}*")
                terms.append(f"aliases:{t}*")
        if not terms:
            conn.close()
            return []
        fts_query = " OR ".join(terms)

        where_country = ""
        params = [fts_query]
        if country_iso:
            ci = country_iso.strip().upper()
            where_country = " AND (s.citizenship_country_iso = ?)"
            params.append(ci)
        params.append(int(limit))

        sql = f"""
            SELECT
                s.list_name,
                s.list_id,
                s.classification,
                s.full_name,
                s.first_name,
                s.middle_name,
                s.last_name,
                s.other_first_name,
                s.nationality,
                s.citizenship_country,
                s.citizenship_country_iso,
                s.primary_address,
                s.address_city,
                s.address_state,
                s.address_postal_code,
                s.address_country,
                s.address_country_iso,
                s.alternative_addresses,
                s.aliases,
                s.global_id
            FROM sanctions_fts
            JOIN sanctionslist AS s
              ON s.list_id = sanctions_fts.list_id AND s.list_name = sanctions_fts.list_name
            WHERE sanctions_fts MATCH ? {where_country}
            LIMIT ?
        """
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        return rows
    else:
        like_clauses = []
        params = []
        for t in tokens:
            if len(t) >= 3:
                like_clauses.append("(LOWER(s.full_name) LIKE ? OR LOWER(s.first_name) LIKE ? OR LOWER(s.middle_name) LIKE ? OR LOWER(s.last_name) LIKE ? OR LOWER(s.aliases) LIKE ?)")
                patt = f"%{t}%"
                params.extend([patt, patt, patt, patt, patt])
        if not like_clauses:
            conn.close()
            return []

        where_country = ""
        if country_iso:
            ci = country_iso.strip().upper()
            where_country = " AND (s.citizenship_country_iso = ?)"
            params.append(ci)
        params.append(int(limit))

        sql = f"""
            SELECT
                s.list_name,
                s.list_id,
                s.classification,
                s.full_name,
                s.first_name,
                s.middle_name,
                s.last_name,
                s.other_first_name,
                s.nationality,
                s.citizenship_country,
                s.citizenship_country_iso,
                s.primary_address,
                s.address_city,
                s.address_state,
                s.address_postal_code,
                s.address_country,
                s.address_country_iso,
                s.alternative_addresses,
                s.aliases,
                s.global_id
            FROM sanctionslist AS s
            WHERE {' AND '.join(like_clauses)} {where_country}
            LIMIT ?
        """
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        return rows


def createdatabase(detailslist):
    dbpath = Path(__file__).parent.parent / "data" / "sanctions.db"
    dbpath.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(dbpath)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA journal_mode=OFF")
    cur.execute("PRAGMA synchronous=OFF")
    cur.execute("PRAGMA temp_store=MEMORY")
    cur.execute("PRAGMA cache_size=-100000")
    cur.execute("DROP TABLE IF EXISTS sanctionslist")
    cur.execute("DROP TABLE IF EXISTS sanctionsdetails")
    cur.execute("DROP TABLE IF EXISTS sanctions_fts")
    cur.execute("DROP TABLE IF EXISTS sanctions_fts_config")
    cur.execute("DROP TABLE IF EXISTS sanctions_fts_content")
    cur.execute("DROP TABLE IF EXISTS sanctions_fts_data")
    cur.execute("DROP TABLE IF EXISTS sanctions_fts_docsize")
    cur.execute("DROP TABLE IF EXISTS sanctions_fts_idx")
    cur.execute("DROP TABLE IF EXISTS entities")
    cur.execute("DROP TABLE IF EXISTS list_entity_map")
    cur.execute("DROP TABLE IF EXISTS entity_aliases")
    cur.execute("DROP TABLE IF EXISTS entity_identifiers")
    cur.execute("DROP TABLE IF EXISTS provenance")
    cur.execute("DROP TABLE IF EXISTS entity_match_keys")
    cur.execute("DROP TABLE IF EXISTS entity_relations")
    cur.execute("DROP TABLE IF EXISTS match_cache")
    cur.execute("DROP TABLE IF EXISTS screening_audit")

    cur.execute("""
        CREATE TABLE sanctionslist (
            list_name TEXT,
            list_id TEXT,
            classification TEXT,
            full_name TEXT,
            first_name TEXT,
            middle_name TEXT,
            last_name TEXT,
            other_first_name TEXT,
            nationality TEXT,
            citizenship_country TEXT,
            citizenship_country_iso TEXT,
            primary_address TEXT,
            address_city TEXT,
            address_state TEXT,
            address_postal_code TEXT,
            address_country TEXT,
            address_country_iso TEXT,
            alternative_addresses TEXT,
            aliases TEXT,
            alternative_location_bundle TEXT,
            alternative_cities TEXT,
            alternative_states TEXT,
            alternative_postal_codes TEXT,
            alternative_countries TEXT,
            alternative_country_isos TEXT,
            global_id TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE sanctionsdetails (
            list_name TEXT,
            list_id TEXT,
            primary_name TEXT,
            primary_name_language TEXT,
            primary_name_quality TEXT,
            first_spelling_variant_value TEXT,
            birth_year TEXT,
            birth_month TEXT,
            birth_day TEXT,
            place_of_birth TEXT,
            sex TEXT,
            nationality TEXT,
            citizenship_country TEXT,
            citizenship_country_iso TEXT,
            primary_address TEXT,
            address_city TEXT,
            address_state TEXT,
            address_postal_code TEXT,
            address_country TEXT,
            address_country_iso TEXT,
            alternative_addresses TEXT,
            justification_text TEXT,
            other_information_text TEXT,
            sanctions_program_name TEXT,
            publication_date TEXT,
            enactment_date TEXT,
            effective_date TEXT,
            aliases TEXT,
            alternative_location_bundle TEXT,
            alternative_cities TEXT,
            alternative_states TEXT,
            alternative_postal_codes TEXT,
            alternative_countries TEXT,
            alternative_country_isos TEXT,
            global_id TEXT,
            classification TEXT,
            contact_emails TEXT,
            contact_phone_numbers TEXT,
            contact_fax_numbers TEXT,
            contact_websites TEXT,
            bic_codes TEXT,
            iban_numbers TEXT,
            ssn_numbers TEXT,
            passport_numbers TEXT,
            national_id_numbers TEXT,
            tax_id_numbers TEXT,
            other_id_numbers TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE entities (
            entity_id INTEGER PRIMARY KEY,
            canonical_name TEXT,
            classification TEXT,
            birth_year TEXT,
            birth_month TEXT,
            birth_day TEXT,
            birth_date TEXT,
            place_of_birth TEXT,
            sex TEXT,
            nationality TEXT,
            citizenship_country TEXT,
            citizenship_country_iso TEXT,
            countries_json TEXT,
            names_ascii TEXT,
            name_tokens TEXT,
            aliases_json TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE list_entity_map (
            list_name TEXT,
            list_id TEXT,
            global_id TEXT,
            entity_id INTEGER,
            PRIMARY KEY (list_name, list_id),
            FOREIGN KEY(entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE entity_aliases (
            entity_id INTEGER,
            alias TEXT,
            FOREIGN KEY(entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE entity_identifiers (
            entity_id INTEGER,
            id_type TEXT,
            id_value TEXT,
            country_iso TEXT,
            issuer TEXT,
            normalized_value TEXT,
            FOREIGN KEY(entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE provenance (
            list_name TEXT,
            list_id TEXT,
            source_url TEXT,
            source_etag TEXT,
            ingested_at TEXT DEFAULT (datetime('now')),
            valid_from TEXT,
            valid_to TEXT,
            record_status TEXT,
            PRIMARY KEY (list_name, list_id)
        )
    """)
    cur.execute("""
        CREATE TABLE entity_match_keys (
            entity_id INTEGER,
            primary_name_ascii TEXT,
            primary_name_tokens TEXT,
            primary_name_soundex TEXT,
            aliases_ascii_json TEXT,
            aliases_tokens_json TEXT,
            aliases_soundex_json TEXT,
            FOREIGN KEY(entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE entity_relations (
            entity_id INTEGER,
            relation_type TEXT,
            related_text TEXT,
            FOREIGN KEY(entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE match_cache (
            key_hash TEXT PRIMARY KEY,
            decision TEXT,
            ttl_expires_at TEXT,
            payload_hash TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE screening_audit (
            tx_id TEXT PRIMARY KEY,
            timestamp TEXT DEFAULT (datetime('now')),
            inputs_json TEXT,
            matched_json TEXT,
            decision_json TEXT
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_country ON sanctionslist(citizenship_country_iso, address_country_iso)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_fullname ON sanctionslist(full_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_lastname ON sanctionslist(last_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_aliases ON sanctionslist(aliases)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_details_birth ON sanctionsdetails(birth_year, birth_month, birth_day)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_details_country ON sanctionsdetails(citizenship_country_iso, address_country_iso)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_details_global ON sanctionsdetails(global_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_map_entity ON list_entity_map(entity_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(canonical_name)")

    skipped = 0
    aux_rows = []
    for rec in detailslist:
        norm = normalize_sanctions_record(rec)
        if not norm:
            skipped += 1
            continue
        cur.execute(
            """
            INSERT INTO sanctionslist (
                list_name, list_id, classification, full_name, first_name, middle_name, last_name, other_first_name,
                nationality, citizenship_country, citizenship_country_iso,
                primary_address, address_city, address_state, address_postal_code, address_country, address_country_iso,
                alternative_addresses, aliases, alternative_location_bundle, alternative_cities, alternative_states, alternative_postal_codes, alternative_countries, alternative_country_isos, global_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            norm["list_row"]
        )
        cur.execute(
            """
            INSERT INTO sanctionsdetails (
                list_name, list_id, primary_name, primary_name_language, primary_name_quality,
                first_spelling_variant_value, birth_year, birth_month, birth_day, place_of_birth, sex,
                nationality, citizenship_country, citizenship_country_iso,
                primary_address, address_city, address_state, address_postal_code, address_country, address_country_iso, alternative_addresses,
                justification_text, other_information_text, sanctions_program_name,
                publication_date, enactment_date, effective_date, aliases, alternative_location_bundle,
                alternative_cities, alternative_states, alternative_postal_codes, alternative_countries, alternative_country_isos,
                global_id,
                classification, contact_emails, contact_phone_numbers, contact_fax_numbers, contact_websites,
                bic_codes, iban_numbers, ssn_numbers, passport_numbers, national_id_numbers, tax_id_numbers, other_id_numbers
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            norm["details_row"]
        )
        aux_rows.append(norm.get("aux", {}))
        print(f"Inserted into database: {norm['details_row'][1]} | {norm['details_row'][2]}")

    entity_key_to_id = {}
    entities_acc = {}
    next_eid = 1

    def make_key(a):
        gid = (a.get("global_id") or "").strip()
        if gid:
            return ("G", gid)
        return ("H", a.get("primary_name_ascii") or "", a.get("birth_year") or "", a.get("citizenship_country_iso") or "")

    for a in aux_rows:
        if not a:
            continue
        k = make_key(a)
        eid = entity_key_to_id.get(k)
        if not eid:
            eid = next_eid
            next_eid += 1
            entity_key_to_id[k] = eid
            entities_acc[eid] = {
                "canonical_name": a.get("primary_name"),
                "classification": a.get("classification"),
                "birth_year": a.get("birth_year"),
                "birth_month": a.get("birth_month"),
                "birth_day": a.get("birth_day"),
                "birth_date": a.get("birth_date"),
                "place_of_birth": a.get("place_of_birth"),
                "sex": a.get("sex"),
                "nationality": a.get("nationality"),
                "citizenship_country": a.get("citizenship_country"),
                "citizenship_country_iso": a.get("citizenship_country_iso"),
                "countries": set([c for c in [a.get("citizenship_country_iso"), a.get("address_country_iso")] if c]),
                "names_ascii": a.get("primary_name_ascii"),
                "name_tokens": a.get("primary_name_tokens"),
                "aliases": set(a.get("aliases_list") or []),
                "aliases_ascii": set(a.get("aliases_ascii") or []),
                "aliases_tokens": set(a.get("aliases_tokens") or []),
                "aliases_soundex": set(a.get("aliases_soundex") or []),
                "primary_name_soundex": a.get("primary_name_soundex"),
                "ids": []
            }
        else:
            agg = entities_acc[eid]
            pn = a.get("primary_name")
            if pn and (not agg["canonical_name"] or len(pn) > len(agg["canonical_name"])):
                agg["canonical_name"] = pn
            agg["countries"].update([c for c in [a.get("citizenship_country_iso"), a.get("address_country_iso")] if c])
            for key in ["aliases","aliases_ascii","aliases_tokens","aliases_soundex"]:
                vals = a.get(key) or []
                if isinstance(vals, (list,set)):
                    agg[key].update([x for x in vals if x])
            if not agg["primary_name_soundex"] and a.get("primary_name_soundex"):
                agg["primary_name_soundex"] = a.get("primary_name_soundex")

        cur.execute(
            "INSERT OR REPLACE INTO provenance(list_name, list_id, source_url, source_etag, valid_from, valid_to, record_status) VALUES (?,?,?,?,?,?,?)",
            (a.get("list_name"), a.get("list_id"), a.get("source_url"), a.get("source_etag"), a.get("valid_from"), a.get("valid_to"), a.get("record_status"))
        )

    for k, eid in entity_key_to_id.items():
        agg = entities_acc[eid]
        cur.execute(
            """
            INSERT INTO entities(entity_id, canonical_name, classification, birth_year, birth_month, birth_day, birth_date, place_of_birth, sex, nationality, citizenship_country, citizenship_country_iso, countries_json, names_ascii, name_tokens, aliases_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                eid,
                agg.get("canonical_name"),
                agg.get("classification"),
                agg.get("birth_year"),
                agg.get("birth_month"),
                agg.get("birth_day"),
                agg.get("birth_date"),
                agg.get("place_of_birth"),
                agg.get("sex"),
                agg.get("nationality"),
                agg.get("citizenship_country"),
                agg.get("citizenship_country_iso"),
                json.dumps(sorted(list(agg.get("countries") or [])), ensure_ascii=False),
                agg.get("names_ascii"),
                agg.get("name_tokens"),
                json.dumps(sorted(list(agg.get("aliases") or [])), ensure_ascii=False)
            )
        )
        cur.execute(
            """
            INSERT INTO entity_match_keys(entity_id, primary_name_ascii, primary_name_tokens, primary_name_soundex, aliases_ascii_json, aliases_tokens_json, aliases_soundex_json)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                eid,
                agg.get("names_ascii"),
                agg.get("name_tokens"),
                agg.get("primary_name_soundex"),
                json.dumps(sorted(list(agg.get("aliases_ascii") or [])), ensure_ascii=False),
                json.dumps(sorted(list(agg.get("aliases_tokens") or [])), ensure_ascii=False),
                json.dumps(sorted(list(agg.get("aliases_soundex") or [])), ensure_ascii=False)
            )
        )
        for al in sorted(list(agg.get("aliases") or [])):
            cur.execute("INSERT INTO entity_aliases(entity_id, alias) VALUES (?,?)", (eid, al))

    for a in aux_rows:
        if not a:
            continue
        k = ("G", a.get("global_id")) if (a.get("global_id") or "").strip() else ("H", a.get("primary_name_ascii") or "", a.get("birth_year") or "", a.get("citizenship_country_iso") or "")
        eid = entity_key_to_id.get(k)
        cur.execute("INSERT OR REPLACE INTO list_entity_map(list_name, list_id, global_id, entity_id) VALUES (?,?,?,?)", (a.get("list_name"), a.get("list_id"), a.get("global_id"), eid))
        def add_ids(id_type, values, country=None):
            if values:
                for v in values:
                    if not v:
                        continue
                    nv = re.sub(r"[^A-Za-z0-9]", "", v).upper()
                    cur.execute("INSERT INTO entity_identifiers(entity_id, id_type, id_value, country_iso, issuer, normalized_value) VALUES (?,?,?,?,?,?)", (eid, id_type, v, country, None, nv))
        add_ids("BIC", a.get("bic_codes_list"))
        add_ids("IBAN", a.get("iban_numbers_list"))
        add_ids("SSN", a.get("ssn_numbers_list"), a.get("citizenship_country_iso"))
        add_ids("PASSPORT", a.get("passport_numbers_list"))
        add_ids("NATIONAL_ID", a.get("national_id_numbers_list"), a.get("citizenship_country_iso"))
        add_ids("TAX_ID", a.get("tax_id_numbers_list"))
        add_ids("OTHER_ID", a.get("other_id_numbers_list"))

    conn.commit()
    _ensure_fts(conn)
    conn.close()
    if skipped:
        print(f"Skipped {skipped} records missing list_id")
    
def returnDetails2():
    dbpath = Path(__file__).parent.parent / "data" / "sanctions.db"
    conn = sqlite3.connect(dbpath)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            list_name,
            list_id,
            classification,
            full_name,
            first_name,
            middle_name,
            last_name,
            other_first_name,
            nationality,
            citizenship_country,
            citizenship_country_iso,
            primary_address,
            address_city,
            address_state,
            address_postal_code,
            address_country,
            address_country_iso,
            alternative_addresses,
            aliases,
            global_id
        FROM sanctionslist
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def returnDetails2_fts_multi(queries, list_filter=None, limit=300):
    import re, sqlite3
    from pathlib import Path

    dbpath = Path(__file__).parent.parent / "data" / "sanctions.db"
    conn = sqlite3.connect(dbpath)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    _ensure_fts(conn)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sanctions_fts'")
    if not cur.fetchone():
        conn.close()
        return []

    def toks(s: str):
        return [t for t in re.findall(r"[0-9A-Za-z]+", s or "") if t]

    q_tokens = list({t.lower() for q in (queries or []) for t in toks(q)})
    if not q_tokens:
        conn.close()
        return []

    per_token_exprs = [f"name:{t}* OR aliases:{t}*" for t in q_tokens]
    fts_query = " AND ".join(per_token_exprs)

    list_clause_sql = ""
    list_clause_params = []
    if list_filter:
        norms = [str(x).strip().upper() for x in list_filter if str(x).strip()]
        if norms:
            like_placeholders = " OR ".join(["UPPER(s.list_name) LIKE ?"] * len(norms))
            list_clause_sql = f" AND ({like_placeholders})"
            list_clause_params = [f"{code}%" for code in norms]

    params = [fts_query] + list_clause_params + [int(limit)]

    sql = f"""
        WITH cands AS (
          SELECT
              s.list_name,
              s.list_id,
              s.classification,
              s.full_name,
              s.first_name,
              s.middle_name,
              s.last_name,
              s.other_first_name,
              s.nationality,
              s.citizenship_country,
              s.citizenship_country_iso,
              s.primary_address,
              s.address_city,
              s.address_state,
              s.address_postal_code,
              s.address_country,
              s.address_country_iso,
              s.alternative_addresses,
              s.aliases,
              s.global_id,
              d.justification_text,
              d.other_information_text
          FROM sanctions_fts AS f
          JOIN sanctionslist AS s
            ON s.list_id = f.list_id AND s.list_name = f.list_name
          LEFT JOIN sanctionsdetails AS d
            ON d.list_id = s.list_id AND d.list_name = s.list_name
          WHERE sanctions_fts MATCH ? {list_clause_sql}
        )
        SELECT *
        FROM cands
        GROUP BY list_name, list_id
        LIMIT ?
    """
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [tuple(r) for r in rows]

def warm_database():
    import sqlite3
    from pathlib import Path
    db_path = Path(__file__).parent.parent / "data" / "sanctions.db"
    if not db_path.exists():
        return {"warmed": False, "reason": "db_missing", "path": str(db_path)}

    try:
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sanctionslist'")
        if cur.fetchone() is None:
            return {"warmed": False, "reason": "schema_missing", "path": str(db_path)}
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sanctions_fts'")
        fts_exists = cur.fetchone() is not None
        cur.execute("SELECT COUNT(*) FROM sanctionslist")
        (row_count,) = cur.fetchone() or (0,)
        if fts_exists:
            for t in ("a*", "e*", "i*", "o*", "u*"):
                cur.execute("SELECT rowid FROM sanctions_fts WHERE sanctions_fts MATCH ? LIMIT 1", (t,))
                cur.fetchone()

        cur.execute("PRAGMA optimize")
        return {"warmed": bool(row_count and fts_exists), "rows": row_count, "fts": fts_exists, "path": str(db_path)}
    except sqlite3.OperationalError as e:
        return {"warmed": False, "reason": "operational_error", "error": str(e), "path": str(db_path)}
    finally:
        try:
            conn.close()
        except Exception:
            pass