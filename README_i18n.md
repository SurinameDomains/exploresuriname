# Multilingual (EN / NL / ES) — how it works

English stays the default at the site root. Dutch and Spanish are full,
statically-generated copies under `/nl/` and `/es/`, built as a pipeline stage
*after* `generate.py`. `generate.py` is **not** modified — all i18n lives in two
new scripts, so the fragile 500 KB generator is untouched.

## Files
- `build_i18n.py` — build stage. Reads the built English site, emits `/nl/` and
  `/es/` trees, finalizes per-page `hreflang` + `x-default`, `<html lang>`,
  `og:locale`, canonical/og:url, injects the EN/NL/ES switcher, writes a
  per-language `search-index.json`, and rewrites `sitemap.xml` with reciprocal
  language alternates. Translation comes only from `translations.json`; any
  missing segment falls back to English, so the site never breaks.
- `translate_cache.py` — fills `translations.json` via the keyless Google endpoint (no API key, no card). Resumable + quota-aware: re-run until complete. Protects business
  names/addresses/phones/prices and skips `<script>`/JSON-LD.
- `translations.json` — committed cache `{source: {nl, es}}`. Source of truth.
- `translation_segments.json` / `i18n_segments.json` — segment inventories.

## CI
- `.github/workflows/update.yml` — added a **Build NL/ES language trees** step
  (runs `build_i18n.py` after `cache_images.py`) and commits `nl/ es/` +
  `translations.json`.
- `.github/workflows/translate.yml` — run manually (or uncomment the daily cron)
  to fill the cache in batches. No time limit on CI, so the full corpus
  completes over a few runs. Cheap no-op once complete.

## Status: translation cache COMPLETE
`translations.json` is fully populated — 3,727 segments, every one in both NL and
ES (UI, editorial copy, all 703 listing descriptions, and per-listing titles/meta).
Business names are preserved verbatim in titles (shielded during translation by
`protect_titles.py`); the site brand reads "ExploreSuriname" in every language.

## To launch
1. Run **Update Site**. `generate.py` builds English, then `build_i18n.py` builds
   `/nl/` and `/es/` from the committed cache and they deploy with everything else.
2. Submit the updated `sitemap.xml` in Google Search Console; watch the
   International Targeting / hreflang report for reciprocity errors.

## Adding listings later
New listings' text falls back to English until translated. To fill the gap, run the
**Fill Translations (NL/ES)** workflow (now backed by the keyless Google endpoint —
no card, no key); it translates only the new segments and commits the cache.

## Quality notes / backlog
- Core nav, footer, categories are **hand-translated** (NL+ES). The rest is
  machine translation (keyless Google endpoint) — good for whole descriptions and labels, weaker on short
  mid-sentence fragments split by inline tags. Worth a human polish pass on the
  editorial pages (visitor-guide, about, daily-notices).
- JSON-LD structured data is intentionally left English (schema is language
  -neutral; avoids mistranslating schema values).
- Per-listing auto-generated meta descriptions backfill when CI runs
  `build_i18n.py` against the full site (writes the complete `i18n_segments.json`).
- Switcher is a lightweight EN/NL/ES text control; restyle in nav if desired.

## QA & polish pass (done)
Full review completed; fixes applied:
- **DOCTYPE bug** — the text-translation loop was replacing the `<!DOCTYPE html>`
  node (its text is literally "html"), which would have shipped quirks-mode pages
  site-wide. Now skips Doctype/Comment/CData; verified `<!doctype html>` on every page.
- **Brand wordmark** — nav AND footer "ExploreSuriname" wordmark kept verbatim in
  all languages (the hero tagline "Explore Suriname" still translates).
- **Brand in prose** — editorial mentions normalized to "Explore Suriname" (no more
  "Ontdek/Explorar Surinam" variants).
- **Business names** — shielded during translation so they stay verbatim in tab
  titles / search snippets.
- **today.html redirect** — now points to the localized /nl/ /es/ daily-notices.
Validated: 0 untranslated, 0 sentinel leaks, 0 empty, 0 mangled brand; all rendered
pages parse with valid DOCTYPE, html lang, 4 hreflang tags, switcher, canonical;
JSON-LD intact; search + sitemap localized. generate.py untouched.
