# Copyright (c) 2025
# All rights reserved.

import hashlib
original_md5 = hashlib.md5
def patched_md5(*args, **kwargs):
    kwargs.pop('usedforsecurity', None)
    return original_md5(*args, **kwargs)
hashlib.md5 = patched_md5

from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from flask_session import Session
import os
from dotenv import load_dotenv
from utils.form_recognizer import parse_resume
from utils.matcher import get_match_score, parse_score_table
from utils.document_converter import (
    pdf_to_docx, extract_text_from_file, get_file_extension,
    is_supported_resume_format, is_supported_jd_format, docx_to_pdf
)
from utils.pdf_merger import merge_resume_and_report, merge_with_jd_and_report
from werkzeug.utils import secure_filename
import tempfile
from azure.storage.blob import BlobServiceClient
import pandas as pd
import re
import base64
from xhtml2pdf import pisa
from markupsafe import Markup
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from functools import lru_cache
import threading

load_dotenv()
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "reports")

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.office365.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "shreyasgowdaravi@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "zkrcnyphbfxzqkfs")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)

AZURE_ENABLED = bool(AZURE_STORAGE_CONNECTION_STRING and AZURE_STORAGE_CONTAINER_NAME)
if not AZURE_ENABLED:
    print("⚠️ Azure Storage not configured. Downloads will be limited to local files only.")

app = Flask(__name__)
app.config.from_object('config.Config')
app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key_for_development_only')

# Configure server-side sessions to avoid large cookies
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'resume_matcher:'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 365 * 24 * 60 * 60  # 365 days in seconds

# Initialize server-side sessions
Session(app)
MAX_WORKERS = 4

# Performance optimizations
blob_client_cache = {}
cache_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

ADMIN_CREDENTIALS = {
    "shreyasgowdaravi@gmail.com": "admin123",
}
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        default_users = {
            "shreyasgowdaravi@gmail.com": {"password": "shreyas123", "approved": True, "last_login": None, "jd_count": 0, "resume_count": 0, "shortlist_count": 0, "not_shortlist_count": 0, "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            
        }
        save_users(default_users)
        return default_users
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

def save_users(users_data):
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users_data, f, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")

def update_session_time(email, session_type, action):
    if session_type == "admin":
        filename = 'admin_sessions.json'
    else:
        users_data = load_users()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if email in users_data:
            if action == "login":
                users_data[email]['current_login'] = current_time
                users_data[email]['last_logout'] = users_data[email].get('last_logout', 'Never')
            else:
                users_data[email]['last_logout'] = current_time
                users_data[email].pop('current_login', None)
            save_users(users_data)
        return
    
    try:
        with open(filename, 'r') as f:
            sessions = json.load(f)
    except FileNotFoundError:
        sessions = {}
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if email not in sessions:
        sessions[email] = {}
    
    if action == "login":
        sessions[email]['current_login'] = current_time
        sessions[email]['last_logout'] = sessions[email].get('last_logout', 'Never')
    else:
        sessions[email]['last_logout'] = current_time
        sessions[email].pop('current_login', None)
    
    with open(filename, 'w') as f:
        json.dump(sessions, f, indent=2)

def process_job_description(jd_file):
    if not is_supported_jd_format(jd_file.filename):
        raise Exception(f"Unsupported job description format: {get_file_extension(jd_file.filename)}. Supported formats: .txt, .docx, .pdf")
    
    file_ext = get_file_extension(jd_file.filename)
    
    try:
        if file_ext == '.pdf':
            docx_path = pdf_to_docx(jd_file)
            jd_text = extract_text_from_file(docx_path)
            os.unlink(docx_path)
            return jd_text
        elif file_ext == '.docx':
            # For .docx files, use the document converter directly
            jd_file.seek(0)  # Reset file pointer
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
            temp_file.write(jd_file.read())
            temp_file.close()
            
            # Extract text from the DOCX file
            jd_text = extract_text_from_file(temp_file.name)
            
            # Clean up the temporary file
            os.unlink(temp_file.name)
            
            if not jd_text or not jd_text.strip():
                raise Exception("No text could be extracted from the DOCX file. Please check if the file is valid and contains text.")
            
            return jd_text
        else:  # .txt files
            # Create a proper temporary file with the correct extension
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
            temp_file.close()
            
            # Save the uploaded file to the temporary location
            jd_file.save(temp_file.name)
            
            # Extract text from the file
            jd_text = extract_text_from_file(temp_file.name)
            
            # Clean up the temporary file
            os.unlink(temp_file.name)
            
            if not jd_text or not jd_text.strip():
                raise Exception(f"No text could be extracted from the {file_ext} file. Please check if the file is valid and contains text.")
            
            return jd_text
    except Exception as e:
        raise Exception(f"Failed to process job description file: {str(e)}")

def get_blob_client():
    with cache_lock:
        if 'client' not in blob_client_cache:
            blob_client_cache['client'] = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        return blob_client_cache['client']

def upload_to_azure(file_path, blob_name):
    if not AZURE_ENABLED:
        return False
    try:
        blob_service_client = get_blob_client()
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        with open(file_path, "rb") as data:
            container_client.upload_blob(name=blob_name, data=data, overwrite=True)
        return True
    except Exception as e:
        print(f"❌ Azure upload failed for {blob_name}: {e}")
        return False

def download_from_azure(blob_name):
    try:
        blob_service_client = get_blob_client()
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        blob_client = container_client.get_blob_client(blob_name)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        with open(temp_file.name, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())
        return temp_file.name
    except Exception as e:
        print(f"Azure download failed: {e}")
        return None

@lru_cache(maxsize=1)
def get_logo_base64():
    for logo_path in ['static/logo.png', 'logo.png']:
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as logo_file:
                return base64.b64encode(logo_file.read()).decode('utf-8')
    return ''

def convert_to_pdf(score_df, context_df, verdict, total_score, file_name="evaluation"):
    verdict_color = '#28a745' if verdict == 'Shortlist' else '#ffc107' if verdict == 'Hold' else '#dc3545'
    logo_base64 = get_logo_base64()
    
    # Get status message based on verdict
    if verdict == "Shortlist":
        status_message = "Resume is Shortlisted can be shared with the Client."
    elif verdict == "Hold":
        status_message = "Resume is on hold. Review before sharing with the client."
    else:
        status_message = "Resume is not relevant for the client's requirement."

    eval_rows = ''
    if not score_df.empty:
        for _, row in score_df.iterrows():
            criteria = row.get('Criteria') or str(row.iloc[0] if len(row) > 0 else '')
            max_score = row.get('Max Score') or str(row.iloc[1] if len(row) > 1 else '')
            candidate_score = row.get('Candidate Score') or row.get('Score') or str(row.iloc[2] if len(row) > 2 else '')
            explanation = row.get('Extracted / Explanation') or row.get('Explanation') or str(row.iloc[3] if len(row) > 3 else '')
            
            eval_rows += f"""
            <tr>
                <td style="width: 40%; font-weight: bold;">{criteria}</td>
                <td style="width: 15%; text-align: center;">{max_score}</td>
                <td style="width: 15%; text-align: center; font-weight: bold; color: #667eea;">{candidate_score}</td>
                <td style="width: 30%;">{explanation}</td>
            </tr>
            """
    
    context_rows = ''
    if not context_df.empty:
        for _, row in context_df.iterrows():
            criteria = row.get('Criteria') or str(row.iloc[0] if len(row) > 0 else '')
            details = row.get('Extracted / Explanation') or str(row.iloc[1] if len(row) > 1 else '')
            # Clean up HTML entities
            details = details.replace('&#39;', "'").replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            context_rows += f"""
            <tr>
                <td style="width: 30%; font-weight: bold;">{criteria}</td>
                <td style="width: 70%;">{details}</td>
            </tr>
            """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 0.5cm; }}
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; line-height: 1.2; color: #333; font-size: 9px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; border-radius: 4px; margin-bottom: 10px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 14px; }}
            .header p {{ margin: 3px 0 0 0; font-size: 10px; }}
            .summary-box {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
            .score-box {{ background-color: #f8f9fa; padding: 8px; border-radius: 4px; text-align: center; width: 48%; border: 1px solid #dee2e6; }}
            .verdict-box {{ background-color: {verdict_color}; color: white; padding: 8px; border-radius: 4px; text-align: center; width: 48%; }}
            .section {{ margin-bottom: 10px; }}
            .section h2 {{ color: #667eea; border-bottom: 1px solid #667eea; padding-bottom: 2px; margin-bottom: 8px; font-size: 11px; margin-top: 5px; }}
            .table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 8px; }}
            .table th {{ background-color: #667eea; color: white; border: 1px solid #dee2e6; padding: 4px; text-align: left; font-weight: bold; }}
            .table td {{ border: 1px solid #dee2e6; padding: 3px; vertical-align: top; word-wrap: break-word; }}
            .table tr:nth-child(even) {{ background-color: #f8f9fa; }}
            .summary-section {{ margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }}
            .footer {{ position: fixed; bottom: 0.5cm; left: 0.5cm; right: 0.5cm; text-align: center; color: #666; font-size: 7px; border-top: 1px solid #dee2e6; padding-top: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 40px; margin-bottom: 5px;"><br>' if logo_base64 else ''}
            <h1>Resume Evaluation Report</h1>
            <p>Candidate: {os.path.splitext(file_name)[0].replace('_', ' ')}</p>
        </div>
        
        <div class="section">
            <h2>📊 Detailed Evaluation Scores</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Evaluation Criteria</th>
                        <th>Max Score</th>
                        <th>Candidate Score</th>
                        <th>Extracted / Explanation</th>
                    </tr>
                </thead>
                <tbody>
                    {eval_rows if eval_rows else '<tr><td colspan="4" style="text-align: center; color: #666;">No evaluation data available</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📝 Additional Context (No Score, Mandatory Explanation)</h2>
            {f'''
            <table class="table">
                <thead>
                    <tr>
                        <th>Criteria</th>
                        <th>Extracted / Explanation</th>
                    </tr>
                </thead>
                <tbody>
                    {context_rows}
                </tbody>
            </table>
            ''' if context_rows else '<p style="color: #666; font-style: italic; text-align: center; padding: 20px;">No additional context available</p>'}
        </div>
        
        <div class="summary-box">
            <div class="score-box" style="width: 100%; background-color: {verdict_color}; color: white;">
                <h3 style="margin: 0; font-size: 12px;">{status_message}</h3>
            </div>
        </div>
        
        <div class="summary-section">
            <h3 style="color: #667eea; margin-top: 0; font-size: 10px;">📋 Report Summary</h3>
            <p style="margin: 2px 0;"><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin: 2px 0;"><strong>Evaluation Method:</strong> AI-Powered Resume Matching</p>
        </div>
        
        <div class="footer">
            <p>Generated by Resume Evaluator | © 2025. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_path = temp_file.name
        temp_file.close()
        
        with open(temp_path, "wb") as f:
            pisa_status = pisa.CreatePDF(html, dest=f, encoding='utf-8', show_error_as_pdf=True)
            if pisa_status.err:
                return None
        
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            return temp_path
        else:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    except Exception as e:
        print(f"❌ PDF generation exception: {e}")
        return None

def send_email_with_attachments(to_email, subject, body, attachments=None):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        return False, "Email not configured"
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        if attachments:
            for file_path, filename in attachments:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except smtplib.SMTPAuthenticationError:
        return False, "Email authentication failed - check credentials"
    except smtplib.SMTPRecipientsRefused:
        return False, "Invalid recipient email address"
    except smtplib.SMTPServerDisconnected:
        return False, "Email server connection lost"
    except Exception as e:
        return False, f"Email failed: {str(e)}"

def parse_context_table(markdown_text):
    pattern = r"\| ([^|]+?)\s*\| ([^|]+?)\|"
    matches = re.findall(pattern, markdown_text)
    data = []
    for row in matches:
        col1, col2 = map(str.strip, row)
        if set(col1) <= {"-", " "} or "criteria" in col1.lower() or "--" in col1:
            continue
        data.append({"Criteria": col1, "Extracted / Explanation": col2})
    return pd.DataFrame(data)

def format_evaluation_for_ui(evaluation_text):
    if not evaluation_text:
        return "No evaluation details available"
    
    html_parts = []
    lines = evaluation_text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('###'):
            header_text = line.replace('###', '').strip()
            html_parts.append(f'<h6 class="fw-bold text-primary mt-4 mb-3">{header_text}</h6>')
            i += 1
            continue
        
        if '|' in line and ('Criteria' in line or 'Max Score' in line):
            html_parts.append('<div class="table-responsive mt-3">')
            html_parts.append('<table class="table table-sm table-bordered">')
            
            headers = [cell.strip() for cell in line.split('|') if cell.strip()]
            html_parts.append('<thead class="table-light"><tr>')
            for header in headers:
                html_parts.append(f'<th class="small fw-bold">{header}</th>')
            html_parts.append('</tr></thead><tbody>')
            
            i += 1
            if i < len(lines) and '---' in lines[i]:
                i += 1
            
            while i < len(lines) and '|' in lines[i] and lines[i].strip():
                row_line = lines[i].strip()
                if not set(row_line) <= {'-', '|', ' '}:
                    cells = [cell.strip() for cell in row_line.split('|') if cell.strip()]
                    if cells:
                        html_parts.append('<tr>')
                        for j, cell in enumerate(cells):
                            # Clean cell content from markdown
                            clean_cell = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', cell)
                            clean_cell = re.sub(r'\*(.*?)\*', r'<em>\1</em>', clean_cell)
                            clean_cell = clean_cell.replace('**', '').replace('*', '')
                            
                            if j == 1 or j == 2:
                                html_parts.append(f'<td class="text-center fw-bold">{clean_cell}</td>')
                            else:
                                html_parts.append(f'<td class="small">{clean_cell}</td>')
                        html_parts.append('</tr>')
                i += 1
            
            html_parts.append('</tbody></table></div>')
            continue
        
        if line:
            # Remove markdown formatting
            line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
            line = re.sub(r'\*(.*?)\*', r'<em>\1</em>', line)
            line = line.replace('**', '').replace('*', '')
            if line.startswith('- '):
                html_parts.append(f'<li class="mb-1">{line[2:]}</li>')
            else:
                html_parts.append(f'<p class="mb-2">{line}</p>')
        
        i += 1
    
    return '\n'.join(html_parts)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        
        if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password:
            session["admin"] = username
            session.permanent = True
            update_session_time(username, "admin", "login")
            return redirect(url_for("admin_dashboard"))
        
        users_data = load_users()
        if username in users_data:
            user_info = users_data[username]
            if user_info['password'] == password:
                if user_info.get('approved', False):
                    session["username"] = username
                    session.permanent = True
                    update_session_time(username, "user", "login")
                    return redirect(url_for("dashboard"))
                else:
                    flash("Your account is pending approval. Please contact the administrator.", "warning")
            else:
                flash("Invalid credentials", "danger")
        else:
            flash("User ID not found. Please check your email or contact the administrator.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        if not all([name, email, password, confirm_password]):
            flash("All fields are required", "danger")
            return render_template("register.html")
        
        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return render_template("register.html")
        
        if len(password) < 6:
            flash("Password must be at least 6 characters long", "danger")
            return render_template("register.html")
        
        users_data = load_users()
        if email in users_data:
            flash("Email already registered", "danger")
            return render_template("register.html")
        
        users_data[email] = {
            "name": name,
            "password": password,
            "approved": False,
            "last_login": None,
            "jd_count": 0,
            "resume_count": 0,
            "shortlist_count": 0,
            "not_shortlist_count": 0,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_users(users_data)
        
        flash("Account created successfully! Please wait for admin approval.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    
    users_data = load_users()
    current_user_email = session["username"]
    
    if current_user_email not in users_data:
        session.clear()
        flash("User ID not found. Your account may have been removed. Please contact the administrator.", "danger")
        return redirect(url_for("login"))
    
    if not users_data[current_user_email].get('approved', False):
        session.clear()
        flash("Your access has been revoked. Please contact the administrator.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            jd_file = request.files["jd_file"]
            resumes = request.files.getlist("resumes")
            
            if not jd_file or not resumes:
                flash("Please upload both job description and resume files", "danger")
                return render_template("dashboard.html", username=session["username"])
            
            if not is_supported_jd_format(jd_file.filename):
                flash("Job description must be in .txt, .docx, or .pdf format", "danger")
                return render_template("dashboard.html", username=session["username"])
            
            if len(resumes) > 10:
                flash("Maximum 10 resume files allowed", "danger")
                return render_template("dashboard.html", username=session["username"])
            
            invalid_resumes = [resume.filename for resume in resumes if not is_supported_resume_format(resume.filename)]
            if invalid_resumes:
                flash(f"Resume files must be in .pdf or .docx format. Invalid files: {', '.join(invalid_resumes)}", "danger")
                return render_template("dashboard.html", username=session["username"])

            jd_text = process_job_description(jd_file)
            jd_name = os.path.splitext(jd_file.filename)[0]
            
            session['jd_content'] = jd_text
            session['jd_filename'] = jd_file.filename
            
            # Update JD count for user
            users_data = load_users()
            if current_user_email in users_data:
                users_data[current_user_email]['jd_count'] = users_data[current_user_email].get('jd_count', 0) + 1
                save_users(users_data)

            def process_resume(resume):
                try:
                    if not is_supported_resume_format(resume.filename):
                        raise Exception(f"Unsupported resume format: {get_file_extension(resume.filename)}. Supported formats: .pdf, .docx")
                    
                    resume_content = parse_resume(resume)
                    match_result, total_score = get_match_score(resume_content, jd_text)
                    parts = re.split(r"###\s*📝 Additional Context.*?\n", match_result)
                    main_table_md = parts[0]
                    context_md = parts[1] if len(parts) > 1 else ""

                    score_df = parse_score_table(main_table_md)
                    context_df = parse_context_table(context_md) if context_md else pd.DataFrame()
                    
                    # Calculate verdict based on actual total score from parsed table
                    actual_total = score_df["Candidate Score"].sum() if not score_df.empty else total_score
                    verdict = "Shortlist" if actual_total >= 70 else "Hold" if actual_total >= 60 else "Not Relevant"
                    
                    report_name = f"{os.path.splitext(resume.filename)[0]}_evaluation_report.pdf"
                    pdf_path = convert_to_pdf(score_df, context_df, verdict, actual_total, resume.filename)
                    
                    # Prepare evaluation data for storage (but don't store in session yet)
                    blob_name = f"{jd_name}/{verdict}/{report_name}"
                    score_table = []
                    if not score_df.empty:
                        for _, row in score_df.iterrows():
                            score_table.append({
                                'criteria': row.get('Criteria', ''),
                                'max_score': row.get('Max Score', ''),
                                'candidate_score': row.get('Candidate Score', ''),
                                'explanation': row.get('Extracted / Explanation', '')
                            })
                    
                    context_table = []
                    if not context_df.empty:
                        for _, row in context_df.iterrows():
                            context_table.append({
                                'criteria': row.get('Criteria', ''),
                                'explanation': row.get('Extracted / Explanation', '')
                            })
                    
                    evaluation_data = {
                        'score_table': score_table,
                        'context_table': context_table
                    }
                    
                    if not pdf_path:
                        raise Exception("Failed to generate PDF report")
                    
                    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
                        raise Exception(f"PDF generation failed or file is empty: {pdf_path}")
                    
                    blob_name = f"{jd_name}/{verdict}/{report_name}"
                    resume_blob_name = f"{jd_name}/resumes/{resume.filename}"
                    
                    # Handle both PDF and DOCX resumes
                    if resume.filename.lower().endswith('.docx'):
                        # For DOCX resumes, convert to PDF first
                        resume.seek(0)
                        resume_temp_path = docx_to_pdf(resume)
                    else:
                        # For PDF resumes, save directly
                        resume_temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
                        resume.seek(0)
                        with open(resume_temp_path, 'wb') as f:
                            f.write(resume.read())
                    
                    if AZURE_ENABLED:
                        upload_to_azure(resume_temp_path, resume_blob_name)
                        os.unlink(resume_temp_path)
                    
                    return {
                        "name": resume.filename,
                        "verdict": verdict,
                        "total_score": int(actual_total),
                        "pdf_path": pdf_path,
                        "evaluation_details": Markup(format_evaluation_for_ui(match_result)),
                        "success": True,
                        "blob_name": blob_name,
                        "report_name": report_name,
                        "resume_blob": resume_blob_name,
                        "evaluation_data": evaluation_data
                    }
                except Exception as e:
                    return {"name": resume.filename, "error": str(e), "success": False}

            results = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(process_resume, resume) for resume in resumes]
                for future in as_completed(futures):
                    result = future.result()
                    if result["success"]:
                        if AZURE_ENABLED:
                            upload_success = upload_to_azure(result["pdf_path"], result["blob_name"])
                            if upload_success:
                                try:
                                    os.unlink(result["pdf_path"])
                                except:
                                    pass
                                
                                # Store evaluation data in session
                                if 'original_evaluation_data' not in session:
                                    session['original_evaluation_data'] = {}
                                session['original_evaluation_data'][result['blob_name']] = result['evaluation_data']
                                
                                results.append(result)
                                # Update resume count and verdict counts for user
                                users_data = load_users()
                                if current_user_email in users_data:
                                    users_data[current_user_email]['resume_count'] = users_data[current_user_email].get('resume_count', 0) + 1
                                    if result['verdict'] == 'Shortlist':
                                        users_data[current_user_email]['shortlist_count'] = users_data[current_user_email].get('shortlist_count', 0) + 1
                                    else:
                                        users_data[current_user_email]['not_shortlist_count'] = users_data[current_user_email].get('not_shortlist_count', 0) + 1
                                    save_users(users_data)
                            else:
                                flash(f"Upload failed for {result['name']}", "warning")
                        else:
                            result["blob_name"] = None
                            
                            # Store evaluation data in session even for non-Azure case
                            if 'original_evaluation_data' not in session:
                                session['original_evaluation_data'] = {}
                            session['original_evaluation_data'][result.get('blob_name', result['name'])] = result['evaluation_data']
                            
                            results.append(result)
                            # Update resume count and verdict counts for user
                            users_data = load_users()
                            if current_user_email in users_data:
                                users_data[current_user_email]['resume_count'] = users_data[current_user_email].get('resume_count', 0) + 1
                                if result['verdict'] == 'Shortlist':
                                    users_data[current_user_email]['shortlist_count'] = users_data[current_user_email].get('shortlist_count', 0) + 1
                                else:
                                    users_data[current_user_email]['not_shortlist_count'] = users_data[current_user_email].get('not_shortlist_count', 0) + 1
                                save_users(users_data)
                    else:
                        flash(f"Error processing {result['name']}: {result['error']}", "warning")
                    
            if results:
                flash(f"Successfully processed {len(results)} resumes", "success")
                return render_template("result.html", results=results)
            else:
                flash("No resumes were processed successfully", "danger")
                
        except Exception as e:
            flash(f"Processing error: {str(e)}", "danger")

    return render_template("dashboard.html", username=session["username"])

@app.route("/download_from_blob/<path:blob_name>/<report_name>")
def download_from_blob(blob_name, report_name):
    if "username" not in session and "admin" not in session:
        return "Unauthorized", 401
    
    if not AZURE_ENABLED:
        return "Cloud storage not available", 503
    
    try:
        # Check if we have updated stability data in session or request
        stability_data = request.args.get('stability_data')
        summary_message = request.args.get('summary_message', 'Resume is shortlisted can be shared with client')
        
        if stability_data:
            # If we have updated data, regenerate the PDF
            import json
            try:
                stability_data = json.loads(stability_data)
                # Here you would regenerate the PDF with updated data
                # For now, we'll use the enhanced PDF function
                # This would require the original evaluation data to be stored/retrieved
                pass
            except:
                pass
        
        # Download original PDF from Azure
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=AZURE_STORAGE_CONTAINER_NAME, blob=blob_name)
        blob_data = blob_client.download_blob().readall()
        
        if len(blob_data) == 0:
            return "File is empty", 404
        
        response = Response(
            blob_data,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{report_name}"',
                'Content-Length': str(len(blob_data))
            }
        )
        return response
        
    except Exception as e:
        print(f"Azure download error: {str(e)}")
        return "Download failed", 500

@app.route("/upload_attachment", methods=["POST"])
def upload_attachment():
    if "username" not in session and "admin" not in session:
        return {"success": False, "message": "Unauthorized"}, 401
    
    if 'file' not in request.files:
        return {"success": False, "message": "No file selected"}, 400
    
    file = request.files['file']
    if file.filename == '':
        return {"success": False, "message": "No file selected"}, 400
    
    # Save file temporarily and return path
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{secure_filename(file.filename)}")
    file.save(temp_file.name)
    temp_file.close()
    
    return {"success": True, "file_path": temp_file.name, "filename": file.filename}

@app.route("/send_email", methods=["POST"])
def send_email():
    if "username" not in session and "admin" not in session:
        return {"success": False, "message": "Unauthorized"}, 401
    
    try:
        data = request.get_json()
        to_email = data.get('email')
        blob_name = data.get('blob_name')
        report_name = data.get('report_name')
        candidate_name = data.get('candidate_name')
        verdict = data.get('verdict')
        score = data.get('score')
        custom_message = data.get('custom_message', '')
        email_subject = data.get('email_subject', f"Resume Evaluation - {data.get('candidate_name', 'Candidate')}")
        include_jd = data.get('include_jd', False)
        cc_sender = data.get('cc_sender', False)
        additional_attachments = data.get('additional_attachments', [])
        stability_data = data.get('stability_data', {})
        summary_message = data.get('summary_message', '')
        updated_evaluation_html = data.get('updated_evaluation_html', '')
        
        # Handle multiple email addresses
        email_addresses = [email.strip() for email in to_email.split(',') if email.strip()]
        if not email_addresses:
            return {"success": False, "message": "Please provide at least one valid email address"}, 400
        
        jd_content = session.get('jd_content', '')
        jd_filename = session.get('jd_filename', 'Job_Description.txt')
        
        if not all([blob_name, report_name, candidate_name]):
            return {"success": False, "message": "Missing required fields"}, 400
        
        # Check if we have updated full evaluation data first, then stability data
        updated_full_data = session.get('updated_full_evaluation', {}).get(blob_name)
        updated_stability_data = session.get('updated_stability_data', {}).get(blob_name)
        
        if updated_full_data:
            # Use full evaluation data (includes all table edits)
            report_path = generate_full_evaluation_pdf(updated_full_data, report_name)
            if not report_path:
                return {"success": False, "message": "Failed to generate updated report"}, 500
        elif updated_stability_data:
            # Use stability-only updates
            report_path = generate_updated_pdf_for_email(updated_stability_data, report_name)
            if not report_path:
                return {"success": False, "message": "Failed to generate updated report"}, 500
        else:
            # Use original PDF from Azure
            report_path = download_from_azure(blob_name)
            if not report_path:
                return {"success": False, "message": "Failed to download report"}, 500
        
        # Get resume file if available
        resume_path = None
        resume_blob = data.get('resume_blob')
        if resume_blob:
            resume_path = download_from_azure(resume_blob)
        
        jd_path = None
        if include_jd and jd_content:
            jd_path = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            jd_path.write(jd_content)
            jd_path.close()
            jd_path = jd_path.name
        
        custom_section = f"""
                <div style="background: #e8f5e8; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #28a745;">
                    <h4 style="color: #155724; margin-top: 0;">Custom Message:</h4>
                    <p style="margin: 0; white-space: pre-wrap;">{custom_message}</p>
                </div>
        """ if custom_message else ""
        
        # Build attachment list
        attachment_list = []
        if resume_path:
            attachment_list.append('📄 <strong>Original Resume</strong>')
        attachment_list.append('📊 <strong>Detailed Evaluation Report</strong>')
        if include_jd and jd_content:
            attachment_list.append('📋 <strong>Job Description</strong>')
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
                    <h2 style="margin: 0;">📄 Resume Evaluation Package</h2>
                    <p style="margin: 5px 0 0 0;">Resume Evaluator</p>
                </div>
                
                {custom_section}
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #667eea;">
                    <h3 style="color: #495057; margin-top: 0;">📊 Candidate Information</h3>
                    <p><strong>Candidate:</strong> {candidate_name}</p>
                    <p><strong>Evaluation Status:</strong> <span style="background: {'#28a745' if verdict == 'Shortlist' else '#ffc107' if verdict == 'Hold' else '#dc3545'}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{verdict}</span></p>
                    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div style="background: white; padding: 20px; border: 1px solid #dee2e6; border-radius: 8px;">
                    <h4 style="color: #667eea; margin-top: 0;">📎 Attachments Included:</h4>
                    <ul>
                        {''.join(f'<li>{item}</li>' for item in attachment_list)}
                    </ul>
                    <p><strong>Next Steps:</strong> Review attachments and proceed as needed.</p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 12px;">
                    <p>Generated by Resume Evaluator<br>
                    © 2025. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        attachments = []
        if resume_path:
            resume_filename = f"{candidate_name}_Resume.pdf"
            attachments.append((resume_path, resume_filename))
        attachments.append((report_path, report_name))
        if jd_path:
            jd_attachment_name = f"JD_{os.path.splitext(jd_filename)[0]}_{datetime.now().strftime('%Y%m%d')}.txt"
            attachments.append((jd_path, jd_attachment_name))
        
        # Add additional attachments
        for att in additional_attachments:
            if os.path.exists(att['file_path']):
                attachments.append((att['file_path'], att['filename']))
        
        # Send to all email addresses
        success_count = 0
        failed_emails = []
        
        for email_addr in email_addresses:
            success, message = send_email_with_attachments(email_addr, email_subject, body, attachments)
            if success:
                success_count += 1
            else:
                failed_emails.append(f"{email_addr}: {message}")
        
        # Send copy to sender if requested
        if cc_sender and session.get('username'):
            sender_email = session.get('username')
            if sender_email not in email_addresses:
                cc_body = f"""<div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
                    <p style="margin: 0;"><strong>Note:</strong> This is a copy of the email sent to: {', '.join(email_addresses)}</p>
                </div>
                {body}"""
                send_email_with_attachments(sender_email, f"[COPY] {email_subject}", cc_body, attachments)
        
        # Cleanup files
        try:
            os.unlink(report_path)
            if resume_path:
                os.unlink(resume_path)
            if jd_path:
                os.unlink(jd_path)
            # Cleanup additional attachments
            for att in additional_attachments:
                if os.path.exists(att['file_path']):
                    os.unlink(att['file_path'])
        except:
            pass
        
        if success_count == len(email_addresses):
            return {"success": True, "message": f"Email sent successfully to {success_count} recipient(s)"}
        elif success_count > 0:
            return {"success": True, "message": f"Email sent to {success_count}/{len(email_addresses)} recipients. Failed: {'; '.join(failed_emails)}"}
        else:
            return {"success": False, "message": f"Failed to send to all recipients: {'; '.join(failed_emails)}"}
        
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}, 500

@app.route("/send_combined_email", methods=["POST"])
def send_combined_email():
    if "username" not in session and "admin" not in session:
        return {"success": False, "message": "Unauthorized"}, 401
    
    try:
        data = request.get_json()
        to_email = data.get('email')
        blob_name = data.get('blob_name')
        candidate_name = data.get('candidate_name')
        verdict = data.get('verdict')
        score = data.get('score')
        custom_message = data.get('custom_message', '')
        resume_blob = data.get('resume_blob')
        email_subject = data.get('email_subject', f"Combined Resume Package - {data.get('candidate_name', 'Candidate')}")
        include_jd = data.get('include_jd', False)
        cc_sender = data.get('cc_sender', False)
        stability_data = data.get('stability_data', {})
        summary_message = data.get('summary_message', '')
        updated_evaluation_html = data.get('updated_evaluation_html', '')
        
        # Handle multiple email addresses
        email_addresses = [email.strip() for email in to_email.split(',') if email.strip()]
        if not email_addresses:
            return {"success": False, "message": "Please provide at least one valid email address"}, 400
        
        jd_content = session.get('jd_content', '')
        jd_filename = session.get('jd_filename', 'Job_Description.txt')
        
        if not all([blob_name, candidate_name, resume_blob]):
            return {"success": False, "message": "Missing required fields"}, 400
        
        # Check if we have updated full evaluation data first, then stability data
        updated_full_data = session.get('updated_full_evaluation', {}).get(blob_name)
        updated_stability_data = session.get('updated_stability_data', {}).get(blob_name)
        
        if updated_full_data:
            report_path = generate_full_evaluation_pdf(updated_full_data, f"{candidate_name}_evaluation_report.pdf")
        elif updated_stability_data:
            report_path = generate_updated_pdf_for_email(updated_stability_data, f"{candidate_name}_evaluation_report.pdf")
        else:
            report_path = download_from_azure(blob_name)
        
        resume_path = download_from_azure(resume_blob)
        
        if not report_path or not resume_path:
            return {"success": False, "message": "Failed to download files"}, 500
        
        combined_filename = f"{candidate_name}_Combined_Package.pdf"
        
        # Combine Report + Resume
        combined_path = merge_resume_and_report(resume_path, report_path, combined_filename)
        
        if not combined_path:
            return {"success": False, "message": "Failed to merge PDFs"}, 500
        
        # Prepare JD attachment if requested
        jd_path = None
        if include_jd and jd_content:
            jd_path = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            jd_path.write(jd_content)
            jd_path.close()
            jd_path = jd_path.name
        
        custom_section = f"""
                <div style="background: #e8f5e8; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #28a745;">
                    <h4 style="color: #155724; margin-top: 0;">Custom Message:</h4>
                    <p style="margin: 0; white-space: pre-wrap;">{custom_message}</p>
                </div>
        """ if custom_message else ""
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
                    <h2 style="margin: 0;"> Combined Resume Package</h2>
                    <p style="margin: 5px 0 0 0;">Resume Evaluator</p>
                </div>
                
                {custom_section}
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #667eea;">
                    <h3 style="color: #495057; margin-top: 0;">📊 Candidate Information</h3>
                    <p><strong>Candidate:</strong> {candidate_name}</p>
                    <p><strong>Evaluation Status:</strong> <span style="background: {'#28a745' if verdict == 'Shortlist' else '#ffc107' if verdict == 'Hold' else '#dc3545'}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{verdict}</span></p>
                    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div style="background: white; padding: 20px; border: 1px solid #dee2e6; border-radius: 8px;">
                    <h4 style="color: #667eea; margin-top: 0;">📎 Attachments Included:</h4>
                    <ul>
                        <li>📄 <strong>Combined PDF</strong> - Resume + Evaluation Report in single file</li>
                        {f'<li>📋 <strong>Job Description</strong> - Original JD used for matching</li>' if include_jd and jd_content else ''}
                    </ul>
                    <p><strong>Note:</strong> Resume and evaluation report are combined in a single PDF for your convenience.</p>
                    <p><strong>Next Steps:</strong> Review the package and proceed as needed.</p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 12px;">
                    <p>Generated by Resume Evaluator<br>
                    © 2025. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        additional_attachments = data.get('additional_attachments', [])
        
        attachments = [(combined_path, combined_filename)]
        if jd_path:
            jd_attachment_name = f"JD_{os.path.splitext(jd_filename)[0]}_{datetime.now().strftime('%Y%m%d')}.txt"
            attachments.append((jd_path, jd_attachment_name))
        
        # Add additional attachments
        for att in additional_attachments:
            if os.path.exists(att['file_path']):
                attachments.append((att['file_path'], att['filename']))
        
        # Send to all email addresses
        success_count = 0
        failed_emails = []
        
        for email_addr in email_addresses:
            success, message = send_email_with_attachments(email_addr, email_subject, body, attachments)
            if success:
                success_count += 1
            else:
                failed_emails.append(f"{email_addr}: {message}")
        
        # Send copy to sender if requested
        if cc_sender and session.get('username'):
            sender_email = session.get('username')
            if sender_email not in email_addresses:
                cc_body = f"""<div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
                    <p style="margin: 0;"><strong>Note:</strong> This is a copy of the email sent to: {', '.join(email_addresses)}</p>
                </div>
                {body}"""
                send_email_with_attachments(sender_email, f"[COPY] {email_subject}", cc_body, attachments)
        
        # Cleanup files
        try:
            os.unlink(report_path)
            os.unlink(resume_path)
            os.unlink(combined_path)
            if jd_path:
                os.unlink(jd_path)
            # Cleanup additional attachments
            for att in additional_attachments:
                if os.path.exists(att['file_path']):
                    os.unlink(att['file_path'])
        except:
            pass
        
        if success_count == len(email_addresses):
            return {"success": True, "message": f"Combined package sent successfully to {success_count} recipient(s)"}
        elif success_count > 0:
            return {"success": True, "message": f"Email sent to {success_count}/{len(email_addresses)} recipients. Failed: {'; '.join(failed_emails)}"}
        else:
            return {"success": False, "message": f"Failed to send to all recipients: {'; '.join(failed_emails)}"}
        
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}, 500

@app.route("/update_stability_data", methods=["POST"])
def update_stability_data():
    if "username" not in session and "admin" not in session:
        return {"success": False, "message": "Unauthorized"}, 401
    
    try:
        data = request.get_json()
        blob_name = data.get('blob_name')
        candidate_name = data.get('candidate_name')
        stability_jd_score = data.get('stability_jd_score')
        stability_candidate_score = data.get('stability_candidate_score')
        stability_explanation = data.get('stability_explanation')
        total_score = data.get('total_score')
        
        # Store updated data in session for PDF regeneration
        if 'updated_stability_data' not in session:
            session['updated_stability_data'] = {}
        
        session['updated_stability_data'][blob_name] = {
            'jd_score': stability_jd_score,
            'candidate_score': stability_candidate_score,
            'explanation': stability_explanation,
            'total_score': total_score,
            'candidate_name': candidate_name
        }
        
        # Store original evaluation data if not already stored
        original_evaluation_data = data.get('original_evaluation_data')
        if original_evaluation_data and 'original_evaluation_data' not in session:
            session['original_evaluation_data'] = {}
        if original_evaluation_data:
            session['original_evaluation_data'][blob_name] = original_evaluation_data
        
        print(f"Stability data updated for {candidate_name}: JD={stability_jd_score}, Candidate={stability_candidate_score}, Total={total_score}")
        
        return {"success": True, "message": "Stability data updated successfully"}
        
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}, 500

@app.route("/update_full_evaluation", methods=["POST"])
def update_full_evaluation():
    if "username" not in session and "admin" not in session:
        return {"success": False, "message": "Unauthorized"}, 401
    
    try:
        data = request.get_json()
        blob_name = data.get('blob_name')
        candidate_name = data.get('candidate_name')
        score_table = data.get('score_table', [])
        context_table = data.get('context_table', [])
        total_score = data.get('total_score')
        
        # Generate updated PDF with full evaluation data
        logo_base64 = get_logo_base64()
        
        eval_rows = ""
        for row in score_table:
            eval_rows += f"""
            <tr>
                <td style="width: 40%; font-weight: bold;">{row.get('criteria', '')}</td>
                <td style="width: 15%; text-align: center;">{row.get('max_score', '')}</td>
                <td style="width: 15%; text-align: center; font-weight: bold; color: #667eea;">{row.get('candidate_score', '')}</td>
                <td style="width: 30%;">{row.get('explanation', '')}</td>
            </tr>
            """
        
        context_rows = ""
        for row in context_table:
            context_rows += f"""
            <tr>
                <td style="width: 30%; font-weight: bold;">{row.get('criteria', '')}</td>
                <td style="width: 70%;">{row.get('explanation', '')}</td>
            </tr>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ size: A4; margin: 0.5cm; }}
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; line-height: 1.2; color: #333; font-size: 9px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; border-radius: 4px; margin-bottom: 10px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 14px; }}
                .header p {{ margin: 3px 0 0 0; font-size: 10px; }}
                .section {{ margin-bottom: 10px; }}
                .section h2 {{ color: #667eea; border-bottom: 1px solid #667eea; padding-bottom: 2px; margin-bottom: 8px; font-size: 11px; margin-top: 5px; }}
                .table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 8px; }}
                .table th {{ background-color: #667eea; color: white; border: 1px solid #dee2e6; padding: 4px; text-align: left; font-weight: bold; }}
                .table td {{ border: 1px solid #dee2e6; padding: 3px; vertical-align: top; word-wrap: break-word; }}
                .table tr:nth-child(even) {{ background-color: #f8f9fa; }}
                .summary-box {{ margin-bottom: 10px; }}
                .score-box {{ background-color: #28a745; color: white; padding: 8px; border-radius: 4px; text-align: center; }}
                .summary-section {{ margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }}
                .footer {{ position: fixed; bottom: 0.5cm; left: 0.5cm; right: 0.5cm; text-align: center; color: #666; font-size: 7px; border-top: 1px solid #dee2e6; padding-top: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                {f'<img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 40px; margin-bottom: 5px;"><br>' if logo_base64 else ''}
                <h1>Resume Evaluation Report (Updated)</h1>
                <p>Candidate: {candidate_name}</p>
            </div>
            
            <div class="section">
                <h2>📊 Detailed Evaluation Scores</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Evaluation Criteria</th>
                            <th>Max Score</th>
                            <th>Candidate Score</th>
                            <th>Extracted / Explanation</th>
                        </tr>
                    </thead>
                    <tbody>
                        {eval_rows}
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>📝 Additional Context (No Score, Mandatory Explanation)</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Criteria</th>
                            <th>Extracted / Explanation</th>
                        </tr>
                    </thead>
                    <tbody>
                        {context_rows}
                    </tbody>
                </table>
            </div>
            
            <div class="summary-box">
                <div class="score-box" style="width: 100%; background-color: #28a745; color: white;">
                    <h3 style="margin: 0; font-size: 12px;">Resume is Shortlisted can be shared with Client</h3>
                </div>
            </div>
            
            <div class="summary-section">
                <h3 style="color: #667eea; margin-top: 0; font-size: 10px;">📋 Report Summary</h3>
                <p style="margin: 2px 0;"><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p style="margin: 2px 0;"><strong>Status:</strong> Updated by Reviewer</p>
            </div>
            
            <div class="footer">
                <p>Generated by Resume Evaluator | © 2025. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        # Generate updated PDF
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_path = temp_file.name
        temp_file.close()
        
        with open(temp_path, "wb") as f:
            pisa_status = pisa.CreatePDF(html, dest=f, encoding='utf-8')
            if pisa_status.err:
                return {"success": False, "message": "PDF generation failed"}, 500
        
        # Store updated data in session for email functionality
        if 'updated_full_evaluation' not in session:
            session['updated_full_evaluation'] = {}
        
        session['updated_full_evaluation'][blob_name] = {
            'score_table': score_table,
            'context_table': context_table,
            'total_score': total_score,
            'candidate_name': candidate_name
        }
        
        # Upload updated PDF to Azure
        if AZURE_ENABLED:
            upload_success = upload_to_azure(temp_path, blob_name)
            if upload_success:
                os.unlink(temp_path)
                return {"success": True, "message": "Full evaluation updated and saved to Azure"}
            else:
                os.unlink(temp_path)
                return {"success": False, "message": "Failed to upload to Azure"}, 500
        else:
            os.unlink(temp_path)
            return {"success": True, "message": "Full evaluation updated (Azure not configured)"}
        
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}, 500

@app.route("/download_updated_pdf/<path:blob_name>/<report_name>")
def download_updated_pdf(blob_name, report_name):
    """Download PDF with updated stability data if available"""
    if "username" not in session and "admin" not in session:
        return "Unauthorized", 401
    
    try:
        # Check if we have updated stability data for this report
        updated_data = session.get('updated_stability_data', {}).get(blob_name)
        
        if updated_data:
            # We need to store the original evaluation data to regenerate the full table
            # For now, we'll use the updated data and create a complete evaluation table
            logo_base64 = get_logo_base64()
            
            # Get original evaluation data from session
            original_data = session.get('original_evaluation_data', {}).get(blob_name, {})
            print(f"Debug: Original data keys: {list(original_data.keys()) if original_data else 'No data'}")
            
            eval_rows = ""
            context_rows = ""
            
            # Build evaluation rows from original data
            if 'score_table' in original_data and original_data['score_table']:
                print(f"Debug: Found {len(original_data['score_table'])} score table rows")
                for row in original_data['score_table']:
                    criteria = row.get('criteria', '')
                    max_score = row.get('max_score', '')
                    candidate_score = row.get('candidate_score', '')
                    explanation = row.get('explanation', '')
                    
                    # Use updated data for stability row
                    if 'stability' in criteria.lower():
                        candidate_score = updated_data['candidate_score']
                        explanation = updated_data['explanation']
                    
                    eval_rows += f"""
                    <tr>
                        <td style="width: 40%; font-weight: bold;">{criteria}</td>
                        <td style="width: 15%; text-align: center;">{max_score}</td>
                        <td style="width: 15%; text-align: center; font-weight: bold; color: #667eea;">{candidate_score}</td>
                        <td style="width: 30%;">{explanation}</td>
                    </tr>
                    """
            else:
                print("Debug: No score_table found, falling back to original PDF")
                # Fallback: Download original PDF and redirect to it with updated stability message
                return redirect(url_for('download_from_blob', blob_name=blob_name, report_name=report_name))
            
            # Build context rows from original data
            if 'context_table' in original_data and original_data['context_table']:
                print(f"Debug: Found {len(original_data['context_table'])} context table rows")
                for row in original_data['context_table']:
                    criteria = row.get('criteria', '')
                    explanation = row.get('explanation', '')
                    context_rows += f"""
                    <tr>
                        <td style="width: 30%; font-weight: bold;">{criteria}</td>
                        <td style="width: 70%;">{explanation}</td>
                    </tr>
                    """
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    @page {{ size: A4; margin: 0.5cm; }}
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; line-height: 1.2; color: #333; font-size: 9px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; border-radius: 4px; margin-bottom: 10px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 14px; }}
                    .header p {{ margin: 3px 0 0 0; font-size: 10px; }}
                    .section {{ margin-bottom: 10px; }}
                    .section h2 {{ color: #667eea; border-bottom: 1px solid #667eea; padding-bottom: 2px; margin-bottom: 8px; font-size: 11px; margin-top: 5px; }}
                    .table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 8px; }}
                    .table th {{ background-color: #667eea; color: white; border: 1px solid #dee2e6; padding: 4px; text-align: left; font-weight: bold; }}
                    .table td {{ border: 1px solid #dee2e6; padding: 3px; vertical-align: top; word-wrap: break-word; }}
                    .table tr:nth-child(even) {{ background-color: #f8f9fa; }}
                    .updated-row {{ background-color: #e8f5e8 !important; border: 2px solid #28a745 !important; }}
                    .summary-box {{ margin-bottom: 10px; }}
                    .score-box {{ background-color: #28a745; color: white; padding: 8px; border-radius: 4px; text-align: center; }}
                    .summary-section {{ margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }}
                    .footer {{ position: fixed; bottom: 0.5cm; left: 0.5cm; right: 0.5cm; text-align: center; color: #666; font-size: 7px; border-top: 1px solid #dee2e6; padding-top: 5px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    {f'<img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 40px; margin-bottom: 5px;"><br>' if logo_base64 else ''}
                    <h1>Resume Evaluation Report (Updated)</h1>
                    <p>Candidate: {updated_data['candidate_name']}</p>
                </div>
                
                <div class="section">
                    <h2>📊 Detailed Evaluation Scores</h2>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Evaluation Criteria</th>
                                <th>Max Score</th>
                                <th>Candidate Score</th>
                                <th>Extracted / Explanation</th>
                            </tr>
                        </thead>
                        <tbody>
                            {eval_rows}
                        </tbody>
                    </table>
                </div>
                
                <div class="section">
                    <h2>📋 Additional Context (No Score, Mandatory Explanation)</h2>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Criteria</th>
                                <th>Extracted / Explanation</th>
                            </tr>
                        </thead>
                        <tbody>
                            {context_rows}
                        </tbody>
                    </table>
                </div>
                
                <div class="summary-box">
                    <div class="score-box" style="width: 100%; background-color: #28a745; color: white;">
                        <h3 style="margin: 0; font-size: 12px;">Resume is Shortlisted can be shared with Client</h3>
                    </div>
                </div>
                
                <div class="summary-section">
                    <h3 style="color: #667eea; margin-top: 0; font-size: 10px;">📋 Report Summary</h3>
                    <p style="margin: 2px 0;"><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p style="margin: 2px 0;"><strong>Status:</strong> Updated by Reviewer</p>
                    <p style="margin: 2px 0;"><strong>Changes:</strong> Stability assessment modified</p>
                </div>
                
                <div class="footer">
                    <p>Generated by Resume Evaluator | © 2025. All rights reserved.</p>
                </div>
            </body>
            </html>
            """
            
            # Generate updated PDF
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_path = temp_file.name
            temp_file.close()
            
            with open(temp_path, "wb") as f:
                pisa_status = pisa.CreatePDF(html, dest=f, encoding='utf-8')
                if pisa_status.err:
                    os.unlink(original_pdf_path)
                    return "PDF generation failed", 500
            
            # Read the updated PDF
            with open(temp_path, 'rb') as f:
                pdf_data = f.read()
            
            # Cleanup
            os.unlink(temp_path)
            
            response = Response(
                pdf_data,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename="Updated_{report_name}"',
                    'Content-Length': str(len(pdf_data))
                }
            )
            return response
        
        else:
            # No updated data, redirect to original download
            return redirect(url_for('download_from_blob', blob_name=blob_name, report_name=report_name))
        
    except Exception as e:
        print(f"Updated PDF download error: {str(e)}")
        return "Download failed", 500

def generate_updated_pdf_for_email(updated_data, filename):
    """Generate updated PDF for email attachments"""
    logo_base64 = get_logo_base64()
    
    # Get original evaluation data from session
    original_data = session.get('evaluation_data', {})
    
    # Build evaluation rows dynamically
    eval_rows = ""
    if 'evaluation_table' in original_data:
        for row in original_data['evaluation_table']:
            criteria = row.get('criteria', '')
            jd_score = row.get('jd_score', '')
            candidate_score = row.get('candidate_score', '')
            explanation = row.get('explanation', '')
            
            # Use updated data for stability row
            if 'stability' in criteria.lower():
                candidate_score = updated_data['candidate_score']
                explanation = updated_data['explanation']
            
            eval_rows += f"""
            <tr>
                <td style="width: 40%; font-weight: bold;">{criteria}</td>
                <td style="width: 15%; text-align: center;">{jd_score}</td>
                <td style="width: 15%; text-align: center; font-weight: bold; color: #667eea;">{candidate_score}</td>
                <td style="width: 30%;">{explanation}</td>
            </tr>
            """
    
    # Build context rows dynamically
    context_rows = ""
    if 'context_table' in original_data:
        for row in original_data['context_table']:
            criteria = row.get('criteria', '')
            explanation = row.get('explanation', '')
            context_rows += f"""
            <tr>
                <td style="width: 30%; font-weight: bold;">{criteria}</td>
                <td style="width: 70%;">{explanation}</td>
            </tr>
            """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 0.5cm; }}
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; line-height: 1.2; color: #333; font-size: 9px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; border-radius: 4px; margin-bottom: 10px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 14px; }}
            .header p {{ margin: 3px 0 0 0; font-size: 10px; }}
            .section {{ margin-bottom: 10px; }}
            .section h2 {{ color: #667eea; border-bottom: 1px solid #667eea; padding-bottom: 2px; margin-bottom: 8px; font-size: 11px; margin-top: 5px; }}
            .table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 8px; }}
            .table th {{ background-color: #667eea; color: white; border: 1px solid #dee2e6; padding: 4px; text-align: left; font-weight: bold; }}
            .table td {{ border: 1px solid #dee2e6; padding: 3px; vertical-align: top; word-wrap: break-word; }}
            .table tr:nth-child(even) {{ background-color: #f8f9fa; }}
            .summary-box {{ margin-bottom: 10px; }}
            .score-box {{ background-color: #28a745; color: white; padding: 8px; border-radius: 4px; text-align: center; }}
            .summary-section {{ margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }}
            .footer {{ position: fixed; bottom: 0.5cm; left: 0.5cm; right: 0.5cm; text-align: center; color: #666; font-size: 7px; border-top: 1px solid #dee2e6; padding-top: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 40px; margin-bottom: 5px;"><br>' if logo_base64 else ''}
            <h1>Resume Evaluation Report</h1>
            <p>Candidate: {updated_data['candidate_name']}</p>
        </div>
        
        <div class="section">
            <h2>📊 Detailed Evaluation Scores</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Evaluation Criteria</th>
                        <th>Max Score</th>
                        <th>Candidate Score</th>
                        <th>Extracted / Explanation</th>
                    </tr>
                </thead>
                <tbody>
                    {eval_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📝 Additional Context (No Score, Mandatory Explanation)</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Criteria</th>
                        <th>Extracted / Explanation</th>
                    </tr>
                </thead>
                <tbody>
                    {context_rows}
                </tbody>
            </table>
        </div>
        
        <div class="summary-box">
            <div class="score-box" style="width: 100%; background-color: #28a745; color: white;">
                <h3 style="margin: 0; font-size: 12px;">Resume is Shortlisted can be shared with Client</h3>
            </div>
        </div>
        
        <div class="summary-section">
            <h3 style="color: #667eea; margin-top: 0; font-size: 10px;">📋 Report Summary</h3>
            <p style="margin: 2px 0;"><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin: 2px 0;"><strong>Evaluation Method:</strong> AI-Powered Resume Matching</p>
            <p style="margin: 2px 0;"><strong>Total Score:</strong> {updated_data['total_score']}/100</p>
        </div>
        
        <div class="footer">
            <p>Generated by Resume Evaluator | © 2025. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_path = temp_file.name
        temp_file.close()
        
        with open(temp_path, "wb") as f:
            pisa_status = pisa.CreatePDF(html, dest=f, encoding='utf-8', show_error_as_pdf=True)
            if pisa_status.err:
                print(f"❌ PDF generation errors: {pisa_status.err}")
                return None
        
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            return temp_path
        else:
            print(f"❌ PDF file is empty or doesn't exist")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    except Exception as e:
        print(f"❌ Updated PDF generation error: {e}")
        return None

def generate_full_evaluation_pdf(full_eval_data, filename):
    """Generate PDF from full evaluation data"""
    logo_base64 = get_logo_base64()
    
    eval_rows = ""
    for row in full_eval_data['score_table']:
        eval_rows += f"""
        <tr>
            <td style="width: 40%; font-weight: bold;">{row['criteria']}</td>
            <td style="width: 15%; text-align: center;">{row['max_score']}</td>
            <td style="width: 15%; text-align: center; font-weight: bold; color: #667eea;">{row['candidate_score']}</td>
            <td style="width: 30%;">{row['explanation']}</td>
        </tr>
        """
    
    context_rows = ""
    for row in full_eval_data['context_table']:
        context_rows += f"""
        <tr>
            <td style="width: 30%; font-weight: bold;">{row['criteria']}</td>
            <td style="width: 70%;">{row['explanation']}</td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 0.5cm; }}
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; line-height: 1.2; color: #333; font-size: 9px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; border-radius: 4px; margin-bottom: 10px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 14px; }}
            .header p {{ margin: 3px 0 0 0; font-size: 10px; }}
            .section {{ margin-bottom: 10px; }}
            .section h2 {{ color: #667eea; border-bottom: 1px solid #667eea; padding-bottom: 2px; margin-bottom: 8px; font-size: 11px; margin-top: 5px; }}
            .table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 8px; }}
            .table th {{ background-color: #667eea; color: white; border: 1px solid #dee2e6; padding: 4px; text-align: left; font-weight: bold; }}
            .table td {{ border: 1px solid #dee2e6; padding: 3px; vertical-align: top; word-wrap: break-word; }}
            .table tr:nth-child(even) {{ background-color: #f8f9fa; }}
            .summary-box {{ margin-bottom: 10px; }}
            .score-box {{ background-color: #28a745; color: white; padding: 8px; border-radius: 4px; text-align: center; }}
            .summary-section {{ margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }}
            .footer {{ position: fixed; bottom: 0.5cm; left: 0.5cm; right: 0.5cm; text-align: center; color: #666; font-size: 7px; border-top: 1px solid #dee2e6; padding-top: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 40px; margin-bottom: 5px;"><br>' if logo_base64 else ''}
            <h1>Resume Evaluation Report (Updated)</h1>
            <p>Candidate: {full_eval_data['candidate_name']}</p>
        </div>
        
        <div class="section">
            <h2>📊 Detailed Evaluation Scores</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Evaluation Criteria</th>
                        <th>Max Score</th>
                        <th>Candidate Score</th>
                        <th>Extracted / Explanation</th>
                    </tr>
                </thead>
                <tbody>
                    {eval_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📝 Additional Context (No Score, Mandatory Explanation)</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Criteria</th>
                        <th>Extracted / Explanation</th>
                    </tr>
                </thead>
                <tbody>
                    {context_rows}
                </tbody>
            </table>
        </div>
        
        <div class="summary-box">
            <div class="score-box" style="width: 100%; background-color: #28a745; color: white;">
                <h3 style="margin: 0; font-size: 12px;">Resume is Shortlisted can be shared with Client</h3>
            </div>
        </div>
        
        <div class="summary-section">
            <h3 style="color: #667eea; margin-top: 0; font-size: 10px;">📋 Report Summary</h3>
            <p style="margin: 2px 0;"><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin: 2px 0;"><strong>Status:</strong> Updated by Reviewer</p>
        </div>
        
        <div class="footer">
            <p>Generated by Resume Evaluator | © 2025. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_path = temp_file.name
        temp_file.close()
        
        with open(temp_path, "wb") as f:
            pisa_status = pisa.CreatePDF(html, dest=f, encoding='utf-8')
            if pisa_status.err:
                return None
        
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            return temp_path
        else:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    except Exception as e:
        print(f"❌ Full evaluation PDF generation error: {e}")
        return None

def convert_to_pdf_with_updates(score_df, context_df, verdict, total_score, file_name="evaluation", stability_data=None, summary_message=None):
    """Enhanced PDF generation with updated stability data and custom summary"""
    verdict_color = '#28a745' if verdict == 'Shortlist' else '#ffc107' if verdict == 'Hold' else '#dc3545'
    logo_base64 = get_logo_base64()
    
    # Use custom summary message if provided
    summary_text = summary_message or f"Total Score: {total_score}/100"

    eval_rows = ''
    if not score_df.empty:
        for _, row in score_df.iterrows():
            criteria = row.get('Criteria') or str(row.iloc[0] if len(row) > 0 else '')
            candidate_score = row.get('Candidate Score') or row.get('Score') or str(row.iloc[1] if len(row) > 1 else '')
            max_score = row.get('Max Score') or str(row.iloc[2] if len(row) > 2 else '')
            explanation = row.get('Explanation') or str(row.iloc[3] if len(row) > 3 else '')
            
            # Update stability row with new data if provided
            if stability_data and 'stability' in criteria.lower():
                candidate_score = stability_data.get('candidate_score', candidate_score)
                explanation = stability_data.get('explanation', explanation)
            
            eval_rows += f"""
            <tr>
                <td style="width: 40%; font-weight: bold;">{criteria}</td>
                <td style="width: 15%; text-align: center; font-weight: bold; color: #667eea;">{candidate_score}</td>
                <td style="width: 15%; text-align: center;">{max_score}</td>
                <td style="width: 30%;">{explanation}</td>
            </tr>
            """
    
    context_rows = ''
    if not context_df.empty:
        for _, row in context_df.iterrows():
            criteria = row.get('Criteria') or str(row.iloc[0] if len(row) > 0 else '')
            details = row.get('Extracted / Explanation') or str(row.iloc[1] if len(row) > 1 else '')
            context_rows += f"""
            <tr>
                <td style="width: 30%; font-weight: bold;">{criteria}</td>
                <td style="width: 70%;">{details}</td>
            </tr>
            """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 0.5cm; }}
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; line-height: 1.2; color: #333; font-size: 9px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; border-radius: 4px; margin-bottom: 10px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 14px; }}
            .header p {{ margin: 3px 0 0 0; font-size: 10px; }}
            .summary-box {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
            .score-box {{ background-color: #f8f9fa; padding: 8px; border-radius: 4px; text-align: center; width: 48%; border: 1px solid #dee2e6; }}
            .verdict-box {{ background-color: {verdict_color}; color: white; padding: 8px; border-radius: 4px; text-align: center; width: 48%; }}
            .section {{ margin-bottom: 10px; }}
            .section h2 {{ color: #667eea; border-bottom: 1px solid #667eea; padding-bottom: 2px; margin-bottom: 8px; font-size: 11px; margin-top: 5px; }}
            .table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 8px; }}
            .table th {{ background-color: #667eea; color: white; border: 1px solid #dee2e6; padding: 4px; text-align: left; font-weight: bold; }}
            .table td {{ border: 1px solid #dee2e6; padding: 3px; vertical-align: top; word-wrap: break-word; }}
            .table tr:nth-child(even) {{ background-color: #f8f9fa; }}
            .summary-section {{ margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }}
            .footer {{ position: fixed; bottom: 0.5cm; left: 0.5cm; right: 0.5cm; text-align: center; color: #666; font-size: 7px; border-top: 1px solid #dee2e6; padding-top: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 40px; margin-bottom: 5px;"><br>' if logo_base64 else ''}
            <h1>Resume Evaluation Report</h1>
            <p>Candidate: {os.path.splitext(file_name)[0].replace('_', ' ')}</p>
        </div>
        
        <div class="section">
            <h2>📊 Detailed Evaluation Scores</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Evaluation Criteria</th>
                        <th>Max Score</th>
                        <th>Candidate Score</th>
                        <th>Extracted / Explanation</th>
                    </tr>
                </thead>
                <tbody>
                    {eval_rows if eval_rows else '<tr><td colspan="4" style="text-align: center; color: #666;">No evaluation data available</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📝 Additional Context (No Score, Mandatory Explanation)</h2>
            {f'''
            <table class="table">
                <thead>
                    <tr>
                        <th>Criteria</th>
                        <th>Extracted / Explanation</th>
                    </tr>
                </thead>
                <tbody>
                    {context_rows}
                </tbody>
            </table>
            ''' if context_rows else '<p style="color: #666; font-style: italic; text-align: center; padding: 20px;">No additional context available</p>'}
        </div>
        
        <div class="summary-box">
            <div class="score-box" style="width: 100%; background-color: #28a745; color: white;">
                <h3 style="margin: 0; font-size: 12px;">Evaluation Summary</h3>
                <div style="font-size: 12px; font-weight: bold; margin: 5px 0;">{summary_text}</div>
            </div>
        </div>
        
        <div class="summary-section">
            <h3 style="color: #667eea; margin-top: 0; font-size: 10px;">📋 Report Summary</h3>
            <p style="margin: 2px 0;"><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin: 2px 0;"><strong>Evaluation Method:</strong> AI-Powered Resume Matching</p>
            <p style="margin: 2px 0;"><strong>Status:</strong> Ready for Review</p>
        </div>
        
        <div class="footer">
            <p>Generated by Resume Evaluator | © 2025. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_path = temp_file.name
        temp_file.close()
        
        with open(temp_path, "wb") as f:
            pisa_status = pisa.CreatePDF(html, dest=f, encoding='utf-8', show_error_as_pdf=True)
            if pisa_status.err:
                return None
        
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            return temp_path
        else:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    except Exception as e:
        print(f"❌ PDF generation exception: {e}")
        return None

@app.route("/send_complete_package", methods=["POST"])
def send_complete_package():
    """Send email with JD + Resume + Report combined in a single PDF"""
    if "username" not in session and "admin" not in session:
        return {"success": False, "message": "Unauthorized"}, 401
    
    try:
        data = request.get_json()
        to_email = data.get('email')
        blob_name = data.get('blob_name')
        candidate_name = data.get('candidate_name')
        verdict = data.get('verdict')
        score = data.get('score')
        custom_message = data.get('custom_message', '')
        resume_blob = data.get('resume_blob')
        email_subject = data.get('email_subject', f"Complete Package - {data.get('candidate_name', 'Candidate')}")
        include_jd = data.get('include_jd', True)  # Default to True for complete package
        cc_sender = data.get('cc_sender', False)
        additional_attachments = data.get('additional_attachments', [])
        stability_data = data.get('stability_data', {})
        summary_message = data.get('summary_message', '')
        updated_evaluation_html = data.get('updated_evaluation_html', '')
        
        # Handle multiple email addresses
        email_addresses = [email.strip() for email in to_email.split(',') if email.strip()]
        if not email_addresses:
            return {"success": False, "message": "Please provide at least one valid email address"}, 400
        
        jd_content = session.get('jd_content', '')
        jd_filename = session.get('jd_filename', 'Job_Description.txt')
        
        if not all([blob_name, candidate_name, resume_blob]):
            return {"success": False, "message": "Missing required fields"}, 400
        
        # Check if we have updated full evaluation data first, then stability data
        updated_full_data = session.get('updated_full_evaluation', {}).get(blob_name)
        updated_stability_data = session.get('updated_stability_data', {}).get(blob_name)
        
        if updated_full_data:
            report_path = generate_full_evaluation_pdf(updated_full_data, f"{candidate_name}_evaluation_report.pdf")
        elif updated_stability_data:
            report_path = generate_updated_pdf_for_email(updated_stability_data, f"{candidate_name}_evaluation_report.pdf")
        else:
            report_path = download_from_azure(blob_name)
        
        resume_path = download_from_azure(resume_blob)
        
        if not report_path or not resume_path:
            return {"success": False, "message": "Failed to download files"}, 500
        
        combined_filename = f"{candidate_name}_Complete_Package.pdf"
        
        # Create complete package with JD if requested
        if include_jd and jd_content:
            # Create JD PDF first
            jd_path = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            jd_path.write(jd_content)
            jd_path.close()
            jd_path = jd_path.name
            
            # Use the merge function that includes JD
            combined_path = merge_with_jd_and_report(jd_path, resume_path, report_path, combined_filename)
            
            # Cleanup JD temp file
            try:
                os.unlink(jd_path)
            except:
                pass
        else:
            # Just merge resume + report
            combined_path = merge_resume_and_report(resume_path, report_path, combined_filename)
        
        if not combined_path:
            return {"success": False, "message": "Failed to merge PDFs"}, 500
        
        custom_section = f"""
                <div style="background: #e8f5e8; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #28a745;">
                    <h4 style="color: #155724; margin-top: 0;">Custom Message:</h4>
                    <p style="margin: 0; white-space: pre-wrap;">{custom_message}</p>
                </div>
        """ if custom_message else ""
        
        # Build package contents list
        package_contents = []
        if include_jd and jd_content:
            package_contents.append('📋 <strong>Job Description</strong> - Original position requirements')
        package_contents.extend([
            '📄 <strong>Original Resume</strong> - Candidate\'s complete resume',
            '📊 <strong>Detailed Evaluation Report</strong> - Complete analysis and scoring'
        ])
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
                    <h2 style="margin: 0;">📦 Complete Evaluation Package</h2>
                    <p style="margin: 5px 0 0 0;">Resume Evaluator</p>
                </div>
                
                {custom_section}
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #667eea;">
                    <h3 style="color: #495057; margin-top: 0;">📊 Candidate Information</h3>
                    <p><strong>Candidate:</strong> {candidate_name}</p>
                    <p><strong>Evaluation Status:</strong> <span style="background: {'#28a745' if verdict == 'Shortlist' else '#ffc107' if verdict == 'Hold' else '#dc3545'}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{verdict}</span></p>
                    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div style="background: white; padding: 20px; border: 1px solid #dee2e6; border-radius: 8px;">
                    <h4 style="color: #667eea; margin-top: 0;">📎 Complete Package Includes:</h4>
                    <ul>
                        {''.join(f'<li>{item}</li>' for item in package_contents)}
                    </ul>
                    <p><strong>Note:</strong> All documents are combined in a single PDF file for your convenience.</p>
                    <p><strong>Next Steps:</strong> Review the complete package and proceed with your hiring decision.</p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 12px;">
                    <p>Generated by Resume Evaluator<br>
                    © 2025. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        attachments = [(combined_path, combined_filename)]
        
        # Add additional attachments
        for att in additional_attachments:
            if os.path.exists(att['file_path']):
                attachments.append((att['file_path'], att['filename']))
        
        # Send to all email addresses
        success_count = 0
        failed_emails = []
        
        for email_addr in email_addresses:
            success, message = send_email_with_attachments(email_addr, email_subject, body, attachments)
            if success:
                success_count += 1
            else:
                failed_emails.append(f"{email_addr}: {message}")
        
        # Send copy to sender if requested
        if cc_sender and session.get('username'):
            sender_email = session.get('username')
            if sender_email not in email_addresses:
                cc_body = f"""<div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
                    <p style="margin: 0;"><strong>Note:</strong> This is a copy of the email sent to: {', '.join(email_addresses)}</p>
                </div>
                {body}"""
                send_email_with_attachments(sender_email, f"[COPY] {email_subject}", cc_body, attachments)
        
        # Cleanup
        try:
            os.unlink(report_path)
            os.unlink(resume_path)
            os.unlink(combined_path)
            # Cleanup additional attachments
            for att in additional_attachments:
                if os.path.exists(att['file_path']):
                    os.unlink(att['file_path'])
        except:
            pass
        
        if success_count == len(email_addresses):
            return {"success": True, "message": f"Complete package sent successfully to {success_count} recipient(s)"}
        elif success_count > 0:
            return {"success": True, "message": f"Email sent to {success_count}/{len(email_addresses)} recipients. Failed: {'; '.join(failed_emails)}"}
        else:
            return {"success": False, "message": f"Failed to send to all recipients: {'; '.join(failed_emails)}"}
        
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}, 500

@app.route("/logout")
def logout():
    if "username" in session:
        update_session_time(session["username"], "user", "logout")
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("login"))
    
    users_data = load_users()
    try:
        with open('admin_sessions.json', 'r') as f:
            admin_sessions = json.load(f)
    except FileNotFoundError:
        admin_sessions = {}
    
    approved_count = sum(1 for user in users_data.values() if user.get('approved', False))
    pending_count = len(users_data) - approved_count
    
    total_shortlisted = sum(user.get('shortlist_count', 0) for user in users_data.values())
    total_not_shortlisted = sum(user.get('not_shortlist_count', 0) for user in users_data.values())
    
    return render_template("admin_dashboard.html", 
                         users=users_data, 
                         admin_sessions=admin_sessions,
                         approved_count=approved_count,
                         pending_count=pending_count,
                         total_shortlisted=total_shortlisted,
                         total_not_shortlisted=total_not_shortlisted)

@app.route("/admin/approve/<user_email>")
def admin_approve(user_email):
    if "admin" not in session:
        return redirect(url_for("login"))
    
    users_data = load_users()
    if user_email in users_data:
        users_data[user_email]['approved'] = True
        save_users(users_data)
        flash(f"User {user_email} has been approved", "success")
    else:
        flash(f"User {user_email} not found", "danger")
    
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/deny/<user_email>")
def admin_deny(user_email):
    if "admin" not in session:
        return redirect(url_for("login"))
    
    users_data = load_users()
    if user_email in users_data:
        users_data[user_email]['approved'] = False
        save_users(users_data)
        flash(f"Access revoked for {user_email}", "warning")
    else:
        flash(f"User {user_email} not found", "danger")
    
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete/<user_email>")
def admin_delete(user_email):
    if "admin" not in session:
        return redirect(url_for("login"))
    
    users_data = load_users()
    if user_email in users_data:
        del users_data[user_email]
        save_users(users_data)
        flash(f"User {user_email} has been deleted", "success")
    else:
        flash(f"User {user_email} not found", "danger")
    
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/logout")
def admin_logout():
    if "admin" in session:
        update_session_time(session["admin"], "admin", "logout")
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        
        if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password:
            session["admin"] = username
            update_session_time(username, "admin", "login")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials", "danger")
    
    return render_template("admin_login.html")

@app.route("/test-azure")
def test_azure():
    if "admin" not in session:
        return "Access denied", 403
    
    config_status = {
        "azure_enabled": AZURE_ENABLED,
        "connection_string": bool(AZURE_STORAGE_CONNECTION_STRING),
        "container_name": AZURE_STORAGE_CONTAINER_NAME,
        "connection_string_length": len(AZURE_STORAGE_CONNECTION_STRING) if AZURE_STORAGE_CONNECTION_STRING else 0
    }
    
    if not AZURE_ENABLED:
        return f"""<h3>Azure Storage Test</h3>
        <p><strong>Status:</strong> ❌ Not Configured</p>
        <p><strong>Configuration:</strong> {config_status}</p>
        <p><strong>Note:</strong> Set AZURE_STORAGE_CONNECTION_STRING environment variable</p>
        """
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        blobs = list(container_client.list_blobs(max_results=5))
        blob_names = [blob.name for blob in blobs]
        
        return f"""<h3>Azure Storage Test</h3>
        <p><strong>Status:</strong> ✅ Connected</p>
        <p><strong>Configuration:</strong> {config_status}</p>
        <p><strong>Container:</strong> {AZURE_STORAGE_CONTAINER_NAME}</p>
        <p><strong>Sample blobs:</strong> {blob_names}</p>
        <p><strong>Total blobs found:</strong> {len(blobs)}</p>
        """
        
    except Exception as e:
        return f"""<h3>Azure Storage Test</h3>
        <p><strong>Status:</strong> ❌ Connection Failed</p>
        <p><strong>Configuration:</strong> {config_status}</p>
        <p><strong>Error:</strong> {str(e)}</p>
        """

if __name__ == "__main__":
    app.run(debug=True)
