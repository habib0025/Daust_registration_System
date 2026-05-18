import uuid
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def seed_database(conn):
    cursor = conn.cursor()
    
    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM Users")
    if cursor.fetchone()[0] > 0:
        return

    # Passwords
    admin_pw = generate_password_hash('admin123')
    student_pw = generate_password_hash('student123')
    instructor_pw = generate_password_hash('instructor123')

    # Users
    admin_id = str(uuid.uuid4())
    s1_id = str(uuid.uuid4())
    s2_id = str(uuid.uuid4())
    s3_id = str(uuid.uuid4())
    i1_id = str(uuid.uuid4())
    i2_id = str(uuid.uuid4())

    users = [
        (admin_id, 'Admin User', 'admin@daust.edu', admin_pw, 'Administrator'),
        (s1_id, 'Student One', 'student1@daust.edu', student_pw, 'Student'),
        (s2_id, 'Student Two', 'student2@daust.edu', student_pw, 'Student'),
        (s3_id, 'Student Three', 'student3@daust.edu', student_pw, 'Student'),
        (i1_id, 'Instructor Math', 'instr1@daust.edu', instructor_pw, 'Instructor'),
        (i2_id, 'Instructor CS', 'instr2@daust.edu', instructor_pw, 'Instructor')
    ]
    cursor.executemany("INSERT INTO Users VALUES (?,?,?,?,?)", users)

    # Students
    cursor.executemany("INSERT INTO Students (userID, major) VALUES (?,?)", [
        (s1_id, 'Computer Science'),
        (s2_id, 'Mathematics'),
        (s3_id, 'Computer Science')
    ])

    # Administrators
    cursor.execute("INSERT INTO Administrators (userID) VALUES (?)", (admin_id,))

    # Departments
    cs_dept_id = str(uuid.uuid4())
    math_dept_id = str(uuid.uuid4())
    cursor.executemany("INSERT INTO Departments VALUES (?,?,?)", [
        (cs_dept_id, 'CS', 'Computer Science'),
        (math_dept_id, 'MATH', 'Mathematics')
    ])

    # Instructors
    cursor.executemany("INSERT INTO Instructors (userID, departmentID) VALUES (?,?)", [
        (i1_id, math_dept_id),
        (i2_id, cs_dept_id)
    ])

    # Courses
    cs101_id = str(uuid.uuid4())
    cs201_id = str(uuid.uuid4())
    cs301_id = str(uuid.uuid4())
    cs2712_id = str(uuid.uuid4())
    math101_id = str(uuid.uuid4())
    math201_id = str(uuid.uuid4())

    courses = [
        (cs101_id, cs_dept_id, 'CS101', 'Intro to CS', 3, 'Basic CS'),
        (cs201_id, cs_dept_id, 'CS201', 'Data Structures', 4, 'DSA'),
        (cs301_id, cs_dept_id, 'CS301', 'Algorithms', 4, 'Advanced Algos'),
        (cs2712_id, cs_dept_id, 'CS2712', 'Software Engineering', 3, 'SWE'),
        (math101_id, math_dept_id, 'MATH101', 'Calculus I', 4, 'Basic Calc'),
        (math201_id, math_dept_id, 'MATH201', 'Calculus II', 4, 'Advanced Calc')
    ]
    cursor.executemany("INSERT INTO Courses VALUES (?,?,?,?,?,?)", courses)

    # Prerequisites
    # CS201 requires CS101. CS301 requires CS201. CS2712 requires CS201.
    prereqs = [
        (str(uuid.uuid4()), cs201_id, cs101_id, 'C'),
        (str(uuid.uuid4()), cs301_id, cs201_id, 'C'),
        (str(uuid.uuid4()), cs2712_id, cs201_id, 'C')
    ]
    cursor.executemany("INSERT INTO Prerequisites (prerequisiteID, courseID, requiredCourseID, minGrade) VALUES (?,?,?,?)", prereqs)

    # Academic Term
    term_id = str(uuid.uuid4())
    term_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    term_end = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO AcademicTerms VALUES (?,?,?,?)", (term_id, 'Fall 2026', term_start, term_end))

    # Registration Window (Currently Open)
    win_id = str(uuid.uuid4())
    win_start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    win_end = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
    drop_deadline = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
    withdraw_deadline = (datetime.now() + timedelta(days=40)).strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO RegistrationWindows VALUES (?,?,?,?,?,?)", (win_id, term_id, win_start, win_end, drop_deadline, withdraw_deadline))

    # Rooms
    room1_id = str(uuid.uuid4())
    room2_id = str(uuid.uuid4())
    cursor.executemany("INSERT INTO Rooms VALUES (?,?,?,?)", [
        (room1_id, '101', 'Main Building', 30),
        (room2_id, '202', 'Science Wing', 1)  # Max capacity 1 for the full section
    ])

    # Sections
    # 4 Published, 1 Full (max=1, enrolled=1), 1 Draft -> Total 6
    sec1_id = str(uuid.uuid4()) # CS101, Published
    sec2_id = str(uuid.uuid4()) # CS201, Published
    sec3_id = str(uuid.uuid4()) # MATH101, Published
    sec4_id = str(uuid.uuid4()) # CS301, Draft
    sec5_id = str(uuid.uuid4()) # CS2712, Full (max 1)
    sec6_id = str(uuid.uuid4()) # MATH201, Published

    sections = [
        (sec1_id, cs101_id, term_id, i2_id, room1_id, 'MWF 09:00-10:00', 30, 0, 'Published'),
        (sec2_id, cs201_id, term_id, i2_id, room1_id, 'TTh 10:00-11:30', 30, 0, 'Published'),
        (sec3_id, math101_id, term_id, i1_id, room1_id, 'MWF 11:00-12:00', 30, 0, 'Published'),
        (sec4_id, cs301_id, term_id, i2_id, room1_id, 'TTh 13:00-14:30', 30, 0, 'Draft'),
        (sec5_id, cs2712_id, term_id, i2_id, room2_id, 'MWF 14:00-15:00', 1, 1, 'Full'),
        (sec6_id, math201_id, term_id, i1_id, room1_id, 'TTh 15:00-16:30', 30, 0, 'Published')
    ]
    cursor.executemany("INSERT INTO Sections VALUES (?,?,?,?,?,?,?,?,?)", sections)

    # Student Completed Courses (Mocking this via old EnrollmentRecords in a past term)
    past_term_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO AcademicTerms VALUES (?,?,?,?)", (past_term_id, 'Spring 2026', '2026-01-01', '2026-05-01'))
    
    # We need dummy sections in past term for the completed courses
    s1_cs101_sec = str(uuid.uuid4())
    s1_math101_sec = str(uuid.uuid4())
    s3_cs101_sec = str(uuid.uuid4())
    s3_cs201_sec = str(uuid.uuid4())

    dummy_sections = [
        (s1_cs101_sec, cs101_id, past_term_id, i2_id, room1_id, 'MWF 09:00', 30, 30, 'Closed'),
        (s1_math101_sec, math101_id, past_term_id, i1_id, room1_id, 'TTh 09:00', 30, 30, 'Closed'),
        (s3_cs101_sec, cs101_id, past_term_id, i2_id, room1_id, 'MWF 10:00', 30, 30, 'Closed'),
        (s3_cs201_sec, cs201_id, past_term_id, i2_id, room1_id, 'TTh 10:00', 30, 30, 'Closed')
    ]
    cursor.executemany("INSERT INTO Sections VALUES (?,?,?,?,?,?,?,?,?)", dummy_sections)

    # Student 1 completed CS101, MATH101
    # Student 3 completed CS101, CS201
    past_enrolls = [
        (str(uuid.uuid4()), s1_id, s1_cs101_sec, '2026-01-02', 'Active', 0),
        (str(uuid.uuid4()), s1_id, s1_math101_sec, '2026-01-02', 'Active', 0),
        (str(uuid.uuid4()), s3_id, s3_cs101_sec, '2026-01-02', 'Active', 0),
        (str(uuid.uuid4()), s3_id, s3_cs201_sec, '2026-01-02', 'Active', 0)
    ]
    cursor.executemany("INSERT INTO EnrollmentRecords VALUES (?,?,?,?,?,?)", past_enrolls)

    # Existing Enrollment for the Full Section (Student 2 enrolled)
    cursor.execute("INSERT INTO EnrollmentRecords VALUES (?,?,?,?,?,?)", 
                  (str(uuid.uuid4()), s2_id, sec5_id, datetime.now().strftime("%Y-%m-%d"), 'Active', 0))

    # Existing Waitlist entry to demonstrate feature (Student 1 waitlisted for the full section)
    cursor.execute("INSERT INTO Waitlist VALUES (?,?,?,?,?,?,?)",
                  (str(uuid.uuid4()), s1_id, sec5_id, 1, datetime.now().strftime("%Y-%m-%d"), None, 'Queued'))

    conn.commit()
