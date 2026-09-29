# EVIDENCE — the seeded outcomes, read back from the chain

Collected 2026-09-29T07:59:51.597Z by `node test/collect.mjs`, which READS the chain rather than trusting the seed script. Full records: `docs/EVIDENCE.json`; every write with its return value: `docs/seed-evidence.json`; raw log: `docs/seed-run.log`.

- DEMO instance `0xf59B1A3DEE9E7075B9Bc1CdcdeD3d0d67666dE99` — DEMO - every cover starts 1521 days before it is bought, fixed at deployment, so that real historical incidents can be replayed. Not insurance.
- Canonical instance `0xF2F545d265dB85495E5Bda8fA02573F17B193983`
- CoverRegistry `0x06144d4702C513d289c4Ef1bAA811bbad0c6a4EB`

| | scenario | evidence |
|---|---|---|
| PASS | MIXED EVIDENCE 6 — DNS record, [DNS article, Vyper article]: classified from the DNS page only → EXCLUDED, no payout | claim #6 DENIED_EXCLUDED; FRONTEND_HIJACK; binding "rekt.news/curve-finance-rekt BOUND 2022-08-10 ; rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; judged digest has no Vyper text: true; tx 0x3fdf39a27f75b56351be45d1bdf57ab964ea708aac0bf4ff248386f84ebff565 |
| PASS | MIXED EVIDENCE 7 — Vyper record, [Vyper article, DNS article]: classified from the Vyper page only → COVERED | claim #7 PAID; SMART_CONTRACT_BUG; bucket 2; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31 ; rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; judged digest has no DNS text: true; tx 0xddabcdb7800377c1a9c03e5b7662d640138301a567e93782cf7d624dae3d23bd |
| PASS | COVERED — Euler V1 2023-03-13 paid at its severity bucket | claim #13 PAID; SMART_CONTRACT_BUG; bucket 4 (drop 9585 bps); gross 0.900000 GEN, paid 0.900000 GEN; judge tx 0x6b48885e705361dee7758e3dee0cd17959bf29fbd3f8817a07e41f186bcd548e |
| PASS | CONTESTED — underwriter contests with novel evidence, verdict held | contest UPHELD; re-read as COVERED strength 7; novel 2367 chars; tx 0xc8a1460da70e240e727f4c21b3a3f94b44bdd532b1846ac096c2268150540c90 |
| PASS | MULTI-INCIDENT 1 — Curve: Vyper evidence + 2023-07-30 record → COVERED, paid at the Vyper window's severity | claim #1 PAID; key 3:2023-07-30; event SAME; SMART_CONTRACT_BUG; bucket 2 (drop 4952 bps); paid 0.225000 GEN; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31"; verify hash/record/window true/true/true; tx 0x5bb0b92f397df1abe05dd68fd5d9730689ad6fb1d903c3612a44bc1ff16ffce4 |
| PASS | MULTI-INCIDENT 2 — Curve: Vyper evidence + 2022-08-09 record → EVIDENCE_MISMATCH, no payout | claim #2 EVIDENCE_MISMATCH; key 3:2022-08-09; event DIFFERENT; model_called false; binding "rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; gross 0; tx 0x39f27738e643247121a4487ea16c66d6fd047c39e3b3205dd5503e5152d7bc40 |
| PASS | MULTI-INCIDENT 3 — Curve: DNS evidence + 2023-07-30 record → EVIDENCE_MISMATCH, no payout | claim #3 EVIDENCE_MISMATCH; key 3:2023-07-30; event DIFFERENT; model_called false; binding "rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; gross 0; tx 0xe5f3d7ddcc52ebfd104705b32ad4f1c69147f198225309536288ed49cae0a18c |
| PASS | MULTI-INCIDENT 4 — Curve: DNS evidence + 2022-08-09 record → EXCLUDED (FRONTEND_HIJACK) | claim #4 DENIED_EXCLUDED; key 3:2022-08-09; event SAME; FRONTEND_HIJACK; bucket 0 (DNS window, not paid: excluded); tx 0x8b26f14edb2fe33607ac18990cdf236634a59330a02b35025162971c1cde6242 |
| PASS | MULTI-INCIDENT 5 — refile after mismatch: DNS evidence on the 2023 record, refiled with the Vyper report → COVERED | claim #5 first EVIDENCE_MISMATCH (tx 0x419f8b7403ed48205f090628415622f428db0f363bb1ea19ffef85ca19726f1b), refiled (tx 0x20415f467f1c5208068e660830bf3b2ee292bc389c94d921348264fe882c6b97), then PAID bucket 2, paid 0.225000 GEN (tx 0xa55aa33c0ac3343796e7eab65f1c82ad56583dc3a7ead93f8e9d7effde0b36d0) |
| PASS | EXCLUDED — Multichain key compromise 2023-07-07 | claim #8 DENIED_EXCLUDED; USER_KEY_COMPROMISE; incident 2023-07-07; bucket 3 (not paid: excluded); tx 0x0035b06293ad8ccb631e845f70ca8ccc920aaa147736a8ee2985ca2980fa24d5 |
| PASS | INCONCLUSIVE — evidence that does not classify; refile allowed | claim #9 INCONCLUSIVE; model_called false; "the evidence names no peril and no exclusion; there is nothing to classify"; refile until 1790667197; tx 0x8f1f8cc406ed6d2661993eb980771318a4f5b3cf157359a61a83f74bd083fd77 |
| PASS | PRO-RATA — two claims on one incident, capacity short, both scaled | batch #2 scaled=true; approved 1.800000 vs locked 1.000000 GEN; paid 0.500000 + 0.500000 GEN; dust 0 wei; tx 0x953e1632fb93ff6efc9ff4fb1f85a1b3f3ba6efb1830743e62a441988b23d530 |
| PASS | EXPIRED — cover expires unclaimed, premium to the underwriter | cover #8 RELEASED; premium 0.000066 GEN earned; tx 0x96363b26db49c9b1e938fb0dbecdb03308cfa202d05ca83b16c3ee09e214f430 |
| PASS | STALLED — settled while paused | claim #12 stalls=1, then DENIED_EXCLUDED (GOVERNANCE_ATTACK); settle tx 0xc4641ce000defcde322bd0cc38aefc4bdf8efcbddf1d320bc31b3716ba1332af (paused by 0x166efe2e9ed05ff2f12a90c98873b291cee0e3575817f9bef75f08ab5d2d27d9) |
| PASS | BACKDATED — canonical cover bought after the incident: claim keyed to it refused at filing, before any model call; the cover keeps its one claim | canonical cover #1 claim_id 0; "incident refused before judging: incident 1183:2023-03-13 predates this cover's start plus its waiting period (2026-09-29); it is not covered and is refused before judging"; tx 0x2327b6dc9caa899e54a9573859cb2dd7e0f52c96d2ac77fcfa181f28c534468d |
| PASS | CoverRegistry attests a live canonical cover | attestation #0 covered=true cover #2 curve-dex; tx 0x6a077bceafb564cd08cd4855cc763ea623258e442832e399563c9a9c705691e7 |
| PASS | WAITING-PERIOD GATE — claim filed inside the waiting period refused mechanically; the one claim is not spent | canonical cover #3: "cover waiting period has not ended yet, claimable after 1791272110"; claim_id still 0; tx 0xb59ea9f7db7b3869b21abb64f252e7317c6df3ef6738cb65b551c943f42a5837 |
| PASS | DRAINED — every demo pool closed, books at exactly 0 wei | 6 pools CLOSED; balance 0 = held 0 + payable 0 wei; locked 0; undelivered_wei 14355900000000000008 (Studio Dev transfers posted, not executed) |
| PASS | Ledger identity holds on both instances | demo balance 0.000000 = held 0.000000 + payable 0.000000; canonical 5.021000 = 5.021000 + 0.000000 |

## The books

Demo: balance 0.000000 GEN = held 0.000000 + payable 0.000000; capital 0.000000, locked 0.000000, paid out 2.575000, claimed 14.355900. Real chain balance 14.355900 GEN; undelivered_wei 14355900000000000008.

## Claims (demo)

| # | protocol | incident key | status | event | classification | peril / exclusion | bucket | strength | model | content hash |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Curve | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `7b244fb5a5ef1dbd` |
| 2 | Curve | `3:2022-08-09` | EVIDENCE_MISMATCH | DIFFERENT | INCONCLUSIVE | NONE | 0 | 0 | false | `e4db574b4f52ad5e` |
| 3 | Curve | `3:2023-07-30` | EVIDENCE_MISMATCH | DIFFERENT | INCONCLUSIVE | NONE | 2 | 0 | false | `b6bc02b93277364b` |
| 4 | Curve | `3:2022-08-09` | DENIED_EXCLUDED | SAME | EXCLUDED | FRONTEND_HIJACK | 0 | 4 | true | `8e3568c652f64ccc` |
| 5 | Curve | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `7b244fb5a5ef1dbd` |
| 6 | Curve | `3:2022-08-09` | DENIED_EXCLUDED | SAME | EXCLUDED | FRONTEND_HIJACK | 0 | 4 | true | `0b58c1f0205ecbfd` |
| 7 | Curve | `3:2023-07-30` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 2 | 4 | true | `83ef494b987a0bd9` |
| 8 | Multichain | `591:2023-07-07` | DENIED_EXCLUDED | SAME | EXCLUDED | USER_KEY_COMPROMISE | 3 | 4 | true | `34176f41865d6887` |
| 9 | Euler | `1183:2023-03-13` | INCONCLUSIVE | NOT_ASKED | INCONCLUSIVE | NONE | 4 | 0 | false | `a83bb6b1f8ad9866` |
| 10 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `1a86f5532cf16402` |
| 11 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `039b5c66144fe003` |
| 12 | Tornado Cash | `148:2023-05-20` | DENIED_EXCLUDED | SAME | EXCLUDED | GOVERNANCE_ATTACK | 0 | 4 | true | `ac3d72dd718832b7` |
| 13 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `1a86f5532cf16402` |

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
