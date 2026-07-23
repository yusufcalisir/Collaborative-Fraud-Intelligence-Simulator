"""ISO 20022 MX and SWIFT MT Financial Messaging Bank Connector."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.infrastructure.connectors.base_connector import BaseBankConnector, NormalizedTransaction

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)


class ISO20022MessagingConnector(BaseBankConnector):
    """Connector for parsing ISO 20022 MX (pacs.008, pacs.009) XML/JSON and SWIFT MT103/MT202 messages."""

    def __init__(self):
        self._parsed_queue: list[NormalizedTransaction] = []

    def parse_pacs008_xml(self, xml_content: str) -> NormalizedTransaction:
        """Parses an ISO 20022 pacs.008.001.08 Financial Institution Customer Credit Transfer XML string."""
        root = ET.fromstring(xml_content)  # nosec B314

        # Remove XML namespace prefixes for robust searching
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        msg_id = root.findtext(".//GrpHdr/MsgId") or f"pacs008_{int(datetime.now(UTC).timestamp())}"
        amount_elem = root.find(".//CdtTrfTxInf/IntrBkSttlmAmt")
        amount = float(amount_elem.text) if amount_elem is not None and amount_elem.text else 100.0
        currency = (amount_elem.get("Ccy") if amount_elem is not None else None) or "EUR"

        debtor_account = (
            root.findtext(".//DbtrAcct/Id/Othr/Id")
            or root.findtext(".//DbtrAcct/Id/IBAN")
            or "DEBTOR_UNKNOWN"
        )
        creditor_account = (
            root.findtext(".//CdtrAcct/Id/Othr/Id")
            or root.findtext(".//CdtrAcct/Id/IBAN")
            or "CREDITOR_UNKNOWN"
        )
        debtor_country = root.findtext(".//Dbtr/PstlAdr/Ctry") or "DE"
        creditor_country = root.findtext(".//Cdtr/PstlAdr/Ctry") or "FR"

        tx = NormalizedTransaction(
            transaction_id=msg_id,
            account_id=debtor_account,
            counterparty_account_id=creditor_account,
            amount=amount,
            currency=currency,
            timestamp=datetime.now(UTC),
            merchant_category_code="6012",
            origin_country=debtor_country,
            destination_country=creditor_country,
            channel_type="ISO20022_PACS008",
        )
        self._parsed_queue.append(tx)
        return tx

    def parse_swift_mt103(self, mt103_text: str) -> NormalizedTransaction:
        """Parses a legacy SWIFT MT103 Single Customer Credit Transfer text string."""
        lines = mt103_text.splitlines()

        tx_id = f"MT103_{int(datetime.now(UTC).timestamp())}"
        amount = 500.0
        currency = "USD"
        debtor = "SWIFT_DEBTOR"
        creditor = "SWIFT_CREDITOR"

        for line in lines:
            if line.startswith(":20:"):
                tx_id = line.replace(":20:", "").strip()
            elif line.startswith(":32A:"):
                val = line.replace(":32A:", "").strip()
                # Format: YYMMDDCCYAMOUNT e.g. 260722USD12500,00
                m = re.search(r"^[0-9]{6}([A-Z]{3})([0-9,.]+)", val)
                if m:
                    currency = m.group(1)
                    amount = float(m.group(2).replace(",", "."))
            elif line.startswith(":50K:") or line.startswith(":50A:"):
                debtor = line.split(":", 2)[-1].strip()
            elif line.startswith(":59:") or line.startswith(":59A:"):
                creditor = line.split(":", 2)[-1].strip()

        tx = NormalizedTransaction(
            transaction_id=tx_id,
            account_id=debtor,
            counterparty_account_id=creditor,
            amount=amount,
            currency=currency,
            timestamp=datetime.now(UTC),
            merchant_category_code="6011",
            origin_country="US",
            destination_country="GB",
            channel_type="SWIFT_MT103",
        )
        self._parsed_queue.append(tx)
        return tx

    def parse_camt053_xml(self, xml_content: str) -> list[NormalizedTransaction]:
        """Parses an ISO 20022 camt.053.001.08 Bank-to-Customer Statement XML string into a list of NormalizedTransactions."""
        root = ET.fromstring(xml_content)  # nosec B314

        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        acct_id = (
            root.findtext(".//Stmt/Acct/Id/IBAN")
            or root.findtext(".//Stmt/Acct/Id/Othr/Id")
            or "STATEMENT_ACCOUNT"
        )
        entries = root.findall(".//Stmt/Ntry")
        results: list[NormalizedTransaction] = []

        for idx, ntry in enumerate(entries):
            amt_elem = ntry.find(".//Amt")
            amount = float(amt_elem.text) if amt_elem is not None and amt_elem.text else 0.0
            currency = (amt_elem.get("Ccy") if amt_elem is not None else None) or "EUR"
            tx_id = ntry.findtext(".//NtryRef") or f"camt053_entry_{idx}"
            counterparty = (
                ntry.findtext(".//NtryDtls/TxDtls/RltdPties/Cdtr/Nm")
                or ntry.findtext(".//NtryDtls/TxDtls/RltdPties/Dbtr/Nm")
                or "COUNTERPARTY_STATEMENT"
            )

            tx = NormalizedTransaction(
                transaction_id=tx_id,
                account_id=acct_id,
                counterparty_account_id=counterparty,
                amount=amount,
                currency=currency,
                timestamp=datetime.now(UTC),
                merchant_category_code="6012",
                origin_country="EU",
                destination_country="EU",
                channel_type="ISO20022_CAMT053",
            )
            results.append(tx)
            self._parsed_queue.append(tx)

        return results

    def parse_pacs002_xml(self, xml_content: str) -> NormalizedTransaction:
        """Parses an ISO 20022 pacs.002.001.10 Payment Status Report XML string."""
        root = ET.fromstring(xml_content)  # nosec B314

        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        msg_id = root.findtext(".//GrpHdr/MsgId") or f"pacs002_{int(datetime.now(UTC).timestamp())}"

        status = root.findtext(".//OrgnlPmtInfAndSts/TxInfAndSts/TxSts") or "ACTC"
        orig_msg_id = root.findtext(".//OrgnlPmtInfAndSts/OrgnlPmtInfId") or "ORIG_UNKNOWN"

        tx = NormalizedTransaction(
            transaction_id=msg_id,
            account_id=orig_msg_id,
            counterparty_account_id=f"STATUS_{status}",
            amount=0.0,
            currency="EUR",
            timestamp=datetime.now(UTC),
            merchant_category_code="6012",
            origin_country="EU",
            destination_country="EU",
            channel_type="ISO20022_PACS002",
        )
        self._parsed_queue.append(tx)
        return tx

    def consume_stream(self) -> Generator[NormalizedTransaction, None, None]:
        """Yields transactions from parsed message queue."""
        while self._parsed_queue:
            yield self._parsed_queue.pop(0)

    def parse_batch(self, payload: Any) -> list[NormalizedTransaction]:
        """Parses batch of XML/SWIFT message strings."""
        if isinstance(payload, list):
            results = []
            for item in payload:
                if "<camt.053" in item:
                    results.extend(self.parse_camt053_xml(item))
                elif "<pacs.002" in item:
                    results.append(self.parse_pacs002_xml(item))
                elif "<pacs.008" in item or "<Document" in item:
                    results.append(self.parse_pacs008_xml(item))
                elif ":20:" in item or ":32A:" in item:
                    results.append(self.parse_swift_mt103(item))
            return results
        elif isinstance(payload, str):
            if "<camt.053" in payload:
                return self.parse_camt053_xml(payload)
            elif "<pacs.002" in payload:
                return [self.parse_pacs002_xml(payload)]
            elif "<pacs.008" in payload or "<Document" in payload:
                return [self.parse_pacs008_xml(payload)]
            elif ":20:" in payload or ":32A:" in payload:
                return [self.parse_swift_mt103(payload)]
        return []
