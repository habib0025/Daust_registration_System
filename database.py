import sqlite3
import os

class DatabaseConnection:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            # We are ensuring that the connect happens in the project root directory
            # by joining the path relative to this file
            db_path = os.path.join(os.path.dirname(__file__), 'registration.db')
            cls._instance = sqlite3.connect(db_path, check_same_thread=False)
            cls._instance.row_factory = sqlite3.Row
            cls._initialize_schema(cls._instance)
        return cls._instance

    @classmethod
    def _initialize_schema(cls, conn):
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Users
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            userID TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Student', 'Instructor', 'Administrator'))
        )
        ''')
        
        # Students
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Students (
            userID TEXT PRIMARY KEY,
            major TEXT NOT NULL,
            eligibilityStatus TEXT NOT NULL DEFAULT 'Eligible',
            completedCredits INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (userID) REFERENCES Users(userID)
        )
        ''')
        
        # Instructors
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Instructors (
            userID TEXT PRIMARY KEY,
            departmentID TEXT NOT NULL,
            officeLocation TEXT,
            FOREIGN KEY (userID) REFERENCES Users(userID)
        )
        ''')
        
        # Administrators
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Administrators (
            userID TEXT PRIMARY KEY,
            adminLevel TEXT NOT NULL DEFAULT 'Standard',
            FOREIGN KEY (userID) REFERENCES Users(userID)
        )
        ''')
        
        # Departments
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Departments (
            deptID TEXT PRIMARY KEY,
            deptCode TEXT NOT NULL UNIQUE,
            deptName TEXT NOT NULL
        )
        ''')
        
        # AcademicTerms
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS AcademicTerms (
            termID TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            startDate TEXT NOT NULL,
            endDate TEXT NOT NULL
        )
        ''')
        
        # RegistrationWindows
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS RegistrationWindows (
            windowID TEXT PRIMARY KEY,
            termID TEXT NOT NULL UNIQUE,
            startDate TEXT NOT NULL,
            endDate TEXT NOT NULL,
            dropDeadline TEXT NOT NULL,
            withdrawDeadline TEXT NOT NULL,
            FOREIGN KEY (termID) REFERENCES AcademicTerms(termID)
        )
        ''')
        
        # Courses
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Courses (
            courseID TEXT PRIMARY KEY,
            deptID TEXT NOT NULL,
            courseCode TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            credits INTEGER NOT NULL,
            description TEXT,
            FOREIGN KEY (deptID) REFERENCES Departments(deptID)
        )
        ''')
        
        # Prerequisites
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Prerequisites (
            prerequisiteID TEXT PRIMARY KEY,
            courseID TEXT NOT NULL,
            requiredCourseID TEXT NOT NULL,
            minGrade TEXT NOT NULL DEFAULT 'D',
            UNIQUE(courseID, requiredCourseID),
            FOREIGN KEY (courseID) REFERENCES Courses(courseID),
            FOREIGN KEY (requiredCourseID) REFERENCES Courses(courseID)
        )
        ''')
        
        # Rooms
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Rooms (
            roomID TEXT PRIMARY KEY,
            roomNumber TEXT NOT NULL,
            building TEXT NOT NULL,
            maxSeats INTEGER NOT NULL
        )
        ''')
        
        # Sections
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Sections (
            sectionID TEXT PRIMARY KEY,
            courseID TEXT NOT NULL,
            termID TEXT NOT NULL,
            instructorID TEXT NOT NULL,
            roomID TEXT NOT NULL,
            timeSlot TEXT NOT NULL,
            maxCapacity INTEGER NOT NULL,
            currentEnrolled INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft','Published','Full','Closed','Cancelled')),
            FOREIGN KEY (courseID) REFERENCES Courses(courseID),
            FOREIGN KEY (termID) REFERENCES AcademicTerms(termID),
            FOREIGN KEY (instructorID) REFERENCES Instructors(userID),
            FOREIGN KEY (roomID) REFERENCES Rooms(roomID)
        )
        ''')
        
        # EnrollmentRecords
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS EnrollmentRecords (
            enrollmentID TEXT PRIMARY KEY,
            studentID TEXT NOT NULL,
            sectionID TEXT NOT NULL,
            enrollmentDate TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Active','Dropped','Withdrawn','Override-Active')),
            isOverride INTEGER NOT NULL DEFAULT 0,
            UNIQUE(studentID, sectionID),
            FOREIGN KEY (studentID) REFERENCES Students(userID),
            FOREIGN KEY (sectionID) REFERENCES Sections(sectionID)
        )
        ''')
        
        # Waitlist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Waitlist (
            waitlistID TEXT PRIMARY KEY,
            studentID TEXT NOT NULL,
            sectionID TEXT NOT NULL,
            queuePosition INTEGER NOT NULL,
            requestDate TEXT NOT NULL,
            expiryDate TEXT,
            status TEXT NOT NULL DEFAULT 'Queued' CHECK(status IN ('Queued','Notified','Registered','Expired')),
            UNIQUE(studentID, sectionID),
            UNIQUE(sectionID, queuePosition),
            FOREIGN KEY (studentID) REFERENCES Students(userID),
            FOREIGN KEY (sectionID) REFERENCES Sections(sectionID)
        )
        ''')

        conn.commit()
