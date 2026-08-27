---
name: feedback-short-installer-branch-names
description: "When handing Joey an openpilot-fork installer link (installer.comma.ai/<account>/<branch>), use a SHORT branch name (~5-7 chars, e.g. latlon / latonly). He hand-types it on the comma 4's tiny touchscreen, so long descriptive branch names are painful."
metadata:
  type: feedback
---

# Use short branch names for comma installer links

**Rule:** when delivering an openpilot fork install link of the form `installer.comma.ai/<github-account>/<branch>`, give the operator a SHORT branch token (~5-7 chars). Create a short-named branch alias pointing at the same commit and hand over `installer.comma.ai/internetadventuresllc/<short-branch>`.

**Why:** Confirmed 2026-05-28. The first link used a long descriptive branch (`eps-civic-latB-shll2-2026-05-28`) which was painful to type on the comma 4's small touchscreen. Joey asked for "5-7 chars," I aliased the branches to `latlon` (lat+long) and `latonly` (lat only), and he confirmed: "much easier lol that worked on the tiny af comma 4 screen."

**How to apply:**
- The `<github-account>` segment is fixed (his handle `internetadventuresllc`, and the installer always reads `<account>/openpilot`) — only the branch is shortenable. A shorter full URL would require a short-named GitHub org with its own `openpilot` repo (operator's action).
- Keep the long descriptive branch as an alias for the record if useful, but lead with the short one.
- Default to a short mnemonic of contents (e.g. `latlon`, `latonly`) so the short name still says what's in it.

See [[project-proper-qa-and-flash-plan]] for the current branch/installer set.
