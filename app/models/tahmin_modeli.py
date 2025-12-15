import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

class SureTahminModeli:
    def __init__(self, all_users_data):
        self.all_data = all_users_data
        self.model = None
        self.is_trained = False
        self.user_speed_factors = {} 

        # --- GELİŞMİŞ NLP SÖZLÜĞÜ ---
        # Kelime bazlı zorluk çarpanları.
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

    def _kategori_belirle(self, text):
        """
        API Response için kategoriyi belirler.
        Router tarafında çağrıldığı için BU FONKSİYON ŞARTTIR.
        """
        text = str(text).lower()
        if any(x in text for x in ['mimari', 'architecture', 'yapı', 'docker']): return 'Architecture & DevOps'
        if any(x in text for x in ['sql', 'database', 'veri', 'tablo']): return 'Database'
        if any(x in text for x in ['ui', 'tasarım', 'css', 'frontend']): return 'Frontend'
        if any(x in text for x in ['api', 'backend', 'endpoint']): return 'Backend'
        if any(x in text for x in ['ai', 'yapay zeka', 'model', 'nlp', 'algoritma']): return 'AI & ML'
        if any(x in text for x in ['test', 'bug', 'fix']): return 'Testing & QA'
        return 'General Development'


    def _metin_zorluk_carpani(self, text):
        """
        Metnin içindeki kelimelere bakarak bir 'Karmaşıklık Çarpanı' hesaplar.
        """

        text = str(text).lower()
        total_multiplier = 1.0

        for word, weight in self.keyword_weights.items():
            if word in text:
                # Çarpanları kümülatif ekle
                
                if weight > 1.0:
                    total_multiplier += (weight - 1.0)
                else:
                    total_multiplier *= weight 
        
        # Tavan sınır koy (Bir iş max 3 kat uzasın, min yarıya düşsün)
        return min(3.0, max(0.5, total_multiplier))

    def veri_hazirla_ve_egit(self):
        data_list = []
        
        # Standart süreler (Benchmark)
        base_minutes = {"easy": 60, "medium": 180, "hard": 480}

        for uid, u_val in self.all_data.items():
            tasks = u_val.get('tasks', {})
            
            # Kullanıcı hız analizi için liste
            u_tasks_durations = []
            
            for t_val in tasks.values():
                if t_val.get('status') == 'done' and 'durationMinutes' in t_val:
                    desc = t_val.get('description', '') or t_val.get('title', '')
                    diff = t_val.get('difficulty', 'medium')
                    duration = float(t_val.get('durationMinutes', 60))
                    
                    data_list.append({
                        'description': desc,
                        'difficulty': diff,
                        'duration': duration
                    })

                    # Kullanıcı performans hesabı

                    expected = base_minutes.get(diff, 180)
                    u_tasks_durations.append(duration / expected)
            

            # Kullanıcının ortalama hız katsayısı
            if u_tasks_durations:
                avg_speed = sum(u_tasks_durations) / len(u_tasks_durations)
                self.user_speed_factors[uid] = avg_speed

        if len(data_list) < 2:
            # Veri yoksa False dön ama crash etme
            return False

        df = pd.DataFrame(data_list)

        # --- GELİŞMİŞ ML PIPELINE ---
        # 1. Metni TF-IDF ile vektöre çevir
        # 2. Zorluğu OneHot ile kodla
        # 3. GradientBoosting kullan
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('text', TfidfVectorizer(max_features=200, stop_words='english'), 'description'),
                ('cat', OneHotEncoder(handle_unknown='ignore'), ['difficulty'])
            ]
        )

        self.model = Pipeline([
            ('preprocessor', preprocessor),
            ('regressor', GradientBoostingRegressor(n_estimators=150, random_state=42))
        ])

        try:
            self.model.fit(df[['description', 'difficulty']], df['duration'])
            self.is_trained = True
            print(f"✅ Gelişmiş Model Eğitildi ({len(df)} görev).")
            return True
        except Exception as e:
            print(f"Eğitim hatası: {e}")
            return False

    def tahmin_et(self, difficulty, description="", user_id=None):
        """
        Hibrit Tahmin: ML Model + Kural Tabanlı NLP + Kişi Profili
        """
        # 1. BASELINE (ML Tahmini veya Varsayılan)
        base_prediction = 180 # Fallback
        
        if self.is_trained:
            input_df = pd.DataFrame([{'description': description, 'difficulty': difficulty}])
            try:
                base_prediction = self.model.predict(input_df)[0]
            except:
                pass
        else:
            defaults = {"easy": 60, "medium": 180, "hard": 480}
            base_prediction = defaults.get(difficulty, 180)

        # 2. NLP ÇARPANI (Kelime Ağırlıkları)
        text_factor = self._metin_zorluk_carpani(description)
        
        # 3. KULLANICI ÇARPANI
        user_factor = 1.0
        if user_id and user_id in self.user_speed_factors:
            user_factor = self.user_speed_factors[user_id]
            # Çarpanı yumuşat
            user_factor = (user_factor + 1.0) / 2.0 

        # --- HESAPLAMA ---
        final_prediction = base_prediction * text_factor * user_factor

        # Mantıksız sonuçları engelle (Min 10 dk, Max 24 saat)
        return int(max(10, min(1440, final_prediction)))