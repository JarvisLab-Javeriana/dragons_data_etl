from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.gdelt.collectors.web.crawler import ArticleCrawler, ExtractedPage, extract_page, safe_dirname
from src.gdelt.common.config import CrawlerConfig


def _config(**overrides) -> CrawlerConfig:
    defaults = dict(
        output_dir="data/crawled",
        limit=50,
        user_agent="DragonsDataETL-test/0.1",
        request_timeout_seconds=5,
        delay_seconds=0,
        respect_robots_txt=True,
        max_html_bytes=1_000_000,
    )
    defaults.update(overrides)
    return CrawlerConfig(**defaults)


def test_safe_dirname_strips_unsafe_characters():
    assert safe_dirname("2015-02-18 12:00:00/abc", "x") == "2015-02-18_12_00_00_abc"


def test_extract_page_reads_title_and_text():
    html = """
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Native species recovery</title>
        <meta name="author" content="Jane Doe">
        <meta property="article:published_time" content="2020-01-15">
      </head>
      <body>
        <article>
          <h1>Native species recovery</h1>
          <p>Conservation teams are restoring native species across several habitats
          after a documented ecological crisis in the region. The programme focuses
          on biodiversity, endangered plants, and community stewardship of the
          natural world over multiple seasons of fieldwork.</p>
        </article>
      </body>
    </html>
    """
    extracted = extract_page(html, "https://example.com/article")
    assert extracted.title
    assert extracted.text
    assert extracted.language
    assert "native species" in extracted.text.lower() or "biodiversity" in extracted.text.lower()


def test_crawler_skips_robots_disallowed_urls(tmp_path: Path, monkeypatch):
    session = MagicMock()
    robots_response = MagicMock()
    robots_response.status_code = 200
    robots_response.text = "User-agent: *\nDisallow: /\n"
    session.get.return_value = robots_response

    crawler = ArticleCrawler(_config(), session=session, output_root=tmp_path)
    summary = crawler.crawl(
        [{"gkg_record_id": "rec-1", "document_identifier": "https://news.example/story"}]
    )

    assert summary["attempted"] == 1
    assert summary["robots_disallowed"] == 1
    assert summary["succeeded"] == 0
    assert session.get.call_count == 1


def test_crawler_writes_local_html_and_metadata(tmp_path: Path, monkeypatch):
    html = "<html><body><p>hello</p></body></html>"

    def fake_get(url, **kwargs):
        response = MagicMock()
        if url.endswith("/robots.txt"):
            response.status_code = 200
            response.text = "User-agent: *\nAllow: /\n"
            response.content = response.text.encode()
            response.url = url
            return response
        response.status_code = 200
        response.text = html
        response.content = html.encode()
        response.url = "https://example.com/final-article"
        return response

    session = MagicMock()
    session.get.side_effect = fake_get
    monkeypatch.setattr(
        "src.gdelt.collectors.web.crawler.extract_page",
        lambda _html, url: ExtractedPage(
            title="A title",
            author="An author",
            date="2020-01-15",
            language="en",
            text="Main article text about biodiversity.",
            final_url=url,
        ),
    )

    crawler = ArticleCrawler(_config(), session=session, output_root=tmp_path)
    summary = crawler.crawl(
        [{"gkg_record_id": "20150218-1", "document_identifier": "https://example.com/article"}]
    )

    assert summary["succeeded"] == 1
    page_dir = tmp_path / summary["run_id"] / "pages" / "20150218-1"
    assert (page_dir / "page.html").read_text(encoding="utf-8") == html
    assert "biodiversity" in (page_dir / "content.txt").read_text(encoding="utf-8")
    metadata = (page_dir / "metadata.json").read_text(encoding="utf-8")
    assert "A title" in metadata
    assert "https://example.com/final-article" in metadata
