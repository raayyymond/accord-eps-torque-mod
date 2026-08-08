---
name: feedback-stale-ghidra-import-defeats-hash-check
description: An open Ghidra program can hold a stale revision of a file whose on-disk hash is correct — so hash-checking alone cannot certify a re-disassembly gate; re-import fresh and spot-check bytes.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ad5622d6-5208-450c-86c6-9dd849c09dd4
  modified: 2026-07-24T20:31:27.284Z
---

**Hashing the file on disk proves nothing about what Ghidra has loaded.** Hit TWICE in one session
(2026-07-24) on the V52C pre-flash gate.

1. **First form (caught by hashing):** an agent verified a **superseded image** and reported the old
   SHA. Caught only because the brief pinned the expected SHA. Its PASS was for the wrong build.
2. **Second form (hashing does NOT catch it):** an agent verified the on-disk SHA **correctly**, but
   the already-open Ghidra program of the same name was **stale**. `read_memory` /
   `disassemble_bytes` returned `ld.h -0x4f60` (raw) at all three newly-edited sites, while a direct
   Python read of the same file offsets returned `00ed` (edited). Ghidra held an earlier revision of
   a file that had since been regenerated in place.

**Why it matters:** this is the failure mode that certifies a bad image as good. In a kit whose only
bricking class is the code cave (V24/V27/V48B), a false PASS on the re-disassembly gate is the last
thing standing between a build and the car.

**★ STANDING RULE for any load-bearing re-disassembly gate:**
1. Verify the on-disk SHA-256 first, and pin the expected value in the agent's brief.
2. **Re-import a FRESH copy** — never trust an open program merely because the name matches. Expect
   a `.N` suffix on name collision (the trustworthy handle became `/_v52c_plain_image.bin.1`).
3. **Spot-check at least one edited site against a direct Python byte read of the file** before
   trusting any disassembly output.

Also: `close_program` matches by display **name** and will close *all* duplicates sharing it — so
cleaning up one stale copy can silently close the good one too.

Related: `disassemble_bytes` MUTATES the shared Ghidra DB unless `dry_run:true`; never `save_program`
after exploratory disassembly. See [[feedback-verify-subagent-conclusions]].
