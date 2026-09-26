"""Runtime stub for the CoverClaim offline suite: the v0.6 `genlayer`
namespace, a storage model faithful to the runner's missing-key semantics, a
fake web (api.llama.fi JSON and rendered pages) and a fake model. Ported from
the GrantJudge/WillExecutor harness; see test_logic.py for what is tested."""

import ast
import builtins
import sys
import types
from pathlib import Path

_UNSET = object()


# ---------------------------------------------------------------------------
# runtime stub
#
# Ported from the proven CourtRoom/WillExecutor harness and kept on the v0.6 runner
# namespace: `gl.contract.Contract`, `gl.storage.TreeMap`, `gl.storage.DynArray`,
# `gl.storage.allow`, `gl.message.raw`, `gl.chain.Account`. A stub still shaped
# like an older namespace would let every test pass against a contract the
# current runner cannot even load.
#
# The TreeMap missing-key semantics in particular are load-bearing: on chain a
# map with a SCALAR value type answers a missing key with that type's ZERO, not
# with None, so a presence check written as `is not None` matches everything. A
# stub that returned None could never reproduce that bug.
# ---------------------------------------------------------------------------


class _UserError(Exception):
    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message


class _Return:
    """gl.vm.Return - a leader result carrying its calldata."""

    def __init__(self, calldata):
        self.calldata = calldata


class _Rollback:
    def __init__(self, message=""):
        self.message = message


class _Addr:
    """Address. Compared and keyed by its lowercase text, like the real one, and
    carrying `.as_hex`, which is the ONLY spelling the runner guarantees. A stub
    whose `str()` happened to produce the hex would hide every place the
    contract forgot `.as_hex`."""

    def __init__(self, value=""):
        v = str(value)
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("not an address: " + v[:60])
        for ch in v[2:]:
            if ch not in "0123456789abcdefABCDEF":
                raise ValueError("not an address: " + v[:60])
        self._v = v.lower()

    @property
    def as_hex(self):
        return self._v

    def __str__(self):
        return self._v

    def __repr__(self):
        return "Address(" + self._v + ")"

    def __eq__(self, other):
        return isinstance(other, _Addr) and self._v == other._v

    def __hash__(self):
        return hash(self._v)


class _TreeMap(dict):
    """Models the runtime's TreeMap, INCLUDING what it returns for a key that is
    not there."""

    _value_type = None

    @classmethod
    def __class_getitem__(cls, item):
        vt = item[1] if isinstance(item, tuple) and len(item) > 1 else None
        return type("_TreeMapOf", (cls,), {"_value_type": vt})

    def _k(self, key):
        return str(key) if isinstance(key, _Addr) else key

    def _missing(self):
        vt = type(self)._value_type
        if vt is None:
            return None
        name = getattr(vt, "__name__", str(vt))
        if name.startswith("_TreeMap") or name.startswith("_DynArray"):
            return _zero_for(vt)
        if vt is int or vt is str or vt is bool:
            return _zero_for(vt)
        if hasattr(vt, "__annotations__") and getattr(vt, "__annotations__"):
            return None
        return _zero_for(vt)

    def get(self, key, default=_UNSET):
        k = self._k(key)
        if k in self:
            return dict.__getitem__(self, k)
        if default is not _UNSET:
            return default
        return self._missing()

    def __contains__(self, key):
        return dict.__contains__(self, self._k(key))

    def __setitem__(self, key, value):
        dict.__setitem__(self, self._k(key), value)

    def __getitem__(self, key):
        """Indexing a key the map does not hold RAISES KeyError, exactly as the
        runner does.

        This stub used to auto-create the entry instead, and that single line
        of convenience hid a real revert: `self.by_owner[sender].append(...)`
        passed 431 offline tests and then died on chain inside `create_will`,
        on the one path that had already banked a deposit. `get_or_insert_default`
        is the spelling that inserts. A stub that is more forgiving than the
        runner is a stub that certifies bugs."""
        return dict.__getitem__(self, self._k(key))

    def __delitem__(self, key):
        dict.__delitem__(self, self._k(key))

    def get_or_insert_default(self, key):
        k = self._k(key)
        if k not in self:
            dict.__setitem__(self, k, self._factory())
        return dict.__getitem__(self, k)

    def _factory(self):
        vt = type(self)._value_type
        if vt is None:
            return _DynArray()
        if hasattr(vt, "__annotations__") and getattr(vt, "__annotations__"):
            return _make_struct(vt)
        return _zero_for(vt)


class _DynArray(list):
    """Models DynArray, INCLUDING `append_new_get()`.

    On chain a DynArray of structs cannot be appended to with a constructed
    value, so the runtime allocates a zeroed element in place and hands back a
    REFERENCE to it. Reproducing that matters for more than API coverage: the
    returned object must be the SAME object the array holds, or a later
    mutation through the reference would be invisible in the array, and every
    test would pass while every will written on chain stayed zero."""

    _elem_type = None

    @classmethod
    def __class_getitem__(cls, item):
        return type("_DynArrayOf", (cls,), {"_elem_type": item})

    def append_new_get(self):
        elem = type(self)._elem_type
        value = _make_struct(elem) if elem is not None and \
            hasattr(elem, "__annotations__") else _zero_for(elem)
        list.append(self, value)
        return value


def _zero_for(annotation):
    """The value the runtime auto-initialises a storage field to."""
    name = getattr(annotation, "__name__", str(annotation))
    if annotation is bool or name == "bool":
        return False
    if annotation is str or name == "str":
        return ""
    if name == "_Addr" or name == "Address":
        return _Addr("0x" + "0" * 40)
    if name.startswith("_TreeMap") or name == "TreeMap":
        return annotation() if isinstance(annotation, type) else _TreeMap()
    if name.startswith("_DynArray") or name == "DynArray":
        return annotation() if isinstance(annotation, type) else _DynArray()
    if name.startswith("u") or name.startswith("i"):
        return 0
    if hasattr(annotation, "__annotations__"):
        return _make_struct(annotation)
    return 0


def _make_struct(cls):
    obj = cls.__new__(cls)
    for field, ann in getattr(cls, "__annotations__", {}).items():
        setattr(obj, field, _zero_for(ann))
    return obj


class _Contract:
    """gl.contract.Contract. Storage fields are declared as class annotations and
    never assigned before use, exactly as on chain, so they are created on
    demand."""

    balance = 0

    def __getattr__(self, name):
        anns = {}
        for klass in reversed(type(self).__mro__):
            anns.update(getattr(klass, "__annotations__", {}))
        if name in anns:
            value = _zero_for(anns[name])
            object.__setattr__(self, name, value)
            return value
        raise AttributeError(name)


TRANSFERS = []
BALANCES = {}
# address text -> contract instance, for cross-contract reads offline.
CONTRACTS = {}


class _Proxy:
    """gl.contract.Proxy. `.emit()` is a METHOD GETTER, exactly like the
    runner's, and it records NOTHING. That is the whole point: on chain,
    `emit()` with no method call after it constructs a namespace and drops it,
    posting no message. A stub that treated a bare `emit(value=...)` as a
    transfer would make this suite agree with a contract that silently never
    pays - which is precisely the bug that shipped once and had to be caught on
    chain by comparing real balances."""

    def __init__(self, address):
        self.address = address

    def view(self, **_k):
        """A cross-contract READ, routed to a contract this process is already
        holding.

        `CONTRACTS` is the offline stand-in for the chain's own register. It
        exists so that CoverRegistry can be driven against a REAL CoverClaim
        rather than against a mock of one - a consumer tested against a mock of
        the oracle is a consumer that has never been tested against the oracle's
        actual refusals, which are the whole of what it is for."""
        target = CONTRACTS.get(str(self.address))
        if target is None:
            raise RuntimeError("no contract at " + str(self.address))
        return target

    def emit(self, **_k):
        return None

    def emit_transfer(self, value, **_k):
        if int(value) <= 0:
            raise ValueError("value must be greater than 0 for emit_transfer")
        key = str(self.address)
        TRANSFERS.append((key, int(value)))
        BALANCES[key] = BALANCES.get(key, 0) + int(value)


class _Account:
    """gl.chain.Account - the wrapper the SDK documents for ANY on-chain
    account, contract or EOA.

    Its `emit_transfer` DELIVERS here. That is a deliberate difference from the
    network the contract is deployed on: Studio Dev queues an `on="finalized"`
    value transfer and never executes it, which is a property of that network
    and not of this contract. This suite models the INTENDED semantics so the
    money invariants can be proved end to end; `test/seed.mjs` asserts the other
    half on chain - that the call posts a well-formed queued transfer to the
    right address for the right amount. Neither check is sufficient alone."""

    def __init__(self, address):
        self.address = address

    @property
    def balance(self):
        return BALANCES.get(str(self.address), 0)

    def emit_transfer(self, value, **_k):
        if int(value) <= 0:
            raise ValueError("value must be greater than 0 for emit_transfer")
        key = str(self.address)
        TRANSFERS.append((key, int(value)))
        BALANCES[key] = BALANCES.get(key, 0) + int(value)


def _proxy_for(address):
    return _Proxy(address)


def _contract_interface(cls):
    return _proxy_for


def _evm_contract_interface(cls):
    class _Handle:
        def __init__(self, to):
            self.to = to
    return _Handle


MESSAGE = types.SimpleNamespace(sender_address=_Addr("0x" + "a" * 40), value=0,
                                raw={"datetime": "2026-09-18T12:00:00Z"})

# ---------------------------------------------------------------------------
# the web and the model
#
# `_collect` runs TWICE per consensus round offline - once as the leader and
# once as the validator - so every fake here is STICKY by default: one
# configured answer serves every call until replaced. `SEQ` exists for the
# opposite case: making the leader and the validator see different bytes, to
# prove that disagreement settles nothing.
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, status, body):
        self.status_code = status
        self.body = body.encode("utf8") if isinstance(body, str) else body


WEB = {}        # url -> (status, body) | Exception
RENDER = {}     # url -> text | Exception
SEQ = {}        # url -> [answers...] consumed first, then WEB/RENDER
CALLS = []      # (kind, url) in order


def _next_of(url, table):
    queue = SEQ.get(url)
    if queue:
        return queue.pop(0)
    if url not in table:
        return RuntimeError("no fake for " + url)
    return table[url]


def _as_html(text):
    """A fixture's text as the HTML page a GET would return: one <p> per
    line, escaped - so the contract's own stripper is on the tested path."""
    esc = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return "<html><head><script>var noise=1;</script></head><body>" + "".join(
        "<p>" + line + "</p>" for line in esc.split("\n")) + "</body></html>"


def _web_request(url, method="GET", **_k):
    CALLS.append(("request", url))
    if url not in WEB and (url in RENDER or SEQ.get(url)):
        got = _next_of(url, RENDER)
        if isinstance(got, Exception):
            raise got
        return _Resp(200, _as_html(got))
    got = _next_of(url, WEB)
    if isinstance(got, Exception):
        raise got
    status, body = got
    return _Resp(status, body)


def _web_render(url, mode="text", **_k):
    CALLS.append(("render", url))
    got = _next_of(url, RENDER)
    if isinstance(got, Exception):
        raise got
    return got


class _Model:
    def __init__(self):
        self.reset()

    def reset(self):
        self.sticky = None
        self.queue = []
        self.log = []
        self.raise_next = 0
        self.calls = 0

    def serve(self, classification, peril="NONE", exclusion="NONE", strength=5):
        self.sticky = {"classification": classification, "peril": peril,
                       "exclusion": exclusion, "evidence_strength": strength}
        self.queue = []

    def serve_raw(self, payload):
        self.sticky = payload
        self.queue = []

    def script(self, *answers):
        self.queue = list(answers)

    def fail(self, times=1):
        self.raise_next = times

    def _next(self, prompt):
        self.calls += 1
        self.log.append(prompt)
        if self.raise_next > 0:
            self.raise_next -= 1
            raise RuntimeError("the model endpoint refused the connection")
        if self.queue:
            return self.queue.pop(0)
        if self.sticky is None:
            raise AssertionError("model call with no configured answer")
        return self.sticky


MODEL = _Model()


def _exec_prompt(prompt, **kwargs):
    if kwargs.get("response_format") != "json":
        raise AssertionError("CoverClaim must ask for response_format='json'")
    return MODEL._next(prompt)


LAST_CONSENSUS = {}

# Set by a test to make the leader misbehave. Kept OUT of LAST_CONSENSUS
# because that dict is cleared at the top of every round - a forgery stored
# there would be wiped before it could be used, and the test would silently
# assert nothing.
FORGE = {"payload": None, "leader_dies": False}


def _run_nondet(leader_fn, validator_fn):
    """Runs the real consensus shape offline: the leader produces a result, a
    validator is handed it as gl.vm.Return and must agree, and disagreement is
    surfaced the way the chain surfaces it - as a round that returns nothing.

    The validator runs the SAME closure the contract gave it, so a validator
    that re-scores really does re-score here too."""
    LAST_CONSENSUS.clear()
    if FORGE["leader_dies"]:
        # A round that never settled. On chain the transaction goes
        # UNDETERMINED and NO state is applied at all; here the call simply
        # answers nothing, which is what the contract must survive.
        LAST_CONSENSUS["agreed"] = False
        return None
    try:
        result = leader_fn()
    except Exception as e:
        LAST_CONSENSUS["agreed"] = False
        LAST_CONSENSUS["leader_error"] = str(e)
        return None
    LAST_CONSENSUS["leader"] = result
    if FORGE["payload"] is not None:
        result = FORGE["payload"]
    agreed = validator_fn(_Return(result))
    LAST_CONSENSUS["agreed"] = bool(agreed)
    if not agreed:
        return None
    return result


def _install_stub():
    if "genlayer" in sys.modules:
        return
    mod = types.ModuleType("genlayer")
    vm = types.SimpleNamespace(UserError=_UserError, Return=_Return,
                               Result=object, Rollback=_Rollback,
                               run_nondet=_run_nondet,
                               run_nondet_unsafe=_run_nondet)
    web = types.SimpleNamespace(request=_web_request, render=_web_render,
                                get=lambda url, **k: _web_request(url, **k))
    nondet = types.SimpleNamespace(web=web, exec_prompt=_exec_prompt)
    public = types.SimpleNamespace()
    public.view = lambda fn: fn
    write = lambda fn: fn
    write.payable = lambda fn: fn
    public.write = write
    evm = types.SimpleNamespace(contract_interface=_evm_contract_interface)
    storage = types.SimpleNamespace(TreeMap=_TreeMap, DynArray=_DynArray,
                                    allow=lambda cls: cls)
    contract_ns = types.SimpleNamespace(Contract=_Contract,
                                        get_at=lambda a: _proxy_for(a),
                                        interface=_contract_interface)
    chain_ns = types.SimpleNamespace(Account=_Account, id=61997)
    mod.gl = types.SimpleNamespace(vm=vm, nondet=nondet, public=public, evm=evm,
                                   storage=storage, message=MESSAGE,
                                   contract=contract_ns, chain=chain_ns)
    mod.Address = _Addr
    mod.TreeMap = _TreeMap
    mod.DynArray = _DynArray
    for name in ("u8", "u16", "u32", "u64", "u128", "u256", "i8", "i16", "i32",
                 "i64", "bigint"):
        mod.__dict__[name] = int
    sys.modules["genlayer"] = mod
    sys.modules["genlayer.gl"] = mod.gl


def load_pure(path: Path, name: str) -> types.ModuleType:
    """Exec only the pure region - every top-level statement before the first
    class definition. That region never touches storage."""
    tree = ast.parse(path.read_text(encoding="utf8"))
    cut = len(tree.body)
    for i, node in enumerate(tree.body):
        if isinstance(node, ast.ClassDef):
            cut = i
            break
    tree.body = tree.body[:cut]
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module


def load_full(path: Path, name: str) -> types.ModuleType:
    """Exec the WHOLE file so the contract class itself can be driven."""
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_text(encoding="utf8"), str(path), "exec"),
         module.__dict__)
    return module



# ---------------------------------------------------------------------------

def _own_nodes(scope):
    out = []

    def rec(node):
        for sub in ast.iter_child_nodes(node):
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef,
                                ast.Lambda)):
                continue
            out.append(sub)
            rec(sub)
    rec(scope)
    return out


def _child_scopes(scope):
    out = []

    def rec(node):
        for sub in ast.iter_child_nodes(node):
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef,
                                ast.Lambda)):
                out.append(sub)
            else:
                rec(sub)
    rec(scope)
    return out


def _bound_names(scope) -> set:
    out = set()
    args = getattr(scope, "args", None)
    if args is not None:
        for group in (args.posonlyargs, args.args, args.kwonlyargs):
            for a in group:
                out.add(a.arg)
        if args.vararg:
            out.add(args.vararg.arg)
        if args.kwarg:
            out.add(args.kwarg.arg)
    for sub in _own_nodes(scope):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
            out.add(sub.id)
        elif isinstance(sub, ast.ExceptHandler) and sub.name:
            out.add(sub.name)
        elif isinstance(sub, (ast.Global, ast.Nonlocal)):
            out.update(sub.names)
        elif isinstance(sub, (ast.Import, ast.ImportFrom)):
            for al in sub.names:
                out.add((al.asname or al.name).split(".")[0])
        elif isinstance(sub, ast.comprehension):
            for nm in ast.walk(sub.target):
                if isinstance(nm, ast.Name):
                    out.add(nm.id)
    for sub in _child_scopes(scope):
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.add(sub.name)
    for sub in _own_nodes(scope):
        if isinstance(sub, ast.ClassDef):
            out.add(sub.name)
    return out


def undefined_names(path: Path) -> list:
    tree = ast.parse(path.read_text(encoding="utf8"))
    module_names = _bound_names(tree) | {
        "gl", "u8", "u16", "u32", "u64", "u128", "u256", "i8", "i16", "i32",
        "i64", "Address", "TreeMap", "DynArray", "bigint", "Array", "self"}
    builtin_names = set(dir(builtins))
    problems = []

    def visit(scope, enclosing, label):
        scope_names = enclosing | _bound_names(scope)
        for sub in _own_nodes(scope):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                if sub.id not in scope_names and sub.id not in builtin_names:
                    problems.append((label, sub.id, sub.lineno))
        for child in _child_scopes(scope):
            visit(child, scope_names,
                  label + "." + getattr(child, "name", "<lambda>"))

    for child in _child_scopes(tree):
        visit(child, module_names, getattr(child, "name", "<lambda>"))
    for node in _own_nodes(tree):
        if isinstance(node, ast.ClassDef):
            for child in _child_scopes(node):
                visit(child, module_names | _bound_names(node),
                      node.name + "." + getattr(child, "name", "<lambda>"))
    return problems




