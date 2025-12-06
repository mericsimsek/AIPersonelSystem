from fastapi import APIRouter, HTTPException, Body
from app.core.firebase_config import rtdb
from app.models.gun_analizi import GunAnalizi
from app.models.tahmin_modeli import SureTahminModeli
from app.models.kumeleme_modeli import DavranisKumeleme
from datetime import datetime
import pandas as pd
router = APIRouter()

# --- 1. GÜNLÜK ANALİZ ---
# --- 1. GÜNLÜK ANALİZ (Detaylı) ---
@router.get("/gunluk-analiz")
def analiz_getir(user_id: str, tarih: str = None):
    # Tarih yoksa bugünü al
    if not tarih:
        from datetime import datetime
        tarih = datetime.now().strftime("%Y-%m-%d")

    try:
        ref = rtdb.reference(f'users/{user_id}')
        user_data = ref.get()

        if not user_data:
            return {"durum": "hata", "mesaj": "Kullanıcı bulunamadı"}

        analizci = GunAnalizi(user_data, tarih)
        sonuc = analizci.hesapla()

        return {"durum": "basarili", "data": sonuc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. TAHMİN (Hatasız) ---
@router.post("/tahmin-et")
def sure_tahmini(
    difficulty: str = Body(..., embed=True), 
    description: str = Body(..., embed=True),
    user_id: str = Body(None, embed=True)
):
    try:
        ref = rtdb.reference('users')
        all_users = ref.get()
        
        ai_model = SureTahminModeli(all_users)
        ai_model.veri_hazirla_ve_egit()
        
        # Tahmin ve Kategori
        sonuc_dk = ai_model.tahmin_et(difficulty, description, user_id)
        # Artık bu fonksiyon modelin içinde var, hata vermez:
        kategori = ai_model._kategori_belirle(description) 

        return {
            "durum": "basarili",
            "analiz": {
                "girdi_metni": description,
                "tespit_edilen_kategori": kategori,
                "zorluk": difficulty
            },
            "sonuc": {
                "tahmini_sure_dk": sonuc_dk,
                "saat_karsiligi": f"{round(sonuc_dk/60, 1)} Saat"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ... (gunluk-analiz ve yerlesim-onerisi AYNI KALSIN) ...

# --- GÜNCELLENMİŞ TAHMİN (Kişi + İçerik Odaklı) ---
@router.post("/tahmin-et")
def sure_tahmini(
    difficulty: str = Body(..., embed=True), 
    description: str = Body(..., embed=True),
    user_id: str = Body(None, embed=True) # Opsiyonel: Kimin için tahmin?
):
    try:
        ref = rtdb.reference('users')
        all_users = ref.get()

        if not all_users:
            return {"durum": "hata", "mesaj": "Veri yok"}

        # Modeli Eğit
        ai_model = SureTahminModeli(all_users)
        basari = ai_model.veri_hazirla_ve_egit()

        if not basari:
            return {"durum": "hata", "mesaj": "Model eğitimi başarısız"}

        # Tahmin Yap
        sonuc_dk = ai_model.tahmin_et(difficulty, description, user_id)

        # Mesajı dinamik yap
        msg = "Genel verilere göre tahmin edildi."
        if user_id:
            msg = "Kullanıcının geçmiş performansına ve işin türüne göre kişiselleştirildi."

        return {
            "durum": "basarili",
            "girdi": {"zorluk": difficulty, "tanim": description, "kategori": ai_model._kategori_belirle(description)},
            "tahmini_sure_dk": sonuc_dk,
            "mesaj": msg
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- GÜNCELLENMİŞ TAKIM ANALİZİ (Dinamik Skorlama) ---
@router.get("/takim-analizi")
def takim_sinerjisi():
    try:
        ref = rtdb.reference('users')
        all_users = ref.get()
        
        if not all_users: return {"mesaj": "Veri yok"}

        user_scores = []
        
        # Puanlama Tablosu
        points_map = {"easy": 10, "medium": 25, "hard": 60, "veryHard": 100}

        for uid, user in all_users.items():
            tasks = user.get('tasks', {})
            total_score = 0
            completed_count = 0
            
            for t in tasks.values():
                if t.get('status') == 'done':
                    diff = t.get('difficulty', 'medium')
                    total_score += points_map.get(diff, 25)
                    completed_count += 1
            
            # Eğer hiç task yoksa listeye alma
            if total_score > 0:
                user_scores.append({
                    "name": f"{user.get('firstName')} {user.get('lastName')}",
                    "role": user.get('role', 'employee'),
                    "raw_score": total_score,
                    "task_count": completed_count
                })

        if not user_scores:
            return {"durum": "bos", "mesaj": "Henüz tamamlanmış görev yok."}

        # 1. Normalizasyon (En yüksek puan alana göre 100'lük sisteme çek)
        df = pd.DataFrame(user_scores)
        max_score = df['raw_score'].max()
        
        # Herkesin puanını max puana bölüp 100 ile çarpıyoruz
        df['final_score'] = (df['raw_score'] / max_score) * 100
        df['final_score'] = df['final_score'].round(1)

        # 2. Takım Ortalamaları
        team_stats = df.groupby('role')['final_score'].mean().reset_index().to_dict(orient='records')

        # 3. MVP Belirleme (Sadece ilk 3 kişi veya %20)
        df = df.sort_values('final_score', ascending=False)
        top_k = max(1, int(len(df) * 0.2)) # En iyi %20
        top_performers = df.head(top_k).to_dict(orient='records')
        
        # Badge ekle
        final_award_list = []
        for p in top_performers:
            final_award_list.append({
                "name": p['name'],
                "score": p['final_score'],
                "badge": "🔥 MVP"
            })
        
        # Geri kalanlar (Sıralı liste için opsiyonel)
        others = df.iloc[top_k:].head(5).to_dict(orient='records') # Sonraki 5 kişi

        return {
            "durum": "basarili",
            "takim_performansi": team_stats,
            "odul_listesi": final_award_list,
            "potansiyel_adaylar": others, # MVP'yi zorlayanlar
            "mesaj": f"Toplam {len(df)} çalışan analiz edildi. En yüksek ham puan: {max_score}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. KÜMELEME (Ofis Yerleşimi) ---
@router.get("/ofis-yerlesim-onerisi")
def ofis_yerlesimi():
    try:
        ref = rtdb.reference('users')
        all_users = ref.get()
        
        if not all_users: return {"mesaj": "Veri yok"}

        cluster_model = DavranisKumeleme(all_users)
        sonuclar = cluster_model.analiz_et()

        return {
            "durum": "basarili",
            "analiz_turu": "K-Means Clustering",
            "data": sonuclar
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/takim-analizi")
def takim_sinerjisi():
    try:
        ref = rtdb.reference('users')
        all_users = ref.get()
        
        if not all_users: return {"mesaj": "Veri yok"}

        user_scores = []
        
        # Puanlama Tablosu
        points_map = {"easy": 10, "medium": 25, "hard": 60, "veryHard": 100}

        for uid, user in all_users.items():
            tasks = user.get('tasks', {})
            total_score = 0
            completed_count = 0
            
            for t in tasks.values():
                if t.get('status') == 'done':
                    diff = t.get('difficulty', 'medium')
                    total_score += points_map.get(diff, 25)
                    completed_count += 1
            
            # Eğer hiç task yoksa listeye alma
            if total_score > 0:
                user_scores.append({
                    "name": f"{user.get('firstName')} {user.get('lastName')}",
                    "role": user.get('role', 'employee'),
                    "raw_score": total_score,
                    "task_count": completed_count
                })

        if not user_scores:
            return {"durum": "bos", "mesaj": "Henüz tamamlanmış görev yok."}

        # 1. Normalizasyon (En yüksek puan alana göre 100'lük sisteme çek)
        df = pd.DataFrame(user_scores)
        max_score = df['raw_score'].max()
        
        # Herkesin puanını max puana bölüp 100 ile çarpıyoruz
        df['final_score'] = (df['raw_score'] / max_score) * 100
        df['final_score'] = df['final_score'].round(1)

        # 2. Takım Ortalamaları
        team_stats = df.groupby('role')['final_score'].mean().reset_index().to_dict(orient='records')

        # 3. MVP Belirleme (Sadece ilk 3 kişi veya %20)
        df = df.sort_values('final_score', ascending=False)
        top_k = max(1, int(len(df) * 0.2)) # En iyi %20
        top_performers = df.head(top_k).to_dict(orient='records')
        
        # Badge ekle
        final_award_list = []
        for p in top_performers:
            final_award_list.append({
                "name": p['name'],
                "score": p['final_score'],
                "badge": "🔥 MVP"
            })
        
        # Geri kalanlar (Sıralı liste için opsiyonel)
        others = df.iloc[top_k:].head(5).to_dict(orient='records') # Sonraki 5 kişi

        return {
            "durum": "basarili",
            "takim_performansi": team_stats,
            "odul_listesi": final_award_list,
            "potansiyel_adaylar": others, # MVP'yi zorlayanlar
            "mesaj": f"Toplam {len(df)} çalışan analiz edildi. En yüksek ham puan: {max_score}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))