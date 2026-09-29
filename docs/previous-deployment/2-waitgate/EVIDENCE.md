# EVIDENCE — the seeded outcomes, read back from the chain

Collected 2026-09-26T09:55:59.545Z by `node test/collect.mjs`, which READS the chain rather than trusting the seed script. Full records: `docs/EVIDENCE.json`; every write with its return value: `docs/seed-evidence.json`; raw log: `docs/seed-run.log`.

- DEMO instance `0xF77087fB487153212c3d3Bc178875f7fBeA52fFa` — DEMO - every cover starts 1521 days before it is bought, fixed at deployment, so that real historical incidents can be replayed. Not insurance.
- Canonical instance `0xeDBB5f6ea3D01289E1D879729C2253058602F145`
- CoverRegistry `0x39A8da9f3b6F7a921B50ecc5256B2837703ADd13`

| | scenario | evidence |
|---|---|---|
| PASS | COVERED — Euler V1 2023-03-13 paid at its severity bucket | claim #1 PAID; SMART_CONTRACT_BUG; bucket 4 (drop 9585 bps); gross 0.900000 GEN, paid 0.900000 GEN; judge tx 0xaa97278468cde69db1d9a5456966e743f5f9866ba0bdcb39b30fa3ec7acd0b0b |
| PASS | CONTESTED — underwriter contests with novel evidence, verdict held | contest UPHELD; re-read as COVERED strength 7; novel 2367 chars; tx 0xf6e9ff12a657fc7e9f7e9a04ba35dab474b4b18a6909b8938c7d14ce37a77cbb |
| PASS | EXCLUDED — Curve DNS hijack 2022-08-09 | claim #2 DENIED_EXCLUDED; FRONTEND_HIJACK; incident 2022-08-09; tx 0x2816656b2e171a1d4c04fb926e5317b1b4f943950741f8a35a8f2c43cd69987b |
| PASS | EXCLUDED — Multichain key compromise 2023-07-07 | claim #3 DENIED_EXCLUDED; USER_KEY_COMPROMISE; incident 2023-07-07; bucket 3 (not paid: excluded); tx 0x61ed8472de732591b899897ff57e6541c26fb15669bf602fbd4fae2e6f345ab3 |
| PASS | INCONCLUSIVE — evidence that does not classify; refile allowed | claim #4 INCONCLUSIVE; model_called false; "the evidence names no peril and no exclusion; there is nothing to classify"; refile until 1790416503; tx 0x7848b157a8da8bead18ffc034bf30c06fe2196d2faf7c1393fd65e6657147f35 |
| PASS | PRO-RATA — two claims on one incident, capacity short, both scaled | batch #2 scaled=true; approved 1.800000 vs locked 1.000000 GEN; paid 0.500000 + 0.500000 GEN; dust 0 wei; tx 0xa5098f3f8a5de38b53f9ebc752885d166eb3c499a221d4b84f1198d03469b24f |
| PASS | EXPIRED — cover expires unclaimed, premium to the underwriter | cover #1 RELEASED; premium 0.000066 GEN earned; tx 0x00d6c959909a68a088defe03b8e46c7bcd1a7f4acb2504b38ca63370ff55ca6d |
| PASS | STALLED — settled while paused | claim #7 stalls=1, then DENIED_EXCLUDED (GOVERNANCE_ATTACK); settle tx 0x9b958a67c03b175e9b15c2e20154b5528a7df23907d9de51700f883c637a19d3 (paused by 0x1b3b430edda68a35ce6e976ee6dab1eacee5bdb363fbbd786e58d646bfe1d78e) |
| PASS | REJECTED_BACKDATED — canonical cover bought after the incident | canonical claim #1 REJECTED_BACKDATED; classification COVERED; incident 2023-03-13 < waiting ends 2026-09-26; tx 0x5db7a99808d1587c6c79a1885d5c34850bf63605f5d43bfc199ea6971e35b1ac |
| PASS | CoverRegistry attests a live canonical cover | attestation #0 covered=true cover #2 curve-dex; tx 0x333e9b1082b989c00423daba9054529802cb7ab907d8e9237b559bb886d25c3e |
| PASS | WAITING-PERIOD GATE — claim filed inside the waiting period refused mechanically; the one claim is not spent | canonical cover #3: "cover waiting period has not ended yet, claimable after 1791018816"; claim_id still 0; tx 0x4d72a84d41178416413755a706ec32ff3531591814f2c0c9e9d54d6d0817682f |
| PASS | Ledger identity holds on both instances | demo balance 7.465000 = held 7.465000 + payable 0.000000; canonical 5.021000 = 5.021000 + 0.000000 |

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
