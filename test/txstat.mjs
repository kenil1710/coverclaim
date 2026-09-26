// Status + consensus timeline for one transaction hash.
import { connect, argOf } from "./harness.mjs";
import { transactionsStatusNumberToName } from "genlayer-js/types";
const c = connect({ address: "0x0000000000000000000000000000000000000000" });
const tx = await c.read.getTransaction({ hash: argOf("hash") });
const j = JSON.parse(JSON.stringify(tx, (k, v) => (typeof v === "bigint" ? v.toString() : v)));
console.log("status", transactionsStatusNumberToName[j.status] ?? j.status, j.txExecutionResultName, "created", j.created_at);
const mon = j.consensus_history?.current_monitoring ?? {};
const t0 = Math.min(...Object.values(mon).map(Number));
for (const [k, v] of Object.entries(mon).sort((a, b) => a[1] - b[1])) console.log("  +" + (v - t0).toFixed(1) + "s", k);
console.log("  now +" + (Date.now() / 1000 - t0).toFixed(0) + "s");
const hist = j.consensus_history?.consensus_results ?? [];
for (const h of hist) console.log(" round", JSON.stringify(h).slice(0, 400));
const lr = j.consensus_data?.leader_receipt?.[0];
if (lr) console.log(" leader", lr.execution_result, String(lr.genvm_result?.stderr ?? "").slice(-800));
