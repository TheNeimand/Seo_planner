# 🚀 SEO Planner: Görsel Site Haritası ve GSC Analiz Aracı

SEO Planner, web sitenizin iç bağlantı (internal link) yapısını keşfetmek, analiz etmek ve Google Search Console (GSC) verileriyle SEO stratejinizi güçlendirmek için tasarlanmış modern bir masaüstü uygulamasıdır.

## ✨ Temel Özellikler

- **🕸 İnteraktif Bağlantı Grafları:** Sitenizin mimarisini kuşbakışı görün. Hangi sayfaların sitenizin "merkezinde" olduğunu, hangilerinin yetersiz link aldığını görselleştirin.
- **📊 GSC Entegrasyonu:** Tıklama, Gösterim, CTR ve Pozisyon verilerini doğrudan grafik üzerindeki düğümlerde inceleyin.
- **🔑 Anahtar Kelime Eşleştirme:** Her sayfa için en çok trafik getiren anahtar kelimeleri ve performans metriklerini listeleyin.
- **📁 Çoklu Proje Desteği:** Farklı siteleri, farklı JSON kimlik bilgileri ile bağımsız projeler olarak yönetin.
- **🌳 Akıllı Hiyerarşi (Smart Tree):** Link karmaşasını önleyen, sitenizin ana iskeletini ön plana çıkaran akıllı yerleşim algoritmaları.
- **🔍 İç Link Denetimi:** Gelen ve giden linkleri, anchor text (çapa metni) detaylarıyla birlikte tablo üzerinden takip edin.
- **💾 Veri Dışa Aktarma:** Analiz sonuçlarınızı JSON formatında kaydedin ve paylaşın.

## 🛠 Kurulum ve Çalıştırma

Uygulamayı kullanmak oldukça basittir:

1. Depoyu klonlayın veya indirin.
2. Ana dizindeki **`SEO Planner.bat`** dosyasını çalıştırın.
   - Bu dosya otomatik olarak Python kontrolü yapacak ve gerekli kütüphaneleri (`PySide6`, `google-api-client` vb.) yükleyecektir.

## 🔐 Google Search Console Bağlantısı

Uygulamayı tam kapasite kullanmak için:
- Bir Google Cloud Projesi üzerinden **Hizmet Hesabı (Service Account)** oluşturun.
- Search Console API'sini etkinleştirin.
- İndirdiğiniz JSON dosyasını uygulama içindeki **Ayarlar > Siteler** kısmından ekleyin.
- **ÖNEMLİ:** JSON içindeki e-posta adresini Search Console mülkünüze "Tam Yetki" ile kullanıcı olarak eklemeyi unutmayın.

## 🎨 Teknolojiler

- **Arayüz:** PySide6 (Qt for Python)
- **Grafik Motoru:** NetworkX ve QGraphicsView tabanlı özel görselleştirme
- **API:** Google Search Console API v1
- **Crawler:** BFS tabanlı multi-threaded özel spider
