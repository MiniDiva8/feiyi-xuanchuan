import test from "node:test";
import assert from "node:assert/strict";
import { parseRoute, routeHash } from "../src/navigation.mjs";

test("a campaign deep link survives refresh without losing its identity", () => {
  assert.deepEqual(parseRoute("#/campaigns/abc-123"), {
    page: "studio",
    campaignId: "abc-123",
    create: false,
    workspaceId: "",
  });
  assert.equal(routeHash("studio", "abc-123"), "#/campaigns/abc-123");
});
test("new activity has a distinct route and channel pages are navigable", () => {
  assert.deepEqual(parseRoute("#/campaigns/new"), {
    page: "campaigns",
    campaignId: "",
    create: true,
    workspaceId: "",
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
      workspaceId: "",
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

test("campaign links retain their workspace across history and reload", () => {
  const hash = routeHash("studio", "second-campaign", "w2");
  assert.equal(hash, "#/workspaces/w2/campaigns/second-campaign");
  assert.equal(parseRoute(hash).workspaceId, "w2");
  assert.equal(parseRoute(hash).campaignId, "second-campaign");
});
test("scoped main pages and new activities keep the merchant identity", () => {
  for (const page of [
    "overview",
    "knowledge",
    "channels",
    "settings",
    "campaign-new",
  ]) {
    const route = parseRoute(routeHash(page, "", "w2"));
    assert.equal(route.workspaceId, "w2");
    assert.equal(route.create, page === "campaign-new");
  }
});
test("malformed merchant path segments cannot become workspace identifiers", () => {
  for (const hash of [
    "#/workspaces/%2F/overview",
    "#/workspaces/%E0%A4%A/overview",
    "#/workspaces//overview",
    "#/workspaces/%00/overview",
  ]) {
    assert.equal(parseRoute(hash).workspaceId || "", "");
    assert.equal(parseRoute(hash).page, "overview");
  }
});
