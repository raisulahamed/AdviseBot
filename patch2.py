p = open("graph.py", encoding="utf-8").read()
n = 0

old = '"rule_question = asks about a university rule, deadline, fee or policy; "'
new = '"rule_question = asks about a university rule, deadline, fee or policy, including how waivers, retakes or credit limits work; "'
if old in p: p = p.replace(old, new); n += 1

old = '"waiver = wants a prerequisite waiver request; "'
new = '"waiver = asks you to write, draft or file a prerequisite waiver request (a question ABOUT waiver rules or conditions is rule_question, not waiver); "'
if old in p: p = p.replace(old, new); n += 1

open("graph.py", "w", encoding="utf-8").write(p)
print("patched", n, "of 2")
