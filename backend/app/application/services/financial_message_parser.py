"""Financial Message Standard Parsers (ISO 20022, SWIFT MT103, SEPA SCT).

Normalizes message schemas into structured transaction dicts.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any


class FinancialMessageParserError(Exception):
    """Raised when parsing fails or input is malformed."""

    pass


class FinancialMessageParser:
    """Ingests, parses, and normalizes standard financial transaction messages."""

    @staticmethod
    def parse_iso_20022_pacs008(xml_content: str) -> dict[str, Any]:
        """Parse ISO 20022 Customer Credit Transfer XML message (pacs.008.001.08)."""
        try:
            root = ET.fromstring(xml_content.strip())  # nosec B314
        except ET.ParseError as exc:
            raise FinancialMessageParserError(f"Invalid XML content: {exc}") from exc

        # Remove namespaces or resolve them dynamically to prevent lookup issues
        # We can extract namespace from root tag or use a namespace-wildcard approach
        ns = ""
        m = re.match(r"({.*})", root.tag)
        if m:
            ns = m.group(1)

        def find_text(element: ET.Element | None, path: str) -> str:
            if element is None:
                return ""
            parts = []
            for p in path.split("/"):
                if not p or p in (".", ".."):
                    parts.append(p)
                elif ns and not p.startswith(ns):
                    parts.append(f"{ns}{p}")
                else:
                    parts.append(p)
            ns_path = "/".join(parts)
            found = element.find(ns_path)
            return found.text.strip() if found is not None and found.text else ""

        # pacs.008 message structures nested under Document/FIToFICstmrCdtTrf/CdtTrfTxInf
        tx_info = root.find(f".//{ns}CdtTrfTxInf")
        if tx_info is None:
            raise FinancialMessageParserError(
                "CdtTrfTxInf (Credit Transfer Transaction Information) block not found in XML"
            )

        # Amount and Currency
        amt_elem = tx_info.find(f"{ns}IntrBkSttlmAmt")
        if amt_elem is None:
            raise FinancialMessageParserError("IntrBkSttlmAmt (Settlement Amount) is missing")
        try:
            amount = float(amt_elem.text.strip()) if amt_elem.text else 0.0
        except ValueError as exc:
            raise FinancialMessageParserError(f"Invalid amount value: {exc}") from exc
        currency = amt_elem.attrib.get("Ccy", "EUR")

        # Basic fields
        tx_id = (
            find_text(tx_info, "PmtId/EndToEndId")
            or find_text(tx_info, "PmtId/TxId")
            or "unknown_tx_id"
        )
        settlement_date = find_text(tx_info, "IntrBkSttlmDt")

        # Debtor (Sender)
        dbtr_name = find_text(tx_info, "Dbtr/Nm")
        dbtr_iban = find_text(tx_info, "DbtrAcct/Id/Othr/Id") or find_text(
            tx_info, "DbtrAcct/Id/IBAN"
        )
        dbtr_bic = find_text(tx_info, "DbtrAgt/FinInstnId/BICFI")
        dbtr_country = find_text(tx_info, "Dbtr/PstlAdr/Ctry") or (
            dbtr_iban[:2] if dbtr_iban else ""
        )

        # Creditor (Receiver)
        cdtr_name = find_text(tx_info, "Cdtr/Nm")
        cdtr_iban = find_text(tx_info, "CdtrAcct/Id/Othr/Id") or find_text(
            tx_info, "CdtrAcct/Id/IBAN"
        )
        cdtr_bic = find_text(tx_info, "CdtrAgt/FinInstnId/BICFI")
        cdtr_country = find_text(tx_info, "Cdtr/PstlAdr/Ctry") or (
            cdtr_iban[:2] if cdtr_iban else ""
        )

        # Remittance info
        remittance = find_text(tx_info, "RmtInf/Ustrd")

        return {
            "message_type": "ISO20022_PACS008",
            "transaction_id": tx_id,
            "amount": amount,
            "currency": currency,
            "date": settlement_date,
            "sender_name": dbtr_name,
            "sender_account": dbtr_iban,
            "sender_bic": dbtr_bic,
            "sender_country": dbtr_country,
            "receiver_name": cdtr_name,
            "receiver_account": cdtr_iban,
            "receiver_bic": cdtr_bic,
            "receiver_country": cdtr_country,
            "remittance_info": remittance,
        }

    @staticmethod
    def parse_swift_mt103(mt103_content: str) -> dict[str, Any]:
        """Parse SWIFT MT103 Single Customer Credit Transfer message."""
        content = mt103_content.strip()
        if not content:
            raise FinancialMessageParserError("Empty MT103 message content")

        # Find block 4, which contains the transaction details
        block4_match = re.search(r"({4:(.*)-})", content, re.DOTALL)
        body = block4_match.group(2) if block4_match else content

        # Helper to extract tags like :XX:
        def get_tag_value(tag: str) -> str:
            # Match the tag and grab lines until the next tag starting with : or block end
            pattern = rf"(?:^|\n):{tag}:(.*?)(?=\n:\d{{2}}[A-Z]?:|\n-}}|\n$)"
            match = re.search(pattern, body, re.DOTALL)
            return match.group(1).strip() if match else ""

        tx_id = get_tag_value("20")
        if not tx_id:
            # Try to grab reference
            tx_id = "unknown_swift_id"

        # Tag 32A contains Date, Currency, Amount (Format: YYMMDDCCYAmount)
        # Example: 260716EUR12500,00 -> Date: 260716, Ccy: EUR, Amt: 12500.00
        tag32a = get_tag_value("32A")
        amount = 0.0
        currency = "EUR"
        date_str = ""
        if tag32a:
            m = re.match(r"^(\d{6})([A-Z]{3})(.*)$", tag32a)
            if m:
                date_str = "20" + m.group(1)  # Expand to YYYYMMDD format
                currency = m.group(2)
                amt_str = m.group(3).replace(",", ".")
                try:
                    amount = float(amt_str)
                except ValueError as exc:
                    raise FinancialMessageParserError(
                        f"Invalid MT103 amount format in 32A: {exc}"
                    ) from exc

        # Tag 50A, 50F, or 50K (Debtor/Ordering Customer)
        tag50 = get_tag_value("50K") or get_tag_value("50A") or get_tag_value("50F")
        sender_account = ""
        sender_name = ""
        sender_country = ""
        if tag50:
            lines = tag50.split("\n")
            if lines[0].startswith("/"):
                sender_account = lines[0][1:]
                sender_name = lines[1] if len(lines) > 1 else ""
            else:
                sender_name = lines[0]
            # Try to guess country from account if IBAN
            if sender_account and len(sender_account) > 2 and sender_account[:2].isalpha():
                sender_country = sender_account[:2].upper()

        # Tag 59 or 59A (Creditor/Beneficiary)
        tag59 = get_tag_value("59") or get_tag_value("59A")
        receiver_account = ""
        receiver_name = ""
        receiver_country = ""
        if tag59:
            lines = tag59.split("\n")
            if lines[0].startswith("/"):
                receiver_account = lines[0][1:]
                receiver_name = lines[1] if len(lines) > 1 else ""
            else:
                receiver_name = lines[0]
            if receiver_account and len(receiver_account) > 2 and receiver_account[:2].isalpha():
                receiver_country = receiver_account[:2].upper()

        # Tag 70 (Remittance Info / Details of Payment)
        remittance_info = get_tag_value("70")

        # Tag 57A (Account With Institution BIC)
        receiver_bic = get_tag_value("57A")

        return {
            "message_type": "SWIFT_MT103",
            "transaction_id": tx_id,
            "amount": amount,
            "currency": currency,
            "date": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            if len(date_str) == 8
            else date_str,
            "sender_name": sender_name,
            "sender_account": sender_account,
            "sender_country": sender_country,
            "receiver_name": receiver_name,
            "receiver_account": receiver_account,
            "receiver_bic": receiver_bic,
            "receiver_country": receiver_country,
            "remittance_info": remittance_info,
        }

    @classmethod
    def parse_sepa_credit_transfer(cls, xml_content: str) -> dict[str, Any]:
        """Parse SEPA Credit Transfer (often identical format to ISO 20022 pacs.008 or pain.001)."""
        # Let's delegate to the pacs.008 parser or pain.001 XML parsing
        try:
            res = cls.parse_iso_20022_pacs008(xml_content)
            res["message_type"] = "SEPA_SCT"
            return res
        except FinancialMessageParserError:
            # Let's implement a simpler pain.001 parser or custom SCT parser if the format is slightly different
            root = ET.fromstring(xml_content.strip())  # nosec B314
            ns = ""
            m = re.match(r"({.*})", root.tag)
            if m:
                ns = m.group(1)

            def find_text(element: ET.Element | None, path: str) -> str:
                if element is None:
                    return ""
                parts = []
                for p in path.split("/"):
                    if not p or p in (".", ".."):
                        parts.append(p)
                    elif ns and not p.startswith(ns):
                        parts.append(f"{ns}{p}")
                    else:
                        parts.append(p)
                ns_path = "/".join(parts)
                found = element.find(ns_path)
                return found.text.strip() if found is not None and found.text else ""

            # Check if pain.001 structure
            tx_info = root.find(f".//{ns}CdtTrfTxInf")
            if tx_info is None:
                raise FinancialMessageParserError(
                    "Could not parse XML payload as SEPA Credit Transfer"
                )

            amt_elem = tx_info.find(f"{ns}Amt/{ns}InstdAmt")
            if amt_elem is None:
                amt_elem = tx_info.find(f"{ns}InstdAmt")
            if amt_elem is None:
                raise FinancialMessageParserError("Instruction Amount is missing in SEPA payload")

            amount = float(amt_elem.text.strip()) if amt_elem.text else 0.0
            currency = amt_elem.attrib.get("Ccy", "EUR")
            tx_id = find_text(tx_info, "PmtId/EndToEndId") or "unknown_sepa_id"

            dbtr_name = find_text(root, ".//Dbtr/Nm")
            dbtr_iban = find_text(root, ".//DbtrAcct/Id/IBAN")
            dbtr_country = dbtr_iban[:2] if dbtr_iban else ""

            cdtr_name = find_text(tx_info, "Cdtr/Nm")
            cdtr_iban = find_text(tx_info, "CdtrAcct/Id/IBAN")
            cdtr_country = cdtr_iban[:2] if cdtr_iban else ""

            return {
                "message_type": "SEPA_SCT",
                "transaction_id": tx_id,
                "amount": amount,
                "currency": currency,
                "date": "",
                "sender_name": dbtr_name,
                "sender_account": dbtr_iban,
                "sender_country": dbtr_country,
                "receiver_name": cdtr_name,
                "receiver_account": cdtr_iban,
                "receiver_country": cdtr_country,
                "remittance_info": find_text(tx_info, "RmtInf/Ustrd"),
            }
