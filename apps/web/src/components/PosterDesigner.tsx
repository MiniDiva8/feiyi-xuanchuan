import { useEffect, useRef, useState } from "react";
import { useApp } from "../context";
import { request } from "../api";
import type { Asset } from "../types";
import { Button, Modal, Notice } from "./UI";

export default function PosterDesigner({ asset }: { asset: Asset }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="secondary small" onClick={() => setOpen(true)}>
        照片与海报设计
      </Button>
      {open && (
        <Editor key={asset.id} asset={asset} close={() => setOpen(false)} />
      )}
    </>
  );
}

function Editor({ asset, close }: { asset: Asset; close: () => void }) {
  const { path, refresh, notify } = useApp();
  const [title, setTitle] = useState(asset.title),
    [body, setBody] = useState(asset.body);
  const [template, setTemplate] = useState(
    String(asset.content.poster_template || "heritage"),
  );
  const [imageId, setImageId] = useState<string | null>(
    typeof asset.content.poster_image_id === "string"
      ? asset.content.poster_image_id
      : null,
  );
  const [confirmed, setConfirmed] = useState(
    Boolean(asset.content.photo_confirmed),
  );
  const [busy, setBusy] = useState(""),
    [error, setError] = useState("");
  const [preview, setPreview] = useState("");
  const pending = useRef<AbortController | null>(null);
  const previewUrl = useRef("");
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      pending.current?.abort();
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    };
  }, []);
  function invalidate() {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = "";
    setPreview("");
  }
  async function act(kind: string, fn: (signal: AbortSignal) => Promise<void>) {
    if (busy) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(kind);
    setError("");
    try {
      await fn(controller.signal);
    } catch (e) {
      if (mounted.current && !controller.signal.aborted)
        setError((e as Error).message);
    } finally {
      if (mounted.current) {
        setBusy("");
        pending.current = null;
      }
    }
  }
  const payload = () => ({
    title,
    body,
    poster_template: template,
    poster_image_id: imageId,
    photo_confirmed: confirmed,
  });
  return (
    <Modal
      title="实拍照片 · 海报设计"
      onClose={close}
      wide
      className="poster-modal"
    >
      <form
        className="form poster-designer-form"
        onSubmit={(event) => {
          event.preventDefault();
          void act("save", async (signal) => {
            await request(path(`/assets/${asset.id}/revise`), {
              method: "POST",
              body: JSON.stringify(payload()),
              signal,
            });
            if (!mounted.current) return;
            refresh();
            notify("海报已保存为新版本，请审核后导出");
            close();
          });
        }}
      >
        <div className="poster-workspace">
          <div className="poster-controls">
            <Notice>
              使用真实照片和 AI
              文案排版，不会生成或改变商品外观。保存后创建新的待审核版本，原审核不会沿用。
            </Notice>
            <fieldset disabled={Boolean(busy)} className="poster-editor-fields">
              <label className="field">
                <span>海报模板</span>
                <select
                  value={template}
                  onChange={(e) => {
                    setTemplate(e.target.value);
                    invalidate();
                  }}
                >
                  <option value="heritage">雅绿 · 非遗工坊</option>
                  <option value="warm">暖陶 · 手作体验</option>
                  <option value="minimal">留白 · 产品展示</option>
                </select>
              </label>
              <label className="field">
                <span>标题</span>
                <input
                  required
                  maxLength={500}
                  value={title}
                  onChange={(e) => {
                    setTitle(e.target.value);
                    invalidate();
                  }}
                />
              </label>
              <label className="field">
                <span>海报文案</span>
                <textarea
                  required
                  maxLength={50000}
                  rows={6}
                  value={body}
                  onChange={(e) => {
                    setBody(e.target.value);
                    invalidate();
                  }}
                />
              </label>
              <label className="upload-area">
                <strong>
                  {imageId
                    ? "照片已附加，可重新选择"
                    : "上传商品或体验课程实拍照片"}
                </strong>
                <small>PNG / JPEG / WebP，最大 10 MiB；按原比例展示</small>
                <input
                  aria-label="上传海报照片"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    e.target.value = "";
                    if (!file) return;
                    if (file.size > 10 * 1024 * 1024) {
                      setError("照片不能超过 10 MiB");
                      return;
                    }
                    if (
                      !["image/png", "image/jpeg", "image/webp"].includes(
                        file.type,
                      )
                    ) {
                      setError("请选择 PNG、JPEG 或 WebP 图片");
                      return;
                    }
                    void act("upload", async (signal) => {
                      const form = new FormData();
                      form.append("file", file);
                      const result = await request<{ id: string }>(
                        path("/files"),
                        {
                          method: "POST",
                          body: form,
                          signal,
                        },
                      );
                      if (!mounted.current) return;
                      setImageId(result.id);
                      setConfirmed(false);
                      invalidate();
                    });
                  }}
                />
              </label>
              {imageId && (
                <>
                  <label className="poster-consent">
                    <input
                      type="checkbox"
                      checked={confirmed}
                      onChange={(e) => {
                        setConfirmed(e.target.checked);
                        invalidate();
                      }}
                    />
                    我确认照片真实，并有权将其用于本次宣传
                  </label>
                  <Button
                    type="button"
                    variant="secondary small"
                    onClick={() => {
                      setImageId(null);
                      setConfirmed(false);
                      invalidate();
                    }}
                  >
                    移除照片
                  </Button>
                </>
              )}
            </fieldset>
          </div>
          <aside className="poster-canvas" aria-label="海报预览区">
            <div className="poster-canvas-head">
              <strong>版式预览</strong>
              <span className="badge ochre">待审核预览</span>
            </div>
            <figure className="poster-preview">
              {preview ? (
                <img src={preview} alt="当前编辑海报预览，待审核" />
              ) : (
                <div className="poster-placeholder">
                  <span>艺</span>
                  <strong>在这里，看见你的作品</strong>
                  <p>
                    选择模板并填写文案，点击“生成预览”。修改内容后需要重新预览。
                  </p>
                </div>
              )}
            </figure>
            <p className="poster-preview-note">
              实拍照片按原比例排版。预览不会发布；保存并审核新版本后，可导出 SVG
              / PNG。
            </p>
          </aside>
        </div>
        {error && <Notice tone="error">{error}</Notice>}
        <div className="form-actions">
          <Button
            type="button"
            variant="secondary"
            disabled={Boolean(busy) || Boolean(imageId && !confirmed)}
            busy={busy === "preview"}
            onClick={() =>
              void act("preview", async (signal) => {
                const response = await fetch(
                  "/api" + path(`/assets/${asset.id}/preview`),
                  {
                    method: "POST",
                    credentials: "include",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload()),
                    signal,
                  },
                );
                if (!response.ok) {
                  const result = await response.json();
                  throw new Error(
                    typeof result.detail === "string"
                      ? result.detail
                      : "预览失败，请检查标题和文案",
                  );
                }
                const blob = await response.blob();
                if (!mounted.current) return;
                invalidate();
                previewUrl.current = URL.createObjectURL(blob);
                setPreview(previewUrl.current);
              })
            }
          >
            生成预览
          </Button>
          <Button
            type="submit"
            busy={busy === "save"}
            disabled={Boolean(busy) || Boolean(imageId && !confirmed)}
          >
            保存新版本
          </Button>
        </div>
      </form>
    </Modal>
  );
}
