# PR #168 vs PR #169 Merge Analysis

Date: `2026-04-05`

## Executive Verdict

### Safe choice

- **Use `#169`**

### Unsafe choice

- **Do not merge `#168`**

## One-Sentence Explanation

`#168` is a mixed branch that would bring in old unrelated work and artifacts, while `#169` is a fresh clean branch that contains only the six workflow changes we actually want for launch.

---

## The Simple Version

Think of the two PRs like this:

- `#168` is a bag with the right item plus a lot of extra things mixed in
- `#169` is the same right item, but packed by itself in a clean box

For launch, you want the clean box, not the mixed bag.

---

## Side-By-Side Comparison

| Topic | PR `#168` | PR `#169` | Why it matters |
|---|---|---|---|
| Overall recommendation | **Do not merge** | **Merge after review** | `#169` is the clean launch-safe replacement |
| PR state | Open | Open | Both exist right now |
| Merge state | `DIRTY` | `BLOCKED` | `DIRTY` means the branch itself is messy/conflicted; `BLOCKED` means branch protection/review is stopping merge |
| Review requirement | Required | Required | Both still need review |
| Commit count | **7 commits** | **1 commit** | More commits means more unrelated history/risk |
| Branch base | Old branch history | Fresh from current `main` | Fresh-from-main is safer |
| File count | Very large and mixed | **6 files only** | Smaller scope is much easier to trust |
| Runtime code included | Indirectly mixed with unrelated history/artifacts | **No** | Launch-safe PR should avoid product/runtime changes |
| Benchmark logic included | **Yes, in branch history** | **No** | Benchmark logic should not be bundled into launch workflow safeguards |
| Artifacts/logs included | **Yes, many** | **No** | These are noise and increase merge risk |
| Workflow-only scope | **No** | **Yes** | This is the key difference |

---

## What Is Inside PR #168

### Commit history in `#168`

`#168` contains these commits on top of `main`:

1. `74e5049b` `Sync model registry for launch (version match to release_manifest.json)`
2. `7a71f063` `Elite+ v3 Stability V1 launch backup`
3. `705092f7` `fix scheduled benchmark auth for HTTP mode`
4. `73898e7d` `fix scheduled benchmarks secret manager auth`
5. `d19bdc63` `mask benchmark api key in scheduled workflow`
6. `c1c136c5` `stabilize scheduled benchmark prompt formatting`
7. `94e19596` `fix: route launch automation through protected branches`

### Why that is a problem

Only the last commit is the launch workflow safeguard we want.

The earlier commits include older workflow work, benchmark prompt-formatting work, and historical launch/benchmark backup material. Even if some of that work is valid on its own, it does **not** belong inside one “safe launch workflow” merge.

### File scope in `#168`

`#168` includes:

- workflow files we want
- `.github/workflows/ci-cd.yaml`
- `.gitignore`
- benchmark and probe artifacts
- launch logs and snapshots
- many artifact files unrelated to the clean launch workflow fix

### Plain-English risk

If you merge `#168`, you are not just merging “safe launch workflow routing.”

You are merging a bundle of older history and extra files that make it much harder to know exactly what changed and why.

That is the opposite of what we want right before launch.

---

## What Is Inside PR #169

### Commit history in `#169`

`#169` contains exactly **one commit**:

- `6078665d` `fix: route launch automation through protected branches`

### File scope in `#169`

It changes exactly these 6 files:

1. `.github/workflows/auto-restore-critical-files.yaml`
2. `.github/workflows/modeldb_refresh.yml`
3. `.github/workflows/scheduled-benchmarks.yml`
4. `.github/workflows/secure-history.yml`
5. `.github/workflows/smoke-tests.yml`
6. `.github/workflows/weekly-improvement.yml`

### Why that is good

This is exactly the scope we wanted:

- route automation to PR branches instead of mutating `main`
- keep `secure-history` manual-only
- preserve benchmark secret wiring
- preserve smoke diagnostics

Nothing in `#169` changes:

- frontend runtime behavior
- backend runtime behavior
- benchmark scoring logic
- pricing
- routing

### Plain-English benefit

If you merge `#169`, you are merging only the workflow safety controls we intended, and nothing more.

---

## Why PR #169 Is Still Blocked

`#169` is currently blocked for two reasons:

1. **Review is required**
2. **One CI job is failing**

### Important clarification

That failing CI job does **not** appear to be caused by the six workflow changes in `#169`.

The failure is in the existing app test suite, with provider/chat test failures like:

- `tests/contract/test_api_contracts.py`
- `tests/test_chat_api_bridge.py`

Recent `main` history already shows the same baseline-red `CI/CD Pipeline` pattern. That means the red CI is most likely an existing repo-level issue, not evidence that `#169` broke product behavior.

---

## Why “DIRTY” vs “BLOCKED” Matters

### `#168` = `DIRTY`

In simple terms, `DIRTY` means:

- the branch is not cleanly aligned for merge
- it has extra baggage
- it is harder to reason about safely

For launch, this is a warning sign.

### `#169` = `BLOCKED`

In simple terms, `BLOCKED` means:

- the branch itself is the right shape
- GitHub is just enforcing process rules like review and required checks

That is much safer than `DIRTY`.

---

## Final Recommendation

### Merge decision

- **Do not merge `#168`**
- **Use `#169` as the only workflow-safeguards PR**

### Why this is the right decision

`#169` is:

- cleaner
- smaller
- easier to review
- easier to explain
- safer for launch

`#168` is:

- larger
- mixed with unrelated history
- harder to trust
- harder to roll back mentally

---

## What You Should Approve

If the goal is safe launch workflow hardening, the right approval target is:

- `#169`

And the right non-approval target is:

- `#168`

---

## Decision Summary

### If you want the safest launch path

- approve and merge `#169`
- leave `#168` unmerged / superseded

### If you merged `#168` instead

You would be accepting extra unrelated history and files at the worst possible time: right before launch.

That is why `#168` is the wrong merge.

---

## Bottom Line

If you only remember one thing, remember this:

- `#168` is the messy historical branch
- `#169` is the clean launch-safe branch

For launch, **`#169` is the correct merge**.
