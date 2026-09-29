# Hacks happen. Claims shouldn't be a vote.

*How CoverClaim lets independent validators decide one narrow question about a DeFi exploit — and leaves every wei to arithmetic.*

---

On 13 March 2023, Euler Finance lost about $197 million. The attacker found a function called `donateToReserves` that let an account give away collateral without checking whether it could still cover its debt, and used it to manufacture bad debt it could liquidate itself. Euler's TVL went from $233 million to under $10 million in a day.

Suppose you had bought cover against Euler being hacked. Here is what would have happened next in most of DeFi insurance: a claim, a forum thread, and a vote of token holders on whether your claim was valid. The same token holders whose capital pays the claim.

For Euler, that vote is easy. For the hard cases it is not. When Curve's website was hijacked in August 2022, users approved a malicious contract and lost $575,000. Was that a smart contract failure? The contracts were fine; the DNS was not. When Multichain's funds drained in July 2023, was that a bridge exploit, or was it the fact that one person held all the keys and was in custody? These arguments run for weeks, and the people deciding them are paid not to lose them.

The problem is not that token holders are bad people. It is that "was it a contract bug or user error?" is being answered by the party that owes the money.

CoverClaim takes that question away from them.

---

## What actually has to be judged

Be precise about which part of an insurance claim is hard.

Checking that a cover was bought before the incident is not hard. Computing a premium is not hard. Measuring how far a protocol's TVL fell is not hard, if somebody publishes the history. Applying a deductible, scaling payouts when the pool is short, returning what is left to the underwriter — none of it is hard, and all of it is what smart contracts were built for.

Exactly one thing is hard: **reading what happened and deciding whether it matches a covered peril or an exclusion.**

That has no API. It is a judgement. So the design is one sentence, and it is written into the contract, the README and the app:

> GenLayer reads public incident evidence and classifies it against the frozen policy's covered perils and exclusions. Deterministic contract logic enforces capacity, waiting periods, backdating checks, premium accounting, severity payouts, deductibles, and pro-rata splits.

## Freeze the wording first

An underwriter opens a pool for one protocol and, in the same transaction, freezes the policy: which of four perils it covers (`SMART_CONTRACT_BUG`, `ORACLE_MANIPULATION`, `ECONOMIC_EXPLOIT`, `BRIDGE_COMPROMISE`), which of five it excludes (`PHISHING`, `FRONTEND_HIJACK`, `USER_KEY_COMPROMISE`, `RUG_BY_TEAM`, `GOVERNANCE_ATTACK`), the rate, waiting period, deductible, term, collateral ratio, payout table and the domains evidence may come from. All of it is written once and hashed. There is no setter anywhere in the contract; a test walks the syntax tree to prove it.

A fixed vocabulary matters more than it looks. A free-text peril puts the meaning of the policy back in the hands of whoever reads it. "Smart contract bug" means the text frozen next to it — "a flaw in the protocol's own smart-contract code or its compiler … that an attacker exploited" — and the model is shown exactly that text and nothing else.

## Mechanical rejection first

Most bad claims never reach a validator. Buying cover checks capacity, the per-buyer cap and the exact premium. Filing a claim checks one claim per cover, the claim window, that the claim's **incident key** — one DeFi Llama record, `id:YYYY-MM-DD` — belongs to this protocol and is dated inside the cover after its waiting period, and that **every evidence URL is on the pool's frozen allowlist**: https only, subdomain-exact (`evilrekt.news` is not `rekt.news`), no `user@host` tricks, no ports. A `web.archive.org` snapshot is allowed as a fallback — but only of a page that is itself on the allowlist, or the archive would launder every blog on the internet.

## GenLayer last, and inside a bracket

When anyone triggers a judgement, each validator independently:

1. reads DeFi Llama's incident list and selects **the one record the claim's key names** — exact day, exact protocol id, never "the latest" — which is where the incident date comes from, not from the article and not from the model;
2. reads the protocol's TVL history and measures the drop from the day before **that record's** date to the lowest point in the next seven days — that is the severity bucket;
3. fetches the evidence pages and **binds each one to that record**: a page counts only if it names the protocol and writes a date within three days of it — and only those pages ever reach the model; then keeps only the sentences that name the protocol or a risk;
4. computes the **bracket**: which of the pool's covered perils and exclusions the evidence actually names, and what evidence strength the sources can support.

If no page is about the selected incident, the answer is EVIDENCE_MISMATCH; if the evidence names no risk, INCONCLUSIVE — in both cases **no model is called at all**. Otherwise the model answers inside the bracket, and also says whether the evidence describes the SAME incident as the record (SAME / DIFFERENT / UNCLEAR). A validator checks the leader's choice against the leader's own inputs by arithmetic before it spends an inference, then fetches everything itself and compares the whole vector: event match, classification, peril, exclusion, incident key and date, which pages were bound, severity bucket, the TVL window and the hash of all of it, exactly.

Then the contract, not the model, applies the policy. Evidence about another event: EVIDENCE_MISMATCH — nothing paid, nothing moved, and the buyer may refile with the right evidence or key, twice. Excluded: denied. Covered: `cover × table[bucket] × (1 − deductible)`. Claims on the same incident wait for a settlement window and are paid together, scaled by one factor if the pool is short.

## What went wrong, and how it was fixed

**Evidence for one hack, paid against another.** A review steward found this one, and it was the most important. The first version chose the incident itself: the *latest* DeFi Llama record for the protocol inside the cover window — independently of the evidence. Curve has two records a year apart: a DNS hijack on 9 August 2022 (a front-end attack, excluded by most policies) and the Vyper reentrancy on 30 July 2023 (a code flaw, covered). With a cover spanning both, a claim carrying the DNS article would have been dated, and its severity measured, on the Vyper record — the evidence, the date and the TVL window could describe three different things. Now the claimant names one record by key, every validator selects exactly that row, the TVL window is anchored on it, a page counts only if it dates the same event, the model is asked whether it is the same event, and one hash covers the key, the record, the evidence and the window. The on-chain proof is below.

**The render that never finished.** The source probe said every evidence page rendered fine: rekt.news in 26 seconds, Euler's own post-mortem in 38, byte-identical on independent validators, even hours apart. The first real judgement then sat in GenVM execution for over twenty-five minutes and never produced a result. The model answered in 11 seconds on its own. The TVL history parsed in 18.

So I ran the contract's own code on chain one stage at a time. Stage 1, the incident list: 9 seconds. Stage 2, plus the 9 MB TVL history: 19 seconds. Stage 3, plus rendering the article *after* those two large downloads: it never settled. Rendering alone was fine; rendering after large bodies in the same execution was not. Evidence is now fetched with a plain GET and stripped to text by a hand-written parser in the contract. The whole judgement then took 31 seconds. The cost is written down: a page that only exists after JavaScript runs reads as empty, which is INCONCLUSIVE — never a payout.

**A menu bar that became evidence.** Euler's post-mortem renders its navigation as one-word lines: "Governance", "Developers", "Community". Flattened into sentences, the menu merged with the article's first line into one "sentence" naming both Euler and governance — and `GOVERNANCE_ATTACK` entered the bracket because of a nav link. Sentences are now split on lines first and need five words.

**A strength range that made honest validators disagree about money.** Evidence strength started as a three-step range, and a covered claim needs at least 3. One agreeing source gave the range 1–3, so one validator answering 2 and another answering 3 disagreed about whether the claim *pays* — a disagreement about the width of a range, not about the hack. The range is now one step wide and one agreeing source gives 3–4. Both answers pay.

**The digest that read the wrong half of the post-mortem.** Salient sentences were capped in page order, and a long post-mortem names its protocol in almost every sentence. The first 2,400 characters of Euler's were about the recovery; the paragraph about the flaw was further down. Sentences that carry a risk word are now taken first and the result is put back in page order.

## What it looks like running

On a demo instance whose covers start 1,521 days before they are bought — same bytes as the real one, one constructor value, labelled DEMO everywhere — the seed replayed real incidents. First, the steward's case: one Curve pool, five covers each spanning **both** of Curve's records, 2022-07-31 to 2023-07-31:

- **Vyper article + the 2023-07-30 record** — COVERED, `SMART_CONTRACT_BUG`, the validators said SAME event; TVL fell 49.52% in the Vyper window, bucket 2, paid.
- **Vyper article + the 2022-08-09 record** — EVIDENCE_MISMATCH. The article is dated 31 July 2023, nowhere near 9 August 2022; no model was asked, nothing paid.
- **DNS article + the 2023-07-30 record** — EVIDENCE_MISMATCH, the same way round.
- **DNS article + the 2022-08-09 record** — EXCLUDED, `FRONTEND_HIJACK`, SAME event, bucket 0 in the DNS window.
- **DNS article on the 2023 record, then refiled with the Vyper article** — EVIDENCE_MISMATCH, then COVERED: the claim was not spent by the mistake.

Then the rest:

- **Euler, 2023-03-13** — COVERED, `SMART_CONTRACT_BUG`, TVL drop 95.85%, bucket 4, paid 0.9 GEN on a 1 GEN cover after a 10% deductible. The underwriter contested with Euler's own post-mortem as new evidence; the validators re-read it and the verdict held, so the bond went to the buyer.
- **Multichain, 2023-07-07** — EXCLUDED, `USER_KEY_COMPROMISE`, despite an 89.8% TVL drop.
- **Euler, claimed with its homepage** — INCONCLUSIVE, no model called; the buyer can refile.
- **Two Euler covers on a 50%-collateral pool** — both approved, both scaled by the same factor.
- **Tornado Cash** — a claim left unjudged while the owner paused the contract, unstuck by `settle_stalled` while still paused, then judged.

On the canonical instance, a cover bought today and claimed against Euler's 2023 record was refused at filing — before any source was read or any validator asked — and kept its one claim. That is exactly the point.

## Honest limitations

- **Parametric.** It pays by incident severity measured from TVL, not by proven personal loss. TVL also falls when prices fall.
- **Evidence is only as good as the allowlisted sources**, and pages are read without JavaScript.
- **Classification is subjective.** The bracket bounds it; inside it, a model still chooses.
- **The incident must be in DeFi Llama's list** before a claim can be decided, and at least one evidence page must **date** it (within three days); an undated post-mortem can support a dated article but cannot carry a claim alone.
- **The demo replays history with a fixed backdate.** It is not insurance.
- **Studio Dev may queue a value transfer without executing it**; `get_stats` publishes the gap as `undelivered_wei` rather than hiding it.

## Try it

- App: https://coverclaim.vercel.app
- Code, probe, audit and evidence: https://github.com/kenil1710/coverclaim
- 650 offline tests, every loophole in its own test class, and a script that reads the deployed bytes back off the chain and compares them with the repository.
