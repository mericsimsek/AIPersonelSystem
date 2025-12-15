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

# --- 2. HEDEF KULLANICI LİSTESİ (TAM LİSTE) ---
hedef_uidler = [
    '05487a04-ce6c-4023-a1ba-073b63ec0593', '06b82477-df20-493f-9be1-ba1b4bb4d7d4', 
    '076c750a-67fa-4780-82b6-6a106c9e4bf3', '0836e159-3ca1-47e8-a44f-9159aebf3783', 
    '117ee3b4-95ce-4f69-bc44-09d9428c12b0', '131248df-447c-46fa-a9d1-315b2c258d3e', 
    '13f71624-cb77-40fb-80cd-5f92a788df1b', '1776622d-4cf0-4066-99b2-1c1acc5178f2', 
    '17c86c99-873a-42f3-9c97-9ddbbc52468d', '1feba73c-889e-4d0c-bce4-9ffbe1568b95', 
    '2045af44-599f-4b42-ae0a-df506887b529', '2710f5b5-ac70-435c-bf3e-077a599e4e7a', 
    '284c3db6-1762-46be-a614-9a8cd2e9d5cd', '2860f14c-1d90-42cf-8956-0306c765572c', 
    '2b08e859-2e51-4b45-b555-e5c785179719', '2c2b7434-c736-439e-8cf7-0130323c55d7', 
    '2ccf740b-6775-41c9-8e64-02b013a48acd', '365d97fa-b03d-46cf-b1fe-3cd4abda4274', 
    '3736e4d2-6b50-41b9-a7d9-03d78f6626a7', '37a97846-7715-4b0c-a58e-bebcd64c7845', 
    '383553ad-6e98-45ba-8434-ec8eee99c31d', '3a672d5f-3436-4022-b273-f2c3510d4f67', 
    '3bf67610-ce85-4644-90c1-48d1b34a7b79', '3e2011a6-b08e-4cb4-a93f-347bd5ec7555', 
    '3f0922ee-819d-4dbe-acb9-dbdffe19de3c', '3f8979cc-e256-49ea-8e4b-d07059466d4e', 
    '41644c02-d12b-422f-93d6-9f65a218053d', '4178a139-ddf7-4064-a721-098e704568d6', 
    '434f64b1-03d3-4a95-908f-7b202cf5ed86', '44400b08-9255-41b0-987f-579397bb288f', 
    '47adb981-b9c3-4971-be7a-db172a7f1689', '4a68d93c-f691-43b8-84ef-a228fadecbed', 
    '562ea4a0-77e4-40e6-b174-0592ffe2d76d', '56efaade-fdbf-461b-bce8-73cb55cfa589', 
    '588d8de1-7e29-4d34-bb3f-6e3c57f327fc', '590b28bc-df04-403a-b582-3c862fde1d83', 
    '61c2da8f-4a00-4cff-95f9-f5fb0aa9f301', '6a322408-7525-4326-9dff-3f3e712510d4', 
    '6c362959-c7de-4bb7-9d40-749a692b8e99', '6e33c8df-1c3e-4c1e-be54-d9284da95690', 
    '702e4726-212e-4d2e-b85f-72bcb56fb46b', '70a7c3f5-e6bb-4d53-8e1a-3fe910d775a5', 
    '70c19f3c-5896-4e12-8a7f-b6d292cec0ad', '710dbfa1-e5a9-4a4c-bcfc-e9a383335732', 
    '73d3f95a-f1ea-48d1-b792-95bdc75e3f9f', '7e1adeca-b13b-4da7-9bf2-620abf747831', 
    '7f38628b-6c74-41c5-bc4e-33e5b20479bc', '841ae735-d94e-4b59-a566-0f4835d8a5de', 
    '880af5ea-bfbf-4ece-be71-f1cb7c6befc1', '8898ba1f-9c00-4e94-bc3d-2e45a9c765b2', 
    '89d6caff-798d-48d5-81c2-6e7c5f1ba9b1', '8a2b2e21-93a7-4043-8203-1dbbc6ad5bca', 
    '8d69e1d0-0cbf-4609-805e-1f49463a1092', '8fbef6bc-3b91-49ed-8e89-af8eda3e602d', 
    '9236e981-88a4-4a83-8500-0f2107162a42', '94e7caec-f33f-412b-8f90-0158e912f286', 
    '95cc3244-9c57-4b32-8943-306e3b2c4494', '993816ca-bb44-420a-9420-646c362a9ce7', 
    '9cbbb174-4d3d-4a40-8eb1-eb6248b6050f', '9d7314d6-f7eb-4561-9087-215fd2c82fb0', 
    '9e143bbe-3a25-4322-b751-5a6601fb3a56', '9ed3113c-764a-4542-bfbf-35eed429d1c4', 
    'OTHweQmXq6Nx9yy7LVbNQUJlk072', 'RHdo0pq2aYWxVEvXEsbyUW4R66W2', 
    'ZepsubScQURJVqDBIzOti469KEG2', 'a3da1851-372d-4f29-9e8e-84e2bea95809', 
    'a47d7f2f-cb1f-4216-9f3a-b0479103fc95', 'a7198000-ecf9-4f17-8192-f4645931846a', 
    'a9594c8c-1641-4e6c-b253-11be05330ebb', 'ad87c9fb-98a3-4229-850b-be3645d6c999', 
    'b2bf1cd9-0dec-45ff-be80-113866d160a5', 'b42d54e7-baa1-4825-bc2a-bf79b1d3b763', 
    'b5356206-074e-4a3f-9701-2ae41f355bc4', 'b58c840f-fd5c-4d61-b125-585c4a49507d', 
    'b5953bf8-7654-43d9-a948-601bbed449cb', 'be83e346-a3fd-4231-9136-9d101b9967e2', 
    'bf398ed9-8294-4261-98ec-515644bf7f9e', 'bf526e77-1fe4-4f90-9f76-33adc532cbcd', 
    'bf708ca3-0bb6-4cb7-b644-6eab5d73d7e7', 'c502a88e-6dda-4f21-83a3-b4d00b74fdcd', 
    'c5962c43-b832-4cdc-b422-39341a41bacc', 'cd07cd6f-e0c5-4676-a3f4-b74cb58a44fe', 
    'ce43e984-0f5f-42ee-bb2e-ae5cbad0621c', 'cfad9cb2-54db-49f5-93ea-1e9202d38ce8', 
    'd36d9644-ec63-41b5-9705-51ba54534778', 'd508c82f-67b2-470c-84fa-95799074a242', 
    'd75dc194-a370-47d4-8127-90a7780fbc1e', 'd7c22101-b7b2-4a19-baaa-79a9068eea00', 
    'd811f249-a703-4ae3-96d4-cbbddd6cd2e2', 'd878f597-a969-4c70-950f-046d363cfcac', 
    'da5c64e4-58ba-4b82-b040-d2296c99df83', 'dc66c2ba-acb9-435b-a0c1-630e297e8710', 
    'e1403196-a077-4eb7-b39d-124907bbda91', 'e9322ee8-9293-41e6-ade4-6c19ef0dbf50', 
    'ea196f78-993a-44f1-8511-a57a9b9534c8', 'ef823347-f480-4d83-94c3-c35cfb34e0af', 
    'f16e5a38-6930-4145-9471-d12585c37492', 'f263c2a7-7fb4-452d-b744-a10c12c6894f', 
    'f5ca4452-b936-40c8-927b-82d57b09cb4c', 'f9a0b4ab-5c50-47d9-9098-6225f58bc328', 
    'fcd1403d-8c7f-4f3f-8900-fd39239c2dd5', 'ffe641aa-11db-4635-84a0-d75bb839b2d9', 
    'fff6f123-f3e4-49f6-bae1-8cdbb0a5c0de', 'oHl4aOGXUWTOLabvbaO5mm5TNYD3'
]

# --- 3. SENARYOLAR (Rastgele dağıtılacak) ---
senaryolar = [
    {"desc": "Login sayfasındaki CSS buton kaymasını düzelt", "diff": "easy"},
    {"desc": "Yapay zeka modelini eğit ve sunucuya deploy et", "diff": "veryHard"},
    {"desc": "SQL veritabanı optimizasyonu ve indexleme", "diff": "hard"},
    {"desc": "Müşteri listesi API endpoint'ini güncelle", "diff": "medium"},
    {"desc": "Docker konteynerlerini yapılandır", "diff": "hard"},
    {"desc": "Anasayfa banner görselini değiştir", "diff": "easy"},
    {"desc": "Kullanıcı yetkilendirme (Auth) servisini yeniden yaz", "diff": "hard"},
    {"desc": "Mobil uygulama için yeni ikon tasarımı", "diff": "medium"},
    {"desc": "Haftalık raporlama modülündeki bug'ı fixle", "diff": "easy"},
    {"desc": "Büyük veri analizi için pipeline kur", "diff": "veryHard"}
]

def toplu_istek_gonder():
    print(f"🚀 Toplam {len(hedef_uidler)} kullanıcıya rastgele görev atanıyor...\n")
    
    # Listenin çok büyük olduğu durumlarda kilitlenmemesi için
    # 0.1 saniye aralıklarla istek atıyoruz.
    
    for i, uid in enumerate(hedef_uidler, 1):
        # Rastgele bir senaryo seç
        secilen_is = random.choice(senaryolar)
        
        istek_verisi = {
            "difficulty": secilen_is["diff"],
            "description": secilen_is["desc"],
            "status": "pending", # AI'yı tetikleyen anahtar
            "timestamp": {".sv": "timestamp"}
        }

        # Veritabanına Yaz
        path = f"users/{uid}/ai_interaction/predict_request"
        
        try:
            db.reference(path).set(istek_verisi)
            print(f"[{i}/{len(hedef_uidler)}] 📤 Gönderildi -> {uid[:5]}... | İş: {secilen_is['desc'][:20]}...")
        except Exception as e:
            print(f"❌ Hata ({uid}): {e}")
        
        # CPU'yu ve Network'ü rahatlatmak için minik bekleme
        time.sleep(0.1)

    print("\n✅ Tüm istekler gönderildi! 'ai_listener' terminaline bak! 👀")

if __name__ == "__main__":
    toplu_istek_gonder()