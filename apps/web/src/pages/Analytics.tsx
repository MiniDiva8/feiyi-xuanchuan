import { useState } from "react";
import {
  Plus,
  Upload,
  Download,
  ChartNoAxesCombined,
  ArrowUpRight,
  Eye,
  Coins,
  ShoppingBag,
  Users,
  FileSpreadsheet,
  Check,
} from "lucide-react";
import { useApp } from "../context";
import { useResource } from "../hooks";
import { post, saveBlob } from "../api";
import type { Analytics, Campaign, Metric, Publication } from "../types";
import { metricTemplate } from "../workflow.mjs";
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
  num,
  money,
  type Field,
} from "../components/UI";
const counts = [
  ["impressions", "曝光"],
  ["views", "播放"],
  ["reads", "阅读"],
  ["interactions", "互动"],
  ["inquiries", "咨询"],
  ["reservations", "预约"],
  ["leads", "线索"],
  ["orders", "订单"],
  ["registrations", "报名"],
  ["checkins", "到场"],
];
export default function AnalyticsPage() {
  const { path, epoch, refresh, notify, go } = useApp();
  const campaigns = useResource<Campaign[]>(path("/campaigns"), epoch),
    publications = useResource<Publication[]>(path("/publications"), epoch);
  const [selected, setSelected] = useState(""),
    [modal, setModal] = useState(""),
    [csv, setCsv] = useState(""),
    [previewSource, setPreviewSource] = useState(""),
    [preview, setPreview] = useState<{
      rows: Metric[];
      errors: { row: number; message: string }[];
      duplicates: number;
      valid_rows: number;
    } | null>(null),
    [csvBusy, setCsvBusy] = useState(false),
    [csvError, setCsvError] = useState("");
  const query = selected ? "?campaign_id=" + encodeURIComponent(selected) : "";
  const analytics = useResource<Analytics>(path("/analytics" + query), epoch),
    records = useResource<Metric[]>(path("/metrics" + query), epoch);
  const data = analytics.data;
  const campaignId = selected || campaigns.data?.[0]?.id || "";
  const fields: Field[] = [
    {
      key: "campaign_id",
      label: "所属活动",
      type: "select",
      required: true,
      options: (campaigns.data || []).map((c) => ({
        value: c.id,
        label: c.name,
      })),
    },
    {
      key: "publication_id",
      label: "关联发布记录（可选）",
      type: "select",
      options: [
        { value: "", label: "不关联发布记录" },
        ...(publications.data || []).map((p) => ({
          value: p.id,
          label: p.channel + " / " + p.url.slice(0, 40),
        })),
      ],
    },
    { key: "date", label: "统计日期", type: "date", required: true },
    {
      key: "channel",
      label: "统计渠道",
      required: true,
      placeholder: "小红书 / 微信公众号 / 门店等",
    },
    {
      key: "source",
      label: "数据来源",
      required: true,
      placeholder: "平台后台 / 商家订单表等",
    },
    {
      key: "attribution",
      label: "收入归因",
      type: "select",
      options: [
        { value: "unknown", label: "未知归因（不计为活动贡献）" },
        { value: "known", label: "有明确活动归因依据" },
      ],
    },
    {
      key: "external_id",
      label: "外部记录 ID（可选）",
      help: "同一来源记录保持 ID 一致，防止重复累计。",
    },
    ...counts.map(([key, label]) => ({
      key,
      label,
      type: "number",
      min: 0,
      step: "1",
    })),
    ...[
      ["revenue", "成交金额（元）"],
      ["refunds", "退款金额（元）"],
      ["spend", "实际花费（元）"],
    ].map(([key, label]) => ({
      key,
      label,
      type: "number",
      min: 0,
      step: "0.01",
    })),
  ];
  async function previewCsv() {
    setCsvBusy(true);
    setCsvError("");
    try {
      const submittedCsv = csv;
      const result = await post<typeof preview>(path("/metrics/preview"), {
        csv: submittedCsv,
      });
      setPreviewSource(submittedCsv);
      setPreview(result);
    } catch (e) {
      setCsvError((e as Error).message);
    } finally {
      setCsvBusy(false);
    }
  }
  return (
    <>
      <SectionTitle
        eyebrow="ANALYTICS & LEARNING / 数据与复盘"
        title="看见发生了什么，再讨论为什么。"
        description="统一记录渠道数据，保留来源与归因边界，用真实经营记录支持下一步判断。"
        action={
          <div className="inline">
            <Button
              variant="secondary"
              disabled={!campaignId}
              onClick={() => {
                setModal("csv");
                setPreview(null);
                setCsvError("");
              }}
            >
              <Upload size={16} />
              导入 CSV
            </Button>
            <Button disabled={!campaignId} onClick={() => setModal("manual")}>
              <Plus size={17} />
              录入指标
            </Button>
          </div>
        }
      />
      <div className="toolbar">
        <label className="inline-label">
          统计范围
          <select
            aria-label="选择数据活动"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">全部活动</option>
            {campaigns.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        {campaignId && (
          <button
            className="text-button"
            onClick={() => go("studio", campaignId)}
          >
            生成活动复盘 <ArrowUpRight size={16} />
          </button>
        )}
      </div>
      {analytics.error && <Notice tone="error">{analytics.error}</Notice>}
      {analytics.loading ? (
        <Loading />
      ) : (
        <>
          <div className="metrics-grid">
            {[
              {
                label: "累计曝光",
                value: num(data?.stats.impressions),
                icon: Eye,
                note: "已录入的渠道曝光合计",
              },
              {
                label: "净成交金额",
                value: money(data?.stats.net_revenue),
                icon: Coins,
                note: "成交减退款，不等于利润",
              },
              {
                label: "产品订单",
                value: num(data?.stats.orders),
                icon: ShoppingBag,
                note: "不同渠道录入订单合计",
              },
              {
                label: "课程报名",
                value: num(data?.stats.registrations),
                icon: Users,
                note: "到场 " + num(data?.stats.checkins) + " 人次",
              },
            ].map((m) => (
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
          <Notice>
            未知归因成交：{money(data?.stats.unknown_revenue)}；累计花费：
            {money(data?.stats.spend)}
            。没有完整成本与归因依据，不推算利润，也不把成交变化宣称为营销增量。
          </Notice>
          <div className="dashboard-columns">
            <Panel title="曝光趋势" subtitle="按统计日期汇总真实录入记录">
              {!data?.trends.length ? (
                <Empty
                  title="数据从第一条记录开始"
                  description="录入指标后，在这里观察实际变化。"
                />
              ) : (
                <div
                  className="trend-chart"
                  role="img"
                  aria-label="各日期曝光柱状图"
                >
                  {data.trends.map((t) => (
                    <div className="trend-col" key={t.date}>
                      <span>{num(t.impressions)}</span>
                      <div
                        style={{
                          height: Math.max(
                            3,
                            (t.impressions /
                              Math.max(
                                1,
                                ...data.trends.map((x) => x.impressions),
                              )) *
                              135,
                          ),
                        }}
                      />
                      <small>{t.date.slice(5)}</small>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
            <Panel
              title="渠道表现"
              subtitle="用于比较已录入数据，不代表因果归因"
            >
              {!data?.channels.length ? (
                <div className="quiet-empty">暂无渠道记录</div>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>渠道</th>
                        <th>曝光</th>
                        <th>互动</th>
                        <th>成交</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.channels.map((ch) => (
                        <tr key={ch.channel}>
                          <td>
                            <Badge>{ch.channel}</Badge>
                          </td>
                          <td>{num(ch.impressions)}</td>
                          <td>{num(ch.interactions)}</td>
                          <td>{money(ch.revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Panel>
          </div>
        </>
      )}
      <Panel
        title="指标明细"
        subtitle={(data?.records || 0) + " 条来源可追溯的统计记录"}
        action={
          <Button
            variant="ghost small"
            disabled={!campaignId}
            onClick={() =>
              saveBlob(
                new Blob([metricTemplate(campaignId)], {
                  type: "text/csv;charset=utf-8",
                }),
                "指标导入模板.csv",
              )
            }
          >
            <Download size={15} />
            下载模板
          </Button>
        }
      >
        {records.loading ? (
          <Loading />
        ) : records.error ? (
          <Notice tone="error">{records.error}</Notice>
        ) : !records.data?.length ? (
          <Empty
            title="还没有录入经营数据"
            description="支持手动录入与 CSV 批量导入。先预检再确认，重复记录不会再次累计。"
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>日期 / 渠道</th>
                  <th>所属活动</th>
                  <th>曝光</th>
                  <th>互动</th>
                  <th>订单 / 报名</th>
                  <th>成交 / 退款</th>
                  <th>花费</th>
                  <th>来源 / 归因</th>
                </tr>
              </thead>
              <tbody>
                {records.data.map((r, i) => (
                  <tr key={String(r.id || i)}>
                    <td>
                      {String(r.date)}
                      <small className="table-sub">{String(r.channel)}</small>
                    </td>
                    <td>
                      {campaigns.data?.find((c) => c.id === r.campaign_id)
                        ?.name || String(r.campaign_id).slice(0, 8)}
                    </td>
                    <td>{num(Number(r.impressions))}</td>
                    <td>{num(Number(r.interactions))}</td>
                    <td>
                      {num(Number(r.orders))} / {num(Number(r.registrations))}
                    </td>
                    <td>
                      {money(Number(r.revenue))}
                      <small className="table-sub">
                        退款 {money(Number(r.refunds))}
                      </small>
                    </td>
                    <td>{money(Number(r.spend))}</td>
                    <td>
                      {String(r.source)}
                      <small className="table-sub">
                        {r.attribution === "known" ? "明确归因" : "归因未知"}
                      </small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      {modal === "manual" && (
        <Modal title="手动录入指标" onClose={() => setModal("")} wide>
          <Form
            fields={fields}
            initial={{
              campaign_id: campaignId,
              date: new Date().toISOString().slice(0, 10),
              ...Object.fromEntries(
                [...counts.map(([k]) => k), "revenue", "refunds", "spend"].map(
                  (k) => [k, 0],
                ),
              ),
            }}
            onCancel={() => setModal("")}
            onSubmit={async (d) => {
              if (d.refunds > d.revenue)
                throw new Error("退款不能超过成交金额");
              if (d.checkins > d.registrations)
                throw new Error("到场不能超过报名人数");
              await post(path("/metrics"), {
                ...d,
                publication_id: d.publication_id || null,
              });
              setModal("");
              refresh();
              notify("真实指标已保存");
            }}
          >
            <Notice>
              关联发布记录必须属于所选活动。未知归因收入会单独标记。
            </Notice>
          </Form>
        </Modal>
      )}
      {modal === "csv" && (
        <Modal
          title="CSV 批量导入 · 先预检，再确认"
          onClose={() => setModal("")}
          wide
        >
          <div className="csv-workspace">
            <div className="inline">
              <Button
                variant="secondary"
                onClick={() =>
                  saveBlob(
                    new Blob([metricTemplate(campaignId)], {
                      type: "text/csv;charset=utf-8",
                    }),
                    "指标导入模板.csv",
                  )
                }
              >
                <Download size={15} />
                下载当前活动模板
              </Button>
              <label className="button secondary">
                <FileSpreadsheet size={15} />
                选择 CSV
                <input
                  className="visually-hidden"
                  type="file"
                  disabled={csvBusy}
                  accept=".csv,text/csv"
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (f) {
                      setCsv(await f.text());
                      setPreview(null);
                    }
                  }}
                />
              </label>
            </div>
            <label className="field full">
              <span>CSV 内容</span>
              <textarea
                disabled={csvBusy}
                rows={8}
                value={csv}
                onChange={(e) => {
                  setCsv(e.target.value);
                  setPreview(null);
                }}
                placeholder="粘贴含字段名的 CSV，或选择文件"
              />
            </label>
            <Notice>
              字段使用英文 API 键名；模板已包含当前活动 ID。统计区间按 date
              填写，外部 ID 或规范化内容用于去重。
            </Notice>
            {csvError && <Notice tone="error">{csvError}</Notice>}
            <Button
              variant="secondary"
              disabled={!csv.trim()}
              busy={csvBusy}
              onClick={previewCsv}
            >
              运行导入预检
            </Button>
            {preview && (
              <div className="csv-preview">
                <div className="preview-stats">
                  <Badge tone="green">{preview.valid_rows} 条有效</Badge>
                  <Badge>{preview.duplicates} 条重复</Badge>
                  <Badge tone={preview.errors.length ? "red" : "green"}>
                    {preview.errors.length} 个错误
                  </Badge>
                </div>
                {preview.errors.map((e, i) => (
                  <Notice tone="error" key={i}>
                    第 {e.row} 行：{e.message}
                  </Notice>
                ))}
                {preview.rows.length > 0 && (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>日期</th>
                          <th>渠道</th>
                          <th>来源</th>
                          <th>曝光</th>
                          <th>成交</th>
                        </tr>
                      </thead>
                      <tbody>
                        {preview.rows.slice(0, 20).map((r, i) => (
                          <tr key={i}>
                            <td>{String(r.date)}</td>
                            <td>{String(r.channel)}</td>
                            <td>{String(r.source)}</td>
                            <td>{String(r.impressions)}</td>
                            <td>{money(Number(r.revenue))}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <small>预览前 20 行；确认时全量校验后事务提交。</small>
                <Button
                  disabled={
                    preview.errors.length > 0 ||
                    preview.valid_rows === 0 ||
                    csv !== previewSource
                  }
                  busy={csvBusy}
                  onClick={async () => {
                    setCsvBusy(true);
                    setCsvError("");
                    try {
                      const r = await post<{
                        imported: number;
                        duplicates: number;
                      }>(path("/metrics/import"), { csv: previewSource });
                      refresh();
                      notify(
                        "导入 " +
                          r.imported +
                          " 条，跳过 " +
                          r.duplicates +
                          " 条重复记录",
                      );
                      setModal("");
                      setCsv("");
                    } catch (e) {
                      setCsvError((e as Error).message);
                    } finally {
                      setCsvBusy(false);
                    }
                  }}
                >
                  <Check size={16} />
                  确认导入
                </Button>
              </div>
            )}
          </div>
        </Modal>
      )}
    </>
  );
}
