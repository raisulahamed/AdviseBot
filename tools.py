import sqlite3
from typing import Annotated
from langchain_core.tools import tool, InjectedToolArg

DB = "registry.db"
POINTS = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}


def _query(sql, args=()):
    con = sqlite3.connect(DB)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


@tool
def check_prerequisites(course_code: str, student_id: Annotated[str, InjectedToolArg]) -> dict:
    """Check whether a student may take a course, based on the student's completed
    courses and grades and the course's prerequisite rule. Use this for any question
    like "can I register for CSE 2101?". Returns eligible (bool), the reason, and the
    grade the decision was based on."""
    course_code = course_code.strip().upper().replace("CSE", "CSE ").replace("MAT", "MAT ")
    course_code = " ".join(course_code.split())

    course = _query("SELECT code, title, prereq, min_grade FROM courses WHERE code=?", (course_code,))
    if not course:
        return {"eligible": False, "reason": f"Course {course_code} was not found in the catalogue."}
    code, title, prereq, min_grade = course[0]

    student = _query("SELECT id FROM students WHERE id=?", (student_id,))
    if not student:
        return {"eligible": False, "reason": f"Student {student_id} was not found."}

    done = dict(_query("SELECT course, grade FROM completed WHERE student_id=?", (student_id,)))

    if code in done and POINTS[done[code]] >= 1:
        return {"eligible": False, "course": code, "reason": f"Already completed {code} with grade {done[code]}."}

    if prereq is None:
        return {"eligible": True, "course": code, "title": title, "reason": "No prerequisite."}

    grade = done.get(prereq)
    if grade is None:
        return {"eligible": False, "course": code, "title": title, "required": f"{prereq} with at least {min_grade}",
                "reason": f"{prereq} has not been completed."}
    if POINTS[grade] < POINTS[min_grade]:
        return {"eligible": False, "course": code, "title": title, "required": f"{prereq} with at least {min_grade}",
                "grade_used": f"{prereq}: {grade}",
                "reason": f"{code} needs at least {min_grade} in {prereq}, but the student has {grade}."}
    return {"eligible": True, "course": code, "title": title, "grade_used": f"{prereq}: {grade}",
            "reason": f"{prereq} completed with {grade} (needs at least {min_grade})."}


# ---------- waiver requests (the only write action) ----------
def _wcon():
    con = sqlite3.connect(DB)
    for col in ("thread_id TEXT", "note TEXT"):
        try:
            con.execute("ALTER TABLE waiver_requests ADD COLUMN " + col)
        except sqlite3.OperationalError:
            pass
    return con


def pending_waiver_for(student_id, course):
    con = _wcon()
    try:
        r = con.execute("SELECT id FROM waiver_requests WHERE student_id=? AND course=? AND status='pending'",
                        (student_id, course)).fetchone()
        return r[0] if r else None
    finally:
        con.close()


def create_waiver(student_id, course, reason, thread_id):
    con = _wcon()
    try:
        cur = con.execute("INSERT INTO waiver_requests(student_id, course, reason, status, thread_id) VALUES (?,?,?,'pending',?)",
                          (student_id, course, reason, thread_id))
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def set_waiver_status(waiver_id, status, note="", reason=None):
    con = _wcon()
    try:
        if reason:
            con.execute("UPDATE waiver_requests SET status=?, note=?, reason=? WHERE id=?", (status, note, reason, waiver_id))
        else:
            con.execute("UPDATE waiver_requests SET status=?, note=? WHERE id=?", (status, note, waiver_id))
        con.commit()
    finally:
        con.close()


def list_pending_waivers():
    con = _wcon()
    try:
        return con.execute("SELECT id, student_id, course, reason, thread_id FROM waiver_requests WHERE status='pending' ORDER BY id").fetchall()
    finally:
        con.close()
