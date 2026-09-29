// On-chain demonstration of the waiting-period gate (review fix 1) on the
// canonical instance: a claim filed inside a 7-day waiting period is refused
// mechanically, and the cover's one claim is NOT spent.
import { readFileSync, writeFileSync } from "node:fs";
import { connect, returnedJson } from "./harness.mjs";
const GEN = 10n ** 18n;
const dep = JSON.parse(readFileSync(new URL("../deployments.json", import.meta.url), "utf8")).deployments.studiodev;
const A = dep.CoverClaim.address;
const log = [];
async function step(label, role, m, args, value = 0n) {
  const out = await connect({ address: A, role }).send(m, args, value);
  const r = { label, method: m, tx: out.hash, status: out.status, returned: returnedJson(out) };
  log.push(r); console.log(label, out.status, out.hash, JSON.stringify(r.returned)?.slice(0, 220));
  return r;
}
const v = connect({ address: A });
await step("wait7-pool", "uw3", "create_pool", ["Euler", "euler-v1", "1183", "Ethereum", "SMART_CONTRACT_BUG,ECONOMIC_EXPLOIT",
  "PHISHING,FRONTEND_HIJACK,USER_KEY_COMPROMISE,RUG_BY_TEAM,GOVERNANCE_ATTACK", 100, 7, 1000, GEN, 90, 10000, "", "euler.finance",
  "Waiting-period gate demonstration."], GEN);
const pid = (await v.view("get_pools", [0, 100])).total;
const q = await v.view("quote", [pid, GEN / 10n, 30]);
await step("wait7-cover", "outsider", "buy_cover", [pid, GEN / 10n, 30], BigInt(q.premium_wei));
const covers = await v.view("get_covers_by_buyer", [JSON.parse(readFileSync(new URL("./.accounts.json", import.meta.url))).outsider.address]);
const cid = covers.items[covers.items.length - 1].cover_id;
await step("wait7-file-refused", "outsider", "file_claim", [cid, "1183:2023-03-13", "https://rekt.news/euler-rekt", "filed inside the waiting period"]);
const after = await v.view("get_cover", [cid]);
log.push({ label: "cover-after", cover_id: cid, claim_id: after.claim_id, claimable: after.claimable, in_waiting_period: after.in_waiting_period, waiting_ends: after.waiting_ends });
console.log("cover after:", JSON.stringify(log[log.length - 1]));
writeFileSync(new URL("../docs/waitgate-evidence.json", import.meta.url), JSON.stringify(log, null, 2) + "\n");
