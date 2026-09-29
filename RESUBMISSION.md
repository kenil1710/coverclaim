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

## Tests (offline, `python3 test/test_logic.py`, 632 passing)

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

## On-chain proof (demo instance `0xf59B1A3DEE9E7075B9Bc1CdcdeD3d0d67666dE99`)

Probed first:
- `api.llama.fi/hacks` has both Curve DEX records under `defillamaId` 3: 2022-08-09 "Frontend & Infrastructure / DNS Hijack" and 2023-07-30 "Reentrancy / Vyper Compiler Bug".
- Both rekt.news articles are readable by plain GET from the allowlist. Each carries one date, a day after its own incident.

Setup:
- One Curve pool, collateral 100%, 10% deductible, 7-day wait.
- Seven 0.5 GEN covers, each running 2022-07-31 05:24 → 2023-07-31 05:24 UTC (waiting ends 2022-08-07).
- `check_incident` accepted both keys on this cover.

| # | evidence | record (key) | outcome | event | binding | severity | judge tx |
|---|---|---|---|---|---|---|---|
| 1 | Vyper (rekt.news/curve-vyper-rekt) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG` | SAME (model) | BOUND 2023-07-31 | bucket 2, 4952 bps (Vyper window); gross 0.225 GEN | `0x5bb0b92f397df1abe05dd68fd5d9730689ad6fb1d903c3612a44bc1ff16ffce4` |
| 2 | Vyper | `3:2022-08-09` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2023-07-31 | window anchored on 2022-08-09 (148 bps), not used | `0x39f27738e643247121a4487ea16c66d6fd047c39e3b3205dd5503e5152d7bc40` |
| 3 | DNS (rekt.news/curve-finance-rekt) | `3:2023-07-30` | **EVIDENCE_MISMATCH**, no payout | DIFFERENT (no model call) | UNBOUND 2022-08-10 | window anchored on 2023-07-30, not used | `0xe5f3d7ddcc52ebfd104705b32ad4f1c69147f198225309536288ed49cae0a18c` |
| 4 | DNS | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK` | SAME (model) | BOUND 2022-08-10 | bucket 0, 148 bps (DNS window) | `0x8b26f14edb2fe33607ac18990cdf236634a59330a02b35025162971c1cde6242` |
| 5 | DNS, then refiled with Vyper | `3:2023-07-30` | EVIDENCE_MISMATCH → refile → **APPROVED → paid** | DIFFERENT → SAME | UNBOUND → BOUND | bucket 2, 4952 bps | mismatch `0x419f8b7403ed48205f090628415622f428db0f363bb1ea19ffef85ca19726f1b`, refile `0x20415f467f1c5208068e660830bf3b2ee292bc389c94d921348264fe882c6b97`, judge `0xa55aa33c0ac3343796e7eab65f1c82ad56583dc3a7ead93f8e9d7effde0b36d0` |
| 6 | [DNS, Vyper] (mixed) | `3:2022-08-09` | **DENIED_EXCLUDED**, `FRONTEND_HIJACK`, no payout, classified from the DNS page only | SAME (model) | DNS BOUND 2022-08-10; Vyper UNBOUND 2023-07-31 | bucket 0 (DNS window) | `0x3fdf39a27f75b56351be45d1bdf57ab964ea708aac0bf4ff248386f84ebff565` |
| 7 | [Vyper, DNS] (mixed) | `3:2023-07-30` | **APPROVED → paid**, COVERED `SMART_CONTRACT_BUG`, classified from the Vyper page only | SAME (model) | Vyper BOUND 2023-07-31; DNS UNBOUND 2022-08-10 | bucket 2, 4952 bps | `0xddabcdb7800377c1a9c03e5b7662d640138301a567e93782cf7d624dae3d23bd` |

Claims 1 and 5 carry the same content hash `7b244fb5a5ef1dbd`: same key, same evidence, same record, same TVL window.

Claim 2's hash `e4db574b4f52ad5e` and claim 3's `b6bc02b93277364b` differ from it and from each other; claim 3 shares its hash with claim 5's first (mismatched) judgement.

**Canonical, backdating.** A cover bought on 2026-09-29, with a claim keyed to Euler's `1183:2023-03-13`, is refused at filing ("predates this cover's start plus its waiting period"), with no fetch and no model. The cover keeps its one claim: tx `0x2327b6dc9caa899e54a9573859cb2dd7e0f52c96d2ac77fcfa181f28c534468d`.

**Settlement.**
- Claims 1, 5 and 7 share one incident, so they are paid together in batch 1 (`0x982c053bbc922b455539f971b1f387099e55eb4ea85e87dedec1b50c6b3c205e`). Each was credited 0.225 GEN: 0.5 GEN × 50% × (1 − 10%).
- Withdrawals: buyer2 `0x66293af7…`, buyer6 `0x22112472…`, buyer4 `0xa68a9ed4…`.
- Claims 2, 3 and 6 have gross 0 and no batch. Their covers released to the underwriter after the claim window.

**All reseeded scenarios pass, read back from chain state** by `node test/collect.mjs` ([docs/EVIDENCE.md](docs/EVIDENCE.md), **19/19**):
- the seven Curve claims above
- Euler COVERED at bucket 4, and the underwriter's contest UPHELD
- Multichain EXCLUDED
- INCONCLUSIVE homepage (no model call)
- PRO-RATA
- EXPIRED
- STALLED (settled and judged while paused)
- canonical BACKDATED, refused at filing (`0x2327b6dc…`)
- waiting-period gate (`0xb59ea9f7…`)
- registry attest
- ledger identity
- demo drained

**One seeding re-run, stated plainly.** In the first seed pass on this deployment, the Euler COVERED + CONTESTED scenario did not run:
- buyer1 bought the 1-day "expired" cover and then the Euler cover 10 s apart, inside the per-wallet buy cooldown, so the contract refused the second buy. The seed script could not read that refusal and took buyer1's previous cover.
- The contract behaved correctly. The script bug is fixed: `newCover` now waits out the cooldown and requires a new cover id.
- The scenario was re-run on its own on a fresh Euler pool (`node test/seed.mjs --part=euler-covered`): claim #13, judged COVERED `0x6b48885e…`, contest UPHELD `0xc8a1460d…`.

**Drained to zero.** Every demo cover was released, all six pools were closed and every balance was withdrawn, in two passes (`docs/drain-evidence-pass1.json`, then `docs/drain-evidence.json` after the Euler re-run). The books read **balance 0 = held 0 + payable 0 wei, locked 0**. As before, Studio Dev finalized every `claim_payout` without executing the value transfer: `undelivered_wei = 14355900000000000008`, published by `get_stats`.

**Audit.** `python3 tools/audit.py` gives **54 PASS / 0 FAIL** ([docs/AUDIT.md](docs/AUDIT.md)). It includes the new checks:
- no "latest row" selection
- the content hash binds incident key + evidence + record + TVL window
- steward tests a–g and the classifier-input tests pass
- README addresses equal `deployments.json`

## New addresses (GenLayer Studio Dev, chain 61997)

| contract | address | deploy tx |
|---|---|---|
| `CoverClaim` (canonical) | `0xF2F545d265dB85495E5Bda8fA02573F17B193983` | `0x4ea19dde06ff07bc91a9ccb81db3f3198990531dd91084b66e857ef3d3ed1f65` |
| `CoverClaimDemo` (DEMO, `demo_backdate_days = 1521`) | `0xf59B1A3DEE9E7075B9Bc1CdcdeD3d0d67666dE99` | `0x4c02ac916c08b7079387c0c433f8b05f35ee21e9251935161fbb5e2dd0aac4fc` |
| `CoverRegistry` | `0x06144d4702C513d289c4Ef1bAA811bbad0c6a4EB` | `0x0a6f32dd1c87a6090ee4631b140fe1628314f7295ace4c94726107ad471e0e81` |

- CoverClaim source: 213,653 bytes, sha256 `c0ba646ac17989f2…`, identical on chain for both instances (`node test/verify_onchain.mjs`).
- Previous deployments: `docs/previous-deployment/1-first/`, `docs/previous-deployment/2-waitgate/`, `docs/previous-deployment/3-one-event/` (this fix before the classifier-input confirmation above).
- App: https://coverclaim.vercel.app. It reads the addresses from Vercel production env vars, and the live bundle contains only these addresses.
