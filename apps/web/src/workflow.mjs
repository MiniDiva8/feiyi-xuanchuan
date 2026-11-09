export function latestVersion(items) {
  return [...items].sort((a, b) => b.version - a.version)[0];
}
export function canExport(asset, siblings) {
  return (
    asset.status === "approved" && latestVersion(siblings)?.id === asset.id
  );
}
export function metricTemplate(campaignId) {
  const q = (x) => '"' + String(x).replaceAll('"', '""') + '"';
  return (
    "\uFEFFcampaign_id,date,channel,source,external_id,attribution,impressions,interactions,orders,revenue,registrations,spend\n" +
    [
      q(campaignId),
      new Date().toISOString().slice(0, 10),
      "小红书",
      "平台后台",
      "",
      "unknown",
      0,
      0,
      0,
      0,
      0,
      0,
    ].join(",") +
    "\n"
  );
}
