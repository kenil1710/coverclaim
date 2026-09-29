# EVIDENCE — the seeded outcomes, read back from the chain

This run is **scoped** (round-2 review): the full Curve proof, pro-rata, a contest, an evidence-outage retry and the early-judging refusal. The previous deployment's full evidence — every scenario — is archived in [docs/superseded/](superseded/) (and earlier deployments in [docs/previous-deployment/](previous-deployment/)).

Collected 2026-09-29T16:25:02.776Z by `node test/collect.mjs`, which READS the chain rather than trusting the seed script. Full records: `docs/EVIDENCE.json`; every write with its return value: `docs/seed-evidence.json`; raw log: `docs/seed-run.log`.

- DEMO instance `0x6FaA9942421467BA5A386B455a71f3baB04aDE84` — DEMO - every cover starts 1521 days before it is bought, fixed at deployment, so that real historical incidents can be replayed. Not insurance.
- Canonical instance `0x71Bf9047F8B2DDFEf086116846fb65d2a974719f`
- CoverRegistry `0x1e6D0F18F82A1B73C0Afd36799703CA5Ed8A111f`

| | scenario | evidence |
|---|---|---|
| PASS | EVIDENCE OUTAGE — a page answering 500 during judging is a RETRY: nothing settles, the claim stays FILED, no refile spent; replaced after the stall window, it is judged and paid | claim #11: judge → RETRY ("evidence page https://rekt.news/coverclaim-evidence-outage-probe answered 500", tx 0x44407ea98c1808e0d9e30ca97673453f2f961a4a6c404de3a3f72ba8df234dd1); stall-settled 0x0e53875ce0a7251f40d04753ef6e3988a400c5aecbcd552af484f7c97afb1f12; refiled 0x48e8693a2904da359a977549b3d64aea066e6b2b74ad7e9d2c18ab1190587431; judged PAID, paid 0.450000 GEN (tx 0xb0b4058a5f0804ea8ed4bba25f8219aac9088cf50cb2cbb53bb6fb32940c46ae) |
| PASS | EARLY JUDGING REFUSED — a claim on an incident whose 7-day TVL window has not ended cannot be judged (staging instance, same bytes) | staging 0x2692A892fDC84f2f83C0eDf139BEEd03FC362d6F claim #1 key 1183:2026-09-29: "the 7-day TVL window of incident 1183:2026-09-29 has not ended; claim #1 can be judged from 1791331200"; judgeable_at 1791331200 (2026-10-07); claim still FILED; tx 0x7397256dbc4e172f33c9dbeb4aa53a2849ff8b4894f2b806bf0435138a87ccbb |
| PASS | MIXED EVIDENCE 6 — DNS record, [DNS article, Vyper article]: classified from the DNS page only → EXCLUDED, no payout | claim #6 DENIED_EXCLUDED; FRONTEND_HIJACK; binding "rekt.news/curve-finance-rekt BOUND 2022-08-10 ; rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; judged digest has no Vyper text: true; tx 0xa75d8459ca1719fa55363dfd5bf792680ffeda8a3363ab861f81e3fb44ddd620 |
| PASS | MIXED EVIDENCE 7 — Vyper record, [Vyper article, DNS article]: classified from the Vyper page only → COVERED | claim #7 PAID; SMART_CONTRACT_BUG; bucket 2; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31 ; rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; judged digest has no DNS text: true; tx 0x0ad3a9ecd9cd40834db990ff1c7945a2739ae359d9c146f33ae5d392b512320c |
| PASS | POOL VERIFICATION — every pool that sold cover was verified against DeFi Llama; its only protocol domain is the website DeFi Llama lists | #1 euler-v1: domain euler.finance (DeFi Llama https://www.euler.finance); #2 curve-dex: domain curve.finance (DeFi Llama https://curve.finance); #3 euler-v1: domain euler.finance (DeFi Llama https://www.euler.finance); 11 demo covers, all on verified pools |
| PASS | ONE PAYOUT PER COVER (double-payout regression, structural) — every batch lists each claim once; no cover paid twice; payouts ≤ locked capacity | 3 batches: #1 3:2023-07-30:curve dex members [1,5,7] paid 0.675000 ≤ locked 1.500000; #2 1183:2023-03-13:euler v1 members [8,11] paid 1.350000 ≤ locked 1.500000; #3 1183:2023-03-13:euler v1 members [9,10] paid 1.000000 ≤ locked 1.000000 |
| PASS | CORE NAME — the Curve proof runs on a pool named "Curve DEX" (DeFi Llama's own name); verification stored the core name "Curve", which the evidence names | pool #2 "Curve DEX" → core "Curve"; claim #1 PAID, protocol named: true |
| PASS | COVERED — Euler V1 2023-03-13 paid at its severity bucket | claim #8 PAID; SMART_CONTRACT_BUG; bucket 4 (drop 9585 bps); gross 0.900000 GEN, paid 0.900000 GEN; judge tx 0x1bce79c2168b784768504127bbf0b0d1660f6efcb2012b7b96ff2b2b69b4044a |
| PASS | CONTESTED — underwriter contests with novel evidence, verdict held | contest UPHELD; re-read as COVERED strength 7; novel 2367 chars; tx 0x68ba9dceae1c7d353f553f44f3f7e68acface2f94fcc9566850cd0e81c48726c |
| PASS | MULTI-INCIDENT 1 — Curve: Vyper evidence + 2023-07-30 record → COVERED, paid at the Vyper window's severity | claim #1 PAID; key 3:2023-07-30; event SAME; SMART_CONTRACT_BUG; bucket 2 (drop 4952 bps); paid 0.225000 GEN; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31"; verify hash/record/window true/true/true; tx 0x617fb420bb466ce44e45d9c9fae0b9e9b62a8d4c58ac514d40c7e1fb9438c28c |
| PASS | MULTI-INCIDENT 2 — Curve: Vyper evidence + 2022-08-09 record → EVIDENCE_MISMATCH, no payout | claim #2 EVIDENCE_MISMATCH; key 3:2022-08-09; event DIFFERENT; model_called false; binding "rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; gross 0; tx 0xceb737f10dcf020861bb58574e13b64d02d7f848e66d291c9d92d8034d1757db |
| PASS | MULTI-INCIDENT 3 — Curve: DNS evidence + 2023-07-30 record → EVIDENCE_MISMATCH, no payout | claim #3 EVIDENCE_MISMATCH; key 3:2023-07-30; event DIFFERENT; model_called false; binding "rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; gross 0; tx 0x34dae23466a0b44b5fc2a0e557e32282d8075fc654cd01dc6dbb8d12bc5c9495 |
| PASS | MULTI-INCIDENT 4 — Curve: DNS evidence + 2022-08-09 record → EXCLUDED (FRONTEND_HIJACK) | claim #4 DENIED_EXCLUDED; key 3:2022-08-09; event SAME; FRONTEND_HIJACK; bucket 0 (DNS window, not paid: excluded); tx 0x8c60d433fab0a03b9d0cecf8ce20c939d840106d7d096f7bcc3c13fc3427bdec |
| PASS | MULTI-INCIDENT 5 — refile after mismatch: DNS evidence on the 2023 record, refiled with the Vyper report → COVERED | claim #5 first EVIDENCE_MISMATCH (tx 0x44b84a47d2ece59729d0fd66036f8cd728db1cbe0ba4121a3e28e9c69b04fde5), refiled (tx 0x887a56c9a1345044631fc404f06879924464781b9a2b8b21e85f69f4b3a16066), then PAID bucket 2, paid 0.225000 GEN (tx 0x233398d8cf04133c289600b80e3b7010fdb2be0129933868961cd0a70de97ab0) |
| PASS | PRO-RATA — two claims on one incident, keyed two ways ("1183:2023-03-13" / "…:Euler V1"), one canonical incident, one batch, both scaled | keys 1183:2023-03-13 / 1183:2023-03-13:Euler V1 → incident 1183:2023-03-13:euler v1; batch #3 scaled=true; approved 1.800000 vs locked 1.000000 GEN; paid 0.500000 + 0.500000 GEN; dust 0 wei; tx 0xf766864ec07c64eb3079d647a7a8a67da7de2d2a29c9d1a675958e03a27d6346 |
| PASS | DRAINED — every demo pool closed, books at exactly 0 wei | 3 pools CLOSED; balance 0 = held 0 + payable 0 wei; locked 0; undelivered_wei 8951666666666666673 (Studio Dev transfers posted, not executed) |
| PASS | Ledger identity holds on both instances | demo balance 0.000000 = held 0.000000 + payable 0.000000; canonical 0.000000 = 0.000000 + 0.000000 |

## The books

Demo: balance 0.000000 GEN = held 0.000000 + payable 0.000000; capital 0.000000, locked 0.000000, paid out 3.025000, claimed 8.951666. Real chain balance 8.951666 GEN; undelivered_wei 8951666666666666673.

## Claims (demo)

| # | protocol | incident key | status | event | classification | peril / exclusion | bucket | strength | model | content hash |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Curve DEX | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `df4975ad13d24e08` |
| 2 | Curve DEX | `3:2022-08-09` | EVIDENCE_MISMATCH | DIFFERENT | INCONCLUSIVE | NONE | 0 | 0 | false | `6ab2db2246bcf44d` |
| 3 | Curve DEX | `3:2023-07-30` | EVIDENCE_MISMATCH | DIFFERENT | INCONCLUSIVE | NONE | 2 | 0 | false | `e8b0ece3cff1e792` |
| 4 | Curve DEX | `3:2022-08-09` | DENIED_EXCLUDED | SAME | EXCLUDED | FRONTEND_HIJACK | 0 | 4 | true | `9e1fbb9a9cf042bf` |
| 5 | Curve DEX | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `df4975ad13d24e08` |
| 6 | Curve DEX | `3:2022-08-09` | DENIED_EXCLUDED | SAME | EXCLUDED | FRONTEND_HIJACK | 0 | 4 | true | `ea8ef79182e1504a` |
| 7 | Curve DEX | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `3ada7767656869dc` |
| 8 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `ec52441004e5e5fc` |
| 9 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `ec52441004e5e5fc` |
| 10 | Euler | `1183:2023-03-13:Euler V1` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `942ff7a157090fee` |
| 11 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `ec52441004e5e5fc` |

## The multi-incident proof, page by page

One Curve pool, one cover window (2022-07-31 start, waiting 7 days, 365 days), two DeFi Llama records inside it: `3:2022-08-09` (DNS hijack) and `3:2023-07-30` (Vyper reentrancy).

| claim | key | evidence binding | event | outcome | TVL window |
|---|---|---|---|---|---|
| #1 | `3:2023-07-30` | `rekt.news/curve-vyper-rekt BOUND 2023-07-31` | SAME | PAID | `TVL id 3 anchor 2023-07-30 before 2023-07-29=3127360057 window 2023-07-30=3133650761;2023-…` |
| #2 | `3:2022-08-09` | `rekt.news/curve-vyper-rekt UNBOUND 2023-07-31` | DIFFERENT | EVIDENCE_MISMATCH | `TVL id 3 anchor 2022-08-09 before 2022-08-08=6075356908 window 2022-08-09=6170017659;2022-…` |
| #3 | `3:2023-07-30` | `rekt.news/curve-finance-rekt UNBOUND 2022-08-10` | DIFFERENT | EVIDENCE_MISMATCH | `TVL id 3 anchor 2023-07-30 before 2023-07-29=3127360057 window 2023-07-30=3133650761;2023-…` |
| #4 | `3:2022-08-09` | `rekt.news/curve-finance-rekt BOUND 2022-08-10` | SAME | DENIED_EXCLUDED | `TVL id 3 anchor 2022-08-09 before 2022-08-08=6075356908 window 2022-08-09=6170017659;2022-…` |
| #5 | `3:2023-07-30` | `rekt.news/curve-vyper-rekt BOUND 2023-07-31` | SAME | PAID | `TVL id 3 anchor 2023-07-30 before 2023-07-29=3127360057 window 2023-07-30=3133650761;2023-…` |
| #6 | `3:2022-08-09` | `rekt.news/curve-finance-rekt BOUND 2022-08-10 ; rekt.news/curve-vyper-rekt UNBOUND 2023-07-31` | SAME | DENIED_EXCLUDED | `TVL id 3 anchor 2022-08-09 before 2022-08-08=6075356908 window 2022-08-09=6170017659;2022-…` |
| #7 | `3:2023-07-30` | `rekt.news/curve-vyper-rekt BOUND 2023-07-31 ; rekt.news/curve-finance-rekt UNBOUND 2022-08-10` | SAME | PAID | `TVL id 3 anchor 2023-07-30 before 2023-07-29=3127360057 window 2023-07-30=3133650761;2023-…` |
