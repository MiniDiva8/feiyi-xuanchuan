import { useState } from "react";
import {
  Plus,
  ShieldCheck,
  KeyRound,
  Users,
  Activity,
  RefreshCw,
  CheckCircle2,
} from "lucide-react";
import { useApp } from "../context";
import { useResource } from "../hooks";
import { post } from "../api";
import type { Audit, Task } from "../types";
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
  date,
} from "../components/UI";
export default function SettingsPage() {
  const { path, workspace, epoch, notify, refresh } = useApp();
  const settings = useResource<{
      ai_configured: boolean;
      ai_model: string;
      publishing: string;
      checkout: string;
    }>(path("/settings"), epoch),
    members = useResource<
      { user_id: string; name: string; email: string; role: string }[]
    >(path("/members"), epoch),
    audit = useResource<Audit[]>(path("/audit"), epoch),
    tasks = useResource<Task[]>(path("/tasks"), epoch);
  const [invite, setInvite] = useState(false),
    [busy, setBusy] = useState("");
  return (
    <>
      <SectionTitle
        eyebrow="WORKSPACE SETTINGS / 商家设置"
        title="商家设置"
        description="管理成员、了解服务状态，查看每一次关键操作与生成任务。"
      />
      <div className="settings-grid">
        <Panel title="商家空间" subtitle="独立的数据边界与成员权限">
          <div className="settings-content">
            <span className="large-workspace-avatar">
              {workspace.name.slice(0, 1)}
            </span>
            <h3>{workspace.name}</h3>
            <p>
              {workspace.description ||
                "每一份品牌资料、策划与经营记录都归属于此商家空间。"}
            </p>
            <Badge tone="green">
              {{ owner: "管理员", editor: "内容编辑", reviewer: "内容审核" }[
                workspace.role
              ] || workspace.role}
            </Badge>
            <small className="muted">创建于 {date(workspace.created_at)}</small>
          </div>
        </Panel>
        <Panel title="服务状态" subtitle="服务端配置，浏览器不收集 API 密钥">
          {settings.loading ? (
            <Loading />
          ) : settings.error ? (
            <Notice tone="error">{settings.error}</Notice>
          ) : (
            <div className="settings-content">
              <div className="setting-row">
                <span>
                  <KeyRound size={18} />
                  内容生成服务
                </span>
                <Badge tone={settings.data?.ai_configured ? "green" : "ochre"}>
                  {settings.data?.ai_configured ? "AI 已配置" : "模板草稿模式"}
                </Badge>
              </div>
              {settings.data?.ai_model && <p>模型：{settings.data.ai_model}</p>}
              <p>
                {settings.data?.ai_configured
                  ? "已配置服务端模型。调用失败会显示错误，任务保留状态供检查。"
                  : "当前未配置模型，内容生成使用带明确标识的公共模板，不会声称真实 AI 生成。"}
              </p>
              <p className="config-help">
                部署管理员可在服务端配置
                MARKETING_AI_API_KEY、MARKETING_AI_MODEL
                与可选服务地址。请勿在浏览器、资料或素材中填写密钥。
              </p>
              <div className="setting-row">
                <span>渠道发布</span>
                <strong>人工发布与登记</strong>
              </div>
              <div className="setting-row">
                <span>购买与报名</span>
                <strong>外部承接链接</strong>
              </div>
            </div>
          )}
        </Panel>
      </div>
      <Panel
        title="商家成员"
        subtitle="编辑负责内容，审核负责确认；管理员拥有全部权限。"
        action={
          <Button
            variant="secondary small"
            disabled={workspace.role !== "owner"}
            onClick={() => setInvite(true)}
          >
            <Plus size={15} />
            添加成员
          </Button>
        }
      >
        {members.loading ? (
          <Loading />
        ) : members.error ? (
          <Notice tone="error">{members.error}</Notice>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>成员</th>
                  <th>邮箱</th>
                  <th>角色</th>
                  <th>空间权限</th>
                </tr>
              </thead>
              <tbody>
                {members.data?.map((m) => (
                  <tr key={m.user_id}>
                    <td>
                      <strong>{m.name}</strong>
                    </td>
                    <td>{m.email}</td>
                    <td>
                      <Badge tone="green">
                        {{
                          owner: "商家管理员",
                          editor: "内容编辑",
                          reviewer: "内容审核",
                        }[m.role] || m.role}
                      </Badge>
                    </td>
                    <td>
                      {m.role === "owner"
                        ? "管理、编辑与审核"
                        : m.role === "editor"
                          ? "编辑资料、活动与素材"
                          : "批准与退回内容版本"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <Panel
        title="生成任务"
        subtitle="查看生成结果与失败状态；失败任务可在服务端允许次数内重试。"
      >
        {tasks.loading ? (
          <Loading />
        ) : tasks.error ? (
          <Notice tone="error">{tasks.error}</Notice>
        ) : !tasks.data?.length ? (
          <div className="quiet-empty">
            暂无生成任务。创建策划或素材后，记录会出现在这里。
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>任务类型</th>
                  <th>状态</th>
                  <th>生成模式</th>
                  <th>创建时间</th>
                  <th>说明</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {[...tasks.data].reverse().map((t) => (
                  <tr key={t.id}>
                    <td>{t.kind}</td>
                    <td>
                      <Status value={t.status} />
                    </td>
                    <td>
                      {t.generation_mode ? (
                        <Mode value={t.generation_mode} />
                      ) : (
                        <span>—</span>
                      )}
                    </td>
                    <td>{date(t.created_at)}</td>
                    <td className="error-text">{t.error || "—"}</td>
                    <td>
                      {t.status === "failed" && (
                        <Button
                          variant="secondary small"
                          busy={busy === t.id}
                          onClick={async () => {
                            setBusy(t.id);
                            try {
                              await post(path("/tasks/" + t.id + "/retry"));
                              refresh();
                              notify("任务已重试");
                            } catch (e) {
                              notify((e as Error).message, "error");
                            } finally {
                              setBusy("");
                            }
                          }}
                        >
                          <RefreshCw size={14} />
                          重试
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <Panel
        title="操作审计"
        subtitle="资料、审批、发布与导入的关键记录，仅展示本商家空间。"
      >
        {audit.loading ? (
          <Loading />
        ) : audit.error ? (
          <Notice tone="error">{audit.error}</Notice>
        ) : !audit.data?.length ? (
          <div className="quiet-empty">尚无操作记录</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>操作时间</th>
                  <th>操作者</th>
                  <th>操作</th>
                  <th>对象</th>
                  <th>变更详情</th>
                </tr>
              </thead>
              <tbody>
                {audit.data.map((a) => (
                  <tr key={a.id}>
                    <td>{date(a.created_at)}</td>
                    <td>{a.actor_name}</td>
                    <td>{a.action}</td>
                    <td>
                      {a.entity_type}
                      <small className="table-sub">{a.entity_id}</small>
                    </td>
                    <td>
                      {a.details && Object.keys(a.details).length ? (
                        <details className="audit-details">
                          <summary>查看记录</summary>
                          <pre>{JSON.stringify(a.details, null, 2)}</pre>
                        </details>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      {invite && (
        <Modal title="添加已有账号为商家成员" onClose={() => setInvite(false)}>
          <Form
            fields={[
              {
                key: "email",
                label: "已注册账号的邮箱",
                type: "email",
                required: true,
              },
              {
                key: "role",
                label: "分配角色",
                type: "select",
                options: [
                  { value: "editor", label: "内容编辑" },
                  { value: "reviewer", label: "内容审核" },
                ],
              },
            ]}
            onCancel={() => setInvite(false)}
            onSubmit={async (d) => {
              await post(path("/members"), d);
              setInvite(false);
              refresh();
              notify("成员已添加");
            }}
          >
            <Notice>
              对方需要先自行注册账号。本操作授予当前商家权限，不会发送邀请邮件。
            </Notice>
          </Form>
        </Modal>
      )}
    </>
  );
}
