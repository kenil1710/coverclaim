# CoverClaim — design notes

The contract documents its rules where they live. This file is for the
reasoning: choices made against an alternative, things that were tried and
were wrong, and hazards the next reader would otherwise re-discover.

`CoverClaim.py` is assembled from `parts/p1_head.py … p6_views.py` with `cat`
(in order). The parts are an editing convenience only; the deployed artifact
and its sha256 are of the assembled file.

---

## 1. What the model decides, and what it does not

The brief's line is that GenLayer classifies and code does everything else.
The design pushes as much of the "classification vector" as possible OUT of
the model's hands:

| field | who decides |
|---|---|
| incident date | DeFi Llama's incident record, looked up by the pool's DeFi Llama id |
| protocol match | code: does an evidence page name the pool's protocol, word-aligned |
| severity bucket | code: TVL drop from DeFi Llama history, integer bps, fixed edges |
| content hash | code: FNV-1a over the normalised digest + record + TVL line |
| which perils / exclusions are *possible* | code: the bracket (indicator phrases ∩ the pool's frozen lists) |
| evidence-strength range | code: sources that name a risk, and whether DeFi Llama's own class agrees |
| classification, peril, exclusion, strength | **the model, inside the bracket** |

So a leader that wanted to forge a payout would have to forge an incident
record, a TVL history and a page's text — all of which every validator fetches
itself and compares exactly.

## 2. Why the incident date is not extracted from the article

Articles are dated when they are published (rekt.news dates Euler's exploit
"March 14" — the day after), mention several dates, and a model asked "when did
this happen" is a model asked a second question the brief did not give it.
DeFi Llama records one row per incident with a day-precision date and the
protocol's numeric id. A protocol can have several rows (Multichain has four),
so `_pick_incident` chooses deterministically: the latest incident inside the
covered window, else the latest before it (which the backdating check then
rejects), else the earliest after it. A claimant cannot pick a better incident
than the record puts in their window, and cannot hide an old incident behind
a later one outside it.

**Consequence, stated in the README:** an incident DeFi Llama has not recorded
yet is INCONCLUSIVE until it has.

## 3. The bracket, and why it is built from the BUYER's evidence only

DeFi Llama's classification ("Key Compromise", "Frontend & Infrastructure") is
strong evidence, and it is used — in the strength range and in the prompt. It
is deliberately NOT used to widen the bracket. If it were, every recorded
incident would always carry an indicator and "no indicator phrase →
INCONCLUSIVE without a model call" would be dead code. The bracket is what the
evidence the buyer brought actually says.

Indicator phrases are deliberately specific. "Exploit", "hack", "attack" and
"stolen" appear in every incident report and say nothing about WHICH risk
happened, so they are indicators of nothing.

Matching is word-START anchored (`" " + phrase in " " + text`), so "dns" does
not fire inside "sdns" but "oracle" finds "oracles". Protocol names are
anchored at both ends, so "Aave" does not match "Aavegotchi".

## 4. The strength range is one step wide — a correction

It was first three steps wide (`[base-2, base]`). With one agreeing source the
range was `[1, 3]` and the COVERED floor is 3: two honest validators choosing 2
and 3 would disagree about whether the claim PAYS — a disagreement about the
width of a range, not about the incident. The range is now `[base-1, base]`
with three points per independent source (capped at two sources) and one for
DeFi Llama agreeing. One agreeing source is `[3, 4]`: both choices pay.

## 5. The digest — three measured corrections

The digest (salient sentences) is what the model reads, what is hashed and what
a contest's novelty is measured against. It went through three corrections,
each from a measurement:

1. **Split on lines, and a sentence needs five words.** Euler's post-mortem
   renders its nav bar as one-word lines ("Governance", "Developers"…).
   Flattened, the bar merged with the first real sentence into one "sentence"
   naming Euler *and* governance — an exclusion put into the bracket by a menu.
2. **A point ends a sentence only when whitespace follows.** "curve.fi" split
   one rekt.news sentence in two.
3. **Indicator sentences first.** On Euler's own post-mortem the first 2,400
   salient characters — in page order — were about the recovery and named no
   risk at all; the flaw was further down. Sentences carrying an indicator are
   now taken first, name-only sentences fill the rest, and the result is
   restored to page order.

## 6. Render → GET: the stall

See `docs/PROBE.md` §4. A judgement that fetched the 350 KB incident list and
a 9 MB TVL history and THEN called `gl.nondet.web.render` sat in GenVM
execution for over 25 minutes and never produced a leader result, on a smoke
instance, twice. Staged on chain with the contract's own code, stage 3 (render
after the two GETs) never settled; each piece alone was fast. Evidence pages
are now fetched with a plain GET and stripped by `_strip_html`, written by hand
so it is identical on every node. The whole pipeline then ran in 31 s.

The cost is honest and bounded: a JavaScript-only page reads as empty, which
names no protocol and no risk — INCONCLUSIVE, never a payout.

## 7. Money: one entrance, one exit, and the clock never meets a transfer

- `_bank()` is the first statement of every write, so any value that arrives
  is immediately the sender's; `_take()` is the only way it stops being theirs.
  A refusal therefore needs no refund and a double credit is not expressible
  (GrantJudge's `_bank` lesson).
- `_release_to()` is the only way value leaves a pool or a bond; every caller
  decrements the matching pool field beside it. The identity
  `balance == held + payable`, and `held == Σ(pool capital + unearned premium)
  + bonds`, is asserted after every call in the offline suite and published by
  `get_stats`.
- `claim_payout()` is the only method that transfers, and it reads no clock.
  Every clock-reading method (finalize, release, cancel, …) only credits. On
  Studio Dev a write that reads the clock AND posts a transfer cannot be
  fee-estimated (the simulator's clock is stale; GrantJudge and AppAudit each
  lost a path to it). This is enforced over the call graph by
  `TestLoophole10_PaymentNeverReadsTheClock`.

## 8. Why a collateral ratio exists at all

The brief asks for a pro-rata split when claims exceed capacity. If every
cover locked its full maximum payout, approved claims could never exceed the
locks and the pro-rata path would be dead code. So a pool freezes a
`collateral_bps` (20%–100%): each cover locks that fraction of its amount.
A fully collateralised pool can never go short; a pool that writes more cover
than it holds can, and then every claim on the incident is scaled by the same
factor. The seeded pro-rata pool is 50%.

## 9. Settlement windows are per incident, and wait for contests

Claims approved on the same (pool, incident day) share a batch. The batch
finalizes only after its window closes AND every member's contest window has
closed with no contest open, so the set of claims is final before anything is
divided. A claim approved after its incident's batch finalized opens a new one.

## 10. Stalls

A round that never settles applies no state, so `JUDGING` markers almost never
persist. What CAN get stuck is a claim whose evidence no network can agree on:
it stays FILED forever, and without help the buyer could never replace the
evidence (refile is for INCONCLUSIVE). `settle_stalled` — permissionless and
ungated by pause — returns such a claim to FILED and opens a refile window of
one stall period, even past the claim deadline, because a network that could
not read the evidence must not cost the buyer their claim. A contest pending
past the stall window is dropped and the bond returned; the verdict under
contest stands.

## 11. Two fixes made after the first seed (review findings)

- **Filing inside the waiting period is refused mechanically.** Before, a claim
  filed then was judged and came back REJECTED_BACKDATED — correctly, since any
  incident that has already happened predates the waiting period's end — but it
  spent the cover's ONE claim doing so. `file_claim` now refuses with
  "cover waiting period has not ended yet, claimable after <ts>", before any
  evidence is read. The canonical backdating demonstration uses a waiting-0
  pool, where the check still bites: the incident predates the cover's start.
- **Unmeasurable severity is INCONCLUSIVE, not NO_PAYOUT.** Before, a TVL
  history with no point before the incident, or none in the seven days after,
  produced a 0% drop — bucket 0 — and a COVERED claim ended as a final
  NO_PAYOUT. Missing data is not "no damage". The reading now carries
  `tvl_measured` (on the compared axis) and `_outcome` turns COVERED +
  unmeasured into INCONCLUSIVE, which is refileable once DeFi Llama has the
  data. EXCLUDED and backdated verdicts are unaffected: severity does not
  change them.

## 12. Hazards carried from earlier projects

- The runner header is exactly two comment lines; a third makes the contract
  undeployable with only `invalid_contract`.
- A nondet closure must not capture `self` (it pickles storage). `_claim_facts`
  copies plain values out first; the suite walks the AST to prove it.
- `str.replace()` is rejected by the runner.
- No float may cross the nondet boundary: every TVL figure is an int.
- Views can read `gl.message.raw["datetime"]` (measured), so `in_force` is
  time-checked; when it is unreadable, `in_force` is false.
- `emit_transfer` via `gl.chain.Account`, never `Proxy.emit(value=…)`, which
  posts nothing.
