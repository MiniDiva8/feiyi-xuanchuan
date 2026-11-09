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
const home = (workspaceId = "") => ({
  page: "overview",
  campaignId: "",
  create: false,
  workspaceId,
});
function decodeSegment(value) {
  try {
    const decoded = decodeURIComponent(value || "");
    return decoded && !/[\/\\\x00-\x1f]/.test(decoded) ? decoded : "";
  } catch {
    return "";
  }
}
export function parseRoute(hash = "") {
  let parts = String(hash).replace(/^#\/?/, "").split("/");
  let workspaceId = "";
  if (parts[0] === "workspaces") {
    workspaceId = decodeSegment(parts[1]);
    if (!workspaceId) return home();
    parts = parts.slice(2);
  }
  if (parts.length === 1 && pages.has(parts[0]))
    return { ...home(workspaceId), page: parts[0] };
  if (parts.length === 2 && parts[0] === "campaigns" && parts[1]) {
    if (parts[1] === "new")
      return { ...home(workspaceId), page: "campaigns", create: true };
    const id = decodeSegment(parts[1]);
    if (id) return { ...home(workspaceId), page: "studio", campaignId: id };
  }
  return home(workspaceId);
}
export function routeHash(page, id = "", workspaceId = "") {
  let path = pages.has(page) ? page : "overview";
  if (page === "studio" && id) path = "campaigns/" + encodeURIComponent(id);
  if (page === "campaign-new") path = "campaigns/new";
  return (
    "#/" +
    (workspaceId ? "workspaces/" + encodeURIComponent(workspaceId) + "/" : "") +
    path
  );
}
