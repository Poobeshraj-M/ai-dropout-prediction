import pandas as pd
import joblib
import os
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'dataset', 'student_data.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'dropout_model.pkl')

def get_model_performance():
    if not os.path.exists(DATA_PATH) or not os.path.exists(MODEL_PATH):
        return None
        
    df = pd.read_csv(DATA_PATH)
    clf = joblib.load(MODEL_PATH)
    
    X = df.drop('Dropout_Risk', axis=1)
    y = df['Dropout_Risk']
    
    # Use the same split as training for consistency in this assessment
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    y_pred = clf.predict(X_test)
    
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, average='weighted'),
        'recall': recall_score(y_test, y_pred, average='weighted'),
        'f1': f1_score(y_test, y_pred, average='weighted'),
        'total_samples': len(df),
        'test_samples': len(y_test)
    }
    
    return metrics
