"""Presentation helpers for REPLIK search results.

This module ports the tailored LegalMonitor REPLIK UI library from the
TypeScript handoff into the Streamlit/Python app.  It keeps REPLIK raw enum
codes in the record detail while exposing stable Slovak labels, severities and
frontend-ready display cards for the search results.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Dict, Iterable, List, Literal, Optional

Severity = Literal["neutral", "info", "warning", "critical"]
Locale = Literal["sk", "en"]
CodeGroup = Literal[
    "konanieTyp",
    "oznamTyp",
    "druhPodania",
    "stavKonania",
    "typSpravcu",
    "textDruh",
    "typTriedenia",
]

SEVERITY_RANK: Dict[str, int] = {"neutral": 0, "info": 1, "warning": 2, "critical": 3}

LABELS: Dict[str, Dict[str, Dict[str, Dict[str, str]]]] = {
    "sk": {
        "konanieTyp": {
            "KONKURZ": {"label": "Konkurz", "description": "Insolvenčné konanie týkajúce sa majetku dlžníka.", "severity": "critical"},
            "MALYKONKURZ": {"label": "Malý konkurz", "description": "Zjednodušený konkurzný režim pre menšie prípady.", "severity": "critical"},
            "RESTRUKTURALIZACIA": {"label": "Reštrukturalizácia", "description": "Súdne vedený proces ozdravenia dlžníka podľa reštrukturalizačného plánu.", "severity": "warning"},
            "INEKONANIA": {"label": "Iné konanie", "description": "Iný typ konania evidovaný v REPLIK mimo hlavné štandardné kategórie.", "severity": "info"},
            "ODDLZENIE_KONKURZ": {"label": "Oddlženie – konkurz", "description": "Osobné oddlženie formou konkurzu.", "severity": "warning"},
            "ODDLZENIE_SPLATKOVY_KALENDAR": {"label": "Oddlženie – splátkový kalendár", "description": "Osobné oddlženie formou splátkového kalendára.", "severity": "warning"},
            "LIKVIDACIA": {"label": "Likvidácia", "description": "Likvidačné konanie alebo súvisiaci proces pri zrušovaní právnickej osoby.", "severity": "warning"},
            "VPR": {"label": "Verejná preventívna reštrukturalizácia", "description": "Preventívna reštrukturalizácia pred plnou insolvenčnou situáciou.", "severity": "warning"},
        },
        "oznamTyp": {
            "OZNAM_SUD": {"label": "Oznam súdu", "description": "Oznam alebo rozhodnutie zverejnené súdom.", "severity": "info"},
            "OZNAM_SPRAVCA": {"label": "Oznam správcu", "description": "Oznam zverejnený správcom, likvidátorom alebo inou osobou v príslušnej procesnej role.", "severity": "info"},
        },
        "druhPodania": {
            "INE_ZVEREJNENIE": {"label": "Iné zverejnenie", "description": "Všeobecný typ zverejnenia bez špecifickejšieho verejne dokumentovaného zaradenia.", "severity": "info"},
        },
        "stavKonania": {
            "SKONCENY_PROCES": {"label": "Skončený proces", "description": "Proces je v REPLIK vedený ako skončený.", "severity": "neutral"},
            "ZASTAVENE_KONANIE": {"label": "Zastavené konanie", "description": "Konanie je vedené ako zastavené.", "severity": "neutral"},
            "PREBIEHAJUCE_KONANIE": {"label": "Prebiehajúce konanie", "description": "Konanie je vedené ako prebiehajúce.", "severity": "warning"},
        },
        "typSpravcu": {
            "RIADNY": {"label": "Riadny správca", "description": "Riadny správca priradený ku konaniu.", "severity": "info"},
            "PREDBEZNY": {"label": "Predbežný správca", "description": "Predbežný správca priradený ku konaniu.", "severity": "info"},
        },
        "textDruh": {
            "UZNESENIE": {"label": "Uznesenie", "description": "Súdne rozhodnutie vo forme uznesenia.", "severity": "info"},
        },
        "typTriedenia": {
            "DATUMPOSLEDNEJUDALOSTI": {"label": "Dátum poslednej udalosti", "description": "Výsledky sú zoradené podľa dátumu poslednej operácie vykonanej na konaní.", "severity": "neutral"},
            "DATUMZACATIAKONANIA": {"label": "Dátum začatia konania", "description": "Výsledky sú zoradené podľa dátumu začatia konania.", "severity": "neutral"},
            "RELEVANCIA": {"label": "Relevancia", "description": "Výsledky sú zoradené podľa relevancie vyhľadávaného výrazu.", "severity": "neutral"},
        },
    },
    "en": {
        "konanieTyp": {
            "KONKURZ": {"label": "Bankruptcy", "description": "Insolvency proceeding concerning the debtor's assets.", "severity": "critical"},
            "MALYKONKURZ": {"label": "Small bankruptcy", "description": "Simplified bankruptcy regime for smaller cases.", "severity": "critical"},
            "RESTRUKTURALIZACIA": {"label": "Restructuring", "description": "Court-supervised debtor restructuring process.", "severity": "warning"},
            "INEKONANIA": {"label": "Other proceeding", "description": "Other REPLIK proceeding type outside the main standard categories.", "severity": "info"},
            "ODDLZENIE_KONKURZ": {"label": "Debt relief – bankruptcy", "description": "Personal debt relief through bankruptcy.", "severity": "warning"},
            "ODDLZENIE_SPLATKOVY_KALENDAR": {"label": "Debt relief – repayment schedule", "description": "Personal debt relief through repayment schedule.", "severity": "warning"},
            "LIKVIDACIA": {"label": "Liquidation", "description": "Liquidation proceeding or related process for winding up a legal entity.", "severity": "warning"},
            "VPR": {"label": "Public preventive restructuring", "description": "Preventive restructuring before full insolvency.", "severity": "warning"},
        },
        "oznamTyp": {
            "OZNAM_SUD": {"label": "Court notice", "description": "Notice or decision published by the court.", "severity": "info"},
            "OZNAM_SPRAVCA": {"label": "Administrator notice", "description": "Notice published by the administrator, liquidator or person acting in the relevant procedural role.", "severity": "info"},
        },
        "druhPodania": {"INE_ZVEREJNENIE": {"label": "Other publication", "description": "Generic publication type without a more specific publicly documented category.", "severity": "info"}},
        "stavKonania": {
            "SKONCENY_PROCES": {"label": "Completed process", "description": "The process is recorded as completed in REPLIK.", "severity": "neutral"},
            "ZASTAVENE_KONANIE": {"label": "Stopped proceeding", "description": "The proceeding is recorded as stopped.", "severity": "neutral"},
            "PREBIEHAJUCE_KONANIE": {"label": "Ongoing proceeding", "description": "The proceeding is recorded as ongoing.", "severity": "warning"},
        },
        "typSpravcu": {
            "RIADNY": {"label": "Regular administrator", "description": "Regular administrator assigned to the proceeding.", "severity": "info"},
            "PREDBEZNY": {"label": "Interim administrator", "description": "Interim administrator assigned to the proceeding.", "severity": "info"},
        },
        "textDruh": {"UZNESENIE": {"label": "Court resolution", "description": "Court decision in the form of a resolution/order.", "severity": "info"}},
        "typTriedenia": {
            "DATUMPOSLEDNEJUDALOSTI": {"label": "Date of last event", "description": "Results sorted by the last operation performed on the proceeding.", "severity": "neutral"},
            "DATUMZACATIAKONANIA": {"label": "Proceeding start date", "description": "Results sorted by proceeding start date.", "severity": "neutral"},
            "RELEVANCIA": {"label": "Relevance", "description": "Results sorted by relevance of the search expression.", "severity": "neutral"},
        },
    },
}


def normalize_code(code: Optional[str]) -> str:
    if not code:
        return ""
    normalized = re.sub(r"_+", "_", re.sub(r"[\s-]+", "_", str(code).strip())).upper()
    if normalized == "ODDLZENIE_SPLATKOVYKALENDAR":
        return "ODDLZENIE_SPLATKOVY_KALENDAR"
    return normalized


def humanize_code(code: Optional[str], locale: Locale = "sk") -> str:
    if not code:
        return "Neuvedené" if locale == "sk" else "Not specified"
    return " ".join(part.capitalize() for part in re.split(r"[\s_-]+", str(code).strip().lower()) if part)


def get_code_label(group: CodeGroup, code: Optional[str], locale: Locale = "sk") -> Dict[str, str]:
    normalized = normalize_code(code)
    group_labels = LABELS.get(locale, LABELS["sk"]).get(group, {})
    if normalized in group_labels:
        return {"code": code or "", **group_labels[normalized]}
    compact = normalized.replace("_", "")
    for stored_code, item in group_labels.items():
        if normalize_code(stored_code).replace("_", "") == compact:
            return {"code": code or stored_code, **item}
    return {
        "code": code or "",
        "label": humanize_code(code, locale),
        "description": (
            "Neznámy alebo nový kód z REPLIK. Pôvodnú hodnotu ponechajte v detaile záznamu a doplňte mapovanie po overení."
            if locale == "sk"
            else "Unknown or new REPLIK code. Keep the original value in the record detail and add mapping after verification."
        ),
        "severity": "info",
    }


def coalesce_string(*values: Any) -> Optional[str]:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return None


def _get(record: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return None


def _str(record: Dict[str, Any], *keys: str) -> Optional[str]:
    return coalesce_string(*(_get(record, key) for key in keys))


def format_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = str(value)
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%d.%m.%Y")
    except ValueError:
        return text


def compact_text(parts: Iterable[Optional[str]], separator: str = "\n\n") -> Optional[str]:
    cleaned = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
    return separator.join(cleaned) if cleaned else None


def max_severity(values: Iterable[str]) -> Severity:
    result: Severity = "neutral"
    for value in values:
        if SEVERITY_RANK.get(value, 0) > SEVERITY_RANK[result]:
            result = value  # type: ignore[assignment]
    return result


def normalize_proceeding(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _str(record, "Id", "KonanieId", "id"),
        "caseNumber": _str(record, "SpisovaZnackaSudu", "spisovaZnackaSudu", "caseNumber"),
        "proceedingTypeCode": _str(record, "Typ", "KonanieTyp", "typ", "konanieTyp", "proceedingTypeCode"),
        "startDate": _str(record, "DatumZacatiaKonania", "DatumZacatiaKonanie", "startDate"),
        "processStartDate": _str(record, "DatumZacatiaProcesu", "processStartDate"),
        "filingDate": _str(record, "DatumPodania", "filingDate"),
        "debtorName": _str(record, "Dlznik", "DlznikMeno", "debtorName"),
        "debtorIco": _str(record, "DlznikIco", "Ico", "debtorIco"),
        "lastEventDate": _str(record, "DatumPoslednejUdalosti", "lastEventDate"),
        "courtCode": _str(record, "Sud", "SudKod", "courtCode"),
        "courtName": _str(record, "SudNazov", "courtName"),
        "administratorName": _str(record, "Spravca", "administratorName"),
        "statusCode": _str(record, "StavKonania", "statusCode"),
        "raw": record,
    }


def normalize_notice(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "noticeId": _str(record, "OznamId", "noticeId", "Id", "id"),
        "noticeTypeCode": _str(record, "OznamTyp", "noticeTypeCode"),
        "courtCode": _str(record, "SudKod", "Sud", "courtCode"),
        "courtName": _str(record, "SudNazov", "courtName"),
        "courtCaseNumber": _str(record, "SpisovaZnackaSudnehoSpisu", "SpisovaZnackaSudu", "courtCaseNumber"),
        "proceedingId": _str(record, "KonanieId", "proceedingId"),
        "proceedingTypeCode": _str(record, "KonanieTyp", "Typ", "proceedingTypeCode"),
        "publishedDate": _str(record, "DatumVydania", "publishedDate"),
        "hasAttachments": _str(record, "ObsahujePrilohy", "hasAttachments"),
        "textKindCode": _str(record, "TextDruh", "textKindCode"),
        "filingTypeCode": _str(record, "DruhPodania", "filingTypeCode"),
        "instructionText": _str(record, "TextPoucenie", "instructionText"),
        "headerText": _str(record, "TextHlavicka", "headerText"),
        "reasoningText": _str(record, "TextOdovodnenie", "reasoningText"),
        "noticeText": _str(record, "TextOznam", "noticeText"),
        "decisionText": _str(record, "TextRozhodnutie", "decisionText"),
        "administratorText": _str(record, "Text", "administratorText"),
        "administratorCaseNumber": _str(record, "SpisovaZnackaSpravcu", "administratorCaseNumber"),
        "raw": record,
    }


def proceeding_to_card(record: Dict[str, Any], locale: Locale = "sk") -> Dict[str, Any]:
    type_label = get_code_label("konanieTyp", record.get("proceedingTypeCode"), locale)
    status_label = get_code_label("stavKonania", record.get("statusCode"), locale) if record.get("statusCode") else None
    severity = max_severity([type_label["severity"], status_label["severity"] if status_label else "neutral"])
    subtitle = compact_text([
        " · ".join(part for part in [record.get("debtorName"), f"IČO {record.get('debtorIco')}" if record.get("debtorIco") else None] if part),
        " · ".join(part for part in [record.get("courtName"), record.get("caseNumber")] if part),
    ], "\n") or ""
    badges = [{"label": type_label["label"], "tone": type_label["severity"], "rawCode": record.get("proceedingTypeCode"), "tooltip": type_label["description"]}]
    if status_label:
        badges.append({"label": status_label["label"], "tone": status_label["severity"], "rawCode": record.get("statusCode"), "tooltip": status_label["description"]})
    return {
        "id": record.get("id") or record.get("caseNumber") or "konanie",
        "type": "proceeding",
        "title": type_label["label"],
        "subtitle": subtitle,
        "date": format_date(record.get("lastEventDate") or record.get("startDate") or record.get("filingDate")),
        "severity": severity,
        "badges": badges,
        "fields": [
            {"key": "debtor", "label": "Dlžník" if locale == "sk" else "Debtor", "value": record.get("debtorName"), "important": True},
            {"key": "debtorIco", "label": "IČO dlžníka" if locale == "sk" else "Debtor IČO", "value": record.get("debtorIco"), "important": True},
            {"key": "caseNumber", "label": "Spisová značka" if locale == "sk" else "Case number", "value": record.get("caseNumber"), "important": True},
            {"key": "court", "label": "Súd" if locale == "sk" else "Court", "value": record.get("courtName")},
            {"key": "administrator", "label": "Správca" if locale == "sk" else "Administrator", "value": record.get("administratorName")},
            {"key": "rawType", "label": "Raw KonanieTyp", "value": record.get("proceedingTypeCode")},
            {"key": "rawStatus", "label": "Raw StavKonania", "value": record.get("statusCode")},
        ],
        "raw": record.get("raw"),
    }


def notice_to_card(record: Dict[str, Any], locale: Locale = "sk") -> Dict[str, Any]:
    notice_label = get_code_label("oznamTyp", record.get("noticeTypeCode"), locale)
    proceeding_label = get_code_label("konanieTyp", record.get("proceedingTypeCode"), locale) if record.get("proceedingTypeCode") else None
    filing_label = get_code_label("druhPodania", record.get("filingTypeCode"), locale) if record.get("filingTypeCode") else None
    severity = max_severity([notice_label["severity"], proceeding_label["severity"] if proceeding_label else "neutral", filing_label["severity"] if filing_label else "neutral"])
    title_parts = [notice_label["label"]]
    if proceeding_label:
        title_parts.append(proceeding_label["label"])
    badges = [{"label": notice_label["label"], "tone": notice_label["severity"], "rawCode": record.get("noticeTypeCode"), "tooltip": notice_label["description"]}]
    if proceeding_label:
        badges.append({"label": proceeding_label["label"], "tone": proceeding_label["severity"], "rawCode": record.get("proceedingTypeCode"), "tooltip": proceeding_label["description"]})
    if filing_label:
        badges.append({"label": filing_label["label"], "tone": filing_label["severity"], "rawCode": record.get("filingTypeCode"), "tooltip": filing_label["description"]})
    return {
        "id": record.get("noticeId") or record.get("courtCaseNumber") or "oznam",
        "type": "notice",
        "title": " · ".join(title_parts),
        "subtitle": " · ".join(part for part in [record.get("courtName"), record.get("courtCaseNumber")] if part),
        "date": format_date(record.get("publishedDate")),
        "severity": severity,
        "badges": badges,
        "fields": [
            {"key": "court", "label": "Súd" if locale == "sk" else "Court", "value": record.get("courtName"), "important": True},
            {"key": "caseNumber", "label": "Spisová značka", "value": record.get("courtCaseNumber"), "important": True},
            {"key": "publishedDate", "label": "Dátum zverejnenia" if locale == "sk" else "Published date", "value": format_date(record.get("publishedDate")), "rawValue": record.get("publishedDate")},
            {"key": "rawNoticeType", "label": "Raw OznamTyp", "value": record.get("noticeTypeCode")},
            {"key": "rawProceedingType", "label": "Raw KonanieTyp", "value": record.get("proceedingTypeCode")},
            {"key": "rawFilingType", "label": "Raw DruhPodania", "value": record.get("filingTypeCode")},
        ],
        "body": compact_text([record.get("headerText"), record.get("noticeText"), record.get("decisionText"), record.get("reasoningText"), record.get("instructionText"), record.get("administratorText")]),
        "raw": record.get("raw"),
    }


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    dataset = str(record.get("dataset", "")).lower()
    if dataset == "oznam" or _str(record, "OznamId", "OznamTyp", "DruhPodania"):
        return {"dataset": "oznam", **normalize_notice(record)}
    return {"dataset": "konanie", **normalize_proceeding(record)}


def card_for_normalized(record: Dict[str, Any], locale: Locale = "sk") -> Dict[str, Any]:
    if record.get("dataset") == "oznam":
        return notice_to_card(record, locale)
    return proceeding_to_card(record, locale)


def build_ui_payload(records: List[Dict[str, Any]], search_mode: str, query: Dict[str, Any], locale: Locale = "sk") -> Dict[str, Any]:
    normalized = [normalize_record(record) for record in records]
    cards = [card_for_normalized(record, locale) for record in normalized]
    proceedings_count = sum(1 for record in normalized if record.get("dataset") == "konanie")
    notices_count = sum(1 for record in normalized if record.get("dataset") == "oznam")
    highest = max_severity(card.get("severity", "neutral") for card in cards)
    headline = "REPLIK obsahuje relevantné záznamy." if cards else "REPLIK nevrátil žiadne záznamy."
    explanation = f"Nájdené konania: {proceedings_count}. Nájdené verejné oznamy: {notices_count}."
    return {
        "summary": {
            "source": "REPLIK",
            "searchMode": search_mode,
            "query": query,
            "queriedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "proceedingsCount": proceedings_count,
            "noticesCount": notices_count,
            "highestSeverity": highest,
            "headline": headline,
            "explanation": explanation,
        },
        "normalized_records": normalized,
        "cards": sorted(cards, key=lambda card: (SEVERITY_RANK.get(card.get("severity", "neutral"), 0), card.get("date") or ""), reverse=True),
    }
