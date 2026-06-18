---
name: cleanup-branches
description: Cleans up local git branches whose remote tracking branches are gone (pruned), deletes remote branches whose PRs are merged or closed, and ensures the GitHub repo has "delete branch on merge" enabled. Use when the user wants to clean up stale branches, prune old branches, remove merged branches, delete closed PR branches, or tidy up their git state. Triggers on phrases like "cleanup branches", "prune branches", "remove stale branches", "clean up old branches", "delete gone branches", "clean remote branches".
user_invocable: true
---

# Cleanup Branches — Prune Gone Remotes, Clean Remote Branches & Enable Auto-Delete

This skill removes local branches that track remote branches which no longer exist (marked as `[gone]`), deletes remote branches whose associated PRs are merged or closed, and ensures the GitHub repository has "delete branch on merge" enabled so merged branches are automatically cleaned up server-side.

## Workflow

### Step 1: Enable "delete branch on merge" on the GitHub repo

Check if the setting is already enabled:

```bash
gh api repos/{owner}/{repo} --jq '.delete_branch_on_merge'
```

To get the owner/repo from the current git remote:

```bash
gh repo view --json nameWithOwner --jq '.nameWithOwner'
```

If it returns `false`, enable it:

```bash
gh api repos/{owner}/{repo} --method PATCH --field delete_branch_on_merge=true
```

Report the result to the user.

### Step 2: Delete remote branches with merged or closed PRs

Find remote branches whose PRs have been merged or closed but whose branches were not deleted:

```bash
gh pr list --state merged --json headRefName --jq '.[].headRefName'
gh pr list --state closed --json headRefName --jq '.[].headRefName'
```

For each branch found, delete it from the remote:

```bash
git push origin --delete <branch-name>
```

**Important**: Never delete the default branch (master/main) or protected branches (like `homolog`). Skip branches that no longer exist on the remote (they may have already been deleted).

If a `git push --delete` fails because the branch doesn't exist on the remote, ignore the error and continue.

### Step 3: Fetch and prune remote tracking references

```bash
git fetch --prune
```

This updates the remote tracking branches and removes references to branches that no longer exist on the remote. Run this **after** Step 2 so that remotely-deleted branches from that step are also pruned locally.

### Step 4: Find local branches with gone remotes

List branches whose upstream is gone:

```bash
git branch -vv | grep ': gone]'
```

Parse out just the branch names from this output. These are the branches to delete.

### Step 5: Delete the stale local branches

For each branch found in Step 4, delete it:

```bash
git branch -D <branch-name>
```

Use `-D` (force delete) because these branches may not be fully merged into the current branch, but their remote counterpart is already gone (meaning they were merged and deleted remotely).

**Important**: Never delete the current branch. If the current branch is in the gone list, switch to `master` (or `main`) first, then delete it.

### Step 6: Report results

Tell the user:
- Whether "delete branch on merge" was already enabled or was just enabled
- How many remote branches were deleted (from merged/closed PRs) and their names
- How many local branches were pruned and their names
- If no stale branches were found, say so

## Error handling

- **No gone branches found**: "No stale branches found — your local repo is clean!"
- **Cannot enable delete_branch_on_merge**: "Could not enable auto-delete on merge — you may not have admin access to this repo."
- **Current branch is gone**: Switch to master/main first, then delete it.
- **Remote branch already deleted**: If `git push origin --delete` fails with "remote ref does not exist", skip it silently.
- **Protected branch in list**: Never delete default or protected branches (master, main, homolog). Skip them with a note to the user.
