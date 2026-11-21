

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
