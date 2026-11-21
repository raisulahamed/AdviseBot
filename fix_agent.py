p = open("agent_test.py", encoding="utf-8").read()
if "msgs.append(ai)" not in p:
    p = p.replace("        ai = model.invoke(msgs)\n", "        ai = model.invoke(msgs)\n        msgs.append(ai)\n")
    open("agent_test.py", "w", encoding="utf-8").write(p)
    print("fixed")
else:
    print("already ok")
