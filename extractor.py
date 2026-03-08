import hashlib
import io
import json
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from pypdf import PdfReader


def _clean(text):
    return " ".join(text.replace("\n", " ").replace("\t", " ").split())


def _hash_id(value):
    return hashlib.md5(value.encode("utf-8")).hexdigest()[:12]


def _detect_source(url, hint):
    if hint and hint != "auto":
        return hint
    low = url.lower()
    if "grants.gov" in low:
        return "grantsgov"
    if "nsf.gov" in low:
        return "nsf"
    return "generic"


def _agency(text, url, source):
    hay = f"{text} {url}".lower()
    if source == "grantsgov":
        return "Grants.gov"
    if source == "nsf" or "national science foundation" in hay or "nsf" in hay:
        return "NSF"
    if "national institutes of health" in hay or "nih" in hay:
        return "NIH"
    if "department of energy" in hay or "doe" in hay:
        return "DOE"
    return "Unknown"


def _read_local(path):
    path = path.replace("file://", "")
    with open(path, "rb") as f:
        raw = f.read()
    if path.lower().endswith(".pdf"):
        return "", _pdf_to_text(raw), None
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError:
        html = raw.decode("latin-1", errors="ignore")
    title, text = _html_to_text(html)
    return title, text, html


def _download(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FOA-Intelligence/1.0)",
        "Accept": "text/html,application/pdf,application/json;q=0.9,*/*;q=0.8",
    }
    res = requests.get(url, headers=headers, timeout=30)
    res.raise_for_status()
    ctype = (res.headers.get("Content-Type") or "").lower()
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        return "", _pdf_to_text(res.content), None
    title, text = _html_to_text(res.text)
    return title, text, res.text


def _pdf_to_text(content):
    reader = PdfReader(io.BytesIO(content))
    return _clean(" ".join((p.extract_text() or "") for p in reader.pages))


def _html_to_text(content):
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = ""
    h1 = soup.find("h1")
    if h1:
        title = _clean(h1.get_text(" ", strip=True))
    elif soup.title:
        title = _clean(soup.title.get_text(" ", strip=True))
    return title, _clean(soup.get_text(separator=" ", strip=True))


def _find_foa_id(text, url):
    for p in [r"\b[A-Z]{2,8}-\d{2}-\d{3}\b", r"\b[A-Z]{2,10}\s?\d{2}-\d{3}\b", r"\b\d{2}-\d{3}\b"]:
        m = re.search(p, text)
        if m:
            return _clean(m.group(0))
    return _hash_id(url)


def _to_iso(value):
    try:
        return date_parser.parse(value, fuzzy=True, default=datetime(1900, 1, 1)).date().isoformat()
    except Exception:
        return ""


def _extract_dates(text):
    patt = r"([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    def find(labels):
        for label in labels:
            m = re.search(rf"{label}[^.\n:]*[:\-]?\s*{patt}", text, flags=re.IGNORECASE)
            if m:
                return _to_iso(m.group(1))
        return ""
    open_date = find([r"open(?:ing)? date", r"posted date", r"published date", r"release date", r"issue date"])
    close_date = find([r"close(?:ing)? date", r"due date", r"application deadline", r"deadline", r"expires"])
    return open_date, close_date


def _extract_section(text, keys, max_len=900):
    for k in keys:
        m = re.search(rf"{k}[:\s-]+(.{{60,{max_len}}}?)(?:\.|\n|$)", text, flags=re.IGNORECASE)
        if m:
            return _clean(m.group(1))
    return ""


def _extract_award(text):
    m = re.search(r"(\$\s?\d[\d,]*(?:\.\d+)?\s*(?:to|\-|\u2013)\s*\$\s?\d[\d,]*(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m:
        return _clean(m.group(1))
    m = re.search(r"\$\s?\d[\d,]*(?:\.\d+)?", text)
    return _clean(m.group(0)) if m else ""


def _extract_jsonld(raw_html):
    fields = {}
    if not raw_html:
        return fields
    soup = BeautifulSoup(raw_html, "html.parser")
    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not s.string:
            continue
        try:
            payload = json.loads(s.string)
        except Exception:
            continue
        objs = payload if isinstance(payload, list) else [payload]
        for obj in objs:
            if not isinstance(obj, dict):
                continue
            if not fields.get("title") and isinstance(obj.get("name"), str):
                fields["title"] = _clean(obj["name"])
            if not fields.get("program_description") and isinstance(obj.get("description"), str):
                fields["program_description"] = _clean(obj["description"])
    return fields


def extract_foa(url, source_hint="auto"):
    source = _detect_source(url, source_hint)
    fallback = {
        "foa_id": _hash_id(url), "title": "Unavailable", "agency": _agency("", url, source), "open_date": "", "close_date": "",
        "eligibility": "", "program_description": "Unable to retrieve source content from URL at runtime.", "award_range": "",
        "source_url": url, "source_type": source,
    }
    try:
        title, text, raw_html = _read_local(url) if (url.lower().startswith("file://") or os.path.exists(url)) else _download(url)
    except Exception:
        return fallback
    if not text:
        return fallback

    open_date, close_date = _extract_dates(text)
    rec = {
        "foa_id": _find_foa_id(text, url),
        "title": title or text[:140],
        "agency": _agency(text, url, source),
        "open_date": open_date,
        "close_date": close_date,
        "eligibility": _extract_section(text, [r"eligibility", r"who may apply", r"eligible applicants", r"applicant eligibility"]),
        "program_description": _extract_section(text, [r"program description", r"synopsis", r"description", r"purpose", r"program overview"], 1600) or text[:1800],
        "award_range": _extract_award(text),
        "source_url": url,
        "source_type": source,
    }
    rec.update(_extract_jsonld(raw_html))
    if source == "nsf":
        m = re.search(r"\bNSF\s*\d{2}-\d{3}\b", text, flags=re.IGNORECASE)
        if m:
            rec["foa_id"] = _clean(m.group(0)).upper()
    elif source == "grantsgov":
        m = re.search(r"\bFunding Opportunity Number\b[:\s-]+([A-Za-z0-9\-_.]+)", text, flags=re.IGNORECASE)
        if m:
            rec["foa_id"] = _clean(m.group(1))
    return rec
