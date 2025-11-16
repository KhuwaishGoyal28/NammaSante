import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# ------------------ Initialize Firebase ------------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ------------------ CSV File Path ------------------
csv_path = r"farmer.csv"  # <-- Replace with your CSV full path

# ------------------ Upload CSV Data to Firestore ------------------
try:
    df = pd.read_csv(csv_path)

    for index, row in df.iterrows():
        user_data = row.to_dict()
        db.collection("users").add(user_data)  # auto-generated document ID

    print("CSV uploaded successfully!")
except Exception as e:
    print(f"Error uploading CSV: {e}")
