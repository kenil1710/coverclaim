# Resubmission — one event binds evidence, incident record and TVL window

## What the steward found

> "Please update the adjudication path so submitted evidence cannot be paired with a different DeFi Llama incident merely because it is the latest row in the cover window. Bind the evidence, selected incident record, and TVL interval to the same event, and add a multi-incident test showing that mismatched evidence cannot produce a payout while matching evidence selects the intended event."

The finding was correct. `_pick_incident` chose **the latest DeFi Llama hacks row for the protocol inside the cover window**, independently of the evidence. Curve has two records a year apart: the DNS hijack of 2022-08-09 (a front-end attack) and the Vyper reentrancy of 2023-07-30 (a code flaw). For a cover spanning both, the old contract dated a claim, and measured its severity, on the Vyper record whatever the evidence described. So a claim carrying the DNS article could be classified from DNS text and paid at the Vyper TVL drop. The evidence, the date and the severity window could each be about a different event.

## The fix

| | before | after |
|---|---|---|
| which record | the latest row in the window, chosen by the contract | the claimant names **one record by key**, `<llama id>:<YYYY-MM-DD>[:<record name>]`. `file_claim(cover_id, incident_key, evidence_urls, statement)` |
| selection | ordering comparison over the feed | `_select_incident`: equality on day (and name) only. No match means the key names no record; two matches mean "add the name". Feed order cannot change the answer. `_pick_incident` is deleted |
| window check | after judging (`REJECTED_BACKDATED`) | **at filing, before any fetch or model call.** The key must carry the pool's DeFi Llama id and a day inside `[start + waiting, end]`, not in the future. `check_incident` is the same check as a view |
| evidence ↔ event | the protocol must be named | per-page **binding**: a page counts only if it names the protocol and writes a date within **±3 days** of the selected record (deterministic parser, `_dates_in`). Pages dated to another event are not read. Plus a bounded model field **`event_match`: SAME / DIFFERENT / UNCLEAR**, compared exactly |
| mismatch | — | **EVIDENCE_MISMATCH**: no payout, no bond or premium movement, not contestable. The claim is **not consumed**: refile with other evidence or a corrected key (one of them must change), **at most 2 times** |
| severity | TVL around the chosen row | TVL window **anchored on the selected record's day**. Existing rules unchanged: a non-zero point before it and at least one point within 7 days after, otherwise INCONCLUSIVE |
| hash | `fnv(digest \| record \| TVL figures)` | `fnv(incident_key \| digest \| page binding \| selected record (every field) \| TVL window points)`. `verify_claim` recomputes it, checks the stored record is the key's (id and day), checks the window is anchored on the key's day with every point inside it, and recomputes low / drop / bucket |

Deterministic gates come first:
- Dated evidence about another event → EVIDENCE_MISMATCH (DIFFERENT) with **no model call**.
- A key that names no record → INCONCLUSIVE with **no model call**.
- Undated-only evidence that would otherwise reach the model → EVIDENCE_MISMATCH (UNCLEAR).

A claim never pays without a page that dates the event.

Design notes: `contracts/NOTES.md` §2. Live probe of every seeded page through the contract's own GET, strip, parser and binding: `docs/PROBE.md`, last section.

## Tests (offline, `python3 test/test_logic.py`, 628 passing)

`TestOneEventBindsEverything` runs on Curve's two real records in one cover window (fixtures captured from the live sources). DNS is excluded (FRONTEND_HIJACK) and Vyper is covered (SMART_CONTRACT_BUG).

| steward case | test | result |
|---|---|---|
| a. evidence A + record A | `test_a_matching_evidence_selects_the_intended_event` | APPROVED, SAME, incident 2023-07-30, Vyper window bucket 2 (4952 bps); DNS + DNS record → DENIED_EXCLUDED at the DNS window's bucket 0 |
| b. evidence A + record B | `test_b_evidence_A_with_record_B_is_mismatch` | EVIDENCE_MISMATCH, no model call, gross 0, no batch, nothing credited |
| c. evidence B + record A | `test_c_evidence_B_with_record_A_is_mismatch`, `test_c_model_different_is_mismatch_even_when_dates_bind` | EVIDENCE_MISMATCH. The model's DIFFERENT / UNCLEAR on a bound page is also a mismatch |
| d. feed reordering | `test_d_feed_order_does_not_change_the_record`, `test_d_on_the_contract_too` | 6 shuffles plus an extra in-window Curve row: same record, same severity, one content hash |
| e. record outside the window | `test_e_record_outside_the_window_refused_before_model` | refused at filing (before start + waiting / after end); no fetch, no model |
| f. missing / unknown key | `test_f_missing_or_malformed_key_refused`, `test_f_unknown_key_refused_before_model`, `test_f_ambiguous_key_refused_until_named` | refused at filing; an unknown key is pinned before any model call and the reply lists the protocol's recorded dates; an ambiguous day needs the name |
| g. refile after mismatch | `test_g_refile_after_mismatch_with_correct_evidence`, `test_g_refile_with_corrected_key_same_evidence`, `test_g_mismatch_refiles_are_limited` | judged normally (APPROVED / DENIED_EXCLUDED); the third mismatch refile is refused |
| hash | `test_hash_binds_key_record_evidence_and_window`, `test_verify_rederives_all_of_it`, `test_forged_leader_with_other_record_is_refused` | changing the key, one TVL point, one record field, the binding or the evidence changes the hash; `verify_claim` catches tampering with each stored field and a re-anchored window |

Two earlier behaviours changed on purpose, and their tests were updated:
- The canonical backdating tests now assert **refusal at filing** rather than a `REJECTED_BACKDATED` verdict.
- Another protocol's article is now EVIDENCE_MISMATCH rather than INCONCLUSIVE.

## On-chain proof (demo instance `0x0DF0bCF182151B248A8d5ac8c4b2d48f2127355C`)

Probed first:
- `api.llama.fi/hacks` has both Curve DEX records under `defillamaId` 3: 2022-08-09 "Frontend & Infrastructure / DNS Hijack" and 2023-07-30 "Reentrancy / Vyper Compiler Bug".
- Both rekt.news articles are readable by plain GET from the allowlist. Each carries one date, a day after its own incident.

Setup:
- One Curve pool, collateral 100%, 10% deductible, 7-day wait.
- Five 0.5 GEN covers, each running 2022-07-31 05:24 → 2023-07-31 05:24 UTC (waiting ends 2022-08-07).
- `check_incident` accepted both keys on this cover.

| # | evidence | record (key) | outcome | event | binding | severity | judge tx |
|---|---|---|---|---|---|---|---|
| 1 | Vyper (rekt.news/curve-vyper-rekt) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG` | SAME (model) | BOUND 2023-07-31 | bucket 2, 4952 bps (Vyper window); gross 0.225 GEN | `0xa790c297f2a00ca8455a57a67f186314a2539d7d0c3f7c1648037e53158be974` |
| 2 | Vyper | `3:2022-08-09` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2023-07-31 | window anchored on 2022-08-09 (148 bps), not used | `0xf68f42dcd00d03bc4b5733734dccf11053ec9e5abdff4d7106cd8311480fc8be` |
| 3 | DNS (rekt.news/curve-finance-rekt) | `3:2023-07-30` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2022-08-10 | window anchored on 2023-07-30, not used | `0x4933d14e83df225024c2e69dc7c6aa2e1bc0c155c54d6c5ffed2a7bef73650de` |
| 4 | DNS | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK` | SAME (model) | BOUND 2022-08-10 | bucket 0, 148 bps (DNS window) | `0x4cec88e87eb3dd56dde9ba9ee6799b75052498d4973f190e3d1f198a48e07b3d` |
| 5 | DNS, then refiled with Vyper | `3:2023-07-30` | EVIDENCE_MISMATCH → refile → **APPROVED → paid** | DIFFERENT → SAME | UNBOUND → BOUND | bucket 2, 4952 bps | mismatch `0x4c20224aaabf591d6177e152c8ce5316ca09ae26bbf74dfd6da1bd5414e407d0`, refile `0xae9aee3959aa31ddacd71c08597619aa4b04fd5cb22cd04655a87cee792d79ea`, judge `0xeeaaffb0a33bd08080765cdc0c84a52ae63b92e1aa52428878f971fd2309dbf2` |

Claims 1 and 5 carry the same content hash `7b244fb5a5ef1dbd`: same key, same evidence, same record, same TVL window.

Claim 2's hash `e4db574b4f52ad5e` and claim 3's `b6bc02b93277364b` differ from it and from each other; claim 3 shares its hash with claim 5's first (mismatched) judgement.

**Canonical, backdating.** A cover bought on 2026-09-29, with a claim keyed to Euler's `1183:2023-03-13`, is refused at filing ("predates this cover's start plus its waiting period"), with no fetch and no model. The cover keeps its one claim: tx `0x7eef0f81ccdca5ff9258709dc831077774d2f997fddda7c0f18569f138547d07`.

**Settlement.**
- Claims 1 and 5 share one incident, so they share one settlement batch. `finalize_incident` tx: `0xf560cdb9ee58d6aba2c7c334acff3d1513982855c9608b8fdbb74c3a340af266`.
- Each was credited 0.225 GEN: 0.5 GEN × 50% × (1 − 10%).
- Withdrawals: buyer2 `0x56cc0fab47aa4c0ff666ca0cbcfba64206553d7ef0cdd4db20f92b44eb62448f`, buyer6 `0x8b6ea2654b354f4428b1ee04b9d78d3f1eb9fb2a9d97301813c875801cdffda5`.
- Claims 2 and 3 have gross 0 and no batch. Their covers released to the underwriter after the claim window (`0xf1b08fef862bb16f95210c30df645114c347fc2e178d4a60592c78925532fcac`, `0x179fca50f02b243148426bf4972cef5cf6e2719d9440bce97e4f64acdab2d67a`).

**All reseeded scenarios pass, read back from chain state** by `node test/collect.mjs` ([docs/EVIDENCE.md](docs/EVIDENCE.md), 17/17):
- the five multi-incident claims
- Euler COVERED at bucket 4, and the contest UPHELD
- Multichain EXCLUDED (bound through the yearless "July 7th")
- INCONCLUSIVE homepage (no model call)
- PRO-RATA (both scaled, batch `0x4794e858…`)
- EXPIRED
- STALLED (settled and judged while paused)
- canonical BACKDATED (refused at filing)
- waiting-period gate (`0x0fcbed7b…`)
- registry attest
- ledger identity
- demo drained

**Drained to zero.** Every demo cover was released, all five pools were closed and every balance was withdrawn (`node test/drain_demo.mjs`, run twice because the Tornado cover had to wait out claim #11's contest window). The demo instance's books read **balance 0 = held 0 + payable 0 wei, locked 0** ([docs/drain-evidence.json](docs/drain-evidence.json) holds the second run; the first run's releases and closes are in the tx list below).
- First run:
  - release `0xc404e2f5…`, `0xf1b08fef…`, `0x179fca50…`, `0x404c87af…`, `0xf25aaca2…`
  - close pools 1–4 `0xa8e4261f…`, `0x90972334…`, `0x1e08a44d…`, `0x79b7def3…`
  - withdraw uw1/uw2/uw3 `0x039aaf93…`, `0x17601c96…`, `0xa2829651…`
- Second run: close pool 5 `0xdcb45120…`, withdraw uw3 `0xf6e635c5…`.

As on the previous deployment, Studio Dev finalized every `claim_payout` without executing the value transfer. `get_stats` publishes `undelivered_wei = 11012566666666666673` rather than hiding it.

**Audit.** `python3 tools/audit.py` gives **52 PASS / 0 FAIL** ([docs/AUDIT.md](docs/AUDIT.md)). New checks:
- no "latest row" selection: `_pick_incident` is absent, `_select_incident` uses no ordering comparison, and `_llama_row` selects only through it
- the content hash binds incident key + digest + page binding + record + TVL window points, and `verify_claim` re-derives it
- steward tests a–g pass
- README addresses equal `deployments.json`

## New addresses (GenLayer Studio Dev, chain 61997)

| contract | address | deploy tx |
|---|---|---|
| `CoverClaim` (canonical) | `0x64DA264e7cBba10E0aA36Dfb0ed12aDB8c9EBDD3` | `0xf883264186db18aeefe95747728022b5874278c1fd371dea88ab056892df89d2` |
| `CoverClaimDemo` (DEMO, `demo_backdate_days = 1521`) | `0x0DF0bCF182151B248A8d5ac8c4b2d48f2127355C` | `0x2755bd6772c5b5d0e2359edb334cba4f4985d1ab95137178dcf2f24803e31f2a` |
| `CoverRegistry` | `0x10f4E23623417098f7d730aB98E576dC9A5bEE70` | `0xe7b365775d4ee70281ccc6b92d76027fee290ae88665c13da271e80155b89860` |

- CoverClaim source: 213,049 bytes, sha256 `ffb55c47e95828df…`, identical on chain for both instances (`node test/verify_onchain.mjs`).
- Previous deployments: `docs/previous-deployment/1-first/`, `docs/previous-deployment/2-waitgate/`.
- App: https://coverclaim.vercel.app. It reads the addresses from Vercel production env vars, and the live bundle contains only these addresses.
