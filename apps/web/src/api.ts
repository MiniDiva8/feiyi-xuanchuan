export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const multipart = options.body instanceof FormData;
  const response = await fetch("/api" + path, {
    ...options,
    credentials: "include",
    headers: {
      ...(!multipart && options.body
        ? { "Content-Type": "application/json" }
        : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = "服务暂时不可用，请稍后重试";
    try {
      const data = await response.json();
      message =
        typeof data.detail === "string"
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail.map((x: { msg?: string }) => x.msg).join("；")
            : message;
    } catch {}
    if (response.status === 401) message = "登录已过期，请重新登录";
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}
export const post = <T>(path: string, body: unknown = {}) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export function workspacePath(id: string, path: string) {
  return "/workspaces/" + encodeURIComponent(id) + path;
}
export async function download(path: string, name: string) {
  const response = await fetch("/api" + path, { credentials: "include" });
  if (!response.ok) {
    const d = await response.json().catch(() => ({ detail: "下载失败" }));
    throw new ApiError(d.detail || "下载失败", response.status);
  }
  saveBlob(await response.blob(), name);
}
export function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function downloadPosterPng(path: string, name: string) {
  const response = await fetch("/api" + path, { credentials: "include" });
  if (!response.ok) {
    const d = await response.json().catch(() => ({ detail: "海报下载失败" }));
    throw new ApiError(d.detail || "海报下载失败", response.status);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  try {
    const picture = new Image();
    await new Promise<void>((resolve, reject) => {
      picture.onload = () => resolve();
      picture.onerror = () => reject(new Error("海报图片转换失败，可导出 SVG"));
      picture.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = picture.naturalWidth || 1080;
    canvas.height = picture.naturalHeight || 1440;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("浏览器不支持图片转换");
    ctx.drawImage(picture, 0, 0);
    const png = await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob(
        (v) => (v ? resolve(v) : reject(new Error("PNG 生成失败"))),
        "image/png",
      ),
    );
    saveBlob(png, name);
  } finally {
    URL.revokeObjectURL(url);
  }
}
