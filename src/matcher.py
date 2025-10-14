from datetime import datetime, timezone
import unicodedata
import json
import re
from countrycode import country_to_iso2

def matching(party_infos, transaction_info, table_data, ScreeningConfig):
    whitespace_re = re.compile(r"\s+")

    def to_text(value):
        return value if isinstance(value, str) else ("" if value is None else str(value))

    def normalize_basic(value):
        s = to_text(value)
        s = unicodedata.normalize("NFKC", s)
        s = s.casefold().strip()
        cleaned = []
        for ch in s:
            if ch.isalnum() or ch.isspace() or ch in "-'@._":
                cleaned.append(ch)
            else:
                cleaned.append(" ")
        s = "".join(cleaned)
        s = whitespace_re.sub(" ", s).strip()
        return s

    def strip_accents_only(value):
        try:
            return "".join(ch for ch in unicodedata.normalize("NFKD", to_text(value)) if not unicodedata.combining(ch))
        except Exception:
            return to_text(value)

    def collapse_duplicate_tokens(name_string):
        toks = [t for t in to_text(name_string).split() if t]
        if not toks:
            return ""
        if len(toks) % 2 == 0:
            mid = len(toks) // 2
            if toks[:mid] == toks[mid:]:
                return " ".join(toks[:mid])
        dedup = []
        prev = None
        for t in toks:
            if t != prev:
                dedup.append(t)
            prev = t
        return " ".join(dedup)

    def normalize_text(value):
        return normalize_basic(value)

    def normalize_text_without_accents(value):
        return normalize_basic(strip_accents_only(value))

    def bic_normalize(value):
        return unicodedata.normalize("NFKC", to_text(value)).upper().replace(" ", "")

    def iban_normalize(value):
        return unicodedata.normalize("NFKC", to_text(value)).upper().replace(" ", "")

    def to_iso2(value):
        s = to_text(value).strip()
        if not s:
            return ""
        if len(s) == 2 and s.isalpha():
            return s.upper()
        try:
            c = country_to_iso2(s)
            return c.upper() if isinstance(c, str) and len(c) == 2 else ""
        except Exception:
            return ""

    def pick_party_name(party_object):
        if not isinstance(party_object, dict):
            return ""
        for key in ("Name", "name", "FullName", "full_name"):
            if party_object.get(key):
                return to_text(party_object.get(key))
        return ""

    risk_levels_order = ["very high risk", "high risk", "moderate risk", "slight risk"]
    matches_total = 0
    matches_by_risk = {rl: 0 for rl in risk_levels_order}

    def risk_from_score(score_value_0_to_1):
        if score_value_0_to_1 >= 0.90:
            return "very high risk"
        if score_value_0_to_1 >= 0.70:
            return "high risk"
        if score_value_0_to_1 >= 0.25:
            return "moderate risk"
        if score_value_0_to_1 > 0.10:
            return "slight risk"
        return "no risk"

    def normalize_party(party_object):
        if not isinstance(party_object, dict):
            return {
                "name_raw": "", "name": "", "aliases": [],
                "street": "", "town": "", "state": "", "post_code": "", "country": "", "country_iso": "",
                "nationality": "", "citizenship": "", "bic": "", "iban": "", "email": "",
                "date_of_birth": "", "place_of_birth_city": "", "place_of_birth_country": "",
                "id_numbers": []
            }
        name_raw = pick_party_name(party_object)

        aliases_value = party_object.get("Aliases")
        if isinstance(aliases_value, str):
            try:
                aliases_list = json.loads(aliases_value) if aliases_value.strip().startswith(("[", "{")) else [aliases_value]
                if isinstance(aliases_list, dict):
                    aliases_list = list(aliases_list.values())
            except Exception:
                aliases_list = [aliases_value]
        elif isinstance(aliases_value, list):
            aliases_list = aliases_value
        else:
            aliases_list = []

        party_date_of_birth = to_text(
            party_object.get("DateOfBirth")
            or party_object.get("Date Of Birth")
            or party_object.get("DOB")
            or party_object.get("BirthDate")
            or party_object.get("Birth Date")
            or party_object.get("date_of_birth")
            or party_object.get("Date Of Birth")
            or ""
        )

        pob_text = to_text(
            party_object.get("PlaceOfBirthCity")
            or party_object.get("Place Of Birth City")
            or party_object.get("BirthPlaceCity")
            or party_object.get("Birth Place City")
            or party_object.get("place_of_birth_city")
            or party_object.get("PlaceOfBirth")
            or party_object.get("Place Of Birth")
            or ""
        )
        pob_city = pob_text.split(",")[0].strip() if pob_text else ""
        pob_country = pob_text.split(",")[1].strip() if (pob_text and "," in pob_text) else ""

        id_numbers_value = (
            party_object.get("IdNumbers")
            or party_object.get("IDNumbers")
            or party_object.get("Identifiers")
            or party_object.get("identifiers")
            or []
        )
        id_numbers_list = []
        if isinstance(id_numbers_value, str):
            try:
                maybe = json.loads(id_numbers_value) if id_numbers_value.strip().startswith(("[", "{")) else [id_numbers_value]
            except Exception:
                maybe = [id_numbers_value]
            if isinstance(maybe, dict):
                for v in maybe.values():
                    if isinstance(v, list):
                        id_numbers_list.extend([to_text(x) for x in v])
                    else:
                        id_numbers_list.append(to_text(v))
            else:
                id_numbers_list.extend([to_text(x) for x in maybe])
        elif isinstance(id_numbers_value, list):
            id_numbers_list = [to_text(x) for x in id_numbers_value]

        country_text = party_object.get("Country") or ""
        state_text = (
            party_object.get("State")
            or party_object.get("State/Province")
            or party_object.get("Province")
            or party_object.get("Region")
            or party_object.get("CtrySubDvsn")
            or party_object.get("Country Sub Division")
            or ""
        )

        normalized = {
            "name_raw": name_raw,
            "name": normalize_text(collapse_duplicate_tokens(name_raw)),
            "aliases": [normalize_text(collapse_duplicate_tokens(a)) for a in aliases_list if a],
            "street": normalize_text(party_object.get("Street", "")),
            "town": normalize_text(party_object.get("City", "") or party_object.get("Town", "")),
            "state": normalize_text(state_text),
            "post_code": normalize_text(party_object.get("Postal Code", "") or party_object.get("Post Code", "")),
            "country": normalize_text(country_text),
            "country_iso": to_iso2(country_text),
            "nationality": normalize_text(party_object.get("Nationality", "") or party_object.get("Nationality Country", "")),
            "citizenship": normalize_text(party_object.get("Citizenship", "") or party_object.get("Citizenship Country", "")),
            "bic": bic_normalize(party_object.get("BIC", "")),
            "iban": iban_normalize(party_object.get("Iban", "") or party_object.get("IBAN", "")),
            "email": normalize_text(party_object.get("Email", "")),
            "date_of_birth": normalize_text(party_date_of_birth),
            "place_of_birth_city": normalize_text(pob_city),
            "place_of_birth_country": normalize_text(pob_country),
            "id_numbers": [unicodedata.normalize("NFKC", to_text(x)).upper().replace(" ", "") for x in id_numbers_list if to_text(x).strip()],
        }
        return normalized

    def record_fields(record_tuple):
        list_name = record_tuple[0] if len(record_tuple) > 0 else ""
        list_id = record_tuple[1] if len(record_tuple) > 1 else ""
        classification = record_tuple[2] if len(record_tuple) > 2 else ""
        full = record_tuple[3] if len(record_tuple) > 3 else ""
        first = record_tuple[4] if len(record_tuple) > 4 else ""
        middle = record_tuple[5] if len(record_tuple) > 5 else ""
        last = record_tuple[6] if len(record_tuple) > 6 else ""
        other_first = record_tuple[7] if len(record_tuple) > 7 else ""
        nationality_value = record_tuple[8] if len(record_tuple) > 8 else ""
        citizenship_country_value = record_tuple[9] if len(record_tuple) > 9 else ""
        address_primary_value = record_tuple[11] if len(record_tuple) > 11 else ""
        address_city_value = record_tuple[12] if len(record_tuple) > 12 else ""
        address_state_value = record_tuple[13] if len(record_tuple) > 13 else ""
        address_post_value = record_tuple[14] if len(record_tuple) > 14 else ""
        address_country_value = record_tuple[15] if len(record_tuple) > 15 else ""
        address_country_iso_value = record_tuple[16] if len(record_tuple) > 16 else ""
        alt_addresses_value = record_tuple[17] if len(record_tuple) > 17 else ""
        aliases_raw_value = record_tuple[18] if len(record_tuple) > 18 else ""
        justification_col_value = record_tuple[20] if len(record_tuple) > 20 else ""
        other_info_col_value = record_tuple[21] if len(record_tuple) > 21 else ""
        name_raw = ""
        name_candidates = [
            to_text(full).strip(),
            " ".join([to_text(first).strip(), to_text(middle).strip(), to_text(last).strip()]).strip(),
            " ".join([to_text(other_first).strip(), to_text(last).strip()]).strip(),
            " ".join([to_text(last).strip(), to_text(first).strip(), to_text(middle).strip()]).strip(),
            " ".join([to_text(last).strip(), to_text(other_first).strip()]).strip(),
        ]
        for cand in name_candidates:
            if cand:
                name_raw = cand
                break
        if not name_raw:
            parts = [to_text(first).strip(), to_text(middle).strip(), to_text(last).strip(), to_text(other_first).strip()]
            name_raw = " ".join([p for p in parts if p]).strip()
        try:
            aliases_list = json.loads(aliases_raw_value) if isinstance(aliases_raw_value, str) and aliases_raw_value.strip().startswith(("[", "{")) else []
            if isinstance(aliases_list, dict):
                aliases_list = list(aliases_list.values())
        except Exception:
            aliases_list = []
        address_primary = to_text(address_primary_value)
        combined_address = " ".join([x for x in [
            to_text(address_city_value).strip(),
            to_text(address_state_value).strip(),
            to_text(address_post_value).strip(),
            to_text(address_country_value).strip()
        ] if x])
        addresses_list = []
        if address_primary.strip():
            addresses_list.append(address_primary.strip())
        if combined_address.strip() and combined_address.strip() not in addresses_list:
            addresses_list.append(combined_address.strip())
        if isinstance(alt_addresses_value, str) and alt_addresses_value.strip():
            try:
                arr = json.loads(alt_addresses_value)
                if isinstance(arr, list):
                    for a in arr:
                        s = to_text(a).strip()
                        if s and s not in addresses_list:
                            addresses_list.append(s)
            except Exception:
                pass
        record_bics = []
        record_ibans = []
        record_emails = []
        record_date_of_birth = ""
        record_place_of_birth_city = ""
        record_place_of_birth_country = ""
        record_id_numbers = []
        out = {
            "list_name": to_text(list_name),
            "list_id": to_text(list_id),
            "classification": to_text(classification),
            "name_raw": to_text(name_raw),
            "name": normalize_text(collapse_duplicate_tokens(name_raw)),
            "aliases": [normalize_text(collapse_duplicate_tokens(a)) for a in aliases_list],
            "addr_country": normalize_text(address_country_value),
            "addr_country_iso": to_iso2(address_country_iso_value) or to_iso2(address_country_value),
            "addr_city": normalize_text(address_city_value),
            "addr_state": normalize_text(address_state_value),
            "addr_post": normalize_text(address_post_value),
            "addr_street": normalize_text(address_primary),
            "addresses": addresses_list,
            "nationality": normalize_text(nationality_value),
            "citizenship": normalize_text(citizenship_country_value),
            "bics": list({x for x in record_bics if x}),
            "ibans": list({x for x in record_ibans if x}),
            "email": record_emails[0] if record_emails else "",
            "date_of_birth": normalize_text(record_date_of_birth),
            "place_of_birth_city": normalize_text(record_place_of_birth_city),
            "place_of_birth_country": normalize_text(record_place_of_birth_country),
            "id_numbers": list({unicodedata.normalize("NFKC", to_text(x)).upper().replace(" ", "") for x in record_id_numbers if to_text(x).strip()}),
            "justification_text": to_text(justification_col_value),
            "other_information_text": to_text(other_info_col_value),
        }
        return out

    STOP = {"bank","ag","plc","inc","corp","llc","ltd","company","co","group","holding","holdings","national","state","of","the","and","sa","spa","gmbh","s.a.","s.p.a.","s.a.s.","sarl","oy","ab","nv","bv","kg","kgaa"}
    EXCLUDE_ROLES = {}

    def tokens(s):
        raw = [t for t in normalize_text_without_accents(s).split() if t]
        return [t for t in raw if len(t) > 2 and t not in STOP]

    def raw_tokens(s):
        return [t for t in normalize_text_without_accents(s).split() if t]

    def jaccard(a, b):
        sa = set(a); sb = set(b)
        if not sa and not sb:
            return 0.0
        return len(sa & sb) / float(len(sa | sb) or 1.0)

    def matched_fields_struct(labels, extras):
        label_map = {}
        for lab in labels:
            if lab in ("name_exact", "name_strong", "name_partial"):
                key = ("name", "exact" if lab == "name_exact" else ("strong" if lab == "name_strong" else "partial"))
            elif lab in ("alias_strong", "alias_partial", "alias_match"):
                key = ("alias", "strong" if lab == "alias_strong" else ("partial" if lab == "alias_partial" else "match"))
            elif lab in ("country_exact", "country_iso_match"):
                key = ("country", "exact" if lab == "country_exact" else "iso")
            elif lab in ("town_exact", "town_partial"):
                key = ("city", "exact" if lab == "town_exact" else "partial")
            elif lab in ("state_exact", "state_partial"):
                key = ("state", "exact" if lab == "state_exact" else "partial")
            elif lab in ("street_exact", "street_partial"):
                key = ("street", "exact" if lab == "street_exact" else "partial")
            elif lab in ("nationality_overlap",):
                key = ("nationality", "overlap")
            elif lab in ("citizenship_overlap",):
                key = ("citizenship", "overlap")
            elif lab in ("bic_exact",):
                key = ("bic", "exact")
            elif lab in ("iban_exact",):
                key = ("iban", "exact")
            elif lab in ("email_exact", "email_partial"):
                key = ("email", "exact" if lab == "email_exact" else "partial")
            elif lab in ("dob_exact", "dob_year"):
                key = ("date_of_birth", "exact" if lab == "dob_exact" else "year")
            elif lab in ("pob_country", "pob_city_exact", "pob_city_partial"):
                key = ("place_of_birth", "country" if lab == "pob_country" else ("city_exact" if lab == "pob_city_exact" else "city_partial"))
            elif lab in ("id_exact",):
                key = ("id_number", "exact")
            else:
                continue
            if key not in label_map:
                label_map[key] = {"field": key[0], "strength": key[1]}

        # Drop all token payloads from extras (no partyTokens / recordTokens)
        for e in extras:
            f = e.get("field"); st = e.get("strength")
            if not f or not st:
                continue
            key = (f, st)
            if key not in label_map:
                label_map[key] = {"field": f, "strength": st}
        return list(label_map.values())

    def evaluate(party_norm, rec_norm, role, party_name_tokens, record_name_tokens, party_alias_tokens, record_alias_tokens):
        matched = []
        score = 0.0
        extras = []

        if party_norm.get("bic") and rec_norm.get("bics"):
            if party_norm["bic"] in rec_norm["bics"]:
                score += 0.90; matched.append("bic_exact")
                extras.append({"field":"bic","strength":"exact"})

        if party_norm.get("iban") and rec_norm.get("ibans"):
            if party_norm["iban"] in rec_norm["ibans"]:
                score += 0.90; matched.append("iban_exact")
                extras.append({"field":"iban","strength":"exact"})

        if party_norm.get("id_numbers") and rec_norm.get("id_numbers"):
            party_ids = {unicodedata.normalize("NFKC", to_text(x)).upper().replace(" ", "") for x in party_norm["id_numbers"]}
            record_ids = set(rec_norm["id_numbers"])
            inter = sorted(party_ids & record_ids)
            if inter:
                score += 0.90; matched.append("id_exact")
                extras.append({"field":"id_number","strength":"exact"})

        if party_norm.get("date_of_birth") and rec_norm.get("date_of_birth"):
            pd = party_norm["date_of_birth"]; rd = rec_norm["date_of_birth"]
            if len(pd) >= 10 and len(rd) >= 10 and pd[:10] != rd[:10]:
                return None
            py = re.findall(r"\d{4}", pd); ry = re.findall(r"\d{4}", rd)
            if py and ry:
                if py[0] == ry[0]:
                    score += 0.01; matched.append("dob_year")
                    extras.append({"field":"date_of_birth","strength":"year"})
                else:
                    return None
            if len(pd) >= 10 and len(rd) >= 10 and pd[:10] == rd[:10]:
                score += 0.02; matched.append("dob_exact")
                extras.append({"field":"date_of_birth","strength":"exact"})

        if party_norm.get("place_of_birth_country") and rec_norm.get("place_of_birth_country"):
            pbc = normalize_text(party_norm["place_of_birth_country"]); rbc = normalize_text(rec_norm["place_of_birth_country"])
            if pbc == rbc:
                score += 0.01; matched.append("pob_country")
                extras.append({"field":"place_of_birth","strength":"country"})

        if party_norm.get("place_of_birth_city") and rec_norm.get("place_of_birth_city"):
            pn = normalize_text(party_norm["place_of_birth_city"]); rn = normalize_text(rec_norm["place_of_birth_city"])
            if pn == rn:
                score += 0.02; matched.append("pob_city_exact")
                extras.append({"field":"place_of_birth","strength":"city_exact"})
            elif pn in rn or rn in pn:
                score += 0.02; matched.append("pob_city_partial")
                extras.append({"field":"place_of_birth","strength":"city_partial"})

        name_j = jaccard(party_name_tokens, record_name_tokens)
        name_points = 0.0
        if   name_j >= 0.95:
            matched.append("name_exact"); name_points = 0.85
        elif name_j >= 0.80:
            matched.append("name_strong"); name_points = 0.75 * name_j
        elif name_j >= 0.60:
            matched.append("name_partial"); name_points = 0.75 * name_j
        if any(lab in matched for lab in ("name_exact","name_strong","name_partial")):
            extras.append({"field":"name","strength":("exact" if "name_exact" in matched else ("strong" if "name_strong" in matched else "partial"))})

        def _first_last(tokens_):
            return (tokens_[0], tokens_[-1]) if len(tokens_) >= 2 else (None, None)
        p_fl = _first_last(party_name_tokens)
        r_fl = _first_last(record_name_tokens)
        first_last_match = (p_fl[0] and r_fl[0] and p_fl[0] == r_fl[0] and p_fl[1] == r_fl[1])
        subset_match = (len(party_name_tokens) >= 2 and set(party_name_tokens).issubset(set(record_name_tokens)))
        if first_last_match or subset_match:
            name_points = max(name_points, 0.55 if name_points == 0.0 else name_points)
        score += name_points

        if party_alias_tokens and record_alias_tokens:
            best_alias = 0.0
            for pt in party_alias_tokens:
                for rt in record_alias_tokens:
                    val = jaccard(pt, rt)
                    if val > best_alias:
                        best_alias = val
            if   best_alias >= 0.8:
                score += 0.50; matched.append("alias_strong")
                extras.append({"field":"alias","strength":"strong"})
            elif best_alias >= 0.6:
                score += 0.25; matched.append("alias_partial")
                extras.append({"field":"alias","strength":"partial"})
            elif best_alias >  0.0:
                score += 0.10; matched.append("alias_match")
                extras.append({"field":"alias","strength":"match"})

        country_exact_bool = bool(party_norm["country"] and rec_norm["addr_country"] and party_norm["country"] == rec_norm["addr_country"])
        iso_match_bool = bool(party_norm.get("country_iso") and rec_norm.get("addr_country_iso") and party_norm["country_iso"] == rec_norm["addr_country_iso"])
        if country_exact_bool:
            score += 0.03; matched.append("country_exact")
            extras.append({"field":"country","strength":"exact"})
        elif iso_match_bool:
            score += 0.03; matched.append("country_iso_match")
            extras.append({"field":"country","strength":"iso"})

        if party_norm["town"] and (rec_norm["addr_city"] or rec_norm["addr_state"]):
            if party_norm["town"] == rec_norm["addr_city"]:
                score += 0.04; matched.append("town_exact")
                extras.append({"field":"city","strength":"exact"})
            elif party_norm["town"] in rec_norm["addr_city"] or party_norm["town"] in rec_norm["addr_state"]:
                score += 0.02; matched.append("town_partial")
                extras.append({"field":"city","strength":"partial"})

        if party_norm.get("state") and (rec_norm.get("addr_state") or rec_norm.get("addr_city")):
            if party_norm["state"] == rec_norm.get("addr_state"):
                score += 0.03; matched.append("state_exact")
                extras.append({"field":"state","strength":"exact"})
            elif (rec_norm.get("addr_state") and party_norm["state"] in rec_norm["addr_state"]) or \
                 (rec_norm.get("addr_city")  and party_norm["state"] in rec_norm["addr_city"]):
                score += 0.01; matched.append("state_partial")
                extras.append({"field":"state","strength":"partial"})

        # Street similarity with threshold and scaled partial
        if party_norm.get("street"):
            party_street_tokens = tokens(party_norm["street"])
            rec_street = rec_norm.get("addr_street") or ""
            best_sim = 0.0
            matched_exact = False

            def _sim_with(addr_text):
                party = set(party_street_tokens)
                rec = set(tokens(addr_text))
                if not party and not rec:
                    return 0.0
                return len(party & rec) / float(len(party | rec) or 1.0)

            if rec_street:
                if party_norm["street"] == rec_street:
                    matched_exact = True
                else:
                    best_sim = _sim_with(rec_street)
            else:
                for addr in (rec_norm.get("addresses") or []):
                    addr_norm = normalize_text(addr)
                    if not addr_norm:
                        continue
                    if party_norm["street"] == addr_norm:
                        matched_exact = True
                        break
                    best_sim = max(best_sim, _sim_with(addr_norm))

            if matched_exact:
                score += 0.40; matched.append("street_exact")
                extras.append({"field":"street","strength":"exact"})
            elif best_sim > 0.60:
                score += 0.30 * best_sim; matched.append("street_partial")
                extras.append({"field":"street","strength":"partial"})

        if party_norm.get("email") and rec_norm.get("email"):
            party_email = party_norm["email"]
            record_email = rec_norm["email"]
            if party_email == record_email:
                score += 0.90; matched.append("email_exact")
                extras.append({"field":"email","strength":"exact"})
            else:
                if "@" in party_email and "@" in record_email:
                    party_local, party_domain = party_email.split("@", 1)
                    record_local, record_domain = record_email.split("@", 1)
                    if party_domain == record_domain:
                        if party_local == record_local or party_local in record_local or record_local in party_local:
                            if abs(len(party_local) - len(record_local)) <= 2:
                                score += 0.30; matched.append("email_partial")
                                extras.append({"field":"email","strength":"partial"})

        if not matched and score > 0:
            if name_points > 0:
                matched.append("name_partial")
                extras.append({"field":"name","strength":"partial"})

        score = min(1.0, score)
        final_score_int = min(100, int(round(score * 100)))
        risk_value = risk_from_score(score)
        return {
            "partyName": party_norm.get("name_raw", ""),
            "role": role,
            "sanctionsName": rec_norm.get("name_raw", ""),
            "sanctionsAliases": rec_norm.get("aliases", []),
            "sanctionsList": rec_norm.get("list_name", ""),
            "sanctionsId": rec_norm.get("list_id", ""),
            "riskLevel": risk_value,
            "finalScore": final_score_int,
            "matchedFields": matched_fields_struct(matched, extras),
            "matchSummary": (rec_norm.get("justification_text", "") + " " + rec_norm.get("other_information_text", "")).strip()
        }

    sanctions_cache = {}
    all_matches = []
    shown_matches = []
    show_slight = False
    if isinstance(ScreeningConfig, dict):
        show_slight = bool(ScreeningConfig.get("SHOW_SLIGHT_MATCHES"))
    else:
        show_slight = bool(getattr(ScreeningConfig, "SHOW_SLIGHT_MATCHES", False))
    for item in (party_infos or []):
        if not isinstance(item, dict):
            continue
        role_value = item.get("Role") or ""
        role_norm = normalize_text(role_value)
        if any(k in role_norm for k in EXCLUDE_ROLES):
            continue
        party_object = item
        index = item.get("index") or item.get("i") or item.get("idx") or ""

        party_norm = normalize_party(party_object)
        party_name_tokens = tokens(party_norm["name"])
        party_alias_tokens = [tokens(a) for a in (party_norm["aliases"] or [])]

        best_by_record = {}
        for record_tuple in (table_data or []):
            rec_key = (
                record_tuple[0] if len(record_tuple) > 0 else "",
                record_tuple[1] if len(record_tuple) > 1 else "",
            )
            if rec_key in sanctions_cache:
                cached = sanctions_cache[rec_key]
                rec_norm = cached["norm"]
                record_name_tokens = cached["name_tokens"]
                record_alias_tokens = cached["alias_tokens"]
            else:
                rec_norm = record_fields(record_tuple)
                record_name_tokens = tokens(rec_norm["name"])
                record_alias_tokens = [tokens(a) for a in rec_norm["aliases"]]
                sanctions_cache[rec_key] = {
                    "norm": rec_norm,
                    "name_tokens": record_name_tokens,
                    "alias_tokens": record_alias_tokens,
                }

            match_obj = evaluate(
                party_norm, rec_norm, role_value,
                party_name_tokens, record_name_tokens,
                party_alias_tokens, record_alias_tokens
            )
            if match_obj is None:
                matches_total += 1
                matches_by_risk["no risk"] += 1
                continue
            rl = risk_from_score((match_obj.get("finalScore", 0) or 0) / 100.0)
            matches_total += 1
            matches_by_risk[rl] = matches_by_risk.get(rl, 0) + 1
            if rl == "no risk":
                continue
            key = (match_obj["sanctionsList"], match_obj["sanctionsId"], role_value, index)
            if key not in best_by_record or match_obj.get("finalScore", 0) > best_by_record[key].get("finalScore", 0):
                best_by_record[key] = match_obj
        if best_by_record:
            for m in best_by_record.values():
                all_matches.append(m)
                if show_slight or (m.get("riskLevel", "").lower() not in {"slight risk"}):
                    shown_matches.append(m)

    def _dedup(lst):
        ded = {}
        for m in lst:
            key = (
                normalize_text(collapse_duplicate_tokens(m.get("partyName", ""))),
                m.get("sanctionsList"),
                m.get("sanctionsId"),
            )
            if key not in ded or int(m.get("finalScore", 0)) > int(ded[key].get("finalScore", 0)):
                ded[key] = m
        return list(ded.values())

    all_matches = _dedup(all_matches)
    shown_matches = _dedup(shown_matches)

    match_counts = {"total": matches_total, "byRiskLevel": matches_by_risk}

    top_score_points = max((int(m.get("finalScore", 0)) for m in all_matches), default=0)

    groups = {}
    for m in all_matches:
        pname = normalize_text(collapse_duplicate_tokens(m.get("partyName", "")))
        groups.setdefault(pname, []).append(m)
    risk_score_points = 0
    for pname, group in groups.items():
        base = max(int(g.get("finalScore", 0)) for g in group)
        qualifying_levels = {"moderate risk", "high risk", "very high risk"}
        qualifying_lists = {
            g.get("sanctionsList")
            for g in group
            if (g.get("sanctionsList") and (g.get("riskLevel") or "").lower() in qualifying_levels)
        }
        distinct_lists = len(qualifying_lists)
        bonus_points = 0 * distinct_lists
        agg = min(100, base + bonus_points)
        if agg > risk_score_points:
            risk_score_points = agg
    if not groups:
        risk_score_points = 0

    top_risk_level = risk_from_score(top_score_points / 100.0) if all_matches else "no risk"
    overall_risk_level = risk_from_score(risk_score_points / 100.0) if all_matches else "no risk"
    flagged = overall_risk_level in ("very high risk", "high risk", "moderate risk")
    rc_map = {
        "very high risk": "VERY_HIGH_RISK",
        "high risk": "HIGH_RISK",
        "moderate risk": "MODERATE_RISK",
        "slight risk": "SLIGHT_RISK",
        "no risk": "NONE",
    }
    response_code_value = f"{rc_map.get(overall_risk_level, 'UNKNOWN')}"
    return {
        "flagged": flagged,
        "matches": shown_matches,
        "topRiskLevel": top_risk_level,
        "topScore": top_score_points,
        "riskScore": min(100, risk_score_points),
        "riskLevel": overall_risk_level,
        "responseCode": response_code_value,
        "matchCounts": match_counts,
        "timeflagged": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
