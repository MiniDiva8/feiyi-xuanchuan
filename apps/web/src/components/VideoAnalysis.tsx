import { useEffect, useRef, useState, type FormEvent } from "react";
import { request } from "../api";
import { useApp } from "../context";
import { useResource } from "../hooks";
import { ContentChecks } from "./ContentPreview";
import { Badge, Button, date, Loading, Notice, Panel } from "./UI";
import "./video-analysis.css";

type TimedText = { start_ms: number; end_ms: number; text: string };
type Suggestion = {
  kind: "hook" | "cut" | "subtitle";
  start_ms: number;
  end_ms: number;
  evidence: string;
  suggestion: string;
};
type Report = {
  id: string;
  filename: string;
  created_at: string;
  duration_ms: number;
  has_audio: boolean;
  sample_times_ms: number[];
  transcript: TimedText[];
  summary: string;
  suggestions: Suggestion[];
  limitations: string[];
  checks: { level: string; message: string }[];
};

const labels = { hook: "开头", cut: "剪辑", subtitle: "字幕" };
const maxBytes = 40 * 1024 * 1024;

function timecode(ms: number) {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const base = [minutes, seconds % 60]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");
  return ms % 1000 ? base + "." + Math.floor((ms % 1000) / 100) : base;
}

export default function VideoAnalysis({ campaignId }: { campaignId: string }) {
  const { path, workspace } = useApp();
  const endpoint = path(
    "/campaigns/" + encodeURIComponent(campaignId) + "/video-analyses",
  );
  const history = useResource<{ available: boolean; items: Report[] }>(
    endpoint,
  );
  const canEdit = workspace.role === "owner" || workspace.role === "editor";
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recent, setRecent] = useState<Report | null>(null);
  const [selected, setSelected] = useState("");
  const [previewReport, setPreviewReport] = useState("");
  const player = useRef<HTMLVideoElement>(null);
  const reports = [
    ...(recent ? [recent] : []),
    ...(history.data?.items || []).filter((item) => item.id !== recent?.id),
  ];
  const report = reports.find((item) => item.id === selected) ?? reports[0];

  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !consent || !history.data?.available || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await request<Report>(endpoint + "?consent=true", {
        method: "POST",
        headers: {
          "Content-Type": "application/octet-stream",
          "X-Video-Filename": encodeURIComponent(file.name),
        },
        body: file,
      });
      setRecent(result);
      setSelected(result.id);
      setPreviewReport(result.id);
      history.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function jumpTo(ms: number) {
    if (!player.current || !Number.isFinite(player.current.duration)) return;
    player.current.currentTime = Math.min(ms / 1000, player.current.duration);
    player.current.focus();
  }

  return (
    <div className="video-analysis">
      <Panel
        title="成片分析"
        subtitle="上传短视频，查看带时间点的开头、剪辑和字幕建议。"
      >
        {canEdit ? (
          <form className="video-analysis-body" onSubmit={analyze}>
            <label>
              <strong>选择视频</strong>
              <input
                type="file"
                accept=".mp4,.mov,video/mp4,video/quicktime"
                disabled={busy}
                onChange={(event) => {
                  const choice = event.target.files?.[0] ?? null;
                  setConsent(false);
                  setPreviewReport("");
                  setError("");
                  if (
                    choice &&
                    (!/\.(mp4|mov)$/i.test(choice.name) ||
                      choice.size === 0 ||
                      choice.size > maxBytes)
                  ) {
                    setFile(null);
                    event.target.value = "";
                    setError("请选择不超过 40 MiB 的 MP4 或 MOV 文件。");
                    return;
                  }
                  setFile(choice);
                }}
              />
            </label>
            <p className="video-analysis-hint">
              支持 MP4、MOV，最长 90 秒，最大 40
              MiB。原视频仅用于本次分析，工作台保存报告和转写。
            </p>
            {preview && (
              <video
                ref={player}
                src={preview}
                controls
                preload="metadata"
                aria-label="原视频预览"
              />
            )}
            <label className="video-analysis-consent">
              <input
                type="checkbox"
                checked={consent}
                disabled={!file || busy}
                onChange={(event) => setConsent(event.target.checked)}
              />
              我有权分析该视频，并同意将采样画面、转写和相关活动资料发送给
              DeepSeek。
            </label>
            {history.data && !history.data.available && (
              <Notice>服务器需要启用 DeepSeek 官方视频分析配置。</Notice>
            )}
            {error && (
              <div role="alert">
                <Notice tone="error">{error}</Notice>
              </div>
            )}
            <div>
              <Button
                type="submit"
                busy={busy}
                disabled={!file || !consent || !history.data?.available}
              >
                {busy ? "正在分析…" : "开始视频分析"}
              </Button>
              {busy && (
                <p className="video-analysis-hint" role="status">
                  正在提取画面、转写口播并生成建议。首次转写可能需要下载语音模型。
                </p>
              )}
            </div>
          </form>
        ) : (
          <div className="video-analysis-body">
            <Notice>
              编辑者和管理员可以提交视频，你可以查看已保存的报告。
            </Notice>
          </div>
        )}
      </Panel>
      {history.error && (
        <Notice tone="error">
          {history.error}{" "}
          <Button type="button" variant="secondary" onClick={history.reload}>
            重试
          </Button>
        </Notice>
      )}
      {history.loading && !report && <Loading />}
      {report && (
        <Panel
          title="分析报告"
          subtitle={report.filename + " · " + timecode(report.duration_ms)}
        >
          <div className="video-analysis-body">
            {reports.length > 1 && (
              <label>
                历史报告
                <select
                  value={report.id}
                  onChange={(event) => setSelected(event.target.value)}
                >
                  {reports.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.filename} · {date(item.created_at)}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <p>{report.summary}</p>
            <p className="video-analysis-hint">
              根据 {report.sample_times_ms.length}{" "}
              个采样画面及可辨识的口播生成，请结合原片复核。
            </p>
            {report.suggestions.length === 0 && (
              <Notice>本次未发现有充分依据的剪辑或字幕问题。</Notice>
            )}
            <ol className="video-analysis-list">
              {report.suggestions.map((item, index) => (
                <li key={index}>
                  <div className="inline">
                    <Badge tone="green">{labels[item.kind]}</Badge>
                    {report.id === previewReport ? (
                      <button
                        className="text-button"
                        type="button"
                        onClick={() => jumpTo(item.start_ms)}
                      >
                        {timecode(item.start_ms)}–{timecode(item.end_ms)}
                      </button>
                    ) : (
                      <span>
                        {timecode(item.start_ms)}–{timecode(item.end_ms)}
                      </span>
                    )}
                  </div>
                  <p>{item.suggestion}</p>
                  <p className="video-analysis-hint">依据 · {item.evidence}</p>
                </li>
              ))}
            </ol>
            <details>
              <summary>口播转写（{report.transcript.length} 段）</summary>
              {report.transcript.length ? (
                <ol className="video-analysis-transcript">
                  {report.transcript.map((item, index) => (
                    <li key={index}>
                      <strong>
                        {timecode(item.start_ms)}–{timecode(item.end_ms)}
                      </strong>{" "}
                      {item.text}
                    </li>
                  ))}
                </ol>
              ) : (
                <p>
                  {report.has_audio ? "未识别到清晰口播。" : "视频没有音轨。"}
                </p>
              )}
            </details>
            {report.checks.length > 0 && (
              <ContentChecks checks={report.checks} />
            )}
            {report.limitations.length > 0 && (
              <details>
                <summary>需要人工确认的地方</summary>
                <ul>
                  {report.limitations.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        </Panel>
      )}
    </div>
  );
}
