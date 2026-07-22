export const SEVERITY_TR: Record<string, string> = {
  critical: "Kritik",
  high: "Yüksek",
  medium: "Orta",
  low: "Düşük",
  info: "Bilgi",
};

export const STATUS_TR: Record<string, string> = {
  open: "Açık",
  resolved: "Giderildi",
  false_positive: "Yanlış alarm",
  accepted_risk: "Kabul edilen risk",
  inconclusive: "Belirsiz",
};

/** Bulgu iş akışı durumları (drawer). */
export const FINDING_WORKFLOW_STATUS_TR: Record<string, string> = {
  open: "Açık",
  inconclusive: "İnceleniyor",
  accepted_risk: "Kabul Edilen Risk",
  false_positive: "Yanlış Alarm",
  resolved: "Çözüldü",
};

export const VERIFICATION_STATUS_TR: Record<string, string> = {
  verified: "Doğrulandı",
  unverified: "Doğrulanmadı",
  inconclusive: "Belirsiz",
  correlated: "Korele edildi",
};

export const CONFIDENCE_TR: Record<string, string> = {
  high: "Yüksek",
  medium: "Orta",
  low: "Düşük",
};

export const AI_CONFIDENCE_TR: Record<string, string> = {
  verified: "Doğrulanmış (AI)",
  unverified: "Doğrulanmamış (AI)",
  likely_false_positive: "Muhtemel yanlış alarm (AI)",
};

export const SCAN_STATUS_TR: Record<string, string> = {
  queued: "Kuyrukta",
  validating: "Doğrulanıyor",
  running: "Taranıyor",
  parsing: "Analiz ediliyor",
  completed: "Tamamlandı",
  failed: "Başarısız",
  cancelled: "İptal",
};

export const HISTORY_EVENT_TR: Record<string, string> = {
  detected: "İlk tespit",
  redetected: "Tekrar tespit",
  reopened: "Yeniden açıldı",
  status_change: "Durum değişti",
  retest_started: "Yeniden tarama",
};

export const SCAN_PROFILE_TR: Record<string, { label: string; description: string }> = {
  safe: {
    label: "Güvenli Tarama",
    description: "Pasif HTTP/TLS kontrolleri — siteye zarar vermez.",
  },
  deep: {
    label: "Derin Tarama",
    description: "Genişletilmiş pasif analiz, yüzey taraması ve yapılandırma kontrolleri.",
  },
  code: {
    label: "Kod / Dosya Taraması",
    description: "Hassas dosya sızıntısı ve kaynak kodu ipuçları (pasif, güvenli).",
  },
};

export function scanProfileLabel(name: string, fallback?: string): string {
  return SCAN_PROFILE_TR[name]?.label ?? fallback ?? name;
}

export function scanProfileDescription(name: string, fallback?: string): string {
  return SCAN_PROFILE_TR[name]?.description ?? fallback ?? "";
}

export function severityLabel(severity: string): string {
  return SEVERITY_TR[severity] ?? severity;
}

export function confidenceLabel(confidence: string | null | undefined): string {
  if (!confidence) return "—";
  return CONFIDENCE_TR[confidence] ?? confidence;
}

export function aiConfidenceLabel(label: string | null | undefined): string {
  if (!label) return "—";
  return AI_CONFIDENCE_TR[label] ?? label;
}

export function scanRiskSummary(counts: Record<string, number>): string {
  if ((counts.critical ?? 0) > 0 || (counts.high ?? 0) > 0) {
    return "Yüksek öncelikli bulgular var — en kısa sürede inceleyin.";
  }
  if ((counts.medium ?? 0) > 0) {
    return "Orta seviye iyileştirmeler önerilir; site çalışmaya devam eder.";
  }
  if ((counts.low ?? 0) + (counts.info ?? 0) > 0) {
    return "Kritik sorun yok; küçük iyileştirmeler yapılabilir.";
  }
  return "Önemli bir sorun tespit edilmedi.";
}
