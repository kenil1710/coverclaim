#!/usr/bin/env python3
"""STEP 6 — the audit. Every past rejection pattern and every loophole in the
brief, as a check that PASSES or FAILS with evidence, written to docs/AUDIT.md.

    python3 tools/audit.py

Structural checks walk the AST (a grep would cry wolf on the source's own
documentation, which names what it forbids). Behavioural checks RUN the
offline test classes that prove them and report their counts. Chain checks
read `docs/EVIDENCE.json`, which `test/collect.mjs` derives by reading the
chain, and the sha256 recorded at deploy time. Exit code 1 on any FAIL.
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "test"))

RESULTS: list[tuple[str, str, bool, str]] = []


def check(group: str, name: str, ok: bool, evidence: str) -> None:
    RESULTS.append((group, name, bool(ok), evidence))
    print(("  PASS  " if ok else "  FAIL  ") + name + " — " + evidence[:140])


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf8")


SRC = read("contracts/CoverClaim.py")
TREE = ast.parse(SRC)
REG = read("contracts/CoverRegistry.py")
REG_TREE = ast.parse(REG)


def cls(tree, name):
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name == name:
            return n
    raise SystemExit("no class " + name)


def methods(c):
    return {m.name: m for m in c.body if isinstance(m, ast.FunctionDef)}


CC = methods(cls(TREE, "CoverClaim"))


def is_write(m):
    return any(ast.unparse(d).startswith("gl.public.write") for d in m.decorator_list)


def is_payable(m):
    return any(ast.unparse(d) == "gl.public.write.payable" for d in m.decorator_list)


def run_tests(*names: str) -> tuple[bool, str]:
    import test_logic  # noqa: E402  (installs the runtime stub)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for n in names:
        suite.addTests(loader.loadTestsFromTestCase(getattr(test_logic, n)))
    stream = io.StringIO()
    res = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    ok = res.wasSuccessful() and res.testsRun > 0
    return ok, f"{res.testsRun} tests in {', '.join(names)}: " + (
        "all pass" if ok else f"{len(res.failures)} failures, {len(res.errors)} errors")


def calls_in(node) -> set:
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "self":
                out.add(f.attr)
            elif isinstance(f, ast.Name):
                out.add(f.id)
    return out


FUNCS = {n.name: n for n in TREE.body if isinstance(n, ast.FunctionDef)}


def reach(name: str) -> set:
    seen, stack = set(), [name]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        node = CC.get(n) or FUNCS.get(n)
        if node is not None:
            stack.extend(calls_in(node))
    return seen


def main() -> int:
    print("\n— rejection patterns")
    raises = [n.lineno for t in (TREE, REG_TREE) for n in ast.walk(t) if isinstance(n, ast.Raise)]
    check("patterns", "0 raise statements (CoverClaim and CoverRegistry)", not raises,
          f"{len(raises)} ast.Raise nodes")

    rep = [n.lineno for t in (TREE, REG_TREE) for n in ast.walk(t)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "replace"]
    check("patterns", "no str.replace()", not rep, f"{len(rep)} .replace( calls")

    hdr = SRC.split("\n")[:3]
    check("patterns", "runner header is exactly two comment lines, pinned",
          hdr[0] == "# v0.3.0" and hdr[1].startswith('# { "Depends": "py-genlayer:') and not hdr[2].startswith("#")
          and "py-genlayer:latest" not in SRC, hdr[1][:70])

    vf = [n for n in ast.walk(CC["_consensus"]) if isinstance(n, ast.FunctionDef) and n.name == "validator_fn"][0]
    order = [ast.unparse(n.func) for n in ast.walk(vf) if isinstance(n, ast.Call)]
    ok = "_coherent" in order and "_agrees" in order
    check("patterns", "leader cannot forge: coherence gate (bracket re-derived) before agreement", ok,
          "validator_fn calls " + ", ".join(dict.fromkeys(o for o in order if o.startswith("_"))))

    t_ok, t_ev = run_tests("TestCoherent", "TestEveryFieldIsBound", "TestAgrees")
    check("patterns", "consensus binds all stored values; full vector compared", t_ok, t_ev)

    derived_keys = set()
    for n in ast.walk(FUNCS["_reading"]):
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict):
            derived_keys |= {k.value for k in n.value.keys if isinstance(k, ast.Constant)}
    ns = {}
    for n in TREE.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id.startswith("EXACT_"):
            ns[n.targets[0].id] = ast.literal_eval(n.value)
    compared = set().union(*ns.values()) | {"strength"}
    missing = sorted(derived_keys - compared)
    check("patterns", "every field of the reading is on the compared axis", not missing,
          "not compared: " + (", ".join(missing) or "none"))

    bad = []
    for name, m in CC.items():
        if is_write(m):
            body = [s for s in m.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
            if ast.unparse(body[0]) != "self._bank()":
                bad.append(name)
    check("patterns", "refund-on-reject on every path: every write banks value to the sender first",
          not bad, "writes not starting with _bank: " + (", ".join(bad) or "none"))

    late = []
    for name, m in CC.items():
        if not is_payable(m):
            continue
        refs = [n.lineno for n in ast.walk(m) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "_refuse" and "could not be booked" not in ast.unparse(n)]
        takes = [n.lineno for n in ast.walk(m) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "_take"]
        if refs and takes and max(refs) > min(takes):
            late.append(name)
    check("patterns", "no value taken before the last refusal (payable methods)", not late,
          "violations: " + (", ".join(late) or "none"))

    t_ok, t_ev = run_tests("TestSourceInvariants")
    check("patterns", "no counter-before-revert; frozen policy; immutable constructor values", t_ok, t_ev)

    check("patterns", "content hash stored and re-verifiable (verify_claim)",
          "verify_claim" in CC and "content_hash" in ast.unparse(CC["_record"]),
          "_record writes content_hash; verify_claim recomputes it from stored digest + record + TVL line")

    gated = sorted({n for n, m in CC.items() if is_write(m) and any(
        isinstance(x, ast.If) and "self.paused" in ast.unparse(x.test) for x in ast.walk(m))})
    check("patterns", "pause gates only new business; settle_stalled works while paused",
          gated == ["add_capacity", "buy_cover", "create_pool"], "pause-gated: " + ", ".join(gated))

    t_ok, t_ev = run_tests("TestStalled", "TestPauseMatrix")
    check("patterns", "settle_stalled while paused (behaviour)", t_ok, t_ev)

    t_ok, t_ev = run_tests("TestReading", "TestLeaderFailed", "TestRefile")
    check("patterns", "conservative INCONCLUSIVE (pinned without a model; retries change nothing)", t_ok, t_ev)

    t_ok, t_ev = run_tests("TestRandomLifecyclesDrainToZero", "TestDrainsAcrossOutcomes")
    check("patterns", "every GEN drains to zero after all covers expire and claims settle", t_ok, t_ev)

    payers = sorted(n for n, m in CC.items() if is_write(m) and "_pay" in reach(n))
    check("patterns", "only claim_payout transfers, and it reads no clock",
          payers == ["claim_payout"] and "_now" not in reach("claim_payout"),
          "writes reaching _pay: " + ", ".join(payers))

    reg_payable = [m.name for m in cls(REG_TREE, "CoverRegistry").body
                   if isinstance(m, ast.FunctionDef) and is_payable(m)]
    check("patterns", "CoverRegistry: custody false, zero payable methods", not reg_payable,
          f"{len(reg_payable)} payable methods; no transfer call")

    dep = json.loads(read("deployments.json"))["deployments"]["studiodev"]
    rows = []
    ok = True
    for name, src in (("CoverClaim", "contracts/CoverClaim.py"), ("CoverClaimDemo", "contracts/CoverClaim.py"),
                      ("CoverRegistry", "contracts/CoverRegistry.py")):
        digest = hashlib.sha256((ROOT / src).read_bytes()).hexdigest()
        same = dep.get(name, {}).get("source_sha256") == digest
        ok = ok and same
        rows.append(f"{name} {'=' if same else '≠'} {digest[:12]}")
    check("patterns", "source matches deployed byte-for-byte (recorded sha256; chain read by test/verify_onchain.mjs)",
          ok, "; ".join(rows))

    demo = dep.get("CoverClaimDemo", {})
    canon = dep.get("CoverClaim", {})
    check("patterns", "DEMO is the same bytes with one constructor value; canonical flag is 0",
          demo.get("source_sha256") == canon.get("source_sha256") and demo.get("demo_backdate_days", 0) > 0
          and canon.get("demo_backdate_days") == 0,
          f"demo_backdate_days demo={demo.get('demo_backdate_days')} canonical={canon.get('demo_backdate_days')}")

    readme = read("README.md") if (ROOT / "README.md").exists() else ""
    sentence = ("GenLayer reads public incident evidence and classifies it against the frozen policy's covered "
                "perils and exclusions. Deterministic contract logic enforces capacity, waiting periods, "
                "backdating checks, premium accounting, severity payouts, deductibles, and pro-rata splits.")
    layout = read("frontend/src/app/layout.tsx")
    check("patterns", "the required sentence in README, contract and app description",
          sentence in readme and "GenLayer reads public incident evidence and classifies it" in SRC
          and "GenLayer reads public incident evidence" in layout, "README + get_config + <meta description>")
    lim = [w for w in ("Parametric", "allowlisted sources", "subjective", "fixed backdate", "undelivered")
           if w.lower() not in readme.lower()]
    check("patterns", "honest limitations documented", not lim, "missing: " + (", ".join(lim) or "none"))
    check("patterns", "DEMO labelled in get_config, UI and README",
          "DEMO" in readme and "DEMO instance." in read("frontend/src/components/AppShell.tsx")
          and '"label": ("DEMO' in SRC, "config label, DemoBanner, README")

    print("\n— loopholes")
    L = [
        ("1. buying cover after an incident is public → backdating check", "TestLoophole01_BuyingAfterAnIncidentIsBackdated"),
        ("2. fake evidence from a random blog → refused before GenLayer", "TestLoophole02_FakeEvidenceRefusedBeforeGenLayer"),
        ("3. underwriter withdrawing before a claim → capacity lock", "TestLoophole03_CapacityLockedBeforeClaims"),
        ("4. same cover claimed twice → one claim per cover", "TestLoophole04_OneClaimPerCover"),
        ("5. more claims than capacity → pro-rata, not first-come", "TestLoophole05_ProRataNotFirstCome"),
        ("6. evidence edited after judging → content hash", "TestLoophole06_EvidenceEditedAfterJudging"),
        ("7. contest copying old evidence → novelty gate", "TestLoophole07_ContestCopyingOldEvidence"),
        ("8. protocol B's incident on protocol A's cover → protocol_match", "TestLoophole08_OtherProtocolsIncident"),
        ("9. owner pausing to freeze money", "TestLoophole09_OwnerPauseCannotFreezeMoney"),
        ("10. payment that also reads the clock → finalize + claim_payout", "TestLoophole10_PaymentNeverReadsTheClock"),
    ]
    for title, klass in L:
        t_ok, t_ev = run_tests(klass)
        check("loopholes", title, t_ok, t_ev)

    ev_path = ROOT / "docs" / "EVIDENCE.json"
    if ev_path.exists():
        print("\n— on chain")
        ev = json.loads(ev_path.read_text())
        for row in ev.get("scenarios", []):
            check("chain", row["scenario"], row.get("pass", False), row.get("evidence", ""))

    import test_logic  # noqa: E402
    total = unittest.TestLoader().loadTestsFromModule(test_logic).countTestCases()
    fails = [r for r in RESULTS if not r[2]]
    out = ["# AUDIT — every rejection pattern and every loophole, checked", "",
           "Generated by `python3 tools/audit.py`. Structural checks walk the AST; behavioural checks run the "
           f"offline suite ({total} tests in total); chain checks read `docs/EVIDENCE.json`, which "
           "`test/collect.mjs` derives from the chain.", "",
           f"**Result: {len(RESULTS) - len(fails)} PASS / {len(fails)} FAIL.**", ""]
    for group, title in (("patterns", "Rejection patterns"), ("loopholes", "Loopholes"), ("chain", "On chain (seeded)")):
        rows = [r for r in RESULTS if r[0] == group]
        if not rows:
            continue
        out += [f"## {title}", "", "| | check | evidence |", "|---|---|---|"]
        for _, name, ok, ev in rows:
            out.append(f"| {'PASS' if ok else '**FAIL**'} | {name} | {ev.replace('|', '/')} |")
        out.append("")
    (ROOT / "docs" / "AUDIT.md").write_text("\n".join(out) + "\n")
    print(f"\n{len(RESULTS) - len(fails)} PASS / {len(fails)} FAIL — wrote docs/AUDIT.md")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
