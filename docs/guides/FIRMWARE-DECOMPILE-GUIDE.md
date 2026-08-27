# Firmware Decompile Guide — V850E2 Reverse Engineering in this Kit

> ## 🛑 TOOL POLICY — READ FIRST (2026-07-20)
>
> **GhidraMCP (the `mcp__ghidra__*` tools) is the ONLY sanctioned disassembly and
> decompilation tool on this kit. Do not use radare2, rizin, `r2pipe`, or any other
> CLI disassembler, and do not call `disasm_v850.py` (a CLI-disassembler wrapper,
> now retired).** Standing operator instruction.
>
> **Large parts of this guide predate that policy** and document an r2-first
> workflow with install notes, `r2pipe` snippets, and `disasm_v850.py` recipes.
> Those sections are **retained as historical reference only** — they explain how
> findings in the `docs/HANDOFF-*.md` chain were originally obtained. **Do not
> follow them as instructions.**
>
> For the current workflow use
> [`.claude/skills/firmware-decompile.md`](../.claude/skills/firmware-decompile.md),
> which is Ghidra-only and up to date. The still-valid content here is the
> **architecture facts** (`gp`/`tp` bases, memory map, flash layout), the
> **V850E2 decode hazards**, and the **Ghidra-specific** sections.

Companion to [`.claude/skills/firmware-decompile.md`](../.claude/skills/firmware-decompile.md)
and [`guides/GHIDRA-CHECKLIST.md`](./GHIDRA-CHECKLIST.md). The skill is the
operational primer agents load before a session; this guide is the deeper
reference with full command lists, install notes, and Ghidra-specific
patterns.

Firmware artifacts live outside the repository under `../accord-firmware` by
default. Python tools honor `ACCORD_FIRMWARE_ROOT`; source code remains under
the repository's `analysis-2020accord/` and `flashing-2020accord/` directories.

**Tool order of preference:**

1. **radare2 / rizin** (with the `v850.gnu` plugin) — CLI disassembler, fast, scriptable via r2pipe
2. **`disasm_v850.py`** — the kit-shipped scripted path (a rizin wrapper — capstone has no V850 support in this environment)
3. **Ghidra / GhidraMCP** — only when you need full decompilation

---

## The firmware: what you're decompiling

**Vehicle:** 2020 Honda Accord Touring. **EPS:** `39990-TVA-A160`. **MCU:**
Renesas µPD70F3508, V850E2/Px4 core, **little-endian**, 1 MB code flash.

Unlike the kit's earlier Civic/SH-2A material, there is **no flash-base
offset to account for** — `../accord-firmware/analysis-2020accord/ghidra_project/code.bin` and the `../accord-firmware/analysis-2020accord/_vNN_plain_image.bin`
snapshots load flat starting at file offset `0x0`.

| File | Description |
|---|---|
| `../accord-firmware/analysis-2020accord/ghidra_project/code.bin` | The STOCK program used across the whole V9–V38 build lineage. Import target for Ghidra/GhidraMCP. |
| `../accord-firmware/analysis-2020accord/_vNN_plain_image.bin` | Decrypted snapshot of a specific shipped build (V22 through V39 plus telemetry/variant images present). Cal-only builds are byte-identical to stock in the code regions — only the `0xC4000`–`0xC6FFF`-ish calibration window differs. |
| `../accord-firmware/analysis-2020accord/stock_fw_dump/` | Raw stock dump material. |
| `../accord-firmware/flashing-2020accord/rwd/*.rwd` | The encrypted, headered container format actually flashed to the car — decrypt via `flashing-2020accord/encode_eps.py` (cipher `((c^0xBF)^0x10)-0x9E`), not any Civic-family tool. |

Cal-only builds (the large majority of the V9→V38 lineage) don't touch code
at all — only data tables/thresholds in the calibration region change. A
handful of builds add a code cave (e.g. V22's float-monitor redirect) or
patch a branch condition directly; each build's script docstring states
exactly what changed and why.

## Architecture quick reference

| Property | Value |
|---|---|
| CPU | Renesas µPD70F3508, V850E2/Px4 core |
| Endianness | **Little-endian** (LE) |
| Instruction width | Mixed 16/32/48-bit (V850E2 variable-length encoding) |
| Code flash | `0x00000000–0x000FFFFF` (1 MB) |
| Data flash | `0x02000000–0x02008000` (32 KB, calibration — doubled-with-tag-word storage) |
| RAM | `0xFEDEC000–0xFEDFFFFF` (80 KB on-chip) |
| `gp` (global pointer) | `0xFEDF8000` — `gp-0xNNNN` operand resolves to `0xFEDF8000 - 0xNNNN` |
| `tp` (cal pointer, **app** context) | `0xBF000` — resolve at the app's own set-site, NOT the bootloader's (bootloader sets `tp=0xF8000`, but the app re-sets it early in its own init). A `tp+0xNNNN` operand resolves to `0xBF000 + 0xNNNN`. |
| Address-build idiom | `movhi imm,r0,rX` + `movea lo,rX,rY` builds a 32-bit absolute address across 2 instructions; neither rizin nor Ghidra auto-resolves this into an xref |
| Ghidra language ID | `V850:LE:32:default` |

---

## Known V850E2 decode bugs — read before trusting any tool output

Full write-up: `memory/reference/tooling/reference_rizin_ghidra_v850_quirks.md`. Summary:

1. **radare2's DEFAULT `v850` plugin mis-decodes V850E2.** It renders
   `ld.hu`/`ld.w` disp16 loads as bogus `setf`/`xori` clusters — the branch
   skeleton still looks plausible, which is the trap. **Use `v850.gnu`**
   (`r2 -a v850.gnu` or `e asm.arch=v850.gnu`) instead. Signature to watch
   for: a function body decoding as a run of `setf`/`xori` where you'd
   expect `ld.hu`/`ld.w` cal reads.
2. **rizin's `sld.hu`/`sld.bu`/`sld.w` short-load displacement is printed at
   HALF the true value** — the ×2 halfword scaling isn't applied. ISA-correct
   decoding: for `sld.hu rrrrr0000111dddd`, `disp = bits[3:0] × 2`. If you
   hand-read a short-load line, verify the raw bytes rather than trusting
   the printed disp.
3. **`divq reg2==reg3` semantics are wrong in both rizin and Ghidra's base
   `V850:LE:32:default` SLEIGH.** Per the V850E2M architecture manual, when
   the two operands are the same register, the result is the **remainder**,
   not the quotient — both tools compute/imply quotient regardless. (Ghidra
   issue #8995 / PR #1430 has an unmerged SLEIGH fix.)
4. Both tools ship V850-base-ISA opcode tables only. Some V850E2-specific
   6-byte encodings (`cmpib`, unsigned-disp23 `st.h`) decode as `invalid` or
   misreport. Raw-byte-verify against the V850E2M architecture manual
   (Renesas R01US0001EJ0100) when in doubt.

**Operational rule:** when V850 analysis produces a "this looks like a
different algorithm than expected" finding, default-suspect the tooling
before the firmware. Both bugs 2 and 3 above compounded once to make a
known 3-constant SecurityAccess formula look like a novel 2-constant divide
variant — raw-byte verification resolved it.

---

## Path A: radare2 / rizin (preferred)

### Install

**macOS:**
```bash
brew install radare2
```

**Linux:**
```bash
git clone https://github.com/radareorg/radare2
cd radare2 && sys/install.sh
```

**Windows:** Installer at <https://radare.org/get/>, or use WSL.

**Python bindings (for scripting):** `pip install r2pipe`

### Open the firmware image

```bash
r2 -a v850.gnu -e cfg.bigendian=false \
   ../accord-firmware/analysis-2020accord/ghidra_project/code.bin
```

Flag breakdown:
- `-a v850.gnu` — the binutils-2.35-based V850 plugin. **Not** the default
  `v850` (LGPL) plugin — see decode bug 1 above. In some radare2 builds this
  is selected via `e asm.arch=v850.gnu` after opening instead of `-a`.
- `-e cfg.bigendian=false` — little-endian. (The Civic's SH-2A was
  big-endian; V850E2 is not — don't carry that assumption over.)
- No base-address flag needed (`code.bin` loads at `0x0` already).

If a function body looks like nonsense `setf`/`xori` soup where you expect
cal reads, you're on the wrong plugin — switch and re-check.

### Essential r2 commands

```
# Analysis
aaa                   # analyze all (run on first open)
aaaa                  # extra-aggressive analysis (slower, finds more)
afl                   # list all functions r2 identified
afi @ fcn.<name>      # info about a specific function

# Navigation
s 0x2214a             # seek to address (e.g. w_steer_control_task)
s-                     # seek to previous position
V / VV                 # visual mode / visual graph mode

# Display
pd 20 @ 0x29344        # print disassembly: 20 instructions from addr
pdf @ fcn.00029344     # print disassembly of full function
pxw 64 @ 0xC64B8       # hex dump 64 bytes as words at addr

# Cross-references (the killer feature)
axt @ 0xC64B8          # who references this address? (caller direction)
axf @ 0x29344          # what does this address reference? (callee direction)

# Search
/x 7F 00               # search byte pattern (bytes as printed — remember LE)
/v1 0xE4               # search for 8-bit value (e.g. CAN ID)
/v4 0xFEDF6807         # search for a 32-bit resolved gp-relative address

# Comments / labels
CC steer status debounce gate @ 0x29344
afn m_steer_torque_arbitration @ 0x2214a    # rename function

q                      # quit
```

### r2pipe (Python scripting)

```python
import r2pipe

r2 = r2pipe.open(
    "../accord-firmware/analysis-2020accord/ghidra_project/code.bin",
    flags=["-a", "v850.gnu", "-e", "cfg.bigendian=false"]
)
r2.cmd("aaa")

xrefs = r2.cmdj("axtj @ 0xC64B8")
for x in xrefs:
    print(f"{x['from']:#x} ({x['type']}) -> 0xC64B8")

disasm = r2.cmd("pd 20 @ 0x29344")
print(disasm)

r2.quit()
```

### radiff2 — byte-level diff between build versions

```bash
radiff2 -A -C ../accord-firmware/analysis-2020accord/_v36_plain_image.bin \
              ../accord-firmware/analysis-2020accord/_v37_plain_image.bin
```

For a build known to be cal-only (most of the V9–V38 lineage), this should
show a single small diff region inside the `0xC4000`–`0xC6FFF`-ish
calibration window plus the trailing block CRC — anything outside that is
worth investigating before trusting the build's own "cal-only" claim.

---

## Path B: `disasm_v850.py` (kit-shipped, scripted iteration)

Capstone has **no V850 support** in this environment, so unlike the old
Civic `disasm_sh2a.py` (a real capstone wrapper), `disasm_v850.py` at
`analysis-2020accord/reference/fw_inventory/decompilation/disasm_v850.py` instead
wraps the `rizin` CLI and adds V850-specific post-processing — most
importantly resolving the `movhi`/`movea` immediate-pair idiom into a
computed 32-bit address, which neither rizin nor Ghidra does automatically.

It inherits rizin's own decode bugs (it does not work around the
`sld.*`/`divq` issues — only the address-pair xref gap).

### API

```python
import sys
sys.path.insert(0, "analysis-2020accord/reference/fw_inventory/decompilation")
from disasm_v850 import (
    rz_disasm,            # disasm n instructions at a file offset, JSON
    rz_disasm_range,       # disasm bytes in [start, end), JSON list
    disasm_function,       # auto-extent disasm of a function
    resolve_imm_pairs,     # annotate movhi/movea pairs with resolved_addr
    classify_addr,         # "flash" / "ram" / "data-flash" / "sfr" / "other"
    format_lines,          # pretty-printer
    KNOWN_OFFSETS,         # landmark addresses (reset vector, strings, CRC engine...)
)

insns = rz_disasm_range(0x8000, 0x8400)
resolve_imm_pairs(insns)
for ins in insns:
    if "resolved_addr" in ins:
        addr = ins["resolved_addr"]
        print(f"{ins['offset']:#x}: {ins['opcode']} -> {addr:#x} ({classify_addr(addr)})")

print(format_lines(disasm_function(0x2214a)))   # full function disasm, pretty-printed
```

`KNOWN_OFFSETS` includes landmarks like the reset vector table, the
part-number string (`0x009011` = `"39990-TVA-A110/A160"`), the build
timestamp string, the CRC engine (DCRA driver), and the calibration region
start — worth reading before you start a new trace.

When Path B beats Path A: "find every X across the whole binary" queries,
programmatic diffing between build versions, anything that fits in a few
function calls instead of an interactive session.

### The rizin-shell-out caveat

Because `disasm_v850.py` shells out to `rizin` per call rather than decoding
bytes itself, it's slower than a native capstone wrapper would be for
whole-binary sweeps, and it inherits every rizin decode bug listed above.
If a resolved address or opcode looks wrong, cross-check the raw bytes by
hand or switch to Path A with `v850.gnu`.

---

## Path C: Ghidra / GhidraMCP (last resort, full decompilation)

Use when:
- You need C-like decompiled output that r2's `pdc` doesn't produce cleanly for V850E2
- One-shot deep dive on a single function
- You want GhidraMCP's structured tool surface (xrefs, call graphs, decompilation) rather than raw r2 text

Ghidra is not installed automatically in this kit — install per
`guides/GHIDRA-CHECKLIST.md` (JDK 21 + a Ghidra release zip) if you need local
Ghidra rather than the MCP bridge.

### GhidraMCP (preferred over hand-rolled headless scripts)

This kit has GhidraMCP tool access. Prefer the structured tools over Jython
postScripts for interactive tracing:
- `decompile_function` / `disassemble_function` — get C-like or asm output for a function
- `get_xrefs_to` / `get_xrefs_from` — cross-reference queries
- `get_function_callers` / `get_function_callees` — call-graph liveness checks (important: some functions that *look* like the producer of a behavior turn out to have zero callers — see the recurring-recipes section below)
- `search_functions` / `list_functions` — enumeration when you don't have an address yet
- `get_current_program_info` / `list_open_programs` — **check this first** if more than one program may be open; confirm you're querying `code.bin` (stock) and not an experimental `../accord-firmware/analysis-2020accord/_vNN_plain_image.bin` before trusting a "stock" claim

### Headless mode (if you need a from-scratch import)

```bash
export GHIDRA_INSTALL=/opt/ghidra_11.x_PUBLIC      # Linux/Mac
$env:GHIDRA_INSTALL = "C:\ghidra_11.x_PUBLIC"       # Windows PowerShell

mkdir -p /tmp/ghidra_projects
$GHIDRA_INSTALL/support/analyzeHeadless \
  /tmp/ghidra_projects accord2020_ghidra \
  -import ../accord-firmware/analysis-2020accord/ghidra_project/code.bin \
  -processor V850:LE:32:default \
  -loader BinaryLoader \
  -loader-baseAddr 0x0 \
  -overwrite
```

```powershell
# Windows variant
& "$env:GHIDRA_INSTALL\support\analyzeHeadless.bat" `
  "$env:TEMP\ghidra_projects" accord2020_ghidra `
  -import "..\accord-firmware\analysis-2020accord\ghidra_project\code.bin" `
  -processor V850:LE:32:default `
  -loader BinaryLoader `
  -loader-baseAddr 0x0 `
  -overwrite
```

### Peripheral registers — use the SVD, not bare addresses

`analysis-2020accord/reference/svd_for_ghidra/UPD70F3508_V850E2Px4.svd` is a
datasheet-authored SVD for this exact chip (µPD70F3508, V850E2/Px4).
Prefer citing register/field NAMES from it over bare peripheral addresses —
e.g. `0xFF481000` = `FCN0M0DAT0B`; TX/RX direction = `FCN0M{n}STRB.SSOW`
bit 7. This settled at least one real dispute (an `FCN0` sub-block vs
"channel B" question in a CAN-TX tracing session) that bare-address
reasoning got wrong.

---

## When to use which path

| Task | Path | Why |
|---|---|---|
| Find references to a cal/gp address | A (`axt`) or B (`resolve_imm_pairs`) | A is interactive; B is scriptable |
| Decompile a function to C | C (GhidraMCP `decompile_function`) | Best V850E2 decompiler output |
| Diff disassembly across build versions | A (`radiff2`) or B (programmatic) | A for one-off, B for systematic |
| Confirm a function is live (not dead code) | C (`get_function_callers`) or A (`axt` on entry) | Call-graph liveness, not just presence |
| Trace a value through gp/tp state | A (graph mode) or C (decompiler) | A for quick scan, C for clean output |
| Verify a `divq`/`sld.*` read that looks wrong | Raw byte decode by hand | Both A and C have known bugs on these — don't trust either blindly |

Rule of thumb: A for "find," B for "script," C for "decompile clean" — and
raw bytes when either tool's V850E2 support is suspect.

---

## Cross-verification discipline

Per `memory/feedback/measurement/feedback_rigorous_validation.md`: "full byte diff > spot diff;
ghidra before declaring victory." Whenever a finding is about to inform a
build decision (a cal value, a branch condition, a function's liveness),
run it through **two independent readings** — e.g. r2 with `v850.gnu` AND
GhidraMCP's decompiler, or `disasm_v850.py`'s resolved address AND a raw
hex dump — and require agreement before trusting either. If they disagree,
investigate the divergence; don't average or guess which is right.

A concrete example from this kit's own history: `FUN_0002a30e` and
`FUN_0002a93a` both initially looked like the `STEER_STATUS` debounce
producer from static reading alone. A callers/xrefs check (0 callers on
both) revealed they're dead code — the live logic is inlined directly in
`m_steer_torque_arbitration`. Presence of a plausible-looking function is
not evidence it's the live path; check the call graph.

---

## Existing analysis artifacts to read before starting your own work

Before opening a disassembler to investigate a question, check whether the
answer already exists in the kit:

- `analysis-2020accord/notes/TORQUE_PATH_AND_TABLE.md` / `notes/TORQUE_PATH_GUIDE.md` — the torque path from CAN input to motor output
- `analysis-2020accord/notes/EME_OVERRIDE_SM_NONVERIFIED.md` — non-verified override state-machine hypotheses (read the verified companions in `.claude/agent-memory/firmware-codepath-tracer/` before trusting these)
- `analysis-2020accord/notes/FUN_00043e44_FLOAT_MONITOR.md` — the float consistency-monitor deep dive
- `analysis-2020accord/notes/SESSION-2026-05-30-EME-RESOLUTION.md` — a resolved EME investigation session
- `analysis-2020accord/notes/HOW_TO_BUILD_ACCORD_TVA_RWD.md` — the build/flash recipe, including the decrypt/cipher/CRC pipeline
- `docs/guides/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md` — the fullest mapped CAN→motor gating chain
- `.claude/agent-memory/firmware-codepath-tracer/MEMORY.md` — the index of every `reference_accord_*` finding from prior tracing sessions on this exact binary

The constellation in `memory/MEMORY_CONSTELLATION.md` is the relational
index of what's known about the firmware structure. Start there.

---

## Recurring recipes

### Recipe 1: Find what reads from/writes to a cal or gp address

Path A:
```
[0x00000000]> axt @ 0xC64B8
```

Path B:
```python
from disasm_v850 import rz_disasm_range, resolve_imm_pairs
insns = rz_disasm_range(0x29a00, 0x29b00)
resolve_imm_pairs(insns)
for ins in insns:
    if ins.get("resolved_addr") == 0xC64B8:
        print(ins)
```

Read 15-20 instructions of context around each hit to identify the function
and access pattern (compare, load-then-branch, accumulate, etc.).

### Recipe 2: Identify the CAN-0xE4 steering handler

The steering torque command arrives on CAN `0xE4` — see
`memory/reference/firmware/reference_accord_lkas_torque_path.md` for the disasm-verified path.
```
[0x00000000]> /v1 0xE4
```
Inspect each hit; the handler will be a function entry near one of the
loads. CAN handlers are typically large functions with many `jarl` calls to
sub-handlers.

### Recipe 3: Trace a value from CAN input to motor output

1. Find the CAN receive handler (recipe 2).
2. Walk forward through the demand aggregator → `m_steer_torque_arbitration`
   (called from `w_steer_control_task@0x2214a`) → shaper/governor chain.
   `docs/guides/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md` is the fullest
   already-mapped version of this — check it before re-deriving from
   scratch.
3. At each hop, note the clamp/LERP table/gate SM the value passes through
   and its `gp-`/`tp-` relative address.

GhidraMCP's decompiler does much of this automatically for a single
function — feed it the entry function and read the C-like output.

### Recipe 4: Compare a build version against stock (or against a prior version)

```bash
# Path A — byte diff
radiff2 -A -C ../accord-firmware/analysis-2020accord/ghidra_project/code.bin \
              ../accord-firmware/analysis-2020accord/_v37_plain_image.bin
```

Every `build_vNN_tva.py` script states its exact intended cal delta from
the prior version in its own docstring header (e.g. "V37-vs-V36 = exactly
`0xC64B8`+CRC") and performs its own full-byte-diff + 49/49-block-CRC
self-check before writing output — read the script itself
(`analysis-2020accord/builds/v18_v49/build_v38_tva.py` is the latest) for the verification
pattern rather than re-deriving it.

---

## Output expectations

Per `memory/feedback/measurement/feedback_rigorous_validation.md`: full walk, not spot check.
Ghidra/r2 output worth producing:

- The specific address/function analyzed, and which binary it was analyzed
  in (`code.bin` stock, or a specific `../accord-firmware/analysis-2020accord/_vNN_plain_image.bin` — builds can
  differ)
- The disassembly or decompiled excerpt that proves the claim (paste it,
  don't summarize)
- Where this fits in the existing knowledge graph (link to the relevant
  memory file in `memory/` or `.claude/agent-memory/firmware-codepath-tracer/`)
- If you discovered a durable new fact: a proposed memory file with the
  `reference_*` prefix

If a hypothesis didn't pan out, say so clearly. "I checked X and it does
not behave as predicted — here's the actual behavior" is high-value
output, not failure.
