# PROBE — which sources a validator can actually read

Everything here was measured on GenLayer Studio Dev (chain 61997) on
2026-09-26, BEFORE the judging code was written, by throwaway contracts:

- `contracts/_probe.py` — `http_probe` (plain GET, optionally parsing the
  DeFi Llama incident list or a TVL history), `render_probe` and
  `get_text_probe` (a page as text). The `strict` variants make **every
  validator fetch the page again and vote on the hash of the normalised
  text**, so an ACCEPTED strict probe is a measurement that independent nodes
  read identical bytes — not just that one node could reach the URL.
- `contracts/_probe_pipe.py` — CoverClaim's own pure judging code run one
  stage at a time on chain (see §4, the finding that changed the design).

Probe lanes: `0x457bE472…931e47`, `0x2fC4A549…82bD1e`, `0x4f64442A…89CA4A`,
`0x20F728ce…A7D7C`, `0x3A9B25c5…94E843`. Raw results, one JSON per job with the
transaction hash: `docs/probe/*.json`. Driver: `test/probe.mjs`,
`test/pipeprobe.mjs`, `test/llmprobe.mjs`.

---

## 1. Results

| source | how | strict | result | time | size | notes |
|---|---|---|---|---:|---:|---|
| `api.llama.fi/hacks` | GET + parse | – | **USABLE** | 10–73 s | 350,622 B | 1,288 rows; rows found by `defillamaId` for Euler (1), Curve (2), Multichain (4), Tornado Cash (1) |
| `api.llama.fi/protocol/euler-v1` | GET + parse | – | **USABLE** | 18 s | 9.4 MB | id `1183`, 1,743 daily points, drop around 2023-03-13 = **9,585 bps** |
| `api.llama.fi/protocol/multichain` | GET + parse | – | **USABLE** | 32 s | 35.3 MB | id `591`, drop around 2023-07-07 = 8,979 bps |
| `api.llama.fi/protocol/curve-dex` | GET + parse | – | **USABLE** | 82 s | **69.0 MB** | id `3`, drop around 2022-08-09 = 148 bps. The largest document parsed inside the execution budget |
| `api.llama.fi/protocol/tornado-cash` | GET + parse | – | **USABLE** | 11 s | 2.9 MB | id `148`, drop around 2023-05-20 = 70 bps |
| `rekt.news/euler-rekt` | render | ✓ | **USABLE** | 26 s | 5,309 ch | hash `802c3d0f…` — **identical again hours later** (`rekt_euler_render_2`) |
| `rekt.news/euler-rekt` | GET + strip | ✓ | **USABLE** | 10 s | 40,558 B | strict-agreed |
| `rekt.news/curve-finance-rekt` | render / GET | ✓ | **USABLE** | 27 / 13 s | | strict-agreed both ways |
| `rekt.news/multichain-r3kt` | render / GET | ✓ | **USABLE** | 29 / 14 s | | strict-agreed both ways |
| `rekt.news/tornado-gov-rekt` | render / GET | ✓ | **USABLE** | 34 / 17 s | | strict-agreed both ways |
| official: `euler.finance/blog/war-peace-…` | render / GET | ✓ | **USABLE** | 38 / 13 s | 294,576 B | Euler's own post-mortem |
| official: `blog.kyberswap.com/post-mortem-…` | render | ✓ | **USABLE** | 46 s | 25,880 ch | |
| official: `euler.finance/` (homepage) | render / GET | ✓ | USABLE (names Euler, no risk words) | 41 / 12 s | | used as the INCONCLUSIVE seed |
| `web.archive.org/web/2023…/rekt.news/euler-rekt/` | render / GET | ✓ | **USABLE** | 53 / 10 s | 48,200 B | the fallback works |
| `web.archive.org/web/2023/…/curve-finance-rekt` | render | ✓ | **USABLE** | 58 s | | |
| `defillama.com/hacks` (web UI) | render | – | **NOT USABLE** | 26 s | 0 | `WEBPAGE_LOAD_FAILED` — the UI is a client-side app behind bot protection |
| `medium.com/balancer-protocol/…` | render | – | **NOT USABLE** | 33 s | 0 | `WEBPAGE_LOAD_FAILED` |
| `forum.balancer.fi/t/…/5153` | render | ✓ | reachable, **wrong page** | 39 s | | the guessed post-mortem URL resolved to an unrelated BIP thread — not used |
| model: `exec_prompt(…, response_format="json")` | – | – | **USABLE** | 11 s | | `test/llmprobe.mjs` |

## 2. The allowlist, designed from what worked

- **Base domains on every pool: `rekt.news`, `web.archive.org`.** Both were
  read identically by independent validators. An archive URL is accepted only
  if the page it archives is itself on the pool's allowlist — otherwise the
  archive would launder any blog on the internet.
- **The protocol's official domain(s)**, set by the underwriter at pool
  creation (Euler's post-mortem and KyberSwap's were both readable).
- **`defillama.com` is NOT on the allowlist**: its web UI does not load for a
  validator. DeFi Llama's DATA reaches a judgement through `api.llama.fi`,
  which the contract reads itself for every claim — the incident list for the
  incident date and classification, the protocol document for severity.
  Claimants cannot submit `api.llama.fi` URLs; the contract chooses them.
- `medium.com` is not usable and not allowlisted by default.

## 3. What the numbers fixed in the design

- **The incident date comes from DeFi Llama, not from the evidence text or the
  model.** `hacks` gives one row per incident with a `date` at day precision
  and a `defillamaId`; a protocol can have several (Multichain has four, Curve
  two), so `_pick_incident` chooses deterministically.
- **Severity is arithmetic on DeFi Llama's TVL history.** Documents up to
  69 MB parse inside the budget. Every figure is converted to an int inside
  the nondet block: a float in a nondet return is not calldata encodable.
- **The TVL doc's `id` must equal the pool's `defillamaId`**, or the claim is
  INCONCLUSIVE — a pool whose slug and id name different protocols cannot pay.
- **Two renders of a rekt.news article hours apart hashed identically**, so an
  exact content hash on the compared axis is realistic, provided navigation
  noise is dropped (the digest keeps only sentences that name the protocol or
  a risk, of at least five words).

## 4. The render stall — the finding that changed the design

The first end-to-end judgement on a smoke instance
(`0x3D157b65…EE40144`, tx `0x99ab7098…242c`) sat in
`PROPOSING.LEADER.GENVM_EXECUTION_START` for more than **25 minutes** and never
produced a leader result. Every component on its own was fast: the model call
11 s, the incident list 11 s, the 9.4 MB TVL document 18 s, the article render
26 s.

`contracts/_probe_pipe.py` ran CoverClaim's own code one stage at a time
(`docs/probe/pipe-run.log`):

| stage | what | result |
|---|---|---|
| 1 | incident list | ACCEPTED, 9 s |
| 2 | + 9.4 MB TVL document | ACCEPTED, 19 s |
| 3 | + `web.render` of the article **after** the two large GETs | **never settled (1,515 s)** |

Rendering *after* large HTTP bodies in the same execution stalls; rendering on
its own does not. So evidence pages are fetched with a plain GET and stripped
to text by the contract itself (`_strip_html`). Re-run with that change
(`docs/probe/pipe-run-get.log`, contract `0x2E78Bc6E…b191b`):

| stage | result |
|---|---|
| 3 — GET + strip after both API fetches | ACCEPTED, 12 s |
| 6 — + bracket + model choice | ACCEPTED, 18 s |
| 7 — the whole `_collect` | ACCEPTED, 31 s |

Every evidence URL the seed uses was then re-probed as a strict GET
(`docs/probe/run3.log`): all ACCEPTED with validator-agreed hashes.

**Cost of the change, stated honestly:** a page that only has content after
JavaScript runs reads as empty. That can never produce a payout — an empty
page names no protocol and no risk, so the claim is INCONCLUSIVE and can be
refiled with another source.

## 5. Other measurements

- Views can read the block clock: `get_config().now` returned the current block
  time from a `gen_call`, so `get_active_cover().in_force` (and therefore
  `CoverRegistry.is_covered`) is time-checked; when it is not readable,
  `in_force` is false, never assumed.
- Lanes sharing one signer race each other's nonces
  (`NonceTooLow(expected=6,actual=5)`); the probe driver now uses one wallet
  per lane.
- Studio intermittently answers `Server busy: all 8 execution slots occupied`
  and rate-limits reads at 30/min; every script retries those.
