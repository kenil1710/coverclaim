

def _outcome(eff: str, incident_day: int, start: int, end: int, waiting_s: int,
             amount: int, table: list, bucket: int, deductible_bps: int,
             measured: bool = True) -> tuple:
    """(claim status, gross payout wei) from an agreed verdict. PURE, and the
    whole of the deterministic half of a judgement - run by this file on stored
    values after consensus, never by a model.

    The order is the policy's:
      EVIDENCE_MISMATCH   - the evidence is not about the selected incident;
                            nothing is decided about it, nothing pays, and the
                            claim may be refiled;
      INCONCLUSIVE        - nothing was decided; refile with new evidence;
      incident before start + waiting period  -> REJECTED_BACKDATED
                            (the premium is NOT refunded: the cover was valid,
                            the incident simply predates it);
      incident after the cover ended          -> REJECTED_AFTER_COVER_END;
      EXCLUDED            -> DENIED_EXCLUDED;
      COVERED, severity NOT MEASURABLE (no DeFi Llama TVL data around the
                          incident) -> INCONCLUSIVE: missing data is not "no
                          damage", so the claim stays refileable;
      COVERED             -> cover x table[bucket] x (1 - deductible), which is
                            NO_PAYOUT when the severity bucket pays nothing."""
    if eff == EVIDENCE_MISMATCH:
        return (CL_MISMATCH, 0)
    if eff != COVERED and eff != EXCLUDED:
        return (CL_INCONCLUSIVE, 0)
    if incident_day < start + waiting_s:
        return (CL_BACKDATED, 0)
    if incident_day > end:
        return (CL_AFTER_END, 0)
    if eff == EXCLUDED:
        return (CL_DENIED, 0)
    if not measured:
        return (CL_INCONCLUSIVE, 0)
    b = _clamp(int(bucket), 0, BUCKETS - 1)
    pct = int(table[b]) if b < len(table) else 0
    gross = _gross(int(amount), pct, int(deductible_bps))
    if gross <= 0:
        return (CL_NO_PAYOUT, 0)
    return (CL_APPROVED, gross)


# --- storage --------------------------------------------------------------------


@gl.storage.allow
@dataclass
class Pool:
    """One underwriter's capacity for one protocol, and its frozen policy.

    EVERY FIELD FROM `protocol_name` TO `policy_hash` IS WRITTEN ONCE, IN
    `create_pool`, AND NEVER AGAIN (rule 4). The offline suite walks the AST and
    fails if any other method assigns one of them.

    Books: `capital_wei` is everything the underwriter has in the pool, locked
    or not; `locked_wei` is the part of it held against live covers;
    `premiums_held_wei` is premium paid for covers that have not ended yet -
    the underwriter's only once each cover expires or pays."""
    pool_id: u32
    underwriter: Address
    protocol_name: str
    llama_slug: str
    llama_id: str
    chain: str
    perils_csv: str
    exclusions_csv: str
    domains_csv: str
    payout_table_csv: str
    rate_bps: u32
    waiting_days: u32
    deductible_bps: u32
    max_cover_wei: u256
    term_days: u32
    collateral_bps: u32
    wording: str
    policy_hash: str

    created_at: u64
    expires_at: u64
    status: str
    closed_at: u64

    capital_wei: u256
    locked_wei: u256
    premiums_held_wei: u256
    deposited_wei: u256
    withdrawn_wei: u256
    premiums_earned_wei: u256
    refunded_wei: u256
    paid_out_wei: u256
    cover_count: u32
    active_covers: u32
    active_cover_wei: u256
    claim_count: u32


@gl.storage.allow
@dataclass
class Cover:
    """One buyer's cover. `start` is the block time of purchase minus the
    instance's fixed demo backdate (zero on the canonical instance)."""
    cover_id: u32
    pool_id: u32
    buyer: Address
    amount_wei: u256
    premium_wei: u256
    lock_wei: u256
    days: u32
    bought_at: u64
    start: u64
    end: u64
    claim_deadline: u64
    status: str
    claim_id: u32
    settled_at: u64
    refund_wei: u256
    payout_wei: u256


@gl.storage.allow
@dataclass
class Claim:
    """One claim - the one claim a cover gets.

    EVERY FIELD BELOW `--- verdict` IS WRITTEN ONLY FROM AN AGREED, RE-DERIVED
    CONSENSUS VECTOR (rules 1 and 11). The offline suite enumerates this struct
    and fails if a verdict field appears that `_record` does not write from the
    derived vector."""
    claim_id: u32
    cover_id: u32
    pool_id: u32
    claimant: Address
    filed_at: u64
    last_filed_at: u64
    # The ONE DeFi Llama incident record this claim is about, by key. Set at
    # filing; changed only by a refile.
    incident_key: str
    mismatch_refiles: u32
    urls: str
    used_urls: str
    statement: str
    status: str
    refiles: u32
    refile_until: u64
    attempts: u32
    judging_since: u64
    stalls: u32

    # --- verdict
    judged_at: u64
    incident_id: str
    classification: str
    event_match: str
    effective: str
    peril: str
    exclusion: str
    strength: u32
    strength_lo: u32
    strength_hi: u32
    incident_day: u64
    protocol_match: bool
    bind_line: str
    bound: u32
    llama_line: str
    tvl_line: str
    tvl_before: u256
    tvl_low: u256
    drop_bps: u32
    bucket: u32
    sources: u32
    bracket: str
    pinned: str
    model_called: bool
    content_hash: str
    digest: str
    reason: str

    # --- settlement
    table_bps: u32
    gross_wei: u256
    payout_wei: u256
    batch_id: u32

    # --- contest
    contest_status: str
    contester: Address
    contest_bond_wei: u256
    contest_urls: str
    contest_statement: str
    contested_at: u64
    contest_judging_since: u64
    contest_attempts: u32
    contest_resolved_at: u64
    contest_classification: str
    contest_effective: str
    contest_peril: str
    contest_exclusion: str
    contest_strength: u32
    contest_bucket: u32
    contest_drop_bps: u32
    contest_content_hash: str
    contest_novel: str
    contest_reason: str
    status_before_contest: str


@gl.storage.allow
@dataclass
class Batch:
    """The settlement window of one incident on one pool. Every claim approved
    on the same incident while it is open is paid TOGETHER, pro-rata if the
    capacity locked for those covers cannot pay them all in full."""
    batch_id: u32
    pool_id: u32
    incident_id: str
    incident_day: u64
    opened_at: u64
    closes_at: u64
    status: str
    finalized_at: u64
    members: u32
    paid_members: u32
    gross_total_wei: u256
    available_wei: u256
    paid_total_wei: u256
    dust_wei: u256
    scaled: bool


class CoverClaim(gl.contract.Contract):
    # --- ownership. The owner can pause NEW pools, NEW capacity and NEW covers
    # and nothing else (rule 6). There is no owner withdraw method (rule 7).
    owner: Address
    paused: bool

    # --- written once, in the constructor, and never again. The offline suite
    # walks the AST to prove no method assigns any of them.
    demo_backdate_days: u32
    claim_window_s: u64
    settlement_window_s: u64
    contest_window_s: u64
    stall_ttl_s: u64
    buy_cooldown_s: u64
    contest_bond_wei: u256

    # --- the ledger: balance_wei == held_wei + payable_wei, after every call.
    balance_wei: u256
    held_wei: u256
    payable_wei: u256
    payout_wei: gl.storage.TreeMap[Address, u256]

    # --- the register
    pools: gl.storage.DynArray[Pool]
    covers: gl.storage.DynArray[Cover]
    claims: gl.storage.DynArray[Claim]
    batches: gl.storage.DynArray[Batch]
    pools_by_underwriter: gl.storage.TreeMap[Address, gl.storage.DynArray[u32]]
    covers_by_buyer: gl.storage.TreeMap[Address, gl.storage.DynArray[u32]]
    covers_by_pool: gl.storage.TreeMap[str, gl.storage.DynArray[u32]]
    claims_by_pool: gl.storage.TreeMap[str, gl.storage.DynArray[u32]]
    batch_claims: gl.storage.TreeMap[str, gl.storage.DynArray[u32]]
    open_batch: gl.storage.TreeMap[str, u32]
    exposure: gl.storage.TreeMap[str, u256]
    last_buy_at: gl.storage.TreeMap[Address, u64]
    claim_counts: gl.storage.TreeMap[str, u32]

    # --- counters
    total_pools: u256
    total_covers: u256
    total_claims: u256
    total_judge_attempts: u256
    total_judgements: u256
    total_retries: u256
    total_contests: u256
    total_flipped: u256
    total_batches_finalized: u256
    total_scaled_batches: u256
    total_rejected: u256
    total_capacity_wei: u256
    total_premiums_wei: u256
    total_earned_wei: u256
    total_refunds_wei: u256
    total_payouts_wei: u256
    total_claimed_wei: u256

    def __init__(self, demo_backdate_days: int = 0,
                 claim_window_s: int = DEFAULT_CLAIM_WINDOW_S,
                 settlement_window_s: int = DEFAULT_SETTLEMENT_WINDOW_S,
                 contest_window_s: int = DEFAULT_CONTEST_WINDOW_S,
                 stall_ttl_s: int = DEFAULT_STALL_TTL_S,
                 buy_cooldown_s: int = DEFAULT_BUY_COOLDOWN_S,
                 contest_bond_wei: int = DEFAULT_CONTEST_BOND_WEI):
        """Every argument is CLAMPED rather than rejected: a deploy that fails
        on a mistyped argument wastes a deploy, and the bounds are the rule.

        `demo_backdate_days` is the one value that makes an instance a DEMO.
        Zero on the canonical instance, which enforces backdating strictly.
        Non-zero, every cover sold here STARTS that many days before it was
        bought - so a cover bought today can replay a real historical incident.
        It is published by `get_config` as `demo: true` with a label, shown on
        every page of the UI, and cannot be changed after deployment."""
        self.owner = gl.message.sender_address
        self.paused = False
        self.demo_backdate_days = u32(_clamp(_as_int(demo_backdate_days, 0),
                                             0, MAX_BACKDATE_DAYS))
        self.claim_window_s = u64(_clamp(_as_int(claim_window_s,
                                                 DEFAULT_CLAIM_WINDOW_S),
                                         60, 365 * DAY))
        self.settlement_window_s = u64(_clamp(
            _as_int(settlement_window_s, DEFAULT_SETTLEMENT_WINDOW_S),
            60, 30 * DAY))
        self.contest_window_s = u64(_clamp(
            _as_int(contest_window_s, DEFAULT_CONTEST_WINDOW_S), 60, 30 * DAY))
        self.stall_ttl_s = u64(_clamp(_as_int(stall_ttl_s, DEFAULT_STALL_TTL_S),
                                      60, 30 * DAY))
        self.buy_cooldown_s = u64(_clamp(_as_int(buy_cooldown_s,
                                                 DEFAULT_BUY_COOLDOWN_S),
                                         0, DAY))
        self.contest_bond_wei = u256(_clamp(
            _as_int(contest_bond_wei, DEFAULT_CONTEST_BOND_WEI), 10 ** 15,
            10 ** 20))
        self.balance_wei = u256(0)
        self.held_wei = u256(0)
        self.payable_wei = u256(0)
        self.total_pools = u256(0)
        self.total_covers = u256(0)
        self.total_claims = u256(0)
        self.total_judge_attempts = u256(0)
        self.total_judgements = u256(0)
        self.total_retries = u256(0)
        self.total_contests = u256(0)
        self.total_flipped = u256(0)
        self.total_batches_finalized = u256(0)
        self.total_scaled_batches = u256(0)
        self.total_rejected = u256(0)
        self.total_capacity_wei = u256(0)
        self.total_premiums_wei = u256(0)
        self.total_earned_wei = u256(0)
        self.total_refunds_wei = u256(0)
        self.total_payouts_wei = u256(0)
        self.total_claimed_wei = u256(0)

    # --- internals: the clock ---------------------------------------------------

    def _now(self) -> int:
        """Block time, from the message. Identical on every validator."""
        try:
            return _epoch_from_iso(gl.message.raw.get("datetime", ""))
        except Exception:
            return 0

    def _backdate_s(self) -> int:
        return int(self.demo_backdate_days) * DAY

    # --- internals: the ledger (rule 7) -------------------------------------------

    def _bank(self) -> int:
        """Book incoming value AND MAKE IT THE SENDER'S, immediately.

        The FIRST STATEMENT of every write, payable or not. Exactly one place
        value becomes the sender's (here) and exactly one place it stops being
        theirs (`_take`), so a refusal needs no refund and a double credit is
        not expressible - the bug GrantJudge found in the other shape."""
        value = int(gl.message.value)
        if value > 0:
            self.balance_wei = u256(int(self.balance_wei) + value)
            self._credit(gl.message.sender_address, value)
        return value

    def _credit(self, who: Address, amount: int) -> None:
        if amount <= 0:
            return
        self.payout_wei[who] = u256(int(self.payout_wei.get(who) or 0) + amount)
        self.payable_wei = u256(int(self.payable_wei) + amount)

    def _take(self, who: Address, amount: int) -> bool:
        """Move value out of a wallet's payable balance into the HELD books. THE
        ONLY WAY VALUE STOPS BEING THE SENDER'S. Returns False rather than
        raising if the balance is short; no public path reaches it short."""
        if amount <= 0:
            return True
        have = int(self.payout_wei.get(who) or 0)
        if have < amount:
            return False
        self.payout_wei[who] = u256(have - amount)
        self.payable_wei = u256(int(self.payable_wei) - amount)
        self.held_wei = u256(int(self.held_wei) + amount)
        return True

    def _release_to(self, who: Address, amount: int) -> None:
        """Move value out of the HELD books into somebody's payable balance. THE
        ONLY WAY VALUE LEAVES A POOL OR A BOND. Every caller decrements the
        matching pool or claim field in the same statement group."""
        if amount <= 0:
            return
        held = int(self.held_wei)
        self.held_wei = u256(held - amount if held >= amount else 0)
        self._credit(who, amount)

    def _settle_payout(self, who: Address) -> int:
        """Pay a wallet everything it is owed. THE ONLY CALLER OF `_pay`, and
        it reads no clock (rule 12)."""
        amount = int(self.payout_wei.get(who) or 0)
        if amount <= 0:
            return 0
        self.payout_wei[who] = u256(0)
        self.payable_wei = u256(int(self.payable_wei) - amount)
        self.balance_wei = u256(int(self.balance_wei) - amount)
        self.total_claimed_wei = u256(int(self.total_claimed_wei) + amount)
        _pay(who, amount)
        return amount

    def _refuse(self, reason: str, extra: typing.Any = None) -> dict:
        """RULE 2. Every refusal comes through here. It credits nothing: `_bank`
        already made any value the sender's, and refusing means never calling
        `_take`."""
        value = int(gl.message.value)
        self.total_rejected = u256(int(self.total_rejected) + 1)
        out = {"status": "REJECTED", "reason": str(reason),
               "refunded_wei": str(value), "claim_with": "claim_payout()"}
        if isinstance(extra, dict):
            for key in extra:
                out[key] = extra[key]
        return out

    def _is_owner(self) -> bool:
        return gl.message.sender_address == self.owner

    # --- internals: lookups (bounds CHECKED - an out-of-range index reverts) ------

    def _pool(self, pool_id: typing.Any) -> typing.Any:
        i = _as_int(pool_id, 0)
        if i < 1 or i > len(self.pools):
            return None
        return self.pools[i - 1]

    def _cover(self, cover_id: typing.Any) -> typing.Any:
        i = _as_int(cover_id, 0)
        if i < 1 or i > len(self.covers):
            return None
        return self.covers[i - 1]

    def _claim(self, claim_id: typing.Any) -> typing.Any:
        i = _as_int(claim_id, 0)
        if i < 1 or i > len(self.claims):
            return None
        return self.claims[i - 1]

    def _batch(self, batch_id: typing.Any) -> typing.Any:
        i = _as_int(batch_id, 0)
        if i < 1 or i > len(self.batches):
            return None
        return self.batches[i - 1]

    def _ids(self, bucket: typing.Any) -> list:
        out = []
        if bucket is None:
            return out
        for v in bucket:
            out.append(int(v))
        return out

    def _bump(self, old: str, new: str) -> None:
        """Claim-status counts, for `get_stats`."""
        if old:
            have = int(self.claim_counts.get(old) or 0)
            if have > 0:
                self.claim_counts[old] = u32(have - 1)
        if new:
            self.claim_counts[new] = u32(int(self.claim_counts.get(new) or 0) + 1)

    def _set_status(self, claim: Claim, new: str) -> None:
        old = str(claim.status)
        claim.status = new
        self._bump(old, new)

    def _table(self, pool: Pool) -> list:
        out = []
        for p in _split_csv(pool.payout_table_csv):
            out.append(_as_int(p, 0))
        while len(out) < BUCKETS:
            out.append(0)
        return out

    def _exposure_key(self, pool_id: int, who: Address) -> str:
        return str(int(pool_id)) + ":" + who.as_hex

    def _drop_exposure(self, cover: Cover) -> None:
        key = self._exposure_key(int(cover.pool_id), cover.buyer)
        have = int(self.exposure.get(key) or 0)
        amt = int(cover.amount_wei)
        self.exposure[key] = u256(have - amt if have >= amt else 0)

    def _end_cover(self, pool: Pool, cover: Cover, status: str, now: int) -> None:
        """Take a cover out of the live books: unlock its capital, drop the
        buyer's exposure, count it off the pool. Every terminal cover path
        (release, cancel, payout) calls this exactly once."""
        lock = int(cover.lock_wei)
        held = int(pool.locked_wei)
        pool.locked_wei = u256(held - lock if held >= lock else 0)
        n = int(pool.active_covers)
        pool.active_covers = u32(n - 1 if n > 0 else 0)
        w = int(pool.active_cover_wei)
        amt = int(cover.amount_wei)
        pool.active_cover_wei = u256(w - amt if w >= amt else 0)
        self._drop_exposure(cover)
        cover.status = status
        cover.settled_at = u64(now)

    def _earn(self, pool: Pool, amount: int) -> None:
        """Premium becomes the underwriter's."""
        if amount <= 0:
            return
        held = int(pool.premiums_held_wei)
        pool.premiums_held_wei = u256(held - amount if held >= amount else 0)
        pool.premiums_earned_wei = u256(int(pool.premiums_earned_wei) + amount)
        self.total_earned_wei = u256(int(self.total_earned_wei) + amount)
        self._release_to(pool.underwriter, amount)

    # --- writes: pools -----------------------------------------------------------

    @gl.public.write.payable
    def create_pool(self, protocol_name: str, llama_slug: str, llama_id: str,
                    chain: str, perils_csv: str, exclusions_csv: str,
                    rate_bps: typing.Any, waiting_days: typing.Any,
                    deductible_bps: typing.Any, max_cover_wei: typing.Any,
                    term_days: typing.Any, collateral_bps: typing.Any,
                    payout_table_csv: str, official_domains_csv: str,
                    wording: str) -> typing.Any:
        """Open a pool and FREEZE ITS POLICY. The value sent is the capacity.

        Every term is validated here and written once. There is no method in
        this contract that changes any of them afterwards (rule 4)."""
        self._bank()
        sender = gl.message.sender_address
        value = int(gl.message.value)
        now = self._now()
        if self.paused:
            return self._refuse("new pools are paused; nothing else is")
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        if value < MIN_CAPACITY_WEI:
            return self._refuse("a pool needs at least " + _gen(MIN_CAPACITY_WEI)
                                + " GEN of capacity")
        name = _clean(protocol_name, MAX_NAME)
        if len(_norm(name)) < 2:
            return self._refuse("the protocol name is required - it is what the "
                                "evidence must name")
        slug = _lower(_clean(llama_slug, MAX_SLUG))
        for ch in slug:
            if not ((ch.isalnum() and ch.isascii()) or ch in "-._"):
                return self._refuse("the DeFi Llama slug may contain only "
                                    "letters, digits, '-', '.' and '_'")
        if slug == "":
            return self._refuse("the DeFi Llama slug is required - it is where "
                                "severity is measured")
        lid = _clean(llama_id, 20)
        if lid == "" or not lid.isdigit():
            return self._refuse("the DeFi Llama protocol id must be numeric (the "
                                "`id` of /protocol/" + slug + ")")
        chain_name = _clean(chain, MAX_CHAIN)
        perils, why = _parse_list(perils_csv, PERILS, False)
        if why:
            return self._refuse("covered perils: " + why)
        exclusions, why = _parse_list(exclusions_csv, EXCLUSIONS, True)
        if why:
            return self._refuse("exclusions: " + why)
        rate = _as_int(rate_bps, -1)
        if rate < MIN_RATE_BPS or rate > MAX_RATE_BPS:
            return self._refuse("the premium rate must be " + str(MIN_RATE_BPS)
                                + ".." + str(MAX_RATE_BPS) + " bps per 30 days")
        wait = _as_int(waiting_days, -1)
        if wait < 0 or wait > MAX_WAITING_DAYS:
            return self._refuse("the waiting period must be 0.." +
                                str(MAX_WAITING_DAYS) + " days")
        ded = _as_int(deductible_bps, -1)
        if ded < 0 or ded > MAX_DEDUCTIBLE_BPS:
            return self._refuse("the deductible must be 0.." +
                                str(MAX_DEDUCTIBLE_BPS) + " bps")
        max_cover = _as_int(max_cover_wei, -1)
        if max_cover < MIN_COVER_WEI:
            return self._refuse("max cover per buyer must be at least "
                                + _gen(MIN_COVER_WEI) + " GEN")
        term = _as_int(term_days, -1)
        if term < MIN_TERM_DAYS or term > MAX_TERM_DAYS:
            return self._refuse("the pool term must be " + str(MIN_TERM_DAYS)
                                + ".." + str(MAX_TERM_DAYS) + " days")
        coll = _as_int(collateral_bps, -1)
        if coll < MIN_COLLATERAL_BPS or coll > BPS:
            return self._refuse("collateral must be " + str(MIN_COLLATERAL_BPS)
                                + ".." + str(BPS) + " bps of each cover")
        table, why = _parse_table(payout_table_csv)
        if why:
            return self._refuse(why)
        official, why = _parse_domains(official_domains_csv)
        if why:
            return self._refuse("official domains: " + why)
        domains = list(BASE_DOMAINS) + official
        notes = _clean(wording, MAX_WORDING)
        text = _policy_text(name, slug, lid, chain_name, perils, exclusions,
                            rate, wait, ded, max_cover, term, coll, table,
                            domains, notes)
        if not self._take(sender, value):
            return self._refuse("the capacity could not be booked")

        pid = len(self.pools) + 1
        pool = self.pools.append_new_get()
        pool.pool_id = u32(pid)
        pool.underwriter = sender
        pool.protocol_name = name
        pool.llama_slug = slug
        pool.llama_id = lid
        pool.chain = chain_name
        pool.perils_csv = _csv(perils)
        pool.exclusions_csv = _csv(exclusions)
        pool.domains_csv = _csv(domains)
        pool.payout_table_csv = _csv(table)
        pool.rate_bps = u32(rate)
        pool.waiting_days = u32(wait)
        pool.deductible_bps = u32(ded)
        pool.max_cover_wei = u256(max_cover)
        pool.term_days = u32(term)
        pool.collateral_bps = u32(coll)
        pool.wording = notes
        pool.policy_hash = _fnv(text)
        pool.created_at = u64(now)
        pool.expires_at = u64(now + term * DAY)
        pool.status = POOL_OPEN
        pool.capital_wei = u256(value)
        pool.deposited_wei = u256(value)
        self.pools_by_underwriter.get_or_insert_default(sender).append(u32(pid))
        self.total_pools = u256(int(self.total_pools) + 1)
        self.total_capacity_wei = u256(int(self.total_capacity_wei) + value)
        return {"status": "OK", "pool_id": pid, "policy_hash": pool.policy_hash,
                "capacity_wei": str(value), "capacity_gen": _gen(value),
                "expires_at": now + term * DAY,
                "evidence_allowlist": domains,
                "note": ("the policy is frozen: no term of it can be changed by "
                         "anyone, including you")}

    @gl.public.write.payable
    def add_capacity(self, pool_id: typing.Any) -> typing.Any:
        """Top up an open pool's capital. Underwriter only; paused with new
        pools, because it is how new cover becomes sellable."""
        self._bank()
        sender = gl.message.sender_address
        value = int(gl.message.value)
        now = self._now()
        pool = self._pool(pool_id)
        if pool is None:
            return self._refuse("no pool with id " + str(_as_int(pool_id, 0)))
        if self.paused:
            return self._refuse("new capacity is paused; withdrawals are not")
        if sender != pool.underwriter:
            return self._refuse("only this pool's underwriter can add capacity")
        if str(pool.status) != POOL_OPEN or now <= 0 or now >= int(pool.expires_at):
            return self._refuse("pool #" + str(int(pool.pool_id))
                                + " is closed or past its term")
        if value <= 0:
            return self._refuse("send the capacity to add as the call's value")
        if not self._take(sender, value):
            return self._refuse("the capacity could not be booked")
        pool.capital_wei = u256(int(pool.capital_wei) + value)
        pool.deposited_wei = u256(int(pool.deposited_wei) + value)
        self.total_capacity_wei = u256(int(self.total_capacity_wei) + value)
        return {"status": "OK", "pool_id": int(pool.pool_id),
                "capital_wei": str(int(pool.capital_wei)),
                "free_wei": str(int(pool.capital_wei) - int(pool.locked_wei))}

    @gl.public.write
    def withdraw_capacity(self, pool_id: typing.Any,
                          amount_wei: typing.Any) -> typing.Any:
        """Take UNLOCKED capital back. Underwriter only. Works while paused.

        THE CAPACITY LOCK IS THE WHOLE POINT: capital held against a live cover
        is not the underwriter's to withdraw until that cover expires unclaimed
        or its claim settles. An underwriter who sees an exploit coming cannot
        empty the pool in front of it - only the part no cover depends on can
        leave. Credits the payable balance; `claim_payout()` transfers (rule 12)."""
        self._bank()
        sender = gl.message.sender_address
        pool = self._pool(pool_id)
        if pool is None:
            return self._refuse("no pool with id " + str(_as_int(pool_id, 0)))
        if sender != pool.underwriter:
            return self._refuse("only this pool's underwriter can withdraw its "
                                "capacity")
        amount = _as_int(amount_wei, -1)
        free = int(pool.capital_wei) - int(pool.locked_wei)
        if amount <= 0:
            return self._refuse("the amount must be a positive number of wei")
        if amount > free:
            return self._refuse(
                "only " + _gen(free) + " GEN of this pool is unlocked; "
                + _gen(int(pool.locked_wei)) + " GEN is locked against live "
                "covers and cannot leave until they expire or settle",
                {"free_wei": str(free), "locked_wei": str(int(pool.locked_wei))})
        pool.capital_wei = u256(int(pool.capital_wei) - amount)
        pool.withdrawn_wei = u256(int(pool.withdrawn_wei) + amount)
        self._release_to(sender, amount)
        return {"status": "OK", "pool_id": int(pool.pool_id),
                "withdrawn_wei": str(amount), "claim_with": "claim_payout()",
                "free_wei": str(free - amount)}

    @gl.public.write
    def close_pool(self, pool_id: typing.Any) -> typing.Any:
        """Close a pool and credit every remaining wei of capital to the
        underwriter. Refused while ANY cover is live - a live cover is an open
        promise, whether or not a claim has been filed on it yet. Works while
        paused."""
        self._bank()
        sender = gl.message.sender_address
        now = self._now()
        pool = self._pool(pool_id)
        if pool is None:
            return self._refuse("no pool with id " + str(_as_int(pool_id, 0)))
        if sender != pool.underwriter:
            return self._refuse("only this pool's underwriter can close it")
        if str(pool.status) != POOL_OPEN:
            return self._refuse("pool #" + str(int(pool.pool_id))
                                + " is already closed")
        if int(pool.active_covers) > 0:
            return self._refuse(
                "pool #" + str(int(pool.pool_id)) + " has "
                + str(int(pool.active_covers)) + " live cover(s); it can close "
                "once every one has expired, been cancelled or settled",
                {"active_covers": int(pool.active_covers)})
        left = int(pool.capital_wei)
        stray = int(pool.premiums_held_wei)
        pool.capital_wei = u256(0)
        pool.locked_wei = u256(0)
        pool.status = POOL_CLOSED
        pool.closed_at = u64(now if now > 0 else 0)
        pool.withdrawn_wei = u256(int(pool.withdrawn_wei) + left)
        self._release_to(sender, left)
        if stray > 0:
            self._earn(pool, stray)
        return {"status": "OK", "pool_id": int(pool.pool_id),
                "returned_wei": str(left + stray), "claim_with": "claim_payout()"}

    # --- writes: covers ----------------------------------------------------------

    @gl.public.write.payable
    def buy_cover(self, pool_id: typing.Any, amount_wei: typing.Any,
                  days: typing.Any) -> typing.Any:
        """Buy cover. EVERY CHECK IS MECHANICAL AND RUNS FIRST (rule 5): pool
        open and in term, the per-buyer cap, the unlocked capacity, the exact
        premium, the per-wallet rate limit. Overpayment stays the buyer's and
        comes back through `claim_payout()`.

        On success the cover's collateral is LOCKED until the cover expires and
        its claim window closes. Cover starts now (minus the demo backdate, on
        the demo instance only) and pays only for incidents on or after start +
        the pool's waiting period."""
        self._bank()
        sender = gl.message.sender_address
        value = int(gl.message.value)
        now = self._now()
        pool = self._pool(pool_id)
        if pool is None:
            return self._refuse("no pool with id " + str(_as_int(pool_id, 0)))
        pid = int(pool.pool_id)
        if self.paused:
            return self._refuse("new cover is paused; claims and payouts are not")
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        if str(pool.status) != POOL_OPEN:
            return self._refuse("pool #" + str(pid) + " is closed")
        if now >= int(pool.expires_at):
            return self._refuse("pool #" + str(pid) + " has reached the end of "
                                "its term")
        amount = _as_int(amount_wei, -1)
        n_days = _as_int(days, -1)
        if amount < MIN_COVER_WEI:
            return self._refuse("cover must be at least " + _gen(MIN_COVER_WEI)
                                + " GEN")
        if n_days < 1 or n_days > int(pool.term_days):
            return self._refuse("cover length must be 1.." + str(int(pool.term_days))
                                + " days")
        start = now - self._backdate_s()
        end = start + n_days * DAY
        if end > int(pool.expires_at):
            return self._refuse(
                "cover would end after the pool's term; at most "
                + str((int(pool.expires_at) - start) // DAY) + " days are left",
                {"pool_expires_at": int(pool.expires_at)})
        key = self._exposure_key(pid, sender)
        already = int(self.exposure.get(key) or 0)
        if already + amount > int(pool.max_cover_wei):
            return self._refuse(
                "max cover per buyer on this pool is " + _gen(int(pool.max_cover_wei))
                + " GEN and this wallet already holds " + _gen(already) + " GEN",
                {"max_cover_wei": str(int(pool.max_cover_wei)),
                 "held_wei": str(already)})
        lock = _lock(amount, int(pool.collateral_bps))
        free = int(pool.capital_wei) - int(pool.locked_wei)
        if lock > free:
            return self._refuse(
                "not enough unlocked capacity: this cover locks " + _gen(lock)
                + " GEN and " + _gen(free) + " GEN is free",
                {"free_wei": str(free), "lock_wei": str(lock)})
        premium = _premium(amount, int(pool.rate_bps), n_days)
        if value < premium:
            return self._refuse("the premium is " + _gen(premium) + " GEN (" +
                                str(premium) + " wei); " + _gen(value)
                                + " GEN was sent", {"premium_wei": str(premium)})
        last = int(self.last_buy_at.get(sender) or 0)
        if last > 0 and now - last < int(self.buy_cooldown_s):
            return self._refuse(
                "one cover per wallet per " + str(int(self.buy_cooldown_s))
                + "s; retry in " + str(int(self.buy_cooldown_s) - (now - last)) + "s")
        if not self._take(sender, premium):
            return self._refuse("the premium could not be booked")

        cid = len(self.covers) + 1
        cover = self.covers.append_new_get()
        cover.cover_id = u32(cid)
        cover.pool_id = u32(pid)
        cover.buyer = sender
        cover.amount_wei = u256(amount)
        cover.premium_wei = u256(premium)
        cover.lock_wei = u256(lock)
        cover.days = u32(n_days)
        cover.bought_at = u64(now)
        cover.start = u64(start)
        cover.end = u64(end)
        cover.claim_deadline = u64((end if end > now else now)
                                   + int(self.claim_window_s))
        cover.status = COVER_ACTIVE
        pool.locked_wei = u256(int(pool.locked_wei) + lock)
        pool.premiums_held_wei = u256(int(pool.premiums_held_wei) + premium)
        pool.cover_count = u32(int(pool.cover_count) + 1)
        pool.active_covers = u32(int(pool.active_covers) + 1)
        pool.active_cover_wei = u256(int(pool.active_cover_wei) + amount)
        self.exposure[key] = u256(already + amount)
        self.last_buy_at[sender] = u64(now)
        self.covers_by_buyer.get_or_insert_default(sender).append(u32(cid))
        self.covers_by_pool.get_or_insert_default(str(pid)).append(u32(cid))
        self.total_covers = u256(int(self.total_covers) + 1)
        self.total_premiums_wei = u256(int(self.total_premiums_wei) + premium)
        return {"status": "OK", "cover_id": cid, "pool_id": pid,
                "premium_wei": str(premium), "premium_gen": _gen(premium),
                "overpaid_wei": str(value - premium),
                "lock_wei": str(lock), "start": start, "end": end,
                "waiting_ends": start + int(pool.waiting_days) * DAY,
                "claim_deadline": int(cover.claim_deadline),
                "demo_backdated_days": int(self.demo_backdate_days),
                "note": ("incidents before start + waiting period are not "
                         "covered; any overpayment is yours via claim_payout()")}

    @gl.public.write
    def cancel_cover(self, cover_id: typing.Any) -> typing.Any:
        """Give cover up early for a PRO-RATA premium refund of the unexpired
        time, rounded down (dust is earned premium). Buyer only, only while no
        claim has been filed on it. Credits balances; `claim_payout()`
        transfers (rule 12). Works while paused."""
        self._bank()
        sender = gl.message.sender_address
        now = self._now()
        cover = self._cover(cover_id)
        if cover is None:
            return self._refuse("no cover with id " + str(_as_int(cover_id, 0)))
        pool = self._pool(cover.pool_id)
        if pool is None:
            return self._refuse("the cover's pool is missing")
        if sender != cover.buyer:
            return self._refuse("only the buyer can cancel this cover")
        if str(cover.status) != COVER_ACTIVE:
            return self._refuse("cover #" + str(int(cover.cover_id)) + " is "
                                + str(cover.status).lower())
        if int(cover.claim_id) > 0:
            return self._refuse("a claim has been filed on this cover; it "
                                "settles through the claim")
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        remaining = int(cover.end) - (now if now > int(cover.start) else int(cover.start))
        if remaining <= 0:
            return self._refuse("this cover has already run its course; nothing "
                                "is refundable - it releases through release_cover()")
        premium = int(cover.premium_wei)
        refund = _refund(premium, int(cover.days) * DAY, remaining)
        earned = premium - refund
        held = int(pool.premiums_held_wei)
        pool.premiums_held_wei = u256(held - refund if held >= refund else 0)
        pool.refunded_wei = u256(int(pool.refunded_wei) + refund)
        self._release_to(cover.buyer, refund)
        self._earn(pool, earned)
        cover.refund_wei = u256(refund)
        self._end_cover(pool, cover, COVER_CANCELLED, now)
        self.total_refunds_wei = u256(int(self.total_refunds_wei) + refund)
        return {"status": "OK", "cover_id": int(cover.cover_id),
                "refund_wei": str(refund), "earned_by_underwriter_wei": str(earned),
                "claim_with": "claim_payout()"}

    @gl.public.write
    def release_cover(self, cover_id: typing.Any) -> typing.Any:
        """A cover whose claim window has closed with nothing to pay: its
        premium becomes the underwriter's and its collateral unlocks.
        PERMISSIONLESS, works while paused.

        Refused while a claim on it is still open - filed, being judged,
        contestable, under contest, or approved and waiting for its incident to
        settle. A REJECTED_BACKDATED claim releases like any other: the cover
        was valid, the incident predated it, and the premium is earned."""
        self._bank()
        now = self._now()
        cover = self._cover(cover_id)
        if cover is None:
            return self._refuse("no cover with id " + str(_as_int(cover_id, 0)))
        pool = self._pool(cover.pool_id)
        if pool is None:
            return self._refuse("the cover's pool is missing")
        cid = int(cover.cover_id)
        if str(cover.status) != COVER_ACTIVE:
            return self._refuse("cover #" + str(cid) + " is "
                                + str(cover.status).lower())
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        if now <= int(cover.claim_deadline):
            return self._refuse(
                "cover #" + str(cid) + " can still be claimed on for "
                + str(int(cover.claim_deadline) - now) + "s",
                {"claim_deadline": int(cover.claim_deadline)})
        if int(cover.claim_id) > 0:
            claim = self._claim(cover.claim_id)
            if claim is not None:
                st = str(claim.status)
                if st in (CL_FILED, CL_JUDGING, CL_APPROVED):
                    return self._refuse("claim #" + str(int(claim.claim_id))
                                        + " on this cover is " + st.lower()
                                        + " and must settle first")
                refileable = st == CL_INCONCLUSIVE or (
                    st == CL_MISMATCH
                    and int(claim.mismatch_refiles) < MAX_MISMATCH_REFILES)
                if refileable and int(claim.refile_until) >= now:
                    return self._refuse("claim #" + str(int(claim.claim_id))
                                        + " may still be refiled")
                if str(claim.contest_status) in CT_OPEN:
                    return self._refuse("claim #" + str(int(claim.claim_id))
                                        + " is under contest")
                if str(claim.contest_status) == CT_NONE and st in CL_CONTESTABLE \
                        and now <= int(claim.judged_at) + int(self.contest_window_s):
                    return self._refuse("claim #" + str(int(claim.claim_id))
                                        + " can still be contested")
        premium = int(cover.premium_wei)
        self._earn(pool, premium)
        self._end_cover(pool, cover, COVER_RELEASED, now)
        return {"status": "OK", "cover_id": cid,
                "premium_earned_wei": str(premium),
                "unlocked_wei": str(int(cover.lock_wei)),
                "underwriter": pool.underwriter.as_hex,
                "claim_with": "claim_payout()"}
