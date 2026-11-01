import {
  ArrowUpRight,
  ArrowRight,
  Plus,
  BookOpen,
  Package,
  Flag,
  ClipboardCheck,
  Eye,
  Coins,
  Users,
  Layers,
  CalendarDays,
} from "lucide-react";
import { useApp } from "../context";
import { useResource } from "../hooks";
import type { Overview } from "../types";
import Preparation from "../components/Preparation";
import {
  Badge,
  Button,
  Panel,
  SectionTitle,
  Loading,
  Notice,
  Empty,
  num,
  money,
  date,
} from "../components/UI";
const actionNames: Record<string, string> = {
  create: "创建了档案",
  update: "更新了档案",
  delete: "移除了资料",
  approve: "批准了一个版本",
  reject: "提出了修改意见",
  generate: "生成了内容草稿",
  revise: "保存了新版本",
  "manual-publication": "登记了发布作品",
  "csv-import": "导入了经营记录",
  "next-round": "创建了下一轮活动",
  export: "导出了审核素材",
};
export default function OverviewPage() {
  const { path, workspace, epoch, go } = useApp();
  const { data, loading, error } = useResource<Overview>(
    path("/overview"),
    epoch,
  );
  if (loading) return <Loading />;
  if (error || !data)
    return (
      <Notice tone="error">
        {error || "暂时无法读取经营概览，请稍后刷新。"}
      </Notice>
    );
  const stats = data.stats;
  const metrics = [
    {
      label: "累计曝光",
      value: num(stats.impressions),
      icon: Eye,
      note: "已录入的渠道数据",
    },
    {
      label: "成交金额",
      value: money(stats.revenue),
      icon: Coins,
      note: "商家录入金额，非利润",
    },
    {
      label: "营销活动",
      value: num(stats.campaigns),
      icon: Flag,
      note: "保留每一轮策划与版本",
    },
    {
      label: "待审核版本",
      value: num(stats.pending_review),
      icon: ClipboardCheck,
      note: "方案与素材待商家确认",
    },
  ];
  return (
    <>
      <SectionTitle
        eyebrow="YOUR BUSINESS, AT A GLANCE"
        title="经营工作台"
        description={workspace.name + "，今天也让好手艺被看见。"}
        action={
          <Button
            disabled={!["owner", "editor"].includes(workspace.role)}
            onClick={() => go("campaign-new")}
          >
            <Plus size={17} />
            创建营销活动
          </Button>
        }
      />
      <div className="metrics-grid">
        {metrics.map((metric, index) => (
          <div className={"metric-card metric-" + index} key={metric.label}>
            <div>
              <span>{metric.label}</span>
              <span className="metric-icon">
                <metric.icon size={18} />
              </span>
            </div>
            <strong>{metric.value}</strong>
            <small>
              <i />
              {metric.note}
            </small>
          </div>
        ))}
      </div>
      <div className="overview-opening">
        <section className="desk-hero">
          <div>
            <span className="eyebrow">HERITAGE IN EVERYDAY LIFE</span>
            <h2>
              好手艺，
              <br />
              值得被认真讲述。
            </h2>
            <p>
              把一件产品、一堂体验课，
              <br />
              变成下一场有据可依的传播。
            </p>
            <button onClick={() => go("campaign-new")}>
              开始一次营销活动 <ArrowUpRight size={17} />
            </button>
          </div>
          <span className="desk-hero-caption">CRAFT / STORY / CONNECTION</span>
        </section>
        <Panel
          title="今天，从这里开始"
          subtitle="常用入口，让工作有序推进"
          className="launch-panel"
        >
          <div className="launch-actions">
            {[
              {
                icon: BookOpen,
                title: "完善品牌档案",
                text: "真实资料与可用素材",
                page: "knowledge",
              },
              {
                icon: Package,
                title: "维护产品与课程",
                text: "价格、库存和报名入口",
                page: "offerings",
              },
              {
                icon: Users,
                title: "记录渠道数据",
                text: "账号快照与历史变化",
                page: "channels",
              },
            ].map((item) => (
              <button key={item.page} onClick={() => go(item.page)}>
                <span className="launch-icon">
                  <item.icon size={21} />
                </span>
                <span>
                  <strong>{item.title}</strong>
                  <small>{item.text}</small>
                </span>
                <ArrowUpRight size={17} />
              </button>
            ))}
          </div>
        </Panel>
      </div>
      <div className="overview-content">
        <Panel
          title="最近的营销活动"
          subtitle="每一轮行动，都留有来处与进度"
          action={
            <button className="text-button" onClick={() => go("campaigns")}>
              全部活动 <ArrowRight size={15} />
            </button>
          }
        >
          {data.recent_campaigns.length ? (
            <div className="campaign-mini-list">
              {data.recent_campaigns.slice(0, 4).map((campaign) => (
                <button
                  key={campaign.id}
                  onClick={() => go("studio", campaign.id)}
                >
                  <span className="mini-icon">
                    <Flag size={20} />
                  </span>
                  <div>
                    <strong>{campaign.name}</strong>
                    <small>
                      <CalendarDays size={12} />
                      {campaign.start_date} — {campaign.end_date}
                    </small>
                  </div>
                  <Badge tone="neutral">
                    {campaign.status === "draft"
                      ? "活动草稿"
                      : campaign.status === "active"
                        ? "进行中"
                        : campaign.status}
                  </Badge>
                  <ArrowUpRight size={17} />
                </button>
              ))}
            </div>
          ) : (
            <Empty
              title="为你的品牌，开启第一场活动"
              description="先选定推广目标，再把策划、素材与审核放到同一个工作室。"
              action={
                <Button variant="secondary" onClick={() => go("campaign-new")}>
                  <Plus size={16} />
                  创建第一场活动
                </Button>
              }
            />
          )}
        </Panel>
        <Preparation key={workspace.id} overview={data} />
      </div>
      <div className="dashboard-columns lower">
        <Panel title="最近动态" subtitle="商家空间内的真实操作记录">
          {data.activity.length ? (
            <div className="activity-list">
              {data.activity.slice(0, 5).map((item) => (
                <div key={item.id}>
                  <i />
                  <div>
                    <strong>{item.actor_name}</strong>{" "}
                    <span>{actionNames[item.action] || item.action}</span>
                    <small>{date(item.created_at)}</small>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="quiet-empty">
              从第一份资料开始，你的操作记录会留在这里。
            </div>
          )}
        </Panel>
        <Panel title="工作空间状态" subtitle="清晰了解当前配置与服务边界">
          <div className="connection-list">
            <div>
              <span>
                <Layers size={15} />
                内容生成
              </span>
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
              <span>经营记录</span>
              <strong>
                {num(stats.orders)} 笔订单 / {num(stats.registrations)} 人报名
              </strong>
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}
