# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
import genlayer as gl
from genlayer import *
from dataclasses import dataclass
import json
import typing

# CoverClaim - DeFi hack insurance where the claim is judged by GenLayer
# validators instead of a vote of the people who would pay it.
#
# An UNDERWRITER opens a pool for one protocol: they deposit capacity and freeze
# the policy - covered perils, exclusions, evidence domains, premium rate,
# waiting period, deductible, term and the payout table - at creation. A BUYER
# pays a premium for cover against that protocol being exploited. When an
# incident happens, the buyer files a claim with public evidence, anybody
# triggers the judgement, and the money follows from arithmetic.
#
# WHERE THE LINE IS, because the whole design sits on it:
#
#   GenLayer reads public incident evidence and classifies it against the
#   frozen policy's covered perils and exclusions. Deterministic contract logic
#   enforces capacity, waiting periods, backdating checks, premium accounting,
#   severity payouts, deductibles, and pro-rata splits.
#
#   THE MODEL ANSWERS ONE QUESTION - does this incident match a covered peril
#   or an exclusion - and only from inside a bracket this file computes first.
#   Beside it, one bounded check: is the evidence about the SAME event as the
#   incident record the claimant selected (SAME / DIFFERENT / UNCLEAR)?
#
#   ONE EVENT BINDS EVERYTHING. The claimant names ONE DeFi Llama incident
#   record by its key (protocol id : day [: name]). That record - and no
#   other, whatever else the feed contains - supplies the incident DATE; the
#   TVL window for SEVERITY is anchored on that date; an evidence page counts
#   only if it names the protocol and carries a date within BIND_WINDOW_DAYS
#   of it; and the content hash covers the key, the record, the evidence and
#   the TVL window points together. Evidence about a different event is
#   EVIDENCE_MISMATCH: no payout, nothing moves, the claim may be refiled.
#   Every wei comes from integer arithmetic. NOT ONE WEI IS MOVED BY A MODEL.
#   A model that answered nonsense could at worst produce INCONCLUSIVE or
#   EVIDENCE_MISMATCH, which change nothing and can be refiled.
#
# Design notes and hazards: contracts/NOTES.md. Probe measurements that fixed
# the evidence allowlist: docs/PROBE.md.
#
# The two header lines above are the whole of what GenVM reads before the code:
# the version line and the runner pin, in that order. NOTHING else may sit
# between line 1 and the imports - GenVM parses the contiguous leading `#` block
# as the runner header, and a stray comment there makes the contract
# undeployable, reporting nothing but `invalid_contract`.
#
# TWELVE RULES govern everything below. Every one of them is a past rejection
# written down so that it cannot happen again.
#
#   1. CONSENSUS BINDS EVERY STORED VALUE. The compared axis is the WHOLE
#      VERDICT VECTOR: classification, event match, matched peril, matched
#      exclusion, incident key and date, the evidence binding, protocol match,
#      severity bucket (with the TVL window points and drop it came from),
#      evidence strength, the bracket, and the content hash of everything
#      every node read. Nothing is stored that was not compared or re-derived
#      from what was (rule 11).
#
#   2. NO PUBLIC WRITE EVER RAISES. There is not one `raise` statement in this
#      file. A revert rolls back storage but NOT the value that came with the
#      call. Every refusal returns {"status": "REJECTED", "reason": ...} and the
#      value that arrived is already the sender's to withdraw (see `_bank`).
#
#   3. NO COUNTER MOVES BEFORE A PATH THAT CAN STILL REFUSE. Every increment
#      happens after the last possible refusal. `total_rejected` and the
#      judgement-attempt counters are the documented exceptions: they are
#      statistics ABOUT attempts, not records of success.
#
#   4. THE POLICY IS FROZEN WHEN THE POOL IS CREATED. Perils, exclusions,
#      evidence domains, rate, waiting period, deductible, collateral ratio,
#      term and payout table are written once, hashed into `policy_hash`, and
#      there is no setter for any of them anywhere in this file. The offline
#      suite walks the AST to prove it. An underwriter who could narrow the
#      wording after selling cover would be deciding claims in advance.
#
#   5. MECHANICAL REJECTION FIRST, GENLAYER LAST. Capacity, timing, amounts,
#      the per-buyer cap, the claim window, one-claim-per-cover and the
#      evidence allowlist are all checked by this file BEFORE a validator is
#      asked anything. Evidence from a domain the pool did not freeze is refused
#      at `file_claim`, not judged.
#
#   6. THE OWNER CANNOT FREEZE USER MONEY. Pause stops NEW pools, NEW capacity
#      and NEW covers, and nothing else. Filing, judging, refiling, contesting,
#      finalising, releasing, cancelling, withdrawing, closing, settle_stalled
#      and claim_payout are ALL ungated on `paused`, by design and by test.
#
#   7. VALUE THE CONTRACT ACCEPTS IS VALUE SOMEBODY CAN GET BACK OUT. The
#      ledger identity, asserted after every operation offline and published by
#      `get_stats` on chain:
#
#          balance_wei == held_wei + payable_wei
#
#      `held_wei` is the sum over pools of capital + unearned premiums, plus
#      contest bonds in flight. Every terminal path converts held value into
#      somebody's payable balance. There is NO protocol revenue and no owner
#      withdraw method at all. When every cover has expired and every claim has
#      settled, every pool closes to exactly zero.
#
#   8. CONSERVATIVE WHEN THE READING IS NOT THERE. An unreachable source or an
#      unreadable model answer produces a RETRY that changes nothing. Evidence
#      that does not name the protocol, carries no indicator phrase, or points
#      only at risks the policy neither covers nor excludes is INCONCLUSIVE
#      without a model call - and INCONCLUSIVE can be refiled, loses nothing,
#      and never pays.
#
#   9. THE MODEL CHOOSES INSIDE A BRACKET. Before any inference, this file
#      computes which covered perils and which exclusions the evidence text
#      actually mentions, and which evidence strengths the sources can support.
#      The model picks from that list and nowhere else; `_coherent` refuses a
#      leader outside it BY ARITHMETIC, before spending an inference.
#
#  10. THE COMPARISON IS EXACT WHERE MONEY MOVES. Classification, peril,
#      exclusion, incident date, protocol match, severity bucket, TVL figures,
#      drop, bracket, content hash and the EFFECTIVE classification (after the
#      strength floor) are exact. Evidence strength alone carries a tolerance of
#      one step, because two honest readers may differ by one - and the one
#      consequence strength has on money, the COVERED floor, is compared
#      exactly through the effective classification.
#
#  11. NOTHING THE LEADER SENDS IS STORED WITHOUT BEING RECOMPUTED. After
#      consensus returns, the verdict is re-derived from the agreed choice and
#      the agreed reading, the digest is re-hashed, and the deterministic checks
#      (backdating, cover end, payout) are run by this file on stored values.
#
#  12. PAYMENT NEVER READS THE CLOCK. `claim_payout` is the ONLY method that
#      posts a transfer and it does not read the block time. Every method that
#      reads the clock - finalize_incident, release_cover, cancel_cover,
#      withdraw_capacity, close_pool - only CREDITS a payable balance. On Studio
#      Dev a write that both reads the clock and posts a transfer cannot be
#      fee-estimated (the simulator's clock is stale, it takes the refusal
#      branch, budgets no message, and the real call reverts with
#      `out_of message_fee total`) - measured by GrantJudge and AppAudit.
#
# str.replace() is rejected by the runner; slice around find() instead.

POLICY_VERSION = "1.0.0"

BPS = 10000
DAY = 86400

# --- the fixed vocabularies ---------------------------------------------------
#
# A pool picks its covered perils and exclusions FROM THESE LISTS and nowhere
# else. A free-text peril would put the policy's meaning back in the hands of
# whoever reads it, which is the argument this contract exists to end.
PERILS = ("SMART_CONTRACT_BUG", "ORACLE_MANIPULATION", "ECONOMIC_EXPLOIT",
          "BRIDGE_COMPROMISE")
EXCLUSIONS = ("PHISHING", "FRONTEND_HIJACK", "USER_KEY_COMPROMISE",
              "RUG_BY_TEAM", "GOVERNANCE_ATTACK")
NONE = "NONE"

# The policy wording of each item. Frozen here, shown in the UI, sent to the
# model verbatim, and hashed into every pool's policy hash.
PERIL_TEXT = {
    "SMART_CONTRACT_BUG": ("a flaw in the protocol's own smart-contract code "
                           "or its compiler - reentrancy, a logic, accounting "
                           "or rounding error, a missing validation or access-"
                           "control check - that an attacker exploited"),
    "ORACLE_MANIPULATION": ("the attacker moved, spoofed or corrupted a price "
                            "feed or oracle the protocol relied on"),
    "ECONOMIC_EXPLOIT": ("the contracts behaved as written but their economic "
                         "design was gamed - flash-loan driven market "
                         "manipulation, bad risk parameters, liquidation "
                         "cascades"),
    "BRIDGE_COMPROMISE": ("a cross-chain bridge's message verification, proof "
                          "checking, relayers or validator set was defeated"),
}
EXCLUSION_TEXT = {
    "PHISHING": ("users or team members were tricked into signing or revealing "
                 "something - phishing, social engineering, impersonation, "
                 "malware, blind signing"),
    "FRONTEND_HIJACK": ("the website, DNS, CDN or another front end was "
                        "hijacked; the contracts themselves were not flawed"),
    "USER_KEY_COMPROMISE": ("a private key, seed phrase, signer or MPC key held "
                            "by a person or an operator was stolen, leaked or "
                            "seized"),
    "RUG_BY_TEAM": ("the team or an insider took the funds - rug pull, exit "
                    "scam, admin drain, backdoor"),
    "GOVERNANCE_ATTACK": ("control was taken through governance - a malicious "
                          "proposal, vote buying, flash-loan voting"),
}

# --- indicator phrases (rule 9) -----------------------------------------------
#
# Lower-cased phrases matched against the NORMALISED evidence text (letters and
# digits kept, everything else a single space). Not a tokeniser, not a stemmer,
# not a model: a substring test is the only text measurement that cannot drift
# between two runner builds. A phrase is written normalised - "front end", not
# "front-end" - because that is what the text it meets looks like.
#
# DELIBERATELY SPECIFIC. "exploit", "hack", "attack" and "stolen" appear in
# every incident report ever written and so say nothing about WHICH risk
# happened; they are not indicators of anything.
PERIL_WORDS = {
    "SMART_CONTRACT_BUG": ("reentrancy", "re entrancy", "logic flaw",
                           "logic error", "logic bug", "rounding error",
                           "rounding issue", "precision loss", "arithmetic",
                           "overflow", "underflow", "donation", "donatetoreserves",
                           "access control", "missing check", "input validation",
                           "infinite mint", "vulnerability", "vulnerable",
                           "compiler bug", "vyper", "smart contract bug",
                           "contract bug", "code flaw", "bug in the",
                           "uninitialized", "share accounting",
                           "accounting error", "first depositor",
                           "signature verification", "unchecked"),
    "ORACLE_MANIPULATION": ("oracle", "price manipulation", "manipulated the price",
                            "price feed", "spot price", "twap"),
    "ECONOMIC_EXPLOIT": ("flash loan", "flashloan", "flash loaned",
                         "market manipulation", "economic attack",
                         "economic exploit", "risk parameter",
                         "liquidation cascade", "bad debt"),
    "BRIDGE_COMPROMISE": ("bridge", "cross chain", "forged proof",
                          "relayer", "message verification"),
}
EXCLUSION_WORDS = {
    "PHISHING": ("phishing", "phished", "social engineering", "impersonat",
                 "malware", "address poisoning", "blind sign", "fake website"),
    "FRONTEND_HIJACK": ("dns", "front end", "frontend", "cdn", "registrar",
                        "mirrored site", "website was compromised",
                        "ui was compromised", "injected script"),
    "USER_KEY_COMPROMISE": ("private key", "key compromise", "keys were compromised",
                            "compromised key", "held all the keys", "seed phrase",
                            "mnemonic", "hot wallet", "mpc", "signer key",
                            "leaked key", "keys were leaked"),
    "RUG_BY_TEAM": ("rug pull", "rugpull", "rugged", "exit scam", "admin drain",
                    "backdoor", "insider", "misappropriat"),
    "GOVERNANCE_ATTACK": ("governance", "malicious proposal", "voting power",
                          "hostile takeover", "dao takeover"),
}

# DeFi Llama's own classification of an incident, mapped onto the vocabulary.
# Used for EVIDENCE STRENGTH and shown to the model; it never widens the
# bracket, because the bracket is about what the buyer's evidence says.
LLAMA_MAP = {
    "frontend & infrastructure": "FRONTEND_HIJACK",
    "social engineering": "PHISHING",
    "key compromise": "USER_KEY_COMPROMISE",
    "rugpull": "RUG_BY_TEAM",
    "governance": "GOVERNANCE_ATTACK",
    "oracle manipulation": "ORACLE_MANIPULATION",
    "market manipulation": "ECONOMIC_EXPLOIT",
    "bridge & cross-chain": "BRIDGE_COMPROMISE",
    "access control": "SMART_CONTRACT_BUG",
    "protocol logic": "SMART_CONTRACT_BUG",
    "token & share accounting": "SMART_CONTRACT_BUG",
    "input validation": "SMART_CONTRACT_BUG",
    "reentrancy": "SMART_CONTRACT_BUG",
}

# --- classification -------------------------------------------------------------
COVERED = "COVERED"
EXCLUDED = "EXCLUDED"
INCONCLUSIVE = "INCONCLUSIVE"
CLASSIFICATIONS = (COVERED, EXCLUDED, INCONCLUSIVE)
# The EFFECTIVE classification when the evidence is not about the selected
# incident. Never a model option: it follows from `event_match` or from the
# deterministic date binding.
EVIDENCE_MISMATCH = "EVIDENCE_MISMATCH"

# --- the event binding ----------------------------------------------------------
#
# The claimant selects ONE incident record by key: "<llama id>:<YYYY-MM-DD>",
# plus ":<record name>" when two records of the protocol share a day. The
# record is selected by exact match on those fields - never by position in the
# feed and never as "the latest in the window".
#
# An evidence page is BOUND to the record when it names the protocol and a
# date written in it falls within BIND_WINDOW_DAYS of the record's date. A
# page with no date at all is read alongside a bound page but cannot bind on
# its own; a dated page with no date near the record is not read at all. No
# bound page -> EVIDENCE_MISMATCH without a model call.
BIND_WINDOW_DAYS = 3
EVENT_SAME = "SAME"
EVENT_DIFFERENT = "DIFFERENT"
EVENT_UNCLEAR = "UNCLEAR"
EVENT_MATCHES = (EVENT_SAME, EVENT_DIFFERENT, EVENT_UNCLEAR)
EVENT_NOT_ASKED = "NOT_ASKED"
PAGE_BOUND = "BOUND"
PAGE_UNDATED = "UNDATED"
PAGE_UNBOUND = "UNBOUND"
PAGE_UNREAD = "UNREAD"
MAX_PAGE_DATES = 40
MAX_KEY = 120
MAX_KEY_NAME = 80
# How many times a claim may be refiled, FOR ANY REASON COMBINED - after
# INCONCLUSIVE, after EVIDENCE_MISMATCH, or after a stall. Each refile must
# also bring a source or an incident that is genuinely new (see `_url_key`,
# `_same_incident`): the same page re-spelled is not new evidence.
MAX_REFILES = 2
# Generic words DeFi Llama appends to a protocol's name ("Curve DEX", "Euler
# V1"). Articles write "Curve Finance", "Euler Finance". The CORE name - the
# record's name with these trailing words removed - is what evidence must
# name, whatever the underwriter typed.
GENERIC_NAME_WORDS = ("dex", "v1", "v2", "v3", "v4", "v5", "finance",
                      "protocol", "labs", "exchange")
MONTHS = {"jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3,
          "march": 3, "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
          "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9,
          "september": 9, "oct": 10, "october": 10, "nov": 11,
          "november": 11, "dec": 12, "december": 12}

# --- severity (rule 11: from DeFi Llama TVL, by arithmetic) ---------------------
#
# drop_bps = (TVL on the last day BEFORE the incident - lowest TVL in the seven
# days FROM the incident) / TVL before, in basis points. Bucket edges are fixed
# here and published by `get_config`; a pool chooses only the PAYOUT per bucket.
SEVERITY_EDGES_BPS = (1000, 3000, 6000, 9000)      # 10%, 30%, 60%, 90%
SEVERITY_WINDOW_DAYS = 7
# A claim (or contest) is judged only once the whole window has ended: the
# incident day plus SEVERITY_WINDOW_DAYS, plus one day for that last point to
# be published. Judging earlier would fix severity from a partial window.
JUDGE_AFTER_DAYS = SEVERITY_WINDOW_DAYS + 1
# Window points written into the TVL line (and so into the content hash). A
# daily series has at most eight in the window.
MAX_TVL_POINTS = 24
BUCKETS = 5
DEFAULT_PAYOUT_TABLE = (0, 2500, 5000, 7500, 10000)

# --- evidence strength ----------------------------------------------------------
TOP_STRENGTH = 7
STRENGTH_TOLERANCE = 1
# A COVERED reading below this strength is treated as INCONCLUSIVE: the policy
# pays on evidence, and thin evidence is a reason to refile, not to pay.
MIN_COVERED_STRENGTH = 3

# --- evidence -----------------------------------------------------------------
LLAMA_HACKS_URL = "https://api.llama.fi/hacks"
LLAMA_PROTOCOL_URL = "https://api.llama.fi/protocol/"
# The domains every pool carries; the underwriter adds the protocol's own.
# Chosen FROM THE PROBE, not from a wish list (docs/PROBE.md): rekt.news and
# official post-mortems render, and render identically on every validator.
# defillama.com's web UI does NOT - validators get WEBPAGE_LOAD_FAILED - so it
# is not here; DeFi Llama's data reaches a judgement through api.llama.fi,
# which the contract reads itself.
BASE_DOMAINS = ("rekt.news", "web.archive.org")
ARCHIVE_HOST = "web.archive.org"
# One protocol domain at most, and only the website DeFi Llama lists for the
# pool's protocol - confirmed by `verify_pool`, never taken on the
# underwriter's word (a domain the underwriter controls would let them write
# the evidence that decides their own claims).
MAX_OFFICIAL_DOMAINS = 1
# Hosts where ANYONE can publish a page. If DeFi Llama's listed website is one
# of these (a Medium blog, a GitHub org, an X account), no protocol domain is
# allowed at all: rekt.news and DeFi Llama are the only sources.
SHARED_HOSTS = ("medium.com", "github.com", "gitlab.com", "twitter.com", "x.com",
                "t.me", "telegram.me", "discord.gg", "discord.com", "linktr.ee",
                "notion.site", "mirror.xyz", "substack.com", "google.com",
                "docs.google.com", "youtube.com", "reddit.com", "ipfs.io",
                "dweb.link", "facebook.com", "linkedin.com", "paragraph.xyz")
MAX_URLS = 3
MAX_URL_LEN = 300
MAX_STATEMENT = 600
MAX_PAGE_CHARS = 80000
MAX_SENTENCE = 360
MIN_SENTENCE_WORDS = 5
MAX_DIGEST_PER_SOURCE = 2400
MAX_DIGEST = 6000
MIN_NOVEL_CHARS = 20
MAX_REASON = 700

# --- pool shape -----------------------------------------------------------------
MIN_CAPACITY_WEI = 10 ** 18                    # 1 GEN
MIN_COVER_WEI = 10 ** 16                       # 0.01 GEN
MIN_RATE_BPS = 1
MAX_RATE_BPS = 2000                            # 20% per 30 days, a ceiling
DEFAULT_WAITING_DAYS = 7
MAX_WAITING_DAYS = 30
MAX_DEDUCTIBLE_BPS = 5000
MIN_TERM_DAYS = 1
MAX_TERM_DAYS = 365
MIN_COLLATERAL_BPS = 2000
MAX_NAME = 60
MAX_SLUG = 80
MAX_CHAIN = 40
MAX_WORDING = 1500

# --- constructor defaults (the canonical instance) --------------------------------
DEFAULT_CLAIM_WINDOW_S = 30 * DAY
DEFAULT_SETTLEMENT_WINDOW_S = 72 * 3600
DEFAULT_CONTEST_WINDOW_S = 48 * 3600
DEFAULT_STALL_TTL_S = 24 * 3600
DEFAULT_BUY_COOLDOWN_S = 60
DEFAULT_CONTEST_BOND_WEI = 10 ** 17            # 0.1 GEN
MAX_BACKDATE_DAYS = 3650

# --- statuses -------------------------------------------------------------------
# A pool is created UNVERIFIED and sells nothing until `verify_pool` - one
# consensus round against DeFi Llama's protocol record - confirms that its
# slug, id, name and declared domain are one protocol. OPEN means verified.
# FAILED_VERIFICATION can only be closed, returning the underwriter's capital.
POOL_UNVERIFIED = "UNVERIFIED"
POOL_OPEN = "OPEN"
POOL_FAILED = "FAILED_VERIFICATION"
POOL_CLOSED = "CLOSED"
POOL_STATUSES = (POOL_UNVERIFIED, POOL_OPEN, POOL_FAILED, POOL_CLOSED)
V_VERIFIED = "VERIFIED"
V_FAILED = "FAILED"

COVER_ACTIVE = "ACTIVE"
COVER_PAID = "PAID"
COVER_RELEASED = "RELEASED"
COVER_CANCELLED = "CANCELLED"
COVER_STATUSES = (COVER_ACTIVE, COVER_PAID, COVER_RELEASED, COVER_CANCELLED)

CL_FILED = "FILED"
CL_JUDGING = "JUDGING"
CL_INCONCLUSIVE = "INCONCLUSIVE"
CL_APPROVED = "APPROVED"
CL_NO_PAYOUT = "NO_PAYOUT"
CL_DENIED = "DENIED_EXCLUDED"
CL_BACKDATED = "REJECTED_BACKDATED"
CL_AFTER_END = "REJECTED_AFTER_COVER_END"
CL_PAID = "PAID"
# The evidence is not about the selected incident. Pays nothing, moves
# nothing, and - like INCONCLUSIVE - is refiled rather than contested, at most
# MAX_REFILES times in all (every refile reason counts).
CL_MISMATCH = "EVIDENCE_MISMATCH"
CLAIM_STATUSES = (CL_FILED, CL_JUDGING, CL_INCONCLUSIVE, CL_MISMATCH,
                  CL_APPROVED, CL_NO_PAYOUT, CL_DENIED, CL_BACKDATED,
                  CL_AFTER_END, CL_PAID)
# A verdict the losing side may contest. INCONCLUSIVE and EVIDENCE_MISMATCH
# are not: they are refiled.
CL_CONTESTABLE = (CL_APPROVED, CL_NO_PAYOUT, CL_DENIED, CL_BACKDATED,
                  CL_AFTER_END)
# Verdicts that end a claim with nothing owed by the pool.
CL_NONPAYING = (CL_NO_PAYOUT, CL_DENIED, CL_BACKDATED, CL_AFTER_END)

CT_NONE = ""
CT_PENDING = "PENDING"
CT_JUDGING = "JUDGING"
CT_UPHELD = "UPHELD"
CT_FLIPPED = "FLIPPED"
CT_NOT_NOVEL = "NOT_NOVEL"
CT_STALLED = "STALLED"
CONTEST_STATUSES = (CT_PENDING, CT_JUDGING, CT_UPHELD, CT_FLIPPED, CT_NOT_NOVEL,
                    CT_STALLED)
CT_OPEN = (CT_PENDING, CT_JUDGING)

B_OPEN = "OPEN"
B_FINALIZED = "FINALIZED"
