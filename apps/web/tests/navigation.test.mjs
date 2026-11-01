import test from "node:test";
import assert from "node:assert/strict";
import { parseRoute, routeHash } from "../src/navigation.mjs";

test("a campaign deep link survives refresh without losing its identity", () => {
  assert.deepEqual(parseRoute("#/campaigns/abc-123"), {
    page: "studio",
    campaignId: "abc-123",
    create: false,
  });
  assert.equal(routeHash("studio", "abc-123"), "#/campaigns/abc-123");
});
test("new activity has a distinct route and channel pages are navigable", () => {
  assert.deepEqual(parseRoute("#/campaigns/new"), {
    page: "campaigns",
    campaignId: "",
    create: true,
  });
  assert.equal(routeHash("campaign-new"), "#/campaigns/new");
  assert.equal(parseRoute("#/channels").page, "channels");
});
test("unknown, malformed and extra-segment fragments safely open overview", () => {
  for (const hash of [
    "",
    "#/nope",
    "#/campaigns/%E0%A4%A",
    "#/campaigns/id/other",
    "#/settings/other",
  ]) {
    assert.deepEqual(parseRoute(hash), {
      page: "overview",
      campaignId: "",
      create: false,
    });
  }
});
test("every main page has a stable, reversible route", () => {
  for (const page of [
    "overview",
    "knowledge",
    "offerings",
    "campaigns",
    "publications",
    "analytics",
    "channels",
    "settings",
  ]) {
    assert.equal(parseRoute(routeHash(page)).page, page);
  }
});
