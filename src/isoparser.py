import xml.etree.ElementTree as ET
def _t(elem):
    return elem.text.strip() if elem is not None and elem.text else None
NS = {
    "msg": "urn:issettled", 
    "head": "urn:iso:std:iso:20022:tech:xsd:head.001.001.03",
    "pacs": "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.09",
}
def parse(xmlpath):
    tree = ET.parse(xmlpath)
    root = tree.getroot()
    app = root.find(".//msg:AppHdr", NS)
    appHdr = {
        "fromBIC": _t(app.find(".//head:Fr/head:FIId/head:FinInstnId/head:BICFII", NS)),
        "toBIC": _t(app.find(".//head:To/head:FIId/head:FinInstnId/head:BICFI", NS)),
        "bizMsgId": _t(app.find(".//head:BizMsgIdr", NS)),
        "msgDefId": _t(app.find(".//head:MsgDefIdr", NS)),
        "created": _t(app.find(".//head:CreDt", NS)),
    }
    grpHdr = root.find(".//pacs:GrpHdr", NS)
    grpHdr_out = {
        "msgId": _t(grpHdr.find("./pacs:MsgId", NS)),
        "createdDateTime": _t(grpHdr.find("./pacs:CreDtTm", NS)),
        "nbOfTxs": int(_t(grpHdr.find("./pacs:NbOfTxs", NS)) or 0),
        "settlementMethod": _t(grpHdr.find("./pacs:SttlmInf/pacs:SttlmMtd", NS)),
        "instructingAgentBIC": _t(grpHdr.find("./pacs:InstgAgt/pacs:FinInstnId/pacs:BICFI", NS)),
        "instructedAgentBIC": _t(grpHdr.find("./pacs:InstdAgt/pacs:FinInstnId/pacs:BICFI", NS)),
    }
    tx = root.find(".//pacs:CdtTrfTxInf", NS)
    pmtId = tx.find("./pacs:PmtId", NS)
    pmtTp = tx.find("./pacs:PmtTpInf", NS)
    amtEl = tx.find("./pacs:IntrBkSttlmAmt", NS)
    transaction = {
        "paymentIdentification": {
            "instrId": _t(pmtId.find("./pacs:InstrId", NS)),
            "endToEndId": _t(pmtId.find("./pacs:EndToEndId", NS)),
            "txId": _t(pmtId.find("./pacs:TxId", NS)),
        },
        "paymentType": {
            "serviceLevel": _t(pmtTp.find("./pacs:SvcLvl/pacs:Cd", NS)),
            "localInstrument": _t(pmtTp.find("./pacs:LclInstrm/pacs:Prtry", NS)),
            "categoryPurpose": _t(pmtTp.find("./pacs:CtgyPurp/pacs:Prtry", NS)),
        },
        "amount": {
            "value": float(_t(amtEl) or 0.0),
            "currency": amtEl.get("Ccy") if amtEl is not None else None
        },
        "settlementDate": _t(tx.find("./pacs:IntrBkSttlmDt", NS)),
        "chargeBearer": _t(tx.find("./pacs:ChrgBr", NS)),
        "purposeCode": _t(tx.find("./pacs:Purp/pacs:Cd", NS)),
        "remittanceInformation": _t(tx.find("./pacs:RmtInf/pacs:Ustrd", NS)),
    }
    def party(role, base):
        addr = base.find("./pacs:PstlAdr", NS)
        acct = base.getparent() if hasattr(base, "getparent") else None
        acctEl = tx.find(f"./pacs:{'DbtrAcct' if role=='Debtor' else 'CdtrAcct'}", NS)
        agentEl = tx.find(f"./pacs:{'DbtrAgt' if role=='Debtor' else 'CdtrAgt'}/pacs:FinInstnId/pacs:BICFI", NS)

        return {
            "role": role,
            "name": _t(base.find("./pacs:Nm", NS)),
            "address": {
                "street": _t(addr.find("./pacs:StrtNm", NS)) if addr is not None else None,
                "town": _t(addr.find("./pacs:TownNm", NS)) if addr is not None else None,
                "postCode": _t(addr.find("./pacs:PostCd", NS)) if addr is not None else None,
                "country": _t(addr.find("./pacs:Ctry", NS)) if addr is not None else None,
            },
            "contact": {
                "email": _t(base.find("./pacs:CtctDtls/pacs:EmailAdr", NS)),
            },
            "account": {
                "iban": _t(acctEl.find("./pacs:Id/pacs:IBAN", NS)) if acctEl is not None else None,
                "currency": _t(acctEl.find("./pacs:Ccy", NS)) if acctEl is not None else None,
            },
            "agentBIC": _t(agentEl),
        }

    parties = [
        party("Debtor", tx.find("./pacs:Dbtr", NS)),
        party("Creditor", tx.find("./pacs:Cdtr", NS)),
    ]

    return {
        "sourceMessage": {"appHdr": appHdr, "grpHdr": grpHdr_out},
        "transaction": transaction,
        "parties": parties
    }

def buildbase(parsed):
    appHdr = parsed.get("sourceMessage", {}).get("appHdr", {}) or {}
    created_at = appHdr.get("created")
    msg_def = appHdr.get("msgDefId")
    return {
    "metadata": {
    "apiVersion": "1.0",
    "responseId": "UUID-PLACEHOLDER",
    "createdAt": created_at,
    "sourceSystem": "ISO20022 Screen Engine",
    "environment": "dev",
    },
    "request": {
    "messageStandard": "ISO 20022",
    "messageDefinition": msg_def,
    "ingestHash": "SHA256-OF-RAW-MSG",
    },
    **parsed,
    }