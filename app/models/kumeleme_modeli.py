import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

class DavranisKumeleme:
    def __init__(self, all_users_data):
        self.all_data = all_users_data

    def analiz_et(self):
        user_stats = []

        # Her kullanıcının özet verisini çıkar
        for uid, u_val in self.all_data.items():
            tasks = u_val.get('tasks', {})
            attendance = u_val.get('attendance', {})
            
            # Toplam tamamlanan task
            completed_tasks = len([t for t in tasks.values() if t.get('status') == 'done'])
            
            # Toplam hareket (Kapı geçiş sayısı)
            total_movement = 0
            for date_val in attendance.values():
                recs = date_val.get('records', {})
                total_movement += len(recs)

            # Sadece verisi olanları al
            if total_movement > 0 or completed_tasks > 0:
                user_stats.append({
                    'user_id': uid,
                    'name': f"{u_val.get('firstName', 'User')} {u_val.get('lastName', '')}",
                    'total_movement': total_movement,
                    'completed_tasks': completed_tasks
                })

        # Kümeleme için en az 2 kişi lazım
        if len(user_stats) < 2:
            return [{"mesaj": "Analiz için yeterli çalışan verisi yok (min 2 kişi)."}]

        df = pd.DataFrame(user_stats)

        # Normalize et (Çünkü task sayısı 5, hareket 100 olabilir. Ölçek farkını yok et.)
        scaler = StandardScaler()
        features = df[['total_movement', 'completed_tasks']]
        scaled_features = scaler.fit_transform(features)

        # K-Means
        kmeans = KMeans(n_clusters=2, random_state=42)
        df['cluster'] = kmeans.fit_predict(scaled_features)

        # Kümeleri Yorumla
        centers = kmeans.cluster_centers_
        # centers[0] -> 0. kümenin [hareket, task] ortalaması
        
        cluster_map = {}
        # Hareketi daha yüksek olan kümeyi bul
        if centers[0][0] > centers[1][0]:
            cluster_map[0] = "Hareketli / Saha Personeli (Kapıya Yakın)"
            cluster_map[1] = "Odaklanmış / Teknik Personel (Sessiz Alan)"
        else:
            cluster_map[0] = "Odaklanmış / Teknik Personel (Sessiz Alan)"
            cluster_map[1] = "Hareketli / Saha Personeli (Kapıya Yakın)"

        df['suggestion'] = df['cluster'].map(cluster_map)

        return df[['name', 'total_movement', 'completed_tasks', 'suggestion']].to_dict(orient='records')