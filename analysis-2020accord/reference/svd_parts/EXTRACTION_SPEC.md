# SVD Peripheral Extraction Spec (V850E2/Px4 — UPD70F3508)

You are extracting register definitions for **one section** of the V850E2/Px4 hardware
manual and emitting a **CMSIS-SVD fragment** (one or more `<peripheral>` elements) to a file.
The orchestrator will merge all fragments into a single `<device>` SVD for Ghidra.

## Inputs available to you
- `UPD70F3508GJA2-GBG-AX-1.pdf` — the manual (in the parent dir `analysis-2020accord/`).
- `_pages.json` — a JSON array of the plain-text of every PDF page (0-indexed: PDF page N is `pages[N-1]`).
  Prefer this for speed. Use Python + PyMuPDF (`import fitz`) against the PDF only if you need
  layout/table reconstruction the flat text lost.
- Your assigned **PDF page range** and **section name** are in your task prompt.

Read pages with Python, writing output to a UTF-8 file then reading it — the Windows console
cannot print the manual's full-width space (U+3000) characters and will crash on direct print.

## What to extract
Every memory-mapped register in your section. Sources, in priority order:
1. **"Overview of … Registers" / "List of … Registers"** tables — give Register Name, Symbol, Address.
2. **Rich overview tables** (e.g. CAN Table 20-9) with columns Address Offset / Name / Symbol / R/W /
   Access(bits) / After Reset — these give size + reset inline; use them.
3. **"… in Detail" / per-register subsections** — header line `(N)` then `SYMBOL - Long Name`, followed by
   `Access` (→ size), `Address` (→ absolute addr), `Initial value` (→ reset), a bit-layout, and a
   `Bit Position / Bit Name / Function` table (→ fields).
4. **Address+Bits tables** (e.g. INTC Table 4-3): Register / Address / per-bit names.

## Address normalization (CRITICAL)
- Manual addresses look like `FF42 0020H`, `FFFF6000H`, `FFFF 73D4H` → strip spaces and trailing `H`,
  prepend `0x`: `0xFF420020`, `0xFFFF6000`, `0xFFFF73D4`.
- **Symbolic bases**: some sections give addresses as `<TAUAn_base0> + 270H` or offsets to `<FCNn_base>`.
  Find the section's **"Register Base Addresses"** table (resolve `<…_base…>` to concrete hex) and
  compute the absolute address. If a section defines multiple instances (TAUA0/TAUA1, FCN0/FCN1,
  CSIH0..3, TSG20/TSG21), emit **one `<peripheral>` per instance** with its own resolved base.
- If you genuinely cannot resolve a base, record those registers' offsets relative to a base you
  set as the peripheral `baseAddress`, and note the unresolved base in a `<!-- comment -->`.

## Output: SVD fragment file
Write to the path given in your prompt, e.g. `reference/svd_parts/section08_reset_controller.svd`.
Content = one or more `<peripheral>` elements, **no `<device>` wrapper, no XML declaration**.

Rules:
- One `<peripheral>` per hardware instance. `<name>` must be a valid identifier (A-Z 0-9 _),
  unique within your file; prefix register-poor sections sensibly (e.g. `RESET`, `INTC`, `DMA`).
- `<baseAddress>` = the lowest register absolute address for that peripheral (hex `0x…`).
- Each `<register>`:
  - `<name>` symbol (identifier chars only; for arrays use the concrete instance name, e.g. `DSA0L`).
  - `<description>` the long register name (escape `&`,`<`,`>`).
  - `<addressOffset>` = absoluteAddr − baseAddress (hex `0x…`, must be ≥ 0).
  - `<size>` in **bits**: map "1-/8-/16-bit units" → pick the largest natural width (8/16/32).
    Access-column "8"/"16"/"32" → use directly. Default 8 if truly unknown.
  - `<access>` from R/W markings: `R`→`read-only`, `R/W`→`read-write`, `W`→`write-only`.
  - `<resetValue>` from Initial value / After Reset (hex `0x…`). Omit if "Undefined"/unknown.
    Replace `x`/`X` "don't care" nibbles with 0.
- `<fields>` (best effort — include when the bit table is parseable, skip cleanly if not):
  each `<field>` has `<name>`, optional `<description>` (one short line), and
  `<bitRange>[msb:lsb]</bitRange>`. Skip reserved/0 bits. Do not invent fields.
- Add one `<addressBlock>` per peripheral:
  `<offset>0x0</offset><size>0xNNN</size><usage>registers</usage>` where size covers the
  highest register offset + its byte width.

## Quality bar (this domain bricks ECUs on confident-wrong data — calibrate honestly)
- Do NOT guess addresses. If a register's address is ambiguous, omit it and leave an XML comment.
- Cross-check a few extracted addresses against the PDF text directly.
- Your fragment must be **well-formed XML** when wrapped in a single root element. Verify with
  `python -c "import xml.etree.ElementTree as ET; ET.fromstring('<r>'+open(PATH,encoding='utf-8').read()+'</r>')"`.
- End your final message with: a count of peripherals + registers emitted, any unresolved bases,
  and any registers you deliberately skipped.

## Example fragment
```xml
<peripheral>
  <name>RESET</name>
  <description>Reset Controller</description>
  <baseAddress>0xFF420014</baseAddress>
  <addressBlock><offset>0x0</offset><size>0x20</size><usage>registers</usage></addressBlock>
  <registers>
    <register>
      <name>RESF</name>
      <description>Reset Source Register</description>
      <addressOffset>0xC</addressOffset>
      <size>16</size>
      <access>read-only</access>
      <resetValue>0x8000</resetValue>
      <fields>
        <field><name>RESF15</name><description>External reset flag</description><bitRange>[15:15]</bitRange></field>
        <field><name>RESF0</name><description>Low voltage indicator reset flag</description><bitRange>[0:0]</bitRange></field>
      </fields>
    </register>
  </registers>
</peripheral>
```
