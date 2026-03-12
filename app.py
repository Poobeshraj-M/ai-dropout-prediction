from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from flask_bcrypt import Bcrypt
import sqlite3
import os
import io
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ml.predict import predict_risk, get_counseling_recommendation, format_recommendations_text
from ml.metrics import get_model_performance
from database.db_setup import DB_PATH
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

app = Flask(__name__)
app.secret_key = 'edusustain_super_secret_key_123'
bcrypt = Bcrypt(app)

import json
# Custom filter for JSON conversion in templates
@app.template_filter('to_json_list')
def to_json_list(sqlite_rows):
    return json.dumps([dict(row) for row in sqlite_rows])

def log_event(username, event, details=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO audit_logs (username, event, details) VALUES (?, ?, ?)', 
                     (username, event, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging event: {e}")

def send_alert_email(student_name, roll_no, risk_level):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get settings
        cursor.execute("SELECT * FROM system_settings")
        settings = {row['key']: row['value'] for row in cursor.fetchall()}
        conn.close()
        
        if not settings.get('smtp_user') or not settings.get('counselor_email'):
            return # E-mail not configured
            
        msg = MIMEMultipart()
        msg['From'] = settings['smtp_user']
        msg['To'] = settings['counselor_email']
        msg['Subject'] = f"HIGH RISK ALERT: Student Dropout Prediction - {student_name}"
        
        body = f"""
        Dear Counselor,
        
        The AI Student Dropout System has identified a student with HIGH DROPOUT RISK.
        
        Student Details:
        - Name: {student_name}
        - Roll Number: {roll_no}
        - Risk Level: {risk_level}
        
        Please log in to the dashboard to review the detailed assessment and recommendations.
        
        Regards,
        EduSustain AI System
        """
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(settings['smtp_server'], int(settings['smtp_port']))
        server.starttls()
        server.login(settings['smtp_user'], settings['smtp_pass'])
        server.send_message(msg)
        server.quit()
        log_event("SYSTEM", "Email Alert Sent", f"Alert for {student_name} ({roll_no})")
    except Exception as e:
        log_event("SYSTEM", "Email Alert Failed", str(e))
        print(f"Email error: {e}")

# Ensure the database gets set up if missing
if not os.path.exists(DB_PATH):
    from database.db_setup import setup_db
    setup_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get data from form
        student_name = request.form.get('student_name')
        roll_number = request.form.get('roll_number')
        department = request.form.get('department', 'General')
        
        features = {
            'Attendance': float(request.form.get('attendance', 0)),
            'Marks': float(request.form.get('marks', 0)),
            'Arrears': int(request.form.get('arrears', 0)),
            'Assignments_Submitted': int(request.form.get('assignments', 0)),
            'Family_Income': int(request.form.get('family_income', 2)),
            'Travel_Distance_km': float(request.form.get('travel_distance', 0)),
            'Stress_Level': int(request.form.get('stress_level', 5)),
            'Feedback_Sentiment': int(request.form.get('feedback_sentiment', 0))
        }
        
        # ML prediction
        risk_level = predict_risk(features)
        
        # AI Recommendation (structured list)
        recommendations = get_counseling_recommendation(risk_level, features)
        recommendation_text = format_recommendations_text(recommendations)
        
        # Save to Database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO students 
            (student_name, roll_number, department, attendance, marks, arrears, assignments, family_income, 
             travel_distance, stress_level, feedback_sentiment, dropout_risk, counseling_recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            student_name, roll_number, department, features['Attendance'], features['Marks'], features['Arrears'],
            features['Assignments_Submitted'], features['Family_Income'], features['Travel_Distance_km'],
            features['Stress_Level'], features['Feedback_Sentiment'], risk_level, recommendation_text
        ))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        
        log_event(session.get('admin_username', 'Unknown'), "Student Prediction", f"Roll: {roll_number}, Name: {student_name}, Risk: {risk_level}")
        
        # Send Alert for High Risk
        if risk_level == 'High':
            send_alert_email(student_name, roll_number, risk_level)
            
        return render_template('result.html', id=last_id, name=student_name, risk=risk_level, recommendations=recommendations)
        
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verify credentials against admins table
        cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
        admin = cursor.fetchone()
        conn.close()
        
        if admin and bcrypt.check_password_hash(admin['password'], password):
            session['logged_in'] = True
            session['admin_name'] = admin['name']
            session['admin_username'] = admin['username']
            log_event(username, "Login", "Successful attempt")
            return redirect(url_for('dashboard'))
        else:
            log_event(username if username else "Unknown", "Login", "Failed attempt")
            flash('Invalid admin credentials. Please try again.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    # Protect Route
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students ORDER BY timestamp DESC')
    records = cursor.fetchall()
    conn.close()
    
    # Calculate summary stats for charts
    risk_counts = {'Low': 0, 'Medium': 0, 'High': 0}
    dept_risk = {}  # {dept: {Low: n, Medium: n, High: n}}
    attendance_ranges = {'0-40': 0, '41-60': 0, '61-80': 0, '81-100': 0}
    stress_dist = {str(i): 0 for i in range(1, 11)}
    monthly_trend = {}  # {month_str: {Low: n, Medium: n, High: n}}
    
    for r in records:
        risk = r['dropout_risk']
        if risk in risk_counts:
            risk_counts[risk] += 1
        
        # Department-wise breakdown
        dept = r['department'] if r['department'] else 'General'
        if dept not in dept_risk:
            dept_risk[dept] = {'Low': 0, 'Medium': 0, 'High': 0}
        if risk in dept_risk[dept]:
            dept_risk[dept][risk] += 1
        
        # Attendance distribution
        att = r['attendance'] or 0
        if att <= 40: attendance_ranges['0-40'] += 1
        elif att <= 60: attendance_ranges['41-60'] += 1
        elif att <= 80: attendance_ranges['61-80'] += 1
        else: attendance_ranges['81-100'] += 1
        
        # Stress distribution
        stress = str(r['stress_level']) if r['stress_level'] else '1'
        if stress in stress_dist:
            stress_dist[stress] += 1
        
        # Monthly trends
        ts = r['timestamp'] or ''
        month_key = ts[:7]  # "YYYY-MM"
        if month_key:
            if month_key not in monthly_trend:
                monthly_trend[month_key] = {'Low': 0, 'Medium': 0, 'High': 0}
            if risk in monthly_trend[month_key]:
                monthly_trend[month_key][risk] += 1
    
    # Sort monthly trend
    sorted_months = sorted(monthly_trend.keys())
    trend_data = {
        'labels': sorted_months,
        'low': [monthly_trend[m]['Low'] for m in sorted_months],
        'medium': [monthly_trend[m]['Medium'] for m in sorted_months],
        'high': [monthly_trend[m]['High'] for m in sorted_months]
    }
    
    # Feature importance (from trained model)
    feature_importance = {}
    try:
        from ml.predict import get_model, FEATURE_NAMES
        model = get_model()
        if hasattr(model, 'feature_importances_'):
            for name, imp in zip(FEATURE_NAMES, model.feature_importances_):
                feature_importance[name] = round(imp * 100, 1)
    except:
        feature_importance = {}
    
    import json
    return render_template('dashboard.html', 
        records=records, 
        risk_counts=risk_counts,
        risk_counts_json=json.dumps(risk_counts),
        dept_risk=json.dumps(dept_risk),
        attendance_ranges=json.dumps(attendance_ranges),
        stress_dist=json.dumps(stress_dist),
        trend_data=json.dumps(trend_data),
        feature_importance=json.dumps(feature_importance),
        admin_name=session.get('admin_name', 'Admin')
    )

@app.route('/student-history/<roll_number>')
def student_history(roll_number):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE roll_number = ? ORDER BY timestamp DESC', (roll_number,))
    history = cursor.fetchall()
    conn.close()
    
    if not history:
        flash("No history found for this roll number.", "danger")
        return redirect(url_for('dashboard'))
        
    student_name = history[0]['student_name']
    
    return render_template('student_history.html', history=history, roll_number=roll_number, student_name=student_name)

@app.route('/download-report/<int:id>')
def download_report(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE id = ?', (id,))
    record = cursor.fetchone()
    conn.close()
    
    if not record:
        flash("Record not found.", "danger")
        return redirect(url_for('dashboard'))
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=1, spaceAfter=20)
    elements.append(Paragraph("Student Risk Assessment Report", title_style))
    elements.append(Paragraph(f"Generated on: {record['timestamp']}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Student Info Table
    data = [
        ["Field", "Value"],
        ["Student Name", record['student_name']],
        ["Roll Number", record['roll_number']],
        ["Department", record['department']],
        ["Attendance", f"{record['attendance']}%"],
        ["Average Marks", f"{record['marks']}%"],
        ["Current Arrears", str(record['arrears'])],
        ["Dropout Risk", record['dropout_risk']]
    ]
    t = Table(data, colWidths=[150, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.cadetblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 24))
    
    # Counseling Recommendation
    elements.append(Paragraph("AI Counseling Recommendations:", styles['Heading2']))
    elements.append(Spacer(1, 6))
    
    # Split the recommendation text back into paragraphs
    rec_text = record['counseling_recommendation']
    for line in rec_text.split('\n'):
        if line.strip():
            elements.append(Paragraph(line, styles['Normal']))
            elements.append(Spacer(1, 6))
    
    # Footer
    elements.append(Spacer(1, 48))
    elements.append(Paragraph("Confidential - For Administrative Use Only", styles['Italic']))
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"Report_{record['roll_number']}_{record['timestamp'][:10]}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

@app.route('/upload-csv', methods=['GET', 'POST'])
def upload_csv():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash("No selected file", "danger")
            return redirect(request.url)
            
        if file and file.filename.endswith('.csv'):
            try:
                import pandas as pd
                df = pd.read_csv(file)
                
                # Expected columns
                required_cols = ['student_name', 'roll_number', 'attendance', 'marks', 'arrears', 
                                'assignments', 'family_income', 'travel_distance', 'stress_level', 
                                'feedback_sentiment']
                
                # Check for department (optional)
                if 'department' not in df.columns:
                    df['department'] = 'General'
                
                missing = [c for c in required_cols if c not in df.columns]
                if missing:
                    flash(f"Missing columns: {', '.join(missing)}", "danger")
                    return redirect(request.url)
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                success_count = 0
                for _, row in df.iterrows():
                    # Prepare features for ML model
                    features = {
                        'Attendance': float(row['attendance']),
                        'Marks': float(row['marks']),
                        'Arrears': int(row['arrears']),
                        'Assignments_Submitted': int(row['assignments']),
                        'Family_Income': int(row['family_income']),
                        'Travel_Distance_km': float(row['travel_distance']),
                        'Stress_Level': int(row['stress_level']),
                        'Feedback_Sentiment': int(row['feedback_sentiment'])
                    }
                    
                    # Run prediction
                    risk_level = predict_risk(features)
                    recommendation_text = get_counseling_recommendation(risk_level, features)
                    
                    # Insert into DB
                    cursor.execute('''
                        INSERT INTO students 
                        (student_name, roll_number, department, attendance, marks, arrears, assignments, family_income, 
                         travel_distance, stress_level, feedback_sentiment, dropout_risk, counseling_recommendation)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['student_name'], row['roll_number'], row['department'], features['Attendance'], 
                        features['Marks'], features['Arrears'], features['Assignments_Submitted'], 
                        features['Family_Income'], features['Travel_Distance_km'], features['Stress_Level'], 
                        features['Feedback_Sentiment'], risk_level, recommendation_text
                    ))
                    
                    # Send Alert for High Risk
                    if risk_level == 'High':
                        send_alert_email(row['student_name'], row['roll_number'], risk_level)
                        
                    success_count += 1
                
                conn.commit()
                conn.close()
                log_event(session.get('admin_username'), "Bulk CSV Upload", f"Processed {success_count} records")
                flash(f"Successfully processed {success_count} student records!", "success")
                return redirect(url_for('dashboard'))
                
            except Exception as e:
                flash(f"Error processing CSV: {str(e)}", "danger")
                return redirect(request.url)
        else:
            flash("Please upload a valid CSV file.", "warning")
            return redirect(request.url)
            
    return render_template('upload.html')

@app.route('/model-performance')
def model_performance():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    metrics = get_model_performance()
    return render_template('model_performance.html', metrics=metrics)

@app.route('/chatbot', methods=['POST'])
def chatbot_response():
    user_msg = request.json.get('message', '').lower()
    
    responses = {
        'stress': "I'm sorry you're feeling stressed. Managing academics can be tough. Try breaking your tasks into smaller goals and don't hesitate to talk to our campus counselor.",
        'marks': "If you're worried about your grades, remember that consistency is key. Have you tried joining a study group or reaching out to your professors for extra help?",
        'attendance': "Attending classes regularly is the first step to success. If travel or personal issues are making it hard, let's discuss how we can support you.",
        'hello': "Hello! I'm your EduSustain AI assistant. How can I help you with your academic journey today?",
        'hi': "Hi there! I'm here to support you. Are you feeling stressed or worried about your studies?",
        'dropout': "Thinking about leaving? Please remember why you started. Most challenges are temporary. Let's look at available resources like scholarships or counseling.",
        'help': "I can provide advice on managing stress, improving marks, or finding campus resources. Just tell me what's on your mind."
    }
    
    # Simple keyword matching
    reply = "I'm here to listen. Can you tell me more about that? For example, are you feeling stressed or worried about specific subjects?"
    for key, resp in responses.items():
        if key in user_msg:
            reply = resp
            break
            
    return jsonify({'reply': reply})

@app.route('/manage-admins', methods=['GET', 'POST'])
def manage_admins():
    # Protect Route: Only 'admin' can access this page
    if not session.get('logged_in') or session.get('admin_username') != 'admin':
        flash('Access Denied: You do not have permission to view the Admin Management page.', 'danger')
        return redirect(url_for('dashboard'))
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        
        import re
        if not re.match(r"^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$", password):
            flash('Error: Password must be at least 8 characters long, and include an uppercase letter, a lowercase letter, and a number.', 'danger')
            return redirect(url_for('manage_admins'))
        
        try:
            hashed_pwd = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute('INSERT INTO admins (username, password, name) VALUES (?, ?, ?)', 
                           (username, hashed_pwd, name))
            conn.commit()
            log_event(session.get('admin_username'), "Admin Created", f"Created administrator account for: {username} ({name})")
            flash(f'Administrator user "{username}" added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash(f'Error: The username "{username}" already exists. Please pick another one.', 'danger')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            
        return redirect(url_for('manage_admins'))
        
    # GET: Fetch all admins to display in the table
    cursor.execute('SELECT id, username, name FROM admins ORDER BY id ASC')
    admins = cursor.fetchall()
    
    # Fetch settings
    cursor.execute("SELECT * FROM system_settings")
    settings_rows = cursor.fetchall()
    settings = {row['key']: row['value'] for row in settings_rows}
    
    conn.close()
    
    return render_template('manage_admins.html', admins=admins, settings=settings)

@app.route('/update-settings', methods=['POST'])
def update_settings():
    if not session.get('logged_in') or session.get('admin_username') != 'admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('dashboard'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for key in ['smtp_server', 'smtp_port', 'smtp_user', 'smtp_pass', 'counselor_email']:
        val = request.form.get(key)
        cursor.execute("UPDATE system_settings SET value = ? WHERE key = ?", (val, key))
    
    conn.commit()
    conn.close()
    
    log_event(session.get('admin_username'), "Settings Updated", "SMTP/Email configuration changed")
    flash("System settings updated successfully!", "success")
    return redirect(url_for('manage_admins'))

@app.route('/delete-admin/<int:id>', methods=['POST'])
def delete_admin(id):
    # Protect Route: Only 'admin' can delete users
    if not session.get('logged_in') or session.get('admin_username') != 'admin':
        flash('Access Denied: You do not have permission to delete administrators.', 'danger')
        return redirect(url_for('dashboard'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Prevent deletion of the primary admin account
    cursor.execute('SELECT username FROM admins WHERE id = ?', (id,))
    target = cursor.fetchone()
    if target and target[0] == 'admin':
        flash('Error: The primary system administrator account cannot be deleted.', 'danger')
    else:
        cursor.execute('DELETE FROM admins WHERE id = ?', (id,))
        conn.commit()
        log_event(session.get('admin_username'), "Admin Deleted", f"Deleted Admin ID: {id}, Username: {target[0]}")
        flash('Administrator successfully removed.', 'success')
        
    conn.close()
    return redirect(url_for('manage_admins'))

@app.route('/reset-admin-password/<int:id>', methods=['POST'])
def reset_admin_password(id):
    # Protect Route: Only 'admin' can reset passwords
    if not session.get('logged_in') or session.get('admin_username') != 'admin':
        flash('Access Denied: You do not have permission to reset passwords.', 'danger')
        return redirect(url_for('dashboard'))
        
    new_password = request.form.get('new_password')
    if not new_password or len(new_password) < 8:
        flash('Error: Password must be at least 8 characters.', 'danger')
        return redirect(url_for('manage_admins'))
        
    # Optional: could add complexity check here too
    
    hashed_pwd = bcrypt.generate_password_hash(new_password).decode('utf-8')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE admins SET password = ? WHERE id = ?', (hashed_pwd, id))
    
    # Get username for logging
    cursor.execute('SELECT username FROM admins WHERE id = ?', (id,))
    target = cursor.fetchone()
    
    conn.commit()
    conn.close()
    
    log_event(session.get('admin_username'), "Password Reset", f"Reset password for Admin ID: {id}, Username: {target[0] if target else 'Unknown'}")
    flash(f'Password for "{target[0] if target else "user"}" has been reset successfully.', 'success')
    
    return redirect(url_for('manage_admins'))

@app.route('/clear-data', methods=['POST'])
def clear_data():
    # Protect Route: Only 'admin' can clear all data
    if not session.get('logged_in') or session.get('admin_username') != 'admin':
        flash('Access Denied: Only the Super Administrator can clear system data.', 'danger')
        return redirect(url_for('dashboard'))
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Delete all student records
        cursor.execute('DELETE FROM students')
        
        # Reset auto-increment ID
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='students'")
        
        conn.commit()
        conn.close()
        
        log_event(session.get('admin_username'), "System Data Reset", "All student analysis records have been cleared.")
        flash('All past student analysis data has been cleared successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred while clearing data: {str(e)}', 'danger')
        
    return redirect(url_for('manage_admins'))

@app.route('/audit-logs')
def view_audit_logs():
    if not session.get('logged_in') or session.get('admin_username') != 'admin':
        flash('Access Denied: You do not have permission to view audit logs.', 'danger')
        return redirect(url_for('dashboard'))
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 200')
    logs = cursor.fetchall()
    conn.close()
    
    return render_template('audit_logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
