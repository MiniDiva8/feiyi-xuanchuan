import { useState } from "react";
import {
  ArrowUpRight,
  Search,
  LayoutDashboard,
  BookOpen,
  Package,
  Flag,
  ClipboardCheck,
  ChartNoAxesCombined,
  Users,
  Settings,
} from "lucide-react";
import { Modal } from "./UI";
const destinations = [
  {
    id: "overview",
    title: "经营概览",
    description: "当前活动、准备进度与经营记录",
    icon: LayoutDashboard,
  },
  {
    id: "knowledge",
    title: "品牌知识库",
    description: "真实资料、来源与使用权限",
    icon: BookOpen,
  },
  {
    id: "offerings",
    title: "产品与课程",
    description: "维护商品、课程及承接入口",
    icon: Package,
  },
  {
    id: "campaigns",
    title: "营销活动",
    description: "活动简报、策划、海报素材和复盘",
    icon: Flag,
  },
  {
    id: "publications",
    title: "审核与发布",
    description: "审核记录、作品链接与发布档案",
    icon: ClipboardCheck,
  },
  {
    id: "channels",
    title: "渠道账号",
    description: "平台账号及手动运营快照",
    icon: Users,
  },
  {
    id: "analytics",
    title: "数据与复盘",
    description: "真实指标、CSV导入及活动分析",
    icon: ChartNoAxesCombined,
  },
  {
    id: "settings",
    title: "商家设置",
    description: "成员、服务配置、任务与审计",
    icon: Settings,
  },
];
export default function QuickNavigation({
  go,
  close,
}: {
  go: (page: string) => void;
  close: () => void;
}) {
  const [query, setQuery] = useState("");
  const matches = destinations.filter((item) =>
    (item.title + item.description).includes(query.trim()),
  );
  return (
    <Modal title="快捷导航" onClose={close}>
      <div className="quick-navigation">
        <label className="quick-search">
          <Search size={19} />
          <input
            autoFocus
            aria-label="搜索工作台功能"
            placeholder="输入功能名称，例如：海报、渠道、数据…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <kbd>ESC</kbd>
        </label>
        <div className="quick-results">
          {matches.length ? (
            matches.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  go(item.id);
                  close();
                }}
              >
                <span className="quick-icon">
                  <item.icon size={19} />
                </span>
                <span>
                  <strong>{item.title}</strong>
                  <small>{item.description}</small>
                </span>
                <ArrowUpRight size={17} />
              </button>
            ))
          ) : (
            <p className="quiet-empty">没有匹配的功能，试试“活动”或“资料”。</p>
          )}
        </div>
        <p className="quick-hint">这是功能导航，不会检索或发送商家私有内容。</p>
      </div>
    </Modal>
  );
}
