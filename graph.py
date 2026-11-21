import os, re, sqlite3
from typing import Annotated, Literal, Optional, TypedDict

from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

from tools import (check_prerequisites, pending_waiver_for, create_waiver, set_waiver_status)
from langgraph.types import interrupt, Command
from langchain_core.runnables import RunnableConfig

def retrieve(q):
    from rag import retrieve as _r          # loaded only when needed
    return _r(q)


IDK = "I don't have a source for that. Please ask the department office."


# ---------- C1: structured output ----------
class Intent(BaseModel):
    category: Literal["rule_question", "my_record", "waiver", "off_topic"] = Field(
        description="rule_question = asks about a university rule, deadline, fee or policy, including how waivers, retakes or credit limits work; "
                    "my_record = asks if THIS student can take a course (including short follow-ups like 'and CSE 2103?'), or about their own grades; "
                    "waiver = asks you to write, draft or file a prerequisite waiver request (a question ABOUT waiver rules or conditions is rule_question, not waiver); "
                    "off_topic = anything else")
    course_code: Optional[str] = Field(default=None, description="Course code mentioned, e.g. CSE 2101, else null")


class WaiverRequest(BaseModel):
    course: str = Field(description="Course code, e.g. CSE 2101")
    reason: str = Field(description="2 short sentences, first person, why the student asks for a waiver, using the grade evidence")


# ---------- C2: model layer with fallback ----------
_cache = {}

def _models():
    if not _cache:
        from langchain.chat_models import init_chat_model
        backup = init_chat_model("groq:openai/gpt-oss-20b", timeout=30)
        if os.getenv("USE_GEMINI", "1") == "0":
            main = backup
        else:
            main = init_chat_model("google_genai:gemini-3.8-flash", timeout=15, max_retries=0)
        _cache["main"], _cache["backup"] = main, backup
    return _cache["main"], _cache["backup"]


def _text(content):
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return content


def llm_text(msgs):
    main, backup = _models()
    return _text(main.with_fallbacks([backup]).invoke(msgs).content)


def classify_llm(msgs) -> Intent:
    main, backup = _models()
    a = main.with_structured_output(Intent)
    b = backup.with_structured_output(Intent, method="function_calling")
    return a.with_fallbacks([b]).invoke(msgs)


def waiver_llm(msgs) -> WaiverRequest:
    main, backup = _models()
    a = main.with_structured_output(WaiverRequest)
    b = backup.with_structured_output(WaiverRequest, method="function_calling")
    return a.with_fallbacks([b]).invoke(msgs)


def agent_llm(msgs):
    main, backup = _models()
    t = [check_prerequisites]
    return main.bind_tools(t).with_fallbacks([backup.bind_tools(t)]).invoke(msgs)


# ---------- state ----------
class State(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    student_id: str
    intent: str
    course_code: str
    question: str
    answer: str
    sources: list
    waiver_id: int
    waiver_course: str
    waiver_reason: str
    approval: dict


def last_user(state):
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            return _text(m.content)
    return ""


def history_text(state, n=6):
    msgs = state["messages"][:-1][-n:]
    return "\n".join(("Student: " if isinstance(m, HumanMessage) else "Bot: ") + _text(m.content) for m in msgs if isinstance(m, (HumanMessage, AIMessage)) and _text(m.content))


# ---------- nodes ----------
INJECTION = re.compile(r"ignore (all |your |previous |the )?(rules|instructions)|system prompt|reveal your|developer mode|jailbreak", re.I)


def input_guard(state):
    q = last_user(state)
    base = {"intent": "", "answer": "", "course_code": "", "question": q, "sources": []}
    if INJECTION.search(q):
        return {**base, "intent": "blocked", "answer": "I can't do that. I can help with CSE prerequisites, registration rules and waiver requests."}
    others = {s for s in re.findall(r"S-\d{4}", q, re.I) if s.upper() != state["student_id"].upper()}
    if others or re.search(r"\b(my friend|classmate|someone else|another student)'?s? (grade|record|result)", q, re.I):
        return {**base, "intent": "blocked", "answer": "I can only see your own record. I can't share another student's information."}
    return base


WAIVER_ASK = re.compile(r"\b(write|draft|file|submit|apply|send|prepare|help me|i need|i want|i would like|i'd like|please|get a waiver|can i get|can i have)\b", re.I)


def classify_intent(state):
    prompt = [SystemMessage("Classify the student's latest message for a CSE department help desk. "
                            "Use the chat history to understand follow-ups."),
              HumanMessage(f"History:\n{history_text(state) or '(none)'}\n\nLatest message: {last_user(state)}")]
    it = classify_llm(prompt)
    cat = it.category
    if cat == "waiver" and not WAIVER_ASK.search(last_user(state)):
        cat = "rule_question"                        # asking ABOUT waivers is a rule question, not a request
    return {"intent": cat, "course_code": it.course_code or ""}


def rewrite_question(state):                     # E4
    q = last_user(state)
    h = history_text(state)
    if not h:
        return {"question": q}
    out = llm_text([SystemMessage("Rewrite the student's latest message as one standalone question, "
                                  "using the chat history to fill in what it refers to. "
                                  "If it is already standalone, return it unchanged. Do not add course codes, grades or details the student did not mention. Output only the question."),
                    HumanMessage(f"History:\n{h}\n\nLatest message: {q}")]).strip()
    return {"question": out or q}


RAG_SYSTEM = ("You are AdviseBot, a help desk assistant for CSE students. Answer ONLY from the numbered sources below. "
              "After every rule you state, cite it like [4.2, p.5], using the section number and page of the source. "
              f"If the sources do not answer the question, reply exactly: \"{IDK}\" "
              "Do not use outside knowledge. Keep the answer short.")


def retrieve_answer(state):
    hits = retrieve(state["question"])
    src = "\n\n".join(f"SOURCE [{p['section']}, p.{p['page']}] {p['text']}" for p, _ in hits)
    ans = llm_text([SystemMessage(RAG_SYSTEM + "\n\n" + src), HumanMessage(state["question"])])
    return {"answer": ans, "sources": [(p["section"], p["page"]) for p, _ in hits]}


AGENT_SYSTEM = ("You are AdviseBot, a help desk assistant for CSE students. The student is already signed in, "
                "so never ask for a student ID. For any question about whether the student can take a course, "
                "call check_prerequisites with the course code. Answer only from the tool result and keep it short. "
                "Never reveal or discuss any other student's data.")


def agent(state):
    msgs = [SystemMessage(AGENT_SYSTEM)] + state["messages"][-10:]
    for _ in range(4):                                         # cap: 4 steps
        ai = agent_llm(msgs)
        msgs.append(ai)
        if not ai.tool_calls:
            return {"answer": _text(ai.content)}
        for call in ai.tool_calls:
            args = dict(call["args"])
            args["student_id"] = state["student_id"]           # injected by code, never by the model
            res = check_prerequisites.invoke(args)
            msgs.append(ToolMessage(content=str(res), tool_call_id=call["id"]))
    return {"answer": "Sorry, I couldn't finish that. Please ask the department office."}


COURSE = re.compile(r"\b(CSE|MAT)\s?-?(\d{4})\b", re.I)
NON_WAIVABLE = {"CSE 2209", "CSE 2213"}                      # Section 5.5


def find_course(state):
    texts = [last_user(state)] + [_text(m.content) for m in reversed(state["messages"][:-1])]
    for t in texts:
        m = COURSE.search(t or "")
        if m:
            return f"{m.group(1).upper()} {m.group(2)}"
    return state.get("course_code", "")


def draft_waiver(state, config: RunnableConfig):
    sid = state["student_id"]
    course = find_course(state)
    if not course:
        return {"answer": "Which course do you want a waiver for?"}
    if course in NON_WAIVABLE:
        return {"answer": f"The prerequisite of {course} cannot be waived. [5.5, p.6]"}
    check = check_prerequisites.invoke({"course_code": course, "student_id": sid})
    if check.get("eligible"):
        return {"answer": f"You already meet the prerequisite for {course}, so no waiver is needed."}
    if "grade_used" not in check:
        return {"answer": check["reason"]}
    old = pending_waiver_for(sid, course)
    if old:                                                    # idempotency: never file the same request twice
        return {"answer": f"You already have a waiver request (#{old}) for {course} waiting for your advisor."}
    d = waiver_llm([SystemMessage("Draft a short prerequisite waiver request for a CSE student. Write exactly two plain sentences in first person: the first states the course requested and the grade the student has in the prerequisite; the second asks the advisor to consider a waiver. Use only the facts given. Do not claim anything about ability, effort or academic record, and do not promise anything."),
                    HumanMessage(f"Student: {sid}\nCourse: {course}\nEvidence: {check['reason']} ({check['grade_used']})\n"
                                 f"Student message: {last_user(state)}")])
    thread = config["configurable"]["thread_id"]
    wid = create_waiver(sid, course, d.reason, thread)
    return {"waiver_id": wid, "waiver_course": course, "waiver_reason": d.reason,
            "answer": f"I drafted a waiver request (#{wid}) for {course}: \"{d.reason}\" It has been sent to your advisor for review."}


def human_approval(state):                                     # E2: the graph pauses here, state is saved to SQLite
    decision = interrupt({"waiver_id": state["waiver_id"], "student_id": state["student_id"],
                          "course": state["waiver_course"], "reason": state["waiver_reason"]})
    return {"approval": decision}


def submit_waiver(state):                                      # runs only after the advisor approved
    a = state["approval"]
    set_waiver_status(state["waiver_id"], "approved", a.get("note", ""), a.get("reason"))
    return {"answer": f"Your advisor approved waiver request #{state['waiver_id']} for {state['waiver_course']}. "
                      f"You can now register for it. {a.get('note', '')}".strip()}


def waiver_rejected(state):
    a = state["approval"]
    set_waiver_status(state["waiver_id"], "rejected", a.get("note", ""))
    return {"answer": f"Your advisor did not approve waiver request #{state['waiver_id']}. {a.get('note', '')}".strip()}


def refuse(state):
    if state.get("answer"):
        return {}
    return {"answer": "I can only help with CSE prerequisites, registration rules and waiver requests."}


def output_guard(state):
    ans = state.get("answer", "")
    if state.get("intent") == "rule_question" and ans != IDK and not re.search(r"\[[^\]]*p\.\s*\d+[^\]]*\]", ans):
        ans = IDK                                              # uncited rule answer is not allowed
    if re.search(r"(you will|you.ll|you are going to) (be )?(approved|granted)|waiver (will be|is) (approved|granted)", ans, re.I):
        ans = "I can't say what the advisor will decide. The request will be sent for review."
    return {"answer": ans, "messages": [AIMessage(ans)]}


# ---------- C7: graph ----------
def after_guard(s):
    return "refuse" if s["intent"] == "blocked" else "classify_intent"

def after_classify(s):
    return {"rule_question": "rewrite_question", "my_record": "agent", "waiver": "draft_waiver"}.get(s["intent"], "refuse")


def after_draft(s):
    return "human_approval" if s.get("waiver_id") and not s.get("approval") else "output_guard"

def after_approval(s):
    return "submit_waiver" if s["approval"].get("decision") == "approved" else "waiver_rejected"


def build(path="memory.db"):
    g = StateGraph(State)
    for n, f in [("input_guard", input_guard), ("classify_intent", classify_intent), ("rewrite_question", rewrite_question),
                 ("retrieve_answer", retrieve_answer), ("agent", agent), ("draft_waiver", draft_waiver), ("human_approval", human_approval),
                 ("submit_waiver", submit_waiver), ("waiver_rejected", waiver_rejected),
                 ("refuse", refuse), ("output_guard", output_guard)]:
        g.add_node(n, f)
    g.add_edge(START, "input_guard")
    g.add_conditional_edges("input_guard", after_guard, ["refuse", "classify_intent"])
    g.add_conditional_edges("classify_intent", after_classify, ["rewrite_question", "agent", "draft_waiver", "refuse"])
    g.add_edge("rewrite_question", "retrieve_answer")
    for n in ("retrieve_answer", "agent", "refuse", "submit_waiver", "waiver_rejected"):
        g.add_edge(n, "output_guard")
    g.add_conditional_edges("draft_waiver", after_draft, ["human_approval", "output_guard"])
    g.add_conditional_edges("human_approval", after_approval, ["submit_waiver", "waiver_rejected"])
    g.add_edge("output_guard", END)
    conn = sqlite3.connect(path, check_same_thread=False)       # C4: memory survives restarts
    return g.compile(checkpointer=SqliteSaver(conn))


def chat(graph, question, student_id="S-0001", thread="demo"):
    out = graph.invoke({"messages": [HumanMessage(question)], "student_id": student_id},
                       config={"configurable": {"thread_id": thread}})
    return out


def resume(graph, thread, decision):
    """Called by the advisor page, possibly in a different process, long after the student's turn."""
    return graph.invoke(Command(resume=decision), config={"configurable": {"thread_id": thread}})


def is_paused(graph, thread):
    return bool(graph.get_state({"configurable": {"thread_id": thread}}).next)
