
    # --- writes: claims ----------------------------------------------------------

    def _claim_facts(self, claim: Claim, cover: Cover, pool: Pool,
                     mode: str) -> dict:
        """Everything a node needs, copied out of storage as PLAIN STRINGS, INTS
        AND LISTS before any nondet block opens. The only boundary between
        storage and the closure."""
        urls = claim.contest_urls if mode == "contest" else claim.urls
        key, lid, day, name, _ = _parse_key(str(claim.incident_key))
        return {
            "mode": mode,
            "claim_id": int(claim.claim_id),
            "incident_key": key,
            "key_id": lid,
            "key_day": day,
            "key_name": name,
            "protocol_name": str(pool.protocol_name),
            "llama_slug": str(pool.llama_slug),
            "llama_id": str(pool.llama_id),
            "perils": _split_csv(pool.perils_csv),
            "exclusions": _split_csv(pool.exclusions_csv),
            "urls": _split_urls(urls),
            "start": int(cover.start),
            "end": int(cover.end),
            "waiting_s": int(pool.waiting_days) * DAY,
            "prior_digest": str(claim.digest) if mode == "contest" else "",
            "prior_sources": int(claim.sources) if mode == "contest" else 0,
            "prior_match": bool(claim.protocol_match) if mode == "contest"
            else False,
            "prior_bound": int(claim.bound) if mode == "contest" else 0,
        }

    def _key_check(self, cover: Cover, pool: Pool, text: typing.Any,
                   now: int) -> tuple:
        """(canonical key, why) - the MECHANICAL half of selecting an incident,
        before any evidence is read or any validator asked. The key must be
        well formed, name THIS pool's DeFi Llama id, and date an incident
        inside the cover after its waiting period and not in the future. That
        the record exists is checked by every validator against the live feed,
        still before any model call."""
        key, lid, day, _, why = _parse_key(text)
        if why:
            return ("", why)
        if lid != str(pool.llama_id):
            return ("", "incident key " + key + " names DeFi Llama id " + lid
                    + " but this pool covers id " + str(pool.llama_id)
                    + " (" + str(pool.protocol_name) + ")")
        lo = int(cover.start) + int(pool.waiting_days) * DAY
        if day < lo:
            return ("", "incident " + key + " predates this cover's start plus "
                    "its waiting period (" + _date_text(_day_of(lo)) + "); it "
                    "is not covered and is refused before judging")
        if day > int(cover.end):
            return ("", "incident " + key + " is after this cover ended ("
                    + _date_text(int(cover.end)) + ")")
        if now > 0 and day > now:
            return ("", "incident " + key + " is dated in the future")
        return (key, "")

    def _consensus(self, facts: dict) -> typing.Any:
        """Run one judgement through consensus and return the agreed payload,
        or a {"retry": ...} dict. Rule 1's machinery in one place."""
        task = facts

        def leader_fn() -> dict:
            return _collect(task)

        def validator_fn(leader_result: gl.vm.Result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return _leader_failed(leader_result, task)
            theirs = leader_result.calldata
            if isinstance(theirs, dict) and theirs.get("retry"):
                return _leader_failed(leader_result, task)
            # Pure gate first: an incoherent leader is refused by arithmetic
            # before this node fetches anything or spends an inference.
            if not _coherent(theirs, task):
                return False
            return _agrees(theirs, _collect(task))

        return gl.vm.run_nondet(leader_fn, validator_fn)

    @gl.public.write
    def file_claim(self, cover_id: typing.Any, incident_key: str,
                   evidence_urls: str, statement: str) -> typing.Any:
        """File THE claim on a cover, about ONE incident. Buyer only. Works
        while paused.

        `incident_key` selects one DeFi Llama hacks record:
        "<llama id>:<YYYY-MM-DD>[:<record name>]". That record alone fixes the
        incident date, the TVL window and what the evidence must be about.

        Mechanical refusals, all before GenLayer: one claim per cover; the
        cover must be live and inside its claim window; the key must name this
        pool's protocol and a day inside the cover after its waiting period;
        1..3 distinct evidence URLs, EVERY ONE on the pool's frozen allowlist
        (a web.archive.org snapshot only of an allowlisted page). Evidence
        from anywhere else is refused here and never reaches a validator."""
        self._bank()
        sender = gl.message.sender_address
        now = self._now()
        cover = self._cover(cover_id)
        if cover is None:
            return self._refuse("no cover with id " + str(_as_int(cover_id, 0)))
        pool = self._pool(cover.pool_id)
        if pool is None:
            return self._refuse("the cover's pool is missing")
        cid = int(cover.cover_id)
        if sender != cover.buyer:
            return self._refuse("only the buyer of cover #" + str(cid)
                                + " can claim on it")
        if int(cover.claim_id) > 0:
            return self._refuse("cover #" + str(cid) + " already has claim #"
                                + str(int(cover.claim_id)) + "; one claim per "
                                "cover - an INCONCLUSIVE one is refiled, not "
                                "filed again", {"claim_id": int(cover.claim_id)})
        if str(cover.status) != COVER_ACTIVE:
            return self._refuse("cover #" + str(cid) + " is "
                                + str(cover.status).lower())
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        waiting_ends = int(cover.start) + int(pool.waiting_days) * DAY
        if now < waiting_ends:
            # MECHANICAL, before any evidence is looked at. Every incident that
            # has happened by now predates the end of the waiting period, so a
            # claim filed now could only ever be REJECTED_BACKDATED - and it
            # would spend the cover's ONE claim doing it. Refusing here keeps
            # the claim for an incident the cover actually covers.
            return self._refuse("cover waiting period has not ended yet, "
                                "claimable after " + str(waiting_ends),
                                {"claimable_after": waiting_ends,
                                 "seconds_remaining": waiting_ends - now})
        if now > int(cover.claim_deadline):
            return self._refuse("the claim window for cover #" + str(cid)
                                + " closed " + str(now - int(cover.claim_deadline))
                                + "s ago", {"claim_deadline": int(cover.claim_deadline)})
        key, why = self._key_check(cover, pool, incident_key, now)
        if why:
            return self._refuse("incident refused before judging: " + why)
        urls, why = _parse_urls(evidence_urls, _split_csv(pool.domains_csv))
        if why:
            return self._refuse("evidence refused before judging: " + why,
                                {"allowlist": _split_csv(pool.domains_csv)})
        text = _clean(statement, MAX_STATEMENT)

        clid = len(self.claims) + 1
        claim = self.claims.append_new_get()
        claim.claim_id = u32(clid)
        claim.cover_id = u32(cid)
        claim.pool_id = u32(int(pool.pool_id))
        claim.claimant = sender
        claim.filed_at = u64(now)
        claim.last_filed_at = u64(now)
        claim.incident_key = key
        claim.urls = " ".join(urls)
        keys = []
        for u in urls:
            keys.append(_url_key(u))
        claim.used_urls = " ".join(keys)
        claim.statement = text
        claim.refile_until = u64(int(cover.claim_deadline))
        self._set_status(claim, CL_FILED)
        cover.claim_id = u32(clid)
        pool.claim_count = u32(int(pool.claim_count) + 1)
        self.claims_by_pool.get_or_insert_default(str(int(pool.pool_id))).append(u32(clid))
        self.total_claims = u256(int(self.total_claims) + 1)
        return {"status": "OK", "claim_id": clid, "cover_id": cid,
                "incident_key": key, "evidence": urls,
                "note": ("filed; anyone may now call judge_claim(" + str(clid)
                         + ") and GenLayer's validators will read the evidence")}

    @gl.public.write
    def refile_claim(self, claim_id: typing.Any, incident_key: str,
                     evidence_urls: str, statement: str) -> typing.Any:
        """Put an INCONCLUSIVE or EVIDENCE_MISMATCH claim - or one
        `settle_stalled` returned to FILED - back in front of the validators.
        Claimant only. `incident_key` may be "" to keep the claim's incident,
        or a corrected key, checked exactly as at filing; `evidence_urls` may be
        "" to keep the claim's evidence (with a corrected key).

        Something must change: at least one URL this claim has never used, or
        a different incident key. Nothing is lost by either verdict and nothing
        is gained by resubmitting it. A claim comes back from EVIDENCE_MISMATCH
        at most MAX_MISMATCH_REFILES times."""
        self._bank()
        sender = gl.message.sender_address
        now = self._now()
        claim = self._claim(claim_id)
        if claim is None:
            return self._refuse("no claim with id " + str(_as_int(claim_id, 0)))
        pool = self._pool(claim.pool_id)
        if pool is None:
            return self._refuse("the claim's pool is missing")
        clid = int(claim.claim_id)
        if sender != claim.claimant:
            return self._refuse("only the claimant can refile claim #" + str(clid))
        st = str(claim.status)
        if st != CL_INCONCLUSIVE and st != CL_MISMATCH and \
                not (st == CL_FILED and int(claim.stalls) > 0):
            return self._refuse("claim #" + str(clid) + " is " + st.lower()
                                + "; only an INCONCLUSIVE, EVIDENCE_MISMATCH or "
                                "stalled claim is refiled")
        if st == CL_MISMATCH and int(claim.mismatch_refiles) >= MAX_MISMATCH_REFILES:
            return self._refuse("claim #" + str(clid) + " has used all "
                                + str(MAX_MISMATCH_REFILES) + " refiles after "
                                "EVIDENCE_MISMATCH")
        cover = self._cover(claim.cover_id)
        if cover is None:
            return self._refuse("the claim's cover is missing")
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        if now > int(claim.refile_until):
            return self._refuse("the refile window for claim #" + str(clid)
                                + " has closed")
        key = str(claim.incident_key)
        if _clean(incident_key, MAX_KEY) != "":
            key, why = self._key_check(cover, pool, incident_key, now)
            if why:
                return self._refuse("incident refused before judging: " + why)
        given = evidence_urls if _split_urls(evidence_urls) else claim.urls
        urls, why = _parse_urls(given, _split_csv(pool.domains_csv))
        if why:
            return self._refuse("evidence refused before judging: " + why)
        used = str(claim.used_urls).split(" ")
        fresh = 0
        for u in urls:
            if _url_key(u) not in used:
                fresh += 1
        if fresh == 0 and key == str(claim.incident_key):
            return self._refuse("every one of these URLs was already judged on "
                                "this claim for this incident; bring at least "
                                "one new source or a corrected incident key")
        if st == CL_MISMATCH:
            claim.mismatch_refiles = u32(int(claim.mismatch_refiles) + 1)
        claim.incident_key = key
        claim.urls = " ".join(urls)
        for u in urls:
            k = _url_key(u)
            if k not in used:
                used.append(k)
        claim.used_urls = " ".join([x for x in used if x])
        claim.statement = _clean(statement, MAX_STATEMENT)
        claim.last_filed_at = u64(now)
        claim.refiles = u32(int(claim.refiles) + 1)
        self._set_status(claim, CL_FILED)
        return {"status": "OK", "claim_id": clid, "refiles": int(claim.refiles),
                "incident_key": key,
                "mismatch_refiles_left": MAX_MISMATCH_REFILES
                - int(claim.mismatch_refiles),
                "note": "refiled; call judge_claim(" + str(clid) + ")"}

    def _join_batch(self, pool: Pool, claim: Claim, now: int) -> int:
        """Put an APPROVED claim into its incident's settlement window, opening
        one if none is open. Returns the batch id."""
        key = str(int(pool.pool_id)) + ":" + str(int(claim.incident_day))
        bid = int(self.open_batch.get(key) or 0)
        batch = self._batch(bid) if bid > 0 else None
        if batch is None or str(batch.status) != B_OPEN:
            bid = len(self.batches) + 1
            batch = self.batches.append_new_get()
            batch.batch_id = u32(bid)
            batch.pool_id = u32(int(pool.pool_id))
            batch.incident_day = u64(int(claim.incident_day))
            batch.opened_at = u64(now)
            batch.closes_at = u64(now + int(self.settlement_window_s))
            batch.status = B_OPEN
            self.open_batch[key] = u32(bid)
        self.batch_claims.get_or_insert_default(str(bid)).append(u32(int(claim.claim_id)))
        batch.members = u32(int(batch.members) + 1)
        claim.batch_id = u32(bid)
        return bid

    def _record(self, claim: Claim, d: dict, now: int) -> None:
        """Write an agreed, RE-DERIVED verdict onto a claim. Every value comes
        out of `d`, which `judge_claim` rebuilt after consensus (rule 11)."""
        claim.judged_at = u64(now)
        claim.classification = str(d.get("classification", ""))
        claim.event_match = str(d.get("event_match", ""))
        claim.effective = str(d.get("effective", ""))
        claim.peril = str(d.get("peril", NONE))
        claim.exclusion = str(d.get("exclusion", NONE))
        claim.strength = u32(_clamp(_as_int(d.get("strength"), 0), 0, TOP_STRENGTH))
        claim.strength_lo = u32(_clamp(_as_int(d.get("strength_lo"), 0), 0, TOP_STRENGTH))
        claim.strength_hi = u32(_clamp(_as_int(d.get("strength_hi"), 0), 0, TOP_STRENGTH))
        claim.incident_day = u64(_as_int(d.get("incident_day"), 0))
        claim.protocol_match = bool(d.get("protocol_match"))
        claim.bind_line = str(d.get("bind_line", ""))
        claim.bound = u32(_clamp(_as_int(d.get("bound"), 0), 0, 99))
        claim.llama_line = str(d.get("llama_line", ""))
        claim.tvl_line = str(d.get("tvl_line", ""))
        claim.tvl_before = u256(_clamp(_as_int(d.get("tvl_before"), 0), 0, 10 ** 30))
        claim.tvl_low = u256(_clamp(_as_int(d.get("tvl_low"), 0), 0, 10 ** 30))
        claim.drop_bps = u32(_clamp(_as_int(d.get("drop_bps"), 0), 0, BPS))
        claim.bucket = u32(_clamp(_as_int(d.get("bucket"), 0), 0, BUCKETS - 1))
        claim.sources = u32(_clamp(_as_int(d.get("sources"), 0), 0, 99))
        claim.bracket = ("P:" + _csv(d.get("allowed_perils") or []) + ";X:"
                         + _csv(d.get("allowed_exclusions") or []) + ";S:"
                         + str(_as_int(d.get("strength_lo"), 0)) + "-"
                         + str(_as_int(d.get("strength_hi"), 0)))
        claim.pinned = _short(str(d.get("pinned", "")), 300)
        claim.model_called = bool(d.get("model_called"))
        claim.content_hash = str(d.get("content_hash", ""))
        claim.digest = str(d.get("digest", ""))
        claim.reason = _short(str(d.get("reason", "")), MAX_REASON)

    @gl.public.write
    def judge_claim(self, claim_id: typing.Any) -> typing.Any:
        """Ask GenLayer's validators to read the evidence and classify it.
        PERMISSIONLESS - anyone may trigger, nobody is paid to. Works while
        paused.

        Each node independently fetches DeFi Llama's incident list and selects
        the ONE record the claim's key names, reads the TVL window around that
        record's day, fetches every evidence page and binds it to that record
        by date, computes the bracket, and - only if the evidence is about the
        selected incident and the bracket leaves a choice - asks its model. The full vector is
        compared (rule 10). THEN this file, not a model, applies the policy:
        backdating, cover end, exclusion, severity, deductible (`_outcome`).

        Moves no money: an APPROVED claim joins its incident's settlement
        window and is paid by `finalize_incident`, pro-rata with every other
        claim on the same incident."""
        self._bank()
        now = self._now()
        claim = self._claim(claim_id)
        if claim is None:
            return self._refuse("no claim with id " + str(_as_int(claim_id, 0)))
        cover = self._cover(claim.cover_id)
        pool = self._pool(claim.pool_id)
        if cover is None or pool is None:
            return self._refuse("the claim's cover or pool is missing")
        clid = int(claim.claim_id)
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        st = str(claim.status)
        if st == CL_JUDGING and now - int(claim.judging_since) < int(self.stall_ttl_s):
            return self._refuse("a judgement of claim #" + str(clid)
                                + " is already in flight",
                                {"stalls_at": int(claim.judging_since)
                                 + int(self.stall_ttl_s)})
        if st != CL_FILED and st != CL_JUDGING:
            return self._refuse("claim #" + str(clid) + " is " + st.lower()
                                + (" - refile it with new evidence" if
                                   st == CL_INCONCLUSIVE else "")
                                + "; nothing to judge")
        facts = self._claim_facts(claim, cover, pool, "claim")

        # Rule 3's documented exception: ATTEMPTS, a statistic about the path.
        self._set_status(claim, CL_JUDGING)
        claim.judging_since = u64(now)
        claim.attempts = u32(int(claim.attempts) + 1)
        self.total_judge_attempts = u256(int(self.total_judge_attempts) + 1)

        out = self._consensus(facts)

        if isinstance(out, dict) and out.get("retry"):
            self._set_status(claim, CL_FILED)
            claim.judging_since = u64(0)
            self.total_retries = u256(int(self.total_retries) + 1)
            return {"status": "OK", "claim_id": clid, "judged": False,
                    "outcome": "RETRY",
                    "reason": _short(str(out.get("why", "")), 200),
                    "note": "nothing changed; anyone may call judge_claim again"}
        if not _coherent(out, facts):
            self._set_status(claim, CL_FILED)
            claim.judging_since = u64(0)
            self.total_retries = u256(int(self.total_retries) + 1)
            return self._refuse("the validators did not return a usable verdict; "
                                "nothing changed and judge_claim can be retried")

        # RULE 11: rebuilt from the agreed raw inputs and choice.
        d = _derive(facts, out.get("raw"), out.get("choice"))
        self._record(claim, d, now)
        claim.judging_since = u64(0)
        status, gross = _outcome(str(d["effective"]), int(d["incident_day"]),
                                 int(cover.start), int(cover.end),
                                 int(pool.waiting_days) * DAY,
                                 int(cover.amount_wei), self._table(pool),
                                 int(d["bucket"]), int(pool.deductible_bps),
                                 bool(d["tvl_measured"]))
        table = self._table(pool)
        claim.table_bps = u32(table[_clamp(int(d["bucket"]), 0, BUCKETS - 1)])
        claim.gross_wei = u256(gross)
        self._set_status(claim, status)
        if status == CL_INCONCLUSIVE or status == CL_MISMATCH:
            claim.refile_until = u64(int(cover.claim_deadline))
        bid = 0
        if status == CL_APPROVED:
            bid = self._join_batch(pool, claim, now)
        self.total_judgements = u256(int(self.total_judgements) + 1)
        return {"status": "OK", "claim_id": clid, "judged": True,
                "outcome": status, "classification": str(d["classification"]),
                "event_match": str(d["event_match"]),
                "effective": str(d["effective"]), "peril": str(d["peril"]),
                "exclusion": str(d["exclusion"]),
                "incident_key": str(d["incident_key"]),
                "evidence_binding": str(d["bind_line"]),
                "incident_date": _date_text(d["incident_day"]),
                "protocol_match": bool(d["protocol_match"]),
                "severity_bucket": int(d["bucket"]),
                "drop_bps": int(d["drop_bps"]),
                "evidence_strength": int(d["strength"]),
                "content_hash": str(d["content_hash"]),
                "model_called": bool(d["model_called"]),
                "gross_payout_wei": str(gross), "batch_id": bid,
                "reason": str(d["reason"])}

    # --- writes: contest -----------------------------------------------------------

    @gl.public.write.payable
    def contest(self, claim_id: typing.Any, evidence_urls: str,
                statement: str) -> typing.Any:
        """The LOSING SIDE asks for a second reading, within the contest window,
        for a bond. The underwriter contests an APPROVED claim; the buyer
        contests a denial, a backdating rejection or a no-payout. INCONCLUSIVE is
        not contested - it is refiled, for free.

        NEW EVIDENCE MUST BE NOVEL, and that is checked mechanically BEFORE the
        bond is taken: every URL must be one this claim has never used, and the
        written grounds must add at least MIN_NOVEL_CHARS of sentences that
        neither the claim's statement nor its judged evidence digest already
        contain - verbatim, re-punctuated or repeated text counts for nothing
        (GrantJudge's sentence-novelty gate). Inside the re-judgement the same
        gate is applied to the new pages: a contest whose sources only repeat
        the judged evidence is NOT_NOVEL and the verdict holds."""
        self._bank()
        sender = gl.message.sender_address
        value = int(gl.message.value)
        now = self._now()
        claim = self._claim(claim_id)
        if claim is None:
            return self._refuse("no claim with id " + str(_as_int(claim_id, 0)))
        pool = self._pool(claim.pool_id)
        if pool is None:
            return self._refuse("the claim's pool is missing")
        clid = int(claim.claim_id)
        st = str(claim.status)
        if st not in CL_CONTESTABLE:
            return self._refuse("claim #" + str(clid) + " is " + st.lower()
                                + " and cannot be contested"
                                + (" - refile it instead" if st == CL_INCONCLUSIVE
                                   or st == CL_MISMATCH else ""))
        if str(claim.contest_status) != CT_NONE:
            return self._refuse("claim #" + str(clid) + " has already been "
                                "contested; one contest per claim")
        losing = pool.underwriter if st == CL_APPROVED else claim.claimant
        if sender != losing:
            return self._refuse("only the losing side may contest: the "
                                + ("underwriter" if st == CL_APPROVED else "claimant")
                                + " of claim #" + str(clid))
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        closes = int(claim.judged_at) + int(self.contest_window_s)
        if now > closes:
            return self._refuse("the contest window for claim #" + str(clid)
                                + " closed " + str(now - closes) + "s ago")
        bond = int(self.contest_bond_wei)
        if value < bond:
            return self._refuse("the contest bond is " + _gen(bond) + " GEN",
                                {"bond_wei": str(bond)})
        urls, why = _parse_urls(evidence_urls, _split_csv(pool.domains_csv))
        if why:
            return self._refuse("evidence refused before judging: " + why)
        used = str(claim.used_urls).split(" ")
        for u in urls:
            if _url_key(u) in used:
                return self._refuse("evidence URL " + _short(u, 80) + " was "
                                    "already judged on this claim; a contest "
                                    "must bring new sources")
        grounds = _clean(statement, MAX_STATEMENT)
        novel = _novel(grounds, str(claim.statement) + " " + str(claim.digest))
        if len(novel) < MIN_NOVEL_CHARS:
            return self._refuse("the contest's written grounds add nothing the "
                                "claim did not already say (verbatim, "
                                "re-punctuated and repeated sentences do not "
                                "count); state what the new evidence shows")
        if not self._take(sender, bond):
            return self._refuse("the bond could not be booked")
        claim.contest_status = CT_PENDING
        claim.contester = sender
        claim.contest_bond_wei = u256(bond)
        claim.contest_urls = " ".join(urls)
        claim.contest_statement = grounds
        claim.contested_at = u64(now)
        claim.status_before_contest = st
        self.total_contests = u256(int(self.total_contests) + 1)
        return {"status": "OK", "claim_id": clid, "bond_wei": str(bond),
                "overpaid_wei": str(value - bond),
                "note": ("contest filed; anyone may call judge_contest("
                         + str(clid) + "). If the outcome flips the bond comes "
                         "back; if it holds, the bond goes to the other side.")}

    @gl.public.write
    def judge_contest(self, claim_id: typing.Any) -> typing.Any:
        """Re-judge a contested claim. PERMISSIONLESS; works while paused.

        The validators read the NEW sources and keep only their NOVEL sentences;
        the combined text is the judged digest - taken from chain, not
        re-fetched, so an original page edited after judging changes nothing -
        plus what is genuinely new. DeFi Llama's record and TVL are re-read.
        Then `_outcome` decides, exactly as for the claim.

        FLIPPED - the claim moved across the line between paying and not - the
        bond is returned to the contester and the claim takes the new outcome.
        Otherwise the verdict holds and the bond goes to the other side."""
        self._bank()
        now = self._now()
        claim = self._claim(claim_id)
        if claim is None:
            return self._refuse("no claim with id " + str(_as_int(claim_id, 0)))
        cover = self._cover(claim.cover_id)
        pool = self._pool(claim.pool_id)
        if cover is None or pool is None:
            return self._refuse("the claim's cover or pool is missing")
        clid = int(claim.claim_id)
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        ct = str(claim.contest_status)
        if ct == CT_JUDGING and now - int(claim.contest_judging_since) < int(self.stall_ttl_s):
            return self._refuse("a contest judgement of claim #" + str(clid)
                                + " is already in flight")
        if ct != CT_PENDING and ct != CT_JUDGING:
            return self._refuse("claim #" + str(clid) + " has no pending contest")
        facts = self._claim_facts(claim, cover, pool, "contest")
        claim.contest_status = CT_JUDGING
        claim.contest_judging_since = u64(now)
        claim.contest_attempts = u32(int(claim.contest_attempts) + 1)
        self.total_judge_attempts = u256(int(self.total_judge_attempts) + 1)

        out = self._consensus(facts)

        if isinstance(out, dict) and out.get("retry"):
            claim.contest_status = CT_PENDING
            claim.contest_judging_since = u64(0)
            self.total_retries = u256(int(self.total_retries) + 1)
            return {"status": "OK", "claim_id": clid, "judged": False,
                    "outcome": "RETRY",
                    "reason": _short(str(out.get("why", "")), 200),
                    "note": "nothing changed; anyone may call judge_contest again"}
        if not _coherent(out, facts):
            claim.contest_status = CT_PENDING
            claim.contest_judging_since = u64(0)
            self.total_retries = u256(int(self.total_retries) + 1)
            return self._refuse("the validators did not return a usable verdict; "
                                "nothing changed and judge_contest can be retried")

        d = _derive(facts, out.get("raw"), out.get("choice"))
        old = str(claim.status)
        claim.contest_classification = str(d["classification"])
        claim.contest_effective = str(d["effective"])
        claim.contest_peril = str(d["peril"])
        claim.contest_exclusion = str(d["exclusion"])
        claim.contest_strength = u32(_clamp(_as_int(d["strength"], 0), 0, TOP_STRENGTH))
        claim.contest_bucket = u32(_clamp(_as_int(d["bucket"], 0), 0, BUCKETS - 1))
        claim.contest_drop_bps = u32(_clamp(_as_int(d["drop_bps"], 0), 0, BPS))
        claim.contest_content_hash = str(d["content_hash"])
        claim.contest_novel = str(d["novel"])
        claim.contest_reason = _short(str(d["reason"]), MAX_REASON)
        claim.contest_resolved_at = u64(now)
        claim.contest_judging_since = u64(0)

        bond = int(claim.contest_bond_wei)
        claim.contest_bond_wei = u256(0)
        other = claim.claimant if claim.contester == pool.underwriter \
            else pool.underwriter
        if str(d["novel"]) == "":
            claim.contest_status = CT_NOT_NOVEL
            self._release_to(other, bond)
            return {"status": "OK", "claim_id": clid, "contest": CT_NOT_NOVEL,
                    "outcome": old, "bond_to": other.as_hex,
                    "reason": str(d["reason"])}
        new, gross = _outcome(str(d["effective"]), int(d["incident_day"]),
                              int(cover.start), int(cover.end),
                              int(pool.waiting_days) * DAY,
                              int(cover.amount_wei), self._table(pool),
                              int(d["bucket"]), int(pool.deductible_bps),
                                 bool(d["tvl_measured"]))
        flipped = (new == CL_APPROVED) != (old == CL_APPROVED)
        if not flipped:
            claim.contest_status = CT_UPHELD
            self._release_to(other, bond)
            return {"status": "OK", "claim_id": clid, "contest": CT_UPHELD,
                    "outcome": old, "rejudged_as": new,
                    "bond_to": other.as_hex, "reason": str(d["reason"])}
        claim.contest_status = CT_FLIPPED
        self.total_flipped = u256(int(self.total_flipped) + 1)
        self._release_to(claim.contester, bond)
        self._set_status(claim, new)
        claim.gross_wei = u256(gross)
        table = self._table(pool)
        claim.table_bps = u32(table[_clamp(int(d["bucket"]), 0, BUCKETS - 1)])
        if new == CL_INCONCLUSIVE or new == CL_MISMATCH:
            claim.refile_until = u64(int(cover.claim_deadline))
        bid = 0
        if new == CL_APPROVED:
            if int(claim.incident_day) <= 0:
                claim.incident_day = u64(int(d["incident_day"]))
            bid = self._join_batch(pool, claim, now)
        return {"status": "OK", "claim_id": clid, "contest": CT_FLIPPED,
                "outcome": new, "was": old, "bond_to": claim.contester.as_hex,
                "gross_payout_wei": str(gross), "batch_id": bid,
                "reason": str(d["reason"])}

    # --- writes: settlement ------------------------------------------------------

    @gl.public.write
    def finalize_incident(self, batch_id: typing.Any) -> typing.Any:
        """Pay every claim approved on one incident, TOGETHER. PERMISSIONLESS;
        works while paused.

        Only after the settlement window closes and every member's contest
        window has closed with no contest open - so the set of claims is final
        before anything is divided. Then: available = the collateral locked for
        exactly those covers; if the approved payouts exceed it, every payout
        is scaled by the same factor (`_prorata`), integer arithmetic, dust to
        the underwriter. First-come gets nothing extra.

        IT CREDITS, IT DOES NOT TRANSFER (rule 12). This method reads the clock;
        `claim_payout()` - which does not - posts the transfer."""
        self._bank()
        now = self._now()
        batch = self._batch(batch_id)
        if batch is None:
            return self._refuse("no settlement batch with id "
                                + str(_as_int(batch_id, 0)))
        bid = int(batch.batch_id)
        pool = self._pool(batch.pool_id)
        if pool is None:
            return self._refuse("the batch's pool is missing")
        if str(batch.status) != B_OPEN:
            return self._refuse("batch #" + str(bid) + " is already finalized")
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        if now < int(batch.closes_at):
            return self._refuse("the settlement window for this incident closes "
                                "in " + str(int(batch.closes_at) - now) + "s",
                                {"closes_at": int(batch.closes_at)})
        members = self._ids(self.batch_claims.get(str(bid)))
        live = []
        for clid in members:
            claim = self._claim(clid)
            if claim is None or str(claim.status) != CL_APPROVED:
                continue
            if str(claim.contest_status) in CT_OPEN:
                return self._refuse("claim #" + str(clid) + " in this incident "
                                    "is under contest")
            if str(claim.contest_status) == CT_NONE and \
                    now <= int(claim.judged_at) + int(self.contest_window_s):
                return self._refuse("claim #" + str(clid) + " can still be "
                                    "contested for " + str(int(claim.judged_at)
                                                           + int(self.contest_window_s) - now)
                                    + "s")
            live.append(claim)
        grosses = []
        available = 0
        for claim in live:
            cover = self._cover(claim.cover_id)
            grosses.append(int(claim.gross_wei))
            available += int(cover.lock_wei) if cover is not None else 0
        pays, dust = _prorata(grosses, available)
        paid = 0
        for i in range(len(live)):
            claim = live[i]
            cover = self._cover(claim.cover_id)
            amount = int(pays[i])
            claim.payout_wei = u256(amount)
            self._set_status(claim, CL_PAID)
            if cover is not None:
                cap = int(pool.capital_wei)
                pool.capital_wei = u256(cap - amount if cap >= amount else 0)
                self._release_to(cover.buyer, amount)
                cover.payout_wei = u256(amount)
                self._earn(pool, int(cover.premium_wei))
                self._end_cover(pool, cover, COVER_PAID, now)
            paid += amount
        pool.paid_out_wei = u256(int(pool.paid_out_wei) + paid)
        total = 0
        for g in grosses:
            total += g
        batch.status = B_FINALIZED
        batch.finalized_at = u64(now)
        batch.paid_members = u32(len(live))
        batch.gross_total_wei = u256(total)
        batch.available_wei = u256(available)
        batch.paid_total_wei = u256(paid)
        batch.dust_wei = u256(dust)
        batch.scaled = total > available
        key = str(int(pool.pool_id)) + ":" + str(int(batch.incident_day))
        if int(self.open_batch.get(key) or 0) == bid:
            self.open_batch[key] = u32(0)
        self.total_batches_finalized = u256(int(self.total_batches_finalized) + 1)
        if total > available:
            self.total_scaled_batches = u256(int(self.total_scaled_batches) + 1)
        self.total_payouts_wei = u256(int(self.total_payouts_wei) + paid)
        return {"status": "OK", "batch_id": bid, "claims_paid": len(live),
                "gross_total_wei": str(total), "available_wei": str(available),
                "paid_total_wei": str(paid), "scaled": total > available,
                "factor_bps": (available * BPS // total) if total > available
                and total > 0 else BPS,
                "dust_to_underwriter_wei": str(dust),
                "claim_with": "claim_payout()"}

    @gl.public.write
    def settle_stalled(self, claim_id: typing.Any) -> typing.Any:
        """Unstick a claim or a contest the network could not judge.
        PERMISSIONLESS, AND IT WORKS WHILE PAUSED (rule 6) - by design and by
        test, because an owner who could pause the one call that unblocks a
        stuck claim could freeze every pool by doing nothing.

        NO MONEY IS LOST EITHER WAY:
          - a CLAIM filed, refiled or in judgement for longer than the stall
            window with no verdict goes back to FILED, and the buyer may refile
            it with different evidence - even past the claim deadline, for one
            more stall window - because a network that could not read their
            evidence must not cost them their claim;
          - a CONTEST pending for longer than the stall window with no verdict
            is dropped: the bond goes back to the contester in full and the
            verdict under contest stands."""
        self._bank()
        now = self._now()
        claim = self._claim(claim_id)
        if claim is None:
            return self._refuse("no claim with id " + str(_as_int(claim_id, 0)))
        clid = int(claim.claim_id)
        if now <= 0:
            return self._refuse("the block time was unreadable; retry")
        ttl = int(self.stall_ttl_s)
        ct = str(claim.contest_status)
        if ct in CT_OPEN:
            since = int(claim.contested_at)
            if int(claim.contest_judging_since) > since:
                since = int(claim.contest_judging_since)
            if now - since < ttl:
                return self._refuse("the contest on claim #" + str(clid)
                                    + " is not stalled; it becomes settleable in "
                                    + str(since + ttl - now) + "s")
            bond = int(claim.contest_bond_wei)
            claim.contest_bond_wei = u256(0)
            claim.contest_status = CT_STALLED
            claim.contest_resolved_at = u64(now)
            claim.contest_judging_since = u64(0)
            self._release_to(claim.contester, bond)
            return {"status": "OK", "claim_id": clid, "settled": "CONTEST",
                    "bond_returned_wei": str(bond),
                    "outcome": str(claim.status),
                    "note": "the contest was never judged; the bond is returned "
                            "and the verdict under contest stands"}
        st = str(claim.status)
        if st != CL_FILED and st != CL_JUDGING:
            return self._refuse("claim #" + str(clid) + " is " + st.lower()
                                + " and is not stuck")
        since = int(claim.last_filed_at)
        if int(claim.judging_since) > since:
            since = int(claim.judging_since)
        if now - since < ttl:
            return self._refuse("claim #" + str(clid) + " has not been stuck long "
                                "enough; it becomes settleable in "
                                + str(since + ttl - now) + "s",
                                {"stalls_at": since + ttl})
        self._set_status(claim, CL_FILED)
        claim.judging_since = u64(0)
        claim.stalls = u32(int(claim.stalls) + 1)
        claim.last_filed_at = u64(now)
        until = now + ttl
        if int(claim.refile_until) > until:
            until = int(claim.refile_until)
        claim.refile_until = u64(until)
        return {"status": "OK", "claim_id": clid, "settled": "CLAIM",
                "outcome": CL_FILED, "refile_until": until,
                "note": ("back to FILED: judge_claim may be retried, and the "
                         "claimant may refile with different evidence until "
                         + str(until))}

    @gl.public.write
    def claim_payout(self) -> typing.Any:
        """Withdraw everything this wallet is owed: payouts, refunds, earned
        premiums, withdrawn capacity, returned bonds, overpayments and any value
        a refused call carried. THE ONLY METHOD THAT TRANSFERS, and it reads no
        clock (rule 12). Not gated on `paused` (rule 6)."""
        self._bank()
        sender = gl.message.sender_address
        owed = int(self.payout_wei.get(sender) or 0)
        if owed <= 0:
            return self._refuse("this wallet is owed nothing")
        paid = self._settle_payout(sender)
        return {"status": "OK", "paid_wei": str(paid), "paid_gen": _gen(paid),
                "note": "the transfer is posted on finalisation of this transaction"}

    # --- owner -----------------------------------------------------------------

    @gl.public.write
    def set_paused(self, paused: typing.Any) -> typing.Any:
        """Stop NEW pools, NEW capacity and NEW covers. That is the whole of the
        owner's power, and the list of what it does NOT stop is the point:
        filing, judging, refiling, contesting, finalising, releasing,
        cancelling, withdrawing, closing, settle_stalled and claim_payout all
        keep working (rule 6)."""
        self._bank()
        if not self._is_owner():
            return self._refuse("only the contract owner can pause new business")
        want = _as_bool(paused)
        self.paused = want
        return {"status": "OK", "paused": want,
                "note": ("claims, judgements, contests, settlements, releases, "
                         "withdrawals, settle_stalled and payouts remain open")}

    @gl.public.write
    def transfer_ownership(self, new_owner: str) -> typing.Any:
        self._bank()
        if not self._is_owner():
            return self._refuse("only the contract owner can transfer ownership")
        if not _is_addr(new_owner):
            return self._refuse("not an address: " + _short(new_owner, 60))
        self.owner = Address(str(new_owner).strip())
        return {"status": "OK", "owner": self.owner.as_hex}
