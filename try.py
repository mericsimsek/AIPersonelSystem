import firebase_admin
from firebase_admin import credentials, db
import os


def init_firebase():
    main_path=os.getcwd()
    key_path=os.path.join(main_path,"Servicejson")

    if not firebase_admin._apps:
        try:
            cred=credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://fundmatch-d3750-default-rtdb.firebaseio.com'
            })
        except Exception as e:
            print("bağlantı hatası")
        return None
    return db

rtdb = init_firebase()



from fastapi import APIRouter, HTTPException, Body
from app.core.firebase_config import rtdb
from app.models.gun_analizi import GunAnalizi
from app.models.tahmin_modeli import SureTahminModeli
from app.models.kumeleme_modeli import DavranisKumeleme
from datetime import datetime
import pandas as pd


router=APIRouter()

@router.get("/günlükanaliz")
def analizgunluk(name :str, tarih: str=None):
    pass

@router.get("/tahmin")
def tahminyap(difficulty:str=Body(...,embed=True),desc:str=Body(...,embed=True)):
    pass

@router.get("/ofis-yerlesim-onerisi")
def ofis_yerlesimi():
    pass

@router.get("/günlükanalizz")
def günlükanaliz(user_id:str,tarih:str=None):
    if not tarih:
        from datetime import datetime
        tarih=datetime.now().strftime("%Y-%m-%d")

    try:
        ref=rtdb.reference(f"users/{user_id}")
        user_data=ref.get()

        if not user_data:
            return {"durum": "hata", "mesaj": "Kullanıcı bulunamadı"}
        
        analiz=günlükanaliz(user_data,tarih)
        sonuc=analiz.hesapla()#bura günlük analizden çekilcek

        return {"durum":"başarılı","data":sonuc}
    
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    
@router.post("/tahmin-et")
def suretahmini(
    difficulty: str=Body(...,embed=True),
    description :str =Body(...,embed=True),
    user_id :str = Body(None,embed=True)
):
    try:
        ref=rtdb.reference("users")
        all_users=ref.get()

        ai_model=SureTahminModeli(all_users)
        ai_model.veri_hazirla_ve_egit()

        kacdk=ai_model.tahmin_et(difficulty,description,user_id)
        category=ai_model._kategori_belirle(description)

        return {
            "durum":"basarili",
            "analiz":{
                "girdi_metni":description,
                "tespit_edilen_kategori":category,
                "zorluk":difficulty
            },
            "sonuc": {
                "tahmini_sure_dk": kacdk,
                "saat_karsiligi": f"{round(kacdk/60, 1)} Saat"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@route.get("/takımanalizi")
def takımanaliz():
    try:
        ref=rtdb.reference("users")
        all_users=ref.get()

        if not all_users: return {"mesaj":"veri yok"} 

        user_score=[]

        points_map={"easy":10,"medium":25,"hard":60,"veryhard":100}

        for uid,user in all_users.items():
            task=user.get("task",{})
            total_score=0
            completed_count=0

            for t in task.values():
                if t.get("status")=="Done":

                    diff=t.get("difficulty","medium")
                    total_score += points_map.get(diff,25)

                    completed_count +=1

            if total_score >0:
                user_score.append({
                    "name": f"{user.get('firstName')} {user.get('lastName')}",
                    "role": user.get('role', 'employee'), #rolü yoksa otomatik emp
                    "raw_score": total_score,
                    "task_count": completed_count
                })

            if not total_score:
                return {"durum":"bos","mesaj":"henüz tamamlanan görev yok"}
            
            df=pd.DataFrame(user_score)

            max_score=df["raw_score"].max()
            df['final_score'] = (df['raw_score'] / max_score) * 100
            df['final_score'] = df['final_score'].round(1)

            team_stats=df.groupby("role")["final_score"].mean().reset_index().to_dict(orient="records")

            df=df.sort_values("final_score",ascending=False)

            top_k=max(1,int(len(df)*0.2))
            top_performers = df.head(top_k).to_dict(orient='records')

            final_awards_top=[]
            for p in top_performers:
                final_awards_top.append({
                "name": p['name'],
                "score": p['final_score'],
                "badge": "🔥 MVP"
            })
                
            others=df.iloc[top_k:].head().to_dict(orient="records")

            return {
            "durum": "basarili",
            "takim_performansi": team_stats,
            "odul_listesi": final_awards_top,
            "potansiyel_adaylar": others, # MVP'yi zorlayanlar
            "mesaj": f"Toplam {len(df)} çalışan analiz edildi. En yüksek ham puan: {max_score}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    



import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

class SureTahminModeli:        
    def __init__(self,all_users_data):
        self.all_data=all_users_data
        self.model=None
        self.is_trained=False
        self.user_speed_factors={}


        self.keyword_weights = {
            # Çok Yüksek Etki (x1.5 - x2.0)
            'yapay zeka': 1.8, 'ai': 1.8, 'model': 1.6, 'eğitim': 1.5,
            'algoritma': 1.7, 'mimari': 1.7, 'architecture': 1.7,
            'optimize': 1.5, 'entegrasyon': 1.4, 'migration': 1.5,
            'security': 1.4, 'güvenlik': 1.4, 'docker': 1.3, 'kubernetes': 1.4,
            
            # Orta Etki (x1.2 - x1.4)
            'sql': 1.2, 'veri': 1.1, 'database': 1.2, 'backend': 1.3,
            'api': 1.2, 'endpoint': 1.2, 'analiz': 1.2, 'refactor': 1.3,
            
            # Düşük Etki / Kolaylaştırıcı (x0.8 - x1.0)
            'ui': 1.0, 'tasarım': 0.9, 'css': 0.9, 'renk': 0.8,
            'text': 0.8, 'metin': 0.8, 'bug': 1.1, 'fix': 0.9,
            'logo': 0.7, 'güncelleme': 0.9, 'çekme': 1.0
        }

    def _kategoribelirleme(self,text):

        text=str(text).lower()

        if any(x in text for x in ['mimari', 'architecture', 'yapı', 'docker']): return 'Architecture & DevOps'
        if any(x in text for x in ['sql', 'database', 'veri', 'tablo']): return 'Database'
        if any(x in text for x in ['ui', 'tasarım', 'css', 'frontend']): return 'Frontend'
        if any(x in text for x in ['api', 'backend', 'endpoint']): return 'Backend'
        if any(x in text for x in ['ai', 'yapay zeka', 'model', 'nlp', 'algoritma']): return 'AI & ML'
        if any(x in text for x in ['test', 'bug', 'fix']): return 'Testing & QA'
        return 'General Development'
    

    def metinzorlukçarpanı(self,text):

        text=str(text).lower()
        total_multipilier=1.0

        for word,weight in self.keyword_weights.items():
            if word in text:
                if weight > 1.0:
                    total_multipilier +=(weight - 1.0)

                else:
                    total_multipilier *=weight

        return min(3.0,max(0.5,total_multipilier))
    

    def veri_hazirlaveegit(self):
        data_list=[]

        base_minutes={"easy":60,"medium":180,"hard":480}

        for uid,u_val in self.all_data.items():
            tasks=u_val.get("task",{})

            u_task_durations=[]

            for t_val in tasks.values():

                if t_val.get("status") == "done" and "durationMinutes" in t_val:
                    desc=t_val.get("description","") or t_val.get("title","")
                    diff=t_val.get("difficulty","medium")
                    duration=float(t_val.get("durationMinutes",60))

                    data_list.append({
                        'description': desc,
                        'difficulty': diff,
                        'duration': duration
                    })


                    excepted=base_minutes.get(diff,180)
                    u_task_durations.append(duration/excepted)

                if u_task_durations:
                    avg_speed=sum(u_task_durations) / len(u_task_durations)
                    self.user_speed_factors[uid]=avg_speed

            if len(data_list) < 2:
            # Veri yoksa False dön ama crash etme
                return False
            
            df=pd.DataFrame(data_list)

            preprocessor = ColumnTransformer(
                transformers=[
                    ("text",TfidfVectorizer(max_features=200,stop_words="english"),"description"),
                    ("cat",OneHotEncoder(handle_unknown="ignore"),["difficulty"])
                ]
            )

            self.model = Pipeline([
            ('preprocessor', preprocessor),
            ('regressor', GradientBoostingRegressor(n_estimators=150, random_state=42))
        ])
            
            try:
                self.model.fit(df[["description","difficulty"]],df["duration"])
                self.is_trained=True
                print("model eğitildi")
                return True
            
            except Exception as e:
                print(f"eğitim hatası {e}")
                return False
            
    def tahminet(self,difficulty,description="",user_id=None):

        base_pred=180

        if self.is_trained:
            input_df=pd.DataFrame({"description":description,"difficulty":difficulty})
            try:
                base_pred=self.model.predict(input_df)[0]
            except:
                pass

        else:
            defaults={"easy":60,"medium":180,"hard":480}
            base_pred=defaults.get(difficulty,180)

        text_factor=self.metinzorlukçarpanı(description)

        user_factor=1.0
        if user_id and user_id in self.user_speed_factors:
            user_factor=self.user_speed_factors[user_id]

            user_factor=(user_factor +1.0) /2.0

            final_prediction = base_pred * text_factor * user_factor

        # Mantıksız sonuçları engelle (Min 10 dk, Max 24 saat)
        return int(max(10, min(1440, final_prediction)))
    


import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime

class DavranisKumeleme:
    def __init__(self, all_users_data):
        self.all_data = all_users_data

    def _safe_ts_convert(self,value):
        if value is None: return 0

        try:
            return(float(value))
        except ValueError:
            try:
                dt=pd.to_datetime(value)
                return dt.timestamp*1000
            except:
                return 0
    
    def zaman_cakismasi(self,user_intervals):
        social_scores={uid:0 for uid in user_intervals}
        all_hours=[]

        for uid,intervals in user_intervals:
            for interval in intervals:
                try:
                    start_ts=interval["start"]
                    end_ts=interval["end"]
                    if start_ts == 0 and end_ts== 0 : continue
                    start_h=datetime.fromtimestamp(start_ts/1000).hour
                    end_h=datetime.fromtimestamp(end_h/1000).hour
                    if end_h>=start_h:
                        all_hours.extend([f"{h}" for h in range(start_h , end_h +1)])
                except:continue

        from collections import Counter
        occupancy=Counter(all_hours)

        for uid,intervals in user_intervals:
            score=0
            for interval in intervals:
                try:
                    start_ts=interval["start"]
                    end_ts=interval["end"]
                    if start_ts==0 and end_ts==0: continue
                    start_h = datetime.fromtimestamp(start_ts / 1000).hour
                    end_h = datetime.fromtimestamp(end_ts / 1000).hour
                    if end_h>start_h:
                        for h in range(start_h, end_h + 1):
                            # O saatteki kişi sayısı
                            density = occupancy.get(str(h), 1)
                            score += density
                except: continue
            social_scores[uid] = score
        return social_scores
    
    def _aksiyon_plani(self, df):
        plan = {}
        # En yüksek puanlıları al
        focus = df[df['suggestion'].str.contains("Odak")].head(5)['name'].tolist()
        mobile = df[df['suggestion'].str.contains("Mobil")].head(5)['name'].tolist()
        social = df[df['suggestion'].str.contains("Takım")].head(5)['name'].tolist()

        plan['Odak_Odasi_Adaylari'] = {
            "kisiler": focus,
            "neden": "Düşük hareketlilik ve izole çalışma saatleri.",
            "oneri": "Gürültüden uzak 'Deep Work' odasına yerleştirin."
        }
        plan['Operasyon_Merkezi_Adaylari'] = {
            "kisiler": mobile,
            "neden": "Sık giriş-çıkış trafiği.",
            "oneri": "Kapıya ve koridora en yakın masaları verin."
        }
        plan['Etkilesim_Liderleri'] = {
            "kisiler": social,
            "neden": "Ofis yoğunluğunun en yüksek olduğu anlarda aktiﬂer.",
            "oneri": "Ekibin merkezinde konumlandırın, bilgi akışını sağlarlar."
        }
        return plan
    

    def _human_readable_score(self, value, max_val):
        """Devasa sayıları 0-100 arası puana ve sıfata çevirir."""
        if max_val == 0: return {"puan": 0, "etiket": "Düşük"}
        
        ratio = (value / max_val) * 100
        score = int(ratio)
        
        label = "Düşük"
        if score > 80: label = "Çok Yüksek"
        elif score > 60: label = "Yüksek"
        elif score > 40: label = "Orta"
        
        return {"puan": score, "etiket": label}
    
    def _akilli_kumeleme_duzeltme(self, row, avg_social, avg_move):
        """
        K-Means bazen hata yapabilir. Bu fonksiyon insan mantığıyla düzeltir (Hibrit).
        """
        # EŞİK DEĞERLERİ (Ortalamaya göre dinamik)
        is_very_social = row['social_score'] > (avg_social * 1.2) # Ortalamadan %20 fazla sosyal
        is_very_mobile = row['movement_density'] > (avg_move * 1.3) # Ortalamadan %30 fazla hareketli
        
        # 1. KURAL: Çok hareketliyse kesinlikle Mobildir (Sosyalliği ne olursa olsun)
        if is_very_mobile:
            return "🚀 Yüksek Mobilite (Saha/Operasyon)"
        
        # 2. KURAL: Hareketi az ama Sosyalliği çok yüksekse -> Takım Lideridir (Odak değil!)
        if not is_very_mobile and is_very_social:
            return "🤝 Takım Oyuncusu / Mentor (Hub)"
            
        # 3. KURAL: Hareketi az ve Sosyalliği ortalamaysa -> Odak
        return "🧘 Derin Odak (Teknik/Yazılım)"
    
    def analiz(self):
        user_stats=[]
        users_intervals = {}

        for uid,u_val in self.all_data.items():
            tasks=u_val.get("tasks",{})
            attedance=u_val.get("attedance",{})
            completed_tasks=len([t for t in tasks.values() if t.get("status")=="done"])

            total_movement = 0
            total_hours_worked = 0.1 
            intervals = []

            for date_val in attedance.values():
                recs = date_val.get('records', {})
                if not recs: continue
                
                clean_recs = []
                for r in recs.values():
                    ts=self._safe_ts_convert(r.get("timestemp"))
                    if ts >0 :
                        r_copy=ts.copy()
                        r_copy["timestamp"]=ts
                        clean_recs.append(r_copy)
                recs_list=sorted(clean_recs,key=lambda x :x["timestamp"])
                total_movement +=len(recs_list)

                entries = [r for r in recs_list if r['type'] == 'entry']
                exits = [r for r in recs_list if r['type'] == 'exit']

                if entries and exits:
                    t_start=entries[0]["timestamp"]
                    t_end=exit[-1]["timestamp"]
                    duration_hours = (t_end - t_start) / (1000 * 3600)
                    if duration_hours > 0:
                        total_hours_worked += duration_hours
                        intervals.append({'start': t_start, 'end': t_end})
            
            users_intervals[uid] = intervals
            # Hareket Yoğunluğu: (GirişÇıkış Sayısı / Saat) * 10 (Okunabilir olsun diye 10 la çarptık)
            movement_density = (total_movement / total_hours_worked) * 10 if total_hours_worked > 0.5 else 0

            if total_movement > 0 or completed_tasks > 0:
                user_stats.append({
                    'user_id': uid,
                    'name': f"{u_val.get('firstName', 'User')} {u_val.get('lastName', '')}",
                    'raw_movement': movement_density, # İşlenmemiş
                    'completed_tasks': completed_tasks
                })

        if len(user_stats) < 2: return {"mesaj": "Yetersiz veri."}
        social_scores = self._zaman_cakismasi_hesapla(users_intervals)
        for u in user_stats:
            u['raw_social'] = social_scores.get(u['user_id'], 0)

        df = pd.DataFrame(user_stats)
        df = df.fillna(0)

        # --- 3. NORMALİZASYON VE OKUNABİLİRLİK ---
        max_social = df['raw_social'].max()
        max_move = df['raw_movement'].max()
        
        # Ham verileri 0-100 arasına ve metne çevir
        df['social_readable'] = df['raw_social'].apply(lambda x: self._human_readable_score(x, max_social))
        df['move_readable'] = df['raw_movement'].apply(lambda x: self._human_readable_score(x, max_move))
        
        # Analiz için sayısal kopyalar (Sklearn için)
        df['social_score'] = df['raw_social']
        df['movement_density'] = df['raw_movement']

        # --- 4. AKILLI ETİKETLEME (Dinamik Eşikli) ---
        # Ortalamaları hesapla (Benchmark)
        avg_social = df['social_score'].mean()
        avg_move = df['movement_density'].mean()
        
        # Her satır için Kural Motorunu çalıştır
        df['suggestion'] = df.apply(lambda row: self._akilli_kumeleme_duzeltme(row, avg_social, avg_move), axis=1)

        # --- 5. SONUÇ FORMATLAMA ---
        final_list = []
        for _, row in df.iterrows():
            soc = row['social_readable']
            mov = row['move_readable']
            
            final_list.append({
                "name": row['name'],
                "suggestion": row['suggestion'],
                # Kullanıcı Dostu Çıktılar:
                "social_level": f"{soc['etiket']} (%{soc['puan']})", 
                "movement_level": f"{mov['etiket']} (%{mov['puan']})",
                # Grafik çizdirmek isterlerse diye ham veriyi de gizli tutuyoruz ama önplana çıkarmıyoruz
                "_debug_social": row['social_score'],
                "_debug_move": row['movement_density']
            })

        # Sosyal puana göre sırala (En popüler en üstte)
        final_list = sorted(final_list, key=lambda x: x['_debug_social'], reverse=True)
        
        aksiyon_plani = self._aksiyon_plani(df)

        return {
            "analiz_ozeti": f"Ofis Ortalaması: Sosyal Skor {int(avg_social)}, Hareket {round(avg_move, 1)}",
            "calisan_listesi": final_list,
            "ofis_stratejisi": aksiyon_plani
        }
