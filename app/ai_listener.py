import firebase_admin
from firebase_admin import credentials, db
from app.models.tahmin_modeli import SureTahminModeli
import os
import json

# --- BAĞLANTI ---
if not firebase_admin._apps:
    base_path = os.getcwd()
    key_path = os.path.join(base_path, "serviceAccountKey.json")
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://fundmatch-d3750-default-rtdb.firebaseio.com' 
    })

print("👂 AI Dinleyici (Stream Modu) Aktif... Kotayı yemeden bekliyor.")

# Modeli bir kez eğit
print("🧠 Model hazırlanıyor...")
ref_users = db.reference('users')
ai_model = SureTahminModeli(ref_users.get()) # İlk açılışta bir kere çeker, sonra çekmez.
ai_model.veri_hazirla_ve_egit()
print("✅ Model Hazır! Değişiklikler dinleniyor...")

def olayi_yakala(event):
    """
    Sadece veritabanında bir değişiklik olduğunda tetiklenir.
    Veri harcamaz, sadece değişen küçücük parçayı getirir.
    """
    # event.path: Değişikliğin olduğu yol (Örn: /uid123/ai_interaction/predict_request)
    # event.data: Yeni girilen veri
    
    if event.data is None: 
        return

    # Sadece 'predict_request' ile ilgili bir değişiklik mi?
    if 'predict_request' in event.path and isinstance(event.data, dict):
        
        req = event.data
        
        # Eğer statüsü 'pending' ise işlem yap
        if req.get('status') == 'pending':
            # Path'den UID'yi ayıkla: /UID/ai_interaction/predict_request
            path_parts = event.path.split('/')
            # Genelde path boş string ile başlar: ['', 'UID', ...]
            try:
                uid = path_parts[1] 
            except:
                # Bazen path tam gelmeyebilir, kök dizinden dinlediğimiz için dikkatli olmalıyız
                # Event path kökten gelmiyorsa, data içinden anlamaya çalışabiliriz ama
                # Stream'de en garantisi path'i parse etmektir.
                print(f"⚠️ UID okunamadı: {event.path}")
                return

            print(f"📨 Yeni İstek Yakalandı! Kullanıcı: {uid}")

            # 1. Tahmin Yap
            desc = req.get('description', '')
            diff = req.get('difficulty', 'medium')
            
            tahmin_dk = ai_model.tahmin_et(diff, desc, uid)
            kategori = ai_model._kategori_belirle(desc)
            
            # 2. Cevabı Hazırla
            response = {
                "predicted_minutes": tahmin_dk,
                "category": kategori,
                "human_time": f"{int(tahmin_dk/60)}sa {tahmin_dk%60}dk",
                "processed_at": {".sv": "timestamp"}
            }
            
            # 3. Cevabı Yaz ve İsteği Kapat (Sadece ilgili düğümlere update atar)
            updates = {
                f"users/{uid}/ai_interaction/predict_response": response,
                f"users/{uid}/ai_interaction/predict_request/status": "completed"
            }
            db.reference().update(updates)
            print(f"✅ Cevaplandı: {tahmin_dk} dk ({kategori})")

# DİNLEYİCİYİ BAŞLAT (LISTEN)
# Bu satır açık bir soket bağlantısı kurar ve sadece değişiklikleri bekler.
# Döngüye gerek yoktur, program kapanmaz.
try:
    db.reference('users').listen(olayi_yakala)
except Exception as e:
    print(f"Bağlantı koptu: {e}")