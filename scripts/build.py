#!/usr/bin/env python3
"""Build all locale HTML pages, sitemap, and i18n runtime config from templates."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
PARTIALS = TEMPLATES / "partials"
I18N_DIR = ROOT / "assets" / "i18n"
SITE_URL = "https://www.parfastenersindia.com"

PAGE_META = {
    "index.html": ("meta.title", "meta.description"),
    "productsRange.html": ("meta.title.products", "meta.description.products"),
    "ourCustomers.html": ("meta.title.customers", "meta.description.customers"),
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def flatten_strings(data: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten_strings(value, full))
        else:
            out[str(full)] = str(value)
    return out


def get_nested(data: dict[str, str], key: str) -> str:
    return data.get(key, f"{{{{MISSING:{key}}}}}")


def render_template(template: str, ctx: dict[str, str], partials: dict[str, str]) -> str:
    partial_re = re.compile(r"\{\{>(\w+)\}\}")

    def replace_partial(match: re.Match[str]) -> str:
        name = match.group(1)
        if name == "content":
            return template
        return partials.get(name, "")

    # First inject partials into template body
    body = template
    for _ in range(10):
        updated = partial_re.sub(lambda m: partials.get(m.group(1), ""), body)
        if updated == body:
            break
        body = updated

    def replace_var(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return get_nested(ctx, key)

    return re.sub(r"\{\{([^#/][^}]*)\}\}", replace_var, body)


def locale_base_path(locale_cfg: dict) -> str:
    path = locale_cfg.get("path", "")
    return f"/{path}" if path else ""


def page_url(site: str, locale_cfg: dict, page: str) -> str:
    base = locale_base_path(locale_cfg)
    if page == "index.html":
        return f"{site}{base}/" if base else f"{site}/"
    return f"{site}{base}/{page}"


def build_hreflang_tags(site: str, locales: dict, page: str) -> str:
    lines = []
    for loc_id, loc in locales.items():
        href = page_url(site, loc, page)
        lines.append(f'  <link rel="alternate" hreflang="{loc["hreflang"]}" href="{href}" />')
    default_href = page_url(site, locales["en"], page)
    lines.append(f'  <link rel="alternate" hreflang="x-default" href="{default_href}" />')
    return "\n".join(lines)


def build_og_alternates(current_id: str, locales: dict) -> str:
    lines = []
    for loc_id, loc in locales.items():
        if loc_id == current_id:
            continue
        lines.append(f'  <meta property="og:locale:alternate" content="{loc["ogLocale"]}" />')
    return "\n".join(lines)


def build_nav_context(locale_id: str, locale_cfg: dict, page: str, strings: dict[str, str]) -> dict[str, str]:
    base = locale_base_path(locale_cfg)
    home = f"{base}/" if base else "/"

    def nav_href(target_page: str, anchor: str = "") -> str:
        if target_page == "index.html" and anchor:
            return f"{home}#{anchor}" if home != "/" else f"/#{anchor}"
        if target_page == "index.html":
            return home
        return f"{base}/{target_page}" if base else f"/{target_page}"

    active = {
        "index.html": {
            "_navHomeActive": "active",
            "_navAboutActive": "",
            "_navServicesActive": "",
            "_navQualityActive": "",
            "_navProductsActive": "",
            "_navProductRangeActive": "",
            "_navCustomersActive": "",
            "_navContactActive": "",
        },
        "productsRange.html": {
            "_navHomeActive": "",
            "_navAboutActive": "",
            "_navServicesActive": "",
            "_navQualityActive": "",
            "_navProductsActive": "",
            "_navProductRangeActive": "active",
            "_navCustomersActive": "",
            "_navContactActive": "",
        },
        "ourCustomers.html": {
            "_navHomeActive": "",
            "_navAboutActive": "",
            "_navServicesActive": "",
            "_navQualityActive": "",
            "_navProductsActive": "",
            "_navCustomersActive": "active",
            "_navProductRangeActive": "",
            "_navContactActive": "",
        },
    }

    ctx = {
        "_localeId": locale_id,
        "_homeUrl": home,
        "_navAbout": nav_href("index.html", "about"),
        "_navServices": nav_href("index.html", "services"),
        "_navQuality": nav_href("index.html", "quality"),
        "_navProducts": nav_href("index.html", "portfolio"),
        "_navProductRange": nav_href("productsRange.html"),
        "_navCustomers": nav_href("ourCustomers.html"),
        "_navContact": nav_href("index.html", "contact"),
    }
    ctx.update(active.get(page, active["index.html"]))
    return ctx


def build_page_context(
    locale_id: str,
    locale_cfg: dict,
    page: str,
    strings: dict[str, str],
    locales: dict,
    site: str,
) -> dict[str, str]:
    title_key, desc_key = PAGE_META[page]
    ctx = dict(strings)
    ctx.update(build_nav_context(locale_id, locale_cfg, page, strings))
    ctx["_htmlLang"] = locale_cfg.get("hreflang", locale_id).replace("-Hans", "-CN") if locale_id == "zh-cn" else (
        "pt-BR" if locale_id == "pt-br" else locale_id
    )
    if locale_id == "zh-cn":
        ctx["_htmlLang"] = "zh-Hans"
    ctx["_dir"] = locale_cfg.get("dir", "ltr")
    ctx["_htmlClass"] = f' class="locale-{locale_id}"' if locale_cfg.get("dir") == "rtl" else ""
    ctx["_pageTitle"] = get_nested(strings, title_key)
    ctx["_pageDescription"] = get_nested(strings, desc_key)
    ctx["_canonical"] = page_url(site, locale_cfg, page)
    ctx["_hreflangTags"] = build_hreflang_tags(site, locales, page)
    ctx["_ogLocale"] = locale_cfg.get("ogLocale", "en_US")
    ctx["_ogLocaleAlternates"] = build_og_alternates(locale_id, locales)
    return ctx


def write_sitemap(site: str, locales: dict, pages: list[str], out_path: Path) -> None:
  lines = [
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
      '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
  ]
  priority_map = {"index.html": "1.0", "productsRange.html": "0.8", "ourCustomers.html": "0.8"}

  for page in pages:
      for loc_id, loc in locales.items():
          loc_url = page_url(site, loc, page)
          lines.append("  <url>")
          lines.append(f"    <loc>{loc_url}</loc>")
          for alt_id, alt in locales.items():
              alt_url = page_url(site, alt, page)
              lines.append(
                  f'    <xhtml:link rel="alternate" hreflang="{alt["hreflang"]}" href="{alt_url}"/>'
              )
          default_url = page_url(site, locales["en"], page)
          lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{default_url}"/>')
          lines.append("    <changefreq>monthly</changefreq>")
          lines.append(f"    <priority>{priority_map.get(page, '0.8')}</priority>")
          lines.append("  </url>")

  lines.append("</urlset>")
  out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_i18n_config(locales_data: dict, out_path: Path) -> None:
    payload = {
        "default": locales_data["default"],
        "siteUrl": locales_data["siteUrl"],
        "storageKey": locales_data["storageKey"],
        "pages": locales_data["pages"],
        "locales": {
            loc_id: {
                "id": loc_id,
                "name": loc["name"],
                "native": loc["native"],
                "hreflang": loc["hreflang"],
                "dir": loc["dir"],
                "path": loc["path"],
            }
            for loc_id, loc in locales_data["locales"].items()
        },
    }
    js = "window.PAR_I18N = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    out_path.write_text(js, encoding="utf-8")


def normalize_asset_paths(html: str) -> str:
    """Ensure asset URLs work from locale subdirectories (/de/, /ar/, etc.)."""
    html = html.replace('href="assets/', 'href="/assets/')
    html = html.replace("href='assets/", "href='/assets/")
    html = html.replace('src="assets/', 'src="/assets/')
    html = html.replace("src='assets/", "src='/assets/")
    return html


def main() -> int:
    locales_data = load_json(ROOT / "locales.json")
    locales = locales_data["locales"]
    pages = locales_data["pages"]
    site = locales_data.get("siteUrl", SITE_URL)

    partials = {
        name: (PARTIALS / f"{name}.html").read_text(encoding="utf-8")
        for name in ["topbar", "header", "footer", "scripts"]
    }
    layout = (TEMPLATES / "layout.html").read_text(encoding="utf-8")

    for locale_id, locale_cfg in locales.items():
        i18n_path = I18N_DIR / f"{locale_id}.json"
        if not i18n_path.exists():
            print(f"WARN: missing {i18n_path}, skipping locale {locale_id}", file=sys.stderr)
            continue
        strings = load_json(i18n_path)

        out_dir = ROOT / locale_cfg["path"] if locale_cfg.get("path") else ROOT
        out_dir.mkdir(parents=True, exist_ok=True)

        for page in pages:
            page_tpl = (TEMPLATES / page).read_text(encoding="utf-8")
            ctx = build_page_context(locale_id, locale_cfg, page, strings, locales, site)

            body = render_template(page_tpl, ctx, partials)
            partials_with_content = dict(partials)
            partials_with_content["content"] = body
            html = render_template(layout, ctx, partials_with_content)
            html = render_template(html, ctx, partials_with_content)
            html = normalize_asset_paths(html)

            (out_dir / page).write_text(html, encoding="utf-8")
            print(f"Built {locale_id}/{page} -> {out_dir / page}")

    write_sitemap(site, locales, pages, ROOT / "sitemap.xml")
    write_i18n_config(locales_data, ROOT / "assets" / "js" / "par-i18n-config.js")
    print("Wrote sitemap.xml and assets/js/par-i18n-config.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
