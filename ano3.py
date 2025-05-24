import streamlit as st
import nltk
import spacy
nltk.download('stopwords')
spacy.load('en_core_web_sm')

import pandas as pd
import io
import time, datetime
from pyresparser import ResumeParser
# from resume_parser import resumeparse
from streamlit_tags import st_tags
from PIL import Image
import pymysql
import mysql.connector
# import plotly.express as px
# from plotly import optional_imports
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# import os
from fpdf import FPDF
import hashlib
import random
import string
from streamlit_option_menu import option_menu
from streamlit_navigation_bar import st_navbar

# Function to generate a random meeting link
def generate_jitsi_link():
    meeting_code = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return f"https://meet.jit.si/{meeting_code}"

def get_meeting_link():
    candidate_id = st.session_state.get("candidate_id", None)

    if not candidate_id:
        return []

    cursor.execute("""
        SELECT interview_date, interview_time, jitsi_link 
        FROM interview_schedule
        WHERE candidate_id = %s AND interview_date = CURDATE()
    """, (candidate_id,))
    
    return cursor.fetchall()

def com_get_meeting_link():
    cursor.execute("""
        SELECT candidate_id, interview_date, interview_time, jitsi_link 
        FROM interview_schedule
        WHERE interview_date=CURDATE()
    """)
    result=cursor.fetchall()
    if result:
        for id, date, time, link in result:
            st.write(f"*candidate id:* {id} 📅 *Date:* {date} 🕒 *Time:* {time}")
            st.markdown(f"🔗 *[Join Jitsi Meeting]({link})*")
    else:
        st.info("No Interview Scheduled")

def view_interview_schedule():
    st.subheader("Your Scheduled Interviews")

    if "candidate_id" not in st.session_state:
        st.warning("You must be logged in to view interviews.")
        return

    if st.button("View Interview Link"):
        interviews = get_meeting_link()

        if interviews:
            for date, time, link in interviews:
                st.write(f"📅 *Date:* {date} 🕒 *Time:* {time}")
                # st.markdown(f"🔗 *[Join Jitsi Meeting]({link})*")
                st.markdown(
                    f'<iframe src="{link}" width="800" height="600" allow="camera; microphone; fullscreen" style="border:0;"></iframe>',
                    unsafe_allow_html=True
                )
                # st.markdown(f'<iframe src="https://meet.jit.si/{link}" width="800" height="600" allow="camera; microphone; fullscreen" style="border:0;"></iframe>', unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No interviews scheduled yet.")

def schedule_interview():
    st.subheader("📅 Schedule an Interview")
    today = datetime.date.today()

    company_id = st.session_state.company_user
    company_name = st.session_state.get("company_name", "Your Company")

    st.markdown(f"**Company:** {company_name} (ID: {company_id})")

    # ✅ Fetch shortlisted candidates for this company
    cursor.execute("""
        SELECT DISTINCT u.candidate_id, u.Name
        FROM user u
        JOIN recruit_data r ON u.rid = r.rid
        WHERE u.status = 'Shortlisted' AND r.cid = %s
    """, (st.session_state.company_user,))
    candidates = cursor.fetchall()

    if not candidates:
        st.info("No shortlisted candidates available for interview.")
        return

    # Select Candidate
    candidate_dict = {f"{name} (ID: {cid})": cid for cid, name in candidates}
    selected_candidate_label = st.selectbox("Select Shortlisted Candidate", list(candidate_dict.keys()))
    candidate_id = candidate_dict[selected_candidate_label]

    # Fetch Email
    cursor.execute("SELECT email FROM user_info WHERE candidate_id = %s", (candidate_id,))
    candidate_email = cursor.fetchone()[0]
    

    # st.markdown(f"**Candidate Email:** {candidate_email}")

    # Schedule
    interview_date = st.date_input("Interview Date", min_value=today)
    interview_time = st.time_input("Interview Time")
    jitsi_link = generate_jitsi_link()

    # if st.checkbox("Confirm Interview Details"):
    if st.button("✅ Schedule Interview"):
            cursor.execute("""
                INSERT INTO interview_schedule (company_id, candidate_id, interview_date, interview_time, jitsi_link)
                VALUES (%s, %s, %s, %s, %s)
            """, (company_id, candidate_id, interview_date, interview_time, jitsi_link))
            connection.commit()

            subject = f"{company_name} - Virtual Interview Invitation"
            message = f"""Dear Candidate,

You have been shortlisted for the 1st round interview with {company_name}.

📅 Date: {interview_date}
🕒 Time: {interview_time}
🔗 Please join via your Smart Hiring System profile.

Regards,  
{company_name} Recruitment Team"""

            send_email(candidate_email, subject, message)
            st.success("✅ Interview scheduled successfully.")
            st.markdown(f"🔗 **[Join Jitsi Meeting]({jitsi_link})**")

def generate_pdf(name, email):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Header
    pdf.cell(200, 10, txt="Smart Hiring System", ln=True, align='C')
    pdf.ln(5)
    pdf.cell(200, 10, txt="Application Reference Letter", ln=True, align='C')
    pdf.ln(10)

    # Candidate Details
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 10, txt=(
        f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"Dear {name},\n\n"
        f"Thank you for applying to our Smart Hiring System.\n\n"
        f"Your application has been successfully submitted and is currently under review by our recruitment team. Please find your application reference details below for your records:\n\n"
        # f"Application ID: {application_id}\n"
        f"Candidate Name: {name}\n"
        f"Email: {email}\n"
        f"We value the time and effort you have invested in applying for this opportunity. Our team will carefully review your application to assess its alignment with the role's requirements. If shortlisted, you will be contacted shortly with the next steps in the selection process.\n"
        "We appreciate your interest in contributing to our team and wish you all the best in your career endeavors.\n\n"
        "Best regards,\n"
        "Smart Hiring System Team"
    ))

    pdf_output = pdf.output(dest='S').encode('latin1')  # Return binary data
    return pdf_output

def get_pdf_from_db(email):
    query = "SELECT Application_PDF FROM user WHERE Email_ID = %s"
    cursor.execute(query, (email,))
    result = cursor.fetchone()
    if result:
        return result[0]  # Binary PDF data
    else:
        return None


def send_email(to_email, subject, message):
    try:
        # Define the sender's email and password
        sender_email = "smarthiringsystem2024@gmail.com"    # "20hritikdey@gmail.com"
        sender_password = "ngpx aerc otlw vxxj"  # Store this securely in practice "ewfb zfri yufy mzfv"
        
        # Setup the MIME
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Add body to email
        msg.attach(MIMEText(message, 'plain'))

        # Create server object with Gmail's SMTP server details
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Enable security
        server.login(sender_email, sender_password)

        # Send email
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)

        # Close the server connection
        server.quit()

    except Exception as e:
        print(f'Error sending email: {e}')

# connection = pymysql.connect(host='localhost', user='root', password='')
connection = mysql.connector.connect(host='sql12.freesqldatabase.com', user='sql12780981', password='DGiXZEmDVf',database='sql12780981')
cursor = connection.cursor()

# def insert_data(candidate_id, name, email, timestamp, exp, skills,count,Resume,Application_pdf,rid):
#     DB_table_name = 'user'
#     insert_sql = "insert into " + DB_table_name + """
#     values (0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
#     rec_values = (candidate_id, name, email, timestamp, str(exp), skills,count,Resume,Application_pdf,rid)
#     cursor.execute(insert_sql, rec_values)
#     connection.commit()

def insert_data(candidate_id, name, email, timestamp, exp, skills, count, Resume, Application_pdf, rid):
    DB_table_name = 'user'
    insert_sql = f"""
        INSERT INTO {DB_table_name} 
        (ID, candidate_id, Name, Email_ID, Timestamp, Experience, Actual_skills, Count, Resume, Application_PDF, rid, status)
        VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rec_values = (candidate_id, name, email, timestamp, str(exp), skills, count, Resume, Application_pdf, rid, 'Applied')
    cursor.execute(insert_sql, rec_values)
    connection.commit()


def insert_com_data(name, password):
    DB_table_name = 'com_data'
    insert_sql = "insert into " + DB_table_name + """
    (Name, password) values (%s,%s)"""
    rec_values = (name, password)
    cursor.execute(insert_sql, rec_values)
    connection.commit()
    return cursor.lastrowid  # Return the auto-generated cid


def insert_recruit_data(cid,domain,reco_skill,timestamp,experience,deadline,description):
    DB_table_name = 'recruit_data'
    insert_sql = "insert into " + DB_table_name + """
    values (0,%s,%s,%s,%s,%s,%s,%s)"""
    rec_values = (cid,domain,reco_skill,timestamp,experience,deadline,description)
    cursor.execute(insert_sql, rec_values)
    connection.commit()

def fetch_previous_recruitments(cid):
    query = "SELECT rid,domain,reco_skill,timestamp,experience,deadline,description FROM recruit_data WHERE cid = %s"
    cursor.execute(query, (cid,))
    return cursor.fetchall()

def update_data(email, rid, timestamp, exp, skills, resume, application_pdf):
    DB_table_name = 'user'
    update_sql = f"""
    UPDATE {DB_table_name} 
    SET timestamp = %s, experience = %s, actual_skills = %s, resume = %s, Application_PDF = %s 
    WHERE email_id = %s AND rid = %s
    """
    cursor.execute(update_sql, (timestamp, exp, skills, resume, application_pdf, email, rid))
    connection.commit()

def application_data(user_id, job_id):
    cursor.execute("""INSERT INTO applications (user_id, job_id, application_time) VALUES (%s, %s, %s)""", (user_id, job_id, datetime.now()))
    connection.commit()

def load_job_posts_from_db():
    cursor = connection.cursor(dictionary=True)
    # cursor.execute("SELECT jp.*, cd.Name AS company_name FROM recruit_data jp JOIN com_data cd ON jp.cid = cd.cid ORDER BY jp.timestamp DESC")
    cursor.execute("SELECT * FROM recruit_data WHERE deadline >= CURDATE() ORDER BY timestamp DESC")
    jobs = cursor.fetchall()
    cursor.close()
    return jobs

def delete_expired_jobs():
    cursor.execute("DELETE FROM recruit_data WHERE deadline < CURDATE()")
    connection.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Sign Up function
def signup(name, email, password):
    hashed_pwd = hash_password(password)
    # Check if user already exists
    cursor.execute("SELECT * FROM user_info WHERE email = %s", (email,))
    result = cursor.fetchone()
    if result:
        return "⚠ Email already registered. Try logging in."
    else:
        # Insert new user
        insert_sql = "INSERT INTO user_info (name, email, password) VALUES (%s, %s, %s)"
        cursor.execute(insert_sql, (name, email, hashed_pwd))
        connection.commit()
        return cursor.lastrowid

# Sign In function
def signin(candidate_id, email, password):
    hashed_pwd = hash_password(password)
    cursor.execute("SELECT * FROM user_info WHERE candidate_id = %s AND email=%s AND password = %s", (candidate_id, email, hashed_pwd))
    result = cursor.fetchone()
    if result:
        st.session_state.logged_in = True
        st.session_state.candidate_id = result[0]
        st.session_state.candidate_name = result[1]
        return result
    else:
        st.error("Invalid username or password.")
        return None
    
def reset_password(email, new_password):
    cursor.execute("SELECT * FROM user_info WHERE email = %s", (email,))
    result = cursor.fetchone()
    if result:
        cursor.execute("UPDATE user_info SET password = %s WHERE email = %s", (new_password, email))
        connection.commit()
        st.success("Password reset successful! You can now sign in.")
        st.session_state.reset_mode = False
    else:
        st.error("Username not found!")


def company_signin(cid, password):
    cursor.execute("SELECT * FROM com_data WHERE cid = %s AND password = %s", (cid, password))
    result = cursor.fetchone()
    if result:
        st.session_state.company_logged_in = True
        st.session_state.company_id = result[0]
        st.session_state.company_name = result[1]
        return result
    else:
        st.error("⚠ Incorrect Company ID or Password.")
        return None

def run():
    # Ensure reset_mode is initialized
    if "reset_mode" not in st.session_state:
        st.session_state.reset_mode = False

    st.sidebar.markdown("### **Choose User**")
    activities = ["User 🧑🏻‍💻", "Admin 👤","Company 🏢"]
    choice = st.sidebar.selectbox("**Choose among the given options:**", activities)

    # Create the DB
    # db_sql = """CREATE DATABASE IF NOT EXISTS SRA3;"""
    # cursor.execute(db_sql)
    # connection.select_db("sra4")

    # Create table
    DB_table_name3 = 'user_info'
    table_sql3 = "CREATE TABLE IF NOT EXISTS " + DB_table_name3 + """
            (candidate_id INT NOT NULL AUTO_INCREMENT,
            name varchar(100) NOT NULL,
            email varchar(100) NOT NULL,
            password varchar(100) NOT NULL,
            PRIMARY KEY (candidate_id)) AUTO_INCREMENT=1001;
            """
    cursor.execute(table_sql3)

    DB_table_name1 = 'com_data'
    table_sql1 = "CREATE TABLE IF NOT EXISTS " + DB_table_name1 + """
                (cid INT NOT NULL AUTO_INCREMENT,
                Name varchar(100) NOT NULL UNIQUE,
                password VARCHAR(50) NOT NULL,
                PRIMARY KEY (cid)) AUTO_INCREMENT=101;
                """
    cursor.execute(table_sql1)

    DB_table_name2 = 'recruit_data'
    table_sql2 = "CREATE TABLE IF NOT EXISTS " + DB_table_name2 + """
            (rid INT NOT NULL AUTO_INCREMENT,
            cid INT NOT NULL,
            domain varchar(100) NOT NULL,
            reco_skill varchar(100) NOT NULL,
            timestamp varchar(100) NOT NULL,
            experience varchar(100) NOT NULL,
            deadline date NOT NULL,
            description varchar(750) NOT NULL,
            PRIMARY KEY (rid),
            FOREIGN KEY(cid) REFERENCES com_data(cid) ON DELETE CASCADE)AUTO_INCREMENT=5001;
            """
    cursor.execute(table_sql2)  
    connection.commit()

    DB_table_name = 'user'
    table_sql = "CREATE TABLE IF NOT EXISTS " + DB_table_name + """
                    (ID INT NOT NULL AUTO_INCREMENT,
                     candidate_id INT NOT NULL,
                     Name varchar(100) NOT NULL,
                     Email_ID VARCHAR(50) NOT NULL,
                     Timestamp VARCHAR(50) NOT NULL,
                     Experience VARCHAR(10) NOT NULL,
                     Actual_skills VARCHAR(700) NOT NULL,
                     Count INT(5) NOT NULL,
                     Resume LONGBLOB NOT NULL,
                     Application_PDF LONGBLOB NOT NULL,
                     rid INT NOT NULL,
                     status VARCHAR(20) DEFAULT 'Applied',
                     PRIMARY KEY (ID),
                     FOREIGN KEY(candidate_id) REFERENCES user_info(candidate_id) ON DELETE CASCADE);
                    """
    cursor.execute(table_sql)
    # ALTER TABLE user ADD COLUMN status VARCHAR(20) DEFAULT 'Applied';


    DB_table_name4 = 'interview_schedule'
    table_sql4 = "CREATE TABLE IF NOT EXISTS " + DB_table_name4 + """
                (
                    interview_id INT AUTO_INCREMENT PRIMARY KEY,
                    company_id INT NOT NULL,
                    candidate_id INT NOT NULL,
                    interview_date DATE NOT NULL,
                    interview_time TIME NOT NULL,
                    jitsi_link VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'Scheduled',
                    FOREIGN KEY (company_id) REFERENCES com_data(cid) ON DELETE CASCADE,
                    FOREIGN KEY (candidate_id) REFERENCES user_info(candidate_id) ON DELETE CASCADE
                );
                """
    cursor.execute(table_sql4)


  

    if choice == 'User 🧑🏻‍💻':
            try:
                menu = ["Sign In", "Sign Up"]
                choice = st.sidebar.selectbox("Select an option", menu)

                # Sign Up Page
                if choice == "Sign Up":
                    st.subheader("Create a New Account")
                    with st.form("signup_form"):
                        name = st.text_input("Full Name")
                        email = st.text_input("Email")
                        password = st.text_input("Password", type="password")
                        if st.form_submit_button("Sign Up"):
                            cursor.execute(f"SELECT * FROM {DB_table_name3} WHERE email = %s", (email,))
                            user_exists = cursor.fetchone()
                            if user_exists:
                                st.error(f"**_A user with the name '{name}' already exists. Please use a different name or log in._**")
                            else:
                                try:
                                    message = signup(name, email, password)
                                    st.success(f"**_:blue[Your profile is created. Your candidate ID is {message}]_**")
                                    # st.balloons()
                                except Exception as e:
                                    st.error(f"**_An unexpected error occurred: {e}_**")
                # Sign In Page
                elif choice == "Sign In":
                    # RESET PASSWORD MODE
                    if st.session_state.reset_mode:
                        st.subheader("🔁 Reset Password")
                        with st.form("reset_form"):
                            email = st.text_input("Registered Email")
                            new_password = st.text_input("New Password", type="password")
                            confirm_password = st.text_input("Confirm Password", type="password")

                            reset_btn = st.form_submit_button("Reset Password")

                            if reset_btn:
                                if new_password != confirm_password:
                                    st.error("❌ Passwords do not match.")
                                else:
                                    hashed = hash_password(new_password)
                                    reset_password(email, hashed)

                        if st.button("⬅ Back to Sign In"):
                            st.session_state.reset_mode = False
                            #st.experimental_rerun()
                        return  # ✅ Important: exit to prevent running login/signup below

                    if not st.session_state.get("logged_in", False):
                        st.subheader("Login to Your Account")
                        with st.form("signin_form"):
                            candidate_id = st.text_input("Candidate ID")
                            email = st.text_input("Email")
                            password = st.text_input("Password", type="password")
   
                            if st.form_submit_button("Sign In"):
                                    user = signin(candidate_id, email, password)
                                    if user:
                                        #st.experimental_rerun()
                                        st.rerun()
                            forgot = st.form_submit_button("Forgot Password?")
                            if forgot:
                                st.session_state.reset_mode = True
                                #st.experimental_rerun()
                                st.rerun()
                    else:
                            pages = {
                                "Profile": "🏠 Home",
                                "Home": "💼 Jobs",
                                "View Interview Schedule": "📅 Interviews",
                                "Logout": "🔐 Logout"
                            }

                            # This is the only valid argument: list of options
                            selected_page = st_navbar(list(pages.values()))

                            # Map back the selected label to internal page name
                            label_to_key = {v: k for k, v in pages.items()}
                            page = label_to_key[selected_page]

                            # Now render the content like before
                            st.title(pages[page])
                            st.success(f"Welcome back, {st.session_state['candidate_name']}! 🎉")

                            if page == "Home":
                                candidate_id = st.session_state.get("candidate_id", None)
                                if candidate_id:
                                # st.write("🏠 Welcome to the Home Page!")       
                            
                                # Job Application Section
                                    st.header("Browse Job Listings")

                                    # Fetch jobs from database
                                    # cursor.execute("SELECT * FROM recruit_data WHERE deadline >= CURDATE() ORDER BY timestamp DESC")
                                    cursor.execute("""
                                        SELECT * FROM recruit_data
                                        WHERE deadline >= CURDATE()
                                        AND rid NOT IN (
                                            SELECT rid FROM user WHERE candidate_id = %s
                                        )
                                        ORDER BY timestamp DESC
                                    """, (candidate_id,))
                                    job_posts = cursor.fetchall()

                                    if job_posts:
                                        for job in job_posts:
                                            job_id = job[0]
                                            job_title = job[2]
                                            job_exp = job[5]
                                            job_deadline = job[6]
                                            Job_desc=job[7]

                                            st.subheader(job_title)
                                            st.write(f"Experience Required: {job_exp}")
                                            st.write(f"Deadline: {job_deadline}")
                                            st.write(f"Description: {Job_desc}")

                                            pdf_file = st.file_uploader("Upload Your Resume", type=["pdf"], key=f"resume_{job_id}")
                                            post = st.button(f"Submit Resume for {job_title}", key=f"submit_{job_id}")
                                            st.markdown("---")

                                            if post:
                                                if pdf_file is not None:
                                                    resume_binary = pdf_file.read()
                                                    resume_data = ResumeParser(pdf_file).get_extracted_data()

                                                    if resume_data:
                                                        st.subheader("**Resume Analysis:**")
                                                        st.success(f"**_Congratulations {resume_data['name']} 🎉. Your Resume has been Submitted._**")
                                                        st.text(f"Name: {resume_data['name']}")
                                                        st.text(f"Email: {resume_data['email']}")
                                                        st.text(f"Experience: {resume_data['total_experience']} years")

                                                        # Generate PDF
                                                        application_pdf = generate_pdf(resume_data["name"], resume_data["email"])

                                                        # Insert application into DB
                                                        sql = "SELECT email_id FROM user WHERE email_id = %s AND rid = %s"
                                                        cursor.execute(sql, (resume_data['email'], job_id))
                                                        result = cursor.fetchone()

                                                        if result:
                                                            update_data(resume_data['email'], job_id, datetime.datetime.now(),
                                                                        str(resume_data['total_experience']), str(resume_data['skills']),
                                                                        resume_binary, application_pdf)
                                                            st.success("✅ Your application has been updated.")
                                                        else:
                                                            insert_data(candidate_id,resume_data['name'], resume_data['email'], datetime.datetime.now(),
                                                                        str(resume_data['total_experience']), str(resume_data['skills']),
                                                                        0, resume_binary, application_pdf,job_id)
                                                            st.success("✅ Your application has been submitted.")

                                                        # Allow user to download PDF
                                                        stored_pdf = get_pdf_from_db(resume_data['email'])
                                                        if stored_pdf:
                                                            st.download_button(
                                                                label="📥 Download Application Reference PDF",
                                                                data=stored_pdf,
                                                                file_name=f"Application_{resume_data['name'].replace(' ', '_')}.pdf",
                                                                mime="application/pdf"
                                                            )
                                                    else:
                                                        st.error("⚠ An unexpected error occurred while processing your resume.")
                                                else:
                                                    st.error("⚠ Please upload your resume before submitting.")
                                    else:
                                        st.write("No job posts available yet.")
                            elif page == "View Interview Schedule":
                                # st.write("Interview Link Section")
                                view_interview_schedule()
                            elif page == "Profile":
                                # st.write("👤 Profile Section")
                                st.header("👤 Your Profile")
                                candidate_id = st.session_state.get("candidate_id", None)
                                if candidate_id:
                                # # --- Fetch user basic info ---
                                    st.subheader("🪪 Basic Information")
                                    cursor.execute("SELECT name, email FROM user_info WHERE candidate_id = %s", (candidate_id,))
                                    user_data = cursor.fetchone()
                                    
                                    if user_data:
                                        st.write(f"*Name:* {user_data[0]}")
                                        st.write(f"*Email:* {user_data[1]}")
                                        st.write(f"*Candidate ID:* {candidate_id}")
                                    else:
                                        st.warning("Unable to fetch profile information.")

                                    # --- Count of Job Applications ---
                                    st.subheader("📄 Applications Summary")
                                    cursor.execute("SELECT COUNT(*) FROM user WHERE candidate_id = %s", (candidate_id,))
                                    apps_count = cursor.fetchone()[0]
                                    st.write(f"*Total Applications Submitted:* {apps_count}")

                                    # --- Interview Calls Received ---
                                    st.subheader("📞 Interview Calls")
                                    cursor.execute("SELECT COUNT(*) FROM interview_schedule WHERE candidate_id = %s", (candidate_id,))
                                    interview_count = cursor.fetchone()[0]
                                    st.write(f"*Total Interview Calls Received:* {interview_count}")

                            elif page=="Logout":
                                st.session_state.clear()
                                st.experimental_rerun()

                        # else:
                            # st.error("⚠ Incorrect email or password.")
            except Exception:
                st.error("**⚠ No job posts available yet.**")

    elif choice=='Admin 👤':
        try:
            # st.header(":blue[Welcome to Admin Side]")
            admin_user=st.text_input("**Username**")
            admin_password=st.text_input("**Password**",type='password')
            loadnow11=st.button("login",type="primary")
            #initialize session state
            if "loadnow11_state" not in st.session_state:
                st.session_state.loadnow11_state= False
            if loadnow11 or st.session_state.loadnow11_state:
                st.session_state.loadnow11_state=True
                with st.spinner(':blue[Wait for it...]'):
                    time.sleep(2)
                if admin_user=='admin' and admin_password=='admin123':
                    st.success("##### **_:blue[Welcome Admin]_**")

                    cursor.execute('''SELECT candidate_id,name,email FROM user_info''')
                    data = cursor.fetchall()
                    st.header("**User's Data**")
                    df = pd.DataFrame(data, columns=['Candidate_ID', 'Name', 'Email'])
                    st.dataframe(df)

                    cursor.execute('''SELECT candidate_id,Name,Email_ID,Timestamp,Experience,Actual_skills,rid,status FROM user''')
                    data = cursor.fetchall()
                    st.header("**User's Resume Data**")
                    df = pd.DataFrame(data, columns=['Candidate_ID', 'Name', 'Email', 'Timestamp', 'Experience', 'Actual Skills','rid','Status'])
                    # df_filtered = df.drop(columns=['Count'])
                    st.dataframe(df)

                    cursor.execute('''SELECT interview_id, company_id, candidate_id,interview_date,interview_time,status FROM interview_schedule''')
                    data1 = cursor.fetchall()
                    st.header("**Interview Details**")
                    df = pd.DataFrame(data1, columns=['interview_id', 'company_id', 'candidate_id','interview_date','interview_time','status'])
                    st.dataframe(df)

                    cursor.execute('''SELECT*FROM com_data''')
                    data1 = cursor.fetchall()
                    st.header("**Company's Data**")
                    df = pd.DataFrame(data1, columns=['CID', 'CName', 'Password'])
                    st.dataframe(df)

                    c_id=st.text_input("**Enter Company ID for Show company's Previous Posts:**")
                    loadnow1=st.button("Show Previous Posts",type="primary")
                    #initialize session state
                    if "loadnow1_state" not in st.session_state:
                        st.session_state.loadnow1_state= False
                    if loadnow1 or st.session_state.loadnow1_state:
                        st.session_state.loadnow1_state=True
                        if c_id.isdigit():
                            c_id=int(c_id)
                            cursor.execute(f"SELECT * FROM com_data WHERE cid = %s", (c_id,))
                            company_exists1 = cursor.fetchone()
                            if company_exists1:
                                st.subheader(f"Previous recruitments for {c_id}:")
                                recruitments = fetch_previous_recruitments(c_id)
                                if recruitments:
                                    # st.success(f"Previous recruitments for {c_id}:")
                                    recruit_df = pd.DataFrame(recruitments, columns=['RID', 'Domain', 'Reco_Skills', 'Timestamp', 'Experience','Deadline','Job Description'])
                                    st.dataframe(recruit_df)
                                else:
                                    
                                    st.info(f"**No previous recruitment posts for {c_id}.**")
                            else:
                                st.error("There is no such ID exists.")
                else:
                    st.error("**_:red[Wrong ID or Password is Provided]_**")
        except Exception as main_error:
            st.error(f"**⚠ An unexpected error occurred: {main_error}**")

    else:
        try:
            activities1 = ["Sign in", "Sign up"]
            choice2 = st.sidebar.selectbox("Select an option:", activities1)
        
            if choice2=='Sign up':
                name=st.text_input("**Company_name**")
                password=st.text_input("**Company_password**")
                if st.button("Create Profile", type="primary"):                 
                    cursor.execute(f"SELECT * FROM {DB_table_name1} WHERE Name = %s", (name,))
                    company_exists = cursor.fetchone()

                    if company_exists:
                        st.error(f"**_A company with the name '{name}' already exists. Please use a different name or log in._**")
                    else:
                        try:
                            new_cid = insert_com_data(name, password)
                            st.success(f"**_:blue[Your profile is created. Your company ID is {new_cid}]_**")
                            st.balloons()
                        except Exception as e:
                            st.error(f"**_An unexpected error occurred: {e}_**")

            else:                 
                if not st.session_state.get("company_logged_in", False):
                    st.subheader("Company Sign In")
                    if "company_cid" not in st.session_state:
                        st.session_state.company_user = ""
                    if "company_password" not in st.session_state:
                        st.session_state.company_password = ""

                    st.session_state.company_user = st.text_input("Company ID", value=st.session_state.company_user)
                    st.session_state.company_password = st.text_input("Password", type="password", value=st.session_state.company_password)

                    if st.button("Sign In"):
                        company = company_signin(st.session_state.company_user, st.session_state.company_password)
                        if company:
                            #st.experimental_rerun()
                            st.rerun()
                else:
                                
                                pages = {
                                "Home": "🏠 Home",
                                "Display Shortlist Candidates": "📅 Display Shortlist Candidates",
                                "Scheduled Interview": "📅 Scheduled Interview",
                                "Logout": "🔐 Logout"
                                }

                                # This is the only valid argument: list of options
                                selected_page = st_navbar(list(pages.values()))

                                # Map back the selected label to internal page name
                                label_to_key = {v: k for k, v in pages.items()}
                                page = label_to_key[selected_page]

                                # Now render the content like before
                                st.title(pages[page])
                                st.success(f"Welcome back, **{st.session_state['company_name']}** 🎉")
                                if page=="Home":

                                    activities = ["Web Development", "Python Development", "Java Development", "Data Scientist", "Full Stack Development","Android Development"]     
                                    choice1 = st.selectbox("**Choose Required Domain:**", activities)
                                    st.session_state.c1=choice1
                                    # st.write("You Selected:", choice1)
                                    st.subheader("You Selected: " + choice1)
                                    cursor.execute('''SELECT Actual_skills FROM user''')
                                    data = cursor.fetchall()
                                    cursor.execute('''SELECT Email_ID FROM user''')
                                    data2 = cursor.fetchall()
                                    if choice1=="Web Development":
                                        options = st.multiselect(
                                            "Choose the required fields",
                                            ["JavaScript", "HTML", "CSS","React","PHP","Node.js","Next.js","Express.js"],
                                            ["HTML"],
                                        )
                                        li=options
                                        l=[]
                                        for x in data:
                                            # print(x)
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                # print("list: ",lowercase_list)
                                                for i in range(len(li)):
                                                    # print(li[i].lower())
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                
                                                l.append(c)
                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
                                            # cursor.execute("UPDATE user_data11 SET Count = %s WHERE Email_ID = ?", (value, email))
                                            delete_sql = f"UPDATE {DB_table_name} SET Count = %s WHERE Email_ID = %s"
                                            cursor.execute(delete_sql, (value,email,))
                                            connection.commit()
                                        # print("You selected:", options)
                                        age = st.slider("**select required experience year?**", 0, 40, 5)
                                        st.subheader("**Experience level set to: **"+ str(age) + "** years**")
                                        job_deadline = st.date_input("Application Deadline", min_value=datetime.date.today())
                                        des=st.text_area("Description","Write here something")
                       
                                    elif choice1=="Python Development":
                                        options = st.multiselect(
                                            "Choose the required fields",
                                            ["Python", "Django", "Flask","Tkinter","CherryPy","WEB2PY","FastAPI","TensorFlow"],
                                            ["Python"],
                                        )
                                        li=options
                                        l=[]
                                        for x in data:
                                            # print(x)
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                # print("list: ",lowercase_list)
                                                for i in range(len(li)):
                                                    # print(li[i].lower())
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                l.append(c)
                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
                                            # cursor.execute("UPDATE user_data11 SET Count = ? WHERE Email_ID = ?", (value, email))
                                            delete_sql = f"UPDATE {DB_table_name} SET Count = %s WHERE Email_ID = %s"
                                            cursor.execute(delete_sql, (value,email,))
                                            connection.commit()
                                        # st.write("You selected:", options)
                                        age = st.slider("**select required experience year?**", 0, 40, 5)
                                        st.subheader("**Experience level set to: **"+ str(age) + "** years**")
                                        job_deadline = st.date_input("Application Deadline",min_value=datetime.date.today())
                                        des=st.text_area("Description","Write here something")


                        
                                    elif choice1=="Java Development":
                                        options = st.multiselect(
                                            "Choose the required fields",
                                            ["java", "JSP", "Servlet","Spring boot","JavaScript","angular"],
                                            ["java"],
                                        )
                                        li=options
                                        l=[]
                                        for x in data:
                                            # print(x)
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                # print("list: ",lowercase_list)
                                                for i in range(len(li)):
                                                    # print(li[i].lower())
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                l.append(c)
                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
                                            # cursor.execute("UPDATE user_data11 SET Count = ? WHERE Email_ID = ?", (value, email))
                                            delete_sql = f"UPDATE {DB_table_name} SET Count = %s WHERE Email_ID = %s"
                                            cursor.execute(delete_sql, (value,email,))
                                            connection.commit()
                                        # st.write("You selected:", options)
                                        age = st.slider("**select required experience year?**", 0, 40, 5)
                                        st.subheader("**Experience level set to: **"+ str(age) + "** years**")
                                        job_deadline = st.date_input("Application Deadline",min_value=datetime.date.today())
                                        des=st.text_area("Description","Write here something")
                                    
                                    elif choice1=="Data Scientist":
                                        options = st.multiselect(
                                            "Choose the required fields",
                                            ["Mechine Learning", "Python", "AI","NLP","Deep Learning","Pandas","TensorFlow","Power BI","Pytorch","Excel"],
                                            ["AI"],
                                        )
                                        li=options
                                        l=[]
                                        for x in data:
                                            # print(x)
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                # print("list: ",lowercase_list)
                                                for i in range(len(li)):
                                                    # print(li[i].lower())
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                l.append(c)

                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
                                            # cursor.execute("UPDATE user_data11 SET Count = ? WHERE Email_ID = ?", (value, email))
                                            delete_sql = f"UPDATE {DB_table_name} SET Count = %s WHERE Email_ID = %s"
                                            cursor.execute(delete_sql, (value,email,))
                                            connection.commit()
                                        # st.write("You selected:", options)
                                        age = st.slider("**select required experience year?**", 0, 40, 5)
                                        st.subheader("**Experience level set to: **"+ str(age) + "** years**")
                                        job_deadline = st.date_input("Application Deadline",min_value=datetime.date.today())
                                        des=st.text_area("Description","Write here something")

                                    elif choice1=="Full Stack Development":
                                        options = st.multiselect(
                                            "Choose the required fields",
                                            ["Python", "Java", "R", "Ruby", "Node.js", "PHP", "React", "Angular", "Express.js","C++","MongoDB","MySQL","PostgreSQL"],
                                            ["PHP"],
                                        )
                                        li=options
                                        l=[]
                                        for x in data:
                                            # print(x)
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                # print("list: ",lowercase_list)
                                                for i in range(len(li)):
                                                    # print(li[i].lower())
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                l.append(c)
                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
                                            # cursor.execute("UPDATE user_data11 SET Count = ? WHERE Email_ID = ?", (value, email))
                                            delete_sql = f"UPDATE {DB_table_name} SET Count = %s WHERE Email_ID = %s"
                                            cursor.execute(delete_sql, (value,email,))
                                            connection.commit()
                                        age = st.slider("**select required experience year?**", 0, 40, 5)
                                        st.subheader("**Experience level set to: **"+ str(age) + "** years**")
                                        job_deadline = st.date_input("Application Deadline",min_value=datetime.date.today())
                                        des=st.text_area("Description","Write here something")

                                    elif choice1=="Android Development":
                                        options = st.multiselect(
                                            "Choose the required fields",
                                            ["Java","Kotlin","Android UI","C++","Python"],
                                            ["Java"],
                                        )
                                        li=options
                                        l=[]
                                        for x in data:
                                            # print(x)
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                # print("list: ",lowercase_list)
                                                for i in range(len(li)):
                                                    # print(li[i].lower())
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                l.append(c)

                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
                                            # cursor.execute("UPDATE user_data11 SET Count = ? WHERE Email_ID = ?", (value, email))
                                            delete_sql = f"UPDATE {DB_table_name} SET Count = %s WHERE Email_ID = %s"
                                            cursor.execute(delete_sql, (value,email,))
                                            connection.commit()
                                        age = st.slider("**select required experience year?**", 0, 40, 5)
                                        st.subheader("**Experience level set to: **"+ str(age) + "** years**")
                                        job_deadline = st.date_input("Application Deadline",min_value=datetime.date.today())
                                        des=st.text_area("Description","Write here something")

                                    if "load1_state" not in st.session_state:
                                        st.session_state.load1_state = False  # For "Submit new recruitment posts"
                                    if "load12_state" not in st.session_state:
                                        st.session_state.load12_state = False  # For "View Previous Recruitment Posts"
                                    if "load120_state" not in st.session_state:
                                        st.session_state.load120_state = False

                                    # First Button: Submit New Recruitment Posts
                                    load1 = st.button('Submit new recruitment posts')

                                    if load1:
                                        st.session_state.load12_state = False
                                        st.session_state.load1_state = True  # Set flag to indicate button click
                                        # st.session_state.load12_state = False  # Ensure the other button state is reset

                                    if st.session_state.load1_state:
                                        ts = time.time()
                                        cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                                        cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                                        timestamp = str(cur_date + '_' + cur_time)

                                        insert_recruit_data(st.session_state.company_user, choice1, ', '.join(options), timestamp, age, job_deadline,des)
                                        st.success("New recruitment post submitted sucessfully")
                                        st.session_state.load1_state = False

                                    # Second Button: View Previous Recruitment Posts (Runs Independently)
                                    load12 = st.button("View Previous Recruitment Posts")

                                    if load12:
                                        st.session_state.load1_state = False
                                        st.session_state.load12_state = True  # Set flag for this button
                                        # st.session_state.load1_state = False  # Ensure the other button state is reset

                                    if st.session_state.load12_state:
                                        previous_posts = fetch_previous_recruitments(st.session_state.company_user)

                                        if previous_posts:
                                            st.header("**Previous Recruitment Posts**")
                                            df = pd.DataFrame(previous_posts, columns=['RID', 'Domain', 'Recommended Skills', 'Timestamp', 'Experience','Deadline','Job Description'])
                                            st.dataframe(df)
                                        else:
                                            st.info("No previous recruitment posts found.")
                                elif page=="Display Shortlist Candidates":
                                    st.subheader("Select a Job Posting to View Candidates")

                                    # Fetch all job postings for this company
                                    cursor.execute("SELECT rid, domain FROM recruit_data WHERE cid = %s", (st.session_state.company_user,))
                                    job_posts = cursor.fetchall()

                                    # Dropdown to select job posting
                                    # job_options = {job[0]: job[1] for job in job_posts}  # Convert to dict {rid: job_title}
                                    # selected_rid = st.selectbox("Select a Job Posting", options=job_options.keys(), format_func=lambda rid: job_options[rid])
                                    job_options = {f"{domain} (ID: {rid})": rid for rid, domain in job_posts}
                                    selected_label = st.selectbox("Select a Job Posting", options=list(job_options.keys()))
                                    selected_rid = job_options[selected_label] # Get rid from selected label

                                    # Button to show candidates for selected job posting
                                    load120 = st.button("Show Candidates for Selected Job")

                                    if load120:
                                        st.session_state.load12_state = False  # Reset previous button states
                                        st.session_state.load120_state = True  # Set flag for this button

                                    if st.session_state.get("load120_state", False):
                                        # Retrieve candidates who applied for the selected job
                                        cursor.execute(f"""
                                            SELECT candidate_id, Name, Email_ID, Experience, Actual_skills, Resume
                                            FROM user 
                                            WHERE rid = %s AND Count >= 1 AND Experience >= (SELECT experience FROM recruit_data WHERE rid = %s) 
                                            ORDER BY Count DESC
                                        """, (selected_rid, selected_rid))
                                        
                                        data10 = cursor.fetchall()

                                        # Display Candidate Data
                                        if data10:
                                            # st.header(f"**Candidates for {job_options[selected_rid]}**")
                                            df1 = pd.DataFrame(data10, columns=['Candidate_ID', 'Name', 'Email_ID', 'Experience', 'Actual Skills', 'Resume'])
                                            st.dataframe(df1)

                                            st.write("## Shortlist Candidates")

                                            # Iterate through candidates and provide actions
                                            for index, row in df1.iterrows():
                                                cols = st.columns([1, 2, 2, 2])  # Adjust column width ratio as needed
                                                cols[0].write(row["Candidate_ID"])
                                                cols[1].write(row["Name"])

                                                # Download Resume Button
                                                if row["Resume"]:
                                                    cols[2].download_button(
                                                        label="Download Resume",
                                                        data=row["Resume"],  # Resume binary data
                                                        file_name=f"{row['Name']}_resume.pdf",
                                                        mime="application/pdf"
                                                    )

                                                # Accept Candidate Button
                                                with cols[3]:
                    
                                                        accept= st.button(f"Accept {row['Name']}",type="primary")
                                                        if "accept_state" not in st.session_state:
                                                            st.session_state.accept_state= False
                                                        if accept or st.session_state.accept_state:
                                                            st.session_state.accept_state=True
                                                            cursor.execute(f"SELECT Name FROM {DB_table_name1} WHERE cid = %s", (st.session_state.company_user,))
                                                            r = cursor.fetchone()
                                                            # Update status to "Shortlisted"
                                                            cursor.execute("UPDATE user SET status = 'Shortlisted' WHERE candidate_id = %s AND rid = %s", (row["Candidate_ID"], selected_rid))
                                                            connection.commit()

                                                            today = datetime.date.today()

                                                            company_id = st.session_state.company_user
                                                            company_name = st.session_state.get("company_name", "Your Company")

                                                            cursor.execute("SELECT email FROM user_info WHERE candidate_id = %s", (row["Candidate_ID"],))
                                                            candidate_email = cursor.fetchone()[0]

                                                            interview_date = st.date_input("Interview Date", min_value=today)
                                                            interview_time = st.time_input("Interview Time")
                                                            jitsi_link = generate_jitsi_link()

                                                            # if st.checkbox("Confirm Interview Details"):
                                                            if st.button("✅ Schedule Interview"):
                                                                    cursor.execute("""
                                                                        INSERT INTO interview_schedule (company_id, Candidate_ID, interview_date, interview_time, jitsi_link)
                                                                        VALUES (%s, %s, %s, %s, %s)
                                                                    """, (company_id, row["Candidate_ID"], interview_date, interview_time, jitsi_link))
                                                                    connection.commit()

                                                                    subject = f"{company_name} - Virtual Interview Invitation"
                                                                    message = f"""Dear Candidate,
Thank you for applying to the role at {company_name}. We are pleased to inform you that you have been shortlisted for the next stage of our hiring process.

Interview Details:
📅 Date: {interview_date}
🕒 Time: {interview_time}
🔗 Link: Please join via your Smart Hiring System profile.

NOTE:
1. Please ensure you have a stable internet connection if the interview is virtual.
2. Keep a copy of your resume and any relevant documents.

We look forward to speaking with you and learning more about your qualifications.

Regards,  
{company_name} Recruitment Team"""

                                                                    send_email(candidate_email, subject, message)
                                                                    st.success("✅ Interview scheduled successfully.")
                                                                    st.markdown(f"🔗 **[Join Jitsi Meeting]({jitsi_link})**")
                                                                    # st.success(f"**Acceptance email sent to {row['Name']}**")
                                                           
                                        else:
                                            st.info("No candidates have applied for this job yet.")

                                elif page=="Scheduled Interview":
                                    com_get_meeting_link()

                                # if st.sidebar.button("🚪 Logout"):
                                elif page=="Logout":
                                    st.session_state.clear()
                                    st.experimental_rerun()

        except Exception as main_error:
            st.error(f"**⚠ An unexpected error occurred: {main_error}**")

run()
