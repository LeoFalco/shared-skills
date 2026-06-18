#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const DEP_KEYS = ["dependencies", "devDependencies", "peerDependencies"];

function findPackageJsonPaths(rootDir) {
  const rootPkg = JSON.parse(
    fs.readFileSync(path.join(rootDir, "package.json"), "utf-8")
  );

  const paths = [path.join(rootDir, "package.json")];

  const workspacePatterns = rootPkg.workspaces
    ? Array.isArray(rootPkg.workspaces)
      ? rootPkg.workspaces
      : rootPkg.workspaces.packages || []
    : [];

  if (workspacePatterns.length === 0) {
    // Check for lerna.json
    const lernaPath = path.join(rootDir, "lerna.json");
    if (fs.existsSync(lernaPath)) {
      const lerna = JSON.parse(fs.readFileSync(lernaPath, "utf-8"));
      if (lerna.packages) {
        workspacePatterns.push(...lerna.packages);
      }
    }
  }

  if (workspacePatterns.length === 0) {
    return paths;
  }

  for (const pattern of workspacePatterns) {
    const globPattern = pattern.endsWith("/")
      ? pattern + "package.json"
      : pattern.endsWith("package.json")
        ? pattern
        : pattern + "/package.json";

    // Simple glob expansion — supports trailing /* only
    const normalized = globPattern.replace(/\*\//g, "*/");
    const parts = normalized.split("*");

    if (parts.length === 1) {
      // No glob, direct path
      const fullPath = path.resolve(rootDir, normalized);
      if (fs.existsSync(fullPath)) {
        paths.push(fullPath);
      }
    } else {
      // Expand one level of *
      const baseDir = path.resolve(rootDir, parts[0]);
      if (fs.existsSync(baseDir) && fs.statSync(baseDir).isDirectory()) {
        const entries = fs.readdirSync(baseDir, { withFileTypes: true });
        for (const entry of entries) {
          if (entry.isDirectory()) {
            const suffix = parts.slice(1).join("*");
            const candidate = path.join(baseDir, entry.name, suffix);
            if (fs.existsSync(candidate)) {
              paths.push(candidate);
            }
          }
        }
      }
    }
  }

  return [...new Set(paths)];
}

function shouldPin(version) {
  if (typeof version !== "string") return false;
  return version.startsWith("^") || version.startsWith("~");
}

function pinVersion(version) {
  return version.replace(/^[\^~]/, "");
}

function pinPackageJson(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  const pkg = JSON.parse(content);
  const changes = [];

  for (const key of DEP_KEYS) {
    if (!pkg[key] || typeof pkg[key] !== "object") continue;

    for (const [dep, version] of Object.entries(pkg[key])) {
      if (shouldPin(version)) {
        const pinned = pinVersion(version);
        changes.push({ section: key, dep, from: version, to: pinned });
        pkg[key][dep] = pinned;
      }
    }
  }

  if (changes.length > 0) {
    // Detect indent from original file
    var match = content.match(/^(\s+)"/m);
    var indent = (match && match[1]) || "  ";
    fs.writeFileSync(filePath, JSON.stringify(pkg, null, indent) + "\n");
  }

  return changes;
}

function main() {
  const rootDir = process.cwd();
  console.log(`\nScanning for package.json files in: ${rootDir}\n`);

  let packagePaths;
  try {
    packagePaths = findPackageJsonPaths(rootDir);
  } catch (err) {
    console.error(`Error finding package.json files: ${err.message}`);
    process.exit(1);
  }

  console.log(`Found ${packagePaths.length} package.json file(s):\n`);
  for (const p of packagePaths) {
    console.log(`  - ${path.relative(rootDir, p)}`);
  }
  console.log();

  let totalChanges = 0;

  for (const pkgPath of packagePaths) {
    const relative = path.relative(rootDir, pkgPath);
    let changes;

    try {
      changes = pinPackageJson(pkgPath);
    } catch (err) {
      console.error(`  Error processing ${relative}: ${err.message}`);
      continue;
    }

    if (changes.length === 0) {
      console.log(`${relative}: no changes needed`);
      continue;
    }

    console.log(`${relative}: pinned ${changes.length} dependencies`);
    for (const c of changes) {
      console.log(`  [${c.section}] ${c.dep}: ${c.from} -> ${c.to}`);
    }
    console.log();

    totalChanges += changes.length;
  }

  if (totalChanges > 0) {
    console.log(`\nPinned ${totalChanges} version(s). Running install for each package.json...\n`);

    for (const pkgPath of packagePaths) {
      var pkgDir = path.dirname(pkgPath);
      var relative = path.relative(rootDir, pkgDir) || ".";
      var usesYarn = fs.existsSync(path.join(pkgDir, "yarn.lock"));
      var cmd = usesYarn ? "yarn install" : "npm install";

      console.log(`[${relative}] ${cmd}`);
      try {
        execSync(cmd, { cwd: pkgDir, stdio: "inherit" });
        console.log(`[${relative}] install complete\n`);
      } catch (err) {
        console.error(`[${relative}] install failed (exit code ${err.status})\n`);
      }
    }
  } else {
    console.log("\nNo changes needed.");
  }

  console.log("Done. Review changes with: git diff");
}

main();
