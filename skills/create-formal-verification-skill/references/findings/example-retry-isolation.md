# Example: retry-attempt isolation of a completion marker

A synthetic record showing the fields every finding carries. The system, names and numbers are illustrative.

| Field | Value |
|---|---|
| Repository | `<owner>/<repo>` |
| Commit | `<full sha>` (also the sync commit) |
| Property A | `PublicationBelongsToCurrentAttempt`: the stored completion marker is empty or was written by the current retry attempt |
| Harm of A | A stale write from an older attempt marks the current attempt as published, so the current watcher's completion claim is refused |
| Property B | `RetryMessageStartsAtMostOneRetry`: each retry message, even when redelivered, starts at most one retry |
| Tool | TLA+ / TLC (version and jar SHA-256); replay against an owned disposable database |
| Bounds | One job, two watcher invocations, `MaxRetries = 2`, each watcher claims at most once |
| Assumptions | Single-document updates are atomic; queue messages can be duplicated or delayed; claims expire and watchers crash nondeterministically |
| Model verdict | A violated: five-state counterexample (34 states generated, 27 distinct). B holds: 510 generated, 218 distinct, search complete |
| Implementation verdict | A violated through the production storage methods. B holds; the duplicate retry is rejected and the retry count stays 1 |
| Mutation | Weakening the retry-count compare-and-set made B fail in the model and in the replay (duplicate accepted, count 2). Source restored, rebuilt, baseline replay matched, covered hashes matched |
| Evidence tier | Model check plus implementation replay at the storage boundary. No queue, watcher process or worker execution |
| Fix owner / state | Who owns the fix and whether it is merged, as the owner reports it |
| Uncovered | Everything outside the bounds: other phases, liveness, failover, deployment or customer impact |
| Evidence | Path to the evidence directory and the files in it |

## Code correspondence

Each model action maps to the method that performs it: the watcher's claim, its publish, its marker write, and the handler that starts the retry. Note which steps are separate (none atomic with another) and which model variables have no stored counterpart.

## Counterexample for A, in the code's terms

1. Watcher A, at retry 0, claims completion.
2. Watcher A publishes a retry with observed retry 0.
3. The retry handler increments the retry count to 1 and clears the sentinels.
4. Watcher A writes the marker by job id alone. The marker now belongs to attempt 0 while the job is on attempt 1.

## Replay procedure

The exact calls against an owned database on a non-default loopback port, in a fresh database dropped in `finally`, with the abort conditions that make an incomplete replay fail instead of pass. Then the baseline and mutant observables, side by side.
