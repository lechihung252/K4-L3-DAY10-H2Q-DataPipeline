from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from html import unescape
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


CROSSREF_WORKS_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 503}
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref API payload into validated, normalized records."""
    if not isinstance(payload, dict):
        raise TypeError("Crossref payload must be a dictionary.")

    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, dict) else []
    if not isinstance(items, list):
        raise ValueError("Crossref payload must contain message.items as a list.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = _clean_text(item.get("DOI"))
        title = _first_text(item.get("title"))
        summary = _clean_text(item.get("abstract"), strip_markup=True)
        published = _first_date(
            item.get("published"),
            item.get("published-online"),
            item.get("published-print"),
            item.get("created"),
        )

        # These fields are required by the downstream cleaning and indexing
        # stages. A duplicate DOI is also discarded at the ingestion boundary.
        normalized_id = paper_id.lower()
        if not paper_id or not title or not summary or not published or normalized_id in seen_ids:
            continue

        authors = _parse_authors(item.get("author"))
        categories = _string_list(item.get("subject"))
        updated = _first_date(
            item.get("indexed"),
            item.get("deposited"),
            item.get("created"),
            item.get("published"),
        ) or published
        abs_url = _clean_text(item.get("URL")) or f"https://doi.org/{paper_id}"
        pdf_url = _find_pdf_url(item.get("link")) or abs_url

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {paper_id}",
            )
        )
        seen_ids.add(normalized_id)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Load Crossref data, preferring the local snapshot in offline mode.

    Set ``REFRESH_SOURCE=true`` to request fresh API data. If the request fails
    after retrying rate-limit/service-unavailable responses, an existing raw
    API snapshot is used as the recovery source.
    """
    snapshot_path = settings.paths.raw_api_response
    payload: dict[str, Any]

    if not settings.refresh_source and snapshot_path.exists():
        payload = read_json(snapshot_path)
    else:
        try:
            payload = _fetch_crossref_payload(settings)
            write_json(snapshot_path, payload)
        except (requests.RequestException, ValueError, TypeError):
            if not snapshot_path.exists():
                raise
            payload = read_json(snapshot_path)

    records = parse_crossref_payload(payload)
    if not records:
        raise ValueError("Crossref source did not contain any valid paper records.")

    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read a normalized raw JSON snapshot and map it to ``PaperRecord``."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw records file must contain a JSON list: {path}")

    records: list[PaperRecord] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record at index {index} must be a JSON object.")
        try:
            records.append(PaperRecord(**item))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid raw record at index {index}: {exc}") from exc
    return records


def _fetch_crossref_payload(settings: Settings) -> dict[str, Any]:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "day10-data-observability-lab/0.1",
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = requests.get(
            CROSSREF_WORKS_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code not in RETRYABLE_STATUS_CODES:
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Crossref API response must be a JSON object.")
            return payload

        if attempt < MAX_ATTEMPTS:
            retry_after = response.headers.get("Retry-After", "")
            try:
                delay = max(1.0, min(float(retry_after), 10.0))
            except ValueError:
                delay = float(2 ** (attempt - 1))
            time.sleep(delay)

    response.raise_for_status()
    raise requests.RequestException("Crossref request failed after retries.")


def _clean_text(value: Any, *, strip_markup: bool = False) -> str:
    if value is None:
        return ""
    text = str(value)
    if strip_markup:
        text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(unescape(text))


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        return _clean_text(value[0], strip_markup=True) if value else ""
    return _clean_text(value, strip_markup=True)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned = _clean_text(item, strip_markup=True)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def _parse_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = _clean_text(author.get("name"))
        if not name:
            name = normalize_whitespace(
                " ".join(
                    part
                    for part in (
                        _clean_text(author.get("given")),
                        _clean_text(author.get("family")),
                    )
                    if part
                )
            )
        if name:
            authors.append(name)
    return authors


def _date_from_crossref(value: Any) -> str:
    if not isinstance(value, dict):
        return ""

    date_parts = value.get("date-parts")
    if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list):
        parts = date_parts[0]
        try:
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            return date(year, month, day).isoformat()
        except (IndexError, TypeError, ValueError):
            pass

    date_time = value.get("date-time")
    if isinstance(date_time, str) and date_time.strip():
        try:
            return datetime.fromisoformat(date_time.strip().replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return ""
    return ""


def _first_date(*values: Any) -> str:
    for value in values:
        parsed = _date_from_crossref(value)
        if parsed:
            return parsed
    return ""


def _find_pdf_url(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    fallback = ""
    for link in value:
        if not isinstance(link, dict):
            continue
        url = _clean_text(link.get("URL"))
        if not url:
            continue
        content_type = _clean_text(link.get("content-type")).lower()
        if content_type == "application/pdf" or url.lower().endswith(".pdf"):
            return url
        if not fallback:
            fallback = url
    return fallback
