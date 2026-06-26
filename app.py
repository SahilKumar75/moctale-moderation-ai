"""Moctale Moderation AI — Hugging Face Space
Target-aware comment moderation for Indian movie review platforms.
Run: gradio app.py   or   python app.py
"""
from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # ensure config/ and data/ relative paths resolve

import gradio as gr

# ── Engine init ───────────────────────────────────────────────────────────────
_engine = None
ENGINE_READY = False
ENGINE_ERR = ""
try:
    from moctale_moderation import ModerationEngine, ModerationRequest  # type: ignore
    _engine = ModerationEngine()
    ENGINE_READY = True
except Exception as exc:
    ENGINE_ERR = str(exc)

# ── Hardcoded eval data (from reports/eval_final.md — git 1f57aa7) ────────────
_PC = {
    "allow":            {"p": 0.947, "r": 0.990, "f1": 0.968, "n": 287},
    "flag_for_review":  {"p": 0.676, "r": 0.825, "f1": 0.743, "n": 114},
    "flag_for_removal": {"p": 0.934, "r": 0.576, "f1": 0.713, "n":  99},
}
_CONF = {
    "allow":            {"allow": 284, "flag_for_review":  3, "flag_for_removal":  0},
    "flag_for_review":  {"allow":  16, "flag_for_review": 94, "flag_for_removal":  4},
    "flag_for_removal": {"allow":   0, "flag_for_review": 42, "flag_for_removal": 57},
}

# ── Dataset sample ────────────────────────────────────────────────────────────
_SAMPLE_ROWS: list[dict] = []
_DATA_CSV = ROOT / "data" / "moderation_examples.csv"
if _DATA_CSV.exists():
    with _DATA_CSV.open(encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= 20:
                break
            _SAMPLE_ROWS.append(row)

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
body { background: #0d0d0d !important; }

.gradio-container {
    max-width: 1140px !important;
    margin: 0 auto !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* ---- result card ---- */
.rc { background:#161616; border:1px solid #282828; border-radius:10px; padding:22px 24px; }
.rc-allow   { border-left:4px solid #22c55e; }
.rc-review  { border-left:4px solid #f59e0b; }
.rc-removal { border-left:4px solid #ef4444; }

.ab { display:inline-flex; align-items:center; gap:7px; padding:5px 14px;
      border-radius:5px; font-size:14px; font-weight:700; letter-spacing:.04em;
      text-transform:uppercase; font-family:'JetBrains Mono',monospace; }
.ab-allow   { background:rgba(34,197,94,.12);  color:#22c55e; }
.ab-review  { background:rgba(245,158,11,.12); color:#f59e0b; }
.ab-removal { background:rgba(239,68,68,.12);  color:#ef4444; }

.lat { display:inline-flex; align-items:center; padding:3px 9px; border-radius:4px;
       font-size:11px; background:rgba(255,255,255,.06); color:#666;
       font-family:'JetBrains Mono',monospace; margin-left:8px; }

.slabel { color:#555; font-size:10px; text-transform:uppercase; letter-spacing:.1em;
          margin-top:16px; margin-bottom:5px; }

.pill { display:inline-flex; padding:2px 9px; border-radius:11px; font-size:11px;
        background:rgba(255,255,255,.05); color:#aaa;
        border:1px solid rgba(255,255,255,.09); margin:2px;
        font-family:'JetBrains Mono',monospace; }

.explain { background:rgba(255,255,255,.03); border:1px solid #282828;
           border-radius:6px; padding:11px 15px; font-size:13px; color:#c8c8c8;
           line-height:1.55; }

.bar-row { display:flex; align-items:center; gap:10px; margin:3px 0; }
.bar-lbl { color:#666; font-size:11px; min-width:160px; font-family:'JetBrains Mono',monospace; }
.bar-bg  { flex:1; height:5px; background:rgba(255,255,255,.07); border-radius:3px; overflow:hidden; }
.bar-fill { height:100%; border-radius:3px; }
.bar-val { color:#ccc; font-size:11px; font-family:'JetBrains Mono',monospace; min-width:32px; text-align:right; }

.meta-row { display:flex; gap:18px; margin-top:14px; font-size:11px;
            color:#444; font-family:'JetBrains Mono',monospace; }

/* ---- stat cards ---- */
.scard { background:#161616; border:1px solid #282828; border-radius:10px;
         padding:20px 18px; text-align:center; }
.snum  { font-size:30px; font-weight:700; font-family:'JetBrains Mono',monospace;
         line-height:1.1; color:#e5e5e5; }
.slbl2 { color:#555; font-size:12px; margin-top:5px; }

/* ---- tables ---- */
.dt { width:100%; border-collapse:collapse; font-size:12px;
      font-family:'JetBrains Mono',monospace; }
.dt th { color:#555; font-weight:500; text-transform:uppercase; font-size:10px;
         letter-spacing:.07em; padding:8px 12px; border-bottom:1px solid #242424; text-align:left; }
.dt td { padding:7px 12px; border-bottom:1px solid rgba(255,255,255,.03); color:#ccc; }
.dt tr:last-child td { border-bottom:none; }
.ca  { color:#22c55e !important; }
.cr  { color:#f59e0b !important; }
.cx  { color:#ef4444 !important; }

/* ---- architecture ---- */
.arch { background:#111; border:1px solid #222; border-radius:8px; padding:22px 24px;
        font-family:'JetBrains Mono',monospace; font-size:12px; color:#ccc;
        line-height:1.9; overflow-x:auto; white-space:pre; }

/* ---- note / assumption boxes ---- */
.note { background:rgba(245,158,11,.06); border:1px solid rgba(245,158,11,.18);
        border-radius:7px; padding:12px 16px; font-size:13px; color:#c8a95a; line-height:1.5; }
.abox { background:#161616; border:1px solid #282828; border-radius:8px;
        padding:16px 20px; font-size:13px; color:#c8c8c8; line-height:1.6; margin-bottom:12px; }
.abox strong { color:#e5e5e5; }

/* ---- tabs override ---- */
.tab-nav button { font-size:13px !important; }
"""


# ── Moderation logic ──────────────────────────────────────────────────────────
def _bar(label: str, val: float, color: str) -> str:
    pct = min(100, round(val * 100))
    return (
        f"<div class='bar-row'>"
        f"<div class='bar-lbl'>{label}</div>"
        f"<div class='bar-bg'><div class='bar-fill' style='width:{pct}%;background:{color}'></div></div>"
        f"<div class='bar-val'>{pct}%</div>"
        f"</div>"
    )


def moderate(text: str, context_type: str) -> str:
    if not text.strip():
        return "<div class='rc' style='color:#444;font-size:13px'>Enter a comment above and click Analyze.</div>"

    if not ENGINE_READY:
        return f"<div class='rc rc-removal'><p style='color:#ef4444;font-size:13px'>Engine error: {ENGINE_ERR}</p></div>"

    t0 = time.perf_counter()
    try:
        req = ModerationRequest(text=text.strip(), context_type=context_type)
        result = _engine.analyze(req)
    except Exception as exc:
        return f"<div class='rc rc-removal'><p style='color:#ef4444'>Error: {exc}</p></div>"

    ms = round((time.perf_counter() - t0) * 1000, 1)
    action = result.predicted_action

    cls_map = {
        "allow": ("rc-allow", "ab-allow", "✓ ALLOW"),
        "flag_for_review": ("rc-review", "ab-review", "⚠ FLAG FOR REVIEW"),
        "flag_for_removal": ("rc-removal", "ab-removal", "✕ FLAG FOR REMOVAL"),
    }
    rc_cls, ab_cls, ab_label = cls_map.get(action, cls_map["flag_for_review"])

    codes_html = (
        "".join(f"<span class='pill'>{c.lower().replace('_', ' ')}</span>" for c in result.reason_codes)
        or "<span style='color:#444;font-size:12px'>none</span>"
    )

    risk_color = "#ef4444" if result.risk_score > 0.65 else "#f59e0b" if result.risk_score > 0.35 else "#22c55e"
    htox_color = "#ef4444" if result.heuristic_toxicity_score > 0.65 else "#f59e0b" if result.heuristic_toxicity_score > 0.35 else "#555"
    mtox_color = "#7c3aed" if result.model_toxicity_score > 0 else "#333"

    triggered = (
        ", ".join(result.triggered_rules) if result.triggered_rules else "none"
    )

    html = f"""
<div class='rc {rc_cls}'>
  <div style='display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:18px'>
    <span class='ab {ab_cls}'>{ab_label}</span>
    <span class='lat'>⚡ {ms}ms</span>
  </div>

  <div class='slabel'>Target &amp; Classification</div>
  <div style='font-family:"JetBrains Mono",monospace;font-size:13px;color:#ccc'>
    <span style='color:#e5e5e5'>{result.target_detected_pred.replace("_", " ")}</span>
    <span style='color:#444'> · </span>{result.predicted_category.replace("_", " ")}
    <span style='color:#444'> · </span><span style='color:#888'>{result.predicted_severity}</span>
  </div>

  <div class='slabel'>Scores</div>
  {_bar("risk score", result.risk_score, risk_color)}
  {_bar("heuristic toxicity", result.heuristic_toxicity_score, htox_color)}
  {_bar("model toxicity", result.model_toxicity_score, mtox_color)}

  <div class='slabel'>Signals</div>
  <div style='margin:3px 0 0'>{codes_html}</div>

  <div class='slabel'>Why this decision</div>
  <div class='explain'>{result.reason}</div>

  <div class='meta-row'>
    <span>intent: {result.predicted_intent}</span>
    <span>sentiment: {result.sentiment_label} ({result.sentiment_score:.2f})</span>
    <span>rag rules: {triggered}</span>
  </div>
</div>
"""
    return html


# ── Static HTML panels ────────────────────────────────────────────────────────
def _model_stats_html() -> str:
    lift = round((0.870 - 0.574) / 0.574 * 100)
    rows = "".join(
        f"<tr>"
        f"<td style='font-weight:500;color:#e5e5e5'>{k.replace('_',' ')}</td>"
        f"<td>{m['p']:.3f}</td><td>{m['r']:.3f}</td>"
        f"<td style='font-weight:600'>{m['f1']:.3f}</td><td>{m['n']}</td>"
        f"</tr>"
        for k, m in _PC.items()
    )

    actions = ["allow", "flag_for_review", "flag_for_removal"]
    conf_header = "<tr><th>actual \\ predicted</th>" + "".join(f"<th>{a.replace('_',' ')}</th>" for a in actions) + "</tr>"
    conf_rows = ""
    for act in actions:
        cells = ""
        for pred in actions:
            v = _CONF[act][pred]
            is_diag = (act == pred)
            style = "style='color:#22c55e;font-weight:600'" if is_diag and v > 0 else ""
            cells += f"<td {style}>{v}</td>"
        conf_rows += f"<tr><td style='color:#888;font-size:11px'>{act.replace('_',' ')}</td>{cells}</tr>"

    lang_rows = (
        "<tr><td>English</td><td>174</td><td>89.7%</td><td>0.835</td></tr>"
        "<tr><td>Hinglish (Latin)</td><td>326</td><td>85.6%</td><td>0.808</td></tr>"
    )

    return f"""
<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:22px'>
  <div class='scard'>
    <div class='snum' style='color:#22c55e'>87.0%</div>
    <div class='slbl2'>Accuracy</div>
    <div style='font-size:11px;color:#444;margin-top:4px'>+{lift}% over naive baseline</div>
  </div>
  <div class='scard'>
    <div class='snum'>0.808</div>
    <div class='slbl2'>Macro F1</div>
    <div style='font-size:11px;color:#444;margin-top:4px'>across 3 classes</div>
  </div>
  <div class='scard'>
    <div class='snum' style='color:#888'>57.4%</div>
    <div class='slbl2'>Naive baseline</div>
    <div style='font-size:11px;color:#444;margin-top:4px'>always predict "allow"</div>
  </div>
</div>

<div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px;margin-bottom:16px'>
  <div class='slabel' style='margin-top:0'>Per-class metrics</div>
  <table class='dt'>
    <tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr>
    {rows}
  </table>
</div>

<div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px;margin-bottom:16px'>
  <div class='slabel' style='margin-top:0'>Confusion matrix</div>
  <table class='dt'>
    {conf_header}
    {conf_rows}
  </table>
</div>

<div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px;margin-bottom:16px'>
  <div class='slabel' style='margin-top:0'>Per-language breakdown</div>
  <table class='dt'>
    <tr><th>Language</th><th>Count</th><th>Accuracy</th><th>Macro F1</th></tr>
    {lang_rows}
  </table>
</div>

<div class='note'>
  ⚠ These are <strong>demo metrics on a 500-row seed dataset</strong> — not production performance claims.
  The dataset is synthetic + screenshot-inspired. Re-evaluate on real consent-cleared Moctale traffic before deployment.
  Git SHA: <code>1f57aa7</code> · Eval run: 2026-06-26
</div>
"""


def _data_stats_html() -> str:
    sample_rows = ""
    for row in _SAMPLE_ROWS:
        text = row.get("text", "")[:72] + ("…" if len(row.get("text", "")) > 72 else "")
        action = row.get("moderation_action", "")
        lang = row.get("language_mix", "")
        cls = {"allow": "ca", "flag_for_review": "cr", "flag_for_removal": "cx"}.get(action, "")
        sample_rows += f"<tr><td style='color:#888;max-width:420px'>{text}</td><td class='{cls}'>{action.replace('_',' ')}</td><td style='color:#555'>{lang}</td></tr>"

    return f"""
<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-bottom:22px'>
  <div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px'>
    <div class='slabel' style='margin-top:0'>Label distribution (500 rows)</div>
    <table class='dt'>
      <tr><th>Action</th><th>Count</th><th>%</th></tr>
      <tr><td class='ca'>allow</td>            <td>287</td><td style='color:#555'>57.4%</td></tr>
      <tr><td class='cr'>flag_for_review</td>  <td>114</td><td style='color:#555'>22.8%</td></tr>
      <tr><td class='cx'>flag_for_removal</td> <td> 99</td><td style='color:#555'>19.8%</td></tr>
    </table>
  </div>
  <div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px'>
    <div class='slabel' style='margin-top:0'>Source mix</div>
    <table class='dt'>
      <tr><th>Source</th><th>Count</th></tr>
      <tr><td>Screenshot-inspired (rewritten)</td><td>245</td></tr>
      <tr><td>Synthetic</td>                       <td>225</td></tr>
      <tr><td>Open-source (Jigsaw CC0)</td>         <td> 30</td></tr>
    </table>
  </div>
</div>

<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-bottom:22px'>
  <div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px'>
    <div class='slabel' style='margin-top:0'>Language mix</div>
    <table class='dt'>
      <tr><th>Language</th><th>Count</th></tr>
      <tr><td>Hinglish (Latin script)</td><td>326</td></tr>
      <tr><td>English</td>               <td>174</td></tr>
    </table>
  </div>
  <div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px'>
    <div class='slabel' style='margin-top:0'>Severity distribution</div>
    <table class='dt'>
      <tr><th>Severity</th><th>Count</th></tr>
      <tr><td>none</td>    <td>265</td></tr>
      <tr><td>high</td>    <td> 75</td></tr>
      <tr><td>medium</td>  <td> 73</td></tr>
      <tr><td>low</td>     <td> 62</td></tr>
      <tr><td>critical</td><td> 25</td></tr>
    </table>
  </div>
</div>

<div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px;margin-bottom:16px'>
  <div class='slabel' style='margin-top:0'>Sample rows (first 20)</div>
  <table class='dt'>
    <tr><th>Text</th><th>Action</th><th>Language</th></tr>
    {sample_rows}
  </table>
</div>

<div class='note'>
  No raw screenshots, usernames, or handles. Screenshot-inspired rows are scenario rewrites only.
  Open-source rows from Jigsaw CC0 dataset — limited sample, sanitized for links and handles.
  <strong>Do not</strong> use these metrics for production performance claims.
</div>
"""


def _arch_html() -> str:
    pipeline = (
        "  REQUEST\n"
        "     │\n"
        "  ┌──▼──────────────────────┐\n"
        "  │  intake                  │  text validation, ModerationRequest\n"
        "  └──┬──────────────────────┘\n"
        "     │\n"
        "  ┌──▼──────────────────────┐\n"
        "  │  language               │  detect English / Hinglish / Hindi\n"
        "  └──┬──────────────────────┘\n"
        "     │\n"
        "  ┌──▼──────────────────────┐\n"
        "  │  heuristic              │  target detection, phrase match, mention check,\n"
        "  │                         │  severe/directed/threat signals, Hinglish slang\n"
        "  └──┬──────────────────────┘\n"
        "     │\n"
        "  ┌──▼──────────────────────┐\n"
        "  │  ml_toxicity            │  DistilBERT multilingual toxicity score (lazy-loaded)\n"
        "  │                         │  falls back to heuristic score if model unavailable\n"
        "  └──┬──────────────────────┘\n"
        "     │\n"
        "  ┌──▼──────────────────────┐\n"
        "  │  context                │  reply context boost, rating disagreement risk,\n"
        "  │                         │  mention proximity scoring\n"
        "  └──┬──────────────────────┘\n"
        "     │\n"
        "  ┌──▼──────────────────────┐\n"
        "  │  policy                 │  risk score = f(context, mention, sentiment, toxicity)\n"
        "  │                         │  decide_action() → allow / flag_for_review / flag_for_removal\n"
        "  │                         │  conditional RAG (skipped for clearly benign comments)\n"
        "  └──┬──────────────────────┘\n"
        "     │\n"
        "     ├── flag_for_review ──▶  review_queue  (audit log + human review queue)\n"
        "     │\n"
        "     └── allow / removal ──▶  RESULT\n"
    )

    return f"""
<div style='margin-bottom:16px'>
  <div class='slabel' style='margin-top:0'>Agent pipeline</div>
  <div class='arch'>{pipeline}</div>
</div>

<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-bottom:16px'>
  <div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px'>
    <div class='slabel' style='margin-top:0'>Key design choices</div>
    <table class='dt'>
      <tr><th>Decision</th><th>Why</th></tr>
      <tr><td>Heuristics-first</td>     <td style='color:#888'>clear cases skip ML inference entirely</td></tr>
      <tr><td>Target detection</td>     <td style='color:#888'>movie vs person is the core distinction</td></tr>
      <tr><td>Conditional RAG</td>      <td style='color:#888'>semantic search only on uncertain/risky comments</td></tr>
      <tr><td>Lazy ChromaDB</td>        <td style='color:#888'>ChromaDB import crash isolated to startup</td></tr>
      <tr><td>Fail-safe fallback</td>   <td style='color:#888'>pipeline error → flag_for_review, never allow</td></tr>
      <tr><td>Frozen dataclasses</td>   <td style='color:#888'>no accidental mutation of moderation results</td></tr>
    </table>
  </div>
  <div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px'>
    <div class='slabel' style='margin-top:0'>Performance (CPU, no ML model)</div>
    <table class='dt'>
      <tr><th>Scenario</th><th>Typical latency</th></tr>
      <tr><td>Clear movie criticism</td>   <td style='color:#22c55e'>~1–3ms</td></tr>
      <tr><td>Ambiguous Hinglish reply</td><td style='color:#f59e0b'>~2–6ms</td></tr>
      <tr><td>Severe abuse (removal)</td>  <td style='color:#ef4444'>~1–4ms</td></tr>
      <tr><td>With ML model loaded</td>    <td style='color:#888'>+30–80ms per call</td></tr>
    </table>
  </div>
</div>

<div style='background:#161616;border:1px solid #282828;border-radius:8px;padding:18px'>
  <div class='slabel' style='margin-top:0'>Stack</div>
  <table class='dt'>
    <tr><th>Layer</th><th>Technology</th></tr>
    <tr><td>API</td>           <td style='color:#888'>FastAPI + slowapi rate limiting</td></tr>
    <tr><td>Engine</td>        <td style='color:#888'>Pure Python, compiled regex, phrase indexes, LRU cache</td></tr>
    <tr><td>ML model</td>      <td style='color:#888'>gravitee-io/distilbert-multilingual-toxicity-classifier (ONNX-quantized)</td></tr>
    <tr><td>Policy store</td>  <td style='color:#888'>ChromaDB persistent + ONNX sentence-transformers embeddings</td></tr>
    <tr><td>Audit log</td>     <td style='color:#888'>RotatingFileHandler, 10MB × 5 backups, JSONL</td></tr>
    <tr><td>Cache</td>         <td style='color:#888'>In-process LRU (8192 slots), thread-safe counters</td></tr>
    <tr><td>Observability</td> <td style='color:#888'>Prometheus metrics via prometheus-fastapi-instrumentator</td></tr>
  </table>
</div>
"""


def _assumptions_html() -> str:
    return """
<div class='abox'>
  <strong>Core principle — moderate abuse, not taste</strong><br>
  Movie criticism can be angry, harsh, and deeply negative. That is not abuse.
  Abuse starts when the comment targets a person — the reviewer, another user, a community, or a protected group —
  rather than the movie, its craft, or review content.
</div>

<div class='abox'>
  <strong>Target-awareness is the key differentiator</strong><br>
  <code style='background:#1a1a1a;padding:2px 6px;border-radius:3px;font-size:12px'>"This movie is shit"</code> → allow &nbsp;·&nbsp;
  <code style='background:#1a1a1a;padding:2px 6px;border-radius:3px;font-size:12px'>"You are shit"</code> → flag for removal<br><br>
  The system detects 8 target types: <em>movie_show, acting_direction_script, actor_public_work,
  review_content, reviewer_or_user, community_identity, protected_class, unknown.</em>
</div>

<div class='abox'>
  <strong>Hinglish is first-class</strong><br>
  Indian movie review platforms are predominantly Hinglish (Hindi–English code-switched, Latin script).
  The engine includes Devanagari transliteration, Hinglish abuse phrase indexes,
  and per-language eval stratification. Hindi Devanagari coverage is partial — the demo dataset
  is primarily Hinglish Latin and English.
</div>

<div class='abox'>
  <strong>Hybrid approach — heuristics + ML, not ML alone</strong><br>
  A toxicity model alone would flag <em>"this movie is shit"</em> as toxic. The heuristic layer
  runs first and cheaply — most obvious cases (clear movie criticism, clear severe abuse) never
  reach the ML model. ML is a tiebreaker, not the sole arbiter.
</div>

<div class='abox'>
  <strong>Removal = recommendation, not automatic deletion</strong><br>
  flag_for_removal means the engine is confident the comment is severe user-directed abuse.
  In production, removals should still pass through moderator review until appeals, policy finalization,
  and threshold validation on real platform traffic are complete.
</div>

<div class='abox'>
  <strong>What this dataset is NOT</strong><br>
  The 500-row dataset is a synthetic + screenshot-inspired seed for demo and policy testing.
  It is not production training data. Metrics from it are toy metrics.
  No raw screenshots, usernames, or handles are stored — screenshot-inspired rows are
  scenario rewrites only. Open-source rows are from Jigsaw CC0, limited to 30 rows.
</div>

<div class='abox'>
  <strong>Known gaps</strong><br>
  · Hindi Devanagari coverage is limited<br>
  · Protected-class slurs are minimized (hate-speech recall not fully stress-tested)<br>
  · flag_for_removal recall is 57.6% on this dataset — borderline cases go to review conservatively<br>
  · No production validation against real Moctale user traffic yet
</div>

<div class='note' style='margin-top:4px'>
  Before production deployment: run on real consent-cleared Moctale data,
  retune thresholds, add appeal handling, and define moderator workflow.
</div>
"""


# ── Gradio layout ─────────────────────────────────────────────────────────────
EXAMPLES = [
    ["This movie is shit but my problem is only with the pacing.", "main_review"],
    ["Ye film bilkul bakwas thi, screenplay weak tha.", "main_review"],
    ["@reviewer tu chutiya hai, band kar review dena.", "reply_to_review"],
    ["Real id se aao baat karte hain phir.", "reply_to_comment"],
    ["tu chamar hai, review mat de.", "reply_to_comment"],
    ["The acting was genuinely impressive in the second half.", "main_review"],
    ["bc teri maa ki aankh, chal nikal.", "reply_to_comment"],
    ["This reviewer is clearly attention-seeking and wrong about everything.", "reply_to_review"],
    ["TMKC wala director hai yeh.", "main_review"],
    ["Go die if you liked this movie.", "reply_to_review"],
]

CONTEXT_MAP = {
    "Reply to a review": "reply_to_review",
    "Reply to a comment": "reply_to_comment",
    "Main review": "main_review",
}

with gr.Blocks(css=CSS, title="Moctale Moderation AI") as demo:
    gr.HTML("""
    <div style='padding:28px 0 10px;border-bottom:1px solid #1e1e1e;margin-bottom:24px'>
      <div style='display:flex;align-items:flex-end;gap:14px;flex-wrap:wrap'>
        <div>
          <div style='font-size:22px;font-weight:700;color:#e5e5e5;letter-spacing:-0.02em'>
            Moctale Moderation AI
          </div>
          <div style='font-size:13px;color:#555;margin-top:4px'>
            Target-aware comment moderation for Indian movie review platforms ·
            <span style='font-family:"JetBrains Mono",monospace;font-size:11px;
            background:#1a1a1a;padding:2px 7px;border-radius:3px;color:#666'>
            heuristics + ML · Hinglish-aware · CPU-only
            </span>
          </div>
        </div>
      </div>
    </div>
    """)

    with gr.Tabs():

        # ── Tab 1: Live demo ──────────────────────────────────────────────────
        with gr.Tab("Live Demo"):
            gr.HTML("""
            <div style='font-size:13px;color:#555;margin:8px 0 18px'>
              Enter any comment. The engine runs the full agent pipeline and returns
              action, all contributing signals, scores, and the reason for the decision.
            </div>
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    text_in = gr.Textbox(
                        label="Comment text",
                        placeholder="e.g.  @reviewer tu chutiya hai, band kar review dena.",
                        lines=4,
                        max_lines=8,
                    )
                    ctx_in = gr.Radio(
                        choices=list(CONTEXT_MAP.keys()),
                        value="Reply to a review",
                        label="Context",
                    )
                    analyze_btn = gr.Button("Analyze →", variant="primary")

                    gr.HTML("<div style='color:#444;font-size:11px;margin-top:14px'>Quick examples</div>")
                    for ex_text, ex_ctx in EXAMPLES:
                        ctx_label = {v: k for k, v in CONTEXT_MAP.items()}.get(ex_ctx, "Reply to a review")
                        gr.Examples(
                            examples=[[ex_text, ctx_label]],
                            inputs=[text_in, ctx_in],
                            label=None,
                        )

                with gr.Column(scale=1):
                    result_html = gr.HTML(
                        value="<div class='rc' style='color:#333;font-size:13px'>Result will appear here.</div>"
                    )

            def _run(text: str, ctx_label: str) -> str:
                ctx = CONTEXT_MAP.get(ctx_label, "reply_to_review")
                return moderate(text, ctx)

            analyze_btn.click(_run, inputs=[text_in, ctx_in], outputs=[result_html])
            text_in.submit(_run, inputs=[text_in, ctx_in], outputs=[result_html])

        # ── Tab 2: Model stats ────────────────────────────────────────────────
        with gr.Tab("Model Stats"):
            gr.HTML(_model_stats_html())

        # ── Tab 3: Dataset ────────────────────────────────────────────────────
        with gr.Tab("Dataset"):
            gr.HTML(_data_stats_html())

        # ── Tab 4: Architecture ───────────────────────────────────────────────
        with gr.Tab("Architecture"):
            gr.HTML(_arch_html())

        # ── Tab 5: Assumptions ────────────────────────────────────────────────
        with gr.Tab("Design Decisions"):
            gr.HTML(_assumptions_html())

    gr.HTML("""
    <div style='text-align:center;padding:18px 0 8px;border-top:1px solid #1a1a1a;
         margin-top:20px;font-size:11px;color:#3a3a3a;font-family:"JetBrains Mono",monospace'>
      Moctale Moderation AI · demo seed dataset · not production metrics ·
      <a href='https://github.com' style='color:#444'>source</a>
    </div>
    """)


if __name__ == "__main__":
    demo.launch()
