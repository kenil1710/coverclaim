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

## Protocol-domain binding and pool verification

Lens: nothing a single party controls may decide money. Line numbers are in the deployed `contracts/CoverClaim.py`.

| # | item | before | fix (code) | tests |
|---|---|---|---|---|
| 1 | **Protocol domain binding** | **FAIL.** `create_pool` put up to 3 underwriter-chosen "official domains" straight onto the evidence allowlist. An underwriter owning `euler-postmortem.xyz` could publish a "post-mortem" there and contest a COVERED claim with it | The underwriter may only *declare* one domain (`MAX_OFFICIAL_DOMAINS = 1`, L333). A new pool's allowlist is the base only (L3196). The only other domain ever added is `pool.protocol_domain` (`_allowlist`, L3023), written once by `verify_pool` (L3094) from the website DeFi Llama lists, with `www.` stripped (`_website_domain`, L1360). It is none if DeFi Llama lists none, or lists a shared publishing host (`SHARED_HOSTS`, L337: medium.com, github.com, x.com, …). A declared domain that isn't DeFi Llama's website fails the pool (L1419). Filing, refiling, contesting and `check_evidence` all read `self._allowlist(pool)` (file_claim L3697, refile_claim L3778, contest L4053, check_evidence L4807), so a contest page on any other domain is refused before GenLayer | `TestPoolVerification`: `test_declared_domain_must_be_defillamas_website`, `test_matching_domain_is_the_only_protocol_domain`, `test_no_website_listed_means_no_protocol_domain`, `test_shared_publishing_host_is_never_a_protocol_domain`, **`test_contest_from_unverified_domain_refused_before_model`** (own domain, look-alike, archive of own domain; and `multichain.org`, which DeFi Llama doesn't list: all refused, model never called, bond returned), `test_allowlist_has_one_source_of_protocol_domain` (AST) |
| 2 | **Pool verification before sale** | **FAIL.** A pool was OPEN at creation, so a pool whose slug, id or name weren't one protocol sold cover that could never pay: `id_match` pins every claim INCONCLUSIVE, and evidence never names a mis-named pool | Pools are created `UNVERIFIED` (L3227). **`verify_pool`** (L3048) is permissionless: one consensus round (`_verify_consensus` L3032, `_verify_collect` L1731) reads `api.llama.fi/protocol/<slug>`. The verdict is **re-derived** from the agreed raw fields (`_verify_verdict` L1377), and validators refuse a leader whose verdict its own raw fields don't produce (`_verify_agrees` L1767). VERIFIED requires: the record exists; its id is the pool's id (L1405); the pool's name names it (same first word, word-aligned: "Euler" ↔ "Euler V1"); a declared domain is its website. A 5xx is RETRY, and nothing changes. `buy_cover` sells only VERIFIED pools (L3373, `_not_selling` L2531). FAILED pools refuse capacity and cover; `close_pool` works on any non-closed pool and returns the capital (L3323) | **`test_buy_before_verification_refused`** (premium refunded, no cover), **`test_mismatched_slug_id_fails_and_cannot_sell`**, `test_unknown_slug_fails`, `test_wrong_protocol_name_fails`, **`test_verified_pool_works_as_before`**, **`test_nobody_can_pay_a_premium_into_a_pool_that_can_never_pay`** (6 bad pool shapes, before and after verification: no premium held, no cover, closes), `test_transient_source_is_retry_and_changes_nothing`, `test_verification_works_while_paused`, `test_forged_verdict_refused_by_validators`, `test_verification_fields_written_only_by_verify_pool` (AST) |

**Live DeFi Llama records** (2026-09-29, the same document judging already reads):

| slug | id | listed website | protocol domain |
|---|---|---|---|
| euler-v1 | 1183 | `https://www.euler.finance` | `euler.finance` |
| curve-dex | 3 | `https://curve.finance` | `curve.finance` |
| multichain | 591 | none | none, so only rekt.news counts |
| tornado-cash | 148 | an IPNS gateway | that gateway host, so the old `tornado.cash` declaration would fail |

On chain, `verify_pool` took 17 s for Euler (9 MB record) and 40–54 s for Curve (69 MB record).

**On chain (demo):**

| scenario | result | tx |
|---|---|---|
| Euler pool (declared `euler.finance`) | VERIFIED; allowlist `rekt.news, web.archive.org, euler.finance` | `0xa326ac96b5b1519921c15fcabaa6b81845295edc137d3b7d07ee418245052377` |
| Curve pool (declared `curve.finance`, 69 MB record) | VERIFIED; `curve.finance` | `0x6d111909110407cc438c40b2a8299e74f195d3caca787b4028fc12528b496a03` |
| Multichain pool (no declaration; DeFi Llama lists none) | VERIFIED with **no** protocol domain: rekt.news only | `0xd17a6eaf8fe703433a3c5b5da13f2518d059fdb1cf587b688dc2c7290ea62d83` |
| Euler slug + id, declaring `euler-postmortem.xyz` | **FAILED_VERIFICATION**: "declared domain euler-postmortem.xyz is not the website DeFi Llama lists for Euler V1"; a premium sent to it came straight back; closed with the capital returned | verify `0x74e2aa945dc30c32c69ae9236ff3b43f448288d7769c6c11754adaed754d259e`, buy refused `0x637b5fc275870c1a4f979ad18f0741cf95df70ffe977e2f75fa8d503572c12c0`, close `0xf4dd0b93cdd9828ae57b27d4c4f410441928af599adf299a687206a856ff8775` |
| slug `curve-dex` + id 1183 | **FAILED_VERIFICATION**: "slug curve-dex is DeFi Llama id 3, not 1183"; buy refused; closed | verify `0x1029699762bacb6bfaa701b38b48177e1e22d7d342ad8d47460be038cb6f8a07`, buy refused `0x31f4c63db9a64d0ed82d8a4b7382f49c36438aa8caa8cecb6da9919078237404`, close `0x3fcc8c6f12012ca16c46cac62e19dcca7351d330edc9c4acdf04534b52006244` |
| underwriter contests the COVERED Euler claim with `euler-postmortem.xyz/official-post-mortem` | **refused before GenLayer** ("not on this pool's frozen evidence allowlist"); bond refunded; the verdict stands | `0x496b7b1c30d963739e5d95baac30d8ff9d2d57296d9a389ef6257955f934aa8f` |
| buyer contests the Multichain denial with `multichain.org` (not listed by DeFi Llama) | **refused before GenLayer**; bond refunded | `0x9fe3aaf6ac25acd5fc1dac6124a9f773e6c2118cbc43af4a1122276037f893be` |
| every cover sold on the demo instance | all on VERIFIED pools | collect row "POOL VERIFICATION" |

**Docs checked after the change:**
- README: the policy step now says "verified before sale", the limitations name DeFi Llama's listed website, and the loophole table gains 2b and 2c.
- `docs/ARTICLE.md` (the Medium draft): its "the domains evidence may come from" sentence was no longer true and is rewritten.
- `contracts/NOTES.md` §2b.
- The app: underwriter form, pool page (Verify button; FAILED banner), pools list, docs page and landing page.

## Binding audit (items 2–6)

Line numbers are in the deployed `contracts/CoverClaim.py`. Tests are in `test/test_logic.py`.

| # | item | before the audit | code | tests |
|---|---|---|---|---|
| 2 | canonical incident identity | **FAIL**: settlement windows were keyed by `pool:incident_day`, so two records of one protocol on one day would share a batch | `_incident_id` L2092: the selected record's `id:day:normalised name`. It is compared exactly (`EXACT_STR`), stored on the claim and the batch, keys the batch (`_join_batch` L3831), and is what the content hash covers | `TestBindingAudit.test_2_differently_written_keys_group_and_scale_together`: `1183:2023-03-13` and `…:Euler V1` → one incident, one batch, same hash, scaled pro-rata. `test_2_two_records_on_one_day_are_two_incidents` |
| 3 | contest binding | **PASS**: already bound | allowlist L4053; the contest has no key parameter (`contest(claim_id, evidence_urls, statement)` L4003) and its facts use the claim's stored key (L3567); only BOUND pages are read (L1923), so pages dated elsewhere and undated pages add nothing; `event_match` is asked again | `test_3_contest_page_dated_elsewhere_is_not_read`, `test_3_contest_undated_page_is_not_read`, `test_3_contest_bound_page_rejudged_with_event_match` (DIFFERENT → EVIDENCE_MISMATCH), `test_3_contest_allowlist_applies`, `test_3_contest_cannot_change_the_incident_key` |
| 4 | refile binding | **PASS for the question, FAIL for leftover state**: the new judgement was already asked from scratch, but the rejected attempt's batch membership and resolved-contest state carried over | refile L3792: `_leave_batch`, gross and table reset, a resolved contest cleared; the key re-checked by `_key_check`; evidence by the allowlist; limit L3760 | `test_4_refile_reuses_nothing_from_the_rejected_attempt`, `test_4_refile_rechecks_the_key_from_scratch`, `test_4_refile_limit` |
| 5 | one payout per cover | **FAIL**, and a real one: approve → contest flip → refile → re-approve inside one open window appended the claim to the same batch twice, and `finalize_incident` paid it twice. The test showed "2 != 1" and a broken ledger before the fix | listed once (L3846); a flip out of APPROVED leaves the batch (L4180, `_leave_batch` L3852); finalize pays each claim once (L4240), only if still in THIS batch and its cover is ACTIVE (L4249) | `test_5_flip_refile_reapprove_pays_once`, `test_5_paid_cover_is_never_paid_again`, `test_5_new_verdict_after_refile_can_be_contested`, `test_5_payouts_never_exceed_locked_capacity_random` (12 random pools, mixed keys, random flips: Σ payouts ≤ Σ locks, one payout per cover) |
| 6 | any other binding | two found (below); everything else PASS | see below | `TestBindingAudit6` |

**Item 6, everything a stored result depends on:**

| stored result | depends on | bound to | status |
|---|---|---|---|
| incident date, record fields | the one hacks row the key names | record | PASS |
| severity (TVL window) | `/protocol/<slug>`, window anchored on the record's day; `id_match` requires the TVL document's id to be the pool's id (L1977) | record + pool | PASS (`test_severity_window_follows_the_record_not_the_filing_time`) |
| classification, peril, exclusion, strength | bound pages only; bracket ∩ the pool's frozen perils and exclusions | record + policy | PASS |
| outcome and gross (`_outcome` L3967) | cover start, end and amount; pool waiting period, table and deductible | cover + policy | PASS (`test_outcome_inputs_are_this_cover_and_this_pool`) |
| settlement batch, pro-rata pool | canonical incident id, the locks of those covers | record + covers | **was FAIL** (item 2), fixed |
| payout | the claim's membership in the batch, the cover's status | cover | **was FAIL** (item 5), fixed |
| a page's evidence date on `web.archive.org` | text of the page | page | PASS: the Wayback "FILE ARCHIVED ON" footer is an HTML comment and is dropped. Hardened: a toolbar block, if one is served inside the page, is cut out (L1579) (`test_wayback_metadata_never_dates_a_page`) |
| **CoverRegistry attestation** (`get_active_cover` / `is_covered`) | **the protocol string matched against the pool's free-text display name** as well as its slug | — | **FAIL**, fixed: matched only by the pool's frozen DeFi Llama slug, id, or `slug:id` (L4947). A pool named "Aave" over Euler's slug no longer attests Aave cover (`test_registry_ignores_display_names`, registry tests) |
| contest re-reading | the stored judged digest, and the record and TVL re-read under the claim's same key | record | PASS. A contest re-reads DeFi Llama live, so if DeFi Llama edits or removes the record afterwards, a contest can come out INCONCLUSIVE (refileable). That is a re-reading of the same record, never a different one |
| pool slug vs id | both frozen at creation, but no web read is possible there | policy | residual, documented: a pool whose slug and id name different protocols can never pay (`id_match` pins every claim INCONCLUSIVE). `slug:id` lets an integrator require both |

## Tests (offline, `python3 test/test_logic.py`, 667 passing)

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

## On-chain proof (demo instance `0xC70DB65CaF6aa8a915b032FBFeBC6600A195F8e7`)

Probed first:
- `api.llama.fi/hacks` has both Curve DEX records under `defillamaId` 3: 2022-08-09 "Frontend & Infrastructure / DNS Hijack" and 2023-07-30 "Reentrancy / Vyper Compiler Bug".
- Both rekt.news articles are readable by plain GET from the allowlist. Each carries one date, a day after its own incident.

Setup:
- One Curve pool, collateral 100%, 10% deductible, 7-day wait.
- Seven 0.5 GEN covers, each running 2022-07-31 05:24 → 2023-07-31 05:24 UTC (waiting ends 2022-08-07).
- `check_incident` accepted both keys on this cover.

| # | evidence | record (key) | outcome | event | binding | severity | judge tx |
|---|---|---|---|---|---|---|---|
| 1 | Vyper (rekt.news/curve-vyper-rekt) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG` | SAME (model) | BOUND 2023-07-31 | bucket 2, 4952 bps (Vyper window); gross 0.225 GEN | `0xa6b5e662c3a2d237be22a20b7b273ff76e3cf102417d6d3629e020d7ef190cdf` |
| 2 | Vyper | `3:2022-08-09` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2023-07-31 | window anchored on 2022-08-09 (148 bps), not used | `0x80a2b3798b4543f060530b5e5b2c9e8ebed3c6a0a7c31623dac46dea86ac98d5` |
| 3 | DNS (rekt.news/curve-finance-rekt) | `3:2023-07-30` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2022-08-10 | window anchored on 2023-07-30, not used | `0x92909b926bde95e10f89c0f51d558a3e0a827d74997a7de5abfd7ba901cfabae` |
| 4 | DNS | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK` | SAME (model) | BOUND 2022-08-10 | bucket 0, 148 bps (DNS window) | `0xf4d8dbffab16030debf94a2523adfd8e1fac34b9c19c7a9d6eb7ec6fa0de9851` |
| 5 | DNS, then refiled with Vyper | `3:2023-07-30` | EVIDENCE_MISMATCH → refile → **APPROVED → paid** | DIFFERENT → SAME | UNBOUND → BOUND | bucket 2, 4952 bps | mismatch `0x1735e2b92dd6131a08ae0d6b8708cd7c988cc14acb8e82c016769a65bb840603`, refile `0x6fba177701f5e4e72cd2f3c0b748346fe31880ecf54ffb011680dc8acf8a2b79`, judge `0xadd788bad11607436d3e1af644a34657c6270030bab721b398acabf7e992144a` |
| 6 | [DNS, Vyper] (mixed) | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK`, no payout, classified from the DNS page only | SAME (model) | DNS BOUND 2022-08-10; Vyper UNBOUND 2023-07-31 | bucket 0 (DNS window) | `0xc091466c3ad357936662be01971363e5ac2e3cc4768871284bf66db5dc1c2d04` |
| 7 | [Vyper, DNS] (mixed) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG`, classified from the Vyper page only | SAME (model) | Vyper BOUND 2023-07-31; DNS UNBOUND 2022-08-10 | bucket 2, 4952 bps | `0x1c35eb86c105ebe08c0e691d8e7dd2be6140a2b98522405dc3044588fd9d56de` |

Claims 1 and 5 carry the same content hash `7b244fb5a5ef1dbd`: same key, same evidence, same record, same TVL window.

Claim 2's hash `e4db574b4f52ad5e` and claim 3's `b6bc02b93277364b` differ from it and from each other; claim 3 shares its hash with claim 5's first (mismatched) judgement.

**Canonical, backdating.** A cover bought on 2026-09-29, with a claim keyed to Euler's `1183:2023-03-13`, is refused at filing ("predates this cover's start plus its waiting period"), with no fetch and no model. The cover keeps its one claim: tx `0x8585c4498c3df5fb77284ab868c1967203a8e65440253b1036ac7518b9561ea6`.

**Settlement.**
- Claims 1, 5 and 7 share one canonical incident (`3:2023-07-30:curve dex`) and are paid together in batch 1 (`0xed45b61f9fa20e8e9f6f765f312adb0b5459c2d91600a8349333a05e7c404d55`). Each was credited 0.225 GEN.
- Claims 2, 3 and 6 have gross 0 and no batch.
- The two pro-rata Euler claims were keyed `1183:2023-03-13` and `1183:2023-03-13:Euler V1`. They are one incident in one batch, scaled at factor 5555 bps (`0xc8198ca7d62149216489c8a0f14a781f1e266e64e1b5071d06ed71b4b3fe57ed`).

**All seeded scenarios pass, read back from chain state** by `node test/collect.mjs` ([docs/EVIDENCE.md](docs/EVIDENCE.md), **24/24**):
- the 7-claim Curve proof, including the two mixed-evidence claims
- pool verification: every pool that sold cover was verified; two failing pools could not sell and closed
- the two contests from unverified domains, refused before GenLayer
- one payout per cover (structural: every batch lists each claim once, no cover paid twice, payouts ≤ locked capacity)
- Euler COVERED and CONTESTED (UPHELD)
- Multichain EXCLUDED
- INCONCLUSIVE
- PRO-RATA
- EXPIRED
- STALLED
- canonical BACKDATED (refused at filing)
- the waiting-period gate
- the registry attest
- ledger identity
- demo drained

The double-payout regression (approve → contest flip → refile → re-approve) cannot be forced on chain: the flip needs validators to change their reading. It is proven offline by `TestBindingAudit.test_5_*`. On chain it is checked structurally in every batch.

**Drained to zero.** In one pass: every demo cover released, all seven pools closed (two of them never verified), every balance withdrawn. The books read **balance 0 = held 0 + payable 0 wei, locked 0** ([docs/drain-evidence.json](docs/drain-evidence.json)). Studio Dev again finalized every `claim_payout` without executing the transfer: `undelivered_wei = 14336233333333333341`, published by `get_stats`.

**Audit.** `python3 tools/audit.py` gives **64 PASS / 0 FAIL** ([docs/AUDIT.md](docs/AUDIT.md)). It includes the new checks:
- protocol-domain binding (the only non-base domain comes from `verify_pool`)
- verified before sale
- canonical incident identity, and one payout per cover
- contest and refile bindings
- registry identity
- no "latest row" selection
- hash binding
- README addresses equal `deployments.json`

**One more bug, found and fixed during this round.** On the first deployment of pool verification (archived in `docs/previous-deployment/6-verification-view-bug/`), the collector flagged pools #6 and #7: `get_pool` showed `verified: true` for a pool that had **failed** verification and was then closed. The flag was derived from the status.
- It is now read from a stored `verify_verdict`, written only by `verify_pool`, with test `test_failed_then_closed_pool_never_reads_verified`.
- No money path used the flag: `buy_cover` checks the live OPEN status.
- Redeployed and reseeded.

## New addresses (GenLayer Studio Dev, chain 61997)

| contract | address | deploy tx |
|---|---|---|
| `CoverClaim` (canonical) | `0x8a698aA7eF620260B192b89C141A1dcE168Dfd80` | `0x8f0fbf8c4466f13182ad35d9aa36c38579d28c8d2ccb4a89e6260687e1cbba98` |
| `CoverClaimDemo` (DEMO, `demo_backdate_days = 1521`) | `0xC70DB65CaF6aa8a915b032FBFeBC6600A195F8e7` | `0x8668ef8e3d428aed20ed43e1a697d1e0559db791c9c66c57896284f1961db257` |
| `CoverRegistry` | `0x8618B4CC15069B056b5b35AF37B029b27a152cf7` | `0xe29767a23946ae0dbc6c3a7072a7fa54bc2f4ce0e19c5da30d0c59212751f1e2` |

- CoverClaim source: 232,855 bytes, sha256 `49b845736f93d48a…`, identical on chain for both instances (`node test/verify_onchain.mjs`).
- Previous deployments: `docs/previous-deployment/1-first/`, `docs/previous-deployment/2-waitgate/`, `docs/previous-deployment/3-one-event/` (before the classifier-input confirmation), `docs/previous-deployment/4-matched-pages/` (before the binding audit), `5-binding-audit/` (before domain binding and pool verification), `6-verification-view-bug/`.
- App: https://coverclaim.vercel.app. It reads the addresses from Vercel production env vars, and the live bundle contains only these addresses.
