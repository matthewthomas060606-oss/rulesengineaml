from typing import Any, Dict, Iterable, List, Mapping, MutableMapping


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, list):
        normalized_list: List[Any] = []
        for item in value:
            normalized_item = _normalize_value(item)
            if normalized_item is not None:
                normalized_list.append(normalized_item)
        return normalized_list or None
    if isinstance(value, dict):
        return value or None
    return value


def _coalesce(*values: Any) -> Any:
    for value in values:
        normalized = _normalize_value(value)
        if normalized is not None:
            return normalized
    return None


def _add_if_value(target: MutableMapping[str, Any], key: str, value: Any) -> None:
    normalized = _normalize_value(value)
    if normalized is not None:
        target[key] = normalized


def _clean_branch(branch_data: Mapping[str, Any]) -> Dict[str, Any]:
    branch_info: Dict[str, Any] = {}
    _add_if_value(branch_info, "Branch Id", branch_data.get("id"))
    _add_if_value(branch_info, "Branch LEI", branch_data.get("lei"))
    _add_if_value(branch_info, "Branch Name", branch_data.get("name"))

    address = _as_dict(branch_data.get("address"))
    _add_if_value(branch_info, "Branch Street", address.get("street"))
    _add_if_value(branch_info, "Branch Building Number", address.get("buildingNumber"))
    _add_if_value(branch_info, "Branch Postal Code", address.get("postalCode"))
    _add_if_value(branch_info, "Branch City", address.get("city"))
    _add_if_value(branch_info, "Branch Country", address.get("country"))
    return branch_info


def _extract_party_record(parsed_party: Mapping[str, Any]) -> Dict[str, Any]:
    party = _as_dict(parsed_party)
    address = _as_dict(party.get("address"))
    contact = _as_dict(party.get("contact"))
    account = _as_dict(party.get("account"))
    identifiers = _as_dict(party.get("identifiers"))
    financial_institution = _as_dict(party.get("financialInstitution"))

    bic_value = _coalesce(account.get("bic"), identifiers.get("anyBIC"))
    lei_value = _coalesce(identifiers.get("lei"), financial_institution.get("lei"))
    identifier_value = identifiers.get("id")
    account_id_value = account.get("accountId")

    role_value = _coalesce(party.get("role")) or "Unknown"
    name_value = _coalesce(party.get("name"), bic_value, lei_value, identifier_value, account_id_value)

    party_record: Dict[str, Any] = {"Role": role_value, "Name": name_value}

    _add_if_value(party_record, "LEI", lei_value)
    _add_if_value(party_record, "Identifier", identifier_value)
    _add_if_value(party_record, "Aliases", party.get("aliases"))

    address_fields = {
        "Country": ("country",),
        "City": ("city", "townLocationName"),
        "Postal Code": ("postalCode",),
        "Street": ("street",),
        "Building Number": ("buildingNumber",),
        "Address Line": ("addressLine",),
        "State": ("state", "countrySubdivision"),
    }
    for label, keys in address_fields.items():
        _add_if_value(party_record, label, _coalesce(*(address.get(key) for key in keys)))

    contact_fields = {
        "Country of Residence": "countryOfResidence",
        "Residency Status": "residencyStatus",
        "Date Of Birth": "dateOfBirth",
        "Place Of Birth": "placeOfBirth",
        "Email": "email",
        "Email Purpose": "emailPurpose",
        "Phone": "phone",
        "Mobile": "mobile",
        "Fax": "fax",
        "URL": "url",
        "Job Title": "jobTitle",
        "Responsibility": "responsibility",
        "Department": "department",
        "Contact Channel Type": "channelType",
        "Contact Channel Id": "channelId",
        "Preferred Contact Method": "preferredMethod",
    }
    for label, contact_key in contact_fields.items():
        _add_if_value(party_record, label, contact.get(contact_key))

    account_fields = {
        "Iban": "iban",
        "Account Other": "other",
        "Account Id": "accountId",
        "Account Currency": "currency",
        "Account Name": "name",
    }
    for label, account_key in account_fields.items():
        _add_if_value(party_record, label, account.get(account_key))

    _add_if_value(party_record, "BIC", bic_value)
    _add_if_value(party_record, "Clearing System Id", financial_institution.get("clearingSystemId"))
    _add_if_value(party_record, "Clearing Member Id", financial_institution.get("clearingMemberId"))

    branch_info = _clean_branch(_as_dict(financial_institution.get("branch")))
    party_record.update(branch_info)

    other_identifiers = _normalize_value(identifiers.get("other"))
    _add_if_value(party_record, "Other Identifiers", other_identifiers)

    structured_identifiers: Dict[str, Any] = {}
    _add_if_value(structured_identifiers, "bic", bic_value)
    _add_if_value(structured_identifiers, "anyBIC", identifiers.get("anyBIC"))
    _add_if_value(structured_identifiers, "lei", lei_value)
    _add_if_value(structured_identifiers, "id", identifier_value)
    _add_if_value(structured_identifiers, "other", other_identifiers)
    if structured_identifiers:
        party_record["Structured Identifiers"] = structured_identifiers

    return party_record


def _iter_list(value: Any) -> Iterable[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def returnitems(parsed, base):
    parsed = parsed or {}
    base = base or {}

    source_message = _as_dict(parsed.get("sourceMessage"))
    application_header = _as_dict(source_message.get("appHdr"))
    group_header = _as_dict(source_message.get("grpHdr"))
    transaction_node = _as_dict(parsed.get("transaction"))

    parsed_parties = parsed.get("parties") or []
    party_information_list = [_extract_party_record(party) for party in parsed_parties]

    payment_identification = _as_dict(transaction_node.get("paymentIdentification"))
    amount_map = _as_dict(transaction_node.get("amount"))
    settlement_amount_map = _as_dict(transaction_node.get("settlementAmount"))
    total_settlement_amount_map = _as_dict(transaction_node.get("totalSettlementAmount"))
    instrument_map = _as_dict(transaction_node.get("instrument"))

    transaction_information: Dict[str, Any] = {}
    _add_if_value(transaction_information, "Business Message Id", application_header.get("bizMsgId"))
    _add_if_value(transaction_information, "Application Header Created", application_header.get("created"))
    _add_if_value(transaction_information, "From BIC", application_header.get("fromBIC"))
    _add_if_value(transaction_information, "To BIC", application_header.get("toBIC"))

    schema_name = None
    for schema_key_candidate in ("xmlSchemaName", "schemaName", "xml_schema_name", "BizSvc", "bizSvc", "xmlSchema"):
        schema_name = _coalesce(application_header.get(schema_key_candidate))
        if schema_name is not None:
            break
    _add_if_value(transaction_information, "XML Schema Name", schema_name)

    _add_if_value(transaction_information, "Message Id", group_header.get("msgId"))
    _add_if_value(transaction_information, "Creation Date Time", group_header.get("creDtTm"))
    _add_if_value(transaction_information, "Number Of Transactions", group_header.get("nbOfTxs"))

    instruction_id_value = _coalesce(payment_identification.get("instrId"))
    end_to_end_id_value = _coalesce(payment_identification.get("endToEndId"))
    transaction_id_value = _coalesce(payment_identification.get("txId"))
    _add_if_value(transaction_information, "Instr Id", instruction_id_value)
    _add_if_value(transaction_information, "End To End Id", end_to_end_id_value)
    _add_if_value(transaction_information, "Tx Id", transaction_id_value)

    amount_value = _coalesce(amount_map.get("value"))
    currency_value = _coalesce(amount_map.get("currency"))
    if (amount_value is None or currency_value is None) and settlement_amount_map:
        amount_value = amount_value if amount_value is not None else _coalesce(settlement_amount_map.get("value"))
        currency_value = currency_value if currency_value is not None else _coalesce(settlement_amount_map.get("currency"))
    _add_if_value(transaction_information, "Amount", amount_value)
    _add_if_value(transaction_information, "Currency", currency_value)

    order_reference_value = _coalesce(transaction_node.get("orderReference"))
    client_reference_value = _coalesce(transaction_node.get("clientReference"))
    order_id_value = _coalesce(
        order_reference_value,
        client_reference_value,
        instruction_id_value,
        end_to_end_id_value,
        transaction_id_value,
    )

    transactional_fields = {
        "Settlement Date": transaction_node.get("settlementDate"),
        "Cash Settlement Date": transaction_node.get("cashSettlementDate"),
        "Requested Future Trade Date": transaction_node.get("requestedFutureTradeDate"),
        "Order Date Time": transaction_node.get("orderDateTime"),
        "Place Of Trade Exchange": transaction_node.get("placeOfTradeExchange"),
        "Pool Reference": transaction_node.get("poolReference"),
        "Previous Reference": transaction_node.get("previousReference"),
        "Master Reference": transaction_node.get("masterReference"),
        "Original Receiver BIC": transaction_node.get("originalReceiverBIC"),
    }
    for label, value in transactional_fields.items():
        _add_if_value(transaction_information, label, value)

    _add_if_value(transaction_information, "Order Reference", order_reference_value)
    _add_if_value(transaction_information, "Client Reference", client_reference_value)
    _add_if_value(transaction_information, "Order Id", order_id_value)

    _add_if_value(transaction_information, "Instrument ISIN", instrument_map.get("isin"))
    _add_if_value(transaction_information, "Instrument Name", instrument_map.get("name"))

    _add_if_value(transaction_information, "Settlement Amount", settlement_amount_map.get("value"))
    _add_if_value(transaction_information, "Settlement Currency", settlement_amount_map.get("currency"))
    _add_if_value(transaction_information, "Total Settlement Amount", total_settlement_amount_map.get("value"))
    _add_if_value(transaction_information, "Total Settlement Currency", total_settlement_amount_map.get("currency"))
    _add_if_value(transaction_information, "Units Number", transaction_node.get("unitsNumber"))

    formatted_extensions: List[Dict[str, Any]] = []
    for extension_entry in _iter_list(transaction_node.get("extensions")):
        extension_record: Dict[str, Any] = {}
        extension_mapping = _as_dict(extension_entry)
        _add_if_value(extension_record, "Place And Name", extension_mapping.get("placeAndName"))
        _add_if_value(extension_record, "Text", extension_mapping.get("text"))
        if extension_record:
            formatted_extensions.append(extension_record)
    if formatted_extensions:
        transaction_information["Extensions"] = formatted_extensions

    metadata = _as_dict(base.get("metadata"))
    message_definition_value = _coalesce(metadata.get("messageDefinition"), application_header.get("msgDefId"))
    _add_if_value(transaction_information, "Message Definition", message_definition_value)
    if message_definition_value:
        message_family_value = message_definition_value.split(".")[0]
        _add_if_value(transaction_information, "Message Family", message_family_value)

    if not parsed_parties:
        transaction_information["Screening Applicable"] = False
        transaction_information["Screening Note"] = "No customer parties present for this message type"

    return party_information_list, transaction_information
