import sqlite3, uuid
import streamlit as st
from graph import build, chat, resume
from tools import list_pending_waivers

st.set_page_config(page_title="AdviseBot", layout="centered")


@st.cache_resource
def get_graph():
    return build("memory.db")


graph = get_graph()
list_pending_waivers()          # also makes sure the waiver table has all its columns


def db(sql, args=()):
    con = sqlite3.connect("registry.db")
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


role = st.sidebar.radio("Sign in as", ["Student", "Advisor"])

# ======================= STUDENT PAGE =======================
if role == "Student":
    st.title("AdviseBot")
    st.caption("CSE help desk: prerequisites, registration rules and waiver requests.")

    students = {f"{sid} - {name}": sid for sid, name in db("SELECT id, name FROM students ORDER BY id")}
    sid = students[st.sidebar.selectbox("Student (login)", list(students))]   # the session decides who the student is

    key = f"thread_{sid}"
    if key not in st.session_state:
        st.session_state[key] = f"web-{sid}-{uuid.uuid4().hex[:6]}"
    if st.sidebar.button("New conversation"):
        st.session_state[key] = f"web-{sid}-{uuid.uuid4().hex[:6]}"
        st.rerun()
    thread = st.session_state[key]
    cfg = {"configurable": {"thread_id": thread}}

    st.sidebar.markdown("**My waiver requests**")
    mine = db("SELECT id, course, status, note FROM waiver_requests WHERE student_id=? ORDER BY id DESC", (sid,))
    if mine:
        for wid, course, status, note in mine:
            st.sidebar.write(f"#{wid} {course}: {status}" + (f" ({note})" if note else ""))
    else:
        st.sidebar.write("None yet.")

    snap = graph.get_state(cfg)
    for m in snap.values.get("messages", []):
        st.chat_message("user" if m.type == "human" else "assistant").write(m.content)

    paused = bool(snap.next)
    if paused:
        st.chat_message("assistant").write(snap.values.get("answer", ""))      # the waiver draft
        st.info("Your waiver request is waiting for your advisor. You can close this page; the answer will be saved.")

    dbg = st.session_state.get("debug_" + thread)
    if dbg:
        with st.expander("How the last answer was made"):
            st.json(dbg)

    q = st.chat_input("Ask about a course, a rule, or a waiver...", disabled=paused)
    if q:
        st.chat_message("user").write(q)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                out = chat(graph, q, sid, thread)
            st.write(out["answer"])
        st.session_state["debug_" + thread] = {"intent": out.get("intent"), "standalone question": out.get("question"),
                                              "sources": [f"[{s}, p.{p}]" for s, p in out.get("sources", [])]}
        st.rerun()

# ======================= ADVISOR PAGE =======================
else:
    st.title("Advisor: waiver requests")
    rows = list_pending_waivers()
    if not rows:
        st.success("No pending requests.")
    for wid, sid, course, reason, thread in rows:
        grades = ", ".join(f"{c}: {g}" for c, g in db("SELECT course, grade FROM completed WHERE student_id=?", (sid,)))
        with st.container(border=True):
            st.markdown(f"**Request #{wid}**  |  student `{sid}`  |  course **{course}**")
            st.caption("Grades on record: " + grades)
            new_reason = st.text_area("Reason (you may edit it)", reason, key=f"reason{wid}")
            note = st.text_input("Note for the student", key=f"note{wid}")
            c1, c2 = st.columns(2)
            decision = None
            if c1.button("Approve", key=f"approve{wid}"):
                decision = {"decision": "approved", "note": note}
                if new_reason.strip() != reason:
                    decision["reason"] = new_reason.strip()
            if c2.button("Reject", key=f"reject{wid}"):
                decision = {"decision": "rejected", "note": note}
            if decision:
                resume(graph, thread, decision)           # continues the student's paused graph from SQLite
                st.rerun()
