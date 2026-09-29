# CoverClaim

**DeFi hack insurance where claims are judged by GenLayer validators instead of a voting committee.**

> GenLayer reads public incident evidence and classifies it against the frozen policy's covered perils and exclusions. Deterministic contract logic enforces capacity, waiting periods, backdating checks, premium accounting, severity payouts, deductibles, and pro-rata splits.

DeFi users lose billions to hacks. Cover exists, but claims are usually decided by token holders voting — the same people who pay the claim — and "was it a contract bug or user error?" gets argued for weeks. CoverClaim freezes the policy wording when a pool is created and lets independent validators decide one narrow question: **does this incident match a covered peril or an exclusion?** Everything else is arithmetic — and **one event binds everything**: the claim names one DeFi Llama incident record, and that record alone fixes the incident date, the TVL window for severity, and what the evidence must be about.

- **Live app:** https://coverclaim.vercel.app
- **Network:** GenLayer Studio Dev, chain 61997
- **Tests:** 668 offline tests (`python3 test/test_logic.py`) plus the independent review's 21 regression tests (`python3 test/test_attacks.py`); every loophole below has its own test class
- **Resubmission (steward fix):** [RESUBMISSION.md](RESUBMISSION.md)
- **Audit:** [docs/AUDIT.md](docs/AUDIT.md) · **Probe:** [docs/PROBE.md](docs/PROBE.md) · **Seeded evidence:** [docs/EVIDENCE.md](docs/EVIDENCE.md) · **Design notes:** [contracts/NOTES.md](contracts/NOTES.md) · **Article draft:** [docs/ARTICLE.md](docs/ARTICLE.md)

## Contracts

| contract | address | what it is |
|---|---|---|
| `CoverClaim` (canonical) | `0x039BCD3b9a12f81e1069dBbe9122A4B2e73db937` | backdating enforced strictly; 30-day claim window, 72 h settlement, 48 h contest, 24 h stall |
| `CoverClaimDemo` — **DEMO** | `0x33e464ebF31eEaeD31fDB16D38CCb97FB30A8339` | **same bytes**, one constructor value: `demo_backdate_days = 1521`; windows in minutes |
| `CoverRegistry` | `0x045C4C2BDE62CA730ceDf9B3ea810fbd645f2c6b` | zero-custody consumer: `is_covered(address, protocol)` — `protocol` is the pool's frozen DeFi Llama slug, id, or `slug:id`, never its display name — and `get_active_cover(address)` |

The source in this repository **is** the source on chain: `node test/verify_onchain.mjs` reads each contract's code back with `gen_getContractCode` and compares it byte for byte (sha256 `d901d871…` for both CoverClaim instances). Earlier deployments are archived in `docs/previous-deployment/` (`1-first/`; `2-waitgate/` — the one the steward reviewed, before the one-event binding; `3-one-event/` — the binding, before undated pages were also kept from the classifier; `4-matched-pages/` — before the binding audit; `5-binding-audit/` — before protocol-domain binding and pool verification; `6-verification-view-bug/` — pool verification, before the view fix that stopped a failed-then-closed pool reading "verified"; `7-before-review-fixes/` — before the independent review's four fixes).

### About the DEMO instance

Real hacks are in the past, and the canonical instance rejects a claim on any incident dated before the cover's start + waiting period — which is the whole point. To demonstrate claim paths against **real historical incidents**, a second instance of the same source is deployed with `demo_backdate_days = 1521`, fixed at deployment: every cover sold there **starts 1,521 days before it is bought** (on 2026-09-29, that is 2022-07-31 — so one 365-day cover spans both of Curve's recorded incidents, 2022-08-09 and 2023-07-30). It is labelled `DEMO` by `get_config`, on every page of the app, and here. **It is not insurance.** The canonical instance has the flag at 0.

## How it works

1. **Frozen policy.** An underwriter calls `create_pool` with capacity (≥ 1 GEN) and the terms: protocol name, DeFi Llama slug and id, chain, covered perils (`SMART_CONTRACT_BUG`, `ORACLE_MANIPULATION`, `ECONOMIC_EXPLOIT`, `BRIDGE_COMPROMISE`), exclusions (`PHISHING`, `FRONTEND_HIJACK`, `USER_KEY_COMPROMISE`, `RUG_BY_TEAM`, `GOVERNANCE_ATTACK`), premium rate per 30 days, waiting period, deductible, max cover per buyer, term, collateral ratio, payout table and, optionally, one declared protocol domain. Every term is written once and hashed; there is no setter anywhere. **Verified before sale.** A pool is created **UNVERIFIED** and cannot sell. `verify_pool` (permissionless, one consensus round) reads DeFi Llama's record for the frozen slug: its id must be the pool's id, the pool's name must name it ("Euler" ↔ "Euler V1"), and a declared domain must **be** the website DeFi Llama lists. Pass → OPEN, and DeFi Llama's listed website becomes the pool's only protocol domain on the evidence allowlist (none if it lists none, or lists a shared publishing host like medium.com / github.com). Fail → FAILED_VERIFICATION: it can never sell, and `close_pool` returns the underwriter's capital. The underwriter's text never adds an evidence domain, so an underwriter cannot publish the post-mortem that decides their own claims.
2. **Mechanical rejection first.** `buy_cover` checks the pool is **verified** and in term, the per-buyer cap, the unlocked capacity, the exact premium (`ceil(cover × rate × days / 30)`, overpayment refunded) and a per-wallet rate limit. `file_claim(cover_id, incident_key, evidence_urls, statement)` checks one claim per cover, that the cover's **waiting period has ended**, the claim window, that the **incident key** (`<DeFi Llama id>:<YYYY-MM-DD>[:<record name>]`) names this pool's protocol and a day **inside the cover after its waiting period** (a key for an incident that predates the cover is refused here, and the cover keeps its one claim), and that **every evidence URL is on the pool's frozen allowlist** — before GenLayer is asked anything. `check_incident` and `check_evidence` are the same checks as views; the app lists the protocol's in-window records from DeFi Llama to pick from.
3. **GenLayer last.** `judge_claim` (permissionless) **opens only once the incident's whole 7-day TVL window has ended** — incident day + 8 days; before that nobody, buyer or underwriter, can have the claim judged, so severity is never fixed from a partial window. Then every validator fetches DeFi Llama's incident list and **selects the one record the key names — by exact day (and name), never "the latest in the window", and the feed's order changes nothing**; reads the protocol's TVL history in the **window anchored on that record's day** (the **severity**: drop from the day before to the 7-day low); fetches the evidence pages and **binds each to the record**: a page counts only if it names the protocol and dates the event within ±3 days of the record. **Only bound pages reach the classifier** — the digest, the prompt, the bracket, the strength and the hash are built from bound pages alone; a page dated to another event, or undated, contributes nothing to any of them. Dated evidence about another event, or undated evidence alone → **EVIDENCE_MISMATCH without a model call**. A key that names no record → **INCONCLUSIVE without a model call**. Then a **bracket** — which of the pool's covered perils and exclusions the bound evidence names, and the evidence-strength range. No indicator → INCONCLUSIVE without a model call. Otherwise the model answers inside the bracket, plus **`event_match`: SAME / DIFFERENT / UNCLEAR** — anything but SAME is EVIDENCE_MISMATCH. The full vector is compared: event match, classification, peril, exclusion, incident key and date, evidence binding, protocol match, severity bucket, TVL window, bracket and content hash exactly; strength within one step. The **content hash covers the incident key, the evidence digest and its page binding, the selected record, and the TVL window points**; `verify_claim` re-derives all of it from storage.
4. **Deterministic money.** EVIDENCE_MISMATCH → nothing paid, nothing moved, refileable. Incident before start + waiting → `REJECTED_BACKDATED` (defence in depth: the key check at filing already refuses it). After cover end → `REJECTED_AFTER_COVER_END`. EXCLUDED → `DENIED_EXCLUDED`. COVERED → `cover × table[bucket] × (1 − deductible)` — but if DeFi Llama has no TVL data around the incident, severity cannot be measured and a COVERED reading is **INCONCLUSIVE** (refileable), never a final 0% payout: missing data is not "no damage". Approved claims on one incident share a settlement window; `finalize_incident` pays them together, **scaled pro-rata** if they exceed the collateral locked for those covers. Integer math, dust to the underwriter. **A window's membership is final when it closes**: a claim approved later on the same incident opens a new batch that settles on its own, so late approvals can never hold an earlier batch open. If DeFi Llama has not published the window's last day, severity is unmeasured and a COVERED reading is INCONCLUSIVE (refileable), never a lower bucket.

### Payout table (default)

| bucket | TVL drop | payout |
|---|---|---|
| 0 | < 10% | 0% |
| 1 | 10–30% | 25% |
| 2 | 30–60% | 50% |
| 3 | 60–90% | 75% |
| 4 | ≥ 90% | 100% |

### Exception paths

- **Waiting period** — a claim cannot be filed until it ends (refused mechanically, "claimable after …"); incidents dated inside it are backdated.
- **Inconclusive** — `refile_claim(claim_id, incident_key, evidence_urls, statement)` with at least one new source or a different incident, free, until the claim deadline. **Two refiles per claim in all**, whatever the reason (inconclusive, mismatch, stall). "New" means a new *source*: the same page with a `#fragment`, a trailing slash, re-ordered query parameters, or another Wayback timestamp of it is the same source; the same record's key written with or without its name is the same incident.
- **Evidence mismatch** — the evidence is not about the selected incident. No payout, no bond or premium movement, not contestable; the claim is **not consumed**: refile with evidence about that incident or a corrected key (`""` keeps the current one) — within the same two-refile limit.
- **Pool expiry** — covers must end within the pool's term; `release_cover` credits the premium to the underwriter once a cover's claim window closes; `close_pool` only when no cover is live.
- **Stalled consensus** — `settle_stalled` (permissionless, **works while paused**) returns a stuck claim to FILED and lets the buyer refile, or drops a stuck contest and returns the bond. No money is lost either way.
- **Contest** — the losing side, once, within the contest window, with a bond and **novel** evidence (new URLs, and written grounds that add sentences the claim never said — verbatim, re-punctuated or repeated text is refused before scoring). Flip → bond back; hold → bond to the other side.

## Seeded outcomes (on chain)

| scenario | instance | incident key | result |
|---|---|---|---|
| **MULTI-INCIDENT 1** | demo | Curve `3:2023-07-30`, Vyper evidence | COVERED `SMART_CONTRACT_BUG`, event SAME, bucket 2 (49.52% drop in the Vyper window) → paid |
| **MULTI-INCIDENT 2** | demo | Curve `3:2022-08-09`, Vyper evidence | **EVIDENCE_MISMATCH** — no page dates the DNS event; no model call, no payout |
| **MULTI-INCIDENT 3** | demo | Curve `3:2023-07-30`, DNS evidence | **EVIDENCE_MISMATCH** — no model call, no payout |
| **MULTI-INCIDENT 4** | demo | Curve `3:2022-08-09`, DNS evidence | EXCLUDED `FRONTEND_HIJACK`, event SAME, bucket 0 (DNS window) |
| **MULTI-INCIDENT 5** | demo | Curve `3:2023-07-30`, DNS evidence → refiled with Vyper | EVIDENCE_MISMATCH → refile → COVERED → paid |
| **MIXED EVIDENCE 6** | demo | Curve `3:2022-08-09`, [DNS article, Vyper article] | classified from the DNS page only → EXCLUDED, no payout |
| **MIXED EVIDENCE 7** | demo | Curve `3:2023-07-30`, [Vyper article, DNS article] | classified from the Vyper page only → COVERED → paid |
| COVERED | demo | Euler `1183:2023-03-13` (donation attack) | APPROVED → PAID at bucket 4 |
| CONTESTED | demo | same claim | underwriter contested with Euler's own post-mortem; **UPHELD**, bond to the buyer |
| EXCLUDED | demo | Multichain `591:2023-07-07` (keys) | DENIED_EXCLUDED — USER_KEY_COMPROMISE |
| INCONCLUSIVE | demo | Euler, evidence = homepage (undated, names no risk) | INCONCLUSIVE with no model call; refile allowed |
| PRO-RATA | demo | Euler, two covers on a 50%-collateral pool, keyed `1183:2023-03-13` and `1183:2023-03-13:Euler V1` | one canonical incident, one batch, both scaled by the same factor |
| EXPIRED | demo | 1-day cover, never claimed | released; premium to the underwriter |
| STALLED | demo | Tornado Cash `148:2023-05-20` | settled while paused, then judged while paused |
| BACKDATED | canonical | Euler `1183:2023-03-13` on a cover bought 2026-09-29 | **refused at filing**, before any fetch or model call; the cover keeps its one claim |
| WAITING-PERIOD GATE | canonical | claim filed on day 0 of a 7-day wait | refused mechanically, "claimable after …"; the cover's one claim is not spent |
| REGISTRY | canonical | waiting-0 cover on Curve | `CoverRegistry.attest` → covered = true |

Every transaction hash: [RESUBMISSION.md](RESUBMISSION.md) (the multi-incident proof) and [docs/EVIDENCE.md](docs/EVIDENCE.md) (all scenarios, derived by reading the chain, `node test/collect.mjs`). After seeding, the demo instance was drained: every cover released, every pool closed, every balance withdrawn — books at exactly 0 ([docs/drain-evidence.json](docs/drain-evidence.json)).

**Measured delivery gap.** Studio Dev finalizes `claim_payout` transactions and the contract's books drop by exactly the amount withdrawn, but — as measured on earlier deployments and on this one — the network may post the transfer without executing it. `get_stats` publishes the contract's real chain balance beside its books as `undelivered_wei` rather than hiding the gap (figure for this deployment in docs/drain-evidence.json).

## Loopholes, and the test that closes each

| # | loophole | how it is blocked | test class |
|---|---|---|---|
| 1 | buying cover after an incident is public | the claim's incident key must be dated inside the cover after its waiting period — refused at filing, before any model call; the date is DeFi Llama's, so an in-window date for an older incident names no record | `TestLoophole01_…` |
| 2 | fake evidence from a random blog | https, frozen allowlist, subdomain-exact, no userinfo/ports; archive only of allowlisted pages; refused before GenLayer | `TestLoophole02_…` |
| 2b | underwriter's own "official" domain used to flip a claim in a contest | the only protocol domain is the website DeFi Llama lists, set by `verify_pool`; any other domain is refused before GenLayer | `TestPoolVerification` |
| 2c | a pool whose slug, id, name or domain are not one protocol selling cover that can never pay | `buy_cover` sells only VERIFIED pools; FAILED pools can only close | `TestPoolVerification` |
| 3 | underwriter withdrawing before a claim | collateral locked per cover until expiry + claim window; close refused while any cover is live | `TestLoophole03_…` |
| 4 | same cover claimed twice | one claim per cover; INCONCLUSIVE is refiled on the same record | `TestLoophole04_…` |
| 5 | more claims than capacity | settlement window per incident; same pro-rata factor for all; dust to underwriter | `TestLoophole05_…` |
| 6 | evidence edited after judging | stored digest + content hash; `verify_claim`; contests re-read the stored text | `TestLoophole06_…` |
| 7 | contest copying old evidence | new URLs only; GrantJudge sentence-novelty gate on grounds and, in consensus, on new pages | `TestLoophole07_…` |
| 8 | protocol B's incident on protocol A's cover | the key must carry the pool's own DeFi Llama id; a page counts only if it names the protocol | `TestLoophole08_…` |
| 11 | evidence about incident A paired with the record of incident B (same protocol, same window) | the claim names ONE record by key; exact selection, no "latest row"; pages bound by date (±3 d) and the model's `event_match` compared exactly; TVL window anchored on the same record; one hash over key + evidence + record + window | `TestOneEventBindsEverything` |
| 12 | the same hack keyed two ways, or approve → contest flip → refile → re-approve | canonical incident id (record's id:day:name) keys settlement and the hash; a claim is listed once per batch; finalize pays each claim once, on a live cover | `TestBindingAudit` |
| 13 | a pool name no article contains ("Curve DEX", "Euler V1") making every claim unpayable | verification stores DeFi Llama's **core name** (generic DEX / V1–V5 / Finance / Protocol / Labs / Exchange dropped); the pool name must reduce to it, and evidence is matched on it — any spelling of the pool name judges identically | `test_attacks.py` Finding1, Fix1 |
| 14 | the underwriter judging at once to fix severity from a partial TVL window | `judge_claim` / `judge_contest` refused before incident day + 8; an unpublished window is INCONCLUSIVE, never a lower bucket | `test_attacks.py` Finding2, Fix2 |
| 15 | late approvals every 47 h holding a settlement batch open | membership final when the window closes; later approvals settle in a new batch | `test_attacks.py` Finding3, Fix3 |
| 16 | re-rolling the same evidence by re-spelling the URL or the key | source identity (fragment, slash, query order, Wayback timestamp) and canonical incident identity; one combined limit of two refiles | `test_attacks.py` Finding4, Fix4 |
| 9 | owner pausing to freeze money | pause gates only create_pool / add_capacity / buy_cover | `TestLoophole09_…` |
| 10 | payment that also reads the clock | only `claim_payout` transfers and it reads no clock; everything else credits | `TestLoophole10_…` |

## Repository

```
contracts/CoverClaim.py      the contract (assembled from contracts/parts/* by tools/assemble.sh)
contracts/CoverRegistry.py   the zero-custody consumer
contracts/_probe*.py         throwaway probes (STEP 1)
contracts/NOTES.md           design reasoning and hazards
test/test_logic.py           668 offline tests, stdlib only
test/test_attacks.py         the independent review's regression tests (21)
test/*.mjs                   probe, deploy, seed, collect, verify_onchain
tools/audit.py               STEP 6 audit → docs/AUDIT.md
frontend/                    Next.js app (obsidian + signal orange)
docs/                        PROBE, EVIDENCE, AUDIT, ARTICLE
```

```
python3 test/test_logic.py          # offline suite
python3 tools/audit.py              # rejection patterns + loopholes → docs/AUDIT.md
node test/verify_onchain.mjs        # deployed bytes == repo bytes
cd frontend && npm i && npm run dev # app (see frontend/.env.example)
```

## Honest limitations

- **Parametric.** It pays by incident severity — the drop in DeFi Llama TVL around the incident — not by proven personal loss. TVL also falls when token prices fall, and a small exploit on a huge protocol may pay nothing.
- **Evidence is only as good as the allowlisted sources.** rekt.news, archive snapshots of allowlisted pages and the protocol's website **as DeFi Llama lists it** (none, if it lists none). Pages are read with a plain GET and stripped by the contract (rendering stalled on chain, see PROBE §4), so a JavaScript-only page reads as empty — INCONCLUSIVE, never a payout.
- **Incident classification is subjective.** The bracket bounds it — the model can only pick risks the evidence names and the pool lists — but inside the bracket a model still chooses, and validators must agree.
- **The incident record must exist.** DeFi Llama's incident list is the source of the incident date. A hack it has not recorded yet cannot be claimed until it does (a key naming no record is INCONCLUSIVE and can be refiled).
- **Evidence must name DeFi Llama's core name.** "Curve DEX" is matched as "Curve", "Euler V1" as "Euler". Where DeFi Llama keeps a product word in the name (KyberSwap *Elastic*, Mango *Markets*), the evidence must use it too.
- **A claim waits for the whole severity window.** Judging opens 8 days after the incident day, and severity counts only if DeFi Llama has published the window's last day; until then a COVERED reading is INCONCLUSIVE and refileable (twice in all).
- **Evidence must date the event.** A page counts toward a claim only if it names the protocol and writes a date within ±3 days of the record (rekt.news heads each article with its date). An official post-mortem that writes no date is not read at all — attach a dated page about the same incident; a claim with no dated page is EVIDENCE_MISMATCH (or INCONCLUSIVE if it names no risk), refileable. Dates are parsed deterministically from written forms (`July 31, 2023`, `31 July 2023`, `2023-07-31`, and yearless `July 7th` taking the page's year).
- **The DEMO instance uses a fixed backdate window** (1,521 days) to replay real incidents. It is not insurance, and a demo cover is never "in force" for CoverRegistry.
- **Studio Dev delivery quirks.** Studio Dev has been measured (by earlier projects) to queue an `on="finalized"` value transfer without executing it. `get_stats` publishes the contract's real chain balance next to its books and names the gap `undelivered_wei`; the seed records it rather than hiding it.
- **Capacity can stay locked if nobody ever judges a filed claim.** Judging is permissionless and anyone — including the underwriter — can trigger it; `settle_stalled` keeps a stuck claim refileable but does not release the collateral.
