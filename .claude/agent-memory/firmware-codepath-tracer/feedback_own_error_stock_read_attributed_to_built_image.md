---
name: feedback_own_error_stock_read_attributed_to_built_image
description: Three own errors, kept together — (1) 2026-08-09, read a cal byte from stock code.bin and reported it as a built-image value; (2) 2026-08-10, the off-by-0x1000 tp trap on tp+0x7158, which would have produced a false hazard claim; (3) 2026-08-10, RELAYED a prior session's census to a teammate that was wrong twice. All three are "the read/record succeeded so I trusted it" failures.
metadata:
  type: feedback
---

I claimed `0x3AA96` = `C5` (Lever B's gate byte) "on V85/V86/V86B" based on a Ghidra `read_memory`/decompile read of `code.bin` — the ONLY program open in Ghidra that session. I never opened or byte-checked any built plain image. Team-lead independently read the actual built images and found `0x3AA96` = `FB` (armed) on V84/V85/V86/V86B, `C5` only on stock and V81. My conclusion about a specific supporting fact was wrong; the broader structural argument it was embedded in (the shape argument — flat gain vs. differentiator, neither fits a band-localized lift) survived because it didn't actually depend on that one fact.

**Why**: I was mid-decompile of `FUN_0003aa2c` on `code.bin` (the address sits inside code I was already reading), and the temptation to just read the SAME open program for "what does the built image have here" is exactly how this slips in — the read succeeds, returns a plausible-looking value, and nothing in the tool call itself signals "this is the wrong program."

**How to apply**: 🛑 **Before reporting any build-specific byte value (V-anything, not stock), verify which program is actually open** (`list_open_programs` / `get_current_program_info`) and if it's stock-only, the value is a STOCK claim, not a claim about any build — full stop, regardless of how confident the surrounding analysis feels. Built-image byte values are a Python job (read the actual `.bin`/`_plain_image.bin` file for that build number from `../accord-firmwares`), not a Ghidra job, unless that specific build's image has been explicitly `open_program`'d in Ghidra this session. This is the same class of trap as [[feedback-stale-ghidra-import-defeats-hash-check]] (a stale IMPORT of the right file) but is actually worse — a live read of the WRONG file entirely, with no version-mismatch signal at all. Cross-check every build-specific claim against which program was open when the read happened, not just against whether the read itself succeeded.

---

## Own error #2 — the off-by-0x1000 `tp` trap, 2026-08-10 (`DampAxis`), caught before reporting

Reading FactorF's scalar fallback `tp+0x7158` in `FUN_00034350`, I wrote **`0xC7158`** and got **45496**.
That number would have supported a *false hazard claim*: "the damper's fallback ceiling (45496) far
exceeds the mixer's ±2048 zero-reject window ⇒ the damper lane can drop out." The correct address is
`0xBF000 + 0x7158 =` **`0xC6158`** = **512**, which yields the **opposite** conclusion — the damper can
*never* be zero-rejected. **A wrong hazard is as costly as a missed one: it would have argued against a
lever that is actually safe.**

**Why it slipped in despite knowing the rule:** I had already converted seven `tp` offsets correctly in
the same session by computing them (`0x7498→0xC6498`, `0x743c→0xC643C`, `0x50dc→0xC40DC`, …). The eighth
I did **by eye**, mid-flow, on a one-off byte check that felt incidental. **The trap does not fire when
you are being careful about addresses; it fires on the read you think is minor.** This is the recorded
SIXTH recurrence in this kit.

**How to apply:** 🛑 **Compute every `tp+off` in code — `hex(0xBF000+off)` — including the incidental
one-off reads.** Never type a `tp` absolute from memory or by eye. Two cheap tells that catch it:
**(a)** anchor against a known-value neighbour before trusting a new region; **(b)** if a cal reads as an
implausible magnitude for its role (a *ceiling* of 45496 on an `int16` lane is not plausible), suspect the
ADDRESS before believing the value. Both would have caught this one instantly.

---

## Own error #3 — RELAYING a prior session's census to a teammate, 2026-08-10 (`DampAxis`)

`ArcAudit` asked what I had on `gp-0x6752`. I relayed §3 of
[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]] — "boot-time constant, always
+1, 3 stores all inside `FUN_000490ac`, 52 disp16 hits" — **explicitly flagged as "a prior session, not a
fresh trace; please re-verify before making it load-bearing."** They did re-verify, and it was **wrong
twice**: five stores across three functions (two invisible to a disp16-only scan; two more misattributed
to an adjacent function), and −1 is a first-class outcome, not an exception.

**Why the caveat was not enough.** Flagging a relay as unverified transfers the *risk* but not the
*work* — and the receiving agent has less context to know where the soft spots are. Worse, I did not just
relay it: I **built a fresh inference on top of it** ("polarity zero and gate failure are the same
branch") which was independently wrong, and the confident framing of the relayed facts made that
inference look better-supported than it was.

**How to apply:**
- 🛑 **A census claim (N writers / N readers / "only in function F" / "never touched") is the single
  least reliable class of fact in this kit's agent memory**, because it is exactly what the documented
  scan traps corrupt — disp16-only scans miss the 6-byte extended-displacement form, and adjacent
  functions get conflated by address proximity. **Before relaying ANY census, re-run it.**
  `search_instructions` with an explicit `mnemonic` filter takes one call and returns the owning
  `function` field per hit — use that field, never address proximity.
- **Never build a new inference on a relayed-but-unverified fact in the same message.** Relay it, or
  verify it and reason from it — not both.
- ✅ **What went right, and should be repeated:** flagging the relay as unverified is what caused
  `ArcAudit` to re-check instead of inherit, and re-tracing their correction myself (rather than just
  accepting it) is what surfaced the *second* error they had missed. **The correction loop worked; it
  just should have run one step earlier, on my side.** [[feedback_check_own_memory_before_retracing_and_variable_reuse_trap]]
