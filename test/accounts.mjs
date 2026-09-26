/**
 * Creates test/.accounts.json — a stable, reusable pool of signing keys.
 *
 * A POOL rather than one key because CoverClaim's rules are RELATIONAL. "Only
 * the underwriter may withdraw capacity", "only the buyer may claim", "the
 * losing side may contest" and "anyone may trigger a judgement" cannot even be
 * STATED with a single address, and the pro-rata case needs two buyers on one
 * incident.
 *
 * Keys are written by hand rather than read off `createAccount()`, because that
 * helper does NOT expose a `privateKey` field — it returns a viem account whose
 * key stays private to the closure. Persisting `account.privateKey` therefore
 * writes `undefined`, JSON.stringify drops the field entirely, and every later
 * `createAccount(undefined)` silently mints a brand-new random account. On a
 * faucet-funded network that failure is INVISIBLE: every run works, just from a
 * different address each time. It surfaces later, as access-control tests that
 * can never trigger and a treasurer nobody holds the key to.
 *
 * Existing roles are PRESERVED across runs unless --force is passed, so a
 * funded address is never silently replaced.
 *
 * Usage: node accounts.mjs [--force]
 */
import { createAccount } from "genlayer-js";
import { randomBytes } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";

const target = new URL("./.accounts.json", import.meta.url);
const force = process.argv.includes("--force");

// `client` deploys and owns both instances. Its only power is pausing NEW
// pools and NEW covers. `uw1..uw3` are underwriters: a pool is one wallet's
// capital, and the seed needs several pools. `buyer1..buyer6` buy cover and
// file claims - one claim per cover, and the pro-rata scenario needs two
// buyers on one incident. `trigger` calls judge_claim / finalize_incident,
// which proves those paths are permissionless. `outsider` only ever probes
// access control and must never be granted a privilege by any script.
const ROLES = [
  "client",
  "uw1", "uw2", "uw3",
  "buyer1", "buyer2", "buyer3", "buyer4", "buyer5", "buyer6",
  "trigger", "outsider",
];

const existing = existsSync(target) && !force ? JSON.parse(readFileSync(target, "utf8")) : {};
const out = {};
let created = 0;

for (const role of ROLES) {
  if (existing[role]?.key) {
    out[role] = existing[role];
    continue;
  }
  const key = `0x${randomBytes(32).toString("hex")}`;
  const account = createAccount(key);
  // Round-trip assertion: the stored address must be the one this key actually
  // derives. Without it a mismatch just sits in the file looking plausible.
  if (createAccount(key).address !== account.address) {
    throw new Error(`key for ${role} does not derive a stable address`);
  }
  out[role] = { key, address: account.address };
  created++;
}

writeFileSync(target, JSON.stringify(out, null, 2) + "\n");
console.log(`wrote .accounts.json — ${created} new, ${ROLES.length - created} preserved`);
for (const role of ROLES) console.log(`  ${role.padEnd(12)} ${out[role].address}`);
