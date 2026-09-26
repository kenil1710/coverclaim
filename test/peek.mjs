// Read-only peek at a deployed instance: config, stats, claims.
import { connect, argOf } from "./harness.mjs";
const c = connect({ address: argOf("address") });
const what = argOf("what", "claims");
if (what === "config") console.log(JSON.stringify(await c.view("get_config"), (k, v) => typeof v === "bigint" ? v.toString() : v).slice(0, 800));
if (what === "stats") console.log(JSON.stringify(await c.view("get_stats"), (k, v) => typeof v === "bigint" ? v.toString() : v));
if (what === "claims") {
  const r = await c.view("get_claims", [0, 100]);
  for (const x of r.items ?? []) console.log(JSON.stringify({ id: x.claim_id, st: x.status, cls: x.classification, peril: x.peril, excl: x.exclusion, date: x.incident_date, b: x.severity_bucket, s: x.evidence_strength, at: x.attempts, reason: String(x.reason).slice(0, 160) }, (k, v) => typeof v === "bigint" ? v.toString() : v));
}
if (what === "tx") {
  const tx = await c.read.getTransaction({ hash: argOf("hash") });
  console.log(JSON.stringify(tx, (k, v) => typeof v === "bigint" ? v.toString() : v).slice(0, 3000));
}
