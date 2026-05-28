import { existsSync, readFileSync, statSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join, resolve } from "node:path";

export function currentGitCommit() {
  if (/^[a-f0-9]{40}$/i.test(process.env.GITHUB_SHA || "")) return process.env.GITHUB_SHA.toLowerCase();

  const gitDir = resolveGitDir();
  const commonDir = resolveCommonGitDir(gitDir);
  const head = readFileSync(join(gitDir, "HEAD"), "utf8").trim();
  if (/^[a-f0-9]{40}$/i.test(head)) return head.toLowerCase();

  const ref = head.match(/^ref: (.+)$/)?.[1];
  if (!ref) throw new Error(`Unsupported git HEAD format: ${head}`);

  const refPath = join(commonDir, ref);
  if (existsSync(refPath)) return readFileSync(refPath, "utf8").trim().toLowerCase();

  const packedRefs = join(commonDir, "packed-refs");
  if (existsSync(packedRefs)) {
    for (const line of readFileSync(packedRefs, "utf8").split(/\r?\n/)) {
      const match = line.match(/^([a-f0-9]{40}) (.+)$/i);
      if (match?.[2] === ref) return match[1].toLowerCase();
    }
  }

  throw new Error(`Git ref not found: ${ref}`);
}

export function gitTagCommit(tagName) {
  if (typeof tagName !== "string" || tagName.length === 0) return null;
  try {
    return execFileSync("git", ["rev-list", "-n", "1", tagName], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim().toLowerCase() || null;
  } catch {
    return null;
  }
}

export function currentGitRepository() {
  try {
    return parseGitHubRepository(execFileSync("git", ["config", "--get", "remote.origin.url"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim());
  } catch {
    return null;
  }
}

export function parseGitHubRepository(remoteUrl) {
  if (typeof remoteUrl !== "string" || remoteUrl.length === 0) return null;
  const normalized = remoteUrl.replace(/\.git$/, "");
  const httpsMatch = normalized.match(/^https:\/\/github\.com\/([^/]+)\/([^/]+)$/);
  if (httpsMatch) return `${httpsMatch[1]}/${httpsMatch[2]}`;
  const sshMatch = normalized.match(/^git@github\.com:([^/]+)\/([^/]+)$/);
  if (sshMatch) return `${sshMatch[1]}/${sshMatch[2]}`;
  return null;
}

function resolveGitDir() {
  if (statSync(".git").isDirectory()) return resolve(".git");

  const dotGit = readFileSync(".git", "utf8").trim();
  const gitDir = dotGit.match(/^gitdir: (.+)$/)?.[1];
  if (gitDir) return resolve(gitDir);
  return resolve(".git");
}

function resolveCommonGitDir(gitDir) {
  const commonDirPath = join(gitDir, "commondir");
  if (!existsSync(commonDirPath)) return gitDir;
  return resolve(gitDir, readFileSync(commonDirPath, "utf8").trim());
}
