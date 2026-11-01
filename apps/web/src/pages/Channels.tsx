import { useState } from "react";
import { useApp } from "../context";
import { useResource } from "../hooks";
import { post, patch } from "../api";
import {
  Badge,
  Button,
  Empty,
  Form,
  Loading,
  Modal,
  Notice,
  Panel,
  SectionTitle,
  num,
  type Field,
} from "../components/UI";

const platforms = [
  { value: "douyin", label: "抖音" },
  { value: "bilibili", label: "B站" },
  { value: "xiaohongshu", label: "小红书" },
  { value: "kuaishou", label: "快手" },
  { value: "channels", label: "微信视频号" },
];
type Snapshot = {
  id: string;
  date: string;
  source: string;
  followers: number | null;
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  posts: number | null;
  latest_post_date: string | null;
};
type Channel = {
  id: string;
  platform: string;
  name: string;
  account_id: string;
  profile_url: string;
  snapshots: Snapshot[];
  latest: Snapshot | null;
  follower_change: number | null;
};
const counters = [
  { key: "followers", label: "粉丝总数" },
  { key: "views", label: "累计播放 / 阅读" },
  { key: "likes", label: "累计点赞" },
  { key: "comments", label: "累计评论" },
  { key: "shares", label: "累计分享" },
  { key: "posts", label: "作品总数" },
];

export default function ChannelsPage() {
  const { path, epoch, refresh, notify, workspace } = useApp();
  const { data, loading, error, reload } = useResource<Channel[]>(
    path("/channels"),
    epoch,
  );
  const [adding, setAdding] = useState(false),
    [editing, setEditing] = useState<Channel | null>(null),
    [recording, setRecording] = useState<Channel | null>(null);
  const canEdit = ["owner", "editor"].includes(workspace.role);
  const fields: Field[] = [
    { key: "date", label: "记录日期", type: "date", required: true },
    {
      key: "source",
      label: "数据来源",
      required: true,
      placeholder: "例如：平台创作者后台，累计口径",
    },
    ...counters.map((field) => ({
      ...field,
      type: "text",
      placeholder: "非负整数，未提供请留空",
    })),
    {
      key: "latest_post_date",
      label: "最近作品发布日期（可选）",
      type: "date",
    },
  ];
  return (
    <>
      <SectionTitle
        eyebrow="CHANNELS & COMMUNITY"
        title="渠道账号与运营记录"
        description="把各平台账号和同口径的数据留在当前商家空间。"
        action={
          <Button disabled={!canEdit} onClick={() => setAdding(true)}>
            添加渠道账号
          </Button>
        }
      />
      <Notice>
        当前为手动记录，尚未接通自动同步。只填写公开账号信息，不需要账号密码。请使用同一累计口径；平台未提供的指标留空，不会当成
        0。
      </Notice>
      {loading ? (
        <Loading />
      ) : error ? (
        <Notice tone="error">
          {error}
          <Button onClick={reload}>重试</Button>
        </Notice>
      ) : !data?.length ? (
        <Empty
          title="添加第一个商家账号"
          description="支持抖音、B站、小红书、快手和微信视频号。视频号没有公开主页链接时可只填写账号标识。"
        />
      ) : (
        <div className="channel-list">
          {data.map((account) => (
            <Panel
              key={account.id}
              title={account.name}
              subtitle={`${platforms.find((p) => p.value === account.platform)?.label} · ${account.account_id}`}
              action={
                <Button
                  variant="secondary small"
                  disabled={!canEdit}
                  onClick={() => setRecording(account)}
                >
                  记录运营数据
                </Button>
              }
            >
              <div className="channel-content">
                <Button
                  variant="secondary small"
                  disabled={!canEdit}
                  onClick={() => setEditing(account)}
                >
                  编辑昵称与主页
                </Button>
                <div className="inline">
                  <Badge tone="ochre">手动记录 · 未自动同步</Badge>
                  {account.profile_url && (
                    <a
                      href={account.profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      打开平台主页 ↗
                    </a>
                  )}
                </div>
                {account.latest ? (
                  <>
                    <p>
                      最近记录：{account.latest.date} · 来源：
                      {account.latest.source}
                    </p>
                    <div className="channel-metrics">
                      {counters.map((field) => (
                        <div key={field.key}>
                          <small>{field.label}</small>
                          <strong>
                            {account.latest![field.key as keyof Snapshot] ==
                            null
                              ? "未提供"
                              : num(
                                  account.latest![
                                    field.key as keyof Snapshot
                                  ] as number,
                                )}
                          </strong>
                        </div>
                      ))}
                    </div>
                    <p>
                      粉丝变化：
                      {account.follower_change === null
                        ? "至少两次记录后可比较"
                        : `${account.follower_change > 0 ? "+" : ""}${account.follower_change}（最近两次记录之间，非单日增量）`}
                      <br />
                      最近作品发布：
                      {account.latest.latest_post_date || "未提供"}
                    </p>
                    <div className="table-wrap">
                      <table>
                        <caption>历史快照 · 数值为累计值，不相加</caption>
                        <thead>
                          <tr>
                            <th>日期</th>
                            <th>粉丝</th>
                            <th>播放/阅读</th>
                            <th>点赞</th>
                            <th>评论</th>
                            <th>分享</th>
                            <th>作品</th>
                            <th>来源</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[...account.snapshots].reverse().map((s) => (
                            <tr key={s.id}>
                              <td>{s.date}</td>
                              <td>
                                {s.followers == null
                                  ? "未提供"
                                  : num(s.followers)}
                              </td>
                              <td>
                                {s.views == null ? "未提供" : num(s.views)}
                              </td>
                              <td>
                                {s.likes == null ? "未提供" : num(s.likes)}
                              </td>
                              <td>
                                {s.comments == null
                                  ? "未提供"
                                  : num(s.comments)}
                              </td>
                              <td>
                                {s.shares == null ? "未提供" : num(s.shares)}
                              </td>
                              <td>
                                {s.posts == null ? "未提供" : num(s.posts)}
                              </td>
                              <td>{s.source}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <p>
                    还没有运营记录。填写平台后台的数据后，这里会显示累计指标及历史变化。
                  </p>
                )}
              </div>
            </Panel>
          ))}
        </div>
      )}
      {(adding || editing) && (
        <Modal
          title={editing ? "编辑渠道账号" : "添加渠道账号"}
          onClose={() => {
            setAdding(false);
            setEditing(null);
          }}
        >
          <Form
            initial={editing || {}}
            fields={[
              ...(!editing
                ? [
                    {
                      key: "platform",
                      label: "平台",
                      type: "select",
                      options: platforms,
                      required: true,
                    },
                    {
                      key: "account_id",
                      label: "账号标识 / UID",
                      required: true,
                    },
                  ]
                : []),
              { key: "name", label: "账号昵称", required: true },
              {
                key: "profile_url",
                label: "主页链接（可选）",
                type: "url",
                help: "填写对应平台的 HTTPS 链接，不能填写密码或授权令牌",
              },
            ]}
            submitLabel="保存账号"
            onCancel={() => {
              setAdding(false);
              setEditing(null);
            }}
            onSubmit={async (values) => {
              if (editing) await patch(path(`/channels/${editing.id}`), values);
              else await post(path("/channels"), values);
              setAdding(false);
              setEditing(null);
              refresh();
              notify("账号已保存，尚未接通自动同步");
            }}
          />
        </Modal>
      )}
      {recording && (
        <Modal
          title={`记录运营数据 · ${recording.name}`}
          onClose={() => setRecording(null)}
        >
          <Form
            fields={fields}
            submitLabel="保存数据快照"
            onCancel={() => setRecording(null)}
            onSubmit={async (values) => {
              await post(path(`/channels/${recording.id}/snapshots`), {
                ...values,
                ...Object.fromEntries(
                  counters.map((f) => [
                    f.key,
                    String(values[f.key] || "").trim() === ""
                      ? null
                      : Number(values[f.key]),
                  ]),
                ),
                latest_post_date: values.latest_post_date || null,
              });
              setRecording(null);
              refresh();
              notify("运营数据已保存");
            }}
          >
            <Notice>
              所有数字均填写截至记录日的累计值；一天一条，不重复累计。来源和日期将保留在历史记录中。
            </Notice>
          </Form>
        </Modal>
      )}
    </>
  );
}
