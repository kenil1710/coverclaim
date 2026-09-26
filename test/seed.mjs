/**
 * STEP 4 — seed both instances with real historical incidents.
 *
 *   node seed.mjs                  # everything
 *   node seed.mjs --part=canonical # just the canonical instance
 *   node seed.mjs --part=demo
 *
 * Every write is logged with its hash and the contract's own return value to
 * docs/seed-evidence.json AS IT HAPPENS; `collect.mjs` then re-derives the
 * outcome table by READING THE CHAIN, because a script's memory is not
 * evidence (GrantJudge's lesson).
 *
 * Canonical (backdating strict):
 *   REJECTED_BACKDATED  cover bought today, claimed with Euler's 2023 exploit
 *   REGISTRY            a waiting-period-0 cover, attested in force by CoverRegistry
 * Demo (covers start 1,521 days before purchase):
 *   COVERED + CONTESTED Euler V1, 2023-03-13 — underwriter contests with Euler's
 *                       own post-mortem; verdict held; paid at bucket 4
 *   EXCLUDED            Curve DNS hijack, 2022-08-09 (FRONTEND_HIJACK)
 *   EXCLUDED            Multichain keys, 2023-07-07 (USER_KEY_COMPROMISE)
 *   INCONCLUSIVE        Euler claimed with its homepage — no peril named
 *   PRO-RATA            two covers on a 50%-collateral Euler pool, both scaled
 *   EXPIRED             a 1-day cover, never claimed; premium to underwriter
 *   STALLED             Tornado Cash claim settled while paused, then judged
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { connect, accounts, fundOnStudio, argOf, returnedJson, sleep } from "./harness.mjs";

const GEN = 10n ** 18n;
const dep = JSON.parse(readFileSync(new URL("../deployments.json", import.meta.url), "utf8")).deployments.studiodev;
const CANON = dep.CoverClaim.address;
const DEMO = dep.CoverClaimDemo.address;
const REG = dep.CoverRegistry.address;
const acc = accounts();
const part = argOf("part", "all");

const evPath = new URL("../docs/seed-evidence.json", import.meta.url);
const EV = existsSync(evPath) ? JSON.parse(readFileSync(evPath, "utf8")) : { steps: [] };
const save = () => writeFileSync(evPath, JSON.stringify(EV, null, 2) + "\n");

const ALL_P = "SMART_CONTRACT_BUG,ORACLE_MANIPULATION,ECONOMIC_EXPLOIT,BRIDGE_COMPROMISE";
const ALL_X = "PHISHING,FRONTEND_HIJACK,USER_KEY_COMPROMISE,RUG_BY_TEAM,GOVERNANCE_ATTACK";
const URL_ = {
  euler: "https://rekt.news/euler-rekt",
  eulerArchive: "https://web.archive.org/web/20231217192546/https://rekt.news/euler-rekt/",
  eulerPM: "https://www.euler.finance/blog/war-peace-behind-the-scenes-of-eulers-240m-exploit-recovery",
  eulerHome: "https://www.euler.finance/",
  curveDns: "https://rekt.news/curve-finance-rekt",
  multichain: "https://rekt.news/multichain-r3kt",
  tornado: "https://rekt.news/tornado-gov-rekt",
};

for (const r of Object.keys(acc)) {
  await fundOnStudio((connect({ address: DEMO, role: "client" })).chain, acc[r].address, 300n * GEN);
}

async function step(label, address, role, method, args, value = 0n) {
  const c = connect({ address, role });
  const out = await c.send(method, args, value);
  const ret = returnedJson(out);
  const rec = { label, contract: address === DEMO ? "demo" : address === CANON ? "canonical" : "registry",
    role, from: acc[role].address, method, args: args.map(String), value: value.toString(),
    tx: out.hash, status: out.status, seconds: Math.round(out.seconds ?? 0), returned: ret, at: new Date().toISOString() };
  EV.steps.push(rec);
  save();
  const short = ret ? JSON.stringify(ret).slice(0, 260) : out.failure ?? "";
  console.log(`[${label}] ${method} ${out.status} ${rec.seconds}s ${out.hash}\n    ${short}`);
  return { out, ret };
}

const view = (address, m, args = []) => connect({ address }).view(m, args);
const lastId = async (address, m) => (await view(address, m, [0, 100])).total;

async function newPool(address, role, label, spec, capital, extra = {}) {
  const o = { rate: 100, wait: 7, ded: 1000, max: 2n * GEN, term: 365, coll: 10000, table: "", perils: ALL_P, excl: ALL_X, ...extra };
  const { ret } = await step(label, address, role, "create_pool",
    [spec.name, spec.slug, spec.id, spec.chain, o.perils, o.excl, o.rate, o.wait, o.ded, o.max, o.term, o.coll, o.table, spec.domains, spec.wording],
    capital);
  return ret?.pool_id ?? (await lastId(address, "get_pools"));
}

async function newCover(address, role, label, pool, amount, days) {
  const q = await view(address, "quote", [pool, amount, days]);
  const { ret } = await step(label, address, role, "buy_cover", [pool, amount, days], BigInt(q.premium_wei));
  if (ret?.cover_id) return ret.cover_id;
  const mine = await view(address, "get_covers_by_buyer", [acc[role].address]);
  return mine.items[mine.items.length - 1].cover_id;
}

async function newClaim(address, role, label, cover, urls, statement) {
  const { ret } = await step(label, address, role, "file_claim", [cover, urls, statement]);
  if (ret?.claim_id) return ret.claim_id;
  return (await view(address, "get_cover", [cover])).claim_id;
}

const SPEC = {
  euler: { name: "Euler", slug: "euler-v1", id: "1183", chain: "Ethereum", domains: "euler.finance",
    wording: "Euler V1 lending markets on Ethereum." },
  curve: { name: "Curve", slug: "curve-dex", id: "3", chain: "Ethereum", domains: "curve.finance",
    wording: "Curve DEX pools on Ethereum." },
  multichain: { name: "Multichain", slug: "multichain", id: "591", chain: "Multi-chain", domains: "multichain.org",
    wording: "Multichain router and bridge deposits." },
  tornado: { name: "Tornado Cash", slug: "tornado-cash", id: "148", chain: "Ethereum", domains: "tornado.cash",
    wording: "Tornado Cash pools and governance." },
};

async function waitUntil(label, fn, everyMs = 30_000, maxMs = 3 * 3600_000) {
  const t0 = Date.now();
  for (;;) {
    const got = await fn().catch(() => false);
    if (got) return got;
    if (Date.now() - t0 > maxMs) throw new Error("gave up waiting: " + label);
    console.log(`  … waiting: ${label}`);
    await sleep(everyMs);
  }
}

if (part === "all" || part === "canonical") {
  console.log("\n=== CANONICAL", CANON);
  const p = await newPool(CANON, "uw1", "canon-euler-pool", SPEC.euler, 2n * GEN);
  const c = await newCover(CANON, "buyer2", "canon-backdated-cover", p, GEN, 30);
  const cl = await newClaim(CANON, "buyer2", "canon-backdated-claim", c, URL_.euler,
    "Euler was exploited through donateToReserves; I hold cover on it.");
  await step("canon-backdated-judge", CANON, "trigger", "judge_claim", [cl]);
  const p2 = await newPool(CANON, "uw3", "canon-curve-pool-wait0", SPEC.curve, 2n * GEN, { wait: 0, term: 90 });
  await newCover(CANON, "buyer3", "canon-registry-cover", p2, GEN / 2n, 60);
  await step("registry-attest", REG, "trigger", "attest", [acc.buyer3.address, "curve-dex"]);
  EV.canonical = { pool_backdated: p, cover_backdated: c, claim_backdated: cl, pool_registry: p2 };
  save();
}

if (part === "all" || part === "demo") {
  console.log("\n=== DEMO", DEMO);
  const P = {};
  P.euler = await newPool(DEMO, "uw1", "demo-euler-pool", SPEC.euler, 3n * GEN);
  P.curve = await newPool(DEMO, "uw2", "demo-curve-pool", SPEC.curve, 2n * GEN, { perils: "SMART_CONTRACT_BUG,ORACLE_MANIPULATION,ECONOMIC_EXPLOIT" });
  P.multichain = await newPool(DEMO, "uw3", "demo-multichain-pool", SPEC.multichain, 2n * GEN);
  P.prorata = await newPool(DEMO, "uw2", "demo-euler-prorata-pool", { ...SPEC.euler, wording: "Thin pool: 50% collateral. Claims on one incident beyond capital are paid pro-rata." }, GEN, { coll: 5000, max: GEN });
  P.tornado = await newPool(DEMO, "uw3", "demo-tornado-pool", SPEC.tornado, GEN);
  EV.demo = { pools: P };
  save();

  const C = {};
  C.expired = await newCover(DEMO, "buyer1", "demo-expired-cover", P.euler, GEN / 5n, 1);
  C.covered = await newCover(DEMO, "buyer1", "demo-covered-cover", P.euler, GEN, 365);
  C.curve = await newCover(DEMO, "buyer2", "demo-curve-cover", P.curve, GEN, 365);
  C.multichain = await newCover(DEMO, "buyer3", "demo-multichain-cover", P.multichain, GEN, 365);
  C.inconclusive = await newCover(DEMO, "buyer4", "demo-inconclusive-cover", P.euler, GEN / 2n, 365);
  C.prorataA = await newCover(DEMO, "buyer5", "demo-prorata-cover-a", P.prorata, GEN, 365);
  C.prorataB = await newCover(DEMO, "buyer6", "demo-prorata-cover-b", P.prorata, GEN, 365);
  C.stalled = await newCover(DEMO, "buyer4", "demo-stalled-cover", P.tornado, GEN / 2n, 365);
  EV.demo.covers = C;
  save();

  const K = {};
  K.covered = await newClaim(DEMO, "buyer1", "demo-covered-claim", C.covered, URL_.euler,
    "Euler V1 was drained on 13 March 2023 via the donateToReserves flaw.");
  K.curve = await newClaim(DEMO, "buyer2", "demo-curve-claim", C.curve, URL_.curveDns,
    "Curve users lost funds on 9 August 2022.");
  K.multichain = await newClaim(DEMO, "buyer3", "demo-multichain-claim", C.multichain, URL_.multichain,
    "Multichain funds were drained in July 2023.");
  K.inconclusive = await newClaim(DEMO, "buyer4", "demo-inconclusive-claim", C.inconclusive, URL_.eulerHome,
    "Euler lost funds; see the official site.");
  K.prorataA = await newClaim(DEMO, "buyer5", "demo-prorata-claim-a", C.prorataA, URL_.euler, "Euler exploit, March 2023.");
  K.prorataB = await newClaim(DEMO, "buyer6", "demo-prorata-claim-b", C.prorataB, URL_.eulerArchive, "Euler exploit (archived report).");
  EV.demo.claims = K;
  save();

  // COVERED, then the underwriter contests it at once with NOVEL evidence.
  await step("demo-covered-judge", DEMO, "trigger", "judge_claim", [K.covered]);
  const bond = BigInt((await view(DEMO, "get_config")).contest_bond_wei);
  await step("demo-contest", DEMO, "uw1", "contest", [K.covered, URL_.eulerPM,
    "Euler's own post-mortem is a new primary source; the underwriter asks the validators to re-read the root cause with it."], bond);
  await step("demo-contest-judge", DEMO, "trigger", "judge_contest", [K.covered]);

  await step("demo-curve-judge", DEMO, "trigger", "judge_claim", [K.curve]);
  await step("demo-multichain-judge", DEMO, "trigger", "judge_claim", [K.multichain]);
  await step("demo-inconclusive-judge", DEMO, "trigger", "judge_claim", [K.inconclusive]);
  await step("demo-prorata-judge-a", DEMO, "trigger", "judge_claim", [K.prorataA]);
  await step("demo-prorata-judge-b", DEMO, "trigger", "judge_claim", [K.prorataB]);

  // STALLED: filed, never judged; the owner pauses; the stall window passes;
  // anyone unsticks it WHILE PAUSED; it is then judged while still paused.
  K.stalled = await newClaim(DEMO, "buyer4", "demo-stalled-claim", C.stalled, URL_.tornado,
    "Tornado Cash governance was taken over in May 2023.");
  save();
  await step("demo-pause", DEMO, "client", "set_paused", [true]);
  const ttl = (await view(DEMO, "get_config")).stall_ttl_s;
  await waitUntil("stall window on claim " + K.stalled, async () => {
    const cl = await view(DEMO, "get_claim", [K.stalled]);
    const cfg = await view(DEMO, "get_config");
    return cfg.now - cl.last_filed_at >= ttl + 5;
  });
  await step("demo-settle-stalled-while-paused", DEMO, "trigger", "settle_stalled", [K.stalled]);
  await step("demo-stalled-judge-while-paused", DEMO, "trigger", "judge_claim", [K.stalled]);
  await step("demo-unpause", DEMO, "client", "set_paused", [false]);

  // Settlement: every open batch, once its window and its members' contest
  // windows have closed.
  await waitUntil("settlement windows", async () => {
    const b = await view(DEMO, "get_batches", [0, 100]);
    const cfg = await view(DEMO, "get_config");
    const open = b.items.filter((x) => x.status === "OPEN");
    if (open.length === 0) return true;
    let all = true;
    for (const x of open) {
      const members = await Promise.all(x.claim_ids.map((id) => view(DEMO, "get_claim", [id])));
      const ready = cfg.now >= x.closes_at && members.every((m) => m.status !== "APPROVED" || m.contest_status !== "" || cfg.now > m.contest_window_closes);
      if (ready) await step(`demo-finalize-batch-${x.batch_id}`, DEMO, "trigger", "finalize_incident", [x.batch_id]);
      else all = false;
    }
    return all;
  });

  // EXPIRED: the 1-day cover, never claimed, releases after its claim window.
  await waitUntil("claim window of the expired cover", async () => {
    const cv = await view(DEMO, "get_cover", [C.expired]);
    const cfg = await view(DEMO, "get_config");
    return cfg.now > cv.claim_deadline + 5;
  });
  await step("demo-release-expired", DEMO, "trigger", "release_cover", [C.expired]);

  // Payouts: the only method that transfers, and it reads no clock.
  for (const role of ["buyer1", "buyer5", "buyer6", "uw1", "uw2"]) {
    const owed = await view(DEMO, "payout_of", [acc[role].address]);
    if (BigInt(owed.owed_wei) > 0n) await step(`demo-payout-${role}`, DEMO, role, "claim_payout", []);
  }
  EV.demo.claims = K;
  save();
}
console.log("\nseed done");
