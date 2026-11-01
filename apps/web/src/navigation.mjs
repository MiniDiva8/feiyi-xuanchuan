const pages = new Set([
  "overview",
  "knowledge",
  "offerings",
  "campaigns",
  "publications",
  "analytics",
  "channels",
  "settings",
]);
const home = () => ({ page: "overview", campaignId: "", create: false });
export function parseRoute(hash = "") {
  try {
    const parts = String(hash).replace(/^#\/?/, "").split("/");
    if (parts.length === 1 && pages.has(parts[0]))
      return { page: parts[0], campaignId: "", create: false };
    if (parts.length === 2 && parts[0] === "campaigns" && parts[1]) {
      if (parts[1] === "new")
        return { page: "campaigns", campaignId: "", create: true };
      const id = decodeURIComponent(parts[1]);
      if (!id || /[\/\\\x00-\x1f]/.test(id)) return home();
      return { page: "studio", campaignId: id, create: false };
    }
  } catch {}
  return home();
}
export function routeHash(page, id = "") {
  if (page === "studio" && id) return "#/campaigns/" + encodeURIComponent(id);
  if (page === "campaign-new") return "#/campaigns/new";
  return "#/" + (pages.has(page) ? page : "overview");
}
