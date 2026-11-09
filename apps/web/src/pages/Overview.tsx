import {
  ArrowUpRight,
  ArrowRight,
  Plus,
  BookOpen,
  Flag,
  ClipboardCheck,
  ChartNoAxesCombined,
  Package,
  Leaf,
  Coins,
  Eye,
  ShoppingBag,
  Users,
} from "lucide-react";
import { useApp } from "../context";
import { useResource } from "../hooks";
import type { Overview } from "../types";
import {
  Badge,
  Button,
  Panel,
  SectionTitle,
  Loading,
  Notice,
  Empty,
  Status,
  num,
  money,
  date,
} from "../components/UI";
export default function OverviewPage() {
  const { path, workspace, epoch, go } = useApp();
  const { data, loading, error } = useResource<Overview>(
    path("/overview"),
    epoch,
  );
  if (loading) return <Loading />;
  if (error || !data) return <Notice tone="error">{error}</Notice>;
  const stats = data.stats;
  const metrics = [
    {
      label: "累计曝光",
      value: num(stats.impressions),
      icon: Eye,
      note: "来自已录入的渠道数据",
    },
    {
      label: "成交金额",
      value: money(stats.revenue),
      icon: Coins,
      note: "录入金额，非利润或增量贡献",
    },
    {
      label: "产品订单",
      value: num(stats.orders),
      icon: ShoppingBag,
      note: "各渠道录入订单合计",
    },
    {
      label: "课程报名",
      value: num(stats.registrations),
      icon: Users,
      note: "各渠道录入报名合计",
    },
  ];
  return (
    <>
      <SectionTitle
        eyebrow="BUSINESS OVERVIEW / 经营概览"
        title={workspace.name + "，今天也让好手艺被看见。"}
        description="从文化资料到下一次传播，把经营的每一步留在这里。"
        action={
          <Button onClick={() => go("campaigns")}>
            <Plus size={17} />
            创建营销活动
          </Button>
        }
      />
      <div className="overview-hero">
        <div>
          <div className="hero-kicker">
            <Leaf size={15} /> 一份匠心，多一种抵达
          </div>
          <h2>
            好的故事，
            <br />
            从真实的手艺开始。
          </h2>
          <p>
            先把你的品牌、工艺与产品记录下来，
            <br />
            再为它们找到合适的表达和人群。
          </p>
          <button onClick={() => go("knowledge")}>
            完善品牌知识库 <ArrowUpRight size={17} />
          </button>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <div className="hero-ring ring-one" />
          <div className="hero-ring ring-two" />
          <div className="hero-ring ring-three" />
          <div className="hero-script">
            传<br />承
          </div>
          <span>CRAFTED WITH PURPOSE</span>
          <div className="hero-seal">
            手作
            <br />
            有声
          </div>
        </div>
        <div className="hero-side">
          <span>你的营销工作流</span>
          <strong>
            有据可依
            <br />
            有序推进
          </strong>
          <p>资料 → 策划 → 审核 → 发布 → 复盘</p>
          <Badge tone="light">
            {data.connections.ai_configured
              ? "AI 服务已配置"
              : "当前为模板草稿模式"}
          </Badge>
        </div>
      </div>
      <div className="metrics-grid">
        {metrics.map((m) => (
          <div className="metric-card" key={m.label}>
            <div>
              <span>{m.label}</span>
              <m.icon size={18} />
            </div>
            <strong>{m.value}</strong>
            <small>{m.note}</small>
          </div>
        ))}
      </div>
      <div className="dashboard-columns">
        <Panel
          title="营销活动"
          subtitle="从一个明确目标，开始一次有效沟通"
          action={
            <button className="text-button" onClick={() => go("campaigns")}>
              全部活动 <ArrowRight size={15} />
            </button>
          }
        >
          {data.recent_campaigns.length ? (
            <div className="campaign-mini-list">
              {data.recent_campaigns.slice(0, 4).map((c) => (
                <button onClick={() => go("studio", c.id)} key={c.id}>
                  <span className="mini-icon">
                    <Flag size={20} />
                  </span>
                  <div>
                    <strong>{c.name}</strong>
                    <small>
                      {c.start_date} — {c.end_date}
                    </small>
                  </div>
                  <Status value={c.status} />
                  <ArrowUpRight size={17} />
                </button>
              ))}
            </div>
          ) : (
            <Empty
              title="你的第一场活动，正在酝酿"
              description="选择一件产品或一堂体验课，设定目标、渠道与预算。"
              action={
                <Button variant="secondary" onClick={() => go("campaigns")}>
                  <Plus size={16} />
                  创建第一场活动
                </Button>
              }
            />
          )}
        </Panel>
        <Panel title="把工作台用起来" subtitle="四步，建立有积累的营销习惯">
          <div className="onboarding">
            {[
              {
                icon: BookOpen,
                title: "记录品牌与工艺",
                text: "填写来源，确认可用于宣传的事实",
                page: "knowledge",
              },
              {
                icon: Package,
                title: "完善产品与课程",
                text: "价格、库存、名额与真实承接入口",
                page: "offerings",
              },
              {
                icon: ClipboardCheck,
                title: "策划并审核内容",
                text: "批准具体版本，再导出和登记发布",
                page: "campaigns",
              },
              {
                icon: ChartNoAxesCombined,
                title: "用真实数据复盘",
                text: "区分观察事实、推测与下一步验证",
                page: "analytics",
              },
            ].map((s, i) => (
              <button key={s.title} onClick={() => go(s.page)}>
                <span className="step-number">0{i + 1}</span>
                <s.icon size={19} />
                <div>
                  <strong>{s.title}</strong>
                  <small>{s.text}</small>
                </div>
                <ArrowUpRight size={15} />
              </button>
            ))}
          </div>
        </Panel>
      </div>
      <div className="dashboard-columns lower">
        <Panel title="最近动态" subtitle="商家空间中的真实操作记录">
          {data.activity.length ? (
            <div className="activity-list">
              {data.activity.slice(0, 5).map((a) => (
                <div key={a.id}>
                  <i />
                  <div>
                    <strong>{a.actor_name}</strong> <span>{a.action}</span>
                    <small>{date(a.created_at)}</small>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="quiet-empty">
              还没有操作记录。创建第一份资料后，操作会记录在这里。
            </div>
          )}
        </Panel>
        <Panel title="服务连接" subtitle="清晰了解当前工作边界">
          <div className="connection-list">
            <div>
              <span>内容生成</span>
              <Badge tone={data.connections.ai_configured ? "green" : "ochre"}>
                {data.connections.ai_configured ? "AI 已配置" : "模板草稿"}
              </Badge>
            </div>
            <div>
              <span>渠道发布</span>
              <strong>人工发布 · 链接登记</strong>
            </div>
            <div>
              <span>购买 / 报名</span>
              <strong>商家外部承接入口</strong>
            </div>
            <div>
              <span>待审核版本</span>
              <strong>{stats.pending_review || 0} 份</strong>
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}
