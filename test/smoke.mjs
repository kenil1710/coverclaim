/**
 * On-chain smoke test against a deployed instance: config readable (and
 * whether a VIEW can read the block clock), one pool, one cover, one claim,
 * one real judgement by Studio's validators.
 *
 *   node smoke.mjs --address=0x...
 */
import { connect, accounts, fundOnStudio, argOf, returnedJson } from "./harness.mjs";

const address = argOf("address");
const acc = accounts();
const as = (role) => connect({ address, role });
const base = as("client");
for (const r of ["uw1", "buyer1", "trigger"]) await fundOnStudio(base.chain, acc[r].address, 200n * 10n ** 18n);

const GEN = 10n ** 18n;
const cfg = await base.view("get_config");
console.log("config demo", cfg.demo, "backdate", cfg.demo_backdate_days, "view clock now =", cfg.now);

const show = (label, out) => {
  const r = returnedJson(out);
  console.log(`${label.padEnd(12)} ${out.status} ${out.seconds?.toFixed?.(0)}s ${out.hash}`);
  console.log("   ", JSON.stringify(r)?.slice(0, 900));
  return r;
};

let r = show("create_pool", await as("uw1").send("create_pool", [
  "Euler", "euler-v1", "1183", "Ethereum",
  "SMART_CONTRACT_BUG,ORACLE_MANIPULATION,ECONOMIC_EXPLOIT,BRIDGE_COMPROMISE",
  "PHISHING,FRONTEND_HIJACK,USER_KEY_COMPROMISE,RUG_BY_TEAM,GOVERNANCE_ATTACK",
  100, 7, 1000, 2n * GEN, 365, 10000, "", "euler.finance", "smoke"], 2n * GEN));
const pools = await base.view("get_pools", [0, 50]);
const pid = pools.total;
console.log("pool id", pid);
const q = await base.view("quote", [pid, GEN, 365]);
console.log("quote", q.premium_wei, q.ok, q.reason);
show("buy_cover", await as("buyer1").send("buy_cover", [pid, GEN, 365], BigInt(q.premium_wei)));
const covers = await base.view("get_covers_by_buyer", [acc.buyer1.address]);
const cid = covers.items[covers.items.length - 1].cover_id;
console.log("cover", cid, covers.items[covers.items.length - 1].start);
show("file_claim", await as("buyer1").send("file_claim", [cid, "https://rekt.news/euler-rekt", "smoke"], 0n));
const claims = await base.view("get_claims", [0, 100]);
const clid = claims.total;
show("judge_claim", await as("trigger").send("judge_claim", [clid], 0n));
const cl = await base.view("get_claim", [clid]);
console.log(JSON.stringify({ status: cl.status, cls: cl.classification, peril: cl.peril, date: cl.incident_date,
  bucket: cl.severity_bucket, drop: cl.drop_bps, strength: cl.evidence_strength, hash: cl.content_hash,
  reason: cl.reason, gross: cl.gross_wei, batch: cl.batch_id }, null, 1));
console.log("stats", JSON.stringify(await base.view("get_stats")).slice(0, 600));
