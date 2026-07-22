# Müşteri kapsamı ve sınırlar

Bu belge, SIBER platformunun orta ölçekli müşteriler için sunduğu yetkili web ve Android APK statik analiz hizmetinin kapsamını, sınırlarını ve raporlama beklentilerini açıklar.

## Hizmet tanımı

SIBER, müşterinin **yetkilendirdiği** web varlıkları ve **sahiplik/onay belgeli** Android APK dosyaları üzerinde **statik ve pasif** güvenlik analizi yapar.

| Alan | Kapsam dahil | Kapsam dışı |
|------|--------------|-------------|
| Web | Yetkilendirilmiş domain taraması, pasif HTTP kontrolleri, Nuclei şablonları, exposed path tespiti | Aktif istismar, brute-force, DoS, sosyal mühendislik |
| Mobil (APK) | Manifest, izinler, dışa aktarılan bileşenler, gizli anahtar taraması, network security config | Dinamik analiz, cihaz/emülatör çalıştırma, runtime hook |
| Raporlama | JSON, HTML, PDF özet raporları | Penetrasyon testi sertifikası, uyumluluk garantisi |

## Web tarama sınırları

- Tarama yalnızca **doğrulanmış domainler** üzerinde çalışır (üretim ortamında zorunlu).
- Müşteri, tarama başlatmadan önce **yetkilendirme onayı** vermelidir.
- Hız limitleri ve eşzamanlı tarama kotası uygulanır; aşırı yük oluşturacak profiller kısıtlanabilir.
- Bulgular **olasılık** temelindedir; manuel doğrulama önerilir.

## Mobil APK sınırları

- Yalnızca **.apk** dosyaları kabul edilir (maks. 100 MB).
- Analiz **dosya içeriği** üzerinde yapılır; uygulama çalıştırılmaz.
- Kontroller: `debuggable`, `allowBackup`, cleartext traffic, exported components, tehlikeli izinler, secret pattern taraması, network security config.
- **False positive** olasılığı vardır (özellikle secret pattern eşleşmeleri).
- Aynı SHA-256 hash ile tekrar yüklemeler duplicate olarak işaretlenir.

## Rol ve erişim modeli

| Rol | Yetkiler |
|-----|----------|
| Owner | Organizasyon yönetimi, üye daveti, tüm tarama/mobil işlemleri |
| Admin | Proje, domain, tarama, mobil yükleme, bulgu yönetimi |
| Analyst | Tarama başlatma, bulgu inceleme, rapor indirme |
| Viewer | Salt okunur erişim; bulgu durumu değiştiremez |

Platform operatörü, müşteri organizasyonuna yalnızca **süreli support grant** ile viewer erişimi alabilir. Tüm grant işlemleri audit log'a yazılır.

## Rapor şablonu (mobil)

Mobil raporlar şu alanları içerir:

- Uygulama adı, paket adı, sürüm, SHA-256
- Güvenlik skoru (0–100) ve severity dağılımı
- MASVS kategori özeti
- Bulgu listesi: başlık, severity, bileşen, MASVS, açıklama, remediation
- Test kapsamı ve sınırlamalar bölümü

## Veri saklama

- APK dosyaları analiz tamamlandıktan sonra sunucudan silinir.
- Bulgular organizasyon kapsamında veritabanında saklanır.
- Audit log kayıtları değiştirilmez (immutable).

## Yasal ve operasyonel notlar

- Müşteri, analiz edilen varlıklar üzerinde **yasal yetkiye** sahip olduğunu onaylar.
- SIBER bir **güvenlik değerlendirme aracıdır**; nihai güvenlik garantisi vermez.
- Kritik bulgular için müşterinin kendi güvenlik ekibiyle doğrulama yapması önerilir.

## Destek erişimi (platform operatörü)

Support grant oluşturulurken:

- Hedef: yalnızca platform admin kullanıcıları
- Süre: 1–168 saat (varsayılan 24 saat)
- Erişim seviyesi: viewer (salt okunur)
- Gerekçe zorunlu (min. 10 karakter)
- İptal edilebilir; süresi dolunca otomatik sona erer

## Sürüm

- Belge sürümü: 1.0
- Son güncelleme: 2026-07-21
