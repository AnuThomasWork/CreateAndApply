"""Load a job description from pasted text, a text file, or a job-posting URL."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (CreateAndApply; personal job-search tool)"}


@dataclass
class JobPosting:
    text: str
    title: str = ""
    company: str = ""
    source: str = "text"


def _clean(text: str) -> str:
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _from_json_ld(soup: BeautifulSoup) -> JobPosting | None:
    """Most job boards (Greenhouse, Lever, Workday, Indeed...) embed schema.org JobPosting."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and "@graph" in item:
                items.extend(item["@graph"])
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                desc = BeautifulSoup(item.get("description", ""), "html.parser").get_text("\n")
                org = item.get("hiringOrganization") or {}
                company = org.get("name", "") if isinstance(org, dict) else str(org)
                return JobPosting(_clean(desc), item.get("title", ""), company, "json-ld")
    return None


def from_url(url: str, timeout: int = 20) -> JobPosting:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    posting = _from_json_ld(soup)
    if posting and len(posting.text) > 200:
        posting.source = url
        return posting

    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "svg", "form"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = _clean(main.get_text("\n"))
    title = (soup.title.string or "").strip() if soup.title else ""
    if len(text) < 200:
        raise ValueError(
            "Could not extract a job description from this page (it may need JavaScript or a login). "
            "Copy the text into a file and use --job-file instead."
        )
    return JobPosting(text, title, "", url)


def from_file(path: str) -> JobPosting:
    with open(path, encoding="utf-8") as fh:
        return JobPosting(_clean(fh.read()), source=path)


def from_text(text: str) -> JobPosting:
    return JobPosting(_clean(text))
