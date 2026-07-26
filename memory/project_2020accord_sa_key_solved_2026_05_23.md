---
name: project-2020accord-sa-key-solved-2026-05-23
description: 2020 Accord TVA EPS SA-key chain is shipped on branch 2020accord (commit 4cf5d3b); algorithm verified, stock .rwd v2 rebuilt, flasher QA-shipped; rayy's dry-run is next
metadata:
  type: project
source: collaborative
---

**The 2020 Accord (TVA chassis) EPS SA-key chain is shipped end-to-end.** Status as of session 2026-05-23 (pushed to `origin/2020accord`):

| Layer | Artifact | Status |
|---|---|---|
| Verified algorithm + constants | `flashing-2020accord/tva_sa_key.py`, `V850_ALGORITHM_VERIFIED.md` | HIGH confidence, datasheet-verified (10 self-check vectors pass) |
| Stock TVA-A160 .rwd v2 | `../accord-firmware/flashing-2020accord/archive/39990-TVA-A160-RECONSTRUCTED-v2.rwd` | 62 blocks byte-equal to code.bin; all 48 CRC-32 trailers PASS; file checksum 0x048338DB |
| Consolidated architecture map | `analysis-2020accord/ACCORD_TVA_ARCHITECTURE_MAP.md` | §7.4 SA algorithm added, §11 #5 RESOLVED |
| Session narrative | `analysis-2020accord/SESSION_DIGEST_2026-05-23.md` | Single-doc handoff |
| Flasher | `flashing-2020accord/eps-update-tva.py` + `flashing-2020accord/EPS_UPDATE_TVA_README.md` + `flashing-2020accord/EPS_UPDATE_TVA_QA.md` | SHIP per adversarial QA; mock-under-danger guard added |

Git: branch `2020accord`, two session commits: `9c23c8a` (Wave 1 + stock recon + QA), `56ff83a` (SA-key chain + docs propagation), `4cf5d3b` (eps-update-tva.py + QA).

## Where to pick up next session

Three real follow-up items remain (architecture map §11):

1. **Trace V850 code paths reading candidate torque tables** — Wave 2 work; needed before any modified higher-torque .rwd build. Use `disasm_v850.py` + the 1378-table inventory in `TABLE_INVENTORY.md`.
2. **Trace `+0xFF6` chain pointer runtime role** — what code walks the 48-block CRC chain pointer? Answers whether torque-table patches need chain-walking or stay local.
3. **Source the actual TVA-A160 stock .rwd** — rayy doesn't have it; iHDS J2534 server (requires Honda VSP sub), leaked archives, or session capture are the realistic paths. Unblocks byte-vs-Honda verification.

## rayy's next concrete action (dry-run validation)

The dry-run path proves the SA-key story on hardware with zero brick risk:

```bash
git pull origin 2020accord
cp flashing-2020accord/{eps-update-tva.py,tva_sa_key.py,encode_eps.py} ~/sunnypilot_eps/
cp ../accord-firmware/flashing-2020accord/archive/39990-TVA-A160-RECONSTRUCTED-v2.rwd ~/sunnypilot_eps/
cd ~/sunnypilot_eps && python eps-update-tva.py --bus 1 39990-TVA-A160-RECONSTRUCTED-v2.rwd
```

If the script reaches `SA handshake succeeded`, the V850 Group C constants are **confirmed against hardware** — closes the last open layer of the SA-key chain. No flash without `--danger` + interactive `FLASH` confirmation.

## Companion memories

- [[reference-v850-sa-algorithm-tva]] — the algorithm + constants details
- [[reference-honda-eps-sa-secret-per-mcu-family]] — cross-family pattern (SH-2A vs V850)
- [[reference-rizin-ghidra-v850-quirks]] — tooling bugs that bit this session

**Why:** captures the session-end state so next session resumption knows what's done, what's open, and what rayy is testing. **How to apply:** read on session resume alongside the architecture map; if rayy has run the dry-run, mark whether SA handshake succeeded as the next confidence step.
