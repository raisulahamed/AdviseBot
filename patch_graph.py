p = open("graph.py", encoding="utf-8").read()
n = 0

old = '"my_record = asks if THIS student can take a course, or about their own grades; "'
new = '"my_record = asks if THIS student can take a course (including short follow-ups like \'and CSE 2103?\'), or about their own grades; "'
if old in p: p = p.replace(old, new); n += 1

old = '"If it is already standalone, return it unchanged. Output only the question."'
new = '"If it is already standalone, return it unchanged. Do not add course codes, grades or details the student did not mention. Output only the question."'
if old in p: p = p.replace(old, new); n += 1

old = 'SystemMessage("Draft a short prerequisite waiver request for a CSE student. Use only the facts given.")'
new = ('SystemMessage("Draft a short prerequisite waiver request for a CSE student. Write exactly two plain sentences in first person: '
       'the first states the course requested and the grade the student has in the prerequisite; the second asks the advisor to consider a waiver. '
       'Use only the facts given. Do not claim anything about ability, effort or academic record, and do not promise anything.")')
if old in p: p = p.replace(old, new); n += 1

open("graph.py", "w", encoding="utf-8").write(p)
print("patched", n, "of 3")
