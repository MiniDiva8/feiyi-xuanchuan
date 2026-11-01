import { ArrowRight, CheckCircle2 } from "lucide-react";
import { useApp } from "../context";
import { useResource } from "../hooks";
import type { Knowledge, Offering, Overview } from "../types";
import { preparation } from "../preparation.mjs";
import { Badge, Button, Notice, Panel } from "./UI";

export default function Preparation({ overview }: { overview: Overview }) {
  const { path, epoch, go } = useApp();
  const knowledge = useResource<Knowledge[]>(path("/knowledge"), epoch);
  const offerings = useResource<Offering[]>(path("/offerings"), epoch);
  const loading = knowledge.loading || offerings.loading;
  const error = knowledge.error || offerings.error;
  const state = preparation(knowledge.data || [], offerings.data || []);
  const steps = [
    { title: "确认宣传资料", done: state.confirmed > 0, page: "knowledge",
      text: state.confirmed > 0 ? `${state.confirmed} 份已确认且可用于营销的资料` : "添加真实资料，填写来源，并确认允许用于营销。" },
    { title: "准备购买或报名入口", done: state.available > 0, page: "offerings",
      text: state.available > 0 ? `${state.available} 项商品或课程有库存 / 名额及有效入口` : "补齐商品库存或课程名额，以及购买 / 报名链接；纯品牌宣传可跳过。" },
    { title: "创建活动并审核内容", done: overview.stats.campaigns > 0, page: "campaigns",
      text: overview.stats.campaigns > 0 ? "已有活动，可进入工作室继续策划和审核；创建活动不代表审核通过。" : "设定目标、周期和预算，生成方案后批准具体版本。" },
    { title: "发布后登记作品", done: overview.stats.publications > 0, page: "publications",
      text: overview.stats.publications > 0 ? "已有发布记录，继续录入真实效果数据并复盘。" : "审核并导出素材，到渠道手动发布，再登记作品链接。" },
  ];
  const next = steps.find((step) => !step.done);
  return (
    <Panel title="开始一次真实的营销活动" subtitle="准备状态随当前商家资料更新；各步骤可按活动目标选择。">
      {loading ? <p role="status">正在检查准备情况…</p> : error ? (
        <Notice tone="error">
          无法读取准备情况：{error}
          <Button variant="secondary" onClick={() => { knowledge.reload(); offerings.reload(); }}>重新检查</Button>
        </Notice>
      ) : (
        <>
          <div className="preparation-list">
            {steps.map((step, index) => (
              <button key={step.page} className="preparation-step" onClick={() => go(step.page)}>
                <span className="step-number">{step.done ? <CheckCircle2 size={20} aria-label="已具备" /> : `0${index + 1}`}</span>
                <span className="preparation-copy"><strong>{step.title}</strong><small>{step.text}</small></span>
                <Badge tone={step.done ? "green" : "ochre"}>{step.done ? "已具备" : "去准备"}</Badge>
              </button>
            ))}
          </div>
          <div className="preparation-next">
            <span>{overview.connections.ai_configured ? "AI 配置已填写，实际可用性以生成结果为准。" : "当前生成模板草稿；配置 AI 后可使用真实模型。"}</span>
            <Button variant="secondary" onClick={() => go(next?.page || "analytics")}>
              {next ? `下一步：${next.title}` : "录入效果与复盘"}<ArrowRight size={16} />
            </Button>
          </div>
        </>
      )}
    </Panel>
  );
}
