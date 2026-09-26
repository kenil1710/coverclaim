// Deploys a fresh probe and runs one exec_prompt through consensus.
import { readFileSync } from "node:fs";
import { connect, deploy, fundOnStudio, argOf } from "./harness.mjs";
const base = connect({ address: "0x0000000000000000000000000000000000000000", role: "uw3" });
await fundOnStudio(base.chain, base.account.address, 100n * 10n ** 18n);
let address = argOf("address");
if (!address) {
  const code = readFileSync(new URL("../contracts/_probe.py", import.meta.url));
  const res = await deploy({ chain: base.chain, wallet: base.wallet, read: base.read, code, args: [], label: "llm probe deploy" });
  if (!res.ok) { console.log("deploy failed", res.reason, res.out?.stderr?.slice(-500)); process.exit(1); }
  address = res.address;
}
console.log("probe", address);
const c = connect({ address, role: "uw3" });
const t0 = Date.now();
const out = await c.send("llm_probe", ["llm1", 'Answer ONLY with JSON: {"classification": "COVERED", "evidence_strength": 4}'], 0n);
console.log("llm_probe", out.status, ((Date.now() - t0) / 1000).toFixed(0) + "s", out.hash);
console.log(await c.view("get", ["llm1"]));
