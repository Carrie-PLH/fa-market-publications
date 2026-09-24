"""Search apparatus for the built site: social meta tags, JSON-LD, the sitemap
with last-modified dates, an Atom feed of published editions, and the Cloudflare
Pages _headers file. Pure functions over strings; nothing here reads the record.

Copied between Provision Record and Materials Monitor rather than shared, so
that neither publication can break the other.
"""

import html
import json
from datetime import date, datetime, timezone


def esc(s):
    return html.escape(str(s), quote=True)


# ---------- head tags ----------

def social_meta(*, title, description, url, site_name, kind="website",
                published=None, modified=None, feed_path=None):
    """Open Graph and Twitter card tags. kind is 'website' or 'article'.
    No image is declared until the site has one; a missing og:image is better
    than a wrong one."""
    tags = [
        f'<meta property="og:site_name" content="{esc(site_name)}">',
        f'<meta property="og:type" content="{esc(kind)}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:url" content="{esc(url)}">',
        '<meta property="og:locale" content="en_US">',
        '<meta name="twitter:card" content="summary">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(description)}">',
    ]
    if kind == "article":
        if published:
            tags.append(f'<meta property="article:published_time" content="{esc(published)}">')
        if modified:
            tags.append(f'<meta property="article:modified_time" content="{esc(modified)}">')
    if feed_path:
        tags.append(f'<link rel="alternate" type="application/atom+xml" title="{esc(site_name)} editions" href="{esc(feed_path)}">')
    return "\n".join(tags)


def jsonld(nodes):
    """One JSON-LD block carrying an @graph. '<' is escaped so the JSON can
    never close the script element."""
    doc = {"@context": "https://schema.org", "@graph": [n for n in nodes if n]}
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return f'<script type="application/ld+json">{text}</script>'


# ---------- schema.org nodes ----------

FIELD_ASSEMBLY = "https://fieldassembly.net"
CC_BY_4 = "https://creativecommons.org/licenses/by/4.0/"


def org_node():
    return {"@type": "Organization", "@id": FIELD_ASSEMBLY + "/#organization",
            "name": "Field Assembly LLC", "alternateName": "Field Assembly", "url": FIELD_ASSEMBLY,
            "address": {"@type": "PostalAddress", "addressRegion": "MA", "addressCountry": "US"}}


def website_node(base, name, description):
    return {"@type": "WebSite", "@id": base + "/#website", "url": base + "/", "name": name,
            "description": description, "inLanguage": "en",
            "publisher": {"@id": FIELD_ASSEMBLY + "/#organization"}}


def webpage_node(base, path, title, description, *, kind="WebPage", published=None, modified=None):
    n = {"@type": kind, "@id": base + path, "url": base + path, "name": title, "description": description,
         "inLanguage": "en", "isPartOf": {"@id": base + "/#website"}}
    if published:
        n["datePublished"] = published
    if modified:
        n["dateModified"] = modified
    return n


def breadcrumb_node(base, items):
    """items: [(name, path)] from the home page down to the current page."""
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": name, "item": base + path}
        for i, (name, path) in enumerate(items)]}


def report_node(*, base, path, headline, description, published, modified=None, version=None,
                periodical=None, citation=None, dataset_id=None, keywords=None):
    """The edition text as a schema.org Report (a subtype of Article)."""
    n = {"@type": "Report", "@id": base + path + "#report", "url": base + path,
         "mainEntityOfPage": base + path, "headline": headline, "description": description,
         "inLanguage": "en", "datePublished": published, "dateModified": modified or published,
         "author": {"@id": FIELD_ASSEMBLY + "/#organization"},
         "publisher": {"@id": FIELD_ASSEMBLY + "/#organization"},
         "license": CC_BY_4, "isAccessibleForFree": True}
    if version:
        n["version"] = str(version)
    if periodical:
        n["isPartOf"] = periodical
    if citation:
        n["citation"] = citation
    if dataset_id:
        n["hasPart"] = {"@id": dataset_id}
    if keywords:
        n["keywords"] = keywords
    return n


def dataset_node(*, base, path, name, description, published, modified=None, version=None,
                 downloads=(), sources=(), temporal=None, keywords=None, variables=None, catalog=None):
    """The edition's downloadable tables as a schema.org Dataset, the shape
    Google Dataset Search reads. downloads: [(url, encoding_format, name)];
    sources: [(name, url)] for isBasedOn; catalog: (name, url) of the publication
    the dataset belongs to, defaulting to the site."""
    n = {"@type": "Dataset", "@id": base + path + "#dataset", "url": base + path, "name": name,
         "description": description, "inLanguage": "en", "datePublished": published,
         "dateModified": modified or published, "license": CC_BY_4, "isAccessibleForFree": True,
         "creator": {"@id": FIELD_ASSEMBLY + "/#organization"},
         "publisher": {"@id": FIELD_ASSEMBLY + "/#organization"},
         "includedInDataCatalog": {"@type": "DataCatalog", "name": catalog[0] if catalog else name.split(",")[0],
                                   "url": catalog[1] if catalog else base + "/"}}
    if version:
        n["version"] = str(version)
    if downloads:
        n["distribution"] = [{"@type": "DataDownload", "contentUrl": u, "encodingFormat": f, "name": nm}
                             for (u, f, nm) in downloads]
    if sources:
        n["isBasedOn"] = [{"@type": "CreativeWork", "name": nm, "url": u} for (nm, u) in sources if u]
    if temporal:
        n["temporalCoverage"] = temporal
    if keywords:
        n["keywords"] = keywords
    if variables:
        n["variableMeasured"] = [{"@type": "PropertyValue", "name": v} for v in variables]
    n["spatialCoverage"] = {"@type": "Place", "name": "United States"}
    return n


# ---------- files ----------

def sitemap_xml(entries):
    """entries: [(loc, lastmod or None)]. Only dates the record states are used."""
    parts = []
    for loc, lastmod in entries:
        lm = f"<lastmod>{esc(lastmod)}</lastmod>" if lastmod else ""
        parts.append(f"<url><loc>{esc(loc)}</loc>{lm}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(parts) + "\n</urlset>\n")


def _rfc3339(d):
    if not d:
        return None
    if len(d) == 10:
        return d + "T00:00:00Z"
    return d


def atom_feed(*, base, site_name, subtitle, feed_path, entries):
    """entries: [{'title','path','published','modified','summary'}], newest first."""
    updated = max((_rfc3339(e.get("modified") or e.get("published")) for e in entries), default=None) \
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = []
    for e in entries:
        pub = _rfc3339(e["published"])
        upd = _rfc3339(e.get("modified")) or pub
        items.append(
            f"<entry><title>{esc(e['title'])}</title><link rel=\"alternate\" href=\"{esc(base + e['path'])}\"/>"
            f"<id>{esc(base + e['path'])}</id><published>{pub}</published><updated>{upd}</updated>"
            f"<summary>{esc(e.get('summary', ''))}</summary></entry>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom">\n'
            f"<title>{esc(site_name)}</title><subtitle>{esc(subtitle)}</subtitle>"
            f"<link href=\"{esc(base)}/\"/><link rel=\"self\" href=\"{esc(base + feed_path)}\"/>"
            f"<id>{esc(base)}/</id><updated>{updated}</updated>"
            f"<author><name>Field Assembly</name><uri>{FIELD_ASSEMBLY}</uri></author>\n"
            + "\n".join(items) + "\n</feed>\n")


def headers_file(rules):
    """Cloudflare Pages _headers. rules: [(path_pattern, [(header, value)])]."""
    out = []
    for pattern, hs in rules:
        out.append(pattern)
        out.extend(f"  {h}: {v}" for h, v in hs)
    return "\n".join(out) + "\n"
