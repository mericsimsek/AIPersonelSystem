import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime

class DavranisKumeleme:
    def __init__(self, all_users_data):
        self.all_data = all_users_data

    def _safe_ts_converter(self, value):
        if value is None: return 0
        try:
            return float(value)
        except ValueError:
            try:
                dt = pd.to_datetime(value)
                return dt.timestamp() * 1000
            except:
                return 0

    def _zaman_cakismasi_hesapla(self, users_intervals):
        social_scores = {uid: 0 for uid in users_intervals}
        all_hours = []
        
        for uid, intervals in users_intervals.items():
            for interval in intervals:
                try:
                    start_ts = interval['start']
                    end_ts = interval['end']
                    if start_ts == 0 or end_ts == 0: continue
                    start_h = datetime.fromtimestamp(start_ts / 1000).hour
                    end_h = datetime.fromtimestamp(end_ts / 1000).hour
                    if end_h >= start_h:
                        all_hours.extend([f"{h}" for h in range(start_h, end_h + 1)])
                except: continue
        
        from collections import Counter
        occupancy = Counter(all_hours) 

        for uid, intervals in users_intervals.items():
            score = 0
            for interval in intervals:
                try:
                    start_ts = interval['start']
                    end_ts = interval['end']
                    if start_ts == 0 or end_ts == 0: continue
                    start_h = datetime.fromtimestamp(start_ts / 1000).hour
                    end_h = datetime.fromtimestamp(end_ts / 1000).hour
                    if end_h >= start_h:
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

    def analiz_et(self):
        user_stats = []
        users_intervals = {} 

        # --- 1. VERİ İŞLEME ---
        for uid, u_val in self.all_data.items():
            tasks = u_val.get('tasks', {})
            attendance = u_val.get('attendance', {})
            completed_tasks = len([t for t in tasks.values() if t.get('status') == 'done'])
            
            total_movement = 0
            total_hours_worked = 0.1 
            intervals = []

            for date_val in attendance.values():
                recs = date_val.get('records', {})
                if not recs: continue
                
                clean_recs = []
                for r in recs.values():
                    ts = self._safe_ts_converter(r.get('timestamp'))
                    if ts > 0:
                        r_copy = r.copy()
                        r_copy['timestamp'] = ts
                        clean_recs.append(r_copy)

                recs_list = sorted(clean_recs, key=lambda x: x['timestamp'])
                total_movement += len(recs_list)
                
                entries = [r for r in recs_list if r['type'] == 'entry']
                exits = [r for r in recs_list if r['type'] == 'exit']
                
                if entries and exits:
                    t_start = entries[0]['timestamp']
                    t_end = exits[-1]['timestamp']
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

        # --- 2. SOSYAL SKOR ---
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