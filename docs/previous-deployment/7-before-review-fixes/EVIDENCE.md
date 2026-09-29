# EVIDENCE — the seeded outcomes, read back from the chain

Collected 2026-09-29T12:40:50.371Z by `node test/collect.mjs`, which READS the chain rather than trusting the seed script. Full records: `docs/EVIDENCE.json`; every write with its return value: `docs/seed-evidence.json`; raw log: `docs/seed-run.log`.

- DEMO instance `0xC70DB65CaF6aa8a915b032FBFeBC6600A195F8e7` — DEMO - every cover starts 1521 days before it is bought, fixed at deployment, so that real historical incidents can be replayed. Not insurance.
- Canonical instance `0x8a698aA7eF620260B192b89C141A1dcE168Dfd80`
- CoverRegistry `0x8618B4CC15069B056b5b35AF37B029b27a152cf7`

| | scenario | evidence |
|---|---|---|
| PASS | MIXED EVIDENCE 6 — DNS record, [DNS article, Vyper article]: classified from the DNS page only → EXCLUDED, no payout | claim #6 DENIED_EXCLUDED; FRONTEND_HIJACK; binding "rekt.news/curve-finance-rekt BOUND 2022-08-10 ; rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; judged digest has no Vyper text: true; tx 0xc091466c3ad357936662be01971363e5ac2e3cc4768871284bf66db5dc1c2d04 |
| PASS | MIXED EVIDENCE 7 — Vyper record, [Vyper article, DNS article]: classified from the Vyper page only → COVERED | claim #7 PAID; SMART_CONTRACT_BUG; bucket 2; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31 ; rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; judged digest has no DNS text: true; tx 0x1c35eb86c105ebe08c0e691d8e7dd2be6140a2b98522405dc3044588fd9d56de |
| PASS | POOL VERIFICATION — every pool that sold cover was verified against DeFi Llama; its only protocol domain is the website DeFi Llama lists | #1 euler-v1: domain euler.finance (DeFi Llama https://www.euler.finance); #2 curve-dex: domain curve.finance (DeFi Llama https://curve.finance); #3 multichain: domain none (DeFi Llama lists none); #4 euler-v1: domain euler.finance (DeFi Llama https://www.euler.finance); #5 tornado-cash: domain tornadocash-eth.ipns.inbrowser.link (DeFi Llama https://tornadocash-eth.ipns.inbrowser.link/); 14 demo covers, all on verified pools |
| PASS | VERIFICATION FAILS — declared domain DeFi Llama does not list: cannot sell, premium refused, closed with capital returned | pool #6 declared euler-postmortem.xyz: "declared domain euler-postmortem.xyz is not the website DeFi Llama lists for Euler V1 (https://www.euler.finance)"; covers 0; verify tx 0x74e2aa945dc30c32c69ae9236ff3b43f448288d7769c6c11754adaed754d259e; buy refused 0x637b5fc275870c1a4f979ad18f0741cf95df70ffe977e2f75fa8d503572c12c0; closed 0xf4dd0b93cdd9828ae57b27d4c4f410441928af599adf299a687206a856ff8775 |
| PASS | VERIFICATION FAILS — slug and id of different protocols: cannot sell, closed with capital returned | pool #7 curve-dex/1183: "slug curve-dex is DeFi Llama id 3, not 1183: slug and id are different protocols"; verify tx 0x1029699762bacb6bfaa701b38b48177e1e22d7d342ad8d47460be038cb6f8a07; buy refused 0x31f4c63db9a64d0ed82d8a4b7382f49c36438aa8caa8cecb6da9919078237404 |
| PASS | CONTEST FROM AN UNVERIFIED DOMAIN — refused before GenLayer (underwriter's own domain; protocol domain DeFi Llama does not list) | demo-contest-unverified-domain: "evidence refused before judging: euler-postmortem.xyz is not on this pool's frozen evidence allowlist" tx 0x496b7b1c30d963739e5d95baac30d8ff9d2d57296d9a389ef6257955f934aa8f; demo-contest-unlisted-domain: "evidence refused before judging: multichain.org is not on this pool's frozen evidence allowlist" tx 0x9fe3aaf6ac25acd5fc1dac6124a9f773e6c2118cbc43af4a1122276037f893be |
| PASS | ONE PAYOUT PER COVER (double-payout regression, structural) — every batch lists each claim once; no cover paid twice; payouts ≤ locked capacity | 3 batches: #1 3:2023-07-30:curve dex members [1,5,7] paid 0.675000 ≤ locked 1.500000; #2 1183:2023-03-13:euler v1 members [8] paid 0.900000 ≤ locked 1.000000; #3 1183:2023-03-13:euler v1 members [11,12] paid 1.000000 ≤ locked 1.000000 |
| PASS | COVERED — Euler V1 2023-03-13 paid at its severity bucket | claim #8 PAID; SMART_CONTRACT_BUG; bucket 4 (drop 9585 bps); gross 0.900000 GEN, paid 0.900000 GEN; judge tx 0xe4e4361d06c013dbe7fd6c2ffa22510b683ec7d2a66f89044c2b27e65a242a3e |
| PASS | CONTESTED — underwriter contests with novel evidence, verdict held | contest UPHELD; re-read as COVERED strength 7; novel 2367 chars; tx 0x7ea0c8aded7603a4a41d51d44b5c9d6cf66b252fad893626ce156127eefcfe58 |
| PASS | MULTI-INCIDENT 1 — Curve: Vyper evidence + 2023-07-30 record → COVERED, paid at the Vyper window's severity | claim #1 PAID; key 3:2023-07-30; event SAME; SMART_CONTRACT_BUG; bucket 2 (drop 4952 bps); paid 0.225000 GEN; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31"; verify hash/record/window true/true/true; tx 0xa6b5e662c3a2d237be22a20b7b273ff76e3cf102417d6d3629e020d7ef190cdf |
| PASS | MULTI-INCIDENT 2 — Curve: Vyper evidence + 2022-08-09 record → EVIDENCE_MISMATCH, no payout | claim #2 EVIDENCE_MISMATCH; key 3:2022-08-09; event DIFFERENT; model_called false; binding "rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; gross 0; tx 0x80a2b3798b4543f060530b5e5b2c9e8ebed3c6a0a7c31623dac46dea86ac98d5 |
| PASS | MULTI-INCIDENT 3 — Curve: DNS evidence + 2023-07-30 record → EVIDENCE_MISMATCH, no payout | claim #3 EVIDENCE_MISMATCH; key 3:2023-07-30; event DIFFERENT; model_called false; binding "rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; gross 0; tx 0x92909b926bde95e10f89c0f51d558a3e0a827d74997a7de5abfd7ba901cfabae |
| PASS | MULTI-INCIDENT 4 — Curve: DNS evidence + 2022-08-09 record → EXCLUDED (FRONTEND_HIJACK) | claim #4 DENIED_EXCLUDED; key 3:2022-08-09; event SAME; FRONTEND_HIJACK; bucket 0 (DNS window, not paid: excluded); tx 0xf4d8dbffab16030debf94a2523adfd8e1fac34b9c19c7a9d6eb7ec6fa0de9851 |
| PASS | MULTI-INCIDENT 5 — refile after mismatch: DNS evidence on the 2023 record, refiled with the Vyper report → COVERED | claim #5 first EVIDENCE_MISMATCH (tx 0x1735e2b92dd6131a08ae0d6b8708cd7c988cc14acb8e82c016769a65bb840603), refiled (tx 0x6fba177701f5e4e72cd2f3c0b748346fe31880ecf54ffb011680dc8acf8a2b79), then PAID bucket 2, paid 0.225000 GEN (tx 0xadd788bad11607436d3e1af644a34657c6270030bab721b398acabf7e992144a) |
| PASS | EXCLUDED — Multichain key compromise 2023-07-07 | claim #9 DENIED_EXCLUDED; USER_KEY_COMPROMISE; incident 2023-07-07; bucket 3 (not paid: excluded); tx 0x3cc125af28df10bd6148a40b96bc107dab3b3b3a1d9bc8d4bde2c266870e1e3a |
| PASS | INCONCLUSIVE — evidence that does not classify; refile allowed | claim #10 INCONCLUSIVE; model_called false; "the evidence names no peril and no exclusion; there is nothing to classify"; refile until 1790685280; tx 0xb169cf5420edc93005c47b4153d4b4abe5a0ecf3b86e13d0180d93e187dab404 |
| PASS | PRO-RATA — two claims on one incident, keyed two ways ("1183:2023-03-13" / "…:Euler V1"), one canonical incident, one batch, both scaled | keys 1183:2023-03-13 / 1183:2023-03-13:Euler V1 → incident 1183:2023-03-13:euler v1; batch #3 scaled=true; approved 1.800000 vs locked 1.000000 GEN; paid 0.500000 + 0.500000 GEN; dust 0 wei; tx 0xc8198ca7d62149216489c8a0f14a781f1e266e64e1b5071d06ed71b4b3fe57ed |
| PASS | EXPIRED — cover expires unclaimed, premium to the underwriter | cover #8 RELEASED; premium 0.000066 GEN earned; tx 0x6b29effa7236bcaea251186400d00b1811149a17bc72b61904cef634ee9872b3 |
| PASS | STALLED — settled while paused | claim #13 stalls=1, then DENIED_EXCLUDED (GOVERNANCE_ATTACK); settle tx 0x9ffaa692c4954b3d541d690407d5cb9ff693c07173b0d9c387af4e7347034d72 (paused by 0x457e1942a91866a1831ae56b24d2d76aa4b7a61b1e487fa113bca97cdb458d1a) |
| PASS | BACKDATED — canonical cover bought after the incident: claim keyed to it refused at filing, before any model call; the cover keeps its one claim | canonical cover #1 claim_id 0; "incident refused before judging: incident 1183:2023-03-13 predates this cover's start plus its waiting period (2026-09-29); it is not covered and is refused before judging"; tx 0x8585c4498c3df5fb77284ab868c1967203a8e65440253b1036ac7518b9561ea6 |
| PASS | CoverRegistry attests a live canonical cover | attestation #0 covered=true cover #2 curve-dex; tx 0x9002078bbd5dc5528b68d2d3b650c1f3a3f2783d3b578cbdb598b073c1964499 |
| PASS | WAITING-PERIOD GATE — claim filed inside the waiting period refused mechanically; the one claim is not spent | canonical cover #3: "cover waiting period has not ended yet, claimable after 1791290164"; claim_id still 0; tx 0x56b756d48fc99221b047fc865586caa83cca4c31ab15c6c62844b75b47282935 |
| PASS | DRAINED — every demo pool closed, books at exactly 0 wei | 7 pools CLOSED; balance 0 = held 0 + payable 0 wei; locked 0; undelivered_wei 14336233333333333341 (Studio Dev transfers posted, not executed) |
| PASS | Ledger identity holds on both instances | demo balance 0.000000 = held 0.000000 + payable 0.000000; canonical 5.021000 = 5.021000 + 0.000000 |

## The books

Demo: balance 0.000000 GEN = held 0.000000 + payable 0.000000; capital 0.000000, locked 0.000000, paid out 2.575000, claimed 14.336233. Real chain balance 14.336233 GEN; undelivered_wei 14336233333333333341.

## Claims (demo)

| # | protocol | incident key | status | event | classification | peril / exclusion | bucket | strength | model | content hash |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Curve | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `d9678928fc154a5d` |
| 2 | Curve | `3:2022-08-09` | EVIDENCE_MISMATCH | DIFFERENT | INCONCLUSIVE | NONE | 0 | 0 | false | `6fc7b5bcac73027e` |
| 3 | Curve | `3:2023-07-30` | EVIDENCE_MISMATCH | DIFFERENT | INCONCLUSIVE | NONE | 2 | 0 | false | `dcd53101fc0b096b` |
| 4 | Curve | `3:2022-08-09` | DENIED_EXCLUDED | SAME | EXCLUDED | FRONTEND_HIJACK | 0 | 4 | true | `e45e321fa3fab96c` |
| 5 | Curve | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `d9678928fc154a5d` |
| 6 | Curve | `3:2022-08-09` | DENIED_EXCLUDED | SAME | EXCLUDED | FRONTEND_HIJACK | 0 | 4 | true | `93e27c42f6286edd` |
| 7 | Curve | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `c165594ec221d939` |
| 8 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `284b2c6b1c480bba` |
| 9 | Multichain | `591:2023-07-07` | DENIED_EXCLUDED | SAME | EXCLUDED | USER_KEY_COMPROMISE | 3 | 4 | true | `1bc69d88bd710aed` |
| 10 | Euler | `1183:2023-03-13` | INCONCLUSIVE | NOT_ASKED | INCONCLUSIVE | NONE | 4 | 0 | false | `a3cef23b62bff0ae` |
| 11 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `284b2c6b1c480bba` |
| 12 | Euler | `1183:2023-03-13:Euler V1` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `9569a088402a418b` |
| 13 | Tornado Cash | `148:2023-05-20` | DENIED_EXCLUDED | SAME | EXCLUDED | GOVERNANCE_ATTACK | 0 | 4 | true | `865a117ad1baa73d` |

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
