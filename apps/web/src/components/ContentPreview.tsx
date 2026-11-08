import { bodyLines, evidenceEntries, groupChecks } from "./content.mjs";
import "./content-preview.css";

/** The editable/exported body is the only source; structured generation snapshots may be stale. */
export default function ContentPreview({
  body,
  kind,
}: {
  body: string;
  kind: string;
}) {
  const labels: Record<string, string> = {
    copy: "渠道文案",
    script: "短视频脚本",
    poster: "海报文案",
  };
  const label = Object.hasOwn(labels, kind) ? labels[kind] : "素材正文";
  return (
    <section
      className={
        "content-preview " + (kind === "script" ? "content-preview-script" : "")
      }
      aria-label={label.endsWith("正文") ? label : label + "正文"}
    >
      <div className="content-preview-heading">
        <strong>{label}</strong>
        <span>完整正文</span>
      </div>
      {body === "" ? (
        <p className="content-preview-empty">本版本暂无正文。</p>
      ) : (
        <div className="content-preview-body">
          {bodyLines(body).map(
            (line: { text: string; ending: string }, index: number) => (
              <span key={index}>
                {line.text}
                {line.ending}
              </span>
            ),
          )}
        </div>
      )}
      {kind === "poster" && (
        <p className="content-preview-note">
          实拍照片与完整排版可在“照片与海报设计”中预览。
        </p>
      )}
    </section>
  );
}

export function ContentChecks({
  checks,
}: {
  checks: { level: string; message: string }[];
}) {
  const groups = groupChecks(checks);
  return (
    <section className="content-checks" aria-label="本版本核对事项">
      <h3>核对事项</h3>
      {!groups.length ? (
        <p>本版本未提供核对项，仍需人工审核。</p>
      ) : (
        groups.map(
          (group: {
            level: string;
            label: string;
            checks: { level: string; message: string }[];
          }) => (
            <div
              className={
                "content-check-group " +
                (group.level === "error"
                  ? "content-check-error"
                  : group.level === "warning"
                    ? "content-check-warning"
                    : "")
              }
              key={group.level}
            >
              <div className="content-check-label">
                <strong>{group.label}</strong>
                <span>{group.level || "未标级别"}</span>
              </div>
              <ul>
                {group.checks.map((check, index) => (
                  <li key={index}>{check.message}</li>
                ))}
              </ul>
            </div>
          ),
        )
      )}
    </section>
  );
}

export function ContentEvidence({ value }: { value: unknown }) {
  return (
    <dl className="content-evidence" aria-label="记录依据">
      {evidenceEntries(value).map(
        (entry: { label: string; value: string }, index: number) => (
          <div key={index}>
            <dt>{entry.label}</dt>
            <dd>{entry.value}</dd>
          </div>
        ),
      )}
    </dl>
  );
}
