/**
 * Deploys CoverClaim (canonical), CoverClaimDemo (same bytes, fixed backdate)
 * and CoverRegistry to Studio Dev, and records every address and the sha256 of
 * the deployed bytes in deployments.json.
 *
 *   node deploy.mjs --all            # all three
 *   node deploy.mjs --only=CoverClaimDemo
 *
 * WHY TWO INSTANCES OF ONE SOURCE. Real hacks are in the past, and the
 * canonical instance enforces backdating strictly: a cover bought today can
 * never pay for Euler's 2023 exploit, which is the whole point. So a claim
 * path against a REAL incident can only be demonstrated on a second instance
 * whose constructor fixes `demo_backdate_days`: every cover sold there starts
 * that many days before it is bought. Same bytes, different constructor value,
 * labelled DEMO by `get_config`, in the UI and in the README - the pattern of
 * WillExecutorDemo and GrantJudgeDemo. Its process windows are minutes, not
 * days, so that settlement, contest and stall paths can be watched.
 *
 * Persisted after EACH contract: a deploy record that only survives a clean run
 * loses exactly the addresses you need after a partial failure.
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { createClient, createAccount } from "genlayer-js";
import { CHAINS, argOf, accounts, fundOnStudio, deploy, gen } from "./harness.mjs";

const networkName = argOf("network", "studiodev");
const chain = CHAINS[networkName];
const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");
const version = (src) => String(src).match(/^POLICY_VERSION\s*=\s*"([^"]+)"/m)[1];

const acc = accounts();
const account = createAccount(acc.client.key);
const wallet = createClient({ chain, account });
const read = createClient({ chain });

console.log(`\nCoverClaim deploy -> ${networkName}`);
console.log(`  signer     ${account.address} (client)`);
await fundOnStudio(chain, account.address, 2000n * 10n ** 18n);
console.log(`  balance    ${gen(await read.getBalance({ address: account.address }))} GEN`);

const path = new URL("../deployments.json", import.meta.url);
const doc = existsSync(path) ? JSON.parse(readFileSync(path, "utf8")) : {};
doc.deployments = doc.deployments || {};
const record = doc.deployments[networkName] || { network: networkName, chain_id: chain.id };
function persist() {
  record.explorer = "https://explorer-studio-dev.genlayer.com/";
  doc.deployments[networkName] = record;
  writeFileSync(path, JSON.stringify(doc, null, 2) + "\n");
}

const code = readFileSync(new URL("../contracts/CoverClaim.py", import.meta.url));
const regCode = readFileSync(new URL("../contracts/CoverRegistry.py", import.meta.url));
const GEN = 10n ** 18n;

// Covers bought on the demo instance on 2026-09-29 start on 2022-07-31, so a
// 365-day cover with a 7-day waiting period covers 2022-08-07 .. 2023-07-31.
// That puts BOTH of Curve's recorded incidents - the DNS hijack (2022-08-09)
// and the Vyper reentrancy (2023-07-30) - inside ONE cover, which is what the
// multi-incident proof needs, with Euler (2023-03-13), Tornado Cash's
// governance takeover (2023-05-20) and Multichain (2023-07-07). A cover bought
// up to 2026-09-30 still spans both. FIXED HERE, AT DEPLOY, FOREVER.
const DEMO_BACKDATE_DAYS = 1521;

// (demo_backdate_days, claim_window_s, settlement_window_s, contest_window_s,
//  stall_ttl_s, buy_cooldown_s, contest_bond_wei)
const VARIANTS = {
  CoverClaim: {
    label: "canonical: backdating strict, 30d claim window, 72h settlement, 48h contest, 24h stall",
    args: [0, 30 * 86400, 72 * 3600, 48 * 3600, 24 * 3600, 60, GEN / 10n],
  },
  CoverClaimDemo: {
    label: `DEMO: covers backdated ${DEMO_BACKDATE_DAYS} days; windows in minutes`,
    args: [DEMO_BACKDATE_DAYS, 45 * 60, 15 * 60, 15 * 60, 10 * 60, 10, GEN / 10n],
  },
};

// STAGING: same bytes, covers start ONE day before purchase, so a cover
// bought today can name today's date - the only way to show the
// early-judging refusal on chain when no real incident is under 8 days old.
VARIANTS.CoverClaimStaging = {
  label: "STAGING: covers backdated 1 day; windows in minutes (early-judging demonstration only)",
  args: [1, 45 * 60, 15 * 60, 15 * 60, 10 * 60, 10, GEN / 10n],
};

const only = argOf("only");
const wanted = only ? only.split(",") : ["CoverClaim", "CoverClaimDemo", "CoverRegistry"];

for (const name of wanted.filter((n) => VARIANTS[n])) {
  const { label, args } = VARIANTS[name];
  console.log(`\n  ${name}  ${label}`);
  console.log(`  source     contracts/CoverClaim.py (${code.length.toLocaleString()} bytes, sha256 ${sha256(code).slice(0, 16)}…)`);
  const res = await deploy({ chain, wallet, read, code, args, label: `${name} deploy` });
  if (!res.ok) {
    console.error(`\n${name} deploy FAILED: ${res.out?.status} ${res.reason ?? ""} ${res.out?.revertReason ?? ""}`);
    console.error((res.out?.stderr ?? "").split("\n").slice(-30).join("\n"));
    persist();
    process.exit(1);
  }
  console.log(`  address    ${res.address}`);
  record[name] = {
    address: res.address,
    deploy_tx: res.hash,
    source_bytes: code.length,
    source_sha256: sha256(code),
    policy_version: version(code),
    owner: account.address,
    demo: args[0] > 0,
    demo_backdate_days: args[0],
    claim_window_s: args[1],
    settlement_window_s: args[2],
    contest_window_s: args[3],
    stall_ttl_s: args[4],
    buy_cooldown_s: args[5],
    contest_bond_wei: args[6].toString(),
    deployed_at: new Date().toISOString(),
  };
  persist();
}

if (wanted.includes("CoverRegistry")) {
  // The registry reads the CANONICAL instance: it answers "is this wallet
  // insured right now", and a demo cover - backdated into 2022 - never is.
  const target = record.CoverClaim?.address;
  if (!target) throw new Error("deploy CoverClaim first");
  console.log(`\n  CoverRegistry  reads ${target}`);
  const res = await deploy({ chain, wallet, read, code: regCode, args: [target], label: "CoverRegistry deploy" });
  if (!res.ok) {
    console.error(`\nCoverRegistry deploy FAILED: ${res.out?.status} ${res.reason ?? ""}`);
    console.error((res.out?.stderr ?? "").split("\n").slice(-30).join("\n"));
    persist();
    process.exit(1);
  }
  console.log(`  address    ${res.address}`);
  record.CoverRegistry = {
    address: res.address,
    deploy_tx: res.hash,
    source_bytes: regCode.length,
    source_sha256: sha256(regCode),
    coverclaim: target,
    owner: account.address,
    custody: false,
    payable_methods: 0,
    deployed_at: new Date().toISOString(),
  };
  persist();
}
console.log(`\nwrote deployments.json`);
