import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { auditCase, initCase } from "./case-memory.mjs";

async function workspace(t) {
  const root = await mkdtemp(join(tmpdir(), "oci-architecture-case-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, ".source"), { recursive: true });
  await writeFile(join(root, ".source", "README.md"), "# Case\n", "utf8");
  return root;
}

test("initializes, audits and preserves the integrated case memory", async (t) => {
  const root = await workspace(t);
  const initialized = await initCase(root, "case-one");
  assert.equal(initialized.created.length, 8);
  assert.equal((await auditCase(root, "case-one")).files, 8);
  await writeFile(join(initialized.caseRoot, "case-profile.md"), "# Preserved\n", "utf8");
  await initCase(root, "case-one");
  assert.equal(await readFile(join(initialized.caseRoot, "case-profile.md"), "utf8"), "# Preserved\n");
});
