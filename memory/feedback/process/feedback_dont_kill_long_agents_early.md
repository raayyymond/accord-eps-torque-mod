---
name: feedback-dont-kill-long-agents-early
description: When operator reports an agent is "lost in the sauce", prefer SendMessage to refine focus over TaskStop; long verbose traces can look like floundering when actually converging
metadata:
  type: feedback
source: collaborative
---

When Joey reports an agent is "getting lost in the sauce" mid-run, **default to SendMessage to refine focus, NOT TaskStop**.

**Why:** A long-running agent's verbose intermediate trace can look like floundering when it's actually working through the search space. This session's Wave 2 SA handler verifier had a 7-step brief and was producing a lot of intermediate output as it traced V850 disassembly + call graphs. Joey was reading the trace and reported "lost in the sauce." I called TaskStop. The agent finished anyway (race condition), and its final result was clean: had localized the actual SA handler at `0xC94C` and was mid-sentence verifying the constants when killed. Joey immediately followed with "nvm it seems like its finishing up" — confirming my read was wrong.

What I should have done: SendMessage with a tightening directive ("stop trying to walk the full call graph; instead, just check whether the 3 mulhi sites at 0x4AFBC/0x5AEF8/0x5AF62 are reachable from the SA handler — answer yes/no"). This would have preserved the agent's accumulated state and focused it on the converging answer.

**How to apply:**
- "Lost in the sauce" from the operator = signal to refine, not to kill
- Use SendMessage to give the agent a tighter focus and a "report what you have so far + this specific question" directive
- Reserve TaskStop for: (a) confirmed-stuck for >10 min with no progress, (b) task is no longer needed (scope changed), (c) destructive operation underway that must be halted
- If unsure whether to kill, ask the operator: "should I refine or stop?"
- The cost of killing too early is real (lose context, may not finish the answer); the cost of refining is near-zero (agent gets more focus, you don't lose the work)

This is symmetric with [[feedback-tight-agent-briefs]] which addresses the root cause: agents with too-broad briefs are MORE likely to look "lost." Prevention is better than mid-flight refinement, but mid-flight refinement is better than termination.

**Companion observation:** Joey actively reads agent JSONL traces in real-time on his end. This means he has signal I don't (I'm told not to tail the transcript file). When he reports a state observation about a running agent, his read is the sensorimotor anchor — but the right response is refine, not terminate.
