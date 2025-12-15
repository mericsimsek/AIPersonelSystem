import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class GunAnalizi:
    def __init__(self, user_data, analiz_tarihi):
        self.user_data = user_data
        self.tarih = analiz_tarihi
        self.logs = pd.DataFrame()
        self.tasks = pd.DataFrame()
        
        # --- LOG VE TASK PARSE İŞLEMLERİ (Öncekiyle Aynı Temel) ---
        self._veri_hazirla()

    def _veri_hazirla(self):
        # Logları Çek
        try:
            # Veriyi bul: Kullanıcının attendance klasörüne gir, 'bugünün tarihini' bul.
            attendance_root = self.user_data.get('attendance', {})
            gunluk_veri = attendance_root.get(self.tarih, {})

            records = gunluk_veri.get('records', {})
            # Listeye çevir ve Pandas Tablosu (Excel gibi düşün) yap
            logs_list = list(records.values())
            
            if logs_list:
                self.logs = pd.DataFrame(logs_list)
                # --- KRİTİK KISIM (Hata Önleyici) ---
                # Sorun: Veritabanında tarihler bazen SAYI (172567...), bazen YAZI ("2025-05...") olarak karışık duruyor.
                # Çözüm: Kod diyor ki;
                # 1. Önce hepsini SAYI (ms) sanıp çevirmeyi dene.
                
                self.logs['temp_ts'] = pd.to_datetime(self.logs['timestamp'], unit='ms', errors='coerce')

                mask = self.logs['temp_ts'].isna()

                if mask.any():
                    self.logs.loc[mask, 'temp_ts'] = pd.to_datetime(self.logs.loc[mask, 'timestamp'], errors='coerce')
                self.logs['timestamp'] = self.logs['temp_ts']
                self.logs = self.logs.dropna(subset=['timestamp']).sort_values('timestamp')
        except: pass

        # Taskları Çek (Sadece bugün bitenler)
        try:
            tasks_dict = self.user_data.get('tasks', {})
            if tasks_dict:
                df_tasks = pd.DataFrame(list(tasks_dict.values()))
                if not df_tasks.empty and 'completedAt' in df_tasks.columns:
                    df_tasks['completedAt'] = pd.to_datetime(df_tasks['completedAt'], errors='coerce')
                    self.tasks = df_tasks[
                        (df_tasks['status'] == 'done') & 
                        (df_tasks['completedAt'].dt.strftime('%Y-%m-%d') == self.tarih)
                    ].copy()
        except: pass

    def _genel_kariyer_analizi(self):
        """
        Kullanıcının geçmişten bugüne TOPLAM skorunu ve seviyesini hesaplar.
        """
        tasks = self.user_data.get('tasks', {})
        total_xp = 0
        total_completed = 0
        
        puan_katalogu = {"easy": 15, "medium": 35, "hard": 70, "veryHard": 100}
        
        for t in tasks.values():
            if t.get('status') == 'done':
                diff = t.get('difficulty', 'medium')
                total_xp += puan_katalogu.get(diff, 25)
                total_completed += 1
        
        # Seviye Belirleme (Gamification)
        level = "Junior"
        if total_xp > 5000: level = "Lead / Architect"
        elif total_xp > 2000: level = "Senior"
        elif total_xp > 500: level = "Mid-Level"
        
        return {
            "toplam_biten_is": total_completed,
            "toplam_kariyer_puani_xp": total_xp,
            "mevcut_seviye": level
        }

    def hesapla(self):
        # 1. ZAMAN HESAPLARI
        ilk_giris, son_cikis = "-", "-"
        ofis_dk, mola_dk = 0, 0
        
        if not self.logs.empty:
            t1 = self.logs.iloc[0]['timestamp']
            t2 = self.logs.iloc[-1]['timestamp']
            ilk_giris = t1.strftime("%H:%M")
            son_cikis = t2.strftime("%H:%M")
            ofis_dk = (t2 - t1).total_seconds() / 60
            
            # Mola Bulma
            self.logs['prev_time'] = self.logs['timestamp'].shift(1)
            self.logs['prev_type'] = self.logs['type'].shift(1)
            molalar = self.logs[(self.logs['type'] == 'entry') & (self.logs['prev_type'] == 'exit')]
            if not molalar.empty:
                mola_dk = (molalar['timestamp'] - molalar['prev_time']).dt.total_seconds().sum() / 60

        net_calisma_dk = max(0, ofis_dk - mola_dk)
        
        # 2. İŞ (TASK) PUANLAMA
        task_puani = 0
        is_listesi = []
        puan_katalogu = {"easy": 15, "medium": 35, "hard": 70, "veryHard": 100}
        
        if not self.tasks.empty:
            for _, row in self.tasks.iterrows():
                diff = row.get('difficulty', 'medium')
                desc = row.get('description', '') or row.get('title', 'İsimsiz')
                p = puan_katalogu.get(diff, 35)
                task_puani += p
                is_listesi.append(f"{desc} ({diff.upper()} - {p} XP)")

        # 3. GÜNLÜK SKOR VE YORUM
        # 600dk (10 saat) ofis süresi üst limit, 100 puan.
        zaman_skoru = min(100, (net_calisma_dk / 480) * 100) 
        
        # Final Skor: %70 İş + %30 Zaman
        gunluk_skor = (task_puani * 0.7) + (zaman_skoru * 0.3)
        
        # Akıllı Öneriler
        oneriler = []
        if net_calisma_dk > 300 and mola_dk < 15:
            oneriler.append("⚠️ Hiç mola vermeden çalıştınız, verim düşebilir.")
        if net_calisma_dk > 100 and task_puani == 0:
            oneriler.append("⚠️ Ofiste bulundunuz ancak sisteme tamamlanmış iş girilmedi.")
        if task_puani > 150:
            oneriler.append("🔥 Harika iş çıkardınız, takımı sırtlıyorsunuz!")

        # 4. GENEL KARİYER ANALİZİ
        genel_durum = self._genel_kariyer_analizi()

        return {
            "tarih": self.tarih,
            "personel": f"{self.user_data.get('firstName', '')} {self.user_data.get('lastName', '')}",
            "genel_kariyer_durumu": genel_durum,  # <--- YENİ EKLENEN KISIM
            "gunluk_ozet": {
                "giris_cikis": f"{ilk_giris} - {son_cikis}",
                "ofis_suresi": f"{int(ofis_dk)} dk",
                "mola_suresi": f"{int(mola_dk)} dk",
                "net_calisma": f"{int(net_calisma_dk)} dk"
            },
            "gunluk_isler": {
                "adet": len(self.tasks),
                "kazanilan_xp": task_puani,
                "detay": is_listesi
            },
            "sonuc": {
                "gunluk_performans_puani": round(gunluk_skor, 1),
                "yapay_zeka_onerisi": oneriler if oneriler else ["Dengeli bir gün."]
            }
        }