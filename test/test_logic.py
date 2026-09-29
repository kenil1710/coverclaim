#!/usr/bin/env python3
"""Offline tests for CoverClaim. No chain, no network, no model, no genlayer
install - stdlib only:

    python3 test/test_logic.py

What is under test, in order:

 1. The pure helpers - text, dates, hashing, money - including randomised
    properties of the premium, lock, payout and pro-rata arithmetic.
 2. The evidence allowlist, attacked the ways a claimant would attack it.
 3. The deterministic READING of real evidence (rekt.news articles, DeFi
    Llama's incident list and TVL history, captured from the live sources):
    digest, indicator hits, bracket, strength, severity.
 4. The consensus gates, by BUILDING FORGERIES - one per field - and requiring
    each to be refused.
 5. The deterministic outcome: backdating, cover end, exclusion, severity,
    deductible.
 6. The stateful contract end to end: pools, covers, claims, judgements,
    contests, settlement, release, cancel, withdraw, close, pause, stall -
    with the ledger identity asserted after EVERY call.
 7. Every loophole in the brief, each as its own test class.
 8. The AST invariants: zero raises, no str.replace(), a two-line header,
    frozen fields, what pause gates, which method transfers, which reads the
    clock, closures that do not capture `self`, undefined names.
 9. Randomised lifecycles that must drain every pool to exactly zero.
10. CoverRegistry, the zero-custody consumer.
"""

import ast
import json
import random
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cc_stub  # noqa: E402
from cc_stub import (MESSAGE, MODEL, WEB, RENDER, SEQ, CALLS, FORGE,  # noqa: E402
                     LAST_CONSENSUS, TRANSFERS, BALANCES, CONTRACTS, _Addr,
                     _Return, load_pure, load_full, undefined_names)

ROOT = HERE.parent
SOURCE = ROOT / "contracts" / "CoverClaim.py"
REGISTRY = ROOT / "contracts" / "CoverRegistry.py"
FIX = HERE / "fixtures"

cc_stub._install_stub()
C = load_pure(SOURCE, "coverclaim_pure")
MOD = load_full(SOURCE, "coverclaim_full")
SRC_TEXT = SOURCE.read_text(encoding="utf8")
TREE = ast.parse(SRC_TEXT)

GEN = 10 ** 18
MIN = 60
HOUR = 3600
DAY = 86400


def iso(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def epoch(text: str) -> int:
    return C._epoch_from_iso(text)


def set_now(ts: int) -> None:
    MESSAGE.raw["datetime"] = iso(ts)


NOW = epoch("2026-09-27T12:00:00Z")
# The demo instance's fixed backdate: covers bought at NOW start on 2022-07-31,
# so a 365-day cover with a 7-day wait runs 2022-08-07 .. 2023-07-31. That puts
# BOTH of Curve's incidents inside one cover - the DNS hijack (2022-08-09) and
# the Vyper reentrancy (2023-07-30) - with Euler (2023-03-13), Tornado Cash
# governance (2023-05-20) and Multichain (2023-07-07).
DEMO_DAYS = (NOW - epoch("2022-07-31T12:00:00Z")) // DAY

OWNER = _Addr("0x" + "a" * 40)
UW = _Addr("0x" + "b" * 40)
UW2 = _Addr("0x" + "c" * 40)
ALICE = _Addr("0x" + "d" * 40)
BOB = _Addr("0x" + "e" * 40)
CAROL = _Addr("0x" + "f" * 40)
DAVE = _Addr("0x" + "1" * 40)
STRANGER = _Addr("0x" + "2" * 40)
NOBODY = _Addr("0x" + "3" * 40)

# --- the real sources, captured -------------------------------------------------

HACKS_URL = "https://api.llama.fi/hacks"
HACKS = (FIX / "hacks_subset.json").read_text()


def proto(slug: str) -> str:
    return "https://api.llama.fi/protocol/" + slug


R_EULER = "https://rekt.news/euler-rekt"
R_CURVE_DNS = "https://rekt.news/curve-finance-rekt"
R_MULTI = "https://rekt.news/multichain-r3kt"
R_TORNADO = "https://rekt.news/tornado-gov-rekt"
R_KYBER = "https://rekt.news/kyberswap-rekt"
R_VYPER = "https://rekt.news/curve-vyper-rekt"
A_EULER = "https://web.archive.org/web/20231217192546/https://rekt.news/euler-rekt/"
PM_EULER = ("https://www.euler.finance/blog/war-peace-behind-the-scenes-of-"
            "eulers-240m-exploit-recovery")
HOME_EULER = "https://www.euler.finance/"
BLOG = "https://someguy.substack.com/p/euler-was-hacked"

TEXT = {
    R_EULER: (FIX / "rekt_euler.txt").read_text(),
    R_CURVE_DNS: (FIX / "rekt_curve_dns.txt").read_text(),
    R_MULTI: (FIX / "rekt_multichain.txt").read_text(),
    R_TORNADO: (FIX / "rekt_tornado.txt").read_text(),
    R_KYBER: (FIX / "rekt_kyberswap.txt").read_text(),
    R_VYPER: (FIX / "rekt_curve_vyper.txt").read_text(),
    A_EULER: (FIX / "archive_euler.txt").read_text(),
    # Euler's official post-mortem: a novel source for a contest.
    PM_EULER: ("Governance\nDevelopers\nCommunity\nBlog\n"
               "War & Peace: Behind the Scenes of Euler's $240M Exploit Recovery\n"
               "On March 13, 2023 an attacker exploited a vulnerability in the "
               "Euler V1 donateToReserves function and drained the protocol. "
               "The flaw was in the smart contract code: the donation path did "
               "not check the health of the donor's position. Euler Labs worked "
               "with the attacker over several weeks and every recoverable "
               "asset was returned to users by April 2023."),
    # The homepage: it never names an incident, so it cannot classify one.
    HOME_EULER: ("Governance\nDevelopers\nCommunity\nExplore\nBlog\nLaunch App\n"
                 "The Credit Layer For Programmable Finance\n"
                 "Lend, borrow and swap without limits.\n"
                 "Euler lets you lend and borrow anything, with your own risk "
                 "parameters set for every market you create today."),
}

TVL = {s: (FIX / ("tvl_" + s + ".json")).read_text()
       for s in ("euler-v1", "curve-dex", "multichain", "tornado-cash",
                 "kyberswap-elastic", "balancer-v2")}

ALL_PERILS = "SMART_CONTRACT_BUG,ORACLE_MANIPULATION,ECONOMIC_EXPLOIT,BRIDGE_COMPROMISE"
ALL_EXCL = "PHISHING,FRONTEND_HIJACK,USER_KEY_COMPROMISE,RUG_BY_TEAM,GOVERNANCE_ATTACK"

EULER = dict(name="Euler", slug="euler-v1", lid="1183", chain="Ethereum",
             domains="euler.finance")
CURVE = dict(name="Curve", slug="curve-dex", lid="3", chain="Ethereum",
             domains="curve.finance")
MULTI = dict(name="Multichain", slug="multichain", lid="591", chain="Fantom",
             domains="multichain.org")
TORNADO = dict(name="Tornado Cash", slug="tornado-cash", lid="148",
               chain="Ethereum", domains="tornado.cash")
KYBER = dict(name="KyberSwap", slug="kyberswap-elastic", lid="2615",
             chain="Arbitrum", domains="kyberswap.com")


def install_web() -> None:
    WEB.clear()
    RENDER.clear()
    SEQ.clear()
    del CALLS[:]
    WEB[HACKS_URL] = (200, HACKS)
    for slug, body in TVL.items():
        WEB[proto(slug)] = (200, body)
    for url, text in TEXT.items():
        RENDER[url] = text


def fresh(demo: bool = True, **kwargs):
    """A deployed contract with clean fakes. Demo by default, because most
    paths need a real historical incident inside a cover."""
    TRANSFERS.clear()
    BALANCES.clear()
    MODEL.reset()
    FORGE["payload"] = None
    FORGE["leader_dies"] = False
    LAST_CONSENSUS.clear()
    install_web()
    MESSAGE.sender_address = OWNER
    MESSAGE.value = 0
    set_now(NOW)
    args = dict(kwargs)
    args.setdefault("demo_backdate_days", DEMO_DAYS if demo else 0)
    args.setdefault("claim_window_s", 30 * DAY)
    args.setdefault("settlement_window_s", 72 * HOUR)
    args.setdefault("contest_window_s", 48 * HOUR)
    args.setdefault("stall_ttl_s", 24 * HOUR)
    args.setdefault("buy_cooldown_s", 60)
    return MOD.CoverClaim(**args)


def books(c) -> None:
    """RULE 7, asserted after every call: the identity, and that `held_wei`
    is exactly the pools' capital and unearned premium plus bonds in flight."""
    booked = int(c.balance_wei)
    held = int(c.held_wei)
    payable = int(c.payable_wei)
    if booked != held + payable:
        raise AssertionError("ledger identity broken: balance %d != held %d + "
                             "payable %d" % (booked, held, payable))
    pools = 0
    for p in c.pools:
        if int(p.locked_wei) > int(p.capital_wei):
            raise AssertionError("pool %d locks more than it holds" % int(p.pool_id))
        pools += int(p.capital_wei) + int(p.premiums_held_wei)
    bonds = sum(int(k.contest_bond_wei) for k in c.claims)
    if held != pools + bonds:
        raise AssertionError("held %d != pools %d + bonds %d" % (held, pools, bonds))
    owed = 0
    for key in list(c.payout_wei.keys()):
        owed += int(c.payout_wei.get(key) or 0)
    if owed != payable:
        raise AssertionError("payable %d != sum of balances %d" % (payable, owed))
    for x in (booked, held, payable):
        if x < 0:
            raise AssertionError("negative bucket")


def send(c, who, value, method, *args):
    """One transaction, the way the runner would run it - and the books checked
    afterwards, every single time."""
    MESSAGE.sender_address = who
    MESSAGE.value = int(value)
    try:
        out = getattr(c, method)(*args)
    finally:
        MESSAGE.value = 0
    books(c)
    return out


def view(c, method, *args):
    MESSAGE.sender_address = STRANGER
    MESSAGE.value = 0
    return getattr(c, method)(*args)


def ok(out) -> bool:
    return isinstance(out, dict) and out.get("status") == "OK"


def rejected(out) -> bool:
    return isinstance(out, dict) and out.get("status") == "REJECTED"


def make_pool(c, uw=UW, spec=EULER, capital=10 * GEN, perils=ALL_PERILS,
              excl=ALL_EXCL, rate=100, wait=7, ded=1000, max_cover=5 * GEN,
              term=365, coll=10000, table="", wording="Frozen at creation."):
    out = send(c, uw, capital, "create_pool", spec["name"], spec["slug"],
               spec["lid"], spec["chain"], perils, excl, rate, wait, ded,
               max_cover, term, coll, table, spec["domains"], wording)
    if not ok(out):
        raise AssertionError("fixture pool failed: " + str(out))
    return int(out["pool_id"])


def premium_of(c, pid, amount, days):
    p = c.pools[pid - 1]
    return C._premium(amount, int(p.rate_bps), days)


def buy(c, pid, who=ALICE, amount=GEN, days=365, extra=0):
    prem = premium_of(c, pid, amount, days)
    out = send(c, who, prem + extra, "buy_cover", pid, amount, days)
    if not ok(out):
        raise AssertionError("fixture cover failed: " + str(out))
    return int(out["cover_id"])


# The incident record each captured article is about, by key.
KEY_OF_URL = {R_EULER: "1183:2023-03-13", A_EULER: "1183:2023-03-13",
              PM_EULER: "1183:2023-03-13", R_CURVE_DNS: "3:2022-08-09",
              R_VYPER: "3:2023-07-30", R_MULTI: "591:2023-07-07",
              R_TORNADO: "148:2023-05-20", R_KYBER: "2615:2023-11-22"}
# The record a claim on a pool of this id is about when the evidence does not
# say (a homepage, a blog, another protocol's article).
KEY_OF_POOL = {"1183": "1183:2023-03-13", "3": "3:2022-08-09",
               "591": "591:2023-07-07", "148": "148:2023-05-20",
               "2615": "2615:2023-11-22"}
K_EULER = "1183:2023-03-13"
K_DNS = "3:2022-08-09"
K_VYPER = "3:2023-07-30"


def live_key(lid):
    """A well-formed key dated TODAY (the fake block time's day): the only kind
    of in-window key a canonical cover bought at NOW can carry."""
    return lid + ":" + C._date_text(now_of())


def key_for(c, cid, urls):
    lid = str(c.pools[int(c.covers[cid - 1].pool_id) - 1].llama_id)
    first = str(urls).replace(",", " ").split()
    k = KEY_OF_URL.get(first[0], "") if first else ""
    return k if k.startswith(lid + ":") else KEY_OF_POOL.get(lid, lid + ":2023-01-01")


def file(c, cid, urls, who=None, statement="The protocol was exploited.",
         key=None):
    cover = c.covers[cid - 1]
    out = send(c, who or cover.buyer, 0, "file_claim", cid,
               key_for(c, cid, urls) if key is None else key, urls, statement)
    if not ok(out):
        raise AssertionError("fixture claim failed: " + str(out))
    return int(out["claim_id"])


def judge(c, clid, classification="COVERED", peril="SMART_CONTRACT_BUG",
          exclusion="NONE", strength=None):
    """Judge with the model answering as told. `strength` defaults to the top
    of whatever bracket the evidence produces."""
    if strength is None:
        MODEL.sticky = None
        MODEL.serve_raw(_TopStrength(classification, peril, exclusion))
    else:
        MODEL.serve(classification, peril, exclusion, strength)
    return send(c, STRANGER, 0, "judge_claim", clid)


class _TopStrength(dict):
    """A model answer whose strength is filled in from the prompt's own range
    - the answer an honest model gives at the top of its bracket."""

    def __init__(self, classification, peril, exclusion, event_match="SAME"):
        super().__init__(classification=classification, peril=peril,
                         exclusion=exclusion, evidence_strength=0,
                         event_match=event_match)


_orig_next = MODEL._next


def _next_with_range(prompt):
    got = _orig_next(prompt)
    if isinstance(got, _TopStrength):
        k = prompt.find("an integer from ")
        lo_hi = prompt[k + len("an integer from "):].split("}")[0]
        hi = int(lo_hi.split(" to ")[1])
        out = dict(got)
        out["evidence_strength"] = hi
        return out
    return got


MODEL._next = _next_with_range


def reset_fakes() -> None:
    """Every test starts from the same world: fakes installed, model clean,
    no forgery armed, the clock at NOW. Applied to EVERY test by wrapping
    TestCase.run - a leftover `MODEL.fail(5)` from one test once turned a
    later, unrelated test red, which is exactly the leakage this prevents."""
    MODEL.reset()
    FORGE["payload"] = None
    FORGE["leader_dies"] = False
    LAST_CONSENSUS.clear()
    install_web()
    MESSAGE.value = 0
    set_now(NOW)


_orig_run = unittest.TestCase.run


def _run_clean(self, result=None):
    reset_fakes()
    return _orig_run(self, result)


unittest.TestCase.run = _run_clean


def advance(seconds: int) -> int:
    now = C._epoch_from_iso(MESSAGE.raw["datetime"]) + int(seconds)
    set_now(now)
    return now


def now_of() -> int:
    return C._epoch_from_iso(MESSAGE.raw["datetime"])


def drain(c, who) -> int:
    owed = int(c.payout_wei.get(who) or 0)
    if owed <= 0:
        return 0
    out = send(c, who, 0, "claim_payout")
    if not ok(out):
        raise AssertionError("claim_payout failed: " + str(out))
    return int(out["paid_wei"])


def settle_ready(c, bid):
    """Advance past the settlement window and every contest window, then
    finalize."""
    advance(73 * HOUR)
    return send(c, STRANGER, 0, "finalize_incident", bid)


def raw_of(llama=None, tvl=None, pages=None):
    return {"retry": False, "llama": llama or {"found": False, "why": "none"},
            "tvl": tvl or {"ok": False, "why": "none"}, "pages": pages or []}


def euler_facts(**over):
    key = over.pop("key", None)
    f = {"mode": "claim", "claim_id": 1, "protocol_name": "Euler",
         "incident_key": "1183:2023-03-13", "key_id": "1183",
         "key_day": epoch("2023-03-13T00:00:00Z"), "key_name": "",
         "prior_bound": 0,
         "llama_slug": "euler-v1", "llama_id": "1183",
         "perils": list(C.PERILS), "exclusions": list(C.EXCLUSIONS),
         "urls": [R_EULER], "start": epoch("2022-07-28T12:00:00Z"),
         "end": epoch("2023-07-28T12:00:00Z"), "waiting_s": 7 * DAY,
         "prior_digest": "", "prior_sources": 0, "prior_match": False}
    f.update(over)
    if key is not None:
        k, lid, day, name, _ = C._parse_key(key)
        f.update(incident_key=k, key_id=lid, key_day=day, key_name=name)
    return f


def fetch_raw(facts):
    """What a node would read for these facts, through the fakes."""
    install_web()
    return C._read_sources(facts)


# ===========================================================================
# 1. pure helpers
# ===========================================================================


class TestTextHelpers(unittest.TestCase):
    def test_flat_collapses_whitespace(self):
        self.assertEqual(C._flat("a  b\n c\t d"), "a b c d")

    def test_flat_of_non_string(self):
        self.assertEqual(C._flat(12), "12")

    def test_clean_caps_length(self):
        self.assertEqual(C._clean("abcdef", 3), "abc")

    def test_clean_strips_control(self):
        self.assertEqual(C._clean("a\x00b\x07c", 10), "abc")

    def test_clean_strips_delete(self):
        self.assertEqual(C._clean("a\x7fb", 10), "ab")

    def test_clean_flattens_newlines(self):
        self.assertEqual(C._clean("a\nb", 10), "a b")

    def test_short(self):
        self.assertEqual(C._short("abcdef", 2), "ab")
        self.assertEqual(C._short("ab", 5), "ab")

    def test_as_int_forms(self):
        self.assertEqual(C._as_int(5), 5)
        self.assertEqual(C._as_int("12"), 12)
        self.assertEqual(C._as_int(" -3 "), -3)
        self.assertEqual(C._as_int(2.9), 2)

    def test_as_int_rejects_bool(self):
        self.assertEqual(C._as_int(True, -1), -1)
        self.assertEqual(C._as_int(False, -1), -1)

    def test_as_int_garbage(self):
        for v in ("1e3", "", "abc", None, [], {}, "1.5"):
            self.assertEqual(C._as_int(v, -9), -9, v)

    def test_as_bool(self):
        self.assertTrue(C._as_bool(True))
        self.assertTrue(C._as_bool("true"))
        self.assertTrue(C._as_bool(1))
        self.assertFalse(C._as_bool("no"))
        self.assertFalse(C._as_bool(0))

    def test_clamp(self):
        self.assertEqual(C._clamp(5, 0, 3), 3)
        self.assertEqual(C._clamp(-1, 0, 3), 0)
        self.assertEqual(C._clamp(2, 0, 3), 2)

    def test_rank(self):
        self.assertEqual(C._rank(0, (1, 2)), 0)
        self.assertEqual(C._rank(2, (1, 2)), 2)
        self.assertEqual(C._rank(1, (1, 2)), 1)

    def test_is_addr(self):
        self.assertTrue(C._is_addr("0x" + "aB" * 20))
        self.assertFalse(C._is_addr("0x" + "g" * 40))
        self.assertFalse(C._is_addr("ab" * 21))
        self.assertFalse(C._is_addr(None))

    def test_err_text_prefers_data(self):
        class E:
            data = "from data"
            message = "from message"
        self.assertEqual(C._err_text(E()), "from data")

    def test_err_text_falls_back(self):
        class E:
            data = ""
            message = "m"
        self.assertEqual(C._err_text(E()), "m")


class TestDates(unittest.TestCase):
    def test_epoch_known(self):
        self.assertEqual(epoch("2023-03-13T00:00:00Z"), 1678665600)

    def test_epoch_rejects_garbage(self):
        for v in ("", "2023", None, 5, "2023-13-01T00:00:00Z",
                  "2023-01-01T25:00:00Z", "abcd-ef-ghTij:kl:mn"):
            self.assertEqual(C._epoch_from_iso(v), 0, v)

    def test_day_of_floors(self):
        self.assertEqual(C._day_of(1678665600 + 5000), 1678665600)
        self.assertEqual(C._day_of(1678665600), 1678665600)

    def test_date_text(self):
        self.assertEqual(C._date_text(1678665600), "2023-03-13")
        self.assertEqual(C._date_text(0), "")

    def test_civil_roundtrip_random(self):
        rnd = random.Random(7)
        for _ in range(400):
            z = rnd.randint(-50000, 80000)
            y, m, d = C._civil_from_days(z)
            self.assertEqual(C._days_from_civil(y, m, d), z)

    def test_date_text_matches_datetime(self):
        rnd = random.Random(8)
        for _ in range(200):
            t = rnd.randint(0, 4102444800)
            want = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
            self.assertEqual(C._date_text(t), want)

    def test_leap_day(self):
        self.assertEqual(C._date_text(epoch("2024-02-29T10:00:00Z")), "2024-02-29")


class TestHashAndFormat(unittest.TestCase):
    def test_fnv_known_empty(self):
        self.assertEqual(C._fnv(""), "cbf29ce484222325")

    def test_fnv_differs(self):
        self.assertNotEqual(C._fnv("a"), C._fnv("b"))

    def test_fnv_deterministic(self):
        self.assertEqual(C._fnv("euler"), C._fnv("euler"))

    def test_gen(self):
        self.assertEqual(C._gen(GEN), "1.00")
        self.assertEqual(C._gen(15 * 10 ** 17), "1.50")
        self.assertEqual(C._gen(1), "0.000000000000000001")
        self.assertEqual(C._gen(-GEN), "-1.00")

    def test_pct(self):
        self.assertEqual(C._pct(1234), "12.34%")
        self.assertEqual(C._pct(5), "0.05%")
        self.assertEqual(C._pct(10000), "100.00%")


class TestNormAndHits(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(C._norm("Front-End, DNS!"), "front end dns")

    def test_has_is_word_start_anchored(self):
        self.assertTrue(C._has(" oracles were moved ", "oracle"))
        self.assertFalse(C._has(" sdns record ", "dns"))
        self.assertTrue(C._has(" dns hijack ", "dns"))

    def test_hits_distinct_in_vocab_order(self):
        text = C._norm("An oracle, an oracle, and a reentrancy bug.")
        self.assertEqual(C._hits_of(text, C.PERIL_WORDS, C.PERILS),
                         ["SMART_CONTRACT_BUG", "ORACLE_MANIPULATION"])

    def test_generic_words_are_not_indicators(self):
        text = C._norm("The protocol was hacked and exploited in an attack; "
                       "funds were stolen.")
        self.assertEqual(C._hits_of(text, C.PERIL_WORDS, C.PERILS), [])
        self.assertEqual(C._hits_of(text, C.EXCLUSION_WORDS, C.EXCLUSIONS), [])

    def test_names_protocol_whole_word(self):
        self.assertTrue(C._names_protocol(C._norm("Curve's pools"), "Curve"))
        self.assertFalse(C._names_protocol(C._norm("Aavegotchi"), "Aave"))
        self.assertTrue(C._names_protocol(C._norm("the Tornado Cash DAO"),
                                          "Tornado Cash"))

    def test_names_protocol_empty(self):
        self.assertFalse(C._names_protocol("anything", ""))

    def test_every_indicator_is_normalised(self):
        for table in (C.PERIL_WORDS, C.EXCLUSION_WORDS):
            for item, phrases in table.items():
                for p in phrases:
                    self.assertEqual(C._norm(p), p, (item, p))

    def test_vocab_tables_cover_vocab(self):
        self.assertEqual(sorted(C.PERIL_WORDS), sorted(C.PERILS))
        self.assertEqual(sorted(C.EXCLUSION_WORDS), sorted(C.EXCLUSIONS))
        self.assertEqual(sorted(C.PERIL_TEXT), sorted(C.PERILS))
        self.assertEqual(sorted(C.EXCLUSION_TEXT), sorted(C.EXCLUSIONS))

    def test_llama_map_targets_vocab(self):
        for k, v in C.LLAMA_MAP.items():
            self.assertIn(v, C.PERILS + C.EXCLUSIONS, k)


class TestSentencesAndNovelty(unittest.TestCase):
    def test_sentences_split(self):
        got = [w for w, _ in C._sentences("One. Two! Three?")]
        self.assertEqual(got, ["One.", "Two!", "Three?"])

    def test_decimal_does_not_split(self):
        got = C._sentences("They lost $1.5M today. Then more.")
        self.assertEqual(len(got), 2)

    def test_domain_does_not_split(self):
        got = C._sentences("Its front end curve.fi was hijacked. Users lost funds.")
        self.assertEqual(len(got), 2)
        self.assertIn("curve.fi", got[0][0])

    def test_novel_drops_verbatim(self):
        self.assertEqual(C._novel("A bug was found.", "A bug was found."), "")

    def test_novel_drops_repunctuated(self):
        self.assertEqual(C._novel("a BUG, was found!!", "A bug was found."), "")

    def test_novel_drops_contained_fragment(self):
        self.assertEqual(C._novel("bug was found.", "A bug was found in code."), "")

    def test_novel_counts_repeat_once(self):
        got = C._novel("New fact here. New fact here. New fact here.", "")
        self.assertEqual(got, "New fact here.")

    def test_novel_keeps_new(self):
        got = C._novel("A bug was found. The key was phished.", "A bug was found.")
        self.assertEqual(got, "The key was phished.")

    def test_novel_never_raises(self):
        for v in (None, 5, [], ""):
            C._novel(v, v)


class TestDigest(unittest.TestCase):
    def test_digest_keeps_salient_only(self):
        text = ("Home\nGovernance\nThe weather was nice across the city today.\n"
                "An attacker used a flash loan against Euler's markets.")
        d = C._digest(text, "Euler", 5000)
        self.assertIn("flash loan", d)
        self.assertNotIn("weather", d)

    def test_short_nav_lines_never_count(self):
        # Measured: Euler's post-mortem renders its nav bar as one-word lines.
        d = C._digest("Governance\nDevelopers\nCommunity", "Euler", 5000)
        self.assertEqual(d, "")

    def test_digest_cap(self):
        text = "\n".join(["Euler lost funds in exploit number %d today." % i
                          for i in range(400)])
        self.assertLessEqual(len(C._digest(text, "Euler", 1000)), 1000)

    def test_real_euler_article(self):
        d = C._digest(TEXT[R_EULER], "Euler", C.MAX_DIGEST_PER_SOURCE)
        self.assertIn("donateToReserves", d)
        self.assertLessEqual(len(d), C.MAX_DIGEST_PER_SOURCE)

    def test_digest_deterministic(self):
        a = C._digest(TEXT[R_MULTI], "Multichain", 2400)
        b = C._digest(TEXT[R_MULTI], "Multichain", 2400)
        self.assertEqual(a, b)


class TestStripHtml(unittest.TestCase):
    def test_blocks_become_lines(self):
        self.assertEqual(C._strip_html("<p>One</p><p>Two <b>bold</b></p>"), "One\nTwo bold")

    def test_scripts_and_styles_dropped(self):
        t = C._strip_html("<script>var euler='reentrancy';</script><style>p{}</style><p>x</p>")
        self.assertEqual(t, "x")

    def test_comments_dropped(self):
        self.assertEqual(C._strip_html("<!-- oracle --><p>a</p>"), "a")

    def test_entities(self):
        self.assertEqual(C._strip_html("<p>A &amp; B &lt;c&gt; &#39;d&#39; &#x27;e&#x27; &rsquo;</p>"),
                         "A & B <c> 'd' 'e' '")

    def test_unknown_entity_kept(self):
        self.assertEqual(C._strip_html("<p>&bogus; x</p>"), "&bogus; x")

    def test_never_raises_on_garbage(self):
        for junk in ("<", "<p", "&#99999999999;", "&#x;", "<script>", "<<>>", "", "&"):
            C._strip_html(junk)

    def test_real_rekt_page_digest(self):
        html = cc_stub._as_html(TEXT[R_EULER])
        d = C._digest(C._strip_html(html), "Euler", C.MAX_DIGEST_PER_SOURCE)
        self.assertIn("donateToReserves", d)

    def test_page_non_200_unreadable(self):
        install_web()
        WEB[R_EULER] = (404, "<p>Euler reentrancy</p>")
        self.assertEqual(C._page(R_EULER), (False, ""))

    def test_page_capped(self):
        install_web()
        WEB[R_EULER] = (200, "<p>" + "a " * 200000 + "</p>")
        ok, text = C._page(R_EULER)
        self.assertTrue(ok)
        self.assertLessEqual(len(text), C.MAX_PAGE_CHARS)

    def test_no_render_anywhere(self):
        for n in ast.walk(TREE):
            if isinstance(n, ast.Attribute):
                self.assertNotEqual(n.attr, "render", getattr(n, "lineno", 0))


# ===========================================================================
# 2. the allowlist
# ===========================================================================

DOMS = ["rekt.news", "web.archive.org", "euler.finance"]


class TestHostParsing(unittest.TestCase):
    def test_https_only(self):
        self.assertEqual(C._host_of("http://rekt.news/x"), "")
        self.assertEqual(C._host_of("ftp://rekt.news/x"), "")
        self.assertEqual(C._host_of("//rekt.news/x"), "")

    def test_basic(self):
        self.assertEqual(C._host_of("https://rekt.news/euler-rekt"), "rekt.news")

    def test_uppercase_scheme_and_host(self):
        self.assertEqual(C._host_of("HTTPS://REKT.News/x"), "rekt.news")

    def test_userinfo_refused(self):
        self.assertEqual(C._host_of("https://rekt.news@evil.com/x"), "")

    def test_port_refused(self):
        self.assertEqual(C._host_of("https://rekt.news:8443/x"), "")

    def test_backslash_refused(self):
        self.assertEqual(C._host_of("https://rekt.news\\@evil.com/x"), "")

    def test_whitespace_refused(self):
        self.assertEqual(C._host_of("https://rekt.news/a b"), "")

    def test_non_ascii_refused(self):
        self.assertEqual(C._host_of("https://rеkt.news/x"), "")  # Cyrillic e

    def test_trailing_dot(self):
        self.assertEqual(C._host_of("https://rekt.news./x"), "rekt.news")

    def test_query_and_fragment(self):
        self.assertEqual(C._host_of("https://rekt.news?x=1"), "rekt.news")
        self.assertEqual(C._host_of("https://rekt.news#x"), "rekt.news")

    def test_too_long(self):
        self.assertEqual(C._host_of("https://rekt.news/" + "a" * 400), "")

    def test_empty_labels(self):
        self.assertEqual(C._host_of("https://rekt..news/x"), "")


class TestAllowlist(unittest.TestCase):
    def test_subdomain_allowed(self):
        self.assertTrue(C._host_allowed("blog.euler.finance", DOMS))

    def test_suffix_attack_refused(self):
        self.assertFalse(C._host_allowed("evilrekt.news", DOMS))
        self.assertFalse(C._host_allowed("rekt.news.evil.com", DOMS))

    def test_random_blog_refused(self):
        self.assertIn("not on this pool's frozen evidence allowlist",
                      C._check_url(BLOG, DOMS))

    def test_llama_api_refused_as_evidence(self):
        self.assertIn("read by the contract itself",
                      C._check_url("https://api.llama.fi/hacks", DOMS + ["llama.fi"]))

    def test_rekt_ok(self):
        self.assertEqual(C._check_url(R_EULER, DOMS), "")

    def test_official_ok(self):
        self.assertEqual(C._check_url(PM_EULER, DOMS), "")

    def test_archive_of_allowlisted_ok(self):
        self.assertEqual(C._check_url(A_EULER, DOMS), "")

    def test_archive_id_stamp_ok(self):
        self.assertEqual(C._check_url(
            "https://web.archive.org/web/2023id_/https://rekt.news/x", DOMS), "")

    def test_archive_of_http_original_ok(self):
        self.assertEqual(C._check_url(
            "https://web.archive.org/web/2023/http://rekt.news/x", DOMS), "")

    def test_archive_of_random_blog_refused(self):
        why = C._check_url("https://web.archive.org/web/2024/" + BLOG, DOMS)
        self.assertIn("only stands in for an allowlisted page", why)

    def test_archive_of_archive_refused(self):
        why = C._check_url("https://web.archive.org/web/2024/https://web.archive.org"
                           "/web/2023/https://evil.com/x", DOMS)
        self.assertNotEqual(why, "")

    def test_archive_without_snapshot_refused(self):
        self.assertNotEqual(C._check_url("https://web.archive.org/", DOMS), "")
        self.assertNotEqual(C._check_url(
            "https://web.archive.org/web/abc/https://rekt.news/x", DOMS), "")

    def test_parse_urls_counts(self):
        self.assertEqual(C._parse_urls("", DOMS)[1] != "", True)
        many = " ".join([R_EULER + str(i) for i in range(4)])
        self.assertIn("at most", C._parse_urls(many, DOMS)[1])

    def test_parse_urls_duplicates(self):
        why = C._parse_urls(R_EULER + " " + R_EULER.upper() + "/", DOMS)[1]
        self.assertIn("twice", why)

    def test_parse_urls_separators(self):
        urls, why = C._parse_urls(R_EULER + ",\n" + A_EULER, DOMS)
        self.assertEqual(why, "")
        self.assertEqual(urls, [R_EULER, A_EULER])

    def test_parse_urls_one_bad_refuses_all(self):
        urls, why = C._parse_urls(R_EULER + " " + BLOG, DOMS)
        self.assertEqual(urls, [])
        self.assertNotEqual(why, "")

    def test_url_key(self):
        self.assertEqual(C._url_key("https://REKT.news/x/"), "rekt.news/x")


class TestPolicyParsing(unittest.TestCase):
    def test_list_vocab_order(self):
        got, why = C._parse_list("ORACLE_MANIPULATION, smart_contract_bug",
                                 C.PERILS, False)
        self.assertEqual(why, "")
        self.assertEqual(got, ["SMART_CONTRACT_BUG", "ORACLE_MANIPULATION"])

    def test_list_rejects_unknown(self):
        self.assertIn("not in the fixed vocabulary",
                      C._parse_list("ACTS_OF_GOD", C.PERILS, False)[1])

    def test_list_rejects_duplicate(self):
        self.assertIn("twice", C._parse_list("PHISHING,PHISHING",
                                             C.EXCLUSIONS, True)[1])

    def test_list_empty(self):
        self.assertNotEqual(C._parse_list("", C.PERILS, False)[1], "")
        self.assertEqual(C._parse_list("", C.EXCLUSIONS, True), ([], ""))

    def test_table_default(self):
        self.assertEqual(C._parse_table(""), (list(C.DEFAULT_PAYOUT_TABLE), ""))

    def test_table_custom(self):
        self.assertEqual(C._parse_table("0,1000,2000,3000,10000")[0],
                         [0, 1000, 2000, 3000, 10000])

    def test_table_refuses_decreasing(self):
        self.assertIn("must not decrease", C._parse_table("0,5000,2500,7500,10000")[1])

    def test_table_refuses_wrong_length(self):
        self.assertIn("exactly", C._parse_table("0,1,2")[1])

    def test_table_refuses_over_100(self):
        self.assertNotEqual(C._parse_table("0,0,0,0,10001")[1], "")

    def test_domains_normalised(self):
        got, why = C._parse_domains("https://www.Euler.finance/blog, rekt.news")
        self.assertEqual(why, "")
        self.assertEqual(got, ["euler.finance"])

    def test_domains_refuse_llama(self):
        self.assertNotEqual(C._parse_domains("api.llama.fi")[1], "")

    def test_domains_refuse_garbage(self):
        self.assertNotEqual(C._parse_domains("not a domain")[1], "")

    def test_domains_cap(self):
        self.assertNotEqual(C._parse_domains("a.com,b.com,c.com,d.com")[1], "")


# ===========================================================================
# money
# ===========================================================================


class TestMoney(unittest.TestCase):
    def test_premium_exact(self):
        # 1 GEN x 100 bps x 30 days / 30 = 0.01 GEN
        self.assertEqual(C._premium(GEN, 100, 30), GEN // 100)

    def test_premium_scales_with_days(self):
        self.assertEqual(C._premium(GEN, 100, 60), 2 * GEN // 100)

    def test_premium_rounds_up(self):
        self.assertEqual(C._premium(1, 1, 1), 1)
        self.assertEqual(C._premium(299999, 1, 1), 1)
        self.assertEqual(C._premium(300001, 1, 1), 2)

    def test_premium_zero_inputs(self):
        self.assertEqual(C._premium(0, 100, 30), 0)
        self.assertEqual(C._premium(GEN, 0, 30), 0)

    def test_premium_never_undercharges_random(self):
        rnd = random.Random(11)
        for _ in range(300):
            a = rnd.randint(1, 10 ** 21)
            r = rnd.randint(1, 2000)
            d = rnd.randint(1, 365)
            p = C._premium(a, r, d)
            self.assertGreaterEqual(p * 300000, a * r * d)
            self.assertLess((p - 1) * 300000, a * r * d)

    def test_lock_rounds_up(self):
        self.assertEqual(C._lock(3, 5000), 2)
        self.assertEqual(C._lock(GEN, 10000), GEN)

    def test_gross(self):
        # 1 GEN x 100% x (1 - 10%) = 0.9 GEN
        self.assertEqual(C._gross(GEN, 10000, 1000), 9 * GEN // 10)
        self.assertEqual(C._gross(GEN, 2500, 1000), 225 * GEN // 1000)

    def test_gross_single_division(self):
        self.assertEqual(C._gross(3, 5000, 5000), 3 * 5000 * 5000 // 10 ** 8)

    def test_gross_zero(self):
        self.assertEqual(C._gross(GEN, 0, 0), 0)
        self.assertEqual(C._gross(GEN, 10000, 10000), 0)

    def test_gross_never_exceeds_cover_random(self):
        rnd = random.Random(12)
        for _ in range(300):
            a = rnd.randint(0, 10 ** 21)
            self.assertLessEqual(C._gross(a, rnd.randint(0, 10000),
                                          rnd.randint(0, 5000)), a)

    def test_prorata_fits(self):
        self.assertEqual(C._prorata([3, 4], 10), ([3, 4], 0))

    def test_prorata_scales(self):
        pays, dust = C._prorata([9, 9], 10)
        self.assertEqual(pays, [5, 5])
        self.assertEqual(dust, 0)

    def test_prorata_dust(self):
        pays, dust = C._prorata([1, 1, 1], 2)
        self.assertEqual(sum(pays) + dust, 2)

    def test_prorata_same_factor_not_first_come(self):
        a, _ = C._prorata([900, 100], 500)
        b, _ = C._prorata([100, 900], 500)
        self.assertEqual(a, [450, 50])
        self.assertEqual(b, [50, 450])

    def test_prorata_properties_random(self):
        rnd = random.Random(13)
        for _ in range(500):
            n = rnd.randint(1, 8)
            gs = [rnd.randint(0, 10 ** 20) for _ in range(n)]
            avail = rnd.randint(0, 2 * 10 ** 20)
            pays, dust = C._prorata(gs, avail)
            self.assertEqual(len(pays), n)
            for p, g in zip(pays, gs):
                self.assertLessEqual(p, g)
                self.assertGreaterEqual(p, 0)
            if sum(gs) <= avail:
                self.assertEqual(pays, gs)
                self.assertEqual(dust, 0)
            else:
                self.assertEqual(sum(pays) + dust, avail)
                self.assertLess(dust, n + 1)

    def test_refund(self):
        self.assertEqual(C._refund(100, 10, 5), 50)
        self.assertEqual(C._refund(100, 10, 20), 100)
        self.assertEqual(C._refund(100, 10, 0), 0)
        self.assertEqual(C._refund(10, 3, 1), 3)

    def test_bucket_edges(self):
        for drop, want in ((0, 0), (999, 0), (1000, 1), (2999, 1), (3000, 2),
                           (5999, 2), (6000, 3), (8999, 3), (9000, 4),
                           (10000, 4)):
            self.assertEqual(C._bucket(drop), want, drop)

    def test_drop(self):
        self.assertEqual(C._drop(100, 50), 5000)
        self.assertEqual(C._drop(100, 100), 0)
        self.assertEqual(C._drop(100, 150), 0)
        self.assertEqual(C._drop(0, 0), 0)
        self.assertEqual(C._drop(100, -1), 0)
        self.assertEqual(C._drop(3, 2), 3333)


class TestSelectIncident(unittest.TestCase):
    """THE record is the one the key names - by exact day (and name) - never
    the latest, the nearest, or the first in feed order."""
    ROWS = [{"date": 100 * DAY, "name": "A"}, {"date": 500 * DAY, "name": "B"},
            {"date": 900 * DAY, "name": "C"}, {"date": 2000 * DAY, "name": "D"}]

    def test_exact_day(self):
        row, n = C._select_incident(self.ROWS, 500 * DAY, "")
        self.assertEqual((row["name"], n), ("B", 1))

    def test_no_latest_fallback(self):
        # 901 is inside any window that holds 900; it names nothing.
        self.assertEqual(C._select_incident(self.ROWS, 901 * DAY, ""), (None, 0))

    def test_name_disambiguates_and_must_match(self):
        rows = self.ROWS + [{"date": 500 * DAY, "name": "B2"}]
        self.assertEqual(C._select_incident(rows, 500 * DAY, ""), (None, 2))
        self.assertEqual(C._select_incident(rows, 500 * DAY, "b2")[0]["name"], "B2")
        self.assertEqual(C._select_incident(rows, 500 * DAY, "zzz"), (None, 0))

    def test_order_never_matters(self):
        rnd = random.Random(7)
        for _ in range(50):
            rows = list(self.ROWS)
            rnd.shuffle(rows)
            for d, name in ((100, "A"), (500, "B"), (900, "C"), (2000, "D")):
                self.assertEqual(C._select_incident(rows, d * DAY, "")[0]["name"], name)

    def test_pick_incident_is_gone(self):
        self.assertFalse(hasattr(C, "_pick_incident"))
        self.assertNotIn("_pick_incident", SRC_TEXT)


class TestDatesAndKeys(unittest.TestCase):
    def days(self, text):
        return [C._date_text(d) for d in C._dates_in(C._norm(text), 40)]

    def test_forms(self):
        self.assertEqual(self.days("Monday, July 31, 2023"), ["2023-07-31"])
        self.assertEqual(self.days("on 9 August 2022 the"), ["2022-08-09"])
        self.assertEqual(self.days("iso 2023-07-30 here"), ["2023-07-30"])
        self.assertEqual(self.days("Sept 3rd, 2021"), ["2021-09-03"])

    def test_yearless_takes_the_page_year(self):
        self.assertEqual(self.days("Friday, July 14, 2023. It began on July 7th."),
                         ["2023-07-14", "2023-07-07"])
        # before any year: the first year the page writes
        self.assertEqual(self.days("On March 13 it broke. Published March 14, 2023"),
                         ["2023-03-13", "2023-03-14"])

    def test_no_year_anywhere_is_no_date(self):
        self.assertEqual(self.days("It happened on July 30th."), [])

    def test_not_dates(self):
        self.assertEqual(self.days("you may 2x it; march 99 2023; 2023 13 40; "
                                   "february 30 2023"), [])

    def test_distinct_and_capped(self):
        text = " ".join("July %d, 2023" % d for d in range(1, 29)) + " July 1, 2023"
        self.assertEqual(len(C._dates_in(C._norm(text), 40)), 28)
        self.assertEqual(len(C._dates_in(C._norm(text), 5)), 5)

    def test_never_raises(self):
        for junk in ("", "july", "31", "2023", "july 31st 99999", "0 jan 2023"):
            C._dates_in(C._norm(junk), 40)

    def test_parse_key(self):
        self.assertEqual(C._parse_key("3:2023-07-30")[:4],
                         ("3:2023-07-30", "3", epoch("2023-07-30T00:00:00Z"), ""))
        self.assertEqual(C._parse_key(" 3:2023-07-30:Curve DEX ")[0],
                         "3:2023-07-30:Curve DEX")
        for bad in ("", "3", "3:", ":2023-07-30", "x:2023-07-30", "3:2023-7-30",
                    "3:2023-02-30", "3:30-07-2023", "3/2023-07-30"):
            self.assertNotEqual(C._parse_key(bad)[4], "", bad)

    def test_tvl_line_roundtrip(self):
        tvl = {"ok": True, "doc_id": "3", "anchor": epoch("2023-07-30T00:00:00Z"),
               "before_at": epoch("2023-07-29T00:00:00Z"), "before": 100,
               "low": 40, "after_points": 2,
               "window": [[epoch("2023-07-30T00:00:00Z"), 90],
                          [epoch("2023-07-31T00:00:00Z"), 40]]}
        got = C._parse_tvl_line(C._tvl_line(tvl))
        self.assertEqual(got["anchor"], "2023-07-30")
        self.assertEqual(got["before_day"], "2023-07-29")
        self.assertEqual((got["before"], got["low"], got["count"]), (100, 40, 2))
        self.assertEqual(got["points"], [["2023-07-30", 90], ["2023-07-31", 40]])
        self.assertEqual(C._parse_tvl_line("no TVL history"), {})


# ===========================================================================
# 3. the reading of real evidence
# ===========================================================================


class TestReadSources(unittest.TestCase):
    def test_reads_the_euler_record(self):
        raw = fetch_raw(euler_facts())
        self.assertFalse(raw["retry"])
        self.assertTrue(raw["llama"]["found"])
        self.assertEqual(C._date_text(raw["llama"]["date"]), "2023-03-13")
        self.assertEqual(raw["llama"]["technique"], "Donation Attack")

    def test_tvl_is_integers(self):
        raw = fetch_raw(euler_facts())
        for k in ("before", "low", "after_points"):
            self.assertIsInstance(raw["tvl"][k], int)
        self.assertEqual(raw["tvl"]["doc_id"], "1183")

    def test_payload_is_calldata_safe(self):
        """No float may cross the consensus boundary (DeFiLens measured the
        TypeError). Walk a real payload and fail on any float."""
        facts = euler_facts()
        install_web()
        MODEL.serve_raw(_TopStrength("COVERED", "SMART_CONTRACT_BUG", "NONE"))
        out = C._collect(facts)

        def walk(v, path):
            self.assertNotIsInstance(v, float, path)
            if isinstance(v, dict):
                for k in v:
                    walk(v[k], path + "." + str(k))
            elif isinstance(v, list):
                for i, x in enumerate(v):
                    walk(x, path + "[" + str(i) + "]")
        walk(out, "payload")
        self.assertTrue(out["ok"])

    def test_hacks_transient_is_retry(self):
        install_web()
        WEB[HACKS_URL] = (503, "down")
        self.assertTrue(C._read_sources(euler_facts())["retry"])

    def test_hacks_rate_limit_is_retry(self):
        install_web()
        WEB[HACKS_URL] = (429, "slow down")
        self.assertTrue(C._read_sources(euler_facts())["retry"])

    def test_hacks_connection_error_is_retry(self):
        install_web()
        WEB[HACKS_URL] = RuntimeError("no route")
        self.assertTrue(C._read_sources(euler_facts())["retry"])

    def test_hacks_404_is_not_retry(self):
        install_web()
        WEB[HACKS_URL] = (404, "gone")
        raw = C._read_sources(euler_facts())
        self.assertFalse(raw["retry"])
        self.assertFalse(raw["llama"]["found"])

    def test_hacks_not_json(self):
        install_web()
        WEB[HACKS_URL] = (200, "<html>")
        self.assertFalse(C._read_sources(euler_facts())["llama"]["found"])

    def test_tvl_transient_is_retry(self):
        install_web()
        WEB[proto("euler-v1")] = (502, "")
        self.assertTrue(C._read_sources(euler_facts())["retry"])

    def test_tvl_400_is_answer(self):
        install_web()
        WEB[proto("euler-v1")] = (400, "Protocol not found")
        raw = C._read_sources(euler_facts())
        self.assertFalse(raw["retry"])
        self.assertFalse(raw["tvl"]["ok"])

    def test_page_render_failure_is_unread(self):
        install_web()
        RENDER[R_EULER] = RuntimeError("WEBPAGE_LOAD_FAILED")
        raw = C._read_sources(euler_facts())
        self.assertFalse(raw["pages"][0]["ok"])
        self.assertEqual(raw["pages"][0]["digest"], "")

    def test_no_tvl_fetch_without_incident(self):
        install_web()
        raw = C._read_sources(euler_facts(llama_id="999999"))
        self.assertFalse(raw["llama"]["found"])
        self.assertNotIn(("request", proto("euler-v1")), CALLS)


class TestReading(unittest.TestCase):
    def read(self, **over):
        facts = euler_facts(**over)
        return C._reading(facts, fetch_raw(facts))

    def test_euler_bracket(self):
        r = self.read()
        self.assertEqual(r["allowed_perils"], ["SMART_CONTRACT_BUG", "ECONOMIC_EXPLOIT"])
        self.assertEqual(r["allowed_exclusions"], [])
        self.assertEqual(r["options"], ["COVERED", "INCONCLUSIVE"])
        self.assertTrue(r["model_called"])

    def test_euler_severity_bucket_4(self):
        r = self.read()
        self.assertEqual(r["bucket"], 4)
        self.assertGreater(r["drop_bps"], 9000)

    def test_euler_strength_one_source_agreeing(self):
        r = self.read()
        self.assertEqual((r["strength_lo"], r["strength_hi"]), (3, 4))

    def test_two_sources_raise_strength(self):
        r = self.read(urls=[R_EULER, PM_EULER])
        self.assertEqual((r["strength_lo"], r["strength_hi"]), (6, 7))

    def test_strength_bracket_is_one_wide(self):
        for urls in ([R_EULER], [R_EULER, PM_EULER], [HOME_EULER]):
            r = self.read(urls=urls)
            self.assertLessEqual(r["strength_hi"] - r["strength_lo"], 1)

    def test_curve_dns(self):
        facts = euler_facts(protocol_name="Curve", llama_slug="curve-dex",
                            llama_id="3", urls=[R_CURVE_DNS], key=K_DNS)
        r = C._reading(facts, fetch_raw(facts))
        self.assertIn("FRONTEND_HIJACK", r["allowed_exclusions"])
        self.assertEqual(C._date_text(r["incident_day"]), "2022-08-09")
        self.assertEqual(r["bucket"], 0)

    def test_multichain(self):
        facts = euler_facts(protocol_name="Multichain", llama_slug="multichain",
                            llama_id="591", urls=[R_MULTI],
                            key="591:2023-07-07")
        r = C._reading(facts, fetch_raw(facts))
        self.assertIn("USER_KEY_COMPROMISE", r["allowed_exclusions"])
        self.assertEqual(C._date_text(r["incident_day"]), "2023-07-07")
        self.assertEqual(r["bucket"], 3)

    def test_tornado_governance(self):
        facts = euler_facts(protocol_name="Tornado Cash", llama_slug="tornado-cash",
                            llama_id="148", urls=[R_TORNADO],
                            key="148:2023-05-20")
        r = C._reading(facts, fetch_raw(facts))
        self.assertIn("GOVERNANCE_ATTACK", r["allowed_exclusions"])

    def test_pinned_no_protocol_name(self):
        # Protocol B's article on protocol A's pool: dated, but to another
        # event and without naming A - EVIDENCE_MISMATCH, no model call.
        r = self.read(urls=[R_MULTI])
        self.assertFalse(r["protocol_match"])
        self.assertFalse(r["model_called"])
        self.assertEqual(r["pinned_as"], "EVIDENCE_MISMATCH")
        self.assertEqual(r["event_gate"], "DIFFERENT")
        self.assertIn("no evidence page both names Euler", r["pinned"])

    def test_pinned_no_indicators(self):
        facts = euler_facts(urls=[HOME_EULER])
        RENDER_HOME = "Euler Finance lets you lend and borrow any asset you like at all.\n"
        install_web()
        RENDER[HOME_EULER] = RENDER_HOME
        r = C._reading(facts, C._read_sources(facts))
        self.assertIn("names no peril and no exclusion", r["pinned"])

    def test_pinned_no_llama_row(self):
        r = self.read(llama_id="424242", key="424242:2023-03-13")
        self.assertIn("no DeFi Llama incident record matches", r["pinned"])
        self.assertEqual(r["incident_day"], 0)
        self.assertFalse(r["model_called"])

    def test_pinned_id_mismatch(self):
        facts = euler_facts(llama_slug="multichain")
        r = C._reading(facts, fetch_raw(facts))
        self.assertIn("name different protocols", r["pinned"])
        self.assertEqual(r["drop_bps"], 0)

    def test_pinned_outside_policy(self):
        r = self.read(perils=["BRIDGE_COMPROMISE"], exclusions=["PHISHING"])
        self.assertIn("neither covers nor excludes", r["pinned"])

    def test_pinned_slug_unreadable(self):
        install_web()
        WEB[proto("euler-v1")] = (400, "Protocol not found")
        facts = euler_facts()
        r = C._reading(facts, C._read_sources(facts))
        self.assertIn("slug could not be read", r["pinned"])

    def test_only_policy_items_enter_bracket(self):
        r = self.read(perils=["ECONOMIC_EXPLOIT"])
        self.assertEqual(r["allowed_perils"], ["ECONOMIC_EXPLOIT"])

    def test_content_hash_moves_with_evidence(self):
        a = self.read()["content_hash"]
        install_web()
        facts = euler_facts()
        RENDER[R_EULER] = ("Euler later found a second reentrancy flaw in its own code.\n"
                           + TEXT[R_EULER])
        b = C._reading(facts, C._read_sources(facts))["content_hash"]
        self.assertNotEqual(a, b)

    def test_content_hash_ignores_page_noise(self):
        a = self.read()["content_hash"]
        install_web()
        facts = euler_facts()
        RENDER[R_EULER] = "Subscribe\nCookie settings\n" + TEXT[R_EULER] + "\nShare\n"
        b = C._reading(facts, C._read_sources(facts))["content_hash"]
        self.assertEqual(a, b)

    def test_archive_snapshot_reads_like_original(self):
        r = self.read(urls=[A_EULER])
        self.assertIn("SMART_CONTRACT_BUG", r["allowed_perils"])
        self.assertEqual(r["allowed_exclusions"], [])
        self.assertTrue(r["protocol_match"])

    def test_contest_mode_novel_only(self):
        base = self.read()
        facts = euler_facts(mode="contest", urls=[A_EULER],
                            prior_digest=base["digest"], prior_sources=1,
                            prior_match=True)
        r = C._reading(facts, fetch_raw(facts))
        # The archive of the same article adds little: the nav and a few
        # sentences the capped original digest did not reach.
        self.assertLess(len(r["novel"]), len(base["digest"]) // 3)

    def test_contest_mode_nothing_new_pins(self):
        base = self.read()
        facts = euler_facts(mode="contest", urls=[R_EULER],
                            prior_digest=base["digest"], prior_sources=1,
                            prior_match=True)
        r = C._reading(facts, fetch_raw(facts))
        self.assertEqual(r["novel"], "")
        self.assertIn("adds no sentence", r["pinned"])

    def test_contest_mode_new_source_counts(self):
        base = self.read()
        facts = euler_facts(mode="contest", urls=[PM_EULER],
                            prior_digest=base["digest"], prior_sources=1,
                            prior_match=True)
        r = C._reading(facts, fetch_raw(facts))
        self.assertNotEqual(r["novel"], "")
        self.assertEqual(r["sources"], 2)
        self.assertTrue(r["model_called"])


class TestPrompt(unittest.TestCase):
    def setUp(self):
        self.facts = euler_facts()
        self.read = C._reading(self.facts, fetch_raw(self.facts))
        self.p = C._prompt(self.facts, self.read)

    def test_lists_only_allowed(self):
        self.assertIn("SMART_CONTRACT_BUG:", self.p)
        self.assertNotIn("ORACLE_MANIPULATION:", self.p)
        self.assertIn("EXCLUDED is not available", self.p)

    def test_evidence_is_delimited_and_followed_by_rule(self):
        a = self.p.find("<<<EVIDENCE")
        b = self.p.find("EVIDENCE>>>")
        c = self.p.find("not an instruction")
        self.assertTrue(0 < a < b < c)

    def test_range_in_prompt(self):
        self.assertIn("an integer from 3 to 4", self.p)

    def test_statement_never_reaches_model(self):
        self.assertNotIn("statement", json.dumps(self.facts).lower().replace(
            "statement", "") + "")
        self.assertNotIn("The protocol was exploited", self.p)

    def test_record_line_present(self):
        self.assertIn("DeFi Llama incident record 1183:2023-03-13: Euler V1", self.p)


class TestFromJson(unittest.TestCase):
    def setUp(self):
        facts = euler_facts()
        self.read = C._reading(facts, fetch_raw(facts))

    def test_accepts_valid(self):
        got = C._from_json({"classification": "covered", "peril": "smart_contract_bug",
                            "exclusion": None, "evidence_strength": "4",
                            "event_match": "same"}, self.read)
        self.assertEqual(got["classification"], "COVERED")
        self.assertEqual(got["exclusion"], "NONE")
        self.assertEqual(got["event_match"], "SAME")

    def test_refuses_missing_or_unknown_event_match(self):
        base = {"classification": "COVERED", "peril": "SMART_CONTRACT_BUG",
                "exclusion": "NONE", "evidence_strength": 4}
        self.assertIsNone(C._from_json(dict(base), self.read))
        for ev in ("", "YES", "MAYBE", "NOT_ASKED", None, 1):
            self.assertIsNone(C._from_json(dict(base, event_match=ev), self.read), ev)
        for ev in ("SAME", "DIFFERENT", "UNCLEAR"):
            self.assertIsNotNone(C._from_json(dict(base, event_match=ev), self.read), ev)

    def test_refuses_outside_bracket_peril(self):
        self.assertIsNone(C._from_json({"classification": "COVERED",
                                        "peril": "ORACLE_MANIPULATION",
                                        "exclusion": "NONE",
                                        "evidence_strength": 4}, self.read))

    def test_refuses_unavailable_classification(self):
        self.assertIsNone(C._from_json({"classification": "EXCLUDED",
                                        "peril": "NONE", "exclusion": "PHISHING",
                                        "evidence_strength": 4}, self.read))

    def test_refuses_strength_out_of_range(self):
        for s in (0, 2, 5, 7, -1, True, None, [3]):
            self.assertIsNone(C._from_json({"classification": "COVERED",
                                            "peril": "SMART_CONTRACT_BUG",
                                            "exclusion": "NONE",
                                            "evidence_strength": s}, self.read), s)

    def test_refuses_covered_with_exclusion(self):
        self.assertIsNone(C._from_json({"classification": "COVERED",
                                        "peril": "SMART_CONTRACT_BUG",
                                        "exclusion": "PHISHING",
                                        "evidence_strength": 4}, self.read))

    def test_refuses_inconclusive_with_peril(self):
        self.assertIsNone(C._from_json({"classification": "INCONCLUSIVE",
                                        "peril": "SMART_CONTRACT_BUG",
                                        "exclusion": "NONE",
                                        "evidence_strength": 3}, self.read))

    def test_refuses_non_dict(self):
        for v in ("COVERED", None, [], 5):
            self.assertIsNone(C._from_json(v, self.read))

    def test_inconclusive_valid(self):
        self.assertIsNotNone(C._from_json({"classification": "INCONCLUSIVE",
                                           "peril": "", "exclusion": "n/a",
                                           "evidence_strength": 3,
                                           "event_match": "SAME"}, self.read))


class TestEffective(unittest.TestCase):
    def test_floor(self):
        self.assertEqual(C._effective({"classification": "COVERED", "strength": 2}),
                         "INCONCLUSIVE")
        self.assertEqual(C._effective({"classification": "COVERED", "strength": 3}),
                         "COVERED")

    def test_excluded_not_floored(self):
        self.assertEqual(C._effective({"classification": "EXCLUDED", "strength": 0}),
                         "EXCLUDED")


# ===========================================================================
# 4. the consensus gates, attacked
# ===========================================================================


def leader_payload(facts=None, cls="COVERED", peril="SMART_CONTRACT_BUG",
                   excl="NONE", strength=None):
    facts = facts or euler_facts()
    install_web()
    MODEL.reset()
    if strength is None:
        MODEL.serve_raw(_TopStrength(cls, peril, excl))
    else:
        MODEL.serve(cls, peril, excl, strength)
    return C._collect(facts)


class TestCoherent(unittest.TestCase):
    def setUp(self):
        self.facts = euler_facts()
        self.good = leader_payload(self.facts)

    def test_honest_leader_is_coherent(self):
        self.assertTrue(self.good["ok"])
        self.assertTrue(C._coherent(self.good, self.facts))

    def test_non_dict(self):
        self.assertFalse(C._coherent(None, self.facts))
        self.assertFalse(C._coherent({"ok": False}, self.facts))

    def test_missing_raw(self):
        bad = dict(self.good)
        bad.pop("raw")
        self.assertFalse(C._coherent(bad, self.facts))

    def test_choice_outside_bracket(self):
        bad = json.loads(json.dumps(self.good))
        bad["choice"]["peril"] = "ORACLE_MANIPULATION"
        self.assertFalse(C._coherent(bad, self.facts))

    def test_strength_above_bracket(self):
        bad = json.loads(json.dumps(self.good))
        bad["choice"]["strength"] = 7
        bad["strength"] = 7
        self.assertFalse(C._coherent(bad, self.facts))

    def test_forged_raw_tvl_changes_bucket_detected(self):
        bad = json.loads(json.dumps(self.good))
        bad["raw"]["tvl"]["low"] = bad["raw"]["tvl"]["before"]
        # derived fields no longer match the payload's claims
        self.assertFalse(C._coherent(bad, self.facts))

    def test_forged_raw_and_fields_consistent_passes_coherent_but_not_agrees(self):
        """A leader that forges its INPUTS consistently passes the pure gate -
        which is why `_agrees` compares inputs against the validator's own
        fetch."""
        bad = json.loads(json.dumps(self.good))
        bad["raw"]["tvl"]["low"] = bad["raw"]["tvl"]["before"]
        rebuilt = C._derive(self.facts, bad["raw"], bad["choice"])
        rebuilt["raw"] = bad["raw"]
        rebuilt["choice"] = bad["choice"]
        self.assertTrue(C._coherent(rebuilt, self.facts))
        mine = leader_payload(self.facts)
        self.assertFalse(C._agrees(rebuilt, mine))


FORGE_FIELDS = (
    ("classification", "EXCLUDED"), ("peril", "ORACLE_MANIPULATION"),
    ("exclusion", "PHISHING"), ("effective", "EXCLUDED"),
    ("incident_day", 1), ("protocol_match", False), ("bucket", 1),
    ("drop_bps", 1234), ("tvl_before", 1), ("tvl_low", 1),
    ("content_hash", "0" * 16), ("digest", "forged"), ("llama_line", "forged"),
    ("tvl_line", "forged"), ("sources", 3), ("strength_lo", 0),
    ("strength_hi", 7), ("allowed_perils", ["ORACLE_MANIPULATION"]),
    ("allowed_exclusions", ["PHISHING"]), ("options", ["EXCLUDED"]),
    ("pinned", "forged"), ("model_called", False), ("llama_found", False),
    ("id_match", False), ("facts_hash", "0" * 16), ("reason", "forged"),
    ("strength", 1), ("claim_id", 99), ("mode", "contest"), ("novel", "x"),
    ("llama_mapped", "PHISHING"),
)


def _make_forge_test(field, value):
    def test(self):
        facts = euler_facts()
        good = leader_payload(facts)
        bad = json.loads(json.dumps(good))
        bad[field] = value
        self.assertFalse(C._coherent(bad, facts), field)
    return test


class TestEveryFieldIsBound(unittest.TestCase):
    """RULE 1 by construction: every stored field of the vector, forged on its
    own, is refused by the pure gate."""


for _f, _v in FORGE_FIELDS:
    setattr(TestEveryFieldIsBound, "test_forged_" + _f, _make_forge_test(_f, _v))


class TestAgrees(unittest.TestCase):
    def setUp(self):
        self.facts = euler_facts()
        self.lead = leader_payload(self.facts, strength=4)

    def test_identical_agree(self):
        mine = leader_payload(self.facts, strength=4)
        self.assertTrue(C._agrees(self.lead, mine))

    def test_strength_one_apart_agrees(self):
        mine = leader_payload(self.facts, strength=3)
        self.assertTrue(C._agrees(self.lead, mine))

    def test_classification_differs(self):
        mine = leader_payload(self.facts, cls="INCONCLUSIVE", peril="NONE", strength=4)
        self.assertFalse(C._agrees(self.lead, mine))

    def test_peril_differs(self):
        mine = leader_payload(self.facts, peril="ECONOMIC_EXPLOIT", strength=4)
        self.assertFalse(C._agrees(self.lead, mine))

    def test_different_page_bytes_disagree(self):
        install_web()
        facts = self.facts
        RENDER[R_EULER] = ("Euler also suffered an oracle failure that same week.\n"
                           + TEXT[R_EULER])
        MODEL.serve("COVERED", "SMART_CONTRACT_BUG", "NONE", 4)
        mine = C._collect(facts)
        self.assertFalse(C._agrees(self.lead, mine))

    def test_different_tvl_disagrees(self):
        install_web()
        doc = json.loads(TVL["euler-v1"])
        doc["tvl"][0]["totalLiquidityUSD"] += 1
        for p in doc["tvl"]:
            p["totalLiquidityUSD"] = p["totalLiquidityUSD"] * 2
        WEB[proto("euler-v1")] = (200, json.dumps(doc))
        MODEL.serve("COVERED", "SMART_CONTRACT_BUG", "NONE", 4)
        mine = C._collect(self.facts)
        self.assertFalse(C._agrees(self.lead, mine))

    def test_retry_never_agrees(self):
        self.assertFalse(C._agrees(self.lead, {"ok": False, "retry": True}))
        self.assertFalse(C._agrees({"ok": False}, self.lead))

    def test_effective_differs_across_floor(self):
        """Strength within tolerance but on opposite sides of the COVERED floor
        is a disagreement about money, and is refused."""
        facts = euler_facts(llama_id="1183")
        lead = leader_payload(facts, strength=3)
        mine = json.loads(json.dumps(lead))
        mine["strength"] = 2
        mine["effective"] = "INCONCLUSIVE"
        self.assertFalse(C._agrees(lead, mine))


class TestLeaderFailed(unittest.TestCase):
    def test_leader_error_rotates(self):
        self.assertFalse(C._leader_failed(object(), euler_facts()))

    def test_retry_agreed_only_if_validator_also_fails(self):
        facts = euler_facts()
        install_web()
        WEB[HACKS_URL] = (503, "")
        res = _Return({"ok": False, "retry": True, "facts_hash": C._facts_hash(facts)})
        self.assertTrue(C._leader_failed(res, facts))
        install_web()
        MODEL.serve("COVERED", "SMART_CONTRACT_BUG", "NONE", 4)
        self.assertFalse(C._leader_failed(res, facts))

    def test_retry_for_other_question_refused(self):
        facts = euler_facts()
        install_web()
        WEB[HACKS_URL] = (503, "")
        res = _Return({"ok": False, "retry": True, "facts_hash": "x"})
        self.assertFalse(C._leader_failed(res, facts))

    def test_model_down_is_retry(self):
        facts = euler_facts()
        install_web()
        MODEL.reset()
        MODEL.fail(5)
        out = C._collect(facts)
        self.assertTrue(out["retry"])

    def test_model_nonsense_is_retry(self):
        facts = euler_facts()
        install_web()
        MODEL.serve_raw({"classification": "MAYBE"})
        self.assertTrue(C._collect(facts)["retry"])


class TestFactsHash(unittest.TestCase):
    def test_changes_with_every_input(self):
        base = C._facts_hash(euler_facts())
        for k, v in (("claim_id", 2), ("urls", [A_EULER]), ("start", 1),
                     ("end", 2), ("waiting_s", 0), ("llama_id", "1"),
                     ("llama_slug", "x"), ("protocol_name", "X"),
                     ("perils", ["ECONOMIC_EXPLOIT"]), ("exclusions", []),
                     ("mode", "contest"), ("prior_digest", "d")):
            self.assertNotEqual(C._facts_hash(euler_facts(**{k: v})), base, k)


# ===========================================================================
# 5. the deterministic outcome
# ===========================================================================

TABLE = [0, 2500, 5000, 7500, 10000]
S0 = epoch("2023-01-01T00:00:00Z")


class TestOutcome(unittest.TestCase):
    def o(self, eff="COVERED", day=None, start=S0, end=S0 + 100 * DAY,
          wait=7 * DAY, amount=GEN, bucket=4, ded=1000):
        return C._outcome(eff, day if day is not None else S0 + 30 * DAY,
                          start, end, wait, amount, TABLE, bucket, ded)

    def test_covered_pays(self):
        self.assertEqual(self.o(), ("APPROVED", 9 * GEN // 10))

    def test_bucket_tables(self):
        for b, want in ((0, 0), (1, 225), (2, 450), (3, 675), (4, 900)):
            st, gross = self.o(bucket=b)
            self.assertEqual(gross, want * GEN // 1000)
            self.assertEqual(st, "NO_PAYOUT" if want == 0 else "APPROVED")

    def test_backdated(self):
        self.assertEqual(self.o(day=S0 - DAY)[0], "REJECTED_BACKDATED")

    def test_inside_waiting_period_is_backdated(self):
        self.assertEqual(self.o(day=S0 + 6 * DAY)[0], "REJECTED_BACKDATED")

    def test_waiting_boundary_is_covered(self):
        self.assertEqual(self.o(day=S0 + 7 * DAY)[0], "APPROVED")

    def test_after_end(self):
        self.assertEqual(self.o(day=S0 + 101 * DAY)[0], "REJECTED_AFTER_COVER_END")

    def test_end_day_covered(self):
        self.assertEqual(self.o(day=S0 + 100 * DAY)[0], "APPROVED")

    def test_excluded(self):
        self.assertEqual(self.o(eff="EXCLUDED"), ("DENIED_EXCLUDED", 0))

    def test_excluded_backdated_is_backdated(self):
        self.assertEqual(self.o(eff="EXCLUDED", day=S0 - DAY)[0], "REJECTED_BACKDATED")

    def test_inconclusive_first(self):
        self.assertEqual(self.o(eff="INCONCLUSIVE", day=S0 - DAY)[0], "INCONCLUSIVE")

    def test_deductible(self):
        self.assertEqual(self.o(ded=0)[1], GEN)
        self.assertEqual(self.o(ded=5000)[1], GEN // 2)


# ===========================================================================
# 6. the stateful contract
# ===========================================================================


class TestConstructor(unittest.TestCase):
    def test_defaults_are_canonical(self):
        MESSAGE.sender_address = OWNER
        c = MOD.CoverClaim()
        self.assertEqual(int(c.demo_backdate_days), 0)
        self.assertEqual(int(c.claim_window_s), 30 * DAY)
        self.assertEqual(int(c.settlement_window_s), 72 * HOUR)
        self.assertEqual(int(c.contest_window_s), 48 * HOUR)
        self.assertEqual(c.owner, OWNER)

    def test_clamped_not_rejected(self):
        c = MOD.CoverClaim(demo_backdate_days=99999, claim_window_s=1,
                           contest_bond_wei=1)
        self.assertEqual(int(c.demo_backdate_days), C.MAX_BACKDATE_DAYS)
        self.assertEqual(int(c.claim_window_s), 60)
        self.assertEqual(int(c.contest_bond_wei), 10 ** 15)

    def test_config_labels_demo(self):
        c = fresh(demo=True)
        cfg = view(c, "get_config")
        self.assertTrue(cfg["demo"])
        self.assertIn("DEMO", cfg["label"])
        self.assertEqual(cfg["demo_backdate_days"], DEMO_DAYS)

    def test_config_labels_canonical(self):
        cfg = view(fresh(demo=False), "get_config")
        self.assertFalse(cfg["demo"])
        self.assertIn("CANONICAL", cfg["label"])

    def test_config_carries_the_sentence(self):
        cfg = view(fresh(), "get_config")
        self.assertIn("GenLayer reads public incident evidence and classifies it "
                      "against the frozen policy's covered perils and exclusions.",
                      cfg["division_of_labour"])


class TestCreatePool(unittest.TestCase):
    def setUp(self):
        self.c = fresh()

    def args(self, **over):
        a = dict(name="Euler", slug="euler-v1", lid="1183", chain="Ethereum",
                 perils=ALL_PERILS, excl=ALL_EXCL, rate=100, wait=7, ded=1000,
                 maxc=5 * GEN, term=365, coll=10000, table="",
                 domains="euler.finance", wording="w")
        a.update(over)
        return [a["name"], a["slug"], a["lid"], a["chain"], a["perils"],
                a["excl"], a["rate"], a["wait"], a["ded"], a["maxc"], a["term"],
                a["coll"], a["table"], a["domains"], a["wording"]]

    def create(self, value=10 * GEN, who=UW, **over):
        return send(self.c, who, value, "create_pool", *self.args(**over))

    def test_ok(self):
        out = self.create()
        self.assertTrue(ok(out), out)
        p = self.c.pools[0]
        self.assertEqual(int(p.capital_wei), 10 * GEN)
        self.assertEqual(p.underwriter, UW)
        self.assertEqual(out["evidence_allowlist"],
                         ["rekt.news", "web.archive.org", "euler.finance"])

    def test_policy_hash_verifies(self):
        self.create()
        pol = view(self.c, "get_policy", 1)
        self.assertTrue(pol["hash_matches"])
        self.assertIn("SMART_CONTRACT_BUG", pol["text"])

    def test_policy_hash_independent_of_typed_order(self):
        self.create(perils="ECONOMIC_EXPLOIT,SMART_CONTRACT_BUG")
        self.create(perils="SMART_CONTRACT_BUG,ECONOMIC_EXPLOIT")
        self.assertEqual(str(self.c.pools[0].policy_hash), str(self.c.pools[1].policy_hash))

    def test_refusals(self):
        cases = [
            dict(value=GEN - 1),
            dict(name="x"),
            dict(slug=""),
            dict(slug="euler v1"),
            dict(lid=""),
            dict(lid="12a"),
            dict(perils=""),
            dict(perils="ACTS_OF_GOD"),
            dict(excl="EARTHQUAKE"),
            dict(rate=0),
            dict(rate=2001),
            dict(wait=-1),
            dict(wait=31),
            dict(ded=5001),
            dict(ded=-1),
            dict(maxc=10 ** 15),
            dict(term=0),
            dict(term=366),
            dict(coll=1999),
            dict(coll=10001),
            dict(table="0,1,2"),
            dict(table="0,5000,100,7500,10000"),
            dict(domains="api.llama.fi"),
            dict(domains="a.com,b.com,c.com,d.com"),
        ]
        for case in cases:
            value = case.pop("value", 10 * GEN)
            out = self.create(value=value, **case)
            self.assertTrue(rejected(out), (case, out))
        self.assertEqual(len(self.c.pools), 0)
        # every refused deposit is the sender's to take back
        self.assertEqual(int(self.c.payout_wei.get(UW)),
                         (len(cases) - 1) * 10 * GEN + GEN - 1)

    def test_refused_while_paused(self):
        send(self.c, OWNER, 0, "set_paused", True)
        self.assertTrue(rejected(self.create()))

    def test_exclusions_may_be_empty(self):
        self.assertTrue(ok(self.create(excl="")))

    def test_custom_table_stored(self):
        self.create(table="0,1000,2000,3000,4000")
        self.assertEqual(str(self.c.pools[0].payout_table_csv), "0,1000,2000,3000,4000")

    def test_expiry(self):
        self.create(term=90)
        self.assertEqual(int(self.c.pools[0].expires_at), NOW + 90 * DAY)

    def test_indexed_by_underwriter(self):
        self.create()
        got = view(self.c, "get_pools_by_underwriter", UW.as_hex)
        self.assertEqual(len(got["items"]), 1)


class TestCapacity(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        self.pid = make_pool(self.c, capital=10 * GEN)

    def test_add_capacity(self):
        self.assertTrue(ok(send(self.c, UW, 2 * GEN, "add_capacity", self.pid)))
        self.assertEqual(int(self.c.pools[0].capital_wei), 12 * GEN)

    def test_add_capacity_only_underwriter(self):
        self.assertTrue(rejected(send(self.c, ALICE, GEN, "add_capacity", self.pid)))
        self.assertEqual(int(self.c.payout_wei.get(ALICE)), GEN)

    def test_add_capacity_zero(self):
        self.assertTrue(rejected(send(self.c, UW, 0, "add_capacity", self.pid)))

    def test_add_capacity_paused(self):
        send(self.c, OWNER, 0, "set_paused", True)
        self.assertTrue(rejected(send(self.c, UW, GEN, "add_capacity", self.pid)))

    def test_add_capacity_after_term(self):
        advance(366 * DAY)
        self.assertTrue(rejected(send(self.c, UW, GEN, "add_capacity", self.pid)))

    def test_withdraw_free(self):
        out = send(self.c, UW, 0, "withdraw_capacity", self.pid, 4 * GEN)
        self.assertTrue(ok(out))
        self.assertEqual(int(self.c.pools[0].capital_wei), 6 * GEN)
        self.assertEqual(drain(self.c, UW), 4 * GEN)

    def test_withdraw_only_underwriter(self):
        self.assertTrue(rejected(send(self.c, ALICE, 0, "withdraw_capacity",
                                      self.pid, GEN)))

    def test_withdraw_bad_amount(self):
        for amt in (0, -1, "x", 11 * GEN):
            self.assertTrue(rejected(send(self.c, UW, 0, "withdraw_capacity",
                                          self.pid, amt)), amt)

    def test_withdraw_works_while_paused(self):
        send(self.c, OWNER, 0, "set_paused", True)
        self.assertTrue(ok(send(self.c, UW, 0, "withdraw_capacity", self.pid, GEN)))

    def test_close_empty_pool(self):
        out = send(self.c, UW, 0, "close_pool", self.pid)
        self.assertTrue(ok(out))
        self.assertEqual(int(out["returned_wei"]), 10 * GEN)
        self.assertEqual(drain(self.c, UW), 10 * GEN)
        self.assertEqual(int(self.c.balance_wei), 0)

    def test_close_twice(self):
        send(self.c, UW, 0, "close_pool", self.pid)
        self.assertTrue(rejected(send(self.c, UW, 0, "close_pool", self.pid)))

    def test_close_only_underwriter(self):
        self.assertTrue(rejected(send(self.c, STRANGER, 0, "close_pool", self.pid)))

    def test_close_refused_with_live_cover(self):
        buy(self.c, self.pid)
        out = send(self.c, UW, 0, "close_pool", self.pid)
        self.assertTrue(rejected(out))
        self.assertIn("live cover", out["reason"])

    def test_no_such_pool(self):
        for m, args in (("add_capacity", (9,)), ("withdraw_capacity", (9, 1)),
                        ("close_pool", (9,))):
            self.assertTrue(rejected(send(self.c, UW, 0, m, *args)))


class TestBuyCover(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        self.pid = make_pool(self.c, capital=10 * GEN, max_cover=5 * GEN)

    def test_ok_and_premium_exact(self):
        amt, days = 2 * GEN, 90
        prem = C._premium(amt, 100, days)
        out = send(self.c, ALICE, prem, "buy_cover", self.pid, amt, days)
        self.assertTrue(ok(out), out)
        self.assertEqual(int(out["premium_wei"]), prem)
        self.assertEqual(int(out["overpaid_wei"]), 0)
        cov = self.c.covers[0]
        self.assertEqual(int(cov.lock_wei), amt)
        self.assertEqual(int(self.c.pools[0].locked_wei), amt)
        self.assertEqual(int(self.c.pools[0].premiums_held_wei), prem)

    def test_overpayment_refunded(self):
        prem = C._premium(GEN, 100, 30)
        out = send(self.c, ALICE, prem + 12345, "buy_cover", self.pid, GEN, 30)
        self.assertTrue(ok(out))
        self.assertEqual(int(out["overpaid_wei"]), 12345)
        self.assertEqual(drain(self.c, ALICE), 12345)

    def test_underpayment_refused_and_refunded(self):
        prem = C._premium(GEN, 100, 30)
        out = send(self.c, ALICE, prem - 1, "buy_cover", self.pid, GEN, 30)
        self.assertTrue(rejected(out))
        self.assertEqual(int(self.c.payout_wei.get(ALICE)), prem - 1)
        self.assertEqual(len(self.c.covers), 0)

    def test_demo_start_is_backdated(self):
        cid = buy(self.c, self.pid)
        self.assertEqual(int(self.c.covers[cid - 1].start), NOW - DEMO_DAYS * DAY)

    def test_canonical_start_is_now(self):
        c = fresh(demo=False)
        pid = make_pool(c)
        cid = buy(c, pid, days=30)
        self.assertEqual(int(c.covers[cid - 1].start), NOW)
        self.assertEqual(int(c.covers[cid - 1].end), NOW + 30 * DAY)

    def test_claim_deadline(self):
        c = fresh(demo=False)
        pid = make_pool(c)
        cid = buy(c, pid, days=30)
        self.assertEqual(int(c.covers[cid - 1].claim_deadline), NOW + 60 * DAY)

    def test_demo_deadline_from_purchase_when_end_is_past(self):
        cid = buy(self.c, self.pid, days=30)
        self.assertEqual(int(self.c.covers[cid - 1].claim_deadline), NOW + 30 * DAY)

    def test_max_cover_per_buyer(self):
        buy(self.c, self.pid, amount=4 * GEN)
        advance(61)
        out = send(self.c, ALICE, 10 * GEN, "buy_cover", self.pid, 2 * GEN, 30)
        self.assertTrue(rejected(out))
        self.assertIn("max cover per buyer", out["reason"])

    def test_max_cover_is_per_buyer_not_global(self):
        buy(self.c, self.pid, who=ALICE, amount=5 * GEN)
        buy(self.c, self.pid, who=BOB, amount=5 * GEN)

    def test_capacity_limit(self):
        buy(self.c, self.pid, who=ALICE, amount=5 * GEN)
        buy(self.c, self.pid, who=BOB, amount=5 * GEN)
        out = send(self.c, CAROL, 10 * GEN, "buy_cover", self.pid, GEN, 30)
        self.assertTrue(rejected(out))
        self.assertIn("unlocked capacity", out["reason"])

    def test_collateral_ratio_lets_more_cover_be_written(self):
        pid = make_pool(self.c, uw=UW2, capital=GEN, coll=5000, max_cover=GEN)
        buy(self.c, pid, who=ALICE, amount=GEN)
        buy(self.c, pid, who=BOB, amount=GEN)
        self.assertEqual(int(self.c.pools[pid - 1].locked_wei), GEN)

    def test_rate_limit(self):
        buy(self.c, self.pid, amount=GEN)
        out = send(self.c, ALICE, 10 * GEN, "buy_cover", self.pid, GEN, 30)
        self.assertTrue(rejected(out))
        self.assertIn("per wallet", out["reason"])
        advance(60)
        self.assertTrue(ok(send(self.c, ALICE, 10 * GEN, "buy_cover", self.pid, GEN, 30)))

    def test_refusals(self):
        for amount, days in ((10 ** 15, 30), (GEN, 0), (GEN, 366), ("x", 30),
                             (GEN, "y")):
            self.assertTrue(rejected(send(self.c, BOB, 10 * GEN, "buy_cover",
                                          self.pid, amount, days)), (amount, days))
        self.assertEqual(len(self.c.covers), 0)

    def test_cover_must_end_in_pool_term(self):
        c = fresh(demo=False)
        pid = make_pool(c, term=30)
        advance(10 * DAY)
        out = send(c, ALICE, 10 * GEN, "buy_cover", pid, GEN, 30)
        self.assertTrue(rejected(out))
        self.assertIn("after the pool's term", out["reason"])

    def test_expired_pool(self):
        advance(366 * DAY)
        self.assertTrue(rejected(send(self.c, ALICE, 10 * GEN, "buy_cover",
                                      self.pid, GEN, 30)))

    def test_closed_pool(self):
        send(self.c, UW, 0, "close_pool", self.pid)
        self.assertTrue(rejected(send(self.c, ALICE, 10 * GEN, "buy_cover",
                                      self.pid, GEN, 30)))

    def test_paused(self):
        send(self.c, OWNER, 0, "set_paused", True)
        out = send(self.c, ALICE, 10 * GEN, "buy_cover", self.pid, GEN, 30)
        self.assertTrue(rejected(out))
        self.assertEqual(int(self.c.payout_wei.get(ALICE)), 10 * GEN)

    def test_no_counter_moves_on_refusal(self):
        before = (int(self.c.total_covers), int(self.c.pools[0].cover_count),
                  int(self.c.pools[0].locked_wei))
        send(self.c, ALICE, 1, "buy_cover", self.pid, GEN, 30)
        after = (int(self.c.total_covers), int(self.c.pools[0].cover_count),
                 int(self.c.pools[0].locked_wei))
        self.assertEqual(before, after)

    def test_quote_matches_buy(self):
        q = view(self.c, "quote", self.pid, 3 * GEN, 45)
        self.assertEqual(int(q["premium_wei"]), C._premium(3 * GEN, 100, 45))
        self.assertTrue(q["ok"])
        self.assertEqual(len(q["payout_by_bucket_wei"]), 5)

    def test_quote_reasons(self):
        self.assertFalse(view(self.c, "quote", self.pid, 1, 30)["ok"])
        self.assertFalse(view(self.c, "quote", self.pid, 6 * GEN, 30)["ok"])
        self.assertFalse(view(self.c, "quote", 99, GEN, 30)["ok"])


class TestCancelAndRelease(unittest.TestCase):
    def setUp(self):
        # waiting 0: these tests file claims at once, and a claim may not be
        # filed inside a waiting period (TestWaitingPeriodGate).
        self.c = fresh(demo=False)
        self.pid = make_pool(self.c, wait=0)

    def test_cancel_prorata(self):
        cid = buy(self.c, self.pid, amount=GEN, days=30)
        prem = int(self.c.covers[0].premium_wei)
        advance(10 * DAY)
        out = send(self.c, ALICE, 0, "cancel_cover", cid)
        self.assertTrue(ok(out))
        want = C._refund(prem, 30 * DAY, 20 * DAY)
        self.assertEqual(int(out["refund_wei"]), want)
        self.assertEqual(int(out["refund_wei"]) + int(out["earned_by_underwriter_wei"]), prem)
        self.assertEqual(int(self.c.pools[0].locked_wei), 0)

    def test_cancel_immediately_full_refund(self):
        cid = buy(self.c, self.pid, amount=GEN, days=30)
        out = send(self.c, ALICE, 0, "cancel_cover", cid)
        self.assertEqual(int(out["refund_wei"]), int(self.c.covers[0].premium_wei))

    def test_cancel_only_buyer(self):
        cid = buy(self.c, self.pid)
        self.assertTrue(rejected(send(self.c, BOB, 0, "cancel_cover", cid)))

    def test_cancel_after_claim_refused(self):
        cid = buy(self.c, self.pid, days=30)
        advance(DAY)
        file(self.c, cid, R_EULER, key=live_key("1183"))
        self.assertTrue(rejected(send(self.c, ALICE, 0, "cancel_cover", cid)))

    def test_cancel_after_end_refused(self):
        cid = buy(self.c, self.pid, days=30)
        advance(31 * DAY)
        self.assertTrue(rejected(send(self.c, ALICE, 0, "cancel_cover", cid)))

    def test_cancel_twice(self):
        cid = buy(self.c, self.pid, days=30)
        send(self.c, ALICE, 0, "cancel_cover", cid)
        self.assertTrue(rejected(send(self.c, ALICE, 0, "cancel_cover", cid)))

    def test_cancel_works_while_paused(self):
        cid = buy(self.c, self.pid, days=30)
        send(self.c, OWNER, 0, "set_paused", True)
        self.assertTrue(ok(send(self.c, ALICE, 0, "cancel_cover", cid)))

    def test_release_after_deadline(self):
        cid = buy(self.c, self.pid, days=30)
        prem = int(self.c.covers[0].premium_wei)
        self.assertTrue(rejected(send(self.c, STRANGER, 0, "release_cover", cid)))
        advance(60 * DAY + 1)
        out = send(self.c, STRANGER, 0, "release_cover", cid)
        self.assertTrue(ok(out), out)
        self.assertEqual(int(out["premium_earned_wei"]), prem)
        self.assertEqual(int(self.c.payout_wei.get(UW)), prem)
        self.assertEqual(int(self.c.pools[0].locked_wei), 0)
        self.assertEqual(str(self.c.covers[0].status), "RELEASED")

    def test_release_twice(self):
        cid = buy(self.c, self.pid, days=30)
        advance(61 * DAY)
        send(self.c, STRANGER, 0, "release_cover", cid)
        self.assertTrue(rejected(send(self.c, STRANGER, 0, "release_cover", cid)))

    def test_release_is_permissionless_and_unpaused(self):
        cid = buy(self.c, self.pid, days=30)
        send(self.c, OWNER, 0, "set_paused", True)
        advance(61 * DAY)
        self.assertTrue(ok(send(self.c, NOBODY, 0, "release_cover", cid)))

    def test_release_blocked_by_filed_claim(self):
        cid = buy(self.c, self.pid, days=30)
        advance(DAY)
        file(self.c, cid, R_EULER, key=live_key("1183"))
        advance(61 * DAY)
        out = send(self.c, STRANGER, 0, "release_cover", cid)
        self.assertTrue(rejected(out))
        self.assertIn("must settle first", out["reason"])

    def test_exposure_released(self):
        cid = buy(self.c, self.pid, amount=5 * GEN, days=30)
        advance(61 * DAY)
        send(self.c, STRANGER, 0, "release_cover", cid)
        buy(self.c, self.pid, amount=5 * GEN, days=1)


class TestWaitingPeriodGate(unittest.TestCase):
    """FIX 1: a claim cannot be FILED before start + waiting period. Any
    incident that has happened by then predates the waiting period, so such a
    claim could only be REJECTED_BACKDATED - and would spend the cover's one
    claim doing it."""

    def setUp(self):
        self.c = fresh(demo=False)
        self.pid = make_pool(self.c, wait=7)
        self.cid = buy(self.c, self.pid, days=30)

    def test_refused_inside_waiting_period(self):
        out = send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER, R_EULER, "x")
        self.assertTrue(rejected(out))
        self.assertEqual(out["reason"], "cover waiting period has not ended yet, "
                         "claimable after " + str(NOW + 7 * DAY))
        self.assertEqual(out["claimable_after"], NOW + 7 * DAY)

    def test_refused_before_genlayer_and_claim_not_spent(self):
        send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER, R_EULER, "x")
        self.assertEqual(len(self.c.claims), 0)
        self.assertEqual(int(self.c.covers[0].claim_id), 0)
        self.assertEqual(CALLS, [])
        self.assertEqual(MODEL.calls, 0)

    def test_one_second_before_is_refused(self):
        advance(7 * DAY - 1)
        self.assertTrue(rejected(send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER, R_EULER, "x")))

    def test_allowed_exactly_at_waiting_end(self):
        # At the second the wait ends the waiting gate opens. No incident can
        # yet be dated inside the cover (days are whole days, and today began
        # before the wait ended), so the KEY is what refuses now; from the
        # next day an incident of that day can be claimed.
        advance(7 * DAY)
        out = send(self.c, ALICE, 0, "file_claim", self.cid, live_key("1183"), R_EULER, "x")
        self.assertNotIn("waiting period has not ended", out.get("reason", ""))
        advance(DAY)
        self.assertTrue(ok(send(self.c, ALICE, 0, "file_claim", self.cid,
                                live_key("1183"), R_EULER, "x")))

    def test_value_sent_is_returned(self):
        send(self.c, ALICE, 7, "file_claim", self.cid, K_EULER, R_EULER, "x")
        self.assertEqual(int(self.c.payout_wei.get(ALICE)), 7)

    def test_refused_while_paused_too_but_only_for_waiting(self):
        send(self.c, OWNER, 0, "set_paused", True)
        out = send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER, R_EULER, "x")
        self.assertIn("waiting period", out["reason"])

    def test_waiting_zero_files_at_once(self):
        pid = make_pool(self.c, uw=UW2, wait=0)
        cid = buy(self.c, pid, who=BOB, days=30)
        out = send(self.c, BOB, 0, "file_claim", cid, live_key("1183"), R_EULER, "x")
        self.assertNotIn("waiting period has not ended", out.get("reason", ""))
        advance(DAY)
        self.assertTrue(ok(send(self.c, BOB, 0, "file_claim", cid, live_key("1183"),
                                R_EULER, "x")))

    def test_demo_waiting_period_already_past(self):
        c = fresh(demo=True)
        pid = make_pool(c, wait=7)
        cid = buy(c, pid)
        self.assertTrue(ok(send(c, ALICE, 0, "file_claim", cid, K_EULER, R_EULER, "x")))

    def test_view_flags_follow_the_gate(self):
        v = view(self.c, "get_cover", self.cid)
        self.assertFalse(v["claimable"])
        self.assertTrue(v["in_waiting_period"])
        advance(7 * DAY)
        v = view(self.c, "get_cover", self.cid)
        self.assertTrue(v["claimable"])
        self.assertFalse(v["in_waiting_period"])

    def test_cover_can_still_claim_after_the_wait(self):
        send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER, R_EULER, "early")
        advance(8 * DAY)
        out = send(self.c, ALICE, 0, "file_claim", self.cid, live_key("1183"), R_EULER,
                   "later")
        self.assertTrue(ok(out), out)


def _tvl_doc(points):
    return json.dumps({"id": "1183", "name": "Euler V1", "tvl": points})


INC = epoch("2023-03-13T00:00:00Z")


class TestSeverityMustBeMeasurable(unittest.TestCase):
    """FIX 2: no TVL data around the incident is MISSING DATA, not "no damage".
    A COVERED reading then ends INCONCLUSIVE (refileable), never a final
    NO_PAYOUT."""

    def setUp(self):
        self.c = fresh()
        self.pid = make_pool(self.c)
        self.cid = buy(self.c, self.pid)
        self.clid = file(self.c, self.cid, R_EULER)

    def judge_with(self, points, *choice):
        WEB[proto("euler-v1")] = (200, _tvl_doc(points))
        return judge(self.c, self.clid, *choice) if choice else judge(self.c, self.clid)

    def test_empty_series_is_inconclusive(self):
        out = self.judge_with([])
        self.assertEqual(out["classification"], "COVERED")
        self.assertEqual(out["outcome"], "INCONCLUSIVE")
        self.assertIn("could not be measured", out["reason"])

    def test_points_before_but_none_after(self):
        out = self.judge_with([{"date": INC - DAY, "totalLiquidityUSD": 2.3e8}])
        self.assertEqual(out["outcome"], "INCONCLUSIVE")

    def test_points_after_but_none_before(self):
        out = self.judge_with([{"date": INC + DAY, "totalLiquidityUSD": 1e7}])
        self.assertEqual(out["outcome"], "INCONCLUSIVE")

    def test_zero_tvl_before_is_unmeasurable(self):
        out = self.judge_with([{"date": INC - DAY, "totalLiquidityUSD": 0},
                               {"date": INC + DAY, "totalLiquidityUSD": 0}])
        self.assertEqual(out["outcome"], "INCONCLUSIVE")

    def test_refileable_and_pays_once_data_exists(self):
        self.judge_with([])
        cl = self.c.claims[0]
        self.assertEqual(str(cl.status), "INCONCLUSIVE")
        self.assertEqual(int(cl.refile_until), int(self.c.covers[0].claim_deadline))
        install_web()      # DeFi Llama now has the history
        self.assertTrue(ok(send(self.c, ALICE, 0, "refile_claim", self.clid, "", A_EULER, "again")))
        self.assertEqual(judge(self.c, self.clid)["outcome"], "APPROVED")

    def test_measured_zero_drop_is_still_no_payout(self):
        out = self.judge_with([{"date": INC - DAY, "totalLiquidityUSD": 1e8},
                               {"date": INC + DAY, "totalLiquidityUSD": 1e8}])
        self.assertEqual(out["outcome"], "NO_PAYOUT")

    def test_excluded_stays_denied_without_tvl(self):
        pid = make_pool(self.c, uw=UW2, spec=CURVE)
        cid = buy(self.c, pid, who=BOB)
        clid = file(self.c, cid, R_CURVE_DNS)
        WEB[proto("curve-dex")] = (200, json.dumps({"id": "3", "tvl": []}))
        out = judge(self.c, clid, "EXCLUDED", "NONE", "FRONTEND_HIJACK")
        self.assertEqual(out["outcome"], "DENIED_EXCLUDED")

    def test_backdated_stays_backdated_without_tvl(self):
        # A historical incident on a cover bought today is refused at filing
        # - before TVL is ever read, so missing TVL cannot soften it.
        c = fresh(demo=False)
        pid = make_pool(c, wait=0)
        cid = buy(c, pid, days=30)
        WEB[proto("euler-v1")] = (200, _tvl_doc([]))
        out = send(c, ALICE, 0, "file_claim", cid, K_EULER, R_EULER, "x")
        self.assertTrue(rejected(out))
        self.assertIn("predates this cover's start", out["reason"])
        self.assertEqual(C._outcome("COVERED", S0 - DAY, S0, S0 + 30 * DAY, 0, GEN,
                                    [0, 2500, 5000, 7500, 10000], 0, 0, False)[0],
                         "REJECTED_BACKDATED")

    def test_measured_flag_is_compared(self):
        self.assertIn("tvl_measured", C.EXACT_BOOL)

    def test_outcome_unit(self):
        self.assertEqual(C._outcome("COVERED", S0 + 30 * DAY, S0, S0 + 100 * DAY, 0,
                                    GEN, TABLE, 0, 1000, False), ("INCONCLUSIVE", 0))
        self.assertEqual(C._outcome("COVERED", S0 + 30 * DAY, S0, S0 + 100 * DAY, 0,
                                    GEN, TABLE, 0, 1000, True), ("NO_PAYOUT", 0))

    def test_contest_path_uses_it_too(self):
        judge(self.c, self.clid)     # APPROVED with real data
        send(self.c, UW, int(self.c.contest_bond_wei), "contest", self.clid, PM_EULER,
             TestContest.GROUNDS)
        WEB[proto("euler-v1")] = (200, _tvl_doc([]))
        MODEL.serve_raw(_TopStrength("COVERED", "SMART_CONTRACT_BUG", "NONE"))
        out = send(self.c, STRANGER, 0, "judge_contest", self.clid)
        self.assertEqual(out["rejudged_as"] if out["contest"] == "UPHELD" else out["outcome"],
                         "INCONCLUSIVE")


class TestFileClaim(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        self.pid = make_pool(self.c)
        self.cid = buy(self.c, self.pid)

    def test_ok(self):
        out = send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER, R_EULER, "hacked")
        self.assertTrue(ok(out), out)
        cl = self.c.claims[0]
        self.assertEqual(str(cl.status), "FILED")
        self.assertEqual(int(self.c.covers[0].claim_id), 1)

    def test_only_buyer(self):
        self.assertTrue(rejected(send(self.c, BOB, 0, "file_claim", self.cid, K_EULER,
                                      R_EULER, "x")))

    def test_refuses_random_blog_before_genlayer(self):
        out = send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER, BLOG, "x")
        self.assertTrue(rejected(out))
        self.assertIn("refused before judging", out["reason"])
        self.assertEqual(len(self.c.claims), 0)
        self.assertEqual(CALLS, [])
        self.assertEqual(MODEL.calls, 0)

    def test_refuses_after_deadline(self):
        advance(31 * DAY)
        self.assertTrue(rejected(send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER,
                                      R_EULER, "x")))

    def test_works_while_paused(self):
        send(self.c, OWNER, 0, "set_paused", True)
        self.assertTrue(ok(send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER,
                                R_EULER, "x")))

    def test_statement_capped(self):
        send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER, R_EULER, "x" * 5000)
        self.assertEqual(len(str(self.c.claims[0].statement)), C.MAX_STATEMENT)

    def test_value_sent_to_file_claim_is_returned(self):
        send(self.c, ALICE, 5, "file_claim", self.cid, K_EULER, R_EULER, "x")
        self.assertEqual(int(self.c.payout_wei.get(ALICE)), 5)

    def test_check_evidence_view(self):
        got = view(self.c, "check_evidence", self.pid, R_EULER + " " + BLOG)
        self.assertFalse(got["ok"])
        self.assertTrue(got["items"][0]["ok"])
        self.assertFalse(got["items"][1]["ok"])


class TestJudgeClaim(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        self.pid = make_pool(self.c)
        self.cid = buy(self.c, self.pid, amount=2 * GEN)

    def test_covered_approved(self):
        clid = file(self.c, self.cid, R_EULER)
        out = judge(self.c, clid)
        self.assertTrue(ok(out), out)
        self.assertEqual(out["outcome"], "APPROVED")
        self.assertEqual(out["incident_date"], "2023-03-13")
        self.assertEqual(out["severity_bucket"], 4)
        cl = self.c.claims[0]
        self.assertEqual(int(cl.gross_wei), C._gross(2 * GEN, 10000, 1000))
        self.assertEqual(int(cl.batch_id), 1)
        self.assertEqual(str(cl.peril), "SMART_CONTRACT_BUG")
        self.assertTrue(bool(cl.model_called))

    def test_judge_is_permissionless_and_moves_no_money(self):
        clid = file(self.c, self.cid, R_EULER)
        before = int(self.c.payable_wei)
        judge(self.c, clid)
        self.assertEqual(int(self.c.payable_wei), before)

    def test_judge_twice_refused(self):
        clid = file(self.c, self.cid, R_EULER)
        judge(self.c, clid)
        self.assertTrue(rejected(judge(self.c, clid)))

    def test_excluded(self):
        pid = make_pool(self.c, uw=UW2, spec=CURVE)
        cid = buy(self.c, pid, who=BOB)
        clid = file(self.c, cid, R_CURVE_DNS)
        out = judge(self.c, clid, "EXCLUDED", "NONE", "FRONTEND_HIJACK")
        self.assertEqual(out["outcome"], "DENIED_EXCLUDED")
        self.assertEqual(out["incident_date"], "2022-08-09")

    def test_inconclusive_without_model(self):
        clid = file(self.c, self.cid, HOME_EULER)
        RENDER[HOME_EULER] = "Euler Finance lets you lend and borrow almost anything."
        out = judge(self.c, clid)
        self.assertEqual(out["outcome"], "INCONCLUSIVE")
        self.assertFalse(out["model_called"])
        self.assertEqual(MODEL.calls, 0)

    def test_model_inconclusive(self):
        clid = file(self.c, self.cid, R_EULER)
        out = judge(self.c, clid, "INCONCLUSIVE", "NONE", "NONE")
        self.assertEqual(out["outcome"], "INCONCLUSIVE")

    def test_thin_covered_is_inconclusive(self):
        """A COVERED reading below the strength floor pays nothing yet."""
        facts_raw = fetch_raw(euler_facts())
        # llama disagreement -> bracket [2,3]; strength 2 -> INCONCLUSIVE
        pid = make_pool(self.c, uw=UW2, perils="ECONOMIC_EXPLOIT")
        cid = buy(self.c, pid, who=BOB)
        clid = file(self.c, cid, R_EULER)
        out = judge(self.c, clid, "COVERED", "ECONOMIC_EXPLOIT", "NONE", strength=2)
        self.assertEqual(out["effective"], "INCONCLUSIVE")
        self.assertEqual(out["outcome"], "INCONCLUSIVE")
        self.assertIsNotNone(facts_raw)

    def test_after_cover_end(self):
        # KyberSwap's record (2023-11-22) is after this cover ends: the key is
        # refused at filing, before any fetch or model call, and the cover
        # keeps its one claim.
        pid = make_pool(self.c, uw=UW2, spec=KYBER)
        cid = buy(self.c, pid, who=BOB)
        out = send(self.c, BOB, 0, "file_claim", cid, "2615:2023-11-22", R_KYBER, "x")
        self.assertTrue(rejected(out))
        self.assertIn("after this cover ended", out["reason"])
        self.assertEqual(int(self.c.covers[cid - 1].claim_id), 0)
        self.assertEqual(MODEL.calls, 0)
        self.assertEqual(C._outcome("COVERED", C._day_of(epoch("2023-11-22T00:00:00Z")),
                                    epoch("2022-07-28T12:00:00Z"),
                                    epoch("2023-07-28T12:00:00Z"), 0, GEN,
                                    [0, 2500, 5000, 7500, 10000], 4, 0)[0],
                         "REJECTED_AFTER_COVER_END")

    def test_no_payout_bucket_zero(self):
        # Curve's DNS hijack moved TVL 1.5%: even if it were covered, bucket 0.
        pid = make_pool(self.c, uw=UW2, spec=CURVE, excl="")
        cid = buy(self.c, pid, who=BOB)
        clid = file(self.c, cid, R_CURVE_DNS)
        out = judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.assertEqual(out["outcome"], "NO_PAYOUT")
        self.assertEqual(out["severity_bucket"], 0)

    def test_retry_changes_nothing(self):
        clid = file(self.c, self.cid, R_EULER)
        WEB[HACKS_URL] = (503, "")
        out = send(self.c, STRANGER, 0, "judge_claim", clid)
        self.assertTrue(ok(out))
        self.assertEqual(out["outcome"], "RETRY")
        self.assertEqual(str(self.c.claims[0].status), "FILED")
        self.assertEqual(int(self.c.claims[0].judged_at), 0)

    def test_undetermined_round_changes_nothing(self):
        clid = file(self.c, self.cid, R_EULER)
        FORGE["leader_dies"] = True
        out = send(self.c, STRANGER, 0, "judge_claim", clid)
        self.assertTrue(rejected(out))
        self.assertEqual(str(self.c.claims[0].status), "FILED")

    def test_forged_leader_refused(self):
        clid = file(self.c, self.cid, R_EULER)
        facts = self.c._claim_facts(self.c.claims[0], self.c.covers[0],
                                    self.c.pools[0], "claim")
        good = leader_payload(facts)
        bad = json.loads(json.dumps(good))
        bad["bucket"] = 1
        FORGE["payload"] = bad
        MODEL.serve_raw(_TopStrength("COVERED", "SMART_CONTRACT_BUG", "NONE"))
        out = send(self.c, STRANGER, 0, "judge_claim", clid)
        self.assertTrue(rejected(out))
        self.assertEqual(str(self.c.claims[0].status), "FILED")

    def test_validator_seeing_other_bytes_settles_nothing(self):
        clid = file(self.c, self.cid, R_EULER)
        SEQ[R_EULER] = [TEXT[R_EULER],
                        "Euler denies any flaw; the donateToReserves story is false.\n"
                        + TEXT[R_EULER]]
        MODEL.serve_raw(_TopStrength("COVERED", "SMART_CONTRACT_BUG", "NONE"))
        out = send(self.c, STRANGER, 0, "judge_claim", clid)
        self.assertTrue(rejected(out))
        self.assertEqual(str(self.c.claims[0].status), "FILED")

    def test_judge_works_while_paused(self):
        clid = file(self.c, self.cid, R_EULER)
        send(self.c, OWNER, 0, "set_paused", True)
        self.assertEqual(judge(self.c, clid)["outcome"], "APPROVED")

    def test_verify_claim(self):
        clid = file(self.c, self.cid, R_EULER)
        judge(self.c, clid)
        v = view(self.c, "verify_claim", clid)
        self.assertTrue(v["hash_matches"])
        self.assertEqual(v["gross_recomputed_wei"], v["gross_stored_wei"])
        self.assertEqual(v["bucket_from_drop"], v["severity_bucket"])

    def test_claim_view(self):
        clid = file(self.c, self.cid, R_EULER)
        judge(self.c, clid)
        v = view(self.c, "get_claim", clid)
        self.assertEqual(v["status"], "APPROVED")
        self.assertEqual(v["contestable_by"], UW.as_hex)
        self.assertEqual(v["incident_date"], "2023-03-13")

    def test_attempts_counted(self):
        clid = file(self.c, self.cid, R_EULER)
        WEB[HACKS_URL] = (503, "")
        send(self.c, STRANGER, 0, "judge_claim", clid)
        install_web()
        judge(self.c, clid)
        self.assertEqual(int(self.c.claims[0].attempts), 2)


class TestRefile(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        self.pid = make_pool(self.c)
        self.cid = buy(self.c, self.pid)
        self.clid = file(self.c, self.cid, HOME_EULER)
        RENDER[HOME_EULER] = "Euler Finance lets you lend and borrow almost anything."
        judge(self.c, self.clid)
        install_web()

    def test_inconclusive_can_be_refiled_and_then_pay(self):
        self.assertEqual(str(self.c.claims[0].status), "INCONCLUSIVE")
        out = send(self.c, ALICE, 0, "refile_claim", self.clid, "", R_EULER, "rekt")
        self.assertTrue(ok(out), out)
        self.assertEqual(judge(self.c, self.clid)["outcome"], "APPROVED")

    def test_refile_needs_a_new_url(self):
        out = send(self.c, ALICE, 0, "refile_claim", self.clid, "", HOME_EULER, "again")
        self.assertTrue(rejected(out))
        self.assertIn("new source", out["reason"])

    def test_refile_only_claimant(self):
        self.assertTrue(rejected(send(self.c, BOB, 0, "refile_claim", self.clid, "",
                                      R_EULER, "x")))

    def test_refile_allowlist(self):
        self.assertTrue(rejected(send(self.c, ALICE, 0, "refile_claim", self.clid, "",
                                      BLOG, "x")))

    def test_refile_after_deadline(self):
        advance(31 * DAY)
        self.assertTrue(rejected(send(self.c, ALICE, 0, "refile_claim", self.clid, "",
                                      R_EULER, "x")))

    def test_refile_not_from_approved(self):
        send(self.c, ALICE, 0, "refile_claim", self.clid, "", R_EULER, "x")
        judge(self.c, self.clid)
        self.assertTrue(rejected(send(self.c, ALICE, 0, "refile_claim", self.clid, "",
                                      A_EULER, "x")))

    def test_inconclusive_is_not_contestable(self):
        out = send(self.c, ALICE, GEN, "contest", self.clid, R_EULER,
                   "Something entirely new about the incident here.")
        self.assertTrue(rejected(out))
        self.assertIn("refile", out["reason"])

    def test_inconclusive_releases_after_deadline(self):
        advance(31 * DAY)
        self.assertTrue(ok(send(self.c, STRANGER, 0, "release_cover", self.cid)))


class TestSettlement(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        self.pid = make_pool(self.c, capital=10 * GEN)

    def approved(self, who, amount=GEN, pid=None):
        cid = buy(self.c, pid or self.pid, who=who, amount=amount)
        clid = file(self.c, cid, R_EULER)
        out = judge(self.c, clid)
        self.assertEqual(out["outcome"], "APPROVED", out)
        return cid, clid

    def test_finalize_pays_and_premium_earned(self):
        cid, clid = self.approved(ALICE, amount=2 * GEN)
        prem = int(self.c.covers[0].premium_wei)
        out = settle_ready(self.c, 1)
        self.assertTrue(ok(out), out)
        self.assertFalse(out["scaled"])
        want = C._gross(2 * GEN, 10000, 1000)
        self.assertEqual(int(self.c.claims[0].payout_wei), want)
        self.assertEqual(drain(self.c, ALICE), want)
        self.assertEqual(drain(self.c, UW), prem)
        self.assertEqual(str(self.c.covers[0].status), "PAID")
        self.assertEqual(int(self.c.pools[0].locked_wei), 0)
        self.assertEqual(int(self.c.pools[0].capital_wei), 10 * GEN - want)

    def test_finalize_before_window_refused(self):
        self.approved(ALICE)
        out = send(self.c, STRANGER, 0, "finalize_incident", 1)
        self.assertTrue(rejected(out))

    def test_finalize_waits_for_contest_window(self):
        c = fresh(settlement_window_s=60)
        pid = make_pool(c)
        cid = buy(c, pid)
        clid = file(c, cid, R_EULER)
        judge(c, clid)
        advance(61)
        out = send(c, STRANGER, 0, "finalize_incident", 1)
        self.assertTrue(rejected(out))
        self.assertIn("can still be contested", out["reason"])

    def test_finalize_twice(self):
        self.approved(ALICE)
        settle_ready(self.c, 1)
        self.assertTrue(rejected(send(self.c, STRANGER, 0, "finalize_incident", 1)))

    def test_finalize_works_while_paused(self):
        self.approved(ALICE)
        send(self.c, OWNER, 0, "set_paused", True)
        self.assertTrue(ok(settle_ready(self.c, 1)))

    def test_two_claims_same_incident_same_batch(self):
        self.approved(ALICE)
        self.approved(BOB)
        self.assertEqual(int(self.c.claims[0].batch_id), int(self.c.claims[1].batch_id))
        out = settle_ready(self.c, 1)
        self.assertEqual(out["claims_paid"], 2)

    def test_late_claim_opens_new_batch(self):
        self.approved(ALICE)
        settle_ready(self.c, 1)
        self.approved(BOB)
        self.assertEqual(int(self.c.claims[1].batch_id), 2)

    def test_prorata_when_short(self):
        pid = make_pool(self.c, uw=UW2, capital=GEN, coll=5000, max_cover=GEN)
        self.approved(ALICE, amount=GEN, pid=pid)
        self.approved(BOB, amount=GEN, pid=pid)
        out = settle_ready(self.c, 1)
        self.assertTrue(out["scaled"])
        gross = C._gross(GEN, 10000, 1000)
        pays, dust = C._prorata([gross, gross], GEN)
        self.assertEqual(int(self.c.claims[0].payout_wei), pays[0])
        self.assertEqual(int(self.c.claims[1].payout_wei), pays[1])
        self.assertEqual(pays[0], pays[1])
        self.assertEqual(int(self.c.pools[pid - 1].capital_wei), dust)

    def test_batch_view(self):
        self.approved(ALICE)
        b = view(self.c, "get_batch", 1)
        self.assertEqual(b["status"], "OPEN")
        self.assertEqual(b["claim_ids"], [1])
        self.assertEqual(b["incident_date"], "2023-03-13")

    def test_claim_payout_owed_nothing(self):
        self.assertTrue(rejected(send(self.c, NOBODY, 0, "claim_payout")))

    def test_transfers_recorded(self):
        self.approved(ALICE)
        settle_ready(self.c, 1)
        paid = drain(self.c, ALICE)
        self.assertIn((ALICE.as_hex, paid), TRANSFERS)


class TestContest(unittest.TestCase):
    GROUNDS = ("Euler's own post-mortem is a new source that states the root "
               "cause in the project's own words.")

    def setUp(self):
        self.c = fresh(contest_bond_wei=GEN // 10)
        self.pid = make_pool(self.c)
        self.cid = buy(self.c, self.pid)
        self.clid = file(self.c, self.cid, R_EULER, statement="Euler was drained.")
        judge(self.c, self.clid)

    def contest(self, who=UW, urls=PM_EULER, grounds=None, value=GEN // 10):
        return send(self.c, who, value, "contest", self.clid, urls,
                    grounds if grounds is not None else self.GROUNDS)

    def test_underwriter_contests_approved(self):
        out = self.contest()
        self.assertTrue(ok(out), out)
        self.assertEqual(str(self.c.claims[0].contest_status), "PENDING")
        self.assertEqual(int(self.c.claims[0].contest_bond_wei), GEN // 10)

    def test_only_losing_side(self):
        self.assertTrue(rejected(self.contest(who=ALICE)))
        self.assertTrue(rejected(self.contest(who=STRANGER)))

    def test_bond_required(self):
        out = self.contest(value=GEN // 10 - 1)
        self.assertTrue(rejected(out))
        self.assertEqual(int(self.c.payout_wei.get(UW)), GEN // 10 - 1)

    def test_window(self):
        advance(49 * HOUR)
        self.assertTrue(rejected(self.contest()))

    def test_reused_url_refused(self):
        out = self.contest(urls=R_EULER)
        self.assertTrue(rejected(out))
        self.assertIn("already judged", out["reason"])

    def test_grounds_verbatim_refused(self):
        out = self.contest(grounds="Euler was drained.")
        self.assertTrue(rejected(out))
        self.assertIn("add nothing", out["reason"])

    def test_grounds_copied_from_digest_refused(self):
        digest = str(self.c.claims[0].digest)
        first = C._sentences(digest)[2][0]
        out = self.contest(grounds=first + " " + first)
        self.assertTrue(rejected(out), out)

    def test_grounds_repunctuated_refused(self):
        digest = str(self.c.claims[0].digest)
        s = C._sentences(digest)[2][1]
        out = self.contest(grounds=s.upper() + "!!!")
        self.assertTrue(rejected(out))

    def test_allowlist_applies(self):
        self.assertTrue(rejected(self.contest(urls=BLOG)))

    def test_one_contest_per_claim(self):
        self.contest()
        out = self.contest(urls=A_EULER)
        self.assertTrue(rejected(out))

    def test_held_bond_to_buyer(self):
        self.contest()
        MODEL.serve_raw(_TopStrength("COVERED", "SMART_CONTRACT_BUG", "NONE"))
        out = send(self.c, STRANGER, 0, "judge_contest", self.clid)
        self.assertEqual(out["contest"], "UPHELD", out)
        self.assertEqual(out["bond_to"], ALICE.as_hex)
        self.assertEqual(int(self.c.payout_wei.get(ALICE)), GEN // 10)
        self.assertEqual(str(self.c.claims[0].status), "APPROVED")

    def test_flip_bond_back_and_claim_denied(self):
        self.contest()
        MODEL.serve_raw(_TopStrength("INCONCLUSIVE", "NONE", "NONE"))
        out = send(self.c, STRANGER, 0, "judge_contest", self.clid)
        self.assertEqual(out["contest"], "FLIPPED", out)
        self.assertEqual(out["outcome"], "INCONCLUSIVE")
        self.assertEqual(int(self.c.payout_wei.get(UW)), GEN // 10)
        # The batch no longer pays it.
        out = settle_ready(self.c, 1)
        self.assertEqual(out["claims_paid"], 0)

    def test_not_novel_holds(self):
        # A new URL whose text is only the judged article again.
        send(self.c, UW, GEN // 10, "contest", self.clid, A_EULER, self.GROUNDS)
        RENDER[A_EULER] = TEXT[R_EULER]
        calls = MODEL.calls
        out = send(self.c, STRANGER, 0, "judge_contest", self.clid)
        self.assertEqual(out["contest"], "NOT_NOVEL", out)
        self.assertEqual(MODEL.calls, calls)
        self.assertEqual(out["bond_to"], ALICE.as_hex)

    def test_buyer_contest_that_cannot_pay_is_upheld(self):
        """Curve's DNS week moved TVL 1.5%: bucket 0. Even a re-reading as
        COVERED pays nothing, so the outcome did not cross the paying line and
        the bond goes to the underwriter."""
        pid = make_pool(self.c, uw=UW2, spec=CURVE)
        cid = buy(self.c, pid, who=BOB)
        clid = file(self.c, cid, R_CURVE_DNS)
        judge(self.c, clid, "EXCLUDED", "NONE", "FRONTEND_HIJACK")
        arch = "https://web.archive.org/web/2023/https://rekt.news/curve-finance-rekt"
        out = send(self.c, BOB, GEN // 10, "contest", clid, arch,
                   "The archived article shows the root cause differently.")
        self.assertTrue(ok(out), out)
        RENDER[arch] = ("On August 9, 2022 Curve later confirmed an oracle flaw "
                        "in its own contracts drained pools that same day.")
        MODEL.serve_raw(_TopStrength("COVERED", "ORACLE_MANIPULATION", "NONE"))
        out = send(self.c, STRANGER, 0, "judge_contest", clid)
        self.assertEqual(out["contest"], "UPHELD", out)
        self.assertEqual(out["rejudged_as"], "NO_PAYOUT")
        self.assertEqual(out["bond_to"], UW2.as_hex)

    def test_buyer_contests_denial_and_flips(self):
        pid = make_pool(self.c, uw=UW2, spec=MULTI)
        cid = buy(self.c, pid, who=BOB)
        clid = file(self.c, cid, R_MULTI)
        out = judge(self.c, clid, "EXCLUDED", "NONE", "USER_KEY_COMPROMISE")
        self.assertEqual(out["outcome"], "DENIED_EXCLUDED")
        url = "https://multichain.org/post-mortem"
        RENDER[url] = ("July 7, 2023. Multichain's post-mortem: the bridge router contract "
                       "had a message verification flaw that let the attacker "
                       "forge withdrawals across chains.")
        out = send(self.c, BOB, GEN // 10, "contest", clid, url,
                   "The project's own post-mortem names a bridge verification flaw.")
        self.assertTrue(ok(out), out)
        MODEL.serve_raw(_TopStrength("COVERED", "BRIDGE_COMPROMISE", "NONE"))
        out = send(self.c, STRANGER, 0, "judge_contest", clid)
        self.assertEqual(out["contest"], "FLIPPED", out)
        self.assertEqual(out["outcome"], "APPROVED")
        self.assertEqual(out["bond_to"], BOB.as_hex)
        cl = self.c.claims[clid - 1]
        self.assertEqual(int(cl.gross_wei), C._gross(GEN, 7500, 1000))
        self.assertGreater(int(cl.batch_id), 0)
        out = settle_ready(self.c, int(cl.batch_id))
        self.assertTrue(ok(out), out)
        self.assertEqual(int(cl.payout_wei), C._gross(GEN, 7500, 1000))

    def test_judge_contest_without_contest(self):
        self.assertTrue(rejected(send(self.c, STRANGER, 0, "judge_contest", self.clid)))

    def test_contest_retry_keeps_pending(self):
        self.contest()
        WEB[HACKS_URL] = (503, "")
        out = send(self.c, STRANGER, 0, "judge_contest", self.clid)
        self.assertEqual(out["outcome"], "RETRY")
        self.assertEqual(str(self.c.claims[0].contest_status), "PENDING")

    def test_finalize_blocked_by_open_contest(self):
        self.contest()
        out = settle_ready(self.c, 1)
        self.assertTrue(rejected(out))
        self.assertIn("under contest", out["reason"])

    def test_contest_works_while_paused(self):
        send(self.c, OWNER, 0, "set_paused", True)
        self.assertTrue(ok(self.contest()))


class TestStalled(unittest.TestCase):
    def setUp(self):
        self.c = fresh(stall_ttl_s=HOUR)
        self.pid = make_pool(self.c)
        self.cid = buy(self.c, self.pid)
        self.clid = file(self.c, self.cid, R_EULER)

    def test_not_stalled_yet(self):
        out = send(self.c, STRANGER, 0, "settle_stalled", self.clid)
        self.assertTrue(rejected(out))
        self.assertIn("not been stuck long enough", out["reason"])

    def test_filed_claim_stalls_back_to_filed_while_paused(self):
        send(self.c, OWNER, 0, "set_paused", True)
        advance(HOUR + 1)
        out = send(self.c, NOBODY, 0, "settle_stalled", self.clid)
        self.assertTrue(ok(out), out)
        cl = self.c.claims[0]
        self.assertEqual(str(cl.status), "FILED")
        self.assertEqual(int(cl.stalls), 1)
        self.assertEqual(int(self.c.balance_wei), int(self.c.held_wei) + int(self.c.payable_wei))

    def test_stall_lets_claimant_replace_evidence(self):
        advance(HOUR + 1)
        send(self.c, STRANGER, 0, "settle_stalled", self.clid)
        out = send(self.c, ALICE, 0, "refile_claim", self.clid, "", A_EULER, "mirror")
        self.assertTrue(ok(out), out)
        self.assertEqual(judge(self.c, self.clid)["outcome"], "APPROVED")

    def test_stall_extends_refile_past_deadline(self):
        advance(30 * DAY - 10)
        advance(HOUR + 20)
        out = send(self.c, STRANGER, 0, "settle_stalled", self.clid)
        self.assertTrue(ok(out))
        self.assertGreater(int(out["refile_until"]), int(self.c.covers[0].claim_deadline))
        self.assertTrue(ok(send(self.c, ALICE, 0, "refile_claim", self.clid, "",
                                A_EULER, "x")))

    def test_judging_marker_stall(self):
        cl = self.c.claims[0]
        cl.status = "JUDGING"
        cl.judging_since = NOW
        self.assertTrue(rejected(send(self.c, STRANGER, 0, "judge_claim", self.clid)))
        advance(HOUR + 1)
        self.assertTrue(ok(send(self.c, STRANGER, 0, "settle_stalled", self.clid)))
        self.assertEqual(str(cl.status), "FILED")

    def test_judged_claim_is_not_stuck(self):
        judge(self.c, self.clid)
        advance(2 * HOUR)
        self.assertTrue(rejected(send(self.c, STRANGER, 0, "settle_stalled", self.clid)))

    def test_stalled_contest_returns_bond(self):
        judge(self.c, self.clid)
        send(self.c, UW, int(self.c.contest_bond_wei), "contest", self.clid,
             PM_EULER, TestContest.GROUNDS)
        send(self.c, OWNER, 0, "set_paused", True)
        advance(HOUR + 1)
        out = send(self.c, STRANGER, 0, "settle_stalled", self.clid)
        self.assertTrue(ok(out), out)
        self.assertEqual(out["settled"], "CONTEST")
        self.assertEqual(int(self.c.payout_wei.get(UW)), int(self.c.contest_bond_wei))
        self.assertEqual(str(self.c.claims[0].status), "APPROVED")
        self.assertTrue(ok(settle_ready(self.c, 1)))

    def test_unknown_claim(self):
        self.assertTrue(rejected(send(self.c, STRANGER, 0, "settle_stalled", 99)))


class TestPauseMatrix(unittest.TestCase):
    """RULE 6: pause gates new business and NOTHING ELSE. Every other write is
    driven while paused and must succeed."""

    def test_owner_only(self):
        c = fresh()
        self.assertTrue(rejected(send(c, STRANGER, 0, "set_paused", True)))
        self.assertTrue(ok(send(c, OWNER, 0, "set_paused", "true")))
        self.assertTrue(bool(c.paused))

    def test_full_lifecycle_while_paused(self):
        c = fresh(contest_bond_wei=GEN // 10)
        pid = make_pool(c)
        a = buy(c, pid, who=ALICE)
        b = buy(c, pid, who=BOB, amount=GEN, days=1)
        send(c, OWNER, 0, "set_paused", True)
        clid = file(c, a, R_EULER)
        self.assertEqual(judge(c, clid)["outcome"], "APPROVED")
        self.assertTrue(ok(send(c, UW, GEN // 10, "contest", clid, PM_EULER,
                                TestContest.GROUNDS)))
        MODEL.serve_raw(_TopStrength("COVERED", "SMART_CONTRACT_BUG", "NONE"))
        self.assertTrue(ok(send(c, STRANGER, 0, "judge_contest", clid)))
        self.assertTrue(ok(settle_ready(c, 1)))
        advance(31 * DAY)
        self.assertTrue(ok(send(c, STRANGER, 0, "release_cover", b)))
        self.assertTrue(ok(send(c, UW, 0, "close_pool", pid)))
        for who in (ALICE, BOB, UW):
            drain(c, who)
        self.assertEqual(int(c.balance_wei), 0)

    def test_transfer_ownership(self):
        c = fresh()
        self.assertTrue(rejected(send(c, STRANGER, 0, "transfer_ownership", ALICE.as_hex)))
        self.assertTrue(rejected(send(c, OWNER, 0, "transfer_ownership", "nope")))
        self.assertTrue(ok(send(c, OWNER, 0, "transfer_ownership", ALICE.as_hex)))
        self.assertEqual(c.owner, ALICE)

    def test_owner_has_no_money_power(self):
        c = fresh()
        pid = make_pool(c)
        buy(c, pid)
        for m, args in (("withdraw_capacity", (pid, GEN)), ("close_pool", (pid,))):
            self.assertTrue(rejected(send(c, OWNER, 0, m, *args)))


# ===========================================================================
# 7. THE LOOPHOLES, one class each
# ===========================================================================


class TestLoophole01_BuyingAfterAnIncidentIsBackdated(unittest.TestCase):
    """Buying cover after an incident is public -> REJECTED_BACKDATED, and the
    premium is not refunded: the cover was valid, the incident predates it."""

    def setUp(self):
        # Waiting 0 so the claim can be FILED today; the incident (2023) still
        # predates the cover's start (today), which is the whole point.
        self.c = fresh(demo=False)
        self.pid = make_pool(self.c, wait=0)

    def test_canonical_rejects_historical_incident(self):
        # REFUSED AT FILING, before any source is fetched or model asked: the
        # key names Euler's 2023 record, which predates a cover bought today.
        cid = buy(self.c, self.pid, days=30)
        out = send(self.c, ALICE, 0, "file_claim", cid, K_EULER, R_EULER, "x")
        self.assertTrue(rejected(out))
        self.assertIn("predates this cover's start", out["reason"])
        self.assertEqual(len(self.c.claims), 0)
        self.assertEqual(int(self.c.covers[0].claim_id), 0)
        self.assertEqual(CALLS, [])
        self.assertEqual(MODEL.calls, 0)

    def test_premium_not_refunded(self):
        cid = buy(self.c, self.pid, days=30)
        prem = int(self.c.covers[0].premium_wei)
        send(self.c, ALICE, 0, "file_claim", cid, K_EULER, R_EULER, "x")
        advance(61 * DAY)
        self.assertTrue(ok(send(self.c, STRANGER, 0, "release_cover", cid)))
        self.assertEqual(int(self.c.payout_wei.get(UW)), prem)
        self.assertEqual(int(self.c.payout_wei.get(ALICE) or 0), 0)

    def test_incident_inside_waiting_period_is_backdated(self):
        # A demo cover starting 3 days before Euler, waiting 7: refused.
        c = fresh(demo_backdate_days=(NOW - epoch("2023-03-10T00:00:00Z")) // DAY + 1)
        pid = make_pool(c)
        cid = buy(c, pid)
        out = send(c, ALICE, 0, "file_claim", cid, K_EULER, R_EULER, "x")
        self.assertTrue(rejected(out))
        self.assertIn("waiting period", out["reason"])
        self.assertEqual(MODEL.calls, 0)

    def test_same_bytes_demo_pays(self):
        c = fresh(demo=True)
        pid = make_pool(c)
        cid = buy(c, pid)
        clid = file(c, cid, R_EULER)
        self.assertEqual(judge(c, clid)["outcome"], "APPROVED")

    def test_a_key_cannot_move_an_incident_into_the_cover(self):
        # The date is DATA from DeFi Llama. Typing an in-window date for
        # Euler's exploit names no record: nothing is judged, nothing pays.
        cid = buy(self.c, self.pid, days=30)
        advance(DAY)
        clid = file(self.c, cid, R_EULER, key=live_key("1183"))
        out = judge(self.c, clid)
        self.assertEqual(out["outcome"], "INCONCLUSIVE")
        self.assertFalse(out["model_called"])
        self.assertEqual(MODEL.calls, 0)
        self.assertIn("no DeFi Llama incident record matches", str(self.c.claims[0].pinned))
        c = fresh(demo=True)
        pid = make_pool(c)
        clid = file(c, buy(c, pid), R_EULER, key="1183:2023-03-20")
        out = judge(c, clid)
        self.assertEqual(out["outcome"], "INCONCLUSIVE")
        self.assertEqual(int(c.claims[0].gross_wei), 0)


class TestLoophole02_FakeEvidenceRefusedBeforeGenLayer(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        self.pid = make_pool(self.c)
        self.cid = buy(self.c, self.pid)

    def attempt(self, urls):
        del CALLS[:]
        calls = MODEL.calls
        out = send(self.c, ALICE, 0, "file_claim", self.cid, K_EULER, urls, "x")
        self.assertTrue(rejected(out), urls)
        self.assertEqual(CALLS, [])
        self.assertEqual(MODEL.calls, calls)
        self.assertEqual(len(self.c.claims), 0)

    def test_random_blog(self):
        self.attempt(BLOG)

    def test_lookalike_domain(self):
        self.attempt("https://rekt.news.blog/euler")
        self.attempt("https://evilrekt.news/euler")

    def test_userinfo_trick(self):
        self.attempt("https://rekt.news@someguy.substack.com/p/x")

    def test_archived_blog(self):
        self.attempt("https://web.archive.org/web/2024/" + BLOG)

    def test_http(self):
        self.attempt("http://rekt.news/euler-rekt")

    def test_mixed_list(self):
        self.attempt(R_EULER + " " + BLOG)

    def test_llama_api(self):
        self.attempt("https://api.llama.fi/hacks")

    def test_frozen_domains_not_later_ones(self):
        # The pool froze euler.finance; curve.finance is not on it.
        self.attempt("https://news.curve.finance/euler")


class TestLoophole03_CapacityLockedBeforeClaims(unittest.TestCase):
    def test_underwriter_cannot_drain_locked_capital(self):
        c = fresh()
        pid = make_pool(c, capital=5 * GEN, max_cover=5 * GEN)
        cid = buy(c, pid, amount=4 * GEN)
        out = send(c, UW, 0, "withdraw_capacity", pid, 2 * GEN)
        self.assertTrue(rejected(out))
        self.assertIn("locked against live covers", out["reason"])
        self.assertTrue(ok(send(c, UW, 0, "withdraw_capacity", pid, GEN)))
        clid = file(c, cid, R_EULER)
        judge(c, clid)
        out = settle_ready(c, 1)
        self.assertEqual(int(c.claims[0].payout_wei), C._gross(4 * GEN, 10000, 1000))

    def test_cannot_close_ahead_of_claim(self):
        c = fresh()
        pid = make_pool(c)
        buy(c, pid)
        self.assertTrue(rejected(send(c, UW, 0, "close_pool", pid)))

    def test_lock_holds_through_claim_window(self):
        c = fresh(demo=False)
        pid = make_pool(c, capital=GEN, max_cover=GEN)
        buy(c, pid, amount=GEN, days=1)
        advance(2 * DAY)       # cover ended, claim window still open
        self.assertTrue(rejected(send(c, UW, 0, "withdraw_capacity", pid, 1)))
        advance(30 * DAY)
        send(c, STRANGER, 0, "release_cover", 1)
        self.assertTrue(ok(send(c, UW, 0, "withdraw_capacity", pid, GEN)))


class TestLoophole04_OneClaimPerCover(unittest.TestCase):
    def test_second_claim_refused(self):
        c = fresh()
        pid = make_pool(c)
        cid = buy(c, pid)
        file(c, cid, R_EULER)
        out = send(c, ALICE, 0, "file_claim", cid, K_EULER, A_EULER, "again")
        self.assertTrue(rejected(out))
        self.assertIn("one claim per cover", out["reason"])

    def test_second_claim_refused_after_payout(self):
        c = fresh()
        pid = make_pool(c)
        cid = buy(c, pid)
        clid = file(c, cid, R_EULER)
        judge(c, clid)
        settle_ready(c, 1)
        self.assertTrue(rejected(send(c, ALICE, 0, "file_claim", cid, K_EULER, A_EULER, "x")))

    def test_second_claim_refused_after_denial(self):
        c = fresh()
        pid = make_pool(c, spec=CURVE)
        cid = buy(c, pid)
        clid = file(c, cid, R_CURVE_DNS)
        judge(c, clid, "EXCLUDED", "NONE", "FRONTEND_HIJACK")
        self.assertTrue(rejected(send(c, ALICE, 0, "file_claim", cid, K_EULER, R_EULER, "x")))

    def test_same_incident_twice_through_two_covers_is_two_covers(self):
        """Two covers are two premiums and two locks - that is not a double
        claim, and each pays its own cover amount."""
        c = fresh()
        pid = make_pool(c)
        a = buy(c, pid, amount=GEN)
        advance(60)
        b = buy(c, pid, amount=GEN)
        for cid in (a, b):
            judge(c, file(c, cid, R_EULER))
        out = settle_ready(c, 1)
        self.assertEqual(out["claims_paid"], 2)


class TestLoophole05_ProRataNotFirstCome(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        self.pid = make_pool(self.c, capital=GEN, coll=5000, max_cover=GEN)

    def test_both_scaled_equally(self):
        a = buy(self.c, self.pid, who=ALICE, amount=GEN)
        b = buy(self.c, self.pid, who=BOB, amount=GEN)
        ca = file(self.c, a, R_EULER)
        cb = file(self.c, b, R_EULER)
        judge(self.c, ca)
        advance(3600)
        judge(self.c, cb)
        out = settle_ready(self.c, 1)
        self.assertTrue(out["scaled"])
        pa = int(self.c.claims[0].payout_wei)
        pb = int(self.c.claims[1].payout_wei)
        self.assertEqual(pa, pb)
        self.assertLess(pa, C._gross(GEN, 10000, 1000))
        self.assertLessEqual(pa + pb, GEN)

    def test_order_does_not_matter(self):
        for first in (0, 1):
            c = fresh()
            pid = make_pool(c, capital=GEN, coll=5000, max_cover=2 * GEN)
            a = buy(c, pid, who=ALICE, amount=GEN)
            b = buy(c, pid, who=BOB, amount=GEN)
            ids = [file(c, a, R_EULER), file(c, b, R_EULER)]
            if first:
                ids.reverse()
            for i in ids:
                judge(c, i)
            settle_ready(c, 1)
            self.assertEqual(int(c.claims[0].payout_wei), int(c.claims[1].payout_wei))

    def test_unequal_covers_scale_by_same_factor(self):
        c = fresh()
        pid = make_pool(c, capital=GEN, coll=4000, max_cover=2 * GEN)
        a = buy(c, pid, who=ALICE, amount=GEN // 2)
        b = buy(c, pid, who=BOB, amount=2 * GEN)
        judge(c, file(c, a, R_EULER))
        judge(c, file(c, b, R_EULER))
        settle_ready(c, 1)
        pa = int(c.claims[0].payout_wei)
        pb = int(c.claims[1].payout_wei)
        self.assertAlmostEqual(pb / pa, 4.0, places=6)

    def test_dust_goes_to_underwriter(self):
        a = buy(self.c, self.pid, who=ALICE, amount=GEN)
        b = buy(self.c, self.pid, who=BOB, amount=GEN)
        judge(self.c, file(self.c, a, R_EULER))
        judge(self.c, file(self.c, b, R_EULER))
        out = settle_ready(self.c, 1)
        send(self.c, UW, 0, "close_pool", self.pid)
        paid = int(out["paid_total_wei"])
        self.assertEqual(int(self.c.pools[0].capital_wei), 0)
        self.assertEqual(int(self.c.payout_wei.get(UW)), GEN - paid
                         + int(self.c.covers[0].premium_wei)
                         + int(self.c.covers[1].premium_wei))


class TestLoophole06_EvidenceEditedAfterJudging(unittest.TestCase):
    def test_stored_hash_is_what_was_judged(self):
        c = fresh()
        pid = make_pool(c)
        cid = buy(c, pid)
        clid = file(c, cid, R_EULER)
        judge(c, clid)
        judged = str(c.claims[0].content_hash)
        # The page is edited afterwards...
        RENDER[R_EULER] = ("Euler says it was phishing all along and no code "
                           "flaw existed.\n" + TEXT[R_EULER])
        v = view(c, "verify_claim", clid)
        self.assertTrue(v["hash_matches"])
        self.assertEqual(v["content_hash"], judged)
        # ... and a re-read of the edited page would hash differently.
        facts = c._claim_facts(c.claims[0], c.covers[0], c.pools[0], "claim")
        raw = C._read_sources(facts)
        self.assertNotEqual(C._reading(facts, raw)["content_hash"], judged)

    def test_contest_rereads_stored_digest_not_edited_page(self):
        c = fresh()
        pid = make_pool(c)
        cid = buy(c, pid)
        clid = file(c, cid, R_EULER)
        judge(c, clid)
        RENDER[R_EULER] = "Euler was phished; the private key was compromised.\n"
        send(c, UW, int(c.contest_bond_wei), "contest", clid, PM_EULER,
             TestContest.GROUNDS)
        MODEL.serve_raw(_TopStrength("COVERED", "SMART_CONTRACT_BUG", "NONE"))
        send(c, STRANGER, 0, "judge_contest", clid)
        # The prompt carried the judged digest, not the edited page.
        self.assertNotIn("private key was compromised", MODEL.log[-1])
        self.assertIn("donateToReserves", MODEL.log[-1])

    def test_tampered_storage_detected(self):
        c = fresh()
        pid = make_pool(c)
        clid = file(c, buy(c, pid), R_EULER)
        judge(c, clid)
        c.claims[0].digest = str(c.claims[0].digest) + " forged"
        self.assertFalse(view(c, "verify_claim", clid)["hash_matches"])


class TestLoophole07_ContestCopyingOldEvidence(unittest.TestCase):
    def setUp(self):
        self.c = fresh()
        self.pid = make_pool(self.c)
        self.clid = file(self.c, buy(self.c, self.pid), R_EULER,
                         statement="Euler was drained by an exploit.")
        judge(self.c, self.clid)
        self.bond = int(self.c.contest_bond_wei)

    def test_same_url(self):
        self.assertTrue(rejected(send(self.c, UW, self.bond, "contest", self.clid,
                                      R_EULER, TestContest.GROUNDS)))

    def test_same_url_different_case_and_slash(self):
        self.assertTrue(rejected(send(self.c, UW, self.bond, "contest", self.clid,
                                      "https://REKT.news/euler-rekt/",
                                      TestContest.GROUNDS)))

    def test_grounds_verbatim_statement(self):
        self.assertTrue(rejected(send(self.c, UW, self.bond, "contest", self.clid,
                                      PM_EULER, "Euler was drained by an exploit.")))

    def test_grounds_repunctuated(self):
        self.assertTrue(rejected(send(self.c, UW, self.bond, "contest", self.clid,
                                      PM_EULER, "EULER -- was drained, by an EXPLOIT!!")))

    def test_grounds_repeated(self):
        self.assertTrue(rejected(send(self.c, UW, self.bond, "contest", self.clid,
                                      PM_EULER, "Euler was drained by an exploit. " * 5)))

    def test_refused_contest_takes_no_bond(self):
        send(self.c, UW, self.bond, "contest", self.clid, R_EULER, TestContest.GROUNDS)
        self.assertEqual(int(self.c.payout_wei.get(UW)), self.bond)
        self.assertEqual(str(self.c.claims[0].contest_status), "")

    def test_new_url_same_text_is_not_novel_inside_consensus(self):
        send(self.c, UW, self.bond, "contest", self.clid, A_EULER, TestContest.GROUNDS)
        RENDER[A_EULER] = TEXT[R_EULER]
        out = send(self.c, STRANGER, 0, "judge_contest", self.clid)
        self.assertEqual(out["contest"], "NOT_NOVEL")
        self.assertEqual(str(self.c.claims[0].status), "APPROVED")


class TestLoophole08_OtherProtocolsIncident(unittest.TestCase):
    def test_protocol_b_evidence_on_protocol_a_cover(self):
        c = fresh()
        pid = make_pool(c, spec=EULER)
        clid = file(c, buy(c, pid), R_MULTI)
        calls = MODEL.calls
        out = judge(c, clid, "COVERED", "BRIDGE_COMPROMISE")
        self.assertEqual(out["outcome"], "EVIDENCE_MISMATCH")
        self.assertFalse(out["protocol_match"])
        self.assertEqual(MODEL.calls, calls)

    def test_mention_of_a_in_b_article_uses_a_record(self):
        """Euler's rekt article mentions Tornado Cash. A Tornado Cash cover
        claimed with it reads TORNADO's record (2023-05-20), not Euler's."""
        c = fresh()
        pid = make_pool(c, spec=TORNADO)
        clid = file(c, buy(c, pid), "https://rekt.news/euler-rekt")
        out = judge(c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.assertEqual(out["incident_date"], "2023-05-20")
        # ...and Euler's article, dated March, is not about that record.
        self.assertEqual(out["outcome"], "EVIDENCE_MISMATCH")

    def test_id_mismatch_pool_cannot_pay(self):
        c = fresh()
        pid = make_pool(c, spec=dict(EULER, slug="multichain"))
        clid = file(c, buy(c, pid), R_EULER)
        out = judge(c, clid)
        self.assertEqual(out["outcome"], "INCONCLUSIVE")
        self.assertIn("different protocols", str(c.claims[0].pinned))

    def test_unknown_protocol_cannot_pay(self):
        c = fresh()
        pid = make_pool(c, spec=dict(EULER, lid="999999"))
        clid = file(c, buy(c, pid), R_EULER)
        self.assertEqual(judge(c, clid)["outcome"], "INCONCLUSIVE")


class TestOneEventBindsEverything(unittest.TestCase):
    """THE STEWARD'S FINDING. A protocol with two incident records inside one
    cover - Curve: the DNS hijack of 2022-08-09 (excluded, FRONTEND_HIJACK)
    and the Vyper reentrancy of 2023-07-30 (covered, SMART_CONTRACT_BUG).
    Evidence, the selected record and the TVL window must be ONE event."""

    def setUp(self):
        self.c = fresh()
        # perils without BRIDGE; every exclusion
        self.pid = make_pool(self.c, uw=UW, spec=CURVE,
                             perils="SMART_CONTRACT_BUG,ORACLE_MANIPULATION,ECONOMIC_EXPLOIT")

    def claim(self, key, urls, who=ALICE):
        cid = buy(self.c, self.pid, who=who, amount=GEN // 2)
        advance(MIN)
        return file(self.c, cid, urls, key=key)

    # a.
    def test_a_matching_evidence_selects_the_intended_event(self):
        clid = self.claim(K_VYPER, R_VYPER)
        out = judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.assertEqual(out["outcome"], "APPROVED")
        self.assertEqual(out["event_match"], "SAME")
        self.assertEqual(out["incident_date"], "2023-07-30")
        self.assertEqual(out["severity_bucket"], 2)          # Vyper's window
        self.assertEqual(out["drop_bps"], 4952)
        k = self.c.claims[clid - 1]
        self.assertIn("anchor 2023-07-30 ", str(k.tvl_line))
        self.assertIn("Vyper Compiler Bug", str(k.llama_line))
        self.assertIn("rekt.news/curve-vyper-rekt BOUND 2023-07-31", str(k.bind_line))
        self.assertEqual(int(k.gross_wei), C._gross(GEN // 2, 5000, 1000))

    def test_a_other_event_matching_is_excluded_at_its_own_severity(self):
        clid = self.claim(K_DNS, R_CURVE_DNS)
        out = judge(self.c, clid, "EXCLUDED", "NONE", "FRONTEND_HIJACK")
        self.assertEqual(out["outcome"], "DENIED_EXCLUDED")
        self.assertEqual(out["incident_date"], "2022-08-09")
        self.assertEqual(out["severity_bucket"], 0)          # DNS's window

    # b.
    def test_b_evidence_A_with_record_B_is_mismatch(self):
        clid = self.claim(K_DNS, R_VYPER)
        out = judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.assertEqual(out["outcome"], "EVIDENCE_MISMATCH")
        self.assertEqual(out["event_match"], "DIFFERENT")
        self.assertFalse(out["model_called"])
        self.assertEqual(MODEL.calls, 0)
        self.nothing_moved(clid)

    # c.
    def test_c_evidence_B_with_record_A_is_mismatch(self):
        clid = self.claim(K_VYPER, R_CURVE_DNS)
        out = judge(self.c, clid, "EXCLUDED", "NONE", "FRONTEND_HIJACK")
        self.assertEqual(out["outcome"], "EVIDENCE_MISMATCH")
        self.assertFalse(out["model_called"])
        self.nothing_moved(clid)

    def test_c_model_different_is_mismatch_even_when_dates_bind(self):
        # A bound page, but the validators read it as another event.
        clid = self.claim(K_VYPER, R_VYPER)
        out = judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.c2 = fresh()
        for ev in ("DIFFERENT", "UNCLEAR"):
            c = fresh()
            pid = make_pool(c, spec=CURVE)
            cid = buy(c, pid, amount=GEN // 2)
            k = file(c, cid, R_VYPER, key=K_VYPER)
            MODEL.serve_raw(_TopStrength("COVERED", "SMART_CONTRACT_BUG", "NONE", ev))
            got = send(c, STRANGER, 0, "judge_claim", k)
            self.assertEqual(got["outcome"], "EVIDENCE_MISMATCH", ev)
            self.assertTrue(got["model_called"])
            self.assertEqual(got["event_match"], ev)
            self.assertEqual(int(c.claims[0].gross_wei), 0)
        self.assertEqual(out["outcome"], "APPROVED")

    def test_mixed_evidence_reads_only_the_bound_page(self):
        # Vyper + DNS pages on the Vyper record: the DNS page is UNBOUND and
        # contributes no sentence - so FRONTEND_HIJACK is not in the bracket.
        clid = self.claim(K_VYPER, R_VYPER + " " + R_CURVE_DNS)
        out = judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.assertEqual(out["outcome"], "APPROVED")
        k = self.c.claims[clid - 1]
        self.assertIn("rekt.news/curve-finance-rekt UNBOUND", str(k.bind_line))
        self.assertNotIn("FRONTEND_HIJACK", str(k.bracket))
        self.assertNotIn("DNS", str(k.digest))

    def test_undated_evidence_cannot_pay(self):
        clid = self.claim(K_VYPER, "https://curve.finance/pm")
        RENDER["https://curve.finance/pm"] = (
            "Curve pools were drained because of a reentrancy bug in the Vyper "
            "compiler that broke the nonreentrant lock on several pools.")
        out = judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.assertEqual(out["outcome"], "EVIDENCE_MISMATCH")
        self.assertEqual(out["event_match"], "UNCLEAR")
        self.assertEqual(MODEL.calls, 0)

    def nothing_moved(self, clid):
        k = self.c.claims[clid - 1]
        self.assertEqual(int(k.gross_wei), 0)
        self.assertEqual(int(k.batch_id), 0)
        self.assertEqual(int(k.payout_wei), 0)
        self.assertEqual(len(self.c.batches), 0)
        self.assertEqual(int(self.c.payout_wei.get(ALICE) or 0), 0)
        # the claim is not consumed: it can come back
        self.assertEqual(str(k.status), "EVIDENCE_MISMATCH")
        self.assertGreater(int(k.refile_until), 0)

    # d.
    def test_d_feed_order_does_not_change_the_record(self):
        rows = json.loads(HACKS)
        # A THIRD Curve row inside the cover, later than DNS and earlier than
        # Vyper: the old "latest in window" rule would have been moved by it.
        rows.append({"name": "Curve DEX", "date": epoch("2023-01-15T00:00:00Z"),
                     "defillamaId": "3", "classification": "Oracle Manipulation",
                     "technique": "Spot Price", "amount": 10})
        hashes = set()
        for seed in range(6):
            random.Random(seed).shuffle(rows)
            facts = euler_facts(protocol_name="Curve", llama_slug="curve-dex",
                                llama_id="3", urls=[R_VYPER], key=K_VYPER)
            install_web()
            WEB[HACKS_URL] = (200, json.dumps(rows))
            r = C._reading(facts, C._read_sources(facts))
            self.assertEqual(C._date_text(r["incident_day"]), "2023-07-30")
            self.assertEqual(r["bucket"], 2)
            hashes.add(r["content_hash"])
        self.assertEqual(len(hashes), 1)

    def test_d_on_the_contract_too(self):
        rows = json.loads(HACKS)
        rows.reverse()
        WEB[HACKS_URL] = (200, json.dumps(rows))
        clid = self.claim(K_DNS, R_CURVE_DNS)
        out = judge(self.c, clid, "EXCLUDED", "NONE", "FRONTEND_HIJACK")
        self.assertEqual(out["incident_date"], "2022-08-09")
        self.assertEqual(out["outcome"], "DENIED_EXCLUDED")

    # ONLY MATCHED PAGES REACH THE CLASSIFIER
    def prompt_of_last_call(self):
        self.assertGreater(len(MODEL.log), 0, "the model was never asked")
        return MODEL.log[-1]

    def test_mixed_dns_record_classifies_from_dns_page_only(self):
        # record = DNS 2022; evidence = [DNS article (bound), Vyper article (not)]
        clid = self.claim(K_DNS, R_CURVE_DNS + " " + R_VYPER)
        out = judge(self.c, clid, "EXCLUDED", "NONE", "FRONTEND_HIJACK")
        self.assertEqual(out["outcome"], "DENIED_EXCLUDED")
        self.assertEqual(int(self.c.claims[clid - 1].gross_wei), 0)
        prompt = self.prompt_of_last_call()
        body = prompt[prompt.index("<<<EVIDENCE"):prompt.index("EVIDENCE>>>")]
        self.assertIn("DNS", body)
        for vyper_only in ("Vyper", "JPEG", "Alchemix", "Metronome", "July 31, 2023"):
            self.assertNotIn(vyper_only, body, vyper_only)
        # the whole prompt is byte-identical to the DNS page's prompt alone
        f = euler_facts(protocol_name="Curve", llama_slug="curve-dex", llama_id="3",
                        urls=[R_CURVE_DNS], key=K_DNS, claim_id=clid,
                        perils=["SMART_CONTRACT_BUG", "ORACLE_MANIPULATION", "ECONOMIC_EXPLOIT"])
        self.assertEqual(prompt, C._prompt(f, C._reading(f, fetch_raw(f))))
        k = self.c.claims[clid - 1]
        self.assertIn("curve-finance-rekt BOUND", str(k.bind_line))
        self.assertIn("curve-vyper-rekt UNBOUND", str(k.bind_line))
        self.assertNotIn("Vyper", str(k.digest))

    def test_mixed_vyper_record_classifies_from_vyper_page_only(self):
        # record = Vyper 2023; evidence = [Vyper article (bound), DNS article (not)]
        clid = self.claim(K_VYPER, R_VYPER + " " + R_CURVE_DNS)
        out = judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.assertEqual(out["outcome"], "APPROVED")
        self.assertEqual(out["severity_bucket"], 2)
        prompt = self.prompt_of_last_call()
        body = prompt[prompt.index("<<<EVIDENCE"):prompt.index("EVIDENCE>>>")]
        self.assertIn("Vyper", body)
        for dns_only in ("DNS", "hijack", "front end", "August 10, 2022"):
            self.assertNotIn(dns_only, body, dns_only)
        self.assertNotIn("FRONTEND_HIJACK:", prompt)
        self.assertNotIn("DNS", str(self.c.claims[clid - 1].digest))
        f = euler_facts(protocol_name="Curve", llama_slug="curve-dex", llama_id="3",
                        urls=[R_VYPER], key=K_VYPER, claim_id=clid,
                        perils=["SMART_CONTRACT_BUG", "ORACLE_MANIPULATION", "ECONOMIC_EXPLOIT"])
        self.assertEqual(prompt, C._prompt(f, C._reading(f, fetch_raw(f))))

    def test_undated_page_never_reaches_the_classifier(self):
        # A bound page plus an UNDATED allowlisted page: the undated text is
        # in no prompt, digest, bracket or hash.
        extra = "https://curve.finance/notes"
        RENDER[extra] = ("Curve notes: a governance proposal and a phishing "
                         "campaign are unrelated background to this incident.")
        clid = self.claim(K_VYPER, R_VYPER + " " + extra)
        judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        prompt = self.prompt_of_last_call()
        for w in ("phishing", "governance proposal", "PHISHING:", "GOVERNANCE_ATTACK:"):
            self.assertNotIn(w, prompt, w)
        k = self.c.claims[clid - 1]
        self.assertIn("curve.finance/notes UNDATED", str(k.bind_line))
        self.assertNotIn("phishing", str(k.digest))
        self.assertNotIn("PHISHING", str(k.bracket))

    def test_classifier_input_is_exactly_the_bound_digests(self):
        f = euler_facts(protocol_name="Curve", llama_slug="curve-dex", llama_id="3",
                        urls=[R_CURVE_DNS, R_VYPER, "https://curve.finance/notes"],
                        key=K_DNS)
        install_web()
        RENDER["https://curve.finance/notes"] = "Curve notes about a phishing campaign in general terms."
        raw = C._read_sources(f)
        r = C._reading(f, raw)
        bound = [p["digest"] for p, st in zip(raw["pages"], C._bind(raw["pages"], r["incident_day"], True)[0])
                 if st == "BOUND"]
        self.assertEqual(len(bound), 1)
        self.assertEqual(r["digest"], C._short(" ".join(bound), C.MAX_DIGEST))
        self.assertIn(r["digest"], C._prompt(f, r))

    # e.
    def test_e_record_outside_the_window_refused_before_model(self):
        # A cover starting after the DNS hijack: its key is refused at filing.
        c = fresh(demo_backdate_days=(NOW - epoch("2023-01-01T00:00:00Z")) // DAY)
        pid = make_pool(c, spec=CURVE)
        cid = buy(c, pid, amount=GEN // 2, days=30)
        out = send(c, ALICE, 0, "file_claim", cid, K_DNS, R_CURVE_DNS, "x")
        self.assertTrue(rejected(out))
        self.assertIn("predates this cover's start", out["reason"])
        # ...and Vyper is after this 30-day cover ended.
        out = send(c, ALICE, 0, "file_claim", cid, K_VYPER, R_VYPER, "x")
        self.assertTrue(rejected(out))
        self.assertIn("after this cover ended", out["reason"])
        self.assertEqual(len(c.claims), 0)
        self.assertEqual(CALLS, [])
        self.assertEqual(MODEL.calls, 0)

    # f.
    def test_f_missing_or_malformed_key_refused(self):
        cid = buy(self.c, self.pid, amount=GEN // 2)
        for bad, why in (("", "incident key is required"),
                         ("curve", "is not <id>"),
                         ("3:2023/07/30", "real day"),
                         ("1183:2023-03-13", "names DeFi Llama id 1183 but this pool covers id 3")):
            out = send(self.c, ALICE, 0, "file_claim", cid, bad, R_VYPER, "x")
            self.assertTrue(rejected(out), bad)
            self.assertIn(why, out["reason"])
        self.assertEqual(len(self.c.claims), 0)
        self.assertEqual(MODEL.calls, 0)

    def test_f_unknown_key_refused_before_model(self):
        clid = self.claim("3:2023-02-02", R_VYPER)
        out = judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.assertEqual(out["outcome"], "INCONCLUSIVE")
        self.assertFalse(out["model_called"])
        self.assertEqual(MODEL.calls, 0)
        pinned = str(self.c.claims[clid - 1].pinned)
        self.assertIn("no DeFi Llama incident record matches incident key 3:2023-02-02", pinned)
        self.assertIn("2022-08-09, 2023-07-30", pinned)
        self.assertEqual(int(self.c.claims[clid - 1].gross_wei), 0)

    def test_f_ambiguous_key_refused_until_named(self):
        rows = json.loads(HACKS)
        rows.append({"name": "Curve Lending", "date": epoch("2023-07-30T00:00:00Z"),
                     "defillamaId": "3", "classification": "Access Control",
                     "technique": "x", "amount": 5})
        WEB[HACKS_URL] = (200, json.dumps(rows))
        clid = self.claim(K_VYPER, R_VYPER)
        out = judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.assertEqual(out["outcome"], "INCONCLUSIVE")
        self.assertIn("add the record's name", str(self.c.claims[clid - 1].pinned))
        self.assertEqual(MODEL.calls, 0)
        out = send(self.c, ALICE, 0, "refile_claim", clid, K_VYPER + ":Curve DEX", "", "x")
        self.assertTrue(ok(out), out)
        self.assertEqual(judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")["outcome"],
                         "APPROVED")

    # g.
    def test_g_refile_after_mismatch_with_correct_evidence(self):
        clid = self.claim(K_VYPER, R_CURVE_DNS)
        self.assertEqual(judge(self.c, clid)["outcome"], "EVIDENCE_MISMATCH")
        out = send(self.c, ALICE, 0, "refile_claim", clid, "", R_VYPER, "the Vyper report")
        self.assertTrue(ok(out), out)
        self.assertEqual(out["mismatch_refiles_left"], 1)
        out = judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        self.assertEqual(out["outcome"], "APPROVED")
        self.assertEqual(out["severity_bucket"], 2)

    def test_g_refile_with_corrected_key_same_evidence(self):
        clid = self.claim(K_VYPER, R_CURVE_DNS)
        judge(self.c, clid)
        out = send(self.c, ALICE, 0, "refile_claim", clid, K_DNS, R_CURVE_DNS, "wrong key")
        self.assertTrue(ok(out), out)
        self.assertEqual(str(self.c.claims[clid - 1].incident_key), K_DNS)
        out = judge(self.c, clid, "EXCLUDED", "NONE", "FRONTEND_HIJACK")
        self.assertEqual(out["outcome"], "DENIED_EXCLUDED")

    def test_g_refile_needs_a_change(self):
        clid = self.claim(K_VYPER, R_CURVE_DNS)
        judge(self.c, clid)
        out = send(self.c, ALICE, 0, "refile_claim", clid, "", R_CURVE_DNS, "again")
        self.assertTrue(rejected(out))
        self.assertIn("corrected incident key", out["reason"])

    def test_g_mismatch_refiles_are_limited(self):
        clid = self.claim(K_VYPER, R_CURVE_DNS)
        judge(self.c, clid)
        urls = [A_EULER, R_EULER]      # allowlisted, dated to another event
        for u in urls:
            self.assertTrue(ok(send(self.c, ALICE, 0, "refile_claim", clid, "", u, "x")))
            self.assertEqual(judge(self.c, clid)["outcome"], "EVIDENCE_MISMATCH")
        out = send(self.c, ALICE, 0, "refile_claim", clid, "", R_VYPER, "x")
        self.assertTrue(rejected(out))
        self.assertIn("used all 2 refiles", out["reason"])
        # the cover then releases after its claim window, premium earned
        advance(31 * DAY)
        self.assertTrue(ok(send(self.c, STRANGER, 0, "release_cover",
                                int(self.c.claims[clid - 1].cover_id))))

    def test_mismatch_is_not_contestable(self):
        clid = self.claim(K_VYPER, R_CURVE_DNS)
        judge(self.c, clid)
        out = send(self.c, UW, int(self.c.contest_bond_wei), "contest", clid,
                   R_VYPER, "The underwriter wants the pool's view on this recorded.")
        self.assertTrue(rejected(out))
        self.assertIn("refile it instead", out["reason"])

    def test_release_waits_for_a_mismatch_refile(self):
        clid = self.claim(K_VYPER, R_CURVE_DNS)
        judge(self.c, clid)
        cover = int(self.c.claims[clid - 1].cover_id)
        out = send(self.c, STRANGER, 0, "release_cover", cover)
        self.assertTrue(rejected(out))

    # the hash binds all of it
    def test_hash_binds_key_record_evidence_and_window(self):
        f = euler_facts(protocol_name="Curve", llama_slug="curve-dex", llama_id="3",
                        urls=[R_VYPER], key=K_VYPER)
        raw = fetch_raw(f)
        base = C._reading(f, raw)["content_hash"]
        variants = []
        g = dict(f, incident_key=K_VYPER + ":Curve DEX", key_name="Curve DEX")
        variants.append(("key", C._reading(g, fetch_raw(g))))
        r2 = json.loads(json.dumps(raw))
        r2["tvl"]["window"][3][1] += 1
        variants.append(("tvl point", C._reading(f, r2)))
        r3 = json.loads(json.dumps(raw))
        r3["llama"]["technique"] = "Something Else"
        variants.append(("record", C._reading(f, r3)))
        r4 = json.loads(json.dumps(raw))
        r4["pages"][0]["days"] = [epoch("2023-07-29T00:00:00Z")]
        variants.append(("binding", C._reading(f, r4)))
        r5 = json.loads(json.dumps(raw))
        r5["pages"][0]["digest"] += " Also the Vyper compiler team apologised to everyone."
        variants.append(("evidence", C._reading(f, r5)))
        for name, r in variants:
            self.assertNotEqual(r["content_hash"], base, name)

    def test_verify_rederives_all_of_it(self):
        clid = self.claim(K_VYPER, R_VYPER)
        judge(self.c, clid, "COVERED", "SMART_CONTRACT_BUG")
        v = view(self.c, "verify_claim", clid)
        for k in ("hash_matches", "record_matches_key", "tvl_window_anchored"):
            self.assertTrue(v[k], k)
        self.assertEqual(v["drop_from_window_bps"], 4952)
        self.assertEqual(v["incident_key"], K_VYPER)
        k = self.c.claims[clid - 1]
        for field, forged in (("incident_key", K_DNS),
                              ("tvl_line", str(k.tvl_line).replace("low 1578413160", "low 1")),
                              ("bind_line", str(k.bind_line) + " x"),
                              ("llama_line", str(k.llama_line).replace("61700000", "1"))):
            old = getattr(k, field)
            setattr(k, field, forged)
            self.assertFalse(view(self.c, "verify_claim", clid)["hash_matches"], field)
            setattr(k, field, old)
        # a stored window re-anchored on the other incident is caught even if
        # the hash were recomputed by whoever tampered with it
        old = k.tvl_line
        k.tvl_line = str(old).replace("anchor 2023-07-30", "anchor 2022-08-09")
        self.assertFalse(view(self.c, "verify_claim", clid)["tvl_window_anchored"])
        k.tvl_line = old
        old = k.llama_line
        k.llama_line = str(old).replace("3:2023-07-30", "3:2022-08-09")
        self.assertFalse(view(self.c, "verify_claim", clid)["record_matches_key"])
        k.llama_line = old

    def test_forged_leader_with_other_record_is_refused(self):
        # A leader that swaps in the DNS record under a Vyper key: its own raw
        # inputs no longer match the question, and coherence fails.
        f = euler_facts(protocol_name="Curve", llama_slug="curve-dex", llama_id="3",
                        urls=[R_VYPER], key=K_VYPER)
        raw = fetch_raw(f)
        g = dict(f, incident_key=K_DNS, key_day=epoch("2022-08-09T00:00:00Z"))
        other = fetch_raw(g)
        forged = json.loads(json.dumps(raw))
        forged["llama"] = other["llama"]
        forged["tvl"] = other["tvl"]
        payload = C._derive(f, forged, {"classification": "INCONCLUSIVE", "peril": "NONE",
                                        "exclusion": "NONE", "strength": 0,
                                        "event_match": "DIFFERENT"})
        honest = C._derive(f, raw, {"classification": "COVERED",
                                    "peril": "SMART_CONTRACT_BUG", "exclusion": "NONE",
                                    "strength": 4, "event_match": "SAME"})
        payload = dict(payload, raw=forged, choice={"classification": "INCONCLUSIVE",
                                                    "peril": "NONE", "exclusion": "NONE",
                                                    "strength": payload["strength_lo"],
                                                    "event_match": payload["event_gate"]})
        honest["raw"] = raw
        self.assertFalse(C._agrees(payload, honest))
        self.assertNotEqual(payload["content_hash"], honest["content_hash"])

    def test_event_fields_are_compared_exactly(self):
        for k in ("incident_key", "bind_line", "event_gate", "pinned_as", "event_match"):
            self.assertIn(k, C.EXACT_STR)
        self.assertIn("bound", C.EXACT_INT)


class TestLoophole09_OwnerPauseCannotFreezeMoney(unittest.TestCase):
    """The full list, method by method, while paused."""

    def setUp(self):
        self.c = fresh(stall_ttl_s=HOUR)
        self.pid = make_pool(self.c)
        self.cid = buy(self.c, self.pid)
        send(self.c, OWNER, 0, "set_paused", True)

    def test_new_business_blocked(self):
        self.assertTrue(rejected(send(self.c, UW, 10 * GEN, "create_pool",
                                      "X", "x", "1", "c", "SMART_CONTRACT_BUG",
                                      "", 100, 7, 0, GEN, 30, 10000, "", "", "")))
        self.assertTrue(rejected(send(self.c, UW, GEN, "add_capacity", self.pid)))
        self.assertTrue(rejected(send(self.c, BOB, GEN, "buy_cover", self.pid, GEN, 30)))

    def test_claims_and_payouts_open(self):
        clid = file(self.c, self.cid, R_EULER)
        self.assertEqual(judge(self.c, clid)["outcome"], "APPROVED")
        self.assertTrue(ok(settle_ready(self.c, 1)))
        self.assertGreater(drain(self.c, ALICE), 0)

    def canonical(self):
        c = fresh(demo=False)
        pid = make_pool(c)
        cid = buy(c, pid, days=30)
        send(c, OWNER, 0, "set_paused", True)
        return c, pid, cid

    def test_refunds_open(self):
        c, _, cid = self.canonical()
        self.assertTrue(ok(send(c, ALICE, 0, "cancel_cover", cid)))
        self.assertGreater(drain(c, ALICE), 0)

    def test_withdraw_and_close_open(self):
        c, pid, cid = self.canonical()
        send(c, ALICE, 0, "cancel_cover", cid)
        self.assertTrue(ok(send(c, UW, 0, "withdraw_capacity", pid, GEN)))
        self.assertTrue(ok(send(c, UW, 0, "close_pool", pid)))

    def test_release_open(self):
        advance(31 * DAY)
        self.assertTrue(ok(send(self.c, STRANGER, 0, "release_cover", self.cid)))

    def test_settle_stalled_open(self):
        clid = file(self.c, self.cid, R_EULER)
        advance(HOUR + 1)
        self.assertTrue(ok(send(self.c, STRANGER, 0, "settle_stalled", clid)))

    def test_refused_value_still_withdrawable(self):
        send(self.c, BOB, 3 * GEN, "buy_cover", self.pid, GEN, 30)
        self.assertEqual(drain(self.c, BOB), 3 * GEN)


class TestLoophole10_PaymentNeverReadsTheClock(unittest.TestCase):
    """Studio Dev's fee simulator runs on a stale clock: a write that both
    reads the clock and posts a transfer cannot be fee-estimated. So exactly
    one method transfers, and it reads no clock - proved over the call graph."""

    def calls_of(self, fn):
        out = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "self":
                    out.add(node.func.attr)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                out.add(node.func.id)
        return out

    def closure(self, name, methods, funcs):
        seen = set()
        stack = [name]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            node = methods.get(n) or funcs.get(n)
            if node is None:
                continue
            stack.extend(self.calls_of(node))
        return seen

    def setUp(self):
        self.methods = {}
        self.funcs = {}
        for node in TREE.body:
            if isinstance(node, ast.FunctionDef):
                self.funcs[node.name] = node
            if isinstance(node, ast.ClassDef) and node.name == "CoverClaim":
                for m in node.body:
                    if isinstance(m, ast.FunctionDef):
                        self.methods[m.name] = m

    def test_only_claim_payout_reaches_pay(self):
        writers = []
        for name, m in self.methods.items():
            decs = [ast.unparse(d) for d in m.decorator_list]
            if any(d.startswith("gl.public.write") for d in decs):
                if "_pay" in self.closure(name, self.methods, self.funcs):
                    writers.append(name)
        self.assertEqual(writers, ["claim_payout"])

    def test_claim_payout_reads_no_clock(self):
        reach = self.closure("claim_payout", self.methods, self.funcs)
        self.assertNotIn("_now", reach)
        self.assertNotIn("_epoch_from_iso", reach)

    def test_every_clock_reader_only_credits(self):
        for name, m in self.methods.items():
            decs = [ast.unparse(d) for d in m.decorator_list]
            if not any(d.startswith("gl.public.write") for d in decs):
                continue
            reach = self.closure(name, self.methods, self.funcs)
            if "_now" in reach:
                self.assertNotIn("_pay", reach, name)

    def test_finalize_credits_and_payout_transfers(self):
        c = fresh()
        pid = make_pool(c)
        judge(c, file(c, buy(c, pid), R_EULER))
        n = len(TRANSFERS)
        settle_ready(c, 1)
        self.assertEqual(len(TRANSFERS), n)
        drain(c, ALICE)
        self.assertEqual(len(TRANSFERS), n + 1)


# ===========================================================================
# 8. the AST invariants - syntax, never grep (the docs mention what they forbid)
# ===========================================================================

REG_TEXT = REGISTRY.read_text(encoding="utf8")
REG_TREE = ast.parse(REG_TEXT)


def _class(tree, name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError("no class " + name)


def _methods(cls):
    return {m.name: m for m in cls.body if isinstance(m, ast.FunctionDef)}


def _is_write(m):
    return any(ast.unparse(d).startswith("gl.public.write") for d in m.decorator_list)


def _is_payable(m):
    return any(ast.unparse(d) == "gl.public.write.payable" for d in m.decorator_list)


CC = _class(TREE, "CoverClaim")
CC_METHODS = _methods(CC)


class TestSourceInvariants(unittest.TestCase):
    def test_zero_raise_statements(self):
        for tree, name in ((TREE, "CoverClaim"), (REG_TREE, "CoverRegistry")):
            raises = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Raise)]
            self.assertEqual(raises, [], name)

    def test_no_str_replace(self):
        for tree in (TREE, REG_TREE):
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                    self.assertNotEqual(n.func.attr, "replace", n.lineno)

    def test_header_is_two_lines(self):
        for text in (SRC_TEXT, REG_TEXT):
            lines = text.split("\n")
            self.assertEqual(lines[0], "# v0.3.0")
            self.assertTrue(lines[1].startswith('# { "Depends": "py-genlayer:'))
            self.assertFalse(lines[2].startswith("#"))

    def test_runner_pinned_not_latest(self):
        self.assertNotIn("py-genlayer:latest", SRC_TEXT)
        self.assertNotIn("py-genlayer:test", SRC_TEXT)

    def test_no_float_literals(self):
        for n in ast.walk(TREE):
            if isinstance(n, ast.Constant):
                self.assertNotIsInstance(n.value, float, getattr(n, "lineno", 0))

    def test_no_undefined_names(self):
        self.assertEqual(undefined_names(SOURCE), [])
        self.assertEqual(undefined_names(REGISTRY), [])

    def test_every_write_banks_first(self):
        for name, m in CC_METHODS.items():
            if not _is_write(m):
                continue
            body = [s for s in m.body if not (isinstance(s, ast.Expr)
                                                and isinstance(s.value, ast.Constant))]
            self.assertEqual(ast.unparse(body[0]), "self._bank()", name)

    def test_payable_methods_are_the_money_entrances(self):
        pay = sorted(n for n, m in CC_METHODS.items() if _is_payable(m))
        self.assertEqual(pay, ["add_capacity", "buy_cover", "contest", "create_pool"])

    def test_every_payable_refusal_goes_through_refuse(self):
        """Every `return` of a payable method either returns `self._refuse(...)`
        or an OK dict - never a hand-built REJECTED that would skip the books."""
        for name, m in CC_METHODS.items():
            if not _is_payable(m):
                continue
            for n in ast.walk(m):
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict):
                    keys = [k.value for k in n.value.keys if isinstance(k, ast.Constant)]
                    vals = [ast.unparse(v) for v in n.value.values]
                    if "status" in keys:
                        self.assertEqual(vals[keys.index("status")], "'OK'", name)

    def test_take_after_every_refusal_in_payables(self):
        """RULE 3 for money: in each payable method the first `_take` comes
        after the last `_refuse`."""
        for name, m in CC_METHODS.items():
            if not _is_payable(m):
                continue
            last_refuse = 0
            first_take = 10 ** 9
            for n in ast.walk(m):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                    if n.func.attr == "_refuse":
                        if "could not be booked" not in ast.unparse(n):
                            last_refuse = max(last_refuse, n.lineno)
                    if n.func.attr == "_take":
                        first_take = min(first_take, n.lineno)
            self.assertLess(last_refuse, first_take, name)

    def test_counters_after_refusals(self):
        """No `self.total_*` counter (other than the refusal and attempt
        statistics) is written before a method's last refusal."""
        allowed = {"total_rejected", "total_judge_attempts", "total_retries"}
        for name, m in CC_METHODS.items():
            if not _is_write(m):
                continue
            refusals = [n.lineno for n in ast.walk(m) if isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "_refuse"
                        and "could not be booked" not in ast.unparse(n)
                        and "usable verdict" not in ast.unparse(n)]
            if not refusals:
                continue
            last = max(refusals)
            for n in ast.walk(m):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Attribute) and t.attr.startswith("total_") \
                                and t.attr not in allowed:
                            self.assertGreater(n.lineno, last, (name, t.attr))

    FROZEN_POOL = ("protocol_name", "llama_slug", "llama_id", "chain", "perils_csv",
                   "exclusions_csv", "domains_csv", "payout_table_csv", "rate_bps",
                   "waiting_days", "deductible_bps", "max_cover_wei", "term_days",
                   "collateral_bps", "wording", "policy_hash", "created_at",
                   "expires_at", "underwriter", "pool_id")

    def test_policy_frozen(self):
        for name, m in CC_METHODS.items():
            for n in ast.walk(m):
                if isinstance(n, (ast.Assign, ast.AugAssign)):
                    targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                    for t in targets:
                        if isinstance(t, ast.Attribute) and t.attr in self.FROZEN_POOL \
                                and ast.unparse(t.value) == "pool":
                            self.assertEqual(name, "create_pool", (name, t.attr))

    IMMUTABLE = ("demo_backdate_days", "claim_window_s", "settlement_window_s",
                 "contest_window_s", "stall_ttl_s", "buy_cooldown_s",
                 "contest_bond_wei")

    def test_constructor_values_immutable(self):
        for name, m in CC_METHODS.items():
            for n in ast.walk(m):
                if isinstance(n, (ast.Assign, ast.AugAssign)):
                    targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                    for t in targets:
                        if isinstance(t, ast.Attribute) and t.attr in self.IMMUTABLE \
                                and ast.unparse(t.value) == "self":
                            self.assertEqual(name, "__init__", (name, t.attr))

    def test_pause_gates_only_new_business(self):
        gated = []
        for name, m in CC_METHODS.items():
            if not _is_write(m):
                continue
            for n in ast.walk(m):
                if isinstance(n, ast.If) and "self.paused" in ast.unparse(n.test):
                    gated.append(name)
        self.assertEqual(sorted(set(gated)), ["add_capacity", "buy_cover", "create_pool"])

    def test_nondet_closures_do_not_capture_self(self):
        m = CC_METHODS["_consensus"]
        for fn in ast.walk(m):
            if isinstance(fn, ast.FunctionDef) and fn.name in ("leader_fn", "validator_fn"):
                names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
                self.assertNotIn("self", names, fn.name)

    def test_nondet_only_in_consensus(self):
        for name, m in CC_METHODS.items():
            text = ast.unparse(m)
            if "run_nondet" in text:
                self.assertEqual(name, "_consensus")

    def test_registry_custody_false(self):
        reg = _class(REG_TREE, "CoverRegistry")
        for m in reg.body:
            if isinstance(m, ast.FunctionDef):
                self.assertFalse(_is_payable(m), m.name)
        self.assertNotIn("emit_transfer(", REG_TEXT.split("# It accepts no value.")[1])

    def test_claim_struct_verdict_fields_written_by_record(self):
        """Every verdict field of Claim is written by `_record` from the derived
        vector, and by nothing else (except the contest's own fields)."""
        claim = _class(TREE, "Claim")
        fields = [n.target.id for n in claim.body if isinstance(n, ast.AnnAssign)]
        verdict = fields[fields.index("judged_at"):fields.index("table_bps")]
        rec = ast.unparse(CC_METHODS["_record"])
        for f in verdict:
            self.assertIn("claim." + f + " =", rec, f)
        for name, m in CC_METHODS.items():
            if name == "_record":
                continue
            for n in ast.walk(m):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Attribute) and t.attr in verdict \
                                and t.attr not in ("judged_at", "incident_day"):
                            self.fail((name, t.attr))

    def test_sentence_in_source(self):
        self.assertIn("GenLayer reads public incident evidence and classifies it",
                      SRC_TEXT)


# ===========================================================================
# 9. randomised lifecycles: every pool drains to exactly zero
# ===========================================================================

SPECS = [(EULER, R_EULER), (CURVE, R_CURVE_DNS), (MULTI, R_MULTI),
         (TORNADO, R_TORNADO), (KYBER, R_KYBER)]
BUYERS = [ALICE, BOB, CAROL, DAVE, _Addr("0x" + "4" * 40), _Addr("0x" + "5" * 40)]
UWS = [UW, UW2, _Addr("0x" + "6" * 40)]


def choose_for(c, clid, rnd):
    """Pick a VALID answer for this claim's bracket, at random - an honest but
    unpredictable model."""
    cl = c.claims[clid - 1]
    facts = c._claim_facts(cl, c.covers[int(cl.cover_id) - 1],
                           c.pools[int(cl.pool_id) - 1], "claim")
    read = C._reading(facts, C._read_sources(facts))
    serve_random(read, rnd)


def serve_random(read, rnd):
    """Weighted towards a decision, so payouts, denials and flips all occur."""
    opts = read["options"]
    r = rnd.random()
    if "COVERED" in opts and r < 0.6:
        opt = "COVERED"
    elif "EXCLUDED" in opts and r < 0.9:
        opt = "EXCLUDED"
    else:
        opt = rnd.choice(opts)
    peril = rnd.choice(read["allowed_perils"]) if opt == "COVERED" else "NONE"
    excl = rnd.choice(read["allowed_exclusions"]) if opt == "EXCLUDED" else "NONE"
    MODEL.serve(opt, peril, excl, rnd.randint(read["strength_lo"], read["strength_hi"]))


def followup_url(slug):
    return "https://web.archive.org/web/2024/https://rekt.news/" + slug + "-followup"


def install_followups():
    for spec, _ in SPECS:
        RENDER[followup_url(spec["slug"])] = (
            spec["name"] + " follow-up: investigators later confirmed a reentrancy "
            "flaw in the contract code as the root cause of the loss.\n"
            "A second report on " + spec["name"] + " claims a private key had "
            "leaked from an operator days before the incident.")


def run_lifecycle(seed):
    rnd = random.Random(seed)
    demo = rnd.random() < 0.8
    c = fresh(demo=demo, stall_ttl_s=HOUR, settlement_window_s=2 * HOUR,
              contest_window_s=HOUR, claim_window_s=3 * DAY,
              buy_cooldown_s=0, contest_bond_wei=GEN // 10)
    install_followups()
    deposited = 0
    pools = []
    for i in range(rnd.randint(1, 3)):
        spec, _ = rnd.choice(SPECS)
        cap = rnd.randint(1, 4) * GEN
        coll = rnd.choice([10000, 5000, 3000, 2000])
        pid = make_pool(c, uw=UWS[i], spec=spec, capital=cap, coll=coll,
                        max_cover=4 * GEN, ded=rnd.choice([0, 500, 1000, 2500]),
                        rate=rnd.randint(10, 500),
                        table=rnd.choice(["", "0,1000,3000,6000,9000"]))
        deposited += cap
        pools.append(pid)
    covers = []
    for b in BUYERS[:rnd.randint(1, 6)]:
        pid = rnd.choice(pools)
        amount = rnd.randint(1, 20) * GEN // 10
        days = rnd.choice([365, 365, 365, 200, 30]) if demo else \
            rnd.choice([1, 30, 90])
        q = view(c, "quote", pid, amount, days)
        prem = int(q["premium_wei"])
        extra = rnd.choice([0, 0, 7, GEN // 100])
        out = send(c, b, prem + extra, "buy_cover", pid, amount, days)
        deposited += prem + extra
        if ok(out):
            covers.append(int(out["cover_id"]))
    for cid in covers:
        cov = c.covers[cid - 1]
        r = rnd.random()
        if r < 0.15 and not demo:
            send(c, cov.buyer, 0, "cancel_cover", cid)
            continue
        if r < 0.75:
            spec_url = rnd.choice(SPECS)[1] if rnd.random() < 0.2 else \
                dict((s["slug"], u) for s, u in SPECS)[str(c.pools[int(cov.pool_id) - 1].llama_slug)]
            out = send(c, cov.buyer, 0, "file_claim", cid, key_for(c, cid, spec_url), spec_url, "claim")
            if not ok(out):
                continue
            clid = int(out["claim_id"])
            choose_for(c, clid, rnd)
            send(c, STRANGER, 0, "judge_claim", clid)
            cl = c.claims[clid - 1]
            st = str(cl.status)
            if st in C.CL_CONTESTABLE and rnd.random() < 0.5:
                pool = c.pools[int(cl.pool_id) - 1]
                who = pool.underwriter if st == "APPROVED" else cl.claimant
                bond = int(c.contest_bond_wei)
                deposited += bond
                slug = str(pool.llama_slug)
                out = send(c, who, bond, "contest", clid, followup_url(slug),
                           "A new source with new facts, seed %d." % seed)
                if ok(out):
                    mode = rnd.random()
                    if mode < 0.3:
                        advance(HOUR + 1)
                        send(c, STRANGER, 0, "settle_stalled", clid)
                    else:
                        facts = c._claim_facts(cl, c.covers[int(cl.cover_id) - 1],
                                               pool, "contest")
                        read = C._reading(facts, C._read_sources(facts))
                        serve_random(read, rnd)
                        send(c, STRANGER, 0, "judge_contest", clid)
    # time passes; everything that can settle, settles
    advance(3 * HOUR)
    for b in c.batches:
        if str(b.status) == "OPEN":
            out = send(c, STRANGER, 0, "finalize_incident", int(b.batch_id))
            assert ok(out), out
    advance(400 * DAY)
    for cov in c.covers:
        if str(cov.status) == "ACTIVE":
            out = send(c, STRANGER, 0, "release_cover", int(cov.cover_id))
            assert ok(out), (seed, out, str(c.claims[int(cov.claim_id) - 1].status)
                             if int(cov.claim_id) else "")
    for p in c.pools:
        out = send(c, p.underwriter, 0, "close_pool", int(p.pool_id))
        assert ok(out), out
    paid = 0
    for who in list(c.payout_wei.keys()):
        addr = who if isinstance(who, _Addr) else _Addr(who)
        paid += drain(c, addr)
    return c, deposited, paid


def _make_lifecycle_test(seed):
    def test(self):
        c, deposited, paid = run_lifecycle(seed)
        self.assertEqual(int(c.balance_wei), 0, seed)
        self.assertEqual(int(c.held_wei), 0)
        self.assertEqual(int(c.payable_wei), 0)
        self.assertEqual(deposited, paid, seed)
        for p in c.pools:
            self.assertEqual(str(p.status), "CLOSED")
            self.assertEqual(int(p.capital_wei) + int(p.premiums_held_wei)
                             + int(p.locked_wei), 0)
        for cov in c.covers:
            self.assertNotEqual(str(cov.status), "ACTIVE")
    return test


class TestRandomLifecyclesDrainToZero(unittest.TestCase):
    """Every GEN that entered leaves: after every cover expires and every claim
    settles, balance == 0 and the sum of transfers equals the sum of deposits."""


for _seed in range(120):
    setattr(TestRandomLifecyclesDrainToZero, "test_seed_%03d" % _seed,
            _make_lifecycle_test(_seed))


class TestDrainsAcrossOutcomes(unittest.TestCase):
    def test_every_outcome_in_one_contract(self):
        c = fresh(contest_bond_wei=GEN // 10)
        e = make_pool(c, uw=UW, spec=EULER)
        cv = make_pool(c, uw=UW2, spec=CURVE)
        a = buy(c, e, who=ALICE)
        b = buy(c, cv, who=BOB)
        d = buy(c, e, who=CAROL)
        judge(c, file(c, a, R_EULER))
        judge(c, file(c, b, R_CURVE_DNS), "EXCLUDED", "NONE", "FRONTEND_HIJACK")
        RENDER[HOME_EULER] = "Euler Finance lets you lend and borrow almost anything."
        judge(c, file(c, d, HOME_EULER))
        settle_ready(c, 1)
        advance(40 * DAY)
        for cid in (b, d):
            self.assertTrue(ok(send(c, STRANGER, 0, "release_cover", cid)))
        for pid, who in ((e, UW), (cv, UW2)):
            self.assertTrue(ok(send(c, who, 0, "close_pool", pid)))
        for who in (ALICE, BOB, CAROL, UW, UW2):
            drain(c, who)
        self.assertEqual(int(c.balance_wei), 0)
        self.assertEqual(sum(v for _, v in TRANSFERS), 20 * GEN + sum(
            int(x.premium_wei) for x in c.covers))


# ===========================================================================
# 10. CoverRegistry
# ===========================================================================

RMOD = load_full(REGISTRY, "coverregistry_full")
CC_ADDR = "0x" + "9" * 40


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.c = fresh(demo=False)
        CONTRACTS.clear()
        CONTRACTS[CC_ADDR] = self.c
        MESSAGE.sender_address = OWNER
        self.r = RMOD.CoverRegistry(CC_ADDR)
        self.pid = make_pool(self.c, wait=7)

    def test_not_covered_without_cover(self):
        self.assertFalse(view(self.r, "is_covered", ALICE.as_hex, "euler-v1"))

    def test_waiting_period_is_not_cover(self):
        buy(self.c, self.pid, days=30)
        self.assertFalse(view(self.r, "is_covered", ALICE.as_hex, "euler-v1"))

    def test_in_force_after_waiting(self):
        buy(self.c, self.pid, days=30)
        advance(8 * DAY)
        self.assertTrue(view(self.r, "is_covered", ALICE.as_hex, "euler-v1"))
        self.assertTrue(view(self.r, "is_covered", ALICE.as_hex, "Euler"))

    def test_other_protocol_not_covered(self):
        buy(self.c, self.pid, days=30)
        advance(8 * DAY)
        self.assertFalse(view(self.r, "is_covered", ALICE.as_hex, "curve-dex"))

    def test_expired_not_covered(self):
        buy(self.c, self.pid, days=30)
        advance(31 * DAY)
        self.assertFalse(view(self.r, "is_covered", ALICE.as_hex, "euler-v1"))

    def test_cancelled_not_covered(self):
        cid = buy(self.c, self.pid, days=30)
        send(self.c, ALICE, 0, "cancel_cover", cid)
        advance(8 * DAY)
        self.assertFalse(view(self.r, "is_covered", ALICE.as_hex, "euler-v1"))

    def test_unreadable_clock_is_not_cover(self):
        buy(self.c, self.pid, days=30)
        advance(8 * DAY)
        MESSAGE.raw["datetime"] = ""
        self.assertFalse(view(self.r, "is_covered", ALICE.as_hex, "euler-v1"))

    def test_unreachable_coverclaim(self):
        CONTRACTS.clear()
        self.assertFalse(view(self.r, "is_covered", ALICE.as_hex, "euler-v1"))
        out = send_reg(self.r, STRANGER, "attest", ALICE.as_hex, "euler-v1")
        self.assertEqual(out["status"], "REJECTED")

    def test_get_active_cover(self):
        buy(self.c, self.pid, days=30)
        got = view(self.r, "get_active_cover", ALICE.as_hex)
        self.assertEqual(got["count"], 1)
        self.assertEqual(got["best"]["protocol_name"], "Euler")

    def test_attest_records_snapshot(self):
        buy(self.c, self.pid, days=30)
        advance(8 * DAY)
        out = send_reg(self.r, STRANGER, "attest", ALICE.as_hex, "euler-v1")
        self.assertTrue(out["covered"])
        a = view(self.r, "get_attestation", 0)
        self.assertTrue(a["covered"])
        self.assertEqual(a["cover_id"], 1)

    def test_attest_uncovered(self):
        out = send_reg(self.r, STRANGER, "attest", BOB.as_hex, "euler-v1")
        self.assertFalse(out["covered"])

    def test_bad_address(self):
        self.assertFalse(view(self.r, "is_covered", "nope", "euler-v1"))
        self.assertEqual(view(self.r, "get_active_cover", "nope")["items"], [])

    def test_config(self):
        cfg = view(self.r, "get_config")
        self.assertFalse(cfg["custody"])
        self.assertEqual(cfg["payable_methods"], 0)

    def test_demo_flag_passes_through(self):
        c = fresh(demo=True)
        CONTRACTS[CC_ADDR] = c
        pid = make_pool(c)
        buy(c, pid)
        out = send_reg(self.r, STRANGER, "attest", ALICE.as_hex, "euler-v1")
        a = view(self.r, "get_attestation", 0)
        self.assertTrue(a["demo"])
        self.assertFalse(out["covered"])   # a demo cover's end is in the past


def send_reg(r, who, method, *args):
    MESSAGE.sender_address = who
    MESSAGE.value = 0
    return getattr(r, method)(*args)


if __name__ == "__main__":
    unittest.main(verbosity=1)
