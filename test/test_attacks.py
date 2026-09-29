#!/usr/bin/env python3
"""Hostile-review findings against CoverClaim. Each test states the property
the contract claims and FAILS on the current source.

    python3 test/test_attacks.py

Reuses the fakes and fixtures of test_logic.py (stdlib only, offline).
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_logic as T  # noqa: E402
from test_logic import (C, WEB, GEN, HOUR, DAY, ALICE, BOB, CAROL, STRANGER,  # noqa: E402
                        UW, CURVE, EULER, R_EULER, R_VYPER, R_CURVE_DNS, A_EULER,
                        K_EULER, K_VYPER, K_DNS, CALLS, MODEL, RENDER, fresh,
                        make_pool, buy, file, judge, send, ok, rejected, advance,
                        set_now, epoch, proto, TVL, view, _TopStrength, TREE,
                        _class, _methods)
import ast  # noqa: E402


class Finding1_VerifiedPoolNameThatNoEvidenceNames(unittest.TestCase):
    """README 2c: verify_pool exists so that a pool "selling cover that can
    never pay" cannot sell. But verification accepts DeFi Llama's OWN name
    ("Curve DEX", "Euler V1"), and binding requires every evidence page to
    contain the pool's name word-for-word. rekt.news writes "Curve Finance"
    and "Euler Finance", never "Curve DEX" or "Euler V1". So the underwriter
    picks a name that passes verification and fails every claim."""

    def run_pool(self, name):
        c = fresh()
        pid = make_pool(c, spec=dict(CURVE, name=name))
        self.assertEqual(str(c.pools[pid - 1].status), "OPEN")   # verified, sells
        cid = buy(c, pid)
        clid = file(c, cid, R_VYPER, key=K_VYPER)
        return judge(c, clid)

    def test_control_pool_named_curve_pays(self):
        self.assertEqual(self.run_pool("Curve")["outcome"], "APPROVED")

    def test_pool_named_with_defillamas_own_name_pays_on_the_same_evidence(self):
        out = self.run_pool("Curve DEX")          # DeFi Llama's own name for id 3
        # Same record, same rekt.news article, same TVL: must be APPROVED.
        self.assertEqual(out["outcome"], "APPROVED", out.get("reason"))

    def test_euler_v1_pool_pays_on_the_euler_article(self):
        c = fresh()
        pid = make_pool(c, spec=dict(EULER, name="Euler V1"))
        self.assertEqual(str(c.pools[pid - 1].status), "OPEN")
        cid = buy(c, pid)
        clid = file(c, cid, R_EULER, key=K_EULER)
        out = judge(c, clid)
        self.assertEqual(out["outcome"], "APPROVED", out.get("reason"))


class Finding2_SeverityFixedBeforeTheSevenDayWindowExists(unittest.TestCase):
    """README: severity is the drop "from the day before to the 7-day low".
    `_tvl` takes whatever part of the window DeFi Llama has published at the
    moment of judging, and `judge_claim` is permissionless with no check that
    incident day + 7 days has passed. The underwriter judges the claim the
    moment it is filed. If the partial drop lands in a paying bucket the claim
    is APPROVED at that bucket, and an APPROVED claim can be contested only
    by the underwriter: the buyer is paid the small bucket for good.

    The TVL series here is synthetic (Euler's real record and real
    pre-incident points, then a drop over several days). Real series show the
    lag exists: Multichain's record is 2023-07-07 and its TVL fell on
    2023-07-13, day 6 of the window."""

    def euler_doc(self, cutoff):
        doc = json.loads(TVL["euler-v1"])
        d0 = epoch("2023-03-13T00:00:00Z")
        # real points up to and including the incident day, then a slow drain
        staged = {d0 + 1 * DAY: 180_000_000,     # -23% vs 2023-03-12 -> bucket 1
                  d0 + 2 * DAY: 150_000_000,
                  d0 + 3 * DAY: 20_000_000,
                  d0 + 4 * DAY: 10_000_000,      # -95.7% -> bucket 4
                  # the rest of the 7-day window, so that it EXISTS once published
                  d0 + 5 * DAY: 10_000_000,
                  d0 + 6 * DAY: 10_000_000,
                  d0 + 7 * DAY: 10_000_000}
        pts = []
        for p in doc["tvl"]:
            if p["date"] <= d0:
                pts.append(p)
        for d, v in sorted(staged.items()):
            pts.append({"date": d, "totalLiquidityUSD": v})
        doc["tvl"] = [p for p in pts if p["date"] <= cutoff]
        return json.dumps(doc)

    def test_early_judgement_does_not_fix_a_partial_severity(self):
        c = fresh(demo=False)                      # canonical instance
        set_now(epoch("2023-03-01T12:00:00Z"))
        pid = make_pool(c, spec=EULER)
        cid = buy(c, pid, amount=GEN, days=60)
        # 2023-03-14 18:00: rekt.news article is out (dated 2023-03-14).
        now = epoch("2023-03-14T18:00:00Z")
        set_now(now)
        WEB[proto("euler-v1")] = (200, self.euler_doc(now))
        clid = file(c, cid, R_EULER, key=K_EULER)
        early = judge(c, clid)                     # the underwriter triggers it
        # FIXED: refused. Nothing is judged, nothing is fixed, nothing fetched.
        self.assertTrue(rejected(early), early)
        self.assertIn("7-day TVL window", early["reason"])
        k = c.claims[clid - 1]
        self.assertEqual((str(k.status), int(k.judged_at), int(k.gross_wei)), ("FILED", 0, 0))
        # Still refused one second before day + 8 (the window's last point).
        set_now(epoch("2023-03-21T00:00:00Z") - 1)
        self.assertTrue(rejected(judge(c, clid)))
        # What the same claim is worth once the 7-day window exists:
        set_now(now + 7 * DAY)
        WEB[proto("euler-v1")] = (200, self.euler_doc(now + 7 * DAY))
        raw = C._read_sources(c._claim_facts(c.claims[clid - 1], c.covers[cid - 1],
                                             c.pools[pid - 1], "claim"))
        full_bucket = C._reading(c._claim_facts(c.claims[clid - 1], c.covers[cid - 1],
                                                c.pools[pid - 1], "claim"), raw)["bucket"]
        self.assertEqual(full_bucket, 4)
        late = judge(c, clid)
        self.assertEqual(late["outcome"], "APPROVED")
        self.assertEqual(late["severity_bucket"], full_bucket,
                         "severity was fixed from a partial window: bucket %d "
                         "(gross %s wei) instead of %d" % (
                             late["severity_bucket"], late["gross_payout_wei"],
                             full_bucket))


def C_BOND(c):
    return int(c.contest_bond_wei)


class Finding3_LateApprovalsHoldASettlementBatchOpenIndefinitely(unittest.TestCase):
    """finalize_incident's docstring: "Only after the settlement window closes
    ... so the set of claims is final before anything is divided". But
    `_join_batch` never checks `closes_at`: any claim APPROVED on the incident
    joins the still-OPEN batch after its window closed, and finalize refuses
    until THAT claim's 48 h contest window passes. A second wallet holding a
    handful of 0.01 GEN covers files and judges one claim every 47 h and the
    honest buyer is never paid. Nobody else can pre-empt it: only the buyer can
    file, and an unfiled claim cannot be judged early."""

    def test_honest_claim_is_paid_after_the_window(self):
        c = fresh()
        pid = make_pool(c, spec=EULER)
        alice = buy(c, pid, who=ALICE, amount=GEN)
        griefer = []
        for _ in range(8):                          # 8 x 0.01 GEN from one wallet
            advance(61)
            griefer.append(buy(c, pid, who=BOB, amount=10 ** 16))
        a = file(c, alice, R_EULER, key=K_EULER)
        out = judge(c, a)
        self.assertEqual(out["outcome"], "APPROVED")
        bid = int(out["batch_id"])
        t0 = T.now_of()
        closes = int(c.batches[bid - 1].closes_at)
        late = []
        for cid in griefer:
            advance(47 * HOUR)
            g = file(c, cid, R_EULER, key=K_EULER)
            self.assertEqual(judge(c, g)["outcome"], "APPROVED")
            # FIXED: only an approval inside Alice's window joins her batch;
            # every later one goes to a NEW batch.
            if T.now_of() < closes:
                self.assertEqual(int(c.claims[g - 1].batch_id), bid)
            else:
                self.assertNotEqual(int(c.claims[g - 1].batch_id), bid)
                late.append(g)
        self.assertGreater(len(late), 5)
        # 16 days after Alice's approval; her batch's window closed on day 3.
        self.assertGreater(T.now_of() - t0, 15 * DAY)
        fin = send(c, STRANGER, 0, "finalize_incident", bid)
        self.assertTrue(ok(fin), "Alice still unpaid after %d days: %s" % (
            (T.now_of() - t0) // DAY, fin.get("reason")))
        self.assertEqual(int(c.claims[a - 1].payout_wei), C._gross(GEN, 10000, 1000))
        # The late claims settle in their own batches; no batch waits on another,
        # and total payouts never exceed the capacity locked for the covers.
        advance(73 * HOUR)
        for b in c.batches:
            if str(b.status) == "OPEN":
                self.assertTrue(ok(send(c, STRANGER, 0, "finalize_incident", int(b.batch_id))))
        for g in late:
            self.assertEqual(str(c.claims[g - 1].status), "PAID")
        self.assertLessEqual(sum(int(k.payout_wei) for k in c.claims),
                             sum(int(cv.lock_wei) for cv in c.covers))


class Finding4_RefileRerollsTheSameEvidence(unittest.TestCase):
    """README: an INCONCLUSIVE claim is refiled "with at least one new source
    or a corrected key"; refile_claim says "nothing is gained by resubmitting
    it". Both checks compare spellings, not sources: the same page with a
    `#fragment` (never sent to the server), or the same record's key written
    with / without its name, passes. The claimant re-rolls the identical
    reading as often as they like until the deadline - e.g. a single-source
    bracket of strength 2..3, where 2 is INCONCLUSIVE and 3 is COVERED."""

    def setUp(self):
        self.c = fresh()
        pid = make_pool(self.c, spec=EULER)
        cid = buy(self.c, pid)
        self.clid = file(self.c, cid, R_EULER, key=K_EULER)
        out = judge(self.c, self.clid, classification="INCONCLUSIVE",
                    peril="NONE")
        self.assertEqual(out["outcome"], "INCONCLUSIVE")

    def test_same_page_with_a_fragment_is_not_a_new_source(self):
        out = send(self.c, ALICE, 0, "refile_claim", self.clid, "",
                   R_EULER + "#again", "same")
        self.assertTrue(rejected(out), "identical evidence accepted as new")

    def test_respelled_key_for_the_same_record_is_not_a_correction(self):
        out = send(self.c, ALICE, 0, "refile_claim", self.clid,
                   K_EULER + ":Euler V1", R_EULER, "same")
        self.assertTrue(rejected(out), "same record accepted as a corrected key")


# ===========================================================================
# The fixes, tested as specified.
# ===========================================================================


class Fix1_CoreName(unittest.TestCase):
    def verdict(self, name, url=R_VYPER, key=K_VYPER):
        c = fresh()
        pid = make_pool(c, spec=dict(CURVE, name=name))
        cid = buy(c, pid)
        clid = file(c, cid, url, key=key)
        out = judge(c, clid)
        k = c.claims[clid - 1]
        return (out["outcome"], out["severity_bucket"], out["drop_bps"], out["classification"],
                out["gross_payout_wei"], str(k.content_hash), str(k.digest), str(k.bracket),
                str(k.bind_line), str(k.reason), bool(k.protocol_match))

    def test_curve_and_curve_dex_give_identical_results(self):
        base = self.verdict("Curve")
        self.assertEqual(base[0], "APPROVED")
        for name in ("Curve DEX", "Curve Finance", "curve", "CURVE  DEX"):
            self.assertEqual(self.verdict(name), base, name)

    def test_core_name_derivation(self):
        for llama, core in (("Curve DEX", "Curve"), ("Euler V1", "Euler"),
                            ("Balancer V2", "Balancer"), ("Mango Markets V3", "Mango Markets"),
                            ("Tornado Cash", "Tornado Cash"), ("Multichain", "Multichain"),
                            ("KyberSwap Elastic", "KyberSwap Elastic"), ("Foo Finance Protocol", "Foo"),
                            ("V1", "V1")):
            self.assertEqual(C._core_name(llama), core, llama)

    def test_names_with_a_different_core_still_fail_verification(self):
        for name in ("Aave", "Curve Lending", "V1", "DEX"):
            c = fresh()
            pid = make_pool(c, spec=dict(CURVE, name=name), verify=False)
            self.assertEqual(send(c, STRANGER, 0, "verify_pool", pid)["outcome"],
                             "FAILED_VERIFICATION", name)

    def test_evidence_is_matched_on_the_stored_core_name(self):
        c = fresh()
        pid = make_pool(c, spec=dict(CURVE, name="Curve DEX"))
        self.assertEqual(str(c.pools[pid - 1].core_name), "Curve")
        facts = c._claim_facts(c.claims[file(c, buy(c, pid), R_VYPER, key=K_VYPER) - 1],
                               c.covers[0], c.pools[pid - 1], "claim")
        self.assertEqual(facts["protocol_name"], "Curve")


class Fix2_FullSeverityWindow(unittest.TestCase):
    def test_judging_early_is_refused_before_any_fetch(self):
        c = fresh(demo=False)
        set_now(epoch("2023-07-01T12:00:00Z"))
        pid = make_pool(c, spec=CURVE)
        cid = buy(c, pid, amount=GEN // 2, days=60)
        set_now(epoch("2023-07-31T12:00:00Z"))
        clid = file(c, cid, R_VYPER, key=K_VYPER)
        del CALLS[:]
        out = judge(c, clid)
        self.assertTrue(rejected(out))
        self.assertEqual(out["judgeable_at"], epoch("2023-08-07T00:00:00Z"))
        self.assertEqual(CALLS, [])
        self.assertEqual(MODEL.calls, 0)
        self.assertEqual(view(c, "get_claim", clid)["judgeable_at"], epoch("2023-08-07T00:00:00Z"))
        set_now(epoch("2023-08-07T00:00:00Z"))
        self.assertEqual(judge(c, clid, "COVERED", "SMART_CONTRACT_BUG")["severity_bucket"], 2)

    def test_window_still_unpublished_after_day_8_is_inconclusive_refileable(self):
        c = fresh()
        pid = make_pool(c, spec=EULER)
        clid = file(c, buy(c, pid), R_EULER, key=K_EULER)
        doc = json.loads(TVL["euler-v1"])
        d0 = epoch("2023-03-13T00:00:00Z")
        doc["tvl"] = [p for p in doc["tvl"] if p["date"] <= d0 + 3 * DAY]   # days 0..3 only
        WEB[proto("euler-v1")] = (200, json.dumps(doc))
        out = judge(c, clid)
        self.assertEqual(out["outcome"], "INCONCLUSIVE")
        self.assertIn("severity could not be measured", str(c.claims[clid - 1].reason))
        self.assertEqual(int(c.claims[clid - 1].gross_wei), 0)
        T.install_web()                                      # DeFi Llama catches up
        self.assertTrue(ok(send(c, ALICE, 0, "refile_claim", clid, "", A_EULER, "window now published")))
        self.assertEqual(judge(c, clid)["outcome"], "APPROVED")
        self.assertEqual(c.claims[clid - 1].bucket, 4)

    def test_contest_rejudging_is_gated_too(self):
        src = ast.unparse(_methods(_class(TREE, "CoverClaim"))["judge_contest"])
        self.assertIn("self._judgeable_at(claim)", src)
        self.assertLess(src.index("_judgeable_at"), src.index("_consensus"))


class Fix3_ClosedBatchesAreFinal(unittest.TestCase):
    def test_membership_is_final_when_the_window_closes(self):
        c = fresh()
        pid = make_pool(c, spec=EULER, capital=5 * GEN, coll=5000, max_cover=GEN)
        covers = []
        for who in (ALICE, BOB, CAROL):
            advance(61)
            covers.append(buy(c, pid, who=who, amount=GEN))
        a = file(c, covers[0], R_EULER, key=K_EULER)
        bid = int(judge(c, a)["batch_id"])
        advance(72 * HOUR)                                   # window closes
        b = file(c, covers[1], R_EULER, key=K_EULER + ":Euler V1")
        judge(c, b)
        self.assertNotEqual(int(c.claims[b - 1].batch_id), bid)
        self.assertEqual([int(x) for x in c.batch_claims.get(str(bid))], [a])
        fin = send(c, STRANGER, 0, "finalize_incident", bid)
        self.assertTrue(ok(fin), fin)                         # does not wait on b
        self.assertEqual(fin["claims_paid"], 1)
        advance(49 * HOUR)
        cl = file(c, covers[2], R_EULER, key=K_EULER)
        judge(c, cl)
        self.assertEqual(int(c.claims[cl - 1].batch_id), int(c.claims[b - 1].batch_id))
        advance(73 * HOUR)
        self.assertTrue(ok(send(c, STRANGER, 0, "finalize_incident", int(c.claims[b - 1].batch_id))))
        paid = sum(int(k.payout_wei) for k in c.claims)
        self.assertLessEqual(paid, sum(int(cv.lock_wei) for cv in c.covers))
        self.assertEqual(sum(1 for k in c.claims if str(k.status) == "PAID"), 3)

    def test_payouts_never_exceed_locked_capacity_random(self):
        import random
        rnd = random.Random(5)
        for _ in range(10):
            c = fresh()
            pid = make_pool(c, spec=EULER, capital=4 * GEN, coll=rnd.choice([2000, 5000, 10000]),
                            max_cover=4 * GEN)
            for who in (ALICE, BOB, CAROL):
                advance(61)
                cid = buy(c, pid, who=who, amount=GEN)
                advance(rnd.choice([HOUR, 50 * HOUR, 80 * HOUR]))
                judge(c, file(c, cid, R_EULER, key=K_EULER))
            advance(200 * HOUR)
            for bt in c.batches:
                if str(bt.status) == "OPEN":
                    self.assertTrue(ok(send(c, STRANGER, 0, "finalize_incident", int(bt.batch_id))))
            self.assertLessEqual(sum(int(k.payout_wei) for k in c.claims),
                                 sum(int(cv.lock_wei) for cv in c.covers))
            for bt in c.batches:
                self.assertLessEqual(int(bt.paid_total_wei), int(bt.available_wei))


class Fix4_RefileIdentity(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        pid = make_pool(self.c, spec=EULER)
        self.clid = file(self.c, buy(self.c, pid), R_EULER + "?b=2&a=1", key=K_EULER)
        judge(self.c, self.clid, classification="INCONCLUSIVE", peril="NONE")

    def test_url_identity(self):
        k = C._url_key
        self.assertEqual(k("https://rekt.news/euler-rekt"), k("https://REKT.news/euler-rekt/#x"))
        self.assertEqual(k("https://rekt.news/x?b=2&a=1"), k("https://rekt.news/x/?a=1&b=2#f"))
        self.assertEqual(k("https://web.archive.org/web/20231217192546/https://rekt.news/euler-rekt/"),
                         k("https://web.archive.org/web/2024id_/http://rekt.news/euler-rekt#top"))
        self.assertNotEqual(k("https://web.archive.org/web/2024/https://rekt.news/euler-rekt"),
                            k("https://rekt.news/euler-rekt"))
        self.assertNotEqual(k("https://rekt.news/x?a=1"), k("https://rekt.news/x?a=2"))

    def test_query_reordering_and_trailing_slash_are_not_new(self):
        out = send(self.c, ALICE, 0, "refile_claim", self.clid, "", R_EULER + "/?a=1&b=2#z", "same")
        self.assertTrue(rejected(out))

    def test_another_archive_timestamp_is_not_new(self):
        self.assertTrue(ok(send(self.c, ALICE, 0, "refile_claim", self.clid, "", A_EULER, "archive")))
        judge(self.c, self.clid, classification="INCONCLUSIVE", peril="NONE")
        out = send(self.c, ALICE, 0, "refile_claim", self.clid, "",
                   "https://web.archive.org/web/2025/https://rekt.news/euler-rekt", "again")
        self.assertTrue(rejected(out))

    def test_refile_limit_counts_every_reason(self):
        c = fresh()
        pid = make_pool(c, spec=CURVE)
        clid = file(c, buy(c, pid, amount=GEN // 2), R_VYPER, key=K_VYPER)
        judge(c, clid, classification="INCONCLUSIVE", peril="NONE")           # INCONCLUSIVE
        self.assertTrue(ok(send(c, ALICE, 0, "refile_claim", clid, "", R_CURVE_DNS, "1")))
        self.assertEqual(judge(c, clid)["outcome"], "EVIDENCE_MISMATCH")      # MISMATCH
        self.assertTrue(ok(send(c, ALICE, 0, "refile_claim", clid, K_DNS, "", "2")))
        MODEL.serve_raw(_TopStrength("INCONCLUSIVE", "NONE", "NONE"))
        send(c, STRANGER, 0, "judge_claim", clid)
        out = send(c, ALICE, 0, "refile_claim", clid, K_VYPER, R_VYPER + "?x=1", "3")
        self.assertTrue(rejected(out))
        self.assertIn("used all 2 refiles", out["reason"])

    def test_stall_refile_counts_too(self):
        c = fresh(stall_ttl_s=HOUR)
        pid = make_pool(c, spec=EULER)
        clid = file(c, buy(c, pid), R_EULER, key=K_EULER)
        for u in (A_EULER, "https://rekt.news/euler-rekt-2"):
            advance(2 * HOUR)
            self.assertTrue(ok(send(c, STRANGER, 0, "settle_stalled", clid)))
            self.assertTrue(ok(send(c, ALICE, 0, "refile_claim", clid, "", u, "stalled")))
        advance(2 * HOUR)
        send(c, STRANGER, 0, "settle_stalled", clid)
        out = send(c, ALICE, 0, "refile_claim", clid, "", "https://rekt.news/euler-rekt-3", "3")
        self.assertTrue(rejected(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
