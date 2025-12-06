from fastapi import FastAPI
from app.core.firebase_config import rtdb
from app.api.endpoints import router as api_router # <--- YENİ EKLEME

app = FastAPI(title="Proje AI Backend", version="1.0")

# Router'ı ana uygulamaya bağlıyoruz
app.include_router(api_router, prefix="/api") # <--- YENİ EKLEME

@app.get("/")
def read_root():
    if rtdb:
        durum = "Firebase Bağlı"
    else:
        durum = "Firebase Bağlantısı YOK"
        
    return {
        "mesaj": "AI Servisi Ayakta 🚀",
        "durum": durum
    }