import { useEffect, useState } from "react";
import {
  Plus,
  ExternalLink,
  ClipboardCheck,
  ArrowUpRight,
  CheckCircle2,
} from "lucide-react";
import { useApp } from "../context";
import { useResource } from "../hooks";
import { post, request } from "../api";
import { canExport, latestVersion } from "../workflow.mjs";
import type { Publication, Campaign, Asset, Plan } from "../types";
import {
  Button,
  Panel,
  SectionTitle,
  Loading,
  Notice,
  Empty,
  Badge,
  Modal,
  Form,
  date,
} from "../components/UI";
export default function PublicationsPage() {
  const { path, epoch, refresh, notify, go } = useApp();
  const publications = useResource<Publication[]>(path("/publications"), epoch),
    campaigns = useResource<Campaign[]>(path("/campaigns"), epoch);
  const [selectedCampaign, setSelectedCampaign] = useState(""),
    [assets, setAssets] = useState<Asset[]>([]),
    [plans, setPlans] = useState<Plan[]>([]),
    [assetError, setAssetError] = useState(""),
    [resolvedCampaign, setResolvedCampaign] = useState(""),
    [assetLoading, setAssetLoading] = useState(false),
    [create, setCreate] = useState(false);
  const campaignId = selectedCampaign || campaigns.data?.[0]?.id || "";
  useEffect(() => {
    setAssets([]);
    setPlans([]);
    setResolvedCampaign("");
    setCreate(false);
    if (!campaignId) {
      setAssets([]);
      setPlans([]);
      return;
    }
    let active = true;
    setAssetLoading(true);
    setAssetError("");
    Promise.all([
      request<Asset[]>(path("/campaigns/" + campaignId + "/assets")),
      request<Plan[]>(path("/campaigns/" + campaignId + "/plans")),
    ])
      .then(([a, p]) => {
        if (active) {
          setAssets(a);
          setPlans(p);
          setResolvedCampaign(campaignId);
        }
      })
      .catch((e) => {
        if (active) {
          setAssets([]);
          setPlans([]);
          setResolvedCampaign("");
          setAssetError(e.message);
        }
      })
      .finally(() => {
        if (active) setAssetLoading(false);
      });
    return () => {
      active = false;
    };
  }, [campaignId, epoch]);
  const assetsReady =
    resolvedCampaign === campaignId && !assetLoading && !assetError;
  const latest = latestVersion(plans) as Plan | undefined;
  const publishable = assets.filter(
    (a) =>
      assetsReady &&
      a.campaign_id === campaignId &&
      canExport(
        a,
        assets.filter((s) => s.kind === a.kind && s.channel === a.channel),
      ) &&
      latest?.status === "approved" &&
      a.plan_id === latest.id,
  );
  return (
    <>
      <SectionTitle
        eyebrow="REVIEW & PUBLICATION / 审核与发布"
        title="审核与发布"
        description="先审核具体素材版本，再人工发布到渠道，最后登记真实作品链接与时间。"
        action={
          <Button
            disabled={!publishable.length || !assetsReady}
            onClick={() => setCreate(true)}
          >
            <Plus size={17} />
            登记已发布作品
          </Button>
        }
      />
      <Notice>
        当前为人工渠道发布。导出素材不等于发布成功；登记链接也不代表平台自动发布或已验证平台统计。
      </Notice>
      <div className="toolbar">
        <div>
          <label className="inline-label">
            活动筛选
            <select
              aria-label="选择发布活动"
              value={campaignId}
              onChange={(e) => {
                setCreate(false);
                setSelectedCampaign(e.target.value);
              }}
            >
              {!campaigns.data?.length && <option value="">暂无活动</option>}
              {campaigns.data?.map((c) => (
                <option value={c.id} key={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        {campaignId && (
          <Button variant="secondary" onClick={() => go("studio", campaignId)}>
            前往版本审核 <ArrowUpRight size={16} />
          </Button>
        )}
      </div>
      {assetError && <Notice tone="error">{assetError}</Notice>}
      <div className="two-stats">
        <div>
          <ClipboardCheck size={22} />
          <span>
            <strong>{assets.filter((a) => a.status === "draft").length}</strong>{" "}
            份待审核素材
          </span>
        </div>
        <div>
          <CheckCircle2 size={22} />
          <span>
            <strong>{publishable.length}</strong> 份当前可发布素材
          </span>
        </div>
      </div>
      <Panel title="发布档案" subtitle="作品、渠道与审批版本在同一条记录中追溯">
        {publications.loading ? (
          <Loading />
        ) : publications.error ? (
          <Notice tone="error">{publications.error}</Notice>
        ) : !publications.data?.filter(
            (p) => !campaignId || p.campaign_id === campaignId,
          ).length ? (
          <Empty
            title="发布之后，把真实链接留在这里"
            description="先在活动工作室批准最新素材，人工发布后回来登记。每条记录固定关联审核版本。"
            action={
              campaignId ? (
                <Button
                  variant="secondary"
                  onClick={() => go("studio", campaignId)}
                >
                  前往活动工作室 <ArrowUpRight size={15} />
                </Button>
              ) : (
                <Button variant="secondary" onClick={() => go("campaigns")}>
                  先创建活动
                </Button>
              )
            }
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>作品链接</th>
                  <th>渠道</th>
                  <th>发布时间</th>
                  <th>关联素材版本</th>
                  <th>记录</th>
                </tr>
              </thead>
              <tbody>
                {publications.data
                  .filter((p) => !campaignId || p.campaign_id === campaignId)
                  .map((p) => (
                    <tr key={p.id}>
                      <td>
                        <a
                          className="work-url"
                          href={p.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {p.url}
                          <ExternalLink size={13} />
                        </a>
                      </td>
                      <td>
                        <Badge>{p.channel}</Badge>
                      </td>
                      <td>{date(p.published_at)}</td>
                      <td>
                        {assets.find((a) => a.id === p.asset_id)?.title ||
                          p.asset_id.slice(0, 10)}
                        <small className="table-sub">
                          策划 {p.plan_id.slice(0, 8)} / 素材{" "}
                          {p.asset_id.slice(0, 8)}
                        </small>
                      </td>
                      <td>
                        <Badge tone="green">人工登记</Badge>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      {create && assetsReady && (
        <Modal title="登记真实发布作品" onClose={() => setCreate(false)} wide>
          <Form
            fields={[
              {
                key: "asset_id",
                label: "已批准的最新素材",
                type: "select",
                required: true,
                options: publishable.map((a) => ({
                  value: a.id,
                  label: a.channel + " / " + a.title + " / V" + a.version,
                })),
              },
              {
                key: "channel",
                label: "实际发布渠道",
                required: true,
                defaultValue: publishable[0]?.channel,
              },
              {
                key: "url",
                label: "真实作品链接",
                type: "url",
                required: true,
                placeholder: "https://...",
              },
              {
                key: "published_at",
                label: "实际发布时间",
                type: "datetime-local",
                required: true,
              },
              { key: "external_id", label: "平台作品 ID（可选）" },
            ]}
            onCancel={() => setCreate(false)}
            submitLabel="保存发布档案"
            onSubmit={async (d) => {
              if (
                !assetsReady ||
                !publishable.some(
                  (a) => a.id === d.asset_id && a.campaign_id === campaignId,
                )
              )
                throw new Error(
                  "活动素材已变化，请重新选择当前活动的已审核素材",
                );
              await post(path("/publications"), {
                ...d,
                published_at: new Date(d.published_at).toISOString(),
              });
              setCreate(false);
              refresh();
              notify("真实发布记录已保存");
            }}
          >
            <Notice>
              此操作只记录人工发布结果，不会代替你向任何渠道发送内容。
            </Notice>
          </Form>
        </Modal>
      )}
    </>
  );
}
