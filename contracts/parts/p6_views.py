
    # --- views ------------------------------------------------------------------

    def _pool_view(self, pool: Pool, now: int) -> dict:
        capital = int(pool.capital_wei)
        locked = int(pool.locked_wei)
        expires = int(pool.expires_at)
        open_now = str(pool.status) == POOL_OPEN and (now <= 0 or now < expires)
        return {
            "pool_id": int(pool.pool_id),
            "underwriter": pool.underwriter.as_hex,
            "protocol_name": str(pool.protocol_name),
            "llama_slug": str(pool.llama_slug),
            "llama_id": str(pool.llama_id),
            "chain": str(pool.chain),
            "perils": _split_csv(pool.perils_csv),
            "exclusions": _split_csv(pool.exclusions_csv),
            "evidence_allowlist": _split_csv(pool.domains_csv),
            "payout_table_bps": [_as_int(x, 0) for x in _split_csv(pool.payout_table_csv)],
            "rate_bps": int(pool.rate_bps),
            "waiting_days": int(pool.waiting_days),
            "deductible_bps": int(pool.deductible_bps),
            "max_cover_wei": str(int(pool.max_cover_wei)),
            "term_days": int(pool.term_days),
            "collateral_bps": int(pool.collateral_bps),
            "wording": str(pool.wording),
            "policy_hash": str(pool.policy_hash),
            "created_at": int(pool.created_at),
            "expires_at": expires,
            "seconds_left": (expires - now) if now > 0 and expires > now else 0,
            "status": str(pool.status),
            "selling": open_now and not bool(self.paused),
            "closed_at": int(pool.closed_at),
            "capital_wei": str(capital),
            "locked_wei": str(locked),
            "free_wei": str(capital - locked if capital >= locked else 0),
            "utilization_bps": (locked * BPS // capital) if capital > 0 else 0,
            "premiums_held_wei": str(int(pool.premiums_held_wei)),
            "premiums_earned_wei": str(int(pool.premiums_earned_wei)),
            "deposited_wei": str(int(pool.deposited_wei)),
            "withdrawn_wei": str(int(pool.withdrawn_wei)),
            "refunded_wei": str(int(pool.refunded_wei)),
            "paid_out_wei": str(int(pool.paid_out_wei)),
            "cover_count": int(pool.cover_count),
            "active_covers": int(pool.active_covers),
            "active_cover_wei": str(int(pool.active_cover_wei)),
            "claim_count": int(pool.claim_count),
            "books_wei": str(capital + int(pool.premiums_held_wei)),
        }

    def _cover_view(self, cover: Cover, now: int) -> dict:
        pool = self._pool(cover.pool_id)
        wait = int(pool.waiting_days) * DAY if pool is not None else 0
        start = int(cover.start)
        end = int(cover.end)
        return {
            "cover_id": int(cover.cover_id),
            "pool_id": int(cover.pool_id),
            "protocol_name": str(pool.protocol_name) if pool is not None else "",
            "llama_slug": str(pool.llama_slug) if pool is not None else "",
            "buyer": cover.buyer.as_hex,
            "amount_wei": str(int(cover.amount_wei)),
            "premium_wei": str(int(cover.premium_wei)),
            "lock_wei": str(int(cover.lock_wei)),
            "days": int(cover.days),
            "bought_at": int(cover.bought_at),
            "start": start,
            "waiting_ends": start + wait,
            "end": end,
            "claim_deadline": int(cover.claim_deadline),
            "status": str(cover.status),
            "in_force": str(cover.status) == COVER_ACTIVE and now > 0
            and now >= start + wait and now <= end,
            "claimable": str(cover.status) == COVER_ACTIVE
            and int(cover.claim_id) == 0 and now > 0
            and now >= start + wait and now <= int(cover.claim_deadline),
            "in_waiting_period": str(cover.status) == COVER_ACTIVE
            and now > 0 and now < start + wait,
            "claim_id": int(cover.claim_id),
            "settled_at": int(cover.settled_at),
            "refund_wei": str(int(cover.refund_wei)),
            "payout_wei": str(int(cover.payout_wei)),
            "backdated_days": (int(cover.bought_at) - start) // DAY,
        }

    def _claim_view(self, claim: Claim, now: int) -> dict:
        cover = self._cover(claim.cover_id)
        pool = self._pool(claim.pool_id)
        closes = int(claim.judged_at) + int(self.contest_window_s) \
            if int(claim.judged_at) > 0 else 0
        losing = ""
        if str(claim.status) in CL_CONTESTABLE and pool is not None:
            losing = pool.underwriter.as_hex if str(claim.status) == CL_APPROVED \
                else claim.claimant.as_hex
        return {
            "claim_id": int(claim.claim_id),
            "cover_id": int(claim.cover_id),
            "pool_id": int(claim.pool_id),
            "protocol_name": str(pool.protocol_name) if pool is not None else "",
            "claimant": claim.claimant.as_hex,
            "underwriter": pool.underwriter.as_hex if pool is not None else "",
            "cover_amount_wei": str(int(cover.amount_wei)) if cover is not None else "0",
            "cover_start": int(cover.start) if cover is not None else 0,
            "cover_end": int(cover.end) if cover is not None else 0,
            "waiting_ends": (int(cover.start) + int(pool.waiting_days) * DAY)
            if cover is not None and pool is not None else 0,
            "deductible_bps": int(pool.deductible_bps) if pool is not None else 0,
            "filed_at": int(claim.filed_at),
            "last_filed_at": int(claim.last_filed_at),
            "incident_key": str(claim.incident_key),
            "evidence_urls": _split_urls(claim.urls),
            "statement": str(claim.statement),
            "status": str(claim.status),
            "refiles": int(claim.refiles),
            "mismatch_refiles": int(claim.mismatch_refiles),
            "mismatch_refiles_left": MAX_MISMATCH_REFILES
            - int(claim.mismatch_refiles),
            "refile_until": int(claim.refile_until),
            "attempts": int(claim.attempts),
            "stalls": int(claim.stalls),
            "judged_at": int(claim.judged_at),
            "classification": str(claim.classification),
            "event_match": str(claim.event_match),
            "effective": str(claim.effective),
            "peril": str(claim.peril),
            "exclusion": str(claim.exclusion),
            "evidence_strength": int(claim.strength),
            "strength_range": [int(claim.strength_lo), int(claim.strength_hi)],
            "incident_day": int(claim.incident_day),
            "incident_date": _date_text(int(claim.incident_day)),
            "protocol_match": bool(claim.protocol_match),
            "evidence_binding": str(claim.bind_line),
            "bound_pages": int(claim.bound),
            "llama_record": str(claim.llama_line),
            "tvl_window": str(claim.tvl_line),
            "tvl_before_usd": str(int(claim.tvl_before)),
            "tvl_low_usd": str(int(claim.tvl_low)),
            "drop_bps": int(claim.drop_bps),
            "severity_bucket": int(claim.bucket),
            "sources": int(claim.sources),
            "bracket": str(claim.bracket),
            "pinned": str(claim.pinned),
            "model_called": bool(claim.model_called),
            "content_hash": str(claim.content_hash),
            "digest": str(claim.digest),
            "reason": str(claim.reason),
            "table_bps": int(claim.table_bps),
            "gross_wei": str(int(claim.gross_wei)),
            "payout_wei": str(int(claim.payout_wei)),
            "batch_id": int(claim.batch_id),
            "contest_window_closes": closes,
            "contestable_by": losing if str(claim.contest_status) == CT_NONE
            and (now <= 0 or now <= closes) else "",
            "contest_status": str(claim.contest_status),
            "contester": claim.contester.as_hex if str(claim.contest_status) else "",
            "contest_bond_wei": str(int(claim.contest_bond_wei)),
            "contest_urls": _split_urls(claim.contest_urls),
            "contest_statement": str(claim.contest_statement),
            "contested_at": int(claim.contested_at),
            "contest_resolved_at": int(claim.contest_resolved_at),
            "contest_classification": str(claim.contest_classification),
            "contest_effective": str(claim.contest_effective),
            "contest_peril": str(claim.contest_peril),
            "contest_exclusion": str(claim.contest_exclusion),
            "contest_strength": int(claim.contest_strength),
            "contest_bucket": int(claim.contest_bucket),
            "contest_drop_bps": int(claim.contest_drop_bps),
            "contest_content_hash": str(claim.contest_content_hash),
            "contest_novel": str(claim.contest_novel),
            "contest_reason": str(claim.contest_reason),
            "status_before_contest": str(claim.status_before_contest),
        }

    def _batch_view(self, batch: Batch, now: int) -> dict:
        return {
            "batch_id": int(batch.batch_id),
            "pool_id": int(batch.pool_id),
            "incident_day": int(batch.incident_day),
            "incident_date": _date_text(int(batch.incident_day)),
            "opened_at": int(batch.opened_at),
            "closes_at": int(batch.closes_at),
            "status": str(batch.status),
            "finalizable": str(batch.status) == B_OPEN and now > 0
            and now >= int(batch.closes_at),
            "finalized_at": int(batch.finalized_at),
            "members": int(batch.members),
            "claim_ids": self._ids(self.batch_claims.get(str(int(batch.batch_id)))),
            "paid_members": int(batch.paid_members),
            "gross_total_wei": str(int(batch.gross_total_wei)),
            "available_wei": str(int(batch.available_wei)),
            "paid_total_wei": str(int(batch.paid_total_wei)),
            "dust_wei": str(int(batch.dust_wei)),
            "scaled": bool(batch.scaled),
        }

    def _page(self, n: int, offset: typing.Any, count: typing.Any) -> tuple:
        start = _clamp(_as_int(offset, 0), 0, n)
        k = _clamp(_as_int(count, 20), 0, 100)
        return (start, min(n, start + k))

    @gl.public.view
    def get_pool(self, pool_id: typing.Any) -> typing.Any:
        pool = self._pool(pool_id)
        if pool is None:
            return {"found": False}
        out = self._pool_view(pool, self._now())
        out["found"] = True
        return out

    @gl.public.view
    def get_pools(self, offset: typing.Any, count: typing.Any) -> typing.Any:
        now = self._now()
        a, b = self._page(len(self.pools), offset, count)
        out = []
        for i in range(a, b):
            out.append(self._pool_view(self.pools[i], now))
        return {"total": len(self.pools), "offset": a, "items": out}

    @gl.public.view
    def get_pools_by_underwriter(self, address: str) -> typing.Any:
        if not _is_addr(address):
            return {"items": []}
        now = self._now()
        out = []
        for pid in self._ids(self.pools_by_underwriter.get(Address(str(address).strip()))):
            pool = self._pool(pid)
            if pool is not None:
                out.append(self._pool_view(pool, now))
        return {"items": out}

    @gl.public.view
    def get_policy(self, pool_id: typing.Any) -> typing.Any:
        """The canonical wording, RE-DERIVED from the stored terms and hashed.
        `hash_matches` is the check anybody can run that the terms judged
        against are the terms sold."""
        pool = self._pool(pool_id)
        if pool is None:
            return {"found": False}
        text = _policy_text(str(pool.protocol_name), str(pool.llama_slug),
                            str(pool.llama_id), str(pool.chain),
                            _split_csv(pool.perils_csv),
                            _split_csv(pool.exclusions_csv),
                            int(pool.rate_bps), int(pool.waiting_days),
                            int(pool.deductible_bps), int(pool.max_cover_wei),
                            int(pool.term_days), int(pool.collateral_bps),
                            self._table(pool), _split_csv(pool.domains_csv),
                            str(pool.wording))
        return {"found": True, "pool_id": int(pool.pool_id), "text": text,
                "policy_hash": str(pool.policy_hash),
                "hash_matches": _fnv(text) == str(pool.policy_hash)}

    @gl.public.view
    def get_cover(self, cover_id: typing.Any) -> typing.Any:
        cover = self._cover(cover_id)
        if cover is None:
            return {"found": False}
        out = self._cover_view(cover, self._now())
        out["found"] = True
        return out

    @gl.public.view
    def get_covers_by_buyer(self, address: str) -> typing.Any:
        if not _is_addr(address):
            return {"items": []}
        now = self._now()
        out = []
        for cid in self._ids(self.covers_by_buyer.get(Address(str(address).strip()))):
            cover = self._cover(cid)
            if cover is not None:
                out.append(self._cover_view(cover, now))
        return {"items": out}

    @gl.public.view
    def get_covers_by_pool(self, pool_id: typing.Any) -> typing.Any:
        now = self._now()
        out = []
        for cid in self._ids(self.covers_by_pool.get(str(_as_int(pool_id, 0)))):
            cover = self._cover(cid)
            if cover is not None:
                out.append(self._cover_view(cover, now))
        return {"items": out}

    @gl.public.view
    def get_claim(self, claim_id: typing.Any) -> typing.Any:
        claim = self._claim(claim_id)
        if claim is None:
            return {"found": False}
        out = self._claim_view(claim, self._now())
        out["found"] = True
        return out

    @gl.public.view
    def get_claims(self, offset: typing.Any, count: typing.Any) -> typing.Any:
        now = self._now()
        a, b = self._page(len(self.claims), offset, count)
        out = []
        for i in range(a, b):
            out.append(self._claim_view(self.claims[i], now))
        return {"total": len(self.claims), "offset": a, "items": out}

    @gl.public.view
    def get_batch(self, batch_id: typing.Any) -> typing.Any:
        batch = self._batch(batch_id)
        if batch is None:
            return {"found": False}
        out = self._batch_view(batch, self._now())
        out["found"] = True
        return out

    @gl.public.view
    def get_batches(self, offset: typing.Any, count: typing.Any) -> typing.Any:
        now = self._now()
        a, b = self._page(len(self.batches), offset, count)
        out = []
        for i in range(a, b):
            out.append(self._batch_view(self.batches[i], now))
        return {"total": len(self.batches), "offset": a, "items": out}

    @gl.public.view
    def payout_of(self, address: str) -> typing.Any:
        if not _is_addr(address):
            return {"owed_wei": "0"}
        owed = int(self.payout_wei.get(Address(str(address).strip())) or 0)
        return {"owed_wei": str(owed), "owed_gen": _gen(owed)}

    @gl.public.view
    def quote(self, pool_id: typing.Any, amount_wei: typing.Any,
              days: typing.Any) -> typing.Any:
        """Exactly what `buy_cover` would charge and lock, by the same
        functions, plus the reason it would refuse if it would. The UI's live
        premium calculator is this view."""
        pool = self._pool(pool_id)
        if pool is None:
            return {"ok": False, "reason": "no such pool"}
        now = self._now()
        amount = _as_int(amount_wei, 0)
        n = _as_int(days, 0)
        premium = _premium(amount, int(pool.rate_bps), n)
        lock = _lock(amount, int(pool.collateral_bps))
        free = int(pool.capital_wei) - int(pool.locked_wei)
        table = self._table(pool)
        payouts = []
        for i in range(BUCKETS):
            payouts.append(str(_gross(amount, table[i], int(pool.deductible_bps))))
        reason = ""
        if str(pool.status) != POOL_OPEN:
            reason = "pool closed"
        elif amount < MIN_COVER_WEI:
            reason = "below the minimum cover"
        elif n < 1 or n > int(pool.term_days):
            reason = "cover length out of range"
        elif lock > free:
            reason = "not enough unlocked capacity"
        elif amount > int(pool.max_cover_wei):
            reason = "above max cover per buyer"
        start = now - self._backdate_s() if now > 0 else 0
        return {"ok": reason == "", "reason": reason, "premium_wei": str(premium),
                "premium_gen": _gen(premium), "lock_wei": str(lock),
                "free_wei": str(free), "payout_by_bucket_wei": payouts,
                "start": start,
                "waiting_ends": start + int(pool.waiting_days) * DAY if start else 0,
                "end": start + n * DAY if start else 0,
                "formula": "premium = ceil(cover x rate_bps x days / (30 x 10000))"}

    @gl.public.view
    def check_evidence(self, pool_id: typing.Any, evidence_urls: str) -> typing.Any:
        """The allowlist verdict for each URL, by the same function
        `file_claim` uses. The claim form validates live against this."""
        pool = self._pool(pool_id)
        if pool is None:
            return {"ok": False, "items": [], "reason": "no such pool"}
        domains = _split_csv(pool.domains_csv)
        items = []
        ok = True
        for u in _split_urls(evidence_urls):
            why = _check_url(u, domains)
            items.append({"url": u, "ok": why == "", "reason": why})
            ok = ok and why == ""
        _, overall = _parse_urls(evidence_urls, domains)
        return {"ok": ok and overall == "", "reason": overall, "items": items,
                "allowlist": domains}

    @gl.public.view
    def check_incident(self, cover_id: typing.Any, incident_key: str) -> typing.Any:
        """The mechanical verdict on an incident key for a cover, by the same
        function `file_claim` uses. Whether DeFi Llama has the record is
        answered by the validators at judgement, before any model call."""
        cover = self._cover(cover_id)
        if cover is None:
            return {"ok": False, "reason": "no such cover"}
        pool = self._pool(cover.pool_id)
        if pool is None:
            return {"ok": False, "reason": "the cover's pool is missing"}
        key, why = self._key_check(cover, pool, incident_key, self._now())
        return {"ok": why == "", "incident_key": key, "reason": why,
                "llama_id": str(pool.llama_id),
                "window": [_date_text(_day_of(int(cover.start)
                                              + int(pool.waiting_days) * DAY)),
                           _date_text(int(cover.end))],
                "format": "<DeFi Llama id>:<YYYY-MM-DD>[:<record name>]"}

    @gl.public.view
    def verify_claim(self, claim_id: typing.Any) -> typing.Any:
        """Recompute, from storage alone, everything about a judged claim that
        arithmetic can recompute, and check that ONE EVENT binds it:

          - the content hash, over the incident key, the evidence digest and
            its page binding, the selected record and the TVL window points;
          - the record in `llama_record` is the one the key names (same id,
            same day), and the claim's incident day is that day;
          - the TVL window is anchored on that day: the "before" point is
            earlier, every window point is inside the seven days from it, and
            the lowest point, the drop and the bucket recompute exactly;
          - the payout from the bucket, the table and the deductible.

        `hash_matches` is the loophole-6 check - an evidence page edited after
        judging does not change what was judged, and anyone can prove which
        text that was."""
        claim = self._claim(claim_id)
        if claim is None:
            return {"found": False}
        cover = self._cover(claim.cover_id)
        pool = self._pool(claim.pool_id)
        judged = int(claim.judged_at) > 0
        key, lid, day, _, _ = _parse_key(str(claim.incident_key))
        recomputed = _content_hash(key, _norm(str(claim.digest)),
                                   str(claim.bind_line), str(claim.llama_line),
                                   str(claim.tvl_line))
        record = str(claim.llama_line)
        has_record = record.startswith("DeFi Llama incident record ")
        record_ok = (not has_record) or (
            record.startswith("DeFi Llama incident record " + lid + ":"
                              + _date_text(day) + ": ")
            and int(claim.incident_day) == day)
        tv = _parse_tvl_line(str(claim.tvl_line))
        tvl_ok = True
        low = -1
        if tv:
            top = day + SEVERITY_WINDOW_DAYS * DAY
            tvl_ok = tv["anchor"] == _date_text(day)
            if tv["before_day"] not in ("", "-"):
                _, _, bday, _, why = _parse_key("0:" + tv["before_day"])
                tvl_ok = tvl_ok and why == "" and bday < day
            for pt in tv["points"]:
                _, _, pday, _, why = _parse_key("0:" + str(pt[0]))
                tvl_ok = tvl_ok and why == "" and pday >= day and pday <= top
                if low < 0 or int(pt[1]) < low:
                    low = int(pt[1])
            if len(tv["points"]) == int(tv["count"]):
                tvl_ok = tvl_ok and low == int(tv["low"])
            if int(tv["before"]) >= 0:
                tvl_ok = tvl_ok and int(tv["before"]) == int(claim.tvl_before)
        drop = _drop(int(tv["before"]), int(tv["low"])) if tv else 0
        amount = int(cover.amount_wei) if cover is not None else 0
        ded = int(pool.deductible_bps) if pool is not None else 0
        gross = _gross(amount, int(claim.table_bps), ded)
        return {"found": True, "claim_id": int(claim.claim_id),
                "incident_key": key,
                "content_hash": str(claim.content_hash),
                "recomputed_hash": recomputed,
                "hash_matches": (not judged)
                or recomputed == str(claim.content_hash),
                "record_matches_key": (not judged) or record_ok,
                "tvl_window_anchored": (not judged) or tvl_ok,
                "evidence_binding": str(claim.bind_line),
                "event_match": str(claim.event_match),
                "severity_bucket": int(claim.bucket),
                "drop_bps": int(claim.drop_bps),
                "drop_from_window_bps": drop,
                "bucket_from_drop": _bucket(int(claim.drop_bps)),
                "table_bps": int(claim.table_bps),
                "deductible_bps": ded,
                "cover_wei": str(amount),
                "gross_recomputed_wei": str(gross),
                "gross_stored_wei": str(int(claim.gross_wei)),
                "payout_wei": str(int(claim.payout_wei)),
                "hash_formula": ("fnv1a64(incident_key | norm(digest) | "
                                 "evidence_binding | norm(llama_record) | "
                                 "tvl_window)"),
                "formula": "gross = cover x table[bucket] x (10000 - deductible) / 10000^2"}

    @gl.public.view
    def get_active_cover(self, address: str, protocol: str) -> typing.Any:
        """The strongest ACTIVE cover this wallet holds on `protocol` (a DeFi
        Llama slug or the pool's protocol name), for integrators such as
        CoverRegistry. `in_force` is true only between start + waiting period
        and end; `time_checked` says whether the block time was readable in
        this call - when it is not, `in_force` is false, never assumed."""
        if not _is_addr(address):
            return {"found": False, "reason": "not an address"}
        now = self._now()
        want = _norm(protocol)
        best = None
        for cid in self._ids(self.covers_by_buyer.get(Address(str(address).strip()))):
            cover = self._cover(cid)
            if cover is None or str(cover.status) != COVER_ACTIVE:
                continue
            pool = self._pool(cover.pool_id)
            if pool is None:
                continue
            if want != _norm(pool.llama_slug) and want != _norm(pool.protocol_name):
                continue
            view = self._cover_view(cover, now)
            if best is None or (view["in_force"] and not best["in_force"]) or \
                    (view["in_force"] == best["in_force"]
                     and int(view["amount_wei"]) > int(best["amount_wei"])):
                best = view
        if best is None:
            return {"found": False, "time_checked": now > 0,
                    "reason": "no active cover on " + _short(protocol, 60)}
        best["found"] = True
        best["time_checked"] = now > 0
        best["demo"] = int(self.demo_backdate_days) > 0
        return best

    @gl.public.view
    def get_stats(self) -> typing.Any:
        """The books, published. RULE 7 IS AN ASSERTION ANYBODY CAN MAKE FROM
        HERE: `balance_wei == held_wei + payable_wei`, and `held_wei` equals the
        sum of every pool's capital and unearned premium plus every bond in
        flight - recomputed below, not remembered."""
        try:
            chain_balance = int(self.balance)
        except Exception:
            chain_balance = -1
        booked = int(self.balance_wei)
        held = int(self.held_wei)
        payable = int(self.payable_wei)
        pools_sum = 0
        capital = 0
        locked = 0
        unearned = 0
        open_pools = 0
        for i in range(len(self.pools)):
            p = self.pools[i]
            pools_sum += int(p.capital_wei) + int(p.premiums_held_wei)
            capital += int(p.capital_wei)
            locked += int(p.locked_wei)
            unearned += int(p.premiums_held_wei)
            if str(p.status) == POOL_OPEN:
                open_pools += 1
        bonds = 0
        for i in range(len(self.claims)):
            bonds += int(self.claims[i].contest_bond_wei)
        counts = {}
        for st in CLAIM_STATUSES:
            counts[st] = int(self.claim_counts.get(st) or 0)
        return {
            "pools": int(self.total_pools),
            "open_pools": open_pools,
            "covers": int(self.total_covers),
            "claims": int(self.total_claims),
            "claims_by_status": counts,
            "judgements": int(self.total_judgements),
            "judge_attempts": int(self.total_judge_attempts),
            "retries": int(self.total_retries),
            "contests": int(self.total_contests),
            "contests_flipped": int(self.total_flipped),
            "batches_finalized": int(self.total_batches_finalized),
            "batches_scaled": int(self.total_scaled_batches),
            "refusals": int(self.total_rejected),
            "capital_wei": str(capital),
            "locked_wei": str(locked),
            "unearned_premium_wei": str(unearned),
            "bonds_wei": str(bonds),
            "total_capacity_deposited_wei": str(int(self.total_capacity_wei)),
            "total_premiums_wei": str(int(self.total_premiums_wei)),
            "total_premiums_earned_wei": str(int(self.total_earned_wei)),
            "total_refunds_wei": str(int(self.total_refunds_wei)),
            "total_payouts_wei": str(int(self.total_payouts_wei)),
            "total_claimed_wei": str(int(self.total_claimed_wei)),
            "balance_wei": str(booked),
            "held_wei": str(held),
            "payable_wei": str(payable),
            "ledger_balanced": booked == held + payable,
            "held_matches_books": held == pools_sum + bonds,
            "identity": "balance_wei == held_wei + payable_wei; held_wei == "
                        "sum(pool capital + unearned premium) + bonds",
            "chain_balance_wei": str(chain_balance) if chain_balance >= 0
            else "unknown",
            "undelivered_wei": (str(chain_balance - booked)
                                if chain_balance > booked else "0")
            if chain_balance >= 0 else "unknown",
            "paused": bool(self.paused),
            "owner": self.owner.as_hex,
            "demo": int(self.demo_backdate_days) > 0,
        }

    @gl.public.view
    def get_config(self) -> typing.Any:
        """Every number this contract judges and pays by, in one place."""
        demo = int(self.demo_backdate_days) > 0
        return {
            "policy_version": POLICY_VERSION,
            "demo": demo,
            "label": ("DEMO - every cover starts " + str(int(self.demo_backdate_days))
                      + " days before it is bought, fixed at deployment, so that "
                      "real historical incidents can be replayed. Not insurance."
                      ) if demo else "CANONICAL - backdating enforced strictly",
            "demo_backdate_days": int(self.demo_backdate_days),
            "owner": self.owner.as_hex,
            "paused": bool(self.paused),
            "now": self._now(),
            "claim_window_s": int(self.claim_window_s),
            "settlement_window_s": int(self.settlement_window_s),
            "contest_window_s": int(self.contest_window_s),
            "stall_ttl_s": int(self.stall_ttl_s),
            "buy_cooldown_s": int(self.buy_cooldown_s),
            "contest_bond_wei": str(int(self.contest_bond_wei)),
            "perils": list(PERILS),
            "exclusions": list(EXCLUSIONS),
            "peril_text": PERIL_TEXT,
            "exclusion_text": EXCLUSION_TEXT,
            "peril_words": {k: list(PERIL_WORDS[k]) for k in PERILS},
            "exclusion_words": {k: list(EXCLUSION_WORDS[k]) for k in EXCLUSIONS},
            "llama_map": LLAMA_MAP,
            "severity_edges_bps": list(SEVERITY_EDGES_BPS),
            "severity_window_days": SEVERITY_WINDOW_DAYS,
            "incident_key_format": "<DeFi Llama id>:<YYYY-MM-DD>[:<record name>]",
            "bind_window_days": BIND_WINDOW_DAYS,
            "event_matches": list(EVENT_MATCHES),
            "max_mismatch_refiles": MAX_MISMATCH_REFILES,
            "default_payout_table_bps": list(DEFAULT_PAYOUT_TABLE),
            "min_covered_strength": MIN_COVERED_STRENGTH,
            "strength_tolerance": STRENGTH_TOLERANCE,
            "base_domains": list(BASE_DOMAINS),
            "max_urls": MAX_URLS,
            "min_capacity_wei": str(MIN_CAPACITY_WEI),
            "min_cover_wei": str(MIN_COVER_WEI),
            "rate_bps_range": [MIN_RATE_BPS, MAX_RATE_BPS],
            "max_waiting_days": MAX_WAITING_DAYS,
            "default_waiting_days": DEFAULT_WAITING_DAYS,
            "max_deductible_bps": MAX_DEDUCTIBLE_BPS,
            "term_days_range": [MIN_TERM_DAYS, MAX_TERM_DAYS],
            "min_collateral_bps": MIN_COLLATERAL_BPS,
            "min_novel_chars": MIN_NOVEL_CHARS,
            "claim_statuses": list(CLAIM_STATUSES),
            "contest_statuses": list(CONTEST_STATUSES),
            "sources": {"incidents": LLAMA_HACKS_URL,
                        "tvl": LLAMA_PROTOCOL_URL + "{slug}"},
            "division_of_labour": (
                "GenLayer reads public incident evidence and classifies it "
                "against the frozen policy's covered perils and exclusions. "
                "Deterministic contract logic enforces capacity, waiting "
                "periods, backdating checks, premium accounting, severity "
                "payouts, deductibles, and pro-rata splits."),
        }
