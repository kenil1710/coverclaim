/**
 * Derives the seeded-outcome evidence BY READING THE CHAIN, not by trusting
 * what seed.mjs remembers (GrantJudge's lesson: a script's memory is not
 * evidence). Writes docs/EVIDENCE.json (read by tools/audit.py) and
 * docs/EVIDENCE.md.
 *
 *   node collect.mjs
 */
import { readFileSync, writeFileSync } from "node:fs";
import { connect } from "./harness.mjs";

const root = new URL("../", import.meta.url);
const dep = JSON.parse(readFileSync(new URL("deployments.json", root), "utf8")).deployments.studiodev;
const seed = JSON.parse(readFileSync(new URL("docs/seed-evidence.json", root), "utf8"));
const J = (v) => JSON.parse(JSON.stringify(v, (k, x) => (typeof x === "bigint" ? x.toString() : x)));
const demo = connect({ address: dep.CoverClaimDemo.address });
const canon = connect({ address: dep.CoverClaim.address });
const reg = connect({ address: dep.CoverRegistry.address });

const txOf = (label) => seed.steps.filter((s) => s.label === label).map((s) => s.tx).pop() ?? "";
const gen = (w) => (Number(BigInt(w ?? 0) / 10n ** 12n) / 1e6).toFixed(6);

const dClaims = J(await demo.view("get_claims", [0, 100])).items;
const cClaims = J(await canon.view("get_claims", [0, 100])).items;
const batches = J(await demo.view("get_batches", [0, 100])).items;
const dStats = J(await demo.view("get_stats"));
const cStats = J(await canon.view("get_stats"));
const dCfg = J(await demo.view("get_config"));
const dPools = J(await demo.view("get_pools", [0, 100])).items;
const K = seed.demo?.claims ?? {};
const C = seed.demo?.covers ?? {};
const byId = (id) => dClaims.find((c) => c.claim_id === id) ?? {};

const covered = byId(K.covered);
const MK = seed.demo?.multi?.claims ?? {};
const m1 = byId(MK.m1);
const m2 = byId(MK.m2);
const m3 = byId(MK.m3);
const m4 = byId(MK.m4);
const m5 = byId(MK.m5);
const m6 = byId(MK.m6);
const m7 = byId(MK.m7);
const noText = (c, words) => words.every((w) => !String(c.digest ?? "").includes(w));
const v1 = MK.m1 ? J(await demo.view("verify_claim", [MK.m1])) : {};
const v5 = MK.m5 ? J(await demo.view("verify_claim", [MK.m5])) : {};
const returnedOf = (label) => seed.steps.filter((s) => s.label === label).map((s) => s.returned).pop() ?? {};
const paidOrApproved = (c) => ["PAID", "APPROVED"].includes(c.status);
const multi = byId(K.multichain);
const inc = byId(K.inconclusive);
const pa = byId(K.prorataA);
const pb = byId(K.prorataB);
const st = byId(K.stalled);
const backdatedCover = seed.canonical?.cover_backdated ? J(await canon.view("get_cover", [seed.canonical.cover_backdated])) : {};
const backdatedRefusal = returnedOf("canon-backdated-file-refused");
const expired = J(await demo.view("get_cover", [C.expired]));
const pBatch = batches.find((b) => b.claim_ids.includes(K.prorataA)) ?? {};
const att = J(await reg.view("get_attestation", [0]));
let wg = [];
try { wg = JSON.parse(readFileSync(new URL("docs/waitgate-evidence.json", root), "utf8")); } catch { wg = []; }
const wgRefused = wg.find((x) => x.label === "wait7-file-refused");
const wgCoverId = wg.find((x) => x.label === "cover-after")?.cover_id ?? 0;
const wgCover = wgCoverId ? J(await canon.view("get_cover", [wgCoverId])) : {};

const scenarios = [
  {
    scenario: "MIXED EVIDENCE 6 — DNS record, [DNS article, Vyper article]: classified from the DNS page only → EXCLUDED, no payout",
    pass: m6.status === "DENIED_EXCLUDED" && m6.exclusion === "FRONTEND_HIJACK" && m6.gross_wei === "0"
      && /curve-finance-rekt BOUND/.test(m6.evidence_binding) && /curve-vyper-rekt UNBOUND/.test(m6.evidence_binding)
      && noText(m6, ["Vyper", "JPEG", "Alchemix"]),
    evidence: `claim #${m6.claim_id} ${m6.status}; ${m6.exclusion}; binding "${m6.evidence_binding}"; judged digest has no Vyper text: ${noText(m6, ["Vyper", "JPEG", "Alchemix"])}; tx ${txOf("multi-m6-judge")}`,
  },
  {
    scenario: "MIXED EVIDENCE 7 — Vyper record, [Vyper article, DNS article]: classified from the Vyper page only → COVERED",
    pass: paidOrApproved(m7) && m7.effective === "COVERED" && /curve-vyper-rekt BOUND/.test(m7.evidence_binding)
      && /curve-finance-rekt UNBOUND/.test(m7.evidence_binding) && noText(m7, ["DNS", "hijack"]),
    evidence: `claim #${m7.claim_id} ${m7.status}; ${m7.peril}; bucket ${m7.severity_bucket}; binding "${m7.evidence_binding}"; judged digest has no DNS text: ${noText(m7, ["DNS", "hijack"])}; tx ${txOf("multi-m7-judge")}`,
  },
  {
    scenario: "COVERED — Euler V1 2023-03-13 paid at its severity bucket",
    pass: ["PAID", "APPROVED"].includes(covered.status) && covered.classification === "COVERED" && covered.severity_bucket === 4,
    evidence: `claim #${covered.claim_id} ${covered.status}; ${covered.peril}; bucket ${covered.severity_bucket} (drop ${covered.drop_bps} bps); gross ${gen(covered.gross_wei)} GEN, paid ${gen(covered.payout_wei)} GEN; judge tx ${txOf("demo-covered-judge")}`,
  },
  {
    scenario: "CONTESTED — underwriter contests with novel evidence, verdict held",
    pass: covered.contest_status === "UPHELD",
    evidence: `contest ${covered.contest_status}; re-read as ${covered.contest_classification} strength ${covered.contest_strength}; novel ${String(covered.contest_novel ?? "").length} chars; tx ${txOf("demo-contest-judge")}`,
  },
  {
    scenario: "MULTI-INCIDENT 1 — Curve: Vyper evidence + 2023-07-30 record → COVERED, paid at the Vyper window's severity",
    pass: paidOrApproved(m1) && m1.effective === "COVERED" && m1.event_match === "SAME" && m1.incident_key === "3:2023-07-30"
      && m1.incident_date === "2023-07-30" && /anchor 2023-07-30 /.test(m1.tvl_window) && v1.hash_matches && v1.record_matches_key && v1.tvl_window_anchored,
    evidence: `claim #${m1.claim_id} ${m1.status}; key ${m1.incident_key}; event ${m1.event_match}; ${m1.peril}; bucket ${m1.severity_bucket} (drop ${m1.drop_bps} bps); paid ${gen(m1.payout_wei)} GEN; binding "${m1.evidence_binding}"; verify hash/record/window ${v1.hash_matches}/${v1.record_matches_key}/${v1.tvl_window_anchored}; tx ${txOf("multi-m1-judge")}`,
  },
  {
    scenario: "MULTI-INCIDENT 2 — Curve: Vyper evidence + 2022-08-09 record → EVIDENCE_MISMATCH, no payout",
    pass: m2.status === "EVIDENCE_MISMATCH" && m2.incident_key === "3:2022-08-09" && m2.gross_wei === "0" && m2.payout_wei === "0" && !m2.batch_id,
    evidence: `claim #${m2.claim_id} ${m2.status}; key ${m2.incident_key}; event ${m2.event_match}; model_called ${m2.model_called}; binding "${m2.evidence_binding}"; gross ${m2.gross_wei}; tx ${txOf("multi-m2-judge")}`,
  },
  {
    scenario: "MULTI-INCIDENT 3 — Curve: DNS evidence + 2023-07-30 record → EVIDENCE_MISMATCH, no payout",
    pass: m3.status === "EVIDENCE_MISMATCH" && m3.incident_key === "3:2023-07-30" && m3.gross_wei === "0" && m3.payout_wei === "0" && !m3.batch_id,
    evidence: `claim #${m3.claim_id} ${m3.status}; key ${m3.incident_key}; event ${m3.event_match}; model_called ${m3.model_called}; binding "${m3.evidence_binding}"; gross ${m3.gross_wei}; tx ${txOf("multi-m3-judge")}`,
  },
  {
    scenario: "MULTI-INCIDENT 4 — Curve: DNS evidence + 2022-08-09 record → EXCLUDED (FRONTEND_HIJACK)",
    pass: m4.status === "DENIED_EXCLUDED" && m4.exclusion === "FRONTEND_HIJACK" && m4.event_match === "SAME" && m4.incident_date === "2022-08-09",
    evidence: `claim #${m4.claim_id} ${m4.status}; key ${m4.incident_key}; event ${m4.event_match}; ${m4.exclusion}; bucket ${m4.severity_bucket} (DNS window, not paid: excluded); tx ${txOf("multi-m4-judge")}`,
  },
  {
    scenario: "MULTI-INCIDENT 5 — refile after mismatch: DNS evidence on the 2023 record, refiled with the Vyper report → COVERED",
    pass: paidOrApproved(m5) && m5.effective === "COVERED" && m5.mismatch_refiles === 1 && m5.refiles === 1 && v5.hash_matches
      && returnedOf("multi-m5-judge-mismatch").outcome === "EVIDENCE_MISMATCH",
    evidence: `claim #${m5.claim_id} first ${returnedOf("multi-m5-judge-mismatch").outcome} (tx ${txOf("multi-m5-judge-mismatch")}), refiled (tx ${txOf("multi-m5-refile")}), then ${m5.status} bucket ${m5.severity_bucket}, paid ${gen(m5.payout_wei)} GEN (tx ${txOf("multi-m5-judge-after-refile")})`,
  },
  {
    scenario: "EXCLUDED — Multichain key compromise 2023-07-07",
    pass: multi.status === "DENIED_EXCLUDED" && multi.exclusion === "USER_KEY_COMPROMISE",
    evidence: `claim #${multi.claim_id} ${multi.status}; ${multi.exclusion}; incident ${multi.incident_date}; bucket ${multi.severity_bucket} (not paid: excluded); tx ${txOf("demo-multichain-judge")}`,
  },
  {
    scenario: "INCONCLUSIVE — evidence that does not classify; refile allowed",
    pass: inc.status === "INCONCLUSIVE" && inc.model_called === false && inc.refile_until > 0,
    evidence: `claim #${inc.claim_id} ${inc.status}; model_called ${inc.model_called}; "${String(inc.pinned).slice(0, 90)}"; refile until ${inc.refile_until}; tx ${txOf("demo-inconclusive-judge")}`,
  },
  {
    scenario: "PRO-RATA — two claims on one incident, capacity short, both scaled",
    pass: pBatch.scaled === true && pa.status === "PAID" && pb.status === "PAID" && pa.payout_wei === pb.payout_wei,
    evidence: `batch #${pBatch.batch_id} scaled=${pBatch.scaled}; approved ${gen(pBatch.gross_total_wei)} vs locked ${gen(pBatch.available_wei)} GEN; paid ${gen(pa.payout_wei)} + ${gen(pb.payout_wei)} GEN; dust ${pBatch.dust_wei} wei; tx ${txOf(`demo-finalize-batch-${pBatch.batch_id}`)}`,
  },
  {
    scenario: "EXPIRED — cover expires unclaimed, premium to the underwriter",
    pass: expired.status === "RELEASED" && expired.claim_id === 0,
    evidence: `cover #${expired.cover_id} ${expired.status}; premium ${gen(expired.premium_wei)} GEN earned; tx ${txOf("demo-release-expired")}`,
  },
  {
    scenario: "STALLED — settled while paused",
    pass: st.stalls >= 1 && seed.steps.some((s) => s.label === "demo-settle-stalled-while-paused" && s.returned?.status === "OK"),
    evidence: `claim #${st.claim_id} stalls=${st.stalls}, then ${st.status} (${st.exclusion}); settle tx ${txOf("demo-settle-stalled-while-paused")} (paused by ${txOf("demo-pause")})`,
  },
  {
    scenario: "BACKDATED — canonical cover bought after the incident: claim keyed to it refused at filing, before any model call; the cover keeps its one claim",
    pass: backdatedRefusal.status === "REJECTED" && /predates this cover's start/.test(backdatedRefusal.reason ?? "") && backdatedCover.claim_id === 0 && cClaims.length === 0,
    evidence: `canonical cover #${backdatedCover.cover_id} claim_id ${backdatedCover.claim_id}; "${backdatedRefusal.reason}"; tx ${txOf("canon-backdated-file-refused")}`,
  },
  {
    scenario: "CoverRegistry attests a live canonical cover",
    pass: att.covered === true,
    evidence: `attestation #0 covered=${att.covered} cover #${att.cover_id} ${att.protocol}; tx ${txOf("registry-attest")}`,
  },
  {
    scenario: "WAITING-PERIOD GATE — claim filed inside the waiting period refused mechanically; the one claim is not spent",
    pass: wgRefused?.returned?.status === "REJECTED" && /waiting period has not ended yet, claimable after \d+/.test(wgRefused?.returned?.reason ?? "") && wgCover.claim_id === 0 && wgCover.in_waiting_period === true,
    evidence: `canonical cover #${wgCover.cover_id}: "${wgRefused?.returned?.reason}"; claim_id still ${wgCover.claim_id}; tx ${wgRefused?.tx}`,
  },
  {
    scenario: "DRAINED — every demo pool closed, books at exactly 0 wei",
    pass: dStats.balance_wei === "0" && dStats.held_wei === "0" && dStats.payable_wei === "0" && dStats.locked_wei === "0"
      && dPools.length > 0 && dPools.every((p) => p.status === "CLOSED" && p.capital_wei === "0" && p.premiums_held_wei === "0"),
    evidence: `${dPools.length} pools CLOSED; balance ${dStats.balance_wei} = held ${dStats.held_wei} + payable ${dStats.payable_wei} wei; locked ${dStats.locked_wei}; undelivered_wei ${dStats.undelivered_wei} (Studio Dev transfers posted, not executed)`,
  },
  {
    scenario: "Ledger identity holds on both instances",
    pass: dStats.ledger_balanced && dStats.held_matches_books && cStats.ledger_balanced && cStats.held_matches_books,
    evidence: `demo balance ${gen(dStats.balance_wei)} = held ${gen(dStats.held_wei)} + payable ${gen(dStats.payable_wei)}; canonical ${gen(cStats.balance_wei)} = ${gen(cStats.held_wei)} + ${gen(cStats.payable_wei)}`,
  },
];

const out = {
  collected_at: new Date().toISOString(),
  demo: { address: dep.CoverClaimDemo.address, config_label: dCfg.label, stats: dStats },
  canonical: { address: dep.CoverClaim.address, stats: cStats },
  scenarios,
  claims: { demo: dClaims, canonical: cClaims },
  batches,
};
writeFileSync(new URL("docs/EVIDENCE.json", root), JSON.stringify(out, null, 2) + "\n");

const md = [
  "# EVIDENCE — the seeded outcomes, read back from the chain",
  "",
  `Collected ${out.collected_at} by \`node test/collect.mjs\`, which READS the chain rather than trusting the seed script. Full records: \`docs/EVIDENCE.json\`; every write with its return value: \`docs/seed-evidence.json\`; raw log: \`docs/seed-run.log\`.`,
  "",
  `- DEMO instance \`${dep.CoverClaimDemo.address}\` — ${dCfg.label}`,
  `- Canonical instance \`${dep.CoverClaim.address}\``,
  `- CoverRegistry \`${dep.CoverRegistry.address}\``,
  "",
  "| | scenario | evidence |",
  "|---|---|---|",
  ...scenarios.map((s) => `| ${s.pass ? "PASS" : "**FAIL**"} | ${s.scenario} | ${s.evidence.replace(/\|/g, "/")} |`),
  "",
  "## The books",
  "",
  `Demo: balance ${gen(dStats.balance_wei)} GEN = held ${gen(dStats.held_wei)} + payable ${gen(dStats.payable_wei)}; capital ${gen(dStats.capital_wei)}, locked ${gen(dStats.locked_wei)}, paid out ${gen(dStats.total_payouts_wei)}, claimed ${gen(dStats.total_claimed_wei)}. Real chain balance ${dStats.chain_balance_wei === "unknown" ? "unknown" : gen(dStats.chain_balance_wei)} GEN; undelivered_wei ${dStats.undelivered_wei}.`,
  "",
  "## Claims (demo)",
  "",
  "| # | protocol | incident key | status | event | classification | peril / exclusion | bucket | strength | model | content hash |",
  "|---|---|---|---|---|---|---|---|---|---|---|",
  ...dClaims.map((c) => `| ${c.claim_id} | ${c.protocol_name} | \`${c.incident_key}\` | ${c.status} | ${c.event_match} | ${c.classification} | ${c.peril !== "NONE" ? c.peril : c.exclusion} | ${c.severity_bucket} | ${c.evidence_strength} | ${c.model_called} | \`${c.content_hash}\` |`),
  "",
  "## The multi-incident proof, page by page",
  "",
  "One Curve pool, one cover window (" + (m1.cover_start ? new Date(m1.cover_start * 1000).toISOString().slice(0, 10) : "?") + " start, waiting 7 days, 365 days), two DeFi Llama records inside it: `3:2022-08-09` (DNS hijack) and `3:2023-07-30` (Vyper reentrancy).",
  "",
  "| claim | key | evidence binding | event | outcome | TVL window |",
  "|---|---|---|---|---|---|",
  ...[m1, m2, m3, m4, m5, m6, m7].filter((c) => c.claim_id).map((c) => `| #${c.claim_id} | \`${c.incident_key}\` | \`${c.evidence_binding}\` | ${c.event_match} | ${c.status} | \`${String(c.tvl_window).slice(0, 90)}…\` |`),
  "",
];
writeFileSync(new URL("docs/EVIDENCE.md", root), md.join("\n"));
for (const s of scenarios) console.log((s.pass ? "PASS " : "FAIL ") + s.scenario + "\n     " + s.evidence);
