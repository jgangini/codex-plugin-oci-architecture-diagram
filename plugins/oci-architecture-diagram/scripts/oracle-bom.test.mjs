import assert from "node:assert/strict";
import test from "node:test";

import { computeConfigHash, listBomItems, summarizeBom, validateBom } from "./oracle-bom.mjs";

function sampleBom() {
  const configs = [{
    label: "Example OKE",
    services: [{
      label: "Compute - Virtual Machine",
      items: [{ sku: "B000001", quantity: 2, unitPrice: 3, monthlyCost: 6 }],
    }],
  }];
  return {
    label: "Example BoM",
    timeFrame: { months: 1 },
    currency: "USD",
    meta: { exportVersion: 1, hash: computeConfigHash(configs) },
    configs,
  };
}

test("returns exact validated configuration and service references", () => {
  const bom = sampleBom();
  assert.equal(validateBom(bom), true);
  assert.equal(summarizeBom(bom).embeddedMonthlyCost, 6);
  assert.deepEqual(listBomItems(bom), [{
    configuration: "Example OKE",
    service: "Compute - Virtual Machine",
    sku: "B000001",
    quantity: 2,
    unitPrice: 3,
    monthlyCost: 6,
  }]);
});

test("refuses a BoM changed after its hash was computed", () => {
  const bom = sampleBom();
  bom.configs[0].services[0].items[0].monthlyCost = 7;
  assert.throws(() => validateBom(bom), /meta\.hash mismatch/);
});
