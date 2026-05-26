"""
Build the mcs-lab-auditor overview-and-architecture PDF.

Hand-written reportlab pipeline - no pandoc, wkhtmltopdf, or weasyprint
dependency. Re-run after editing:

  python scripts/Build-OverviewPdf.py [output-path]

Default output path:
  C:\\Users\\dewainr\\Downloads\\mcs-lab-auditor-overview-and-architecture.pdf
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


DEFAULT_OUTPUT = Path(r"C:\Users\dewainr\Downloads\mcs-lab-auditor-overview-and-architecture.pdf")


# ---------------------------------------------------------------------------
# Palette - inspired by modern dev tooling docs (slate + indigo + amber)
# ---------------------------------------------------------------------------

class Theme:
    primary = colors.HexColor("#2563eb")        # indigo-600
    primary_dark = colors.HexColor("#1d4ed8")   # indigo-700
    secondary = colors.HexColor("#0f766e")      # teal-700
    accent = colors.HexColor("#f59e0b")         # amber-500
    ink = colors.HexColor("#0f172a")            # slate-900
    body = colors.HexColor("#1e293b")           # slate-800
    muted = colors.HexColor("#64748b")          # slate-500
    line = colors.HexColor("#cbd5e1")           # slate-300
    panel = colors.HexColor("#f1f5f9")          # slate-100
    panel_soft = colors.HexColor("#f8fafc")     # slate-50
    code_bg = colors.HexColor("#0f172a")
    code_fg = colors.HexColor("#e2e8f0")        # slate-200
    code_accent = colors.HexColor("#7dd3fc")    # sky-300
    info_bg = colors.HexColor("#eff6ff")        # blue-50
    info_border = colors.HexColor("#3b82f6")    # blue-500
    warn_bg = colors.HexColor("#fffbeb")        # amber-50
    warn_border = colors.HexColor("#f59e0b")    # amber-500
    good_bg = colors.HexColor("#ecfdf5")        # emerald-50
    good_border = colors.HexColor("#10b981")    # emerald-500
    white = colors.white


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def build_styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=44, leading=48, spaceAfter=6, alignment=TA_LEFT,
            textColor=Theme.white,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=16, leading=22, spaceAfter=20, alignment=TA_LEFT,
            textColor=Theme.code_accent,
        ),
        "cover_byline": ParagraphStyle(
            "cover_byline", parent=base["Normal"], fontName="Helvetica",
            fontSize=11, leading=15, alignment=TA_LEFT, textColor=Theme.code_fg,
        ),
        "cover_summary": ParagraphStyle(
            "cover_summary", parent=base["Normal"], fontName="Helvetica",
            fontSize=12.5, leading=18, alignment=TA_LEFT, textColor=Theme.code_fg,
            spaceAfter=10,
        ),
        "section_eyebrow": ParagraphStyle(
            "section_eyebrow", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9.5, leading=12, textColor=Theme.primary,
            spaceAfter=2, alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=22, leading=28, spaceBefore=12, spaceAfter=4,
            textColor=Theme.ink, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=14, leading=18, spaceBefore=14, spaceAfter=4,
            textColor=Theme.primary_dark, keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base["Heading3"], fontName="Helvetica-Bold",
            fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=3,
            textColor=Theme.secondary, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=10.5, leading=15.5, spaceBefore=0, spaceAfter=8,
            alignment=TA_JUSTIFY, textColor=Theme.body,
        ),
        "lede": ParagraphStyle(
            "lede", parent=base["BodyText"], fontName="Helvetica",
            fontSize=12, leading=18, spaceBefore=2, spaceAfter=12,
            alignment=TA_JUSTIFY, textColor=Theme.body,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["BodyText"], fontName="Helvetica",
            fontSize=10.5, leading=15, leftIndent=18, bulletIndent=4,
            spaceBefore=0, spaceAfter=4, textColor=Theme.body,
        ),
        "code": ParagraphStyle(
            "code", parent=base["Code"], fontName="Courier",
            fontSize=9.0, leading=12.5, spaceBefore=4, spaceAfter=12,
            leftIndent=10, rightIndent=10, textColor=Theme.code_fg,
            backColor=Theme.code_bg, borderColor=Theme.code_bg,
            borderWidth=0, borderPadding=10,
        ),
        "callout": ParagraphStyle(
            "callout", parent=base["BodyText"], fontName="Helvetica",
            fontSize=10.5, leading=15.5, leftIndent=14, rightIndent=12,
            spaceBefore=4, spaceAfter=12, textColor=Theme.ink,
            backColor=Theme.info_bg, borderColor=Theme.info_border,
            borderWidth=0, borderPadding=12,
        ),
        "callout_label": ParagraphStyle(
            "callout_label", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=10, leading=13, textColor=Theme.info_border,
            spaceBefore=2, spaceAfter=4,
        ),
        "warn": ParagraphStyle(
            "warn", parent=base["BodyText"], fontName="Helvetica",
            fontSize=10.5, leading=15.5, leftIndent=14, rightIndent=12,
            spaceBefore=4, spaceAfter=12, textColor=Theme.ink,
            backColor=Theme.warn_bg, borderColor=Theme.warn_border,
            borderWidth=0, borderPadding=12,
        ),
        "warn_label": ParagraphStyle(
            "warn_label", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9.5, leading=12, textColor=Theme.warn_border,
            spaceAfter=2,
        ),
        "good": ParagraphStyle(
            "good", parent=base["BodyText"], fontName="Helvetica",
            fontSize=10.5, leading=15.5, leftIndent=14, rightIndent=12,
            spaceBefore=4, spaceAfter=12, textColor=Theme.ink,
            backColor=Theme.good_bg, borderColor=Theme.good_border,
            borderWidth=0, borderPadding=12,
        ),
        "good_label": ParagraphStyle(
            "good_label", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9.5, leading=12, textColor=Theme.good_border,
            spaceAfter=2,
        ),
        "toc_title": ParagraphStyle(
            "toc_title", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=14, leading=18, spaceAfter=8, textColor=Theme.muted,
        ),
        "toc_entry": ParagraphStyle(
            "toc_entry", parent=base["Normal"], fontName="Helvetica",
            fontSize=11, leading=18, textColor=Theme.body, leftIndent=0,
        ),
        "toc_entry_num": ParagraphStyle(
            "toc_entry_num", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=11, leading=18, textColor=Theme.primary,
        ),
    }


# ---------------------------------------------------------------------------
# Custom flowables
# ---------------------------------------------------------------------------

class HRule(Flowable):
    """Thin colored rule. Useful as a section divider."""
    def __init__(self, width=None, thickness=1.2, color=Theme.line, space_before=0, space_after=8):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.color = color
        self.space_before = space_before
        self.space_after = space_after

    def wrap(self, avail_w, avail_h):
        self._w = self.width if self.width is not None else avail_w
        self._h = self.thickness + self.space_before + self.space_after
        return (self._w, self._h)

    def draw(self):
        c = self.canv
        c.saveState()
        c.setStrokeColor(self.color)
        c.setLineWidth(self.thickness)
        y = self.space_after + self.thickness / 2
        c.line(0, y, self._w, y)
        c.restoreState()


class AccentChip(Flowable):
    """A horizontal accent bar with a number/label inside - used at section openers."""
    def __init__(self, label, color=Theme.primary, width=None, height=22):
        super().__init__()
        self.label = label
        self.color = color
        self.width = width
        self.height = height

    def wrap(self, avail_w, avail_h):
        self._w = self.width if self.width is not None else avail_w
        return (self._w, self.height + 4)

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self.color)
        c.rect(0, 4, 18, self.height - 8, stroke=0, fill=1)
        c.setFillColor(self.color)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(28, 10, self.label)
        c.restoreState()


# ---------------------------------------------------------------------------
# Page templates
# ---------------------------------------------------------------------------

def cover_page(canvas, doc):
    """Branded cover. Solid background + diagonal accent rule + footer band."""
    w, h = LETTER
    c = canvas
    c.saveState()
    # Solid background
    c.setFillColor(Theme.ink)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    # Accent diagonal stripe
    c.setFillColor(Theme.primary)
    c.beginPath()
    p = c.beginPath()
    p.moveTo(0, h * 0.18)
    p.lineTo(w, h * 0.30)
    p.lineTo(w, h * 0.22)
    p.lineTo(0, h * 0.10)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    # Secondary thin teal stripe
    c.setFillColor(Theme.secondary)
    p2 = c.beginPath()
    p2.moveTo(0, h * 0.085)
    p2.lineTo(w, h * 0.205)
    p2.lineTo(w, h * 0.19)
    p2.lineTo(0, h * 0.07)
    p2.close()
    c.drawPath(p2, stroke=0, fill=1)
    # Footer bar
    c.setFillColor(Theme.primary_dark)
    c.rect(0, 0, w, 0.65 * inch, stroke=0, fill=1)
    c.setFillColor(Theme.code_fg)
    c.setFont("Helvetica", 9.5)
    c.drawString(0.75 * inch, 0.30 * inch, "microsoft / BootcampLabTestPlugin")
    c.drawRightString(w - 0.75 * inch, 0.30 * inch,
                      "Overview & Architecture - " + date.today().isoformat())
    c.restoreState()


def content_page(canvas, doc):
    """Body page. Slim header bar + side accent rule + footer with page number."""
    w, h = LETTER
    c = canvas
    c.saveState()
    # Top accent bar
    c.setFillColor(Theme.primary)
    c.rect(0, h - 0.32 * inch, w, 0.32 * inch, stroke=0, fill=1)
    # Within the top bar - title left, section right
    c.setFillColor(Theme.white)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(0.75 * inch, h - 0.22 * inch, "mcs-lab-auditor")
    c.setFont("Helvetica", 9.0)
    c.setFillColor(Theme.code_accent)
    c.drawRightString(w - 0.75 * inch, h - 0.22 * inch, "Overview & Architecture")
    # Footer divider
    c.setStrokeColor(Theme.line)
    c.setLineWidth(0.5)
    c.line(0.75 * inch, 0.55 * inch, w - 0.75 * inch, 0.55 * inch)
    # Footer text
    c.setFont("Helvetica", 8.5)
    c.setFillColor(Theme.muted)
    c.drawString(0.75 * inch, 0.38 * inch,
                 "BootcampLabTestPlugin / mcs-lab-auditor")
    c.drawRightString(w - 0.75 * inch, 0.38 * inch, f"Page {doc.page - 1}")
    # Slim accent strip on left margin
    c.setFillColor(Theme.primary)
    c.rect(0.35 * inch, 0.55 * inch, 0.04 * inch, h - 0.95 * inch, stroke=0, fill=1)
    c.restoreState()


def make_templates():
    w, h = LETTER

    cover_frame = Frame(
        0.75 * inch, 0.75 * inch,
        w - 1.5 * inch, h - 1.5 * inch,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        showBoundary=0,
    )
    content_frame = Frame(
        0.75 * inch, 0.65 * inch,
        w - 1.5 * inch, h - 1.20 * inch,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        showBoundary=0,
    )

    return [
        PageTemplate(id="cover", frames=[cover_frame], onPage=cover_page),
        PageTemplate(id="content", frames=[content_frame], onPage=content_page),
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def P(styles, key, text):
    return Paragraph(text, styles[key])


def bullets(styles, items):
    return [
        Paragraph(f"<font color='#2563eb'><b>&bull;</b></font>&nbsp;&nbsp;{item}",
                  styles["bullet"])
        for item in items
    ]


def code(styles, text):
    return Preformatted(text, styles["code"])


def callout(styles, label, text, kind="info"):
    body_key, label_key, label_text = {
        "info": ("callout", "callout_label", label or "Note"),
        "warn": ("warn", "warn_label", label or "Heads up"),
        "good": ("good", "good_label", label or "Why this matters"),
    }[kind]
    return KeepTogether([
        Spacer(1, 0.08 * inch),
        Paragraph(label_text.upper(), styles[label_key]),
        Paragraph(text, styles[body_key]),
    ])


def section_opener(styles, number, title, eyebrow=None):
    """Standardized big section opener - chip + heading + accent rule."""
    parts = []
    parts.append(AccentChip(f"SECTION {number}"))
    if eyebrow:
        parts.append(P(styles, "section_eyebrow", eyebrow.upper()))
    parts.append(P(styles, "h1", title))
    parts.append(HRule(thickness=1.5, color=Theme.primary, space_after=8))
    return parts


_TABLE_HEADER_STYLE = ParagraphStyle(
    "tbl_header", fontName="Helvetica-Bold", fontSize=9.5, leading=12,
    textColor=Theme.white, alignment=TA_LEFT,
)
_TABLE_CELL_STYLE = ParagraphStyle(
    "tbl_cell", fontName="Helvetica", fontSize=9.2, leading=12.5,
    textColor=Theme.body, alignment=TA_LEFT,
)


def _wrap_cell(value, style):
    """Convert a cell value into a Paragraph so it word-wraps. Already-flowable values pass through."""
    if hasattr(value, "wrap"):
        return value
    return Paragraph(str(value), style)


def header_table(rows, col_widths, header_color=None):
    header_color = header_color or Theme.ink
    wrapped_rows = []
    for i, row in enumerate(rows):
        style = _TABLE_HEADER_STYLE if i == 0 else _TABLE_CELL_STYLE
        wrapped_rows.append([_wrap_cell(c, style) for c in row])
    tbl = Table(wrapped_rows, colWidths=col_widths, hAlign="LEFT", repeatRows=1, splitByRow=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [Theme.white, Theme.panel_soft]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, Theme.primary),
        ("LINEABOVE", (0, 0), (-1, 0), 0, Theme.white),
        ("BOX", (0, 0), (-1, -1), 0.4, Theme.line),
        ("INNERGRID", (0, 1), (-1, -1), 0.25, Theme.line),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
    ]))
    return tbl


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

def build_story(styles):
    story = []

    # ==================== Cover ====================
    story.append(NextPageTemplate("content"))
    story.append(Spacer(1, 1.5 * inch))
    story.append(P(styles, "cover_byline",
                   "<font color='#7dd3fc'>BOOTCAMP LAB TEST PLUGIN</font>"))
    story.append(Spacer(1, 0.05 * inch))
    story.append(P(styles, "cover_title", "mcs-lab-auditor"))
    story.append(Spacer(1, 0.05 * inch))
    story.append(P(styles, "cover_subtitle",
                   "End-to-end audits for Microsoft Copilot Studio workshop labs."))
    story.append(Spacer(1, 0.35 * inch))
    story.append(P(styles, "cover_summary",
        "A Claude Code plugin that drives the live product UI with Playwright, "
        "judges each step with an LLM, and files GitHub issues + matching fix PRs "
        "against <font face='Courier' color='#7dd3fc'>microsoft/mcs-labs</font> whenever the lab and the "
        "UI disagree."
    ))
    story.append(Spacer(1, 0.25 * inch))
    story.append(P(styles, "cover_byline",
        "Overview &middot; Architecture &middot; Installation &middot; CUA comparison &nbsp;|&nbsp; "
        f"v0.3.0-unreleased &middot; {date.today().isoformat()}"
    ))
    story.append(PageBreak())

    # ==================== TOC ====================
    story.append(P(styles, "toc_title", "CONTENTS"))
    story.append(HRule(thickness=1.5, color=Theme.primary, space_after=10))
    toc_rows = [
        ["1", "Overview", "what the plugin does, top-level entry points"],
        ["2", "Why a CUA cannot replace this", "interview, correction loop, verdicts, static checks, PR authoring"],
        ["3", "Architecture", "boundaries, components, run lifecycle, cross-lab consistency"],
        ["4", "Installation", "prerequisites, step-by-step, first run, Claude Code + Copilot CLI"],
        ["5", "Configuration", "workshop.yml + judge-config.yml keys"],
        ["6", "Troubleshooting", "common failure modes"],
        ["7", "Known limitations", "what this plugin will not do"],
        ["8", "Projected token spend", "per-step / per-lab / per-event estimates + cost knobs"],
        ["9", "Read next", "where to find the operational rulebooks"],
    ]
    toc_styled = []
    for n, title, hint in toc_rows:
        toc_styled.append([
            Paragraph(f"<b><font color='#2563eb'>{n}</font></b>", styles["toc_entry_num"]),
            Paragraph(f"<b>{title}</b><br/><font color='#64748b' size='9'>{hint}</font>",
                      styles["toc_entry"]),
        ])
    toc_table = Table(toc_styled, colWidths=[0.4 * inch, 5.6 * inch])
    toc_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, Theme.line),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ==================== 1. Overview ====================
    story.extend(section_opener(styles, 1, "Overview", eyebrow="What the plugin does"))
    story.append(P(styles, "lede",
        "<font color='#1d4ed8'><b>mcs-lab-auditor</b></font> takes a workshop event (or a single lab) as input and "
        "produces, per lab, either (a) a clean-pass entry in a local audit log, or (b) one "
        "GitHub issue plus one fix-PR against <font face='Courier'>microsoft/mcs-labs</font> describing every step "
        "where the live UI did not match the written instruction. Findings include verbatim "
        "text replacements, screenshot evidence, and machine-readable fingerprints that future "
        "audits use to de-duplicate against the same issue."
    ))
    story.append(P(styles, "body",
        "The plugin is <b>event-aware</b>. Any entry in <font face='Courier'>_data/lab-config.yml.event_configs</font> "
        "(Architecture Bootcamp, Agent Build-A-Thon variants, MCS-in-a-Day variants, the Azure AI "
        "workshop, anything added later) is a valid scope. Single labs can also be audited "
        "individually against the full <font face='Courier'>lab_metadata</font> catalog - independent of any event."
    ))

    story.append(P(styles, "h2", "Top-level entry points"))
    cmd_rows = [
        ["Command", "Purpose"],
        ["/audit-event [--event <key>]",
         "Audit every lab in a workshop event. With --event, pinned; without, the interview asks."],
        ["/audit-bootcamp",
         "Shortcut for /audit-event --event bootcamp."],
        ["/audit-lab [<slug>]",
         "Audit a single lab. With <slug>, scope is pinned. Without, the interview picks from the full all-labs catalog."],
        ["/audit-report [<run-id>]",
         "Print a local summary of recent audit runs. No browser activity."],
        ["/audit-account [show|redeem|clear]",
         "Manage the DPAPI-cached workshop-issued test account."],
    ]
    story.append(header_table(cmd_rows, [2.1 * inch, 4.1 * inch]))

    story.append(P(styles, "h2", "What runs at a glance"))
    story.extend(bullets(styles, [
        "<b>Run-start interview</b> (Q1 account / Q2 phase mix / Q3 scope / Q3a event picker / Q4 lab picker).",
        "<b>Lab parsing</b> into use cases, scenes, and numbered steps. Image refs become semantic hints.",
        "<b>Static fan-out + cross-lab consistency</b> (markdown checks, link checks, image-ref resolution, identifier-token drift between sibling labs).",
        "<b>Interactive step execution</b> via Playwright MCP - one per-Use-Case subagent at a time.",
        "<b>LLM judge</b> emits a structured verdict per step (pass / broken / unclear / non_deterministic / transient / cannot_verify).",
        "<b>Issue + fix-PR, or local log</b>. Findings render to one issue body and one PR with the literal diffs applied.",
    ]))

    # ==================== 2. Why not a CUA ====================
    story.append(PageBreak())
    story.extend(section_opener(styles, 2, "Why a generic Computer-Use Agent (CUA) cannot replace this plugin",
                                eyebrow="Design rationale"))
    story.append(P(styles, "lede",
        "A general-purpose CUA - an agent that observes a screen, plans clicks, and "
        "manipulates the OS through a single screenshot-and-action loop - is the closest "
        "off-the-shelf alternative. It is <b>not a substitute</b>. The plugin combines structured "
        "pre-processing, dynamic verification against a known specification, and downstream "
        "code authorship in ways a CUA pipeline does not."
    ))
    story.append(callout(styles, "Why this matters",
        "The gaps below are not implementation oversights in current CUAs - they are "
        "categorically outside the CUA design contract. A CUA receives a screen and a task, "
        "then optimizes actions. It does not receive a typed lab specification, an issue "
        "tracker, or a git working tree, and it does not maintain a per-step verdict log.",
        kind="good",
    ))

    # 2.1
    story.append(P(styles, "h2", "2.1 &nbsp; No pre-process interview before destructive work"))
    story.append(P(styles, "body",
        "The plugin runs a Phase 1.5 run-start interview before touching anything: it confirms "
        "the account, the phase mix (static / interactive / both), the scope (event vs single lab), "
        "the chosen event, and the chosen lab. Every question is mandatory unless explicitly "
        "skipped by a CLI flag. This safety net catches the &quot;wrong tenant&quot; class of failure "
        "that has already cost real audit time."
    ))
    story.append(P(styles, "body",
        "A CUA invokes immediately on whatever task description it receives. It has no protocol "
        "for pausing and asking the user &quot;which of these six events did you mean?&quot; before "
        "opening the browser, and no structured way to record the answer in a manifest the next "
        "run can resume from."
    ))

    # 2.2
    story.append(P(styles, "h2", "2.2 &nbsp; No interactive problem-solving / correction loop"))
    story.append(P(styles, "body",
        "When the auditor encounters something wrong mid-run, the human can redirect the agent "
        "(&quot;save it before navigating away,&quot; &quot;don't include that NOTE,&quot; &quot;update the actual PNG, "
        "not just alt text&quot;) and the agent updates its working approach in place. This is "
        "interactive problem-solving against the same browser session and the same in-progress "
        "fix branch."
    ))
    story.append(P(styles, "body",
        "A CUA's natural unit is an isolated task with a screen-grounded objective, not a "
        "long-running, redirectable collaboration where corrections compound on a working set "
        "of files."
    ))

    # 2.3
    story.append(P(styles, "h2", "2.3 &nbsp; No dynamic verification of screenshots against a typed lab spec"))
    story.append(P(styles, "body",
        "For each numbered step, the plugin captures a before-snapshot, dispatches the step, "
        "captures an after-snapshot and a screenshot, and feeds all three to an LLM judge "
        "alongside the raw markdown instruction. The judge returns a structured verdict "
        "(<b>pass / broken / unclear / non_deterministic / transient / cannot_verify</b>) with "
        "confidence and a <font face='Courier'>suggested_correction</font> that points at the literal text in "
        "the lab to replace."
    ))
    story.append(P(styles, "body",
        "A CUA watches a screen and acts. It does not have a typed specification (parsed lab "
        "markdown, expected visual references, alert blocks attached as hints) to verify against, "
        "and it does not produce structured per-step verdicts that an issue body can be rendered "
        "from."
    ))

    # 2.4
    story.append(P(styles, "h2", "2.4 &nbsp; No static-phase analysis"))
    story.append(P(styles, "body",
        "Roughly a third of real findings never appear on a screen: typos, broken external URLs, "
        "anchor-hash mismatches, image references that point at deleted files, front-matter "
        "versus body-table divergences, and cross-lab drift in column names or control labels. "
        "The plugin's static fan-out runs one subagent per lab against the raw markdown, then "
        "a fan-in pass groups scenes across labs by shape hash and emits drift findings - e.g. "
        "<font face='Courier'>Address 1: State/Province</font> in one lab versus <font face='Courier'>Address1: State or "
        "Providence</font> in a sibling lab."
    ))
    story.append(callout(styles, "Static + screen, not screen-only",
        "A CUA never reads the markdown source. It only sees what the browser renders. Static "
        "findings - typos, drift, broken refs - are invisible to it by construction.",
        kind="warn",
    ))

    # 2.5
    story.append(P(styles, "h2", "2.5 &nbsp; No GitHub issue or PR authorship"))
    story.append(P(styles, "body",
        "The plugin closes the loop. For every lab with findings, it (a) files a GitHub issue "
        "(or fingerprint-dedup-comments on the existing one) describing every finding with a "
        "literal diff, evidence path, and severity tag, and (b) opens a fix-PR on branch "
        "<font face='Courier'>dewain/fix-&lt;slug&gt;-content-audit</font> that applies the <font face='Courier'>suggested_correction</font> "
        "diffs to the lab markdown and copies any refreshed screenshots into "
        "<font face='Courier'>labs/&lt;slug&gt;/images/</font>."
    ))
    story.append(P(styles, "body",
        "A CUA does not write source files or open pull requests. Even a CUA wired to a code "
        "editor would lack the per-finding fingerprint dedup and the same-author / mergeable / "
        "unprotected-branch guardrails the plugin enforces."
    ))

    # 2.6
    story.append(P(styles, "h2", "2.6 &nbsp; No structured resume / context-window management"))
    story.append(P(styles, "body",
        "An 11-lab bootcamp generates more accessibility snapshots, screenshots, console "
        "messages, and network records than a single agent's context window can hold. The "
        "plugin slices each lab into per-Use-Case subagents (5-20 steps each), writes "
        "<font face='Courier'>uc-&lt;N&gt;-state.yml</font> handoffs, and resumes interrupted runs at the first UC "
        "missing a state file."
    ))
    story.append(P(styles, "body",
        "A CUA is a single agent with a single rolling context. It has no equivalent of "
        "<font face='Courier'>--resume &lt;run-id&gt;</font> against per-UC checkpoints, and a long audit hits its "
        "context limits long before the run completes."
    ))

    story.append(callout(styles, "Summary",
        "A CUA is good at executing a single screen-bound task. The plugin is structured around "
        "the entire audit pipeline - pre-process interview, lab-aware parsing, dynamic "
        "verification with structured verdicts, static checks the screen never reveals, and "
        "downstream issue+PR authorship - and the value <b>compounds across those stages</b>. "
        "Replacing the pipeline with one CUA loop would drop everything except step 2.3, and even "
        "that loses the structured verdict it depends on.",
        kind="good",
    ))

    # ==================== 3. Architecture ====================
    story.append(PageBreak())
    story.extend(section_opener(styles, 3, "Architecture", eyebrow="How it works"))
    story.append(P(styles, "lede",
        "The plugin has no compiled code and no test runner. Claude is the runtime; the plugin "
        "is a tree of markdown (commands, skills, references) and YAML configuration. It "
        "orchestrates three external systems: the user's filesystem (the cloned <font face='Courier'>mcs-labs</font> "
        "repo), the Playwright MCP (a real browser against Microsoft product portals), and the "
        "GitHub Issues + PRs APIs."
    ))

    story.append(P(styles, "h2", "Boundaries"))
    story.extend(bullets(styles, [
        "<b>Source-of-truth boundary</b> - <font face='Courier'>_data/lab-config.yml</font> provides the event "
        "catalog (<font face='Courier'>event_configs.&lt;key&gt;</font>) and the all-labs catalog "
        "(<font face='Courier'>lab_metadata.*</font>). Slug lists are never hard-coded in the plugin.",
        "<b>Write boundary</b> - three narrow paths: (i) <font face='Courier'>gh issue create | comment | edit</font>; "
        "(ii) <font face='Courier'>gh pr create</font> on per-slug fix branches; (iii) <font face='Courier'>git push</font> of one "
        "screenshots-only commit onto an already-open fix-PR.",
        "<b>Secret boundary</b> - workshop credentials live only in <font face='Courier'>runtime/account/credential.enc</font> "
        "(DPAPI-encrypted, current-user scope) and in memory for one sign-in dispatch.",
    ]))

    story.append(P(styles, "h2", "Components"))
    cmp_rows = [
        ["Component", "Role"],
        ["commands/", "Slash command entry points (audit-event, audit-bootcamp, audit-lab, audit-report, audit-account)."],
        ["skills/mcs-lab-auditor/", "Primary orchestrator: pre-flight, interview, parse, dispatch, judge, file."],
        ["skills/mcs-lab-issue-filer/", "Render findings.json into an issue body and create or comment via gh."],
        ["skills/mcs-lab-fix-pr-filer/", "Apply suggested_correction diffs to lab files, commit, push, open PR."],
        ["skills/mcs-lab-pr-appender/", "Push a screenshots-only commit onto an already-open fix-PR branch."],
        ["references/", "Operational rulebooks loaded on demand."],
        ["config/workshop.yml", "Workshop portal URL + redemption selectors."],
        ["config/judge-config.yml", "Confidence thresholds, retry caps, dedup config, cross-lab consistency knobs."],
        ["runtime/account/", "DPAPI-encrypted credentials + non-secret account metadata."],
        ["runtime/runs/<id>/", "Per-run parsed steps, findings, screenshots, transcripts, issue bodies."],
        ["runtime/audit-history.yml", "Rolling local log of every audit run, pass or fail."],
    ]
    story.append(header_table(cmp_rows, [2.0 * inch, 4.2 * inch]))

    story.append(P(styles, "h2", "Run lifecycle"))
    story.append(P(styles, "body",
        "Phases reference <font face='Courier'>skills/mcs-lab-auditor/SKILL.md</font>:"
    ))
    phase_rows = [
        ["Phase", "What happens"],
        ["1", "Pre-flight: load configs, build events map + all-labs catalog, check gh auth."],
        ["1.4", "Existing-state probe: gh issue list + gh pr list per slug. Output: existing-state.yml."],
        ["1.5", "Run-start interview (Q1-Q4)."],
        ["1.6", "Lab Resources discovery + pre-flight scrape (conditional)."],
        ["1.7", "Plan execution order. Static fan-out per lab; step 1a: cross-lab consistency fan-in."],
        ["2", "Interactive per-lab loop. Each lab is sliced into per-Use-Case subagents."],
        ["3", "Wrap-up: close browser, print summary, save manifest."],
    ]
    story.append(header_table(phase_rows, [0.55 * inch, 5.65 * inch]))

    story.append(P(styles, "h2", "Per-step data flow"))
    story.append(P(styles, "body",
        "Inside one step of one scene of one lab:"
    ))
    story.append(code(styles,
        "step (from steps.json)\n"
        "    -> _browser_snapshot (before)\n"
        "    -> dispatch by kind  (navigate / click / type / select / wait / inspect)\n"
        "    -> _browser_snapshot (after) + _browser_take_screenshot\n"
        "    -> _browser_console_messages + _browser_network_requests\n"
        "    -> judge prompt (per-step)\n"
        "         outcome:    pass | broken | unclear | non_deterministic |\n"
        "                     transient | cannot_verify\n"
        "         confidence: 0..1\n"
        "         suggested_correction: { original_text, proposed_text,\n"
        "                                  rationale, scope }\n"
        "    -> critique pass (optional second opinion)\n"
        "    -> append to findings.json (unless pass)"
    ))

    story.append(P(styles, "h2", "Cross-lab consistency check"))
    story.append(P(styles, "body",
        "After the static fan-out completes, a single fan-in pass groups scenes by shape "
        "hash across the lab set and emits drift findings for divergent identifier tokens. "
        "Sibling labs that verify the same UI surface get their wording aligned. Findings "
        "are severity <font face='Courier'>low</font> with <font face='Courier'>flags.cross_lab_drift: true</font> and render under "
        "a dedicated &quot;Cross-lab consistency&quot; section in issue bodies."
    ))
    story.append(callout(styles, "Live example",
        "Discovered between <font face='Courier'>mcs-multi-agent</font> UC3 and <font face='Courier'>mcs-orchestration</font> UC1 during the "
        "2026-05-26 audit cycle: same Account Data Lookup Agent verification flow, but one lab "
        "said <font face='Courier'>Address1: State or Providence</font> and the other (correct) said "
        "<font face='Courier'>Address 1: State/Province</font>. The cross-lab check now catches this class of drift "
        "at fan-in time.",
        kind="info",
    ))

    # ==================== 4. Installation ====================
    story.append(PageBreak())
    story.extend(section_opener(styles, 4, "Installation", eyebrow="From clone to first audit"))
    story.append(P(styles, "lede",
        "Windows-only (DPAPI dependency). Targets PowerShell 7+ and Claude Code with the global "
        "Playwright MCP plugin enabled."
    ))

    story.append(P(styles, "h2", "Prerequisites"))
    story.extend(bullets(styles, [
        "Windows 10 or 11 (DPAPI is required for credential storage).",
        "<font face='Courier'>gh</font> CLI authenticated against <font face='Courier'>microsoft/mcs-labs</font>.",
        "PowerShell 7+ (<font face='Courier'>$PSVersionTable.PSVersion.Major</font> &gt;= 7).",
        "Claude Code with the Playwright MCP plugin enabled (<font face='Courier'>playwright@claude-plugins-official</font>).",
        "A local clone of <font face='Courier'>microsoft/mcs-labs</font> at <font face='Courier'>C:\\Users\\&lt;you&gt;\\mcs-labs</font>.",
        "An unredeemed workshop code for the event you plan to audit.",
    ]))

    story.append(P(styles, "h2", "Step 1 - Clone the plugin"))
    story.append(P(styles, "body",
        "The plugin is a directory of markdown and YAML - no compiled artifacts. Both "
        "<b>Claude Code</b> and <b>GitHub Copilot CLI</b> auto-discover plugins from their "
        "respective user-plugins directories; install via <font face='Courier'>git clone</font> into the right place. "
        "Pick whichever runtime(s) you want."
    ))
    story.append(P(styles, "h3", "Option A &mdash; Claude Code (primary, fully tested)"))
    story.append(code(styles,
        "git clone https://github.com/microsoft/BootcampLabTestPlugin `\n"
        "    \"$env:USERPROFILE\\.claude\\plugins\\mcs-lab-auditor\""
    ))
    story.append(P(styles, "h3", "Option B &mdash; GitHub Copilot CLI"))
    story.append(P(styles, "body",
        "Same skill-discovery model, different plugins directory. Find the directory with "
        "<font face='Courier'>copilot --help</font> (look for the <i>plugins</i> or <i>extensions</i> section) or "
        "<font face='Courier'>copilot config get plugins.path</font> if your version supports it. Then:"
    ))
    story.append(code(styles,
        "# Example - confirm $copilotPluginsPath against `copilot --help` first\n"
        "git clone https://github.com/microsoft/BootcampLabTestPlugin `\n"
        "    (Join-Path $copilotPluginsPath \"mcs-lab-auditor\")"
    ))
    story.append(callout(styles, "Copilot CLI caveats",
        "Some command files hard-code <font face='Courier'>$env:USERPROFILE\\.claude\\plugins\\mcs-lab-auditor</font> "
        "in their preflight <font face='Courier'>!</font> interpolations. Adjust to your Copilot CLI plugins "
        "directory or use a symlink (see Option C). Workshop-portal redemption needs Playwright "
        "MCP tools - if your Copilot CLI session lacks them, use <font face='Courier'>--static-only</font> for "
        "doc-audit sweeps and fall back to Claude Code for the interactive phase. DPAPI is "
        "Windows-only regardless of runtime.",
        kind="warn",
    ))
    story.append(P(styles, "h3", "Option C &mdash; both at once"))
    story.append(P(styles, "body",
        "Symlink (or hardlink) the Copilot CLI directory at the Claude Code clone so both "
        "runtimes share one source of truth:"
    ))
    story.append(code(styles,
        "# Elevated PowerShell required for directory symlinks\n"
        "New-Item -ItemType SymbolicLink `\n"
        "    -Path (Join-Path $copilotPluginsPath \"mcs-lab-auditor\") `\n"
        "    -Target \"$env:USERPROFILE\\.claude\\plugins\\mcs-lab-auditor\""
    ))

    story.append(P(styles, "h2", "Step 2 - Restart your runtime"))
    story.append(P(styles, "body",
        "Plugins are discovered at session start. Close Claude Code (or end your Copilot CLI "
        "session) completely and reopen. Type <font face='Courier'>/</font> in the prompt and verify these "
        "commands appear: <font face='Courier'>/audit-event</font>, <font face='Courier'>/audit-bootcamp</font>, "
        "<font face='Courier'>/audit-lab</font>, <font face='Courier'>/audit-report</font>, <font face='Courier'>/audit-account</font>."
    ))

    story.append(P(styles, "h2", "Step 3 - Configure the workshop portal"))
    story.append(P(styles, "body",
        "Edit <font face='Courier'>config/workshop.yml</font> (the first redemption flow can also auto-prompt for "
        "the URL if it is still the placeholder)."
    ))
    story.append(code(styles,
        "workshop_portal_url: \"https://your-workshop-portal/...\"\n"
        "portal_kind:         \"chatbot\"     # chatbot | skillable | email\n"
        "tenant_hint:         \"your-label\""
    ))

    story.append(P(styles, "h2", "Step 4 - Redeem a workshop code (one-time per event)"))
    story.append(code(styles, "/audit-account redeem"))
    story.append(P(styles, "body",
        "The redemption flow prompts for the code, navigates the portal, scrapes the issued "
        "credentials, signs in to <font face='Courier'>login.microsoftonline.com</font>, and DPAPI-encrypts the "
        "blob to <font face='Courier'>runtime/account/credential.enc</font>. Verify with <font face='Courier'>/audit-account show</font>."
    ))

    story.append(P(styles, "h2", "Step 5 - Smoke-test the parser (no browser)"))
    story.append(code(styles, "/audit-lab core-concepts-analytics-evaluations --dry-run"))

    story.append(P(styles, "h2", "Step 6 - Single-lab run"))
    story.append(code(styles, "/audit-lab core-concepts-analytics-evaluations"))
    story.append(P(styles, "body",
        "Expect 5-10 minutes. The plugin either appends a clean-pass entry to "
        "<font face='Courier'>runtime/audit-history.yml</font>, or files one GitHub issue + opens one fix-PR "
        "with the URLs printed in the summary."
    ))

    story.append(P(styles, "h2", "Step 7 - Full event sweep"))
    story.append(code(styles,
        "/audit-bootcamp                               # shortcut: event = bootcamp\n"
        "/audit-event --event agent-buildathon-1month  # any other event by key\n"
        "/audit-event                                  # interview picks the event"
    ))
    story.append(P(styles, "body",
        "Expect 3-8 hours for the 11-lab bootcamp. The plugin checkpoints at every scene "
        "boundary. If it dies mid-run, resume with the printed run-id:"
    ))
    story.append(code(styles, "/audit-event --resume <run-id>"))

    # ==================== 5. Configuration ====================
    story.append(PageBreak())
    story.extend(section_opener(styles, 5, "Configuration", eyebrow="Knobs you may want to tune"))
    story.append(P(styles, "h2", "config/workshop.yml"))
    story.append(P(styles, "body",
        "Workshop portal URL + redemption selectors. Edit on first install per your event organizer."
    ))
    story.append(P(styles, "h2", "config/judge-config.yml &mdash; selected keys"))
    cfg_rows = [
        ["Key", "Default", "Effect"],
        ["confidence.min_to_include_in_issue", "0.5", "Findings below this never reach an issue."],
        ["confidence.low_confidence_marker_max", "0.7", "Findings in 0.5-0.7 are tagged 'low confidence' in the issue body."],
        ["execution.require_interactive_phase", "true", "Skip Phase 2 only when explicitly opted out."],
        ["execution.account_prompt_mode", "always", "Q1 interview behavior."],
        ["execution.network_retry_count", "3", "Connection-class failures retry up to N times before halting."],
        ["execution.fanout_concurrency", "1", "Parallel interactive browser sessions per account."],
        ["execution.static_fanout_concurrency", "11", "Background subagents for the static phase."],
        ["consistency.cross_lab_enabled", "true", "Enable the Phase 1.7 step 1a fan-in pass."],
        ["consistency.cross_lab_similarity_threshold", "0.85", "Threshold for near-match drift detection."],
        ["issues.pr_append.enabled_by_default", "true", "Screenshot-refresh commits onto open fix-PRs."],
        ["non_deterministic_lab_slugs", "[agent-builder-m365, mcs-multi-agent]", "Labs that default to log-only (no issue) unless --force-issue."],
        ["execution.model.preset", "prompt", "prompt | optimized | opus | custom. 'prompt' asks the Phase 1.5 Q2a model question."],
        ["execution.model.uc_subagent", "sonnet", "Per-UC subagent model (Playwright loop)."],
        ["execution.model.judge", "sonnet", "Per-step LLM judge."],
        ["execution.model.critique", "sonnet", "Second-opinion critique pass."],
        ["execution.model.static_subagent", "haiku", "Per-lab static-phase fan-out subagent."],
        ["execution.model.cross_lab", "sonnet", "Cross-lab consistency fan-in."],
        ["execution.model.lab_parser", "sonnet", "Markdown -> step tree."],
        ["execution.model.issue_filer", "haiku", "Render issue body + gh issue create."],
        ["execution.model.fix_pr_filer", "haiku", "Apply suggested_correction diffs + open PR."],
        ["execution.model.pr_appender", "haiku", "Screenshot-only commit to open fix-PR branch."],
    ]
    story.append(header_table(cfg_rows, [2.4 * inch, 1.1 * inch, 2.5 * inch]))

    story.append(P(styles, "h3", "Model preset (Phase 1.5 Q2a)"))
    story.append(P(styles, "body",
        "The orchestrator is always Opus (asserted at Phase 1 step 1). The "
        "<font face='Courier'>execution.model.preset</font> key controls sub-agent model selection:"
    ))
    story.extend(bullets(styles, [
        "<b>prompt</b> (factory default) - Phase 1.5 Q2a asks the user which preset to use this run.",
        "<b>optimized</b> - each per-function key above is used as-is. Sonnet for UI reasoning + judge, Haiku for filers + static fan-out.",
        "<b>opus</b> - every per-function key is forced to opus.",
        "<b>custom</b> - read each per-function key literally (no preset rule). Use to mix-and-match.",
    ]))
    story.append(P(styles, "body",
        "Override per run with <font face='Courier'>--model-preset optimized|opus|custom</font> on any "
        "<font face='Courier'>/audit-*</font> command."
    ))

    # ==================== 6. Troubleshooting ====================
    story.append(PageBreak())
    story.extend(section_opener(styles, 6, "Troubleshooting", eyebrow="When things go sideways"))
    story.extend(bullets(styles, [
        "<b>Slash commands don't appear</b> - restart Claude Code. Plugins are discovered at session start.",
        "<b>gh auth fails</b> - <font face='Courier'>gh auth status</font> must succeed and the user must have viewer permission on <font face='Courier'>microsoft/mcs-labs</font>.",
        "<b>credential.enc unreadable</b> - DPAPI keys are bound to (Windows user, machine). If you switched user or moved the machine, <font face='Courier'>/audit-account clear</font> then <font face='Courier'>/audit-account redeem</font> with a fresh code.",
        "<b>Workshop portal mismatch</b> - confirm <font face='Courier'>config/workshop.yml.portal_kind</font> matches the actual portal (chatbot vs Skillable vs email).",
        "<b>Lab file missing</b> - per-slug skip with <font face='Courier'>status: skipped, reason: lab_file_missing</font>. The whole run continues.",
        "<b>Stuck mid-lab</b> - every scene boundary writes <font face='Courier'>checkpoint.yml</font>. Resume with <font face='Courier'>/audit-event --resume &lt;run-id&gt;</font>.",
    ]))

    # ==================== 7. Limitations ====================
    story.extend(section_opener(styles, 7, "Known limitations", eyebrow="What the plugin will not do"))
    story.extend(bullets(styles, [
        "Windows-only (DPAPI).",
        "Single workshop-portal flow assumed (chatbot is the current default). Other portals require editing <font face='Courier'>config/workshop.yml.portal_kind</font> and the matching redemption reference.",
        "Screenshots aren't attached inline to issues - <font face='Courier'>gh issue create</font> doesn't support file uploads. Paths reference local run artifacts; maintainers can request the artifact for triage.",
        "No automatic tenant cleanup. Orphan agents created during audit runs accumulate; tenant hygiene is the user's responsibility.",
        "Cross-lab consistency in single-lab runs is discovery-limited - it can only diff against previously-audited siblings on disk.",
    ]))

    # ==================== 8. Projected token spend ====================
    story.append(PageBreak())
    story.extend(section_opener(styles, 8, "Projected token spend", eyebrow="What it costs to run"))
    story.append(P(styles, "lede",
        "These are field estimates calibrated against the bootcamp runs done during the "
        "May 2026 audit cycle. Token spend is dominated by the per-step LLM judge call - "
        "every other line item rounds to noise next to it."
    ))

    story.append(P(styles, "h2", "Method"))
    story.append(P(styles, "body",
        "Measured one representative bootcamp lab end-to-end "
        "(<font face='Courier'>core-concepts-agent-knowledge-tools</font>): 77 executable steps after the "
        "parser-spec pass, across 4 use cases and 16 scenes. The 11-lab bootcamp totals "
        "~720 judge-relevant steps. Other events are scaled by their step counts."
    ))

    story.append(P(styles, "h2", "Per-step token budget"))
    story.append(P(styles, "body",
        "Each step's judge call assembles a structured prompt around the parsed instruction "
        "plus the live UI evidence. Typical breakdown:"
    ))
    perstep_rows = [
        ["Input segment", "Tokens (avg)", "Notes"],
        ["Step instruction (raw_markdown + hints + sub-bullets)", "~800", "Bounded by parser output, ~109 chars per step measured."],
        ["CTX_VARS from prior UCs", "~500", "Agent names, schema names, knowledge URLs created upstream."],
        ["Before-snapshot (accessibility tree)", "~2,000", "Copilot Studio dialogs are dense; range 1.5-3k."],
        ["After-snapshot", "~2,000", "Same shape as before-snapshot."],
        ["Screenshot (vision)", "~1,500", "Token-equivalent for the page image."],
        ["Console + failed-network excerpts", "~300", "Usually small; large on broken steps."],
        ["Judge prompt scaffolding + JSON contract", "~600", "Stable across runs; benefits most from prompt cache."],
        ["<b>TOTAL input per step</b>", "<b>~7,700</b>", "Range observed: 6.5k - 9.5k."],
        ["<b>TOTAL output per step</b>", "<b>~300</b>", "Most steps pass (short verdict); findings add 200-400."],
    ]
    story.append(header_table(perstep_rows, [2.8 * inch, 0.9 * inch, 2.6 * inch]))

    story.append(callout(styles, "Critique pass",
        "Default-on. Only fires for non-pass verdicts (~10-20% of steps), so the realistic "
        "overhead is ~12% added input and ~10% added output across the run - not 100%. "
        "Disable in <font face='Courier'>config/judge-config.yml</font> with <font face='Courier'>critique.enabled: false</font> if "
        "you're cost-sensitive and willing to accept a higher false-positive rate.",
        kind="info",
    ))

    story.append(P(styles, "h2", "Per-lab estimate"))
    perlab_rows = [
        ["Lab", "Steps (parsed)", "Input tokens (M)", "Output tokens (k)"],
        ["agent-builder-m365", "~50", "0.50", "25"],
        ["core-concepts-agent-knowledge-tools (measured)", "77", "0.76", "35"],
        ["core-concepts-variables-agents-channels", "~60", "0.59", "28"],
        ["core-concepts-analytics-evaluations", "~60", "0.59", "28"],
        ["mcs-alm", "~40", "0.40", "20"],
        ["component-collections", "~45", "0.45", "22"],
        ["mcs-tools (largest)", "~135", "1.36", "55"],
        ["mcs-orchestration", "~80", "0.79", "36"],
        ["mcs-governance", "~85", "0.84", "38"],
        ["mcs-multi-agent", "~75", "0.74", "34"],
        ["autonomous-account-news", "~40", "0.40", "20"],
        ["Bootcamp total (11 labs)", "~720", "~7.4 M", "~330 k"],
    ]
    story.append(header_table(perlab_rows, [2.6 * inch, 1.0 * inch, 1.3 * inch, 1.3 * inch]))
    story.append(P(styles, "body",
        "Includes: per-step judge calls + critique overhead + parser pass + static-phase fan-out "
        "+ cross-lab consistency + UC handoff state files + per-lab issue and PR rendering + "
        "orchestrator coordination. Excludes: account redemption (one-time ~20k), interview "
        "(~5k), and Claude Code's own prompt-cache reuse (which materially lowers the realized "
        "cost - see &quot;Prompt cache effect&quot; below)."
    ))

    story.append(P(styles, "h2", "Per-event estimate"))
    perevent_rows = [
        ["Event", "Labs", "Input tokens", "Output tokens"],
        ["bootcamp", "11", "~7.4 M", "~330 k"],
        ["agent-buildathon-1month", "8", "~5.4 M", "~250 k"],
        ["azure-ai-workshop", "5", "~3.4 M", "~150 k"],
        ["mcs-in-a-day", "5", "~3.0 M", "~135 k"],
        ["mcs-in-a-day-v2", "4", "~2.5 M", "~115 k"],
        ["agent-buildathon-1day", "2", "~1.0 M", "~45 k"],
    ]
    story.append(header_table(perevent_rows, [2.2 * inch, 0.7 * inch, 1.6 * inch, 1.4 * inch]))

    story.append(P(styles, "h2", "USD ranges (without prompt caching)"))
    story.append(P(styles, "body",
        "Multiplied through with model pricing as of late 2025. Prompt caching can cut "
        "realized input cost 50-90% on repeated reads of stable content (schema files, "
        "judge templates, parser spec) - see the next subsection."
    ))
    cost_rows = [
        ["Model", "$ / Mtok in", "$ / Mtok out", "Per medium lab", "Per bootcamp event"],
        ["Opus 4.7", "$15", "$75", "~$13-18", "~$140"],
        ["Sonnet 4.6", "$3", "$15", "~$3-4", "~$28"],
        ["Haiku 4.5", "$1", "$5", "~$1", "~$9"],
        ["Mixed (Opus orch + Sonnet judge)", "-", "-", "~$5", "~$50"],
    ]
    story.append(header_table(cost_rows, [2.3 * inch, 0.9 * inch, 0.95 * inch, 1.05 * inch, 1.1 * inch]))
    story.append(callout(styles, "Prompt cache effect",
        "The Anthropic prompt cache has a 5-minute TTL. Within a single audit run, "
        "the parser spec, finding schema, judge template, and lab-config catalog are "
        "read repeatedly across every per-UC subagent and every per-step judge call. "
        "Empirically the cache hit rate for those segments lands in the 70-90% range, "
        "which trims realized input cost on Opus from ~$110 to roughly $30-60 for a "
        "full bootcamp run. The exact realized cost depends on how many subagents "
        "spawn in parallel (each one pays the cold cache once) and how much the "
        "browser session lingers on the same page between steps.",
        kind="info",
    ))

    story.append(P(styles, "h2", "Knobs to reduce spend"))
    story.extend(bullets(styles, [
        "<b>--static-only</b> - skips Phase 2 entirely. Cuts ~95% of input tokens. Useful for doc-only sweeps where you just want spelling, link, image-ref, and cross-lab drift findings. Trade-off: misses live UI drift.",
        "<b>critique.enabled: false</b> in <font face='Courier'>config/judge-config.yml</font> - cuts ~10-15%. Raises false positives slightly; the issue body's &quot;low confidence&quot; markers compensate.",
        "<b>--model-preset optimized</b> (Phase 1.5 Q2a default) - the judge call dominates spend, so dropping the judge from Opus to Sonnet while keeping the orchestrator on Opus yields the best $-per-coverage trade. The <font face='Courier'>optimized</font> preset also drops the static fan-out + issue/PR filers to Haiku (they're text-only). One CLI flag swap; per-function overrides live in <font face='Courier'>config/judge-config.yml.execution.model.*</font>.",
        "<b>--labs csv</b> - cap scope to the labs you actually care about. Cost scales linearly with step count.",
        "<b>Reuse the cached account</b> - <font face='Courier'>account_prompt_mode: only_if_expired</font> avoids re-running redemption (~20k tokens). Accept the safety trade-off documented in Phase 1.5.",
        "<b>Resume rather than restart</b> - <font face='Courier'>/audit-event --resume &lt;run-id&gt;</font> skips finished UCs and replays their state files instead of re-judging.",
    ]))

    story.append(callout(styles, "Bottom line",
        "Plan ~$30-$60 per full bootcamp audit run on Opus 4.7 with prompt caching, or "
        "~$5-$12 per single-lab run. Sonnet-as-judge with Opus orchestrator drops those "
        "to ~$10-$15 and ~$2-$3 respectively. Static-only sweeps are effectively free "
        "(under $1 across all 11 labs). Token spend is dominated by per-step judge calls "
        "- the static and orchestrator phases are rounding error.",
        kind="good",
    ))

    # ==================== 9. Read next ====================
    story.extend(section_opener(styles, 9, "Read next", eyebrow="Operational references"))
    refs = [
        ("skills/mcs-lab-auditor/SKILL.md", "Full orchestrator procedure."),
        ("skills/mcs-lab-auditor/references/cross-lab-consistency.md", "Cross-lab drift algorithm + finding format."),
        ("skills/mcs-lab-auditor/references/lab-parser-spec.md", "Markdown -> step tree grammar + scene-fingerprint sidecar."),
        ("skills/mcs-lab-auditor/references/playwright-cookbook.md", "Sign-in flow, scene-boundary auth probe, tool mapping per step kind."),
        ("skills/mcs-lab-auditor/references/finding-schema.md", "Finding record schema + outcome/severity rubric."),
        ("docs/architecture.md", "Architecture deep-dive with Mermaid diagrams."),
        ("docs/installation.md", "Full step-by-step install with troubleshooting."),
        ("docs/extending.md", "Adapting to a new event, portal, or repo location."),
        ("docs/security.md", "What is encrypted, what is logged, what is at risk."),
        ("CHANGELOG.md", "Version history."),
    ]
    ref_rows = [["File", "Read when..."]] + [[a, b] for a, b in refs]
    story.append(header_table(ref_rows, [3.6 * inch, 2.6 * inch]))

    return story


def main(argv):
    output = DEFAULT_OUTPUT
    if len(argv) > 1:
        output = Path(argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(output),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="mcs-lab-auditor - overview & architecture",
        author="dewainr@microsoft.com",
        subject="Plugin overview, architecture, and installation guide",
        keywords="mcs-labs, Copilot Studio, audit, Playwright, CUA",
    )
    doc.addPageTemplates(make_templates())

    styles = build_styles()
    story = build_story(styles)
    doc.build(story)

    print(f"Wrote {output}")


if __name__ == "__main__":
    main(sys.argv)
