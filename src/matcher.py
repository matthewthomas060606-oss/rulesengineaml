from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from countrycode import country_to_iso2


WHITESPACE_RE = re.compile(r"\s+")
ALLOWED_PUNCT = {"-", "'", "@", ".", "_"}
STOP_WORDS = {
    # "bank",
    # "ag",
    # "plc",
    # "inc",
    # "corp",
    # "llc",
    # "ltd",
    # "company",
    # "co",
    # "group",
    # "holding",
    # "holdings",
    # "national",
    # "state",
    "of",
    "the",
    "and",
    # "sa",
    # "spa",
    # "gmbh",
    # "s.a.",
    # "s.p.a.",
    # "s.a.s.",
    # "sarl",
    # "oy",
    # "ab",
    # "nv",
    # "bv",
    # "kg",
    # "kgaa",
}
RISK_LEVELS = ("very high risk", "high risk", "moderate risk", "slight risk")
EXCLUDE_ROLES: Tuple[str, ...] = ()


def to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def _normalize_basic(value: Any) -> str:
    text = to_text(value)
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text).casefold()
    cleaned = [
        ch if (ch.isalnum() or ch.isspace() or ch in ALLOWED_PUNCT) else " "
        for ch in text
    ]
    normalized = "".join(cleaned)
    return WHITESPACE_RE.sub(" ", normalized).strip()


def strip_accents(value: Any) -> str:
    try:
        return "".join(
            ch for ch in unicodedata.normalize("NFKD", to_text(value)) if not unicodedata.combining(ch)
        )
    except Exception:
        return to_text(value)


def normalize_text(value: Any) -> str:
    return _normalize_basic(value)


def normalize_text_without_accents(value: Any) -> str:
    return _normalize_basic(strip_accents(value))


def collapse_duplicate_tokens(name_string: Any) -> str:
    tokens = [t for t in to_text(name_string).split() if t]
    if not tokens:
        return ""
    if len(tokens) % 2 == 0:
        midpoint = len(tokens) // 2
        if tokens[:midpoint] == tokens[midpoint:]:
            return " ".join(tokens[:midpoint])
    deduped: List[str] = []
    previous = None
    for token in tokens:
        if token != previous:
            deduped.append(token)
        previous = token
    return " ".join(deduped)


def tokenize(value: Any) -> List[str]:
    return [t for t in normalize_text_without_accents(value).split() if len(t) > 2 and t not in STOP_WORDS]


def raw_tokens(value: Any) -> List[str]:
    return [t for t in normalize_text_without_accents(value).split() if t]


def _parse_jsonish(value: Any) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith(("[", "{")):
            try:
                data = json.loads(stripped)
            except Exception:
                return [stripped]
            if isinstance(data, dict):
                return [v for v in data.values() if v is not None]
            if isinstance(data, list):
                return [v for v in data if v is not None]
            return [data]
        return [stripped]
    return []


def _coalesce(*values: Any) -> str:
    for value in values:
        text = to_text(value).strip()
        if text:
            return text
    return ""


def _split_place_of_birth(value: str) -> Tuple[str, str]:
    if not value:
        return "", ""
    if "," in value:
        city, country = value.split(",", 1)
        return city.strip(), country.strip()
    return value.strip(), ""


def _to_iso2(value: Any) -> str:
    text = to_text(value).strip()
    if not text:
        return ""
    if len(text) == 2 and text.isalpha():
        return text.upper()
    try:
        code = country_to_iso2(text)
    except Exception:
        return ""
    return code.upper() if isinstance(code, str) and len(code) == 2 else ""


def _normalize_id_numbers(values: Iterable[Any]) -> List[str]:
    normalized: List[str] = []
    for value in values or []:
        text = unicodedata.normalize("NFKC", to_text(value)).upper().replace(" ", "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def normalize_party(party_object: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(party_object, dict):
        return {
            "name_raw": "",
            "name": "",
            "aliases": [],
            "street": "",
            "town": "",
            "state": "",
            "post_code": "",
            "country": "",
            "country_iso": "",
            "nationality": "",
            "citizenship": "",
            "bic": "",
            "iban": "",
            "email": "",
            "date_of_birth": "",
            "place_of_birth_city": "",
            "place_of_birth_country": "",
            "id_numbers": [],
        }

    name_candidates = [
        party_object.get(key, "")
        for key in ("Name", "name", "FullName", "full_name")
    ]
    name_raw = _coalesce(*name_candidates)

    alias_values = []
    for key in ("Aliases", "aliases", "Alias", "alias"):
        alias_values = _parse_jsonish(party_object.get(key))
        if alias_values:
            break

    dob_value = _coalesce(
        party_object.get("DateOfBirth"),
        party_object.get("Date Of Birth"),
        party_object.get("DOB"),
        party_object.get("BirthDate"),
        party_object.get("Birth Date"),
        party_object.get("date_of_birth"),
    )

    pob_value = _coalesce(
        party_object.get("PlaceOfBirthCity"),
        party_object.get("Place Of Birth City"),
        party_object.get("BirthPlaceCity"),
        party_object.get("Birth Place City"),
        party_object.get("place_of_birth_city"),
        party_object.get("PlaceOfBirth"),
        party_object.get("Place Of Birth"),
    )
    pob_city, pob_country = _split_place_of_birth(to_text(pob_value))

    id_sources: List[Any] = []
    for key in ("IdNumbers", "IDNumbers", "Identifiers", "identifiers", "id_numbers"):
        value = party_object.get(key)
        if value:
            id_sources.extend(_parse_jsonish(value))
    id_numbers = _normalize_id_numbers(id_sources)

    country_text = _coalesce(
        party_object.get("Country"),
        party_object.get("CountryName"),
    )
    state_text = _coalesce(
        party_object.get("State"),
        party_object.get("State/Province"),
        party_object.get("Province"),
        party_object.get("Region"),
        party_object.get("CtrySubDvsn"),
        party_object.get("Country Sub Division"),
    )

    normalized = {
        "name_raw": name_raw,
        "name": normalize_text(collapse_duplicate_tokens(name_raw)),
        "aliases": [normalize_text(collapse_duplicate_tokens(a)) for a in alias_values if a],
        "street": normalize_text(party_object.get("Street", "")),
        "town": normalize_text(_coalesce(party_object.get("City"), party_object.get("Town"))),
        "state": normalize_text(state_text),
        "post_code": normalize_text(_coalesce(party_object.get("Postal Code"), party_object.get("Post Code"))),
        "country": normalize_text(country_text),
        "country_iso": _to_iso2(
            _coalesce(party_object.get("CountryIso"), party_object.get("Country ISO"), party_object.get("CountryCode"), country_text)
        ),
        "nationality": normalize_text(_coalesce(party_object.get("Nationality"), party_object.get("Nationality Country"))),
        "citizenship": normalize_text(_coalesce(party_object.get("Citizenship"), party_object.get("Citizenship Country"))),
        "bic": unicodedata.normalize("NFKC", to_text(party_object.get("BIC", ""))).upper().replace(" ", ""),
        "iban": unicodedata.normalize("NFKC", to_text(_coalesce(party_object.get("Iban"), party_object.get("IBAN")))).upper().replace(" ", ""),
        "email": normalize_text(party_object.get("Email", "")),
        "date_of_birth": normalize_text(dob_value),
        "place_of_birth_city": normalize_text(pob_city),
        "place_of_birth_country": normalize_text(pob_country),
        "id_numbers": id_numbers,
    }
    return normalized


def normalize_record(record_tuple: Sequence[Any]) -> Dict[str, Any]:
    def get(index: int, default: Any = "") -> Any:
        try:
            return record_tuple[index]
        except IndexError:
            return default

    list_name = to_text(get(0))
    list_id = to_text(get(1))
    classification = to_text(get(2))
    full = to_text(get(3))
    first = to_text(get(4))
    middle = to_text(get(5))
    last = to_text(get(6))
    other_first = to_text(get(7))
    nationality_value = get(8)
    citizenship_value = get(9)
    citizenship_iso_value = get(10)
    street_value = get(11)
    city_value = get(12)
    state_value = get(13)
    post_value = get(14)
    country_value = get(15)
    country_iso_value = get(16)
    alt_addresses_value = get(17)
    aliases_value = get(18)
    global_id_value = get(19)
    justification_value = get(20)
    other_info_value = get(21)

    name_candidates = [full.strip(), f"{first} {middle} {last}".strip(), f"{other_first} {last}".strip(), f"{last} {first} {middle}".strip(), f"{last} {other_first}".strip()]
    name_raw = next((candidate for candidate in name_candidates if candidate), "")
    if not name_raw:
        parts = [first.strip(), middle.strip(), last.strip(), other_first.strip()]
        name_raw = " ".join([p for p in parts if p]).strip()

    aliases_list = _parse_jsonish(aliases_value)
    alt_addresses = _parse_jsonish(alt_addresses_value)

    addresses: List[str] = []
    primary = to_text(street_value).strip()
    if primary:
        addresses.append(primary)
    combined_address = " ".join(
        [
            to_text(city_value).strip(),
            to_text(state_value).strip(),
            to_text(post_value).strip(),
            to_text(country_value).strip(),
        ]
    ).strip()
    if combined_address and combined_address not in addresses:
        addresses.append(combined_address)
    for address in alt_addresses:
        text = to_text(address).strip()
        if text and text not in addresses:
            addresses.append(text)

    id_numbers = _normalize_id_numbers(_parse_jsonish(global_id_value))

    normalized = {
        "list_name": list_name,
        "list_id": list_id,
        "classification": classification,
        "name_raw": name_raw,
        "name": normalize_text(collapse_duplicate_tokens(name_raw)),
        "aliases": [normalize_text(collapse_duplicate_tokens(alias)) for alias in aliases_list if alias],
        "addr_country": normalize_text(country_value),
        "addr_country_iso": _to_iso2(country_iso_value or country_value),
        "addr_city": normalize_text(city_value),
        "addr_state": normalize_text(state_value),
        "addr_post": normalize_text(post_value),
        "addr_street": normalize_text(primary),
        "addresses": [normalize_text(addr) for addr in addresses if addr],
        "nationality": normalize_text(nationality_value),
        "citizenship": normalize_text(citizenship_value),
        "citizenship_iso": _to_iso2(citizenship_iso_value),
        "bics": [],
        "ibans": [],
        "email": "",
        "date_of_birth": "",
        "place_of_birth_city": "",
        "place_of_birth_country": "",
        "id_numbers": id_numbers,
        "justification_text": to_text(justification_value),
        "other_information_text": to_text(other_info_value),
    }
    return normalized


def risk_from_score(score_value: float) -> str:
    if score_value >= 0.90:
        return "very high risk"
    if score_value >= 0.70:
        return "high risk"
    if score_value >= 0.25:
        return "moderate risk"
    if score_value > 0.10:
        return "slight risk"
    return "no risk"


def matched_fields_struct(labels: Iterable[str], extras: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    label_map: Dict[Tuple[str, str], Dict[str, str]] = {}
    for label in labels:
        if label in {"name_exact", "name_strong", "name_partial"}:
            key = ("name", "exact" if label == "name_exact" else ("strong" if label == "name_strong" else "partial"))
        elif label in {"alias_strong", "alias_partial", "alias_match"}:
            key = ("alias", "strong" if label == "alias_strong" else ("partial" if label == "alias_partial" else "match"))
        elif label in {"country_exact", "country_iso_match"}:
            key = ("country", "exact" if label == "country_exact" else "iso")
        elif label in {"town_exact", "town_partial"}:
            key = ("city", "exact" if label == "town_exact" else "partial")
        elif label in {"state_exact", "state_partial"}:
            key = ("state", "exact" if label == "state_exact" else "partial")
        elif label in {"street_exact", "street_partial"}:
            key = ("street", "exact" if label == "street_exact" else "partial")
        elif label == "nationality_overlap":
            key = ("nationality", "overlap")
        elif label == "citizenship_overlap":
            key = ("citizenship", "overlap")
        elif label == "bic_exact":
            key = ("bic", "exact")
        elif label == "iban_exact":
            key = ("iban", "exact")
        elif label in {"email_exact", "email_partial"}:
            key = ("email", "exact" if label == "email_exact" else "partial")
        elif label in {"dob_exact", "dob_year"}:
            key = ("date_of_birth", "exact" if label == "dob_exact" else "year")
        elif label in {"pob_country", "pob_city_exact", "pob_city_partial"}:
            key = ("place_of_birth", "country" if label == "pob_country" else ("city_exact" if label == "pob_city_exact" else "city_partial"))
        elif label == "id_exact":
            key = ("id_number", "exact")
        else:
            continue
        label_map.setdefault(key, {"field": key[0], "strength": key[1]})

    for extra in extras:
        field = extra.get("field")
        strength = extra.get("strength")
        if not field or not strength:
            continue
        key = (field, strength)
        label_map.setdefault(key, {"field": field, "strength": strength})

    return list(label_map.values())


def _best_alias_score(party_alias_tokens: List[List[str]], record_alias_tokens: List[List[str]]) -> float:
    best = 0.0
    for party_tokens in party_alias_tokens:
        for record_tokens in record_alias_tokens:
            if not party_tokens and not record_tokens:
                continue
            union = set(party_tokens) | set(record_tokens)
            if not union:
                continue
            score = len(set(party_tokens) & set(record_tokens)) / float(len(union))
            if score > best:
                best = score
    return best


def _street_similarity(party_street_tokens: List[str], record_text: str) -> float:
    if not party_street_tokens:
        return 0.0
    party_set = set(party_street_tokens)
    record_set = set(tokenize(record_text))
    if not record_set and not party_set:
        return 0.0
    union = party_set | record_set
    if not union:
        return 0.0
    return len(party_set & record_set) / float(len(union))


def evaluate_match(
    party_norm: Dict[str, Any],
    rec_norm: Dict[str, Any],
    role: str,
    party_name_tokens: List[str],
    record_name_tokens: List[str],
    party_alias_tokens: List[List[str]],
    record_alias_tokens: List[List[str]],
) -> Dict[str, Any] | None:
    matched: List[str] = []
    extras: List[Dict[str, str]] = []
    score = 0.0

    party_bic = party_norm.get("bic")
    if party_bic and party_bic in (rec_norm.get("bics") or []):
        score += 0.90
        matched.append("bic_exact")
        extras.append({"field": "bic", "strength": "exact"})

    party_iban = party_norm.get("iban")
    if party_iban and party_iban in (rec_norm.get("ibans") or []):
        score += 0.90
        matched.append("iban_exact")
        extras.append({"field": "iban", "strength": "exact"})

    party_ids = set(party_norm.get("id_numbers") or [])
    record_ids = set(rec_norm.get("id_numbers") or [])
    if party_ids and record_ids:
        if party_ids & record_ids:
            score += 0.90
            matched.append("id_exact")
            extras.append({"field": "id_number", "strength": "exact"})

    party_dob = party_norm.get("date_of_birth", "")
    record_dob = rec_norm.get("date_of_birth", "")
    if party_dob and record_dob:
        party_years = re.findall(r"\d{4}", party_dob)
        record_years = re.findall(r"\d{4}", record_dob)
        if party_years and record_years and party_years[0] != record_years[0]:
            return None
        if len(party_dob) >= 10 and len(record_dob) >= 10:
            if party_dob[:10] != record_dob[:10]:
                return None
            score += 0.02
            matched.append("dob_exact")
            extras.append({"field": "date_of_birth", "strength": "exact"})
        elif party_years and record_years and party_years[0] == record_years[0]:
            score += 0.01
            matched.append("dob_year")
            extras.append({"field": "date_of_birth", "strength": "year"})

    party_pob_country = party_norm.get("place_of_birth_country")
    record_pob_country = rec_norm.get("place_of_birth_country")
    if party_pob_country and record_pob_country and party_pob_country == record_pob_country:
        score += 0.01
        matched.append("pob_country")
        extras.append({"field": "place_of_birth", "strength": "country"})

    party_pob_city = party_norm.get("place_of_birth_city")
    record_pob_city = rec_norm.get("place_of_birth_city")
    if party_pob_city and record_pob_city:
        if party_pob_city == record_pob_city:
            score += 0.02
            matched.append("pob_city_exact")
            extras.append({"field": "place_of_birth", "strength": "city_exact"})
        elif party_pob_city in record_pob_city or record_pob_city in party_pob_city:
            score += 0.02
            matched.append("pob_city_partial")
            extras.append({"field": "place_of_birth", "strength": "city_partial"})

    name_tokens_party = party_name_tokens
    name_tokens_record = record_name_tokens
    intersection = set(name_tokens_party) & set(name_tokens_record)
    union = set(name_tokens_party) | set(name_tokens_record)
    name_jaccard = (len(intersection) / float(len(union))) if union else 0.0

    name_points = 0.0
    if name_jaccard >= 0.95:
        matched.append("name_exact")
        name_points = 0.85
    elif name_jaccard >= 0.70:
        matched.append("name_strong")
        name_points = 0.85 * name_jaccard
    elif name_jaccard >= 0.40:
        matched.append("name_partial")
        name_points = 0.85 * name_jaccard

    if matched and any(label.startswith("name_") for label in matched):
        extras.append(
            {
                "field": "name",
                "strength": "exact" if "name_exact" in matched else ("strong" if "name_strong" in matched else "partial"),
            }
        )

    if len(name_tokens_party) >= 2:
        party_first, party_last = name_tokens_party[0], name_tokens_party[-1]
        record_first = record_last = None
        if len(name_tokens_record) >= 2:
            record_first, record_last = name_tokens_record[0], name_tokens_record[-1]
        first_last_match = bool(record_first and record_last and party_first == record_first and party_last == record_last)
        subset_match = set(name_tokens_party).issubset(set(name_tokens_record))
        if first_last_match or subset_match:
            name_points = max(name_points, 0.55 if name_points == 0.0 else name_points)

    score += name_points

    if party_alias_tokens and record_alias_tokens:
        alias_score = _best_alias_score(party_alias_tokens, record_alias_tokens)
        if alias_score >= 0.70:
            score += 0.40
            matched.append("alias_strong")
            extras.append({"field": "alias", "strength": "strong"})
        elif alias_score >= 0.30:
            score += 0.25
            matched.append("alias_partial")
            extras.append({"field": "alias", "strength": "partial"})
        elif alias_score > 0.0:
            score += 0.10
            matched.append("alias_match")
            extras.append({"field": "alias", "strength": "match"})

    party_country = party_norm.get("country")
    record_country = rec_norm.get("addr_country")
    party_country_iso = party_norm.get("country_iso")
    record_country_iso = rec_norm.get("addr_country_iso")
    if party_country and record_country and party_country == record_country:
        score += 0.03
        matched.append("country_exact")
        extras.append({"field": "country", "strength": "exact"})
    elif party_country_iso and record_country_iso and party_country_iso == record_country_iso:
        score += 0.03
        matched.append("country_iso_match")
        extras.append({"field": "country", "strength": "iso"})

    party_town = party_norm.get("town")
    record_city = rec_norm.get("addr_city")
    record_state = rec_norm.get("addr_state")
    if party_town and (record_city or record_state):
        if party_town and party_town == record_city:
            score += 0.04
            matched.append("town_exact")
            extras.append({"field": "city", "strength": "exact"})
        elif (record_city and party_town in record_city) or (record_state and party_town in record_state):
            score += 0.02
            matched.append("town_partial")
            extras.append({"field": "city", "strength": "partial"})

    party_state = party_norm.get("state")
    if party_state and (record_state or record_city):
        if party_state == record_state:
            score += 0.03
            matched.append("state_exact")
            extras.append({"field": "state", "strength": "exact"})
        elif (record_state and party_state in record_state) or (record_city and party_state in record_city):
            score += 0.01
            matched.append("state_partial")
            extras.append({"field": "state", "strength": "partial"})

    party_street = party_norm.get("street")
    if party_street:
        party_street_tokens = tokenize(party_street)
        record_street = rec_norm.get("addr_street") or ""
        matched_exact = bool(party_street and record_street and party_street == record_street)
        best_similarity = 0.0
        if not matched_exact:
            if record_street:
                best_similarity = _street_similarity(party_street_tokens, record_street)
            for addr in rec_norm.get("addresses") or []:
                if party_street == addr:
                    matched_exact = True
                    break
                best_similarity = max(best_similarity, _street_similarity(party_street_tokens, addr))
        if matched_exact:
            score += 0.40
            matched.append("street_exact")
            extras.append({"field": "street", "strength": "exact"})
        elif best_similarity > 0.60:
            score += 0.30 * best_similarity
            matched.append("street_partial")
            extras.append({"field": "street", "strength": "partial"})

    party_email = party_norm.get("email")
    record_email = rec_norm.get("email")
    if party_email and record_email:
        if party_email == record_email:
            score += 0.90
            matched.append("email_exact")
            extras.append({"field": "email", "strength": "exact"})
        elif "@" in party_email and "@" in record_email:
            party_local, party_domain = party_email.split("@", 1)
            record_local, record_domain = record_email.split("@", 1)
            if party_domain == record_domain:
                if party_local == record_local or party_local in record_local or record_local in party_local:
                    if abs(len(party_local) - len(record_local)) <= 2:
                        score += 0.30
                        matched.append("email_partial")
                        extras.append({"field": "email", "strength": "partial"})

    if not matched and score > 0 and name_points == 0.0:
        matched.append("name_partial")
        extras.append({"field": "name", "strength": "partial"})

    score = min(1.0, score)
    final_score = min(100, int(round(score * 100)))
    risk_value = risk_from_score(score)
    return {
        "partyName": party_norm.get("name_raw", ""),
        "role": role,
        "sanctionsName": rec_norm.get("name_raw", ""),
        "sanctionsAliases": rec_norm.get("aliases", []),
        "sanctionsList": rec_norm.get("list_name", ""),
        "sanctionsId": rec_norm.get("list_id", ""),
        "riskLevel": risk_value,
        "finalScore": final_score,
        "matchedFields": matched_fields_struct(matched, extras),
        "matchSummary": (rec_norm.get("justification_text", "") + " " + rec_norm.get("other_information_text", "")).strip(),
    }


def _dedup(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for match in matches:
        key = (
            normalize_text(collapse_duplicate_tokens(match.get("partyName", ""))),
            match.get("sanctionsList"),
            match.get("sanctionsId"),
        )
        existing = deduped.get(key)
        if not existing or int(match.get("finalScore", 0)) > int(existing.get("finalScore", 0)):
            deduped[key] = match
    return list(deduped.values())


def matching(party_infos, transaction_info, table_data, ScreeningConfig):
    matches_total = 0
    matches_by_risk = {level: 0 for level in RISK_LEVELS}
    matches_by_risk["no risk"] = 0
    sanctions_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
    all_matches: List[Dict[str, Any]] = []
    shown_matches: List[Dict[str, Any]] = []

    if isinstance(ScreeningConfig, dict):
        show_slight = bool(ScreeningConfig.get("SHOW_SLIGHT_MATCHES"))
    else:
        show_slight = bool(getattr(ScreeningConfig, "SHOW_SLIGHT_MATCHES", False))

    for party in party_infos or []:
        if not isinstance(party, dict):
            continue
        role_value = to_text(party.get("Role") or "")
        role_norm = normalize_text(role_value)
        if any(stop_role in role_norm for stop_role in EXCLUDE_ROLES):
            continue
        index = party.get("index") or party.get("i") or party.get("idx") or ""
        party_norm = normalize_party(party)
        name_tokens = tokenize(party_norm.get("name", ""))
        alias_tokens = [tokenize(alias) for alias in party_norm.get("aliases", [])]

        best_by_record: Dict[Tuple[str, str, str, Any], Dict[str, Any]] = {}
        for record in table_data or []:
            record_key = (to_text(record[0]) if len(record) > 0 else "", to_text(record[1]) if len(record) > 1 else "")
            cached = sanctions_cache.get(record_key)
            if cached is None:
                rec_norm = normalize_record(record)
                cache_entry = {
                    "norm": rec_norm,
                    "name_tokens": tokenize(rec_norm.get("name", "")),
                    "alias_tokens": [tokenize(alias) for alias in rec_norm.get("aliases", [])],
                }
                sanctions_cache[record_key] = cache_entry
            else:
                rec_norm = cached["norm"]
            cache_tokens = sanctions_cache[record_key]
            match_obj = evaluate_match(
                party_norm,
                rec_norm,
                role_value,
                name_tokens,
                cache_tokens["name_tokens"],
                alias_tokens,
                cache_tokens["alias_tokens"],
            )
            if match_obj is None:
                matches_total += 1
                matches_by_risk["no risk"] += 1
                continue
            risk_label = risk_from_score((match_obj.get("finalScore", 0) or 0) / 100.0)
            matches_total += 1
            matches_by_risk[risk_label] = matches_by_risk.get(risk_label, 0) + 1
            if risk_label == "no risk":
                continue
            dedupe_key = (match_obj["sanctionsList"], match_obj["sanctionsId"], role_value, index)
            existing = best_by_record.get(dedupe_key)
            if not existing or match_obj.get("finalScore", 0) > existing.get("finalScore", 0):
                best_by_record[dedupe_key] = match_obj
        if best_by_record:
            for match in best_by_record.values():
                all_matches.append(match)
                if show_slight or (match.get("riskLevel", "").lower() not in {"slight risk"}):
                    shown_matches.append(match)

    all_matches = _dedup(all_matches)
    shown_matches = _dedup(shown_matches)

    top_score = max((int(match.get("finalScore", 0)) for match in all_matches), default=0)

    groups: Dict[str, List[Dict[str, Any]]] = {}
    for match in all_matches:
        party_name_key = normalize_text(collapse_duplicate_tokens(match.get("partyName", "")))
        groups.setdefault(party_name_key, []).append(match)

    risk_score = 0
    for group in groups.values():
        base_score = max(int(item.get("finalScore", 0)) for item in group)
        qualifying_levels = {"moderate risk", "high risk", "very high risk"}
        qualifying_lists = {
            item.get("sanctionsList")
            for item in group
            if (item.get("sanctionsList") and (item.get("riskLevel") or "").lower() in qualifying_levels)
        }
        distinct_lists = len(qualifying_lists)
        bonus_points = 3 * distinct_lists
        aggregate = min(100, base_score + bonus_points)
        if aggregate > risk_score:
            risk_score = aggregate

    if not groups:
        risk_score = 0

    top_risk_level = risk_from_score(top_score / 100.0) if all_matches else "no risk"
    overall_risk_level = risk_from_score(risk_score / 100.0) if all_matches else "no risk"
    flagged = overall_risk_level in {"very high risk", "high risk", "moderate risk"}

    response_code_map = {
        "very high risk": "VERY_HIGH_RISK",
        "high risk": "HIGH_RISK",
        "moderate risk": "MODERATE_RISK",
        "slight risk": "SLIGHT_RISK",
        "no risk": "NONE",
    }
    response_code_value = response_code_map.get(overall_risk_level, "UNKNOWN")

    match_counts = {"total": matches_total, "byRiskLevel": matches_by_risk}

    return {
        "flagged": flagged,
        "matches": shown_matches,
        "topRiskLevel": top_risk_level,
        "topScore": top_score,
        "riskScore": min(100, risk_score),
        "riskLevel": overall_risk_level,
        "responseCode": response_code_value,
        "matchCounts": match_counts,
        "timeflagged": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
