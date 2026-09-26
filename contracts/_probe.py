# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
import genlayer as gl
from genlayer import *

import json

# Throwaway diagnostic, NOT part of CoverClaim. It answers the questions the
# evidence allowlist is built from, BEFORE a line of judging code is written:
#
#   1. Can a validator GET https://api.llama.fi/hacks, parse it, and find one
#      protocol's incident rows by defillamaId?
#   2. Can a validator GET https://api.llama.fi/protocol/{slug} (up to tens of
#      MB) and measure the TVL drop around an incident date, in integers?
#   3. Can a validator read a rekt.news article, an official post-mortem and a
#      web.archive.org snapshot - and does the text come back IDENTICAL on a
#      second node (the `strict` variants make the validator re-fetch and vote
#      on the hash, so an ACCEPTED strict probe is a cross-node stability test)?
#
# The two header lines above are the whole of what GenVM reads before the code.


def _status(res) -> int:
    s = getattr(res, "status_code", None)
    if s is None:
        s = getattr(res, "status", None)
    try:
        return int(s)
    except Exception:
        return 0


def _body(res) -> str:
    b = getattr(res, "body", None)
    if b is None:
        b = getattr(res, "text", None)
    if b is None:
        return ""
    if isinstance(b, bytes):
        return b.decode("utf-8", errors="ignore")
    return str(b)


def _get(url: str) -> tuple:
    try:
        try:
            res = gl.nondet.web.request(url, method="GET")
        except AttributeError:
            res = gl.nondet.web.get(url)
    except Exception as e:
        return (-1, "", str(e)[:300])
    return (_status(res), _body(res), "")


def _render(url: str) -> tuple:
    try:
        txt = gl.nondet.web.render(url, mode="text", wait_after_loaded="3s")
    except Exception as e:
        return (False, "", str(e)[:300])
    return (True, str(txt), "")


def _norm(text: str) -> str:
    out = []
    for ch in str(text).lower():
        out.append(ch if ch.isalnum() else " ")
    return " ".join("".join(out).split())


def _fnv(s: str) -> str:
    h = 0xCBF29CE484222325
    for ch in s:
        h ^= ord(ch) & 0xFF
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return format(h, "016x")


def _hacks(body: str, want_id: str) -> dict:
    try:
        rows = json.loads(body)
    except Exception:
        return {"err": "unparseable"}
    if not isinstance(rows, list):
        return {"err": "not a list"}
    hits = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if str(r.get("defillamaId", "")) == want_id:
            hits.append({"date": int(r.get("date") or 0),
                         "name": str(r.get("name", ""))[:60],
                         "classification": str(r.get("classification", ""))[:60],
                         "technique": str(r.get("technique", ""))[:60],
                         "amount": int(r.get("amount") or 0),
                         "chain": str(r.get("chain", ""))[:80],
                         "source": str(r.get("source", ""))[:120]})
    keys = sorted([str(k) for k in rows[0].keys()]) if len(rows) > 0 and isinstance(rows[0], dict) else []
    return {"rows": len(rows), "keys": keys, "hits": hits}


def _tvl(body: str, day: int) -> dict:
    try:
        doc = json.loads(body)
    except Exception:
        return {"err": "unparseable"}
    if not isinstance(doc, dict):
        return {"err": "not an object"}
    series = doc.get("tvl")
    if not isinstance(series, list):
        return {"err": "no tvl series", "keys": sorted([str(k) for k in doc.keys()])[:40]}
    before = -1
    before_at = 0
    low = -1
    low_at = 0
    n_after = 0
    for p in series:
        if not isinstance(p, dict):
            continue
        d = p.get("date")
        v = p.get("totalLiquidityUSD")
        if not isinstance(d, (int, float)) or not isinstance(v, (int, float)):
            continue
        d = int(d)
        v = int(v)
        if d < day and d >= before_at:
            before_at = d
            before = v
        if d >= day and d <= day + 7 * 86400:
            n_after += 1
            if low < 0 or v < low:
                low = v
                low_at = d
    drop = 0
    if before > 0 and low >= 0 and low < before:
        drop = (before - low) * 10000 // before
    return {"id": str(doc.get("id", "")), "name": str(doc.get("name", ""))[:60],
            "points": len(series), "before": before, "before_at": before_at,
            "low": low, "low_at": low_at, "after_points": n_after,
            "drop_bps": drop, "url": str(doc.get("url", ""))[:80]}


class CoverProbe(gl.contract.Contract):
    results: gl.storage.TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def http_probe(self, key: str, url: str, mode: str, arg: str) -> None:
        """GET one URL. mode: raw | hacks (arg = defillamaId) | tvl (arg =
        incident day as epoch seconds)."""
        target = str(url)
        m = str(mode)
        a = str(arg)

        def leader_fn() -> dict:
            st, body, err = _get(target)
            out = {"status": st, "len": len(body), "err": err}
            if m == "hacks" and st == 200:
                out["hacks"] = _hacks(body, a)
            elif m == "tvl" and st == 200:
                try:
                    day = int(a)
                except Exception:
                    day = 0
                out["tvl"] = _tvl(body, day)
            else:
                norm = _norm(body)
                out["hash"] = _fnv(norm)
                out["head"] = body[:2500]
            return out

        def validator_fn(leader_result) -> bool:
            return isinstance(leader_result, gl.vm.Return)

        res = gl.vm.run_nondet(leader_fn, validator_fn)
        self.results[str(key)] = json.dumps(res)

    @gl.public.write
    def render_probe(self, key: str, url: str, strict: bool) -> None:
        """Render one page as text. With `strict`, every validator renders it
        too and votes on the normalised hash - an ACCEPTED strict probe is a
        measurement that two nodes read the same bytes."""
        target = str(url)
        want_strict = bool(strict)

        def leader_fn() -> dict:
            ok, txt, err = _render(target)
            norm = _norm(txt)
            return {"ok": ok, "len": len(txt), "norm_len": len(norm),
                    "hash": _fnv(norm), "err": err, "head": txt[:3000],
                    "tail": txt[-1500:] if len(txt) > 1500 else ""}

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            if not want_strict:
                return True
            ok, txt, err = _render(target)
            theirs = leader_result.calldata
            return isinstance(theirs, dict) and str(theirs.get("hash", "")) == _fnv(_norm(txt))

        res = gl.vm.run_nondet(leader_fn, validator_fn)
        self.results[str(key)] = json.dumps(res)

    @gl.public.write
    def get_text_probe(self, key: str, url: str, strict: bool) -> None:
        """Plain GET of an HTML page with tags stripped by hand - the render
        alternative. Same strict semantics as render_probe."""
        target = str(url)
        want_strict = bool(strict)

        def strip(html: str) -> str:
            out = []
            depth = 0
            skip = ""
            i = 0
            low = html.lower()
            n = len(html)
            while i < n:
                if skip:
                    j = low.find("</" + skip, i)
                    if j < 0:
                        break
                    i = j + len(skip) + 2
                    skip = ""
                    continue
                ch = html[i]
                if ch == "<":
                    if low.startswith("<script", i):
                        skip = "script"
                    elif low.startswith("<style", i):
                        skip = "style"
                    j = html.find(">", i)
                    if j < 0:
                        break
                    i = j + 1
                    out.append(" ")
                    continue
                out.append(ch)
                i += 1
            return " ".join("".join(out).split())

        def leader_fn() -> dict:
            st, body, err = _get(target)
            txt = strip(body)
            norm = _norm(txt)
            return {"status": st, "len": len(body), "text_len": len(txt),
                    "hash": _fnv(norm), "err": err, "head": txt[:3000]}

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            if not want_strict:
                return True
            st, body, err = _get(target)
            theirs = leader_result.calldata
            return isinstance(theirs, dict) and str(theirs.get("hash", "")) == _fnv(_norm(strip(body)))

        res = gl.vm.run_nondet(leader_fn, validator_fn)
        self.results[str(key)] = json.dumps(res)

    @gl.public.write
    def llm_probe(self, key: str, prompt: str) -> None:
        """One exec_prompt, leader-only answer accepted by shape. Isolates the
        model call from every fetch."""
        text = str(prompt)

        def leader_fn() -> dict:
            try:
                raw = gl.nondet.exec_prompt(text, response_format="json")
                return {"ok": True, "answer": json.dumps(raw)[:2000]}
            except Exception as e:
                return {"ok": False, "err": str(e)[:600]}

        def validator_fn(leader_result) -> bool:
            return isinstance(leader_result, gl.vm.Return)

        res = gl.vm.run_nondet(leader_fn, validator_fn)
        self.results[str(key)] = json.dumps(res)

    @gl.public.view
    def get(self, key: str) -> str:
        return self.results.get(str(key)) or ""
