# 🧠 Yapay Zeka Destekli Personel Verimlilik ve Ofis Analiz Sistemi

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Firebase](https://img.shields.io/badge/Firebase-Realtime_DB-orange)
![Machine Learning](https://img.shields.io/badge/AI-Gradient_Boosting-yellow)
![Architecture](https://img.shields.io/badge/Architecture-Event_Driven-green)
![Status](https://img.shields.io/badge/Status-Active_Development-success)

Bu proje, çalışan performansını analiz etmek, görev sürelerini tahmin etmek ve davranışsal kümeleme (clustering) yöntemiyle ofis yerleşimini optimize etmek için geliştirilmiş **Uçtan Uca (End-to-End) bir Yapay Zeka Arka Uç (Backend)** sistemidir.

Standart veri analizinden farklı olarak; **Hibrit Makine Öğrenmesi**, **NLP (Doğal Dil İşleme)** ve **Gerçek Zamanlı Veri Akışını** birleştirerek yaşayan bir sistem sunar.

---

## 🏗️ Sistem Mimarisi ve Çalışma Mantığı

Sistem, **Event-Driven (Olay Güdümlü)** bir mimariye sahiptir. Geleneksel REST API yerine, **Firebase Realtime Database** üzerinden "Listener (Dinleyici)" yapısı kullanılarak milisaniyeler içinde tepki verir.

```mermaid
graph TD;
    A[Mobil Uygulama / İstemci] -->|1. İstek Gönderir| B(Firebase Realtime DB);
    B -->|2. Stream Tetiklenir| C[Python AI Listener];
    C -->|3. Veriyi İşler| D{Hibrit AI Motoru};
    D -->|4. Tahmin Üretir| C;
    C -->|5. Sonucu Yazar| B;
    B -->|6. Canlı Güncelleme| A;
    
    E[Zamanlanmış Görev] -->|Gün Sonu Analizi| F[Toplu İşlem Servisi];
    F -->|K-Means Kümeleme| B;