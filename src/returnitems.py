def returnitems(parsed, base):
    application_header = (parsed or {}).get("sourceMessage", {}).get("appHdr", {}) or {}
    group_header = (parsed or {}).get("sourceMessage", {}).get("grpHdr", {}) or {}
    transaction_node = (parsed or {}).get("transaction", {}) or {}
    parsed_parties = (parsed or {}).get("parties", []) or []
    party_information_list = []
    for parsed_party in parsed_parties:
        parsed_party = parsed_party or {}
        address_map = (parsed_party.get("address") or {}) or {}
        contact_map = (parsed_party.get("contact") or {}) or {}
        account_map = (parsed_party.get("account") or {}) or {}
        identifiers_map = (parsed_party.get("identifiers") or {}) or {}
        financial_institution_map = (parsed_party.get("financialInstitution") or {}) or {}

        role_value = parsed_party.get("role") or "Unknown"
        real_name_value = parsed_party.get("name")

        country_value = address_map.get("country")
        city_value = address_map.get("city") or address_map.get("townLocationName")
        postal_code_value = address_map.get("postalCode")
        street_value = address_map.get("street")
        building_number_value = address_map.get("buildingNumber")
        address_line_value = address_map.get("addressLine")
        state_value = address_map.get("state") or address_map.get("countrySubdivision")

        country_of_residence_value = contact_map.get("countryOfResidence")
        residency_status_value = contact_map.get("residencyStatus")
        date_of_birth_value = contact_map.get("dateOfBirth")
        place_of_birth_value = contact_map.get("placeOfBirth")
        email_value = contact_map.get("email")
        email_purpose_value = contact_map.get("emailPurpose")
        phone_value = contact_map.get("phone")
        mobile_value = contact_map.get("mobile")
        fax_value = contact_map.get("fax")
        url_value = contact_map.get("url")
        job_title_value = contact_map.get("jobTitle")
        responsibility_value = contact_map.get("responsibility")
        department_value = contact_map.get("department")
        channel_type_value = contact_map.get("channelType")
        channel_id_value = contact_map.get("channelId")
        preferred_method_value = contact_map.get("preferredMethod")

        iban_value = account_map.get("iban")
        other_account_value = account_map.get("other")
        account_currency_value = account_map.get("currency")
        account_name_value = account_map.get("name")
        account_id_value = account_map.get("accountId")
        bic_value = account_map.get("bic") or (identifiers_map.get("anyBIC") if isinstance(identifiers_map, dict) else None)

        simple_identifier_value = identifiers_map.get("id")
        lei_value = identifiers_map.get("lei") or financial_institution_map.get("lei")
        clearing_system_id_value = financial_institution_map.get("clearingSystemId")
        clearing_member_id_value = financial_institution_map.get("clearingMemberId")
        branch_object = financial_institution_map.get("branch") or {}

        if (real_name_value is None or str(real_name_value).strip() == "") and bic_value not in (None, "", []):
            real_name_value = bic_value
        elif (real_name_value is None or str(real_name_value).strip() == "") and lei_value not in (None, "", []):
            real_name_value = lei_value
        elif (real_name_value is None or str(real_name_value).strip() == "") and simple_identifier_value not in (None, "", []):
            real_name_value = simple_identifier_value
        elif (real_name_value is None or str(real_name_value).strip() == "") and account_id_value not in (None, "", []):
            real_name_value = account_id_value

        party_record = {}
        party_record["Role"] = role_value
        party_record["Name"] = real_name_value

        if lei_value not in (None, "", []):
            party_record["LEI"] = lei_value
        if simple_identifier_value not in (None, "", []):
            party_record["Identifier"] = simple_identifier_value
        aliases_value = parsed_party.get("aliases")
        if aliases_value not in (None, [], ""):
            party_record["Aliases"] = aliases_value

        if country_value not in (None, "", []):
            party_record["Country"] = country_value
        if city_value not in (None, "", []):
            party_record["City"] = city_value
        if postal_code_value not in (None, "", []):
            party_record["Postal Code"] = postal_code_value
        if street_value not in (None, "", []):
            party_record["Street"] = street_value
        if building_number_value not in (None, "", []):
            party_record["Building Number"] = building_number_value
        if address_line_value not in (None, "", []):
            party_record["Address Line"] = address_line_value
        if state_value not in (None, "", []):
            party_record["State"] = state_value

        if country_of_residence_value not in (None, "", []):
            party_record["Country of Residence"] = country_of_residence_value
        if residency_status_value not in (None, "", []):
            party_record["Residency Status"] = residency_status_value
        if date_of_birth_value not in (None, "", []):
            party_record["Date Of Birth"] = date_of_birth_value
        if place_of_birth_value not in (None, "", []):
            party_record["Place Of Birth"] = place_of_birth_value

        if email_value not in (None, "", []):
            party_record["Email"] = email_value
        if email_purpose_value not in (None, "", []):
            party_record["Email Purpose"] = email_purpose_value
        if phone_value not in (None, "", []):
            party_record["Phone"] = phone_value
        if mobile_value not in (None, "", []):
            party_record["Mobile"] = mobile_value
        if fax_value not in (None, "", []):
            party_record["Fax"] = fax_value
        if url_value not in (None, "", []):
            party_record["URL"] = url_value
        if job_title_value not in (None, "", []):
            party_record["Job Title"] = job_title_value
        if responsibility_value not in (None, "", []):
            party_record["Responsibility"] = responsibility_value
        if department_value not in (None, "", []):
            party_record["Department"] = department_value
        if channel_type_value not in (None, "", []):
            party_record["Contact Channel Type"] = channel_type_value
        if channel_id_value not in (None, "", []):
            party_record["Contact Channel Id"] = channel_id_value
        if preferred_method_value not in (None, "", []):
            party_record["Preferred Contact Method"] = preferred_method_value

        if iban_value not in (None, "", []):
            party_record["Iban"] = iban_value
        if other_account_value not in (None, "", []):
            party_record["Account Other"] = other_account_value
        if account_id_value not in (None, "", []):
            party_record["Account Id"] = account_id_value
        if account_currency_value not in (None, "", []):
            party_record["Account Currency"] = account_currency_value
        if account_name_value not in (None, "", []):
            party_record["Account Name"] = account_name_value
        if bic_value not in (None, "", []):
            party_record["BIC"] = bic_value
        if clearing_system_id_value not in (None, "", []):
            party_record["Clearing System Id"] = clearing_system_id_value
        if clearing_member_id_value not in (None, "", []):
            party_record["Clearing Member Id"] = clearing_member_id_value
        if isinstance(branch_object, dict) and branch_object:
            branch_id_value = branch_object.get("id")
            branch_lei_value = branch_object.get("lei")
            branch_name_value = branch_object.get("name")
            branch_address_map = branch_object.get("address") or {}
            if branch_id_value not in (None, "", []):
                party_record["Branch Id"] = branch_id_value
            if branch_lei_value not in (None, "", []):
                party_record["Branch LEI"] = branch_lei_value
            if branch_name_value not in (None, "", []):
                party_record["Branch Name"] = branch_name_value
            if branch_address_map.get("street") not in (None, "", []):
                party_record["Branch Street"] = branch_address_map.get("street")
            if branch_address_map.get("buildingNumber") not in (None, "", []):
                party_record["Branch Building Number"] = branch_address_map.get("buildingNumber")
            if branch_address_map.get("postalCode") not in (None, "", []):
                party_record["Branch Postal Code"] = branch_address_map.get("postalCode")
            if branch_address_map.get("city") not in (None, "", []):
                party_record["Branch City"] = branch_address_map.get("city")
            if branch_address_map.get("country") not in (None, "", []):
                party_record["Branch Country"] = branch_address_map.get("country")

        other_identifiers_list = identifiers_map.get("other") if isinstance(identifiers_map, dict) else None
        if other_identifiers_list not in (None, [], ""):
            party_record["Other Identifiers"] = other_identifiers_list

        structured_identifiers_map = {}
        any_bic_value = identifiers_map.get("anyBIC") if isinstance(identifiers_map, dict) else None
        if bic_value not in (None, "", []):
            structured_identifiers_map["bic"] = bic_value
        if any_bic_value not in (None, "", []):
            structured_identifiers_map["anyBIC"] = any_bic_value
        if lei_value not in (None, "", []):
            structured_identifiers_map["lei"] = lei_value
        if simple_identifier_value not in (None, "", []):
            structured_identifiers_map["id"] = simple_identifier_value
        if other_identifiers_list not in (None, [], ""):
            structured_identifiers_map["other"] = other_identifiers_list
        if structured_identifiers_map:
            party_record["Structured Identifiers"] = structured_identifiers_map

        party_information_list.append(party_record)

    payment_identification = (transaction_node or {}).get("paymentIdentification") or {}
    payment_type = (transaction_node or {}).get("paymentType") or {}
    amount_map = (transaction_node or {}).get("amount") or {}
    settlement_amount_map = (transaction_node or {}).get("settlementAmount") or {}
    total_settlement_amount_map = (transaction_node or {}).get("totalSettlementAmount") or {}
    instrument_map = (transaction_node or {}).get("instrument") or {}
    extensions_list = (transaction_node or {}).get("extensions") or []

    transaction_information = {}
    if application_header.get("bizMsgId") not in (None, "", []):
        transaction_information["Business Message Id"] = application_header.get("bizMsgId")
    if application_header.get("created") not in (None, "", []):
        transaction_information["Application Header Created"] = application_header.get("created")
    if application_header.get("fromBIC") not in (None, "", []):
        transaction_information["From BIC"] = application_header.get("fromBIC")
    if application_header.get("toBIC") not in (None, "", []):
        transaction_information["To BIC"] = application_header.get("toBIC")

    xml_schema_name_value = None
    for schema_key_candidate in ["xmlSchemaName", "schemaName", "xml_schema_name", "BizSvc", "bizSvc", "xmlSchema"]:
        schema_candidate_value = application_header.get(schema_key_candidate)
        if schema_candidate_value not in (None, "", []):
            xml_schema_name_value = schema_candidate_value
            break
    if xml_schema_name_value not in (None, "", []):
        transaction_information["XML Schema Name"] = xml_schema_name_value

    message_id_value = group_header.get("msgId")
    creation_date_time_value = group_header.get("creDtTm")
    number_of_transactions_value = group_header.get("nbOfTxs")
    if message_id_value not in (None, "", []):
        transaction_information["Message Id"] = message_id_value
    if creation_date_time_value not in (None, "", []):
        transaction_information["Creation Date Time"] = creation_date_time_value
    if number_of_transactions_value not in (None, "", []):
        transaction_information["Number Of Transactions"] = number_of_transactions_value

    instruction_id_value = payment_identification.get("instrId")
    end_to_end_id_value = payment_identification.get("endToEndId")
    transaction_id_value = payment_identification.get("txId")
    if instruction_id_value not in (None, "", []):
        transaction_information["Instr Id"] = instruction_id_value
    if end_to_end_id_value not in (None, "", []):
        transaction_information["End To End Id"] = end_to_end_id_value
    if transaction_id_value not in (None, "", []):
        transaction_information["Tx Id"] = transaction_id_value

    amount_value = amount_map.get("value")
    currency_value = amount_map.get("currency")
    if (amount_value in (None, "", []) or currency_value in (None, "", [])) and settlement_amount_map:
        amount_value = amount_value if amount_value not in (None, "", []) else settlement_amount_map.get("value")
        currency_value = currency_value if currency_value not in (None, "", []) else settlement_amount_map.get("currency")
    if amount_value not in (None, "", []):
        transaction_information["Amount"] = amount_value
    if currency_value not in (None, "", []):
        transaction_information["Currency"] = currency_value

    order_reference_value = (transaction_node or {}).get("orderReference")
    client_reference_value = (transaction_node or {}).get("clientReference")
    order_id_value = order_reference_value or client_reference_value or instruction_id_value or end_to_end_id_value or transaction_id_value
    if (transaction_node or {}).get("settlementDate") not in (None, "", []):
        transaction_information["Settlement Date"] = (transaction_node or {}).get("settlementDate")
    if (transaction_node or {}).get("cashSettlementDate") not in (None, "", []):
        transaction_information["Cash Settlement Date"] = (transaction_node or {}).get("cashSettlementDate")
    if (transaction_node or {}).get("requestedFutureTradeDate") not in (None, "", []):
        transaction_information["Requested Future Trade Date"] = (transaction_node or {}).get("requestedFutureTradeDate")
    if (transaction_node or {}).get("orderDateTime") not in (None, "", []):
        transaction_information["Order Date Time"] = (transaction_node or {}).get("orderDateTime")
    if (transaction_node or {}).get("placeOfTradeExchange") not in (None, "", []):
        transaction_information["Place Of Trade Exchange"] = (transaction_node or {}).get("placeOfTradeExchange")
    if (transaction_node or {}).get("poolReference") not in (None, "", []):
        transaction_information["Pool Reference"] = (transaction_node or {}).get("poolReference")
    if (transaction_node or {}).get("previousReference") not in (None, "", []):
        transaction_information["Previous Reference"] = (transaction_node or {}).get("previousReference")
    if (transaction_node or {}).get("masterReference") not in (None, "", []):
        transaction_information["Master Reference"] = (transaction_node or {}).get("masterReference")
    if (transaction_node or {}).get("originalReceiverBIC") not in (None, "", []):
        transaction_information["Original Receiver BIC"] = (transaction_node or {}).get("originalReceiverBIC")
    if order_reference_value not in (None, "", []):
        transaction_information["Order Reference"] = order_reference_value
    if client_reference_value not in (None, "", []):
        transaction_information["Client Reference"] = client_reference_value
    if order_id_value not in (None, "", []):
        transaction_information["Order Id"] = order_id_value

    if instrument_map.get("isin") not in (None, "", []):
        transaction_information["Instrument ISIN"] = instrument_map.get("isin")
    if instrument_map.get("name") not in (None, "", []):
        transaction_information["Instrument Name"] = instrument_map.get("name")

    if settlement_amount_map.get("value") not in (None, "", []):
        transaction_information["Settlement Amount"] = settlement_amount_map.get("value")
    if settlement_amount_map.get("currency") not in (None, "", []):
        transaction_information["Settlement Currency"] = settlement_amount_map.get("currency")
    if total_settlement_amount_map.get("value") not in (None, "", []):
        transaction_information["Total Settlement Amount"] = total_settlement_amount_map.get("value")
    if total_settlement_amount_map.get("currency") not in (None, "", []):
        transaction_information["Total Settlement Currency"] = total_settlement_amount_map.get("currency")
    if (transaction_node or {}).get("unitsNumber") not in (None, "", []):
        transaction_information["Units Number"] = (transaction_node or {}).get("unitsNumber")

    if isinstance(extensions_list, list) and extensions_list:
        formatted_extensions = []
        for extension_entry in extensions_list:
            place_and_name_value = (extension_entry or {}).get("placeAndName")
            text_value = (extension_entry or {}).get("text")
            extension_record = {}
            if place_and_name_value not in (None, "", []):
                extension_record["Place And Name"] = place_and_name_value
            if text_value not in (None, "", []):
                extension_record["Text"] = text_value
            if extension_record:
                formatted_extensions.append(extension_record)
        if formatted_extensions:
            transaction_information["Extensions"] = formatted_extensions

    message_definition_value = (base.get("metadata") or {}).get("messageDefinition") or application_header.get("msgDefId")
    message_family_value = (message_definition_value.split(".")[:1] or [None])[0] if message_definition_value else None
    if message_definition_value not in (None, "", []):
        transaction_information["Message Definition"] = message_definition_value
    if message_family_value not in (None, "", []):
        transaction_information["Message Family"] = message_family_value

    if not parsed_parties:
        transaction_information["Screening Applicable"] = False
        transaction_information["Screening Note"] = "No customer parties present for this message type"

    return party_information_list, transaction_information
