import { useEffect, useRef, useState } from "react";
import { FileText, Image as ImageIcon } from "lucide-react";
import { useApp } from "../context";
export default function AttachmentPreview({
  fileId,
  label,
}: {
  fileId?: string;
  label: string;
}) {
  const { path } = useApp();
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const endpoint = fileId ? path("/files/" + encodeURIComponent(fileId)) : "";
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (!("IntersectionObserver" in window)) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "120px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    setUrl("");
    if (!endpoint || !visible) return;
    const controller = new AbortController();
    let objectUrl = "";
    setLoading(true);
    fetch("/api" + endpoint, {
      credentials: "include",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) return;
        const blob = await response.blob();
        if (
          controller.signal.aborted ||
          !["image/png", "image/jpeg", "image/webp"].includes(blob.type)
        )
          return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {})
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [endpoint, visible]);
  return (
    <div
      ref={ref}
      className={"attachment-cover " + (url ? "with-image" : "")}
      aria-busy={loading}
    >
      {url ? (
        <img src={url} alt={label + "的资料附件预览"} loading="lazy" />
      ) : (
        <>
          <span className="cover-lines" aria-hidden="true" />
          <span className="cover-symbol">
            {fileId ? (
              <ImageIcon size={28} strokeWidth={1.2} />
            ) : (
              <FileText size={28} strokeWidth={1.2} />
            )}
          </span>
          <span className="cover-type">
            {loading ? "读取附件…" : fileId ? "品牌资料附件" : "文字与来源档案"}
          </span>
        </>
      )}
    </div>
  );
}
