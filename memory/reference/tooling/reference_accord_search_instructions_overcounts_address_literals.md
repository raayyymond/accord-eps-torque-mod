# ⚠ NEW TRAP CLASS: `search_instructions` can OVER-count too — address-literal substring collisions

Every scan trap on record in this kit before 2026-07-30 was about **undercounting** (it only scans
already-analysed instructions, misses cave reads, misses the 6-byte extended-displacement encoding).
**It also over-counts**, and it happened twice in one session.

## The two instances
| query | reported | real | the collision |
|---|---|---|---|
| `operand_pattern="6bd0"` | several hits incl. `FUN_0006bcb2`, `FUN_000757a2` | those two are **false** | branch-target literal **`0x00076bd0`** |
| `operand_pattern="6b70"` | **21 hits** | **2** (writer `0x382d2`, reader `0x38006`) | **`jarl 0x0006b700,lp`** — a call to the function AT `0x6b700` |

**19 of 21 hits were noise in the second case.** A reader/writer set built on that would have been
wrong by an order of magnitude, in the *safe-looking* direction (it makes a lane look widely consumed
when it is private).

## The rule
**A `gp-0x****` pattern will match any address literal containing those hex digits — branch targets,
`jarl` operands, embedded pointers.** Before trusting a hit:
1. Confirm it is a **gp-relative operand**, not an address literal.
2. Corroborate the count with a **raw Python byte scan** for the actual instruction encoding
   (both the 4-byte disp16 form and the 6-byte extended-displacement form; remember `hw2 = disp|1`
   for `ld.hu`/`ld.w`).

Both directions of error are now documented: it misses real accesses **and** invents fake ones.
**Never let a reader/writer set or a null rest on `search_instructions` alone** — that instruction was
already in every subagent brief for the undercount; it now covers the overcount too.

## Related, same session
The **off-by-0x1000 tp trap recurred a fifth time** (`tp+0x73a8` computed as `0xC73A8`; it is
`0xC63A8`). `tp = 0xBF000`. Self-caught by the subagent, but only because it re-checked. **Anchor every
tp-relative address against a known value before trusting it.**

Related: [[accord-v850-scan-traps-formatv-and-storezero]], [[accord-lerp-tables-count-word-first]],
[[accord-check-build-lineage-before-proposing-lever]].
