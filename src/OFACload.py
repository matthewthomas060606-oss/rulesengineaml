import xml.etree.ElementTree as ET
import requests
from countrycode import country_to_iso2
from datetime import datetime, timezone
import re
from pathlib import Path
import logging
from config import get_config
cfg = get_config()


OFAC_CONS_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONSOLIDATED.XML"
OFAC_SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML"
OFAC_CONS_XML = "OFACCONS.30.06.25.xml"
OFAC_SDN_XML = "OFACSDN.10.09.25.xml"

def OFAC_fetch_cons():
    try:
        resp = requests.get(OFAC_CONS_URL, timeout=120)
        resp.raise_for_status()
        xml_bytes = resp.content
        if not xml_bytes:
            raise ValueError("empty body")
        log_path = cfg.paths.DATA_DIR / "OFACconslog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat() + "\n")
        return ET.fromstring(xml_bytes)
    except Exception as e:
        local = Path(__file__).parent.parent / "data" / OFAC_CONS_XML
        if local.exists():
            logging.error("OFAC consolidated download failed; using backup file %s", local, exc_info=True)
            return ET.parse(str(local)).getroot()
        raise RuntimeError(f"OFAC consolidated download failed and no backup found at {local}: {e}")

def OFAC_fetch_sdn():
    try:
        resp = requests.get(OFAC_SDN_URL, timeout=120)
        resp.raise_for_status()
        xml_bytes = resp.content
        if not xml_bytes:
            raise ValueError("empty body")
        log_path = cfg.paths.DATA_DIR / "OFACsdnlog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat() + "\n")
        return ET.fromstring(xml_bytes)
    except Exception as e:
        local = Path(__file__).parent.parent / "data" / OFAC_SDN_XML
        if local.exists():
            logging.error("OFAC SDN download failed; using backup file %s", local, exc_info=True)
            return ET.parse(str(local)).getroot()
        raise RuntimeError(f"OFAC SDN download failed and no backup found at {local}: {e}")

def _j(x):
    return [s for s in x if isinstance(s, str) and s.strip()]

def OFAC_extract(xml_root):
    ns = "{https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML}"
    list_name_value = xml_root.get("__source") or "OFAC"

    publication_date_value_global = None
    publ = xml_root.find(f"{ns}publshInformation")
    if publ is not None:
        pd = publ.find(f"{ns}Publish_Date")
        if pd is not None and pd.text and pd.text.strip():
            publication_date_value_global = pd.text.strip()

    out = []
    for sdn in xml_root.findall(f"{ns}sdnEntry"):
        uid_node = sdn.find(f"{ns}uid")
        list_id_value = uid_node.text.strip() if uid_node is not None and uid_node.text else None

        first_name_value = None
        middle_name_value = None
        last_name_value = None
        full_name_value = None

        fn = sdn.find(f"{ns}firstName")
        ln = sdn.find(f"{ns}lastName")
        mn = sdn.find(f"{ns}middleName")
        if fn is not None and fn.text: first_name_value = fn.text.strip() or None
        if mn is not None and mn.text: middle_name_value = mn.text.strip() or None
        if ln is not None and ln.text: last_name_value = ln.text.strip() or None
        name_parts = [p for p in [first_name_value, middle_name_value, last_name_value] if p]
        if name_parts:
            full_name_value = " ".join(name_parts)
        else:
            if last_name_value:
                full_name_value = last_name_value

        aliases = []
        aka_list = sdn.find(f"{ns}akaList")
        if aka_list is not None:
            for aka in aka_list.findall(f"{ns}aka"):
                a_fn = aka.find(f"{ns}firstName").text.strip() if aka.find(f"{ns}firstName") is not None and aka.find(f"{ns}firstName").text else None
                a_mn = aka.find(f"{ns}middleName").text.strip() if aka.find(f"{ns}middleName") is not None and aka.find(f"{ns}middleName").text else None
                a_ln = aka.find(f"{ns}lastName").text.strip() if aka.find(f"{ns}lastName") is not None and aka.find(f"{ns}lastName").text else None
                ap = [p for p in [a_fn, a_mn, a_ln] if p]
                if ap:
                    aliases.append(" ".join(ap))

        nationality_value = None
        citizenship_value = None
        nationality_list = sdn.find(f"{ns}nationalityList")
        if nationality_list is not None:
            nat_vals = []
            for n in nationality_list.findall(f"{ns}nationality"):
                if n is not None and n.text and n.text.strip():
                    nat_vals.append(n.text.strip())
            if nat_vals:
                nationality_value = "; ".join(nat_vals)

        citizenship_country_iso_value = None
        citizenship_list = sdn.find(f"{ns}citizenshipList")
        if citizenship_list is not None:
            c_vals = []
            for c in citizenship_list.findall(f"{ns}citizenship"):
                if c is not None and c.text and c.text.strip():
                    c_vals.append(c.text.strip())
            if c_vals:
                citizenship_value = "; ".join(c_vals)
                citizenship_country_iso_value = country_to_iso2(c_vals[0])

        sex_value = None
        gender_list = sdn.find(f"{ns}genderList")
        if gender_list is not None:
            g = gender_list.find(f"{ns}gender")
            if g is not None and g.text and g.text.strip():
                sex_value = g.text.strip()

        place_of_birth_text_value = None
        pob_list = sdn.find(f"{ns}placeOfBirthList")
        if pob_list is not None:
            items = pob_list.findall(f"{ns}placeOfBirthItem") or []
            chosen = None
            for p in items:
                main = (p.find(f"{ns}mainEntry").text.strip().lower() == "true") if p.find(f"{ns}mainEntry") is not None and p.find(f"{ns}mainEntry").text else False
                if main:
                    chosen = p
                    break
            if chosen is None and items:
                chosen = items[0]
            if chosen is not None:
                pb = chosen.find(f"{ns}placeOfBirth")
                if pb is not None and pb.text and pb.text.strip():
                    place_of_birth_text_value = pb.text.strip()

        birth_year_value = None
        birth_month_value = None
        birth_day_value = None
        dob_list = sdn.find(f"{ns}dateOfBirthList")
        if dob_list is not None:
            items = dob_list.findall(f"{ns}dateOfBirthItem") or []
            chosen = None
            for d in items:
                main = (d.find(f"{ns}mainEntry").text.strip().lower() == "true") if d.find(f"{ns}mainEntry") is not None and d.find(f"{ns}mainEntry").text else False
                if main:
                    chosen = d
                    break
            if chosen is None and items:
                chosen = items[0]
            if chosen is not None:
                dt = chosen.find(f"{ns}dateOfBirth")
                if dt is not None and dt.text and dt.text.strip():
                    t = dt.text.strip()
                    if len(t) >= 10 and t[4] == "-" and t[7] == "-":
                        birth_year_value, birth_month_value, birth_day_value = t[0:4], t[5:7], t[8:10]
                    elif len(t) >= 7 and t[4] == "-":
                        birth_year_value, birth_month_value = t[0:4], t[5:7]
                    elif len(t) >= 4:
                        birth_year_value = t[0:4]

        address_country_value = None
        address_country_iso_value = None
        address_city_value = None
        address_state_value = None
        address_postal_code_value = None
        primary_address_value = None
        address_details_value = None

        alternative_addresses_list = []
        alternative_cities_list = []
        alternative_states_list = []
        alternative_postal_codes_list = []
        alternative_countries_list = []
        alternative_country_isos_list = []

        addr_list = sdn.find(f"{ns}addressList")
        if addr_list is not None:
            addresses = addr_list.findall(f"{ns}address") or []
            for idx, a in enumerate(addresses):
                lines = []
                for tag in ("address1", "address2", "address3", "address4", "address5", "address6"):
                    v = (a.findtext(f"{ns}{tag}") or "").strip()
                    if v:
                        lines.append(v)
                city = (a.findtext(f"{ns}city") or "").strip() or None
                state = (a.findtext(f"{ns}stateOrProvince") or "").strip() or None
                postal = (a.findtext(f"{ns}postalCode") or "").strip() or None
                country = (a.findtext(f"{ns}country") or "").strip() or None

                if idx == 0:
                    primary_address_value = lines[0] if lines else None
                    address_city_value = city
                    address_state_value = state
                    address_postal_code_value = postal
                    address_country_value = country
                    address_country_iso_value = country_to_iso2(country) if country else None
                    address_details_value = "; ".join(lines[1:]) if len(lines) > 1 else None

                street = " | ".join(lines) if lines else None
                parts = [p for p in [street, city, state, postal, country] if p]
                alt_line = ", ".join(parts) if parts else None
                if alt_line:
                    alternative_addresses_list.append(alt_line)
                if city:
                    alternative_cities_list.append(city)
                if state:
                    alternative_states_list.append(state)
                if postal:
                    alternative_postal_codes_list.append(postal)
                if country:
                    alternative_countries_list.append(country)
                    try:
                        cc = country_to_iso2(country)
                        if cc:
                            alternative_country_isos_list.append(cc)
                    except Exception:
                        pass

        def _dedup_keep_order(seq):
            seen = set()
            out_seq = []
            for s in seq:
                k = (s or "").strip()
                if not k:
                    continue
                low = k.lower()
                if low not in seen:
                    seen.add(low)
                    out_seq.append(k)
            return out_seq

        alternative_addresses_list = _dedup_keep_order(alternative_addresses_list)
        alternative_cities_list = _dedup_keep_order(alternative_cities_list)
        alternative_states_list = _dedup_keep_order(alternative_states_list)
        alternative_postal_codes_list = _dedup_keep_order(alternative_postal_codes_list)
        alternative_countries_list = _dedup_keep_order(alternative_countries_list)
        alternative_country_isos_list = _dedup_keep_order(alternative_country_isos_list)

        programs = []
        program_list = sdn.find(f"{ns}programList")
        if program_list is not None:
            for p in program_list.findall(f"{ns}program"):
                if p is not None and p.text and p.text.strip():
                    programs.append(p.text.strip())
        sanctions_program_name_value = "; ".join(programs) if programs else None

        remarks_text = None
        remarks_node = sdn.find(f"{ns}remarks")
        if remarks_node is not None and remarks_node.text and remarks_node.text.strip():
            remarks_text = remarks_node.text.strip()

        target_type_value = None
        sdn_type = sdn.find(f"{ns}sdnType")
        if sdn_type is not None and sdn_type.text and sdn_type.text.strip():
            target_type_value = sdn_type.text.strip()

        emails = []
        websites = []
        phone_numbers = []
        fax_numbers = []
        bic_codes = []
        iban_numbers = []
        ssn_numbers = []
        passport_numbers = []
        national_id_numbers = []
        tax_id_numbers = []
        other_id_numbers = []
        equity_tickers = []
        issuer_names = []
        isin_codes = []
        sanctions_measures = []
        entry_events = []
        relationships = []
        secondary_sanctions_notes = []

        id_list = sdn.find(f"{ns}idList")
        if id_list is not None:
            for idn in id_list.findall(f"{ns}id"):
                t = idn.find(f"{ns}idType")
                v = idn.find(f"{ns}idNumber")
                t_text = t.text.strip() if t is not None and t.text else None
                v_text = v.text.strip() if v is not None and v.text else None
                if not t_text or not v_text:
                    continue
                flat = re.sub(r"[.\s:]+","",t_text.lower())

                if "email" in flat and "@" in v_text:
                    emails.append(v_text)
                elif flat in ("website","web","webaddress","url") or ("http" in v_text.lower() or "." in v_text):
                    if "website" in flat or "http" in v_text.lower():
                        websites.append(v_text)
                elif "telephone" in flat or "phone" in flat:
                    phone_numbers.append(v_text)
                elif "fax" in flat:
                    fax_numbers.append(v_text)
                elif "swift" in flat or "bic" in flat:
                    bic_codes.append(v_text)
                elif "iban" in flat:
                    iban_numbers.append(v_text)
                elif flat.startswith("ssn"):
                    ssn_numbers.append(v_text)
                elif "passport" in flat:
                    passport_numbers.append(v_text)
                elif "nationalid" in flat or "nationalidentification" in flat:
                    national_id_numbers.append(v_text)
                elif flat.startswith("taxid") or "tax" in flat:
                    tax_id_numbers.append(v_text)
                elif "equityticker" in flat or "ticker" in flat:
                    equity_tickers.append(v_text)
                elif "issuername" in flat:
                    issuer_names.append(v_text)
                elif flat == "isin":
                    isin_codes.append(v_text)
                elif t_text.lower().startswith("executive order") or "directive determination" in t_text.lower():
                    sanctions_measures.append(f"{t_text} {v_text}".strip())
                elif t_text.lower().startswith("cmic"):
                    entry_events.append(f"{t_text}: {v_text}")
                elif t_text.lower().startswith("secondary sanctions risk"):
                    secondary_sanctions_notes.append(v_text)
                else:
                    other_id_numbers.append(f"{t_text}: {v_text}")

        links = []
        if remarks_text:
            m = re.search(r"\(Linked To:\s*([^)]+)\)", remarks_text, flags=re.IGNORECASE)
            if m:
                links.append(m.group(1).strip())
        if links:
            relationships.extend(links)

        email_first = emails[0] if emails else None
        website_first = websites[0] if websites else None
        bic_first = bic_codes[0] if bic_codes else None

        record = {
            "list_name": list_name_value,
            "list_id": list_id_value,

            "full_name": full_name_value,
            "first_name": first_name_value,
            "middle_name": middle_name_value,
            "last_name": last_name_value,
            "aliases": aliases if aliases else None,

            "classification": target_type_value,

            "sex": sex_value,
            "birth_year": birth_year_value,
            "birth_month": birth_month_value,
            "birth_day": birth_day_value,
            "place_of_birth_text": place_of_birth_text_value,

            "nationality": nationality_value,
            "citizenship_country": citizenship_value,
            "citizenship_country_iso": citizenship_country_iso_value,

            "address_country": address_country_value,
            "address_country_iso": address_country_iso_value,
            "address_city": address_city_value,
            "address_state": address_state_value,
            "address_postal_code": address_postal_code_value,
            "primary_address_value": primary_address_value,
            "address_details": address_details_value,

            "OFAC_alternative_addresses": alternative_addresses_list or None,
            "OFAC_all_cities": alternative_cities_list or None,
            "OFAC_all_states": alternative_states_list or None,
            "OFAC_all_postal_codes": alternative_postal_codes_list or None,
            "OFAC_all_countries": alternative_countries_list or None,
            "OFAC_all_country_isos": alternative_country_isos_list or None,

            "sanctions_program_name": sanctions_program_name_value,
            "justification_text": remarks_text,
            "publication_date": publication_date_value_global,
            "enactment_date": None,
            "effective_date": None,

            "email_address": email_first,
            "website": website_first,
            "bic": bic_first,

            "OFAC_emails": emails if emails else None,
            "OFAC_websites": websites if websites else None,
            "OFAC_phone_numbers": phone_numbers if phone_numbers else None,
            "OFAC_fax_numbers": fax_numbers if fax_numbers else None,
            "OFAC_bic_codes": bic_codes if bic_codes else None,
            "OFAC_iban_numbers": iban_numbers if iban_numbers else None,
            "OFAC_ssn_numbers": ssn_numbers if ssn_numbers else None,
            "OFAC_passport_numbers": passport_numbers if passport_numbers else None,
            "OFAC_national_id_numbers": national_id_numbers if national_id_numbers else None,
            "OFAC_tax_id_numbers": tax_id_numbers if tax_id_numbers else None,
            "OFAC_other_id_numbers": other_id_numbers if other_id_numbers else None,
            "OFAC_equity_tickers": equity_tickers if equity_tickers else None,
            "OFAC_issuer_names": issuer_names if issuer_names else None,
            "OFAC_isin_codes": isin_codes if isin_codes else None,
            "OFAC_sanctions_measures": sanctions_measures if sanctions_measures else None,
            "OFAC_entry_events": entry_events if entry_events else None,
            "OFAC_relationships": relationships if relationships else None,
            "OFAC_secondary_sanctions_notes": secondary_sanctions_notes if secondary_sanctions_notes else None,
            "OFAC_remarks_raw": remarks_text,
        }
        out.append(record)

    return out
