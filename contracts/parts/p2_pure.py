

def _flat(s: typing.Any) -> str:
    """Collapse whitespace. A stored string with a newline in it breaks every
    CSV and every log line downstream."""
    return " ".join(str(s).split())


def _clean(s: typing.Any, n: int) -> str:
    """Flattened, control-stripped, length-capped. Everything that reaches
    storage from calldata goes through here, once, at the boundary."""
    out = []
    for ch in _flat(s):
        o = ord(ch)
        if o < 32 or o == 127:
            continue
        out.append(ch)
        if len(out) >= n:
            break
    return "".join(out)


def _short(s: typing.Any, n: int = 120) -> str:
    t = str(s)
    return t if len(t) <= n else t[:n]


def _as_int(v: typing.Any, default: int = 0) -> int:
    """An int from whatever arrived on calldata. `bool` is excluded ON PURPOSE:
    Python makes `True` an int of value 1, so a boolean would silently read as
    1 rather than as junk."""
    if isinstance(v, bool):
        return default
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        t = v.strip()
        neg = t.startswith("-")
        if neg:
            t = t[1:]
        if t == "" or not t.isdigit():
            return default
        return -int(t) if neg else int(t)
    return default


def _as_bool(v: typing.Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return _as_int(v, 0) != 0


def _clamp(v: int, lo: int, hi: int) -> int:
    return lo if v < lo else (hi if v > hi else v)


def _rank(n: int, ladder: tuple) -> int:
    """How many of the ladder's lower bounds `n` has reached. The one place a
    bucket edge is interpreted in this file."""
    r = 0
    for bound in ladder:
        if n >= bound:
            r += 1
    return r


def _is_addr(text: typing.Any) -> bool:
    """A 0x-prefixed 20-byte hex string, checked character by character BEFORE
    `Address()` is constructed from it, because `Address("nonsense")` raises
    and rule 2 says nothing in this file may."""
    t = str(text).strip()
    if len(t) != 42 or not t.startswith("0x"):
        return False
    for ch in t[2:]:
        if ch not in "0123456789abcdefABCDEF":
            return False
    return True


def _lower(text: typing.Any) -> str:
    return str(text).strip().lower()


def _days_from_civil(y: int, m: int, d: int) -> int:
    """Days from 1970-01-01 to a civil date. Howard Hinnant's algorithm, written
    out so that a date routine on the consensus axis is one anybody can check."""
    y -= 1 if m <= 2 else 0
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def _civil_from_days(z: int) -> tuple:
    """The inverse: (y, m, d) from days since 1970-01-01. Hinnant again."""
    z += 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    return (y + (1 if m <= 2 else 0), m, d)


def _epoch_from_iso(value: typing.Any) -> int:
    """Seconds since the epoch from an ISO-8601 instant, by hand.

    The source is `gl.message.raw["datetime"]` - the block time, which is part
    of the transaction and therefore IDENTICAL on every validator. There is no
    block.timestamp on this chain, and a wall clock read per node would put the
    difference between two nodes' clocks on the consensus axis."""
    if not isinstance(value, str) or len(value) < 19:
        return 0
    try:
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        hour = int(value[11:13])
        minute = int(value[14:16])
        second = int(value[17:19])
    except Exception:
        return 0
    if month < 1 or month > 12 or day < 1 or day > 31:
        return 0
    if hour > 23 or minute > 59 or second > 60:
        return 0
    return (_days_from_civil(year, month, day) * 86400
            + hour * 3600 + minute * 60 + second)


def _day_of(epoch: int) -> int:
    """Midnight UTC of the day `epoch` falls in. Incident dates are DAY
    precision: DeFi Llama records them that way, and a claim that turned on the
    hour of an exploit would be a claim decided by whoever guessed the hour."""
    e = int(epoch)
    return e - (e % DAY) if e >= 0 else 0


def _date_text(epoch: typing.Any) -> str:
    """"2023-03-13" from an epoch. Integer arithmetic; no datetime import."""
    e = _as_int(epoch, 0)
    if e <= 0:
        return ""
    y, m, d = _civil_from_days(e // DAY)
    return (str(y) + "-" + ("0" + str(m))[-2:] + "-" + ("0" + str(d))[-2:])


def _fnv(s: str) -> str:
    """FNV-1a, 64-bit, hex. The content hash. Written out rather than imported
    because it must produce the same digest on every validator and years later
    inside `verify_claim`."""
    h = 0xCBF29CE484222325
    for ch in s:
        h ^= ord(ch) & 0xFF
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return format(h, "016x")


def _gen(wei: typing.Any) -> str:
    """Wei as a decimal GEN string, by integer arithmetic only. There is not
    one float in this file: a float in a nondet return is not calldata
    encodable, and a float in a settlement puts a rounding mode on the
    consensus axis."""
    n = _as_int(wei, 0)
    sign = "-" if n < 0 else ""
    n = -n if n < 0 else n
    whole = n // 10 ** 18
    frac = n % 10 ** 18
    text = str(frac)
    while len(text) < 18:
        text = "0" + text
    while len(text) > 2 and text[-1] == "0":
        text = text[:-1]
    return sign + str(whole) + "." + text


def _pct(bps: typing.Any) -> str:
    """Basis points as "12.34%"."""
    n = _as_int(bps, 0)
    sign = "-" if n < 0 else ""
    n = -n if n < 0 else n
    return sign + str(n // 100) + "." + ("0" + str(n % 100))[-2:] + "%"


def _err_text(e: typing.Any) -> str:
    """The text out of a raised error or a returned VM result. `UserError`
    carries `.data` on v0.6 where the old SDK carried `.message`; reading the
    wrong one returns "" and an empty message makes every comparison succeed."""
    for attr in ("data", "message"):
        got = getattr(e, attr, None)
        if isinstance(got, str) and got != "":
            return got
    return str(e)


# --- text measurement (rule 9) -------------------------------------------------


def _norm(text: typing.Any) -> str:
    """Lower-cased, every non-alphanumeric a space, whitespace collapsed. THE
    one normal form: indicator phrases, protocol names, the digest and the
    content hash all meet text in this shape and no other."""
    out = []
    for ch in str(text).lower():
        out.append(ch if ch.isalnum() else " ")
    return " ".join("".join(out).split())


def _has(padded: str, phrase: str) -> bool:
    """Does a normalised phrase occur in `padded` (normalised text with a space
    at each end) STARTING AT A WORD BOUNDARY?

    Start-anchored rather than a bare substring, so "dns" does not fire inside
    "sdns" and "mpc" not inside some longer token; open at the end, so
    "oracle" also finds "oracles" and "impersonat" finds "impersonation"."""
    return (" " + phrase) in padded


def _hits_of(norm_text: str, table: dict, order: tuple) -> list:
    """The vocabulary items (in vocabulary order) at least one of whose
    indicator phrases occurs in the text. DISTINCT items, not occurrences: an
    article that says "oracle" nine times has named one risk nine times."""
    padded = " " + norm_text + " "
    out = []
    for item in order:
        for phrase in table.get(item, ()):
            if _has(padded, phrase):
                out.append(item)
                break
    return out


def _names_protocol(norm_text: str, protocol_name: str) -> bool:
    """Does the text name this pool's protocol? Word-aligned at BOTH ends, so
    "Aave" does not match "Aavegotchi" and "Curve" is found in "Curve's"."""
    want = _norm(protocol_name)
    if want == "":
        return False
    return (" " + want + " ") in (" " + norm_text + " ")


def _sentences(text: typing.Any) -> list:
    """`text` split into the smallest units that carry a claim, in order, each
    returned twice: as written (flattened), and as a COMPARISON KEY - the
    normal form - so that re-typing or re-punctuating a sentence is recognised
    as the same sentence. Ported from GrantJudge."""
    out = []
    piece = []
    flat = _flat(text)
    n = len(flat)
    for i in range(n + 1):
        end = i == n
        if not end:
            ch = flat[i]
            piece.append(ch)
            if ch not in ".!?;":
                continue
            # A point ends a sentence only when WHITESPACE (or the end)
            # follows it. So "0.6 GEN" and "$1.5M" stay whole - GrantJudge's
            # rule - and so do "curve.fi" and every URL: measured on the
            # rekt.news Curve article, where "curve.fi" split one sentence.
            if ch == "." and i + 1 < n and flat[i + 1] != " ":
                continue
        written = _flat("".join(piece))
        piece = []
        key = _norm(written)
        if key == "":
            continue
        out.append((written, key))
    return out


def _novel(evidence: typing.Any, prior: typing.Any) -> str:
    """The part of `evidence` that `prior` did not already say. NEVER RAISES.

    THE CONTEST'S GUARD, reused from GrantJudge where it closed a real hole: an
    appeal that re-sent its own filing was re-read as if it had been written
    twice, and the extra length moved the result. Here the same attack would be
    a contest that re-submits the evidence already judged - or re-punctuates
    it, or repeats one sentence five times - to buy a second reading of the
    same facts.

    A sentence counts as already said if its normal form is CONTAINED in any
    prior sentence's normal form (so half a sentence, or one split in two, is
    still a repeat), and a sentence repeated inside the new evidence itself
    counts once. What survives is only what is genuinely new."""
    prior_keys = []
    for _, key in _sentences(prior):
        prior_keys.append(" " + key + " ")
    out = []
    seen = []
    for written, key in _sentences(evidence):
        probe = " " + key + " "
        already = False
        for old in prior_keys:
            if probe in old:
                already = True
                break
        if already or probe in seen:
            continue
        seen.append(probe)
        out.append(written)
    return _flat(" ".join(out))


def _digest(text: typing.Any, protocol_name: str, cap: int) -> str:
    """The SALIENT sentences of one page: those that name the protocol or carry
    an indicator phrase, in page order, each capped, the whole capped.

    This is what the model reads, what is hashed, what is stored on the claim
    and what a contest's novelty is measured against. Keeping only salient
    sentences is also what makes two renders of one page agree: navigation,
    cookie banners, share buttons and footers carry neither the protocol's name
    nor a peril, so the noise that differs between two page loads never reaches
    the hash.

    SPLIT ON LINES FIRST, AND A SENTENCE NEEDS MIN_SENTENCE_WORDS WORDS. Both
    were measured, not guessed: a rendered page is line-broken text, and Euler's
    own post-mortem renders its navigation bar as "Governance | Developers |
    Community ..." (docs/PROBE.md). Flattened, that bar and the article's first
    line became one "sentence" naming both Euler and governance - an exclusion
    indicator put into the bracket by a menu. A menu item is a line of one or
    two words; a claim about an incident is not.

    INDICATOR SENTENCES FIRST. A long post-mortem names its protocol in almost
    every sentence, and filling the cap in page order spent it on the
    protocol's history before reaching the paragraph about the flaw - measured
    on Euler's own post-mortem, whose first 2,400 salient characters named no
    risk at all. So sentences carrying an indicator phrase are taken first,
    name-only sentences fill what is left, and the result is put back in page
    order. Deterministic: a pure function of the text."""
    name = _norm(protocol_name)
    cands = []
    for line in str(text).split("\n"):
        for written, key in _sentences(line):
            if len(key.split(" ")) < MIN_SENTENCE_WORDS:
                continue
            padded = " " + key + " "
            hit = False
            for table in (PERIL_WORDS, EXCLUSION_WORDS):
                for item in table:
                    for phrase in table[item]:
                        if _has(padded, phrase):
                            hit = True
                            break
                    if hit:
                        break
                if hit:
                    break
            named = name != "" and (" " + name + " ") in padded
            if not hit and not named:
                continue
            piece = written if len(written) <= MAX_SENTENCE else written[:MAX_SENTENCE]
            cands.append((len(cands), piece, hit))
    chosen = []
    used = 0
    for want in (True, False):
        for idx, piece, hit in cands:
            if hit != want:
                continue
            if used + len(piece) + 1 > cap:
                continue
            chosen.append((idx, piece))
            used += len(piece) + 1
    chosen.sort()
    return " ".join([p for _, p in chosen])


# --- the evidence allowlist (rule 5) --------------------------------------------


def _valid_domain(d: typing.Any) -> bool:
    """A bare lower-case host name: letters, digits, dots and hyphens, at least
    one dot, no leading/trailing dot or hyphen, no empty label."""
    t = str(d)
    if len(t) < 4 or len(t) > 80 or "." not in t:
        return False
    for ch in t:
        if not (ch.isalnum() and ch.isascii()) and ch not in ".-":
            return False
        if ch.isalpha() and not ch.islower():
            return False
    for label in t.split("."):
        if label == "" or label.startswith("-") or label.endswith("-"):
            return False
    return True


def _host_of(url: typing.Any) -> str:
    """The host of an https URL, or "" if it is not one this contract will read.

    Strict on purpose, because every relaxation is a way to launder a random
    blog past the allowlist:
      - https only; no other scheme, no scheme-relative URL;
      - no userinfo (`https://rekt.news@evil.com/` is a request to evil.com);
      - no port, no backslash, no whitespace, no non-ASCII (no homoglyphs);
      - the host is lower-cased and must be a valid domain."""
    t = str(url).strip()
    if len(t) < 12 or len(t) > MAX_URL_LEN:
        return ""
    if not t.lower().startswith("https://"):
        return ""
    for ch in t:
        o = ord(ch)
        if o <= 32 or o >= 127 or ch == "\\":
            return ""
    rest = t[8:]
    cut = len(rest)
    for sep in ("/", "?", "#"):
        k = rest.find(sep)
        if k >= 0 and k < cut:
            cut = k
    authority = rest[:cut]
    if "@" in authority or ":" in authority or authority == "":
        return ""
    host = authority.lower()
    if host.endswith("."):
        host = host[:-1]
    return host if _valid_domain(host) else ""


def _host_allowed(host: str, domains: list) -> bool:
    """`host` IS an allowlisted domain or a SUBDOMAIN of one. Suffix-with-a-dot,
    never a bare suffix: "evilrekt.news" is not "rekt.news"."""
    for d in domains:
        if host == d or host.endswith("." + d):
            return True
    return False


def _archived_target(url: str) -> str:
    """The original URL inside a web.archive.org snapshot URL
    (`https://web.archive.org/web/<timestamp>[id_]/<original>`), or ""."""
    t = str(url).strip()
    marker = "web.archive.org/web/"
    k = t.find(marker)
    if k < 0:
        return ""
    rest = t[k + len(marker):]
    slash = rest.find("/")
    if slash <= 0:
        return ""
    stamp = rest[:slash]
    digits = stamp
    if digits.endswith("id_"):
        digits = digits[:-3]
    if digits == "" or not digits.isdigit():
        return ""
    return rest[slash + 1:]


def _check_url(url: typing.Any, domains: list) -> str:
    """"" if `url` may be used as evidence for a pool with this allowlist, else
    the reason it may not. MECHANICAL, and run before GenLayer is asked
    anything (rule 5).

    THE ARCHIVE IS NOT A LOOPHOLE. web.archive.org is allowlisted as a
    FALLBACK for a page on the allowlist that has since moved or died - so an
    archive URL is accepted only if the page it archives is itself on the
    allowlist. Otherwise anybody could publish a blog post, archive it, and
    submit the snapshot."""
    host = _host_of(url)
    if host == "":
        return "not an https URL this contract will read: " + _short(url, 80)
    if host == "api.llama.fi":
        return ("api.llama.fi is read by the contract itself for every claim; "
                "submit the article or post-mortem instead")
    if not _host_allowed(host, domains):
        return host + " is not on this pool's frozen evidence allowlist"
    if host == ARCHIVE_HOST:
        inner = _archived_target(str(url))
        if inner == "":
            return "a web.archive.org URL must be a /web/<timestamp>/<url> snapshot"
        if not inner.lower().startswith("http"):
            return "the archived page is not an http(s) URL"
        inner_https = inner
        if inner_https.lower().startswith("http://"):
            inner_https = "https://" + inner_https[7:]
        inner_host = _host_of(inner_https)
        if inner_host == "" or inner_host == ARCHIVE_HOST:
            return "the archived page is not a URL this contract will read"
        others = []
        for d in domains:
            if d != ARCHIVE_HOST:
                others.append(d)
        if not _host_allowed(inner_host, others):
            return ("the archived page is on " + inner_host + ", which is not "
                    "on this pool's allowlist - an archive only stands in for "
                    "an allowlisted page")
    return ""


def _split_urls(text: typing.Any) -> list:
    """URLs from a comma-, space- or newline-separated string, in order."""
    out = []
    word = []
    for ch in str(text) + " ":
        if ch in " ,\n\t\r":
            if word:
                out.append("".join(word))
                word = []
            continue
        word.append(ch)
    return out


def _url_key(url: str) -> str:
    """A URL's identity for the one-URL-once rule: lower-cased, scheme and
    trailing slash dropped, so `https://rekt.news/x/` and `https://REKT.news/x`
    are the same evidence."""
    t = str(url).strip().lower()
    if t.startswith("https://"):
        t = t[8:]
    while t.endswith("/"):
        t = t[:-1]
    return t


def _parse_urls(text: typing.Any, domains: list) -> tuple:
    """(urls, error). 1..MAX_URLS distinct allowlisted URLs, or a reason."""
    raw = _split_urls(text)
    if len(raw) == 0:
        return ([], "at least one evidence URL is required")
    if len(raw) > MAX_URLS:
        return ([], "at most " + str(MAX_URLS) + " evidence URLs per filing")
    urls = []
    keys = []
    for u in raw:
        why = _check_url(u, domains)
        if why:
            return ([], why)
        k = _url_key(u)
        if k in keys:
            return ([], "the same evidence URL was given twice")
        keys.append(k)
        urls.append(str(u).strip())
    return (urls, "")


def _parse_list(text: typing.Any, vocab: tuple, allow_empty: bool) -> tuple:
    """(items, error). Comma-separated vocabulary items, upper-cased, distinct,
    returned IN VOCABULARY ORDER so that two pools with the same cover produce
    the same policy hash whatever order their creator typed."""
    want = []
    for part in str(text).split(","):
        p = part.strip().upper()
        if p == "":
            continue
        if p not in vocab:
            return ([], p + " is not in the fixed vocabulary " + ",".join(vocab))
        if p in want:
            return ([], p + " is listed twice")
        want.append(p)
    if len(want) == 0 and not allow_empty:
        return ([], "at least one of " + ",".join(vocab) + " is required")
    out = []
    for v in vocab:
        if v in want:
            out.append(v)
    return (out, "")


def _parse_table(text: typing.Any) -> tuple:
    """(table, error). Five payout percentages in bps, one per severity bucket,
    non-decreasing, each 0..10000. Empty means the default table."""
    t = str(text).strip()
    if t == "":
        return (list(DEFAULT_PAYOUT_TABLE), "")
    parts = t.split(",")
    if len(parts) != BUCKETS:
        return ([], "the payout table needs exactly " + str(BUCKETS) + " entries")
    out = []
    for p in parts:
        v = _as_int(p.strip(), -1)
        if v < 0 or v > BPS:
            return ([], "payout table entries are basis points 0..10000")
        if len(out) > 0 and v < out[-1]:
            return ([], "the payout table must not decrease with severity")
        out.append(v)
    return (out, "")


def _parse_domains(text: typing.Any) -> tuple:
    """(domains, error). The protocol's official domain(s), added to the base
    allowlist. Lower-case bare hosts; a scheme or path is stripped."""
    out = []
    for part in str(text).split(","):
        p = part.strip().lower()
        if p == "":
            continue
        if p.startswith("https://"):
            p = p[8:]
        if p.startswith("http://"):
            p = p[7:]
        if p.startswith("www."):
            p = p[4:]
        k = p.find("/")
        if k >= 0:
            p = p[:k]
        if not _valid_domain(p):
            return ([], "not a domain: " + _short(part, 60))
        if p in BASE_DOMAINS:
            continue
        if p == "llama.fi" or p.endswith(".llama.fi"):
            return ([], "api.llama.fi is read by the contract itself")
        if p not in out:
            out.append(p)
    if len(out) > MAX_OFFICIAL_DOMAINS:
        return ([], "at most " + str(MAX_OFFICIAL_DOMAINS) + " official domains")
    return (out, "")


# --- money (rule 7: integers only, every rounding direction written down) ------


def _ceil_div(a: int, b: int) -> int:
    return -((-a) // b)


def _premium(amount: int, rate_bps: int, days: int) -> int:
    """premium = cover x rate x days / 30, in wei. ROUNDED UP to the wei, so the
    pool is never paid less than its own rate; the rounding is at most one wei
    and the buyer is told the exact figure before paying."""
    if amount <= 0 or rate_bps <= 0 or days <= 0:
        return 0
    return _ceil_div(amount * rate_bps * days, 30 * BPS)


def _lock(amount: int, collateral_bps: int) -> int:
    """Capital locked against one cover. ROUNDED UP: a lock that is short by a
    wei is a pool that promised more than it held."""
    if amount <= 0:
        return 0
    return _ceil_div(amount * collateral_bps, BPS)


def _gross(amount: int, table_bps: int, deductible_bps: int) -> int:
    """payout = cover x payout_table[bucket] x (1 - deductible). ONE division,
    rounded DOWN, so the product of two fractions is never rounded twice."""
    if amount <= 0 or table_bps <= 0 or deductible_bps >= BPS:
        return 0
    return amount * table_bps * (BPS - deductible_bps) // (BPS * BPS)


def _prorata(grosses: list, available: int) -> tuple:
    """(payouts, dust). THE PRO-RATA SPLIT, not first-come.

    If what was approved fits in what is available, everybody gets their gross
    payout. If not, every claim is scaled by the SAME factor, available/total,
    rounded down per claim - so the order claims were filed or judged in
    changes nothing - and the rounding dust stays with the underwriter."""
    total = 0
    for g in grosses:
        total += int(g)
    if total <= available:
        return ([int(g) for g in grosses], 0)
    out = []
    paid = 0
    for g in grosses:
        share = int(g) * available // total if total > 0 else 0
        out.append(share)
        paid += share
    return (out, available - paid)


def _refund(premium: int, total_s: int, remaining_s: int) -> int:
    """Pro-rata premium refund for an unused period, ROUNDED DOWN (the dust is
    earned premium)."""
    if premium <= 0 or total_s <= 0 or remaining_s <= 0:
        return 0
    if remaining_s >= total_s:
        return premium
    return premium * remaining_s // total_s


def _bucket(drop_bps: int) -> int:
    return _rank(int(drop_bps), SEVERITY_EDGES_BPS)


def _drop(before: int, low: int) -> int:
    """TVL drop in bps, 0..10000, rounded DOWN. A drop that cannot be measured
    - no TVL before, no point after - is ZERO, which is bucket 0, which pays
    nothing: conservative (rule 8)."""
    if before <= 0 or low < 0 or low >= before:
        return 0
    return (before - low) * BPS // before


def _csv(items: list) -> str:
    return ",".join([str(x) for x in items])


def _split_csv(text: typing.Any) -> list:
    out = []
    for p in str(text).split(","):
        p = p.strip()
        if p != "":
            out.append(p)
    return out


def _policy_text(name: str, slug: str, llama_id: str, chain: str,
                 perils: list, exclusions: list, rate_bps: int,
                 waiting_days: int, deductible_bps: int, max_cover: int,
                 term_days: int, collateral_bps: int, table: list,
                 domains: list, wording: str, declared: str = "") -> str:
    """The canonical wording of a policy: every frozen term, in a fixed order,
    in plain English. Stored nowhere - it is re-derived from the stored terms,
    hashed into `policy_hash`, and shown by `get_policy` - so the text a buyer
    reads and the terms a claim is judged against cannot come apart."""
    lines = ["CoverClaim policy v" + POLICY_VERSION,
             "Protocol: " + name + " (DeFi Llama " + slug + ", id " + llama_id
             + ") on " + chain,
             "Covered perils:"]
    for p in perils:
        lines.append("  " + p + " - " + PERIL_TEXT.get(p, ""))
    lines.append("Exclusions:")
    for x in exclusions:
        lines.append("  " + x + " - " + EXCLUSION_TEXT.get(x, ""))
    lines.append("Premium: " + _pct(rate_bps) + " of cover per 30 days")
    lines.append("Waiting period: " + str(waiting_days) + " days from cover start")
    lines.append("Deductible: " + _pct(deductible_bps) + " of the severity payout")
    lines.append("Max cover per buyer: " + _gen(max_cover) + " GEN")
    lines.append("Pool term: " + str(term_days) + " days")
    lines.append("Collateral: " + _pct(collateral_bps) + " of cover locked per cover")
    edges = ["<10%", "10-30%", "30-60%", "60-90%", ">=90%"]
    rows = []
    for i in range(BUCKETS):
        rows.append(edges[i] + " TVL drop -> " + _pct(table[i]))
    lines.append("Payout by severity: " + "; ".join(rows))
    lines.append("Evidence allowlist: " + ", ".join(domains) + " + the website "
                 "DeFi Llama lists for protocol id " + llama_id + ", confirmed by "
                 "verify_pool (declared: " + (declared if declared else "none")
                 + "); no other domain, and none if DeFi Llama lists none or "
                 "lists a shared publishing host")
    lines.append("Claims: a claim names ONE DeFi Llama incident record of this "
                 "protocol by key (id:YYYY-MM-DD[:name]) dated inside the cover "
                 "after the waiting period; the evidence must name the protocol "
                 "and date the same event within " + str(BIND_WINDOW_DAYS)
                 + " days of that record, or the claim is EVIDENCE_MISMATCH")
    if wording:
        lines.append("Underwriter's notes: " + wording)
    return "\n".join(lines)


# --- the event binding: dates, keys, the TVL window (pure) -----------------------


def _day_token(t: str) -> int:
    """1..31 from "7", "07", "7th", "31st"; 0 for anything else."""
    k = 0
    while k < len(t) and t[k].isdigit():
        k += 1
    if k == 0 or k > 2:
        return 0
    rest = t[k:]
    if rest not in ("", "st", "nd", "rd", "th"):
        return 0
    d = int(t[:k])
    return d if d >= 1 and d <= 31 else 0


def _year_token(t: str) -> int:
    if len(t) != 4 or not t.isdigit():
        return 0
    y = int(t)
    return y if y >= 1990 and y <= 2099 else 0


def _civil_ok(y: int, m: int, d: int) -> bool:
    """Is (y, m, d) a real calendar day? February 30th round-trips to March."""
    if y <= 0 or m < 1 or m > 12 or d < 1 or d > 31:
        return False
    return _civil_from_days(_days_from_civil(y, m, d)) == (y, m, d)


def _dates_in(norm_text: str, cap: int) -> list:
    """Every calendar date WRITTEN in a normalised text, as midnight-UTC epochs,
    distinct, in page order, at most `cap`. PURE and hand-written: it is on the
    consensus axis, because it decides which evidence pages are about the
    selected incident.

    Forms read (after `_norm`, which has already dropped the punctuation):
      "july 31 2023", "jul 31st", "31 july 2023", "2023 07 31" (ISO).
    A date written WITHOUT a year ("on July 7th") takes the year of the last
    dated mention before it in the page - rekt.news heads every article with
    its full publication date - or, if none precedes it, the first year the
    page writes. A page that never writes a year contributes no dates."""
    w = norm_text.split(" ")
    n = len(w)
    found = []
    i = 0
    while i < n:
        t = w[i]
        m = MONTHS.get(t, 0)
        if m > 0 and i + 1 < n and _day_token(w[i + 1]) > 0:
            y = _year_token(w[i + 2]) if i + 2 < n else 0
            found.append((y, m, _day_token(w[i + 1])))
            i += 3 if y > 0 else 2
            continue
        d = _day_token(t)
        if d > 0 and i + 1 < n and MONTHS.get(w[i + 1], 0) > 0:
            y = _year_token(w[i + 2]) if i + 2 < n else 0
            found.append((y, MONTHS[w[i + 1]], d))
            i += 3 if y > 0 else 2
            continue
        y = _year_token(t)
        if y > 0 and i + 2 < n and len(w[i + 1]) == 2 and len(w[i + 2]) == 2 \
                and w[i + 1].isdigit() and w[i + 2].isdigit():
            found.append((y, int(w[i + 1]), int(w[i + 2])))
            i += 3
            continue
        i += 1
    first_year = 0
    for f in found:
        if f[0] > 0:
            first_year = f[0]
            break
    out = []
    ctx = first_year
    for f in found:
        y = f[0]
        if y > 0:
            ctx = y
        else:
            y = ctx
        if not _civil_ok(y, f[1], f[2]):
            continue
        e = _days_from_civil(y, f[1], f[2]) * DAY
        if e not in out:
            out.append(e)
            if len(out) >= cap:
                break
    return out


def _nearest(days: list, target: int) -> int:
    """The date in `days` closest to `target` (the earlier on a tie), or -1."""
    best = -1
    gap = -1
    for d in days:
        g = d - target if d >= target else target - d
        if gap < 0 or g < gap:
            best = d
            gap = g
    return best


def _parse_key(text: typing.Any) -> tuple:
    """(canonical key, llama id, incident day epoch, record name, why) from an
    incident key "<llama id>:<YYYY-MM-DD>[:<record name>]". `why` is "" when
    the key is well formed. The key names ONE DeFi Llama hacks record: the id
    is the record's `defillamaId`, the date its day, and the name - optional -
    tells apart two records of one protocol on one day."""
    t = _clean(text, MAX_KEY)
    if t == "":
        return ("", "", 0, "", "an incident key is required: <DeFi Llama id>:"
                "<YYYY-MM-DD>[:<record name>], naming one record of "
                "api.llama.fi/hacks")
    k = t.find(":")
    if k <= 0:
        return ("", "", 0, "", "incident key " + _short(t, 60) + " is not "
                "<id>:<YYYY-MM-DD>[:<name>]")
    lid = t[:k].strip()
    rest = t[k + 1:]
    k2 = rest.find(":")
    date = (rest if k2 < 0 else rest[:k2]).strip()
    name = "" if k2 < 0 else _clean(rest[k2 + 1:], MAX_KEY_NAME)
    if lid == "" or not lid.isdigit() or len(lid) > 20:
        return ("", "", 0, "", "the incident key's id must be the numeric "
                "DeFi Llama id")
    ok = len(date) == 10 and date[4] == "-" and date[7] == "-" \
        and date[:4].isdigit() and date[5:7].isdigit() and date[8:].isdigit()
    if not ok or not _civil_ok(int(date[:4]), int(date[5:7]), int(date[8:])):
        return ("", "", 0, "", "the incident key's date must be a real day "
                "written YYYY-MM-DD")
    day = _days_from_civil(int(date[:4]), int(date[5:7]), int(date[8:])) * DAY
    key = lid + ":" + date + (":" + name if name else "")
    return (key, lid, day, name, "")


def _parse_tvl_line(line: str) -> dict:
    """The TVL window read back out of a stored `tvl_line`, so `verify_claim`
    can recompute severity from the points the claim was judged on. {} when
    the line records no TVL history."""
    w = str(line).split(" ")
    if len(w) < 12 or w[0] != "TVL" or w[1] != "id":
        return {}
    out = {"doc_id": w[2], "anchor": "", "before_day": "", "before": -1,
           "points": [], "low": -1, "count": 0}
    i = 3
    while i + 1 < len(w):
        tag = w[i]
        val = w[i + 1]
        if tag == "anchor":
            out["anchor"] = val
        elif tag == "before":
            k = val.find("=")
            out["before_day"] = val[:k] if k > 0 else ""
            out["before"] = _as_int(val[k + 1:] if k > 0 else val, -1)
        elif tag == "window":
            pts = []
            if val != "-":
                for item in val.split(";"):
                    k = item.find("=")
                    if k > 0:
                        pts.append([item[:k], _as_int(item[k + 1:], -1)])
            out["points"] = pts
        elif tag == "low":
            out["low"] = _as_int(val, -1)
        elif tag == "points":
            out["count"] = _as_int(val, 0)
        i += 2
    return out


# --- pool verification (pure) ------------------------------------------------------


def _website_domain(url: typing.Any) -> str:
    """The protocol domain DeFi Llama's listed website allows: its https host
    without a leading "www.", or "" when there is no usable website - none
    listed, not https, a shared publishing host anyone can post on, or a host
    the contract already reads for itself."""
    host = _host_of(str(url if url is not None else ""))
    if host.startswith("www."):
        host = host[4:]
    if host == "" or not _valid_domain(host):
        return ""
    if host in SHARED_HOSTS or host in BASE_DOMAINS:
        return ""
    if host == "llama.fi" or host.endswith(".llama.fi"):
        return ""
    return host


def _verify_verdict(facts: dict, raw: dict) -> dict:
    """VERIFIED or FAILED for a pool, from DeFi Llama's protocol record alone.
    PURE: the leader, every validator and `verify_pool` after consensus
    derive it from the same raw fields.

    VERIFIED requires ALL of:
      - /protocol/<slug> exists (a 400 "Protocol not found" is an answer);
      - its `id` is the pool's DeFi Llama id (slug and id are one protocol);
      - the pool's name names DeFi Llama's protocol - word-aligned, and on
        the same first word ("Euler" for "Euler V1") - because the evidence
        must name the pool's protocol, and a pool named for another protocol
        could never be paid;
      - a declared domain, if any, IS the website DeFi Llama lists.
    The protocol domain on the allowlist is then DeFi Llama's website domain
    (or none). The underwriter's text never adds a domain."""
    slug = str(facts.get("llama_slug", ""))
    want_id = str(facts.get("llama_id", ""))
    name = str(facts.get("protocol_name", ""))
    declared = str(facts.get("declared_domain", ""))
    status = _as_int(raw.get("status"), 0)
    out = {"verdict": V_FAILED, "domain": "", "reason": "",
           "llama_name": _clean(raw.get("name", ""), 80),
           "website": _clean(raw.get("url", ""), 200),
           "doc_id": _clean(raw.get("doc_id", ""), 40)}
    if status != 200 or not raw.get("found"):
        out["reason"] = ("DeFi Llama has no protocol with slug " + slug
                         + " (api.llama.fi answered " + str(status) + ")")
        return out
    if out["doc_id"] != want_id:
        out["reason"] = ("slug " + slug + " is DeFi Llama id " + out["doc_id"]
                         + ", not " + want_id + ": slug and id are different "
                         "protocols")
        return out
    ln = _norm(out["llama_name"])
    pn = _norm(name)
    if pn == "" or not _names_protocol(ln, name) or ln.split(" ")[0] != pn.split(" ")[0]:
        out["reason"] = ("the pool is named " + _short(name, 60) + " but DeFi "
                         "Llama id " + want_id + " is " + out["llama_name"]
                         + "; evidence naming the pool's protocol could never "
                         "be about this one")
        return out
    domain = _website_domain(out["website"])
    if declared != "" and declared != domain:
        out["reason"] = ("declared domain " + declared + " is not the website "
                         "DeFi Llama lists for " + out["llama_name"] + " ("
                         + (out["website"] if out["website"] else "none listed")
                         + ")")
        return out
    out["verdict"] = V_VERIFIED
    out["domain"] = domain
    out["reason"] = ("slug " + slug + ", id " + want_id + " and name agree with "
                     "DeFi Llama (" + out["llama_name"] + "); protocol domain: "
                     + (domain if domain else "none - only rekt.news and DeFi "
                        "Llama count"))
    return out
