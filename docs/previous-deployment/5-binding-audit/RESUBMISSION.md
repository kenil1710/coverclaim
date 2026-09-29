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

## Confirmation: only matched pages reach the classifier

Asked after the fix: with several evidence pages of which only some match the selected record, does the classifier see only the matched pages?

**Before this confirmation: partly.**
- A page dated to another event was already excluded.
- A page with **no date at all** was still read beside a matched page. By the definition (protocol named + date within ±3 days) such a page is unmatched.

**Fixed.** The digest is now built from BOUND pages alone. That digest is the only evidence text in the prompt, and it also sets the bracket, the strength and the hash (`contracts/parts/p3_judge.py`, `_reading`):

```python
    for i in range(len(pages)):
        p = pages[i]
        st = states[i]                    # from _bind: BOUND / UNDATED / UNBOUND / UNREAD
        ...
        if st == PAGE_UNDATED:
            undated_text.append(str(p.get("digest", "")))   # gate only, never the model
        if st != PAGE_BOUND:
            continue                      # unmatched: no sentence, indicator or source
        dg = str(p.get("digest", ""))
        if dg:
            fresh.append(dg)
    ...
    digest = _short(fresh_text, MAX_DIGEST)   # -> _prompt: "<<<EVIDENCE\n" + digest + "\nEVIDENCE>>>"
```

Undated text is used for exactly one decision, and never reaches the model: whether an evidence set with no bound page is EVIDENCE_MISMATCH (UNCLEAR, it names a risk) or INCONCLUSIVE (it names none).

`event_match` is decided by the model over the matched pages only, in the same call as the classification. Anything but SAME is EVIDENCE_MISMATCH.

**Tests** (`TestOneEventBindsEverything`):
- `test_mixed_dns_record_classifies_from_dns_page_only`: record DNS 2022, evidence [DNS, Vyper] → EXCLUDED, no payout. The model's prompt is byte-identical to the prompt for the DNS page alone and contains no Vyper text.
- `test_mixed_vyper_record_classifies_from_vyper_page_only`: record Vyper 2023, evidence [Vyper, DNS] → COVERED at bucket 2. The prompt is byte-identical to the Vyper-only prompt and contains no DNS text.
- `test_undated_page_never_reaches_the_classifier`: an undated allowlisted page's text is in no prompt, digest or bracket.
- `test_classifier_input_is_exactly_the_bound_digests`: the digest equals the bound pages' digests, and it is what the prompt carries.

**On chain:** claims 6 and 7 below. Each claim's stored, hashed digest contains no text from the unmatched article.

## Binding audit (items 2–6)

Line numbers are in the deployed `contracts/CoverClaim.py`. Tests are in `test/test_logic.py`.

| # | item | before the audit | code | tests |
|---|---|---|---|---|
| 2 | canonical incident identity | **FAIL**: settlement windows were keyed by `pool:incident_day`, so two records of one protocol on one day would share a batch | `_incident_id` L1934: the selected record's `id:day:normalised name`. It is compared exactly (`EXACT_STR`), stored on the claim and the batch, keys the batch (`_join_batch` L3556), and is what the content hash covers | `TestBindingAudit.test_2_differently_written_keys_group_and_scale_together`: `1183:2023-03-13` and `…:Euler V1` → one incident, one batch, same hash, scaled pro-rata. `test_2_two_records_on_one_day_are_two_incidents` |
| 3 | contest binding | **PASS**: already bound | allowlist L3778; the contest has no key parameter (`contest(claim_id, evidence_urls, statement)` L3728) and its facts use the claim's stored key (L3292); only BOUND pages are read (L1765), so pages dated elsewhere and undated pages add nothing; `event_match` is asked again | `test_3_contest_page_dated_elsewhere_is_not_read`, `test_3_contest_undated_page_is_not_read`, `test_3_contest_bound_page_rejudged_with_event_match` (DIFFERENT → EVIDENCE_MISMATCH), `test_3_contest_allowlist_applies`, `test_3_contest_cannot_change_the_incident_key` |
| 4 | refile binding | **PASS for the question, FAIL for leftover state**: the new judgement was already asked from scratch, but the rejected attempt's batch membership and resolved-contest state carried over | refile L3517: `_leave_batch`, gross and table reset, a resolved contest cleared; the key re-checked by `_key_check`; evidence by the allowlist; limit L3485 | `test_4_refile_reuses_nothing_from_the_rejected_attempt`, `test_4_refile_rechecks_the_key_from_scratch`, `test_4_refile_limit` |
| 5 | one payout per cover | **FAIL**, and a real one: approve → contest flip → refile → re-approve inside one open window appended the claim to the same batch twice, and `finalize_incident` paid it twice. The test showed "2 != 1" and a broken ledger before the fix | listed once (L3571); a flip out of APPROVED leaves the batch (L3905, `_leave_batch` L3577); finalize pays each claim once (L3965), only if still in THIS batch and its cover is ACTIVE (L3974) | `test_5_flip_refile_reapprove_pays_once`, `test_5_paid_cover_is_never_paid_again`, `test_5_new_verdict_after_refile_can_be_contested`, `test_5_payouts_never_exceed_locked_capacity_random` (12 random pools, mixed keys, random flips: Σ payouts ≤ Σ locks, one payout per cover) |
| 6 | any other binding | two found (below); everything else PASS | see below | `TestBindingAudit6` |

**Item 6, everything a stored result depends on:**

| stored result | depends on | bound to | status |
|---|---|---|---|
| incident date, record fields | the one hacks row the key names | record | PASS |
| severity (TVL window) | `/protocol/<slug>`, window anchored on the record's day; `id_match` requires the TVL document's id to be the pool's id (L1819) | record + pool | PASS (`test_severity_window_follows_the_record_not_the_filing_time`) |
| classification, peril, exclusion, strength | bound pages only; bracket ∩ the pool's frozen perils and exclusions | record + policy | PASS |
| outcome and gross (`_outcome` L3692) | cover start, end and amount; pool waiting period, table and deductible | cover + policy | PASS (`test_outcome_inputs_are_this_cover_and_this_pool`) |
| settlement batch, pro-rata pool | canonical incident id, the locks of those covers | record + covers | **was FAIL** (item 2), fixed |
| payout | the claim's membership in the batch, the cover's status | cover | **was FAIL** (item 5), fixed |
| a page's evidence date on `web.archive.org` | text of the page | page | PASS: the Wayback "FILE ARCHIVED ON" footer is an HTML comment and is dropped. Hardened: a toolbar block, if one is served inside the page, is cut out (L1477) (`test_wayback_metadata_never_dates_a_page`) |
| **CoverRegistry attestation** (`get_active_cover` / `is_covered`) | **the protocol string matched against the pool's free-text display name** as well as its slug | — | **FAIL**, fixed: matched only by the pool's frozen DeFi Llama slug, id, or `slug:id` (L4661). A pool named "Aave" over Euler's slug no longer attests Aave cover (`test_registry_ignores_display_names`, registry tests) |
| contest re-reading | the stored judged digest, and the record and TVL re-read under the claim's same key | record | PASS. A contest re-reads DeFi Llama live, so if DeFi Llama edits or removes the record afterwards, a contest can come out INCONCLUSIVE (refileable). That is a re-reading of the same record, never a different one |
| pool slug vs id | both frozen at creation, but no web read is possible there | policy | residual, documented: a pool whose slug and id name different protocols can never pay (`id_match` pins every claim INCONCLUSIVE). `slug:id` lets an integrator require both |

## Tests (offline, `python3 test/test_logic.py`, 650 passing)

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

## On-chain proof (demo instance `0x02A81134c4aCc85386Ad092Bcd2EB55809df15a9`)

Probed first:
- `api.llama.fi/hacks` has both Curve DEX records under `defillamaId` 3: 2022-08-09 "Frontend & Infrastructure / DNS Hijack" and 2023-07-30 "Reentrancy / Vyper Compiler Bug".
- Both rekt.news articles are readable by plain GET from the allowlist. Each carries one date, a day after its own incident.

Setup:
- One Curve pool, collateral 100%, 10% deductible, 7-day wait.
- Seven 0.5 GEN covers, each running 2022-07-31 05:24 → 2023-07-31 05:24 UTC (waiting ends 2022-08-07).
- `check_incident` accepted both keys on this cover.

| # | evidence | record (key) | outcome | event | binding | severity | judge tx |
|---|---|---|---|---|---|---|---|
| 1 | Vyper (rekt.news/curve-vyper-rekt) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG` | SAME (model) | BOUND 2023-07-31 | bucket 2, 4952 bps (Vyper window); gross 0.225 GEN | `0xba9299bfa20d5641228e2c15384127f5ea376cfc101163070b712c428dea693c` |
| 2 | Vyper | `3:2022-08-09` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2023-07-31 | window anchored on 2022-08-09 (148 bps), not used | `0x99d79d65309427de6a655f7451494088a8287b8d88c3243ee698f3377b73d28f` |
| 3 | DNS (rekt.news/curve-finance-rekt) | `3:2023-07-30` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2022-08-10 | window anchored on 2023-07-30, not used | `0x85379cae7696b56bb2cb7a3d6dec31c78f90a59b1d602e5e6769f82ced502ddb` |
| 4 | DNS | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK` | SAME (model) | BOUND 2022-08-10 | bucket 0, 148 bps (DNS window) | `0xb9682a340416807cf012194adfdfacb3e8e5ed8feab53c3aca2d1a0b4153b437` |
| 5 | DNS, then refiled with Vyper | `3:2023-07-30` | EVIDENCE_MISMATCH → refile → **APPROVED → paid** | DIFFERENT → SAME | UNBOUND → BOUND | bucket 2, 4952 bps | mismatch `0xf36b6caa57b80dc2e5e23c52381f3c567c7e46cd7f99f27b764a14f40938336e`, refile `0xe0e7538367a66f17b58b648d3e2a66e3e16d01a41e309a487bb34bc9aefb5b44`, judge `0xa841ac4034cb3d6570b3a8868126edffd26c6ef85759686c8ff934eda385a60c` |
| 6 | [DNS, Vyper] (mixed) | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK`, no payout, classified from the DNS page only | SAME (model) | DNS BOUND 2022-08-10; Vyper UNBOUND 2023-07-31 | bucket 0 (DNS window) | `0x718b1a7cb6cbfdee948e7ec14fc560d2de7ce00103db1a16d5ab627c66e29de4` |
| 7 | [Vyper, DNS] (mixed) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG`, classified from the Vyper page only | SAME (model) | Vyper BOUND 2023-07-31; DNS UNBOUND 2022-08-10 | bucket 2, 4952 bps | `0x9095fc70fe6fe8c0f270c0cb1beb78dc96e7751eee7a4187e8d8acd3a4e34f14` |

Claims 1 and 5 carry the same content hash `7b244fb5a5ef1dbd`: same key, same evidence, same record, same TVL window.

Claim 2's hash `e4db574b4f52ad5e` and claim 3's `b6bc02b93277364b` differ from it and from each other; claim 3 shares its hash with claim 5's first (mismatched) judgement.

**Canonical, backdating.** A cover bought on 2026-09-29, with a claim keyed to Euler's `1183:2023-03-13`, is refused at filing ("predates this cover's start plus its waiting period"), with no fetch and no model. The cover keeps its one claim: tx `0xffae8e905755fbf5be114f48099f4ddb4c409a74d0e2190f2483ab11eae651bf`.

**Settlement.**
- Claims 1, 5 and 7 share one canonical incident (`3:2023-07-30:curve dex`), so they are paid together in batch 1 (`0x981613fe73090ae206c533839de9ba16573d449dd3f122cffe04a23083a04d78`). Each was credited 0.225 GEN: 0.5 GEN × 50% × (1 − 10%).
- Claims 2, 3 and 6 have gross 0 and no batch. Their covers released to the underwriter after the claim window.
- **Item 2 on chain:** the two pro-rata Euler claims were keyed `1183:2023-03-13` and `1183:2023-03-13:Euler V1`. Both resolved to incident `1183:2023-03-13:euler v1` and settled in one batch, scaled at factor 5555 bps (`0x78ee0948948d8f3b8494890b6a19249876b7a87272ddb7d42845ec24051b1277`).

**All reseeded scenarios pass, read back from chain state** by `node test/collect.mjs` ([docs/EVIDENCE.md](docs/EVIDENCE.md), **19/19**):
- the seven Curve claims
- Euler COVERED at bucket 4, and the contest UPHELD
- Multichain EXCLUDED
- INCONCLUSIVE homepage (no model call)
- PRO-RATA, keyed two ways, one batch
- EXPIRED
- STALLED (settled and judged while paused)
- canonical BACKDATED, refused at filing
- waiting-period gate
- registry attest (queried by slug `curve-dex`)
- ledger identity
- demo drained

The seed script's buy-cooldown bug from the previous deployment is fixed. This run needed no re-run.

**Drained to zero.** In one pass, every demo cover was released, all five pools were closed and every balance was withdrawn ([docs/drain-evidence.json](docs/drain-evidence.json)). The books read **balance 0 = held 0 + payable 0 wei, locked 0**. Studio Dev again finalized every `claim_payout` without executing the transfer: `undelivered_wei = 12134233333333333341`, published by `get_stats`.

**Audit.** `python3 tools/audit.py` gives **57 PASS / 0 FAIL** ([docs/AUDIT.md](docs/AUDIT.md)). It includes:
- no "latest row" selection
- the hash binds canonical incident + evidence + record + TVL window
- canonical identity keys the batches; one listing per claim; finalize pays once, on a live cover
- contest and refile bindings
- registry matches frozen DeFi Llama identity only
- README addresses equal `deployments.json`

## New addresses (GenLayer Studio Dev, chain 61997)

| contract | address | deploy tx |
|---|---|---|
| `CoverClaim` (canonical) | `0x8a7e766b9221fA55A5d6d868f6ed0Adaa16a93D3` | `0xb6d4fd74e413509d803232a8bb4684b736a4c2aaaa08613ab707185795a3e06d` |
| `CoverClaimDemo` (DEMO, `demo_backdate_days = 1521`) | `0x02A81134c4aCc85386Ad092Bcd2EB55809df15a9` | `0x755c47837df2c77ff169725538aa42711f345bfd6db3967de266b08d5b27aa0a` |
| `CoverRegistry` | `0x325A84972a8D86D94bFb4301CA04312B15Cf2F99` | `0x416a275c3b89a1ade41b1b1aa75ac69da593b1fbacef96f772606d6706d9d5bb` |

- CoverClaim source: 218,088 bytes, sha256 `3e8593642bad764f…`, identical on chain for both instances (`node test/verify_onchain.mjs`).
- Previous deployments: `docs/previous-deployment/1-first/`, `docs/previous-deployment/2-waitgate/`, `docs/previous-deployment/3-one-event/` (before the classifier-input confirmation), `docs/previous-deployment/4-matched-pages/` (before the binding audit).
- App: https://coverclaim.vercel.app. It reads the addresses from Vercel production env vars, and the live bundle contains only these addresses.
