"""
HTML report generator for media analysis results.
Produces a self-contained .html file (all CSS inline, no external dependencies).
"""

from pathlib import Path
from typing import Optional
from .schemas import MediaAnalysisResult


# ── Severity colour mapping ────────────────────────────────────────────────────
_SEVERITY_COLORS = {
    "minor":    ("#d1fae5", "#065f46", "#6ee7b7"),   # bg, text, border
    "moderate": ("#fef9c3", "#854d0e", "#fde047"),
    "severe":   ("#fee2e2", "#991b1b", "#fca5a5"),
    "critical": ("#4c0519", "#fecdd3", "#e11d48"),
}

# Arabic display labels (severity and intensity values stay English in JSON for CSS/logic)
_SEVERITY_LABELS_AR = {
    "minor":    "بسيط",
    "moderate": "متوسط",
    "severe":   "شديد",
    "critical": "حرج",
}
_INTENSITY_LABELS_AR = {
    "low":    "منخفض",
    "medium": "متوسط",
    "high":   "مرتفع",
}

# Egyptian law classification colours  (fg, bg)
_CLASSIFICATION_COLORS = {
    "جناية":  ("#dc2626", "#fef2f2"),
    "جنحة":   ("#ea580c", "#fff7ed"),
    "مخالفة": ("#ca8a04", "#fef9c3"),
    "لا شيء": ("#94a3b8", "#f1f5f9"),
}


def _classification_color(classification: Optional[str]):
    return _CLASSIFICATION_COLORS.get(classification or "لا شيء", ("#94a3b8", "#f1f5f9"))

_DANGER_COLORS = {
    (0, 3):  ("#16a34a", "#dcfce7"),   # fg, bg  — low
    (4, 5):  ("#ca8a04", "#fef9c3"),   # medium-low
    (6, 7):  ("#ea580c", "#fff7ed"),   # medium-high
    (8, 10): ("#dc2626", "#fef2f2"),   # high
}

_SENTIMENT_COLORS = {
    "anger":      ("#dc2626", "#fef2f2"),
    "aggression": ("#dc2626", "#fef2f2"),
    "distress":   ("#ea580c", "#fff7ed"),
    "fear":       ("#7c3aed", "#f5f3ff"),
    "calm":       ("#16a34a", "#dcfce7"),
    "neutral":    ("#475569", "#f1f5f9"),
    "unknown":    ("#6b7280", "#f9fafb"),
    "error":      ("#6b7280", "#f9fafb"),
}


def _danger_color(score: int):
    for (lo, hi), colors in _DANGER_COLORS.items():
        if lo <= score <= hi:
            return colors
    return ("#6b7280", "#f9fafb")


def _sentiment_color(sentiment: str):
    key = sentiment.lower().split("/")[0].strip()
    return _SENTIMENT_COLORS.get(key, ("#475569", "#f1f5f9"))


def _severity_style(severity: str):
    colors = _SEVERITY_COLORS.get(severity.lower(), ("#f1f5f9", "#334155", "#94a3b8"))
    return f"background:{colors[0]};color:{colors[1]};border:1px solid {colors[2]}"


def _e(text: Optional[str]) -> str:
    """Escape HTML special characters."""
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _section(title: str, icon: str, content: str) -> str:
    return f"""
    <section class="card">
      <h2 class="card-title"><span class="icon">{icon}</span>{_e(title)}</h2>
      {content}
    </section>"""


def _badge(text: str, fg: str, bg: str, extra_style: str = "") -> str:
    return (
        f'<span class="badge" style="background:{bg};color:{fg};{extra_style}">'
        f"{_e(text)}</span>"
    )


# ── Section builders ──────────────────────────────────────────────────────────

def _build_danger_section(score: int, classification: Optional[str] = None, in_egypt: str = "غير محدد") -> str:
    label = classification or "لا شيء"

    if in_egypt == "نعم":
        fg, bg = _classification_color(classification)
        bar_fill = f'<div class="danger-bar-fill" style="width:{score * 10}%;background:{fg}"></div>'
        score_style = f"color:{fg};background:{bg}"
        border_style = f"border-right:6px solid {fg}"
        bar_opacity = ""
        jurisdiction_banner = ""
        classification_html = f'التصنيف القانوني: <span style="color:{fg}">{_e(label)}</span>'

    elif in_egypt == "لا":
        fg, bg = "#94a3b8", "#f1f5f9"
        bar_fill = ""
        score_style = "color:#94a3b8;background:#f1f5f9"
        border_style = "border-right:6px solid #94a3b8"
        bar_opacity = ""
        jurisdiction_banner = """
      <div class="jurisdiction-banner jurisdiction-outside">
        <span class="jurisdiction-icon">⚠️</span>
        الجريمة خارج نطاق الاختصاص المصري — درجة الخطورة غير مفعّلة
      </div>"""
        classification_html = f'التصنيف القانوني: <span style="color:#94a3b8">{_e(label)}</span>'

    else:  # "غير محدد"
        fg, bg = _classification_color(classification)
        bar_fill = f'<div class="danger-bar-fill" style="width:{score * 10}%;background:{fg}"></div>'
        score_style = f"color:{fg};background:{bg}"
        border_style = f"border-right:6px solid {fg}"
        bar_opacity = "opacity:0.45;"
        jurisdiction_banner = """
      <div class="jurisdiction-banner jurisdiction-unknown">
        <span class="jurisdiction-icon">ℹ️</span>
        موقع الجريمة غير محدد — يُعرض التقييم للاستئناس فقط
      </div>"""
        classification_html = f'التصنيف القانوني: <span style="color:{fg}">{_e(label)}</span>'

    return f"""
    <section class="card danger-card" style="{border_style}">
      {jurisdiction_banner}
      <div class="danger-inner">
        <div>
          <div class="danger-score" style="{score_style}">{score}<span class="danger-denom">/10</span></div>
          <div class="danger-label">{classification_html}</div>
        </div>
        <div class="danger-bar-wrap" style="{bar_opacity}">
          <div class="danger-bar-track" dir="ltr">
            {bar_fill}
          </div>
          <div class="danger-bar-ranges" dir="ltr">
            <div class="range-segment" style="width:10%;background:#f1f5f9;color:#94a3b8">لا شيء<span class="range-nums">0</span></div>
            <div class="range-segment" style="width:30%;background:#fef9c3;color:#854d0e">مخالفة<span class="range-nums">1–3</span></div>
            <div class="range-segment" style="width:30%;background:#fed7aa;color:#c2410c">جنحة<span class="range-nums">4–6</span></div>
            <div class="range-segment" style="width:30%;background:#fecdd3;color:#be123c">جناية<span class="range-nums">7–10</span></div>
          </div>
        </div>
      </div>
    </section>"""


def _build_matched_articles(articles) -> str:
    """Render penal code articles matched to a single crime."""
    if not articles:
        return ""
    items = []
    for a in articles:
        sim_pct = f"{a.similarity:.0%}"
        items.append(f"""
        <div class="penal-article-item">
          <div class="penal-article-meta">
            <span class="penal-article-num">المادة {_e(a.article_number)}</span>
            <span class="penal-chapter">{_e(a.chapter_title)}</span>
            <span class="penal-sim">{sim_pct} تطابق</span>
          </div>
          <p class="penal-article-text" dir="rtl">{_e(a.article_text)}</p>
        </div>""")
    return f"""
      <div class="penal-articles">
        <div class="penal-articles-title">المواد القانونية ذات الصلة</div>
        {"".join(items)}
      </div>"""


def _build_crimes_section(crimes) -> str:
    if not crimes:
        return _section("الجرائم المرصودة", "⚖️", '<p class="muted">لم يُرصد أي جرائم.</p>')

    cards = []
    for crime in crimes:
        sev = crime.severity or "unknown"
        sev_style = _severity_style(sev)
        sev_label = _SEVERITY_LABELS_AR.get(sev.lower(), sev)
        articles_html = _build_matched_articles(getattr(crime, "matched_articles", []))
        cards.append(f"""
        <div class="crime-card">
          <div class="crime-header">
            <span class="crime-rule">{_e(crime.rule_violated)}</span>
            <span class="crime-badge" style="{sev_style}">{_e(sev_label)}</span>
            <span class="crime-ts">@ {_e(crime.timestamp)}</span>
          </div>
          <p class="crime-content">{_e(crime.content)}</p>
          {articles_html}
        </div>""")

    return _section("الجرائم المرصودة", "⚖️", "\n".join(cards))


def _build_entities_section(entities) -> str:
    rows = []

    # People
    rows.append(f"""
    <div class="entity-row">
      <span class="entity-icon">👥</span>
      <span class="entity-label">أشخاص مرصودون</span>
      <span class="entity-value">{entities.people_count}</span>
    </div>""")

    # Weapons
    if entities.weapons:
        for w in entities.weapons:
            desc = f" — {w.description}" if w.description else ""
            rows.append(f"""
    <div class="entity-row entity-alert">
      <span class="entity-icon">🔫</span>
      <span class="entity-label">سلاح @ {_e(w.timestamp)}</span>
      <span class="entity-value">{_e(w.type)}{_e(desc)} ({w.confidence:.0%} ثقة)</span>
    </div>""")
    else:
        rows.append("""
    <div class="entity-row">
      <span class="entity-icon">🔫</span>
      <span class="entity-label">أسلحة</span>
      <span class="entity-value muted">لم يُرصد</span>
    </div>""")

    # Vehicles
    if entities.vehicles:
        for v in entities.vehicles:
            plate_text = ""
            if v.license_plate and v.license_plate.raw_text:
                plate_text = f" | لوحة: {v.license_plate.raw_text}"
                if v.license_plate.governorate_guess:
                    plate_text += f" ({v.license_plate.governorate_guess})"
            ts = f" @ {v.timestamp}" if v.timestamp else ""
            rows.append(f"""
    <div class="entity-row">
      <span class="entity-icon">🚗</span>
      <span class="entity-label">{_e(v.type)} ({_e(v.color)}){ts}</span>
      <span class="entity-value">{_e(plate_text) if plate_text else '<span class="muted">لا لوحة</span>'}</span>
    </div>""")
    else:
        rows.append("""
    <div class="entity-row">
      <span class="entity-icon">🚗</span>
      <span class="entity-label">مركبات</span>
      <span class="entity-value muted">لم يُرصد</span>
    </div>""")

    # Other objects
    if entities.other_objects:
        rows.append(f"""
    <div class="entity-row">
      <span class="entity-icon">📦</span>
      <span class="entity-label">أشياء أخرى</span>
      <span class="entity-value">{_e(", ".join(entities.other_objects))}</span>
    </div>""")

    return _section("الكيانات المرصودة", "🔍", '<div class="entity-list">' + "\n".join(rows) + "</div>")


def _build_scene_section(scene) -> str:
    rows = []
    if scene.identified_landmark:
        rows.append(f'<div class="scene-row"><span class="scene-key">معلم</span><span>{_e(scene.identified_landmark)}</span></div>')
    if scene.architectural_style:
        rows.append(f'<div class="scene-row"><span class="scene-key">الطراز المعماري</span><span>{_e(scene.architectural_style)}</span></div>')
    if scene.approximate_location:
        conf = f" ({scene.confidence:.0%} ثقة)" if scene.confidence else ""
        rows.append(f'<div class="scene-row"><span class="scene-key">الموقع التقريبي</span><span>{_e(scene.approximate_location)}{_e(conf)}</span></div>')
    if scene.location_hints:
        hints_html = "".join(f'<li>{_e(h)}</li>' for h in scene.location_hints)
        rows.append(f'<div class="scene-row"><span class="scene-key">تلميحات الموقع</span><ul class="hint-list">{hints_html}</ul></div>')

    if not rows:
        return _section("المشهد والموقع", "📍", '<p class="muted">لا معلومات عن المشهد.</p>')

    return _section("المشهد والموقع", "📍", '<div class="scene-block">' + "\n".join(rows) + "</div>")


def _build_audio_section(audio) -> str:
    fg, bg = _sentiment_color(audio.sentiment)
    sentiment_badge = _badge(audio.sentiment, fg, bg, "font-size:0.9rem;padding:4px 12px;")
    conf_pct = f"{audio.confidence:.0%}" if audio.confidence else "N/A"

    # Transcript
    transcript_html = (
        f'<div class="transcript" dir="rtl" lang="ar">{_e(audio.transcript)}</div>'
        if audio.transcript and not audio.transcript.startswith("[")
        else f'<div class="transcript muted">{_e(audio.transcript)}</div>'
    )

    # Audio events
    events_html = ""
    if audio.audio_events:
        event_items = "".join(
            f'<li><span class="event-ts">{_e(ev.timestamp)}</span>'
            f'<span class="event-name">{_e(ev.event.replace("_", " "))}</span>'
            f'<span class="event-intensity intensity-{_e(ev.intensity or "")}">'
            f'{_e(_INTENSITY_LABELS_AR.get((ev.intensity or "").lower(), ev.intensity or ""))}'
            f'</span></li>'
            for ev in audio.audio_events
        )
        events_html = f'<h3 class="sub-title">الأحداث الصوتية</h3><ul class="event-list">{event_items}</ul>'

    content = f"""
    <div class="audio-meta">
      <div><span class="meta-key">المشاعر</span>{sentiment_badge}</div>
      <div><span class="meta-key">اللغة</span><span class="meta-val">{_e(audio.language.upper())}</span></div>
      <div><span class="meta-key">درجة الثقة</span><span class="meta-val">{conf_pct}</span></div>
    </div>
    <h3 class="sub-title">النص المفرغ</h3>
    {transcript_html}
    {events_html}"""

    return _section("تحليل الصوت", "🎙️", content)


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Segoe UI', 'Cairo', 'Tahoma', 'Arial Unicode MS', -apple-system, BlinkMacSystemFont, Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f8fafc;
  color: #1e293b;
  font-size: 15px;
  line-height: 1.8;
}

.page-wrap { max-width: 860px; margin: 0 auto; padding: 32px 20px 60px; }

/* Header */
.report-header {
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
  color: #f1f5f9;
  border-radius: 12px;
  padding: 32px 36px;
  margin-bottom: 24px;
}
.report-header .project-name {
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #94a3b8;
  margin-bottom: 4px;
}
.report-header h1 { font-size: 1.6rem; font-weight: 700; margin-bottom: 12px; }
.report-meta { display: flex; gap: 20px; flex-wrap: wrap; font-size: 0.82rem; color: #94a3b8; }
.report-meta span b { color: #cbd5e1; }

/* Cards */
.card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 24px 28px;
  margin-bottom: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.card-title {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 18px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  gap: 8px;
}
.icon { font-size: 1.1rem; }

/* Danger */
.danger-card { padding: 24px 28px; }
.danger-inner { display: flex; align-items: center; gap: 36px; flex-wrap: wrap; }
.danger-score {
  font-size: 3.4rem;
  font-weight: 800;
  border-radius: 14px;
  padding: 10px 22px;
  line-height: 1;
}
.danger-denom { font-size: 1.2rem; font-weight: 500; opacity: 0.7; }
.danger-label { font-size: 0.85rem; font-weight: 600; color: #64748b; margin-top: 6px; }
.danger-bar-wrap { flex: 1; min-width: 200px; }
.danger-bar-track {
  height: 14px;
  background: #cbd5e1;
  border-radius: 99px;
  overflow: hidden;
}
.danger-bar-fill { height: 100%; border-radius: 99px; transition: width 0.3s; }
.jurisdiction-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 16px;
  font-size: 0.85rem;
  font-weight: 600;
}
.jurisdiction-outside {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #64748b;
}
.jurisdiction-unknown {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
}
.jurisdiction-icon { font-size: 1rem; flex-shrink: 0; }

.danger-bar-ranges {
  display: flex;
  margin-top: 6px;
  border-radius: 6px;
  overflow: hidden;
  font-size: 0.68rem;
  font-weight: 600;
}
.range-segment {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3px 2px;
  text-align: center;
  line-height: 1.2;
}
.range-nums {
  font-size: 0.6rem;
  font-weight: 400;
  opacity: 0.8;
  direction: ltr;
}

/* Assessment */
.assessment-text {
  font-size: 0.97rem;
  color: #334155;
  line-height: 1.8;
}
.action-box {
  margin-top: 16px;
  padding: 14px 18px;
  background: #eff6ff;
  border-right: 4px solid #3b82f6;
  border-radius: 8px 0 0 8px;
  font-size: 0.9rem;
  color: #1e40af;
}
.action-box strong { display: block; margin-bottom: 4px; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; }

/* Crimes */
.crime-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 12px;
}
.crime-card:last-child { margin-bottom: 0; }
.crime-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.crime-rule { font-weight: 600; font-size: 0.9rem; color: #0f172a; }
.crime-badge {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 2px 8px;
  border-radius: 99px;
}
.crime-ts { font-size: 0.78rem; color: #94a3b8; margin-right: auto; }
.crime-content { font-size: 0.88rem; color: #475569; }

/* Entities */
.entity-list { display: flex; flex-direction: column; gap: 10px; }
.entity-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
  font-size: 0.88rem;
}
.entity-alert { background: #fff5f5; border-color: #fee2e2; }
.entity-icon { font-size: 1rem; flex-shrink: 0; }
.entity-label { font-weight: 600; color: #334155; flex-shrink: 0; }
.entity-value { color: #475569; margin-right: auto; text-align: right; }

/* Scene */
.scene-block { display: flex; flex-direction: column; gap: 12px; }
.scene-row {
  display: flex;
  gap: 16px;
  font-size: 0.88rem;
  align-items: baseline;
}
.scene-key {
  font-weight: 600;
  color: #64748b;
  min-width: 140px;
  flex-shrink: 0;
}
.hint-list { margin: 4px 16px 0 0; color: #475569; }
.hint-list li { margin-bottom: 2px; }

/* Audio */
.audio-meta {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  align-items: center;
}
.meta-key {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94a3b8;
  margin-left: 8px;
}
.meta-val { font-weight: 600; color: #334155; }
.sub-title {
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #94a3b8;
  margin-bottom: 10px;
}
.transcript {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px 18px;
  font-size: 0.88rem;
  color: #334155;
  white-space: pre-wrap;
  line-height: 2;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  margin-bottom: 20px;
}
.event-list { list-style: none; display: flex; flex-direction: column; gap: 8px; }
.event-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 6px;
  font-size: 0.85rem;
}
.event-ts { color: #94a3b8; font-size: 0.8rem; min-width: 44px; }
.event-name { color: #334155; font-weight: 500; flex: 1; }
.event-intensity {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 99px;
}
.intensity-low    { background:#dcfce7; color:#166534; }
.intensity-medium { background:#fef9c3; color:#854d0e; }
.intensity-high   { background:#fee2e2; color:#991b1b; }

/* Penal code articles (matched to a crime) */
.penal-articles {
  margin-top: 14px;
  border-top: 1px dashed #e2e8f0;
  padding-top: 12px;
}
.penal-articles-title {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #94a3b8;
  margin-bottom: 10px;
}
.penal-article-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-right: 3px solid #3b82f6;
  border-radius: 0 6px 6px 0;
  padding: 10px 14px;
  margin-bottom: 8px;
}
.penal-article-item:last-child { margin-bottom: 0; }
.penal-article-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.penal-article-num {
  font-weight: 700;
  font-size: 0.82rem;
  color: #1e40af;
}
.penal-chapter {
  font-size: 0.78rem;
  color: #64748b;
  flex: 1;
}
.penal-sim {
  font-size: 0.72rem;
  font-weight: 600;
  color: #0369a1;
  background: #e0f2fe;
  padding: 2px 8px;
  border-radius: 99px;
  white-space: nowrap;
}
.penal-article-text {
  font-size: 0.84rem;
  color: #334155;
  line-height: 1.9;
}

/* Badge */
.badge {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 99px;
}

/* Misc */
.muted { color: #94a3b8; font-style: italic; }

/* Video player */
.video-player-card video { display: block; }

/* Footer */
.report-footer {
  text-align: center;
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

@media print {
  body { background: white; }
  .page-wrap { padding: 0; }
  .card { break-inside: avoid; box-shadow: none; }
}
"""


# ── Main entry point ──────────────────────────────────────────────────────────

def _build_video_player(video_url: str) -> str:
    return f"""
    <section class="card video-player-card">
      <h2 class="card-title"><span class="icon">▶️</span>الفيديو</h2>
      <video controls preload="metadata" style="width:100%;border-radius:8px;max-height:480px;background:#000;">
        <source src="{_e(video_url)}" type="video/mp4">
      </video>
    </section>"""


def generate_html_report(result: MediaAnalysisResult, output_path: str, video_url: Optional[str] = None) -> None:
    """
    Write a self-contained HTML analysis report to output_path.

    Args:
        result:      Completed MediaAnalysisResult from the pipeline
        output_path: Destination .html file path
        video_url:   Optional public URL to the video (e.g. Supabase Storage).
                     When provided, an embedded player is shown at the top of the report.
    """
    va = result.video_analysis
    aa = result.audio_analysis
    shortcode = Path(result.video_path).stem if result.video_path else "unknown"

    # ── Header ──────────────────────────────────────────────────────────────
    header_html = f"""
  <div class="report-header">
    <div class="project-name">مشروع عين</div>
    <h1>تقرير تحليل الميديا</h1>
    <div class="report-meta">
      <span><b>ريل</b> {_e(shortcode)}</span>
      <span><b>وقت التحليل</b> {_e(result.timestamp[:19].replace("T", " "))}</span>
      <span><b>أشخاص مرصودون</b> {va.detected_entities.people_count}</span>
      <span><b>جرائم مرصودة</b> {len(va.possible_crimes)}</span>
    </div>
  </div>"""

    # ── Assessment + recommended action ─────────────────────────────────────
    action_html = ""
    if result.recommended_action:
        action_html = f"""
    <div class="action-box">
      <strong>الإجراء الموصى به</strong>
      {_e(result.recommended_action)}
    </div>"""

    assessment_section = _section(
        "التقييم العام", "📋",
        f'<p class="assessment-text">{_e(result.overall_assessment)}</p>{action_html}',
    )

    # ── Video description ────────────────────────────────────────────────────
    description_section = _section(
        "وصف الفيديو", "🎬",
        f'<p class="assessment-text">{_e(va.description)}</p>',
    )

    # ── Assemble body ────────────────────────────────────────────────────────
    sections = [header_html]
    if video_url:
        sections.append(_build_video_player(video_url))
    sections += [
        _build_danger_section(va.danger_score, va.crime_classification, va.in_egypt),
        assessment_section,
        description_section,
        _build_crimes_section(va.possible_crimes),
        _build_entities_section(va.detected_entities),
        _build_scene_section(va.scene_landmarks),
        _build_audio_section(aa),
    ]
    body = "\n".join(sections)

    footer_html = f'<div class="report-footer">تم الإنشاء بواسطة مشروع عين &mdash; {_e(result.timestamp[:19].replace("T", " "))}</div>'

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>تقرير التحليل — {_e(shortcode)}</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="page-wrap">
{body}
{footer_html}
  </div>
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")
