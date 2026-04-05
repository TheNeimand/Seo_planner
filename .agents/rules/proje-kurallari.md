# SEO Planner - Proje Kuralları

## 📋 Proje Genel Bilgiler
- **Proje Adı:** SEO Planner
- **Dil:** Python 3.11+
- **Hedef Site:** altinorankimya.com
- **GSC Anahtarı:** `gen-lang-client-0512982673-96b59e3de05c.json`
- **Service Account:** `python-keywords-tool@gen-lang-client-0512982673.iam.gserviceaccount.com`

---

## 🏗️ Mimari Kurallar

### Dizin Yapısı
```
Seo Planner/
├── .agents/                   # AI asistan kuralları
│   ├── rules/
│   └── workflows/
├── src/                       # Ana kaynak kodları
│   ├── __init__.py
│   ├── main.py               # Uygulama giriş noktası
│   ├── config.py             # Yapılandırma / sabitler
│   ├── gsc/                  # Google Search Console modülü
│   │   ├── __init__.py
│   │   ├── auth.py           # GSC kimlik doğrulama
│   │   ├── client.py         # GSC API istemcisi
│   │   └── models.py         # Veri modelleri
│   ├── crawler/              # Site tarayıcı modülü
│   │   ├── __init__.py
│   │   ├── spider.py         # İç link tarayıcı
│   │   └── parser.py         # HTML parser
│   ├── analysis/             # Analiz modülü
│   │   ├── __init__.py
│   │   ├── link_graph.py     # Link graf analizi
│   │   └── keyword_mapper.py # Anahtar kelime eşleştirme
│   └── ui/                   # Kullanıcı arayüzü modülü
│       ├── __init__.py
│       ├── app.py            # Ana uygulama penceresi
│       ├── components/       # UI bileşenleri
│       │   ├── __init__.py
│       │   ├── graph_view.py # İnteraktif graf görünümü
│       │   ├── sidebar.py    # Yan panel (ayrıntılar)
│       │   ├── toolbar.py    # Üst araç çubuğu
│       │   └── dialogs.py    # Pop-up pencereler
│       ├── styles/           # CSS/QSS stil dosyaları
│       │   └── theme.qss
│       └── assets/           # İkonlar, görseller
├── data/                     # Önbellek ve veri dosyaları
├── requirements.txt          # Python bağımlılıkları
├── README.md
└── gen-lang-client-*.json    # GSC Service Account anahtarı
```

### Modüler Tasarım Prensipleri
1. **Separation of Concerns (SoC):** Her modül tek bir sorumluluğa sahip olmalıdır.
2. **Loose Coupling:** Modüller arasında gevşek bağlantı kullanılmalıdır.
3. **Dependency Injection:** GSC client ve crawler gibi servisler inject edilmelidir.
4. **Type Hints:** Tüm fonksiyonlarda Python type hint kullanılmalıdır.
5. **Docstrings:** Tüm public fonksiyonlar ve sınıflar docstring içermelidir.

---

## 🎨 UI/UX Kuralları

### GUI Framework
- **Ana Framework:** PySide6 (Qt6 for Python)
- PySide6 kullanılmasının sebebi: LGPL lisansı, profesyonel görünüm, zengin widget seti

### Tema ve Renkler
- **Tema Modu:** Dark Mode (ana tema)
- **Ana Renk Paleti:**
  - Arka Plan: `#0D1117` (koyu lacivert-siyah)
  - Kart/Panel Arka Plan: `#161B22`
  - Kenarlık: `#30363D`
  - Birincil Accent: `#58A6FF` (mavi)
  - İkincil Accent: `#3FB950` (yeşil)
  - Uyarı: `#F0883E` (turuncu)
  - Hata: `#F85149` (kırmızı)
  - Metin Birincil: `#C9D1D9`
  - Metin İkincil: `#8B949E`

### Graf Görünümü Renkleri
- **Ana Sayfa (Homepage) Node:** `#F0883E` (turuncu, büyük)
- **Kategori Sayfası Node:** `#58A6FF` (mavi, orta)
- **Ürün Sayfası Node:** `#3FB950` (yeşil, küçük)
- **Blog Sayfası Node:** `#BC8CFF` (mor, küçük)
- **Link Edge:** `#30363D` → hover'da `#58A6FF`
- **Seçili Node:** Parlak halka efekti (`glow`)

### UI Tasarım Prensipleri
1. Tüm paneller **yumuşak köşelere** (border-radius) sahip olmalıdır.
2. **Hover efektleri** ve **geçiş animasyonları** (150-300ms) kullanılmalıdır.
3. Sidebar sayfaya tıklandığında **slide-in animasyonu** ile açılmalıdır.
4. Graf üzerinde **zoom**, **pan**, **drag** işlemleri desteklenmelidir.
5. **Loading state** göstergeleri (spinner, skeleton) kullanılmalıdır.
6. **Responsif** pencere boyutu desteği sağlanmalıdır.

---

## 🔧 Teknik Kurallar

### Bağımlılıklar
```
PySide6>=6.6                    # GUI framework
google-api-python-client>=2.0  # GSC API
google-auth>=2.0               # Kimlik doğrulama
requests>=2.28                 # HTTP istekleri  
beautifulsoup4>=4.12           # HTML parsing
networkx>=3.0                  # Graf algoritmaları
pandas>=2.0                    # Veri işleme
lxml>=4.9                      # Hızlı HTML parser
```

### GSC API Kuralları
1. **Rate Limiting:** API çağrıları arasında en az 100ms bekleme süresi bırakılmalıdır.
2. **Önbellek:** GSC verileri yerel olarak `data/` dizinine JSON formatında önbelleğe alınmalıdır.
3. **Tarih Aralığı:** Varsayılan olarak son 28 gün verisi çekilmelidir.
4. **Sayfalama:** API sonuçlarında startRow ile sayfalama yapılmalıdır.
5. **Hata Yönetimi:** API hataları kullanıcıya anlaşılır mesajlarla gösterilmelidir.

### Crawler Kuralları
1. **Concurrent Crawling:** Crawler `ThreadPoolExecutor` ile birden fazla spider çalıştırır.
2. **Spider Sayısı:** Varsayılan 5, ayarlar panelinden (⚙) 1-20 arası değiştirilebilir.
3. **Politeness:** Her batch arasında varsayılan 0.3 saniye gecikme (ayarlanabilir).
4. **Thread Safety:** `threading.Lock` ile pages/edges yazma işlemleri korunmalıdır.
5. **Scope:** Sadece hedef domain içindeki linkler takip edilmelidir.
6. **Depth Limit:** Crawl derinliği varsayılan olarak 5 ile sınırlı olmalıdır (ayarlanabilir).
7. **Timeout:** Her istek için 10 saniye timeout olmalıdır.
8. **User-Agent:** Özel bir user-agent string'i kullanılmalıdır: `SeoPlanner/1.0`

### Ayarlar Sistemi Kuralları
1. Kullanıcı ayarları `data/settings.json` dosyasında kalıcı olarak saklanmalıdır.
2. Ayarlar paneli toolbar'da **⚙ ikonu** ile açılmalıdır (dışa aktar butonunun yanında).
3. `load_settings()` / `save_settings()` fonksiyonları ile okunup yazılmalıdır.
4. Yeni ayarlar eklenirken `_DEFAULT_SETTINGS` dict'ine varsayılan değer eklenmelidir.
5. Mevcut ayarlar:
   - `crawl_workers`: Spider sayısı (1-20, varsayılan: 5)
   - `crawl_delay`: İstek gecikmesi (0.0-5.0s, varsayılan: 0.3)
   - `crawl_max_depth`: Maksimum derinlik (1-20, varsayılan: 5)
   - `crawl_max_pages`: Maksimum sayfa (10-5000, varsayılan: 500)

### Link Analizi Kuralları
1. İç linkler (internal links) ve dış linkler (external links) ayrı takip edilmelidir.
2. Link'lerin **anchor text'leri** kaydedilmelidir.
3. **Kırık linkler** (404) işaretlenmelidir.
4. Her node'un **in-degree** ve **out-degree** değerleri hesaplanmalıdır.

---

## 📊 Veri Modelleri

### Page (Sayfa)
```python
@dataclass
class Page:
    url: str
    title: str
    page_type: str          # homepage, category, product, blog, other
    status_code: int
    internal_links_out: list[str]
    internal_links_in: list[str]
    external_links: list[str]
    gsc_keywords: list[KeywordData]
    total_clicks: int
    total_impressions: int
    avg_position: float
    avg_ctr: float
```

### KeywordData (Anahtar Kelime)
```python
@dataclass
class KeywordData:
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float
```

### LinkEdge (Link Bağlantısı)
```python
@dataclass
class LinkEdge:
    source_url: str
    target_url: str
    anchor_text: str
    is_internal: bool
    shared_keywords: list[str]  # ortak anahtar kelimeler
```

---

## 🚀 Geliştirme Kuralları

### Kod Stili
1. **PEP 8** kodlama standartlarına uyulmalıdır.
2. Dosya isimleri **snake_case** kullanılmalıdır.
3. Sınıf isimleri **PascalCase** kullanılmalıdır.
4. Değişken ve fonksiyon isimleri **snake_case** kullanılmalıdır.
5. Sabitler **UPPER_SNAKE_CASE** kullanılmalıdır.

### Hata Yönetimi
1. Tüm dış API çağrıları `try/except` bloğunda olmalıdır.
2. Hatalar `logging` modülü ile loglanmalıdır.
3. Kullanıcıya gösterilecek hatalar Türkçe olmalıdır.

### Thread Yönetimi
1. GSC API çağrıları ve crawling işlemleri **arka plan thread'lerinde** çalışmalıdır.
2. UI thread'i hiçbir zaman bloklanmamalıdır.
3. `QThread` veya `QRunnable` kullanılmalıdır.
4. İlerleme durumu ana thread'e `Signal` ile bildirilmelidir.

### Test
1. Her modül için temel birim testleri yazılmalıdır.
2. API mock'ları kullanılarak testler bağımsız çalışabilmelidir.

---

## 📝 Dil ve Arayüz
- Uygulama arayüzü **Türkçe** olmalıdır.
- Kod içi yorumlar ve docstring'ler **İngilizce** olmalıdır.
- Log mesajları **İngilizce** olmalıdır.
- Kullanıcıya gösterilen mesajlar **Türkçe** olmalıdır.
