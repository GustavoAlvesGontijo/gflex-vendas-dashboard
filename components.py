"""
Componentes HTML reutilizaveis estilo Hub GFlex.
Cada funcao retorna uma string HTML pronta pra `st.markdown(unsafe_allow_html=True)`.
"""
from config import CORES, EMPRESA_LABELS, get_logo_b64

# ============================================================
# ICONES (SVG inline — Lucide)
# https://lucide.dev — MIT
# ============================================================

def icon(name: str, size: int = 13, color: str = "currentColor") -> str:
    p = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.2" '
        f'stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:-2px">'
    )
    paths = {
        "target":       '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
        "flame":        '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
        "list-checks":  '<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/>',
        "trending-up":  '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
        "trending-down":'<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>',
        "scale":        '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
        "users":        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
        "file-text":    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/>',
        "calendar":     '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
        "chart":        '<path d="M3 3v18h18"/><path d="M7 16l4-4 4 4 6-8"/>',
        "fuel":         '<line x1="3" x2="15" y1="22" y2="22"/><line x1="4" x2="14" y1="9" y2="9"/><path d="M14 22V4a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v18"/><path d="M14 13h2a2 2 0 0 1 2 2v2a2 2 0 0 0 2 2a2 2 0 0 0 2-2V9.83a2 2 0 0 0-.59-1.42L18 5"/>',
    }
    return p + paths.get(name, '<circle cx="12" cy="12" r="9"/>') + '</svg>'


# ============================================================
# Variação percentual em pill com seta
# ============================================================

def var_badge(pct, threshold_neutro: float = 1.0) -> str:
    """Pill colorida com seta. None/zero -> string vazia.
    threshold_neutro: variacoes menores que isso em modulo viram cinza (ruido)."""
    if pct is None:
        return ""
    try:
        p = float(pct)
    except Exception:
        return ""
    if abs(p) < threshold_neutro:
        return (
            f'<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 6px;'
            f'border-radius:5px;background:var(--bg-overlay);color:var(--text-muted);'
            f'font-size:0.65rem;font-weight:700">{p:+.0f}%</span>'
        )
    pos = p > 0
    color = "#059669" if pos else "#dc2626"
    bg = "#10b98118" if pos else "#dc262618"
    ico = icon("trending-up", 11, color) if pos else icon("trending-down", 11, color)
    sign = "+" if pos else ""
    return (
        f'<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 6px;'
        f'border-radius:5px;background:{bg};color:{color};font-size:0.65rem;'
        f'font-weight:700;font-feature-settings:\'tnum\'">{ico}{sign}{p:.0f}%</span>'
    )


# ============================================================
# Header da empresa (com logo + nome + accent line)
# ============================================================

def empresa_header(empresa: str, badge_extra: str = "") -> str:
    label = EMPRESA_LABELS.get(empresa, empresa)
    color = CORES.get(empresa, {}).get("primaria", "#1a1a2e")
    logo = get_logo_b64(empresa)
    logo_html = (
        f'<img src="{logo}" style="height:38px;width:38px;border-radius:8px;'
        f'object-fit:cover;box-shadow:var(--shadow-sm)" alt="{label}"/>'
        if logo else
        f'<div style="height:38px;width:38px;border-radius:8px;background:{color};'
        f'display:flex;align-items:center;justify-content:center;color:white;'
        f'font-weight:700">{label[:1]}</div>'
    )
    return (
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px">'
        '<div style="display:flex;align-items:center;gap:11px">'
        f'{logo_html}'
        f'<div><div style="font-weight:700;color:{color};font-size:1.05rem;line-height:1.15">{label}</div></div>'
        '</div>'
        f'{badge_extra}'
        '</div>'
    )


# ============================================================
# Bloco de KPI com tint colorido (estilo Hub: bg semi-transparente)
# ============================================================

def kpi_block(
    label: str,
    primary_value: str,
    primary_caption: str = "",
    secondary_value: str = "",
    secondary_caption: str = "",
    accent: str = "#3b82f6",
    tint_bg: str = "#3b82f614",
    icon_name: str = "",
    primary_extra: str = "",
    secondary_extra: str = "",
) -> str:
    """Bloco com label + 2 valores lado a lado (ou 1 só se secondary_value vazio).
    accent = cor do texto principal. tint_bg = cor de fundo (com alpha).
    primary_extra/secondary_extra: HTML adicional (ex: var_badge ou split licit/outras)."""
    icon_html = f'{icon(icon_name, 11, accent)} ' if icon_name else ""
    if secondary_value:
        body = (
            '<div style="display:flex;gap:14px">'
            '<div style="flex:1">'
            f'<div style="font-size:1.4rem;font-weight:700;color:{accent};line-height:1.1;font-feature-settings:\'tnum\'">{primary_value}</div>'
            f'<div style="font-size:0.6rem;color:var(--text-secondary);margin-top:3px">{primary_caption}</div>'
            f'{primary_extra}'
            '</div>'
            '<div style="flex:1">'
            f'<div style="font-size:1.4rem;font-weight:700;color:{accent};line-height:1.1;font-feature-settings:\'tnum\'">{secondary_value}</div>'
            f'<div style="font-size:0.6rem;color:var(--text-secondary);margin-top:3px">{secondary_caption}</div>'
            f'{secondary_extra}'
            '</div>'
            '</div>'
        )
    else:
        body = (
            f'<div style="font-size:1.4rem;font-weight:700;color:{accent};line-height:1.1;font-feature-settings:\'tnum\'">{primary_value}</div>'
            f'<div style="font-size:0.6rem;color:var(--text-secondary);margin-top:3px">{primary_caption}</div>'
            f'{primary_extra}'
        )
    return (
        f'<div class="gx-tint" style="background:{tint_bg}">'
        f'<div style="font-size:0.6rem;color:{accent};text-transform:uppercase;'
        f'font-weight:700;letter-spacing:0.5px;margin-bottom:7px;display:flex;align-items:center;gap:4px">'
        f'{icon_html}{label}</div>'
        f'{body}'
        '</div>'
    )


# ============================================================
# Wrapper de Card com accent na borda esquerda
# ============================================================

def card_open(accent_color: str) -> str:
    return (
        f'<div class="gx-card gx-card-accent" style="border-left-color:{accent_color}">'
    )


def card_close() -> str:
    return '</div>'


# ============================================================
# Sub-linha split (Licitação vs Outras) — usado nos cards Flex Tendas
# ============================================================

def split_lines(label_a: str, val_a: str, label_b: str, val_b: str, show: bool = True) -> str:
    """Duas linhas pequenas com cores diferentes. show=False -> ''."""
    if not show:
        return ""
    return (
        '<div style="margin-top:5px;line-height:1.4;font-size:0.6rem;font-weight:600">'
        f'<div style="color:#B45309">{label_a}: {val_a}</div>'
        f'<div style="color:var(--text-muted)">{label_b}: {val_b}</div>'
        '</div>'
    )


# ============================================================
# Header principal de página (banner com gradient)
# ============================================================

def page_header(title: str, subtitle: str = "", status_bar_pct: float | None = None) -> str:
    bar = ""
    if status_bar_pct is not None:
        pct = max(0, min(100, status_bar_pct))
        bar = (
            f'<div style="background:rgba(255,255,255,0.12);border-radius:8px;height:6px;margin-top:14px">'
            f'<div style="background:linear-gradient(90deg,#EC8500,#F7C42D);'
            f'border-radius:8px;height:6px;width:{pct:.0f}%;transition:width 0.4s"></div>'
            f'</div>'
        )
    return (
        '<div style="background:linear-gradient(135deg,#1a1a2e 0%,#2d2d5e 100%);'
        'padding:22px 28px;border-radius:16px;margin-bottom:22px;'
        'box-shadow:0 4px 14px rgba(26,26,46,0.18)">'
        f'<h1 style="color:white;margin:0;font-size:1.55rem;font-weight:700;letter-spacing:-0.4px">{title}</h1>'
        f'<div style="color:rgba(255,255,255,0.75);font-size:0.85rem;margin-top:6px">{subtitle}</div>'
        f'{bar}'
        '</div>'
    )


# ============================================================
# Section heading (h3 + caption)
# ============================================================

def section(title: str, subtitle: str = "", icon_name: str = "") -> str:
    icon_html = f'{icon(icon_name, 18, "var(--accent)")} ' if icon_name else ""
    return (
        f'<h3 class="gx-h3" style="display:flex;align-items:center;gap:8px">'
        f'{icon_html}{title}</h3>'
        f'<p class="gx-subtle">{subtitle}</p>'
    )
