import { useState } from "react";
import {
  Plus,
  ArrowUpRight,
  ArrowLeft,
  Flag,
  CalendarDays,
  Coins,
  Users,
  Check,
  RefreshCw,
  Sparkles,
  Download,
  FileText,
  Image,
  Clapperboard,
  ExternalLink,
  BookOpen,
} from "lucide-react";
import { useApp } from "../context";
import PosterDesigner from "../components/PosterDesigner";
import VideoAnalysis from "../components/VideoAnalysis";
import ContentPreview, {
  ContentChecks,
  ContentEvidence,
} from "../components/ContentPreview";
import { useResource } from "../hooks";
import { post, patch, download, downloadPosterPng } from "../api";
import type { Campaign, Offering, Plan, Asset, Review, Audit } from "../types";
import { latestVersion, canExport } from "../workflow.mjs";
import {
  Button,
  Panel,
  SectionTitle,
  Loading,
  Notice,
  Empty,
  Badge,
  Status,
  Mode,
  Modal,
  Form,
  money,
  date,
  type Field,
} from "../components/UI";
function validateBrief(d: Record<string, any>, offerings: Offering[]) {
  if (d.end_date < d.start_date) throw new Error("结束日期不能早于开始日期");
  if (d.objective !== "awareness") {
    const offering = offerings.find((o) => o.id === d.offering_id);
    if (!offering)
      throw new Error(
        "产品销售或课程报名活动必须关联产品 / 课程，请先添加目录，或选择品牌认知目标",
      );
    if (offering.kind !== (d.objective === "sales" ? "product" : "course"))
      throw new Error("销售目标需关联手作产品，报名目标需关联体验课程");
    if (offering.quantity <= 0)
      throw new Error("关联产品需要有库存，体验课程需要有可报名名额");
  }
}
const objectives = {
  sales: "产品销售",
  registration: "课程报名",
  awareness: "品牌认知",
};
export function CampaignsPage({
  createInitially = false,
}: {
  createInitially?: boolean;
}) {
  const { path, epoch, notify, refresh, go } = useApp();
  const campaigns = useResource<Campaign[]>(path("/campaigns"), epoch),
    offerings = useResource<Offering[]>(path("/offerings"), epoch);
  const [create, setCreate] = useState(createInitially),
    [filter, setFilter] = useState("all");
  const fields: Field[] = [
    {
      key: "name",
      label: "活动名称",
      required: true,
      placeholder: "例如：周末的一堂传统手作课",
    },
    {
      key: "objective",
      label: "活动目标",
      type: "select",
      options: Object.entries(objectives).map(([value, label]) => ({
        value,
        label,
      })),
    },
    {
      key: "offering_id",
      label: "关联产品 / 课程",
      type: "select",
      options: [
        { value: "", label: "不关联（品牌认知活动）" },
        ...(offerings.data || []).map((o) => ({
          value: o.id,
          label: (o.kind === "course" ? "课程 / " : "产品 / ") + o.name,
        })),
      ],
    },
    {
      key: "audience",
      label: "目标人群",
      required: true,
      placeholder: "例如：本地对传统工艺感兴趣的年轻人",
    },
    { key: "start_date", label: "开始日期", type: "date", required: true },
    { key: "end_date", label: "结束日期", type: "date", required: true },
    {
      key: "budget",
      label: "计划预算（元）",
      type: "number",
      min: 0,
      step: "0.01",
      required: true,
    },
    {
      key: "channels",
      label: "计划渠道",
      required: true,
      placeholder: "小红书，微信公众号，抖音",
      help: "多个渠道用逗号分隔",
    },
    {
      key: "notes",
      label: "活动简报 / 约束",
      type: "textarea",
      placeholder: "核心卖点、素材限制、履约安排、希望避免的表述…",
    },
  ];
  return (
    <>
      <SectionTitle
        eyebrow="CAMPAIGN WORKSPACE / 营销活动"
        title="营销活动"
        description="从简报出发，完成策划、审核与发布，用真实数据为下一轮留下依据。"
        action={
          <Button onClick={() => setCreate(true)}>
            <Plus size={17} />
            创建营销活动
          </Button>
        }
      />
      <div className="tabs">
        {[
          { id: "all", name: "全部活动" },
          { id: "sales", name: "产品销售" },
          { id: "registration", name: "课程报名" },
          { id: "awareness", name: "品牌认知" },
        ].map((t) => (
          <button
            key={t.id}
            className={filter === t.id ? "active" : ""}
            onClick={() => setFilter(t.id)}
          >
            {t.name}
            {t.id === "all" && <span>{campaigns.data?.length || 0}</span>}
          </button>
        ))}
      </div>
      {campaigns.loading ? (
        <Loading />
      ) : campaigns.error ? (
        <Notice tone="error">{campaigns.error}</Notice>
      ) : !campaigns.data?.length ? (
        <Panel>
          <Empty
            title="从一个明确目标开始"
            description="一款产品的推广、一堂课程的招募，或者品牌的第一次自我介绍。"
            action={
              <Button variant="secondary" onClick={() => setCreate(true)}>
                <Plus size={16} />
                创建第一场活动
              </Button>
            }
          />
        </Panel>
      ) : (
        <div className="campaign-grid">
          {campaigns.data
            .filter((c) => filter === "all" || c.objective === filter)
            .map((c) => (
              <button
                className="campaign-card"
                key={c.id}
                onClick={() => go("studio", c.id)}
              >
                <header>
                  <span className="mini-icon">
                    <Flag size={20} />
                  </span>
                  <Badge tone="green">{objectives[c.objective]}</Badge>
                  <ArrowUpRight size={19} />
                </header>
                <h3>{c.name}</h3>
                <p>{c.audience}</p>
                <div className="campaign-dates">
                  <CalendarDays size={15} />
                  {c.start_date} — {c.end_date}
                </div>
                <footer>
                  <span>
                    计划预算 <strong>{money(c.budget)}</strong>
                  </span>
                  <Badge tone="neutral">
                    {c.status === "draft"
                      ? "活动草稿"
                      : c.status === "active"
                        ? "进行中"
                        : c.status}
                  </Badge>
                </footer>
                <div className="campaign-channels">
                  {c.channels.map((ch) => (
                    <Badge key={ch}>{ch}</Badge>
                  ))}
                </div>
              </button>
            ))}
        </div>
      )}
      {create && (
        <Modal
          title="创建营销活动"
          onClose={() => {
            setCreate(false);
            if (createInitially) go("campaigns");
          }}
          wide
        >
          <Form
            fields={fields}
            initial={{
              budget: 0,
              start_date: new Date().toISOString().slice(0, 10),
            }}
            submitLabel="创建并进入工作室"
            onCancel={() => {
              setCreate(false);
              if (createInitially) go("campaigns");
            }}
            onSubmit={async (d) => {
              validateBrief(d, offerings.data || []);
              const c = await post<Campaign>(path("/campaigns"), {
                ...d,
                offering_id: d.offering_id || null,
                channels: String(d.channels)
                  .split(/[,，、]/)
                  .map((s) => s.trim())
                  .filter(Boolean),
              });
              setCreate(false);
              refresh();
              notify("活动已创建，开始填写策划吧");
              go("studio", c.id);
            }}
          />
        </Modal>
      )}
    </>
  );
}
export function StudioPage({ id }: { id: string }) {
  const { path, epoch, notify, refresh, go } = useApp();
  const offerings = useResource<Offering[]>(path("/offerings"), epoch);
  const audit = useResource<Audit[]>(path("/audit"), epoch);
  const rejectionReason = (entityId: string) =>
    [...(audit.data || [])]
      .filter((a) => a.entity_id === entityId && a.action === "reject")
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .map((a) => a.details?.reason)
      .find(Boolean);
  const campaign = useResource<Campaign>(path("/campaigns/" + id), epoch),
    plans = useResource<Plan[]>(path("/campaigns/" + id + "/plans"), epoch),
    assets = useResource<Asset[]>(path("/campaigns/" + id + "/assets"), epoch),
    reviews = useResource<Review[]>(
      path("/campaigns/" + id + "/reviews"),
      epoch,
    );
  const [tab, setTab] = useState("plan"),
    [modal, setModal] = useState(""),
    [selectedPlan, setSelectedPlan] = useState(""),
    [selectedAsset, setSelectedAsset] = useState<Asset | null>(null),
    [busy, setBusy] = useState("");
  const latest = latestVersion(plans.data || []) as Plan | undefined;
  const current = plans.data?.find((p) => p.id === selectedPlan) || latest;
  const approved = latest?.status === "approved";
  const c = campaign.data;
  async function action(
    key: string,
    fn: () => Promise<unknown>,
    message: string,
  ) {
    setBusy(key);
    try {
      await fn();
      refresh();
      notify(message);
    } catch (e) {
      notify((e as Error).message, "error");
    } finally {
      setBusy("");
    }
  }
  if (campaign.loading) return <Loading />;
  if (campaign.error || !c)
    return <Notice tone="error">{campaign.error}</Notice>;
  return (
    <>
      <button className="back-link" onClick={() => go("campaigns")}>
        <ArrowLeft size={15} />
        返回营销活动
      </button>
      <SectionTitle
        eyebrow="CAMPAIGN STUDIO / 活动工作室"
        title={c.name}
        description={
          c.notes || "围绕真实资料，为这次活动打磨一套可执行的传播方案。"
        }
        action={
          <div className="inline">
            <Badge tone="green">{objectives[c.objective]}</Badge>
            <Button variant="secondary" onClick={() => setModal("brief-edit")}>
              编辑活动简报
            </Button>
          </div>
        }
      />
      <div className="brief-strip">
        <span>
          <Users size={17} />
          {c.audience}
        </span>
        <span>
          <CalendarDays size={17} />
          {c.start_date} — {c.end_date}
        </span>
        <span>
          <Coins size={17} />
          预算 {money(c.budget)}
        </span>
        <span>{c.channels.join(" / ")}</span>
      </div>
      <div className="content-studio-context" aria-label="活动版本上下文">
        <div>
          <span>最新策划</span>
          <strong>
            {plans.loading
              ? "读取中…"
              : plans.error
                ? "读取失败"
                : latest
                  ? `V${latest.version}`
                  : "尚未生成"}
          </strong>
          {latest && <Status value={latest.status} />}
        </div>
        <p>策划确认后生成素材；编辑后保存新版本，再审核导出。</p>
      </div>
      <div className="tabs">
        <button
          className={tab === "plan" ? "active" : ""}
          aria-pressed={tab === "plan"}
          onClick={() => setTab("plan")}
        >
          活动策划<span>{plans.data?.length || 0}</span>
        </button>
        <button
          className={tab === "assets" ? "active" : ""}
          aria-pressed={tab === "assets"}
          onClick={() => setTab("assets")}
        >
          传播素材<span>{assets.data?.length || 0}</span>
        </button>
        <button
          className={tab === "video" ? "active" : ""}
          aria-pressed={tab === "video"}
          onClick={() => setTab("video")}
        >
          视频分析
        </button>
        <button
          className={tab === "review" ? "active" : ""}
          aria-pressed={tab === "review"}
          onClick={() => setTab("review")}
        >
          复盘与下一轮
        </button>
      </div>
      {tab === "video" && <VideoAnalysis campaignId={id} />}
      {tab === "plan" && (
        <>
          {plans.loading ? (
            <Loading />
          ) : plans.error ? (
            <Notice tone="error">{plans.error}</Notice>
          ) : !current ? (
            <Panel>
              <Empty
                title="把活动简报，变成执行方案"
                description="将引用本商家已确认的营销资料；未配置模型时会明确生成模板草稿。"
                action={
                  <Button onClick={() => setModal("plan-generate")}>
                    <Sparkles size={16} />
                    生成策划草稿
                  </Button>
                }
              />
            </Panel>
          ) : (
            <div className="studio-columns">
              <div>
                <Panel
                  title={current.content.theme}
                  subtitle={
                    "策划 V" +
                    current.version +
                    " · " +
                    date(current.created_at)
                  }
                  action={
                    <div className="inline">
                      <Mode value={current.generation_mode} />
                      <Status value={current.status} />
                    </div>
                  }
                >
                  <div className="plan-content">
                    {current.status === "rejected" && (
                      <Notice tone="error">
                        审核退回：
                        {String(
                          rejectionReason(current.id) ||
                            (audit.loading
                              ? "正在读取审核意见…"
                              : audit.error
                                ? "审核意见读取失败，请稍后重试或查看操作审计"
                                : "未记录具体原因，请查看操作审计"),
                        )}
                      </Notice>
                    )}
                    <p className="plan-summary">{current.content.summary}</p>
                    <div className="plan-block">
                      <span className="eyebrow">目标人群</span>
                      <p>{current.content.audience}</p>
                    </div>
                    <div className="plan-block">
                      <h3>渠道与内容方向</h3>
                      <div className="channel-plans">
                        {current.content.channels?.map((ch, i) => (
                          <div key={i}>
                            <strong>{ch.channel}</strong>
                            <p>{ch.reason}</p>
                            <ul>
                              {ch.content_ideas?.map((s, j) => (
                                <li key={j}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="plan-block">
                      <h3>执行节奏</h3>
                      <div className="schedule">
                        {current.content.schedule?.map((s, i) => (
                          <div key={i}>
                            <span>{s.day}</span>
                            <div>
                              <strong>{s.action}</strong>
                              <small>{s.channel}</small>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="plan-block">
                      <h3>预算建议</h3>
                      {current.content.budget?.map((b, i) => (
                        <div className="budget-row" key={i}>
                          <span>{b.item}</span>
                          <strong>{money(b.amount)}</strong>
                        </div>
                      ))}
                    </div>
                    {current.content.warnings?.map((w, i) => (
                      <Notice key={i}>{w}</Notice>
                    ))}
                  </div>
                </Panel>
              </div>
              <aside className="studio-aside">
                <Panel title="版本与商家确认">
                  <div className="version-select">
                    <label>
                      查看策划版本
                      <select
                        value={current.id}
                        onChange={(e) => setSelectedPlan(e.target.value)}
                      >
                        {[...(plans.data || [])]
                          .sort((a, b) => b.version - a.version)
                          .map((p) => (
                            <option key={p.id} value={p.id}>
                              V{p.version} ·{" "}
                              {p.status === "approved"
                                ? "已批准"
                                : p.status === "rejected"
                                  ? "已退回"
                                  : "待审核"}
                            </option>
                          ))}
                      </select>
                    </label>
                  </div>
                  <div className="aside-actions">
                    {current.id !== latest?.id && (
                      <Notice>
                        当前为历史版本，仅最新版本可以进入后续流程。
                      </Notice>
                    )}
                    <Button
                      busy={busy === "approve-plan"}
                      disabled={
                        current.status !== "draft" || current.id !== latest?.id
                      }
                      onClick={() =>
                        action(
                          "approve-plan",
                          () => post(path("/plans/" + current.id + "/approve")),
                          "策划版本已批准",
                        )
                      }
                    >
                      <Check size={16} />
                      批准此版本
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => setModal("plan-revise")}
                    >
                      <RefreshCw size={15} />
                      修订为新版本
                    </Button>
                    <Button
                      variant="ghost danger"
                      disabled={current.status !== "draft"}
                      onClick={() => setModal("plan-reject")}
                    >
                      退回并填写原因
                    </Button>
                    <small>
                      确认具体版本后才可生成素材。修改将产生新版本，必须重新审核。
                    </small>
                  </div>
                </Panel>
                <Panel title="引用依据" subtitle="来源事实与策划建议分开核验">
                  <div className="evidence-list">
                    {current.content.evidence?.length ? (
                      current.content.evidence.map((e, i) => (
                        <div key={i}>
                          <BookOpen size={16} />
                          <div>
                            <strong>{e.title}</strong>
                            <p>{e.source}</p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <Notice>
                        暂无已确认的来源资料；当前为公共模板建议，请先补充知识库。
                      </Notice>
                    )}
                  </div>
                  <button
                    className="text-button evidence-link"
                    onClick={() => go("knowledge")}
                  >
                    前往知识库核验 <ArrowUpRight size={15} />
                  </button>
                </Panel>
              </aside>
            </div>
          )}
        </>
      )}
      {tab === "assets" && (
        <>
          <div className="toolbar">
            <p>每次修订保留旧版本。仅最新、已批准且来源有效的素材可以导出。</p>
            <Button
              disabled={!approved}
              onClick={() => setModal("asset-generate")}
            >
              <Sparkles size={16} />
              生成传播素材
            </Button>
          </div>
          {!approved && <Notice>请先批准最新策划版本，再生成本轮素材。</Notice>}
          {assets.loading ? (
            <Loading />
          ) : assets.error ? (
            <Notice tone="error">{assets.error}</Notice>
          ) : !assets.data?.length ? (
            <Panel>
              <Empty
                title="为不同渠道，打磨合适的表达"
                description="支持文案、海报和短视频脚本。生成后逐份审核，再导出用于真实发布。"
                action={
                  <Button
                    disabled={!approved}
                    onClick={() => setModal("asset-generate")}
                  >
                    <Plus size={16} />
                    生成第一份素材
                  </Button>
                }
              />
            </Panel>
          ) : (
            <div className="asset-grid content-review-list">
              {[...(assets.data || [])]
                .sort((a, b) => b.version - a.version)
                .map((a) => {
                  const exportable =
                    canExport(
                      a,
                      (assets.data || []).filter(
                        (s) => s.channel === a.channel && s.kind === a.kind,
                      ),
                    ) &&
                    a.plan_id === latest?.id &&
                    approved;
                  return (
                    <Panel
                      key={a.id}
                      className="asset-card content-review-card"
                    >
                      <header className="asset-header">
                        <span className="resource-icon">
                          {a.kind === "poster" ? (
                            <Image size={20} />
                          ) : a.kind === "script" ? (
                            <Clapperboard size={20} />
                          ) : (
                            <FileText size={20} />
                          )}
                        </span>
                        <div>
                          <strong>{a.title}</strong>
                          <small>
                            {a.channel} ·{" "}
                            {
                              {
                                copy: "文案",
                                poster: "海报",
                                script: "短视频脚本",
                              }[a.kind]
                            }{" "}
                            · V{a.version}
                          </small>
                        </div>
                        <Status value={a.status} />
                      </header>
                      <div className="content-review-layout">
                        <div className="content-review-main">
                          <ContentPreview body={a.body} kind={a.kind} />
                        </div>
                        <aside
                          className="content-review-sidebar"
                          aria-label={`素材 V${a.version} 核对与审核`}
                        >
                          <div className="content-review-version">
                            <strong>素材 V{a.version}</strong>
                            <span>
                              {a.plan_id === latest?.id
                                ? "关联最新策划"
                                : "关联历史策划"}
                            </span>
                          </div>
                          <div className="asset-checks">
                            {a.status === "rejected" && (
                              <Notice tone="error">
                                审核退回：
                                {String(
                                  rejectionReason(a.id) ||
                                    (audit.loading
                                      ? "正在读取审核意见…"
                                      : audit.error
                                        ? "审核意见读取失败，请稍后重试或查看操作审计"
                                        : "未记录具体原因，请查看操作审计"),
                                )}
                              </Notice>
                            )}
                            <Mode value={a.generation_mode} />
                            <ContentChecks checks={a.checks || []} />
                          </div>
                          <footer className="asset-actions">
                            {a.kind === "poster" && (
                              <PosterDesigner asset={a} />
                            )}
                            <Button
                              variant="secondary small"
                              onClick={() => {
                                setSelectedAsset(a);
                                setModal("asset-revise");
                              }}
                            >
                              编辑新版本
                            </Button>
                            <Button
                              variant="secondary small"
                              disabled={
                                a.status !== "draft" ||
                                a.plan_id !== latest?.id ||
                                !canExport(
                                  { ...a, status: "approved" },
                                  (assets.data || [])
                                    .filter(
                                      (s) =>
                                        s.channel === a.channel &&
                                        s.kind === a.kind,
                                    )
                                    .map((s) =>
                                      s.id === a.id
                                        ? { ...s, status: "approved" }
                                        : s,
                                    ),
                                )
                              }
                              busy={busy === a.id}
                              onClick={() =>
                                action(
                                  a.id,
                                  () =>
                                    post(path("/assets/" + a.id + "/approve")),
                                  "素材版本已批准",
                                )
                              }
                            >
                              批准
                            </Button>
                            <Button
                              variant="ghost small"
                              disabled={a.status !== "draft"}
                              onClick={() => {
                                setSelectedAsset(a);
                                setModal("asset-reject");
                              }}
                            >
                              退回
                            </Button>
                            <div className="export-buttons">
                              <Button
                                variant="small"
                                disabled={!exportable}
                                onClick={() =>
                                  action(
                                    "export",
                                    () =>
                                      download(
                                        path(
                                          "/assets/" +
                                            a.id +
                                            "/export?format=txt",
                                        ),
                                        a.title + ".txt",
                                      ),
                                    "已导出文案",
                                  )
                                }
                              >
                                <Download size={14} />
                                TXT
                              </Button>
                              {a.kind === "poster" ? (
                                <>
                                  <Button
                                    variant="secondary small"
                                    disabled={!exportable}
                                    onClick={() =>
                                      action(
                                        "export",
                                        () =>
                                          download(
                                            path(
                                              "/assets/" +
                                                a.id +
                                                "/export?format=svg",
                                            ),
                                            a.title + ".svg",
                                          ),
                                        "已导出 SVG",
                                      )
                                    }
                                  >
                                    SVG
                                  </Button>
                                  <Button
                                    variant="secondary small"
                                    disabled={!exportable}
                                    onClick={() =>
                                      action(
                                        "export",
                                        () =>
                                          downloadPosterPng(
                                            path(
                                              "/assets/" +
                                                a.id +
                                                "/export?format=svg",
                                            ),
                                            a.title + ".png",
                                          ),
                                        "已导出 PNG",
                                      )
                                    }
                                  >
                                    PNG
                                  </Button>
                                </>
                              ) : (
                                <Button
                                  variant="secondary small"
                                  disabled={!exportable}
                                  onClick={() =>
                                    action(
                                      "export",
                                      () =>
                                        download(
                                          path(
                                            "/assets/" +
                                              a.id +
                                              "/export?format=html",
                                          ),
                                          a.title + ".html",
                                        ),
                                      "已导出 HTML",
                                    )
                                  }
                                >
                                  HTML
                                </Button>
                              )}
                              <button
                                className="text-button"
                                disabled={!exportable}
                                onClick={() => go("publications")}
                              >
                                登记发布 <ExternalLink size={13} />
                              </button>
                            </div>
                          </footer>
                        </aside>
                      </div>
                    </Panel>
                  );
                })}
            </div>
          )}
        </>
      )}
      {tab === "review" && (
        <>
          <div className="toolbar">
            <p>复盘依据已录入的真实指标。缺失归因、成本和样本将明确提示。</p>
            <div className="inline">
              <Button variant="secondary" onClick={() => go("analytics")}>
                录入指标
              </Button>
              <Button
                busy={busy === "review"}
                onClick={() =>
                  action(
                    "review",
                    () => post(path("/campaigns/" + id + "/reviews/generate")),
                    "复盘已生成",
                  )
                }
              >
                <Sparkles size={16} />
                生成复盘
              </Button>
            </div>
          </div>
          {reviews.loading ? (
            <Loading />
          ) : reviews.error ? (
            <Notice tone="error">{reviews.error}</Notice>
          ) : !reviews.data?.length ? (
            <Panel>
              <Empty
                title="让每一轮活动，留下可验证的经验"
                description="先录入曝光、互动、成交或报名指标，再生成区分事实与推测的复盘。"
              />
            </Panel>
          ) : (
            <>
              {[...reviews.data].reverse().map((r) => (
                <Panel
                  key={r.id}
                  title={"活动复盘 · " + date(r.created_at)}
                  action={<Mode value={r.generation_mode} />}
                >
                  <ReviewContent review={r} />
                </Panel>
              ))}
              <Panel
                title="带着经验，开始下一轮"
                subtitle="复制活动简报为新活动，策划、素材与审批从新版本开始。"
              >
                <div className="panel-pad">
                  <Button
                    busy={busy === "next"}
                    onClick={() =>
                      action(
                        "next",
                        async () => {
                          const next = await post<Campaign>(
                            path("/campaigns/" + id + "/next-round"),
                          );
                          go("studio", next.id);
                        },
                        "下一轮活动已创建",
                      )
                    }
                  >
                    创建下一轮活动 <ArrowUpRight size={16} />
                  </Button>
                </div>
              </Panel>
            </>
          )}
        </>
      )}
      {modal && (
        <Modal
          title={
            {
              "brief-edit": "编辑活动简报",
              "plan-generate": "生成策划草稿",
              "plan-revise": "修订策划 · 创建新版本",
              "plan-reject": "退回策划",
              "asset-generate": "生成传播素材",
              "asset-revise": "编辑素材 · 创建新版本",
              "asset-reject": "退回素材",
            }[modal] || ""
          }
          onClose={() => setModal("")}
          wide
        >
          <Form
            fields={
              modal === "brief-edit"
                ? [
                    { key: "name", label: "活动名称", required: true },
                    {
                      key: "objective",
                      label: "活动目标",
                      type: "select",
                      options: Object.entries(objectives).map(
                        ([value, label]) => ({ value, label }),
                      ),
                    },
                    {
                      key: "offering_id",
                      label: "关联产品 / 课程",
                      type: "select",
                      options: [
                        { value: "", label: "不关联（品牌认知活动）" },
                        ...(offerings.data || []).map((o) => ({
                          value: o.id,
                          label:
                            (o.kind === "course" ? "课程 / " : "产品 / ") +
                            o.name,
                        })),
                      ],
                    },
                    { key: "audience", label: "目标人群", required: true },
                    {
                      key: "start_date",
                      label: "开始日期",
                      type: "date",
                      required: true,
                    },
                    {
                      key: "end_date",
                      label: "结束日期",
                      type: "date",
                      required: true,
                    },
                    {
                      key: "budget",
                      label: "计划预算（元）",
                      type: "number",
                      min: 0,
                      step: "0.01",
                      required: true,
                    },
                    {
                      key: "channels",
                      label: "计划渠道",
                      required: true,
                      help: "多个渠道用逗号分隔",
                    },
                    {
                      key: "notes",
                      label: "活动简报 / 约束",
                      type: "textarea",
                    },
                  ]
                : modal === "asset-generate"
                  ? [
                      {
                        key: "channel",
                        label: "发布渠道",
                        type: "select",
                        options: c.channels.map((ch) => ({
                          value: ch,
                          label: ch,
                        })),
                      },
                      {
                        key: "kind",
                        label: "素材类型",
                        type: "select",
                        options: [
                          { value: "copy", label: "图文文案" },
                          { value: "poster", label: "宣传海报" },
                          { value: "script", label: "短视频脚本" },
                        ],
                      },
                      {
                        key: "instructions",
                        label: "表达要求",
                        type: "textarea",
                        placeholder: "期望的语气、篇幅、内容重点…",
                      },
                    ]
                  : modal === "asset-revise"
                    ? [
                        { key: "title", label: "标题", required: true },
                        {
                          key: "body",
                          label: "素材正文",
                          type: "textarea",
                          required: true,
                        },
                      ]
                    : modal.includes("reject")
                      ? [
                          {
                            key: "reason",
                            label: "退回原因",
                            type: "textarea",
                            required: true,
                            placeholder: "具体指出需要核验或修改的内容",
                          },
                        ]
                      : [
                          {
                            key: "instructions",
                            label:
                              modal === "plan-revise"
                                ? "修订要求"
                                : "补充要求（可选）",
                            type: "textarea",
                            required: modal === "plan-revise",
                            placeholder:
                              "例如：优先本地到店客群，压缩渠道数量，保留工艺来源引用",
                          },
                        ]
            }
            initial={
              modal === "brief-edit"
                ? {
                    ...c,
                    offering_id: c.offering_id || "",
                    channels: c.channels.join("，"),
                  }
                : modal === "asset-revise"
                  ? { title: selectedAsset?.title, body: selectedAsset?.body }
                  : {}
            }
            submitLabel={
              modal === "brief-edit"
                ? "保存活动简报"
                : modal.includes("reject")
                  ? "确认退回"
                  : modal.includes("revise")
                    ? "保存为新版本"
                    : "生成草稿"
            }
            onCancel={() => setModal("")}
            onSubmit={async (d) => {
              if (modal === "brief-edit") {
                validateBrief(d, offerings.data || []);
                await patch(path("/campaigns/" + id), {
                  ...d,
                  offering_id: d.offering_id || null,
                  channels: String(d.channels)
                    .split(/[,，、]/)
                    .map((s) => s.trim())
                    .filter(Boolean),
                });
              }
              if (modal === "plan-generate")
                await post(path("/campaigns/" + id + "/plans/generate"), d);
              if (modal === "plan-revise") {
                const p = await post<Plan>(
                  path("/plans/" + current!.id + "/revise"),
                  d,
                );
                setSelectedPlan(p.id);
              }
              if (modal === "plan-reject")
                await post(path("/plans/" + current!.id + "/reject"), d);
              if (modal === "asset-generate")
                await post(path("/campaigns/" + id + "/assets/generate"), {
                  ...d,
                  plan_id: latest!.id,
                });
              if (modal === "asset-revise")
                await post(path("/assets/" + selectedAsset!.id + "/revise"), d);
              if (modal === "asset-reject")
                await post(path("/assets/" + selectedAsset!.id + "/reject"), d);
              setModal("");
              refresh();
              notify("操作完成，版本已保存");
            }}
          >
            <Notice>
              {modal === "brief-edit"
                ? "修改活动目标、预算、时间或关联产品后，原方案与素材需要重新生成、审核。"
                : ""}
              未配置模型时生成模板草稿；配置模型后如调用失败，将显示错误，不会伪装成
              AI 成功。
            </Notice>
          </Form>
        </Modal>
      )}
    </>
  );
}
export function ReviewContent({ review: r }: { review: Review }) {
  return (
    <div className="review-content content-review-summary">
      <div>
        <h3>
          <Badge tone="green">观察事实</Badge>有记录的数据
        </h3>
        {r.content.facts?.map((f, i) => (
          <article key={i}>
            <strong>{f.statement}</strong>
            <ContentEvidence value={f.evidence} />
          </article>
        ))}
      </div>
      <div>
        <h3>
          <Badge tone="ochre">原因假设</Badge>仍需验证
        </h3>
        {r.content.hypotheses?.map((h, i) => (
          <article key={i}>
            <strong>{h.statement}</strong>
            <p>验证方式：{h.validation}</p>
          </article>
        ))}
      </div>
      <div>
        <h3>下一步调整建议</h3>
        {r.content.suggestions?.map((s, i) => (
          <article key={i}>
            <strong>{s.action}</strong>
            <p>观察指标：{s.metric}</p>
          </article>
        ))}
      </div>
      <div>
        <h3>数据与结论边界</h3>
        {r.content.limitations?.map((l, i) => (
          <Notice key={i}>{l}</Notice>
        ))}
      </div>
    </div>
  );
}
