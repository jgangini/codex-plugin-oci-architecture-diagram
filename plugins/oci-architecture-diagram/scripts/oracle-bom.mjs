#!/usr/bin/env node

import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export function computeConfigHash(configs) {
  return createHash("md5").update(JSON.stringify(configs), "utf8").digest("hex");
}

function requireString(value, path) {
  if (typeof value !== "string" || value.trim() === "") throw new Error(path + " must be a non-empty string");
}

function requireFiniteNonNegative(value, path) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    throw new Error(path + " must be a finite non-negative number");
  }
}

export function validateBom(bom) {
  if (!bom || typeof bom !== "object" || Array.isArray(bom)) throw new Error("BoM root must be an object");
  requireString(bom.label, "label");
  const validTimeFrame =
    (typeof bom.timeFrame === "string" && bom.timeFrame.trim() !== "") ||
    (bom.timeFrame && typeof bom.timeFrame === "object" && !Array.isArray(bom.timeFrame));
  if (!validTimeFrame) throw new Error("timeFrame must be a non-empty string or an estimator time-frame object");
  requireString(bom.currency, "currency");
  if (!bom.meta || typeof bom.meta !== "object" || Array.isArray(bom.meta)) throw new Error("meta must be an object");
  if (!Array.isArray(bom.configs) || bom.configs.length === 0) throw new Error("configs must be a non-empty array");
  if (!/^[a-f0-9]{32}$/i.test(bom.meta.hash ?? "")) throw new Error("meta.hash must be a 32-character hexadecimal MD5");

  bom.configs.forEach((config, configIndex) => {
    requireString(config?.label, "configs[" + configIndex + "].label");
    if (!Array.isArray(config.services) || config.services.length === 0) {
      throw new Error("configs[" + configIndex + "].services must be a non-empty array");
    }
    config.services.forEach((service, serviceIndex) => {
      requireString(service?.label, "configs[" + configIndex + "].services[" + serviceIndex + "].label");
      if (!Array.isArray(service.items)) throw new Error("configs[" + configIndex + "].services[" + serviceIndex + "].items must be an array");
      service.items.forEach((item, itemIndex) => {
        const base = "configs[" + configIndex + "].services[" + serviceIndex + "].items[" + itemIndex + "]";
        requireString(item?.sku, base + ".sku");
        requireFiniteNonNegative(item.quantity, base + ".quantity");
        requireFiniteNonNegative(item.unitPrice, base + ".unitPrice");
        requireFiniteNonNegative(item.monthlyCost, base + ".monthlyCost");
      });
    });
  });

  const computedHash = computeConfigHash(bom.configs);
  if (computedHash.toLowerCase() !== bom.meta.hash.toLowerCase()) {
    throw new Error("meta.hash mismatch: expected " + computedHash + ", found " + bom.meta.hash);
  }
  return true;
}

export function summarizeBom(bom) {
  validateBom(bom);
  let serviceCount = 0;
  let itemCount = 0;
  let monthlyCost = 0;
  for (const config of bom.configs) {
    serviceCount += config.services.length;
    for (const service of config.services) {
      itemCount += service.items.length;
      monthlyCost += service.items.reduce((sum, item) => sum + item.monthlyCost, 0);
    }
  }
  return {
    label: bom.label, timeFrame: bom.timeFrame, currency: bom.currency, configurations: bom.configs.length,
    services: serviceCount, pricedItems: itemCount, embeddedMonthlyCost: monthlyCost,
    dataBuildID: bom.meta.dataBuildID ?? null, hash: bom.meta.hash,
  };
}

export function listBomItems(bom) {
  validateBom(bom);
  return bom.configs.flatMap((config) =>
    config.services.flatMap((service) =>
      service.items.map((item) => ({
        configuration: config.label, service: service.label, sku: item.sku,
        quantity: item.quantity, unitPrice: item.unitPrice, monthlyCost: item.monthlyCost,
      })),
    ),
  );
}

async function loadJson(path) {
  return JSON.parse(await readFile(path, "utf8"));
}

async function main(argv) {
  const [command, inputPath, outputPath] = argv;
  if (!command || !inputPath || !["validate", "summary", "detail", "rehash"].includes(command)) {
    throw new Error("Usage: oracle-bom.mjs <validate|summary|detail|rehash> <input.json> [output.json]");
  }
  const input = resolve(inputPath);
  const bom = await loadJson(input);
  if (command === "validate") {
    validateBom(bom);
    console.log("Valid local structure and hash: " + input);
    return;
  }
  if (command === "summary") {
    console.log(JSON.stringify(summarizeBom(bom), null, 2));
    return;
  }
  if (command === "detail") {
    console.log(JSON.stringify({ summary: summarizeBom(bom), items: listBomItems(bom) }));
    return;
  }
  if (!outputPath) throw new Error("rehash requires a distinct output.json path");
  const output = resolve(outputPath);
  if (input.toLowerCase() === output.toLowerCase()) throw new Error("Refusing to overwrite the input; choose a distinct output path");
  if (!Array.isArray(bom.configs) || bom.configs.length === 0) throw new Error("configs must be a non-empty array before rehashing");
  bom.meta ??= {};
  bom.meta.hash = computeConfigHash(bom.configs);
  validateBom(bom);
  await writeFile(output, JSON.stringify(bom, null, 2) + "\n", { encoding: "utf8", flag: "wx" });
  console.log("Rehashed copy written: " + output);
}

const isDirectRun = process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);
if (isDirectRun) {
  main(process.argv.slice(2)).catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
