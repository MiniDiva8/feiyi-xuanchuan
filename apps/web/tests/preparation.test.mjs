import test from "node:test";
import assert from "node:assert/strict";
import { preparation } from "../src/preparation.mjs";

test("unconfirmed and private knowledge cannot count as marketing preparation", () => {
  assert.deepEqual(preparation([
    { confirmed: false, usage_scope: "marketing" },
    { confirmed: true, usage_scope: "internal" },
    { confirmed: true, usage_scope: "marketing" },
  ], []), { confirmed: 1, available: 0 });
});
test("a sale or booking needs positive availability and a real web link", () => {
  const item = { kind: "course", quantity: 5, conversion_url: "https://example.org/book" };
  assert.equal(preparation([], [item, { ...item, kind: "product" }]).available, 2);
  for (const invalid of [
    { quantity: 0 }, { quantity: -1 }, { conversion_url: "" },
    { conversion_url: "javascript:alert(1)" }, { conversion_url: "/book" },
    { conversion_url: "not a url" }, { kind: "unknown" },
  ]) assert.equal(preparation([], [{ ...item, ...invalid }]).available, 0);
});
test("empty or changed workspace inputs do not retain previous preparation", () => {
  const previous = preparation([{ confirmed: true, usage_scope: "marketing" }], []);
  assert.equal(previous.confirmed, 1);
  assert.deepEqual(preparation([], []), { confirmed: 0, available: 0 });
});
