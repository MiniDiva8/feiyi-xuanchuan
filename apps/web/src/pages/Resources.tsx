import { useEffect, useRef, useState } from "react";
import {
  Plus,
  Search,
  FileUp,
  BookOpen,
  Check,
  ShieldCheck,
  Pencil,
  Trash2,
  ExternalLink,
  Package,
  GraduationCap,
  FileText,
  Download,
} from "lucide-react";
import { useApp } from "../context";
import AttachmentPreview from "../components/AttachmentPreview";
import { useResource } from "../hooks";
import { request, post, patch, download } from "../api";
import type { Knowledge, Offering } from "../types";
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
  money,
  type Field,
} from "../components/UI";
const knowledgeFields: Field[] = [
  {
    key: "title",
    label: "资料标题",
    required: true,
    placeholder: "例如：品牌起源与工艺介绍",
  },
  {
    key: "kind",
    label: "资料类型",
    type: "select",
    options: [
      { value: "fact", label: "文化 / 工艺事实" },
      { value: "brand", label: "商家品牌信息" },
      { value: "material", label: "可用素材" },
    ],
  },
  {
    key: "content",
    label: "资料正文",
    type: "textarea",
    required: true,
    help: "请写入有依据的信息，避免无来源的传承人身份、认证或功效。",
  },
  {
    key: "source",
    label: "来源 / 依据",
    required: true,
    placeholder: "文献、官方链接、商家确认说明等",
  },
  {
    key: "usage_scope",
    label: "使用范围",
    type: "select",
    options: [
      { value: "marketing", label: "可用于营销宣传" },
      { value: "internal", label: "仅内部参考" },
    ],
  },
  {
    key: "confirmed",
    label: "商家已核实并确认使用权限",
    type: "checkbox",
    help: "只有已确认、可用于营销的资料会进入内容生成。",
  },
];
export function KnowledgePage() {
  const { path, epoch, notify, refresh } = useApp();
  const { data, loading, error } = useResource<Knowledge[]>(
    path("/knowledge"),
    epoch,
  );
  const [query, setQuery] = useState(""),
    [editing, setEditing] = useState<Knowledge | null | undefined>(undefined),
    [deleting, setDeleting] = useState<Knowledge | null>(null),
    [upload, setUpload] = useState<{ id: string; name: string } | null>(null),
    [uploading, setUploading] = useState(false),
    [uploadError, setUploadError] = useState("");
  const editSession = useRef(0);
  const pendingUpload = useRef<AbortController | null>(null);
  const changeEditor = (record: Knowledge | null | undefined) => {
    editSession.current += 1;
    pendingUpload.current?.abort();
    pendingUpload.current = null;
    setUpload(null);
    setUploadError("");
    setUploading(false);
    setEditing(record);
  };
  useEffect(
    () => () => {
      editSession.current += 1;
      pendingUpload.current?.abort();
    },
    [],
  );
  const filteredKnowledge = (data || []).filter((k) =>
    (k.title + k.content + k.source)
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  );
  async function toggle(k: Knowledge) {
    try {
      await patch(path("/knowledge/" + k.id), { confirmed: !k.confirmed });
      refresh();
      notify(k.confirmed ? "已撤销资料确认，相关内容需重新核验" : "资料已确认");
    } catch (e) {
      notify((e as Error).message, "error");
    }
  }
  return (
    <>
      <SectionTitle
        eyebrow="BRAND KNOWLEDGE / 品牌知识库"
        title="品牌知识库"
        description="记录真实的工艺、品牌与授权素材。生成内容只引用已确认的营销资料。"
        action={
          <Button
            onClick={() => {
              changeEditor(null);
            }}
          >
            <Plus size={17} />
            新增资料
          </Button>
        }
      />
      <div className="resource-summary">
        <span>
          <BookOpen size={21} />
          <strong>{data?.length || 0}</strong>份品牌资料
        </span>
        <span>
          <ShieldCheck size={20} />
          <strong>
            {data?.filter((k) => k.confirmed && k.usage_scope === "marketing")
              .length || 0}
          </strong>
          份可用于生成
        </span>
        <span className="summary-hint">确认是对事实与使用权限的核验</span>
      </div>
      <Panel
        title="资料档案"
        action={
          <div className="search-field">
            <Search size={16} />
            <input
              aria-label="搜索资料"
              placeholder="搜索标题、内容或来源"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        }
      >
        {loading ? (
          <Loading />
        ) : error ? (
          <Notice tone="error">{error}</Notice>
        ) : !data?.length ? (
          <Empty
            title="先为你的品牌留一份真实档案"
            description="从品牌介绍、工艺流程或授权素材开始。每份资料保留来源与使用范围。"
            action={
              <Button
                variant="secondary"
                onClick={() => {
                  changeEditor(null);
                }}
              >
                <Plus size={16} />
                添加第一份资料
              </Button>
            }
          />
        ) : !filteredKnowledge.length ? (
          <Empty
            title="没有匹配的资料"
            description="试试其他标题、内容或来源关键词。"
            action={
              <Button variant="secondary" onClick={() => setQuery("")}>
                清空搜索
              </Button>
            }
          />
        ) : (
          <div className="knowledge-grid">
            {filteredKnowledge.map((k) => (
              <article className="knowledge-card" key={k.id}>
                <AttachmentPreview fileId={k.file_id} label={k.title} />
                <div className="card-top">
                  <span className="resource-icon">
                    <FileText size={20} />
                  </span>
                  <Badge tone={k.confirmed ? "green" : "ochre"}>
                    {k.confirmed ? "已确认" : "待确认"}
                  </Badge>
                </div>
                <h3>{k.title}</h3>
                <p>{k.content}</p>
                <div className="source-line">来源：{k.source}</div>
                <div className="tag-row">
                  <Badge>
                    {
                      {
                        fact: "文化 / 工艺事实",
                        brand: "商家信息",
                        material: "素材",
                      }[k.kind]
                    }
                  </Badge>
                  <Badge>
                    {k.usage_scope === "marketing" ? "营销可用" : "仅内部"}
                  </Badge>
                </div>
                <footer>
                  <button className="text-button" onClick={() => toggle(k)}>
                    {k.confirmed ? "撤销确认" : "确认资料"}
                  </button>
                  {k.file_id && (
                    <button
                      className="icon-button"
                      aria-label="下载附件"
                      onClick={() =>
                        download(path("/files/" + k.file_id), "资料附件").catch(
                          (e) => notify(e.message, "error"),
                        )
                      }
                    >
                      <Download size={16} />
                    </button>
                  )}
                  <button
                    className="icon-button"
                    aria-label={"编辑" + k.title}
                    onClick={() => {
                      changeEditor(k);
                    }}
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    className="icon-button danger"
                    aria-label={"删除" + k.title}
                    onClick={() => setDeleting(k)}
                  >
                    <Trash2 size={16} />
                  </button>
                </footer>
              </article>
            ))}
          </div>
        )}
      </Panel>
      {editing !== undefined && (
        <Modal
          title={editing ? "编辑资料" : "新增品牌资料"}
          onClose={() => changeEditor(undefined)}
          wide
        >
          <Form
            fields={knowledgeFields}
            initial={editing || {}}
            onCancel={() => changeEditor(undefined)}
            onSubmit={async (d) => {
              if (uploading)
                throw new Error("附件正在上传，请上传完成后再保存");
              const savingSession = editSession.current;
              const payload = {
                ...d,
                ...(upload ? { file_id: upload.id } : {}),
              };
              if (editing)
                await patch(path("/knowledge/" + editing.id), payload);
              else await post(path("/knowledge"), payload);
              refresh();
              if (savingSession !== editSession.current) return;
              changeEditor(undefined);
              notify("资料已保存");
            }}
          >
            <label className="upload-area">
              <FileUp size={22} />
              <strong>
                {uploading
                  ? "正在上传…"
                  : upload?.name || "附加文档或图片（可选）"}
              </strong>
              <small>支持 UTF-8 TXT / CSV、PNG、JPEG、WebP，最大 10 MiB</small>
              <input
                type="file"
                accept=".txt,.csv,.png,.jpg,.jpeg,.webp,text/plain,text/csv,image/png,image/jpeg,image/webp"
                disabled={uploading}
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  if (f.size > 10 * 1024 * 1024) {
                    setUploadError("文件不能超过 10 MiB");
                    return;
                  }
                  const uploadSession = editSession.current;
                  const controller = new AbortController();
                  pendingUpload.current?.abort();
                  pendingUpload.current = controller;
                  const isCurrentUpload = () =>
                    editSession.current === uploadSession &&
                    pendingUpload.current === controller &&
                    !controller.signal.aborted;
                  setUploading(true);
                  setUploadError("");
                  try {
                    const form = new FormData();
                    form.append("file", f);
                    const result = await request<{ id: string; name: string }>(
                      path("/files"),
                      {
                        method: "POST",
                        body: form,
                        signal: controller.signal,
                      },
                    );
                    if (isCurrentUpload()) setUpload(result);
                  } catch (e) {
                    if (isCurrentUpload()) setUploadError((e as Error).message);
                  } finally {
                    if (isCurrentUpload()) {
                      setUploading(false);
                      pendingUpload.current = null;
                    }
                  }
                }}
              />
            </label>
            {uploadError && <Notice tone="error">{uploadError}</Notice>}
          </Form>
        </Modal>
      )}
      {deleting && (
        <Modal title="删除这份资料？" onClose={() => setDeleting(null)}>
          <p>
            “{deleting.title}
            ”将从知识库移除。历史版本保留记录，后续内容需要重新核验来源。
          </p>
          <Form
            fields={[]}
            submitLabel="确认删除"
            onCancel={() => setDeleting(null)}
            onSubmit={async () => {
              await request(path("/knowledge/" + deleting.id), {
                method: "DELETE",
              });
              setDeleting(null);
              refresh();
              notify("资料已删除");
            }}
          />
        </Modal>
      )}
    </>
  );
}
const offeringFields: Field[] = [
  {
    key: "kind",
    label: "承接类型",
    type: "select",
    options: [
      { value: "product", label: "手作产品 · 销售" },
      { value: "course", label: "体验课程 · 报名" },
    ],
  },
  { key: "name", label: "产品 / 课程名称", required: true },
  { key: "description", label: "介绍与特色", type: "textarea", required: true },
  {
    key: "price",
    label: "价格（元）",
    type: "number",
    min: 0,
    step: "0.01",
    required: true,
  },
  {
    key: "quantity",
    label: "库存 / 可报名名额",
    type: "number",
    min: 0,
    step: "1",
    required: true,
  },
  { key: "location", label: "地点 / 发货地", required: true },
  {
    key: "delivery",
    label: "履约方式 / 课程时间",
    required: true,
    placeholder: "如：3 天内发货 / 每周六 14:00 到店体验",
  },
  {
    key: "conversion_url",
    label: "购买 / 报名链接",
    type: "url",
    required: true,
    help: "商家真实的 https:// 承接入口；本平台不处理支付。",
  },
];
export function OfferingsPage() {
  const { path, epoch, refresh, notify } = useApp();
  const { data, loading, error } = useResource<Offering[]>(
    path("/offerings"),
    epoch,
  );
  const [editing, setEditing] = useState<Offering | null | undefined>(
      undefined,
    ),
    [filter, setFilter] = useState("all");
  return (
    <>
      <SectionTitle
        eyebrow="PRODUCTS & EXPERIENCES / 产品与课程"
        title="产品与课程"
        description="产品销售与课程报名分开管理，让每一次传播都有明确的承接入口。"
        action={
          <Button onClick={() => setEditing(null)}>
            <Plus size={17} />
            新增产品 / 课程
          </Button>
        }
      />
      <div className="tabs">
        <button
          className={filter === "all" ? "active" : ""}
          onClick={() => setFilter("all")}
        >
          全部内容 <span>{data?.length || 0}</span>
        </button>
        <button
          className={filter === "product" ? "active" : ""}
          onClick={() => setFilter("product")}
        >
          手作产品
        </button>
        <button
          className={filter === "course" ? "active" : ""}
          onClick={() => setFilter("course")}
        >
          体验课程
        </button>
      </div>
      {loading ? (
        <Loading />
      ) : error ? (
        <Notice tone="error">{error}</Notice>
      ) : !data?.length ? (
        <Panel>
          <Empty
            title="好产品与好课程，值得被认真介绍"
            description="添加售价、库存或名额、履约方式和真实承接链接，再将它关联到营销活动。"
            action={
              <Button variant="secondary" onClick={() => setEditing(null)}>
                <Plus size={16} />
                添加第一项
              </Button>
            }
          />
        </Panel>
      ) : (
        <div className="offering-grid">
          {data
            .filter((o) => filter === "all" || o.kind === filter)
            .map((o) => (
              <article className="offering-card" key={o.id}>
                <div className={"offering-visual " + o.kind}>
                  <span>
                    {o.kind === "course" ? (
                      <GraduationCap size={42} strokeWidth={1.2} />
                    ) : (
                      <Package size={42} strokeWidth={1.2} />
                    )}
                  </span>
                  <div className="offering-monogram">{o.name.slice(0, 2)}</div>
                  <Badge tone="light">
                    {o.kind === "course" ? "体验课程" : "手作产品"}
                  </Badge>
                </div>
                <div className="offering-body">
                  <div className="offering-heading">
                    <h3>{o.name}</h3>
                    <strong>{money(o.price)}</strong>
                  </div>
                  <p>{o.description}</p>
                  <dl>
                    <div>
                      <dt>{o.kind === "course" ? "可报名名额" : "当前库存"}</dt>
                      <dd>
                        {o.quantity}{" "}
                        {o.quantity === 0 && (
                          <Badge tone="ochre">
                            {o.kind === "course" ? "名额已满" : "暂无库存"}
                          </Badge>
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>地点</dt>
                      <dd>{o.location}</dd>
                    </div>
                    <div>
                      <dt>履约方式</dt>
                      <dd>{o.delivery}</dd>
                    </div>
                  </dl>
                  <footer>
                    <a href={o.conversion_url} target="_blank" rel="noreferrer">
                      查看{o.kind === "course" ? "报名" : "购买"}入口{" "}
                      <ExternalLink size={14} />
                    </a>
                    <Button
                      variant="secondary small"
                      onClick={() => setEditing(o)}
                    >
                      <Pencil size={14} />
                      编辑
                    </Button>
                  </footer>
                </div>
              </article>
            ))}
        </div>
      )}
      {editing !== undefined && (
        <Modal
          title={editing ? "编辑产品 / 课程" : "新增产品 / 课程"}
          onClose={() => setEditing(undefined)}
          wide
        >
          <Form
            fields={offeringFields}
            initial={editing || { price: 0, quantity: 0 }}
            onCancel={() => setEditing(undefined)}
            onSubmit={async (d) => {
              if (editing) await patch(path("/offerings/" + editing.id), d);
              else await post(path("/offerings"), d);
              setEditing(undefined);
              refresh();
              notify("产品 / 课程已保存");
            }}
          />
        </Modal>
      )}
    </>
  );
}
