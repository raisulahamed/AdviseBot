from graph import build, resume
from tools import list_pending_waivers

graph = build()
rows = list_pending_waivers()
if not rows:
    print("No pending waiver requests.")
    raise SystemExit

print("Pending waiver requests:\n")
for r in rows:
    print(f"  #{r[0]}  student {r[1]}  course {r[2]}\n      reason: {r[3]}\n")

wid = int(input("Request number to review: "))
row = next(r for r in rows if r[0] == wid)
choice = input("approve (a) or reject (r)? ").strip().lower()
reason = input("Edit the reason (press Enter to keep it): ").strip()
note = input("Note for the student (optional): ").strip()

decision = {"decision": "approved" if choice.startswith("a") else "rejected", "note": note}
if reason:
    decision["reason"] = reason
res = resume(graph, row[4], decision)
print("\nResumed the student's thread. The student will see:\n ", res["answer"])
