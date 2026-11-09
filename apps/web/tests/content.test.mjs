import test from "node:test";
import assert from "node:assert/strict";
import {
  bodyLines,
  evidenceEntries,
  groupChecks,
} from "../src/components/content.mjs";

test("body reading preserves all whitespace, CRLF, blank lines and markup literally", () => {
  for (const body of [
    "",
    "a",
    "\n",
    "  标题 \r\n\r\n正文\n\n尾行\r",
    "<script>alert(1)</script>\n\t最后一行  ",
    "\r\n\n\r",
    "  ",
  ]) {
    assert.equal(
      bodyLines(body)
        .map((line) => line.text + line.ending)
        .join(""),
      body,
    );
  }
  assert.deepEqual(bodyLines("甲\r\n\r\n乙\n"), [
    { text: "甲", ending: "\r\n" },
    { text: "", ending: "\r\n" },
    { text: "乙", ending: "\n" },
  ]);
  assert.deepEqual(bodyLines(""), []);
});

test("evidence presents nested fields with labels and keeps zero, false and missing distinct", () => {
  assert.deepEqual(
    evidenceEntries({
      date: "2026-11-08",
      stats: { impressions: 0, revenue: null },
      verified: false,
    }),
    [
      { label: "日期", value: "2026-11-08" },
      { label: "统计 / 曝光", value: "0" },
      { label: "统计 / 收入", value: "未提供" },
      { label: "verified", value: "否" },
    ],
  );
  assert.deepEqual(
    evidenceEntries({
      sources: ["商家台账", { unknown_key: "原始依据" }],
      note: "",
    }),
    [
      { label: "sources / 第 1 项", value: "商家台账" },
      { label: "sources / 第 2 项 / unknown_key", value: "原始依据" },
      { label: "说明", value: "空文本" },
    ],
  );
  assert.deepEqual(evidenceEntries({}), [{ label: "依据", value: "未提供" }]);
  assert.deepEqual(evidenceEntries("analytics.records=2"), [
    { label: "依据", value: "analytics.records=2" },
  ]);
});

test("check groups put errors first without dropping unknown levels or duplicate messages", () => {
  const checks = [
    { level: "info", message: "提示" },
    { level: "warning", message: "待确认" },
    { level: "error", message: "事实缺失" },
    { level: "custom-level", message: "原始说明" },
    { level: "error", message: "事实缺失" },
  ];
  const grouped = groupChecks(checks);
  assert.deepEqual(
    grouped.map((group) => group.level),
    ["error", "warning", "info", "custom-level"],
  );
  assert.equal(grouped[0].label, "需处理");
  assert.equal(grouped[3].label, "custom-level");
  assert.equal(grouped.flatMap((group) => group.checks).length, checks.length);
  assert.deepEqual(
    grouped[0].checks.map((check) => check.message),
    ["事实缺失", "事实缺失"],
  );
  assert.deepEqual(checks[0], { level: "info", message: "提示" });
});

test("unrecognized evidence keys and check levels remain safe literal labels", () => {
  assert.deepEqual(
    evidenceEntries(JSON.parse('{"constructor":0,"__proto__":false}')),
    [
      { label: "constructor", value: "0" },
      { label: "__proto__", value: "否" },
    ],
  );
  assert.equal(
    groupChecks([{ level: "__proto__", message: "保留核对信息" }])[0].label,
    "__proto__",
  );
});
