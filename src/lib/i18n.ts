export type Language = "en" | "vi";

export interface Translations {
  header: {
    appTitle: string;
    appSubtitle: string;
    modelBadge: string;
    langSwitch: string;
  };
  onboarding: {
    guideTitle: string;
    step1: string;
    step2: string;
    step3: string;
    dismiss: string;
  };
  hero: {
    badge: string;
    headline: string;
    realCases: string;
  };
  input: {
    tabImage: string;
    tabText: string;
    dropzoneTitle: string;
    dropzoneSubtitle: string;
    supportedFormats: string;
    changeImage: string;
    pastePlaceholder: string;
    btnAnalyze: string;
    analyzing: string;
    analyzingSubtitle: string;
  };
  verdict: {
    scamDetected: string;
    highRisk: string;
    suspicious: string;
    safe: string;
    riskScore: string;
    category: string;
    actionScam: string;
    actionHigh: string;
    actionSuspicious: string;
    actionSafe: string;
  };
  mlBadge: {
    badgeTitle: string;
    detectedAs: string;
    confidence: string;
    subtext: string;
    keySignals: string;
  };
  webIntel: {
    badgeTitle: string;
    fraudulentDomain: string;
    legitimateDomain: string;
    unverifiedMatch: string;
    targetBrand: string;
    unidentified: string;
    confidence: string;
    verifiedLive: string;
    unreachable: string;
    suspiciousBehaviors: string;
    threatEvidence: string;
    source: string;
  };
  tabs: {
    overview: string;
    psychology: string;
    family: string;
    roleplay: string;
  };
  overview: {
    executiveSummary: string;
    evidenceComparator: string;
    detectedInData: string;
    officialBenchmark: string;
    forensicAnalysis: string;
    emergencyActions: string;
  };
  psychology: {
    title: string;
    targetEmotion: string;
  };
  family: {
    title: string;
    keyWarning: string;
    copied: string;
    copyBtn: string;
    downloadPdf: string;
    printReport: string;
  };
  roleplay: {
    title: string;
    subtitle: string;
    placeholder: string;
    send: string;
    quickChoiceDanger: string;
    quickChoiceSafe: string;
    resetChat: string;
  };
  community: {
    title: string;
    subtitle: string;
    searchPlaceholder: string;
    allTags: string;
    views: string;
  };
}

export const translations: Record<Language, Translations> = {
  en: {
    header: {
      appTitle: "ScamShield Forensic AI",
      appSubtitle: "Digital Forensic Investigation & Multimodal Cognitive Deception Defense",
      modelBadge: "Gemini 2.5 Flash + Hybrid ML",
      langSwitch: "English",
    },
    onboarding: {
      guideTitle: "3-Step Quick Guide — Accessible to Everyone",
      step1: "Screenshot suspicious SMS/chat or paste suspicious URLs / text",
      step2: "Click Start Forensic Analysis — AI evaluates in ~10 seconds",
      step3: "Review the report → Share emergency alert with friends and family",
      dismiss: "Dismiss guide",
    },
    hero: {
      badge: "AI Riser Vietnam 2026",
      headline: "Forensic Scam Detection & Cognitive Deception Analysis",
      realCases: "Real-world Forensic Cases:",
    },
    input: {
      tabImage: "Image Scan",
      tabText: "Text / URL Scan",
      dropzoneTitle: "Drag & Drop Evidence Image Here",
      dropzoneSubtitle: "or click to browse from device (Screenshots of SMS, Bank transfer, Telegram, WhatsApp)",
      supportedFormats: "Supports PNG, JPG, WEBP (Max 10MB)",
      changeImage: "Change Image",
      pastePlaceholder: "Paste suspicious message, SMS, email, or suspicious link (e.g., https://...)...",
      btnAnalyze: "Start Forensic Investigation",
      analyzing: "Running Multimodal Forensic Analysis...",
      analyzingSubtitle: "Examining URL intelligence, linguistic threats, and psychological coercion...",
    },
    verdict: {
      scamDetected: "SCAM DETECTED",
      highRisk: "HIGH RISK",
      suspicious: "SUSPICIOUS",
      safe: "SAFE",
      riskScore: "Risk Score",
      category: "Category",
      actionScam: "Stop immediately — do not click, call back, or transfer anything.",
      actionHigh: "Do not interact — block the sender and verify via official channels.",
      actionSuspicious: "Proceed with caution — verify the source before taking any action.",
      actionSafe: "No significant threats detected — safe to continue.",
    },
    mlBadge: {
      badgeTitle: "ML PRE-CLASSIFIER",
      detectedAs: "Detected as",
      confidence: "confidence",
      subtext: "Ultra-fast local model (TF-IDF + Gradient Boosting)",
      keySignals: "Key signals:",
    },
    webIntel: {
      badgeTitle: "WEB INTELLIGENCE",
      fraudulentDomain: "🚨 Fraudulent Domain (MISMATCH)",
      legitimateDomain: "✅ Legitimate Domain (MATCH)",
      unverifiedMatch: "⚠️ Unverified Match (UNKNOWN)",
      targetBrand: "Claimed Brand / Impersonation Target:",
      unidentified: "Unidentified",
      confidence: "Web Verification Confidence:",
      verifiedLive: "✓ Verified Live HTTP",
      unreachable: "⚠ URL unreachable during live probe",
      suspiciousBehaviors: "Suspicious Web Behaviors:",
      threatEvidence: "Threat Intelligence & Official Sources:",
      source: "Source",
    },
    tabs: {
      overview: "Forensic Evidence",
      psychology: "Cognitive Deception",
      family: "Family Alert Card",
      roleplay: "🎯 Roleplay Reflex Lab",
    },
    overview: {
      executiveSummary: "Executive Forensic Summary:",
      evidenceComparator: "Ground-Truth Evidence Comparator:",
      detectedInData: "[Detected in Data]",
      officialBenchmark: "[Official Benchmark]",
      forensicAnalysis: "Forensic Analysis:",
      emergencyActions: "60-Second Emergency Actions:",
    },
    psychology: {
      title: "Psychological Exploitation Tactics:",
      targetEmotion: "Target Emotion:",
    },
    family: {
      title: "Quick Family Emergency Dispatch (Messaging/Telegram):",
      keyWarning: "⚠️ Warning for Loved Ones:",
      copied: "Copied to clipboard!",
      copyBtn: "Copy Message",
      downloadPdf: "Download PDF",
      printReport: "Print Report",
    },
    roleplay: {
      title: "Interactive Scam Reflex Simulation",
      subtitle: "Practice dealing with the scammer in a safe sandbox to build natural defense reflexes",
      placeholder: "Type your response to the scammer...",
      send: "Send",
      quickChoiceDanger: "Give requested info",
      quickChoiceSafe: "Ask for official verification",
      resetChat: "Reset Simulation",
    },
    community: {
      title: "Community Defense Feed",
      subtitle: "Real-time anonymous forensic alerts submitted across the network",
      searchPlaceholder: "Search cases by brand, threat type, or domain...",
      allTags: "All Cases",
      views: "views",
    },
  },
  vi: {
    header: {
      appTitle: "ScamShield Forensic AI",
      appSubtitle: "Giám định Kỹ thuật số & Phòng thủ Nhận thức Đa phương thức",
      modelBadge: "Gemini 2.5 Flash + Hybrid ML",
      langSwitch: "Tiếng Việt",
    },
    onboarding: {
      guideTitle: "Hướng dẫn nhanh 3 bước — Dành cho mọi người",
      step1: "Chụp ảnh màn hình tin nhắn SMS/chat hoặc dán đường link / nội dung đáng ngờ",
      step2: "Bấm Bắt đầu phân tích giám định — AI đánh giá trong khoảng 10 giây",
      step3: "Xem báo cáo cảnh báo → Chia sẻ cảnh báo khẩn cấp cho người thân và gia đình",
      dismiss: "Đóng hướng dẫn",
    },
    hero: {
      badge: "AI Riser Vietnam 2026",
      headline: "Phát hiện Lừa đảo Giám định & Phân tích Đánh lừa Tâm lý",
      realCases: "Các tình huống lừa đảo thực tế:",
    },
    input: {
      tabImage: "Quét bằng Ảnh",
      tabText: "Quét Văn bản / URL",
      dropzoneTitle: "Kéo & Thả ảnh bằng chứng vào đây",
      dropzoneSubtitle: "hoặc bấm để chọn ảnh từ máy (Ảnh chụp SMS, Giao dịch ngân hàng, Telegram, Zalo)",
      supportedFormats: "Hỗ trợ định dạng PNG, JPG, WEBP (Tối đa 10MB)",
      changeImage: "Đổi ảnh khác",
      pastePlaceholder: "Dán nội dung tin nhắn, SMS, email hoặc đường link nghi vấn (ví dụ: https://...)...",
      btnAnalyze: "Bắt đầu Giám định Kỹ thuật số",
      analyzing: "Đang tiến hành giám định đa phương thức...",
      analyzingSubtitle: "Đang kiểm tra an toàn tên miền, phân tích ngôn ngữ đe dọa và thao túng tâm lý...",
    },
    verdict: {
      scamDetected: "PHÁT HIỆN LỪA ĐẢO",
      highRisk: "NGUY CƠ CAO",
      suspicious: "KHẢ NGHI",
      safe: "AN TOÀN",
      riskScore: "Điểm rủi ro",
      category: "Phân loại",
      actionScam: "DỪNG LẠI NGAY LẬP TỨC — Tuyệt đối không bấm link, không nghe máy, không chuyển tiền.",
      actionHigh: "Không tương tác — Chặn người gửi và xác minh qua kênh chính thống.",
      actionSuspicious: "Cần thận trọng — Kiểm tra kỹ nguồn gửi trước khi thực hiện bất kỳ hành động nào.",
      actionSafe: "Không phát hiện mối nguy hại đáng kể — An toàn để tiếp tục.",
    },
    mlBadge: {
      badgeTitle: "MÔ HÌNH HỌC MÁY (ML PRE-CLASSIFIER)",
      detectedAs: "Phân loại",
      confidence: "độ tin cậy",
      subtext: "Mô hình siêu tốc chạy cục bộ (TF-IDF + Gradient Boosting)",
      keySignals: "Dấu hiệu phát hiện:",
    },
    webIntel: {
      badgeTitle: "TÌNH BÁO WEB & TÊN MIỀN",
      fraudulentDomain: "🚨 Tên miền Giả mạo (MISMATCH)",
      legitimateDomain: "✅ Tên miền Chính thống (MATCH)",
      unverifiedMatch: "⚠️ Chưa thể xác thực (UNKNOWN)",
      targetBrand: "Thương hiệu bị mạo danh:",
      unidentified: "Chưa xác định",
      confidence: "Độ tin cậy xác thực Web:",
      verifiedLive: "✓ Đã xác minh hoạt động HTTP",
      unreachable: "⚠ Đường link không thể kết nối khi kiểm tra trực tiếp",
      suspiciousBehaviors: "Hành vi Web đáng ngờ:",
      threatEvidence: "Bằng chứng & Nguồn chính thống:",
      source: "Nguồn",
    },
    tabs: {
      overview: "Bằng chứng Giám định",
      psychology: "Thao túng Tâm lý",
      family: "Thẻ Cảnh báo Gia đình",
      roleplay: "🎯 Phòng Luyện tập Phản xạ",
    },
    overview: {
      executiveSummary: "Tóm tắt Giám định:",
      evidenceComparator: "So sánh Bằng chứng với Sự thật Chính thống:",
      detectedInData: "[Dữ liệu Phát hiện]",
      officialBenchmark: "[Quy chuẩn Chính thống]",
      forensicAnalysis: "Phân tích Giám định:",
      emergencyActions: "Hành động Khẩn cấp trong 60 giây:",
    },
    psychology: {
      title: "Chiêu thức Thao túng Tâm lý:",
      targetEmotion: "Cảm xúc bị nhắm tới:",
    },
    family: {
      title: "Gửi Cảnh báo Khẩn cấp cho Người thân (Zalo/Telegram/SMS):",
      keyWarning: "⚠️ Lời cảnh báo dành cho người thân:",
      copied: "Đã sao chép vào bộ nhớ tạm!",
      copyBtn: "Sao chép Tin nhắn",
      downloadPdf: "Tải báo cáo PDF",
      printReport: "In Báo cáo",
    },
    roleplay: {
      title: "Mô phỏng Phản xạ Đối kháng với Kẻ lừa đảo",
      subtitle: "Thực hành đối thoại an toàn với kẻ lừa đảo trong môi trường hộp cát để rèn luyện phản xạ tự vệ",
      placeholder: "Nhập câu trả lời của bạn với kẻ lừa đảo...",
      send: "Gửi phản hồi",
      quickChoiceDanger: "Cung cấp thông tin theo yêu cầu",
      quickChoiceSafe: "Yêu cầu xác minh chính thống",
      resetChat: "Bắt đầu lại Mô phỏng",
    },
    community: {
      title: "Bản tin Cảnh báo Cộng đồng",
      subtitle: "Các vụ lừa đảo mới nhất được ẩn danh và chia sẻ trên toàn hệ thống",
      searchPlaceholder: "Tìm kiếm theo thương hiệu, thủ đoạn lừa đảo, tên miền...",
      allTags: "Tất cả tình huống",
      views: "lượt xem",
    },
  },
};
