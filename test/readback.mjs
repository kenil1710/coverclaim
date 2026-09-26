// Re-reads every probe result from the lane contracts (the view after each
// write sometimes failed under Studio load while the write itself landed).
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { connect, argOf } from "./harness.mjs";
const lanes = argOf("lanes").split(",");
const dir = new URL("../docs/probe/", import.meta.url);
for (const f of (await import("node:fs")).readdirSync(dir).filter((x) => x.endsWith(".json"))) {
  const rec = JSON.parse(readFileSync(new URL(f, dir), "utf8"));
  if (rec.result && Object.keys(rec.result).length) continue;
  const order = [rec.probe_contract, ...lanes.filter((l) => l !== rec.probe_contract)];
  for (const a of order) {
    let s = "";
    try { s = await connect({ address: a }).view("get", [rec.key]); } catch { s = ""; }
    if (s) { rec.result = JSON.parse(s); rec.read_from = a; break; }
  }
  writeFileSync(new URL(f, dir), JSON.stringify(rec, null, 2));
  console.log(rec.key, rec.result ? "recovered" : "still empty");
}
