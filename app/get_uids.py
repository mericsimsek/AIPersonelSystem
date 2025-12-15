import firebase_admin
from firebase_admin import credentials, db
import os

# --- BAĞLANTI ---
base_path = os.getcwd()
key_path = os.path.join(base_path, "serviceAccountKey.json")

if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://fundmatch-d3750-default-rtdb.firebaseio.com' 
        })
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")
        exit()

def idleri_getir():
    print("⏳ Kullanıcı ID'leri çekiliyor...")
    
    ref = db.reference('users')
    users = ref.get()
    
    if users:
        # Sadece ID'leri (keys) alıp listeye çeviriyoruz
        uid_listesi = list(users.keys())
        
        print(f"\n✅ Toplam {len(uid_listesi)} kullanıcı bulundu.\n")
        print("👇 BU LİSTEYİ KOPYALA VE BANA AT 👇")
        print("-" * 50)
        print(uid_listesi)
        print("-" * 50)
    else:
        print("❌ Hiç kullanıcı bulunamadı.")

if __name__ == "__main__":
    idleri_getir()