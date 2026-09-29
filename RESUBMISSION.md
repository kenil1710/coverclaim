# Resubmission — one event binds evidence, incident record and TVL window

**Deployment of record** (Studio Dev, chain 61997; source sha256 `f5b18afd2a1acdfe…`, identical on chain, in this repository and on GitHub):

| contract | address |
|---|---|
| `CoverClaim` (canonical) | `0x71Bf9047F8B2DDFEf086116846fb65d2a974719f` |
| `CoverClaimDemo` (DEMO, `demo_backdate_days = 1521`) | `0x6FaA9942421467BA5A386B455a71f3baB04aDE84` |
| `CoverRegistry` | `0x1e6D0F18F82A1B73C0Afd36799703CA5Ed8A111f` |

This deployment was seeded with a **scoped** set after review round 2: the full Curve proof (7 claims), pro-rata, a contest, an evidence-outage retry, and the early-judging refusal. All 17/17 pass, read back from chain state ([docs/EVIDENCE.md](docs/EVIDENCE.md)). On-chain hashes for those scenarios below are from this deployment. Hashes marked **‡** are from the previous deployment, whose complete evidence (every scenario, 27/27) is archived in [docs/superseded/2026-09-29-review-round1/](docs/superseded/2026-09-29-review-round1/).

## Independent review, round 2: two findings (`test/test_attacks_round2.py`)

`python3 test/test_attacks_round2.py` passes 11/11: the reviewer's 3 tests plus 8 for the fixes. Both attack files stay in the suite, and the audit runs both.

| # | finding | fix (`contracts/CoverClaim.py`) | tests |
|---|---|---|---|
| 5 | **An evidence outage ends a claim.** A page answering non-200 read as "unread", so the verdict was INCONCLUSIVE ("no evidence page could be read"). Because round 1 requires a *new* source for a refile, the buyer could never resubmit that page. `judge_claim` is permissionless, so the underwriter could time it | `_page` returns its status. In `_read_sources`, any page that isn't a 200 with a body (5xx, 4xx, timeout, refused connection) makes the round a **RETRY**, like a DeFi Llama 5xx: nothing settles, the claim stays FILED, no refile is spent. A validator agrees with a leader's RETRY only if it sees the same. `_coherent` refuses a verdict whose raw inputs contain an unread page. Sources become "already judged" only when a settled judgement **read** them (`_mark_read`, called by `judge_claim` and `judge_contest`); filing and refiling record nothing. If every page fails, the result is RETRY, never INCONCLUSIVE | Finding5; `Fix5_EvidenceOutageIsRetry`: every non-200 status, one of two pages down, all pages down, only read pages recorded, a forged unread page refused, a contest page outage keeps the contest PENDING |
| 6 | **`www.` and `?ref=x` made one page a new source** | `_url_key`: `www.` stripped, so it and the bare host are one host; the query string is dropped entirely | Finding6 (2 reviewer tests); `Fix6_UrlIdentity`, including the same page twice in one filing refused |

**Test change, stated plainly.** The reviewer's Finding 5 asserted the vulnerable outcome as its precondition: INCONCLUSIVE during the outage, then a refile. Under the fix the outage is a RETRY and the claim stays FILED, so there is nothing to refile. The test now asserts exactly the specified behaviour: 503 → RETRY, claim FILED, no refile spent, nothing marked judged; after recovery, the same page is judged and pays.

In `test_attacks.py`, my own round-1 URL test now expects a query string to be ignored. One fixture serves its query-bearing URL, which was previously "unread" and is now correctly a RETRY. In `test_logic.py`, three tests follow `_page`'s new return value and a failed page load now being a RETRY.

**On chain:**
- **Evidence outage.** Demo claim #11 was filed with a rekt.news page answering 500. `judge_claim` → **RETRY**, `judged: false`, claim still FILED, no refile spent (`0x44407ea98c1808e0d9e30ca97673453f2f961a4a6c404de3a3f72ba8df234dd1`).
  - That page never comes back, so the buyer replaced it through the stall path: `settle_stalled` `0x0e53875ce0a7251f40d04753ef6e3988a400c5aecbcd552af484f7c97afb1f12`, refile with the real article `0x48e8693a2904da359a977549b3d64aea066e6b2b74ad7e9d2c18ab1190587431`.
  - It was then judged COVERED at bucket 4 and paid (`0xb0b4058a5f0804ea8ed4bba25f8219aac9088cf50cb2cbb53bb6fb32940c46ae`).
  - Judging the *same* page after it recovers is shown offline (Finding5), since a live page can't be made to go down and come back.
- **Early-judging refusal.** No real incident is less than 8 days old inside a cover today, so this runs on a **staging instance**: the same bytes, `demo_backdate_days = 1`, at `0x2692A892fDC84f2f83C0eDf139BEEd03FC362d6F`. A cover bought there can name today's date. A claim keyed `1183:2026-09-29` was refused: "the 7-day TVL window of incident 1183:2026-09-29 has not ended; claim #1 can be judged from 1791331200" (2026-10-07) (`0x7397256dbc4e172f33c9dbeb4aa53a2849ff8b4894f2b806bf0435138a87ccbb`). The staging instance holds that one 0.01 GEN cover and its 1 GEN pool. By the very rule it demonstrates, they can't be settled before 2026-10-07.
- **Curve proof, pro-rata, contest.** All pass again on this deployment. Hashes are in the sections below and in [docs/EVIDENCE.md](docs/EVIDENCE.md).
- **Drained.** The demo instance drained to **balance 0 = held 0 + payable 0 wei**. Studio Dev again finalized every `claim_payout` without executing the transfer (`undelivered_wei = 8951666666666666673`).
- **Audit.** 60 PASS / 0 FAIL: fewer on-chain rows than last time, because the reseed was scoped.

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
- **Finding 1:** the Curve proof now runs on a pool named **"Curve DEX"**. Verification stored the core name "Curve" (`0xefda36a016937f9e153ff1ec10bf3db11af96b75fa47ca8ee1cbd3384a624c65`), and all seven Curve outcomes are as before.
- **Finding 3:** a late Euler approval after batch #2's window closed went into a new batch and was paid separately (`0x2558c1207ee84db42871ffdfcee16a9616a3c80c003c775bbd96a8cbbd1fed8c`‡).
- **Finding 4:** a refile with the same DNS page plus `#again` was refused as the same source (`0xa3fb24a24a4119287dbc4fc9a5c8267af4f9bf9a5599ade6ae3dbe1cd56d894c`).
- **Finding 2** cannot be shown on chain with real data today. It needs an incident less than 8 days old inside a cover window. It is proven offline.

## Protocol-domain binding and pool verification

Lens: nothing a single party controls may decide money. Line numbers are in the deployed `contracts/CoverClaim.py`.

| # | item | before | fix (code) | tests |
|---|---|---|---|---|
| 1 | **Protocol domain binding** | **FAIL.** `create_pool` put up to 3 underwriter-chosen "official domains" straight onto the evidence allowlist. An underwriter owning `euler-postmortem.xyz` could publish a "post-mortem" there and contest a COVERED claim with it | The underwriter may only *declare* one domain (`MAX_OFFICIAL_DOMAINS = 1`, L345). A new pool's allowlist is the base only (L3289). The only other domain ever added is `pool.protocol_domain` (`_allowlist`, L3115), written once by `verify_pool` (L3186) from the website DeFi Llama lists, with `www.` stripped (`_website_domain`, L1392). It is none if DeFi Llama lists none, or lists a shared publishing host (`SHARED_HOSTS`, L349: medium.com, github.com, x.com, …). A declared domain that isn't DeFi Llama's website fails the pool (L1452). Filing, refiling, contesting and `check_evidence` all read `self._allowlist(pool)` (file_claim L3813, refile_claim L3896, contest L4179, check_evidence L4940), so a contest page on any other domain is refused before GenLayer | `TestPoolVerification`: `test_declared_domain_must_be_defillamas_website`, `test_matching_domain_is_the_only_protocol_domain`, `test_no_website_listed_means_no_protocol_domain`, `test_shared_publishing_host_is_never_a_protocol_domain`, **`test_contest_from_unverified_domain_refused_before_model`** (own domain, look-alike, archive of own domain; and `multichain.org`, which DeFi Llama doesn't list: all refused, model never called, bond returned), `test_allowlist_has_one_source_of_protocol_domain` (AST) |
| 2 | **Pool verification before sale** | **FAIL.** A pool was OPEN at creation, so a pool whose slug, id or name weren't one protocol sold cover that could never pay: `id_match` pins every claim INCONCLUSIVE, and evidence never names a mis-named pool | Pools are created `UNVERIFIED` (L3320). **`verify_pool`** (L3140) is permissionless: one consensus round (`_verify_consensus` L3124, `_verify_collect` L1803) reads `api.llama.fi/protocol/<slug>`. The verdict is **re-derived** from the agreed raw fields (`_verify_verdict` L1409), and validators refuse a leader whose verdict its own raw fields don't produce (`_verify_agrees` L1839). VERIFIED requires: the record exists; its id is the pool's id (L1438); the pool's name names it (same first word, word-aligned: "Euler" ↔ "Euler V1"); a declared domain is its website. A 5xx is RETRY, and nothing changes. `buy_cover` sells only VERIFIED pools (L3466, `_not_selling` L2623). FAILED pools refuse capacity and cover; `close_pool` works on any non-closed pool and returns the capital (L3416) | **`test_buy_before_verification_refused`** (premium refunded, no cover), **`test_mismatched_slug_id_fails_and_cannot_sell`**, `test_unknown_slug_fails`, `test_wrong_protocol_name_fails`, **`test_verified_pool_works_as_before`**, **`test_nobody_can_pay_a_premium_into_a_pool_that_can_never_pay`** (6 bad pool shapes, before and after verification: no premium held, no cover, closes), `test_transient_source_is_retry_and_changes_nothing`, `test_verification_works_while_paused`, `test_forged_verdict_refused_by_validators`, `test_verification_fields_written_only_by_verify_pool` (AST) |

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
| Euler pool (declared `euler.finance`) | VERIFIED; allowlist `rekt.news, web.archive.org, euler.finance` | `0xfa81da280890223eb43f01aca1340235c3ddd5fad91793c74596735b3e4478c2` |
| Curve pool (declared `curve.finance`, 69 MB record) | VERIFIED; `curve.finance` | `0xefda36a016937f9e153ff1ec10bf3db11af96b75fa47ca8ee1cbd3384a624c65` |
| Multichain pool (no declaration; DeFi Llama lists none) | VERIFIED with **no** protocol domain: rekt.news only | `0x775ade34c0d50f28c0e95b2833553bff4902161c3feef906b2ce4dff66c9f8d7`‡ |
| Euler slug + id, declaring `euler-postmortem.xyz` | **FAILED_VERIFICATION**: "declared domain euler-postmortem.xyz is not the website DeFi Llama lists for Euler V1"; a premium sent to it came straight back; closed with the capital returned | verify `0xcf29456e73ef9f793bce062b19268e75e8f3487b9e4768cf32d499fdee9f6bdf`‡, buy refused `0x3561e2f441223ab3df3c76a4aee130366c69e2d25dbf11f9c9f3c6951f9b21f4`‡, close `0xd47ea5e2a2c6c44dfe9648b7ae0ea022e5969f16aae0cf9f7165b8e968f2822b`‡ |
| slug `curve-dex` + id 1183 | **FAILED_VERIFICATION**: "slug curve-dex is DeFi Llama id 3, not 1183"; buy refused; closed | verify `0xdcfd9973eb815b7f49f5f3a3e4ecb933187e1dca189fd7a6a74d39752768e703`‡, buy refused `0x0559b38eb4901f2952ad4ebdf17841aed9208f468c23b35f2bc1759908d76400`‡, close `0xa047dfbab80016807c3cfa09708c3168dd7ffbb0f52061c0b86d3edf454978e5`‡ |
| underwriter contests the COVERED Euler claim with `euler-postmortem.xyz/official-post-mortem` | **refused before GenLayer** ("not on this pool's frozen evidence allowlist"); bond refunded; the verdict stands | `0xed256bc4141c4e35ef771713e533ae6e86535552febaae547376ac3f90ccb75e`‡ |
| buyer contests the Multichain denial with `multichain.org` (not listed by DeFi Llama) | **refused before GenLayer**; bond refunded | `0x3619fa28c2c12f98f92a45d6eaa0d21b20151d7a8c05b4069f2ecc98aa328a28`‡ |
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
| 2 | canonical incident identity | **FAIL**: settlement windows were keyed by `pool:incident_day`, so two records of one protocol on one day would share a batch | `_incident_id` L2179: the selected record's `id:day:normalised name`. It is compared exactly (`EXACT_STR`), stored on the claim and the batch, keys the batch (`_join_batch` L3942), and is what the content hash covers | `TestBindingAudit.test_2_differently_written_keys_group_and_scale_together`: `1183:2023-03-13` and `…:Euler V1` → one incident, one batch, same hash, scaled pro-rata. `test_2_two_records_on_one_day_are_two_incidents` |
| 3 | contest binding | **PASS**: already bound | allowlist L4179; the contest has no key parameter (`contest(claim_id, evidence_urls, statement)` L4129) and its facts use the claim's stored key (L3659); only BOUND pages are read (L2005), so pages dated elsewhere and undated pages add nothing; `event_match` is asked again | `test_3_contest_page_dated_elsewhere_is_not_read`, `test_3_contest_undated_page_is_not_read`, `test_3_contest_bound_page_rejudged_with_event_match` (DIFFERENT → EVIDENCE_MISMATCH), `test_3_contest_allowlist_applies`, `test_3_contest_cannot_change_the_incident_key` |
| 4 | refile binding | **PASS for the question, FAIL for leftover state**: the new judgement was already asked from scratch, but the rejected attempt's batch membership and resolved-contest state carried over | refile L3909: `_leave_batch`, gross and table reset, a resolved contest cleared; the key re-checked by `_key_check`; evidence by the allowlist; combined refile limit L3875 (MAX_REFILES, every reason) | `test_4_refile_reuses_nothing_from_the_rejected_attempt`, `test_4_refile_rechecks_the_key_from_scratch`, `test_4_refile_limit` |
| 5 | one payout per cover | **FAIL**, and a real one: approve → contest flip → refile → re-approve inside one open window appended the claim to the same batch twice, and `finalize_incident` paid it twice. The test showed "2 != 1" and a broken ledger before the fix | listed once (L3961); a flip out of APPROVED leaves the batch (L4313, `_leave_batch` L3967); finalize pays each claim once (L4373), only if still in THIS batch and its cover is ACTIVE (L4382) | `test_5_flip_refile_reapprove_pays_once`, `test_5_paid_cover_is_never_paid_again`, `test_5_new_verdict_after_refile_can_be_contested`, `test_5_payouts_never_exceed_locked_capacity_random` (12 random pools, mixed keys, random flips: Σ payouts ≤ Σ locks, one payout per cover) |
| 6 | any other binding | two found (below); everything else PASS | see below | `TestBindingAudit6` |

**Item 6, everything a stored result depends on:**

| stored result | depends on | bound to | status |
|---|---|---|---|
| incident date, record fields | the one hacks row the key names | record | PASS |
| severity (TVL window) | `/protocol/<slug>`, window anchored on the record's day; `id_match` requires the TVL document's id to be the pool's id (L2059) | record + pool | PASS (`test_severity_window_follows_the_record_not_the_filing_time`) |
| classification, peril, exclusion, strength | bound pages only; bracket ∩ the pool's frozen perils and exclusions | record + policy | PASS |
| outcome and gross (`_outcome` L4093) | cover start, end and amount; pool waiting period, table and deductible | cover + policy | PASS (`test_outcome_inputs_are_this_cover_and_this_pool`) |
| settlement batch, pro-rata pool | canonical incident id, the locks of those covers | record + covers | **was FAIL** (item 2), fixed |
| payout | the claim's membership in the batch, the cover's status | cover | **was FAIL** (item 5), fixed |
| a page's evidence date on `web.archive.org` | text of the page | page | PASS: the Wayback "FILE ARCHIVED ON" footer is an HTML comment and is dropped. Hardened: a toolbar block, if one is served inside the page, is cut out (L1647) (`test_wayback_metadata_never_dates_a_page`) |
| **CoverRegistry attestation** (`get_active_cover` / `is_covered`) | **the protocol string matched against the pool's free-text display name** as well as its slug | — | **FAIL**, fixed: matched only by the pool's frozen DeFi Llama slug, id, or `slug:id` (L5082). A pool named "Aave" over Euler's slug no longer attests Aave cover (`test_registry_ignores_display_names`, registry tests) |
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

## On-chain proof (demo instance `0x6FaA9942421467BA5A386B455a71f3baB04aDE84`)

Probed first:
- `api.llama.fi/hacks` has both Curve DEX records under `defillamaId` 3: 2022-08-09 "Frontend & Infrastructure / DNS Hijack" and 2023-07-30 "Reentrancy / Vyper Compiler Bug".
- Both rekt.news articles are readable by plain GET from the allowlist. Each carries one date, a day after its own incident.

Setup:
- One Curve pool, collateral 100%, 10% deductible, 7-day wait.
- Seven 0.5 GEN covers, each running 2022-07-31 05:24 → 2023-07-31 05:24 UTC (waiting ends 2022-08-07).
- `check_incident` accepted both keys on this cover.

| # | evidence | record (key) | outcome | event | binding | severity | judge tx |
|---|---|---|---|---|---|---|---|
| 1 | Vyper (rekt.news/curve-vyper-rekt) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG` | SAME (model) | BOUND 2023-07-31 | bucket 2, 4952 bps (Vyper window); gross 0.225 GEN | `0x617fb420bb466ce44e45d9c9fae0b9e9b62a8d4c58ac514d40c7e1fb9438c28c` |
| 2 | Vyper | `3:2022-08-09` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2023-07-31 | window anchored on 2022-08-09 (148 bps), not used | `0xceb737f10dcf020861bb58574e13b64d02d7f848e66d291c9d92d8034d1757db` |
| 3 | DNS (rekt.news/curve-finance-rekt) | `3:2023-07-30` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2022-08-10 | window anchored on 2023-07-30, not used | `0x34dae23466a0b44b5fc2a0e557e32282d8075fc654cd01dc6dbb8d12bc5c9495` |
| 4 | DNS | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK` | SAME (model) | BOUND 2022-08-10 | bucket 0, 148 bps (DNS window) | `0x8c60d433fab0a03b9d0cecf8ce20c939d840106d7d096f7bcc3c13fc3427bdec` |
| 5 | DNS, then refiled with Vyper | `3:2023-07-30` | EVIDENCE_MISMATCH → refile → **APPROVED → paid** | DIFFERENT → SAME | UNBOUND → BOUND | bucket 2, 4952 bps | mismatch `0x44b84a47d2ece59729d0fd66036f8cd728db1cbe0ba4121a3e28e9c69b04fde5`, refile `0x887a56c9a1345044631fc404f06879924464781b9a2b8b21e85f69f4b3a16066`, judge `0x233398d8cf04133c289600b80e3b7010fdb2be0129933868961cd0a70de97ab0` |
| 6 | [DNS, Vyper] (mixed) | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK`, no payout, classified from the DNS page only | SAME (model) | DNS BOUND 2022-08-10; Vyper UNBOUND 2023-07-31 | bucket 0 (DNS window) | `0xa75d8459ca1719fa55363dfd5bf792680ffeda8a3363ab861f81e3fb44ddd620` |
| 7 | [Vyper, DNS] (mixed) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG`, classified from the Vyper page only | SAME (model) | Vyper BOUND 2023-07-31; DNS UNBOUND 2022-08-10 | bucket 2, 4952 bps | `0x0ad3a9ecd9cd40834db990ff1c7945a2739ae359d9c146f33ae5d392b512320c` |

Claims 1 and 5 carry the same content hash `7b244fb5a5ef1dbd`: same key, same evidence, same record, same TVL window.

Claim 2's hash `e4db574b4f52ad5e` and claim 3's `b6bc02b93277364b` differ from it and from each other; claim 3 shares its hash with claim 5's first (mismatched) judgement.

**Canonical, backdating.** A cover bought on 2026-09-29, with a claim keyed to Euler's `1183:2023-03-13`, is refused at filing ("predates this cover's start plus its waiting period"), with no fetch and no model. The cover keeps its one claim: tx `0x9b967f20eb41d8cdd1a38dbdaf7599d7e295de9ba4e3e85b45b58bacda491380`‡.

_The settlement, full-scenario and audit figures in this block are from the **previous** deployment (full reseed, archived in [docs/superseded/2026-09-29-review-round1/](docs/superseded/2026-09-29-review-round1/)); the current deployment's scoped results are at the top of this document._

**Settlement.**
- Claims 1, 5 and 7 (canonical incident `3:2023-07-30:curve dex`) are paid together in batch 1 (`0xd90888ab5c4c9db9c67ac6f14e6ff68f276fc62333f9b65880d42e75fc4bdd10`).
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
| `CoverClaim` (canonical) | `0x71Bf9047F8B2DDFEf086116846fb65d2a974719f` | `0xda7e20a221516d7c89e27e304e2fbbe93fde900abaccbd83b5f96a79253dd2e3` |
| `CoverClaimDemo` (DEMO, `demo_backdate_days = 1521`) | `0x6FaA9942421467BA5A386B455a71f3baB04aDE84` | `0xaf42be3e136f4efba7b47b6a4a18218b93ca66d70e3488df2d85a110f8ed8e90` |
| `CoverRegistry` | `0x1e6D0F18F82A1B73C0Afd36799703CA5Ed8A111f` | `0x4c7dbc81d3786850db5d1dc016e7a34df53fecf8ce32599b194a3e6b8af637ce` |

- CoverClaim source: 240,848 bytes, sha256 `f5b18afd2a1acdfe…`, identical on chain for canonical, demo and the staging instance (`node test/verify_onchain.mjs`), and on GitHub.
- Staging instance (early-judging demonstration only; same bytes, `demo_backdate_days = 1`): `0x2692A892fDC84f2f83C0eDf139BEEd03FC362d6F`. It is not one of the three addresses of record.
- Previous deployments: `docs/previous-deployment/1-first/`, `docs/previous-deployment/2-waitgate/`, `docs/previous-deployment/3-one-event/` (before the classifier-input confirmation), `docs/previous-deployment/4-matched-pages/` (before the binding audit), `5-binding-audit/` (before domain binding and pool verification), `6-verification-view-bug/`, `7-before-review-fixes/`.
- App: https://coverclaim.vercel.app. It reads the addresses from Vercel production env vars, and the live bundle contains only these addresses.
