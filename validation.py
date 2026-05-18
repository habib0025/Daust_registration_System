from datetime import datetime
from database import DatabaseConnection

def _get_db():
    return DatabaseConnection.get_instance().cursor()

def check_registration_window_open(term_id):
    cursor = _get_db()
    cursor.execute("SELECT startDate, endDate FROM RegistrationWindows WHERE termID = ?", (term_id,))
    window = cursor.fetchone()
    if not window:
        return False, "No registration window defined for this term."
    
    now = datetime.now().strftime("%Y-%m-%d")
    if now < window['startDate'] or now > window['endDate']:
        return False, f"Registration is currently closed. The registration period runs from {window['startDate']} to {window['endDate']}."
    return True, "Window is open"

def check_prerequisites(student_id, course_id):
    cursor = _get_db()
    cursor.execute('''
        SELECT c.courseCode 
        FROM Prerequisites p
        JOIN Courses c ON p.requiredCourseID = c.courseID
        WHERE p.courseID = ?
    ''', (course_id,))
    prereqs = cursor.fetchall()
    
    if not prereqs:
        return True, "No prerequisites", []
        
    cursor.execute('''
        SELECT c.courseCode 
        FROM EnrollmentRecords e
        JOIN Sections s ON e.sectionID = s.sectionID
        JOIN Courses c ON s.courseID = c.courseID
        WHERE e.studentID = ? AND e.status = 'Active'
    ''', (student_id,))
    
    completed_rows = cursor.fetchall()
    completed = [r['courseCode'] for r in completed_rows]
    
    missing = []
    for p in prereqs:
        if p['courseCode'] not in completed:
            missing.append(p['courseCode'])
            
    if missing:
        return False, f"You have not completed the required prerequisites for this course. Missing: {', '.join(missing)}.", missing
    return True, "Prerequisites met", []

def check_schedule_conflict(student_id, section_id):
    cursor = _get_db()
    cursor.execute("SELECT timeSlot, termID FROM Sections WHERE sectionID = ?", (section_id,))
    target = cursor.fetchone()
    if not target:
        return False, "Section not found", None
        
    cursor.execute('''
        SELECT s.timeSlot, c.title
        FROM EnrollmentRecords e
        JOIN Sections s ON e.sectionID = s.sectionID
        JOIN Courses c ON s.courseID = c.courseID
        WHERE e.studentID = ? AND e.status = 'Active' AND s.termID = ?
    ''', (student_id, target['termID']))
    
    target_slot = target['timeSlot']
    for row in cursor.fetchall():
        if row['timeSlot'] == target_slot:
            return False, f"This section conflicts with {row['title']} already in your schedule at {target_slot}.", row['title']
            
    return True, "No conflict", None

def check_capacity(section_id):
    cursor = _get_db()
    cursor.execute("SELECT currentEnrolled, maxCapacity FROM Sections WHERE sectionID = ?", (section_id,))
    row = cursor.fetchone()
    if not row:
        return False, "Section not found"
        
    if row['currentEnrolled'] >= row['maxCapacity']:
        return False, "This section is full."
    return True, "Seats available"

def check_section_visibility(section_id):
    cursor = _get_db()
    cursor.execute("SELECT status FROM Sections WHERE sectionID = ?", (section_id,))
    row = cursor.fetchone()
    if not row or row['status'] != 'Published':
        return False, "Section is not visible or published."
    return True, "Section is visible"

def run_full_validation(student_id, section_id):
    cursor = _get_db()
    cursor.execute("SELECT termID, courseID FROM Sections WHERE sectionID = ?", (section_id,))
    sec_info = cursor.fetchone()
    if not sec_info:
        return False, "Section not found", "not_found"
        
    term_id = sec_info['termID']
    course_id = sec_info['courseID']

    valid, msg = check_section_visibility(section_id)
    if not valid: return False, msg, 'visibility'

    valid, msg = check_registration_window_open(term_id)
    if not valid: return False, msg, 'window'

    valid, msg, _ = check_prerequisites(student_id, course_id)
    if not valid: return False, msg, 'prerequisite'

    valid, msg, _ = check_schedule_conflict(student_id, section_id)
    if not valid: return False, msg, 'conflict'

    valid, msg = check_capacity(section_id)
    if not valid: return False, msg, 'capacity'

    return True, "Validation successful", "success"
