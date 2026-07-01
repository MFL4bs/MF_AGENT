import sys
sys.stdout.reconfigure(encoding='utf-8')
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate('mf-agent-2b482-firebase-adminsdk-fbsvc-3eff30e990.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()
db.collection('licenses').document('MF-O5R8-FV81-V7X2-DWUP').update({'profile_id': '30b9707f'})
doc = db.collection('licenses').document('MF-O5R8-FV81-V7X2-DWUP').get()
print('OK:', doc.to_dict())
