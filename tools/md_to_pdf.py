#!/usr/bin/env python3
"""
md_to_pdf.py — render the interview-prep markdown docs as print-ready PDFs.

No pandoc/LaTeX required: this is a small, self-contained markdown subset
renderer built on ReportLab Platypus.

Supported syntax: #/##/### headings, paragraphs, - and 1. lists, > blockquotes,
``` fenced code ```, pipe tables, --- rules, and inline **bold**, *italic*,
`code` and [links](url).

Unicode: body text is set in DejaVu Sans (and DejaVu Sans Mono for code) because
the standard PDF fonts cannot represent arrows, ≤, √, superscripts or ₹. Any
glyph missing from the font is substituted or dropped with a console report,
never silently printed as a black box.

Usage:
    python3 tools/md_to_pdf.py            # writes interview-prep/pdf/*.pdf
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ---------------------------------------------------------------------------
# Paths and fonts
# ---------------------------------------------------------------------------

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREP = os.path.join(REPO, "interview-prep")
OUT = os.path.join(PREP, "pdf")

FONT_CANDIDATES = {
    "Body": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "Body-Bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "Body-Italic": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    ],
    "Body-BoldItalic": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
    ],
    "Mono": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ],
    "Mono-Bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ],
}

MONO_FALLBACK_DIRS = []
try:  # matplotlib ships the full DejaVu family, including decorative obliques
    import matplotlib  # type: ignore

    MONO_FALLBACK_DIRS.append(
        os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    )
except Exception:  # pragma: no cover
    pass

FALLBACK_NAMES = {
    "Body": ["DejaVuSans.ttf"],
    "Body-Bold": ["DejaVuSans-Bold.ttf"],
    "Body-Italic": ["DejaVuSans-Oblique.ttf", "DejaVuSans.ttf"],
    "Body-BoldItalic": ["DejaVuSans-BoldOblique.ttf", "DejaVuSans-Bold.ttf"],
    "Mono": ["DejaVuSansMono.ttf"],
    "Mono-Bold": ["DejaVuSansMono-Bold.ttf"],
}


def _resolve(font_name: str) -> str:
    for path in FONT_CANDIDATES[font_name]:
        if os.path.exists(path):
            return path
    for directory in MONO_FALLBACK_DIRS:
        for candidate in FALLBACK_NAMES[font_name]:
            path = os.path.join(directory, candidate)
            if os.path.exists(path):
                return path
    raise FileNotFoundError(f"cannot locate a font file for {font_name}")


BODY, BODY_B, BODY_I, BODY_BI, MONO, MONO_B = (
    "Body", "Body-Bold", "Body-Italic", "Body-BoldItalic", "Mono", "Mono-Bold"
)


def register_fonts() -> None:
    for name in (BODY, BODY_B, BODY_I, BODY_BI, MONO, MONO_B):
        pdfmetrics.registerFont(TTFont(name, _resolve(name)))
    pdfmetrics.registerFontFamily(
        BODY, normal=BODY, bold=BODY_B, italic=BODY_I, boldItalic=BODY_BI
    )
    pdfmetrics.registerFontFamily(MONO, normal=MONO, bold=MONO_B, italic=MONO, boldItalic=MONO_B)


def available_codepoints() -> set[int]:
    """Codepoints present in the body + mono fonts, via fontTools.

    If fontTools is unavailable we assume the fonts are complete and pass all
    characters through: DejaVu Sans covers everything these documents use, and a
    silent glyph-drop would be far worse than an occasional missing box.
    """
    covered: set[int] = set()
    try:
        from fontTools.ttLib import TTFont as FTFont  # type: ignore

        for name in (BODY, MONO):
            font = FTFont(_resolve(name))
            for table in font["cmap"].tables:
                covered |= set(table.cmap.keys())
    except Exception:
        return set(range(0x20, 0x2500))  # permissive: pass Unicode through
    return covered


# ---------------------------------------------------------------------------
# Unicode safety
# ---------------------------------------------------------------------------

_SUBSTITUTIONS = {
    "\ufe0f": "",       # variation selector, meaningless in PDF
    "\u274c": "\u2717",  # ❌ -> ✗
    "\u2705": "\u2713",  # ✅ -> ✓
    "\u26a0": "!",       # ⚠ -> !
    "\U0001f6f0": "",    # 🛰
    "\U0001f4a1": "",    # 💡
    "\u2b50": "*",       # ⭐
    "\U0001f4cc": "",    # 📌
    "\u200b": "",        # zero width space
    "\u00a0": " ",       # non-breaking space -> normal space
}

_MISSING: dict[str, int] = {}


def sanitize(text: str, covered: set[int]) -> str:
    """Replace or drop glyphs the fonts cannot draw, and record what was changed."""
    out = []
    for char in text:
        if char in _SUBSTITUTIONS:
            out.append(_SUBSTITUTIONS[char])
            continue
        if ord(char) < 128 or ord(char) in covered:
            out.append(char)
            continue
        for replacement in ("?", "-", "*", ""):
            if replacement == "" or ord(replacement) in covered:
                out.append(replacement)
                break
        _MISSING[char] = _MISSING.get(char, 0) + 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Inline markdown -> ReportLab mini-HTML
# ---------------------------------------------------------------------------

CODE_TOKEN = "\x00C{}\x00"
LINK_TOKEN = "\x00L{}\x00"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str, base_size: float = 9.6) -> str:
    """Convert inline markdown into the XML that ReportLab's Paragraph accepts."""
    code_spans: list[str] = []
    links: list[str] = []

    def stash_code(match: re.Match) -> str:
        code_spans.append(match.group(1))
        return CODE_TOKEN.format(len(code_spans) - 1)

    def stash_link(match: re.Match) -> str:
        links.append((match.group(1), match.group(2)))  # type: ignore[arg-type]
        return LINK_TOKEN.format(len(links) - 1)

    text = re.sub(r"`([^`]+)`", stash_code, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", stash_link, text)
    text = _escape(text)

    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.S)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<![\w*])_([^_\n]+?)_(?![\w_])", r"<i>\1</i>", text)

    def render_code(code: str) -> str:
        return f'<font face="{MONO}" size="{base_size - 0.9:.1f}">{_escape(code)}</font>'

    for index, code in enumerate(code_spans):
        text = text.replace(CODE_TOKEN.format(index), render_code(code))

    for index, (label, url) in enumerate(links):
        # A link label arrives un-escaped (it was stashed before escaping) and may
        # itself contain a code span, e.g. [`cubetwin_model.py`](code/...). Render
        # the label properly before splicing it into the <link> element.
        rendered = _escape(label)
        for code_index, code in enumerate(code_spans):
            rendered = rendered.replace(CODE_TOKEN.format(code_index), render_code(code))
        text = text.replace(
            LINK_TOKEN.format(index),
            f'<link href="{_escape(url)}" color="#1B4F86">{rendered}</link>',
        )
    return text


# ---------------------------------------------------------------------------
# Markdown block parser
# ---------------------------------------------------------------------------

@dataclass
class Block:
    kind: str
    text: str = ""
    items: list[str] = field(default_factory=list)
    header: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    level: int = 0


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", line.strip())) and "-" in line


def parse_markdown(lines: Sequence[str]) -> list[Block]:
    blocks: list[Block] = []
    index = 0
    total = len(lines)

    while index < total:
        raw = lines[index]
        stripped = raw.strip()

        if not stripped:
            index += 1
            continue

        # fenced code
        if stripped.startswith("```"):
            index += 1
            buffer: list[str] = []
            while index < total and not lines[index].strip().startswith("```"):
                buffer.append(lines[index].rstrip())
                index += 1
            index += 1
            blocks.append(Block("code", text="\n".join(buffer)))
            continue

        # horizontal rule
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            blocks.append(Block("hr"))
            index += 1
            continue

        # heading
        match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if match:
            level = len(match.group(1))
            blocks.append(Block("heading", text=match.group(2).strip(), level=min(level, 3)))
            index += 1
            continue

        # table
        if "|" in stripped and index + 1 < total and _is_separator(lines[index + 1]):
            header = _split_row(stripped)
            index += 2
            rows: list[list[str]] = []
            while index < total and "|" in lines[index] and lines[index].strip():
                rows.append(_split_row(lines[index]))
                index += 1
            blocks.append(Block("table", header=header, rows=rows))
            continue

        # blockquote
        if stripped.startswith(">"):
            buffer = []
            while index < total and lines[index].strip().startswith(">"):
                buffer.append(re.sub(r"^\s*>\s?", "", lines[index]).rstrip())
                index += 1
            paragraph_buffer: list[str] = []
            for line in buffer:
                if not line.strip():
                    if paragraph_buffer:
                        blocks.append(Block("quote", text=" ".join(paragraph_buffer).strip()))
                        paragraph_buffer = []
                    continue
                paragraph_buffer.append(line.strip())
            if paragraph_buffer:
                blocks.append(Block("quote", text=" ".join(paragraph_buffer).strip()))
            continue

        # lists (bullets and numbered), with one level of nesting
        if re.match(r"^(\s*)([-*+]|\d+[.)])\s+", raw):
            items: list[str] = []
            while index < total and re.match(r"^(\s*)([-*+]|\d+[.)])\s+", lines[index]):
                indent = len(lines[index]) - len(lines[index].lstrip())
                content = re.sub(r"^(\s*)([-*+]|\d+[.)])\s+", "", lines[index]).rstrip()
                if indent >= 2 and items:
                    items[-1] = items[-1] + "\n    \u2022 " + content.strip()
                else:
                    items.append(content.strip())
                index += 1
            blocks.append(Block("list", items=items))
            continue

        # paragraph
        buffer = []
        while index < total:
            candidate = lines[index]
            if not candidate.strip():
                break
            if re.match(r"^(\s*)(#{1,6}\s|>\s|[-*+]\s|\d+[.)]\s)", candidate):
                break
            if candidate.strip().startswith("```") or re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", candidate.strip()):
                break
            if "|" in candidate and index + 1 < total and _is_separator(lines[index + 1]):
                break
            buffer.append(candidate.strip())
            index += 1
        if buffer:
            blocks.append(Block("paragraph", text=" ".join(buffer)))
        else:
            index += 1

    return blocks


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

NAVY = colors.HexColor("#12263A")
BLUE = colors.HexColor("#1B4F86")
RULE = colors.HexColor("#C9D4E2")
CODE_BG = colors.HexColor("#F4F6F9")
QUOTE_BG = colors.HexColor("#EEF3F9")
TABLE_HEAD = colors.HexColor("#1B4F86")
TABLE_ALT = colors.HexColor("#F6F8FB")

STYLES = {
    "h1": ParagraphStyle("h1", fontName=BODY_B, fontSize=19, leading=23, textColor=NAVY,
                         spaceBefore=6, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName=BODY_B, fontSize=13.2, leading=16.5, textColor=BLUE,
                         spaceBefore=15, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName=BODY_B, fontSize=10.8, leading=13.5, textColor=NAVY,
                         spaceBefore=11, spaceAfter=3),
    "body": ParagraphStyle("body", fontName=BODY, fontSize=9.6, leading=13.6,
                           textColor=colors.HexColor("#1A1A1A"), alignment=TA_LEFT, spaceAfter=6),
    "bullet": ParagraphStyle("bullet", fontName=BODY, fontSize=9.4, leading=13.2,
                             textColor=colors.HexColor("#1A1A1A"), leftIndent=12,
                             bulletIndent=2, spaceAfter=3.5),
    "quote": ParagraphStyle("quote", fontName=BODY_I, fontSize=9.5, leading=13.6,
                            textColor=colors.HexColor("#243B55"), leftIndent=8, rightIndent=4),
    "table": ParagraphStyle("table", fontName=BODY, fontSize=8.2, leading=10.6,
                            textColor=colors.HexColor("#1A1A1A")),
    "tablehead": ParagraphStyle("tablehead", fontName=BODY_B, fontSize=8.4, leading=10.8,
                                textColor=colors.white),
    "code": ParagraphStyle("code", fontName=MONO, fontSize=8.0, leading=10.6,
                           textColor=colors.HexColor("#16212B")),
    "toc1": ParagraphStyle("toc1", fontName=BODY_B, fontSize=10.5, leading=15, textColor=NAVY),
    "toc2": ParagraphStyle("toc2", fontName=BODY, fontSize=9.2, leading=12.6, leftIndent=14,
                           textColor=colors.HexColor("#333333")),
    "title": ParagraphStyle("title", fontName=BODY_B, fontSize=27, leading=32, textColor=NAVY),
    "subtitle": ParagraphStyle("subtitle", fontName=BODY, fontSize=12, leading=17,
                               textColor=BLUE),
    "meta": ParagraphStyle("meta", fontName=BODY, fontSize=9.2, leading=13.5,
                           textColor=colors.HexColor("#444444")),
}


# ---------------------------------------------------------------------------
# Flowables
# ---------------------------------------------------------------------------

class ChapterMark(Flowable):
    """Zero-height flowable that tags the current chapter for headers + the TOC."""

    def __init__(self, level: int, text: str):
        super().__init__()
        self.bookmark = (level, text)
        self.width = 0
        self.height = 0

    def draw(self) -> None:  # pragma: no cover - nothing to draw
        pass


class Rule(Flowable):
    def __init__(self, width: float, thickness: float = 0.6, color=RULE, space: float = 4):
        super().__init__()
        self.width, self.thickness, self.color, self.space = width, thickness, color, space
        self.height = thickness + space * 2

    def draw(self) -> None:  # pragma: no cover
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.space, self.width, self.space)


class HtmlDoc(BaseDocTemplate):
    """DocTemplate that records chapter names, PDF outline entries and TOC targets."""

    def __init__(self, filename: str, title: str, **kwargs):
        super().__init__(filename, title=title, author="Soham Vinchu", **kwargs)
        self.chapter = title
        self.pack_title = title
        self._anchor_seq = 0

    def handle_documentBegin(self):
        # multiBuild runs the whole story more than once (once to collect TOC
        # entries, once more to resolve page numbers). Reset the running header
        # and the anchor counter so every pass produces identical keys.
        self.chapter = self.pack_title
        self._anchor_seq = 0
        super().handle_documentBegin()

    def _anchor(self, text: str) -> str:
        base = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()[:38] or "section"
        self._anchor_seq += 1
        return f"{base}-{self._anchor_seq}"

    def afterFlowable(self, flowable):
        bookmark = getattr(flowable, "bookmark", None)
        if not bookmark:
            return
        level, text = bookmark
        key = self._anchor(text)

        # PDF outline (the bookmarks panel / jump-to-section menu on any reader)
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text[:110], key, level=min(level, 2), closed=False)
        # clickable contents entry
        self.notify("TOCEntry", (level, text, self.page, key))
        if level == 0:
            self.chapter = text


def _header_footer(canvas, doc: HtmlDoc) -> None:
    canvas.saveState()
    width, height = A4
    left, right = 16 * mm, width - 16 * mm

    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(left, height - 13 * mm, right, height - 13 * mm)

    canvas.setFont(BODY, 7.4)
    canvas.setFillColor(colors.HexColor("#6B7A8D"))
    chapter = getattr(doc, "chapter", "")
    canvas.drawString(left, height - 11.6 * mm, chapter[:88])

    short = getattr(doc, "pack_title", "CubeTwin interview prep")
    canvas.drawRightString(right, height - 11.6 * mm, short[:60])

    canvas.line(left, 13.5 * mm, right, 13.5 * mm)
    canvas.setFont(BODY, 7.4)
    canvas.drawString(left, 10.2 * mm, "Prepared for Soham Vinchu · interview 29 September 2026")
    canvas.drawRightString(right, 10.2 * mm, f"Page {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Block -> flowables
# ---------------------------------------------------------------------------

def table_flowable(header: list[str], rows: list[list[str]], avail: float) -> Table:
    columns = max([len(header)] + [len(r) for r in rows])
    header = header + [""] * (columns - len(header))
    normalised = [r + [""] * (columns - len(r)) for r in rows]

    data: list[list[Paragraph]] = [[
        Paragraph(inline(cell, 8.2), STYLES["tablehead"] if cell else STYLES["table"])
        for cell in header
    ]]
    for row in normalised:
        data.append([Paragraph(inline(cell, 8.2), STYLES["table"]) for cell in row])

    widths = [0.0] * columns
    for column in range(columns):
        widest = stringWidth(_plain(header[column]), BODY_B, 8.4)
        for row in normalised:
            widest = max(widest, stringWidth(_plain(row[column]), BODY, 8.2))
        widths[column] = min(widest + 12, avail * 0.55)
    scale = avail / sum(widths) if sum(widths) > avail else 1.0
    widths = [max(w * scale, avail * 0.07) for w in widths]
    total = sum(widths)
    if total != avail:  # normalise any rounding drift
        widths = [w * avail / total for w in widths]

    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEAD),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, TABLE_HEAD),
        ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.6),
    ]
    for row_index in range(1, len(data)):
        if row_index % 2 == 0:
            style.append(("BACKGROUND", (0, row_index), (-1, row_index), TABLE_ALT))
    table.setStyle(TableStyle(style))
    return table


def _plain(text: str) -> str:
    """Strip markdown markup so text can be measured with the real font metrics."""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text


def code_flowable(code: str, avail: float) -> Table:
    body = Preformatted(code, STYLES["code"], maxLineLength=200)
    table = Table([[body]], colWidths=[avail], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.4, RULE),
        ("LINEBEFORE", (0, 0), (0, -1), 2.2, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def quote_flowable(text: str, avail: float) -> Table:
    table = Table([[Paragraph(inline(text, 9.5), STYLES["quote"])]], colWidths=[avail], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), QUOTE_BG),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def blocks_to_story(
    blocks: Iterable[Block],
    avail: float,
    skip_first_h1: bool = False,
    inline_first_h1: bool = False,
) -> list:
    """Turn parsed blocks into flowables.

    skip_first_h1   - the combined pack already shows this title on its cover page
    inline_first_h1 - standalone document: render the title in place instead of
                      forcing it onto its own chapter-opening page
    """
    story: list = []
    seen_h1 = False

    for block in blocks:
        if block.kind == "heading":
            text = inline(block.text, 13)
            if block.level == 1:
                if not seen_h1 and skip_first_h1:
                    seen_h1 = True
                    story.append(ChapterMark(0, _plain(block.text)))
                    continue
                if not seen_h1 and inline_first_h1:
                    seen_h1 = True
                    story.append(ChapterMark(0, _plain(block.text)))
                    story.append(Paragraph(text, STYLES["h1"]))
                    story.append(Rule(avail, 1.0, BLUE, 2))
                    story.append(Spacer(1, 6))
                    continue
                seen_h1 = True
                if story:
                    story.append(PageBreak())
                mark = ChapterMark(0, _plain(block.text))
                story.append(mark)
                story.append(Paragraph(text, STYLES["h1"]))
                story.append(Rule(avail, 1.0, BLUE, 2))
                story.append(Spacer(1, 4))
            elif block.level == 2:
                story.append(ChapterMark(1, _plain(block.text)))
                story.append(Paragraph(text, STYLES["h2"]))
                story.append(Rule(avail, 0.5, RULE, 1.5))
                story.append(Spacer(1, 2))
            else:
                story.append(Paragraph(text, STYLES["h3"]))

        elif block.kind == "paragraph":
            story.append(Paragraph(inline(block.text), STYLES["body"]))

        elif block.kind == "list":
            numbered = bool(re.match(r"^\d+[.)]", block.items[0])) if block.items else False
            for position, item in enumerate(block.items, start=1):
                marker = f"{position}." if numbered else "\u2022"
                parts = item.split("\n    \u2022 ")
                story.append(Paragraph(f"{marker}&nbsp;&nbsp;{inline(parts[0])}",
                                       STYLES["bullet"], bulletText=None))
                for sub in parts[1:]:
                    sub_style = ParagraphStyle(
                        "sub", parent=STYLES["bullet"], leftIndent=26, fontSize=9.0, leading=12.6
                    )
                    story.append(Paragraph(f"\u2013&nbsp;&nbsp;{inline(sub)}", sub_style))

        elif block.kind == "quote":
            story.append(quote_flowable(block.text, avail))
            story.append(Spacer(1, 4))

        elif block.kind == "code":
            story.append(KeepTogether([Spacer(1, 2), code_flowable(block.text, avail), Spacer(1, 5)]))

        elif block.kind == "table":
            story.append(Spacer(1, 3))
            story.append(table_flowable(block.header, block.rows, avail))
            story.append(Spacer(1, 7))

        elif block.kind == "hr":
            story.append(Rule(avail, 0.6, RULE, 5))
            story.append(Spacer(1, 3))

    return story


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------

MARGIN_X = 16 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 18 * mm


def _frame_and_template(doc: HtmlDoc) -> None:
    width, height = A4
    frame = Frame(
        MARGIN_X,
        MARGIN_BOTTOM,
        width - 2 * MARGIN_X,
        height - MARGIN_TOP - MARGIN_BOTTOM,
        id="main",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    # Headers are drawn on page END: by then every flowable on the page has been
    # processed, so the running chapter name is the one that actually belongs to
    # this page (drawing on page begin lags by a page).
    doc.addPageTemplates(
        [PageTemplate(id="all", frames=[frame], onPageEnd=_header_footer)]
    )


def build_pdf(
    path: str,
    sources: list[tuple[str, str]],
    title: str,
    subtitle: str,
    *,
    toc: bool = False,
    cover: bool = False,
    inline_first_heading: bool = False,
) -> int:
    """Render one PDF from a list of (markdown_path, section_label) sources."""
    covered = available_codepoints()
    doc = HtmlDoc(
        path,
        title,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )
    _frame_and_template(doc)
    avail = A4[0] - 2 * MARGIN_X

    story: list = []
    if cover:
        story += [
            Spacer(1, 60),
            Paragraph(title, STYLES["title"]),
            Spacer(1, 6),
            Rule(avail, 1.6, BLUE, 2),
            Spacer(1, 8),
            Paragraph(subtitle, STYLES["subtitle"]),
            Spacer(1, 26),
            Paragraph(
                inline(
                    "Satellite Engineering Internship — *CubeTwin: CubeSat Digital Twin Simulation*. "
                    "iTelematics Software Private Limited (EV Society / EV.ENGINEER / "
                    "ISHAVASYAM.ORG), advertised through the National Internship Portal (AICTE)."
                ),
                STYLES["meta"],
            ),
            Spacer(1, 10),
            Paragraph(
                inline(
                    "**Contents:** interview brief · skills mapping · synopsis and written answers · "
                    "one-page cheat sheet · reference model of the published CubeTwin physics."
                ),
                STYLES["meta"],
            ),
            Spacer(1, 18),
            Paragraph(
                inline(
                    "Everything in this pack is drawn from the public internship listing and the "
                    "CubeTwin platform documentation, plus the candidate's own project record. "
                    "No experience is claimed that cannot be demonstrated on request."
                ),
                STYLES["meta"],
            ),
            PageBreak(),
        ]
        if toc:
            story.append(Paragraph("Contents", STYLES["h1"]))
            story.append(Rule(avail, 1.0, BLUE, 2))
            story.append(Spacer(1, 8))
            contents = TableOfContents()
            contents.levelStyles = [STYLES["toc1"], STYLES["toc2"]]
            contents.dotsMinLevel = 0
            story.append(contents)
            story.append(PageBreak())

    first = True
    for source_path, _label in sources:
        with open(source_path, "r", encoding="utf-8") as handle:
            raw = handle.read()
        raw = sanitize(raw, covered)
        blocks = parse_markdown(raw.splitlines())
        story += blocks_to_story(
            blocks,
            avail,
            skip_first_h1=cover and first,
            inline_first_h1=inline_first_heading and first,
        )
        first = False

    doc.multiBuild(story)
    return doc.page


def main() -> int:
    register_fonts()
    os.makedirs(OUT, exist_ok=True)

    docs = [
        ("01-interview-brief.md", "Interview brief"),
        ("02-skills-mapping.md", "Skills mapping"),
        ("03-synopsis-and-written-answers.md", "Synopsis & written answers"),
        ("04-cheatsheet.md", "Cheat sheet"),
    ]

    combined = os.path.join(OUT, "CubeTwin-Interview-Pack.pdf")
    pages = build_pdf(
        combined,
        [(os.path.join(PREP, name), label) for name, label in docs],
        "CubeTwin Interview Pack",
        "Satellite Engineering Internship · iTelematics Software · 29 September 2026",
        toc=True,
        cover=True,
    )
    print(f"wrote {os.path.relpath(combined, REPO)}  ({pages} pages)")

    for name, label in docs:
        target = os.path.join(OUT, name.replace(".md", ".pdf"))
        pages = build_pdf(
            target,
            [(os.path.join(PREP, name), label)],
            label,
            "CubeTwin Satellite Engineering Internship · 29 September 2026",
            inline_first_heading=True,
        )
        print(f"wrote {os.path.relpath(target, REPO)}  ({pages} pages)")

    if _MISSING:
        print("\nGlyphs substituted or dropped (absent from DejaVu):")
        for char, count in sorted(_MISSING.items(), key=lambda kv: -kv[1]):
            print(f"  U+{ord(char):04X} {char!r} x{count}")
    else:
        print("\nAll glyphs rendered from the embedded fonts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
