/** Split for reading without normalizing, trimming or losing a single character. */
export function bodyLines(body) {
  return (body.match(/[^\r\n]*(?:\r\n|\r|\n|$)/g) || [])
    .filter((part) => part !== "")
    .map((part) => {
      const ending = part.match(/(?:\r\n|\r|\n)$/)?.[0] || "";
      return { text: ending ? part.slice(0, -ending.length) : part, ending };
    });
}

const evidenceLabels = {
  date: "日期",
  stats: "统计",
  impressions: "曝光",
  revenue: "收入",
  spend: "花费",
  orders: "订单",
  registrations: "报名",
  source: "来源",
  channel: "渠道",
  records: "记录数",
  note: "说明",
  before: "前值",
  after: "后值",
  delta: "变化",
  previous_date: "前次日期",
  latest_date: "最近日期",
  start_date: "开始日期",
  end_date: "结束日期",
  metric: "指标",
  value: "数值",
};

/** Flatten JSON evidence into readable labelled entries; unknown keys remain visible. */
export function evidenceEntries(value) {
  const entries = [];
  function visit(item, path) {
    if (item !== null && typeof item === "object") {
      const children = Array.isArray(item)
        ? item.map((child, index) => [`第 ${index + 1} 项`, child])
        : Object.entries(item).map(([key, child]) => [
            Object.hasOwn(evidenceLabels, key) ? evidenceLabels[key] : key,
            child,
          ]);
      if (children.length) {
        for (const [label, child] of children) visit(child, [...path, label]);
        return;
      }
    }
    let text;
    if (item == null || typeof item === "object") text = "未提供";
    else if (typeof item === "boolean") text = item ? "是" : "否";
    else if (item === "") text = "空文本";
    else text = String(item);
    entries.push({ label: path.join(" / ") || "依据", value: text });
  }
  visit(value, []);
  return entries;
}

/** Preserve full messages and unknown levels while bringing errors into view first. */
export function groupChecks(checks) {
  const labels = { error: "需处理", warning: "待核对", info: "提示" };
  const groups = new Map();
  for (const check of checks) {
    const level = check.level;
    if (!groups.has(level))
      groups.set(level, {
        level,
        label: Object.hasOwn(labels, level)
          ? labels[level]
          : level || "未标级别",
        checks: [],
      });
    groups.get(level).checks.push(check);
  }
  const priority = ["error", "warning", "info"];
  const rank = (level) =>
    priority.includes(level) ? priority.indexOf(level) : priority.length;
  return [...groups.values()].sort((a, b) => rank(a.level) - rank(b.level));
}
