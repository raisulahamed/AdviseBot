from tools import check_prerequisites

tests = [("S-0001", "CSE 2101"), ("S-0002", "CSE 2101"), ("S-0001", "CSE 1101"),
         ("S-0001", "cse2103"), ("S-0001", "CSE 9999"), ("S-9999", "CSE 2101")]
for sid, course in tests:
    print(sid, course, "->", check_prerequisites.invoke({"student_id": sid, "course_code": course}))
