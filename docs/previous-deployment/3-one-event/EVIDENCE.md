# EVIDENCE — the seeded outcomes, read back from the chain

Collected 2026-09-29T06:31:25.231Z by `node test/collect.mjs`, which READS the chain rather than trusting the seed script. Full records: `docs/EVIDENCE.json`; every write with its return value: `docs/seed-evidence.json`; raw log: `docs/seed-run.log`.

- DEMO instance `0x0DF0bCF182151B248A8d5ac8c4b2d48f2127355C` — DEMO - every cover starts 1521 days before it is bought, fixed at deployment, so that real historical incidents can be replayed. Not insurance.
- Canonical instance `0x64DA264e7cBba10E0aA36Dfb0ed12aDB8c9EBDD3`
- CoverRegistry `0x10f4E23623417098f7d730aB98E576dC9A5bEE70`

| | scenario | evidence |
|---|---|---|
| PASS | COVERED — Euler V1 2023-03-13 paid at its severity bucket | claim #6 PAID; SMART_CONTRACT_BUG; bucket 4 (drop 9585 bps); gross 0.900000 GEN, paid 0.900000 GEN; judge tx 0x2a164168892318c0b4317a9f0b4791a9d375790577c102536a411032d3bf088a |
| PASS | CONTESTED — underwriter contests with novel evidence, verdict held | contest UPHELD; re-read as COVERED strength 7; novel 2367 chars; tx 0x966d586671f61f951a74391b4fcd066ac873d16281b3ebc46ef8e0de7199c151 |
| PASS | MULTI-INCIDENT 1 — Curve: Vyper evidence + 2023-07-30 record → COVERED, paid at the Vyper window's severity | claim #1 PAID; key 3:2023-07-30; event SAME; SMART_CONTRACT_BUG; bucket 2 (drop 4952 bps); paid 0.225000 GEN; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31"; verify hash/record/window true/true/true; tx 0xa790c297f2a00ca8455a57a67f186314a2539d7d0c3f7c1648037e53158be974 |
| PASS | MULTI-INCIDENT 2 — Curve: Vyper evidence + 2022-08-09 record → EVIDENCE_MISMATCH, no payout | claim #2 EVIDENCE_MISMATCH; key 3:2022-08-09; event DIFFERENT; model_called false; binding "rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; gross 0; tx 0xf68f42dcd00d03bc4b5733734dccf11053ec9e5abdff4d7106cd8311480fc8be |
| PASS | MULTI-INCIDENT 3 — Curve: DNS evidence + 2023-07-30 record → EVIDENCE_MISMATCH, no payout | claim #3 EVIDENCE_MISMATCH; key 3:2023-07-30; event DIFFERENT; model_called false; binding "rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; gross 0; tx 0x4933d14e83df225024c2e69dc7c6aa2e1bc0c155c54d6c5ffed2a7bef73650de |
| PASS | MULTI-INCIDENT 4 — Curve: DNS evidence + 2022-08-09 record → EXCLUDED (FRONTEND_HIJACK) | claim #4 DENIED_EXCLUDED; key 3:2022-08-09; event SAME; FRONTEND_HIJACK; bucket 0 (DNS window, not paid: excluded); tx 0x4cec88e87eb3dd56dde9ba9ee6799b75052498d4973f190e3d1f198a48e07b3d |
| PASS | MULTI-INCIDENT 5 — refile after mismatch: DNS evidence on the 2023 record, refiled with the Vyper report → COVERED | claim #5 first EVIDENCE_MISMATCH (tx 0x4c20224aaabf591d6177e152c8ce5316ca09ae26bbf74dfd6da1bd5414e407d0), refiled (tx 0xae9aee3959aa31ddacd71c08597619aa4b04fd5cb22cd04655a87cee792d79ea), then PAID bucket 2, paid 0.225000 GEN (tx 0xeeaaffb0a33bd08080765cdc0c84a52ae63b92e1aa52428878f971fd2309dbf2) |
| PASS | EXCLUDED — Multichain key compromise 2023-07-07 | claim #7 DENIED_EXCLUDED; USER_KEY_COMPROMISE; incident 2023-07-07; bucket 3 (not paid: excluded); tx 0x3f407a30547b53c0c8f2f5447b54ea2f1e1b3866a7d7af905e6b0eab816f8a2a |
| PASS | INCONCLUSIVE — evidence that does not classify; refile allowed | claim #8 INCONCLUSIVE; model_called false; "the evidence names no peril and no exclusion; there is nothing to classify"; refile until 1790662595; tx 0x619565777c7c7084a1d9dd98841641579d2e110483bd8b580f4d71efff1c9b08 |
| PASS | PRO-RATA — two claims on one incident, capacity short, both scaled | batch #3 scaled=true; approved 1.800000 vs locked 1.000000 GEN; paid 0.500000 + 0.500000 GEN; dust 0 wei; tx 0x4794e8589d136187d5b371577ce5921b7fc13ae75d026bd62378023ce8b4e854 |
| PASS | EXPIRED — cover expires unclaimed, premium to the underwriter | cover #6 RELEASED; premium 0.000066 GEN earned; tx 0x1d0ed16f4b5c2828bad35fd8bf4a2cb8b23c8cf12bdf3e538ff8fb8db3b9486e |
| PASS | STALLED — settled while paused | claim #11 stalls=1, then DENIED_EXCLUDED (GOVERNANCE_ATTACK); settle tx 0xd197d1a3bfe226ec46bda65ba344e82f032d863dfdeddce214e10f894a2aca55 (paused by 0xde26bf624e544bd4ef3352c63fe9e58dc5af5ab3ec1892339e80fc89ed3c926e) |
| PASS | BACKDATED — canonical cover bought after the incident: claim keyed to it refused at filing, before any model call; the cover keeps its one claim | canonical cover #1 claim_id 0; "incident refused before judging: incident 1183:2023-03-13 predates this cover's start plus its waiting period (2026-09-29); it is not covered and is refused before judging"; tx 0x7eef0f81ccdca5ff9258709dc831077774d2f997fddda7c0f18569f138547d07 |
| PASS | CoverRegistry attests a live canonical cover | attestation #0 covered=true cover #2 curve-dex; tx 0x5ddfee9c68ca66bd7d7ce91d464514485b38570be7068541d566de621bc1eb85 |
| PASS | WAITING-PERIOD GATE — claim filed inside the waiting period refused mechanically; the one claim is not spent | canonical cover #3: "cover waiting period has not ended yet, claimable after 1791267569"; claim_id still 0; tx 0x0fcbed7bad7ed945a1a8446e23b4e445b5f97e143f9bae26e796abad8a78ac72 |
| PASS | DRAINED — every demo pool closed, books at exactly 0 wei | 5 pools CLOSED; balance 0 = held 0 + payable 0 wei; locked 0; undelivered_wei 11012566666666666673 (Studio Dev transfers posted, not executed) |
| PASS | Ledger identity holds on both instances | demo balance 0.000000 = held 0.000000 + payable 0.000000; canonical 5.021000 = 5.021000 + 0.000000 |

## The books

Demo: balance 0.000000 GEN = held 0.000000 + payable 0.000000; capital 0.000000, locked 0.000000, paid out 2.350000, claimed 11.012566. Real chain balance 11.012566 GEN; undelivered_wei 11012566666666666673.

## Claims (demo)

| # | protocol | incident key | status | event | classification | peril / exclusion | bucket | strength | model | content hash |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Curve | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `7b244fb5a5ef1dbd` |
| 2 | Curve | `3:2022-08-09` | EVIDENCE_MISMATCH | DIFFERENT | INCONCLUSIVE | NONE | 0 | 0 | false | `e4db574b4f52ad5e` |
| 3 | Curve | `3:2023-07-30` | EVIDENCE_MISMATCH | DIFFERENT | INCONCLUSIVE | NONE | 2 | 0 | false | `b6bc02b93277364b` |
| 4 | Curve | `3:2022-08-09` | DENIED_EXCLUDED | SAME | EXCLUDED | FRONTEND_HIJACK | 0 | 4 | true | `8e3568c652f64ccc` |
| 5 | Curve | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `7b244fb5a5ef1dbd` |
| 6 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `1a86f5532cf16402` |
| 7 | Multichain | `591:2023-07-07` | DENIED_EXCLUDED | SAME | EXCLUDED | USER_KEY_COMPROMISE | 3 | 4 | true | `34176f41865d6887` |
| 8 | Euler | `1183:2023-03-13` | INCONCLUSIVE | NOT_ASKED | INCONCLUSIVE | NONE | 4 | 0 | false | `196b5ea9db315453` |
| 9 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `1a86f5532cf16402` |
| 10 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `039b5c66144fe003` |
| 11 | Tornado Cash | `148:2023-05-20` | DENIED_EXCLUDED | SAME | EXCLUDED | GOVERNANCE_ATTACK | 0 | 4 | true | `ac3d72dd718832b7` |

## The multi-incident proof, page by page

One Curve pool, one cover window (2022-07-31 start, waiting 7 days, 365 days), two DeFi Llama records inside it: `3:2022-08-09` (DNS hijack) and `3:2023-07-30` (Vyper reentrancy).

| claim | key | evidence binding | event | outcome | TVL window |
|---|---|---|---|---|---|
| #1 | `3:2023-07-30` | `rekt.news/curve-vyper-rekt BOUND 2023-07-31` | SAME | PAID | `TVL id 3 anchor 2023-07-30 before 2023-07-29=3127360057 window 2023-07-30=3133650761;2023-…` |
| #2 | `3:2022-08-09` | `rekt.news/curve-vyper-rekt UNBOUND 2023-07-31` | DIFFERENT | EVIDENCE_MISMATCH | `TVL id 3 anchor 2022-08-09 before 2022-08-08=6075356908 window 2022-08-09=6170017659;2022-…` |
| #3 | `3:2023-07-30` | `rekt.news/curve-finance-rekt UNBOUND 2022-08-10` | DIFFERENT | EVIDENCE_MISMATCH | `TVL id 3 anchor 2023-07-30 before 2023-07-29=3127360057 window 2023-07-30=3133650761;2023-…` |
| #4 | `3:2022-08-09` | `rekt.news/curve-finance-rekt BOUND 2022-08-10` | SAME | DENIED_EXCLUDED | `TVL id 3 anchor 2022-08-09 before 2022-08-08=6075356908 window 2022-08-09=6170017659;2022-…` |
| #5 | `3:2023-07-30` | `rekt.news/curve-vyper-rekt BOUND 2023-07-31` | SAME | PAID | `TVL id 3 anchor 2023-07-30 before 2023-07-29=3127360057 window 2023-07-30=3133650761;2023-…` |
