"""Small, deterministic BibTeX parser and citation resolver."""

from __future__ import annotations

import re
from collections.abc import Iterable

from scholartrace.schemas import BibTeXEntry, CitationValidationReport


class BibTeXParseError(ValueError):
    """Raised when a BibTeX entry cannot be parsed or is incomplete."""


_ENTRY_START = re.compile(r"@([A-Za-z][A-Za-z0-9_-]*)\s*([({])")
_IGNORED_TYPES = {"comment", "preamble", "string"}
_SUPPORTED_TYPES = {
    "article",
    "book",
    "incollection",
    "inproceedings",
    "misc",
    "phdthesis",
    "techreport",
}


def parse_bibtex(text: str) -> list[BibTeXEntry]:
    """Parse supported BibTeX entries without network access or silent repair."""

    entries: list[BibTeXEntry] = []
    seen_keys: set[str] = set()
    position = 0
    while True:
        match = _ENTRY_START.search(text, position)
        if match is None:
            break
        entry_type = match.group(1).lower()
        opening = match.group(2)
        end = _find_entry_end(text, match.end() - 1, opening)
        if end is None:
            raise BibTeXParseError(f"unterminated BibTeX entry near position {match.start()}")
        position = end
        if entry_type in _IGNORED_TYPES:
            continue
        if entry_type not in _SUPPORTED_TYPES:
            raise BibTeXParseError(f"unsupported BibTeX entry type: {entry_type}")
        body = text[match.end() : end - 1].strip()
        if "," not in body:
            raise BibTeXParseError(f"BibTeX entry {entry_type!r} has no citation key")
        key, field_text = body.split(",", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9:._-]*", key):
            raise BibTeXParseError(f"invalid BibTeX citation key: {key!r}")
        if key in seen_keys:
            raise BibTeXParseError(f"duplicate BibTeX citation key: {key}")
        fields = _parse_fields(field_text)
        entries.append(_entry_from_fields(key, entry_type, fields))
        seen_keys.add(key)
    return entries


def render_bibtex(entries: Iterable[BibTeXEntry]) -> str:
    """Render entries in stable key order for reproducible manuscript artifacts."""

    ordered = sorted(entries, key=lambda entry: entry.citation_key)
    if len({entry.citation_key for entry in ordered}) != len(ordered):
        raise BibTeXParseError("duplicate BibTeX citation key")
    rendered: list[str] = []
    for entry in ordered:
        fields = {
            "author": " and ".join(entry.authors),
            "title": entry.title,
            "year": str(entry.year),
        }
        for name in ("doi", "url", "journal", "booktitle", "publisher"):
            value = getattr(entry, name)
            if value is not None:
                fields[name] = value
        rendered.append(f"@{entry.entry_type}{{{entry.citation_key},")
        rendered.extend(f"  {name} = {{{fields[name]}}}," for name in sorted(fields))
        rendered.append("}")
    return "\n\n".join(rendered) + ("\n" if rendered else "")


def extract_citation_keys(markdown: str) -> list[str]:
    """Extract common Markdown/LaTeX citation forms while preserving first-seen order."""

    found: list[str] = []
    matches: list[tuple[int, list[str]]] = []
    for match in re.finditer(r"\\cite[a-zA-Z]*\{([^}]*)\}", markdown):
        matches.append(
            (match.start(), [item.strip().lstrip("@") for item in match.group(1).split(",")])
        )
    for match in re.finditer(r"\[@([A-Za-z][A-Za-z0-9:._-]*)", markdown):
        matches.append((match.start(), [match.group(1)]))
    for match in re.finditer(r";\s*@([A-Za-z][A-Za-z0-9:._-]*)", markdown):
        matches.append((match.start(), [match.group(1)]))
    for _, candidates in sorted(matches, key=lambda item: item[0]):
        for key in candidates:
            if key and key not in found:
                found.append(key)
    return found


def validate_citations(
    markdown: str,
    bibliography: Iterable[BibTeXEntry],
) -> CitationValidationReport:
    """Report every cited key missing from the parsed bibliography."""

    entries = list(bibliography)
    seen: set[str] = set()
    duplicate_keys: list[str] = []
    by_key: dict[str, BibTeXEntry] = {}
    for entry in entries:
        if entry.citation_key in seen and entry.citation_key not in duplicate_keys:
            duplicate_keys.append(entry.citation_key)
        seen.add(entry.citation_key)
        by_key.setdefault(entry.citation_key, entry)
    cited_keys = extract_citation_keys(markdown)
    missing_keys = [key for key in cited_keys if key not in by_key]
    resolved_keys = [key for key in cited_keys if key in by_key]
    return CitationValidationReport(
        status="failed" if missing_keys or duplicate_keys else "passed",
        cited_keys=cited_keys,
        resolved_keys=resolved_keys,
        missing_keys=missing_keys,
        duplicate_keys=duplicate_keys,
    )


def validate_bibtex_citations(markdown: str, bibtex: str) -> CitationValidationReport:
    """Parse a BibTeX source and return a non-throwing citation validation report."""

    try:
        entries = parse_bibtex(bibtex)
    except BibTeXParseError as error:
        return CitationValidationReport(status="failed", parse_errors=[str(error)])
    return validate_citations(markdown, entries)


def _find_entry_end(text: str, opening_index: int, opening: str) -> int | None:
    closing = "}" if opening == "{" else ")"
    depth = 0
    in_quote = False
    escaped = False
    for index in range(opening_index, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    while index < len(text):
        while index < len(text) and (text[index].isspace() or text[index] == ","):
            index += 1
        if index >= len(text):
            break
        name_start = index
        while index < len(text) and text[index] not in "=,":
            index += 1
        if index >= len(text) or text[index] != "=":
            raise BibTeXParseError("BibTeX field is missing '='")
        name = text[name_start:index].strip().lower()
        if not name:
            raise BibTeXParseError("BibTeX field name cannot be blank")
        index += 1
        while index < len(text) and text[index].isspace():
            index += 1
        value, index = _read_value(text, index)
        fields[name] = _clean_value(value)
    return fields


def _read_value(text: str, index: int) -> tuple[str, int]:
    if index >= len(text):
        raise BibTeXParseError("BibTeX field value cannot be blank")
    if text[index] == "{":
        end = _find_entry_end(text, index, "{")
        if end is None:
            raise BibTeXParseError("unterminated BibTeX braced value")
        return text[index + 1 : end - 1], end
    if text[index] == '"':
        end = index + 1
        escaped = False
        while end < len(text):
            if escaped:
                escaped = False
            elif text[end] == "\\":
                escaped = True
            elif text[end] == '"':
                return text[index + 1 : end], end + 1
            end += 1
        raise BibTeXParseError("unterminated BibTeX quoted value")
    end = index
    while end < len(text) and text[end] != ",":
        end += 1
    return text[index:end], end


def _clean_value(value: str) -> str:
    return " ".join(value.replace("\n", " ").split()).strip("{} ")


def _entry_from_fields(key: str, entry_type: str, fields: dict[str, str]) -> BibTeXEntry:
    required = {"author", "title", "year"}
    missing = sorted(required.difference(fields))
    if missing:
        raise BibTeXParseError(f"BibTeX entry {key!r} is missing: {', '.join(missing)}")
    year_match = re.search(r"\b(\d{4})\b", fields["year"])
    if year_match is None:
        raise BibTeXParseError(f"BibTeX entry {key!r} has an invalid year")
    authors = [
        author.strip() for author in re.split(r"\s+and\s+", fields["author"]) if author.strip()
    ]
    if not authors:
        raise BibTeXParseError(f"BibTeX entry {key!r} has no authors")
    doi = fields.get("doi")
    if doi is not None:
        doi = re.sub(r"^https?://doi\.org/", "", doi, flags=re.IGNORECASE).strip()
    return BibTeXEntry(
        citation_key=key,
        entry_type=entry_type,  # type: ignore[arg-type]
        title=fields["title"],
        authors=authors,
        year=int(year_match.group(1)),
        doi=doi,
        url=fields.get("url"),
        journal=fields.get("journal"),
        booktitle=fields.get("booktitle"),
        publisher=fields.get("publisher"),
    )
