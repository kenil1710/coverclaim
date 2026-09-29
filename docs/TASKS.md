# Steward fix: one event binds evidence, incident record and TVL window

Status legend: [ ] todo · [x] done · [!] blocked (reason inline)

## Contract
- [x] `file_claim(cover_id, incident_key, evidence_urls, statement)`; key = `<llama id>:<YYYY-MM-DD>[:<name>]`
- [x] mechanical refusals at filing: missing/malformed key, id != pool's, date outside start+waiting..end, future date
- [x] exact record selection by key (`_select_incident`); `_pick_incident` ("latest row") removed; a tie is refused, not broken by position
- [x] unknown key → pinned INCONCLUSIVE, no model call, refileable with a corrected key
- [x] date binding per page (±3 days, deterministic parser incl. yearless dates) — `_dates_in`, `_bind`
- [x] model field `event_match` SAME/DIFFERENT/UNCLEAR, compared exactly
- [x] EVIDENCE_MISMATCH status: no payout, nothing moves, not contestable, refileable (new URL or corrected key), max 2 mismatch refiles
- [x] TVL window anchored on the selected record; window points in `tvl_line`
- [x] content hash = key | digest | page binding | record | TVL window; `verify_claim` re-derives hash, record↔key, window anchor, low/drop
- [x] views/config: `check_incident`, claim view fields, `get_config` key format / window / refile limit
- [x] NOTES.md §2 rewritten

## Tests (offline) — `TestOneEventBindsEverything`, `TestSelectIncident`, `TestDatesAndKeys`
- [x] a. A evidence + A record → classified, A's severity (Vyper: bucket 2, 4952 bps)
- [x] b. A evidence + B record → EVIDENCE_MISMATCH, no model call, nothing moved
- [x] c. B evidence + A record → EVIDENCE_MISMATCH (also: model DIFFERENT/UNCLEAR on a bound page)
- [x] d. feed rows shuffled / reversed, extra in-window row → same record, same hash
- [x] e. record outside window → refused at filing, no fetch, no model
- [x] f. missing / malformed / wrong-protocol key refused at filing; unknown key pinned before model; ambiguous key needs the name
- [x] g. refile after mismatch (new evidence, or corrected key) → judged normally; limit 2 enforced
- [x] existing suite green — 628 tests. Intended changes: canonical backdating tests now assert refusal at filing; other-protocol evidence is EVIDENCE_MISMATCH

## Chain
- [x] probe: both Curve rows in live /hacks; all seed pages readable by GET and bound (docs/PROBE.md, last section)
- [x] deploy canonical, demo, registry; source byte-for-byte vs repo (verify_onchain.mjs)
- [x] reseed existing scenarios + Curve multi-incident proof (M1–M5)
- [x] waiting-period gate on the new canonical (waitgate.mjs)
- [x] collect → docs/EVIDENCE.md
- [x] drain demo to exactly 0
- [x] audit incl. no-latest-row + hash-binding checks; README addresses == deployments.json
- [x] source byte-for-byte vs GitHub after push (commit aec7e1f: CoverClaim ffb55c47…, CoverRegistry 7aa73378… — identical to repo and chain)

## Docs / frontend / ship
- [x] README, docs/EVIDENCE.md, docs/ARTICLE.md — 52/0 audit, 17/17 chain scenarios
- [x] frontend: incident picker (live api.llama.fi), `check_incident`, refile with key, binding shown; builds
- [x] Vercel production env → new addresses; deployed; live bundle has only the new addresses
- [x] RESUBMISSION.md
- [x] push (no Co-Authored-By) — aec7e1f
