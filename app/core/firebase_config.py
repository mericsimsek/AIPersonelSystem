import firebase_admin
from firebase_admin import credentials, db
import os

def init_firebase():
    base_path = os.getcwd()
    key_path = os.path.join(base_path, "serviceAccountKey.json")

    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(key_path)
            # Realtime Database için URL şarttır:
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://fundmatch-d3750-default-rtdb.firebaseio.com'
            })
            print("✅ Realtime Database Bağlantısı Başarılı!")
        except Exception as e:
            print(f"❌ Bağlantı Hatası: {e}")
            return None
    
    # Veritabanı modülünü döndür
    return db

# Diğer dosyalarda kullanacağımız nesne
rtdb = init_firebase()