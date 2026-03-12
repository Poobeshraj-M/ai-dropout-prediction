import joblib
import os
import pandas as pd

# Define mapping to consistent feature names used during training
FEATURE_NAMES = [
    'Attendance', 'Marks', 'Arrears', 'Assignments_Submitted', 
    'Family_Income', 'Travel_Distance_km', 'Stress_Level', 'Feedback_Sentiment'
]

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'dropout_model.pkl')

# Load the model lazily
model = None

def get_model():
    global model
    if model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError("Model file not found. Please train the model first.")
        model = joblib.load(MODEL_PATH)
    return model

def predict_risk(features_dict):
    """
    Predicts the dropout risk.
    features_dict should have keys matching FEATURE_NAMES exactly.
    """
    model = get_model()
    # Ensure correct order
    input_data = pd.DataFrame([[features_dict[k] for k in FEATURE_NAMES]], columns=FEATURE_NAMES)
    prediction = model.predict(input_data)
    return prediction[0]

def get_counseling_recommendation(risk_level, features_dict):
    """
    Provides personalized, structured AI counseling recommendations based on the
    combined risk level and individual feature values.
    Returns a list of recommendation dicts with: category, icon, severity, title, message, action
    """
    recommendations = []
    
    # --- Overall Risk Assessment ---
    if risk_level == 'High':
        recommendations.append({
            'category': 'Overall Risk',
            'icon': 'triangle-exclamation',
            'severity': 'danger',
            'title': 'Critical Dropout Risk Detected',
            'message': 'This student is at HIGH risk of dropping out. Immediate intervention from the counseling team is essential.',
            'action': 'Schedule an urgent 1-on-1 meeting with the student within the next 48 hours. Notify the Head of Department.'
        })
    elif risk_level == 'Medium':
        recommendations.append({
            'category': 'Overall Risk',
            'icon': 'exclamation-circle',
            'severity': 'warning',
            'title': 'Moderate Dropout Risk',
            'message': 'This student shows early warning signs. Preventive counseling measures are recommended before the situation escalates.',
            'action': 'Assign a faculty mentor for weekly check-ins. Monitor progress over the next 30 days.'
        })
    else:
        recommendations.append({
            'category': 'Overall Risk',
            'icon': 'circle-check',
            'severity': 'success',
            'title': 'Low Dropout Risk',
            'message': 'This student appears to be on track. Continue providing positive reinforcement and encouragement.',
            'action': 'Maintain regular engagement. Consider nominating for academic achiever awards or peer mentoring roles.'
        })
    
    # --- Attendance Analysis ---
    attendance = features_dict['Attendance']
    if attendance < 50:
        recommendations.append({
            'category': 'Attendance',
            'icon': 'calendar-xmark',
            'severity': 'danger',
            'title': 'Severely Low Attendance ({:.0f}%)'.format(attendance),
            'message': 'Attendance is critically below acceptable levels. This is a strong indicator of disengagement.',
            'action': 'Immediately schedule a parent-teacher meeting. Investigate possible causes: health issues, bullying, family problems, or lack of transportation.'
        })
    elif attendance < 75:
        recommendations.append({
            'category': 'Attendance',
            'icon': 'calendar-minus',
            'severity': 'warning',
            'title': 'Below Average Attendance ({:.0f}%)'.format(attendance),
            'message': 'Attendance is below the required threshold. Student may miss important coursework and assessments.',
            'action': 'Send an attendance warning letter. Assign a class buddy to encourage regular attendance. Check for scheduling conflicts.'
        })
    
    # --- Academic Performance ---
    marks = features_dict['Marks']
    if marks < 35:
        recommendations.append({
            'category': 'Academics',
            'icon': 'book-skull',
            'severity': 'danger',
            'title': 'Failing Academic Performance (Marks: {:.0f})'.format(marks),
            'message': 'The student is at risk of academic failure. Scores indicate severe learning gaps.',
            'action': 'Enroll in mandatory remedial classes. Assign a dedicated tutor. Consider reducing course load if permissible.'
        })
    elif marks < 60:
        recommendations.append({
            'category': 'Academics',
            'icon': 'book-open',
            'severity': 'warning',
            'title': 'Below Average Academic Scores (Marks: {:.0f})'.format(marks),
            'message': 'Performance is below average. The student may benefit from additional academic support.',
            'action': 'Recommend joining peer tutoring or study groups. Provide extra practice materials and past exam papers.'
        })
    
    # --- Arrears / Backlogs ---
    arrears = features_dict['Arrears']
    if arrears >= 4:
        recommendations.append({
            'category': 'Backlogs',
            'icon': 'file-circle-exclamation',
            'severity': 'danger',
            'title': 'Excessive Arrears ({} subjects)'.format(arrears),
            'message': 'A high number of backlogs creates academic pressure and significantly increases dropout probability.',
            'action': 'Create a structured arrear clearance plan with target dates. Provide study materials and connect with subject teachers for doubt-clearing sessions.'
        })
    elif arrears > 2:
        recommendations.append({
            'category': 'Backlogs',
            'icon': 'file-circle-minus',
            'severity': 'warning',
            'title': 'Multiple Arrears ({} subjects)'.format(arrears),
            'message': 'Accumulating backlogs can demotivate the student and hinder academic progress.',
            'action': 'Academic advising is necessary. Create a realistic clearance roadmap and monitor monthly progress.'
        })
    
    # --- Assignment Submission ---
    assignments = features_dict['Assignments_Submitted']
    if assignments < 3:
        recommendations.append({
            'category': 'Assignments',
            'icon': 'clipboard-question',
            'severity': 'danger',
            'title': 'Very Low Assignment Submissions ({} out of 10)'.format(assignments),
            'message': 'Consistently missing assignments reflects disengagement from the learning process.',
            'action': 'Counsel the student on time management. Check if they understand the assignments. Offer deadline extensions with conditions.'
        })
    elif assignments < 6:
        recommendations.append({
            'category': 'Assignments',
            'icon': 'clipboard-list',
            'severity': 'warning',
            'title': 'Irregular Assignment Submissions ({} out of 10)'.format(assignments),
            'message': 'The student is partially engaged but not completing all required work.',
            'action': 'Set up weekly submission reminders. Pair with a responsible classmate for accountability.'
        })
    
    # --- Stress Level ---
    stress = features_dict['Stress_Level']
    if stress >= 8:
        recommendations.append({
            'category': 'Mental Health',
            'icon': 'heart-pulse',
            'severity': 'danger',
            'title': 'Extremely High Stress Level ({}/10)'.format(stress),
            'message': 'The student is under severe emotional/mental stress. This requires immediate attention to prevent burnout or dropout.',
            'action': 'Urgently refer to the campus psychological counselor. Suggest relaxation workshops, yoga/meditation sessions. Reduce academic workload temporarily if possible.'
        })
    elif stress >= 6:
        recommendations.append({
            'category': 'Mental Health',
            'icon': 'brain',
            'severity': 'warning',
            'title': 'Elevated Stress Level ({}/10)'.format(stress),
            'message': 'The student is experiencing notable stress that could affect performance and well-being.',
            'action': 'Schedule a casual counseling check-in. Share stress management resources. Encourage participation in extracurricular or recreational activities.'
        })
    
    # --- Feedback Sentiment ---
    sentiment = features_dict['Feedback_Sentiment']
    if sentiment == -1:
        recommendations.append({
            'category': 'Student Voice',
            'icon': 'comment-dots',
            'severity': 'danger',
            'title': 'Negative Feedback Sentiment',
            'message': 'The student has expressed dissatisfaction or negativity in their feedback, signaling frustration with the system.',
            'action': 'Conduct a private 1-on-1 qualitative interview. Understand specific grievances and take corrective action where possible. Show the student their voice is heard.'
        })
    elif sentiment == 0:
        recommendations.append({
            'category': 'Student Voice',
            'icon': 'comment',
            'severity': 'warning',
            'title': 'Neutral Feedback Sentiment',
            'message': 'The student has not expressed strong feelings either way. There may be underlying issues not being communicated.',
            'action': 'Encourage open dialogue through anonymous surveys or suggestion boxes. Build trust through informal interactions.'
        })
    
    # --- Financial & Travel Factors ---
    income = features_dict['Family_Income']
    distance = features_dict['Travel_Distance_km']
    if income == 1:  # Low income
        if distance > 20:
            recommendations.append({
                'category': 'Socioeconomic',
                'icon': 'hand-holding-heart',
                'severity': 'danger',
                'title': 'Low Income + Long Commute ({:.0f} km)'.format(distance),
                'message': 'The combination of financial hardship and long travel distance creates a significant barrier to continuing education.',
                'action': 'Apply for travel allowances and financial aid scholarships. Explore hostel accommodation options. Connect with NGOs providing student support.'
            })
        else:
            recommendations.append({
                'category': 'Socioeconomic',
                'icon': 'coins',
                'severity': 'warning',
                'title': 'Low Family Income',
                'message': 'Financial constraints may limit the student\'s ability to afford resources, materials, or even meals.',
                'action': 'Guide the student to apply for government scholarships, fee waivers, or part-time on-campus employment opportunities.'
            })
    elif distance > 30:
        recommendations.append({
            'category': 'Socioeconomic',
            'icon': 'route',
            'severity': 'warning',
            'title': 'Long Travel Distance ({:.0f} km)'.format(distance),
            'message': 'Extended commute times can cause fatigue, reduce study time, and contribute to absenteeism.',
            'action': 'Explore hostel facilities or nearby PG accommodation. Consider flexible class scheduling if available.'
        })
    
    return recommendations


def format_recommendations_text(recommendations):
    """
    Converts the structured recommendations list into a plain text summary
    for storing in the database.
    """
    lines = []
    for rec in recommendations:
        lines.append(f"[{rec['category']}] {rec['title']}: {rec['message']} Action: {rec['action']}")
    return " | ".join(lines)
