import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type FormEvent,
} from "react";
import { X, LoaderCircle, ArrowRight, Inbox, AlertCircle } from "lucide-react";
export function Button({
  children,
  variant = "",
  busy = false,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: string;
  busy?: boolean;
}) {
  return (
    <button
      className={"button " + variant}
      {...props}
      disabled={props.disabled || busy}
    >
      {busy && <LoaderCircle size={16} className="spin" />}
      {children}
    </button>
  );
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
export function Status({ value }: { value: string }) {
  const labels: Record<string, string> = {
    draft: "待审核",
    approved: "已批准",
    rejected: "已退回",
    active: "进行中",
    queued: "排队中",
    running: "生成中",
    succeeded: "已完成",
    failed: "失败",
  };
  return (
    <Badge
      tone={
        value === "approved" || value === "succeeded"
          ? "green"
          : value === "rejected" || value === "failed"
            ? "red"
            : "ochre"
      }
    >
      {labels[value] || value}
    </Badge>
  );
}
export function Mode({ value }: { value: string }) {
  return (
    <Badge tone={value === "ai" ? "green" : "ochre"}>
      {value === "ai" ? "AI 生成" : "模板草稿"}
    </Badge>
  );
}
export function Empty({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Inbox size={28} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
export function Notice({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return (
    <div className={"notice " + tone}>
      <AlertCircle size={17} />
      <div>{children}</div>
    </div>
  );
}
export function SectionTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-title">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}
export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={"panel " + className}>
      {title && (
        <header className="panel-header">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
  className = "",
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const before = document.activeElement as HTMLElement;
    const prior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const el = ref.current;
    (
      el?.querySelector<HTMLElement>("[autofocus]") ||
      el?.querySelector<HTMLElement>("input,textarea,select") ||
      el?.querySelector<HTMLElement>("button")
    )?.focus({ preventScroll: true });
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && el) {
        const nodes = Array.from(
          el.querySelectorAll<HTMLElement>(
            "button:not([disabled]), input:not([disabled]),textarea:not([disabled]),select:not([disabled]),a[href]",
          ),
        );
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.body.style.overflow = prior;
      document.removeEventListener("keydown", key);
      before?.focus();
    };
  }, [onClose]);
  return (
    <div
      className="modal-scrim"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={"modal " + (wide ? "wide " : "") + className}
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <button
            className="icon-button"
            aria-label="关闭对话框"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}
export type Field = {
  key: string;
  label: string;
  type?: string;
  required?: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
  help?: string;
  min?: number;
  step?: string;
  defaultValue?: unknown;
};
export function Form({
  fields,
  initial = {},
  submitLabel = "保存",
  onSubmit,
  onCancel,
  children,
}: {
  fields: Field[];
  initial?: Record<string, unknown>;
  submitLabel?: string;
  onSubmit: (data: Record<string, any>) => Promise<void>;
  onCancel?: () => void;
  children?: ReactNode;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const form = e.currentTarget;
    const d = new FormData(form),
      out: Record<string, any> = {};
    fields.forEach((f) => {
      const value = d.get(f.key);
      out[f.key] =
        f.type === "checkbox"
          ? value === "on"
          : f.type === "number"
            ? Number(value)
            : value;
    });
    setBusy(true);
    try {
      await onSubmit(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="form">
      <div className="form-fields">
        {fields.map((f) => (
          <label
            className={"field " + (f.type === "textarea" ? "full" : "")}
            key={f.key}
          >
            <span>
              {f.label}
              {f.required && <b> *</b>}
            </span>
            {f.type === "textarea" ? (
              <textarea
                name={f.key}
                defaultValue={String(initial[f.key] ?? f.defaultValue ?? "")}
                required={f.required}
                placeholder={f.placeholder}
                rows={4}
              />
            ) : f.type === "select" ? (
              <select
                name={f.key}
                defaultValue={String(
                  initial[f.key] ??
                    f.defaultValue ??
                    f.options?.[0]?.value ??
                    "",
                )}
                required={f.required}
              >
                {f.options?.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            ) : f.type === "checkbox" ? (
              <input
                type="checkbox"
                name={f.key}
                defaultChecked={Boolean(initial[f.key] ?? f.defaultValue)}
              />
            ) : (
              <input
                name={f.key}
                type={f.type || "text"}
                defaultValue={String(initial[f.key] ?? f.defaultValue ?? "")}
                required={f.required}
                placeholder={f.placeholder}
                min={f.min}
                step={f.step}
                minLength={f.type === "password" ? 10 : undefined}
              />
            )}{" "}
            {f.help && <small>{f.help}</small>}
          </label>
        ))}
      </div>
      {children}
      {error && <Notice tone="error">{error}</Notice>}
      <footer className="form-actions">
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            取消
          </Button>
        )}
        <Button type="submit" busy={busy}>
          {submitLabel}
          <ArrowRight size={16} />
        </Button>
      </footer>
    </form>
  );
}
export function Loading() {
  return (
    <div className="loading">
      <LoaderCircle className="spin" size={25} />
      <span>正在读取工作台…</span>
    </div>
  );
}
export const money = (n: number = 0) =>
  "¥" +
  Number(n).toLocaleString("zh-CN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
export const num = (n: number = 0) => Number(n).toLocaleString("zh-CN");
export const date = (v: string) =>
  v
    ? new Date(v).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
