# EVIDENCE — the seeded outcomes, read back from the chain

Collected 2026-09-29T10:58:12.238Z by `node test/collect.mjs`, which READS the chain rather than trusting the seed script. Full records: `docs/EVIDENCE.json`; every write with its return value: `docs/seed-evidence.json`; raw log: `docs/seed-run.log`.

- DEMO instance `0xeB236D6Ed23B820d392C92974CF6dE178E55E4c1` — DEMO - every cover starts 1521 days before it is bought, fixed at deployment, so that real historical incidents can be replayed. Not insurance.
- Canonical instance `0xb41e6c81fB3Ec6D431296D6C15486Be5bB6D174f`
- CoverRegistry `0x2a6Af93674C430D570c50f23aEFAA2F11Eae899A`

| | scenario | evidence |
|---|---|---|
| PASS | MIXED EVIDENCE 6 — DNS record, [DNS article, Vyper article]: classified from the DNS page only → EXCLUDED, no payout | claim #6 DENIED_EXCLUDED; FRONTEND_HIJACK; binding "rekt.news/curve-finance-rekt BOUND 2022-08-10 ; rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; judged digest has no Vyper text: true; tx 0x8cd7d0e19be4ad4cbaa9a1486a772916cea8b35b8eba58f9c1d2f8ee66a12a7c |
| PASS | MIXED EVIDENCE 7 — Vyper record, [Vyper article, DNS article]: classified from the Vyper page only → COVERED | claim #7 PAID; SMART_CONTRACT_BUG; bucket 2; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31 ; rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; judged digest has no DNS text: true; tx 0xc40aa12d84c77eff7ff50724ee3c1b1c1245c84d0833453f83eb5a70998e83e3 |
| PASS | POOL VERIFICATION — every pool that sold cover was verified against DeFi Llama; its only protocol domain is the website DeFi Llama lists | #1 euler-v1: domain euler.finance (DeFi Llama https://www.euler.finance); #2 curve-dex: domain curve.finance (DeFi Llama https://curve.finance); #3 multichain: domain none (DeFi Llama lists none); #4 euler-v1: domain euler.finance (DeFi Llama https://www.euler.finance); #5 tornado-cash: domain tornadocash-eth.ipns.inbrowser.link (DeFi Llama https://tornadocash-eth.ipns.inbrowser.link/); #6 euler-v1: domain none (DeFi Llama https://www.euler.finance); #7 curve-dex: domain none (DeFi Llama https://curve.finance); 14 demo covers, all on verified pools |
| **FAIL** | VERIFICATION FAILS — declared domain DeFi Llama does not list: cannot sell, premium refused, closed with capital returned | pool #6 declared euler-postmortem.xyz: "declared domain euler-postmortem.xyz is not the website DeFi Llama lists for Euler V1 (https://www.euler.finance)"; covers 0; verify tx 0x935888d5c5be03f4a4c1e3d0c57de655ae3dc26f4f8ac8e546b5ae9c369fc730; buy refused 0xc4cd227962d71568430a1ca9208a1b4c57ad6e62d35ca90b5b260e88aeae244e; closed 0x7d65d776f25f42ac83da3da71e96b3ddc691f08fd409d0e9099ecda378290c00 |
| **FAIL** | VERIFICATION FAILS — slug and id of different protocols: cannot sell, closed with capital returned | pool #7 curve-dex/1183: "slug curve-dex is DeFi Llama id 3, not 1183: slug and id are different protocols"; verify tx 0xd317dbd9033c9e64fadf698a0f61350ee50b3e51f8bc4d59f07509a3ba63708d; buy refused 0x17000b1e64a57b95664fd7d5eef479baed916e7d3d76126308a1ff45d25ca460 |
| PASS | CONTEST FROM AN UNVERIFIED DOMAIN — refused before GenLayer (underwriter's own domain; protocol domain DeFi Llama does not list) | demo-contest-unverified-domain: "evidence refused before judging: euler-postmortem.xyz is not on this pool's frozen evidence allowlist" tx 0xafede34379ab32c598fbda00322dc3abb8209c577fb60abc8feffefb8b57b975; demo-contest-unlisted-domain: "evidence refused before judging: multichain.org is not on this pool's frozen evidence allowlist" tx 0xf9d6a58437c91ab629d400156c2bce3ad35006e76792fd2e3925750c1137d19d |
| PASS | ONE PAYOUT PER COVER (double-payout regression, structural) — every batch lists each claim once; no cover paid twice; payouts ≤ locked capacity | 3 batches: #1 3:2023-07-30:curve dex members [1,5,7] paid 0.675000 ≤ locked 1.500000; #2 1183:2023-03-13:euler v1 members [8] paid 0.900000 ≤ locked 1.000000; #3 1183:2023-03-13:euler v1 members [11,12] paid 1.000000 ≤ locked 1.000000 |
| PASS | COVERED — Euler V1 2023-03-13 paid at its severity bucket | claim #8 PAID; SMART_CONTRACT_BUG; bucket 4 (drop 9585 bps); gross 0.900000 GEN, paid 0.900000 GEN; judge tx 0xed6910bd486eeabe1dc8e94b46bc4dd1bbdbdeaec02a342bbad50f474b1da963 |
| PASS | CONTESTED — underwriter contests with novel evidence, verdict held | contest UPHELD; re-read as COVERED strength 7; novel 2367 chars; tx 0x0de44f8b053e95601c5b58d71ff7a4d83ef19a12bf4c3e7662d199b09ae85a01 |
| PASS | MULTI-INCIDENT 1 — Curve: Vyper evidence + 2023-07-30 record → COVERED, paid at the Vyper window's severity | claim #1 PAID; key 3:2023-07-30; event SAME; SMART_CONTRACT_BUG; bucket 2 (drop 4952 bps); paid 0.225000 GEN; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31"; verify hash/record/window true/true/true; tx 0x4207b571c43b94ace49c0692bd5a42598fa5aca4d8a086a05f7f5488b4a97700 |
| PASS | MULTI-INCIDENT 2 — Curve: Vyper evidence + 2022-08-09 record → EVIDENCE_MISMATCH, no payout | claim #2 EVIDENCE_MISMATCH; key 3:2022-08-09; event DIFFERENT; model_called false; binding "rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; gross 0; tx 0x797c83cd46d3bb5a4d6764fd805fcc9a8d439f960d642cd48c45c5e1933ed1e7 |
| PASS | MULTI-INCIDENT 3 — Curve: DNS evidence + 2023-07-30 record → EVIDENCE_MISMATCH, no payout | claim #3 EVIDENCE_MISMATCH; key 3:2023-07-30; event DIFFERENT; model_called false; binding "rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; gross 0; tx 0xd90d22c8bf9eefa09f887277fce62741131b61c43dbe931cfb8d22bca624a2a3 |
| PASS | MULTI-INCIDENT 4 — Curve: DNS evidence + 2022-08-09 record → EXCLUDED (FRONTEND_HIJACK) | claim #4 DENIED_EXCLUDED; key 3:2022-08-09; event SAME; FRONTEND_HIJACK; bucket 0 (DNS window, not paid: excluded); tx 0xdc6724324d32ac8d8db5228e4e2fa938cdd9cc61701b91c91517c64c369017c8 |
| PASS | MULTI-INCIDENT 5 — refile after mismatch: DNS evidence on the 2023 record, refiled with the Vyper report → COVERED | claim #5 first EVIDENCE_MISMATCH (tx 0x31a67ea126ccc69b16f927139d9de2dab06803852ea0c0b63268736c9c2d7d38), refiled (tx 0xa3a8328f9510fc2f0c9c0acfedba01d5a4641f2c869edb13743d181f913fb3a9), then PAID bucket 2, paid 0.225000 GEN (tx 0x2280a3ca2886fa74e5cd09be85f9f5065aa3538b235411d5f59b740e150fb147) |
| PASS | EXCLUDED — Multichain key compromise 2023-07-07 | claim #9 DENIED_EXCLUDED; USER_KEY_COMPROMISE; incident 2023-07-07; bucket 3 (not paid: excluded); tx 0x429d2941ec811a548be838a504775534efe62c04458a7061f71765c37708c0de |
| PASS | INCONCLUSIVE — evidence that does not classify; refile allowed | claim #10 INCONCLUSIVE; model_called false; "the evidence names no peril and no exclusion; there is nothing to classify"; refile until 1790679055; tx 0xfdf2be6335bb74dc08dbb96b05a2a4f174b484a33f42fe9b333fcdb8ff7e8f16 |
| PASS | PRO-RATA — two claims on one incident, keyed two ways ("1183:2023-03-13" / "…:Euler V1"), one canonical incident, one batch, both scaled | keys 1183:2023-03-13 / 1183:2023-03-13:Euler V1 → incident 1183:2023-03-13:euler v1; batch #3 scaled=true; approved 1.800000 vs locked 1.000000 GEN; paid 0.500000 + 0.500000 GEN; dust 0 wei; tx 0x987b1e9545df18dcd9ba19d4a5934e6c757fce2726d81343db903d749b53c13e |
| PASS | EXPIRED — cover expires unclaimed, premium to the underwriter | cover #8 RELEASED; premium 0.000066 GEN earned; tx 0x7a4a9c2483a0b07786557166233fa52e65524438a24b119c5a2d0e6f3ad24645 |
| PASS | STALLED — settled while paused | claim #13 stalls=1, then DENIED_EXCLUDED (GOVERNANCE_ATTACK); settle tx 0x9cd5d28704d9efb82c0dee690e8f4c1f03665a0ebab388d9f09c1434bd6d77bf (paused by 0xd4de4887b351057df46f16a9aede0d267501a874de04502e9f024f2c87018660) |
| PASS | BACKDATED — canonical cover bought after the incident: claim keyed to it refused at filing, before any model call; the cover keeps its one claim | canonical cover #1 claim_id 0; "incident refused before judging: incident 1183:2023-03-13 predates this cover's start plus its waiting period (2026-09-29); it is not covered and is refused before judging"; tx 0x55043384f30eae7034724fe5978f8af37556e42d48bd59f62084464af33d7158 |
| PASS | CoverRegistry attests a live canonical cover | attestation #0 covered=true cover #2 curve-dex; tx 0xcc5b7a6ffb0ad9e825f53e3da7e1fe5e1d032240a7851b8f6d1e0588932354c2 |
| PASS | WAITING-PERIOD GATE — claim filed inside the waiting period refused mechanically; the one claim is not spent | canonical cover #3: "cover waiting period has not ended yet, claimable after 1791283986"; claim_id still 0; tx 0x40996a17b2b20c6cfc468a7cb23105c5cf789b1fb028f5773ccb6ccbccc22df0 |
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
