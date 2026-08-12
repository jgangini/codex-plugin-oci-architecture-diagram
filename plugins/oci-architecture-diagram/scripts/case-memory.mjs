#!/usr/bin/env node

import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REQUIRED_CASE_FILES = [
  "case-profile.md",
  "evidence-ledger.md",
  "question-log.json",
  "architecture-handoff.md",
  "sizing-handoff.md",
  "validation.md",
  "learning-log.md",
  "handoff-status.json",
];

function assertSlug(slug) {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) throw new Error("Case slug must be lowercase kebab-case");
}

async function createOnce(path, contents) {
  try {
    await writeFile(path, contents, { encoding: "utf8", flag: "wx" });
    return true;
  } catch (error) {
    if (error?.code === "EEXIST") return false;
    throw error;
  }
}

export async function initCase(workspacePath, slug, knowledgeRootInput) {
  assertSlug(slug);
  const workspace = resolve(workspacePath);
  const sourceReadme = resolve(workspace, ".source", "README.md");
  const source = await readFile(sourceReadme, "utf8").catch(() => "");
  if (!source.trim()) throw new Error("Missing non-empty case description at .source/README.md");

  const caseRoot = resolve(workspace, ".oci-bom", "cases", slug);
  const knowledgeRoot = knowledgeRootInput ? resolve(knowledgeRootInput) : resolve(workspace, ".oci-bom", "knowledge");
  await mkdir(caseRoot, { recursive: true });
  await mkdir(knowledgeRoot, { recursive: true });
  const templates = [
    ["case-profile.md", "# Case profile\n\nRecord confirmed business outcome, scope and assumptions.\n"],
    ["evidence-ledger.md", "# Evidence ledger\n\n| Source | Fact | Confidence | Notes |\n| --- | --- | --- | --- |\n"],
    ["question-log.json", JSON.stringify({ caseSlug: slug, questions: [] }, null, 2) + "\n"],
    ["architecture-handoff.md", "# Architecture handoff\n\nRecord the approved service map and technical constraints.\n"],
    ["sizing-handoff.md", "# Sizing handoff\n\nRecord drivers, formulas, quantities and cost bridge.\n"],
    ["validation.md", "# Validation\n\nRecord local and clean-browser import results for the exact delivered JSON.\n"],
    ["learning-log.md", "# Learning log\n\nRecord anonymized, evidence-backed improvements only.\n"],
    ["handoff-status.json", JSON.stringify({
      caseSlug: slug,
      commercial: { status: "pending", reviewer: null, timestamp: null, notes: "" },
      architecture: { status: "pending", reviewer: null, timestamp: null, notes: "" },
      engineering: { status: "pending", reviewer: null, timestamp: null, notes: "" },
      learning: { status: "pending", reviewer: null, timestamp: null, notes: "" },
    }, null, 2) + "\n"],
  ];
  const created = [];
  for (const [name, contents] of templates) if (await createOnce(resolve(caseRoot, name), contents)) created.push(name);
  await createOnce(resolve(knowledgeRoot, "question-bank.md"), "# Reusable question bank\n\nPromote only anonymized, evidence-backed questions.\n");
  await createOnce(resolve(knowledgeRoot, "pattern-candidates.md"), "# Pattern candidates\n\nRecord recurrence, limits and anonymous evidence.\n");
  await createOnce(resolve(knowledgeRoot, "improvement-log.md"), "# Improvement log\n\nRecord proposed, accepted, rejected and deferred changes.\n");
  return { workspace, caseRoot, knowledgeRoot, created };
}

export async function auditCase(workspacePath, slug) {
  assertSlug(slug);
  const caseRoot = resolve(workspacePath, ".oci-bom", "cases", slug);
  const missing = [];
  for (const name of REQUIRED_CASE_FILES) {
    const info = await stat(resolve(caseRoot, name)).catch(() => null);
    if (!info?.isFile() || info.size === 0) missing.push(name);
  }
  if (missing.length) throw new Error("Case memory is incomplete: " + missing.join(", "));
  const questions = JSON.parse(await readFile(resolve(caseRoot, "question-log.json"), "utf8"));
  if (questions.caseSlug !== slug || !Array.isArray(questions.questions)) {
    throw new Error("question-log.json does not match the case memory contract");
  }
  const handoffs = JSON.parse(await readFile(resolve(caseRoot, "handoff-status.json"), "utf8"));
  const allowed = new Set(["pending", "accepted", "rejected", "accepted_with_assumptions"]);
  for (const role of ["commercial", "architecture", "engineering", "learning"]) {
    if (!allowed.has(handoffs[role]?.status)) throw new Error("handoff-status.json has an invalid " + role + " status");
  }
  return { caseRoot, files: REQUIRED_CASE_FILES.length, questionCount: questions.questions.length, handoffs };
}

async function main(argv) {
  const [command, workspace, slug, knowledgeRoot] = argv;
  if (!command || !workspace || !slug || !["init", "audit"].includes(command)) {
    throw new Error("Usage: case-memory.mjs <init|audit> <workspace> <case-slug> [knowledge-root]");
  }
  const result = command === "init" ? await initCase(workspace, slug, knowledgeRoot) : await auditCase(workspace, slug);
  console.log(JSON.stringify(result, null, 2));
}

const isDirectRun = process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);
if (isDirectRun) {
  main(process.argv.slice(2)).catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
