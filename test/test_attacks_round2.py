#!/usr/bin/env python3
"""Round 2: attacks on the fixes. python3 <this file> (run from repo root)."""
import sys, unittest
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import test_logic as T  # noqa: E402
from test_logic import (WEB, ALICE, EULER, R_EULER, K_EULER, fresh, make_pool,  # noqa: E402
                        buy, file, judge, send, ok, rejected)


class Finding5_OutageTimedJudgementKillsTheClaim(unittest.TestCase):
    """An evidence page that answers non-200 is UNREAD -> INCONCLUSIVE ("no
    evidence page could be read"), not RETRY. judge_claim is permissionless,
    so the underwriter can pick that moment. With the round-1 fix a refile now
    needs a genuinely new source, so the buyer cannot resubmit the same page
    once it is back up: the claim can never be judged on its own evidence."""

    def test_same_page_after_an_outage_can_be_judged_again(self):
        c = fresh()
        pid = make_pool(c, spec=EULER)
        clid = file(c, buy(c, pid), R_EULER, key=K_EULER)
        WEB[R_EULER] = (503, "")                       # rekt.news briefly down
        out = judge(c, clid)                           # underwriter triggers now
        # FIXED: an outage is a RETRY - nothing settles, nothing is spent.
        self.assertEqual(out["outcome"], "RETRY")
        k = c.claims[clid - 1]
        self.assertEqual((str(k.status), int(k.refiles), int(k.judged_at)), ("FILED", 0, 0))
        self.assertEqual(str(k.used_urls), "")          # not "already judged"
        del WEB[R_EULER]                               # page is back
        again = judge(c, clid)                         # the same page, judged normally
        self.assertEqual(again["outcome"], "APPROVED", again.get("reason"))
        self.assertEqual(int(k.refiles), 0)


class Finding6_RespelledSourcesStillCountAsNew(unittest.TestCase):
    """Round-1 fix says a re-spelled URL is the same source. `www.` and an
    extra query parameter still make one page a "new" source (bounded now by
    the two-refile cap)."""

    def setUp(self):
        self.c = fresh()
        pid = make_pool(self.c, spec=EULER)
        self.clid = file(self.c, buy(self.c, pid), R_EULER, key=K_EULER)
        judge(self.c, self.clid, classification="INCONCLUSIVE", peril="NONE")

    def test_www_is_the_same_source(self):
        out = send(self.c, ALICE, 0, "refile_claim", self.clid, "",
                   "https://www.rekt.news/euler-rekt", "same")
        self.assertTrue(rejected(out))

    def test_added_query_is_the_same_source(self):
        out = send(self.c, ALICE, 0, "refile_claim", self.clid, "",
                   R_EULER + "?ref=x", "same")
        self.assertTrue(rejected(out))


class Fix5_EvidenceOutageIsRetry(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        pid = make_pool(self.c, spec=EULER)
        self.clid = file(self.c, buy(self.c, pid), R_EULER + " " + T.A_EULER, key=K_EULER)

    def test_every_non_200_is_retry(self):
        for status in (503, 500, 429, 404, 403, 0):
            WEB[R_EULER] = (status, "")
            out = judge(self.c, self.clid)
            self.assertEqual(out["outcome"], "RETRY", status)
            self.assertEqual(str(self.c.claims[self.clid - 1].status), "FILED")
        self.assertEqual(int(self.c.claims[self.clid - 1].refiles), 0)
        self.assertEqual(int(self.c.claims[self.clid - 1].judged_at), 0)

    def test_one_page_down_of_two_is_still_retry(self):
        WEB[T.A_EULER] = (503, "")
        self.assertEqual(judge(self.c, self.clid)["outcome"], "RETRY")

    def test_all_pages_down_is_retry_never_inconclusive(self):
        WEB[R_EULER] = (503, "")
        WEB[T.A_EULER] = (503, "")
        out = judge(self.c, self.clid)
        self.assertEqual(out["outcome"], "RETRY")
        self.assertNotEqual(str(self.c.claims[self.clid - 1].status), "INCONCLUSIVE")

    def test_only_read_pages_count_as_judged(self):
        c = fresh()
        pid = make_pool(c, spec=EULER)
        clid = file(c, buy(c, pid), T.HOME_EULER, key=K_EULER)
        T.RENDER[T.HOME_EULER] = "Euler Finance lets you lend and borrow almost anything."
        self.assertEqual(judge(c, clid)["outcome"], "INCONCLUSIVE")   # read: names no risk
        self.assertEqual(str(c.claims[clid - 1].used_urls), "euler.finance")
        # a page submitted in a refile but never read (outage) is not used up
        self.assertTrue(ok(send(c, ALICE, 0, "refile_claim", clid, "", R_EULER, "the article")))
        WEB[R_EULER] = (503, "")
        self.assertEqual(judge(c, clid)["outcome"], "RETRY")
        self.assertNotIn("rekt.news/euler-rekt", str(c.claims[clid - 1].used_urls))
        del WEB[R_EULER]
        self.assertEqual(judge(c, clid)["outcome"], "APPROVED")
        self.assertIn("rekt.news/euler-rekt", str(c.claims[clid - 1].used_urls))

    def test_a_leader_cannot_pass_an_unread_page_off_as_a_verdict(self):
        f = T.euler_facts()
        raw = T.fetch_raw(f)
        forged = dict(raw, pages=[dict(raw["pages"][0], ok=False, named=False, days=[], digest="")])
        d = T.C._derive(f, forged, T.C._pinned_choice(T.C._reading(f, forged)))
        d["raw"] = forged
        d["choice"] = T.C._pinned_choice(T.C._reading(f, forged))
        self.assertFalse(T.C._coherent(d, f))

    def test_contest_page_outage_keeps_the_contest_pending(self):
        c = fresh()
        pid = make_pool(c, spec=EULER)
        clid = file(c, buy(c, pid), R_EULER, key=K_EULER)
        judge(c, clid)
        send(c, T.UW, int(c.contest_bond_wei), "contest", clid, T.PM_EULER,
             "Euler's own post-mortem is a new primary source on the root cause.")
        WEB[T.PM_EULER] = (503, "")
        out = send(c, T.STRANGER, 0, "judge_contest", clid)
        self.assertEqual(out["outcome"], "RETRY")
        self.assertEqual(str(c.claims[clid - 1].contest_status), "PENDING")


class Fix6_UrlIdentity(unittest.TestCase):
    def test_www_and_query_are_the_same_source(self):
        k = T.C._url_key
        base = k("https://rekt.news/euler-rekt")
        for u in ("https://www.rekt.news/euler-rekt", "https://rekt.news/euler-rekt?ref=x",
                  "https://WWW.rekt.news/euler-rekt/?utm_source=a&b=2#top",
                  "http://rekt.news/euler-rekt"):
            self.assertEqual(k(u), base, u)
        self.assertEqual(k("https://web.archive.org/web/2023/https://www.rekt.news/euler-rekt?x=1"),
                         k("https://web.archive.org/web/2024/https://rekt.news/euler-rekt"))
        self.assertNotEqual(k("https://rekt.news/euler-rekt-2"), base)
        self.assertNotEqual(k("https://app.rekt.news/euler-rekt"), base)

    def test_same_page_twice_in_one_filing_is_refused(self):
        c = fresh()
        pid = make_pool(c, spec=EULER)
        cid = buy(c, pid)
        out = send(c, ALICE, 0, "file_claim", cid, K_EULER,
                   R_EULER + " https://www.rekt.news/euler-rekt?ref=x", "x")
        self.assertTrue(rejected(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
