import { useEffect, useState, useCallback } from "react";
import {
  LayoutDashboard,
  BookOpen,
  Package,
  Flag,
  ClipboardCheck,
  ChartNoAxesCombined,
  Settings,
  ChevronDown,
  LogOut,
  Plus,
  Menu,
  X,
  Search,
  ArrowUpRight,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { request, post, workspacePath, ApiError } from "./api";
import type { Session } from "./types";
import { AppContext } from "./context";
import { Button, Form, Loading, Modal, Notice } from "./components/UI";
import Auth from "./pages/Auth";
import OverviewPage from "./pages/Overview";
import { KnowledgePage, OfferingsPage } from "./pages/Resources";
import { CampaignsPage, StudioPage } from "./pages/Campaigns";
import PublicationsPage from "./pages/Publications";
import AnalyticsPage from "./pages/Analytics";
import SettingsPage from "./pages/Settings";
const nav = [
  { id: "overview", label: "经营概览", icon: LayoutDashboard },
  { id: "knowledge", label: "品牌知识库", icon: BookOpen },
  { id: "offerings", label: "产品与课程", icon: Package },
  { id: "campaigns", label: "营销活动", icon: Flag },
  { id: "publications", label: "审核与发布", icon: ClipboardCheck },
  { id: "analytics", label: "数据与复盘", icon: ChartNoAxesCombined },
];
export default function App() {
  const [session, setSession] = useState<Session | null>(null),
    [loading, setLoading] = useState(true),
    [loadError, setLoadError] = useState(""),
    [workspaceId, setWorkspaceId] = useState(""),
    [page, setPage] = useState("overview"),
    [campaignId, setCampaignId] = useState(""),
    [epoch, setEpoch] = useState(0),
    [mobile, setMobile] = useState(false),
    [createWorkspace, setCreateWorkspace] = useState(false),
    [toast, setToast] = useState<{ message: string; tone: string } | null>(
      null,
    );
  const loadSession = () => {
    setLoading(true);
    setLoadError("");
    request<Session>("/auth/me")
      .then((s) => {
        setSession(s);
        setWorkspaceId((v) =>
          s.workspaces.some((w) => w.id === v) ? v : s.workspaces[0]?.id || "",
        );
      })
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401))
          setLoadError(e.message);
      })
      .finally(() => setLoading(false));
  };
  useEffect(loadSession, []);
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(t);
    }
  }, [toast]);
  const notify = useCallback(
    (message: string, tone = "success") => setToast({ message, tone }),
    [],
  );
  const refresh = useCallback(() => setEpoch((v) => v + 1), []);
  const go = useCallback((p: string, id?: string) => {
    setPage(p);
    if (id) setCampaignId(id);
    setMobile(false);
    window.scrollTo({ top: 0 });
  }, []);
  if (loading) return <Loading />;
  if (loadError && !session)
    return (
      <div className="boot-error">
        <Notice tone="error">{loadError}</Notice>
        <Button onClick={loadSession}>重新连接</Button>
      </div>
    );
  if (!session)
    return (
      <Auth
        onSuccess={(s) => {
          setSession(s);
          setWorkspaceId(s.workspaces[0]?.id || "");
        }}
      />
    );
  const workspace =
    session.workspaces.find((w) => w.id === workspaceId) ||
    session.workspaces[0];
  if (!workspace) return <Notice>暂无可用商家空间，请重新登录。</Notice>;
  const path = (p: string) => workspacePath(workspace.id, p);
  return (
    <AppContext.Provider
      value={{ workspace, path, notify, go, refresh, epoch }}
    >
      <div className="app">
        <a className="skip-link" href="#main-content">
          跳至主要内容
        </a>
        {mobile && (
          <div className="sidebar-scrim" onClick={() => setMobile(false)} />
        )}
        <aside className={"sidebar " + (mobile ? "open" : "")}>
          <a
            className="brand"
            href="#"
            onClick={(e) => {
              e.preventDefault();
              go("overview");
            }}
          >
            <span className="brand-seal">承</span>
            <div>
              承艺<span>HERITAGE STUDIO</span>
            </div>
          </a>
          <button
            className="mobile-close icon-button"
            aria-label="关闭导航"
            onClick={() => setMobile(false)}
          >
            <X size={20} />
          </button>
          <div className="workspace-switch">
            <span className="workspace-avatar">
              {workspace.name.slice(0, 1)}
            </span>
            <label>
              <small>当前商家空间</small>
              <select
                aria-label="切换商家空间"
                value={workspace.id}
                onChange={(e) => {
                  setWorkspaceId(e.target.value);
                  go("overview");
                  refresh();
                }}
              >
                {session.workspaces.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                  </option>
                ))}
              </select>
            </label>
            <ChevronDown size={15} />
          </div>
          <span className="nav-caption">工作空间 / WORKSPACE</span>
          <nav>
            {nav.map((n) => (
              <button
                key={n.id}
                className={
                  page === n.id || (page === "studio" && n.id === "campaigns")
                    ? "active"
                    : ""
                }
                onClick={() => go(n.id)}
              >
                <n.icon size={19} />
                {n.label}
                {page === n.id && <span className="nav-dot" />}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="sidebar-note">
              <span>
                让手艺的价值
                <br />
                被看见，也被记住。
              </span>
              <div className="note-grid" aria-hidden="true">
                匠
              </div>
              <ArrowUpRight size={17} />
            </div>
            <button
              className={
                "settings-link " + (page === "settings" ? "active" : "")
              }
              onClick={() => go("settings")}
            >
              <Settings size={18} />
              商家设置
            </button>
            <button
              className="settings-link"
              onClick={() => setCreateWorkspace(true)}
            >
              <Plus size={18} />
              创建商家空间
            </button>
            <div className="user-row">
              <span className="user-avatar">
                {session.user.name.slice(0, 1)}
              </span>
              <div>
                <strong>{session.user.name}</strong>
                <small>
                  {{
                    owner: "商家管理员",
                    editor: "内容编辑",
                    reviewer: "内容审核",
                  }[workspace.role] || workspace.role}
                </small>
              </div>
              <button
                className="icon-button"
                aria-label="退出登录"
                onClick={async () => {
                  try {
                    await post("/auth/logout");
                    setSession(null);
                  } catch (e) {
                    notify((e as Error).message, "error");
                  }
                }}
              >
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </aside>
        <div className="workspace-main">
          <header className="topbar">
            <button
              className="icon-button mobile-menu"
              aria-label="打开导航"
              onClick={() => setMobile(true)}
            >
              <Menu size={21} />
            </button>
            <div className="breadcrumb">
              工作台 <span>/</span>
              <strong>
                {page === "studio"
                  ? "活动工作室"
                  : page === "settings"
                    ? "商家设置"
                    : nav.find((n) => n.id === page)?.label}
              </strong>
            </div>
            <div className="topbar-right">
              <span className="live-status">
                <i />
                空间数据已连接
              </span>
              <span className="topbar-date">
                {new Date().toLocaleDateString("zh-CN", {
                  month: "long",
                  day: "numeric",
                  weekday: "long",
                })}
              </span>
              <button
                className="topbar-profile"
                aria-label="打开商家设置"
                onClick={() => go("settings")}
              >
                {session.user.name.slice(0, 1)}
              </button>
            </div>
          </header>
          <main id="main-content" key={workspace.id}>
            {page === "overview" ? (
              <OverviewPage />
            ) : page === "knowledge" ? (
              <KnowledgePage />
            ) : page === "offerings" ? (
              <OfferingsPage />
            ) : page === "campaigns" ? (
              <CampaignsPage />
            ) : page === "studio" ? (
              <StudioPage key={campaignId} id={campaignId} />
            ) : page === "publications" ? (
              <PublicationsPage />
            ) : page === "analytics" ? (
              <AnalyticsPage />
            ) : (
              <SettingsPage />
            )}
          </main>
          <footer className="workspace-footer">
            <span>承艺 / 让每一份匠心有迹可循</span>
            <span>资料有据 · 版本可溯 · 数据真实</span>
          </footer>
        </div>
        {toast && (
          <div className={"toast " + toast.tone} role="status">
            {toast.tone === "error" ? (
              <AlertCircle size={18} />
            ) : (
              <CheckCircle2 size={18} />
            )}
            <span>{toast.message}</span>
            <button
              className="icon-button"
              onClick={() => setToast(null)}
              aria-label="关闭提示"
            >
              <X size={15} />
            </button>
          </div>
        )}
        {createWorkspace && (
          <Modal
            title="创建新的商家空间"
            onClose={() => setCreateWorkspace(false)}
          >
            <Form
              fields={[
                { key: "name", label: "商家名称", required: true },
                { key: "description", label: "商家简介", type: "textarea" },
              ]}
              onCancel={() => setCreateWorkspace(false)}
              onSubmit={async (d) => {
                const w = await post<Session["workspaces"][number]>(
                  "/workspaces",
                  d,
                );
                setSession({
                  ...session,
                  workspaces: [...session.workspaces, w],
                });
                setWorkspaceId(w.id);
                setCreateWorkspace(false);
                go("overview");
                notify("商家空间已创建");
              }}
            />
          </Modal>
        )}
      </div>
    </AppContext.Provider>
  );
}
