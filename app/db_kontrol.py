import firebase_admin
from firebase_admin import credentials, db
import os

# Firebase Bağlantısı
base_path = os.getcwd()
key_path = os.path.join(base_path, "serviceAccountKey.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://fundmatch-d3750-default-rtdb.firebaseio.com'
    })

def verileri_listele():
    ref = db.reference('users')
    users = ref.get()
    
    if not users:
        print("❌ Veritabanı BOŞ! Önce create_dummy_data.py çalıştır.")
        return

    print("\n🔎 KULLANILABİLİR ID VE TARİHLER:")
    print("-" * 40)
    
    for uid, data in users.items():
        attendance = data.get('attendance', {})
        if attendance:
            # Sadece ilk ve son tarihi gösterelim kalabalık olmasın
            tarihler = list(attendance.keys())
            print(f"👤 User ID: {uid}")
            print(f"📅 Tarihler: {tarihler[0]} ... {tarihler[-1]}")
            print("-" * 20)
        else:
            print(f"👤 User ID: {uid} (HİÇ LOG YOK)")

verileri_listele()