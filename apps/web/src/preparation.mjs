// Preparation is guidance, never an authorization or approval decision.
export function preparation(knowledge, offerings) {
  const confirmed = knowledge.filter(
    (item) => item.confirmed && item.usage_scope === "marketing",
  ).length;
  const available = offerings.filter((item) => {
    if (!["product", "course"].includes(item.kind) || !(item.quantity > 0)) return false;
    try {
      const url = new URL(item.conversion_url);
      return ["http:", "https:"].includes(url.protocol) && Boolean(url.hostname);
    } catch {
      return false;
    }
  }).length;
  return { confirmed, available };
}
