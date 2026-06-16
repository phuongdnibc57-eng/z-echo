# zecho/render.py
_FIXED = {
    "vi": "Cảm ơn bạn đã báo! Sự cố ({key}) đã được khắc phục ở phiên bản {ver} 🎉",
    "en": "Thanks for reporting! The issue ({key}) is fixed in version {ver} 🎉",
}
_VERDICT = {
    "vi": "Cập nhật về phản hồi của bạn ({key}): kết luận **{verdict}** — lý do: {reason}. "
          "Nếu bạn vẫn gặp lỗi, nhắn 'vẫn lỗi' để mình mở lại.",
    "en": "Update on your report ({key}): verdict **{verdict}** — reason: {reason}. "
          "If you still see the issue, reply 'still broken' to re-open.",
}

def close_msg(jira_key, verdict, reason, fixed_in, lang="vi") -> str:
    lang = lang if lang in ("vi", "en") else "vi"
    key = jira_key or "issue"
    if verdict and verdict != "fixed":
        return _VERDICT[lang].format(key=key, verdict=verdict, reason=reason)
    return _FIXED[lang].format(key=key, ver=fixed_in or ("latest" if lang == "en" else "mới nhất"))

def squad_digest(squad: str, items: list, reasons: list) -> str:
    head = f"🟠 [Squad {squad}] Daily feedback digest"
    if reasons:
        head += " — " + ", ".join(reasons)
    lines = [head]
    for it in items:
        key = it.get("jira_key", it["id"])
        lines.append(f"• [{it.get('severity','?')}] {it['short_desc']} — "
                     f"{it.get('freq','?')} báo cáo → {key}")
    return "\n".join(lines)

def po_digest(items: list) -> str:
    lines = ["📋 [PO] Daily rollup"]
    by_theme = {}
    for it in items:
        by_theme.setdefault(it.get("theme", it["id"]), 0)
        by_theme[it.get("theme", it["id"])] += int(it.get("freq", 0))
    for theme, vol in sorted(by_theme.items(), key=lambda kv: -kv[1]):
        lines.append(f"• {theme}: {vol} feedback")
    return "\n".join(lines)
