# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
import genlayer as gl
from genlayer import *
from dataclasses import dataclass
import typing

# CoverRegistry - the block another protocol copies.
#
# A lending market, a vault or a DAO treasury that wants to know "is this
# wallet's position on protocol X actually insured right now?" asks this
# contract, and this contract asks CoverClaim. It holds NO MONEY, has NO
# JUDGING CODE and stores NO VERDICTS of its own: every answer is a free
# cross-contract read of CoverClaim's views.
#
# CUSTODY: FALSE. There is not one `@gl.public.write.payable` method in this
# file and no `emit_transfer` anywhere in it. There is not one `raise`
# statement either: a registry is a gate, and a gate that reverts on a
# transport failure would make "CoverClaim could not be read" look like "this
# wallet is not covered", which are two different answers.
#
# The one write, `attest`, records a SNAPSHOT of what CoverClaim said about a
# wallet at a moment, so that an integrator can later prove what it relied on.
# It accepts no value.


def _as_int(v: typing.Any, default: int = 0) -> int:
    if isinstance(v, bool):
        return default
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        t = v.strip()
        if t.isdigit():
            return int(t)
    return default


def _short(s: typing.Any, n: int = 160) -> str:
    t = str(s)
    return t if len(t) <= n else t[:n]


def _is_addr(text: typing.Any) -> bool:
    t = str(text).strip()
    if len(t) != 42 or not t.startswith("0x"):
        return False
    for ch in t[2:]:
        if ch not in "0123456789abcdefABCDEF":
            return False
    return True


@gl.contract.interface
class ICoverClaim:
    """CoverClaim's public surface as this registry uses it. Type stubs only."""

    class View:
        def get_active_cover(self, address: str, protocol: str) -> typing.Any: ...

        def get_covers_by_buyer(self, address: str) -> typing.Any: ...

        def get_config(self) -> typing.Any: ...

    class Write:
        pass


@gl.storage.allow
@dataclass
class Attestation:
    """What CoverClaim said about one wallet and one protocol at one moment."""
    holder: Address
    protocol: str
    covered: bool
    cover_id: u32
    pool_id: u32
    amount_wei: u256
    start: u64
    end: u64
    demo: bool
    recorded_by: Address
    reason: str


class CoverRegistry(gl.contract.Contract):
    owner: Address
    coverclaim: Address
    attestations: gl.storage.DynArray[Attestation]
    total_covered: u256
    total_uncovered: u256

    def __init__(self, coverclaim_address: str):
        self.owner = gl.message.sender_address
        self.coverclaim = Address(str(coverclaim_address).strip())
        self.total_covered = u256(0)
        self.total_uncovered = u256(0)

    def _ask(self, address: str, protocol: str) -> dict:
        """The non-reverting read, with the transport failure folded in: a
        CoverClaim that cannot be read is NOT a wallet that is uncovered, and
        the answer says which it was."""
        if not _is_addr(address):
            return {"found": False, "reachable": True, "reason": "not an address"}
        try:
            got = ICoverClaim(self.coverclaim).view().get_active_cover(
                str(address), str(protocol))
        except Exception as e:
            return {"found": False, "reachable": False,
                    "reason": "CoverClaim could not be read: " + _short(e)}
        if not isinstance(got, dict):
            return {"found": False, "reachable": False,
                    "reason": "CoverClaim returned nothing usable"}
        got["reachable"] = True
        return got

    @gl.public.view
    def is_covered(self, address: str, protocol: str) -> bool:
        """True only if the wallet holds an ACTIVE cover on `protocol` that is
        IN FORCE: past its waiting period and before its end. A cover still in
        its waiting period is not cover yet, and an unreadable clock or an
        unreachable CoverClaim is never read as covered."""
        got = self._ask(address, protocol)
        return bool(got.get("found")) and bool(got.get("in_force"))

    @gl.public.view
    def get_active_cover(self, address: str) -> typing.Any:
        """The wallet's live covers across every protocol, strongest first,
        straight from CoverClaim."""
        if not _is_addr(address):
            return {"items": [], "reason": "not an address"}
        try:
            got = ICoverClaim(self.coverclaim).view().get_covers_by_buyer(str(address))
        except Exception as e:
            return {"items": [], "reachable": False,
                    "reason": "CoverClaim could not be read: " + _short(e)}
        items = []
        if isinstance(got, dict) and isinstance(got.get("items"), list):
            for c in got["items"]:
                if isinstance(c, dict) and str(c.get("status", "")) == "ACTIVE":
                    items.append(c)
        best = None
        for c in items:
            if best is None or (bool(c.get("in_force")) and not bool(best.get("in_force"))) \
                    or (bool(c.get("in_force")) == bool(best.get("in_force"))
                        and _as_int(c.get("amount_wei"), 0) > _as_int(best.get("amount_wei"), 0)):
                best = c
        return {"reachable": True, "count": len(items), "best": best,
                "items": items}

    @gl.public.write
    def attest(self, address: str, protocol: str) -> typing.Any:
        """Record what CoverClaim says about `address` on `protocol` right now.
        Anyone may call; nobody pays; nothing reverts. An unreachable CoverClaim
        records nothing and says so."""
        got = self._ask(address, protocol)
        if not got.get("reachable"):
            return {"status": "REJECTED", "reason": str(got.get("reason", ""))}
        if not _is_addr(address):
            return {"status": "REJECTED", "reason": "not an address"}
        covered = bool(got.get("found")) and bool(got.get("in_force"))
        row = self.attestations.append_new_get()
        row.holder = Address(str(address).strip())
        row.protocol = _short(protocol, 80)
        row.covered = covered
        row.cover_id = u32(_as_int(got.get("cover_id"), 0))
        row.pool_id = u32(_as_int(got.get("pool_id"), 0))
        row.amount_wei = u256(_as_int(got.get("amount_wei"), 0))
        row.start = u64(_as_int(got.get("start"), 0))
        row.end = u64(_as_int(got.get("end"), 0))
        row.demo = bool(got.get("demo"))
        row.recorded_by = gl.message.sender_address
        row.reason = _short(got.get("reason", ""), 160)
        if covered:
            self.total_covered = u256(int(self.total_covered) + 1)
        else:
            self.total_uncovered = u256(int(self.total_uncovered) + 1)
        return {"status": "OK", "index": len(self.attestations) - 1,
                "covered": covered, "cover_id": int(row.cover_id)}

    @gl.public.view
    def get_attestation(self, index: typing.Any) -> typing.Any:
        i = _as_int(index, -1)
        if i < 0 or i >= len(self.attestations):
            return {"found": False}
        a = self.attestations[i]
        return {"found": True, "index": i, "holder": a.holder.as_hex,
                "protocol": str(a.protocol), "covered": bool(a.covered),
                "cover_id": int(a.cover_id), "pool_id": int(a.pool_id),
                "amount_wei": str(int(a.amount_wei)), "start": int(a.start),
                "end": int(a.end), "demo": bool(a.demo),
                "recorded_by": a.recorded_by.as_hex, "reason": str(a.reason)}

    @gl.public.view
    def get_config(self) -> typing.Any:
        return {"coverclaim": self.coverclaim.as_hex, "owner": self.owner.as_hex,
                "custody": False, "payable_methods": 0,
                "attestations": len(self.attestations),
                "covered": int(self.total_covered),
                "uncovered": int(self.total_uncovered),
                "rule": ("covered = an ACTIVE cover on the protocol, past its "
                         "waiting period and before its end, read from "
                         "CoverClaim at call time")}
