p = open("tools.py", encoding="utf-8").read()
p = p.replace("from langchain_core.tools import tool",
              "from typing import Annotated\nfrom langchain_core.tools import tool, InjectedToolArg")
p = p.replace("student_id: str, course_code: str",
              "course_code: str, student_id: Annotated[str, InjectedToolArg]")
open("tools.py", "w", encoding="utf-8").write(p)
print("patched")
