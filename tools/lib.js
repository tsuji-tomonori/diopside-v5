import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

export function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

export function readText(path) {
  return readFileSync(path, "utf8");
}

export function listFiles(roots, predicate = () => true) {
  const files = [];
  for (const root of roots) walk(root, files, predicate);
  return files.sort();
}

function walk(path, files, predicate) {
  const stat = statSync(path);
  if (stat.isDirectory()) {
    if ([".git", "node_modules", ".worktrees", "dist", "build", "coverage"].includes(path.split("/").at(-1))) return;
    for (const entry of readdirSync(path)) walk(join(path, entry), files, predicate);
    return;
  }
  if (predicate(path)) files.push(path);
}

export function assert(condition, message) {
  if (!condition) throw new Error(message);
}

export function currentJstTimestamp(now = new Date()) {
  return `${jstIsoBase(now)}+09:00`;
}

export function currentJstDate(now = new Date()) {
  return jstIsoBase(now).slice(0, 10);
}

export function isCurrentJstTimestamp(value, now = new Date()) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$/.test(value) && value.slice(0, 10) === currentJstDate(now);
}

export function isCurrentJstDate(value, now = new Date()) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) && value === currentJstDate(now);
}

function jstIsoBase(now) {
  return new Date(now.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 19);
}
