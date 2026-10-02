---
name: feedback-never-sendmessage-a-running-workflow-subagent-it-resumes-a-duplicate
description: "Harness trap 2026-10-01: replying by SendMessage to a workflow subagent that is still running RESUMES A DUPLICATE copy of it from its transcript ('Resuming agent …'); both copies then edit the same tree — the fixer saw a 'concurrent writer' that was its own resumed twin (it committed 2712e1336 from the original's uncommitted edits). Outcome was consistent only because the original verified HEAD and re-ran the suites. Rule: answer a running workflow agent's question only through the next workflow stage or by stopping and resuming the workflow with the answer in the prompt; never SendMessage it mid-run."
metadata:
  type: feedback
---

**Why:** the Agent/SendMessage path treats an agent id as a resumable transcript; a workflow's live agent and the resumed
copy run concurrently in the same working tree. **How to apply:** design workflow briefs to be self-sufficient (decide the
ambiguous points in the brief); if an agent asks mid-run, let it proceed on its stated default.
