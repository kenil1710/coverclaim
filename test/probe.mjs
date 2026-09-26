/**
 * STEP 1 — the source probe. Deploys contracts/_probe.py and asks real
 * validators to read every candidate evidence source, then writes the raw
 * results to docs/probe/<key>.json. docs/PROBE.md is written from these files.
 *
 *   node probe.mjs                  # deploy fresh probes and run every job
 *   node probe.mjs --only=k1,k2     # just these jobs
 *   node probe.mjs --lanes=0x..,0x.. # reuse deployed probe contracts
 *
 * Jobs run in LANES, one probe contract per lane, because a Studio node holds
 * one transaction slot per recipient contract: queueing twenty probes on one
 * address serialises them behind each other's twenty-to-ninety seconds.
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { connect, deploy, fundOnStudio, argOf } from "./harness.mjs";

const day = (iso) => String(Date.parse(iso + "T00:00:00Z") / 1000);

const JOBS = [
  // 1. the incident list
  { key: "hacks_euler", kind: "http", url: "https://api.llama.fi/hacks", mode: "hacks", arg: "1183" },
  { key: "hacks_curve", kind: "http", url: "https://api.llama.fi/hacks", mode: "hacks", arg: "3" },
  { key: "hacks_multichain", kind: "http", url: "https://api.llama.fi/hacks", mode: "hacks", arg: "591" },
  { key: "hacks_tornado", kind: "http", url: "https://api.llama.fi/hacks", mode: "hacks", arg: "148" },
  // 2. TVL history for the severity measure — small, medium, large, huge
  { key: "tvl_euler", kind: "http", url: "https://api.llama.fi/protocol/euler-v1", mode: "tvl", arg: day("2023-03-13") },
  { key: "tvl_tornado", kind: "http", url: "https://api.llama.fi/protocol/tornado-cash", mode: "tvl", arg: day("2023-05-20") },
  { key: "tvl_multichain", kind: "http", url: "https://api.llama.fi/protocol/multichain", mode: "tvl", arg: day("2023-07-07") },
  { key: "tvl_curve", kind: "http", url: "https://api.llama.fi/protocol/curve-dex", mode: "tvl", arg: day("2022-08-09") },
  // 3. rekt.news articles — rendered, strict (validators re-render and vote on the hash)
  { key: "rekt_euler_render", kind: "render", url: "https://rekt.news/euler-rekt", strict: true },
  { key: "rekt_curve_dns_render", kind: "render", url: "https://rekt.news/curve-finance-rekt", strict: true },
  { key: "rekt_multichain_render", kind: "render", url: "https://rekt.news/multichain-r3kt", strict: true },
  { key: "rekt_tornado_render", kind: "render", url: "https://rekt.news/tornado-gov-rekt", strict: true },
  // ... and as a plain GET with tags stripped, the alternative path
  { key: "rekt_euler_get", kind: "gettext", url: "https://rekt.news/euler-rekt", strict: true },
  // 4. official post-mortems
  { key: "pm_euler_render", kind: "render", url: "https://www.euler.finance/blog/war-peace-behind-the-scenes-of-eulers-240m-exploit-recovery", strict: true },
  { key: "pm_kyber_render", kind: "render", url: "https://blog.kyberswap.com/post-mortem-kyberswap-elastic-exploit/", strict: true },
  { key: "pm_balancer_forum", kind: "render", url: "https://forum.balancer.fi/t/balancer-frontend-incident-post-mortem/5153", strict: true },
  { key: "home_euler_render", kind: "render", url: "https://www.euler.finance/", strict: true },
  // 5. archive fallback
  { key: "archive_euler_render", kind: "render", url: "https://web.archive.org/web/20231217192546/https://rekt.news/euler-rekt/", strict: true },
  // 6. things expected to fail, so the allowlist is not built on hope
  { key: "defillama_web_hacks", kind: "render", url: "https://defillama.com/hacks", strict: false },
  { key: "rekt_euler_render_2", kind: "render", url: "https://rekt.news/euler-rekt", strict: true },
  { key: "archive_curve_dns_render", kind: "render", url: "https://web.archive.org/web/2023/https://rekt.news/curve-finance-rekt", strict: true },
  { key: "get_rekt_curve_dns", kind: "gettext", url: "https://rekt.news/curve-finance-rekt", strict: true },
  { key: "get_rekt_multichain", kind: "gettext", url: "https://rekt.news/multichain-r3kt", strict: true },
  { key: "get_rekt_tornado", kind: "gettext", url: "https://rekt.news/tornado-gov-rekt", strict: true },
  { key: "get_archive_euler", kind: "gettext", url: "https://web.archive.org/web/20231217192546/https://rekt.news/euler-rekt/", strict: true },
  { key: "get_pm_euler", kind: "gettext", url: "https://www.euler.finance/blog/war-peace-behind-the-scenes-of-eulers-240m-exploit-recovery", strict: true },
  { key: "get_home_euler", kind: "gettext", url: "https://www.euler.finance/", strict: true },
  { key: "medium_balancer", kind: "render", url: "https://medium.com/balancer-protocol/balancer-frontend-incident-post-mortem-8e6de0c4d2e3", strict: false },
];

const only = argOf("only");
const jobs = only ? JOBS.filter((j) => only.split(",").includes(j.key)) : JOBS;
let lanes = argOf("lanes") ? argOf("lanes").split(",") : null;
const laneCount = Number(argOf("n", "5"));

const base = connect({ address: "0x0000000000000000000000000000000000000000" });
await fundOnStudio(base.chain, base.account.address, 1000n * 10n ** 18n);

if (!lanes) {
  lanes = [];
  const code = readFileSync(new URL("../contracts/_probe.py", import.meta.url));
  for (let i = 0; i < laneCount; i++) {
    const res = await deploy({ chain: base.chain, wallet: base.wallet, read: base.read, code, args: [], label: `probe ${i}` });
    if (!res.ok) { console.error("deploy failed", res.out?.status, res.out?.stderr?.slice(-1500), res.reason); process.exit(1); }
    console.log(`lane ${i}: ${res.address}`);
    lanes.push(res.address);
  }
}

mkdirSync(new URL("../docs/probe/", import.meta.url), { recursive: true });

// One SIGNER per lane as well as one contract: lanes that share a wallet race
// each other's nonces (measured: `NonceTooLow(expected=6,actual=5)` on the
// first run, which dropped three jobs on the floor).
const LANE_ROLES = ["client", "uw1", "uw2", "uw3", "buyer1", "buyer2"];
const acc = JSON.parse(readFileSync(new URL("./.accounts.json", import.meta.url), "utf8"));
for (const role of LANE_ROLES) await fundOnStudio(base.chain, acc[role].address, 200n * 10n ** 18n);

async function run(address, job, lane) {
  const c = connect({ address, role: LANE_ROLES[lane % LANE_ROLES.length] });
  const t0 = Date.now();
  let out;
  if (job.kind === "http") out = await c.send("http_probe", [job.key, job.url, job.mode, job.arg], 0n);
  else if (job.kind === "render") out = await c.send("render_probe", [job.key, job.url, job.strict], 0n);
  else out = await c.send("get_text_probe", [job.key, job.url, job.strict], 0n);
  const secs = Math.round((Date.now() - t0) / 1000);
  let stored = "";
  for (let k = 0; k < 5 && !stored; k++) {
    try { stored = await c.view("get", [job.key]); } catch (e) { stored = ""; }
  }
  const record = {
    key: job.key, url: job.url, kind: job.kind, strict: job.strict ?? null,
    probe_contract: address, tx: out.hash, status: out.status, ok: out.ok, seconds: secs,
    failure: out.failure ?? null, stderr_tail: out.stderr ? out.stderr.slice(-600) : "",
    result: stored ? JSON.parse(stored) : null,
  };
  writeFileSync(new URL(`../docs/probe/${job.key}.json`, import.meta.url), JSON.stringify(record, null, 2));
  const r = record.result || {};
  console.log(`${job.key.padEnd(24)} ${String(out.status).padEnd(12)} ${secs}s  len=${r.len ?? "-"} status=${r.status ?? r.ok ?? "-"} hash=${r.hash ?? "-"} ${r.err ? "err=" + String(r.err).slice(0, 80) : ""}`);
}

const queues = lanes.map(() => []);
jobs.forEach((j, i) => queues[i % lanes.length].push(j));
await Promise.all(queues.map(async (q, i) => {
  for (const job of q) await run(lanes[i], job, i);
}));
console.log("lanes:", lanes.join(","));
