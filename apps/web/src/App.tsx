import { useCallback, useEffect, useState } from "react";
import {
  LayoutDashboard,
  BookOpen,
  Package,
  Flag,
  ClipboardCheck,
  ChartNoAxesCombined,
  Users,
  Settings,
  ChevronDown,
  LogOut,
  Plus,
  Menu,
  X,
  Search,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { request, post, workspacePath, ApiError } from "./api";
import { parseRoute, routeHash } from "./navigation.mjs";
import type { Session } from "./types";
import { AppContext } from "./context";
import { Button, Form, Loading, Modal, Notice } from "./components/UI";
import QuickNavigation from "./components/QuickNavigation";
import Auth from "./pages/Auth";
import OverviewPage from "./pages/Overview";
import { KnowledgePage, OfferingsPage } from "./pages/Resources";
import { CampaignsPage, StudioPage } from "./pages/Campaigns";
import PublicationsPage from "./pages/Publications";
import AnalyticsPage from "./pages/Analytics";
import SettingsPage from "./pages/Settings";
import ChannelsPage from "./pages/Channels";
const sections = [
  {
    label: "工作台",
    items: [{ id: "overview", label: "经营概览", icon: LayoutDashboard }],
  },
  {
    label: "品牌与经营",
    items: [
      { id: "knowledge", label: "品牌知识库", icon: BookOpen },
      { id: "offerings", label: "产品与课程", icon: Package },
    ],
  },
  {
    label: "内容与传播",
    items: [
      { id: "campaigns", label: "营销活动", icon: Flag },
      { id: "publications", label: "审核与发布", icon: ClipboardCheck },
    ],
  },
  {
    label: "渠道与洞察",
    items: [
      { id: "channels", label: "渠道账号", icon: Users },
      { id: "analytics", label: "数据与复盘", icon: ChartNoAxesCombined },
    ],
  },
];
const nav = sections.flatMap((section) => section.items);
export default function App() {
  const [session, setSession] = useState<Session | null>(null),
    [loading, setLoading] = useState(true),
    [loadError, setLoadError] = useState(""),
    [workspaceId, setWorkspaceId] = useState(""),
    [route, setRoute] = useState(() => parseRoute(window.location.hash)),
    [epoch, setEpoch] = useState(0),
    [mobile, setMobile] = useState(false),
    [quick, setQuick] = useState(false),
    [createWorkspace, setCreateWorkspace] = useState(false),
    [toast, setToast] = useState<{ message: string; tone: string } | null>(
      null,
    );
  const navigate = useCallback((page: string, id?: string, merchantId = "") => {
    const hash = routeHash(page, id, merchantId);
    setRoute(parseRoute(hash));
    if (window.location.hash !== hash) window.location.hash = hash;
    setMobile(false);
    setQuick(false);
    window.scrollTo({ top: 0 });
  }, []);
  const go = useCallback(
    (page: string, id?: string) =>
      navigate(page, id, route.workspaceId || workspaceId),
    [navigate, route.workspaceId, workspaceId],
  );
  useEffect(() => {
    const change = () => {
      setRoute(parseRoute(window.location.hash));
      setMobile(false);
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);
  const loadSession = useCallback(() => {
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
  }, []);
  useEffect(loadSession, [loadSession]);
  useEffect(() => {
    if (!toast) return;
    const timeout = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(timeout);
  }, [toast]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "k" &&
        session
      ) {
        event.preventDefault();
        if (document.querySelector('[aria-modal="true"]') && !quick) return;
        setQuick((value) => !value);
      }
      if (event.key === "Escape") setMobile(false);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [session, quick]);
  const notify = useCallback(
      (message: string, tone = "success") => setToast({ message, tone }),
      [],
    ),
    refresh = useCallback(() => setEpoch((value) => value + 1), []);
  if (loading)
    return (
      <div className="app-start">
        <span className="brand-seal">承</span>
        <Loading />
      </div>
    );
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
        onSuccess={(value) => {
          setSession(value);
          setWorkspaceId(value.workspaces[0]?.id || "");
          if (!route.workspaceId && route.page === "overview")
            navigate("overview", undefined, value.workspaces[0]?.id || "");
        }}
      />
    );
  const requestedWorkspace = route.workspaceId || workspaceId;
  if (
    route.workspaceId &&
    !session.workspaces.some((value) => value.id === route.workspaceId)
  )
    return (
      <div className="boot-error">
        <Notice tone="error">无权访问此商家空间</Notice>
        <Button
          onClick={() =>
            navigate("overview", undefined, session.workspaces[0]?.id || "")
          }
        >
          返回可用商家空间
        </Button>
      </div>
    );
  const workspace =
    session.workspaces.find((value) => value.id === requestedWorkspace) ||
    session.workspaces[0];
  if (!workspace) return <Notice>暂无可用商家空间，请重新登录。</Notice>;
  const path = (value: string) => workspacePath(workspace.id, value),
    page = route.page;
  const title =
    page === "studio"
      ? "活动工作室"
      : page === "settings"
        ? "商家设置"
        : nav.find((item) => item.id === page)?.label || "经营概览";
  return (
    <AppContext.Provider
      value={{ workspace, path, notify, go, refresh, epoch }}
    >
      <div className="app">
        <a
          className="skip-link"
          href="#main-content"
          onClick={(event) => {
            event.preventDefault();
            document.getElementById("main-content")?.focus();
          }}
        >
          跳至主要内容
        </a>
        {mobile && (
          <div className="sidebar-scrim" onClick={() => setMobile(false)} />
        )}
        <aside
          className={"sidebar " + (mobile ? "open" : "")}
          aria-label="商家导航"
        >
          <a
            className="brand"
            href="#/overview"
            onClick={(event) => {
              event.preventDefault();
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
                onChange={(event) => {
                  setWorkspaceId(event.target.value);
                  navigate("overview", undefined, event.target.value);
                  refresh();
                }}
              >
                {session.workspaces.map((value) => (
                  <option key={value.id} value={value.id}>
                    {value.name}
                  </option>
                ))}
              </select>
            </label>
            <ChevronDown size={14} />
          </div>
          <nav>
            {sections.map((section) => (
              <div className="nav-group" key={section.label}>
                <span className="nav-caption">{section.label}</span>
                {section.items.map((item) => (
                  <button
                    key={item.id}
                    aria-current={
                      page === item.id ||
                      (page === "studio" && item.id === "campaigns")
                        ? "page"
                        : undefined
                    }
                    className={
                      page === item.id ||
                      (page === "studio" && item.id === "campaigns")
                        ? "active"
                        : ""
                    }
                    onClick={() => go(item.id)}
                  >
                    <item.icon size={18} />
                    <span>{item.label}</span>
                    {(page === item.id ||
                      (page === "studio" && item.id === "campaigns")) && (
                      <span className="nav-dot" />
                    )}
                  </button>
                ))}
              </div>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="sidebar-workflow">
              <span className="workflow-dot" />
              <span>资料有据 · 内容可审 · 经营可循</span>
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
                    setQuick(false);
                    setMobile(false);
                  } catch (e) {
                    notify((e as Error).message, "error");
                  }
                }}
              >
                <LogOut size={17} />
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
              <span className="breadcrumb-home">工作台</span>
              <span>/</span>
              <strong>{title}</strong>
            </div>
            <div className="topbar-right">
              <button
                className="quick-trigger"
                onClick={() => setQuick(true)}
                aria-label="打开快捷导航"
              >
                <Search size={16} />
                <span>快捷导航</span>
                <kbd>Ctrl K</kbd>
              </button>
              <span className="workspace-private">
                <ShieldCheck size={14} />
                独立商家空间
              </span>
              <span className="topbar-date">
                {new Date().toLocaleDateString("zh-CN", {
                  month: "long",
                  day: "numeric",
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
          <main
            tabIndex={-1}
            id="main-content"
            className={"page page-" + page}
            key={workspace.id}
          >
            {page === "overview" ? (
              <OverviewPage />
            ) : page === "channels" ? (
              <ChannelsPage />
            ) : page === "knowledge" ? (
              <KnowledgePage />
            ) : page === "offerings" ? (
              <OfferingsPage />
            ) : page === "campaigns" ? (
              <CampaignsPage
                key={route.create ? "new" : "list"}
                createInitially={route.create}
              />
            ) : page === "studio" ? (
              <StudioPage key={route.campaignId} id={route.campaignId} />
            ) : page === "publications" ? (
              <PublicationsPage />
            ) : page === "analytics" ? (
              <AnalyticsPage />
            ) : (
              <SettingsPage />
            )}
          </main>
          <footer className="workspace-footer">
            <span>承艺 / 每一次传播，都有真实的来处</span>
            <span>HERITAGE, WITH PURPOSE</span>
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
        {quick && <QuickNavigation go={go} close={() => setQuick(false)} />}{" "}
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
              onSubmit={async (data) => {
                const value = await post<Session["workspaces"][number]>(
                  "/workspaces",
                  data,
                );
                setSession({
                  ...session,
                  workspaces: [...session.workspaces, value],
                });
                setWorkspaceId(value.id);
                setCreateWorkspace(false);
                navigate("overview", undefined, value.id);
                notify("商家空间已创建");
              }}
            />
          </Modal>
        )}
      </div>
    </AppContext.Provider>
  );
}
