# Profesyonel test öncesi özet (sizin için)

**Tarih:** 2026-09-14  
**Site:** https://siber.cloudnira.com  
**Son kod durumu:** Bu oturumda testler yeşil; production’a almak için deploy gerekir (aşağıda).

---

## 1. Kısa cevap: Test kullanıcısı anlayabilir mi?

**Evet, büyük ölçüde** — ama üç şart var:

1. **Operatör (siz)** test kullanıcısına doğru hazırlanmış hesap vermeli: `security_analyst` rolü, hazır **proje**, günlük **10 tarama** kotası, sadece **güvenli tarama** açık.
2. Uzman **kendi domainini** ekleyip DNS veya meta ile **doğrulamalı** (operatör SQL ile doğrulama yapmamalı; sadece acil durumda).
3. Destek e-postası production ayarında dolu olmalı (`SUPPORT_CONTACT_EMAIL`).

Bu oturumda arayüzde özellikle **kafa karıştıran yerler** düzeltildi (aşağıda).

---

## 2. Otomatik test sonuçları (bugün)

| Test | Sonuç |
|------|--------|
| Backend (266 test + ruff) | **Geçti** |
| Frontend (typecheck + 32 test + build) | **Geçti** |
| GitHub CI (son bilinen run #100) | **Başarılı** |

Yani kod tarafında bilinen kırık test **yok**.

---

## 3. Arayüzde ne düzelttik? (test kullanıcısı gözüyle)

| Sorun | Ne yaptık |
|-------|-----------|
| “Safe tarama” / İngilizce karışık metin | Türkçe: **“Güvenli tarama”**; Almanca: **“Sicheren Scan”** |
| Pilot hesabında “Proje oluştur” ama yetki yok | Analyst/viewer artık **proje formu görmüyor**; açıklama + **Projeyi aç** / **Domainlerime git** butonları |
| Kota bazen yanlış “5” görünüyordu | Artık **sunucudan gelen gerçek kota**; yoksa “yüklenemedi” mesajı, **UTC yenilenme** notu |
| Nereden devam edeceği belirsiz | **“Sıradaki adım”** şeridi + checklist’te her adım için **Tamamla →** linki |
| Domain adımı projesiz takılıyordu | Domain adımları **Domainler** sayfasına da yönlendiriyor |
| Expert checklist “Pilot kurulum” | Expert tenant’ta başlık: **“Başlangıç rehberi”** + kısa açıklama |

---

## 4. Test kullanıcısının izlemesi gereken yol (basit)

1. **Giriş** → https://siber.cloudnira.com/login  
2. **Organizasyon / Genel bakış** → “Başlangıç rehberi”ndeki adımları takip et  
3. **Domainler** → domain ekle → talimatları kopyala → DNS/meta ile **Doğrula**  
4. **Güvenli tarama** (Site tara / Taramalar) → doğrulanmış domain ile tarama başlat  
5. **Bulgular** → filtrele, detay, rapor indir, gerekirse geri bildirim / yeniden test  
6. **Ayarlar** → kota ve **destek** iletişimi  

Kapalı: derin tarama, kod taraması, kayıt ol sayfası (403).

---

## 5. Sizin (operatör) yapmanız gerekenler — profesyoneli çağırmadan önce

- [ ] RoE dosyasındaki tarih ve iletişim alanlarını doldurun (`docs/security/expert-test-rules-of-engagement.md`)
- [ ] Expert tenant oluşturun: rol **security_analyst**, **en az 1 proje**, quota **10**, sadece **safe**
- [ ] Kendi hesabınızla veya geçici test hesabıyla **yukarıdaki 6 adımı** bir kez uçtan uca deneyin
- [ ] Production’da son UX düzeltmelerini **deploy** edin (commit henüz sunucuda olmayabilir)
- [ ] Test bitince test hesabını **kapatın**, oturumları iptal edin

**Not:** `prepare_expert_test_tenant.py` scripti tek başına kullanıcı oluşturmaz; sadece plan yazar. Gerçek hesap platform/operatör işlemidir.

---

## 6. Hâlâ bilinçli olarak eksik olanlar (profesyonel bulabilir)

Bunlar çoğunlukla **güvenlik açığı değil**, **ürün olgunluğu**:

- PDF raporunun “kurumsal” kalitesi canlı onaylanmadı  
- Tam otomatik tarayıcı testi (Playwright) yok  
- Erişilebilirlik (ekran okuyucu, kontrast) tam denetlenmedi  
- Resmi UI raporu hâlâ `expert_ui_ready_with_blockers` seviyesinde tanımlı; bu oturum UX’i iyileştirdi ama **17 adımlık fotoğraflı walkthrough** arşivi yok  

Backend / tarama tarafı için daha önce **`expert_security_test_ready`** denmişti (benchmark kanıtı rc5 dönemi). UI değişiklikleri tarama motoruna dokunmadı.

---

## 7. Risk özeti (dürüst tablo)

| Konu | Durum |
|------|--------|
| Analyst başka tenant verisine erişir mi? | Testler ve tasarım: **hayır** (403/404) |
| Analyst admin onayı verir mi? | **Hayır** |
| Ham sunucu hatası kullanıcıya sızar mı? | Scan ekranında **temizlenmiş** mesaj |
| Test kullanıcısı projesiz kalır mı? | **Operatör proje vermezse evet** — UI artık bunu açıklıyor |
| CI sürekli kırık mail atar mı? | Son fix’ten sonra **atmamalı** |

---

## 8. Sonraki adım önerisi

1. Bu değişiklikleri **commit + production deploy**  
2. Bir **dry-run** test hesabı ile checklist’i siz tamamlayın  
3. Ardından profesyonel uzmana RoE + hesap verin  

**Karar (pratik):** Profesyonel **platform + müşteri akışı** testine **deploy sonrası dry-run ile** gönderilebilir. “Mükemmel ürün” beklentisi için PDF/a11y maddelerini ayrıca planlayın.
