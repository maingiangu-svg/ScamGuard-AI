export type Language = "vi" | "en";

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
    headlineSub: string;
    realCases: string;
    sampleHelper: string;
    scenarioDisclaimer: string;
  };
  input: {
    tabImage: string;
    tabText: string;
    dropzoneTitle: string;
    dropzoneSubtitle: string;
    dropzoneDragActive: string;
    supportedFormats: string;
    pasteHint: string;
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
    viewAnalysis: string;
  };
}

export const translations: Record<Language, Translations> = {
  vi: {
    header: {
      appTitle: "ScamShield",
      appSubtitle: "Kiểm tra dấu hiệu lừa đảo trong hình ảnh, tin nhắn và liên kết",
      modelBadge: "Gemini 2.5 Flash",
      langSwitch: "Tiếng Việt",
    },
    onboarding: {
      guideTitle: "3 bước kiểm tra nhanh",
      step1: "Tải ảnh chụp màn hình hoặc dán nội dung nghi vấn",
      step2: "Bấm kiểm tra để hệ thống phân tích dấu hiệu mạo danh",
      step3: "Xem kết quả và gửi ngay cảnh báo cho người thân",
      dismiss: "Đã hiểu",
    },
    hero: {
      badge: "Công cụ bảo vệ an toàn số",
      headline: "Kiểm tra dấu hiệu lừa đảo",
      headlineSub: "Tải ảnh chụp màn hình hoặc dán tin nhắn, đường link để phát hiện chiêu trò mạo danh và thao túng tâm lý.",
      realCases: "Tình huống mẫu hay gặp",
      sampleHelper: "Bấm để xem mẫu",
      scenarioDisclaimer: "Dựa trên các phương thức lừa đảo phổ biến thường gặp.",
    },
    input: {
      tabImage: "Ảnh",
      tabText: "Văn bản hoặc liên kết",
      dropzoneTitle: "Kéo thả ảnh chụp vào đây hoặc bấm để chọn tệp",
      dropzoneSubtitle: "Ảnh chụp tin nhắn SMS, Zalo, Telegram, giao dịch ngân hàng",
      dropzoneDragActive: "Thả ảnh vào đây để tải lên",
      supportedFormats: "Hỗ trợ PNG, JPG, WEBP (tối đa 10MB)",
      pasteHint: "Bạn cũng có thể dán ảnh trực tiếp bằng phím tắt Ctrl+V hoặc Cmd+V",
      changeImage: "Chọn ảnh khác",
      pastePlaceholder: "Dán nội dung tin nhắn, email hoặc đường link nghi ngờ (ví dụ: https://...)...",
      btnAnalyze: "Kiểm tra nội dung",
      analyzing: "Đang kiểm tra...",
      analyzingSubtitle: "Đối chiếu tên miền, dấu hiệu mạo danh và phân tích ngôn ngữ...",
    },
    verdict: {
      scamDetected: "Dấu hiệu lừa đảo rõ ràng",
      highRisk: "Rủi ro rất cao",
      suspicious: "Đáng ngờ, cần thận trọng",
      safe: "Chưa thấy dấu hiệu bất thường",
      riskScore: "Điểm rủi ro",
      category: "Hình thức",
      actionScam: "Dừng lại ngay lập tức — Không bấm vào liên kết, không cung cấp mã OTP hay chuyển tiền.",
      actionHigh: "Không tương tác — Hãy xác minh trực tiếp với đơn vị chính thức qua tổng đài.",
      actionSuspicious: "Cần cẩn trọng — Kiểm tra kỹ nguồn gốc trước khi thực hiện bất kỳ thao tác nào.",
      actionSafe: "Không phát hiện yếu tố đe dọa rõ rệt — Vẫn nên giữ thói quen bảo mật cơ bản.",
    },
    mlBadge: {
      badgeTitle: "Mô hình học máy",
      detectedAs: "Phân loại",
      confidence: "độ tin cậy",
      subtext: "Bộ lọc nhanh cục bộ (TF-IDF + Gradient Boosting)",
      keySignals: "Dấu hiệu phát hiện:",
    },
    webIntel: {
      badgeTitle: "Kiểm tra tên miền & liên kết",
      fraudulentDomain: "Tên miền giả mạo",
      legitimateDomain: "Tên miền chính thống",
      unverifiedMatch: "Chưa xác minh",
      targetBrand: "Đơn vị bị mạo danh:",
      unidentified: "Chưa xác định",
      confidence: "Độ tin cậy kiểm tra web:",
      verifiedLive: "Đã kết nối trực tiếp",
      unreachable: "Không thể kết nối tới liên kết",
      suspiciousBehaviors: "Dấu hiệu đáng ngờ trên trang:",
      threatEvidence: "Bằng chứng & nguồn tham chiếu:",
      source: "Nguồn chính thức",
    },
    tabs: {
      overview: "Bằng chứng & Tổng quan",
      psychology: "Thủ đoạn tâm lý",
      family: "Cảnh báo người thân",
      roleplay: "Thực hành phản xạ",
    },
    overview: {
      executiveSummary: "Tóm tắt đánh giá:",
      evidenceComparator: "Đối chiếu bằng chứng thực tế:",
      detectedInData: "Nội dung ghi nhận",
      officialBenchmark: "Sự thật chính thống",
      forensicAnalysis: "Phân tích:",
      emergencyActions: "Hành động an toàn nên làm ngay:",
    },
    psychology: {
      title: "Chiêu thức tâm lý kẻ lừa đảo sử dụng:",
      targetEmotion: "Cảm xúc nhắm đến:",
    },
    family: {
      title: "Tin nhắn cảnh báo nhanh gửi cho người thân:",
      keyWarning: "Lưu ý quan trọng:",
      copied: "Đã sao chép vào bộ nhớ tạm",
      copyBtn: "Sao chép tin nhắn",
      downloadPdf: "Tải báo cáo PDF",
      printReport: "In báo cáo",
    },
    roleplay: {
      title: "Tập dượt ứng biến với kẻ lừa đảo",
      subtitle: "Thử đối thoại trong môi trường an toàn để hình thành phản xạ từ chối dứt khoát",
      placeholder: "Nhập phản hồi của bạn với kẻ lừa đảo...",
      send: "Gửi",
      quickChoiceDanger: "Làm theo yêu cầu (nguy hiểm)",
      quickChoiceSafe: "Từ chối và kiểm tra lại",
      resetChat: "Bắt đầu lại",
    },
    community: {
      title: "Cảnh báo thủ đoạn gần đây",
      subtitle: "Tổng hợp các thủ đoạn mạo danh phổ biến để chủ động phòng tránh",
      searchPlaceholder: "Tìm theo tên ngân hàng, dịch vụ hoặc thủ đoạn...",
      allTags: "Tất cả",
      views: "lượt quan tâm",
      viewAnalysis: "Xem phân tích",
    },
  },
  en: {
    header: {
      appTitle: "ScamShield",
      appSubtitle: "Detect fraudulent patterns in screenshots, messages, and suspicious links",
      modelBadge: "Gemini 2.5 Flash",
      langSwitch: "English",
    },
    onboarding: {
      guideTitle: "Quick 3-step check",
      step1: "Upload a suspicious screenshot or paste suspicious text or link",
      step2: "Click check to evaluate impersonation and threat patterns",
      step3: "Review findings and share instant warning with loved ones",
      dismiss: "Got it",
    },
    hero: {
      badge: "Digital Safety Tool",
      headline: "Check for scam indicators",
      headlineSub: "Upload a screenshot or paste text and links to inspect impersonation traps and psychological pressure.",
      realCases: "Common scenarios",
      sampleHelper: "Click to inspect sample",
      scenarioDisclaimer: "Based on commonly reported scam patterns.",
    },
    input: {
      tabImage: "Image",
      tabText: "Text or Link",
      dropzoneTitle: "Drop screenshot here or click to browse",
      dropzoneSubtitle: "Screenshots of SMS, chat apps, bank receipts, or invoices",
      dropzoneDragActive: "Drop image here to upload",
      supportedFormats: "Supports PNG, JPG, WEBP (up to 10MB)",
      pasteHint: "You can also paste an image directly using Ctrl+V or Cmd+V",
      changeImage: "Change image",
      pastePlaceholder: "Paste suspicious message, SMS, email, or link (e.g. https://...)...",
      btnAnalyze: "Check content",
      analyzing: "Analyzing...",
      analyzingSubtitle: "Examining domain records, brand identity, and coercive language...",
    },
    verdict: {
      scamDetected: "Scam detected",
      highRisk: "High risk",
      suspicious: "Suspicious",
      safe: "No obvious threat",
      riskScore: "Risk score",
      category: "Category",
      actionScam: "Stop immediately — do not click links, share OTP codes, or send money.",
      actionHigh: "Do not interact — verify directly through the institution's official hotline.",
      actionSuspicious: "Proceed with caution — verify the sender before taking any action.",
      actionSafe: "No significant threat detected — continue practicing basic security habits.",
    },
    mlBadge: {
      badgeTitle: "Machine learning pre-scan",
      detectedAs: "Classification",
      confidence: "confidence",
      subtext: "Fast local model (TF-IDF + Gradient Boosting)",
      keySignals: "Key indicators:",
    },
    webIntel: {
      badgeTitle: "Domain & website inspection",
      fraudulentDomain: "Fraudulent domain",
      legitimateDomain: "Legitimate domain",
      unverifiedMatch: "Unverified match",
      targetBrand: "Impersonated brand:",
      unidentified: "Unidentified",
      confidence: "Verification confidence:",
      verifiedLive: "Live probe verified",
      unreachable: "Link unreachable during probe",
      suspiciousBehaviors: "Suspicious indicators on site:",
      threatEvidence: "Evidence & official benchmarks:",
      source: "Official source",
    },
    tabs: {
      overview: "Evidence & Overview",
      psychology: "Psychology tactics",
      family: "Family alert",
      roleplay: "Reflex practice",
    },
    overview: {
      executiveSummary: "Summary:",
      evidenceComparator: "Real-world evidence comparison:",
      detectedInData: "Observed in input",
      officialBenchmark: "Official truth",
      forensicAnalysis: "Analysis:",
      emergencyActions: "Recommended immediate steps:",
    },
    psychology: {
      title: "Psychological tactics used:",
      targetEmotion: "Targeted emotion:",
    },
    family: {
      title: "Quick alert to forward to loved ones:",
      keyWarning: "Important warning:",
      copied: "Copied to clipboard",
      copyBtn: "Copy message",
      downloadPdf: "Download PDF",
      printReport: "Print report",
    },
    roleplay: {
      title: "Practice responding to scammers",
      subtitle: "Simulate a safe conversation to build confident refusal reflexes",
      placeholder: "Type your response...",
      send: "Send",
      quickChoiceDanger: "Comply with request (risky)",
      quickChoiceSafe: "Refuse and verify officially",
      resetChat: "Restart",
    },
    community: {
      title: "Recent fraud alerts",
      subtitle: "Common impersonation schemes to watch out for",
      searchPlaceholder: "Search by brand name or threat pattern...",
      allTags: "All cases",
      views: "views",
      viewAnalysis: "View analysis",
    },
  },
};
