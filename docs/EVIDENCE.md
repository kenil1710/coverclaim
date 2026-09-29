# EVIDENCE — the seeded outcomes, read back from the chain

Collected 2026-09-29T09:22:04.187Z by `node test/collect.mjs`, which READS the chain rather than trusting the seed script. Full records: `docs/EVIDENCE.json`; every write with its return value: `docs/seed-evidence.json`; raw log: `docs/seed-run.log`.

- DEMO instance `0x02A81134c4aCc85386Ad092Bcd2EB55809df15a9` — DEMO - every cover starts 1521 days before it is bought, fixed at deployment, so that real historical incidents can be replayed. Not insurance.
- Canonical instance `0x8a7e766b9221fA55A5d6d868f6ed0Adaa16a93D3`
- CoverRegistry `0x325A84972a8D86D94bFb4301CA04312B15Cf2F99`

| | scenario | evidence |
|---|---|---|
| PASS | MIXED EVIDENCE 6 — DNS record, [DNS article, Vyper article]: classified from the DNS page only → EXCLUDED, no payout | claim #6 DENIED_EXCLUDED; FRONTEND_HIJACK; binding "rekt.news/curve-finance-rekt BOUND 2022-08-10 ; rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; judged digest has no Vyper text: true; tx 0x718b1a7cb6cbfdee948e7ec14fc560d2de7ce00103db1a16d5ab627c66e29de4 |
| PASS | MIXED EVIDENCE 7 — Vyper record, [Vyper article, DNS article]: classified from the Vyper page only → COVERED | claim #7 PAID; SMART_CONTRACT_BUG; bucket 2; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31 ; rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; judged digest has no DNS text: true; tx 0x9095fc70fe6fe8c0f270c0cb1beb78dc96e7751eee7a4187e8d8acd3a4e34f14 |
| PASS | COVERED — Euler V1 2023-03-13 paid at its severity bucket | claim #8 PAID; SMART_CONTRACT_BUG; bucket 4 (drop 9585 bps); gross 0.900000 GEN, paid 0.900000 GEN; judge tx 0x3bad9783b62219a86530144e9a6ae457a55090ccbc6c171cf59c692108426586 |
| PASS | CONTESTED — underwriter contests with novel evidence, verdict held | contest UPHELD; re-read as COVERED strength 7; novel 2367 chars; tx 0x4fa1576123a69df0c541aa799b3302b185dc6c767619a86058bc1b4748f19224 |
| PASS | MULTI-INCIDENT 1 — Curve: Vyper evidence + 2023-07-30 record → COVERED, paid at the Vyper window's severity | claim #1 PAID; key 3:2023-07-30; event SAME; SMART_CONTRACT_BUG; bucket 2 (drop 4952 bps); paid 0.225000 GEN; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31"; verify hash/record/window true/true/true; tx 0xba9299bfa20d5641228e2c15384127f5ea376cfc101163070b712c428dea693c |
| PASS | MULTI-INCIDENT 2 — Curve: Vyper evidence + 2022-08-09 record → EVIDENCE_MISMATCH, no payout | claim #2 EVIDENCE_MISMATCH; key 3:2022-08-09; event DIFFERENT; model_called false; binding "rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; gross 0; tx 0x99d79d65309427de6a655f7451494088a8287b8d88c3243ee698f3377b73d28f |
| PASS | MULTI-INCIDENT 3 — Curve: DNS evidence + 2023-07-30 record → EVIDENCE_MISMATCH, no payout | claim #3 EVIDENCE_MISMATCH; key 3:2023-07-30; event DIFFERENT; model_called false; binding "rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; gross 0; tx 0x85379cae7696b56bb2cb7a3d6dec31c78f90a59b1d602e5e6769f82ced502ddb |
| PASS | MULTI-INCIDENT 4 — Curve: DNS evidence + 2022-08-09 record → EXCLUDED (FRONTEND_HIJACK) | claim #4 DENIED_EXCLUDED; key 3:2022-08-09; event SAME; FRONTEND_HIJACK; bucket 0 (DNS window, not paid: excluded); tx 0xb9682a340416807cf012194adfdfacb3e8e5ed8feab53c3aca2d1a0b4153b437 |
| PASS | MULTI-INCIDENT 5 — refile after mismatch: DNS evidence on the 2023 record, refiled with the Vyper report → COVERED | claim #5 first EVIDENCE_MISMATCH (tx 0xf36b6caa57b80dc2e5e23c52381f3c567c7e46cd7f99f27b764a14f40938336e), refiled (tx 0xe0e7538367a66f17b58b648d3e2a66e3e16d01a41e309a487bb34bc9aefb5b44), then PAID bucket 2, paid 0.225000 GEN (tx 0xa841ac4034cb3d6570b3a8868126edffd26c6ef85759686c8ff934eda385a60c) |
| PASS | EXCLUDED — Multichain key compromise 2023-07-07 | claim #9 DENIED_EXCLUDED; USER_KEY_COMPROMISE; incident 2023-07-07; bucket 3 (not paid: excluded); tx 0x3dc0928eb8fa0a2ade2cb50ed8512a562f9a9474606057507fdbb7aabfd909df |
| PASS | INCONCLUSIVE — evidence that does not classify; refile allowed | claim #10 INCONCLUSIVE; model_called false; "the evidence names no peril and no exclusion; there is nothing to classify"; refile until 1790673441; tx 0xb88ca862608b0ae10383b70b88530398312e66710db351896866e8082e263369 |
| PASS | PRO-RATA — two claims on one incident, keyed two ways ("1183:2023-03-13" / "…:Euler V1"), one canonical incident, one batch, both scaled | keys 1183:2023-03-13 / 1183:2023-03-13:Euler V1 → incident 1183:2023-03-13:euler v1; batch #3 scaled=true; approved 1.800000 vs locked 1.000000 GEN; paid 0.500000 + 0.500000 GEN; dust 0 wei; tx 0x78ee0948948d8f3b8494890b6a19249876b7a87272ddb7d42845ec24051b1277 |
| PASS | EXPIRED — cover expires unclaimed, premium to the underwriter | cover #8 RELEASED; premium 0.000066 GEN earned; tx 0xe053a67e5b5092d4915e18e49b4d969389197dc2b2eb9f4c8e2423c5a4c575c4 |
| PASS | STALLED — settled while paused | claim #13 stalls=1, then DENIED_EXCLUDED (GOVERNANCE_ATTACK); settle tx 0xc42efa05c8c8d0ab231de1fd67743d0147fc1d44769b85a6d74e3d537f9381e7 (paused by 0x25f920ce5fefb22866266c08c0e40edb439ec043c57d0baf5c31dffd5df4fb77) |
| PASS | BACKDATED — canonical cover bought after the incident: claim keyed to it refused at filing, before any model call; the cover keeps its one claim | canonical cover #1 claim_id 0; "incident refused before judging: incident 1183:2023-03-13 predates this cover's start plus its waiting period (2026-09-29); it is not covered and is refused before judging"; tx 0xffae8e905755fbf5be114f48099f4ddb4c409a74d0e2190f2483ab11eae651bf |
| PASS | CoverRegistry attests a live canonical cover | attestation #0 covered=true cover #2 curve-dex; tx 0x11affe292a67d210b73e5bc3c0467858a559d28873bc84ed565af40e38455059 |
| PASS | WAITING-PERIOD GATE — claim filed inside the waiting period refused mechanically; the one claim is not spent | canonical cover #3: "cover waiting period has not ended yet, claimable after 1791278292"; claim_id still 0; tx 0xe919a8a3b988287bfb1e750afd8b76d43dbd22b8fc6ae7e8827be20e8c4c819a |
| PASS | DRAINED — every demo pool closed, books at exactly 0 wei | 5 pools CLOSED; balance 0 = held 0 + payable 0 wei; locked 0; undelivered_wei 12134233333333333341 (Studio Dev transfers posted, not executed) |
| PASS | Ledger identity holds on both instances | demo balance 0.000000 = held 0.000000 + payable 0.000000; canonical 5.021000 = 5.021000 + 0.000000 |

## The books

Demo: balance 0.000000 GEN = held 0.000000 + payable 0.000000; capital 0.000000, locked 0.000000, paid out 2.575000, claimed 12.134233. Real chain balance 12.134233 GEN; undelivered_wei 12134233333333333341.

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
