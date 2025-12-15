import firebase_admin
from firebase_admin import credentials, db
import os
import time
import random

# --- 1. BAĞLANTI ---
base_path = os.getcwd()
key_path = os.path.join(base_path, "serviceAccountKey.json")

if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://fundmatch-d3750-default-rtdb.firebaseio.com' 
        })
        print("✅ Bağlantı Hazır.")
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")
        exit()

def gercek_verilerle_test_et():
    print("📥 Veritabanındaki GERÇEK Görevler Çekiliyor...")
    
    ref_users = db.reference('users')
    all_users = ref_users.get()
    
    if not all_users:
        print("❌ Kullanıcı yok.")
        return

    # --- ADIM 1: GÖREV HAVUZU OLUŞTUR ---
    # Tüm kullanıcıların tasklarını tek bir havuzda toplayalım
    gercek_gorev_havuzu = []
    user_ids = list(all_users.keys()) # Kullanıcı ID listesi

    for uid, data in all_users.items():
        tasks = data.get('tasks', {})
        for t_id, t_data in tasks.items():
            # Sadece açıklaması olan görevleri alalım
            if 'description' in t_data and 'difficulty' in t_data:
                gercek_gorev_havuzu.append({
                    "description": t_data['description'],
                    "difficulty": t_data['difficulty'],
                    "kaynak_user": data.get('firstName', 'Bilinmiyor') # Kimin göreviydi?
                })

    print(f"✅ Toplam {len(gercek_gorev_havuzu)} adet gerçek görev bulundu.\n")
    print("🚀 Simülasyon Başlıyor: Bu görevler rastgele kişilere sorulacak...\n")

    # --- ADIM 2: RASTGELE ATAMA VE TAHMİN ---
    # 20 tane deneme yapalım
    for i in range(1, 21):
        # A. Rastgele bir gerçek görev seç
        secilen_gorev = random.choice(gercek_gorev_havuzu)
        
        # B. Rastgele bir hedef kullanıcı seç
        hedef_uid = random.choice(user_ids)
        hedef_user_name = all_users[hedef_uid].get('firstName', 'User')

        # C. İstek Paketini Hazırla
        istek_verisi = {
            "difficulty": secilen_gorev['difficulty'],
            "description": secilen_gorev['description'], # Gerçek açıklama!
            "status": "pending",
            "timestamp": {".sv": "timestamp"}
        }

        # D. Veritabanına Yaz (AI Listener bunu yakalayacak)
        path = f"users/{hedef_uid}/ai_interaction/predict_request"
        
        try:
            db.reference(path).set(istek_verisi)
            
            print(f"[{i}] 📤 {hedef_user_name} kişisine soruldu:")
            print(f"    📝 Görev: {secilen_gorev['description'][:40]}...")
            print(f"    🏷️ Zorluk: {secilen_gorev['difficulty']}")
            print(f"    🔙 Kaynak: Bu görev aslında {secilen_gorev['kaynak_user']} kişisine aitti.\n")
            
        except Exception as e:
            print(f"❌ Hata: {e}")
        
        # Biraz bekle ki terminal aksın
        time.sleep(1.5)

    print("\n🏁 Test Tamamlandı. AI Listener terminaline bak!")

if __name__ == "__main__":
    gercek_verilerle_test_et()