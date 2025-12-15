import firebase_admin
from firebase_admin import credentials, db
from app.models.gun_analizi import GunAnalizi
from app.models.kumeleme_modeli import DavranisKumeleme
from app.models.tahmin_modeli import SureTahminModeli
from datetime import datetime
import os

# --- 1. BAĞLANTI AYARLARI ---
base_path = os.getcwd()
key_path = os.path.join(base_path, "serviceAccountKey.json")

if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://fundmatch-d3750-default-rtdb.firebaseio.com' 
        })
        print("✅ Firebase Bağlantısı Başarılı.")
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")
        exit()

def sistem_guncelle():
    print("\n🚀 AI Analiz Motoru Çalışıyor... (Veriler işleniyor)")
    print("-" * 50)
    
    # Tüm kullanıcıları çek
    users_ref = db.reference('users')
    all_users = users_ref.get()

    if not all_users:
        print("❌ Veritabanında kullanıcı bulunamadı.")
        return

    bugun = datetime.now().strftime("%Y-%m-%d")
    # Test için elle tarih verebilirsin:
    # bugun = "2025-12-05"

    # ==========================================
    # 1. HAZIRLIK: TAHMİN MODELİNİ EĞİT (Hız Skorlarını Al)
    # ==========================================
    print("🧠 Tahmin Modeli Eğitiliyor ve Hız Profilleri Çıkarılıyor...")
    ai_tahmin = SureTahminModeli(all_users)
    ai_tahmin.veri_hazirla_ve_egit()
    
    # Kullanıcıların hız katsayılarını alıyoruz {uid: 0.8, uid: 1.2 ...}
    hiz_profilleri = ai_tahmin.user_speed_factors

    # ==========================================
    # 2. AŞAMA: KİŞİSEL ANALİZLER (Her UID için)
    # ==========================================
    print(f"📊 Günlük ve Kariyer Analizleri Yapılıyor (Tarih: {bugun})...")
    
    for uid, user_data in all_users.items():
        try:
            # A. Günlük Analiz (GunAnalizi Class)
            # ------------------------------------------------
            analizci = GunAnalizi(user_data, bugun)
            sonuc = analizci.hesapla()
            
            # Verileri çek (Modeldeki return yapısına göre)
            gunluk_skor = sonuc['skor_tablosu']['gunluk_skor']
            genel_xp = sonuc['genel_kariyer_durumu']['toplam_kariyer_puani_xp']
            seviye = sonuc['genel_kariyer_durumu']['mevcut_seviye']
            oneriler = sonuc['sonuc']['yapay_zeka_onerisi']
            
            # B. Hız Analizi (Tahmin Modelinden Gelen)
            # ------------------------------------------------
            # Katsayı 1.0 ise standart (100 puan), 0.5 ise çok hızlı (200 puan), 1.5 ise yavaş.
            speed_factor = hiz_profilleri.get(uid, 1.0) 
            speed_score = int((1.0 / speed_factor) * 100) if speed_factor > 0 else 100
            
            speed_label = "Standart"
            if speed_score > 120: speed_label = "⚡ Çok Hızlı"
            elif speed_score < 80: speed_label = "🐢 Biraz Yavaş"

            # C. Mod Belirle
            daily_mood = "Stabil 😐"
            if gunluk_skor > 85: daily_mood = "Alev Aldı 🔥"
            elif gunluk_skor < 30: daily_mood = "Yorgun 😴"

            # D. Yazılacak Veri Paketi (Mobilin dinleyeceği yer)
            ai_performance_data = {
                "daily_score": round(gunluk_skor, 1),
                "general_score_xp": genel_xp,
                "career_level": seviye,
                "daily_mood": daily_mood,
                
                # Yeni Eklediğimiz Hız Verileri
                "speed_score": speed_score,
                "speed_label": speed_label,

                "action_items": oneriler, 
                "last_updated": {".sv": "timestamp"}
            }

            # E. Veritabanına Bas (users -> UID -> ai_performance)
            db.reference(f'users/{uid}/ai_performance').update(ai_performance_data)
            
            isim = user_data.get('firstName', 'İsimsiz')
            print(f"  ➜ {isim}: Günlük={gunluk_skor}, Hız={speed_label}")

        except Exception as e:
            # Bazı kullanıcılarda attendance verisi yoksa hata verebilir, devam et.
            # print(f"  ⚠️ Atlandı ({uid}) - Veri eksik olabilir.")
            pass

    # ==========================================
    # 3. AŞAMA: GLOBAL ANALİZLER (Şirket Geneli)
    # ==========================================
    print("-" * 50)
    print("🌍 Şirket Geneli (K-Means & Strateji) Analizleri Yapılıyor...")

    try:
        # A. Kümeleme Modelini Çalıştır
        kumeleyici = DavranisKumeleme(all_users)
        kume_sonuc = kumeleyici.analiz_et()
        
        # B. Listeleri Ayrıştır (Kovulacaklar vs.)
        # kume_sonuc yapısı: {'calisan_listesi': [...], 'ofis_stratejisi': {...}}
        kovulacaklar_listesi = []
        yildizlar_listesi = []

        if "calisan_listesi" in kume_sonuc:
            for calisan in kume_sonuc['calisan_listesi']:
                # Modelden dönen anahtarlar: name, suggestion, social_level, movement_level
                c_data = {
                    "name": calisan['name'],
                    "role": calisan['suggestion'],
                    "social": calisan['social_level'],   # Örn: "Yüksek (%85)"
                    "movement": calisan['movement_level'] # Örn: "Düşük (%20)"
                }
                
                # Basit Kurallar
                if "Düşük" in calisan['social_level'] and "Düşük" in calisan['movement_level']:
                    kovulacaklar_listesi.append(c_data)
                
                if "Takım" in calisan['suggestion'] or "Yüksek" in calisan['social_level']:
                    yildizlar_listesi.append(c_data)

        # C. Global Veri Paketi
        company_insights = {
            "strategy_map": kume_sonuc.get('ofis_stratejisi', {}), 
            "clusters_list": kume_sonuc.get('calisan_listesi', []),
            "risk_alert_list": kovulacaklar_listesi, 
            "star_performers": yildizlar_listesi,
            "last_updated": {".sv": "timestamp"}
        }

        # D. Veritabanına Bas (ai_company_insights)
        db.reference('ai_company_insights').set(company_insights)
        
        print("✅ Global strateji, riskli personeller ve oturma planı güncellendi.")

        # ==========================================
        # 4. AŞAMA: KİŞİSEL PROFİLE ROL EKLEME (Opsiyonel ama yararlı)
        # ==========================================
        # Kişinin hangi kümede olduğunu (Odak/Mobil) kendi profiline de yazalım.
        # İsim üzerinden eşleştirme yapıyoruz (UID elimizde listede olmadığı için)
        print("🔄 Profil Rolleri Eşitleniyor...")
        for c in kume_sonuc.get('calisan_listesi', []):
            name_to_find = c['name']
            role_to_assign = c['suggestion']
            
            # İsmi eşleşen kullanıcıyı bul (Biraz yavaş yöntem ama çalışır)
            for uid, u_data in all_users.items():
                full_name = f"{u_data.get('firstName', '')} {u_data.get('lastName', '')}".strip()
                if full_name == name_to_find:
                    db.reference(f'users/{uid}/ai_performance/cluster_role').set(role_to_assign)
                    break

    except Exception as e:
        print(f"❌ Global Analiz Hatası: {e}")

    print("-" * 50)
    print("🎉 TÜM İŞLEMLER TAMAMLANDI. MOBİL UYGULAMA İÇİN HAZIR.")

if __name__ == "__main__":
    sistem_guncelle()