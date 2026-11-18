### Investigation

**You own the answer. Plan, route, write.**

Read-only requests: "how does X work?", "why was Y built this way?", "are we sure about Z?", "should we do X or Y?". They produce a cited explanation or a recommendation, not a code change.

0. Restate the question in your own words and name what would count as an answer. A question inherited from a thread carries its author's framing; drop the framing, keep the question.
1. When delegation is allowed, send **one** read-only reader at the question, with the affected subsystems named in its brief; summaries back, never raw file dumps. Widen to a second reader only when the first reports back insufficient and says what it could not cover — never preemptively, and never one-per-subsystem (the fan-out cap). For motivation questions ("why was this built this way") the reader also does archaeology, over the sources the question points at rather than all of them: git history, PRs, and the Jira ticket trail (`gh`, `git log -S`, atlassian tooling); Slack threads (the Slack MCP search) when the decision looks argued rather than documented; production signals (GCP logs, Influx metrics) when the question is about runtime behavior. Motivation lives outside the repo more often than in it. Without delegation, do the same bounded reads serially.
2. For "are we sure?" questions, add one adversarial reader prompted to refute the premise, not confirm it — this is the sanctioned second agent, so it replaces a widening read rather than stacking on one.
3. Produce the answer shaped as Overview / Key Concepts / How It Works / Where Things Live / Gotchas — or, when the request is a decision between alternatives, a recommendation with a short tradeoffs table and your real judgment. Cite `file:line` for every load-bearing claim.
4. When a diagram genuinely clarifies, use `show-me`.

No PR, no babysit, no design exploration unless the investigation precedes a code change. If it does, report back and re-route to Bug fix or Feature.

**Reply:** the investigation output. For "are we sure?" answers, include your real judgment with reasons. Push back if the premise is wrong.
