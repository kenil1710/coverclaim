# EVIDENCE — the seeded outcomes, read back from the chain

Collected 2026-09-29T15:18:16.013Z by `node test/collect.mjs`, which READS the chain rather than trusting the seed script. Full records: `docs/EVIDENCE.json`; every write with its return value: `docs/seed-evidence.json`; raw log: `docs/seed-run.log`.

- DEMO instance `0x33e464ebF31eEaeD31fDB16D38CCb97FB30A8339` — DEMO - every cover starts 1521 days before it is bought, fixed at deployment, so that real historical incidents can be replayed. Not insurance.
- Canonical instance `0x039BCD3b9a12f81e1069dBbe9122A4B2e73db937`
- CoverRegistry `0x045C4C2BDE62CA730ceDf9B3ea810fbd645f2c6b`

| | scenario | evidence |
|---|---|---|
| PASS | MIXED EVIDENCE 6 — DNS record, [DNS article, Vyper article]: classified from the DNS page only → EXCLUDED, no payout | claim #6 DENIED_EXCLUDED; FRONTEND_HIJACK; binding "rekt.news/curve-finance-rekt BOUND 2022-08-10 ; rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; judged digest has no Vyper text: true; tx 0xd63eba5abb53ebbf4e4fe1f92bae440a4727b41ab9fdb42c2be772bfd268e542 |
| PASS | MIXED EVIDENCE 7 — Vyper record, [Vyper article, DNS article]: classified from the Vyper page only → COVERED | claim #7 PAID; SMART_CONTRACT_BUG; bucket 2; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31 ; rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; judged digest has no DNS text: true; tx 0xf47afbc0d4ce6bfef94bf736fae4ca2b1b5f2b27f4b20cb77d9653b5cc03a78b |
| PASS | POOL VERIFICATION — every pool that sold cover was verified against DeFi Llama; its only protocol domain is the website DeFi Llama lists | #1 euler-v1: domain euler.finance (DeFi Llama https://www.euler.finance); #2 curve-dex: domain curve.finance (DeFi Llama https://curve.finance); #3 multichain: domain none (DeFi Llama lists none); #4 euler-v1: domain euler.finance (DeFi Llama https://www.euler.finance); #5 tornado-cash: domain tornadocash-eth.ipns.inbrowser.link (DeFi Llama https://tornadocash-eth.ipns.inbrowser.link/); 15 demo covers, all on verified pools |
| PASS | VERIFICATION FAILS — declared domain DeFi Llama does not list: cannot sell, premium refused, closed with capital returned | pool #6 declared euler-postmortem.xyz: "declared domain euler-postmortem.xyz is not the website DeFi Llama lists for Euler V1 (https://www.euler.finance)"; covers 0; verify tx 0xcf29456e73ef9f793bce062b19268e75e8f3487b9e4768cf32d499fdee9f6bdf; buy refused 0x3561e2f441223ab3df3c76a4aee130366c69e2d25dbf11f9c9f3c6951f9b21f4; closed 0xd47ea5e2a2c6c44dfe9648b7ae0ea022e5969f16aae0cf9f7165b8e968f2822b |
| PASS | VERIFICATION FAILS — slug and id of different protocols: cannot sell, closed with capital returned | pool #7 curve-dex/1183: "slug curve-dex is DeFi Llama id 3, not 1183: slug and id are different protocols"; verify tx 0xdcfd9973eb815b7f49f5f3a3e4ecb933187e1dca189fd7a6a74d39752768e703; buy refused 0x0559b38eb4901f2952ad4ebdf17841aed9208f468c23b35f2bc1759908d76400 |
| PASS | CONTEST FROM AN UNVERIFIED DOMAIN — refused before GenLayer (underwriter's own domain; protocol domain DeFi Llama does not list) | demo-contest-unverified-domain: "evidence refused before judging: euler-postmortem.xyz is not on this pool's frozen evidence allowlist" tx 0xed256bc4141c4e35ef771713e533ae6e86535552febaae547376ac3f90ccb75e; demo-contest-unlisted-domain: "evidence refused before judging: multichain.org is not on this pool's frozen evidence allowlist" tx 0x3619fa28c2c12f98f92a45d6eaa0d21b20151d7a8c05b4069f2ecc98aa328a28 |
| PASS | ONE PAYOUT PER COVER (double-payout regression, structural) — every batch lists each claim once; no cover paid twice; payouts ≤ locked capacity | 4 batches: #1 3:2023-07-30:curve dex members [1,5,7] paid 0.675000 ≤ locked 1.500000; #2 1183:2023-03-13:euler v1 members [8] paid 0.900000 ≤ locked 1.000000; #3 1183:2023-03-13:euler v1 members [11,12] paid 1.000000 ≤ locked 1.000000; #4 1183:2023-03-13:euler v1 members [14] paid 0.450000 ≤ locked 0.500000 |
| PASS | CORE NAME — the Curve proof runs on a pool named "Curve DEX" (DeFi Llama's own name); verification stored the core name "Curve", which the evidence names | pool #2 "Curve DEX" → core "Curve"; claim #1 PAID, protocol named: true |
| PASS | LATE APPROVAL — an approval after a batch's window closed goes into a new batch; both settle | first batch #2 members [8]; late claim #14 in batch #4, PAID; judge tx 0x2558c1207ee84db42871ffdfcee16a9616a3c80c003c775bbd96a8cbbd1fed8c |
| PASS | REFILE IDENTITY — the same page with a #fragment is refused as not new | "every one of these sources was already judged on this claim for this incident (a re-spelled URL or key is the same sourc" tx 0xf69a2e854131305bb719949ccd2206d0ed2a80333b34d1658b3413b9bea41c3a |
| PASS | COVERED — Euler V1 2023-03-13 paid at its severity bucket | claim #8 PAID; SMART_CONTRACT_BUG; bucket 4 (drop 9585 bps); gross 0.900000 GEN, paid 0.900000 GEN; judge tx 0x19f79a27d6b6a6498c4b5c0a589d512a8b74ea52cbffc95efac840599e08a34e |
| PASS | CONTESTED — underwriter contests with novel evidence, verdict held | contest UPHELD; re-read as COVERED strength 7; novel 2367 chars; tx 0x0012333ce2a69ebb4a4b1aee2314cb3eedc42611cdbad39a8c8c8a23f92fd9be |
| PASS | MULTI-INCIDENT 1 — Curve: Vyper evidence + 2023-07-30 record → COVERED, paid at the Vyper window's severity | claim #1 PAID; key 3:2023-07-30; event SAME; SMART_CONTRACT_BUG; bucket 2 (drop 4952 bps); paid 0.225000 GEN; binding "rekt.news/curve-vyper-rekt BOUND 2023-07-31"; verify hash/record/window true/true/true; tx 0xe79d721eabd37e675f7b6f255120899c125d62c30ba8bb5d2fdb1e67c7683dfb |
| PASS | MULTI-INCIDENT 2 — Curve: Vyper evidence + 2022-08-09 record → EVIDENCE_MISMATCH, no payout | claim #2 EVIDENCE_MISMATCH; key 3:2022-08-09; event DIFFERENT; model_called false; binding "rekt.news/curve-vyper-rekt UNBOUND 2023-07-31"; gross 0; tx 0x2b07e697af9ba1f505fb4314ec809dda94472f58bb100b195b687b2ba680dcf6 |
| PASS | MULTI-INCIDENT 3 — Curve: DNS evidence + 2023-07-30 record → EVIDENCE_MISMATCH, no payout | claim #3 EVIDENCE_MISMATCH; key 3:2023-07-30; event DIFFERENT; model_called false; binding "rekt.news/curve-finance-rekt UNBOUND 2022-08-10"; gross 0; tx 0x62e33efac5c991afe5c466e7f51747b07539b066db055a2627cfde838d23c3b0 |
| PASS | MULTI-INCIDENT 4 — Curve: DNS evidence + 2022-08-09 record → EXCLUDED (FRONTEND_HIJACK) | claim #4 DENIED_EXCLUDED; key 3:2022-08-09; event SAME; FRONTEND_HIJACK; bucket 0 (DNS window, not paid: excluded); tx 0x63dbf7d4febe57dd98553b278f88452239f90961e6232de2453e983b0541d865 |
| PASS | MULTI-INCIDENT 5 — refile after mismatch: DNS evidence on the 2023 record, refiled with the Vyper report → COVERED | claim #5 first EVIDENCE_MISMATCH (tx 0x21d62a128d81c89ebf657add7aded702303761641c8eee9b8c40fdc71e4feb2b), refiled (tx 0x48efb8fea5d93f8a75c898d845c29fa7d9ea73c9b974f0201841f293c5d61854), then PAID bucket 2, paid 0.225000 GEN (tx 0x7ff3c68580e386bed4fe80651559fb692283909bd88df88f64ae6a10e430de5f) |
| PASS | EXCLUDED — Multichain key compromise 2023-07-07 | claim #9 DENIED_EXCLUDED; USER_KEY_COMPROMISE; incident 2023-07-07; bucket 3 (not paid: excluded); tx 0xaa578132f922a751607a48e65456500a054a0c0ed388bd27bb428bcb587b0975 |
| PASS | INCONCLUSIVE — evidence that does not classify; refile allowed | claim #10 INCONCLUSIVE; model_called false; "the evidence names no peril and no exclusion; there is nothing to classify"; refile until 1790694591; tx 0xbf80cee59510cbdd031c80c9bade2b17e1a96f6c2d53329e33bd1e359733c929 |
| PASS | PRO-RATA — two claims on one incident, keyed two ways ("1183:2023-03-13" / "…:Euler V1"), one canonical incident, one batch, both scaled | keys 1183:2023-03-13 / 1183:2023-03-13:Euler V1 → incident 1183:2023-03-13:euler v1; batch #3 scaled=true; approved 1.800000 vs locked 1.000000 GEN; paid 0.500000 + 0.500000 GEN; dust 0 wei; tx 0x2120701adc6b55c6e051110f26073cb849ba92ec7dcc87ff85157459d9ca1225 |
| PASS | EXPIRED — cover expires unclaimed, premium to the underwriter | cover #8 RELEASED; premium 0.000066 GEN earned; tx 0xc39e369fba0b738e5b7cd4dc57e00a24674ff0785ffb21b52435ba28466d94e3 |
| PASS | STALLED — settled while paused | claim #13 stalls=1, then DENIED_EXCLUDED (GOVERNANCE_ATTACK); settle tx 0x4d48bc3b51b3406051faddd8351105e1505a8131f2dfacefd701108e1f7b14f3 (paused by 0xdbedd21c4442b9d567b07abfcb718c887a757896d3bdfedd9bb5e294a177a3f2) |
| PASS | BACKDATED — canonical cover bought after the incident: claim keyed to it refused at filing, before any model call; the cover keeps its one claim | canonical cover #1 claim_id 0; "incident refused before judging: incident 1183:2023-03-13 predates this cover's start plus its waiting period (2026-09-29); it is not covered and is refused before judging"; tx 0x9b967f20eb41d8cdd1a38dbdaf7599d7e295de9ba4e3e85b45b58bacda491380 |
| PASS | CoverRegistry attests a live canonical cover | attestation #0 covered=true cover #2 curve-dex; tx 0xb3d3c9bf6d17208f72b0db5185af57f48153854eca53b566471916567659ed49 |
| PASS | WAITING-PERIOD GATE — claim filed inside the waiting period refused mechanically; the one claim is not spent | canonical cover #3: "cover waiting period has not ended yet, claimable after 1791299470"; claim_id still 0; tx 0x91e68600c351e9c0ddf197ceede42ee83ad5c16b3262a8110512daf068a0c4a3 |
| PASS | DRAINED — every demo pool closed, books at exactly 0 wei | 7 pools CLOSED; balance 0 = held 0 + payable 0 wei; locked 0; undelivered_wei 14397066666666666675 (Studio Dev transfers posted, not executed) |
| PASS | Ledger identity holds on both instances | demo balance 0.000000 = held 0.000000 + payable 0.000000; canonical 5.021000 = 5.021000 + 0.000000 |

## The books

Demo: balance 0.000000 GEN = held 0.000000 + payable 0.000000; capital 0.000000, locked 0.000000, paid out 3.025000, claimed 14.397066. Real chain balance 14.397066 GEN; undelivered_wei 14397066666666666675.

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
| 9 | Multichain | `591:2023-07-07` | DENIED_EXCLUDED | SAME | EXCLUDED | USER_KEY_COMPROMISE | 3 | 3 | true | `ab526fb017fa70f8` |
| 10 | Euler | `1183:2023-03-13` | INCONCLUSIVE | NOT_ASKED | INCONCLUSIVE | NONE | 4 | 0 | false | `f1953cd0f97a0220` |
| 11 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `ec52441004e5e5fc` |
| 12 | Euler | `1183:2023-03-13:Euler V1` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `942ff7a157090fee` |
| 13 | Tornado Cash | `148:2023-05-20` | DENIED_EXCLUDED | SAME | EXCLUDED | GOVERNANCE_ATTACK | 0 | 4 | true | `8665063248a8cd94` |
| 14 | Euler | `1183:2023-03-13` | PAID | SAME | COVERED | SMART_CONTRACT_BUG | 4 | 4 | true | `ec52441004e5e5fc` |

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
