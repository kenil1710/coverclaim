// Runs CoverClaim's judging pipeline stage by stage on Studio (see _probe_pipe.py).
import { readFileSync } from "node:fs";
import { connect, deploy, fundOnStudio, argOf } from "./harness.mjs";
const role = argOf("role", "uw2");
const base = connect({ address: "0x0000000000000000000000000000000000000000", role });
await fundOnStudio(base.chain, base.account.address, 100n * 10n ** 18n);
let address = argOf("address");
if (!address) {
  const code = readFileSync(new URL("../contracts/_probe_pipe.py", import.meta.url));
  const res = await deploy({ chain: base.chain, wallet: base.wallet, read: base.read, code, args: [], label: "pipe deploy" });
  if (!res.ok) { console.log("deploy failed", res.reason, res.out?.stderr?.slice(-800)); process.exit(1); }
  address = res.address;
}
console.log("pipe", address);
const c = connect({ address, role });
for (const n of (argOf("stages", "1,2,3,4,5,6,7")).split(",").map(Number)) {
  const t0 = Date.now();
  const out = await c.send("stage", ["s" + n, n], 0n);
  console.log("stage", n, out.status, ((Date.now() - t0) / 1000).toFixed(0) + "s", out.hash);
  console.log("   ", (await c.view("get", ["s" + n])).slice(0, 600));
  if (!out.ok) break;
}
