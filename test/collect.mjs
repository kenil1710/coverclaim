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
const K = seed.demo?.claims ?? {};
const C = seed.demo?.covers ?? {};
const byId = (id) => dClaims.find((c) => c.claim_id === id) ?? {};

const covered = byId(K.covered);
const curve = byId(K.curve);
const multi = byId(K.multichain);
const inc = byId(K.inconclusive);
const pa = byId(K.prorataA);
const pb = byId(K.prorataB);
const st = byId(K.stalled);
const backdated = cClaims.find((c) => c.claim_id === seed.canonical?.claim_backdated) ?? {};
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
    scenario: "EXCLUDED — Curve DNS hijack 2022-08-09",
    pass: curve.status === "DENIED_EXCLUDED" && curve.exclusion === "FRONTEND_HIJACK",
    evidence: `claim #${curve.claim_id} ${curve.status}; ${curve.exclusion}; incident ${curve.incident_date}; tx ${txOf("demo-curve-judge")}`,
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
    scenario: "REJECTED_BACKDATED — canonical cover bought after the incident",
    pass: backdated.status === "REJECTED_BACKDATED",
    evidence: `canonical claim #${backdated.claim_id} ${backdated.status}; classification ${backdated.classification}; incident ${backdated.incident_date} < waiting ends ${new Date(backdated.waiting_ends * 1000).toISOString().slice(0, 10)}; tx ${txOf("canon-backdated-judge")}`,
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
  "| # | protocol | status | classification | peril / exclusion | incident | bucket | strength | model | content hash |",
  "|---|---|---|---|---|---|---|---|---|---|",
  ...dClaims.map((c) => `| ${c.claim_id} | ${c.protocol_name} | ${c.status} | ${c.classification} | ${c.peril !== "NONE" ? c.peril : c.exclusion} | ${c.incident_date} | ${c.severity_bucket} | ${c.evidence_strength} | ${c.model_called} | \`${c.content_hash}\` |`),
  "",
];
writeFileSync(new URL("docs/EVIDENCE.md", root), md.join("\n"));
for (const s of scenarios) console.log((s.pass ? "PASS " : "FAIL ") + s.scenario + "\n     " + s.evidence);
