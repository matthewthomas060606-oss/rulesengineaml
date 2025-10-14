import xml.etree.ElementTree as ET
import hashlib
import uuid
import io
import re


def parse(iso20022xml: bytes):
    try:
        tree = ET.parse(io.BytesIO(iso20022xml))
    except ET.ParseError:
        b = iso20022xml[3:] if iso20022xml.startswith(b'\xef\xbb\xbf') else iso20022xml
        b = re.sub(rb'[\x00-\x08\x0B\x0C\x0E-\x1F]', b'', b)
        b = re.sub(rb'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9A-Fa-f]+;)', b'&amp;', b)
        tree = ET.parse(io.BytesIO(b))

    root_element = tree.getroot()
    ingest_hash = "sha256:" + hashlib.sha256(iso20022xml or b"").hexdigest()
    root_tag_name = root_element.tag.split("}")[-1] if isinstance(root_element.tag, str) else root_element.tag
    parent_map = {c: p for p in root_element.iter() for c in p}

    application_header_element = None
    for element in root_element.iter():
        if (element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag) == "AppHdr":
            application_header_element = element
            break

    application_header = {
        "bizMsgId": None,
        "msgDefId": None,
        "created": None,
        "fromBIC": None,
        "fromName": None,
        "toBIC": None,
        "toName": None,
        "bizSvc": None
    }

    if application_header_element is not None:
        for element in application_header_element.iter():
            tag_name = element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag
            if tag_name == "BizMsgIdr" and element.text and element.text.strip():
                application_header["bizMsgId"] = element.text.strip()
            elif tag_name == "MsgDefIdr" and element.text and element.text.strip():
                application_header["msgDefId"] = element.text.strip()
            elif tag_name == "CreDt" and element.text and element.text.strip():
                application_header["created"] = element.text.strip()
            elif tag_name == "BizSvc" and element.text and element.text.strip():
                application_header["bizSvc"] = element.text.strip()

        from_container = None
        to_container = None
        for child in application_header_element:
            child_name = child.tag.split("}")[-1] if isinstance(child.tag, str) else child.tag
            if child_name in ("Fr", "From"):
                from_container = child
            elif child_name in ("To", "Receiver", "ToWhom"):
                to_container = child

        if from_container is not None:
            bic_value = None
            name_value = None
            for e in from_container.iter():
                n = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
                if n == "BICFI" and e.text and e.text.strip():
                    bic_value = e.text.strip()
                elif n == "Nm" and e.text and e.text.strip():
                    name_value = e.text.strip()
            application_header["fromBIC"] = bic_value
            application_header["fromName"] = name_value

        if to_container is not None:
            bic_value = None
            name_value = None
            for e in to_container.iter():
                n = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
                if n == "BICFI" and e.text and e.text.strip():
                    bic_value = e.text.strip()
                elif n == "Nm" and e.text and e.text.strip():
                    name_value = e.text.strip()
            application_header["toBIC"] = bic_value
            application_header["toName"] = name_value

    if not application_header.get("msgDefId"):
        if isinstance(root_element.tag, str) and "}" in root_element.tag:
            namespace_uri = root_element.tag.split("}")[0].strip("{")
            if namespace_uri and ":" in namespace_uri:
                application_header["msgDefId"] = namespace_uri.rsplit(":", 1)[-1]

    document_element = None
    for element in root_element.iter():
        if (element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag) == "Document":
            document_element = element
            break
    if document_element is None:
        document_element = root_element

    group_header_element = None
    for candidate_name in ("GrpHdr", "MsgHdr", "Hdr"):
        for element in document_element.iter():
            if (element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag) == candidate_name:
                group_header_element = element
                break
        if group_header_element is not None:
            break

    group_header = {"msgId": None, "creDtTm": None, "nbOfTxs": None}
    if group_header_element is not None:
        for element in group_header_element.iter():
            tag_name = element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag
            if tag_name == "MsgId" and element.text and element.text.strip():
                group_header["msgId"] = element.text.strip()
            elif tag_name == "CreDtTm" and element.text and element.text.strip():
                group_header["creDtTm"] = element.text.strip()
            elif tag_name == "NbOfTxs" and element.text and element.text.strip():
                group_header["nbOfTxs"] = element.text.strip()
    else:
        msg_id_block = None
        for element in document_element.iter():
            if (element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag) == "MsgId":
                msg_id_block = element
                break
        if msg_id_block is not None:
            for e in msg_id_block:
                en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
                if en == "Id" and e.text and e.text.strip():
                    group_header["msgId"] = e.text.strip()
                elif en == "CreDtTm" and e.text and e.text.strip():
                    group_header["creDtTm"] = e.text.strip()

    canonical_role_map = {
        "MsgRcpt": "messageReceiver",
        "Svcr": "accountServicer",
        "RltdPties": "relatedParty",
        "RltdAgts": "relatedAgent",
        "RcptPty": "messageReceiver",
        "InitgPty": "initiatingParty",
        "Acqrr": "acquirer",
        "ATMMgr": "atmManager",
        "HstgNtty": "hostingEntity",
        "ATM": "atm",
        "Dbtr": "debtor",
        "Cdtr": "creditor",
        "DbtrAgt": "debtorAgent",
        "CdtrAgt": "creditorAgent",
        "UltmtDbtr": "ultimateDebtor",
        "UltmtCdtr": "ultimateCreditor",
        "InstgAgt": "instructingAgent",
        "InstdAgt": "instructedAgent",
        "IntrmyAgt1": "intermediaryAgent",
        "IntrmyAgt2": "intermediaryAgent",
        "IntrmyAgt3": "intermediaryAgent",
        "Bnfcry": "beneficiary",
        "BnfcryDtls": "beneficiary",
        "OrgnlRcvr": "originalReceiver",
        "AcctOwnr": "accountOwner",
        "Ownr": "accountOwner",
        "PmryOwnr": "accountOwner",
        "ScndryOwnr": "accountOwner",
        "PrncplAcctPty": "accountOwner",
        "OwnrId": "accountOwner",
        "AcctSvcr": "accountServicer",
        "SttlmPlc": "settlementPlace",
        "SfkpgPlc": "safekeepingPlace",
        "RcvgAgt": "receivingAgent",
        "RcvgAgtDtls": "receivingAgent",
        "RcvgSd": "receivingAgent",
        "RcvgSdDtls": "receivingAgent",
        "DlvrgAgt": "deliveringAgent",
        "DlvrgAgtDtls": "deliveringAgent",
        "DlvrgSd": "deliveringAgent",
        "DlvrgSdDtls": "deliveringAgent",
        "Dpstry": "depository",
        "Ctdn": "custodian",
        "Custodian": "custodian",
        "Brkr": "broker",
        "ClrMmb": "clearingMember",
        "CCP": "centralCounterparty",
        "Regar": "registrar",
        "TrfAgt": "transferAgent",
        "Issr": "issuer",
        "PngAgt": "payingAgent",
        "WhldgAgt": "withholdingAgent",
        "TaxAgt": "taxAgent",
        "InfAgt": "informationAgent",
        "TndrAgt": "tenderAgent",
        "XchgAgt": "exchangeAgent",
        "CltrlTkr": "collateralTaker",
        "CltrlGv": "collateralGiver",
        "TrptyAgt": "tripartyAgent",
        "Crdhldr": "cardholder",
        "CardHldr": "cardholder",
        "Mrchnt": "merchant",
        "Accptr": "merchant",
        "AccptrAgt": "acceptorAgent",
        "POI": "pointOfInteraction",
        "PointOfInteraction": "pointOfInteraction",
        "TermnlMgrId": "pointOfInteraction",
        "IssrBk": "issuerBank",
        "CardSchme": "cardScheme",
        "ATMOp": "atmOperator",
        "ATMOpr": "atmOperator",
        "Buyr": "buyer",
        "Sellr": "seller",
        "BuyrCsdn": "buyerCustodian",
        "SellrCsdn": "sellerCustodian",
        "BuyrBkr": "buyerBroker",
        "SellrBkr": "sellerBroker",
        "BuyrBk": "buyerBank",
        "SellrBk": "sellerBank",
        "BuyrAgt": "buyerAgent",
        "SellrAgt": "sellerAgent",
        "FXSttlmAgt": "fxSettlementAgent",
        "MsgSndr": "messageSender",
        "Sndr": "messageSender",
        "Fr": "messageSender",
        "MsgRcvr": "messageReceiver",
        "Rcvr": "messageReceiver",
        "To": "messageReceiver",
        "Rqstr": "requestor",
        "Rspndr": "responder",
        "Authrty": "authority",
        "MandateHldr": "mandateHolder",
        "MndtHldr": "mandateHolder",
        "Prxy": "mandateHolder",
        "BkCtct": "bankContact",
        "RptgPty": "reportingParty",
        "InstgPty": "instructingParty",
        "InstdPty": "instructedParty",
        "Initr": "initiator",
        "AgtId": "agent",
        "Pty": "party"
    }

    def _detect_unmapped_parties(document_element, canonical_role_map, already_seen):
        parties_local = []
        if document_element is None:
            return parties_local

        parent_map_local = {c: p for p in document_element.iter() for c in p}
        trigger_tags = {"Nm", "Adr", "PstlAdr", "NmAndAdr", "Lctn"}

        for trigger in document_element.iter():
            trig_local = trigger.tag.split("}")[-1] if isinstance(trigger.tag, str) else trigger.tag
            if trig_local not in trigger_tags:
                continue
            parent = parent_map_local.get(trigger)
            if parent is None:
                continue
            parent_local = parent.tag.split("}")[-1] if isinstance(parent.tag, str) else parent.tag
            if not parent_local or parent_local in ("Document", "AppHdr"):
                continue
            if parent_local in canonical_role_map:
                continue
            parent_id = id(parent)
            if parent_id in already_seen:
                continue

            name_value = None
            if trig_local == "Nm" and trigger.text and trigger.text.strip():
                name_value = trigger.text.strip()
            else:
                for child in list(parent):
                    cn = child.tag.split("}")[-1] if isinstance(child.tag, str) else child.tag
                    if cn == "Nm" and child.text and child.text.strip():
                        name_value = child.text.strip()
                        break

            if name_value is None and trig_local in {"Adr", "PstlAdr", "NmAndAdr", "Lctn"}:
                addr_bits = []
                for c in list(trigger):
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    if cn in ("AdrLine", "StrtNm", "BldgNb", "TwnNm", "TownNm", "PstCd", "PostCd", "Ctry", "CtryCd"):
                        if c.text and c.text.strip():
                            addr_bits.append(c.text.strip())
                if addr_bits:
                    name_value = " ".join(addr_bits)[:256]

            if name_value is None:
                continue

            alias_values = None
            address = {
                "type": {"id": None, "issuer": None, "schemeName": None},
                "careOf": None,
                "department": None,
                "subDepartment": None,
                "street": None,
                "buildingNumber": None,
                "buildingName": None,
                "floor": None,
                "unitNumber": None,
                "postBox": None,
                "room": None,
                "postalCode": None,
                "city": None,
                "townLocationName": None,
                "districtName": None,
                "state": None,
                "country": None,
                "addressLine": None,
                "addressLines": []
            }

            address_node = None
            for e in parent.iter():
                if (e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag) == "PstlAdr":
                    address_node = e
                    break
            if address_node is None:
                for e in parent.iter():
                    if (e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag) == "Adr":
                        address_node = e
                        break
            if address_node is None:
                for e in parent.iter():
                    if (e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag) == "Lctn":
                        address_node = e
                        break

            if address_node is not None:
                for c in address_node:
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    cl = cn.lower() if isinstance(cn, str) else cn
                    if cn == "AdrTp":
                        for p in c.iter():
                            pn = p.tag.split("}")[-1] if isinstance(p.tag, str) else p.tag
                            if pn == "Prtry":
                                for q in p:
                                    qn = q.tag.split("}")[-1] if isinstance(q.tag, str) else q.tag
                                    if qn == "Id" and q.text and q.text.strip():
                                        address["type"]["id"] = q.text.strip()
                                    elif qn == "Issr" and q.text and q.text.strip():
                                        address["type"]["issuer"] = q.text.strip()
                                    elif qn == "SchmeNm" and q.text and q.text.strip():
                                        address["type"]["schemeName"] = q.text.strip()
                    elif cl == "careof" and c.text and c.text.strip():
                        address["careOf"] = c.text.strip()
                    elif cn == "Dept" and c.text and c.text.strip():
                        address["department"] = c.text.strip()
                    elif cn == "SubDept" and c.text and c.text.strip():
                        address["subDepartment"] = c.text.strip()
                    elif cn == "StrtNm" and c.text and c.text.strip():
                        address["street"] = c.text.strip()
                    elif cn == "BldgNb" and c.text and c.text.strip():
                        address["buildingNumber"] = c.text.strip()
                    elif cn == "BldgNm" and c.text and c.text.strip():
                        address["buildingName"] = c.text.strip()
                    elif cn == "Flr" and c.text and c.text.strip():
                        address["floor"] = c.text.strip()
                    elif cn == "UnitNb" and c.text and c.text.strip():
                        address["unitNumber"] = c.text.strip()
                    elif cn == "PstBx" and c.text and c.text.strip():
                        address["postBox"] = c.text.strip()
                    elif cn == "Room" and c.text and c.text.strip():
                        address["room"] = c.text.strip()
                    elif cl in ("pstcd", "postcd") and c.text and c.text.strip():
                        address["postalCode"] = c.text.strip()
                    elif cl in ("twnnm", "townnm") and c.text and c.text.strip():
                        address["city"] = c.text.strip()
                    elif cn == "TwnLctnNm" and c.text and c.text.strip():
                        address["townLocationName"] = c.text.strip()
                    elif cn == "DstrctNm" and c.text and c.text.strip():
                        address["districtName"] = c.text.strip()
                    elif cn == "CtrySubDvsn" and c.text and c.text.strip():
                        address["state"] = c.text.strip()
                    elif cn in ("Ctry", "CtryCd") and c.text and c.text.strip():
                        address["country"] = c.text.strip()
                    elif cn == "AdrLine" and c.text and c.text.strip():
                        address["addressLines"].append(c.text.strip())
                if address["addressLines"] and not address.get("addressLine"):
                    address["addressLine"] = address["addressLines"][0]

            identifiers = {"id": None, "anyBIC": None, "lei": None, "other": []}
            bic_value = None
            financial_institution_other = []
            financial_institution_lei = None
            clearing_system_id = None
            clearing_member_id = None
            branch_object = None
            any_bic_value = None
            prtry_id_value = None
            prtry_id_scheme = None
            prtry_id_issuer = None

            for e in parent.iter():
                en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
                if en == "BICFI" and e.text and e.text.strip():
                    bic_value = e.text.strip()
                elif en == "AnyBIC" and e.text and e.text.strip():
                    any_bic_value = e.text.strip()
                elif en == "LEI" and e.text and e.text.strip():
                    identifiers["lei"] = e.text.strip()
                elif en == "Id" and e.text and e.text.strip() and identifiers["id"] is None:
                    identifiers["id"] = e.text.strip()
                elif en == "PrtryId":
                    id_text = None
                    scheme_text = None
                    issuer_text = None
                    for y in e:
                        yn = y.tag.split("}")[-1] if isinstance(y.tag, str) else y.tag
                        if yn == "Id" and y.text and y.text.strip():
                            id_text = y.text.strip()
                        elif yn == "SchmeNm" and y.text and y.text.strip():
                            scheme_text = y.text.strip()
                        elif yn == "Issr" and y.text and y.text.strip():
                            issuer_text = y.text.strip()
                    prtry_id_value = id_text or prtry_id_value
                    prtry_id_scheme = scheme_text or prtry_id_scheme
                    prtry_id_issuer = issuer_text or prtry_id_issuer
                    if id_text or scheme_text:
                        financial_institution_other.append({"id": id_text, "scheme": scheme_text})
                if any_bic_value and not identifiers["anyBIC"]:
                    identifiers["anyBIC"] = any_bic_value

            party_obj = {
                "role": parent_local,
                "name": name_value,
                "aliases": alias_values,
                "address": address,
                "contact": {
                    "countryOfResidence": None,
                    "residencyStatus": None,
                    "placeOfBirth": None,
                    "dateOfBirth": None,
                    "provinceOfBirth": None,
                    "cityOfBirth": None,
                    "countryOfBirth": None,
                    "prefix": None,
                    "contactName": None,
                    "phone": None,
                    "mobile": None,
                    "fax": None,
                    "url": None,
                    "email": None,
                    "emailPurpose": None,
                    "jobTitle": None,
                    "responsibility": None,
                    "department": None,
                    "channelType": None,
                    "channelId": None,
                    "preferredMethod": None
                },
                "account": {
                    "iban": None,
                    "other": None,
                    "others": [],
                    "bic": bic_value,
                    "currency": None,
                    "name": None,
                    "accountId": None
                },
                "identifiers": identifiers,
                "financialInstitution": {
                    "bic": bic_value,
                    "lei": financial_institution_lei,
                    "clearingSystemId": clearing_system_id,
                    "clearingMemberId": clearing_member_id,
                    "other": financial_institution_other,
                    "branch": branch_object
                }
            }
            parties_local.append(party_obj)
            already_seen.add(parent_id)

        return parties_local

    parties = []
    seen_party_elements = set()

    if application_header.get("fromBIC") or application_header.get("fromName"):
        identifiers_map = {"id": None, "anyBIC": application_header.get("fromBIC"), "lei": None, "other": []}
        parties.append({
            "role": "messageSender",
            "name": application_header.get("fromName"),
            "aliases": None,
            "address": {
                "type": {"id": None, "issuer": None, "schemeName": None},
                "careOf": None,
                "department": None,
                "subDepartment": None,
                "street": None,
                "buildingNumber": None,
                "buildingName": None,
                "floor": None,
                "unitNumber": None,
                "postBox": None,
                "room": None,
                "postalCode": None,
                "city": None,
                "townLocationName": None,
                "districtName": None,
                "state": None,
                "country": None,
                "addressLine": None,
                "addressLines": []
            },
            "contact": {
                "countryOfResidence": None,
                "residencyStatus": None,
                "placeOfBirth": None,
                "dateOfBirth": None,
                "provinceOfBirth": None,
                "cityOfBirth": None,
                "countryOfBirth": None,
                "prefix": None,
                "contactName": None,
                "phone": None,
                "mobile": None,
                "fax": None,
                "url": None,
                "email": None,
                "emailPurpose": None,
                "jobTitle": None,
                "responsibility": None,
                "department": None,
                "channelType": None,
                "channelId": None,
                "preferredMethod": None
            },
            "account": {
                "iban": None,
                "other": None,
                "others": [],
                "bic": application_header.get("fromBIC"),
                "currency": None,
                "name": None,
                "accountId": None
            },
            "identifiers": identifiers_map,
            "financialInstitution": {
                "bic": application_header.get("fromBIC"),
                "lei": None,
                "clearingSystemId": None,
                "clearingMemberId": None,
                "other": [],
                "branch": None
            }
        })

    if application_header.get("toBIC") or application_header.get("toName"):
        identifiers_map = {"id": None, "anyBIC": application_header.get("toBIC"), "lei": None, "other": []}
        parties.append({
            "role": "messageReceiver",
            "name": application_header.get("toName"),
            "aliases": None,
            "address": {
                "type": {"id": None, "issuer": None, "schemeName": None},
                "careOf": None,
                "department": None,
                "subDepartment": None,
                "street": None,
                "buildingNumber": None,
                "buildingName": None,
                "floor": None,
                "unitNumber": None,
                "postBox": None,
                "room": None,
                "postalCode": None,
                "city": None,
                "townLocationName": None,
                "districtName": None,
                "state": None,
                "country": None,
                "addressLine": None,
                "addressLines": []
            },
            "contact": {
                "countryOfResidence": None,
                "residencyStatus": None,
                "placeOfBirth": None,
                "dateOfBirth": None,
                "provinceOfBirth": None,
                "cityOfBirth": None,
                "countryOfBirth": None,
                "prefix": None,
                "contactName": None,
                "phone": None,
                "mobile": None,
                "fax": None,
                "url": None,
                "email": None,
                "emailPurpose": None,
                "jobTitle": None,
                "responsibility": None,
                "department": None,
                "channelType": None,
                "channelId": None,
                "preferredMethod": None
            },
            "account": {
                "iban": None,
                "other": None,
                "others": [],
                "bic": application_header.get("toBIC"),
                "currency": None,
                "name": None,
                "accountId": None
            },
            "identifiers": identifiers_map,
            "financialInstitution": {
                "bic": application_header.get("toBIC"),
                "lei": None,
                "clearingSystemId": None,
                "clearingMemberId": None,
                "other": [],
                "branch": None
            }
        })

    investment_accounts = []
    for element in document_element.iter():
        if (element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag) == "IndvOrdrDtls":
            owner_name_value = None
            account_identifier_value = None
            account_display_name_value = None
            for e in element.iter():
                en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
                if en == "AcctOwnr":
                    for c in e.iter():
                        cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                        if cn == "Nm" and c.text and c.text.strip():
                            owner_name_value = c.text.strip()
                if en == "OwnrId":
                    for c in e.iter():
                        cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                        if cn == "Nm" and c.text and c.text.strip():
                            owner_name_value = c.text.strip()
                if en == "AcctNm" and e.text and e.text.strip() and owner_name_value is None:
                    owner_name_value = e.text.strip()
                if en == "InvstmtAcctDtls":
                    for c in e.iter():
                        cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                        if cn == "AcctId":
                            direct_text_value = c.text.strip() if c.text and c.text.strip() else None
                            nested_value = None
                            for z in c:
                                zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                                if zn == "Id" and z.text and z.text.strip():
                                    nested_value = z.text.strip()
                            account_identifier_value = nested_value or direct_text_value or account_identifier_value
                        elif cn == "AcctNm" and c.text and c.text.strip():
                            account_display_name_value = c.text.strip()
            if owner_name_value and account_identifier_value:
                investment_accounts.append({
                    "ownerName": owner_name_value,
                    "acctId": account_identifier_value,
                    "acctName": account_display_name_value
                })

    for element in document_element.iter():
        local_name = element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag
        canonical_role = canonical_role_map.get(local_name)
        if canonical_role is None:
            continue

        element_id_value = id(element)
        if element_id_value in seen_party_elements:
            continue

        has_party_like_descendant = False
        for d in element.iter():
            dn = d.tag.split("}")[-1] if isinstance(d.tag, str) else d.tag
            if dn in ("Nm", "PstlAdr", "Adr", "NmAndAdr", "OrgId", "PrvtId", "Id", "FinInstnId", "BICFI", "AnyBIC", "LEI", "IBAN", "Lctn", "PrtryId"):
                has_party_like_descendant = True
                break
        if not has_party_like_descendant:
            continue

        seen_party_elements.add(element_id_value)

        name_value = None
        for e in element.iter():
            tn = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if tn == "Nm" and e.text and e.text.strip():
                name_value = e.text.strip()
                break

        if name_value is None:
            person_or_party_node = None
            for e in element.iter():
                tn = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
                if tn in ("Pty", "IndvPrsn", "OrgId", "PrvtId", "NmAndAdr"):
                    person_or_party_node = e
                    break
            if person_or_party_node is not None:
                for e in person_or_party_node.iter():
                    tn = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
                    if tn == "Nm" and e.text and e.text.strip():
                        name_value = e.text.strip()
                        break

        if name_value is None:
            for e in element.iter():
                tn = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
                if tn in ("Id", "AcqrgInstn", "AddtlId", "ShrtNm", "ShortName"):
                    if e.text and e.text.strip():
                        name_value = e.text.strip()
                        break

        alias_values = []
        for e in element.iter():
            tn = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if tn in ("Alia", "Alias"):
                alias_text = None
                alias_name_child = None
                for c in list(e):
                    if (c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag) == "Nm":
                        alias_name_child = c
                        break
                if alias_name_child is not None and alias_name_child.text and alias_name_child.text.strip():
                    alias_text = alias_name_child.text.strip()
                elif e.text and e.text.strip():
                    alias_text = e.text.strip()
                if alias_text:
                    alias_values.append(alias_text)
        if not alias_values:
            alias_values = None

        address = {
            "type": {"id": None, "issuer": None, "schemeName": None},
            "careOf": None,
            "department": None,
            "subDepartment": None,
            "street": None,
            "buildingNumber": None,
            "buildingName": None,
            "floor": None,
            "unitNumber": None,
            "postBox": None,
            "room": None,
            "postalCode": None,
            "city": None,
            "townLocationName": None,
            "districtName": None,
            "state": None,
            "country": None,
            "addressLine": None,
            "addressLines": []
        }

        address_node = None
        for e in element.iter():
            if (e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag) == "PstlAdr":
                address_node = e
                break
        if address_node is not None:
            for c in address_node:
                cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                cl = cn.lower() if isinstance(cn, str) else cn
                if cn == "AdrTp":
                    for p in c.iter():
                        pn = p.tag.split("}")[-1] if isinstance(p.tag, str) else p.tag
                        if pn == "Prtry":
                            for q in p:
                                qn = q.tag.split("}")[-1] if isinstance(q.tag, str) else q.tag
                                if qn == "Id" and q.text and q.text.strip():
                                    address["type"]["id"] = q.text.strip()
                                elif qn == "Issr" and q.text and q.text.strip():
                                    address["type"]["issuer"] = q.text.strip()
                                elif qn == "SchmeNm" and q.text and q.text.strip():
                                    address["type"]["schemeName"] = q.text.strip()
                elif cl == "careof" and c.text and c.text.strip():
                    address["careOf"] = c.text.strip()
                elif cn == "Dept" and c.text and c.text.strip():
                    address["department"] = c.text.strip()
                elif cn == "SubDept" and c.text and c.text.strip():
                    address["subDepartment"] = c.text.strip()
                elif cn == "StrtNm" and c.text and c.text.strip():
                    address["street"] = c.text.strip()
                elif cn == "BldgNb" and c.text and c.text.strip():
                    address["buildingNumber"] = c.text.strip()
                elif cn == "BldgNm" and c.text and c.text.strip():
                    address["buildingName"] = c.text.strip()
                elif cn == "Flr" and c.text and c.text.strip():
                    address["floor"] = c.text.strip()
                elif cn == "UnitNb" and c.text and c.text.strip():
                    address["unitNumber"] = c.text.strip()
                elif cn == "PstBx" and c.text and c.text.strip():
                    address["postBox"] = c.text.strip()
                elif cn == "Room" and c.text and c.text.strip():
                    address["room"] = c.text.strip()
                elif cl in ("pstcd", "postcd") and c.text and c.text.strip():
                    address["postalCode"] = c.text.strip()
                elif cl in ("twnnm", "townnm") and c.text and c.text.strip():
                    address["city"] = c.text.strip()
                elif cn == "TwnLctnNm" and c.text and c.text.strip():
                    address["townLocationName"] = c.text.strip()
                elif cn == "DstrctNm" and c.text and c.text.strip():
                    address["districtName"] = c.text.strip()
                elif cn == "CtrySubDvsn" and c.text and c.text.strip():
                    address["state"] = c.text.strip()
                elif cn in ("Ctry", "CtryCd") and c.text and c.text.strip():
                    address["country"] = c.text.strip()
                elif cn == "AdrLine" and c.text and c.text.strip():
                    address["addressLines"].append(c.text.strip())
            if address["addressLines"] and not address.get("addressLine"):
                address["addressLine"] = address["addressLines"][0]

        if not address.get("street") and not address.get("city") and not address.get("postalCode") and not address.get("country"):
            nm_and_adr_node = None
            for e in element.iter():
                if (e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag) == "NmAndAdr":
                    nm_and_adr_node = e
                    break
            if nm_and_adr_node is not None:
                adr_node = None
                for c in nm_and_adr_node:
                    if (c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag) == "Adr":
                        adr_node = c
                        break
                if adr_node is not None:
                    for c in adr_node:
                        cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                        if cn == "StrtNm" and c.text and c.text.strip():
                            address["street"] = c.text.strip()
                        elif cn == "BldgNb" and c.text and c.text.strip():
                            address["buildingNumber"] = c.text.strip()
                        elif cn in ("TwnNm", "TownNm") and c.text and c.text.strip():
                            address["city"] = c.text.strip()
                        elif cn in ("PstCd", "PostCd") and c.text and c.text.strip():
                            address["postalCode"] = c.text.strip()
                        elif cn == "Ctry" and c.text and c.text.strip():
                            address["country"] = c.text.strip()
                        elif cn == "AdrLine" and c.text and c.text.strip():
                            address["addressLines"].append(c.text.strip())
                    if address["addressLines"] and not address.get("addressLine"):
                        address["addressLine"] = address["addressLines"][0]

        if not address.get("street") and not address.get("city") and not address.get("postalCode") and not address.get("country"):
            direct_adr_node = None
            for e in element.iter():
                if (e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag) == "Adr":
                    direct_adr_node = e
                    break
            if direct_adr_node is not None:
                for c in direct_adr_node:
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    if cn == "StrtNm" and c.text and c.text.strip():
                        address["street"] = c.text.strip()
                    elif cn == "BldgNb" and c.text and c.text.strip():
                        address["buildingNumber"] = c.text.strip()
                    elif cn in ("TwnNm", "TownNm") and c.text and c.text.strip():
                        address["city"] = c.text.strip()
                    elif cn in ("PstCd", "PostCd") and c.text and c.text.strip():
                        address["postalCode"] = c.text.strip()
                    elif cn in ("Ctry", "CtryCd") and c.text and c.text.strip():
                        address["country"] = c.text.strip()
                    elif cn == "AdrLine" and c.text and c.text.strip():
                        address["addressLines"].append(c.text.strip())
                if address["addressLines"] and not address.get("addressLine"):
                    address["addressLine"] = address["addressLines"][0]

        if not address.get("street") and not address.get("city") and not address.get("postalCode") and not address.get("country"):
            lctn_node = None
            for e in element.iter():
                if (e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag) == "Lctn":
                    lctn_node = e
                    break
            if lctn_node is not None:
                for c in lctn_node:
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    if cn == "StrtNm" and c.text and c.text.strip():
                        address["street"] = c.text.strip()
                    elif cn in ("BldgNb", "BldgNm") and c.text and c.text.strip():
                        address["buildingNumber"] = c.text.strip()
                    elif cn in ("PstCd", "PostCd") and c.text and c.text.strip():
                        address["postalCode"] = c.text.strip()
                    elif cn in ("TwnNm", "TownNm") and c.text and c.text.strip():
                        address["city"] = c.text.strip()
                    elif cn in ("CtrySubDvsn",) and c.text and c.text.strip():
                        address["state"] = c.text.strip()
                    elif cn in ("Ctry", "CtryCd") and c.text and c.text.strip():
                        address["country"] = c.text.strip()
                    elif cn == "AdrLine" and c.text and c.text.strip():
                        address["addressLines"].append(c.text.strip())
                if address["addressLines"] and not address.get("addressLine"):
                    address["addressLine"] = address["addressLines"][0]

        identifiers = {"id": None, "anyBIC": None, "lei": None, "other": []}
        for child in list(element):
            child_name = child.tag.split("}")[-1] if isinstance(child.tag, str) else child.tag
            if child_name == "Id" and child.text and child.text.strip():
                identifiers["id"] = child.text.strip()
                break
        for e in element.iter():
            en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if en == "OrgId":
                for sub in e.iter():
                    sn = sub.tag.split("}")[-1] if isinstance(sub.tag, str) else sub.tag
                    if sn == "AnyBIC" and sub.text and sub.text.strip():
                        identifiers["anyBIC"] = sub.text.strip()
                    elif sn == "LEI" and sub.text and sub.text.strip():
                        identifiers["lei"] = sub.text.strip()
                    elif sn == "Othr":
                        id_text = None
                        scheme_text = None
                        issuer_text = None
                        for x in sub:
                            xn = x.tag.split("}")[-1] if isinstance(x.tag, str) else x.tag
                            if xn == "Id" and x.text and x.text.strip():
                                id_text = x.text.strip()
                            elif xn == "SchmeNm":
                                for y in x:
                                    yn = y.tag.split("}")[-1] if isinstance(y.tag, str) else y.tag
                                    if yn == "Prtry" and y.text and y.text.strip():
                                        scheme_text = y.text.strip()
                            elif xn == "Issr" and x.text and x.text.strip():
                                issuer_text = x.text.strip()
                        if id_text or scheme_text or issuer_text:
                            identifiers["other"].append({"id": id_text, "scheme": scheme_text, "issuer": issuer_text})
        if identifiers.get("lei") is None:
            for e in element.iter():
                if (e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag) == "LEI" and e.text and e.text.strip():
                    identifiers["lei"] = e.text.strip()
                    break

        country_of_residence_value = None
        residency_status_value = None
        date_of_birth_value = None
        place_of_birth_value = None
        province_of_birth_value = None
        city_of_birth_value = None
        country_of_birth_value = None
        contact_person_prefix = None
        contact_person_name = None
        contact_phone = None
        contact_mobile = None
        contact_fax = None
        contact_url = None
        contact_email = None
        contact_email_purpose = None
        contact_job_title = None
        contact_responsibility = None
        contact_department = None
        contact_channel_type = None
        contact_channel_id = None
        contact_preferred_method = None

        for e in element.iter():
            en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if en in ("CtryOfRes", "CountryOfResidence") and e.text and e.text.strip() and not country_of_residence_value:
                country_of_residence_value = e.text.strip()
            if en == "CtryAndResdtlSts":
                for c in e:
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    if cn == "Ctry" and c.text and c.text.strip():
                        country_of_residence_value = c.text.strip()
                    elif cn == "ResdtlSts" and c.text and c.text.strip():
                        residency_status_value = c.text.strip()
            if en == "BirthDt" and e.text and e.text.strip() and not date_of_birth_value:
                date_of_birth_value = e.text.strip()
            if en == "DtAndPlcOfBirth":
                for c in e:
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    if cn == "BirthDt" and c.text and c.text.strip():
                        date_of_birth_value = c.text.strip()
                    elif cn == "PrvcOfBirth" and c.text and c.text.strip():
                        province_of_birth_value = c.text.strip()
                    elif cn == "CityOfBirth" and c.text and c.text.strip():
                        city_of_birth_value = c.text.strip()
                    elif cn == "CtryOfBirth" and c.text and c.text.strip():
                        country_of_birth_value = c.text.strip()
                    elif cn == "City" and c.text and c.text.strip() and not place_of_birth_value:
                        place_of_birth_value = c.text.strip()
            if en == "CtctDtls":
                for c in e:
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    if cn == "NmPrfx" and c.text and c.text.strip():
                        contact_person_prefix = c.text.strip()
                    elif cn == "Nm" and c.text and c.text.strip():
                        contact_person_name = c.text.strip()
                    elif cn == "PhneNb" and c.text and c.text.strip():
                        contact_phone = c.text.strip()
                    elif cn == "MobNb" and c.text and c.text.strip():
                        contact_mobile = c.text.strip()
                    elif cn == "FaxNb" and c.text and c.text.strip():
                        contact_fax = c.text.strip()
                    elif cn == "URLAdr" and c.text and c.text.strip():
                        contact_url = c.text.strip()
                    elif cn == "EmailAdr" and c.text and c.text.strip():
                        contact_email = c.text.strip()
                    elif cn == "EmailPurp" and c.text and c.text.strip():
                        contact_email_purpose = c.text.strip()
                    elif cn == "JobTitl" and c.text and c.text.strip():
                        contact_job_title = c.text.strip()
                    elif cn == "Rspnsblty" and c.text and c.text.strip():
                        contact_responsibility = c.text.strip()
                    elif cn == "Dept" and c.text and c.text.strip():
                        contact_department = c.text.strip()
                    elif cn == "Othr":
                        chan_tp = None
                        chan_id = None
                        for z in c:
                            zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                            if zn == "ChanlTp" and z.text and z.text.strip():
                                chan_tp = z.text.strip()
                            elif zn == "Id" and z.text and z.text.strip():
                                chan_id = z.text.strip()
                        if chan_tp:
                            contact_channel_type = chan_tp
                        if chan_id:
                            contact_channel_id = chan_id
                    elif cn == "PrefrdMtd" and c.text and c.text.strip():
                        contact_preferred_method = c.text.strip()
            if en == "PhneNb" and e.text and e.text.strip() and not contact_phone:
                contact_phone = e.text.strip()
            if en == "EmailAdr" and e.text and e.text.strip() and not contact_email:
                contact_email = e.text.strip()
            if en == "Dept" and e.text and e.text.strip() and not contact_department:
                contact_department = e.text.strip()

        iban_value = None
        other_account_value = None
        other_accounts = []
        account_currency_value = None
        account_id_value = None

        for e in element.iter():
            en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if en == "IBAN" and e.text and e.text.strip() and not iban_value:
                iban_value = e.text.strip()
            elif en == "Othr":
                id_child = None
                scheme_child_text = None
                issuer_child_text = None
                for c in list(e):
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    if cn == "Id" and c.text and c.text.strip():
                        id_child = c
                    elif cn == "SchmeNm":
                        for pr in c:
                            pn = pr.tag.split("}")[-1] if isinstance(pr.tag, str) else pr.tag
                            if pn == "Prtry" and pr.text and pr.text.strip():
                                scheme_child_text = pr.text.strip()
                    elif cn == "Issr":
                        if c.text and c.text.strip():
                            issuer_child_text = c.text.strip()
                if id_child is not None and id_child.text and id_child.text.strip():
                    if not other_account_value:
                        other_account_value = id_child.text.strip()
                    other_accounts.append({
                        "id": id_child.text.strip(),
                        "scheme": scheme_child_text,
                        "issuer": issuer_child_text
                    })
                elif e.text and e.text.strip() and not other_account_value:
                    other_account_value = e.text.strip()
            elif en == "Ccy" and e.text and e.text.strip() and not account_currency_value:
                account_currency_value = e.text.strip()
            elif en == "AcctId":
                direct_text_value = e.text.strip() if e.text and e.text.strip() else None
                nested_value = None
                for c in e:
                    if (c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag) == "Id" and c.text and c.text.strip():
                        nested_value = c.text.strip()
                if nested_value or direct_text_value:
                    account_id_value = nested_value or direct_text_value
            elif en == "SfkpgAcct":
                for c in e.iter():
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    if cn == "Id" and c.text and c.text.strip():
                        account_id_value = c.text.strip()

        bic_value = None
        financial_institution_other = []
        financial_institution_lei = None
        clearing_system_id = None
        clearing_member_id = None
        branch_object = None
        any_bic_value = None
        prtry_id_value = None
        prtry_id_scheme = None
        prtry_id_issuer = None

        for e in element.iter():
            en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if en == "BICFI" and e.text and e.text.strip():
                bic_value = e.text.strip()
            elif en == "AnyBIC" and e.text and e.text.strip():
                any_bic_value = e.text.strip()
            elif en == "PrtryId":
                id_text = None
                scheme_text = None
                issuer_text = None
                for y in e:
                    yn = y.tag.split("}")[-1] if isinstance(y.tag, str) else y.tag
                    if yn == "Id" and y.text and y.text.strip():
                        id_text = y.text.strip()
                    elif yn == "SchmeNm" and y.text and y.text.strip():
                        scheme_text = y.text.strip()
                    elif yn == "Issr" and y.text and y.text.strip():
                        issuer_text = y.text.strip()
                prtry_id_value = id_text or prtry_id_value
                prtry_id_scheme = scheme_text or prtry_id_scheme
                prtry_id_issuer = issuer_text or prtry_id_issuer
                if id_text or scheme_text:
                    financial_institution_other.append({"id": id_text, "scheme": scheme_text})
            elif en == "FinInstnId":
                for sub in e:
                    sn = sub.tag.split("}")[-1] if isinstance(sub.tag, str) else sub.tag
                    if sn == "BICFI" and sub.text and sub.text.strip():
                        bic_value = sub.text.strip()
                    elif sn == "AnyBIC" and sub.text and sub.text.strip():
                        any_bic_value = sub.text.strip()
                    elif sn == "LEI" and sub.text and sub.text.strip():
                        financial_institution_lei = sub.text.strip()
                    elif sn == "ClrSysMmbId":
                        for y in sub:
                            yn = y.tag.split("}")[-1] if isinstance(y.tag, str) else y.tag
                            if yn == "ClrSysId":
                                for z in y:
                                    zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                                    if zn == "Cd" and z.text and z.text.strip():
                                        clearing_system_id = z.text.strip()
                            elif yn == "MmbId" and y.text and y.text.strip():
                                clearing_member_id = y.text.strip()
                    elif sn == "Othr":
                        id_text = None
                        scheme_text = None
                        for y in sub:
                            yn = y.tag.split("}")[-1] if isinstance(y.tag, str) else y.tag
                            if yn == "Id" and y.text and y.text.strip():
                                id_text = y.text.strip()
                            elif yn == "SchmeNm":
                                for z in y:
                                    zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                                    if zn == "Prtry" and z.text and z.text.strip():
                                        scheme_text = z.text.strip()
                        if id_text or scheme_text:
                            financial_institution_other.append({"id": id_text, "scheme": scheme_text})
            elif en == "BrnchId":
                b_id = None
                b_lei = None
                b_name = None
                b_address = {}
                for sub in e:
                    sn = sub.tag.split("}")[-1] if isinstance(sub.tag, str) else sub.tag
                    if sn == "Id" and sub.text and sub.text.strip():
                        b_id = sub.text.strip()
                    elif sn == "LEI" and sub.text and sub.text.strip():
                        b_lei = sub.text.strip()
                    elif sn == "Nm" and sub.text and sub.text.strip():
                        b_name = sub.text.strip()
                    elif sn == "PstlAdr":
                        ba = {
                            "street": None,
                            "buildingNumber": None,
                            "postalCode": None,
                            "city": None,
                            "state": None,
                            "country": None,
                            "addressLine": None,
                            "addressLines": []
                        }
                        for q in sub:
                            qn = q.tag.split("}")[-1] if isinstance(q.tag, str) else q.tag
                            if qn == "StrtNm" and q.text and q.text.strip():
                                ba["street"] = q.text.strip()
                            elif qn == "BldgNb" and q.text and q.text.strip():
                                ba["buildingNumber"] = q.text.strip()
                            elif qn in ("PstCd", "PostCd") and q.text and q.text.strip():
                                ba["postalCode"] = q.text.strip()
                            elif qn in ("TwnNm", "TownNm") and q.text and q.text.strip():
                                ba["city"] = q.text.strip()
                            elif qn == "CtrySubDvsn" and q.text and q.text.strip():
                                ba["state"] = q.text.strip()
                            elif qn in ("Ctry", "CtryCd") and q.text and q.text.strip():
                                ba["country"] = q.text.strip()
                            elif qn == "AdrLine" and q.text and q.text.strip():
                                ba["addressLines"].append(q.text.strip())
                        if ba["addressLines"] and not ba.get("addressLine"):
                            ba["addressLine"] = ba["addressLines"][0]
                        b_address = ba
                branch_object = {"id": b_id, "lei": b_lei, "name": b_name, "address": b_address}

        if bic_value is None and any_bic_value:
            bic_value = any_bic_value
        if name_value is None and bic_value:
            name_value = bic_value
        if name_value is None and prtry_id_value:
            name_value = prtry_id_value

        names_acc = []
        for e in element.iter():
            tn = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if tn == "Nm" and e.text and e.text.strip():
                val = e.text.strip()
                if val not in names_acc:
                    names_acc.append(val)

        addresses_acc = []
        for e in element.iter():
            tn = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if tn in ("PstlAdr", "Adr"):
                addr_obj = {
                    "type": {"id": None, "issuer": None, "schemeName": None},
                    "careOf": None,
                    "department": None,
                    "subDepartment": None,
                    "street": None,
                    "buildingNumber": None,
                    "buildingName": None,
                    "floor": None,
                    "unitNumber": None,
                    "postBox": None,
                    "room": None,
                    "postalCode": None,
                    "city": None,
                    "townLocationName": None,
                    "districtName": None,
                    "state": None,
                    "country": None,
                    "addressLine": None,
                    "addressLines": []
                }
                for c in e:
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    cl = cn.lower() if isinstance(cn, str) else cn
                    if cn == "AdrTp":
                        for p in c.iter():
                            pn = p.tag.split("}")[-1] if isinstance(p.tag, str) else p.tag
                            if pn == "Prtry":
                                for q in p:
                                    qn = q.tag.split("}")[-1] if isinstance(q.tag, str) else q.tag
                                    if qn == "Id" and q.text and q.text.strip():
                                        addr_obj["type"]["id"] = q.text.strip()
                                    elif qn == "Issr" and q.text and q.text.strip():
                                        addr_obj["type"]["issuer"] = q.text.strip()
                                    elif qn == "SchmeNm":
                                        for r in q:
                                            rn = r.tag.split("}")[-1] if isinstance(r.tag, str) else r.tag
                                            if rn == "Prtry" and r.text and r.text.strip():
                                                addr_obj["type"]["schemeName"] = r.text.strip()
                    elif cl == "careof" and c.text and c.text.strip():
                        addr_obj["careOf"] = c.text.strip()
                    elif cn == "Dept" and c.text and c.text.strip():
                        addr_obj["department"] = c.text.strip()
                    elif cn == "SubDept" and c.text and c.text.strip():
                        addr_obj["subDepartment"] = c.text.strip()
                    elif cn == "StrtNm" and c.text and c.text.strip():
                        addr_obj["street"] = c.text.strip()
                    elif cn == "BldgNb" and c.text and c.text.strip():
                        addr_obj["buildingNumber"] = c.text.strip()
                    elif cn == "BldgNm" and c.text and c.text.strip():
                        addr_obj["buildingName"] = c.text.strip()
                    elif cn == "Flr" and c.text and c.text.strip():
                        addr_obj["floor"] = c.text.strip()
                    elif cn == "UnitNb" and c.text and c.text.strip():
                        addr_obj["unitNumber"] = c.text.strip()
                    elif cn == "PstBx" and c.text and c.text.strip():
                        addr_obj["postBox"] = c.text.strip()
                    elif cn == "Room" and c.text and c.text.strip():
                        addr_obj["room"] = c.text.strip()
                    elif cl in ("pstcd", "postcd") and c.text and c.text.strip():
                        addr_obj["postalCode"] = c.text.strip()
                    elif cl in ("twnnm", "townnm") and c.text and c.text.strip():
                        addr_obj["city"] = c.text.strip()
                    elif cn == "TwnLctnNm" and c.text and c.text.strip():
                        addr_obj["townLocationName"] = c.text.strip()
                    elif cn == "DstrctNm" and c.text and c.text.strip():
                        addr_obj["districtName"] = c.text.strip()
                    elif cn == "CtrySubDvsn" and c.text and c.text.strip():
                        addr_obj["state"] = c.text.strip()
                    elif cn in ("Ctry", "CtryCd") and c.text and c.text.strip():
                        addr_obj["country"] = c.text.strip()
                    elif cn == "AdrLine" and c.text and c.text.strip():
                        addr_obj["addressLines"].append(c.text.strip())
                if addr_obj["addressLines"] and not addr_obj.get("addressLine"):
                    addr_obj["addressLine"] = addr_obj["addressLines"][0]
                if any(v for k, v in addr_obj.items() if k != "type") or any(v for v in addr_obj["type"].values()) or addr_obj["addressLines"]:
                    addresses_acc.append(addr_obj)

        multi_names = names_acc if names_acc else None
        multi_addresses = addresses_acc if addresses_acc else None
        if not name_value and names_acc:
            name_value = names_acc[0]
        if not (address.get("street") or address.get("city") or address.get("postalCode") or address.get("country") or address.get("addressLines")) and addresses_acc:
            address = addresses_acc[0]

        parties.append({
            "role": canonical_role,
            "name": name_value,
            "names": multi_names,
            "aliases": alias_values,
            "address": address,
            "addresses": multi_addresses,
            "contact": {
                "countryOfResidence": country_of_residence_value,
                "residencyStatus": residency_status_value,
                "placeOfBirth": place_of_birth_value,
                "dateOfBirth": date_of_birth_value,
                "provinceOfBirth": province_of_birth_value,
                "cityOfBirth": city_of_birth_value,
                "countryOfBirth": country_of_birth_value,
                "prefix": contact_person_prefix,
                "contactName": contact_person_name,
                "phone": contact_phone,
                "mobile": contact_mobile,
                "fax": contact_fax,
                "url": contact_url,
                "email": contact_email,
                "emailPurpose": contact_email_purpose,
                "jobTitle": contact_job_title,
                "responsibility": contact_responsibility,
                "department": contact_department,
                "channelType": contact_channel_type,
                "channelId": contact_channel_id,
                "preferredMethod": contact_preferred_method
            },
            "account": {
                "iban": iban_value,
                "other": other_account_value,
                "others": other_accounts,
                "bic": bic_value,
                "currency": account_currency_value,
                "name": None,
                "accountId": account_id_value
            },
            "identifiers": identifiers,
            "financialInstitution": {
                "bic": bic_value,
                "lei": financial_institution_lei,
                "clearingSystemId": clearing_system_id,
                "clearingMemberId": clearing_member_id,
                "other": financial_institution_other,
                "branch": branch_object
            }
        })

    safeguard_seen = set()
    addr_like_tags = {"PstlAdr", "Adr", "NmAndAdr", "Lctn"}
    addr_field_tags = {
        "StrtNm": "street", "BldgNb": "buildingNumber", "BldgNm": "buildingName", "Flr": "floor", "UnitNb": "unitNumber",
        "PstBx": "postBox", "Room": "room", "PstCd": "postalCode", "PostCd": "postalCode",
        "TwnNm": "city", "TownNm": "city", "TwnLctnNm": "townLocationName", "DstrctNm": "districtName",
        "CtrySubDvsn": "state", "Ctry": "country", "CtryCd": "country", "AdrLine": "addressLine",
        "Dept": "department", "SubDept": "subDepartment"
    }

    extra_parties = _detect_unmapped_parties(document_element, canonical_role_map, seen_party_elements)
    if extra_parties:
        parties.extend(extra_parties)

    account_role_to_party_role = {
        "DbtrAcct": "debtor",
        "CdtrAcct": "creditor",
        "UltmtDbtrAcct": "ultimateDebtor",
        "UltmtCdtrAcct": "ultimateCreditor"
    }

    role_to_first_index = {}
    for i, p in enumerate(parties):
        if p.get("role") not in role_to_first_index:
            role_to_first_index[p.get("role")] = i

    for acct_tag, target_role in account_role_to_party_role.items():
        account_nodes = []
        for e in document_element.iter():
            if (e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag) == acct_tag:
                account_nodes.append(e)
        if not account_nodes:
            continue

        account_node = account_nodes[0]
        iban_text = None
        other_text = None
        others_list = []
        currency_text = None
        display_name_text = None
        account_id_text = None

        for e in account_node.iter():
            n = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if n == "IBAN" and e.text and e.text.strip():
                iban_text = e.text.strip()
            elif n == "Othr":
                id_val = None
                scheme_val = None
                issuer_val = None
                for sub in e:
                    sn = sub.tag.split("}")[-1] if isinstance(sub.tag, str) else sub.tag
                    if sn == "Id" and sub.text and sub.text.strip():
                        id_val = sub.text.strip()
                    elif sn == "SchmeNm":
                        for pr in sub:
                            prn = pr.tag.split("}")[-1] if isinstance(pr.tag, str) else pr.tag
                            if prn == "Prtry" and pr.text and pr.text.strip():
                                scheme_val = pr.text.strip()
                    elif sn == "Issr" and sub.text and sub.text.strip():
                        issuer_val = sub.text.strip()
                if id_val:
                    if other_text is None:
                        other_text = id_val
                    others_list.append({"id": id_val, "scheme": scheme_val, "issuer": issuer_val})
            elif n == "Ccy" and e.text and e.text.strip():
                currency_text = e.text.strip()
            elif n == "Nm" and e.text and e.text.strip():
                display_name_text = e.text.strip()
            elif n == "AcctId":
                for c in e:
                    if (c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag) == "Id" and c.text and c.text.strip():
                        account_id_text = c.text.strip()
                if e.text and e.text.strip() and not account_id_text:
                    account_id_text = e.text.strip()
            elif n == "SfkpgAcct":
                for c in e.iter():
                    cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                    if cn == "Id" and c.text and c.text.strip():
                        account_id_text = c.text.strip()

        if target_role in role_to_first_index:
            idx = role_to_first_index[target_role]
            account_object = parties[idx].get("account") or {}
            if iban_text:
                account_object["iban"] = iban_text
            if other_text:
                if not account_object.get("other") or not str(account_object.get("other")).startswith("ACC-"):
                    account_object["other"] = other_text
            if others_list:
                account_object["others"] = (account_object.get("others") or []) + [
                    x for x in others_list if x not in (account_object.get("others") or [])
                ]
            if currency_text:
                account_object["currency"] = currency_text if not account_object.get("currency") else account_object.get("currency")
            if display_name_text:
                account_object["name"] = display_name_text if not account_object.get("name") else account_object.get("name")
            if account_id_text:
                account_object["accountId"] = account_id_text if not account_object.get("accountId") else account_object.get("accountId")
            parties[idx]["account"] = account_object

    for inv in investment_accounts:
        owner_name_value = inv.get("ownerName")
        acct_id_value = inv.get("acctId")
        acct_name_value = inv.get("acctName")
        if not owner_name_value or not acct_id_value:
            continue
        for p in parties:
            if p.get("role") == "accountOwner":
                party_name_value = p.get("name") or ""
                if party_name_value and party_name_value.strip().lower() == owner_name_value.strip().lower():
                    account_object = p.get("account") or {}
                    if not account_object.get("accountId"):
                        account_object["accountId"] = acct_id_value
                    if acct_name_value and not account_object.get("name"):
                        account_object["name"] = acct_name_value
                    p["account"] = account_object
                    break

    for element in document_element.iter():
        local_name = element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag
        if local_name in canonical_role_map:
            continue
        element_id_value = id(element)
        if element_id_value in seen_party_elements:
            continue
        has_name = False
        has_address = False
        for e in element.iter():
            en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if en == "Nm" and e.text and e.text.strip():
                has_name = True
            if en in ("PstlAdr", "Adr"):
                has_address = True
        if not (has_name and has_address):
            continue
        cur = element
        skip_due_to_ancestor = False
        while cur in parent_map:
            cur = parent_map[cur]
            if id(cur) in seen_party_elements:
                skip_due_to_ancestor = True
                break
        if skip_due_to_ancestor:
            continue

        name_value = None
        for e in element.iter():
            en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if en == "Nm" and e.text and e.text.strip():
                name_value = e.text.strip()
                break

        address_obj = {
            "type": {"id": None, "issuer": None, "schemeName": None},
            "careOf": None, "department": None, "subDepartment": None,
            "street": None, "buildingNumber": None, "buildingName": None, "floor": None, "unitNumber": None,
            "postBox": None, "room": None, "postalCode": None, "city": None,
            "townLocationName": None, "districtName": None, "state": None, "country": None,
            "addressLine": None, "addressLines": []
        }
        direct_adr_node = None
        pstl_adr_node = None
        for e in element.iter():
            en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if en == "PstlAdr":
                pstl_adr_node = e
                break
        if pstl_adr_node is None:
            for e in element.iter():
                en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
                if en == "Adr":
                    direct_adr_node = e
                    break
        adr_node = pstl_adr_node or direct_adr_node
        if adr_node is not None:
            for c in adr_node:
                cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                cl = cn.lower() if isinstance(cn, str) else cn
                if cn == "AdrTp":
                    for p in c.iter():
                        pn = p.tag.split("}")[-1] if isinstance(p.tag, str) else p.tag
                        if pn == "Prtry":
                            for q in p:
                                qn = q.tag.split("}")[-1] if isinstance(q.tag, str) else q.tag
                                if qn == "Id" and q.text and q.text.strip():
                                    address_obj["type"]["id"] = q.text.strip()
                                elif qn == "Issr" and q.text and q.text.strip():
                                    address_obj["type"]["issuer"] = q.text.strip()
                                elif qn == "SchmeNm" and q.text and q.text.strip():
                                    address_obj["type"]["schemeName"] = q.text.strip()
                elif cn == "StrtNm" and c.text and c.text.strip():
                    address_obj["street"] = c.text.strip()
                elif cn == "BldgNb" and c.text and c.text.strip():
                    address_obj["buildingNumber"] = c.text.strip()
                elif cn in ("TwnNm", "TownNm") and c.text and c.text.strip():
                    address_obj["city"] = c.text.strip()
                elif cn in ("PstCd", "PostCd") and c.text and c.text.strip():
                    address_obj["postalCode"] = c.text.strip()
                elif cn == "CtrySubDvsn" and c.text and c.text.strip():
                    address_obj["state"] = c.text.strip()
                elif cn in ("Ctry", "CtryCd") and c.text and c.text.strip():
                    address_obj["country"] = c.text.strip()
                elif cn == "AdrLine" and c.text and c.text.strip():
                    address_obj["addressLines"].append(c.text.strip())
            if address_obj["addressLines"] and not address_obj.get("addressLine"):
                address_obj["addressLine"] = address_obj["addressLines"][0]

        alias_values = []
        for e in element.iter():
            en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
            if en in ("Alia", "Alias"):
                if e.text and e.text.strip():
                    alias_values.append(e.text.strip())
                else:
                    for c in e:
                        if (c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag) == "Nm" and c.text and c.text.strip():
                            alias_values.append(c.text.strip())
                            break

        parties.append({
            "role": "party",
            "name": name_value,
            "names": [name_value] if name_value else None,
            "aliases": alias_values or None,
            "address": address_obj,
            "addresses": [address_obj],
            "contact": {
                "countryOfResidence": None, "residencyStatus": None, "placeOfBirth": None, "dateOfBirth": None,
                "provinceOfBirth": None, "cityOfBirth": None, "countryOfBirth": None,
                "prefix": None, "contactName": None, "phone": None, "mobile": None, "fax": None,
                "url": None, "email": None, "emailPurpose": None, "jobTitle": None,
                "responsibility": None, "department": None, "channelType": None, "channelId": None,
                "preferredMethod": None
            },
            "account": {"iban": None, "other": None, "others": [], "bic": None, "currency": None, "name": None, "accountId": None},
            "identifiers": {"id": None, "anyBIC": None, "lei": None, "other": []},
            "financialInstitution": {"bic": None, "lei": None, "clearingSystemId": None, "clearingMemberId": None, "other": [], "branch": None}
        })

    settlement_date_value = None
    cash_settlement_date_value = None
    requested_future_trade_date_value = None
    order_date_time_value = None
    place_of_trade_exchange_value = None
    pool_reference_value = None
    previous_reference_value = None
    master_reference_value = None
    original_receiver_bic_value = None
    total_settlement_amount_value = None
    total_settlement_amount_currency_value = None
    extension_list = []

    for element in document_element.iter():
        ancestor_is_order = False
        cur = element
        while cur in parent_map:
            cur = parent_map[cur]
            if (cur.tag.split("}")[-1] if isinstance(cur.tag, str) else cur.tag) == "IndvOrdrDtls":
                ancestor_is_order = True
                break
        if ancestor_is_order:
            continue
        tag_name = element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag
        if tag_name in ("ReqdExctnDt", "IntrBkSttlmDt", "SttlmDt") and element.text and element.text.strip():
            settlement_date_value = element.text.strip()
        if tag_name in ("CshSttlmDt",) and element.text and element.text.strip():
            cash_settlement_date_value = element.text.strip()
        if tag_name in ("ReqdFutrTradDt",) and element.text and element.text.strip():
            requested_future_trade_date_value = element.text.strip()
        if tag_name in ("OrdrDtTm",) and element.text and element.text.strip():
            order_date_time_value = element.text.strip()
        if tag_name == "PlcOfTrad":
            for c in element:
                if (c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag) == "Xchg" and c.text and c.text.strip():
                    place_of_trade_exchange_value = c.text.strip()
        if tag_name == "PoolRef":
            for c in element:
                if (c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag) == "Ref" and c.text and c.text.strip():
                    pool_reference_value = c.text.strip()
        if tag_name == "PrvsRef":
            for c in element:
                if (c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag) == "Ref" and c.text and c.text.strip():
                    previous_reference_value = c.text.strip()
        if tag_name in ("MstrRef", "MstrId") and element.text and element.text.strip():
            master_reference_value = element.text.strip()
        if tag_name == "CpyDtls":
            for c in element.iter():
                cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                if cn == "OrgnlRcvr":
                    for z in c.iter():
                        zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                        if zn == "BICFI" and z.text and z.text.strip():
                            original_receiver_bic_value = z.text.strip()
                        elif z.text and z.text.strip() and original_receiver_bic_value is None:
                            original_receiver_bic_value = z.text.strip()
        if tag_name == "TtlSttlmAmt":
            if element.get("Ccy") and element.text and element.text.strip():
                total_settlement_amount_value = element.text.strip()
                total_settlement_amount_currency_value = element.get("Ccy")
        if tag_name == "Xtnsn":
            place_and_name_value = None
            text_value = None
            for c in element:
                cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                if cn == "PlcAndNm" and c.text and c.text.strip():
                    place_and_name_value = c.text.strip()
                elif cn == "Txt" and c.text and c.text.strip():
                    text_value = c.text.strip()
            if place_and_name_value or text_value:
                extension_list.append({"placeAndName": place_and_name_value, "text": text_value})

    undertaking_id_value = None
    applicant_reference_value = None
    requested_expiry_date_value = None
    bank_instr_text_value = None
    bank_instr_last_date_value = None
    demand_id_value = None
    demand_submission_dt_value = None
    demand_amount_value = None
    demand_amount_currency_value = None
    demand_additional_info_value = None
    enclosures_list = []
    transaction_additional_info_value = None

    for element in document_element.iter():
        tag_name = element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag
        if tag_name == "XtndOrPayReqDtls":
            for e in element.iter():
                en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
                if en == "UdrtkgId":
                    for u in e.iter():
                        un = u.tag.split("}")[-1] if isinstance(u.tag, str) else u.tag
                        if un == "Id" and u.text and u.text.strip():
                            undertaking_id_value = u.text.strip()
                        elif un == "ApplcntRefNb" and u.text and u.text.strip():
                            applicant_reference_value = u.text.strip()
                elif en == "ReqdXpryDt" and e.text and e.text.strip():
                    requested_expiry_date_value = e.text.strip()
                elif en == "BkInstrs":
                    for b in e:
                        bn = b.tag.split("}")[-1] if isinstance(b.tag, str) else b.tag
                        if bn == "Txt" and b.text and b.text.strip():
                            bank_instr_text_value = b.text.strip()
                        elif bn == "LastDtForRspn" and b.text and b.text.strip():
                            bank_instr_last_date_value = b.text.strip()
                elif en == "DmndDtls":
                    for d in e.iter():
                        dn = d.tag.split("}")[-1] if isinstance(d.tag, str) else d.tag
                        if dn == "Id" and d.text and d.text.strip():
                            demand_id_value = d.text.strip()
                        elif dn == "SubmissnDtTm" and d.text and d.text.strip():
                            demand_submission_dt_value = d.text.strip()
                        elif dn == "Amt":
                            if d.text and d.text.strip():
                                demand_amount_value = d.text.strip()
                            ccy_attr = d.get("Ccy")
                            if ccy_attr:
                                demand_amount_currency_value = ccy_attr
                        elif dn == "AddtlInf" and d.text and d.text.strip():
                            demand_additional_info_value = d.text.strip()
                elif en == "AddtlInf" and e.text and e.text.strip():
                    if transaction_additional_info_value is None:
                        transaction_additional_info_value = e.text.strip()
                elif en == "NclsdFile":
                    type_id = None
                    type_scheme_name = None
                    type_issuer = None
                    file_id = None
                    file_format = None
                    file_content = None
                    for nf in e:
                        nfn = nf.tag.split("}")[-1] if isinstance(nf.tag, str) else nf.tag
                        if nfn == "Tp":
                            for tp in nf.iter():
                                tpn = tp.tag.split("}")[-1] if isinstance(tp.tag, str) else tp.tag
                                if tpn == "Prtry":
                                    for pr in tp:
                                        prn = pr.tag.split("}")[-1] if isinstance(pr.tag, str) else pr.tag
                                        if prn == "Id" and pr.text and pr.text.strip():
                                            type_id = pr.text.strip()
                                        elif prn == "Issr" and pr.text and pr.text.strip():
                                            type_issuer = pr.text.strip()
                                        elif prn == "SchmeNm":
                                            for q in pr:
                                                qn = q.tag.split("}")[-1] if isinstance(q.tag, str) else q.tag
                                                if qn == "Prtry" and q.text and q.text.strip():
                                                    type_scheme_name = q.text.strip()
                        elif nfn == "Id" and nf.text and nf.text.strip():
                            file_id = nf.text.strip()
                        elif nfn == "Frmt":
                            for fr in nf:
                                frn = fr.tag.split("}")[-1] if isinstance(fr.tag, str) else fr.tag
                                if frn == "Cd" and fr.text and fr.text.strip():
                                    file_format = fr.text.strip()
                        elif nfn in ("Nclsr", "NclsrCntt") and nf.text and nf.text.strip():
                            file_content = nf.text.strip()
                    enclosure_obj = {
                        "type": {"id": type_id, "schemeName": type_scheme_name, "issuer": type_issuer},
                        "id": file_id,
                        "format": file_format,
                        "contentBase64": file_content
                    }
                    if any(v for v in enclosure_obj.values()):
                        enclosures_list.append(enclosure_obj)

    orders_list = []
    for element in document_element.iter():
        if (element.tag.split("}")[-1] if isinstance(element.tag, str) else element.tag) != "IndvOrdrDtls":
            continue
        or_ref = None
        cl_ref = None
        units = None
        st_amt = None
        st_ccy = None
        cash_dt = None
        st_dt = None
        ord_isin = None
        ord_name = None
        dbtr_iban = None
        cdtr_iban = None
        dbtr_bic = None
        cdtr_bic = None
        for c in element.iter():
            cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
            if cn == "OrdrRef" and c.text and c.text.strip():
                or_ref = c.text.strip()
            elif cn == "ClntRef" and c.text and c.text.strip():
                cl_ref = c.text.strip()
            elif cn == "UnitsNb" and c.text and c.text.strip():
                units = c.text.strip()
            elif cn == "SttlmAmt" and c.get("Ccy") and c.text and c.text.strip():
                st_amt = c.text.strip()
                st_ccy = c.get("Ccy")
            elif cn in ("CshSttlmDt",) and c.text and c.text.strip():
                cash_dt = c.text.strip()
            elif cn in ("ReqdExctnDt", "SttlmDt") and c.text and c.text.strip():
                st_dt = c.text.strip()
            elif cn == "FinInstrmDtls":
                for z in c.iter():
                    zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                    if zn == "ISIN" and z.text and z.text.strip():
                        ord_isin = z.text.strip()
                    elif zn in ("Nm", "FullNm", "ShrtNm") and z.text and z.text.strip() and ord_name is None:
                        ord_name = z.text.strip()
            elif cn == "DbtrAcct":
                for z in c.iter():
                    zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                    if zn == "IBAN" and z.text and z.text.strip():
                        dbtr_iban = z.text.strip()
            elif cn == "CdtrAcct":
                for z in c.iter():
                    zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                    if zn == "IBAN" and z.text and z.text.strip():
                        cdtr_iban = z.text.strip()
            elif cn == "DbtrAgt":
                for z in c.iter():
                    zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                    if zn == "BICFI" and z.text and z.text.strip():
                        dbtr_bic = z.text.strip()
            elif cn == "CdtrAgt":
                for z in c.iter():
                    zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                    if zn == "BICFI" and z.text and z.text.strip():
                        cdtr_bic = z.text.strip()

        order_obj = {}
        if or_ref:
            order_obj["orderRef"] = or_ref
        if cl_ref:
            order_obj["clientRef"] = cl_ref
        if ord_isin or ord_name:
            order_obj["instrument"] = {"isin": ord_isin, "name": ord_name}
        if units:
            order_obj["units"] = units
        if st_amt or st_ccy or cash_dt or st_dt:
            order_obj["settlement"] = {"amount": {"value": st_amt, "currency": st_ccy}}
            if cash_dt:
                order_obj["settlement"]["cashSettlementDate"] = cash_dt
            if st_dt:
                order_obj["settlement"]["settlementDate"] = st_dt
        if dbtr_iban or dbtr_bic or cdtr_bic or cdtr_iban:
            order_obj["payment"] = {
                "debtorIban": dbtr_iban,
                "debtorAgentBic": dbtr_bic,
                "creditorAgentBic": cdtr_bic,
                "creditorIban": cdtr_iban
            }
        if order_obj:
            orders_list.append(order_obj)

    payment_instr_id_value = None
    payment_end_to_end_id_value = None
    payment_tx_id_value = None
    payment_amount_value = None
    payment_amount_currency_value = None
    service_level_code_value = None
    service_level_proprietary_value = None
    local_instrument_code_value = None
    local_instrument_proprietary_value = None
    category_purpose_code_value = None
    charge_bearer_value = None
    purpose_code_value = None
    remittance_information_value = None
    request_type_id_value = None
    request_type_scheme_value = None
    request_type_issuer_value = None

    for e in document_element.iter():
        en = e.tag.split("}")[-1] if isinstance(e.tag, str) else e.tag
        if en == "PmtId":
            for c in e:
                cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                if cn == "InstrId" and c.text and c.text.strip():
                    payment_instr_id_value = c.text.strip()
                elif cn == "EndToEndId" and c.text and c.text.strip():
                    payment_end_to_end_id_value = c.text.strip()
                elif cn == "TxId" and c.text and c.text.strip():
                    payment_tx_id_value = c.text.strip()
        elif en in ("InstdAmt", "IntrBkSttlmAmt", "Amt"):
            if e.text and e.text.strip():
                payment_amount_value = e.text.strip()
            ccy_attr = e.get("Ccy")
            if ccy_attr:
                payment_amount_currency_value = ccy_attr
        elif en == "PmtTpInf":
            for c in e.iter():
                cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                if cn == "SvcLvl":
                    for z in c:
                        zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                        if zn == "Cd" and z.text and z.text.strip():
                            service_level_code_value = z.text.strip()
                        elif zn == "Prtry" and z.text and z.text.strip():
                            service_level_proprietary_value = z.text.strip()
                elif cn == "LclInstrm":
                    for z in c:
                        zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                        if zn == "Cd" and z.text and z.text.strip():
                            local_instrument_code_value = z.text.strip()
                        elif zn == "Prtry" and z.text and z.text.strip():
                            local_instrument_proprietary_value = z.text.strip()
                elif cn == "CtgyPurp":
                    for z in c:
                        zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                        if zn == "Cd" and z.text and z.text.strip():
                            category_purpose_code_value = z.text.strip()
        elif en == "ChrgBr" and e.text and e.text.strip():
            charge_bearer_value = e.text.strip()
        elif en == "Purp":
            for c in e:
                cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                if cn == "Cd" and c.text and c.text.strip():
                    purpose_code_value = c.text.strip()
        elif en == "RmtInf":
            texts = []
            for c in e.iter():
                cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                if cn == "Ustrd" and c.text and c.text.strip():
                    texts.append(c.text.strip())
                if cn == "Ref" and c.text and c.text.strip():
                    texts.append(c.text.strip())
            if texts:
                remittance_information_value = " | ".join(texts)
        elif en == "ReqTp":
            for c in e:
                cn = c.tag.split("}")[-1] if isinstance(c.tag, str) else c.tag
                if cn == "Id" and c.text and c.text.strip():
                    request_type_id_value = c.text.strip()
                elif cn == "SchmeNm":
                    for z in c:
                        zn = z.tag.split("}")[-1] if isinstance(z.tag, str) else z.tag
                        if zn == "Prtry" and z.text and z.text.strip():
                            request_type_scheme_value = z.text.strip()
                elif cn == "Issr" and c.text and c.text.strip():
                    request_type_issuer_value = c.text.strip()

    def _is_currency_role(role):
        if not isinstance(role, str):
            return False
        if role == "Ccy":
            return True
        if role.endswith("Ccy"):
            return True
        return False

    parties = [p for p in parties if not _is_currency_role(p.get("role"))]

    parsed = {
        "sourceMessage": {"appHdr": application_header, "grpHdr": group_header},
        "transactions": [],
        "parties": parties,
        "metadata": {"ingestHash": ingest_hash}
    }

    parsed["transaction"] = {
        "messageType": application_header.get("msgDefId"),
        "paymentIdentification": {
            "instrId": payment_instr_id_value,
            "endToEndId": payment_end_to_end_id_value,
            "txId": payment_tx_id_value
        },
        "paymentInformationId": None,
        "paymentType": {
            "serviceLevel": {"code": service_level_code_value, "proprietary": service_level_proprietary_value} if (service_level_code_value or service_level_proprietary_value) else None,
            "localInstrument": {"code": local_instrument_code_value, "proprietary": local_instrument_proprietary_value} if (local_instrument_code_value or local_instrument_proprietary_value) else None,
            "categoryPurpose": {"code": category_purpose_code_value} if category_purpose_code_value else None
        },
        "amount": {"value": payment_amount_value, "currency": payment_amount_currency_value},
        "settlementDate": settlement_date_value,
        "cashSettlementDate": cash_settlement_date_value,
        "requestedFutureTradeDate": requested_future_trade_date_value,
        "orderDateTime": order_date_time_value,
        "placeOfTradeExchange": place_of_trade_exchange_value,
        "poolReference": pool_reference_value,
        "previousReference": previous_reference_value,
        "masterReference": master_reference_value,
        "originalReceiverBIC": original_receiver_bic_value,
        "settlementAmount": {"value": None, "currency": None},
        "totalSettlementAmount": {"value": total_settlement_amount_value, "currency": total_settlement_amount_currency_value},
        "unitsNumber": None,
        "chargeBearer": charge_bearer_value,
        "purposeCode": purpose_code_value,
        "remittanceInformation": remittance_information_value,
        "requestType": {"id": request_type_id_value, "schemeName": request_type_scheme_value, "issuer": request_type_issuer_value},
        "dataSetType": None,
        "extensions": extension_list,
        "orders": orders_list,
        "undertakingId": undertaking_id_value,
        "applicantReference": applicant_reference_value,
        "requestedExpiryDate": requested_expiry_date_value,
        "bankInstructions": {"text": bank_instr_text_value, "lastDateForResponse": bank_instr_last_date_value} if (bank_instr_text_value or bank_instr_last_date_value) else None,
        "demand": {
            "id": demand_id_value,
            "submissionDateTime": demand_submission_dt_value,
            "amount": {"value": demand_amount_value, "currency": demand_amount_currency_value},
            "additionalInfo": demand_additional_info_value
        } if (demand_id_value or demand_amount_value or demand_submission_dt_value or demand_additional_info_value) else None,
        "enclosures": enclosures_list if enclosures_list else None,
        "additionalInfo": transaction_additional_info_value
    }

    xml_schema_name_value = None
    bizsvc_text = (application_header.get("bizSvc") or "")[:256]
    bizsvc_lower = bizsvc_text.lower()
    document_ns = None
    if isinstance(document_element.tag, str) and "}" in document_element.tag:
        document_ns = document_element.tag.split("}")[0].strip("{")
    root_ns = None
    if isinstance(root_element.tag, str) and "}" in root_element.tag:
        root_ns = root_element.tag.split("}")[0].strip("{")
    if bizsvc_lower:
        if "cbpr" in bizsvc_lower:
            xml_schema_name_value = "CBPR+"
        elif "sepa" in bizsvc_lower:
            xml_schema_name_value = "SEPA"
        elif ".ch" in bizsvc_lower or "ch-" in bizsvc_lower or bizsvc_lower.endswith(".ch") or "swift.ch" in bizsvc_lower:
            xml_schema_name_value = "CH"
    if xml_schema_name_value is None and (root_ns or document_ns):
        ns_text = ((root_ns or "") + " " + (document_ns or "")).lower()
        if "cbpr" in ns_text or "swift" in ns_text:
            xml_schema_name_value = "CBPR+"
        elif ":ch:" in ns_text or ".ch." in ns_text or ns_text.endswith(".ch") or ns_text.endswith(":ch"):
            xml_schema_name_value = "CH"
    if xml_schema_name_value is None:
        if service_level_code_value and str(service_level_code_value).strip().upper() == "SEPA":
            xml_schema_name_value = "SEPA"
        elif (local_instrument_code_value and str(local_instrument_code_value).strip().upper().startswith("CH")) or (local_instrument_proprietary_value and str(local_instrument_proprietary_value).strip().upper().startswith("CH")):
            xml_schema_name_value = "CH"

    parsed["sourceMessage"]["xmlSchemaName"] = xml_schema_name_value
    schema_hints = {
        "bizSvc": application_header.get("bizSvc"),
        "serviceLevelCode": service_level_code_value,
        "serviceLevelProprietary": service_level_proprietary_value,
        "localInstrumentCode": local_instrument_code_value,
        "localInstrumentProprietary": local_instrument_proprietary_value
    }
    parsed.setdefault("metadata", {}).update({
        "xmlSchemaName": xml_schema_name_value,
        "schemaHints": schema_hints
    })
    return parsed


def buildbase(parsed):
    source_message = (parsed.get("sourceMessage") or {})
    application_header = source_message.get("appHdr") or {}
    message_definition = application_header.get("msgDefId")
    message_family = message_definition.split(".")[0] if message_definition else None
    parties = parsed.get("parties") or []
    role_priority = {"Debtor": 1, "InitiatingParty": 2, "AccountOwner": 3, "Creditor": 4}
    selected_party = None
    for party in sorted(parties, key=lambda p: role_priority.get(p.get("role"), 99)):
        selected_party = party
        break

    customer = None
    if selected_party is not None:
        customer = {
            "name": selected_party.get("name"),
            "identifiers": {
                "iban": (selected_party.get("account") or {}).get("iban"),
                "bic": (selected_party.get("account") or {}).get("bic")
            },
            "address": selected_party.get("address"),
        }

    bics_set = set()
    leis_set = set()
    ibans_set = set()
    for p in parties:
        acc = p.get("account") or {}
        ids = p.get("identifiers") or {}
        if acc.get("bic"):
            bics_set.add(acc.get("bic"))
        if ids.get("anyBIC"):
            bics_set.add(ids.get("anyBIC"))
        if ids.get("lei"):
            leis_set.add(ids.get("lei"))
        if acc.get("iban"):
            ibans_set.add(acc.get("iban"))

    identifiers_summary = {}
    if bics_set:
        identifiers_summary["bics"] = sorted(bics_set)
    if leis_set:
        identifiers_summary["leis"] = sorted(leis_set)
    if ibans_set:
        identifiers_summary["ibans"] = sorted(ibans_set)

    base = {
        "engineVersion": None,
        "screeningTimestamp": None,
        "caseId": None,
        "sources": [],
        "transactions": parsed.get("transactions") or [],
        "transaction": parsed.get("transaction"),
        "flag": "CLEAR",
        "matchStatus": "clear",
        "riskLevel": "low",
        "recommendedAction": "allow",
        "matches": [],
        "customer": customer,
        "totalHits": 0,
        "totalMatches": 0,
        "trace": {
            "messageDefinition": message_definition,
            "messageFamily": message_family,
            "originalBizMsgId": application_header.get("bizMsgId"),
            "groupMessageId": (parsed.get("sourceMessage") or {}).get("grpHdr", {}).get("msgId"),
            "xmlSchemaName": (parsed.get("metadata") or {}).get("xmlSchemaName"),
            "bizSvc": (source_message.get("appHdr") or {}).get("bizSvc")
        },
        "sourceMessage": parsed.get("sourceMessage"),
        "parties": parties,
        "metadata": {
            "apiVersion": "1.0",
            "responseId": str(uuid.uuid4()),
            "messageStandard": "ISO 20022",
            "messageDefinition": message_definition,
            "messageFamily": message_family,
            "ingestHash": (parsed.get("metadata") or {}).get("ingestHash"),
            "xmlSchemaName": (parsed.get("metadata") or {}).get("xmlSchemaName"),
            "schemaHints": (parsed.get("metadata") or {}).get("schemaHints"),
            "identifiers": identifiers_summary if identifiers_summary else None
        },
    }
    return base
