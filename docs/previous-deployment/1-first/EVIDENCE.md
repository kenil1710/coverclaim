# EVIDENCE — the seeded outcomes, read back from the chain

Collected 2026-09-26T08:29:24.790Z by `node test/collect.mjs`, which READS the chain rather than trusting the seed script. Full records: `docs/EVIDENCE.json`; every write with its return value: `docs/seed-evidence.json`; raw log: `docs/seed-run.log`.

- DEMO instance `0xa87Cd248C2667bFc3b79102C56A80E2912DE2A21` — DEMO - every cover starts 1521 days before it is bought, fixed at deployment, so that real historical incidents can be replayed. Not insurance.
- Canonical instance `0x36F2D1385Bd6fd0Fa22678FD6Cb5A00cc021Cee3`
- CoverRegistry `0x858Dbd7febCc3717f3B35163C1a4528c64D3108F`

| | scenario | evidence |
|---|---|---|
| PASS | COVERED — Euler V1 2023-03-13 paid at its severity bucket | claim #1 PAID; SMART_CONTRACT_BUG; bucket 4 (drop 9585 bps); gross 0.900000 GEN, paid 0.900000 GEN; judge tx 0xe9c8b5a06d5ab12942c97395322c3c6d7cc16df23336be081c52efe7805f23a6 |
| PASS | CONTESTED — underwriter contests with novel evidence, verdict held | contest UPHELD; re-read as COVERED strength 7; novel 2367 chars; tx 0x0838e8417b0b8dcdef80b84ee9af62b9557a2e34b9cc8f28693366b544aa3c05 |
| PASS | EXCLUDED — Curve DNS hijack 2022-08-09 | claim #2 DENIED_EXCLUDED; FRONTEND_HIJACK; incident 2022-08-09; tx 0x486d53fca0c73fcbb7b770aaa2479bc8fe063a3e22b293af000e92636400d42a |
| PASS | EXCLUDED — Multichain key compromise 2023-07-07 | claim #3 DENIED_EXCLUDED; USER_KEY_COMPROMISE; incident 2023-07-07; bucket 3 (not paid: excluded); tx 0x23b78747396e0ca5a9bb2b0729523df15493782e143d4735d6db810737c4e521 |
| PASS | INCONCLUSIVE — evidence that does not classify; refile allowed | claim #4 INCONCLUSIVE; model_called false; "the evidence names no peril and no exclusion; there is nothing to classify"; refile until 1790411268; tx 0xa49b38213091092d5715ddfeae946f946a7080020b73cbbbdd9cf8db75846705 |
| PASS | PRO-RATA — two claims on one incident, capacity short, both scaled | batch #2 scaled=true; approved 1.800000 vs locked 1.000000 GEN; paid 0.500000 + 0.500000 GEN; dust 0 wei; tx 0xe7b984abdc7a26f42d21bc88d0a1f858f76c807dd3ee6a01b01c9f14ba658b20 |
| PASS | EXPIRED — cover expires unclaimed, premium to the underwriter | cover #1 RELEASED; premium 0.000066 GEN earned; tx 0x8e7f10c662685d3248e923a4141e9c0c2f40b653508639f22b1336de56050a8e |
| PASS | STALLED — settled while paused | claim #7 stalls=1, then DENIED_EXCLUDED (GOVERNANCE_ATTACK); settle tx 0x7e744bc1574327c1f9228283ff9430c4677f964c911923ec827eae083ecc901b (paused by 0x7d342c059c2d18e01c46edd11d0158f57b46e841be64790985c40d91e0cd0cff) |
| PASS | REJECTED_BACKDATED — canonical cover bought after the incident | canonical claim #1 REJECTED_BACKDATED; classification COVERED; incident 2023-03-13 < waiting ends 2026-10-03; tx 0xa8959c25bd600b61440c1a12e1a5a75c078ba29459c4dbdef499bd057db1a1c9 |
| PASS | CoverRegistry attests a live canonical cover | attestation #0 covered=true cover #2 curve-dex; tx 0x5323df20f8edaaaa1ce32380b8fa60fe05880471b11ce26cf8d98f9155449e10 |
| PASS | Ledger identity holds on both instances | demo balance 7.465000 = held 7.465000 + payable 0.000000; canonical 4.020000 = 4.020000 + 0.000000 |

## The books

Demo: balance 7.465000 GEN = held 7.465000 + payable 0.000000; capital 7.100000, locked 3.000000, paid out 1.900000, claimed 2.365066. Real chain balance 9.830066 GEN; undelivered_wei 2365066666666666668.

## Claims (demo)

| # | protocol | status | classification | peril / exclusion | incident | bucket | strength | model | content hash |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Euler | PAID | COVERED | SMART_CONTRACT_BUG | 2023-03-13 | 4 | 4 | true | `4a9acc9c5131dbe3` |
| 2 | Curve | DENIED_EXCLUDED | EXCLUDED | FRONTEND_HIJACK | 2022-08-09 | 0 | 4 | true | `ff36629b12a323a1` |
| 3 | Multichain | DENIED_EXCLUDED | EXCLUDED | USER_KEY_COMPROMISE | 2023-07-07 | 3 | 4 | true | `b5357357dd59d42a` |
| 4 | Euler | INCONCLUSIVE | INCONCLUSIVE | NONE | 2023-03-13 | 4 | 0 | false | `b03315447e55fca9` |
| 5 | Euler | PAID | COVERED | SMART_CONTRACT_BUG | 2023-03-13 | 4 | 4 | true | `4a9acc9c5131dbe3` |
| 6 | Euler | PAID | COVERED | SMART_CONTRACT_BUG | 2023-03-13 | 4 | 4 | true | `912b860d3c97f56b` |
| 7 | Tornado Cash | DENIED_EXCLUDED | EXCLUDED | GOVERNANCE_ATTACK | 2023-05-20 | 0 | 4 | true | `3ca5dee94cebdfeb` |
