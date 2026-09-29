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

## Independent review: four findings, each with a failing test (`test/test_attacks.py`)

All four were real. `python3 test/test_attacks.py` now passes 21/21: the reviewer's 7 tests plus 14 for the fixes. The file stays in the suite, and the audit runs it.

| # | finding | fix (`contracts/CoverClaim.py`) | tests |
|---|---|---|---|
| 1 | **A pool name no evidence contains.** Verification accepted "Curve DEX" / "Euler V1" (DeFi Llama's own names), but binding needed the pool name word-for-word, and articles say "Curve Finance". | `_core_name` drops trailing generic words (DEX, V1–V5, Finance, Protocol, Labs, Exchange) from DeFi Llama's name. The pool name must reduce to the same core (`_verify_verdict`). The core is stored once as `pool.core_name` by `verify_pool`, and the judging facts use it (`_claim_facts`), so evidence is matched on the core name whatever the pool is called | Finding1 (3 reviewer tests); `Fix1_CoreName`: "Curve", "Curve DEX", "Curve Finance", "curve", "CURVE  DEX" give byte-identical verdicts (outcome, bucket, content hash, digest, bracket, binding, reason); core derivation; "Aave" / "Curve Lending" / "V1" still fail |
| 2 | **Severity locked in before the 7-day window exists.** `judge_claim` could run on day 1 and fix a partial-window bucket that the buyer couldn't contest | `judge_claim` and `judge_contest` are refused before incident day + `JUDGE_AFTER_DAYS` (8), `_judgeable_at`, with no fetch and no state change. `_tvl` records the window's last point, and severity is measured only if a point exists on day 7; otherwise COVERED becomes INCONCLUSIVE (refileable), never a lower bucket | Finding2 (the reviewer's scenario: refused at 2023-03-14 18:00 and one second before 03-21; at the full window: APPROVED at bucket 4); `Fix2_FullSeverityWindow` |
| 3 | **Late approvals hold a batch open** (one approval every 47 h) | `_join_batch` opens a new batch once the open one's `closes_at` has passed, so membership is final at close. Each batch settles against its own covers' locks | Finding3 (the reviewer's 8-griefer scenario: Alice paid 16 days in, late claims in their own batches, all paid, Σ payouts ≤ Σ locks); `Fix3_ClosedBatchesAreFinal` (including randomized) |
| 4 | **Refile re-rolls identical evidence** (`#fragment`, re-spelled key) | `_url_key`: scheme, fragment and trailing slash dropped, query sorted, every Wayback timestamp of a page one archived source. `_same_incident`: keys compared as the record they name. One combined `MAX_REFILES = 2` for every reason (inconclusive, mismatch, stall) | Finding4 (2 reviewer tests); `Fix4_RefileIdentity`: query order, archive timestamps, combined limit across reasons, stalls count |

**Test changes, stated plainly.** In `test_attacks.py`, two of the reviewer's tests asserted the vulnerable behaviour as a *precondition*, so they could not pass under the specified fixes:
- **Finding 2** asserted that the early judgement returns APPROVED. It now asserts that the early judgement is refused and that the judgement after the window pays bucket 4. The reviewer's synthetic TVL series stopped at day 4, so it is extended through day 7 at the same drained level, so the window "exists" as the test intends.
- **Finding 3** asserted that every late griefer claim joins Alice's batch. It now asserts that only approvals inside her window do. It also settles the late batches and checks payouts ≤ locked capacity.

Each finding's property is unchanged.

In `test_logic.py`:
- the KyberSwap fixture pool is named "KyberSwap Elastic" (DeFi Llama's core; "Elastic" is a product word, not a generic suffix);
- a partial TVL window test now expects INCONCLUSIVE;
- a canonical claim test waits out the window;
- two assertions follow the renamed refile fields and message.

**Live check before deploying.** Every seeded incident's live DeFi Llama window is complete (8 daily points through day 7) and gives the same buckets as before. Every seeded pool's core name matches its name.

**On chain (demo):**
- **Finding 1:** the Curve proof now runs on a pool named **"Curve DEX"**. Verification stored the core name "Curve" (`0xee05328ace5783f60c99880e4ffedabf6a16900587e0d0e208b048c101eaab41`), and all seven Curve outcomes are as before.
- **Finding 3:** a late Euler approval after batch #2's window closed went into a new batch and was paid separately (`0x2558c1207ee84db42871ffdfcee16a9616a3c80c003c775bbd96a8cbbd1fed8c`).
- **Finding 4:** a refile with the same DNS page plus `#again` was refused as the same source (`0xf69a2e854131305bb719949ccd2206d0ed2a80333b34d1658b3413b9bea41c3a`).
- **Finding 2** cannot be shown on chain with real data today. It needs an incident less than 8 days old inside a cover window. It is proven offline.

## Protocol-domain binding and pool verification

Lens: nothing a single party controls may decide money. Line numbers are in the deployed `contracts/CoverClaim.py`.

| # | item | before | fix (code) | tests |
|---|---|---|---|---|
| 1 | **Protocol domain binding** | **FAIL.** `create_pool` put up to 3 underwriter-chosen "official domains" straight onto the evidence allowlist. An underwriter owning `euler-postmortem.xyz` could publish a "post-mortem" there and contest a COVERED claim with it | The underwriter may only *declare* one domain (`MAX_OFFICIAL_DOMAINS = 1`, L345). A new pool's allowlist is the base only (L3280). The only other domain ever added is `pool.protocol_domain` (`_allowlist`, L3106), written once by `verify_pool` (L3177) from the website DeFi Llama lists, with `www.` stripped (`_website_domain`, L1398). It is none if DeFi Llama lists none, or lists a shared publishing host (`SHARED_HOSTS`, L349: medium.com, github.com, x.com, …). A declared domain that isn't DeFi Llama's website fails the pool (L1458). Filing, refiling, contesting and `check_evidence` all read `self._allowlist(pool)` (file_claim L3792, refile_claim L3876, contest L4163, check_evidence L4923), so a contest page on any other domain is refused before GenLayer | `TestPoolVerification`: `test_declared_domain_must_be_defillamas_website`, `test_matching_domain_is_the_only_protocol_domain`, `test_no_website_listed_means_no_protocol_domain`, `test_shared_publishing_host_is_never_a_protocol_domain`, **`test_contest_from_unverified_domain_refused_before_model`** (own domain, look-alike, archive of own domain; and `multichain.org`, which DeFi Llama doesn't list: all refused, model never called, bond returned), `test_allowlist_has_one_source_of_protocol_domain` (AST) |
| 2 | **Pool verification before sale** | **FAIL.** A pool was OPEN at creation, so a pool whose slug, id or name weren't one protocol sold cover that could never pay: `id_match` pins every claim INCONCLUSIVE, and evidence never names a mis-named pool | Pools are created `UNVERIFIED` (L3311). **`verify_pool`** (L3131) is permissionless: one consensus round (`_verify_consensus` L3115, `_verify_collect` L1808) reads `api.llama.fi/protocol/<slug>`. The verdict is **re-derived** from the agreed raw fields (`_verify_verdict` L1415), and validators refuse a leader whose verdict its own raw fields don't produce (`_verify_agrees` L1844). VERIFIED requires: the record exists; its id is the pool's id (L1444); the pool's name names it (same first word, word-aligned: "Euler" ↔ "Euler V1"); a declared domain is its website. A 5xx is RETRY, and nothing changes. `buy_cover` sells only VERIFIED pools (L3457, `_not_selling` L2614). FAILED pools refuse capacity and cover; `close_pool` works on any non-closed pool and returns the capital (L3407) | **`test_buy_before_verification_refused`** (premium refunded, no cover), **`test_mismatched_slug_id_fails_and_cannot_sell`**, `test_unknown_slug_fails`, `test_wrong_protocol_name_fails`, **`test_verified_pool_works_as_before`**, **`test_nobody_can_pay_a_premium_into_a_pool_that_can_never_pay`** (6 bad pool shapes, before and after verification: no premium held, no cover, closes), `test_transient_source_is_retry_and_changes_nothing`, `test_verification_works_while_paused`, `test_forged_verdict_refused_by_validators`, `test_verification_fields_written_only_by_verify_pool` (AST) |

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
| Euler pool (declared `euler.finance`) | VERIFIED; allowlist `rekt.news, web.archive.org, euler.finance` | `0x922291e254713aee3667a3b723e3fc404d9388e4b8540f27cf47bf7c518abad2` |
| Curve pool (declared `curve.finance`, 69 MB record) | VERIFIED; `curve.finance` | `0xee05328ace5783f60c99880e4ffedabf6a16900587e0d0e208b048c101eaab41` |
| Multichain pool (no declaration; DeFi Llama lists none) | VERIFIED with **no** protocol domain: rekt.news only | `0x775ade34c0d50f28c0e95b2833553bff4902161c3feef906b2ce4dff66c9f8d7` |
| Euler slug + id, declaring `euler-postmortem.xyz` | **FAILED_VERIFICATION**: "declared domain euler-postmortem.xyz is not the website DeFi Llama lists for Euler V1"; a premium sent to it came straight back; closed with the capital returned | verify `0xcf29456e73ef9f793bce062b19268e75e8f3487b9e4768cf32d499fdee9f6bdf`, buy refused `0x3561e2f441223ab3df3c76a4aee130366c69e2d25dbf11f9c9f3c6951f9b21f4`, close `0xd47ea5e2a2c6c44dfe9648b7ae0ea022e5969f16aae0cf9f7165b8e968f2822b` |
| slug `curve-dex` + id 1183 | **FAILED_VERIFICATION**: "slug curve-dex is DeFi Llama id 3, not 1183"; buy refused; closed | verify `0xdcfd9973eb815b7f49f5f3a3e4ecb933187e1dca189fd7a6a74d39752768e703`, buy refused `0x0559b38eb4901f2952ad4ebdf17841aed9208f468c23b35f2bc1759908d76400`, close `0xa047dfbab80016807c3cfa09708c3168dd7ffbb0f52061c0b86d3edf454978e5` |
| underwriter contests the COVERED Euler claim with `euler-postmortem.xyz/official-post-mortem` | **refused before GenLayer** ("not on this pool's frozen evidence allowlist"); bond refunded; the verdict stands | `0xed256bc4141c4e35ef771713e533ae6e86535552febaae547376ac3f90ccb75e` |
| buyer contests the Multichain denial with `multichain.org` (not listed by DeFi Llama) | **refused before GenLayer**; bond refunded | `0x3619fa28c2c12f98f92a45d6eaa0d21b20151d7a8c05b4069f2ecc98aa328a28` |
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
| 2 | canonical incident identity | **FAIL**: settlement windows were keyed by `pool:incident_day`, so two records of one protocol on one day would share a batch | `_incident_id` L2175: the selected record's `id:day:normalised name`. It is compared exactly (`EXACT_STR`), stored on the claim and the batch, keys the batch (`_join_batch` L3927), and is what the content hash covers | `TestBindingAudit.test_2_differently_written_keys_group_and_scale_together`: `1183:2023-03-13` and `…:Euler V1` → one incident, one batch, same hash, scaled pro-rata. `test_2_two_records_on_one_day_are_two_incidents` |
| 3 | contest binding | **PASS**: already bound | allowlist L4163; the contest has no key parameter (`contest(claim_id, evidence_urls, statement)` L4113) and its facts use the claim's stored key (L3650); only BOUND pages are read (L2001), so pages dated elsewhere and undated pages add nothing; `event_match` is asked again | `test_3_contest_page_dated_elsewhere_is_not_read`, `test_3_contest_undated_page_is_not_read`, `test_3_contest_bound_page_rejudged_with_event_match` (DIFFERENT → EVIDENCE_MISMATCH), `test_3_contest_allowlist_applies`, `test_3_contest_cannot_change_the_incident_key` |
| 4 | refile binding | **PASS for the question, FAIL for leftover state**: the new judgement was already asked from scratch, but the rejected attempt's batch membership and resolved-contest state carried over | refile L3889: `_leave_batch`, gross and table reset, a resolved contest cleared; the key re-checked by `_key_check`; evidence by the allowlist; combined refile limit L3855 (MAX_REFILES, every reason) | `test_4_refile_reuses_nothing_from_the_rejected_attempt`, `test_4_refile_rechecks_the_key_from_scratch`, `test_4_refile_limit` |
| 5 | one payout per cover | **FAIL**, and a real one: approve → contest flip → refile → re-approve inside one open window appended the claim to the same batch twice, and `finalize_incident` paid it twice. The test showed "2 != 1" and a broken ledger before the fix | listed once (L3946); a flip out of APPROVED leaves the batch (L4296, `_leave_batch` L3952); finalize pays each claim once (L4356), only if still in THIS batch and its cover is ACTIVE (L4365) | `test_5_flip_refile_reapprove_pays_once`, `test_5_paid_cover_is_never_paid_again`, `test_5_new_verdict_after_refile_can_be_contested`, `test_5_payouts_never_exceed_locked_capacity_random` (12 random pools, mixed keys, random flips: Σ payouts ≤ Σ locks, one payout per cover) |
| 6 | any other binding | two found (below); everything else PASS | see below | `TestBindingAudit6` |

**Item 6, everything a stored result depends on:**

| stored result | depends on | bound to | status |
|---|---|---|---|
| incident date, record fields | the one hacks row the key names | record | PASS |
| severity (TVL window) | `/protocol/<slug>`, window anchored on the record's day; `id_match` requires the TVL document's id to be the pool's id (L2055) | record + pool | PASS (`test_severity_window_follows_the_record_not_the_filing_time`) |
| classification, peril, exclusion, strength | bound pages only; bracket ∩ the pool's frozen perils and exclusions | record + policy | PASS |
| outcome and gross (`_outcome` L4077) | cover start, end and amount; pool waiting period, table and deductible | cover + policy | PASS (`test_outcome_inputs_are_this_cover_and_this_pool`) |
| settlement batch, pro-rata pool | canonical incident id, the locks of those covers | record + covers | **was FAIL** (item 2), fixed |
| payout | the claim's membership in the batch, the cover's status | cover | **was FAIL** (item 5), fixed |
| a page's evidence date on `web.archive.org` | text of the page | page | PASS: the Wayback "FILE ARCHIVED ON" footer is an HTML comment and is dropped. Hardened: a toolbar block, if one is served inside the page, is cut out (L1652) (`test_wayback_metadata_never_dates_a_page`) |
| **CoverRegistry attestation** (`get_active_cover` / `is_covered`) | **the protocol string matched against the pool's free-text display name** as well as its slug | — | **FAIL**, fixed: matched only by the pool's frozen DeFi Llama slug, id, or `slug:id` (L5065). A pool named "Aave" over Euler's slug no longer attests Aave cover (`test_registry_ignores_display_names`, registry tests) |
| contest re-reading | the stored judged digest, and the record and TVL re-read under the claim's same key | record | PASS. A contest re-reads DeFi Llama live, so if DeFi Llama edits or removes the record afterwards, a contest can come out INCONCLUSIVE (refileable). That is a re-reading of the same record, never a different one |
| pool slug vs id | both frozen at creation, but no web read is possible there | policy | residual, documented: a pool whose slug and id name different protocols can never pay (`id_match` pins every claim INCONCLUSIVE). `slug:id` lets an integrator require both |

## Tests (offline, `python3 test/test_logic.py`, 668 passing; `python3 test/test_attacks.py`, 21 passing)

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

## On-chain proof (demo instance `0x33e464ebF31eEaeD31fDB16D38CCb97FB30A8339`)

Probed first:
- `api.llama.fi/hacks` has both Curve DEX records under `defillamaId` 3: 2022-08-09 "Frontend & Infrastructure / DNS Hijack" and 2023-07-30 "Reentrancy / Vyper Compiler Bug".
- Both rekt.news articles are readable by plain GET from the allowlist. Each carries one date, a day after its own incident.

Setup:
- One Curve pool, collateral 100%, 10% deductible, 7-day wait.
- Seven 0.5 GEN covers, each running 2022-07-31 05:24 → 2023-07-31 05:24 UTC (waiting ends 2022-08-07).
- `check_incident` accepted both keys on this cover.

| # | evidence | record (key) | outcome | event | binding | severity | judge tx |
|---|---|---|---|---|---|---|---|
| 1 | Vyper (rekt.news/curve-vyper-rekt) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG` | SAME (model) | BOUND 2023-07-31 | bucket 2, 4952 bps (Vyper window); gross 0.225 GEN | `0xe79d721eabd37e675f7b6f255120899c125d62c30ba8bb5d2fdb1e67c7683dfb` |
| 2 | Vyper | `3:2022-08-09` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2023-07-31 | window anchored on 2022-08-09 (148 bps), not used | `0x2b07e697af9ba1f505fb4314ec809dda94472f58bb100b195b687b2ba680dcf6` |
| 3 | DNS (rekt.news/curve-finance-rekt) | `3:2023-07-30` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2022-08-10 | window anchored on 2023-07-30, not used | `0x62e33efac5c991afe5c466e7f51747b07539b066db055a2627cfde838d23c3b0` |
| 4 | DNS | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK` | SAME (model) | BOUND 2022-08-10 | bucket 0, 148 bps (DNS window) | `0x63dbf7d4febe57dd98553b278f88452239f90961e6232de2453e983b0541d865` |
| 5 | DNS, then refiled with Vyper | `3:2023-07-30` | EVIDENCE_MISMATCH → refile → **APPROVED → paid** | DIFFERENT → SAME | UNBOUND → BOUND | bucket 2, 4952 bps | mismatch `0x21d62a128d81c89ebf657add7aded702303761641c8eee9b8c40fdc71e4feb2b`, refile `0x48efb8fea5d93f8a75c898d845c29fa7d9ea73c9b974f0201841f293c5d61854`, judge `0x7ff3c68580e386bed4fe80651559fb692283909bd88df88f64ae6a10e430de5f` |
| 6 | [DNS, Vyper] (mixed) | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK`, no payout, classified from the DNS page only | SAME (model) | DNS BOUND 2022-08-10; Vyper UNBOUND 2023-07-31 | bucket 0 (DNS window) | `0xd63eba5abb53ebbf4e4fe1f92bae440a4727b41ab9fdb42c2be772bfd268e542` |
| 7 | [Vyper, DNS] (mixed) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG`, classified from the Vyper page only | SAME (model) | Vyper BOUND 2023-07-31; DNS UNBOUND 2022-08-10 | bucket 2, 4952 bps | `0xf47afbc0d4ce6bfef94bf736fae4ca2b1b5f2b27f4b20cb77d9653b5cc03a78b` |

Claims 1 and 5 carry the same content hash `7b244fb5a5ef1dbd`: same key, same evidence, same record, same TVL window.

Claim 2's hash `e4db574b4f52ad5e` and claim 3's `b6bc02b93277364b` differ from it and from each other; claim 3 shares its hash with claim 5's first (mismatched) judgement.

**Canonical, backdating.** A cover bought on 2026-09-29, with a claim keyed to Euler's `1183:2023-03-13`, is refused at filing ("predates this cover's start plus its waiting period"), with no fetch and no model. The cover keeps its one claim: tx `0x9b967f20eb41d8cdd1a38dbdaf7599d7e295de9ba4e3e85b45b58bacda491380`.

**Settlement.**
- Claims 1, 5 and 7 (canonical incident `3:2023-07-30:curve dex`) are paid together in batch 1 (`0x9e815a17933f6800faf1ef74ca1c0368d7614eb309edbb79f97decd3b6abc9da`).
- Claims 2, 3 and 6 have gross 0 and no batch.
- The two pro-rata Euler claims, keyed two ways, are one incident in one batch, scaled at 5555 bps.

**All seeded scenarios pass, read back from chain state** by `node test/collect.mjs` ([docs/EVIDENCE.md](docs/EVIDENCE.md), **27/27**):
- the review fixes: core name, late approval, refile identity
- the 7-claim Curve proof
- pool verification: two failing pools could not sell
- contests from unverified domains refused
- one payout per cover (structural)
- Euler COVERED and CONTESTED
- Multichain EXCLUDED
- INCONCLUSIVE
- PRO-RATA
- EXPIRED
- STALLED
- canonical BACKDATED
- the waiting-period gate
- the registry
- ledger identity
- demo drained

**Drained to zero** in one pass: all seven pools closed, every balance withdrawn. The books read **balance 0 = held 0 + payable 0 wei, locked 0**. Studio Dev again finalized every `claim_payout` without executing the transfer: `undelivered_wei = 14397066666666666675`.

**Audit.** `python3 tools/audit.py` gives **69 PASS / 0 FAIL**. It now runs `test/test_attacks.py` and checks the judging gate and batch finality structurally.

## New addresses (GenLayer Studio Dev, chain 61997)

| contract | address | deploy tx |
|---|---|---|
| `CoverClaim` (canonical) | `0x039BCD3b9a12f81e1069dBbe9122A4B2e73db937` | `0x81b159036b3e0131ccfae8d97ecbf2c03a448f7d468338a62f8a2f367d73bcfb` |
| `CoverClaimDemo` (DEMO, `demo_backdate_days = 1521`) | `0x33e464ebF31eEaeD31fDB16D38CCb97FB30A8339` | `0x9b2ec2eabe733a8fd1109d226de7d3cecf632ce38809b3957af6ac1820460670` |
| `CoverRegistry` | `0x045C4C2BDE62CA730ceDf9B3ea810fbd645f2c6b` | `0xe42c25b72bca5f83934a96bd13de6f064f4d2496cbf128d7b033d0a9f901edf4` |

- CoverClaim source: 239,268 bytes, sha256 `d901d87195097391…`, identical on chain for both instances (`node test/verify_onchain.mjs`).
- Previous deployments: `docs/previous-deployment/1-first/`, `docs/previous-deployment/2-waitgate/`, `docs/previous-deployment/3-one-event/` (before the classifier-input confirmation), `docs/previous-deployment/4-matched-pages/` (before the binding audit), `5-binding-audit/` (before domain binding and pool verification), `6-verification-view-bug/`, `7-before-review-fixes/`.
- App: https://coverclaim.vercel.app. It reads the addresses from Vercel production env vars, and the live bundle contains only these addresses.
