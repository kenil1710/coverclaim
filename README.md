# CoverClaim

**DeFi hack insurance where claims are judged by GenLayer validators instead of a voting committee.**

> GenLayer reads public incident evidence and classifies it against the frozen policy's covered perils and exclusions. Deterministic contract logic enforces capacity, waiting periods, backdating checks, premium accounting, severity payouts, deductibles, and pro-rata splits.

DeFi users lose billions to hacks. Cover exists, but claims are usually decided by token holders voting — the same people who pay the claim — and "was it a contract bug or user error?" gets argued for weeks. CoverClaim freezes the policy wording when a pool is created and lets independent validators decide one narrow question: **does this incident match a covered peril or an exclusion?** Everything else is arithmetic.

- **Live app:** https://coverclaim.vercel.app
- **Network:** GenLayer Studio Dev, chain 61997
- **Tests:** 598 offline tests (`python3 test/test_logic.py`), every loophole below has its own test class
- **Audit:** [docs/AUDIT.md](docs/AUDIT.md) · **Probe:** [docs/PROBE.md](docs/PROBE.md) · **Seeded evidence:** [docs/EVIDENCE.md](docs/EVIDENCE.md) · **Design notes:** [contracts/NOTES.md](contracts/NOTES.md) · **Article draft:** [docs/ARTICLE.md](docs/ARTICLE.md)

## Contracts

| contract | address | what it is |
|---|---|---|
| `CoverClaim` (canonical) | `0xeDBB5f6ea3D01289E1D879729C2253058602F145` | backdating enforced strictly; 30-day claim window, 72 h settlement, 48 h contest, 24 h stall |
| `CoverClaimDemo` — **DEMO** | `0xF77087fB487153212c3d3Bc178875f7fBeA52fFa` | **same bytes**, one constructor value: `demo_backdate_days = 1521`; windows in minutes |
| `CoverRegistry` | `0x39A8da9f3b6F7a921B50ecc5256B2837703ADd13` | zero-custody consumer: `is_covered(address, protocol)`, `get_active_cover(address)` |

The source in this repository **is** the source on chain: `node test/verify_onchain.mjs` reads each contract's code back with `gen_getContractCode` and compares it byte for byte (sha256 `51e15cf7…` for both CoverClaim instances). The first deployment, before the two review fixes, is archived in `docs/previous-deployment/`.

### About the DEMO instance

Real hacks are in the past, and the canonical instance rejects a claim on any incident dated before the cover's start + waiting period — which is the whole point. To demonstrate claim paths against **real historical incidents**, a second instance of the same source is deployed with `demo_backdate_days = 1521`, fixed at deployment: every cover sold there **starts 1,521 days before it is bought** (on 2026-09-26, that is 2022-07-28). It is labelled `DEMO` by `get_config`, on every page of the app, and here. **It is not insurance.** The canonical instance has the flag at 0.

## How it works

1. **Frozen policy.** An underwriter calls `create_pool` with capacity (≥ 1 GEN) and the terms: protocol name, DeFi Llama slug and id, chain, covered perils (`SMART_CONTRACT_BUG`, `ORACLE_MANIPULATION`, `ECONOMIC_EXPLOIT`, `BRIDGE_COMPROMISE`), exclusions (`PHISHING`, `FRONTEND_HIJACK`, `USER_KEY_COMPROMISE`, `RUG_BY_TEAM`, `GOVERNANCE_ATTACK`), premium rate per 30 days, waiting period, deductible, max cover per buyer, term, collateral ratio, payout table and official evidence domains. Every term is written once and hashed; there is no setter anywhere.
2. **Mechanical rejection first.** `buy_cover` checks the pool is open and in term, the per-buyer cap, the unlocked capacity, the exact premium (`ceil(cover × rate × days / 30)`, overpayment refunded) and a per-wallet rate limit. `file_claim` checks one claim per cover, that the cover's **waiting period has ended** (a claim filed earlier could only ever be backdated, and would waste the cover's one claim), the claim window, and that **every evidence URL is on the pool's frozen allowlist** — before GenLayer is asked anything.
3. **GenLayer last.** `judge_claim` (permissionless): every validator fetches DeFi Llama's incident list (the **incident date**, by the pool's DeFi Llama id), the protocol's TVL history (the **severity**: drop from the day before to the 7-day low), and the evidence pages; keeps only sentences that name the protocol or a risk; and computes a **bracket** — which of the pool's covered perils and exclusions the evidence actually names, and the evidence-strength range the sources support. No indicator, or protocol not named → **INCONCLUSIVE without a model call**. Otherwise the model chooses inside the bracket. The full vector is compared: classification, peril, exclusion, incident date, protocol match, severity bucket, TVL figures, bracket and content hash exactly; strength within one step.
4. **Deterministic money.** Incident before start + waiting → `REJECTED_BACKDATED` (premium not refunded — the cover was valid, the incident predates it). After cover end → `REJECTED_AFTER_COVER_END`. EXCLUDED → `DENIED_EXCLUDED`. COVERED → `cover × table[bucket] × (1 − deductible)` — but if DeFi Llama has no TVL data around the incident, severity cannot be measured and a COVERED reading is **INCONCLUSIVE** (refileable), never a final 0% payout: missing data is not "no damage". Approved claims on one incident share a settlement window; `finalize_incident` pays them together, **scaled pro-rata** if they exceed the collateral locked for those covers. Integer math, dust to the underwriter.

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
- **Inconclusive** — `refile_claim` with at least one new source, free, until the claim deadline.
- **Pool expiry** — covers must end within the pool's term; `release_cover` credits the premium to the underwriter once a cover's claim window closes; `close_pool` only when no cover is live.
- **Stalled consensus** — `settle_stalled` (permissionless, **works while paused**) returns a stuck claim to FILED and lets the buyer refile, or drops a stuck contest and returns the bond. No money is lost either way.
- **Contest** — the losing side, once, within the contest window, with a bond and **novel** evidence (new URLs, and written grounds that add sentences the claim never said — verbatim, re-punctuated or repeated text is refused before scoring). Flip → bond back; hold → bond to the other side.

## Seeded outcomes (on chain)

| scenario | instance | incident | result |
|---|---|---|---|
| COVERED | demo | Euler V1, 2023-03-13 (donation attack) | APPROVED → PAID at bucket 4 (95.85% TVL drop) |
| CONTESTED | demo | same claim | underwriter contested with Euler's own post-mortem; **UPHELD**, bond to the buyer |
| EXCLUDED | demo | Curve, 2022-08-09 (DNS hijack) | DENIED_EXCLUDED — FRONTEND_HIJACK |
| EXCLUDED | demo | Multichain, 2023-07-07 (keys) | DENIED_EXCLUDED — USER_KEY_COMPROMISE |
| INCONCLUSIVE | demo | Euler, evidence = homepage | INCONCLUSIVE with no model call; refile allowed |
| PRO-RATA | demo | Euler, two covers on a 50%-collateral pool | both scaled by the same factor |
| EXPIRED | demo | 1-day cover, never claimed | released; premium to the underwriter |
| STALLED | demo | Tornado Cash, 2023-05-20 | settled while paused, then judged while paused |
| REJECTED_BACKDATED | canonical | Euler, cover bought 2026-09-26 (waiting-0 pool) | REJECTED_BACKDATED; classification COVERED, date predates cover |
| WAITING-PERIOD GATE | canonical | claim filed on day 0 of a 7-day wait | refused mechanically, "claimable after …"; the cover's one claim is not spent |
| REGISTRY | canonical | waiting-0 cover on Curve | `CoverRegistry.attest` → covered = true |

**Measured delivery gap.** Five `claim_payout` calls on the demo instance withdrew 2.365 GEN (payouts, the returned contest bond, earned premium). Each transaction reached FINALIZED and the contract's books dropped by exactly that amount — but its real chain balance did not: `get_stats` reports `undelivered_wei = 2365066666666666668`. Studio Dev posted the transfers and did not execute them, as measured on earlier projects. The contract's books and the ledger identity are correct; the network's delivery is the gap, and it is published rather than hidden.

Every transaction hash and return value: [docs/EVIDENCE.md](docs/EVIDENCE.md) (derived by reading the chain, `node test/collect.mjs`).

## Loopholes, and the test that closes each

| # | loophole | how it is blocked | test class |
|---|---|---|---|
| 1 | buying cover after an incident is public | incident date from DeFi Llama; before start + waiting → REJECTED_BACKDATED | `TestLoophole01_…` |
| 2 | fake evidence from a random blog | https, frozen allowlist, subdomain-exact, no userinfo/ports; archive only of allowlisted pages; refused before GenLayer | `TestLoophole02_…` |
| 3 | underwriter withdrawing before a claim | collateral locked per cover until expiry + claim window; close refused while any cover is live | `TestLoophole03_…` |
| 4 | same cover claimed twice | one claim per cover; INCONCLUSIVE is refiled on the same record | `TestLoophole04_…` |
| 5 | more claims than capacity | settlement window per incident; same pro-rata factor for all; dust to underwriter | `TestLoophole05_…` |
| 6 | evidence edited after judging | stored digest + content hash; `verify_claim`; contests re-read the stored text | `TestLoophole06_…` |
| 7 | contest copying old evidence | new URLs only; GrantJudge sentence-novelty gate on grounds and, in consensus, on new pages | `TestLoophole07_…` |
| 8 | protocol B's incident on protocol A's cover | record looked up by the pool's own DeFi Llama id; evidence must name the protocol | `TestLoophole08_…` |
| 9 | owner pausing to freeze money | pause gates only create_pool / add_capacity / buy_cover | `TestLoophole09_…` |
| 10 | payment that also reads the clock | only `claim_payout` transfers and it reads no clock; everything else credits | `TestLoophole10_…` |

## Repository

```
contracts/CoverClaim.py      the contract (assembled from contracts/parts/*)
contracts/CoverRegistry.py   the zero-custody consumer
contracts/_probe*.py         throwaway probes (STEP 1)
contracts/NOTES.md           design reasoning and hazards
test/test_logic.py           598 offline tests, stdlib only
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
- **Evidence is only as good as the allowlisted sources.** rekt.news, archive snapshots of allowlisted pages and the protocol's official domain. Pages are read with a plain GET and stripped by the contract (rendering stalled on chain, see PROBE §4), so a JavaScript-only page reads as empty — INCONCLUSIVE, never a payout.
- **Incident classification is subjective.** The bracket bounds it — the model can only pick risks the evidence names and the pool lists — but inside the bracket a model still chooses, and validators must agree.
- **The incident record must exist.** DeFi Llama's incident list is the source of the incident date. A hack it has not recorded yet is INCONCLUSIVE until it does.
- **The DEMO instance uses a fixed backdate window** (1,521 days) to replay real incidents. It is not insurance, and a demo cover is never "in force" for CoverRegistry.
- **Studio Dev delivery quirks.** Studio Dev has been measured (by earlier projects) to queue an `on="finalized"` value transfer without executing it. `get_stats` publishes the contract's real chain balance next to its books and names the gap `undelivered_wei`; the seed records it rather than hiding it.
- **Capacity can stay locked if nobody ever judges a filed claim.** Judging is permissionless and anyone — including the underwriter — can trigger it; `settle_stalled` keeps a stuck claim refileable but does not release the collateral.
