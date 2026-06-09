import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger("cliniq.ingestion.pubmed")

MESH_TERMS = [
    "clinical guidelines",
    "drug interactions",
    "evidence-based medicine",
    "diagnostic criteria",
]
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _text(element: ElementTree.Element | None, default: str = "") -> str:
    return "".join(element.itertext()).strip() if element is not None else default


def _parse_article(article: ElementTree.Element) -> dict:
    medline = article.find(".//MedlineCitation")
    article_node = article.find(".//Article")
    pmid = _text(medline.find("PMID") if medline is not None else None)
    title = _text(article_node.find("ArticleTitle") if article_node is not None else None)
    abstract_parts = [
        _text(node)
        for node in article.findall(".//Abstract/AbstractText")
        if _text(node)
    ]
    authors = []
    for author in article.findall(".//Author"):
        last = _text(author.find("LastName"))
        first = _text(author.find("ForeName"))
        collective = _text(author.find("CollectiveName"))
        name = collective or " ".join(part for part in [first, last] if part)
        if name:
            authors.append(name)
    mesh_terms = [_text(node.find("DescriptorName")) for node in article.findall(".//MeshHeading")]
    pub_date_node = article.find(".//PubDate")
    year = _text(pub_date_node.find("Year") if pub_date_node is not None else None)
    month = _text(pub_date_node.find("Month") if pub_date_node is not None else None)
    day = _text(pub_date_node.find("Day") if pub_date_node is not None else None)
    return {
        "pmid": pmid,
        "title": title,
        "abstract": " ".join(abstract_parts),
        "authors": authors,
        "publication_date": " ".join(part for part in [year, month, day] if part),
        "mesh_terms": [term for term in mesh_terms if term],
        "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
    }


async def _search_pmids(client: httpx.AsyncClient, term: str, retmax: int) -> list[str]:
    response = await client.get(
        f"{BASE_URL}/esearch.fcgi",
        params={
            "db": "pubmed",
            "term": f"{term}[MeSH Terms] OR {term}[Title/Abstract]",
            "retmode": "json",
            "retmax": retmax,
            "sort": "relevance",
        },
    )
    response.raise_for_status()
    return response.json()["esearchresult"].get("idlist", [])


async def _fetch_details(client: httpx.AsyncClient, pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    response = await client.get(
        f"{BASE_URL}/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
        timeout=60,
    )
    response.raise_for_status()
    root = ElementTree.fromstring(response.text)
    return [
        article
        for article in (_parse_article(node) for node in root.findall(".//PubmedArticle"))
        if article["pmid"] and article["title"] and article["abstract"]
    ]


async def fetch_pubmed_corpus(target_count: int = 500, batch_size: int = 100) -> list[dict]:
    settings = get_settings()
    raw_dir = Path(settings.raw_data_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    articles_by_pmid: dict[str, dict] = {}
    per_term = max(target_count // len(MESH_TERMS) + 50, 150)
    async with httpx.AsyncClient(timeout=30) as client:
        for term in MESH_TERMS:
            pmids = await _search_pmids(client, term, per_term)
            logger.info("pubmed_pmids_found", term=term, count=len(pmids))
            for start in range(0, len(pmids), batch_size):
                batch = pmids[start : start + batch_size]
                for article in await _fetch_details(client, batch):
                    articles_by_pmid[article["pmid"]] = article
                await asyncio.sleep(0.34)
                if len(articles_by_pmid) >= target_count:
                    break
            if len(articles_by_pmid) >= target_count:
                break
    articles = list(articles_by_pmid.values())[:target_count]
    output = raw_dir / f"pubmed_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.json"
    output.write_text(json.dumps(articles, indent=2), encoding="utf-8")
    logger.info("pubmed_corpus_saved", path=str(output), count=len(articles))
    return articles
