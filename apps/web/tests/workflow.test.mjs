import test from "node:test";
import assert from "node:assert/strict";
import { latestVersion, canExport, metricTemplate } from "../src/workflow.mjs";
test("an old approved asset cannot be exported after a new draft revision", () => {
  const a = { id: "old", version: 1, status: "approved" };
  const b = { id: "new", version: 2, status: "draft" };
  assert.equal(canExport(a, [a, b]), false);
  assert.equal(canExport(b, [a, b]), false);
  assert.equal(
    canExport({ ...b, status: "approved" }, [a, { ...b, status: "approved" }]),
    true,
  );
});
test("versions are selected numerically and empty lists are safe", () => {
  assert.equal(latestVersion([]), undefined);
  assert.equal(
    latestVersion([
      { id: "v2", version: 2 },
      { id: "v10", version: 10 },
    ]).id,
    "v10",
  );
});
test("CSV template quotes identifiers containing commas and distinguishes unknown attribution", () => {
  const s = metricTemplate("a,b");
  assert.ok(s.includes('"a,b"'));
  assert.ok(s.includes("unknown"));
  assert.ok(s.includes("campaign_id"));
});
