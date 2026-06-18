---
name: merge
description: Automates the full PR merge workflow for the current branch — waits for CI checks to pass, approves the PR (if not authored by the current user), attempts to merge, and falls back to admin merge if needed. Use this skill whenever the user wants to merge a PR, wait for checks and merge, approve and merge, or automate the merge process for the current branch. Triggers on phrases like "merge this PR", "wait and merge", "approve and merge", "merge current PR", or just "merge it".
---

# Merge — Automated PR Merge Workflow

This skill automates the complete lifecycle of merging a pull request from the current branch. It handles the tedious wait-for-CI-then-merge loop so the user doesn't have to keep checking back.

## Workflow

### Step 1: Identify the PR

Get the PR associated with the current branch:

```bash
gh pr view --json number,title,author,state,mergeable,mergeStateStatus,statusCheckRollup,url,headRefName,baseRefName
```

If no PR exists for the current branch, tell the user and stop.

### Step 2: Wait for checks to pass

Poll the PR's check status every 30 seconds until all checks resolve (pass or fail). Use this command to check status:

```bash
gh pr checks --watch --fail-fast
```

The `--watch` flag makes `gh` poll automatically until checks complete. If `--watch` is not available in the installed version, fall back to manual polling:

```bash
gh pr checks
```

And re-run every 10 seconds. Give up after 30 minutes — if checks haven't completed by then, report the status and stop.

While waiting, give the user brief status updates at reasonable intervals (not every poll — maybe every 2-3 minutes or when something changes).

**If any check fails**: Report which checks failed and stop. Don't attempt to merge a PR with failed checks.

### Step 3: Approve the PR (if not yours)

Check who authored the PR and who the current GitHub user is:

```bash
gh api user --jq '.login'
```

If the current user is **not** the PR author, approve the PR:

```bash
gh pr review --approve
```

If the current user **is** the author, skip approval (GitHub doesn't allow self-approval) and mention this to the user.

### Step 4: Merge the PR

Attempt a normal merge (respecting the repo's configured merge strategy):

```bash
gh pr merge --auto
```

If `--auto` is not enabled for the repo, try a direct merge:

```bash
gh pr merge
```

Let `gh` use whatever merge method the repo allows (squash, merge commit, or rebase) — don't force a specific strategy unless the repo only allows one.

### Step 5: Admin merge fallback

If the merge fails (e.g., branch protection rules, required reviews not met), check if the current user has admin privileges and attempt an admin merge:

```bash
gh pr merge --admin
```

If admin merge also fails, report the error clearly to the user — it likely means they don't have admin access or the repo has restrictions that can't be bypassed.

### Step 6: Post-merge CI monitoring

After the merge is complete, monitor the CI pipeline on the base branch to confirm the deploy succeeded.

1. Get the latest commit on the base branch (usually `master`) and find its check runs:

```bash
gh run list --branch master --limit 5 --json databaseId,status,conclusion,name,headSha,createdAt
```

2. Identify the run triggered by the merge commit and watch it:

```bash
gh run watch <run-id>
```

If `--watch` hangs or is unavailable, fall back to polling with `gh run view <run-id> --json status,conclusion` every 10 seconds. Give up after 30 minutes. Only update the user every 1 minute or when status changes — don't spam on every poll.

3. Report the outcome:
   - **All jobs succeeded**: Tell the user the deploy completed successfully.
   - **Any job failed**: Report which jobs failed, include the URL to the failed run, and suggest the user investigate.

## Error handling

- **No PR found**: "No PR found for the current branch. Create one first."
- **Checks failed**: "CI checks failed: [list failed checks]. Fix the issues before merging."
- **Merge conflict**: "PR has merge conflicts. Resolve them before merging."
- **Permission denied on admin merge**: "Regular merge failed and admin merge is not available. You may need additional permissions or required reviews."

## Important notes

- Never force-push or modify the branch — this skill only handles the approve/merge flow.
- If the PR is in draft state, tell the user and stop — don't try to merge drafts.
- If the PR is already merged or closed, tell the user and stop.
