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

def _build_danger_section(score: int) -> str:
    fg, bg = _danger_color(score)
    label = (
        "Low" if score <= 3
        else "Medium" if score <= 5
        else "High" if score <= 7
        else "Critical"
    )
    pct = score * 10
    return f"""
    <section class="card danger-card" style="border-left:6px solid {fg}">
      <div class="danger-inner">
        <div>
          <div class="danger-score" style="color:{fg};background:{bg}">{score}<span class="danger-denom">/10</span></div>
          <div class="danger-label">{_e(label)} Threat Level</div>
        </div>
        <div class="danger-bar-wrap">
          <div class="danger-bar-track">
            <div class="danger-bar-fill" style="width:{pct}%;background:{fg}"></div>
          </div>
          <div class="danger-bar-labels">
            <span>0</span><span>5</span><span>10</span>
          </div>
        </div>
      </div>
    </section>"""


def _build_crimes_section(crimes) -> str:
    if not crimes:
        return _section("Detected Crimes", "⚖️", '<p class="muted">No crimes detected.</p>')

    cards = []
    for crime in crimes:
        sev = crime.severity or "unknown"
        sev_style = _severity_style(sev)
        rule = crime.rule_violated.replace("_", " ").title()
        cards.append(f"""
        <div class="crime-card">
          <div class="crime-header">
            <span class="crime-rule">{_e(rule)}</span>
            <span class="crime-badge" style="{sev_style}">{_e(sev.upper())}</span>
            <span class="crime-ts">@ {_e(crime.timestamp)}</span>
          </div>
          <p class="crime-content">{_e(crime.content)}</p>
        </div>""")

    return _section("Detected Crimes", "⚖️", "\n".join(cards))


def _build_entities_section(entities) -> str:
    rows = []

    # People
    rows.append(f"""
    <div class="entity-row">
      <span class="entity-icon">👥</span>
      <span class="entity-label">People detected</span>
      <span class="entity-value">{entities.people_count}</span>
    </div>""")

    # Weapons
    if entities.weapons:
        for w in entities.weapons:
            desc = f" — {w.description}" if w.description else ""
            rows.append(f"""
    <div class="entity-row entity-alert">
      <span class="entity-icon">🔫</span>
      <span class="entity-label">Weapon @ {_e(w.timestamp)}</span>
      <span class="entity-value">{_e(w.type)}{_e(desc)} ({w.confidence:.0%} confidence)</span>
    </div>""")
    else:
        rows.append("""
    <div class="entity-row">
      <span class="entity-icon">🔫</span>
      <span class="entity-label">Weapons</span>
      <span class="entity-value muted">None detected</span>
    </div>""")

    # Vehicles
    if entities.vehicles:
        for v in entities.vehicles:
            plate_text = ""
            if v.license_plate and v.license_plate.raw_text:
                plate_text = f" | Plate: {v.license_plate.raw_text}"
                if v.license_plate.governorate_guess:
                    plate_text += f" ({v.license_plate.governorate_guess})"
            ts = f" @ {v.timestamp}" if v.timestamp else ""
            rows.append(f"""
    <div class="entity-row">
      <span class="entity-icon">🚗</span>
      <span class="entity-label">{_e(v.type.title())} ({_e(v.color)}){ts}</span>
      <span class="entity-value">{_e(plate_text) if plate_text else '<span class="muted">No plate</span>'}</span>
    </div>""")
    else:
        rows.append("""
    <div class="entity-row">
      <span class="entity-icon">🚗</span>
      <span class="entity-label">Vehicles</span>
      <span class="entity-value muted">None detected</span>
    </div>""")

    # Other objects
    if entities.other_objects:
        rows.append(f"""
    <div class="entity-row">
      <span class="entity-icon">📦</span>
      <span class="entity-label">Other objects</span>
      <span class="entity-value">{_e(", ".join(entities.other_objects))}</span>
    </div>""")

    return _section("Detected Entities", "🔍", '<div class="entity-list">' + "\n".join(rows) + "</div>")


def _build_scene_section(scene) -> str:
    rows = []
    if scene.identified_landmark:
        rows.append(f'<div class="scene-row"><span class="scene-key">Landmark</span><span>{_e(scene.identified_landmark)}</span></div>')
    if scene.architectural_style:
        rows.append(f'<div class="scene-row"><span class="scene-key">Architecture</span><span>{_e(scene.architectural_style)}</span></div>')
    if scene.approximate_location:
        conf = f" ({scene.confidence:.0%} confidence)" if scene.confidence else ""
        rows.append(f'<div class="scene-row"><span class="scene-key">Approx. Location</span><span>{_e(scene.approximate_location)}{_e(conf)}</span></div>')
    if scene.location_hints:
        hints_html = "".join(f'<li>{_e(h)}</li>' for h in scene.location_hints)
        rows.append(f'<div class="scene-row"><span class="scene-key">Location Hints</span><ul class="hint-list">{hints_html}</ul></div>')

    if not rows:
        return _section("Scene &amp; Location", "📍", '<p class="muted">No scene information available.</p>')

    return _section("Scene &amp; Location", "📍", '<div class="scene-block">' + "\n".join(rows) + "</div>")


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
            f'<span class="event-name">{_e(ev.event.replace("_", " ").title())}</span>'
            f'<span class="event-intensity intensity-{_e(ev.intensity or "")}">{_e((ev.intensity or "").upper())}</span></li>'
            for ev in audio.audio_events
        )
        events_html = f'<h3 class="sub-title">Audio Events</h3><ul class="event-list">{event_items}</ul>'

    content = f"""
    <div class="audio-meta">
      <div><span class="meta-key">Sentiment</span>{sentiment_badge}</div>
      <div><span class="meta-key">Language</span><span class="meta-val">{_e(audio.language.upper())}</span></div>
      <div><span class="meta-key">Confidence</span><span class="meta-val">{conf_pct}</span></div>
    </div>
    <h3 class="sub-title">Transcript</h3>
    {transcript_html}
    {events_html}"""

    return _section("Audio Analysis", "🎙️", content)


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f8fafc;
  color: #1e293b;
  font-size: 15px;
  line-height: 1.6;
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
  background: #f1f5f9;
  border-radius: 99px;
  overflow: hidden;
}
.danger-bar-fill { height: 100%; border-radius: 99px; transition: width 0.3s; }
.danger-bar-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.72rem;
  color: #94a3b8;
  margin-top: 4px;
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
  border-left: 4px solid #3b82f6;
  border-radius: 0 8px 8px 0;
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
.crime-ts { font-size: 0.78rem; color: #94a3b8; margin-left: auto; }
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
.entity-value { color: #475569; margin-left: auto; text-align: right; }

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
.hint-list { margin: 4px 0 0 16px; color: #475569; }
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
  margin-right: 8px;
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

def generate_html_report(result: MediaAnalysisResult, output_path: str) -> None:
    """
    Write a self-contained HTML analysis report to output_path.

    Args:
        result:      Completed MediaAnalysisResult from the pipeline
        output_path: Destination .html file path
    """
    va = result.video_analysis
    aa = result.audio_analysis
    shortcode = Path(result.video_path).stem if result.video_path else "unknown"

    # ── Header ──────────────────────────────────────────────────────────────
    header_html = f"""
  <div class="report-header">
    <div class="project-name">Project Ain</div>
    <h1>Media Analysis Report</h1>
    <div class="report-meta">
      <span><b>Reel</b> {_e(shortcode)}</span>
      <span><b>Analysed</b> {_e(result.timestamp[:19].replace("T", " "))}</span>
      <span><b>People detected</b> {va.detected_entities.people_count}</span>
      <span><b>Crimes found</b> {len(va.possible_crimes)}</span>
    </div>
  </div>"""

    # ── Assessment + recommended action ─────────────────────────────────────
    action_html = ""
    if result.recommended_action:
        action_html = f"""
    <div class="action-box">
      <strong>Recommended Action</strong>
      {_e(result.recommended_action)}
    </div>"""

    assessment_section = _section(
        "Overall Assessment", "📋",
        f'<p class="assessment-text">{_e(result.overall_assessment)}</p>{action_html}',
    )

    # ── Video description ────────────────────────────────────────────────────
    description_section = _section(
        "Video Description", "🎬",
        f'<p class="assessment-text">{_e(va.description)}</p>',
    )

    # ── Assemble body ────────────────────────────────────────────────────────
    body = "\n".join([
        header_html,
        _build_danger_section(va.danger_score),
        assessment_section,
        description_section,
        _build_crimes_section(va.possible_crimes),
        _build_entities_section(va.detected_entities),
        _build_scene_section(va.scene_landmarks),
        _build_audio_section(aa),
    ])

    footer_html = f'<div class="report-footer">Generated by Project Ain &mdash; {_e(result.timestamp[:19].replace("T", " "))}</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Analysis Report — {_e(shortcode)}</title>
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
