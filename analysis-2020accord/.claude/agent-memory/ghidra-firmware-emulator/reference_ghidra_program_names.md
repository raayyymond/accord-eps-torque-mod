---
name: reference-ghidra-program-names
description: Ghidra open program names for this project — always pass program= explicitly
metadata:
  type: reference
---

# Ghidra Open Programs

Always pass `program=` explicitly on every GhidraMCP call. Three programs are open:

| Name | Description | Function count |
|------|-------------|---------------|
| `code.bin` | STOCK baseline (fully analyzed) | 2113 |
| `_v23_plain_image.bin` | V23 modded build (partially analyzed) | 1687 |
| `_v22_plain_image.bin` | V22 modded build (partially analyzed) | 1681 |

- All use `V850:LE:32:default` language, image_base `0x00000000`
- `code.bin` path in Ghidra project: `/master.bin`
- V23 is stock + 3-byte patches (addresses identical to stock)
- Current active program (default if omitted): `_v23_plain_image.bin`
