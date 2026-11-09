"""Native SVG poster layout; only reviewed text is injected, always XML-escaped."""

from html import escape
import unicodedata


def _lines(text: str, units: int) -> list[str]:
    result = []
    for paragraph in str(text).splitlines() or [""]:
        current, width = "", 0
        for char in paragraph:
            size = 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
            if (
                width + size > units
                and current
                and char not in "。，、：；！？）】》”’%"
            ):
                result.append(current)
                current, width = "", 0
            current += char
            width += size
        result.append(current)
    return result


def render_poster(
    title: str, body: str, channel: str = "", workspace_name: str = "",
    template: str = "heritage", photo: str | None = None, approved: bool = True,
) -> str:
    titles = _lines(title, 28)
    lines = _lines(body, 64)
    body_y = 300 + len(titles) * 76
    photo_y = body_y - 25
    if photo:
        body_y += 570
    bottom = body_y + len(lines) * 43 + 85
    height = max(1440, bottom + 230)
    footer_y = height - 180
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{height}" viewBox="0 0 1080 {height}">',
        '<defs><pattern id="paper" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="2" cy="3" r=".7" fill="#284d45" opacity=".05"/></pattern></defs>',
        f'<rect width="1080" height="{height}" fill="#f5f1e7"/>',
        f'<rect width="1080" height="{height}" fill="url(#paper)"/>',
        f'<rect x="30" y="30" width="1020" height="{height-60}" rx="4" fill="none" stroke="#bdc8b7"/>',
        '<path d="M72 168V72H168M912 72H1008V168" stroke="#235b4d" stroke-width="3" fill="none"/>',
        '<g fill="none" stroke="#c7c8ab" stroke-width="1.4" opacity=".65"><circle cx="958" cy="290" r="165"/><circle cx="958" cy="290" r="142"/><circle cx="958" cy="290" r="119"/><path d="M830 180L1040 390M830 390L1040 180"/></g>',
        '<rect x="90" y="95" width="63" height="63" rx="7" fill="#235b4d"/>',
        '<text x="121.5" y="140" font-size="39" text-anchor="middle" fill="#f5f1e7">艺</text>',
        '<text x="176" y="119" font-size="17" letter-spacing="4" fill="#507665">HERITAGE STUDIO</text>',
        '<text x="176" y="151" font-size="22" fill="#235b4d">手艺与日常 · 让匠心被看见</text>',
        '<g font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
    ]
    for index, line in enumerate(titles):
        parts.append(
            f'<text x="90" y="{265+index*76}" font-size="56" font-weight="700" fill="#163f36">{escape(line)}</text>'
        )
    divider = body_y - 35
    if photo:
        parts.append(f'<rect x="90" y="{photo_y}" width="900" height="520" rx="8" fill="#e5e7de"/>')
        parts.append(f'<image x="90" y="{photo_y}" width="900" height="520" preserveAspectRatio="xMidYMid meet" href="{escape(photo, quote=True)}"/>')
    parts.append(f'<path d="M92 {divider}H980" stroke="#c4cbbd"/>')
    parts.append(f'<rect x="90" y="{divider-3}" width="72" height="6" fill="#b9975a"/>')
    for index, line in enumerate(lines):
        parts.append(
            f'<text x="90" y="{body_y+index*43}" font-size="26" fill="#3d5147">{escape(line)}</text>'
        )
    parts.extend(
        [
            f'<rect x="70" y="{footer_y-38}" width="940" height="142" rx="5" fill="#235b4d"/>',
            f'<text x="102" y="{footer_y+10}" font-size="24" fill="#f5f1e7">{escape(workspace_name[:28] or "商家传播素材")}</text>',
            f'<text x="102" y="{footer_y+52}" font-size="18" fill="#d4dfce">{"商家已审核版本" if approved else "待审核预览 · 不用于发布"} · {escape(channel[:30])}</text>',
            f'<text x="90" y="{height-53}" font-size="15" fill="#7e8b7e">承艺 / 每一份表达，都有来处。</text>',
            "</g></svg>",
        ]
    )
    # Font is applied on the root too so the masthead uses the same CJK fallback.
    result = "".join(parts).replace(
        "<svg xmlns=",
        '<svg font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" xmlns=',
        1,
    )
    palettes = {
        "warm": {"#f5f1e7": "#fff5e9", "#235b4d": "#914d35", "#163f36": "#683622", "#507665": "#936a53", "#3d5147": "#644b3b"},
        "minimal": {"#f5f1e7": "#ffffff", "#235b4d": "#25354b", "#163f36": "#172236", "#507665": "#52647b", "#3d5147": "#3d4859"},
    }
    for old, new in palettes.get(template, {}).items():
        result = result.replace(old, new)
    return result
