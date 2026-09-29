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

## Confirmation: only matched pages reach the classifier
- [x] finding: dated-elsewhere pages were already excluded; UNDATED pages still reached the classifier → FAIL, fixed (bound pages only)
- [x] tests: DNS record + [DNS, Vyper] → EXCLUDED from DNS page only; Vyper record + [Vyper, DNS] → COVERED from Vyper page only; prompts byte-identical to single-page prompts; undated page never in prompt (632 tests)
- [x] redeployed (canonical 0xF2F545d2…, demo 0xf59B1A3D…, registry 0x06144d47…), byte-for-byte verified
- [x] reseeded incl. mixed-evidence claims 6 and 7 on chain; Euler scenario re-run after a seed-script cooldown bug (fixed)
- [x] drained to 0; chain scenarios 19/19; audit 54/0
- [x] addresses updated: deployments.json, README, RESUBMISSION, frontend env (Vercel prod), live bundle verified
- [x] pushed; GitHub bytes verified

## Binding audit, items 2–6
- [x] 2 canonical incident identity: FAIL (batches keyed by day) → fixed, `incident_id` from the record; tests
- [x] 3 contest binding: PASS; tests added
- [x] 4 refile binding: leftover batch/contest state → fixed; tests
- [x] 5 one payout per cover: FAIL (double listing → double pay after flip+refile) → fixed; tests incl. randomized
- [x] 6 other bindings: registry matched free-text pool name → fixed (slug/id only); Wayback metadata hardened; rest PASS
- [x] 650 offline tests
- [x] redeployed all three, byte-for-byte verified (canonical 0x8a7e766b…, demo 0x02A81134…, registry 0x325A8497…)
- [x] Vercel production env + deploy; live bundle only new addresses
- [x] reseed incl. Curve proof and two-way-keyed pro-rata (19/19); drained to 0; audit 57/0; pushed

## Protocol-domain binding and pool verification
- [x] 1 protocol domain binding: FAIL (underwriter-chosen domains on the allowlist) → only DeFi Llama's listed website, via verify_pool; shared hosts never; tests
- [x] 2 pool verification before sale: FAIL (pools sold at creation) → UNVERIFIED until verify_pool; FAILED can only close; tests
- [x] extra: pool name must name DeFi Llama's protocol (premium trap via mis-named pool)
- [x] bug found by the chain collector and fixed: failed-then-closed pool read "verified" (view derived from status) → stored verify_verdict; redeployed
- [x] 667 offline tests; README / ARTICLE / NOTES / app docs re-checked
- [x] redeployed all three, byte-for-byte; 24/24 chain scenarios; drained to 0; audit 64/0; Vercel; pushed

## Independent review (test/test_attacks.py)
- [x] 1 pool name / evidence: core name from DeFi Llama stored at verification; evidence matched on it; "Curve" ≡ "Curve DEX"
- [x] 2 partial severity window: judge_claim / judge_contest refused before day + 8; unpublished window → INCONCLUSIVE
- [x] 3 batch held open: membership final at close; late approvals → new batch
- [x] 4 refile re-roll: URL source identity + canonical incident identity; one combined refile limit (2)
- [x] test_attacks.py: 21/21 (reviewer's 7 + 14 fix tests); Finding 2/3 preconditions updated to the fixed behaviour; test_logic.py 668/668
- [x] live TVL windows of every seeded incident are complete (8 daily points)
- [x] redeployed all three (canonical 0x039BCD3b…, demo 0x33e464eb…, registry 0x045C4C2B…), byte-for-byte vs repo
- [x] Vercel production env + deploy; live bundle only new addresses
- [x] README / ARTICLE / NOTES / in-app docs
- [x] reseeded (27/27 on chain incl. Curve proof on a "Curve DEX" pool, late-approval batch, fragment refile refused); drained to 0; audit 69/0; RESUBMISSION; pushed; GitHub bytes verified
