#!/usr/bin/env python3
"""
Daily updater for a rehabilitation paper digest site.

The script fetches recent PubMed records, filters them, asks Claude to evaluate
and summarize safe candidates, writes article Markdown, updates duplicate state,
and rebuilds static HTML for GitHub Pages.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import sys
import textwrap
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - GitHub Actions installs requirements.
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data"
CONTENT_DIR = PROJECT_ROOT / "content" / "articles"
PUBLIC_DIR = PROJECT_ROOT / "public"
PROCESSED_PATH = DATA_DIR / "processed_articles.json"
DISCLAIMER = (
    "本記事は論文の書誌情報および抄録を基にAIを利用して作成した要約です。"
    "診断・治療等の医学的助言を目的とするものではありません。"
    "詳細は原著論文をご確認ください。"
)
CATEGORY_SLUGS = {
    "作業療法": "occupational-therapy",
    "理学療法": "physical-therapy",
    "言語聴覚療法": "speech-language-therapy",
    "脳卒中": "stroke",
    "神経疾患": "neurological-disease",
    "認知症": "dementia",
    "高齢者": "older-adults",
    "整形外科": "orthopedics",
    "精神科": "psychiatry",
    "小児": "pediatrics",
    "認知機能": "cognitive-function",
    "ADL": "adl",
    "歩行": "gait",
    "上肢機能": "upper-limb",
    "福祉用具・支援技術": "assistive-technology",
    "その他": "other",
}


@dataclass
class Paper:
    pmid: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    published_date: str = ""
    doi: str = ""
    publication_types: list[str] = field(default_factory=list)
    pubmed_url: str = ""
    source_url: str = ""

    @property
    def identifier(self) -> str:
        return self.pmid or self.doi.lower()


def log(message: str) -> None:
    print(f"[daily-update] {message}", flush=True)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config: {CONFIG_PATH}")
    text = CONFIG_PATH.read_text(encoding="utf-8")
    if yaml:
        return yaml.safe_load(text)
    return simple_yaml_load(text)


def simple_yaml_load(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by config.yaml when PyYAML is absent."""
    lines = text.splitlines()
    data: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        raw = strip_comment(lines[i]).rstrip()
        if not raw:
            i += 1
            continue
        if not raw.startswith(" ") and raw.endswith(":"):
            key = raw[:-1].strip()
            i += 1
            block, i = parse_yaml_block(lines, i, 2)
            data[key] = block
            continue
        i += 1
    return data


def parse_yaml_block(lines: list[str], i: int, indent: int) -> tuple[Any, int]:
    items: list[Any] = []
    mapping: dict[str, Any] = {}
    mode = None
    while i < len(lines):
        raw_line = lines[i]
        raw = strip_comment(raw_line).rstrip()
        if not raw:
            i += 1
            continue
        current_indent = len(raw_line) - len(raw_line.lstrip(" "))
        if current_indent < indent:
            break
        content = raw_line[indent:].rstrip()
        if content.startswith("- "):
            mode = "list"
            items.append(parse_scalar(content[2:].strip()))
            i += 1
            continue
        if ":" in content:
            mode = "map"
            key, value = content.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value == ">":
                collected = []
                i += 1
                while i < len(lines):
                    nested_raw = lines[i]
                    nested = strip_comment(nested_raw).rstrip()
                    nested_indent = len(nested_raw) - len(nested_raw.lstrip(" "))
                    if nested and nested_indent <= indent:
                        break
                    if nested:
                        collected.append(nested.strip())
                    i += 1
                mapping[key] = " ".join(collected)
                continue
            if value:
                mapping[key] = parse_scalar(value)
                i += 1
                continue
            i += 1
            nested, i = parse_yaml_block(lines, i, indent + 2)
            mapping[key] = nested
            continue
        i += 1
    return (items if mode == "list" else mapping), i


def strip_comment(line: str) -> str:
    in_quote = False
    quote = ""
    for idx, char in enumerate(line):
        if char in {"'", '"'}:
            if in_quote and char == quote:
                in_quote = False
            elif not in_quote:
                in_quote = True
                quote = char
        if char == "#" and not in_quote:
            return line[:idx]
    return line


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", ""}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def ensure_dirs() -> None:
    for path in [DATA_DIR, CONTENT_DIR, PUBLIC_DIR, PUBLIC_DIR / "assets"]:
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = path.with_suffix(path.suffix + ".broken")
        shutil.copyfile(path, backup)
        log(f"Broken JSON moved aside: {backup}")
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def http_request_json(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def http_request_text(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> str:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read().decode("utf-8", errors="replace")


class PubMedClient:
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.email = config.get("contact_email", "")
        self.tool = config.get("tool_name", "rehab-paper-digest")
        self.api_key = os.getenv("NCBI_API_KEY", "")

    def _common_params(self) -> dict[str, str]:
        params = {"tool": self.tool}
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def search_recent(self) -> list[str]:
        pubmed = self.config["pubmed"]
        lookback_days = max(1, int((int(pubmed.get("lookback_hours", 48)) + 23) / 24))
        params: dict[str, Any] = {
            "db": "pubmed",
            "term": pubmed["search_query"],
            "retmode": "json",
            "retmax": int(pubmed.get("retmax", 100)),
            "sort": "pub+date",
            "datetype": pubmed.get("date_type", "edat"),
            "reldate": lookback_days,
        }
        params.update(self._common_params())
        data = http_request_json(f"{self.base_url}/esearch.fcgi", params=params)
        return data.get("esearchresult", {}).get("idlist", [])

    def fetch_details(self, pmids: list[str]) -> list[Paper]:
        if not pmids:
            return []
        papers: list[Paper] = []
        batch_size = 100
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i : i + batch_size]
            params = {
                "db": "pubmed",
                "id": ",".join(batch),
                "retmode": "xml",
            }
            params.update(self._common_params())
            xml_text = http_request_text(f"{self.base_url}/efetch.fcgi", params=params)
            papers.extend(parse_pubmed_xml(xml_text))
            time.sleep(float(self.config["pubmed"].get("request_interval_seconds", 0.34)))
        return papers


def parse_pubmed_xml(xml_text: str) -> list[Paper]:
    root = ET.fromstring(xml_text)
    papers: list[Paper] = []
    for article_node in root.findall(".//PubmedArticle"):
        medline = article_node.find("MedlineCitation")
        article = medline.find("Article") if medline is not None else None
        if medline is None or article is None:
            continue
        pmid = text_or_empty(medline.find("PMID"))
        title = collect_text(article.find("ArticleTitle"))
        abstract = collect_abstract(article)
        journal = collect_text(article.find("Journal/Title")) or collect_text(article.find("Journal/ISOAbbreviation"))
        published_date = parse_pub_date(article.find("Journal/JournalIssue/PubDate"))
        authors = collect_authors(article)
        doi = collect_doi(article_node)
        pub_types = [collect_text(node) for node in article.findall(".//PublicationType")]
        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
        source_url = f"https://doi.org/{doi}" if doi else pubmed_url
        papers.append(
            Paper(
                pmid=pmid,
                title=normalize_space(title),
                abstract=normalize_space(abstract),
                authors=authors,
                journal=normalize_space(journal),
                published_date=published_date,
                doi=doi,
                publication_types=[p for p in pub_types if p],
                pubmed_url=pubmed_url,
                source_url=source_url,
            )
        )
    return papers


def text_or_empty(node: ET.Element | None) -> str:
    return node.text.strip() if node is not None and node.text else ""


def collect_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def collect_abstract(article: ET.Element) -> str:
    parts = []
    for node in article.findall(".//Abstract/AbstractText"):
        label = node.attrib.get("Label") or node.attrib.get("NlmCategory")
        text = collect_text(node)
        if not text:
            continue
        parts.append(f"{label}: {text}" if label else text)
    return "\n".join(parts)


def collect_authors(article: ET.Element) -> list[str]:
    authors = []
    for author in article.findall(".//AuthorList/Author"):
        collective = text_or_empty(author.find("CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        last = text_or_empty(author.find("LastName"))
        initials = text_or_empty(author.find("Initials"))
        fore = text_or_empty(author.find("ForeName"))
        name = " ".join(part for part in [last, initials or fore] if part)
        if name:
            authors.append(name)
    return authors[:12]


def collect_doi(article_node: ET.Element) -> str:
    for node in article_node.findall(".//ArticleId"):
        if node.attrib.get("IdType") == "doi" and node.text:
            return node.text.strip()
    for node in article_node.findall(".//ELocationID"):
        if node.attrib.get("EIdType") == "doi" and node.text:
            return node.text.strip()
    return ""


def parse_pub_date(node: ET.Element | None) -> str:
    if node is None:
        return ""
    year = text_or_empty(node.find("Year"))
    month = normalize_month(text_or_empty(node.find("Month")))
    day = text_or_empty(node.find("Day")) or "01"
    if year:
        try:
            return dt.date(int(year), int(month or "1"), int(day)).isoformat()
        except ValueError:
            return f"{year}-{month or '01'}-01"
    return normalize_space(collect_text(node))


def normalize_month(value: str) -> str:
    if not value:
        return ""
    months = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }
    value = value.strip()
    if value.isdigit():
        return value.zfill(2)
    return months.get(value[:3].lower(), "01")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def filter_papers(papers: list[Paper], config: dict[str, Any], processed: dict[str, Any]) -> tuple[list[Paper], dict[str, int]]:
    seen_ids = set(processed.get("ids", []))
    excluded_types = {x.lower() for x in config["pubmed"].get("exclude_publication_types", [])}
    exclude_keywords = [x.lower() for x in config["pubmed"].get("exclude_keywords", [])]
    candidates = []
    stats = {
        "missing_abstract": 0,
        "duplicate": 0,
        "excluded_type": 0,
        "excluded_keyword": 0,
        "missing_identifier": 0,
    }
    for paper in papers:
        if not paper.identifier:
            stats["missing_identifier"] += 1
            continue
        if paper.identifier in seen_ids:
            stats["duplicate"] += 1
            continue
        if not paper.abstract:
            stats["missing_abstract"] += 1
            continue
        pub_types = {x.lower() for x in paper.publication_types}
        if excluded_types.intersection(pub_types):
            stats["excluded_type"] += 1
            continue
        combined = f"{paper.title} {paper.abstract}".lower()
        if any(keyword in combined for keyword in exclude_keywords):
            stats["excluded_keyword"] += 1
            continue
        candidates.append(paper)
    return candidates, stats


class ClaudeClient:
    def __init__(self, config: dict[str, Any], dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.calls = 0
        self.max_calls = int(config["claude"].get("max_api_calls_per_day", 20))

    def available(self) -> bool:
        return bool(self.api_key)

    def json_completion(self, system: str, prompt: str, schema: dict[str, Any], max_tokens: int) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        if self.calls >= self.max_calls:
            raise RuntimeError("Claude API call limit reached")
        self.calls += 1
        guided_prompt = (
            f"{prompt}\n\n"
            "Return only valid JSON. Do not wrap it in Markdown. "
            "The JSON must match this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False)}"
        )
        payload = {
            "model": self.config["claude"]["model"],
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": guided_prompt}],
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.config["claude"].get("anthropic_version", "2023-06-01"),
        }
        delay = 2.0
        for attempt in range(1, int(self.config["claude"].get("max_retries", 3)) + 1):
            try:
                text = http_request_text(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    data=body,
                )
                data = json.loads(text)
                return parse_claude_json(data)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:500]
                detail = re.sub(r"\s+", " ", detail).strip()
                if attempt >= int(self.config["claude"].get("max_retries", 3)):
                    raise RuntimeError(f"Claude API failed after retries: HTTP {exc.code} {detail}") from exc
                log(f"Claude API retry {attempt}: HTTP {exc.code} {detail}")
                time.sleep(delay)
                delay *= 2
            except (urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
                if attempt >= int(self.config["claude"].get("max_retries", 3)):
                    raise RuntimeError(f"Claude API failed after retries: {type(exc).__name__}") from exc
                log(f"Claude API retry {attempt}: {type(exc).__name__}")
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("Claude API failed")


def parse_claude_json(data: dict[str, Any]) -> dict[str, Any]:
    text_parts = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
    raw = "\n".join(text_parts).strip()
    if not raw:
        raise ValueError("Claude response did not include text JSON")
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    if not raw.startswith("{"):
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            raw = match.group(0)
    return json.loads(raw)


EVALUATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["clinical_importance", "novelty", "usefulness", "design_strength", "reader_interest", "total_score", "categories", "reason"],
    "properties": {
        "clinical_importance": {"type": "number", "minimum": 0, "maximum": 5},
        "novelty": {"type": "number", "minimum": 0, "maximum": 5},
        "usefulness": {"type": "number", "minimum": 0, "maximum": 5},
        "design_strength": {"type": "number", "minimum": 0, "maximum": 5},
        "reader_interest": {"type": "number", "minimum": 0, "maximum": 5},
        "total_score": {"type": "number", "minimum": 0, "maximum": 25},
        "categories": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
}

ARTICLE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title_ja",
        "one_sentence_summary",
        "background",
        "participants",
        "methods",
        "results",
        "clinical_meaning",
        "limitations",
        "categories",
        "score",
    ],
    "properties": {
        "title_ja": {"type": "string"},
        "one_sentence_summary": {"type": "string"},
        "background": {"type": "string"},
        "participants": {"type": "string"},
        "methods": {"type": "string"},
        "results": {"type": "string"},
        "clinical_meaning": {"type": "string"},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "categories": {"type": "array", "items": {"type": "string"}},
        "score": EVALUATION_SCHEMA,
    },
}


SYSTEM_PROMPT = """
あなたは医学・リハビリテーション領域の論文抄録を、日本語で慎重に要約する編集者です。
与えられたタイトル・書誌情報・抄録以外に記載されていない研究内容を推測してはいけません。
論文本文を読んだように書いてはいけません。
結果、対象者数、統計値、因果関係を補完・誇張してはいけません。
抄録に情報がない項目は、本文中に「記載されていません」「不明です」と補足しないでください。
ただし研究解釈に重要な不足情報だけは、最後の限界に短く含めてください。
医学的助言、診断、治療指示として読める表現は避けてください。
煽り表現は禁止です。
""".strip()


def paper_payload(paper: Paper) -> str:
    return json.dumps(
        {
            "title": paper.title,
            "authors": paper.authors,
            "journal": paper.journal,
            "published_date": paper.published_date,
            "doi": paper.doi,
            "pmid": paper.pmid,
            "publication_types": paper.publication_types,
            "abstract": paper.abstract,
        },
        ensure_ascii=False,
        indent=2,
    )


def evaluate_with_claude(client: ClaudeClient, paper: Paper, categories: list[str]) -> dict[str, Any]:
    prompt = f"""
以下の論文について、掲載価値を0から5点で評価してください。総合スコアは各項目の合計です。
カテゴリは次の候補から選んでください: {", ".join(categories)}

論文情報:
{paper_payload(paper)}
""".strip()
    result = client.json_completion(SYSTEM_PROMPT, prompt, EVALUATION_SCHEMA, max_tokens=1200)
    return normalize_evaluation(result, categories)


def generate_article_with_claude(
    client: ClaudeClient,
    paper: Paper,
    evaluation: dict[str, Any],
    categories: list[str],
) -> dict[str, Any]:
    prompt = f"""
以下の論文について、一般の医療職が短時間で理解できる日本語記事用の構造化JSONを作成してください。
本文はアブストラクトに近い項目立てで、背景・目的、対象、方法、結果、臨床的示唆、限界が自然に読めるようにしてください。
対象は抄録から確認できる集団・人数・条件だけを書いてください。年齢、性別などの詳細属性が抄録にない場合は、その欠落を対象欄に書かないでください。
抄録にない情報を「記載されていません」「不明です」と項目埋めのために書かないでください。
カテゴリは次の候補から選んでください: {", ".join(categories)}
scoreには、事前評価JSONをそのまま反映してください。

事前評価JSON:
{json.dumps(evaluation, ensure_ascii=False, indent=2)}

論文情報:
{paper_payload(paper)}
""".strip()
    result = client.json_completion(SYSTEM_PROMPT, prompt, ARTICLE_SCHEMA, max_tokens=3600)
    return normalize_article(result, evaluation, categories)


def normalize_evaluation(result: dict[str, Any], categories: list[str]) -> dict[str, Any]:
    normalized = dict(result)
    for key in ["clinical_importance", "novelty", "usefulness", "design_strength", "reader_interest"]:
        normalized[key] = max(0.0, min(5.0, float(normalized.get(key, 0))))
    normalized["total_score"] = sum(normalized[key] for key in ["clinical_importance", "novelty", "usefulness", "design_strength", "reader_interest"])
    allowed = set(categories)
    normalized["categories"] = [c for c in normalized.get("categories", []) if c in allowed] or ["その他"]
    normalized["reason"] = str(normalized.get("reason", ""))[:400]
    return normalized


def normalize_article(result: dict[str, Any], evaluation: dict[str, Any], categories: list[str]) -> dict[str, Any]:
    normalized = dict(result)
    allowed = set(categories)
    normalized["categories"] = [c for c in normalized.get("categories", []) if c in allowed] or evaluation.get("categories", ["その他"])
    normalized["score"] = normalize_evaluation(normalized.get("score") or evaluation, categories)
    for key in ["title_ja", "one_sentence_summary", "background", "methods", "results", "clinical_meaning"]:
        normalized[key] = safe_article_text(str(normalized.get(key) or "抄録には記載されていません"))
    normalized["participants"] = clean_missing_info_text(str(normalized.get("participants") or ""))
    limitations = normalized.get("limitations") or []
    normalized["limitations"] = [safe_article_text(str(item)) for item in limitations if str(item).strip()]
    return normalized


def clean_missing_info_text(value: str) -> str:
    value = normalize_space(value)
    if not value:
        return ""
    sentences = re.split(r"(?<=[。！？.!?])\s*", value)
    kept = []
    for sentence in sentences:
        text = sentence.strip()
        if not text:
            continue
        if re.search(r"(記載されていません|記載はありません|不明です|不明である)", text):
            continue
        kept.append(text)
    return normalize_space("".join(kept))


def safe_article_text(value: str) -> str:
    value = normalize_space(value)
    if not value:
        return "抄録には記載されていません"
    return value


def heuristic_evaluation(paper: Paper, categories: list[str]) -> dict[str, Any]:
    text = f"{paper.title} {paper.abstract}".lower()
    design = 1.5
    if any(word in text for word in ["randomized", "randomised", "trial", "meta-analysis", "systematic review"]):
        design = 4.0
    if any(word in text for word in ["cohort", "longitudinal"]):
        design = max(design, 3.0)
    matched = [c for c in categories if category_matches(c, text)]
    base = min(5.0, 2.5 + len(paper.abstract) / 1200)
    return normalize_evaluation(
        {
            "clinical_importance": base,
            "novelty": 2.5,
            "usefulness": base,
            "design_strength": design,
            "reader_interest": base,
            "total_score": 0,
            "categories": matched or ["その他"],
            "reason": "Claudeを使わないテスト用の簡易評価です。",
        },
        categories,
    )


def category_matches(category: str, text: str) -> bool:
    mapping = {
        "作業療法": ["occupational therapy"],
        "理学療法": ["physical therapy", "physiotherapy"],
        "言語聴覚療法": ["speech", "language", "dysphagia"],
        "脳卒中": ["stroke"],
        "神経疾患": ["neurolog", "parkinson", "multiple sclerosis"],
        "認知症": ["dementia", "alzheimer"],
        "高齢者": ["older", "elderly", "aged"],
        "整形外科": ["orthop", "fracture", "knee", "hip"],
        "精神科": ["psychiatr", "mental"],
        "小児": ["child", "pediatric", "paediatric"],
        "認知機能": ["cognitive", "cognition"],
        "ADL": ["activities of daily living", " adl"],
        "歩行": ["gait", "walking"],
        "上肢機能": ["upper extremity", "upper limb"],
        "福祉用具・支援技術": ["assistive technology", "device"],
    }
    return any(keyword in text for keyword in mapping.get(category, []))


def slugify(title: str, fallback: str) -> str:
    if title in CATEGORY_SLUGS:
        return CATEGORY_SLUGS[title]
    base = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base.lower()).strip("-")
    if not base:
        base = hashlib.sha1(fallback.encode("utf-8")).hexdigest()[:12]
    return base[:80].strip("-")


def article_markdown(paper: Paper, article: dict[str, Any], slug: str, now: dt.datetime) -> str:
    published = paper.published_date or now.date().isoformat()
    year, month = published[:4], published[5:7] if len(published) >= 7 else "01"
    metadata = {
        "title": article["title_ja"],
        "original_title": paper.title,
        "authors": paper.authors,
        "journal": paper.journal,
        "published_date": published,
        "generated_at": now.isoformat(timespec="seconds"),
        "updated_at": now.isoformat(timespec="seconds"),
        "doi": paper.doi,
        "pmid": paper.pmid,
        "source_url": paper.source_url,
        "pubmed_url": paper.pubmed_url,
        "slug": slug,
        "url_path": f"/articles/{year}/{month}/{slug}/",
        "categories": article["categories"],
        "score": article["score"],
        "summary": article["one_sentence_summary"],
        "background": article["background"],
        "participants": article["participants"],
        "methods": article["methods"],
        "results": article["results"],
        "clinical_meaning": article["clinical_meaning"],
        "limitations": article["limitations"],
        "disclaimer": DISCLAIMER,
    }
    front_matter = json.dumps(metadata, ensure_ascii=False, indent=2)
    limitations = "\n".join(f"- {item}" for item in article["limitations"]) or "- 抄録から判断できる明確な限界は記載されていません。"
    participants_section = f'\n## 対象\n\n{article["participants"]}\n' if article["participants"] else ""
    return f"""---
{front_matter}
---

# {article["title_ja"]}

**Original title:** {paper.title}

## 原著論文

- Original title: {paper.title}
- 著者: {", ".join(paper.authors) if paper.authors else "抄録には記載されていません"}
- 雑誌名: {paper.journal or "抄録には記載されていません"}
- 出版年月日: {published}
- DOI: {paper.doi or "抄録には記載されていません"}
- PMID: {paper.pmid or "抄録には記載されていません"}
- 原著論文へのリンク: {paper.source_url or paper.pubmed_url}

## 概要

{article["one_sentence_summary"]}

## 背景・目的

{article["background"]}
{participants_section}

## 方法

{article["methods"]}

## 結果

{article["results"]}

## 臨床的示唆

{article["clinical_meaning"]}

## 限界

{limitations}

## 原著論文を確認する

{paper.source_url or paper.pubmed_url}

{DISCLAIMER}
"""


def write_article(paper: Paper, article: dict[str, Any], now: dt.datetime) -> tuple[Path, dict[str, Any]]:
    published = paper.published_date or now.date().isoformat()
    year = published[:4] if len(published) >= 4 else str(now.year)
    month = published[5:7] if len(published) >= 7 else f"{now.month:02d}"
    slug = slugify(paper.title, paper.identifier)
    path = CONTENT_DIR / year / month / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = article_markdown(paper, article, slug, now)
    path.write_text(text, encoding="utf-8")
    metadata = parse_article_file(path)["metadata"]
    return path, metadata


def parse_article_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"Article missing front matter: {path}")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError(f"Article front matter not closed: {path}")
    raw = text[3:end].strip()
    metadata = json.loads(raw)
    body = text[end + 4 :].strip()
    return {"metadata": metadata, "body": body, "path": path}


def load_articles() -> list[dict[str, Any]]:
    if not CONTENT_DIR.exists():
        return []
    articles = []
    for path in CONTENT_DIR.rglob("*.md"):
        try:
            articles.append(parse_article_file(path))
        except Exception as exc:
            log(f"Skip broken article {path}: {exc}")
    articles.sort(key=lambda item: item["metadata"].get("published_date", ""), reverse=True)
    return articles


def render_site(config: dict[str, Any]) -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    (PUBLIC_DIR / "assets").mkdir(parents=True, exist_ok=True)
    articles = load_articles()
    write_static_assets(config)
    render_index(config, articles)
    render_listing(config, articles, PUBLIC_DIR / "articles" / "index.html", "新着論文", "公開済みの記事を新しい順に掲載しています。")
    render_category_pages(config, articles)
    render_archive_pages(config, articles)
    render_article_pages(config, articles)
    render_search_json(config, articles)
    render_rss(config, articles)
    render_sitemap(config, articles)
    render_robots(config)


def site_url(config: dict[str, Any]) -> str:
    return config["site"].get("url", "").rstrip("/")


def base_path(config: dict[str, Any]) -> str:
    raw = (config["site"].get("base_path") or "").strip("/")
    return f"/{raw}" if raw else ""


def public_path(config: dict[str, Any], path: str) -> str:
    if path.startswith(("http://", "https://", "mailto:")):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return f"{base_path(config)}{path}" or "/"


def absolute_url(config: dict[str, Any], path: str) -> str:
    base = site_url(config)
    route = public_path(config, path)
    return f"{base}{route}" if base else route


def page_shell(config: dict[str, Any], title: str, description: str, path: str, body: str) -> str:
    canonical = absolute_url(config, path)
    site_name = config["site"]["name"]
    description_esc = html.escape(description)
    title_full = f"{title} | {site_name}" if title != site_name else site_name
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title_full)}</title>
  <meta name="description" content="{description_esc}">
  <link rel="canonical" href="{html.escape(canonical)}">
  <meta name="site-base-path" content="{html.escape(base_path(config))}">
  <link rel="icon" href="{html.escape(public_path(config, '/assets/favicon.svg'))}" type="image/svg+xml">
  <link rel="alternate" type="application/rss+xml" title="{html.escape(site_name)} RSS" href="{html.escape(public_path(config, '/feed.xml'))}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{html.escape(title_full)}">
  <meta property="og:description" content="{description_esc}">
  <meta property="og:url" content="{html.escape(canonical)}">
  <meta property="og:site_name" content="{html.escape(site_name)}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{html.escape(title_full)}">
  <meta name="twitter:description" content="{description_esc}">
  <link rel="stylesheet" href="{html.escape(public_path(config, '/assets/styles.css'))}">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="{html.escape(public_path(config, '/'))}">{html.escape(site_name)}</a>
    <nav class="nav">
      <a href="{html.escape(public_path(config, '/articles/'))}">新着</a>
      <a href="{html.escape(public_path(config, '/categories/'))}">カテゴリ</a>
      <a href="{html.escape(public_path(config, '/diseases/'))}">疾患別</a>
      <a href="{html.escape(public_path(config, '/archive/'))}">年月別</a>
      <a href="{html.escape(public_path(config, '/feed.xml'))}">RSS</a>
    </nav>
  </header>
  <main>
{body}
  </main>
  <footer class="site-footer">
    <p>{html.escape(DISCLAIMER)}</p>
  </footer>
  <script src="{html.escape(public_path(config, '/assets/search.js'))}" defer></script>
</body>
</html>
"""


def article_card(config: dict[str, Any], article: dict[str, Any]) -> str:
    m = article["metadata"]
    cats = "".join(f'<span class="tag">{html.escape(c)}</span>' for c in m.get("categories", []))
    search_text = " ".join(
        str(value)
        for value in [
            m.get("title", ""),
            m.get("original_title", ""),
            m.get("summary", ""),
            m.get("journal", ""),
            m.get("pmid", ""),
            m.get("doi", ""),
            " ".join(m.get("categories", [])),
        ]
    ).lower()
    return f"""
<article class="article-card" data-search="{html.escape(search_text, quote=True)}" data-date="{html.escape(m.get("published_date", ""), quote=True)}">
  <div class="meta-line">{html.escape(m.get("published_date", ""))}</div>
  <h2><a href="{html.escape(public_path(config, m.get("url_path", "#")))}">{html.escape(m.get("title", ""))}</a></h2>
  <p class="original-title">{html.escape(m.get("original_title", ""))}</p>
  <p>{html.escape(m.get("summary", ""))}</p>
  <div class="tags">{cats}</div>
</article>
"""


def lookup_journal_impact_factor(config: dict[str, Any], journal: str) -> str:
    table = config.get("journal_impact_factors", {}) or {}
    if not isinstance(table, dict) or not journal:
        return ""
    normalized_journal = normalize_space(str(journal)).casefold()
    for name, value in table.items():
        if normalize_space(str(name)).casefold() == normalized_journal and str(value).strip():
            return str(value).strip()
    return ""


def render_index(config: dict[str, Any], articles: list[dict[str, Any]]) -> None:
    latest = "\n".join(article_card(config, a) for a in articles[: int(config["site"].get("homepage_items", 10))])
    if not latest:
        latest = '<p class="empty">まだ記事はありません。GitHub Actions の手動実行、または dry-run で取得状況を確認してください。</p>'
    body = f"""
    <section class="hero">
      <div>
        <p class="eyebrow">医学・リハビリテーション論文ダイジェスト</p>
        <h1>最新の論文</h1>
        <p>{html.escape(config["site"]["description"])}</p>
      </div>
      <form class="search-box list-tools" role="search">
        <label for="searchInput">検索</label>
        <input id="searchInput" type="search" placeholder="キーワード、カテゴリ、PMID">
        <label for="sortSelect">並び替え</label>
        <select id="sortSelect">
          <option value="new">新しい順</option>
          <option value="old">古い順</option>
        </select>
      </form>
    </section>
    <section class="content-grid">
      <div class="article-list" id="searchResults" data-search-mode="local">{latest}</div>
      <aside class="side-panel">
        <h2>カテゴリ</h2>
        {category_links(config, config["categories"], "/categories/")}
        <h2>疾患別</h2>
        {category_links(config, config["disease_categories"], "/diseases/")}
        <div class="ad-slot" data-slot="sidebar">広告枠</div>
      </aside>
    </section>
"""
    (PUBLIC_DIR / "index.html").write_text(page_shell(config, config["site"]["name"], config["site"]["description"], "/", body), encoding="utf-8")


def category_links(config: dict[str, Any], categories: list[str], base: str) -> str:
    links = []
    for category in categories:
        route = f"{base}{slugify(category, category)}/"
        links.append(f'<a class="tag-link" href="{public_path(config, route)}">{html.escape(category)}</a>')
    return '<div class="tag-cloud">' + "".join(links) + "</div>"


def render_listing(config: dict[str, Any], articles: list[dict[str, Any]], path: Path, title: str, description: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = f"""
    <section class="page-heading">
      <h1>{html.escape(title)}</h1>
      <p>{html.escape(description)}</p>
    </section>
    <form class="list-tools" role="search">
      <label for="searchInput">この一覧内を検索</label>
      <input id="searchInput" type="search" placeholder="キーワード、カテゴリ、PMID">
      <label for="sortSelect">並び替え</label>
      <select id="sortSelect">
        <option value="new">新しい順</option>
        <option value="old">古い順</option>
      </select>
    </form>
    <section class="article-list" id="searchResults" data-search-mode="local">
      {"".join(article_card(config, a) for a in articles) or '<p class="empty">該当する記事はまだありません。</p>'}
    </section>
"""
    route = "/" + str(path.relative_to(PUBLIC_DIR)).replace("\\", "/").replace("index.html", "")
    path.write_text(page_shell(config, title, description, route, body), encoding="utf-8")


def render_category_pages(config: dict[str, Any], articles: list[dict[str, Any]]) -> None:
    for page_name, categories, base in [
        ("カテゴリ", config["categories"], "categories"),
        ("疾患別", config["disease_categories"], "diseases"),
    ]:
        index_body = f"""
        <section class="page-heading">
          <h1>{page_name}</h1>
          <p>関心のある領域から論文を探せます。</p>
        </section>
        {category_links(config, categories, f"/{base}/")}
"""
        index_path = PUBLIC_DIR / base / "index.html"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(page_shell(config, page_name, f"{page_name}から論文を探す", f"/{base}/", index_body), encoding="utf-8")
        for category in categories:
            matched = [a for a in articles if category in a["metadata"].get("categories", [])]
            render_listing(
                config,
                matched,
                PUBLIC_DIR / base / slugify(category, category) / "index.html",
                category,
                f"{category}に関連する論文です。新しい順で表示しています。検索欄で、このカテゴリ内をさらに絞り込めます。",
            )


def render_archive_pages(config: dict[str, Any], articles: list[dict[str, Any]]) -> None:
    archive: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        date = article["metadata"].get("published_date", "")
        key = date[:7] if len(date) >= 7 else "unknown"
        archive.setdefault(key, []).append(article)
    links = []
    for key in sorted(archive.keys(), reverse=True):
        if key == "unknown":
            route = "/archive/unknown/"
        else:
            year, month = key.split("-")
            route = f"/archive/{year}/{month}/"
        links.append(f'<a class="archive-link" href="{route}">{html.escape(key)} <span>{len(archive[key])}本</span></a>')
        path = PUBLIC_DIR / route.strip("/") / "index.html"
        render_listing(config, archive[key], path, key, f"{key}に公開された記事です。")
    body = f"""
    <section class="page-heading">
      <h1>年月別</h1>
      <p>公開月ごとに記事を確認できます。</p>
    </section>
    <div class="archive-list">{"".join(links) or '<p class="empty">記事はまだありません。</p>'}</div>
"""
    path = PUBLIC_DIR / "archive" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page_shell(config, "年月別", "公開月ごとに論文記事を探す", "/archive/", body), encoding="utf-8")


def render_article_pages(config: dict[str, Any], articles: list[dict[str, Any]]) -> None:
    for article in articles:
        m = article["metadata"]
        route = m["url_path"]
        path = PUBLIC_DIR / route.strip("/") / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        tags = "".join(
            f'<a class="tag" href="{public_path(config, f"/categories/{slugify(c, c)}/")}">{html.escape(c)}</a>'
            for c in m.get("categories", [])
        )
        limitations = "".join(f"<li>{html.escape(item)}</li>" for item in m.get("limitations", [])) or "<li>抄録から判断できる明確な限界は記載されていません。</li>"
        source_link = m.get("source_url") or m.get("pubmed_url") or "#"
        impact_factor = lookup_journal_impact_factor(config, m.get("journal", ""))
        impact_factor_row = ""
        if impact_factor:
            impact_factor_row = f"\n          <dt>Impact Factor</dt><dd>{html.escape(impact_factor)}</dd>"
        participants = clean_missing_info_text(str(m.get("participants", "")))
        participants_section = ""
        if participants:
            participants_section = f'\n      <section><h2>対象</h2><p>{html.escape(participants)}</p></section>'
        json_ld = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": m.get("title"),
            "datePublished": m.get("published_date"),
            "dateModified": m.get("updated_at"),
            "author": {"@type": "Organization", "name": config["site"]["name"]},
            "isBasedOn": source_link,
            "description": m.get("summary"),
            "mainEntityOfPage": absolute_url(config, route),
        }
        json_ld_text = json.dumps(json_ld, ensure_ascii=False).replace("</", "<\\/")
        body = f"""
    <article class="article-page">
      <div class="ad-slot" data-slot="article-top">広告枠</div>
      <p class="meta-line">{html.escape(m.get("published_date", ""))}</p>
      <h1>{html.escape(m.get("title", ""))}</h1>
      <p class="original-title">{html.escape(m.get("original_title", ""))}</p>
      <p class="lead">{html.escape(m.get("summary", ""))}</p>
      <div class="tags">{tags}</div>

      <section class="source-box">
        <h2>原著論文</h2>
        <dl>
          <dt>Original title</dt><dd>{html.escape(m.get("original_title", ""))}</dd>
          <dt>著者</dt><dd>{html.escape(", ".join(m.get("authors", [])) or "抄録には記載されていません")}</dd>
          <dt>雑誌名</dt><dd>{html.escape(m.get("journal", "") or "抄録には記載されていません")}</dd>{impact_factor_row}
          <dt>DOI</dt><dd>{html.escape(m.get("doi", "") or "抄録には記載されていません")}</dd>
          <dt>PMID</dt><dd>{html.escape(m.get("pmid", "") or "抄録には記載されていません")}</dd>
        </dl>
        <a class="button" href="{html.escape(source_link)}" rel="noopener noreferrer">原著論文を確認する</a>
      </section>

      <section><h2>背景・目的</h2><p>{html.escape(m.get("background", ""))}</p></section>
      {participants_section}
      <section><h2>方法</h2><p>{html.escape(m.get("methods", ""))}</p></section>
      <div class="ad-slot" data-slot="article-middle">広告枠</div>
      <section><h2>結果</h2><p>{html.escape(m.get("results", ""))}</p></section>
      <section><h2>臨床的示唆</h2><p>{html.escape(m.get("clinical_meaning", ""))}</p></section>
      <section><h2>限界</h2><ul>{limitations}</ul></section>
      <div class="ad-slot" data-slot="article-bottom">広告枠</div>
      <p class="disclaimer">{html.escape(m.get("disclaimer", DISCLAIMER))}</p>
      <script type="application/ld+json">{json_ld_text}</script>
    </article>
"""
        description = m.get("summary", config["site"]["description"])
        path.write_text(page_shell(config, m.get("title", config["site"]["name"]), description, route, body), encoding="utf-8")


def render_search_json(config: dict[str, Any], articles: list[dict[str, Any]]) -> None:
    data = []
    for article in articles:
        m = article["metadata"]
        data.append(
            {
                "title": m.get("title", ""),
                "summary": m.get("summary", ""),
                "url": public_path(config, m.get("url_path", "")),
                "categories": m.get("categories", []),
                "pmid": m.get("pmid", ""),
                "doi": m.get("doi", ""),
                "published_date": m.get("published_date", ""),
            }
        )
    write_json(PUBLIC_DIR / "search.json", data)


def render_rss(config: dict[str, Any], articles: list[dict[str, Any]]) -> None:
    items = []
    for article in articles[: int(config["site"].get("rss_items", 20))]:
        m = article["metadata"]
        url = absolute_url(config, m.get("url_path", "/"))
        items.append(
            f"""
    <item>
      <title>{html.escape(m.get("title", ""))}</title>
      <link>{html.escape(url)}</link>
      <guid>{html.escape(url)}</guid>
      <pubDate>{rss_date(m.get("published_date", ""))}</pubDate>
      <description>{html.escape(m.get("summary", ""))}</description>
    </item>"""
        )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{html.escape(config["site"]["name"])}</title>
    <link>{html.escape(site_url(config) or "/")}</link>
    <description>{html.escape(config["site"]["description"])}</description>
    {"".join(items)}
  </channel>
</rss>
"""
    (PUBLIC_DIR / "feed.xml").write_text(xml, encoding="utf-8")


def rss_date(value: str) -> str:
    try:
        date = dt.datetime.fromisoformat(value[:10])
    except ValueError:
        date = dt.datetime.now(dt.timezone.utc)
    return date.strftime("%a, %d %b %Y 00:00:00 +0000")


def render_sitemap(config: dict[str, Any], articles: list[dict[str, Any]]) -> None:
    urls = ["/", "/articles/", "/categories/", "/diseases/", "/archive/"]
    urls.extend(article["metadata"].get("url_path", "") for article in articles)
    entries = []
    for route in sorted(set(filter(None, urls))):
        entries.append(
            f"""
  <url>
    <loc>{html.escape(absolute_url(config, route))}</loc>
    <lastmod>{dt.date.today().isoformat()}</lastmod>
  </url>"""
        )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{"".join(entries)}
</urlset>
"""
    (PUBLIC_DIR / "sitemap.xml").write_text(xml, encoding="utf-8")


def render_robots(config: dict[str, Any]) -> None:
    sitemap = absolute_url(config, "/sitemap.xml")
    (PUBLIC_DIR / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {sitemap}\n", encoding="utf-8")


def write_static_assets(config: dict[str, Any]) -> None:
    styles = """
:root {
  color-scheme: light;
  --bg: #f7f9f8;
  --panel: #ffffff;
  --ink: #20302e;
  --muted: #62716f;
  --line: #d8e1de;
  --accent: #176b63;
  --accent-2: #9a5b2f;
  --soft: #e8f1ef;
  --warn: #f3eee4;
  font-family: "Hiragino Sans", "Yu Gothic", "Yu Gothic UI", Meiryo, system-ui, sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); line-height: 1.75; }
a { color: var(--accent); text-decoration-thickness: .08em; text-underline-offset: .22em; }
.site-header { display: flex; gap: 24px; align-items: center; justify-content: space-between; padding: 18px clamp(18px, 4vw, 56px); border-bottom: 1px solid var(--line); background: rgba(255,255,255,.92); position: sticky; top: 0; z-index: 10; }
.brand { color: var(--ink); font-weight: 700; text-decoration: none; font-size: 1.05rem; }
.nav { display: flex; gap: 16px; flex-wrap: wrap; }
.nav a { color: var(--muted); text-decoration: none; font-size: .95rem; }
main { width: min(1120px, calc(100% - 32px)); margin: 0 auto; }
.hero { display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 360px); gap: 32px; align-items: end; padding: 48px 0 32px; border-bottom: 1px solid var(--line); }
.eyebrow, .meta-line { color: var(--accent-2); font-size: .9rem; font-weight: 700; }
h1 { font-size: clamp(2rem, 5vw, 4rem); line-height: 1.15; margin: 8px 0 16px; letter-spacing: 0; }
h2 { font-size: 1.25rem; line-height: 1.35; margin: 0 0 10px; letter-spacing: 0; }
.hero p { max-width: 680px; color: var(--muted); font-size: 1.05rem; }
.search-box { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 18px; min-width: 0; }
.search-box label { display: block; font-weight: 700; margin-bottom: 8px; }
.list-tools { display: grid; grid-template-columns: minmax(220px, 1fr) 180px; gap: 10px 14px; align-items: end; margin: 0 0 20px; }
.search-box.list-tools { grid-template-columns: max-content minmax(0, 1fr); align-items: center; gap: 14px 18px; }
.search-box.list-tools label { margin: 0; }
.list-tools label { font-weight: 700; }
.list-tools input, .list-tools select { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; font: inherit; background: #fff; color: var(--ink); }
input[type="search"] { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; font: inherit; background: #fff; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 28px; padding: 30px 0 56px; }
.article-list { display: grid; gap: 16px; }
.article-card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 22px; }
.article-card h2 a { color: var(--ink); }
.article-card p { color: var(--muted); margin: 0 0 14px; }
.original-title { color: var(--muted); font-size: .95rem; font-style: italic; line-height: 1.55; }
.tags, .tag-cloud { display: flex; flex-wrap: wrap; gap: 8px; }
.tag, .tag-link { display: inline-flex; align-items: center; min-height: 30px; padding: 4px 10px; border-radius: 999px; background: var(--soft); color: var(--accent); text-decoration: none; font-size: .9rem; }
.side-panel { display: grid; align-content: start; gap: 18px; }
.side-panel h2 { margin-top: 10px; }
.page-heading { padding: 44px 0 20px; border-bottom: 1px solid var(--line); margin-bottom: 24px; }
.page-heading p { color: var(--muted); }
.article-page { width: min(820px, 100%); margin: 0 auto; padding: 44px 0 64px; }
.article-page h1 { font-size: clamp(1.9rem, 4vw, 3rem); }
.lead { font-size: 1.15rem; color: var(--muted); }
.article-page section, .source-box { margin: 28px 0; }
.source-box { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 22px; }
dl { display: grid; grid-template-columns: 130px minmax(0, 1fr); gap: 8px 16px; margin: 0; }
dt { color: var(--muted); font-weight: 700; }
dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
.button { display: inline-flex; margin-top: 18px; padding: 10px 14px; border-radius: 6px; background: var(--accent); color: #fff; text-decoration: none; font-weight: 700; }
.disclaimer { background: var(--warn); border-left: 4px solid var(--accent-2); padding: 14px 16px; color: #4a4037; }
.ad-slot { border: 1px dashed #b7c5c1; color: #7a8885; min-height: 72px; display: grid; place-items: center; border-radius: 8px; background: rgba(255,255,255,.5); font-size: .9rem; }
.archive-list { display: grid; gap: 10px; padding-bottom: 56px; }
.archive-link { display: flex; justify-content: space-between; border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 14px 16px; text-decoration: none; }
.empty { color: var(--muted); background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 22px; }
.site-footer { border-top: 1px solid var(--line); padding: 24px clamp(18px, 4vw, 56px); color: var(--muted); font-size: .9rem; }
@media (max-width: 820px) {
  .site-header, .hero, .content-grid { display: block; }
  .nav { margin-top: 12px; }
  .search-box { margin-top: 22px; }
  .list-tools, .search-box.list-tools { grid-template-columns: 1fr; }
  .search-box.list-tools label { margin-bottom: 4px; }
  .side-panel { margin-top: 28px; }
  dl { grid-template-columns: 1fr; }
}
"""
    script = """
function bootSearch() {
  const form = document.querySelector('.list-tools');
  const input = document.querySelector('#searchInput');
  const results = document.querySelector('#searchResults');
  const sort = document.querySelector('#sortSelect');
  if (!input || !results) return;
  const emptyHtml = '<p class="empty">該当する記事はありません。</p>';
  const originalCards = Array.from(results.querySelectorAll('.article-card')).map((card) => card.cloneNode(true));

  function applyFilters() {
    const q = input.value.trim().toLowerCase();
    const order = sort?.value || 'new';
    const cards = originalCards
      .filter((card) => !q || String(card.dataset.search || '').includes(q))
      .sort((a, b) => compareCards(a, b, order));

    results.replaceChildren();
    if (!cards.length) {
      results.innerHTML = emptyHtml;
      return;
    }
    cards.forEach((card) => results.appendChild(card.cloneNode(true)));
  }

  form?.addEventListener('submit', (event) => {
    event.preventDefault();
    applyFilters();
  });
  input.addEventListener('input', applyFilters);
  sort?.addEventListener('change', applyFilters);
  applyFilters();
}

function compareCards(a, b, order) {
  if (order === 'old') {
    return String(a.dataset.date || '').localeCompare(String(b.dataset.date || ''));
  }
  return String(b.dataset.date || '').localeCompare(String(a.dataset.date || ''));
}
bootSearch();
"""
    favicon = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#176b63"/>
  <path d="M17 33h10l4-13 7 27 5-14h5" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="44" cy="19" r="6" fill="#f3eee4"/>
</svg>
""".strip()
    (PUBLIC_DIR / "assets" / "styles.css").write_text(styles.strip() + "\n", encoding="utf-8")
    (PUBLIC_DIR / "assets" / "search.js").write_text(script.strip() + "\n", encoding="utf-8")
    (PUBLIC_DIR / "assets" / "favicon.svg").write_text(favicon + "\n", encoding="utf-8")


def update_processed(processed: dict[str, Any], articles: list[dict[str, Any]]) -> dict[str, Any]:
    ids = set(processed.get("ids", []))
    records = processed.get("records", [])
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    for metadata in articles:
        identifier = metadata.get("pmid") or str(metadata.get("doi", "")).lower()
        if not identifier or identifier in ids:
            continue
        ids.add(identifier)
        records.append(
            {
                "id": identifier,
                "pmid": metadata.get("pmid", ""),
                "doi": metadata.get("doi", ""),
                "title": metadata.get("original_title", metadata.get("title", "")),
                "url_path": metadata.get("url_path", ""),
                "processed_at": now,
            }
        )
    return {"ids": sorted(ids), "records": records}


def run(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_dirs()
    if args.build_only:
        render_site(config)
        log("build-only completed")
        return 0

    processed = read_json(PROCESSED_PATH, {"ids": [], "records": []})
    client = PubMedClient(config)
    pmids = client.search_recent()
    log(f"fetched_pmids={len(pmids)}")
    papers = client.fetch_details(pmids)
    candidates, excluded = filter_papers(papers, config, processed)
    log(f"fetched_details={len(papers)} candidates={len(candidates)} excluded={excluded}")

    categories = config["categories"]
    max_eval = min(int(config["claude"].get("max_evaluation_candidates", 12)), len(candidates))
    evaluated: list[tuple[Paper, dict[str, Any]]] = []
    api_errors = 0
    claude: ClaudeClient | None = None

    if args.no_claude:
        evaluated = [(paper, heuristic_evaluation(paper, categories)) for paper in candidates[:max_eval]]
        log("Claude disabled: heuristic candidate scoring only")
    else:
        claude = ClaudeClient(config, dry_run=args.dry_run)
        for paper in candidates[:max_eval]:
            try:
                evaluation = evaluate_with_claude(claude, paper, categories)
                evaluated.append((paper, evaluation))
            except Exception as exc:
                api_errors += 1
                log(f"skip_evaluation pmid={paper.pmid} error={type(exc).__name__}")

    evaluated.sort(key=lambda item: item[1].get("total_score", 0), reverse=True)
    threshold = float(config["claude"].get("publish_score_threshold", 12))
    selected = [
        item for item in evaluated if float(item[1].get("total_score", 0)) >= threshold
    ][: int(config["site"].get("max_articles_per_day", 8))]
    log(f"claude_evaluations={len(evaluated)} selected={len(selected)} api_errors={api_errors}")

    if args.dry_run or args.no_claude:
        for paper, evaluation in selected:
            log(f"candidate score={evaluation['total_score']:.1f} pmid={paper.pmid} title={paper.title[:120]}")
        log("dry-run completed; no article files, processed state, commit, or deployment were written")
        return 0

    if claude is None:
        claude = ClaudeClient(config)
    generated_metadata = []
    now = dt.datetime.now(dt.timezone.utc)
    for paper, evaluation in selected:
        try:
            article = generate_article_with_claude(claude, paper, evaluation, categories)
            path, metadata = write_article(paper, article, now)
            generated_metadata.append(metadata)
            log(f"article_generated pmid={paper.pmid} path={path.relative_to(PROJECT_ROOT)}")
        except Exception as exc:
            api_errors += 1
            log(f"skip_article pmid={paper.pmid} error={type(exc).__name__}")

    processed = update_processed(processed, generated_metadata)
    write_json(PROCESSED_PATH, processed)
    render_site(config)
    log(
        f"completed generated={len(generated_metadata)} total_processed={len(processed.get('ids', []))} api_errors={api_errors}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch PubMed papers and rebuild the static site.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and score candidates without writing new articles or state.")
    parser.add_argument("--no-claude", action="store_true", help="Use heuristic scoring for test runs without ANTHROPIC_API_KEY.")
    parser.add_argument("--build-only", action="store_true", help="Only rebuild the static site from existing content.")
    args = parser.parse_args()
    try:
        return run(args)
    except Exception as exc:
        log(f"fatal error: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
