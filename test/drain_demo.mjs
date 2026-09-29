// Close every demo pool that can be closed, and withdraw underwriter balances.
// Step 1 reads state; releases covers whose claim window has closed with
// nothing owed (permissionless release_cover); closes pools with no live
// cover (underwriter); claim_payout per underwriter; reports what remains.
import { readFileSync, writeFileSync } from "node:fs";
import { connect, accounts, returnedJson } from "./harness.mjs";
const dep = JSON.parse(readFileSync(new URL("../deployments.json", import.meta.url), "utf8")).deployments.studiodev;
const A = dep.CoverClaimDemo.address;
const acc = accounts();
const roleOf = Object.fromEntries(Object.entries(acc).map(([r, v]) => [v.address.toLowerCase(), r]));
const v = connect({ address: A });
const gen = (w) => (Number(BigInt(w ?? 0) / 10n ** 12n) / 1e6).toFixed(6);
const log = [];
async function step(label, role, m, args) {
  const out = await connect({ address: A, role }).send(m, args, 0n);
  const r = returnedJson(out);
  log.push({ label, role, method: m, args, tx: out.hash, status: out.status, returned: r });
  console.log(`  ${label}: ${out.status} ${r?.status ?? ""} ${r?.reason ?? ""} ${out.hash}`);
  return r;
}
const cfg = await v.view("get_config");
const pools = (await v.view("get_pools", [0, 100])).items;
console.log("now", cfg.now, "\n== state");
const plan = [];
for (const p of pools) {
  const covers = (await v.view("get_covers_by_pool", [p.pool_id])).items;
  console.log(`pool #${p.pool_id} ${p.protocol_name} ${p.status} capital ${gen(p.capital_wei)} locked ${gen(p.locked_wei)} premiums held ${gen(p.premiums_held_wei)} active ${p.active_covers}`);
  for (const c of covers) {
    let cl = null;
    if (c.claim_id) cl = await v.view("get_claim", [c.claim_id]);
    const deadlinePassed = Number(cfg.now) > Number(c.claim_deadline);
    console.log(`   cover #${c.cover_id} ${c.status} deadline ${c.claim_deadline} passed=${deadlinePassed} claim ${cl ? `#${cl.claim_id} ${cl.status} contest=${cl.contest_status || "-"}` : "-"}`);
    if (c.status === "ACTIVE") plan.push(c.cover_id);
  }
}
console.log("\n== release covers whose windows have closed");
for (const id of plan) await step(`release cover #${id}`, "trigger", "release_cover", [id]);
console.log("\n== close pools with no live cover");
for (const p of (await v.view("get_pools", [0, 100])).items) {
  if (p.status !== "OPEN") continue;
  if (Number(p.active_covers) > 0) { console.log(`  pool #${p.pool_id}: ${p.active_covers} live cover(s), cannot close`); continue; }
  await step(`close pool #${p.pool_id}`, roleOf[p.underwriter.toLowerCase()], "close_pool", [p.pool_id]);
}
console.log("\n== withdraw every balance still owed (underwriters, buyers, bond holders, overpayments)");
for (const [role, a] of Object.entries(acc)) {
  const owed = await v.view("payout_of", [a.address]);
  if (BigInt(owed.owed_wei) > 0n) await step(`claim_payout ${role} (${gen(owed.owed_wei)} GEN)`, role, "claim_payout", []);
}
const s = await v.view("get_stats");
const out = { at: new Date().toISOString(), pools: (await v.view("get_pools", [0, 100])).items.map((p) => ({ id: p.pool_id, status: p.status, capital_wei: p.capital_wei, locked_wei: p.locked_wei, premiums_held_wei: p.premiums_held_wei, active_covers: p.active_covers })), stats: { balance_wei: s.balance_wei, held_wei: s.held_wei, payable_wei: s.payable_wei, locked_wei: s.locked_wei, capital_wei: s.capital_wei, bonds_wei: s.bonds_wei, chain_balance_wei: s.chain_balance_wei, undelivered_wei: s.undelivered_wei, ledger_balanced: s.ledger_balanced, held_matches_books: s.held_matches_books }, steps: log };
writeFileSync(new URL("../docs/drain-evidence.json", import.meta.url), JSON.stringify(out, (k, x) => (typeof x === "bigint" ? x.toString() : x), 2) + "\n");
console.log("\n== after");
for (const p of out.pools) console.log(`pool #${p.id} ${p.status} capital ${gen(p.capital_wei)} locked ${gen(p.locked_wei)} premiums held ${gen(p.premiums_held_wei)}`);
console.log(`books: balance ${gen(s.balance_wei)} = held ${gen(s.held_wei)} + payable ${gen(s.payable_wei)} | balanced ${s.ledger_balanced}/${s.held_matches_books}`);
console.log(`chain balance ${gen(s.chain_balance_wei)} | undelivered ${gen(s.undelivered_wei)}`);
