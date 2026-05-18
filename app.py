import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from functools import wraps
from datetime import datetime

from database import DatabaseConnection
import seed_data
import validation

# ==========================================
# PythonAnywhere WSGI Configuration info:
# ==========================================
# To run this on PythonAnywhere, configure your WSGI script (typically something like 
# /var/www/yourusername_pythonanywhere_com_wsgi.py) to import the app:
#
# import sys
# path = '/home/yourusername/course_registration'
# if path not in sys.path:
#     sys.path.append(path)
# from app import app as application
# ==========================================

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_daust_prototype_only'

def init_db():
    # Automatically initialize and seed DB if missing
    conn = DatabaseConnection.get_instance()
    seed_data.seed_database(conn)

def get_db():
    return DatabaseConnection.get_instance().cursor()

# ------------------------------------------
# Authentication Decorators
# ------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] != role:
                flash(f"Unauthorized access. You must be a {role} to view this page.", "error")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ------------------------------------------
# Main Routes
# ------------------------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        if session['role'] == 'Administrator':
            return redirect(url_for('admin_dashboard'))
        elif session['role'] == 'Student':
            return redirect(url_for('student_dashboard'))
        else:
            return redirect(url_for('login'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor = get_db()
        cursor.execute("SELECT * FROM Users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['userID']
            session['role'] = user['role']
            session['name'] = user['name']
            
            flash("Successfully logged in.", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password.", "error")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# ------------------------------------------
# Student Routes
# ------------------------------------------
@app.route('/student/dashboard')
@login_required
@role_required('Student')
def student_dashboard():
    cursor = get_db()
    cursor.execute("SELECT major, completedCredits, eligibilityStatus FROM Students WHERE userID = ?", (session['user_id'],))
    student_info = cursor.fetchone()
    
    # Get active enrollments
    cursor.execute("SELECT COUNT(*) as count FROM EnrollmentRecords WHERE studentID = ? AND status='Active'", (session['user_id'],))
    active_credits = cursor.fetchone()['count'] * 3 # Assuming 3 credits per course for simple display

    return render_template('student/dashboard.html', student=student_info, active_credits=active_credits)

@app.route('/student/search')
@login_required
@role_required('Student')
def student_search():
    cursor = get_db()
    
    # Query only Published sections
    cursor.execute('''
        SELECT s.sectionID, c.courseCode, c.title, c.credits, s.timeSlot, r.roomNumber, u.name as instructorName, s.currentEnrolled, s.maxCapacity, s.status, d.deptName
        FROM Sections s
        JOIN Courses c ON s.courseID = c.courseID
        JOIN Departments d ON c.deptID = d.deptID
        JOIN Instructors i ON s.instructorID = i.userID
        JOIN Users u ON i.userID = u.userID
        JOIN Rooms r ON s.roomID = r.roomID
        WHERE s.status IN ('Published', 'Full')
    ''')
    sections = cursor.fetchall()
    
    return render_template('student/search.html', sections=sections)

@app.route('/student/schedule')
@login_required
@role_required('Student')
def student_schedule():
    cursor = get_db()
    cursor.execute('''
        SELECT e.enrollmentID, s.sectionID, c.courseCode, c.title, s.timeSlot, r.roomNumber, u.name as instructorName, e.status
        FROM EnrollmentRecords e
        JOIN Sections s ON e.sectionID = s.sectionID
        JOIN Courses c ON s.courseID = c.courseID
        JOIN Instructors i ON s.instructorID = i.userID
        JOIN Users u ON i.userID = u.userID
        JOIN Rooms r ON s.roomID = r.roomID
        WHERE e.studentID = ? AND (e.status = 'Active' OR e.status = 'Dropped')
    ''', (session['user_id'],))
    enrollments = cursor.fetchall()
    
    return render_template('student/schedule.html', enrollments=enrollments)

@app.route('/student/register/<section_id>', methods=['GET'])
@login_required
@role_required('Student')
def student_register_confirm(section_id):
    student_id = session['user_id']
    cursor = get_db()
    
    # Get section details
    cursor.execute('''
        SELECT s.sectionID, c.courseCode, c.title, s.timeSlot, s.currentEnrolled, s.maxCapacity, s.termID, s.courseID
        FROM Sections s
        JOIN Courses c ON s.courseID = c.courseID
        WHERE s.sectionID = ?
    ''', (section_id,))
    section = cursor.fetchone()
    
    if not section:
        flash("Section not found.", "error")
        return redirect(url_for('student_search'))

    # Run individual validation checks to display in UI for demo purposes
    val_visibility = validation.check_section_visibility(section_id)
    val_window = validation.check_registration_window_open(section['termID'])
    val_prereq = validation.check_prerequisites(student_id, section['courseID'])
    val_conflict = validation.check_schedule_conflict(student_id, section_id)
    val_capacity = validation.check_capacity(section_id)

    # Check if already enrolled
    cursor.execute("SELECT status FROM EnrollmentRecords WHERE studentID = ? AND sectionID = ?", (student_id, section_id))
    existing = cursor.fetchone()
    already_enrolled = (existing and existing['status'] == 'Active')

    results = {
        'visibility': val_visibility,
        'window': val_window,
        'prereq': val_prereq,
        'conflict': val_conflict,
        'capacity': val_capacity,
        'already_enrolled': already_enrolled
    }

    return render_template('student/register_confirm.html', section=section, results=results)

@app.route('/student/register/<section_id>', methods=['POST'])
@login_required
@role_required('Student')
def student_register_action(section_id):
    student_id = session['user_id']
    
    cursor = get_db()
    cursor.execute("SELECT status FROM EnrollmentRecords WHERE studentID = ? AND sectionID = ?", (student_id, section_id))
    existing = cursor.fetchone()
    if existing and existing['status'] == 'Active':
        flash("You are already enrolled in this section.", "error")
        return redirect(url_for('student_schedule'))

    valid, msg, fail_type = validation.run_full_validation(student_id, section_id)
    
    if not valid:
        if fail_type == 'capacity':
            # Ask if they want to waitlist, message in UI logic handles this by showing the form in register_confirm
            flash("This section is full. You can join the waitlist from the previous page.", "warning")
            return redirect(url_for('student_register_confirm', section_id=section_id))
        else:
            flash(msg, "error")
            return redirect(url_for('student_register_confirm', section_id=section_id))

    # All checks passed, perform registration
    import uuid
    conn = DatabaseConnection.get_instance()
    try:
        cursor.execute("UPDATE Sections SET currentEnrolled = currentEnrolled + 1 WHERE sectionID = ?", (section_id,))
        cursor.execute("INSERT INTO EnrollmentRecords (enrollmentID, studentID, sectionID, enrollmentDate, status, isOverride) VALUES (?, ?, ?, ?, 'Active', 0)",
                      (str(uuid.uuid4()), student_id, section_id, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        
        # Get course title for success message
        cursor.execute("SELECT c.title FROM Sections s JOIN Courses c ON s.courseID = c.courseID WHERE s.sectionID = ?", (section_id,))
        title = cursor.fetchone()['title']
        
        flash(f"Successfully registered for {title}.", "success")
        return redirect(url_for('student_schedule'))
    except Exception as e:
        conn.rollback()
        flash(f"Database error occurred: {str(e)}", "error")
        return redirect(url_for('student_search'))

@app.route('/student/waitlist/<section_id>', methods=['POST'])
@login_required
@role_required('Student')
def student_waitlist(section_id):
    student_id = session['user_id']
    cursor = get_db()
    
    # Check if already waitlisted
    cursor.execute("SELECT * FROM Waitlist WHERE studentID=? AND sectionID=?", (student_id, section_id))
    if cursor.fetchone():
        flash("You are already on the waitlist for this section.", "warning")
        return redirect(url_for('student_search'))

    # Calculate queue position
    cursor.execute("SELECT MAX(queuePosition) as maxPos FROM Waitlist WHERE sectionID=?", (section_id,))
    res = cursor.fetchone()
    next_pos = (res['maxPos'] or 0) + 1

    import uuid
    conn = DatabaseConnection.get_instance()
    try:
        cursor.execute("INSERT INTO Waitlist (waitlistID, studentID, sectionID, queuePosition, requestDate, status) VALUES (?,?,?,?,?,?)",
                      (str(uuid.uuid4()), student_id, section_id, next_pos, datetime.now().strftime("%Y-%m-%d"), 'Queued'))
        conn.commit()
        flash(f"Successfully joined waitlist. Your position is: {next_pos}.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Database error: {str(e)}", "error")
        
    return redirect(url_for('student_schedule'))

@app.route('/student/drop/<enrollment_id>', methods=['POST'])
@login_required
@role_required('Student')
def student_drop(enrollment_id):
    student_id = session['user_id']
    cursor = get_db()
    
    cursor.execute("SELECT sectionID, status FROM EnrollmentRecords WHERE enrollmentID=? AND studentID=?", (enrollment_id, student_id))
    record = cursor.fetchone()
    
    if not record or record['status'] != 'Active':
        flash("Invalid enrollment record.", "error")
        return redirect(url_for('student_schedule'))
        
    conn = DatabaseConnection.get_instance()
    try:
        cursor.execute("UPDATE EnrollmentRecords SET status='Dropped' WHERE enrollmentID=?", (enrollment_id,))
        cursor.execute("UPDATE Sections SET currentEnrolled = currentEnrolled - 1 WHERE sectionID=?", (record['sectionID'],))
        conn.commit()
        flash("Successfully dropped the course.", "success")
    except Exception as e:
        conn.rollback()
        flash("Error dropping course.", "error")
        
    return redirect(url_for('student_schedule'))

# ------------------------------------------
# Administrator Routes
# ------------------------------------------
@app.route('/admin/dashboard')
@login_required
@role_required('Administrator')
def admin_dashboard():
    cursor = get_db()
    
    # Simple aggregates
    cursor.execute("SELECT COUNT(*) as cnt FROM Students")
    student_count = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM Sections")
    section_count = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM EnrollmentRecords WHERE status='Active' OR status='Override-Active'")
    enr_count = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM Waitlist")
    waitlist_count = cursor.fetchone()['cnt']
    
    stats = {
        'students': student_count,
        'sections': section_count,
        'enrollments': enr_count,
        'waitlists': waitlist_count
    }
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/catalog', methods=['GET', 'POST'])
@login_required
@role_required('Administrator')
def admin_catalog():
    cursor = get_db()
    if request.method == 'POST':
        section_id = request.form.get('section_id')
        new_status = request.form.get('new_status')
        if section_id and new_status:
            conn = DatabaseConnection.get_instance()
            cursor.execute("UPDATE Sections SET status = ? WHERE sectionID = ?", (new_status, section_id))
            conn.commit()
            flash(f"Section status updated to {new_status}.", "success")
        return redirect(url_for('admin_catalog'))
        
    cursor.execute('''
        SELECT s.sectionID, c.courseCode, c.title, s.timeSlot, r.roomNumber, u.name as instructorName, s.currentEnrolled, s.maxCapacity, s.status
        FROM Sections s
        JOIN Courses c ON s.courseID = c.courseID
        JOIN Instructors i ON s.instructorID = i.userID
        JOIN Users u ON i.userID = u.userID
        JOIN Rooms r ON s.roomID = r.roomID
    ''')
    sections = cursor.fetchall()
    return render_template('admin/catalog.html', sections=sections)

@app.route('/admin/window', methods=['GET', 'POST'])
@login_required
@role_required('Administrator')
def admin_window():
    cursor = get_db()
    
    if request.method == 'POST':
        window_id = request.form.get('window_id')
        start = request.form.get('startDate')
        end = request.form.get('endDate')
        drop = request.form.get('dropDeadline')
        withd = request.form.get('withdrawDeadline')
        
        conn = DatabaseConnection.get_instance()
        cursor.execute('''
            UPDATE RegistrationWindows 
            SET startDate=?, endDate=?, dropDeadline=?, withdrawDeadline=?
            WHERE windowID=?
        ''', (start, end, drop, withd, window_id))
        conn.commit()
        flash("Registration window updated successfully.", "success")
        return redirect(url_for('admin_window'))
        
    cursor.execute('''
        SELECT rw.*, t.name as termName 
        FROM RegistrationWindows rw
        JOIN AcademicTerms t ON rw.termID = t.termID
        LIMIT 1
    ''')
    window = cursor.fetchone()
    return render_template('admin/window.html', window=window)

@app.route('/admin/roster/<section_id>')
@login_required
@role_required('Administrator')
def admin_roster(section_id):
    cursor = get_db()
    cursor.execute('''
        SELECT s.courseCode, c.title, u.name as instructorName, sec.status, sec.currentEnrolled, sec.maxCapacity
        FROM Sections sec
        JOIN Courses s ON sec.courseID = s.courseID
        JOIN Instructors i ON sec.instructorID = i.userID
        JOIN Users u ON i.userID = u.userID
        WHERE sec.sectionID = ?
    ''', (section_id,))
    section = cursor.fetchone()
    
    cursor.execute('''
        SELECT u.name, u.email, st.major, e.enrollmentDate, e.status
        FROM EnrollmentRecords e
        JOIN Students st ON e.studentID = st.userID
        JOIN Users u ON st.userID = u.userID
        WHERE e.sectionID = ?
    ''', (section_id,))
    roster = cursor.fetchall()
    
    return render_template('admin/roster.html', section=section, roster=roster)

@app.route('/admin/override', methods=['GET', 'POST'])
@login_required
@role_required('Administrator')
def admin_override():
    if request.method == 'POST':
        student_email = request.form.get('student_email')
        course_code = request.form.get('course_code')
        
        cursor = get_db()
        cursor.execute("SELECT userID FROM Users WHERE email = ? AND role = 'Student'", (student_email,))
        student = cursor.fetchone()
        
        if not student:
            flash("Student not found.", "error")
            return redirect(url_for('admin_override'))
            
        cursor.execute('''
            SELECT s.sectionID, s.courseID 
            FROM Sections s 
            JOIN Courses c ON s.courseID = c.courseID 
            WHERE c.courseCode = ?
        ''', (course_code,))
        section = cursor.fetchone()
        
        if not section:
            flash("Section not found.", "error")
            return redirect(url_for('admin_override'))
            
        # Check if already enrolled
        cursor.execute("SELECT status FROM EnrollmentRecords WHERE studentID = ? AND sectionID = ?", (student['userID'], section['sectionID']))
        enr = cursor.fetchone()
        if enr and (enr['status'] == 'Active' or enr['status'] == 'Override-Active'):
            flash("Student is already enrolled in this section.", "warning")
            return redirect(url_for('admin_override'))
            
        # Force Enroll
        import uuid
        conn = DatabaseConnection.get_instance()
        try:
            cursor.execute("UPDATE Sections SET currentEnrolled = currentEnrolled + 1 WHERE sectionID = ?", (section['sectionID'],))
            cursor.execute('''
                INSERT INTO EnrollmentRecords (enrollmentID, studentID, sectionID, enrollmentDate, status, isOverride) 
                VALUES (?, ?, ?, ?, 'Override-Active', 1)
            ''', (str(uuid.uuid4()), student['userID'], section['sectionID'], datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            flash(f"Override successful. Forced enrollment for {student_email} into {course_code}.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Database error during override: {str(e)}", "error")
            
        return redirect(url_for('admin_override'))
        
    return render_template('admin/override.html')

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=False)
