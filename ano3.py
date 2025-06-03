import time
import streamlit as st
import nltk
nltk.download('stopwords')
import spacy
spacy.load('en_core_web_sm')

import pandas as pd
import io
import time, datetime
from pyresparser import ResumeParser
from streamlit_tags import st_tags
from PIL import Image
import mysql.connector
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
import hashlib
import random
import string
from streamlit_option_menu import option_menu
from streamlit_navigation_bar import st_navbar


def delete_old_user_resume_data():
    try:
        cursor.execute("""
            DELETE FROM user
            WHERE STR_TO_DATE(Timestamp, '%Y-%m-%d %H:%i:%s') < DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """)
        connection.commit()
        #st.success("✅ Old user application data (older than 30 days) has been deleted.")
    except Exception as e:
        st.error(f"⚠ Error while deleting old data: {e}")

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
        SELECT candidate_id, interview_date, interview_time, jitsi_link, rid, domain 
        FROM interview_schedule
        WHERE interview_date=CURDATE()
    """)
    result=cursor.fetchall()
    if result:
        for id, date, time, link, rid, domain in result:
            st.subheader("Job Post: "+domain)
            st.write(f"**Post ID:** {rid}")
            st.write(f"**Candidate ID:** {id}")
            st.write(f"📅 **Date:** {date} 🕒 **Time:** {time}")
            st.markdown(f"🔗 *[Join Jitsi Meeting]({link})*")
            st.markdown("---")
    else:
        st.info("No Interview Scheduled")


def view_interview_schedule():
    st.subheader("Your Scheduled Interviews")

    if "candidate_id" not in st.session_state:
        st.warning("You must be logged in to view interviews.")
        return

    if st.button("View Interview Link",type="primary"):
        interviews = get_meeting_link()

        if interviews:
            for date, time, link in interviews:
                st.write(f"📅 **Date:** {date} 🕒 **Time:** {time}")
                # st.markdown(f"🔗 *[Join Jitsi Meeting]({link})*")
                st.markdown(
                    f'<iframe src="{link}" width="800" height="600" allow="camera; microphone; fullscreen" style="border:0;"></iframe>',
                    unsafe_allow_html=True
                )
                st.markdown("---")
        else:
            st.info("No interviews scheduled yet.")

def generate_pdf(name, email, com, role):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Header
    pdf.set_font("Arial", "B", 15)  # Bold font for header
    pdf.cell(200, 10, txt="Smart Hiring System", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, txt="Application Reference Letter", ln=True, align='C')
    pdf.ln(10)

    # Candidate Details
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, txt="Date: " + datetime.datetime.now().strftime('%Y-%m-%d'), ln=True)
    pdf.ln(5)
    pdf.multi_cell(0, 10, txt=f"Dear {name},\n\n  Thank you for your interest in joining {com}. We are pleased to confirm the receipt of your application for the {role} role.\n\n")

    # pdf.set_font("Arial", "B", 11)  # Bold font for key details
    # pdf.multi_cell(0, 10, txt=f"Candidate Name: {name}\nEmail: {email}\n")
    
    pdf.set_font("Arial", size=11)  # Regular font for the rest of the text
    pdf.multi_cell(0, 10, txt=(
        "We value the time and effort you have invested in applying for this opportunity. Our team will carefully review your application "
        "to assess its alignment with the role's requirements. If shortlisted, you will be contacted shortly with the next steps in the "
        "selection process.\n\n"
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


connection = mysql.connector.connect(host='sql12.freesqldatabase.com', user='sql12782695', password='UtpUX9H2nd',database='sql12782695')
cursor = connection.cursor()


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


def insert_com_data(name, email, password):
    DB_table_name = 'com_data'
    insert_sql = "insert into " + DB_table_name + """
    (Name, email, password) values (%s,%s,%s)"""
    rec_values = (name, email, password)
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
    return cursor.lastrowid

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

def reset_password_company(email, new_password):
    cursor.execute("SELECT * FROM com_data WHERE email = %s", (email,))
    result = cursor.fetchone()
    if result:
        cursor.execute("UPDATE com_data SET password = %s WHERE email = %s", (new_password, email))
        connection.commit()
        st.success("Password reset successful! You can now sign in.")
        st.session_state.reset_mode = False
    else:
        st.error("Username not found!")


def company_signin(cid, password):
    has_pass=hash_password(password)
    cursor.execute("SELECT * FROM com_data WHERE cid = %s AND password = %s", (cid, has_pass))
    result = cursor.fetchone()
    #st.write("Entered (hashed):", has_pass)
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
                email VARCHAR(50) NOT NULL,
                password VARCHAR(100) NOT NULL,
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
            PRIMARY KEY (rid,domain),
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


    DB_table_name4 = 'interview_schedule'
    table_sql4 = "CREATE TABLE IF NOT EXISTS " + DB_table_name4 + """
                (
                    interview_id INT AUTO_INCREMENT PRIMARY KEY,
                    company_id INT NOT NULL,
                    candidate_id INT NOT NULL,
                    rid INT NOT NULL,
                    domain varchar(100) NOT NULL,
                    interview_date DATE NOT NULL,
                    interview_time TIME NOT NULL,
                    jitsi_link VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'Scheduled',
                    FOREIGN KEY (company_id) REFERENCES com_data(cid) ON DELETE CASCADE,
                    FOREIGN KEY (rid, domain) REFERENCES recruit_data(rid, domain) ON DELETE CASCADE,
                    FOREIGN KEY (candidate_id) REFERENCES user_info(candidate_id) ON DELETE CASCADE
                );
                """
    cursor.execute(table_sql4)

    delete_old_user_resume_data()
  

    if choice == 'User 🧑🏻‍💻':
            # try:
                menu = ["Sign In", "Sign Up"]
                choice = st.sidebar.selectbox("Select an option", menu)

                # Sign Up Page
                if choice == "Sign Up":

                    original_title ='''<p style="font-size: 45px; font-weight: bold;color: #333; 
                    text-shadow: 
                    1px 1px 0px #eab,  /* Top-left shadow (light) */
                    2px 2px 0px #ccc,  /* Middle-left shadow */
                    3px 3px 0px #999;  /* Bottom-left shadow (dark) */
                    font-family: Times new roman;"><b>SMART HIRING SYSTEM</b></p>'''
                    st.markdown(original_title, unsafe_allow_html=True)

                    st.subheader("Create a New Account")
                    with st.form("signup_form"):
                        name = st.text_input("Full Name")
                        email = st.text_input("Email")
                        password = st.text_input("Password", type="password")
                        if st.form_submit_button("Sign Up",type="primary"):
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

# ata khola

                # Sign In Page
                elif choice == "Sign In":
                    # RESET PASSWORD MODE
                    if st.session_state.reset_mode:
                        st.subheader("🔁 Reset Password")
                        with st.form("reset_form"):
                            email = st.text_input("Registered Email")
                            new_password = st.text_input("New Password", type="password")
                            confirm_password = st.text_input("Confirm Password", type="password")

                            reset_btn = st.form_submit_button("Reset Password",type="primary")

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
                        original_title ='''<p style="font-size: 50px; font-weight: bold;color: #333; 
                        text-shadow: 
                        1px 1px 0px #eab,  /* Top-left shadow (light) */
                        2px 2px 0px #ccc,  /* Middle-left shadow */
                        3px 3px 0px #999;  /* Bottom-left shadow (dark) */
                        font-family: Times new roman;"><b>SMART HIRING SYSTEM</b></p>'''
                        st.markdown(original_title, unsafe_allow_html=True)
                        st.subheader("Login to Your Account")
                        with st.form("signin_form"):
                            candidate_id = st.text_input("Candidate ID")
                            email = st.text_input("Email")
                            password = st.text_input("Password", type="password")
   
                            if st.form_submit_button("Sign In",type="primary"):
                                    user = signin(candidate_id, email, password)
                                    if user:
                                        #st.experimental_rerun()
                                        st.rerun()
                            forgot = st.form_submit_button("Forgot Password?")
                            if forgot:
                                st.session_state.reset_mode = True
                                #st.experimental_rerun()
                                st.rerun()

                        # ata khola
                    else:
                            pages = {
                                "Profile": "🏠 Home",
                                "Jobs": "💼 Jobs",
                                "Applied Jobs":"💼 Applied Jobs",
                                "View Interview Schedule": "📅 Interviews",
                                "About":"💡About",
                                "Logout": "🔐 Logout"
                            }

                            # This is the only valid argument: list of options
                            selected_page = st_navbar(list(pages.values()))

                            # Map back the selected label to internal page name
                            label_to_key = {v: k for k, v in pages.items()}
                            page = label_to_key[selected_page]

                            # Now render the content like before
                            # st.title(pages[page])
                            # st.subheader(f"*:green[Welcome back, {st.session_state['candidate_name']}! 🎉]*")
                            st.toast(f"**:green[Welcome back, {st.session_state['candidate_name']}! 🎉]**")
                            # st.success(f"Welcome back, {st.session_state['candidate_name']}! 🎉")
                            page_bg_img = f"""
                            <style>
                            [data-testid="stAppViewContainer"] > .main {{
                            background-image: url("https://i.postimg.cc/LXgf9ZvP/Untitled-design-43.png");

                            background-position: center center;

                            /* Make image fixed */
                            background-attachment: fixed;

                            /* Not repeat images */
                            background-repeat: no-repeat;

                            /* Set background size auto */
                            background-size: 100%;
                            }}

                            [data-testid="stHeader"] {{
                            background: rgba(0,0,0,0);
                            }}

                            </style>
                            """

                            st.markdown(page_bg_img, unsafe_allow_html=True)

                            if page == "Jobs":
                                candidate_id = st.session_state.get("candidate_id", None)
                                if candidate_id:                            
                                # Job Application Section
                                    st.header("Browse Job Listings")

                                    # Fetch jobs from database
                                    cursor.execute("""
                                        SELECT r.rid, c.Name, r.domain, r.reco_skill, r.timestamp, r.experience, r.deadline, r.description, r.cid FROM recruit_data r, com_data c
                                        WHERE r.cid=c.cid and deadline >= CURDATE()
                                        AND rid NOT IN (
                                            SELECT rid FROM user WHERE candidate_id = %s
                                        )
                                        ORDER BY timestamp DESC
                                    """, (candidate_id,))
                                    job_posts = cursor.fetchall()

                                    if job_posts:
                                        for job in job_posts:
                                            job_id = job[0]
                                            job_com = job[1]
                                            job_title = job[2]
                                            job_exp = job[5]
                                            job_deadline = job[6]
                                            Job_desc=job[7]

                                            st.subheader("Job Post: "+job_title)
                                            st.write(f"**Company:** {job_com.upper()}")
                                            st.write(f"**Experience Required:** {job_exp}")
                                            st.write(f"**Deadline:** {job_deadline}")
                                            st.write(f"**Description:** {Job_desc}")

                                            # Check if already applied
                                            # cursor.execute("SELECT 1 FROM user WHERE candidate_id = %s AND rid = %s", (candidate_id, job_id))
                                            # already_applied = cursor.fetchone()

                                            # if already_applied:
                                            #     st.success("✅ You have already applied for this job.")
                                            # else:


                                            pdf_file = st.file_uploader("Upload Your Resume", type=["pdf"], key=f"resume_{job_id}")
                                            post = st.button(f"Submit Resume", key=f"submit_{job_id}", type="primary")

                                            st.markdown("---")

                                            if post:
                                                if pdf_file is not None:
                                                    resume_binary = pdf_file.read()
                                                    resume_data = ResumeParser(pdf_file).get_extracted_data()

                                                    # Insert application into DB
                                                    sql = "SELECT email_id FROM user WHERE email_id = %s AND rid = %s"
                                                    cursor.execute(sql, (resume_data['email'], job_id))
                                                    result = cursor.fetchone()

                                                    if result:
                                                        st.warning("**⚠ Something went wrong. You CV is already submitted for this post.**")
                                                        # break
                                                        # update_data(resume_data['email'], job_id, datetime.datetime.now(),
                                                        #             str(resume_data['total_experience']), str(resume_data['skills']),
                                                        #             resume_binary, application_pdf)
                                                        # st.success("**✅ Your data has been updated.**")
                                                    else:
                                                        # Generate PDF
                                                        application_pdf = generate_pdf(resume_data["name"], resume_data["email"], job_com, job_title)

                                                        insert_data(candidate_id,resume_data['name'], resume_data['email'], datetime.datetime.now(),
                                                                    str(resume_data['total_experience']), str(resume_data['skills']),
                                                                    0, resume_binary, application_pdf,job_id)
                                                            # st.success("**✅ Your application has been submitted.**")
                                                        
                                                        if resume_data:
                                                            st.subheader("**Resume Analysis:**")
                                                            st.success(f"**_✅Congratulations {resume_data['name']} 🎉. Your application has been Submitted._**")
                                                            st.text(f"Name: {resume_data['name']}")
                                                            st.text(f"Email: {resume_data['email']}")
                                                            st.text(f"Experience: {resume_data['total_experience']} years")

                                                        # Allow user to download PDF
                                                        stored_pdf = get_pdf_from_db(resume_data['email'])
                                                        if stored_pdf:
                                                            st.download_button(
                                                                label="📥 Download Application Reference PDF",
                                                                data=stored_pdf,
                                                                file_name=f"Application_{resume_data['name'].replace(' ', '_')}.pdf",
                                                                mime="application/pdf",
                                                                type="primary"
                                                            )                                                            
                                                            
                                                            st.markdown("---")
                                                        else:
                                                            st.error("**⚠ An unexpected error occurred while processing your resume.**")
                                                else:
                                                    st.error("**⚠ Please upload your resume before submitting.**")
                                        
                                    else:
                                        st.write("No job posts available yet.")

                            elif page =="Applied Jobs":
                                candidate_id = st.session_state.get("candidate_id", None)
                                if candidate_id:                            
                                # Job Application Section
                                    st.header("Applied Job List")
                                    cursor.execute("""
                                        SELECT r.rid, c.Name, r.domain, r.reco_skill, u.Timestamp, r.experience, r.deadline, r.description, r.cid, u.status FROM recruit_data r, com_data c, user u
                                        WHERE r.cid=c.cid and u.rid=r.rid and u.candidate_id = %s 
                                        ORDER BY u.Timestamp DESC
                                    """, (candidate_id,))
                                    job_posts = cursor.fetchall()

                                    if job_posts:
                                        for job in job_posts:
                                            job_id = job[0]
                                            job_com = job[1]
                                            job_title = job[2]
                                            job_exp = job[5]
                                            job_deadline = job[6]
                                            Job_desc=job[7]
                                            Job_status=job[9]

                                            st.subheader("Job Post: "+job_title)
                                            st.write(f"**Company:** {job_com.upper()}")
                                            st.write(f"**Experience Required:** {job_exp}")
                                            st.write(f"**Deadline:** {job_deadline}")
                                            st.write(f"**Description:** {Job_desc}")
                                            st.write(f"**Status:** {Job_status}")
                                            st.markdown("---")
                                    else:
                                        st.write("You have not applied to any Job posts yet.")
                            elif page == "View Interview Schedule":
                                view_interview_schedule()
                            elif page == "Profile":
                                st.header("👤 Your Profile")
                                candidate_id = st.session_state.get("candidate_id", None)
                                if candidate_id:
                                # # --- Fetch user basic info ---
                                    st.subheader("🪪 Basic Information")
                                    cursor.execute("SELECT name, email FROM user_info WHERE candidate_id = %s", (candidate_id,))
                                    user_data = cursor.fetchone()
                                    
                                    if user_data:
                                        st.write(f"**Name:** {user_data[0]}")
                                        st.write(f"**Email:** {user_data[1]}")
                                        st.write(f"**Candidate ID:** {candidate_id}")
                                    else:
                                        st.warning("**Unable to fetch profile information.**")

                                    # --- Count of Job Applications ---
                                    st.subheader("📄 Applications Summary")
                                    cursor.execute("SELECT COUNT(*) FROM user WHERE candidate_id = %s", (candidate_id,))
                                    apps_count = cursor.fetchone()[0]
                                    st.write(f"**Total Applications Submitted:** {apps_count}")

                                    # --- Interview Calls Received ---
                                    st.subheader("📞 Interview Calls")
                                    cursor.execute("SELECT COUNT(*) FROM interview_schedule WHERE candidate_id = %s", (candidate_id,))
                                    interview_count = cursor.fetchone()[0]
                                    st.write(f"**Total Interview Calls Received:** {interview_count}")
                            

                            elif page == "About":
                                st.header("About Smart Hiring System")
                                st.write("Welcome to the Smart Hiring System, a cutting-edge recruitment platform designed to connect talented candidates with top-tier organizations. Our platform streamlines the hiring process by offering an intuitive interface for job seekers, recruiters, and administrators alike.")
                                st.subheader("Key Features:")
                                columns = st.columns(3)
                                # Add unique content in each column using containers
                                with columns[0]:
                                    with st.container(height=250):
                                        st.write("**For Candidates:**")
                                        st.write("Effortlessly apply for jobs, upload resumes, and track your applications. Get instant notifications about interview schedules and stay ahead in your job search.")                                        
                                        
                                with columns[1]:
                                    with st.container(height=250):
                                        st.write("**For Companies:**")
                                        st.write(" Post job openings, review candidate applications, and schedule interviews seamlessly. Utilize intelligent filters to shortlist the best talent for your organization.")
                                        
                                with columns[2]:
                                    with st.container(height=250):
                                        st.write("**For Admins:**")
                                        st.write("Oversee platform activities, manage user data, and ensure smooth operations across all stakeholders.")
                                        

                            elif page=="Logout":
                                st.session_state.clear()
                                st.rerun()

            # except Exception:
            #     st.error("**⚠ No job posts available yet.**")


    elif choice=='Admin 👤':
        try:
            original_title ='''<p style="font-size: 50px; font-weight: bold;color: #333; 
            text-shadow: 
            1px 1px 0px #eab,  /* Top-left shadow (light) */
            2px 2px 0px #ccc,  /* Middle-left shadow */
            3px 3px 0px #999;  /* Bottom-left shadow (dark) */
            font-family: Times new roman;"><b>SMART HIRING SYSTEM</b></p>'''
            st.markdown(original_title, unsafe_allow_html=True)
            if "admin_logged_in" not in st.session_state:
                st.session_state.admin_logged_in = False

            # if not st.session_state.admin_logged_in:
            if not st.session_state.get("admin_logged_in", False):
                st.subheader("Admin Login Page")
                with st.form("signin_form"):
                    admin_user=st.text_input("**Username**")
                    admin_password=st.text_input("**Password**",type='password')

                    if st.form_submit_button("Sign In",type="primary"):
                        
            # loadnow11=st.button("login",type="primary")
            # #initialize session state
            # if "loadnow11_state" not in st.session_state:
            #     st.session_state.loadnow11_state= False
            # if loadnow11 or st.session_state.loadnow11_state:
            #     st.session_state.loadnow11_state=True
                        with st.spinner(':blue[Authenticating...]'):
                            time.sleep(2)
                            if admin_user == 'admin' and admin_password == 'admin123':
                                st.session_state.admin_logged_in = True
                                # st.success("##### **_:blue[Welcome Admin]_**")
                                st.rerun()
                            else:
                                st.error("**Invalid credentials. Please try again.**")
                        # st.rerun()
            # if st.session_state.admin_logged_in:
            else:
                # --- Admin Dashboard Content ---
                st.toast(f"**:green[Welcome back Admin 🎉]**")
                            # st.success(f"Welcome back, {st.session_state['candidate_name']}! 🎉")
                page_bg_img = f"""
                <style>
                [data-testid="stAppViewContainer"] > .main {{
                background-image: url("https://i.postimg.cc/LXgf9ZvP/Untitled-design-43.png");

                background-position: center center;

                /* Make image fixed */
                background-attachment: fixed;

                /* Not repeat images */
                background-repeat: no-repeat;

                /* Set background size auto */
                background-size: 100%;
                }}

                [data-testid="stHeader"] {{
                background: rgba(0,0,0,0);
                }}

                </style>
                """

                st.markdown(page_bg_img, unsafe_allow_html=True)
                st.markdown("### 👤 Admin Dashboard")

                cursor.execute('''SELECT candidate_id,name,email FROM user_info''')
                data = cursor.fetchall()
                st.header("**User's Data**")
                df = pd.DataFrame(data, columns=['Candidate_ID', 'Name', 'Email'])
                st.dataframe(df)

                cursor.execute('''SELECT u.candidate_id, u.Name, u.Email_ID, u.Timestamp, u.Experience, u.Actual_skills, u.rid, c.Name, u.status FROM user u, recruit_data r, com_data c where u.rid=r.rid and r.cid=c.cid''')
                data = cursor.fetchall()
                st.header("**Job Application Data**")
                df = pd.DataFrame(data, columns=['Candidate ID', 'Name', 'Email', 'Timestamp', 'Experience', 'Actual Skills','Recruit Id','Company','Status'])
                st.dataframe(df)

                cursor.execute('''SELECT interview_id, company_id, candidate_id,interview_date,interview_time,status FROM interview_schedule''')
                data1 = cursor.fetchall()
                st.header("**Interview Details**")
                df = pd.DataFrame(data1, columns=['interview_id', 'company_id', 'candidate_id','interview_date','interview_time','status'])
                st.dataframe(df)

                cursor.execute('''SELECT cid, Name, email FROM com_data''')
                data1 = cursor.fetchall()
                st.header("**Company's Data**")
                df = pd.DataFrame(data1, columns=['Company ID', 'Company Name', 'email'])
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
                            st.subheader(f"Previous recruitments of Company ID- {c_id}:")
                            recruitments = fetch_previous_recruitments(c_id)
                            if recruitments:
                                recruit_df = pd.DataFrame(recruitments, columns=['RID', 'Domain', 'Reco_Skills', 'Timestamp', 'Experience','Deadline','Job Description'])
                                st.dataframe(recruit_df)
                            else:
                                
                                st.info(f"**No previous recruitment posts for {c_id}.**")
                        else:
                            st.error("**There is no such ID exists.**")
                    else:
                        st.error("**⚠ Nothing to show**")
        except Exception as main_error:
            st.error(f"**⚠ An unexpected error occurred: {main_error}**")

# company side
    else:
        try:
            activities1 = ["Sign in", "Sign up"]
            choice2 = st.sidebar.selectbox("Select an option:", activities1)
        
            if choice2=='Sign up':
                original_title ='''<p style="font-size: 50px; font-weight: bold;color: #333; 
                text-shadow: 
                1px 1px 0px #eab,  /* Top-left shadow (light) */
                2px 2px 0px #ccc,  /* Middle-left shadow */
                3px 3px 0px #999;  /* Bottom-left shadow (dark) */
                font-family: Times new roman;"><b>SMART HIRING SYSTEM</b></p>'''
                st.markdown(original_title, unsafe_allow_html=True)               
                st.subheader("Create a New Account")
                with st.form("signup_form"):
                    name=st.text_input("**Company_name**")
                    email=st.text_input("**Company_email**")
                    password=st.text_input("**Company_password**",type="password")
                    if st.form_submit_button("Sign Up",type="primary"):
                        hsd_pass=hash_password(password)
                # name=st.text_input("**Company_name**")
                # password=st.text_input("**Company_password**")
                # if st.button("Create Profile", type="primary"):               
                        cursor.execute(f"SELECT * FROM {DB_table_name1} WHERE Name = %s", (name,))
                        company_exists = cursor.fetchone()

                        if company_exists:
                            st.error(f"**_A company with the name '{name}' already exists. Please use a different name or log in._**")
                        else:
                            try:
                                new_cid = insert_com_data(name, email, hsd_pass)
                                st.success(f"**_:blue[Your profile is created. Your company ID is {new_cid}]_**")
                                st.balloons()
                            except Exception as e:
                                st.error(f"**_An unexpected error occurred: {e}_**")

            else: 
                if st.session_state.get("reset_mode", False):
                    original_title ='''<p style="font-size: 50px; font-weight: bold;color: #333; 
                    text-shadow: 
                    1px 1px 0px #eab,  /* Top-left shadow (light) */
                    2px 2px 0px #ccc,  /* Middle-left shadow */
                    3px 3px 0px #999;  /* Bottom-left shadow (dark) */
                    font-family: Times new roman;"><b>SMART HIRING SYSTEM</b></p>'''
                    st.markdown(original_title, unsafe_allow_html=True)
                    st.subheader("🔁 Reset Password")
                    with st.form("reset_form"):
                        email = st.text_input("Registered Email")
                        new_password = st.text_input("New Password", type="password")
                        confirm_password = st.text_input("Confirm Password", type="password")

                        reset_btn = st.form_submit_button("Reset Password",type="primary")

                        if reset_btn:
                            if new_password != confirm_password:
                                st.error("❌ Passwords do not match.")
                            else:
                                hashed = hash_password(new_password)
                                reset_password_company(email, hashed)
                                st.session_state.reset_mode = False

                    if st.button("⬅ Back to Sign In"):
                        st.session_state.reset_mode = False
                        #st.experimental_rerun()  
                        # st.rerun()
                    return               
                if not st.session_state.get("company_logged_in", False) and not st.session_state.get("reset_mode", False):
                    original_title ='''<p style="font-size: 50px; font-weight: bold;color: #333; 
                    text-shadow: 
                    1px 1px 0px #eab,  /* Top-left shadow (light) */
                    2px 2px 0px #ccc,  /* Middle-left shadow */
                    3px 3px 0px #999;  /* Bottom-left shadow (dark) */
                    font-family: Times new roman;"><b>SMART HIRING SYSTEM</b></p>'''
                    st.markdown(original_title, unsafe_allow_html=True)                    
                    st.subheader("Company Sign In")
                    if "company_cid" not in st.session_state:
                        st.session_state.company_user = ""
                    if "company_password" not in st.session_state:
                        st.session_state.company_password = ""

                    with st.form("signin_form"):
                        st.session_state.company_user = st.text_input("Company ID", value=st.session_state.company_user)
                        st.session_state.company_password = st.text_input("Password", type="password", value=st.session_state.company_password)

                        if st.form_submit_button("Sign In",type="primary"):
                            with st.spinner(':blue[Authenticating...]'):
                                time.sleep(2)
                            # st.session_state.has_pass=hash_password(st.session_state.company_password)
                                company = company_signin(st.session_state.company_user, st.session_state.company_password)
                                
                                if company:
                                    st.experimental_rerun()
                                    # st.rerun()
                                    st.session_state.company_logged_in = True
                                    st.session_state.company_user_id = company[0]
                                    st.session_state.company_name = company[1]
                        forgot = st.form_submit_button("Forgot Password?")
                        if forgot:
                            st.session_state.reset_mode = True
                            #st.experimental_rerun()
                            st.rerun()
                else:
                    if st.session_state.get("company_logged_in", False):
                                
                                pages = {
                                "Home": "🏠 Home",
                                "Display Shortlist Candidates": "📅 Shortlisted Candidates",
                                "Scheduled Interview": "📅 Scheduled Interview",
                                "About":"💡About",
                                "Logout": "🔐 Logout"
                                }

                                # This is the only valid argument: list of options
                                selected_page = st_navbar(list(pages.values()))

                                # Map back the selected label to internal page name
                                label_to_key = {v: k for k, v in pages.items()}
                                page = label_to_key[selected_page]

                                # Now render the content like before
                                # st.title(pages[page])
                                st.toast(f"**:green[Welcome back, {st.session_state['company_name']}! 🎉]**")

                                page_bg_img = f"""
                                <style>
                                [data-testid="stAppViewContainer"] > .main {{
                                background-image: url("https://i.postimg.cc/LXgf9ZvP/Untitled-design-43.png");

                                background-position: center center;

                                /* Make image fixed */
                                background-attachment: fixed;

                                /* Not repeat images */
                                background-repeat: no-repeat;

                                /* Set background size auto */
                                background-size: 100%;
                                }}

                                [data-testid="stHeader"] {{
                                background: rgba(0,0,0,0);
                                }}

                                </style>
                                """

                                st.markdown(page_bg_img, unsafe_allow_html=True)
                                if page=="Home":

                                    activities = ["Web Development", "Python Development", "Java Development", "Data Scientist", "Full Stack Development","Android Development"]     
                                    choice1 = st.selectbox("**Choose Required Domain:**", activities)
                                    st.session_state.c1=choice1
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
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                for i in range(len(li)):
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                
                                                l.append(c)
                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
                                            delete_sql = f"UPDATE {DB_table_name} SET Count = %s WHERE Email_ID = %s"
                                            cursor.execute(delete_sql, (value,email,))
                                            connection.commit()
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
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                for i in range(len(li)):
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                l.append(c)
                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
                                            delete_sql = f"UPDATE {DB_table_name} SET Count = %s WHERE Email_ID = %s"
                                            cursor.execute(delete_sql, (value,email,))
                                            connection.commit()
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
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                for i in range(len(li)):
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                l.append(c)
                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
                                            delete_sql = f"UPDATE {DB_table_name} SET Count = %s WHERE Email_ID = %s"
                                            cursor.execute(delete_sql, (value,email,))
                                            connection.commit()
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
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                for i in range(len(li)):
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                l.append(c)

                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
                                            delete_sql = f"UPDATE {DB_table_name} SET Count = %s WHERE Email_ID = %s"
                                            cursor.execute(delete_sql, (value,email,))
                                            connection.commit()
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
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                for i in range(len(li)):
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                l.append(c)
                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
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
                                            for y in x:
                                                converted_list = eval(y)
                                                c=0
                                                lowercase_list = [item.lower() for item in converted_list]
                                                for i in range(len(li)):
                                                    if li[i].lower() in lowercase_list:
                                                        c=c+1
                                                l.append(c)

                                        emails_list = [email[0] for email in data2]
                                        result = dict(zip(emails_list, l))
                                        for email, value in result.items():
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
                                    load1 = st.button('Submit new recruitment posts',type="primary")

                                    if load1:
                                        st.session_state.load12_state = False
                                        st.session_state.load1_state = True  # Set flag to indicate button click
                                        # st.session_state.load12_state = False  # Ensure the other button state is reset

                                    if st.session_state.load1_state:
                                        ts = time.time()
                                        cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                                        cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                                        timestamp = str(cur_date + '_' + cur_time)

                                        jid=insert_recruit_data(st.session_state.company_user, choice1, ', '.join(options), timestamp, age, job_deadline,des)
                                        
                                        st.success(f"**New recruitment post for {choice1} submitted sucessfully**")
                                        st.success(f"**Post ID is: {jid}**")
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


                                    if job_posts:
                                        job_options = {f"{domain} (ID: {rid})": rid for rid, domain in job_posts}
                                        selected_label = st.selectbox("Select a Job Posting", options=list(job_options.keys()))
                                        selected_rid = job_options[selected_label] # Get rid from selected label

                                        # Button to show candidates for selected job posting
                                        load120 = st.button("Show Candidates for Selected Job",type="primary")

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

                                            cursor.execute(f"""
                                                SELECT candidate_id, Name, Email_ID, Experience, Actual_skills
                                                FROM user 
                                                WHERE rid = %s AND Count >= 1 AND Experience >= (SELECT experience FROM recruit_data WHERE rid = %s) 
                                                ORDER BY Count DESC
                                            """, (selected_rid, selected_rid))
                                            
                                            data_10 = cursor.fetchall()

                                            # Display Candidate Data
                                            if data10:
                                                df2 = pd.DataFrame(data_10, columns=['Candidate_ID', 'Name', 'Email_ID', 'Experience', 'Actual Skills'])
                                                st.dataframe(df2)

                                                df1 = pd.DataFrame(data10, columns=['Candidate_ID', 'Name', 'Email_ID', 'Experience', 'Actual Skills','Resume'])

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
                        
                                                            accept_key = f"accept_state_{row['Candidate_ID']}"
                                                            accept = st.button(f"Accept {row['Name']}", type="primary", key=f"interview_{row['Candidate_ID']}")

                                                            if accept:
                                                                st.session_state[accept_key] = True

                                                            if st.session_state.get(accept_key, False):
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

                                                                cursor.execute("SELECT domain FROM recruit_data WHERE rid = %s", (selected_rid,))
                                                                domain = cursor.fetchone()[0]

                                                                interview_date = st.date_input("Interview Date", min_value=today, key=f"interview_date_{row['Candidate_ID']}")
                                                                interview_time = st.time_input("Interview Time",key=f"interview_time_{row['Candidate_ID']}")
                                                                jitsi_link = generate_jitsi_link()

                                                                if st.button("✅ Schedule Interview",type="primary",key=f"interview_set_{row['Candidate_ID']}"):
                                                                        cursor.execute("""
                                                                            INSERT INTO interview_schedule (company_id, Candidate_ID, rid, domain, interview_date, interview_time, jitsi_link)
                                                                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                                                                        """, (company_id, row["Candidate_ID"], selected_rid, domain, interview_date, interview_time, jitsi_link))
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
                                                            
                                            else:
                                                st.info("No candidates have applied for this job yet.")
                                    else:
                                        st.info("No job post available yet.")
                                elif page=="Scheduled Interview":
                                    com_get_meeting_link()

                                    
                                elif page == "About":
                                    st.header("About Smart Hiring System")
                                    st.write("Welcome to the Smart Hiring System, a cutting-edge recruitment platform designed to connect talented candidates with top-tier organizations. Our platform streamlines the hiring process by offering an intuitive interface for job seekers, recruiters, and administrators alike.")
                                    st.subheader("Key Features:")
                                    columns = st.columns(3)
                                    # Add unique content in each column using containers
                                    with columns[0]:
                                        with st.container(height=250):
                                            st.write("**For Candidates:**")
                                            st.write("Effortlessly apply for jobs, upload resumes, and track your applications. Get instant notifications about interview schedules and stay ahead in your job search.")
                                            

                                    with columns[1]:
                                        with st.container(height=250):
                                            st.write("**For Companies:**")
                                            st.write(" Post job openings, review candidate applications, and schedule interviews seamlessly. Utilize intelligent filters to shortlist the best talent for your organization.")
                                            
                                    with columns[2]:
                                        with st.container(height=250):
                                            st.write("**For Admins:**")
                                            st.write("Oversee platform activities, manage user data, and ensure smooth operations across all stakeholders.")
                                        

                                elif page=="Logout":
                                    st.session_state.clear()
                                    # st.experimental_rerun()
                                    st.rerun()

        except Exception as main_error:
            st.error(f"**⚠ An unexpected error occurred: {main_error}**")

run()
