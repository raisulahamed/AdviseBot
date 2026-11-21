p = open("graph.py", encoding="utf-8").read()
n = 0

old = "def classify_intent(state):"
new = ('WAIVER_ASK = re.compile(r"\\b(write|draft|file|submit|apply|send|prepare|help me|i need|i want|i would like|i\'d like|please|get a waiver|can i get|can i have)\\b", re.I)\n\n\n'
       "def classify_intent(state):")
if old in p and "WAIVER_ASK" not in p:
    p = p.replace(old, new, 1); n += 1

old = '    return {"intent": it.category, "course_code": it.course_code or ""}'
new = ('    cat = it.category\n'
       '    if cat == "waiver" and not WAIVER_ASK.search(last_user(state)):\n'
       '        cat = "rule_question"                        # asking ABOUT waivers is a rule question, not a request\n'
       '    return {"intent": cat, "course_code": it.course_code or ""}')
if old in p: p = p.replace(old, new, 1); n += 1

open("graph.py", "w", encoding="utf-8").write(p)
print("patched", n, "of 2")
