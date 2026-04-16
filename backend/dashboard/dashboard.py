import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Voice agent analytics", layout="wide")
st.title("Voice agent analytics")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///calls.db")
engine = create_engine(DATABASE_URL)

# Ensure the table exists before querying
with engine.connect() as _conn:
    _conn.execute(__import__("sqlalchemy").text("""
        CREATE TABLE IF NOT EXISTS calls (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id     TEXT UNIQUE,
            phone       TEXT,
            language    TEXT,
            intent      TEXT,
            query       TEXT,
            top_score   REAL,
            escalated   INTEGER DEFAULT 0,
            duration_s  INTEGER,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    _conn.commit()


@st.cache_data(ttl=30)
def load() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT * FROM calls ORDER BY created_at DESC",
        engine,
        parse_dates=["created_at"],
    )


df = load()

if df.empty:
    st.info("No calls logged yet. Make a test call to see data here.")
    st.stop()

# ── KPI row ──────────────────────────────────────────────────────────────────
total       = len(df)
self_serve  = round((1 - df["escalated"].mean()) * 100, 1)
avg_score   = round(df["top_score"].mean(), 2)
avg_dur     = round(df["duration_s"].mean())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total calls",           total)
c2.metric("Self-service rate",     f"{self_serve}%",  help="Calls that did not escalate")
c3.metric("Avg retrieval score",   avg_score,          help="Qdrant cosine similarity, 0–1")
c4.metric("Avg duration (s)",      avg_dur)

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Calls by language")
    lang_counts = df["language"].value_counts().reset_index()
    lang_counts.columns = ["language", "count"]
    fig = px.bar(lang_counts, x="language", y="count",
                 color_discrete_sequence=["#378ADD"])
    fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Intent distribution")
    intent_counts = df["intent"].value_counts().reset_index()
    intent_counts.columns = ["intent", "count"]
    fig2 = px.pie(intent_counts, names="intent", values="count",
                  color_discrete_sequence=px.colors.qualitative.Set2)
    fig2.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig2, use_container_width=True)

# ── Calls over time ───────────────────────────────────────────────────────────
st.subheader("Call volume over time")
daily = df.set_index("created_at").resample("D").size().reset_index(name="calls")
fig3 = px.line(daily, x="created_at", y="calls", color_discrete_sequence=["#1D9E75"])
fig3.update_layout(margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(fig3, use_container_width=True)

# ── Content gaps ──────────────────────────────────────────────────────────────
st.subheader("Content gaps — retrieval score below threshold")
st.caption("These queries had low Qdrant confidence. Add answers to your FAQ files and re-ingest.")
threshold = st.slider("Score threshold", 0.0, 1.0, 0.6, 0.05)
gaps = df[df["top_score"] < threshold][["created_at", "language", "query", "top_score"]].copy()
gaps["top_score"] = gaps["top_score"].round(3)
gaps = gaps.sort_values("top_score")
st.dataframe(gaps, use_container_width=True, hide_index=True)

if not gaps.empty:
    csv = gaps.to_csv(index=False)
    st.download_button("Download gaps as CSV", csv, "content_gaps.csv", "text/csv")

# ── Recent call log ───────────────────────────────────────────────────────────
st.subheader("Recent calls")
recent = df.head(100)[
    ["created_at", "language", "intent", "query", "top_score", "escalated", "duration_s"]
].copy()
recent["top_score"] = recent["top_score"].round(3)
recent["escalated"] = recent["escalated"].map({0: "Self-served", 1: "Escalated"})
st.dataframe(recent, use_container_width=True, hide_index=True)
