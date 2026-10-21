# ADR-0004: Separate permanent seen-URLs table from the TTL'd content cache

## Context
`save_lead` must reject evidence URLs that were never actually fetched (an anti-hallucination
guard), and must verify a claimed email appears verbatim on its source page. `fetch_page`
already caches extracted page text, but that cache has a 7-day TTL for freshness — a URL fetched
3 weeks ago would have aged out, even though it genuinely was fetched once.

## Decision
Two separate stores, both written by `fetch_page`:
- `seen_urls` (`seen.py`): permanent, no TTL — proves a URL was legitimately fetched at some
  point. This is what `save_lead` checks before trusting an evidence URL at all.
- the content cache's `page_full:{url}` key (`cache.py`, via `fetch.get_full_text`): TTL'd like
  the rest of the cache — this is what the verbatim-email check reads.

A URL can be "seen" (permanently) while its content cache has since expired. In that case,
`save_lead` treats the email as unverified rather than trusting an unverifiable claim — citing
stale evidence should require re-fetching, not sliding through on an old "yes, I saw it once".

## Alternatives considered
- One permanent cache with no TTL at all: simpler, but means `fetch_page` never reflects a page
  that's since changed, which defeats the point of caching live web content.
- Re-fetch on every `save_lead` call to verify: respects the per-domain rate limit and
  `robots.txt` correctly, but makes `save_lead` a network call instead of a pure
  validate-and-score step, and duplicates `fetch_page`'s own fetch logic.

## Consequences
Two related but distinct concepts ("was this ever fetched" vs "do we still have its content") to
keep straight when reading `fetch.py`. Worth revisiting if the TTL mismatch between the two ever
causes confusing "seen but unverifiable" results in practice.
