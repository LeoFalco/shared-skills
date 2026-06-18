---
name: pin-dependencies
description: Pin npm dependencies by removing ^ and ~ version prefixes from package.json files. Detects monorepos (workspaces) and applies across all package.json files. Use when the user asks to pin dependencies, lock versions, remove version ranges, exact versions, or freeze dependency versions — even if they phrase it casually like "make my deps exact" or "stop version drift".
---

# Pin Dependencies

Remove `^` and `~` prefixes from version strings in `package.json` files, converting semver ranges into exact pinned versions.

## What it does

- Scans the project root `package.json` for workspace definitions
- If workspaces are found, collects all workspace `package.json` files
- If no workspaces, operates on the root `package.json` only
- Strips `^` and `~` from all version values in `dependencies`, `devDependencies`, and `peerDependencies`
- Leaves versions that are already exact, use `*`, `latest`, URLs, git refs, or `workspace:` protocol untouched — only `^` and `~` prefixes are removed

## How to use

A skill pode estar instalada em vários lugares dependendo do harness (`$HOME/.claude/skills/pin-dependencies`, `$HOME/.agents/skills/pin-dependencies`, `$HOME/.cursor/skills/pin-dependencies`, ou em `.claude/skills/pin-dependencies` / `.agents/skills/pin-dependencies` dentro do projeto). Antes do primeiro uso na conversa, descubra o caminho real do `pin-dependencies.js` filtrando apenas os diretórios que existem (senão o `find` aborta com exit≠0 e zera a variável):

```bash
SEARCH=""
for d in "$HOME/.claude/skills" "$HOME/.agents/skills" "$HOME/.cursor/skills" ".claude/skills" ".agents/skills"; do
  [ -d "$d" ] && SEARCH="$SEARCH $d"
done
SCRIPT="$(find $SEARCH -name pin-dependencies.js -path '*/pin-dependencies/*' 2>/dev/null | head -1)"
```

Se `$SCRIPT` ficar vazio, a skill não está instalada nesse harness — diga ao usuário pra rodar `npx skills add LeoFalco/shared-skills -g -y` (ou `npx skills update pin-dependencies -g -y` se já tiver outras skills do repo) e pare.

Run the bundled script from the project root:

```bash
node "$SCRIPT"
```

The script will:
1. Print which `package.json` files it found
2. For each file, list every dependency that was pinned (old → new)
3. Run `npm install` (or `yarn install` if `yarn.lock` exists) in each directory that had changes, to update the lock file
4. Print a summary of total changes

After running, review the changes with `git diff` and confirm with the user before committing.

## Edge cases

- **Workspace protocols** (`workspace:^1.0.0`): left untouched since these are managed by the package manager
- **Non-semver values** (`*`, `latest`, URLs, file paths, git refs): left untouched
- **Already pinned versions** (`1.2.3`): skipped silently
- **Empty dependency sections**: skipped
- **Nested node_modules package.json**: ignored (only workspace-declared packages are processed)
