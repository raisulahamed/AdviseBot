import sqlite3, random, os
random.seed(7)
DB = "registry.db"
if os.path.exists(DB):
    os.remove(DB)
con = sqlite3.connect(DB)
cur = con.cursor()
cur.executescript("""
CREATE TABLE courses(code TEXT PRIMARY KEY, title TEXT, credits INTEGER, prereq TEXT, min_grade TEXT);
CREATE TABLE students(id TEXT PRIMARY KEY, name TEXT, advisor TEXT, year INTEGER);
CREATE TABLE completed(student_id TEXT, course TEXT, grade TEXT);
CREATE TABLE waiver_requests(id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, course TEXT, reason TEXT, status TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
""")

POINTS = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
COURSES = [
    ("CSE 1101", "Structured Programming", 3, None, None),
    ("CSE 1103", "Discrete Mathematics", 3, None, None),
    ("CSE 1105", "Digital Logic Design", 3, None, None),
    ("CSE 1201", "Data Structures", 3, "CSE 1101", "C"),
    ("CSE 1203", "Object Oriented Programming", 3, "CSE 1101", "C"),
    ("CSE 1205", "Computer Architecture", 3, "CSE 1105", "C"),
    ("MAT 1101", "Calculus I", 3, None, None),
    ("MAT 1201", "Linear Algebra", 3, "MAT 1101", "D"),
    ("CSE 2101", "Algorithms", 3, "CSE 1201", "C"),
    ("CSE 2103", "Database Systems", 3, "CSE 1201", "C"),
    ("CSE 2105", "Operating Systems", 3, "CSE 1205", "C"),
    ("CSE 2107", "Computer Networks", 3, "CSE 1205", "D"),
    ("CSE 2201", "Theory of Computation", 3, "CSE 1103", "C"),
    ("CSE 2203", "Artificial Intelligence", 3, "CSE 2101", "C"),
    ("CSE 2205", "Web Programming", 3, "CSE 1203", "D"),
    ("CSE 2207", "Numerical Methods", 3, "MAT 1201", "D"),
    ("CSE 2209", "Compiler Design", 3, "CSE 2201", "C"),
    ("CSE 2211", "Computer Graphics", 3, "CSE 1201", "D"),
    ("CSE 2213", "Machine Learning", 3, "CSE 2203", "C"),
    ("CSE 2109", "Software Engineering", 3, "CSE 1203", "C"),
]
cur.executemany("INSERT INTO courses VALUES (?,?,?,?,?)", COURSES)

NAMES = ["Rafi Ahmed", "Nusrat Jahan", "Tanvir Hasan", "Mim Akter", "Sabbir Hossain",
         "Farhana Islam", "Imran Khan", "Sadia Rahman", "Arif Chowdhury", "Lamia Sultana",
         "Naeem Uddin", "Tasnim Haque", "Rakib Mia", "Joya Barua", "Shuvo Das",
         "Anika Tabassum", "Mahin Alam", "Ritu Paul", "Zahid Karim", "Sumaiya Noor"]
ADVISORS = ["Dr. Rahman", "Dr. Akter", "Dr. Hasan"]

fixed = {
    "S-0001": [("CSE 1101", "B"), ("CSE 1103", "B"), ("CSE 1105", "C"), ("CSE 1201", "D"), ("CSE 1203", "B")],
    "S-0002": [("CSE 1101", "A"), ("CSE 1103", "B"), ("CSE 1105", "B"), ("CSE 1201", "B")],
}
for i, name in enumerate(NAMES, start=1):
    sid = f"S-{i:04d}"
    cur.execute("INSERT INTO students VALUES (?,?,?,?)", (sid, name, random.choice(ADVISORS), random.choice([1, 2])))
    if sid in fixed:
        records = fixed[sid]
    else:
        records, passed = [], {}
        target = random.randint(4, 12)
        for code, title, cr, prereq, mg in COURSES:
            if len(records) >= target:
                break
            if prereq and POINTS[passed.get(prereq, "F")] < POINTS[mg]:
                continue
            g = random.choices(["A", "B", "C", "D", "F"], [3, 4, 3, 1, 1])[0]
            records.append((code, g))
            passed[code] = g
    cur.executemany("INSERT INTO completed VALUES (?,?,?)", [(sid, c, g) for c, g in records])

con.commit()
print("courses:", cur.execute("SELECT COUNT(*) FROM courses").fetchone()[0])
print("students:", cur.execute("SELECT COUNT(*) FROM students").fetchone()[0])
print("S-0001:", cur.execute("SELECT course, grade FROM completed WHERE student_id='S-0001'").fetchall())
print("S-0002:", cur.execute("SELECT course, grade FROM completed WHERE student_id='S-0002'").fetchall())
con.close()
