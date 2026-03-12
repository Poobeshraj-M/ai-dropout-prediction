import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'dataset', 'student_data.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'dropout_model.pkl')

def generate_synthetic_data(num_samples=500):
    """Generates synthetic student data if it doesn't exist."""
    np.random.seed(42)
    
    features = {
        'Attendance': np.random.randint(40, 100, num_samples),
        'Marks': np.random.randint(30, 100, num_samples),
        'Arrears': np.random.randint(0, 6, num_samples),
        'Assignments_Submitted': np.random.randint(0, 11, num_samples),
        'Family_Income': np.random.choice([1, 2, 3], num_samples), # 1: Low, 2: Medium, 3: High
        'Travel_Distance_km': np.random.randint(1, 50, num_samples),
        'Stress_Level': np.random.randint(1, 11, num_samples), # 1-10
        'Feedback_Sentiment': np.random.choice([-1, 0, 1], num_samples) # -1: Negative, 0: Neutral, 1: Positive
    }
    
    df = pd.DataFrame(features)
    
    # Create Target Variable Based on Logic
    def calculate_risk(row):
        score = 0
        if row['Attendance'] < 60: score += 3
        if row['Marks'] < 50: score += 3
        if row['Arrears'] > 2: score += 2
        if row['Assignments_Submitted'] < 5: score += 1
        if row['Family_Income'] == 1: score += 1
        if row['Travel_Distance_km'] > 20: score += 1
        if row['Stress_Level'] > 7: score += 2
        if row['Feedback_Sentiment'] == -1: score += 2
        
        if score >= 8: return 'High'
        elif score >= 4: return 'Medium'
        else: return 'Low'
        
    df['Dropout_Risk'] = df.apply(calculate_risk, axis=1)
    
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    print(f"Generated {num_samples} records of synthetic data at {DATA_PATH}")

def train_model():
    """Trains the Random Forest Model using the dataset."""
    if not os.path.exists(DATA_PATH):
        generate_synthetic_data()
        
    df = pd.read_csv(DATA_PATH)
    
    X = df.drop('Dropout_Risk', axis=1)
    y = df['Dropout_Risk']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model trained with Accuracy: {acc * 100:.2f}%")
    
    # Save Model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"Model saved at {MODEL_PATH}")

if __name__ == "__main__":
    train_model()
