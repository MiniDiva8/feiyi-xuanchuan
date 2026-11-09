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
  const current = data.recent_campaigns[0];
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
      note: "每场活动保留独立版本",
    },
    {
      label: "待审核版本",
      value: num(stats.pending_review),
      icon: ClipboardCheck,
      note: "方案与素材待商家确认",
    },
  ];
  const objective: Record<string, string> = {
    sales: "产品销售",
    registration: "课程报名",
    awareness: "品牌宣传",
  };
  return (
    <>
      <SectionTitle
        title="经营工作台"
        description={workspace.name + "，从今天最重要的工作开始。"}
        action={
          <Button variant="secondary" onClick={() => go("campaigns")}>
            查看全部活动 <ArrowUpRight size={15} />
          </Button>
        }
      />
      {stats.pending_review > 0 && (
        <div className="overview-alert" role="status">
          <ClipboardCheck size={17} />
          <span>
            <strong>{num(stats.pending_review)} 个版本</strong>
            等待商家审核，确认后继续下一步。
          </span>
          <button className="text-button" onClick={() => go("campaigns")}>
            选择活动审核 <ArrowRight size={14} />
          </button>
        </div>
      )}
      <div className="overview-layout">
        <div className="overview-primary">
          <Panel
            title="当前活动"
            subtitle="策划、内容和发布，都在同一处"
            className="current-panel"
          >
            {current ? (
              <div className="current-campaign">
                <div className="current-campaign-label">
                  {objective[current.objective] || current.objective}
                </div>
                <h2>{current.name}</h2>
                <p>
                  {current.audience || "在活动工作室完善目标受众与表达要求。"}
                </p>
                <div className="campaign-channels">
                  {current.channels.map((channel) => (
                    <Badge key={channel}>{channel}</Badge>
                  ))}
                </div>
                <div className="current-campaign-footer">
                  <span className="current-campaign-meta">
                    <CalendarDays size={14} />
                    {current.start_date} — {current.end_date}
                  </span>
                  <Button onClick={() => go("studio", current.id)}>
                    继续当前活动 <ArrowRight size={15} />
                  </Button>
                </div>
              </div>
            ) : (
              <Empty
                title="为你的品牌，开启第一场活动"
                description="确定这次推广什么，再把方案、素材与审核放到一个工作室。"
                action={
                  <Button
                    disabled={!["owner", "editor"].includes(workspace.role)}
                    onClick={() => go("campaign-new")}
                  >
                    <Plus size={16} />
                    创建第一场活动
                  </Button>
                }
              />
            )}
          </Panel>
          <Panel
            title="最近的营销活动"
            className="recent-panel"
            subtitle="回到每一轮行动与对应版本"
            action={
              <button className="text-button" onClick={() => go("campaigns")}>
                全部活动 <ArrowRight size={14} />
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
                      <Flag size={17} />
                    </span>
                    <div>
                      <strong>{campaign.name}</strong>
                      <small>
                        <CalendarDays size={12} />
                        {campaign.start_date} — {campaign.end_date}
                      </small>
                    </div>
                    <Badge>
                      {campaign.status === "draft"
                        ? "活动草稿"
                        : campaign.status === "active"
                          ? "进行中"
                          : campaign.status}
                    </Badge>
                    <ArrowUpRight size={16} />
                  </button>
                ))}
              </div>
            ) : (
              <div className="quiet-empty">
                创建活动后，在这里继续策划、制作素材和复盘。
              </div>
            )}
          </Panel>
          <div className="metrics-grid">
            {metrics.map((metric) => (
              <div className="metric-card" key={metric.label}>
                <div>
                  <span>{metric.label}</span>
                  <span className="metric-icon">
                    <metric.icon size={17} />
                  </span>
                </div>
                <strong>{metric.value}</strong>
                <small>{metric.note}</small>
              </div>
            ))}
          </div>
          <Panel
            title="最近动态"
            subtitle="当前商家空间的操作记录"
            className="events-panel"
          >
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
                从第一份资料开始，操作记录会留在这里。
              </div>
            )}
          </Panel>
        </div>
        <div className="overview-secondary">
          <Preparation key={workspace.id} overview={data} />
          <Panel title="常用入口" subtitle="把日常工作放在手边">
            <div className="launch-actions">
              {[
                {
                  icon: BookOpen,
                  title: "完善品牌档案",
                  text: "工艺事实、来源与可用素材",
                  page: "knowledge",
                },
                {
                  icon: Package,
                  title: "维护产品与课程",
                  text: "价格、名额与真实承接入口",
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
                    <item.icon size={18} />
                  </span>
                  <span>
                    <strong>{item.title}</strong>
                    <small>{item.text}</small>
                  </span>
                  <ArrowUpRight size={15} />
                </button>
              ))}
            </div>
          </Panel>
          <Panel title="工作空间状态">
            <div className="connection-list">
              <div>
                <span>
                  <Layers size={14} />
                  内容生成
                </span>
                <Badge
                  tone={data.connections.ai_configured ? "green" : "ochre"}
                >
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
      </div>
    </>
  );
}
