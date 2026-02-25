#!/usr/bin/env python3
"""
HUAP Public Beta Manual — Developer Zine Edition
Generates a ~20-page styled PDF using PyMuPDF (fitz).

Usage:
    python docs/manual/generate_manual_pdf.py

Requires: PyMuPDF (pip install pymupdf)
"""

import os
import fitz  # PyMuPDF

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
DARK_NAVY = (0x1A / 255, 0x1A / 255, 0x2E / 255)
ACCENT_BLUE = (0x00 / 255, 0x77 / 255, 0xFF / 255)
CODE_BG = (0xF0 / 255, 0xF0 / 255, 0xF0 / 255)
CALLOUT_BG = (0xE8 / 255, 0xF0 / 255, 0xFE / 255)
BODY_COLOR = (0x22 / 255, 0x22 / 255, 0x22 / 255)
WHITE = (1, 1, 1)
LIGHT_GRAY = (0.6, 0.6, 0.6)
TABLE_HEADER_BG = (0x2C / 255, 0x2C / 255, 0x44 / 255)
TABLE_ROW_ALT = (0xF7 / 255, 0xF7 / 255, 0xFA / 255)

PAGE_W, PAGE_H = fitz.paper_size("letter")
MARGIN_X = 72
MARGIN_TOP = 72
MARGIN_BOTTOM = 60
CONTENT_W = PAGE_W - 2 * MARGIN_X


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class PDFWriter:
    """Stateful page-based PDF builder."""

    def __init__(self):
        self.doc = fitz.open()
        self.page = None
        self.y = MARGIN_TOP
        self.page_num = 0

    # -- page management ---------------------------------------------------
    def new_page(self):
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.page_num += 1
        self.y = MARGIN_TOP
        return self.page

    def ensure_space(self, needed):
        if self.y + needed > PAGE_H - MARGIN_BOTTOM:
            self._footer()
            self.new_page()

    def _footer(self):
        """Add page number footer."""
        if self.page is None:
            return
        txt = f"— {self.page_num} —"
        self.page.insert_text(
            fitz.Point(PAGE_W / 2 - 20, PAGE_H - 30),
            txt,
            fontsize=9,
            fontname="helv",
            color=LIGHT_GRAY,
        )

    # -- drawing primitives ------------------------------------------------
    def dark_banner(self, text, height=44):
        """Full-width dark navy banner with white text."""
        self.ensure_space(height + 20)
        rect = fitz.Rect(0, self.y, PAGE_W, self.y + height)
        self.page.draw_rect(rect, color=None, fill=DARK_NAVY)
        self.page.insert_text(
            fitz.Point(MARGIN_X, self.y + height - 14),
            text,
            fontsize=18,
            fontname="helv",
            color=WHITE,
        )
        self.y += height + 16

    def section_title(self, text):
        """Dark banner section title — starts new page."""
        self._footer()
        self.new_page()
        self.dark_banner(text)

    def heading2(self, text):
        """Sub-heading in dark navy."""
        self.ensure_space(30)
        self.page.insert_text(
            fitz.Point(MARGIN_X, self.y + 14),
            text,
            fontsize=14,
            fontname="helv",
            color=DARK_NAVY,
        )
        self.y += 26

    def heading3(self, text):
        """Smaller sub-heading."""
        self.ensure_space(24)
        self.page.insert_text(
            fitz.Point(MARGIN_X, self.y + 12),
            text,
            fontsize=11,
            fontname="helv",
            color=ACCENT_BLUE,
        )
        self.y += 22

    def body(self, text, indent=0, bold=False):
        """Body paragraph — wraps text automatically."""
        fn = "helv" if not bold else "helv"
        # PyMuPDF doesn't have helv bold built-in separately, we fake with fontname
        # Actually we can use "hebo" for Helvetica-Bold
        if bold:
            fn = "hebo"
        lines = self._wrap(text, fontsize=10, fontname=fn, max_w=CONTENT_W - indent)
        for line in lines:
            self.ensure_space(15)
            self.page.insert_text(
                fitz.Point(MARGIN_X + indent, self.y + 11),
                line,
                fontsize=10,
                fontname=fn,
                color=BODY_COLOR,
            )
            self.y += 15
        self.y += 4

    def body_small(self, text, indent=0, color=BODY_COLOR):
        """Smaller body text."""
        lines = self._wrap(text, fontsize=9, fontname="helv", max_w=CONTENT_W - indent)
        for line in lines:
            self.ensure_space(13)
            self.page.insert_text(
                fitz.Point(MARGIN_X + indent, self.y + 10),
                line,
                fontsize=9,
                fontname="helv",
                color=color,
            )
            self.y += 13

    def spacer(self, h=10):
        self.y += h

    def pull_quote(self, text):
        """Large italic-style quote with accent border."""
        self.ensure_space(50)
        # Draw left accent bar
        self.page.draw_rect(
            fitz.Rect(MARGIN_X, self.y, MARGIN_X + 4, self.y + 40),
            color=None,
            fill=ACCENT_BLUE,
        )
        lines = self._wrap(text, fontsize=12, fontname="helv", max_w=CONTENT_W - 20)
        ly = self.y
        for line in lines:
            self.page.insert_text(
                fitz.Point(MARGIN_X + 16, ly + 13),
                line,
                fontsize=12,
                fontname="helv",
                color=DARK_NAVY,
            )
            ly += 17
        self.y = ly + 12

    def callout_box(self, title, text):
        """Tinted blue callout box."""
        lines = self._wrap(text, fontsize=9, fontname="helv", max_w=CONTENT_W - 28)
        box_h = 28 + len(lines) * 14 + 8
        self.ensure_space(box_h + 8)
        rect = fitz.Rect(MARGIN_X, self.y, MARGIN_X + CONTENT_W, self.y + box_h)
        self.page.draw_rect(rect, color=None, fill=CALLOUT_BG)
        # Accent left bar
        self.page.draw_rect(
            fitz.Rect(MARGIN_X, self.y, MARGIN_X + 4, self.y + box_h),
            color=None,
            fill=ACCENT_BLUE,
        )
        self.page.insert_text(
            fitz.Point(MARGIN_X + 14, self.y + 16),
            title,
            fontsize=10,
            fontname="hebo",
            color=ACCENT_BLUE,
        )
        ly = self.y + 30
        for line in lines:
            self.page.insert_text(
                fitz.Point(MARGIN_X + 14, ly + 10),
                line,
                fontsize=9,
                fontname="helv",
                color=BODY_COLOR,
            )
            ly += 14
        self.y += box_h + 10

    def code_block(self, code):
        """Gray background monospace code block."""
        code_lines = code.strip().split("\n")
        line_h = 13
        box_h = len(code_lines) * line_h + 16
        self.ensure_space(box_h + 8)
        rect = fitz.Rect(MARGIN_X, self.y, MARGIN_X + CONTENT_W, self.y + box_h)
        self.page.draw_rect(rect, color=None, fill=CODE_BG)
        ly = self.y + 12
        for cl in code_lines:
            # Truncate long lines
            if len(cl) > 85:
                cl = cl[:82] + "..."
            self.page.insert_text(
                fitz.Point(MARGIN_X + 10, ly),
                cl,
                fontsize=8.5,
                fontname="cour",
                color=BODY_COLOR,
            )
            ly += line_h
        self.y += box_h + 8

    def table(self, headers, rows):
        """Simple styled table."""
        col_count = len(headers)
        col_w = CONTENT_W / col_count
        row_h = 22
        header_h = 24
        total_h = header_h + len(rows) * row_h + 4
        self.ensure_space(total_h)

        x0 = MARGIN_X
        # Header row
        hr = fitz.Rect(x0, self.y, x0 + CONTENT_W, self.y + header_h)
        self.page.draw_rect(hr, color=None, fill=TABLE_HEADER_BG)
        for i, h in enumerate(headers):
            self.page.insert_text(
                fitz.Point(x0 + i * col_w + 6, self.y + 16),
                h,
                fontsize=9,
                fontname="hebo",
                color=WHITE,
            )
        self.y += header_h

        # Data rows
        for ri, row in enumerate(rows):
            if ri % 2 == 1:
                rr = fitz.Rect(x0, self.y, x0 + CONTENT_W, self.y + row_h)
                self.page.draw_rect(rr, color=None, fill=TABLE_ROW_ALT)
            for i, cell in enumerate(row):
                # Truncate to fit column
                max_chars = int(col_w / 4.5)
                display = cell if len(cell) <= max_chars else cell[: max_chars - 3] + "..."
                self.page.insert_text(
                    fitz.Point(x0 + i * col_w + 6, self.y + 15),
                    display,
                    fontsize=8.5,
                    fontname="helv",
                    color=BODY_COLOR,
                )
            self.y += row_h
        self.y += 8

    def bullet(self, text, indent=0):
        """Bullet point."""
        self.ensure_space(16)
        self.page.insert_text(
            fitz.Point(MARGIN_X + indent, self.y + 11),
            "•",
            fontsize=10,
            fontname="helv",
            color=ACCENT_BLUE,
        )
        lines = self._wrap(text, fontsize=10, fontname="helv", max_w=CONTENT_W - indent - 16)
        first = True
        for line in lines:
            self.ensure_space(15)
            self.page.insert_text(
                fitz.Point(MARGIN_X + indent + 14, self.y + 11),
                line,
                fontsize=10,
                fontname="helv",
                color=BODY_COLOR,
            )
            self.y += 15
            first = False
        if first:
            self.y += 15
        self.y += 2

    def checklist(self, text, indent=10):
        """Checkbox item."""
        self.ensure_space(16)
        self.page.draw_rect(
            fitz.Rect(MARGIN_X + indent, self.y + 2, MARGIN_X + indent + 10, self.y + 12),
            color=LIGHT_GRAY,
            fill=WHITE,
            width=0.8,
        )
        lines = self._wrap(text, fontsize=9, fontname="helv", max_w=CONTENT_W - indent - 18)
        for line in lines:
            self.page.insert_text(
                fitz.Point(MARGIN_X + indent + 16, self.y + 11),
                line,
                fontsize=9,
                fontname="helv",
                color=BODY_COLOR,
            )
            self.y += 14
        self.y += 2

    # -- text wrapping -----------------------------------------------------
    def _wrap(self, text, fontsize, fontname, max_w):
        """Word-wrap text to fit within max_w pixels."""
        words = text.split()
        lines = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            tw = fitz.get_text_length(test, fontsize=fontsize, fontname=fontname)
            if tw > max_w and current:
                lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)
        return lines or [""]

    # -- finalize ----------------------------------------------------------
    def save(self, path):
        # Add footer to last page
        self._footer()
        self.doc.save(path)
        self.doc.close()
        print(f"Saved: {path} ({self.page_num} pages)")


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------
def build_manual():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    logo_path = os.path.join(repo_root, "HUAP-logo.png")
    output_path = os.path.join(script_dir, "HUAP_Public_Beta_Manual.pdf")

    w = PDFWriter()

    # ===================================================================
    # PAGE 1 — COVER
    # ===================================================================
    page = w.new_page()
    # Full dark background
    page.draw_rect(fitz.Rect(0, 0, PAGE_W, PAGE_H), color=None, fill=DARK_NAVY)

    # Logo
    if os.path.exists(logo_path):
        logo_w, logo_h = 200, 200
        lx = (PAGE_W - logo_w) / 2
        ly = 100
        page.insert_image(fitz.Rect(lx, ly, lx + logo_w, ly + logo_h), filename=logo_path)
    else:
        print(f"Warning: logo not found at {logo_path}")

    # Title
    page.insert_text(
        fitz.Point(PAGE_W / 2 - 160, 360),
        "HUAP",
        fontsize=60,
        fontname="hebo",
        color=WHITE,
    )
    page.insert_text(
        fitz.Point(PAGE_W / 2 - 160, 400),
        "Public Beta Manual",
        fontsize=24,
        fontname="helv",
        color=WHITE,
    )
    # Subtitle
    page.insert_text(
        fitz.Point(PAGE_W / 2 - 160, 440),
        "Ship agents like software:",
        fontsize=14,
        fontname="helv",
        color=ACCENT_BLUE,
    )
    page.insert_text(
        fitz.Point(PAGE_W / 2 - 160, 458),
        "traceable, testable, governable.",
        fontsize=14,
        fontname="helv",
        color=ACCENT_BLUE,
    )

    # pip install box
    box_x = PAGE_W / 2 - 120
    box_rect = fitz.Rect(box_x, 500, box_x + 240, 540)
    page.draw_rect(box_rect, color=ACCENT_BLUE, fill=(0.08, 0.08, 0.16), width=1.5)
    page.insert_text(
        fitz.Point(box_x + 30, 526),
        "pip install huap-core",
        fontsize=14,
        fontname="cour",
        color=ACCENT_BLUE,
    )

    # Version & date
    page.insert_text(
        fitz.Point(PAGE_W / 2 - 100, 590),
        "Version: Public Beta (pre-1.0)",
        fontsize=10,
        fontname="helv",
        color=LIGHT_GRAY,
    )
    page.insert_text(
        fitz.Point(PAGE_W / 2 - 60, 608),
        "February 2026",
        fontsize=10,
        fontname="helv",
        color=LIGHT_GRAY,
    )

    # Footer on cover
    page.insert_text(
        fitz.Point(PAGE_W / 2 - 90, PAGE_H - 50),
        "github.com/Mircus/HUAP",
        fontsize=9,
        fontname="helv",
        color=LIGHT_GRAY,
    )

    # ===================================================================
    # PAGE 2 — WHY THIS EXISTS
    # ===================================================================
    w.section_title("Why this exists")

    w.pull_quote(
        '"Most agent frameworks demo well and fail badly '
        'once you try to operate them."'
    )
    w.spacer(6)

    w.body(
        "They look impressive on a laptop because nobody is asking "
        "the two questions that matter:"
    )
    w.spacer(4)

    w.body("1. Can you reproduce the run that failed?", bold=True)
    w.body("2. Can you stop the agent before it does something dumb?", bold=True)
    w.spacer(8)

    w.body(
        "HUAP exists because agentic systems are software systems with "
        "uncertainty inside them — models, tools, changing state, memory, "
        "actions. You don't manage uncertainty by ignoring it. You manage it "
        "by making runs observable, changes reviewable, and risky actions "
        "controllable."
    )
    w.spacer(8)

    w.callout_box(
        "The bottom line",
        "If you build with HUAP, you're not buying 'more agent magic.' "
        "You're buying operational sanity."
    )

    # ===================================================================
    # PAGE 3 — WHO THIS IS FOR + WHAT HUAP IS / ISN'T
    # ===================================================================
    w.section_title("Who this is for")

    w.heading2("Primary readers")
    w.bullet("Tech Leads / Founders — you want agents in production and you want to sleep at night.")
    w.bullet("Engineering Managers — you need a workflow that doesn't depend on hero debugging.")
    w.bullet("AI Engineers — you already use LangChain/CrewAI/etc. You want trace + CI + review on top.")
    w.bullet("R&D teams — you want reproducible multi-step workflows with artifacts you can share.")

    w.spacer(10)
    w.heading2("If this is you, HUAP is not necessary (yet)")
    w.bullet("You only do one-shot prompts.")
    w.bullet("You don't ship to users.")
    w.bullet("You don't care if outputs drift over time.")

    w.spacer(16)
    w.dark_banner("What HUAP is (and isn't)")

    w.heading3("HUAP is")
    w.bullet("A runtime harness for agent workflows (your code runs inside it).")
    w.bullet("A flight recorder — every action becomes a trace.jsonl event + human-readable trace.html.")
    w.bullet("A CI runner — compare current run against a known-good baseline, produce diff.html.")
    w.bullet("A governance layer — human gates pause the agent and wait for approval.")
    w.bullet("A memory port with a local SQLite backend (Hindsight) — searchable, auditable.")

    w.spacer(8)
    w.heading3("HUAP is not")
    w.bullet("A replacement for LangChain / CrewAI / LangGraph / AutoGen.")
    w.bullet("A prompt playground.")
    w.bullet("A full enterprise platform (that's the post-beta roadmap).")

    w.spacer(8)
    w.callout_box(
        "Think of it this way",
        "HUAP is the layer that turns 'agent demos' into 'agent systems.'"
    )

    # ===================================================================
    # PAGES 4-5 — THE PROBLEM
    # ===================================================================
    w.section_title("The problem HUAP solves")

    w.body(
        "Classic software is deterministic enough to test. "
        "Agents are workflows with uncertainty baked in. "
        "Here's where that uncertainty comes from:"
    )
    w.spacer(6)

    w.table(
        ["Source of uncertainty", "What happens"],
        [
            ["Model calls", "Non-deterministic — same prompt, different output"],
            ["Tool calls", "External systems change state, fail, rate-limit"],
            ["Changing state", "The world evolves between runs"],
            ["Memory", "Context grows, drifts, accumulates noise"],
            ["Actions", "Real-world consequences — emails, files, money"],
        ],
    )

    w.spacer(8)
    w.pull_quote(
        '"It worked yesterday. Today it failed. Same prompt. Same code. '
        'Different outcome." That sentence is poison.'
    )

    w.spacer(8)
    w.heading2("HUAP's answer: treat runs like flights")
    w.body(
        "Aviation solved this decades ago. Every flight has a black box, "
        "a replay procedure, checklists, and crew approval for risky maneuvers. "
        "HUAP brings the same discipline to agent runs."
    )
    w.spacer(6)

    w.table(
        ["Aviation", "HUAP"],
        [
            ["Flight recorder", "Trace (trace.jsonl)"],
            ["Replay & investigate", "Replay (huap trace replay)"],
            ["Compare to known-good", "Baseline + Diff (huap trace diff)"],
            ["Crew approval for risky maneuvers", "Human Gates (huap inbox)"],
            ["Maintenance logs", "Memory (Hindsight — auditable)"],
        ],
    )

    w.spacer(6)
    w.callout_box("No philosophy.", "Just engineering.")

    # ===================================================================
    # PAGES 6-7 — WHAT YOU GET
    # ===================================================================
    w.section_title("What you get (artifacts)")

    w.body(
        "When you run a workflow under HUAP, you get artifacts you can review, share, and CI-gate. "
        "Here's the full picture:"
    )
    w.spacer(6)

    w.table(
        ["Artifact", "What it is", "Who reads it"],
        [
            ["trace.jsonl", "Event timeline (machine-readable)", "CI, replay, diff tool"],
            ["trace.html", "Standalone HTML report", "Engineers, managers, auditors"],
            ["diff.html", "Visual diff vs baseline", "PR reviewers, triage"],
            ["memo.md", "Agent-produced summary", "Anyone — shareable artifact"],
            ["Suites + baselines", "Regression tests for agents", "CI pipeline"],
            ["Gates", "Agents propose; humans dispose", "Gatekeepers, compliance"],
            ["Memory DB", "Local searchable store", "Agents (cross-session recall)"],
        ],
    )

    w.spacer(10)
    w.callout_box(
        "Key takeaway",
        "Every HUAP run produces a reviewable paper trail. "
        "Traces aren't logs — they're structured, replayable timelines "
        "that turn 'CI failed' into 'CI explained why.'"
    )

    # ===================================================================
    # PAGES 8-10 — THE 10-MINUTE WOW PATH
    # ===================================================================
    w.section_title("The 10-Minute WOW Path")

    w.body(
        "This proves the whole stack in under ten minutes: multi-node workflow, "
        "trace, gates, memory, and drift detection. Copy-paste your way through."
    )

    w.spacer(8)
    w.heading2("Step 1: Install")
    w.code_block("pip install huap-core")

    w.heading2("Step 2: Run the flagship demo")
    w.code_block("huap flagship")
    w.body(
        "This runs a 5-node pipeline (research -> analyze -> human gate -> synthesize -> memorize) "
        "in stub mode — no API keys needed."
    )
    w.spacer(4)
    w.body("Expected outputs in huap_flagship_demo/:", bold=True)
    w.table(
        ["File", "Contents"],
        [
            ["trace.jsonl", "Full event timeline"],
            ["trace.html", "Standalone HTML report (opens in browser)"],
            ["memo.md", "Agent-produced research memo"],
        ],
    )

    w.heading2("Step 3: Prove Agent CI")
    w.code_block(
        "huap ci run suites/flagship/suite.yaml \\\n"
        "  --html reports/flagship.html"
    )
    w.body(
        "This replays the flagship workflow, diffs against a committed baseline, "
        "and produces an HTML report. Match = PASS. Drift = FAIL with a visual diff."
    )

    w.heading2("Step 4: Prove drift detection")
    w.code_block(
        "huap flagship --drift\n"
        "huap ci run suites/flagship/suite.yaml \\\n"
        "  --html reports/flagship_drift.html"
    )
    w.body(
        "The --drift flag injects a controlled change. "
        "The CI runner catches it and shows exactly what changed."
    )

    w.heading2("Step 5: Prove memory persists")
    w.code_block(
        "huap flagship --with-memory\n"
        "huap flagship --with-memory\n"
        'huap memory search "memo" --k 5'
    )
    w.body(
        "First run stores findings in SQLite. Second run retrieves them. "
        "The search command queries the memory store directly."
    )

    w.spacer(6)
    w.callout_box(
        "What 'DRIFT' means",
        "Drift is any meaningful change between the current run and the baseline. "
        "Some drift is good (you improved behavior). Some drift is bad (you broke something). "
        "HUAP makes drift visible so you decide intentionally."
    )

    # ===================================================================
    # PAGES 11-12 — MENTAL MODEL
    # ===================================================================
    w.section_title("Mental model (two pictures)")

    w.heading2("The runtime loop")
    w.body("Here's what happens when your agent runs inside HUAP:")
    w.spacer(4)
    w.code_block(
        "┌───────────────────────────────┐\n"
        "│   Your Agent                  │   (LangChain / CrewAI / custom)\n"
        "└──────────────┬────────────────┘\n"
        "               │\n"
        "               ▼\n"
        "┌──────────────────────────────────────────────────────┐\n"
        "│  HUAP Runtime                                        │\n"
        "│                                                      │\n"
        "│  · runs workflow graph (nodes + edges)               │\n"
        "│  · calls tools via sandbox (safe batteries)          │\n"
        "│  · records every event to trace.jsonl                │\n"
        "│  · applies human gates (pause → inbox → decide)      │\n"
        "│  · reads/writes memory via MemoryPort                │\n"
        "│  · routes model calls via Specialist Squad           │\n"
        "└──────────────┬───────────────────────────────────────┘\n"
        "               │\n"
        "               ▼\n"
        "    Artifacts: trace.jsonl · trace.html · memo.md · diff.html"
    )

    w.spacer(10)
    w.heading2("The CI loop")
    w.code_block(
        "  Baseline (known good)          Current run (PR / main)\n"
        "          │                              │\n"
        "          └──────────┬───────────────────┘\n"
        "                     ▼\n"
        "              huap ci run\n"
        "                     ▼\n"
        "     PASS   or   DRIFT DETECTED (+ diff.html)\n"
        "                     ▼\n"
        "         fix  /  accept  /  refresh baseline"
    )

    w.spacer(8)
    w.callout_box(
        "The whole loop in one line",
        "Trace -> Baseline -> CI Diff. That's it. Everything else is detail."
    )

    # ===================================================================
    # PAGES 13-14 — ADOPTION PATHS
    # ===================================================================
    w.section_title("Adoption paths (pick one)")

    w.heading2("Path A — Wrap existing agents (fastest)")
    w.body(
        "Keep LangChain/CrewAI/etc. HUAP adds trace + CI + gates on top. "
        "One callback handler is all it takes."
    )
    w.code_block(
        "# LangChain — one callback handler\n"
        "from hu_core.adapters.langchain import HuapCallbackHandler\n"
        "\n"
        'handler = HuapCallbackHandler(out="traces/langchain.jsonl")\n'
        'chain.invoke({"input": "hello"}, config={"callbacks": [handler]})\n'
        "handler.flush()"
    )
    w.code_block(
        "# Or wrap any script\n"
        "huap trace wrap --out traces/agent.jsonl -- python my_agent.py"
    )
    w.spacer(4)
    w.heading3("Path A checklist")
    w.checklist("Wrap your run entrypoint")
    w.checklist("Route risky tools through safe wrappers or gates")
    w.checklist("Baseline one 'good' run")
    w.checklist("Run a smoke suite in CI")

    w.spacer(10)
    w.heading2("Path B — HUAP-native graphs (cleanest)")
    w.body(
        "Define workflows as YAML graphs. Full tracing, replay, and CI built in."
    )
    w.code_block(
        "nodes:\n"
        "  - name: research\n"
        "    run: my_pod.nodes.research\n"
        "  - name: analyze\n"
        "    run: my_pod.nodes.analyze\n"
        "edges:\n"
        "  - from: research\n"
        "    to: analyze\n"
        "  - from: analyze\n"
        "    to: null"
    )
    w.heading3("Path B checklist")
    w.checklist("Define nodes / edges / conditions")
    w.checklist("Baseline 'good' behavior")
    w.checklist("Gate risky nodes")
    w.checklist("Add memory only for curated knowledge")

    w.spacer(10)
    w.heading2("Path C — Mixed migration (realistic)")
    w.body(
        "Wrap now; migrate critical workflows to native graphs later. "
        "This is the path most teams actually take."
    )
    w.heading3("Path C checklist")
    w.checklist("Wrap existing agent for trace coverage today")
    w.checklist("Migrate the critical workflow into a HUAP suite")
    w.checklist("Gates early, memory last")

    # ===================================================================
    # PAGE 15 — OPERATING MODEL
    # ===================================================================
    w.section_title("Operating model")

    w.body(
        "HUAP gives you tools. But tools without roles and policies just create "
        "a different kind of chaos. Here's how teams stay sane."
    )
    w.spacer(6)

    w.heading2("Roles")
    w.table(
        ["Role", "Responsibility"],
        [
            ["Workflow owner", "Defines expected behavior + suite"],
            ["Baseline owner", "Approves baseline refreshes"],
            ["Gatekeeper", "Approves risky actions via inbox"],
            ["CI maintainer", "Keeps suites stable + fast"],
        ],
    )

    w.spacer(8)
    w.heading2("Baseline refresh policy")
    w.body("Refresh baselines only when:")
    w.bullet("The diff has been reviewed.")
    w.bullet("The change is intentional.")
    w.bullet("Someone owns the outcome.")

    w.spacer(4)
    w.callout_box(
        "Golden rule",
        "Never refresh baselines just to 'make CI green.' "
        "That defeats the entire purpose."
    )

    w.spacer(8)
    w.heading2("Drift triage workflow")
    w.body("When CI flags drift, follow this three-step process:")
    w.bullet("Open diff.html.")
    w.bullet("Identify the source: prompt change? tool change? model update? memory drift? nondeterminism?")
    w.bullet("Decide: fix / accept / refresh baseline intentionally.")

    # ===================================================================
    # PAGE 16 — MEMORY GUIDE
    # ===================================================================
    w.section_title("Memory guide (Hindsight)")

    w.body(
        "HUAP ships with Hindsight, a local SQLite memory backend. "
        "It's searchable, auditable, and redacted by default. "
        "Here's how to use it without shooting yourself in the foot."
    )

    w.spacer(6)
    w.heading2("What to store (good)")
    w.table(
        ["Category", "Example"],
        [
            ["Decisions + rationale", "Chose vendor X because of rate limits on Y"],
            ["Short stable summaries", "User prefers JSON output format"],
            ["Tool/API constraints", "API v2 has a 100 req/min limit"],
            ["Known failure modes", "Model hallucinates dates before 2020"],
        ],
    )

    w.spacer(6)
    w.heading2("What NOT to store (bad)")
    w.table(
        ["Category", "Why"],
        [
            ["Raw secrets / tokens", "Don't rely on redaction — just don't store them"],
            ["Full payload dumps", "Bloats memory, adds noise"],
            ["Unfiltered transcripts", "Low signal-to-noise ratio"],
        ],
    )

    w.spacer(6)
    w.heading2("Commands")
    w.code_block(
        "# Check what's in memory\n"
        "huap memory stats\n"
        "\n"
        "# Ingest trace events into memory\n"
        "huap memory ingest --from-trace traces/flagship.jsonl\n"
        "\n"
        "# Search by keyword\n"
        'huap memory search "rate limit" --k 5\n'
        "\n"
        "# Reset memory (delete local store)\n"
        "rm -rf .huap/"
    )

    w.spacer(6)
    w.callout_box(
        "Secret redaction",
        "HUAP automatically strips API keys, tokens, and credentials before storing "
        "anything in memory. This happens at the persistence layer — you can't "
        "accidentally store sk-abc123... in the database."
    )

    # ===================================================================
    # PAGE 17 — CI COOKBOOK
    # ===================================================================
    w.section_title("CI cookbook")

    w.body(
        "Here's a copy-paste rollout plan for getting Agent CI into your pipeline. "
        "Start small, prove value, expand."
    )

    w.spacer(6)
    w.heading2("Rollout cadence")
    w.table(
        ["Week", "Action"],
        [
            ["Week 1", "Smoke suite in CI (proves the pipeline works)"],
            ["Week 2", "Baseline one critical workflow"],
            ["Week 3", "Gate the riskiest action"],
            ["Week 4", "Add memory (carefully, for curated knowledge only)"],
        ],
    )

    w.spacer(8)
    w.heading2("GitHub Actions example")
    w.code_block(
        "- name: Agent CI - smoke suite\n"
        "  run: |\n"
        "    export HUAP_LLM_MODE=stub\n"
        "    huap ci run suites/smoke/suite.yaml \\\n"
        "      --html reports/smoke.html\n"
        "\n"
        "- name: Agent CI - flagship suite\n"
        "  run: |\n"
        "    export HUAP_LLM_MODE=stub\n"
        "    huap ci run suites/flagship/suite.yaml \\\n"
        "      --html reports/flagship.html\n"
        "\n"
        "- name: Upload artifacts\n"
        "  if: always()\n"
        "  uses: actions/upload-artifact@v4\n"
        "  with:\n"
        "    name: huap-reports\n"
        "    path: reports/*.html\n"
        "    retention-days: 14"
    )

    w.spacer(6)
    w.callout_box(
        "Always upload artifacts",
        "trace.html shows what happened. diff.html shows what changed. "
        "reports/*.html gives CI summary with pass/fail. "
        "Artifacts turn 'CI failed' into 'CI explained why.'"
    )

    # ===================================================================
    # PAGE 18 — SECURITY + ROLLOUT PLAN
    # ===================================================================
    w.section_title("Security + Rollout plan")

    w.heading2("Tool risk tiers")
    w.table(
        ["Tier", "Examples", "Default policy"],
        [
            ["Low", "Read allowed local files", "Allow"],
            ["Medium", "Safe HTTP GET to allowlist", "Allow + log"],
            ["High", "File writes, external API writes", "Gate + log"],
            ["Critical", "Money transfers, irreversible", "Gate + 2-person rule"],
        ],
    )

    w.spacer(6)
    w.heading2("Safe batteries included")
    w.body("HUAP ships two safe-by-default tools:")
    w.bullet("http_fetch_safe — HTTP GET with domain allowlist, timeout, size cap, content-type filter.")
    w.bullet("fs_sandbox — File I/O confined to a root directory — no path traversal.")

    w.spacer(6)
    w.heading2("Memory safety")
    w.bullet("Memory is sanitized on ingest via redact_secrets().")
    w.bullet("API keys, tokens, and credentials are automatically stripped.")
    w.bullet("Allowlist what becomes memory — don't dump everything.")

    w.spacer(12)
    w.dark_banner("Rollout plan")

    w.heading3("First 2 weeks")
    w.checklist("Install HUAP (pip install huap-core)")
    w.checklist("Wrap your agent (or run the flagship demo)")
    w.checklist("Record traces — get comfortable reading trace.html")
    w.checklist("Add 1 smoke suite to CI")
    w.checklist("Add 1 gate for the riskiest action")

    w.spacer(6)
    w.heading3("First 30 days")
    w.checklist("Add a critical workflow suite with a committed baseline")
    w.checklist("Establish baseline ownership (who reviews, who approves)")
    w.checklist("Upload trace.html and diff.html as CI artifacts")
    w.checklist("Use memory only for curated summaries (not raw dumps)")

    w.spacer(6)
    w.heading3("First 90 days")
    w.checklist("Multiple suites (fast smoke vs slow integration)")
    w.checklist("Structured policies for tool access tiers")
    w.checklist("Optional: external memory backend")
    w.checklist("Optional: team approval workflows")

    # ===================================================================
    # PAGE 19 — FAQ
    # ===================================================================
    w.section_title("FAQ")

    faqs = [
        (
            '"Is this just logging?"',
            "No. Logging gives you text lines. HUAP gives you structured event timelines, "
            "baselines, visual diffs, CI gating, human approvals, and auditable memory — all in one pipeline."
        ),
        (
            '"What about nondeterminism?"',
            "Use stub mode in CI (HUAP_LLM_MODE=stub) for fully deterministic replay. "
            "For live runs: pin model providers, ignore noise fields in diffs, stabilize memory retrieval. "
            "HUAP's diff engine highlights meaningful changes, not random noise."
        ),
        (
            '"Do I have to rewrite my agents?"',
            "No. Start with wrappers (Path A). The LangChain adapter is one callback handler. "
            "Or wrap any script with 'huap trace wrap'."
        ),
        (
            '"How big do traces get?"',
            "Traces record what you need to debug — node entries/exits, tool calls, LLM requests/responses, "
            "gate decisions, memory ops. Avoid dumping full web pages into state. "
            "Store large blobs separately and reference them by path."
        ),
        (
            '"Can I replace Hindsight?"',
            "Yes — that's the design. The MemoryProvider interface is a plugin boundary. "
            "Hindsight (SQLite) ships as the default. Future backends plug in without "
            "changing your workflow code."
        ),
        (
            '"What if I need real LLM calls in CI?"',
            "Set HUAP_LLM_MODE=live and provide OPENAI_API_KEY. But for regression testing, "
            "stub mode is recommended — it's free, fast, and fully deterministic."
        ),
        (
            '"Is HUAP production-ready?"',
            "This is a public beta. The core pipeline (trace, replay, diff, CI, gates, memory) is solid "
            "and tested (96+ tests, CI on Python 3.10-3.12). The interfaces are stable. "
            "Coming soon: more adapters, vector memory, web UI for gates."
        ),
    ]

    for q, a in faqs:
        w.heading3(q)
        w.body(a)
        w.spacer(4)

    # ===================================================================
    # PAGE 20 — COMMAND REFERENCE + FOOTER
    # ===================================================================
    w.section_title("Command reference")

    cmd_groups = [
        ("Core", [
            "huap --help                    # Show all commands",
            "huap --version                 # Show version",
            "huap init <name>               # Create a runnable workspace",
            "huap flagship                  # Full demo (opens browser)",
            "huap flagship --drift          # Demo with injected drift",
            "huap flagship --with-memory    # Demo with persistent memory",
            "huap demo                      # Simple hello graph demo",
        ]),
        ("Tracing", [
            "huap trace run <pod> <graph>   # Run and record trace",
            "huap trace view <file>         # View trace events",
            "huap trace replay <file>       # Replay with stubs",
            "huap trace diff <a> <b>        # Compare two traces",
            "huap trace wrap -- <cmd>       # Wrap any command",
            "huap trace report <file>       # Generate HTML report",
            "huap trace validate <file>     # Validate trace schema",
        ]),
        ("Agent CI", [
            "huap ci init                   # Create CI config",
            "huap ci run <suite>            # Run suite, diff vs golden",
            "huap ci run <suite> --html ... # Same, with HTML report",
            "huap ci check <suite>          # Full CI check",
            "huap ci status                 # Show last CI run status",
        ]),
        ("Human Gates / Inbox", [
            "huap inbox list                # List pending gates",
            "huap inbox show <id>           # Show gate details",
            "huap inbox approve <id>        # Approve a gate",
            "huap inbox reject <id>         # Reject a gate",
            "huap inbox edit <id>           # Edit params and approve",
        ]),
        ("Memory", [
            "huap memory stats              # Show database statistics",
            "huap memory search <query>     # Keyword search",
            "huap memory ingest --from-trace <file>  # Ingest trace",
        ]),
        ("Model Router & Plugins", [
            "huap models init               # Create models.yaml",
            "huap models list               # List registered models",
            "huap models explain            # Explain routing",
            "huap plugins init              # Create plugins.yaml",
            "huap plugins list              # List plugins",
        ]),
    ]

    for group_name, cmds in cmd_groups:
        w.heading3(group_name)
        w.code_block("\n".join(cmds))
        w.spacer(2)

    # Final footer
    w.spacer(20)
    w.ensure_space(60)
    # Centered footer bar
    rect = fitz.Rect(0, w.y, PAGE_W, w.y + 50)
    w.page.draw_rect(rect, color=None, fill=DARK_NAVY)
    w.page.insert_text(
        fitz.Point(MARGIN_X, w.y + 20),
        "HUAP Core v0.1.0b1",
        fontsize=10,
        fontname="hebo",
        color=WHITE,
    )
    w.page.insert_text(
        fitz.Point(MARGIN_X, w.y + 36),
        "pip install huap-core  |  github.com/Mircus/HUAP  |  pypi.org/project/huap-core",
        fontsize=9,
        fontname="helv",
        color=LIGHT_GRAY,
    )

    # Save
    w.save(output_path)


if __name__ == "__main__":
    build_manual()
