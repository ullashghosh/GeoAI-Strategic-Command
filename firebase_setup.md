# Firebase Setup Guide for LLM Project

## Overview
This guide walks through setting up Firebase (Google Cloud Firestore) for your Python LLM project, from project creation through integration and testing.

---

## Step 1: Access Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. If you don't have a Google Cloud account, create one

---

## Step 2: Create a New Google Cloud Project

1. In the top navigation bar, click on the **Project Selector** (shows current project name)
2. Click **NEW PROJECT**
3. Enter project name: `multi-llm-chat` (or your preferred name)
4. Click **CREATE**
5. Wait for the project to be created (this may take a moment)
6. Select your newly created project from the Project Selector

---

## Step 3: Enable Firebase and Firestore

### Enable Firebase API:
1. In the Google Cloud Console, go to **APIs & Services** > **Enabled APIs & Services**
2. Click **+ ENABLE APIS AND SERVICES**
3. Search for **"Cloud Firestore API"**
4. Click on it and press **ENABLE**
5. Repeat for **"Firebase Admin SDK API"** (search and enable)

### Initialize Firebase:
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **Add project**
3. Select your Google Cloud project from the dropdown
4. Click **Continue**
5. Enable Google Analytics (optional, click **Continue** or skip)
6. Your Firebase project is now initialized

---

## Step 4: Create Firestore Database

1. In Firebase Console, click on your project
2. In the left sidebar, go to **Build** > **Firestore Database**
3. Click **Create Database**
4. Choose location (e.g., `us-central1`)
5. Start in **Production mode** (or Test mode for development)
6. Click **Create**
7. Wait for database initialization

---

## Step 5: Create Collections (Optional at this stage)

1. In Firestore, click **Start Collection**
2. Collection name: `testing` (or your collection name)
3. Add the first document with sample data
4. Click **Save**

---

## Step 6: Create Firebase Service Account

1. In Firebase Console, go to **Project Settings** (gear icon top-left)
2. Click **Service Accounts** tab
3. Click **Generate New Private Key** button
4. A JSON file will be downloaded: `multi-llm-chat-487415-firebase-adminsdk-fbsvc-7ee1f7cdc6.json`
5. Save this file in your project root directory (keep it secure, don't commit to version control)

---

## Step 7: Install Firebase Admin SDK for Python

Run the following command to install required packages:

```bash
pip install firebase-admin
```

Or add to your `requirements.txt`:
```
firebase-admin==6.2.0
```

Then run:
```bash
pip install -r requirements.txt
```

---

## Step 8: Integrate Firebase with Your Application

### Create a Firebase initialization module - `firebase_config.py`:

```python
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os

# Initialize Firebase Admin SDK
cred = credentials.Certificate('multi-llm-chat-487415-firebase-adminsdk-fbsvc-7ee1f7cdc6.json')
firebase_admin.initialize_app(cred)

# Get Firestore database reference
db = firestore.client()

def get_db():
    """Return Firestore database instance"""
    return db
```

### Use in your main application:

```python
from firebase_config import get_db

db = get_db()

# Example: Add data
def add_message(collection, data):
    db.collection(collection).add(data)

# Example: Read data
def get_messages(collection):
    docs = db.collection(collection).stream()
    return [doc.to_dict() for doc in docs]
```

---

## Step 9: Test Firebase Integration

### Create a test script - `test_firebase.py`:

```python
from firebase_config import get_db
from datetime import datetime

def test_firebase():
    db = get_db()
    
    # Test Write Operation
    print("Testing Write Operation...")
    test_data = {
        'message': 'Hello Firebase!',
        'timestamp': datetime.now(),
        'project': 'LLM Chat'
    }
    
    doc_ref = db.collection('testing').add(test_data)
    print(f"✓ Document written successfully with ID: {doc_ref[1].id}")
    
    # Test Read Operation
    print("\nTesting Read Operation...")
    docs = db.collection('testing').stream()
    
    print(f"✓ Retrieved documents:")
    for doc in docs:
        print(f"  - {doc.id}: {doc.to_dict()}")
    
    print("\n✓ Firebase integration successful!")

if __name__ == '__main__':
    test_firebase()
```

Run the test:
```bash
python test_firebase.py
```

---

## Step 10: Security Rules Setup (Important!)

1. In Firebase Console, go to **Firestore Database** > **Rules**
2. For development, use (NOT for production):
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

3. For production, implement proper authentication and authorization rules
4. Click **Publish** to apply rules

---

## Step 11: Environment Setup (Recommended)

Create a `.env` file (don't commit to version control):
```
FIREBASE_CREDENTIALS=multi-llm-chat-487415-firebase-adminsdk-fbsvc-7ee1f7cdc6.json
FIREBASE_COLLECTION=testing
```

Update `firebase_config.py` to use environment variables:
```python
import os
from dotenv import load_dotenv

load_dotenv()

cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS'))
```

---

## Step 12: Add to .gitignore

Make sure not to commit sensitive files:
```
*.json
.env
__pycache__/
*.pyc
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "ServiceAccountCredentials" error | Ensure JSON credential file path is correct |
| Permission denied errors | Check Firestore security rules |
| Module not found | Run `pip install firebase-admin` |
| Connection timeout | Verify Google Cloud/Firebase project is active |

---

## Common Operations Reference

```python
# Add document
db.collection('testing').add({'key': 'value'})

# Get all documents
docs = db.collection('testing').stream()

# Query documents
query = db.collection('testing').where('status', '==', 'active').stream()

# Update document
db.collection('testing').document('docID').update({'key': 'new_value'})

# Delete document
db.collection('testing').document('docID').delete()
```

---

## Next Steps

1. Implement proper authentication (email/password, OAuth, etc.)
2. Set up Firestore indexes for complex queries
3. Enable Cloud Functions for backend logic
4. Implement proper error handling and logging
5. Set up monitoring and analytics

---

## Resources

- [Firebase Documentation](https://firebase.google.com/docs)
- [Firebase Admin SDK for Python](https://firebase.google.com/docs/database/admin/start)
- [Firestore Security Rules](https://firebase.google.com/docs/firestore/security/start)
- [Google Cloud Console](https://console.cloud.google.com/)
