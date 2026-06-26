# PAR Industries Website

Static brochure site for [parfastenersindia.com](https://www.parfastenersindia.com) — fasteners manufacturer, Ludhiana, India.

## Multilingual (10 languages)

English at `/`, other locales at `/de/`, `/es/`, `/fr/`, `/pt-br/`, `/ar/`, `/ru/`, `/it/`, `/ja/`, `/zh-cn/`.

## Edit workflow

1. Update copy in `assets/i18n/en.json` and/or `templates/`
2. Add/remove languages in `locales.json`
3. Build generated HTML:

```bash
npm run build          # rebuild all locale pages + sitemap
npm run translate      # machine-translate missing keys (optional)
npm run i18n           # translate + build
```

4. Preview locally:

```bash
python3 -m http.server 8765
# open http://localhost:8765/
```

5. Commit and push to `master` — GitHub Pages deploys automatically.

**Do not hand-edit** generated files in locale folders (`de/`, `es/`, …) or root `index.html` — edit templates and JSON, then rebuild.

## Project layout

| Path | Purpose |
|------|---------|
| `templates/` | HTML source with `{{placeholders}}` |
| `assets/i18n/*.json` | Translations |
| `locales.json` | Language registry |
| `scripts/build.py` | Generates all HTML + sitemap |
| `assets/js/lang.js` | Language selector + preference |
