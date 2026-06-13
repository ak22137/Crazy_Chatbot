"""
Generate visual architecture & flow diagrams for Excel Intelligence Backend.
Produces 8 high-quality PNG files in ./diagrams/

Run:
    python generate_diagrams.py

Requirements: matplotlib, networkx (both in requirements or venv)
"""

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")           # headless, no display needed
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import networkx as nx

OUT = Path("./diagrams")
OUT.mkdir(exist_ok=True)

# ── palette ────────────────────────────────────────────────────────────────────
P = {
    "blue0": "#E3F2FD", "blue1": "#90CAF9", "blue2": "#1565C0",
    "green0": "#E8F5E9", "green1": "#81C784", "green2": "#1B5E20",
    "red0":  "#FFEBEE", "red1":  "#EF9A9A", "red2":  "#B71C1C",
    "amber0":"#FFF8E1", "amber1":"#FFD54F", "amber2":"#E65100",
    "purple0":"#F3E5F5","purple1":"#CE93D8","purple2":"#4A148C",
    "teal0": "#E0F2F1", "teal1": "#80CBC4", "teal2": "#004D40",
    "gray0": "#FAFAFA", "gray1": "#BDBDBD", "gray2": "#212121",
    "white": "#FFFFFF",
}

# ── helpers ─────────────────────────────────────────────────────────────────────

def box(ax, x, y, w, h, fc, ec="#212121", lw=1.5, radius=0.3, alpha=1.0,
        text="", fontsize=9, bold=False, style="normal", ha="center",
        va="center", color="#212121"):
    patch = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=f"round,pad={radius*0.1}",
        facecolor=fc, edgecolor=ec, linewidth=lw, alpha=alpha, zorder=3
    )
    ax.add_patch(patch)
    if text:
        ax.text(x, y, text, fontsize=fontsize, ha=ha, va=va,
                fontweight="bold" if bold else "normal",
                style=style, color=color, zorder=4,
                wrap=True)

def arrow(ax, x1, y1, x2, y2, color="#555555", lw=1.5, style="->",
          label="", label_fc="white"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, lw=lw, color=color,
                                connectionstyle="arc3,rad=0.05"),
                zorder=5)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my, label, fontsize=7, ha="center", va="center",
                color=color, zorder=6,
                bbox=dict(fc=label_fc, ec="none", boxstyle="round,pad=0.15"))

def title(ax, text, y=0.97, fontsize=16):
    ax.text(0.5, y, text, transform=ax.transAxes,
            fontsize=fontsize, fontweight="bold", ha="center", va="top",
            color=P["gray2"])

def save(fig, name):
    fig.savefig(OUT / name, dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  ✅  {name}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. SYSTEM ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
def diagram_system_architecture():
    fig, ax = plt.subplots(figsize=(18, 11), facecolor=P["gray0"])
    ax.set_xlim(0, 18); ax.set_ylim(0, 11); ax.axis("off")
    title(ax, "Excel Intelligence — System Architecture")

    # ── layer bands ──
    bands = [
        (0.2, 1.6, P["blue0"],   "🖥️  CLIENT LAYER"),
        (1.9, 3.2, P["teal0"],   "🌐  API LAYER  (FastAPI · Port 8001)"),
        (3.4, 5.8, P["purple0"], "⚙️  PROCESSING LAYER"),
        (5.8, 7.8, P["amber0"],  "💾  STORAGE LAYER"),
        (8.0, 9.4, P["red0"],    "🔗  EXTERNAL SERVICES"),
    ]
    for y0, y1, fc, lbl in bands:
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.3, y0), 17.4, y1-y0,
            boxstyle="round,pad=0.1", facecolor=fc, edgecolor=P["gray1"],
            linewidth=1, alpha=0.4, zorder=1))
        ax.text(0.55, (y0+y1)/2, lbl, fontsize=9, va="center",
                color=P["gray2"], alpha=0.6, rotation=0)

    # ── CLIENT ──
    box(ax, 9,  1.1, 3, 0.8, P["blue1"], ec=P["blue2"], lw=2,
        text="🖥️  Next.js Frontend  (Port 3000)", fontsize=10, bold=True)

    # ── API routers ──
    for i, (lbl, x) in enumerate([("Upload\nRouter", 4.5),
                                    ("Chat\nRouter",   9),
                                    ("Metadata\nRouter",13.5)]):
        box(ax, x, 2.55, 3.2, 0.9, P["teal1"], ec=P["teal2"], lw=2,
            text=f"/{lbl.split()[0].lower()}\n{lbl}", fontsize=9, bold=True)

    # ── PROCESSING ──
    proc = [
        (3,   4.6, "🎯 Orchestrator\n(Intent Classification)"),
        (7.5, 5.0, "🔧 SQL Agent\n(Query Generation)"),
        (12,  4.6, "📚 Metadata Agent\n(Schema Q&A)"),
        (16,  4.6, "📥 Ingestion\nPipeline"),
    ]
    for x, y, lbl in proc:
        box(ax, x, y, 3.4, 1.2, P["purple1"], ec=P["purple2"], lw=2,
            text=lbl, fontsize=9, bold=True)

    # ── STORAGE ──
    store = [
        (4,   6.8, "🗄️  DuckDB\nanalytics.duckdb"),
        (9,   6.8, "📦 Parquet Files\n./storage/parquet/"),
        (14,  6.8, "📂 Raw Uploads\n./storage/raw_files/"),
    ]
    for x, y, lbl in store:
        box(ax, x, y, 3.4, 1.2, P["amber1"], ec=P["amber2"], lw=2,
            text=lbl, fontsize=9, bold=True)

    # ── EXTERNAL ──
    ext = [
        (4,   8.7, "🤖 Siemens LLM API\n(OpenAI-compatible)"),
        (9,   8.7, "🔍 SQLGlot\n(SQL Validator)"),
        (14,  8.7, "🐍 PyArrow\n(Parquet R/W)"),
    ]
    for x, y, lbl in ext:
        box(ax, x, y, 3.4, 1.0, P["red1"], ec=P["red2"], lw=2,
            text=lbl, fontsize=9, bold=True)

    # ── arrows ──
    # frontend → routers
    for x in [4.5, 9, 13.5]:
        arrow(ax, 9, 1.5, x, 2.1, color=P["blue2"], lw=1.5)
    # upload router → ingestion
    arrow(ax, 4.5, 3.0, 16, 4.0, color=P["teal2"], lw=1.5)
    # chat router → orchestrator
    arrow(ax, 9, 3.0, 3, 4.0, color=P["teal2"], lw=2)
    # metadata router → metadata agent
    arrow(ax, 13.5, 3.0, 12, 4.0, color=P["teal2"], lw=1.5)
    # orchestrator → sql agent
    arrow(ax, 4.5, 4.6, 7.5, 4.6, color=P["purple2"], lw=1.5)
    # orchestrator → metadata agent
    arrow(ax, 4.5, 4.6, 10.5, 4.6, color=P["purple2"], lw=1.5, style="->")
    # sql agent → duckdb
    arrow(ax, 7.5, 5.6, 5, 6.2, color=P["amber2"], lw=2)
    # ingestion → parquet
    arrow(ax, 16, 5.2, 9, 6.2, color=P["amber2"], lw=1.5)
    # ingestion → duckdb
    arrow(ax, 16, 5.2, 4, 6.2, color=P["amber2"], lw=1.5)
    # sql agent → llm
    arrow(ax, 7.5, 5.6, 4, 8.2, color=P["red2"], lw=2, label="LLM call")
    # sql agent → sqlglot
    arrow(ax, 7.5, 5.6, 9, 8.2, color=P["red2"], lw=1.5)
    # parquet → pyarrow
    arrow(ax, 9, 7.4, 14, 8.2, color=P["red2"], lw=1.5)

    plt.tight_layout()
    save(fig, "01_system_architecture.png")


# ══════════════════════════════════════════════════════════════════════════════
# 2. END-TO-END CHAT FLOW
# ══════════════════════════════════════════════════════════════════════════════
def diagram_chat_flow():
    fig, ax = plt.subplots(figsize=(16, 20), facecolor=P["gray0"])
    ax.set_xlim(0, 10); ax.set_ylim(0, 22); ax.axis("off")
    title(ax, "End-to-End Chat Request Flow", y=0.985, fontsize=15)

    # steps: (y_centre, label, description, face_color, edge_color)
    steps = [
        (21.0, "👤 USER",        "Sends question via browser",
         P["blue1"],   P["blue2"]),
        (19.5, "📩 POST /api/v1/chat",
                                 "FastAPI chat endpoint receives JSON {question}",
         P["teal1"],  P["teal2"]),
        (18.0, "🎯 CLASSIFY INTENT",
                                 "Orchestrator asks LLM: SQL_ANALYTICS / METADATA / GREETING?",
         P["purple1"], P["purple2"]),
        (16.3, "📋 SELECT TABLES",
                                 "Similarity rank all metadata → keep top 3–5 relevant tables",
         P["purple1"], P["purple2"]),
        (14.6, "🔍 BUILD SCHEMA CONTEXT",
                                 "Columns + types + distinct categorical values fed to LLM",
         P["purple1"], P["purple2"]),
        (12.9, "🤖 GENERATE SQL  (LLM call #2)",
                                 "SQL_GENERATION prompt → LLM returns {sql, explanation}",
         P["red1"],   P["red2"]),
        (11.2, "✅ PARSE & VALIDATE SQL",
                                 "Multi-strategy JSON parse → sqlglot syntax check",
         P["amber1"],  P["amber2"]),
        (9.5,  "⚡ EXECUTE on DuckDB",
                                 "SELECT query on read connection · max 200 rows returned",
         P["amber1"],  P["amber2"]),
        (7.8,  "📝 FORMAT RESPONSE  (LLM call #3)",
                                 "RESPONSE_FORMAT prompt → natural language + markdown table",
         P["red1"],   P["red2"]),
        (6.1,  "📤 ChatResponse JSON",
                                 "{intent, answer, sql_result, processing_time_ms}",
         P["teal1"],  P["teal2"]),
        (4.4,  "🖥️ FRONTEND RENDER",
                                 "MessageBubble: markdown table visible if answer has | rows |",
         P["blue1"],  P["blue2"]),
        (2.7,  "👁️ USER SEES RESULT",
                                 "Status breakdown table + total summary line",
         P["green1"],  P["green2"]),
    ]

    for y, hdr, desc, fc, ec in steps:
        box(ax, 5, y,      9.2, 1.0, fc, ec=ec, lw=2)
        ax.text(5, y+0.2, hdr,  fontsize=11, ha="center", va="center",
                fontweight="bold", color=P["gray2"], zorder=5)
        ax.text(5, y-0.2, desc, fontsize=8,  ha="center", va="center",
                style="italic",  color=P["gray2"], zorder=5)

    # arrows between steps
    ys = [s[0] for s in steps]
    for i in range(len(ys)-1):
        arrow(ax, 5, ys[i]-0.5, 5, ys[i+1]+0.5, color=P["gray2"], lw=2)

    # Repair loop annotation
    box(ax, 8.4, 10.35, 2.4, 0.9, P["red0"], ec=P["red2"], lw=1.5, alpha=0.9,
        text="⚠️ Repair Loop\nup to 3 retries", fontsize=8, bold=True)
    arrow(ax, 6.5, 11.2, 7.2, 10.8, color=P["red2"], lw=1.5)
    arrow(ax, 7.2, 9.9,  6.5, 9.5,  color=P["red2"], lw=1.5)

    # Time annotation
    ax.text(0.4, 1.5, "⏱  Typical latency:\n~5–8 s end-to-end",
            fontsize=9, color=P["gray2"], style="italic",
            bbox=dict(fc=P["green0"], ec=P["green2"], boxstyle="round,pad=0.3"))

    plt.tight_layout()
    save(fig, "02_chat_flow.png")


# ══════════════════════════════════════════════════════════════════════════════
# 3. SQL AGENT DETAIL
# ══════════════════════════════════════════════════════════════════════════════
def diagram_sql_agent():
    fig, ax = plt.subplots(figsize=(18, 14), facecolor=P["gray0"])
    ax.set_xlim(0, 18); ax.set_ylim(0, 14); ax.axis("off")
    title(ax, "SQL Agent — Internal Pipeline", fontsize=15)

    # Column layout: 3 columns
    col = [3.2, 9, 14.8]

    # ── Column 1: Schema gathering ──
    ax.text(col[0], 13.2, "① Schema Gathering",
            fontsize=11, fontweight="bold", ha="center", color=P["purple2"])

    items_c1 = [
        (12.3, "get_all_metadata()",    P["purple1"], P["purple2"]),
        (11.0, "→ _metadata_tables",    P["purple0"], P["purple2"]),
        (10.1, "→ _metadata_columns",   P["purple0"], P["purple2"]),
        (9.2,  "→ _relationships",      P["purple0"], P["purple2"]),
        (8.0,  "_select_tables()\ncosine similarity rank",
                                         P["purple1"], P["purple2"]),
        (6.8,  "Top 3–5 tables chosen", P["purple0"], P["purple2"]),
        (5.6,  "_build_schema_context()\n+ distinct values for\ncategorical cols",
                                         P["purple1"], P["purple2"]),
    ]
    for y, lbl, fc, ec in items_c1:
        box(ax, col[0], y, 5.5, 0.75, fc, ec=ec, lw=1.5, text=lbl, fontsize=9)

    for i in range(len(items_c1)-1):
        arrow(ax, col[0], items_c1[i][0]-0.38,
                  col[0], items_c1[i+1][0]+0.38, color=P["purple2"])

    # ── Column 2: LLM Interaction ──
    ax.text(col[1], 13.2, "② LLM SQL Generation",
            fontsize=11, fontweight="bold", ha="center", color=P["red2"])

    items_c2 = [
        (12.3, "SQL_GENERATION prompt\n(schema + semantics rules)",
                P["red1"], P["red2"]),
        (10.8, "🤖 LLM call\ngpt-oss-120b",
                P["red0"], P["red2"]),
        (9.3,  "parse_json_response()\n5-level fallback parser",
                P["amber1"], P["amber2"]),
        (7.8,  "sql_validator.py\nvia sqlglot",
                P["amber1"], P["amber2"]),
        (6.3,  "SQL valid?",
                P["amber0"], P["amber2"]),
        (4.8,  "_repair_sql()\n+ retry (max 3×)",
                P["red1"], P["red2"]),
    ]
    for y, lbl, fc, ec in items_c2:
        box(ax, col[1], y, 5.5, 0.85, fc, ec=ec, lw=1.5, text=lbl, fontsize=9)

    for i in range(len(items_c2)-1):
        arrow(ax, col[1], items_c2[i][0]-0.43,
                  col[1], items_c2[i+1][0]+0.43, color=P["red2"])

    # repair back-loop
    arrow(ax, col[1]+2.2, 6.3, col[1]+2.2, 4.4, color=P["red2"], lw=1.2)
    arrow(ax, col[1]+2.2, 4.4, col[1]+2.8, 4.4, color=P["red2"], lw=1.2)

    # ── Column 3: Execution & Response ──
    ax.text(col[2], 13.2, "③ Execution & Formatting",
            fontsize=11, fontweight="bold", ha="center", color=P["teal2"])

    items_c3 = [
        (12.3, "DuckDB\nread connection",       P["teal1"], P["teal2"]),
        (11.0, "Execute SELECT\nmax 200 rows",  P["teal0"], P["teal2"]),
        (9.7,  "Collect columns + rows",        P["teal0"], P["teal2"]),
        (8.4,  "RESPONSE_FORMAT prompt\nto LLM", P["red1"],  P["red2"]),
        (7.1,  "Multi-row? → markdown table\nSingle? → text sentence",
                P["green1"], P["green2"]),
        (5.8,  "SQLResult{}\n{sql, rows, columns\nsuccess, row_count}",
                P["teal1"],  P["teal2"]),
    ]
    for y, lbl, fc, ec in items_c3:
        box(ax, col[2], y, 5.5, 0.85, fc, ec=ec, lw=1.5, text=lbl, fontsize=9)

    for i in range(len(items_c3)-1):
        arrow(ax, col[2], items_c3[i][0]-0.43,
                  col[2], items_c3[i+1][0]+0.43, color=P["teal2"])

    # ── Cross-column arrows ──
    # schema context → LLM prompt
    arrow(ax, col[0]+2.75, 5.6, col[1]-2.75, 12.3, color=P["gray1"], lw=2,
          label="schema context")
    # valid SQL → execution
    arrow(ax, col[1]+2.75, 6.3, col[2]-2.75, 12.3, color=P["gray1"], lw=2,
          label="valid SQL")

    # ── Semantic rules callout ──
    rules_text = (
        "📌 Status Semantics Rules:\n"
        "  OPEN:    Published · On Hold\n"
        "           Consultation · Hiring Demand\n"
        "  TERMINAL: Filled · Filled & Hired\n"
        "             Cancelled/Withdrawn"
    )
    ax.text(0.3, 2.8, rules_text,
            fontsize=8, va="top", color=P["gray2"], family="monospace",
            bbox=dict(fc=P["green0"], ec=P["green2"],
                      boxstyle="round,pad=0.4", lw=1.5))

    plt.tight_layout()
    save(fig, "03_sql_agent_detail.png")


# ══════════════════════════════════════════════════════════════════════════════
# 4. DATA INGESTION PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
def diagram_ingestion():
    fig, ax = plt.subplots(figsize=(16, 10), facecolor=P["gray0"])
    ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.axis("off")
    title(ax, "Data Ingestion Pipeline — File Upload → DuckDB", fontsize=14)

    stages = [
        (1.2, 8.0, 2.0, 1.4, P["blue1"],   P["blue2"],
         "📁 File Upload\n(.xlsx / .xls / .csv)"),
        (4.0, 8.0, 2.0, 1.4, P["teal1"],   P["teal2"],
         "📄 excel_parser.py\nRead Sheets\nClean Columns"),
        (7.0, 8.0, 2.0, 1.4, P["purple1"], P["purple2"],
         "🔍 schema_detector.py\nInfer Types\nDetect PKs / Cats"),
        (10.0, 8.0, 2.0, 1.4, P["amber1"],  P["amber2"],
         "📊 metadata_builder.py\nStore in Catalog\n_metadata_*"),
        (13.2, 8.0, 2.0, 1.4, P["red1"],    P["red2"],
         "🔗 relationship_detector\nFK Heuristics\nConfidence Score"),

        (4.0, 5.0, 2.0, 1.4, P["teal0"],   P["teal2"],
         "💾 pipeline.py\nWrite Parquet\n./storage/parquet/"),
        (10.0, 5.0, 2.0, 1.4, P["amber0"],  P["amber2"],
         "🗄️ DuckDB\nRegister Tables\nanalytics.duckdb"),
        (7.0, 5.0, 2.0, 1.4, P["purple0"], P["purple2"],
         "📖 semantic_dictionary\nSynonyms / Aliases\nColumn Mapping"),

        (7.0, 2.0, 3.5, 1.4, P["green1"],  P["green2"],
         "✅ Data Ready\nMetadata Catalog Populated\nQueries Enabled"),
    ]

    for x, y, w, h, fc, ec, lbl in stages:
        box(ax, x, y, w*1.5, h, fc, ec=ec, lw=2, text=lbl, fontsize=9)

    # arrows - top row
    for x1, x2 in [(1.2, 4.0), (4.0, 7.0), (7.0, 10.0), (10.0, 13.2)]:
        arrow(ax, x1+1.5, 8.0, x2-1.5, 8.0, color=P["gray2"], lw=2)

    # down arrows
    arrow(ax, 4.0,  7.3, 4.0,  5.7,  color=P["teal2"],   lw=2)
    arrow(ax, 10.0, 7.3, 10.0, 5.7,  color=P["amber2"],  lw=2)
    arrow(ax, 7.0,  7.3, 7.0,  5.7,  color=P["purple2"], lw=2)

    # to ready
    for x in [4.0, 10.0, 7.0]:
        arrow(ax, x, 4.3, 7.0, 2.7, color=P["green2"], lw=1.5)

    # ── ColumnSchema detail box ──
    detail = (
        "ColumnSchema:\n"
        " name, data_type\n"
        " nullable, is_primary_key\n"
        " is_categorical\n"
        " distinct_count, null_count\n"
        " sample_values[]"
    )
    ax.text(0.3, 4.5, detail, fontsize=8, va="top", family="monospace",
            color=P["gray2"],
            bbox=dict(fc=P["purple0"], ec=P["purple2"],
                      boxstyle="round,pad=0.4", lw=1.2))

    plt.tight_layout()
    save(fig, "04_ingestion_pipeline.png")


# ══════════════════════════════════════════════════════════════════════════════
# 5. DATABASE SCHEMA (ER)
# ══════════════════════════════════════════════════════════════════════════════
def diagram_database_schema():
    fig, ax = plt.subplots(figsize=(18, 12), facecolor=P["gray0"])
    ax.set_xlim(0, 18); ax.set_ylim(0, 12); ax.axis("off")
    title(ax, "Database Schema — DuckDB Catalog & Data Tables", fontsize=14)

    def er_table(ax, x, y, name, cols, fc, ec, w=4.0):
        h_header = 0.6
        h_row = 0.42
        total_h = h_header + len(cols)*h_row
        # header
        box(ax, x, y - h_header/2, w, h_header, fc, ec=ec, lw=2.5,
            text=f"▣  {name}", fontsize=10, bold=True)
        # rows
        for i, (col, dtype, note) in enumerate(cols):
            row_y = y - h_header - i*h_row - h_row/2
            row_fc = P["white"] if i % 2 == 0 else P["gray0"]
            box(ax, x, row_y, w, h_row, row_fc, ec=P["gray1"], lw=0.5, radius=0.05)
            ax.text(x - w/2 + 0.15, row_y, f"{col}", fontsize=8,
                    va="center", family="monospace", color=P["blue2"] if "PK" in note else P["gray2"])
            ax.text(x + w/2 - 0.1, row_y, f"{dtype}", fontsize=7,
                    va="center", ha="right", color=P["gray1"])
            if note:
                ax.text(x - w/2 + 0.15, row_y + 0.15, note, fontsize=6,
                        va="top", color=P["red2"])
        return y - h_header - len(cols)*h_row   # bottom y

    # _metadata_tables
    er_table(ax, 3.5, 11.5, "_metadata_tables",
             [("table_name",   "TEXT",    "PK"),
              ("upload_id",    "TEXT",    "FK→uploads"),
              ("sheet_name",   "TEXT",    ""),
              ("description",  "TEXT",    ""),
              ("row_count",    "INTEGER", ""),
              ("column_count", "INTEGER", ""),
              ("created_at",   "TIMESTAMP","")],
             P["blue0"], P["blue2"])

    # _metadata_columns
    er_table(ax, 9.5, 11.5, "_metadata_columns",
             [("table_name",    "TEXT",    "FK→_metadata_tables"),
              ("column_name",   "TEXT",    "PK composite"),
              ("data_type",     "TEXT",    "string/int/float/date…"),
              ("nullable",      "BOOLEAN", ""),
              ("is_primary_key","BOOLEAN", ""),
              ("description",   "TEXT",    ""),
              ("sample_values", "JSON",    "up to 5 values"),
              ("distinct_count","INTEGER", ""),
              ("null_count",    "INTEGER", "")],
             P["purple0"], P["purple2"])

    # _relationships
    er_table(ax, 15.2, 11.5, "_relationships",
             [("source_table",     "TEXT",  "FK"),
              ("source_column",    "TEXT",  ""),
              ("target_table",     "TEXT",  "FK"),
              ("target_column",    "TEXT",  ""),
              ("relationship_type","TEXT",  "foreign_key / match"),
              ("confidence",       "FLOAT", "0.0–1.0"),
              ("detection_method", "TEXT",  "")],
             P["teal0"], P["teal2"])

    # Data table (example)
    er_table(ax, 3.5, 4.5, "ft_d_requisition_list  (example data table)",
             [("folder_workflow_step", "VARCHAR", "status/state column"),
              ("bu",                  "VARCHAR", "DTS / SGI / SB …"),
              ("number_of_openings",  "BIGINT",  ""),
              ("remaining_openings",  "BIGINT",  ""),
              ("cancelledwithdrawn_date","VARCHAR",""),
              ("date_closed",         "VARCHAR", ""),
              ("filled_date",         "VARCHAR", ""),
              ("days_open",           "BIGINT",  "")],
             P["amber0"], P["amber2"], w=5.5)

    # relationship arrows
    arrow(ax, 3.5+4.0/2, 8.3,  9.5-4.0/2, 11.5-0.3, color=P["blue2"], lw=1.5,
          label="1 : N")
    arrow(ax, 9.5+4.0/2, 8.0, 15.2-4.0/2, 11.5-0.3, color=P["purple2"], lw=1.5,
          label="1 : N")
    arrow(ax, 3.5+5.5/2, 4.5, 9.5-4.0/2,  9.7,       color=P["amber2"], lw=1.5,
          label="is catalogued by")

    plt.tight_layout()
    save(fig, "05_database_schema.png")


# ══════════════════════════════════════════════════════════════════════════════
# 6. COMPONENT DEPENDENCY GRAPH
# ══════════════════════════════════════════════════════════════════════════════
def diagram_dependencies():
    G = nx.DiGraph()

    nodes = {
        # (display label, layer, color)
        "main.py":              ("main.py",              0, P["blue1"]),
        "config.py":            ("config.py",            0, P["blue0"]),
        "upload.py":            ("upload.py",            1, P["teal1"]),
        "chat.py":              ("chat.py",              1, P["teal1"]),
        "metadata_api.py":      ("metadata.py\n(API)",   1, P["teal1"]),
        "orchestrator.py":      ("orchestrator.py",      2, P["purple1"]),
        "sql_agent.py":         ("sql_agent.py",         3, P["purple0"]),
        "sql_validator.py":     ("sql_validator.py",     4, P["amber1"]),
        "ingestion.py":         ("ingestion.py",         2, P["red1"]),
        "schema_detector.py":   ("schema_detector.py",  3, P["red0"]),
        "metadata_builder.py":  ("metadata_builder.py", 3, P["red0"]),
        "relationship.py":      ("relationship\ndetector",3,P["red0"]),
        "mistral_client.py":    ("mistral_client.py",   3, P["amber1"]),
        "prompts.py":           ("prompts.py",           4, P["amber0"]),
        "connection.py":        ("connection.py",        4, P["teal0"]),
        "duckdb":               ("duckdb\n(external)",   5, P["green1"]),
        "sqlglot":              ("sqlglot\n(external)",  5, P["green0"]),
        "siemens_api":          ("Siemens API\n(external)",5,P["amber0"]),
        "pandas":               ("pandas\n(external)",   5, P["blue0"]),
    }

    edges = [
        ("main.py","config.py"),("main.py","upload.py"),
        ("main.py","chat.py"),("main.py","metadata_api.py"),
        ("main.py","connection.py"),
        ("upload.py","ingestion.py"),
        ("chat.py","orchestrator.py"),
        ("metadata_api.py","orchestrator.py"),
        ("orchestrator.py","sql_agent.py"),
        ("orchestrator.py","mistral_client.py"),
        ("sql_agent.py","mistral_client.py"),
        ("sql_agent.py","sql_validator.py"),
        ("sql_agent.py","connection.py"),
        ("sql_agent.py","metadata_builder.py"),
        ("ingestion.py","schema_detector.py"),
        ("ingestion.py","metadata_builder.py"),
        ("ingestion.py","relationship.py"),
        ("ingestion.py","pandas"),
        ("schema_detector.py","pandas"),
        ("metadata_builder.py","connection.py"),
        ("mistral_client.py","prompts.py"),
        ("mistral_client.py","siemens_api"),
        ("sql_validator.py","sqlglot"),
        ("connection.py","duckdb"),
    ]

    for n in nodes:
        G.add_node(n)
    G.add_edges_from(edges)

    # Layered layout
    layer_order = {
        0: ["main.py","config.py"],
        1: ["upload.py","chat.py","metadata_api.py"],
        2: ["orchestrator.py","ingestion.py"],
        3: ["sql_agent.py","schema_detector.py","metadata_builder.py",
            "relationship.py","mistral_client.py"],
        4: ["sql_validator.py","prompts.py","connection.py"],
        5: ["duckdb","sqlglot","siemens_api","pandas"],
    }
    pos = {}
    for layer, nlist in layer_order.items():
        n = len(nlist)
        for i, node in enumerate(nlist):
            pos[node] = ((i+1)/(n+1), 1 - layer/5.5)

    fig, ax = plt.subplots(figsize=(18, 12), facecolor=P["gray0"])
    ax.set_xlim(-0.05, 1.05); ax.set_ylim(0.0, 1.15); ax.axis("off")
    title(ax, "Component Dependency Graph", fontsize=15)

    # Draw edges first
    for u, v in G.edges():
        x1, y1 = pos[u]; x2, y2 = pos[v]
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", lw=1.3,
                                   color=P["gray1"],
                                   connectionstyle="arc3,rad=0.08"),
                    zorder=2)

    # Draw nodes
    for node, (label, layer, color) in nodes.items():
        x, y = pos[node]
        circ = plt.Circle((x, y), 0.035, color=color, ec=P["gray2"],
                          linewidth=1.5, zorder=3)
        ax.add_patch(circ)
        ax.text(x, y - 0.055, label, fontsize=7.5, ha="center", va="top",
                zorder=4, color=P["gray2"], fontweight="bold")

    # Layer labels on left
    layer_labels = {0:"Entry", 1:"API Routers", 2:"Agents / Ingestion",
                    3:"Core Logic", 4:"Validators / DB / Prompts", 5:"External"}
    for layer, lbl in layer_labels.items():
        y = 1 - layer/5.5
        ax.text(-0.04, y, lbl, fontsize=9, va="center", ha="right",
                color=P["gray1"], style="italic")

    plt.tight_layout()
    save(fig, "06_component_dependencies.png")


# ══════════════════════════════════════════════════════════════════════════════
# 7. LLM INTERACTION FLOW
# ══════════════════════════════════════════════════════════════════════════════
def diagram_llm_flow():
    fig, ax = plt.subplots(figsize=(16, 10), facecolor=P["gray0"])
    ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.axis("off")
    title(ax, "LLM Interaction Calls — 3 Calls per Chat Turn", fontsize=14)

    calls = [
        # x, y, w, h, fc, ec, title, prompt_name, in_text, out_text
        (3.0, 8.0, 5.5, 3.5, P["teal0"], P["teal2"],
         "Call ①  Intent Classification",
         "INTENT_CLASSIFICATION",
         "Input:\n  • User question\n  • Brief schema summary\n    (table names + row counts)",
         "Output JSON:\n  { intent: SQL_ANALYTICS,\n    confidence: 0.95,\n    reason: \"...\" }"),

        (3.0, 4.0, 5.5, 3.5, P["purple0"], P["purple2"],
         "Call ②  SQL Generation",
         "SQL_GENERATION",
         "Input:\n  • Full schema context\n  • Distinct categorical values\n  • Relationships + semantics\n  • User question",
         "Output JSON:\n  { sql: \"SELECT ...\",\n    explanation: \"...\" }"),

        (3.0, 0.2, 5.5, 3.2, P["amber0"], P["amber2"],
         "Call ③  Response Formatting",
         "RESPONSE_FORMAT",
         "Input:\n  • Original question\n  • Executed SQL\n  • Query results (rows)\n  • Row count",
         "Output text:\n  Natural language answer\n  + markdown table if multi-row"),
    ]

    for x, y, w, h, fc, ec, call_title, prompt, inp, out in calls:
        # outer box
        box(ax, x, y + h/2, w, h, fc, ec=ec, lw=2)
        # title
        ax.text(x, y + h - 0.3, call_title, fontsize=10, ha="center",
                fontweight="bold", color=ec, zorder=5)
        # prompt badge
        ax.text(x, y + h - 0.7, f"Prompt: {prompt}", fontsize=8, ha="center",
                style="italic", color=P["gray2"], zorder=5,
                bbox=dict(fc=P["white"], ec=ec, boxstyle="round,pad=0.2", lw=1))
        # input / output boxes
        box(ax, x - 1.2, y + h/2 - 0.5, 2.1, h-1.2, P["white"], ec=P["gray1"], lw=1)
        ax.text(x - 1.2, y + h - 1.1, "IN", fontsize=7, ha="center",
                color=P["gray1"], fontweight="bold")
        ax.text(x - 1.2, y + h - 1.4, inp, fontsize=7, ha="center",
                va="top", color=P["gray2"])

        box(ax, x + 1.2, y + h/2 - 0.5, 2.1, h-1.2, P["white"], ec=P["gray1"], lw=1)
        ax.text(x + 1.2, y + h - 1.1, "OUT", fontsize=7, ha="center",
                color=P["gray1"], fontweight="bold")
        ax.text(x + 1.2, y + h - 1.4, out, fontsize=7, ha="center",
                va="top", color=P["gray2"])

    # LLM box (right side)
    box(ax, 12, 5, 3.5, 9.0, P["red0"], ec=P["red2"], lw=3,
        text="🤖\nSiemens\nLLM API\n\ngpt-oss-120b\n\nhttps://api\n.siemens.com\n/llm/v1/\nchat/completions\n\nBearer Auth",
        fontsize=9, bold=True)

    # arrows to/from LLM
    for y_call, dy in [(8.0, 0), (4.0, 0), (0.2, 0)]:
        arrow(ax, 6.0, y_call + 1.75, 10.25, 5 + 2,   color=P["red2"], lw=2, label="HTTP POST")
        arrow(ax, 10.25, 5 - 2,       6.0,   y_call + 1.75 - 3.2, color=P["red2"], lw=2, label="JSON")

    # sequential arrows (call 1→2→3)
    for y1, y2 in [(7.0, 4.0+3.2), (4.0, 0.2+3.0)]:
        arrow(ax, 2.5, y1, 2.5, y2, color=P["gray2"], lw=2)

    plt.tight_layout()
    save(fig, "07_llm_interactions.png")


# ══════════════════════════════════════════════════════════════════════════════
# 8. STATUS SEMANTICS
# ══════════════════════════════════════════════════════════════════════════════
def diagram_status_semantics():
    fig, ax = plt.subplots(figsize=(16, 10), facecolor=P["gray0"])
    ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.axis("off")
    title(ax, "Status Semantics — What Counts as an 'Open Position'?", fontsize=14)

    # Central column header
    box(ax, 8, 9.0, 6, 0.7, P["amber1"], ec=P["amber2"], lw=2.5,
        text='Column:  "folder_workflow_step"', fontsize=12, bold=True)

    # OPEN side
    box(ax, 3.5, 7.5, 5.5, 0.7, P["green1"], ec=P["green2"], lw=2.5,
        text="🟢  OPEN STATES  →  COUNT IN",
        fontsize=11, bold=True)

    open_states = [
        ("Published",                    "42 rows", "Actively seeking candidates"),
        ("Consultation & Planning Mtg",  " 5 rows", "In planning, not yet closed"),
        ("Hiring Demand Creation",       " 3 rows", "Demand raised, not published"),
        ("On Hold",                      " 1 row",  "Paused — not cancelled"),
    ]
    for i, (status, count, note) in enumerate(open_states):
        y = 6.8 - i * 0.95
        box(ax, 3.5, y, 5.5, 0.7, P["green0"], ec=P["green2"], lw=1.5)
        ax.text(1.1, y+0.1, "✓", fontsize=16, color=P["green2"], va="center")
        ax.text(2.1, y+0.13, status, fontsize=9,  color=P["gray2"], fontweight="bold", va="center")
        ax.text(2.1, y-0.15, note,   fontsize=7.5, color=P["gray1"], va="center", style="italic")
        ax.text(5.9, y,      count,  fontsize=9,  color=P["green2"], va="center",
                fontweight="bold", ha="center")

    # TERMINAL side
    box(ax, 12.5, 7.5, 5.5, 0.7, P["red1"], ec=P["red2"], lw=2.5,
        text="🔴  TERMINAL STATES  →  EXCLUDE",
        fontsize=11, bold=True)

    terminal_states = [
        ("Filled & Hired",       "83 rows", "Successfully hired — done"),
        ("Cancelled/Withdrawn",  "75 rows", "Closed without hire — done"),
        ("Filled",               "29 rows", "Position filled — done"),
    ]
    for i, (status, count, note) in enumerate(terminal_states):
        y = 6.8 - i * 0.95
        box(ax, 12.5, y, 5.5, 0.7, P["red0"], ec=P["red2"], lw=1.5)
        ax.text(9.6, y+0.1, "✗", fontsize=16, color=P["red2"], va="center")
        ax.text(10.6, y+0.13, status, fontsize=9,  color=P["gray2"], fontweight="bold", va="center")
        ax.text(10.6, y-0.15, note,   fontsize=7.5, color=P["gray1"], va="center", style="italic")
        ax.text(14.9, y,      count,  fontsize=9,  color=P["red2"], va="center",
                fontweight="bold", ha="center")

    # arrows from header
    arrow(ax, 6.5, 8.65, 4.2, 8.15, color=P["green2"], lw=2.5)
    arrow(ax, 9.5, 8.65, 11.8, 8.15, color=P["red2"],  lw=2.5)

    # Result box
    box(ax, 8, 1.3, 14, 2.0, P["green0"], ec=P["green2"], lw=3)
    ax.text(8, 2.05, "✅  Result for 'How many open positions in DTS?'",
            fontsize=12, ha="center", fontweight="bold", color=P["green2"])

    # Mini table
    cols = ["Status", "Count"]
    rows = [
        ("Published",                   "42"),
        ("Consultation & Planning Mtg", " 5"),
        ("Hiring Demand Creation",      " 3"),
        ("On Hold",                     " 1"),
        ("TOTAL",                       "51"),
    ]
    col_x = [5.5, 10.5]
    for ci, ch in enumerate(cols):
        ax.text(col_x[ci], 1.65, ch, fontsize=9, ha="center",
                fontweight="bold", color=P["green2"])
    for ri, (s, c) in enumerate(rows):
        ry = 1.35 - ri * 0.25
        fc = P["green1"] if s == "TOTAL" else P["white"]
        box(ax, 8, ry, 7, 0.22, fc, ec=P["green1"], lw=0.5)
        ax.text(col_x[0], ry, s, fontsize=8, ha="center", va="center",
                fontweight="bold" if s=="TOTAL" else "normal")
        ax.text(col_x[1], ry, c, fontsize=8, ha="center", va="center",
                fontweight="bold" if s=="TOTAL" else "normal",
                color=P["green2"])

    plt.tight_layout()
    save(fig, "08_status_semantics.png")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("\n🎨  Excel Intelligence — Generating Diagrams")
    print(f"📁  Output: {OUT.absolute()}\n")

    diagram_system_architecture()
    diagram_chat_flow()
    diagram_sql_agent()
    diagram_ingestion()
    diagram_database_schema()
    diagram_dependencies()
    diagram_llm_flow()
    diagram_status_semantics()

    print(f"\n✅  Done — {len(list(OUT.glob('*.png')))} PNG files created in {OUT.absolute()}")
    print("\n📊  Files:")
    for f in sorted(OUT.glob("*.png")):
        kb = f.stat().st_size // 1024
        print(f"    {f.name}  ({kb} KB)")


if __name__ == "__main__":
    main()
