---
name: dream-can-topology-method-generalization
description: "vfn's 'opendbc dbc + SH mailbox CAN ID table + LKAS-path RAM trace' method is a generalizable methodology for mapping any vehicle's firmware to its CAN message semantics. Currently specialist-7-drafted for C120; cross-platform generalizations: Accord TVA (V850 / different MCU but same DBC source), CR-V (different LKAS architecture), Pilot (V850 LE). The methodology, not just its Civic application, is the durable artifact."
metadata:
  type: dream
---

# Dream — vfn's CAN-topology method as a cross-platform methodology

**Lower-confidence thread.** Generated 2026-05-25 from vfn's Discord tip and the realization that the method generalizes well beyond Civic.

## The thread

vfn dropped this method 2026-05-25 7:25pm:
> "look for the opendbc and imports in your vehicles dbc, the ecus that we know about your vehicle will be labeled, and different messages from those ecus will be labeled, that gives you a starting point to see whats what in the firmware
> then find the sh mailbox can ecu id table
> then have your llm check every function on the lkas code path to see from the ram addresses that the mailbox stores those states/messages in
> and see what values are used where"

The Ghidra MCP swarm specialist-7 prompt (`docs/swarm-specialists/07-can-topology.md`) implements this for C120. But the method itself is platform-agnostic:

1. **Acquire a vehicle's DBC** (opendbc has multiple, including Civic 2024+, Accord 2018+, Pilot, CR-V, Clarity)
2. **Find the firmware's CAN acceptance filter / mailbox table** (architecture-specific: SH-2A uses RCAN mailbox tables; V850 uses CAN-FD acceptance filters; etc.)
3. **Decode each mailbox entry** to its CAN ID + DLC + handler function
4. **For each CAN ID matched to DBC**, the message has named signals
5. **Trace mailbox → RAM destination → downstream readers** to find where each signal feeds in firmware
6. **Filter to the relevant code path** (LKAS for steering tuning, brakes for ABS work, throttle for cruise tuning, etc.)

The result for each platform: a CAN-message-by-message map of what each inbound message drives in firmware.

## Why generalization matters

The current state of cross-platform Honda EPS knowledge in this kit:
- **C120 (Civic)** — Era 10 reaches the depth where lever sites are well-mapped, but CAN-message-by-message tracing is still partial (only mailbox 19 = CAN 0xE4 STEERING_CONTROL is deeply traced). Specialist 7 would finish this.
- **Accord TVA (V850)** — Era 4: SA-key algorithm verified, .rwd parsed, flasher shipped. CAN topology side untouched. If Accord tuning ever matters, the same method applies.
- **CR-V** — Currently only present as `eps_tool.py:79` config entries. Same MCU family as Civic; same SH-2A LKAS architecture. The method would adapt cleanly.
- **Pilot** — `reference_pilot_tg7_is_v850.md` resolved chip identity to V850. CAN topology side completely unstudied. Same method, different MCU.
- **Clarity** — Reference `reference_clarity_civic_plus28.md` documents the +28 table shift. CAN topology side similar to Civic but with different addresses (`reference_civic_can_dispatch_topology.md` notes the Clarity mailbox table is at 0x4A850 not at C120's 0x49E80; same conceptual structure, different addresses).

**A platform-agnostic methodology document would let any future Honda EPS chassis be brought up to "we know what each inbound CAN message does" using the same playbook.** Time-to-coverage for a new platform drops dramatically.

## The methodology distilled

Phase 1 (DBC): get the vehicle's DBC from opendbc. Identify the messages relevant to your tuning question (e.g., for LKAS steering: STEERING_CONTROL, STEERING_SENSORS, STEER_TORQUE_SENSOR, STEER_STATUS).

Phase 2 (Filter table): find the firmware's CAN acceptance filter. Architecture-specific helpers:
- SH-2A: look for a contiguous 60×16B region near the CAN controller initialization code. CAN IDs are typically u16 BE at offset 4-5 of each entry.
- V850: different CAN controller; acceptance filters are also tabular but encoded differently.

Phase 3 (Mailbox decode): per-mailbox CAN ID extraction + DBC cross-reference. Annotate each mailbox with its DBC name in Ghidra.

Phase 4 (Mailbox-to-RAM): identify per-mailbox receive handlers. Either a single dispatcher with index-table dispatch, OR per-mailbox handler ptr table. Trace each mailbox's RAM destination.

Phase 5 (LKAS-path filter): for steering tuning, the LKAS path is the relevant subset. Other paths (brake, throttle, telemetry, diagnostic) get noted but not deep-dived in this campaign.

Phase 6 (Signal-to-function): for each LKAS-path mailbox, enumerate downstream readers and classify (flag test / stride-index / parameter pass / arithmetic operand). Result: "what each CAN signal value does in the firmware."

## Cross-platform considerations

- **MCU architecture matters for phases 2-3.** SH-2A and V850 have different CAN controller register layouts. The acceptance filter table format differs. A platform-specific cheat-sheet would help.
- **DBC coverage matters.** Some Honda vehicles have full opendbc coverage; others have partial. Where DBC is missing, phase 1 produces a numerical map instead of a semantic one (still useful, but less rich).
- **Naming conventions transfer.** The §9 naming convention from the C120 brief (`CAN_<purpose>_<addr>`, `FN_CAN_<handler>_<id>`, `RAM_<message>_<addr>`) transfers cleanly to any platform.

## The aspirational artifact

A document: `docs/methodology/CAN-TOPOLOGY-METHOD.md` describing the 6-phase method, with architecture-specific subsections (SH-2A, V850), and a reference application (C120) showing the method end-to-end. Other platforms then have a recipe rather than reinventing.

## What this is NOT

- A claim the methodology is complete. CAN_TOPOLOGY specialist-7 hasn't run yet; the method is well-formed but unvalidated end-to-end on C120 itself.
- A claim that running this for every Honda EPS chassis is worth the effort. Each platform has its own priorities; the methodology being available doesn't mean it should be applied indiscriminately.
- A commitment to write the methodology doc tonight. Speculative — Joey's call whether the cross-platform value justifies the doc-writing time.

## Cross-refs

- [[reference-civic-can-dispatch-topology]] — the C120 application of the method (current depth: mailbox 19 only)
- [[reference-clarity-civic+28]] — Clarity's analog architecture (different addresses, same structure)
- [[reference-pilot-tg7-is-v850]] — Pilot uses V850; the method would extend cross-MCU
- [[project-2020accord-sa-key-solved-2026-05-23]] — Accord TVA / V850 platform state; CAN topology side is untouched there
- [[reference-honda-eps-sa-secret-per-mcu-family]] — methodology generalization pattern from a different angle (SA secret per family); CAN topology is a parallel cross-family pattern
