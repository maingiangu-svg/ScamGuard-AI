"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  ShieldAlert, UploadCloud, FileSearch, Check,
  Link2, Image as ImageIcon, ExternalLink, FileDown,
  Printer, Share2, Copy, Send, RefreshCw, X, ArrowRight,
  AlertCircle, Moon, Sun
} from "lucide-react";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { translations, type Language } from "@/lib/i18n";

interface ExternalEvidenceItem {
  title: string;
  source_url: string;
}

interface WebIntelligence {
  detected: boolean;
  url: string | null;
  domain: string | null;
  brand_detected: string | null;
  domain_match: "match" | "mismatch" | "unknown";
  website_status: "accessible" | "unavailable" | "unknown";
  suspicious_indicators: string[];
  external_evidence: ExternalEvidenceItem[];
  confidence: number;
  verified_live?: boolean;
  http_status?: number | null;
}

interface RedFlagItem {
  evidence: string;
  official_fact: string;
  official_link?: string | null;
  explanation: string;
}

interface ForensicResult {
  scam_detected: boolean;
  risk_score: number;
  threat_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "SAFE";
  scam_type: string;
  executive_summary: string;
  web_intelligence?: WebIntelligence;
  red_flags: RedFlagItem[];
  psychological_tricks: { tactic: string; target_emotion: string; analysis: string }[];
  next_move_prediction: string;
  urgent_actions: string[];
  family_alert_card: { headline: string; key_warning: string; shareable_text: string };
  ml_classifier?: {
    ml_risk_score: number;
    ml_label: string;
    ml_confidence: number;
    ml_top_signals: string[];
    model_ready: boolean;
    text_score?: number | null;
    url_score?: number | null;
    text_tokens?: string[];
    url_signals?: string[];
    uncertainty?: number | null;
    action?: string | null;
    normalized_text?: string;
    extracted_url?: string;
    meta_formula?: string;
  };
}

interface CommunityFeedItem {
  id: string;
  timestamp: string;
  title: string;
  tag: string;
  summary: string;
  result: ForensicResult;
}

interface RoleplayMessage {
  id: string;
  sender: "scammer" | "user" | "eval";
  text: string;
  evalStatus?: "safe" | "danger";
}

// Multilingual Sample Cases
const getSampleCases = (lang: Language) => [
  {
    title: lang === "vi"
      ? "Dự án đầu tư Solana cam kết trả lãi theo giờ"
      : "Fake Solana investment promising hourly returns",
    tag: lang === "vi" ? "Bẫy tiền mã hóa" : "Crypto drainer",
    summary: lang === "vi"
      ? "Trang web hứa hẹn lãi suất cố định mỗi giờ nhằm dụ người dùng cấp quyền rút tiền từ ví Web3."
      : "Phishing site promising unrealistic hourly yields to trick victims into signing wallet-draining approvals.",
    mockResult: {
      scam_detected: true,
      risk_score: 98,
      threat_level: "CRITICAL" as const,
      scam_type: lang === "vi" ? "Lừa đảo tiền mã hóa & chiếm đoạt ví" : "Crypto Phishing & Wallet Drainer",
      executive_summary: lang === "vi"
        ? "Nền tảng lừa đảo giả mạo Solana Foundation trên tên miền lạ hashrate-accesscenter.com nhằm chiếm quyền kiểm soát ví người dùng."
        : "Fraudulent platform impersonating the Solana Foundation on an unverified domain designed to siphon connected Web3 wallet assets.",
      web_intelligence: {
        detected: true,
        url: "https://hashrate-accesscenter.com/solana-miner",
        domain: "hashrate-accesscenter.com",
        brand_detected: "Solana Foundation",
        domain_match: "mismatch" as const,
        website_status: "accessible" as const,
        suspicious_indicators: lang === "vi"
          ? [
              "Yêu cầu cấp toàn quyền truy cập tài sản trong ví",
              "Cam kết lợi nhuận cố định phi thực tế theo giờ",
              "Tên miền mới đăng ký, không có chứng chỉ pháp nhân"
            ]
          : [
              "Requests unlimited wallet asset permissions",
              "Guarantees unrealistic fixed hourly returns",
              "Newly registered domain lacking corporate SSL and legal identity"
            ],
        external_evidence: [
          {
            title: lang === "vi" ? "Cảnh báo thủ đoạn rút ruột ví điện tử Web3" : "Web3 Security Advisory: Fake Cloud Mining Drainers",
            source_url: "https://www.google.com/search?q=solana+mining+drainer+scam+alert"
          },
          {
            title: lang === "vi" ? "Trang web chính thức của Solana Foundation (solana.com)" : "Official Solana Foundation Domain (solana.com)",
            source_url: "https://solana.com"
          }
        ],
        confidence: 96,
      },
      red_flags: [
        {
          evidence: "hashrate-accesscenter.com",
          official_fact: lang === "vi" ? "Địa chỉ chính thức duy nhất của Solana là solana.com." : "The only official website of the Solana Foundation is solana.com.",
          official_link: "https://solana.com",
          explanation: lang === "vi"
            ? "Tên miền của bên thứ ba không được xác minh, tạo ra nhằm mục đích chiếm quyền ví khi kết nối."
            : "Unregistered third-party domain crafted to drain connected cryptocurrency wallets."
        },
        {
          evidence: lang === "vi" ? "Cam kết lợi nhuận 0.065 SOL/giờ (~1.56 SOL/ngày)" : "Guaranteed 0.065 SOL/hour (~1.56 SOL/day)",
          official_fact: lang === "vi" ? "Lợi suất gửi staking chính thức của mạng lưới Solana chỉ khoảng 6-7% mỗi năm." : "Official Solana staking yield is approximately 6-7% annually.",
          official_link: "https://solana.com",
          explanation: lang === "vi"
            ? "Mức lãi gấp hàng trăm lần thực tế là dấu hiệu điển hình của mô hình lừa đảo ponzi."
            : "Yield promises exceeding market benchmarks by over 100x indicate a fraudulent ponzi scheme."
        }
      ],
      psychological_tricks: [
        {
          tactic: lang === "vi" ? "Tạo cảm giác sợ bỏ lỡ cơ hội (FOMO)" : "Profit FOMO",
          target_emotion: lang === "vi" ? "Kỳ vọng kiếm tiền nhanh" : "Greed & Urgency",
          analysis: lang === "vi"
            ? "Kích thích tâm lý muốn có nguồn thu nhập thụ động mà không phải chịu rủi ro."
            : "Instills urgency and fear of missing out on risk-free passive hourly income."
        }
      ],
      next_move_prediction: lang === "vi"
        ? "Yêu cầu ký lệnh phê duyệt giao dịch không giới hạn để chuyển toàn bộ token ra khỏi ví của bạn."
        : "Requests unlimited token spending approval to siphon all native SOL and tokens from the wallet.",
      urgent_actions: lang === "vi"
        ? [
            "Đóng ngay tab trình duyệt đang mở",
            "Hủy quyền phê duyệt hợp đồng đáng ngờ qua Revoke.cash nếu đã lỡ kết nối ví"
          ]
        : [
            "Close the browser tab immediately",
            "Revoke suspicious token approvals via Revoke.cash"
          ],
      family_alert_card: {
        headline: lang === "vi" ? "Cảnh báo lừa đảo đầu tư tiền mã hóa" : "Alert: Fake Crypto Yield Mining Trap",
        key_warning: lang === "vi" ? "Không bao giờ kết nối ví cá nhân vào các trang web hứa hẹn trả lãi theo giờ!" : "Never connect personal Web3 wallets to sites promising hourly returns!",
        shareable_text: lang === "vi"
          ? "CẢNH BÁO: Đừng bấm vào các liên kết mời tham gia 'đào coin nhận lãi theo giờ'. Đây là bẫy rút sạch tiền trong ví điện tử!"
          : "WARNING: Never join sites promising guaranteed hourly cryptocurrency yields. Connecting your wallet will drain all deposited funds!"
      }
    }
  },
  {
    title: lang === "vi"
      ? "Cuộc gọi video Deepfake giả người thân mượn tiền gấp"
      : "AI deepfake video call mimicking a family member",
    tag: lang === "vi" ? "Mạo danh Deepfake" : "Deepfake fraud",
    summary: lang === "vi"
      ? "Kẻ gian giả mạo khuôn mặt và giọng nói trong vài giây chập chờn để tạo tình huống khẩn cấp giả tạo."
      : "Fraudsters synthesize a brief, glitchy emergency call to pressure victims into urgent money transfers.",
    mockResult: {
      scam_detected: true,
      risk_score: 94,
      threat_level: "HIGH" as const,
      scam_type: lang === "vi" ? "Mạo danh bằng công nghệ AI Deepfake" : "AI Deepfake Impersonation",
      executive_summary: lang === "vi"
        ? "Kẻ xấu ghép mặt và giọng nói của người quen trong cuộc gọi video chập chờn để tạo tình huống khẩn cấp giả tạo."
        : "Real-time AI voice and face synthesis used in a brief emergency call to trigger a hasty wire transfer.",
      web_intelligence: {
        detected: false,
        url: null,
        domain: null,
        brand_detected: null,
        domain_match: "unknown" as const,
        website_status: "unknown" as const,
        suspicious_indicators: [],
        external_evidence: [],
        confidence: 0,
      },
      red_flags: [
        {
          evidence: lang === "vi" ? "Cuộc gọi hình ảnh chập chờn và ngắt đột ngột sau vài giây" : "Glitchy video stream disconnected after a few seconds",
          official_fact: lang === "vi" ? "Kẻ gian cố tình tạo mạng chập chờn để che giấu các lỗi ghép ảnh do AI tạo ra." : "Generative deepfakes often struggle with continuous facial consistency, so attackers fake lag.",
          official_link: "https://khonggianmang.vn",
          explanation: lang === "vi"
            ? "Công nghệ Deepfake thời gian thực còn nhiều khuyết điểm quanh viền mắt và khẩu hình miệng."
            : "Attackers intentionally induce blur and latency to conceal AI synthesis artifacts."
        },
        {
          evidence: lang === "vi" ? "Yêu cầu chuyển tiền vào số tài khoản lạ mang tên người khác" : "Demands money transfer to an unfamiliar third-party account",
          official_fact: lang === "vi" ? "Người thân trong gia đình khi gặp sự cố thật thường nhận tiền qua tài khoản chính chủ của họ." : "Family members in legitimate emergencies use their own accounts or verified contacts.",
          official_link: "https://khonggianmang.vn",
          explanation: lang === "vi"
            ? "Kẻ gian viện lý do tài khoản cá nhân bị lỗi hoặc nhờ chuyển vào số tài khoản của bệnh viện."
            : "Pretends personal account is frozen or provides a fabricated clinic account."
        }
      ],
      psychological_tricks: [
        {
          tactic: lang === "vi" ? "Tạo áp lực khẩn cấp giả tạo" : "Fabricated Emergency",
          target_emotion: lang === "vi" ? "Lo lắng cho người thân" : "Family Concern",
          analysis: lang === "vi"
            ? "Đẩy nạn nhân vào trạng thái hoảng loạn để không kịp gọi điện kiểm tra chéo."
            : "Induces panic to prevent the victim from calmly placing a direct call to verify."
        }
      ],
      next_move_prediction: lang === "vi"
        ? "Tiếp tục hối thúc chuyển thêm tiền với lý do chi phí cấp cứu phát sinh ngoài dự kiến."
        : "Follows up aggressively demanding additional transfers claiming unexpected medical costs.",
      urgent_actions: lang === "vi"
        ? [
            "Tắt máy ngay và gọi trực tiếp vào số điện thoại viễn thông thông thường của người đó",
            "Hỏi một câu hỏi riêng tư mà chỉ người thân thực sự mới biết để xác minh"
          ]
        : [
            "Hang up and place a direct cellular call (GSM) to the family member",
            "Ask a personal question only the real person would know to verify identity"
          ],
      family_alert_card: {
        headline: lang === "vi" ? "Cảnh báo cuộc gọi video mạo danh người thân" : "Alert: Deepfake Video Call Money Request",
        key_warning: lang === "vi" ? "Thấy mặt người quen trên video call vẫn có thể là sản phẩm ghép nối của AI!" : "Seeing a familiar face on a video call can still be an AI-generated fake!",
        shareable_text: lang === "vi"
          ? "CẢNH BÁO GIA ĐÌNH: Nếu nhận được cuộc gọi video từ người thân nhờ chuyển tiền gấp, hãy cúp máy và gọi lại số điện thoại chính để xác nhận!"
          : "FAMILY ALERT: If you receive a video call from a relative asking for emergency money, hang up and call their direct phone number to verify!"
      }
    }
  },
  {
    title: lang === "vi"
      ? "Yêu cầu cài tệp APK giả mạo cổng dịch vụ công"
      : "Malicious APK mimicking official government portal",
    tag: lang === "vi" ? "Mã độc Android" : "Android malware",
    summary: lang === "vi"
      ? "Đường dẫn tải tệp APK mạo danh cơ quan nhà nước nhằm chiếm quyền trợ năng và đọc mã OTP."
      : "Fraudulent download link installing Trojan software to hijack accessibility services and intercept bank OTPs.",
    mockResult: {
      scam_detected: true,
      risk_score: 99,
      threat_level: "CRITICAL" as const,
      scam_type: lang === "vi" ? "Mã độc chiếm quyền điều khiển điện thoại" : "Android Banking Malware",
      executive_summary: lang === "vi"
        ? "Đường link phân phối tệp .APK độc hại giả mạo cổng dịch vụ công để kiểm soát ứng dụng ngân hàng và đánh cắp OTP."
        : "Distribution of malicious .APK exploiting Android Accessibility Service to remotely control banking apps and harvest OTP.",
      web_intelligence: {
        detected: true,
        url: "https://dichvucong-gov.apk-store.site/app.apk",
        domain: "dichvucong-gov.apk-store.site",
        brand_detected: lang === "vi" ? "Cổng Dịch vụ công Quốc gia" : "Government Identity Authority",
        domain_match: "mismatch" as const,
        website_status: "accessible" as const,
        suspicious_indicators: lang === "vi"
          ? [
              "Tải tệp tin .APK trực tiếp bên ngoài kho ứng dụng Google Play",
              "Yêu cầu cấp quyền Accessibility (Trợ năng) để điều khiển từ xa"
            ]
          : [
              "Direct .APK download outside Google Play",
              "Demands Accessibility Service permissions for remote control"
            ],
        external_evidence: [
          { title: "Cổng thông tin Cục An toàn thông tin", source_url: "https://khonggianmang.vn" }
        ],
        confidence: 99,
      },
      red_flags: [
        {
          evidence: "dichvucong-gov.apk-store.site",
          official_fact: lang === "vi" ? "Các ứng dụng dịch vụ công chính thức chỉ được phân phối qua Google Play và Apple App Store." : "Official public administration apps are distributed strictly via Google Play and App Store.",
          official_link: "https://khonggianmang.vn",
          explanation: lang === "vi"
            ? "Cơ quan nhà nước không bao giờ gửi link qua Zalo hay SMS để yêu cầu người dân cài đặt file APK."
            : "Government agencies never send links over SMS or social media to install APK updates."
        },
        {
          evidence: "Accessibility Service",
          official_fact: lang === "vi" ? "Ứng dụng hành chính công hợp pháp không bao giờ yêu cầu quyền trợ năng." : "Legitimate public administration applications never require Accessibility permissions.",
          official_link: "https://khonggianmang.vn",
          explanation: lang === "vi"
            ? "Quyền này cho phép mã độc tự động đọc màn hình và tự duyệt lệnh chuyển tiền ngân hàng."
            : "Malware exploits Accessibility to read screen content and automate illicit banking transfers."
        }
      ],
      psychological_tricks: [
        {
          tactic: lang === "vi" ? "Mạo danh quyền lực pháp lý" : "State Authority Impersonation",
          target_emotion: lang === "vi" ? "Sợ hãi rắc rối thủ tục" : "Legal Fear",
          analysis: lang === "vi"
            ? "Đe dọa khóa tài khoản định danh hoặc phạt hành chính nếu không làm theo hướng dẫn ngay."
            : "Threatens legal sanctions or account freezing if instructions are not carried out immediately."
        }
      ],
      next_move_prediction: lang === "vi"
        ? "Chiếm quyền điều khiển màn hình, tự mở ứng dụng ngân hàng và chuyển tiền trong lúc người dùng không để ý."
        : "Remotely locks victim device display and executes unauthorized withdrawals from banking apps.",
      urgent_actions: lang === "vi"
        ? [
            "Tắt ngay kết nối Wi-Fi, 4G hoặc tắt nguồn điện thoại",
            "Dùng một máy khác gọi ngay đến tổng đài ngân hàng để khóa tài khoản và thẻ"
          ]
        : [
            "Disconnect Wi-Fi and mobile data immediately, or power down the phone",
            "Use a separate phone to call banking fraud hotlines to freeze all accounts"
          ],
      family_alert_card: {
        headline: lang === "vi" ? "Cảnh báo tệp tin độc hại mạo danh cơ quan chức năng" : "Critical Warning: Fake APK Malware",
        key_warning: lang === "vi" ? "Công an hay cán bộ nhà nước không bao giờ gửi link bắt cài file APK!" : "Law enforcement officers never send links asking you to install .APK files!",
        shareable_text: lang === "vi"
          ? "CẢNH BÁO: Tuyệt đối không bấm link cài đặt file APK từ người tự xưng là cán bộ công an hay thuế. Điện thoại sẽ bị chiếm quyền và mất tiền!"
          : "CRITICAL ALERT: Never install APK files from callers claiming to be police or tax officers. They hijack your phone and drain your bank account!"
      }
    }
  }
];

// Multilingual Mock Feed
const getMockCommunityFeed = (lang: Language): CommunityFeedItem[] => [
  {
    id: "case-01",
    timestamp: lang === "vi" ? "Hôm nay" : "Today",
    title: lang === "vi"
      ? "Sàn giao dịch quyền chọn nhị phân cam kết bảo hiểm 100% vốn"
      : "Binary options platform promising 100% capital protection",
    tag: lang === "vi" ? "Đầu tư giả mạo" : "Fake investment",
    summary: lang === "vi"
      ? "Biểu đồ nến lập trình sẵn để tạo cảm giác có lãi, sau đó chặn rút tiền và đòi nộp thêm thuế."
      : "Rigged charts simulate early trading wins, then lock withdrawals demanding advance fee and tax payments.",
    result: {
      scam_detected: true,
      risk_score: 96,
      threat_level: "CRITICAL" as const,
      scam_type: lang === "vi" ? "Sàn đầu tư tài chính lừa đảo" : "Fake Trading Platform",
      executive_summary: lang === "vi"
        ? "Sàn giao dịch không phép tạo biểu đồ ảo để dụ người dùng nạp thêm tiền trước khi cắt đứt liên lạc."
        : "Unregulated binary options exchange manipulating prices and demanding fee deposits before permitting withdrawals.",
      web_intelligence: {
        detected: true,
        url: "https://bo-trade-vip.net",
        domain: "bo-trade-vip.net",
        brand_detected: "Sàn chứng khoán",
        domain_match: "mismatch" as const,
        website_status: "accessible" as const,
        suspicious_indicators: [
          "Guarantees 100% loss indemnity",
          "Demands advance tax fee before withdrawal"
        ],
        external_evidence: [
          { title: "Ủy ban Chứng khoán Nhà nước", source_url: "https://ssc.gov.vn" }
        ],
        confidence: 95,
      },
      red_flags: [
        {
          evidence: "100% capital protection",
          official_fact: lang === "vi" ? "Mọi hình thức đầu tư tài chính hợp pháp đều có rủi ro và không thể cam kết hoàn vốn 100%." : "Regulated financial investments carry risk and never guarantee 100% capital preservation.",
          official_link: "https://ssc.gov.vn",
          explanation: lang === "vi" ? "Lời hứa phi thực tế nhằm làm mờ đi cảnh giác của người mới tham gia." : "Psychological bait designed to reassure victims into depositing large sums."
        }
      ],
      psychological_tricks: [
        {
          tactic: "Tạo niềm tin ảo",
          target_emotion: "Kỳ vọng lợi nhuận",
          analysis: "Cho rút thử số tiền nhỏ ban đầu để tạo niềm tin trước khi yêu cầu nạp số tiền lớn."
        }
      ],
      next_move_prediction: "Yêu cầu đóng 20% phí xác minh tài khoản trước khi cho rút tiền.",
      urgent_actions: [
        "Ngừng nạp thêm bất kỳ khoản tiền nào",
        "Lưu lại lịch sử giao dịch và tin nhắn"
      ],
      family_alert_card: {
        headline: "Cảnh báo sàn đầu tư cam kết bảo hiểm vốn",
        key_warning: "Bất kỳ lời mời đầu tư nào cam kết không bao giờ lỗ đều là lừa đảo!",
        shareable_text: "CẢNH BÁO: Đừng tin vào các nhóm đầu tư cam kết bảo hiểm 100% vốn. Nạp tiền vào là sẽ không rút ra được!"
      }
    }
  },
  {
    id: "case-02",
    timestamp: lang === "vi" ? "Hôm qua" : "Yesterday",
    title: lang === "vi"
      ? "Tin nhắn nhờ bình chọn cuộc thi ảnh để đánh cắp tài khoản Telegram"
      : "Photo contest voting link designed to hijack Telegram accounts",
    tag: lang === "vi" ? "Đánh cắp tài khoản" : "Account takeover",
    summary: lang === "vi"
      ? "Người quen bị hack nhắn tin nhờ bình chọn, trang web yêu cầu nhập mã OTP Telegram."
      : "Compromised friend asks for a vote, directing victims to a phishing form harvesting login OTPs.",
    result: {
      scam_detected: true,
      risk_score: 95,
      threat_level: "CRITICAL" as const,
      scam_type: lang === "vi" ? "Đánh cắp tài khoản mạng xã hội" : "Telegram Phishing",
      executive_summary: lang === "vi"
        ? "Trang web bình chọn giả mạo thu thập mã xác nhận OTP để đăng nhập và chiếm quyền tài khoản Telegram."
        : "Spoofed voting portal capturing Telegram authentication OTP to hijack active user sessions.",
      web_intelligence: {
        detected: true,
        url: "https://vote-khoanhkhac-2026.com",
        domain: "vote-khoanhkhac-2026.com",
        brand_detected: "Telegram",
        domain_match: "mismatch" as const,
        website_status: "accessible" as const,
        suspicious_indicators: [
          "Phishing form asking for Telegram OTP",
          "Recently registered disposable domain"
        ],
        external_evidence: [
          { title: "Telegram Security", source_url: "https://telegram.org" }
        ],
        confidence: 97,
      },
      red_flags: [
        {
          evidence: "vote-khoanhkhac-2026.com",
          official_fact: lang === "vi" ? "Mã OTP chỉ dùng để đăng nhập vào ứng dụng Telegram, không bao giờ dùng để bình chọn cuộc thi." : "Telegram login codes are strictly for application login, never for voting contests.",
          official_link: "https://telegram.org",
          explanation: lang === "vi" ? "Kẻ gian dùng mã này để đăng nhập vào tài khoản của bạn trên thiết bị của chúng." : "Attackers use this OTP to authenticate on their own devices."
        }
      ],
      psychological_tricks: [
        {
          tactic: "Lợi dụng sự nhiệt tình giúp đỡ bạn bè",
          target_emotion: "Tin tưởng người quen",
          analysis: "Tin nhắn gửi từ tài khoản người quen đã bị chiếm đoạt khiến người nhận ít đề phòng."
        }
      ],
      next_move_prediction: "Chiếm đoạt tài khoản và tiếp tục gửi tin nhắn vay tiền đến toàn bộ danh bạ.",
      urgent_actions: [
        "Vào Cài đặt Telegram -> Thiết bị -> Đăng xuất khỏi tất cả các phiên lạ",
        "Bật xác thực hai bước (mật khẩu phụ)"
      ],
      family_alert_card: {
        headline: "Cảnh báo bẫy bình chọn cuộc thi qua tin nhắn",
        key_warning: "Tuyệt đối không nhập mã OTP Telegram trên bất kỳ trang web nào!",
        shareable_text: "CẢNH BÁO: Nhận được tin nhắn nhờ vote cuộc thi thì đừng bấm link hay nhập mã xác thực, nếu không tài khoản sẽ bị cướp ngay lập tức!"
      }
    }
  }
];

const getQuickRoleplayResponses = (lang: Language) => [
  {
    label: lang === "vi" ? "Gọi lại số hotline chính thức để xác minh" : "Call official hotline directly to verify",
    text: lang === "vi"
      ? "Tôi sẽ tự liên hệ lên hotline chính thức của ngân hàng để kiểm tra. Tôi không cung cấp thông tin qua tin nhắn hay link lạ."
      : "I will contact the bank's official customer support line directly. I never share credentials over chat or external links.",
    isRisky: false,
  },
  {
    label: lang === "vi" ? "Từ chối và báo cáo số điện thoại" : "Decline and report the contact",
    text: lang === "vi"
      ? "Tôi không có nhu cầu. Đây là dấu hiệu lừa đảo và tôi sẽ báo cáo số điện thoại này đến cơ quan chức năng."
      : "I am not interested. This is a fraudulent scheme and I am reporting this number immediately.",
    isRisky: false,
  },
  {
    label: lang === "vi" ? "Làm theo hướng dẫn: Gửi mã OTP hoặc bấm link" : "Trap: Provide OTP code or click the link",
    text: lang === "vi"
      ? "Vâng, để tôi đọc mã OTP vừa gửi về điện thoại cho bạn để xử lý giúp tôi luôn nhé!"
      : "Sure, let me read you the OTP code I just received so you can unlock my account!",
    isRisky: true,
  },
];

export default function ScamShieldDashboard() {
  const [inputMode, setInputMode] = useState<"image" | "text">("image");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [textInput, setTextInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ForensicResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [caseId, setCaseId] = useState("");
  const [activeTab, setActiveTab] = useState<"overview" | "psychology" | "family" | "roleplay">("overview");
  const [isDragging, setIsDragging] = useState(false);

  // Theme state: defaults to "muted" (warm graphite/obsidian - not white, not pure black)
  const [theme, setTheme] = useState<"muted" | "light">("muted");

  // Roleplay state
  const [roleplayInput, setRoleplayInput] = useState("");
  const [roleplayMessages, setRoleplayMessages] = useState<RoleplayMessage[]>([]);
  const [roleplayLoading, setRoleplayLoading] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [lang, setLang] = useState<Language>("en");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedLang = localStorage.getItem("scamshield-lang") as Language;
      if (savedLang === "en" || savedLang === "vi") {
        setLang(savedLang);
      }
      const savedTheme = localStorage.getItem("scamshield-theme") as "muted" | "light";
      if (savedTheme === "muted" || savedTheme === "light") {
        setTheme(savedTheme);
      }
    }
  }, []);

  const toggleLang = (newLang: Language) => {
    setLang(newLang);
    if (typeof window !== "undefined") {
      localStorage.setItem("scamshield-lang", newLang);
    }
  };

  const toggleTheme = (newTheme: "muted" | "light") => {
    setTheme(newTheme);
    if (typeof window !== "undefined") {
      localStorage.setItem("scamshield-theme", newTheme);
    }
  };

  const isMuted = theme === "muted";
  const t = translations[lang];
  const sampleCases = getSampleCases(lang);
  const communityFeed = getMockCommunityFeed(lang);
  const quickRoleplayResponses = getQuickRoleplayResponses(lang);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const reportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && !localStorage.getItem("scamshield-onboarded")) {
      setShowOnboarding(true);
    }
  }, []);

  // Global paste handler: Ctrl+V or Cmd+V anywhere to paste screenshot
  useEffect(() => {
    const handleGlobalPaste = (e: ClipboardEvent) => {
      const target = e.target as HTMLElement;
      if (target && (target.tagName === "TEXTAREA" || target.tagName === "INPUT")) {
        return;
      }

      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf("image") !== -1) {
          const pastedFile = items[i].getAsFile();
          if (pastedFile) {
            setInputMode("image");
            handleFile(pastedFile);
            e.preventDefault();
            break;
          }
        }
      }
    };

    window.addEventListener("paste", handleGlobalPaste);
    return () => window.removeEventListener("paste", handleGlobalPaste);
  }, []);

  const dismissOnboarding = () => {
    localStorage.setItem("scamshield-onboarded", "1");
    setShowOnboarding(false);
  };

  const generateId = () => `scam-${Math.floor(1000 + Math.random() * 9000)}`;

  const getInitialRoleplayMessages = (res: ForensicResult | null): RoleplayMessage[] => {
    if (!res) return [];
    let scammerOpening = lang === "vi"
      ? "Thông báo khẩn từ hệ thống! Tài khoản của bạn vừa ghi nhận giao dịch bất thường. Bấm vào liên kết hoặc đọc mã xác thực trong 3 phút để không bị khóa thẻ!"
      : "Urgent alert! An unauthorized transaction was detected on your account. Click the verification link or provide your OTP within 3 minutes to avoid card suspension!";

    if (res.red_flags?.[0]?.evidence) {
      scammerOpening = lang === "vi"
        ? `"${res.red_flags[0].evidence}" — Bạn cần thao tác theo đúng hướng dẫn ngay bây giờ để được hỗ trợ!`
        : `"${res.red_flags[0].evidence}" — You must follow our instructions immediately to resolve this matter!`;
    }

    return [
      {
        id: "msg-init",
        sender: "scammer",
        text: scammerOpening,
      }
    ];
  };

  const handleFile = (selected: File) => {
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
    setResult(null);
    setError(null);
  };

  const handleSelectCase = (sample: typeof sampleCases[0]) => {
    setFile(null);
    setPreviewUrl(null);
    setTextInput("");
    setCaseId(generateId());
    setResult(sample.mockResult);
    setRoleplayMessages(getInitialRoleplayMessages(sample.mockResult));
    setActiveTab("overview");
    window.scrollTo({ top: 380, behavior: "smooth" });
  };

  const handleSelectFeedItem = (item: CommunityFeedItem) => {
    setCaseId(item.id);
    setResult(item.result);
    setRoleplayMessages(getInitialRoleplayMessages(item.result));
    setActiveTab("overview");
    window.scrollTo({ top: 380, behavior: "smooth" });
  };

  const handleNativeShare = async () => {
    if (!result) return;
    const shareText = result.family_alert_card.shareable_text;
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({
          title: result.family_alert_card.headline || "Cảnh báo an toàn",
          text: shareText,
          url: window.location.href,
        });
      } catch {
        // User closed native share dialog
      }
    } else {
      navigator.clipboard.writeText(shareText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSendRoleplay = async (userText: string, isRiskyQuickChoice?: boolean) => {
    if (!userText.trim() || !result || roleplayLoading) return;

    const userMsg: RoleplayMessage = {
      id: `u-${Date.now()}`,
      sender: "user",
      text: userText,
    };

    setRoleplayMessages((prev) => {
      const base = prev.length > 0 ? prev : getInitialRoleplayMessages(result);
      return [...base, userMsg];
    });
    setRoleplayInput("");
    setRoleplayLoading(true);

    try {
      const history = (roleplayMessages.length > 0 ? roleplayMessages : getInitialRoleplayMessages(result))
        .map((m) => ({ sender: m.sender, text: m.text }));

      const res = await fetch("/api/roleplay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scamType: result.scam_type,
          scamContext: result.executive_summary,
          userMessage: userText,
          history,
          isRiskyQuickChoice,
        }),
      });

      if (!res.ok) throw new Error((await res.json()).error || "Roleplay error");

      const data = await res.json();

      const evalMsg: RoleplayMessage = {
        id: `e-${Date.now()}`,
        sender: "eval",
        text: data.eval_text,
        evalStatus: data.eval_status,
      };

      const scammerReplyMsg: RoleplayMessage = {
        id: `s-${Date.now()}`,
        sender: "scammer",
        text: data.scammer_reply,
      };

      setRoleplayMessages((prev) => [...prev, evalMsg, scammerReplyMsg]);
    } catch {
      const lower = userText.toLowerCase();
      const isDangerous = isRiskyQuickChoice || lower.includes("otp") || lower.includes("mật khẩu") || lower.includes("chuyển") || lower.includes("password");
      setRoleplayMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          sender: "eval",
          text: isDangerous
            ? (lang === "vi" ? "Rất nguy hiểm: Tuyệt đối không bao giờ cung cấp mã OTP, mật khẩu hay chuyển tiền theo yêu cầu của người lạ." : "Dangerous: Never share OTP codes, passwords, or send funds to unverified parties.")
            : (lang === "vi" ? "Xử lý an toàn: Phản hồi bình tĩnh và chủ động xác minh qua kênh chính thống." : "Safe response: Staying calm and verifying through official channels."),
          evalStatus: isDangerous ? "danger" : "safe",
        },
        {
          id: `s-${Date.now()}`,
          sender: "scammer",
          text: isDangerous
            ? (lang === "vi" ? "Kẻ lừa đảo đã đạt được mục đích chiếm đoạt thông tin. Đây là bài học để bạn cảnh giác hơn ngoài đời thực." : "The scammer succeeded in capturing credentials. Use this simulation to stay alert.")
            : (lang === "vi" ? "Kẻ lừa đảo thấy bạn cảnh giác và đã chủ động ngắt cuộc gọi để tìm nạn nhân khác." : "The scammer realized you were cautious and abandoned the attempt."),
        },
      ]);
    } finally {
      setRoleplayLoading(false);
    }
  };

  const handleExportPdf = async () => {
    if (!reportRef.current || !result) return;
    setExportingPdf(true);
    try {
      const canvas = await html2canvas(reportRef.current, {
        backgroundColor: isMuted ? "#161618" : "#FAF8F5",
        scale: 2,
        useCORS: true,
      });
      const img = canvas.toDataURL("image/png");
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      const w = pdf.internal.pageSize.getWidth();
      const h = (canvas.height * w) / canvas.width;
      pdf.addImage(img, "PNG", 0, 0, w, h);
      pdf.save(`ScamShield-${caseId || "report"}.pdf`);
    } catch {
      window.print();
    } finally {
      setExportingPdf(false);
    }
  };

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      let res;
      if (inputMode === "image") {
        if (!file) return;
        const fd = new FormData();
        fd.append("image", file);
        fd.append("language", lang);
        res = await fetch("/api/analyze", { method: "POST", body: fd });
      } else {
        if (!textInput.trim()) return;
        res = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ textInput, language: lang }),
        });
      }
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        let rawErr = errData.error || (lang === "vi" ? "Không thể hoàn thành kiểm tra" : "Forensic analysis failed");
        if (typeof rawErr === "object") rawErr = JSON.stringify(rawErr);
        if (typeof rawErr === "string" && (rawErr.includes("API key not valid") || rawErr.includes("INVALID_ARGUMENT"))) {
          rawErr = lang === "vi"
            ? "Chưa cấu hình GEMINI_API_KEY hợp lệ trong môi trường chạy."
            : "GEMINI_API_KEY is missing or invalid in your environment.";
        }
        throw new Error(rawErr);
      }
      const analysisData: ForensicResult = await res.json();
      const newId = generateId();
      setCaseId(newId);
      setResult(analysisData);
      setRoleplayMessages(getInitialRoleplayMessages(analysisData));
      setActiveTab("overview");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const activeRoleplayList = roleplayMessages.length > 0 ? roleplayMessages : getInitialRoleplayMessages(result);
  const canAnalyze = (inputMode === "image" && !!file) || (inputMode === "text" && !!textInput.trim());

  return (
    <div className={`min-h-screen transition-colors duration-200 selection:bg-[#E5484D]/25 selection:text-inherit pb-24 ${
      isMuted
        ? "bg-[#161618] text-[#EDEAE4]"
        : "bg-[#FAF8F5] text-[#1C1917]"
    }`}>
      {/* ── TOP NAVIGATION ──────────────────────────────────────────────────────── */}
      <header className={`border-b backdrop-blur-md sticky top-0 z-40 print:hidden transition-colors ${
        isMuted
          ? "border-[#2E2E34] bg-[#161618]/90"
          : "border-[#E7E2D9] bg-[#FAF8F5]/90"
      }`}>
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#E5484D] text-white flex items-center justify-center shadow-xs">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <div className="font-semibold text-base tracking-tight flex items-center gap-2">
                <span>{t.header.appTitle}</span>
              </div>
              <p className={`text-xs hidden sm:block ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                {t.header.appSubtitle}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Theme Toggle (Muted Dark vs Warm Light) */}
            <button
              onClick={() => toggleTheme(isMuted ? "light" : "muted")}
              className={`p-1.5 px-2.5 rounded-lg border text-xs flex items-center gap-1.5 transition cursor-pointer ${
                isMuted
                  ? "bg-[#202024] border-[#2E2E34] text-[#A19E95] hover:text-[#EDEAE4]"
                  : "bg-white border-[#E7E2D9] text-[#57534E] hover:text-[#1C1917]"
              }`}
              title={isMuted ? (lang === "vi" ? "Chuyển sang nền sáng" : "Switch to light theme") : (lang === "vi" ? "Chuyển sang nền trầm" : "Switch to muted dark theme")}
            >
              {isMuted ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-[#57534E]" />}
              <span className="hidden sm:inline font-medium text-[11px]">
                {isMuted ? (lang === "vi" ? "Tối trầm" : "Muted") : (lang === "vi" ? "Sáng" : "Light")}
              </span>
            </button>

            {/* Language Switcher */}
            <div className={`flex items-center text-xs ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
              <button
                onClick={() => toggleLang("vi")}
                className={`px-2 py-1 transition cursor-pointer ${
                  lang === "vi" ? (isMuted ? "text-[#EDEAE4] font-semibold" : "text-[#1C1917] font-semibold") : (isMuted ? "hover:text-[#EDEAE4]" : "hover:text-[#1C1917]")
                }`}
              >
                VI
              </button>
              <span className={isMuted ? "text-[#3E3E48]" : "text-[#D6D0C4]"}>/</span>
              <button
                onClick={() => toggleLang("en")}
                className={`px-2 py-1 transition cursor-pointer ${
                  lang === "en" ? (isMuted ? "text-[#EDEAE4] font-semibold" : "text-[#1C1917] font-semibold") : (isMuted ? "hover:text-[#EDEAE4]" : "hover:text-[#1C1917]")
                }`}
              >
                EN
              </button>
            </div>

            <span className={`hidden md:inline-flex items-center px-2.5 py-1 text-xs border rounded-md font-medium ${
              isMuted
                ? "bg-[#202024] border-[#2E2E34] text-[#A19E95]"
                : "bg-[#F5F2EB] border-[#E7E2D9] text-[#57534E]"
            }`}>
              {t.header.modelBadge}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 mt-10">
        {/* Onboarding Banner (Clean, Dismissible) */}
        {showOnboarding && (
          <div className={`mb-8 p-4 border rounded-xl shadow-xs relative print:hidden ${
            isMuted
              ? "bg-[#202024] border-[#2E2E34]"
              : "bg-white border-[#E7E2D9]"
          }`}>
            <button
              onClick={dismissOnboarding}
              className={`absolute top-3 right-3 cursor-pointer ${isMuted ? "text-[#71717A] hover:text-[#EDEAE4]" : "text-[#78716C] hover:text-[#1C1917]"}`}
              aria-label={t.onboarding.dismiss}
            >
              <X className="w-4 h-4" />
            </button>
            <div className="pr-8">
              <div className="text-sm font-semibold mb-1">
                {t.onboarding.guideTitle}
              </div>
              <div className={`grid grid-cols-1 md:grid-cols-3 gap-3 text-[13px] mt-2 ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                <div className="flex items-start gap-2">
                  <span className={`w-5 h-5 rounded-full font-semibold flex items-center justify-center shrink-0 text-xs ${
                    isMuted ? "bg-[#2E2E34] text-[#EDEAE4]" : "bg-[#F5F2EB] text-[#1C1917]"
                  }`}>1</span>
                  <span>{t.onboarding.step1}</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className={`w-5 h-5 rounded-full font-semibold flex items-center justify-center shrink-0 text-xs ${
                    isMuted ? "bg-[#2E2E34] text-[#EDEAE4]" : "bg-[#F5F2EB] text-[#1C1917]"
                  }`}>2</span>
                  <span>{t.onboarding.step2}</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className={`w-5 h-5 rounded-full font-semibold flex items-center justify-center shrink-0 text-xs ${
                    isMuted ? "bg-[#2E2E34] text-[#EDEAE4]" : "bg-[#F5F2EB] text-[#1C1917]"
                  }`}>3</span>
                  <span>{t.onboarding.step3}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── HERO HEADER WITH EDITORIAL ILLUSTRATION ──────────────────────────── */}
        <div className="mb-10 print:hidden flex items-center justify-between gap-6 flex-wrap md:flex-nowrap">
          <div className="max-w-xl">
            <h1 className="text-3xl sm:text-4xl font-editorial font-normal tracking-tight mb-2 leading-tight">
              {t.hero.headline}
            </h1>
            <p className={`text-[15px] leading-relaxed ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
              {t.hero.headlineSub}
            </p>
          </div>

          {/* Hand-drawn style illustration: Shield protecting a conversation */}
          <div className="hidden sm:flex shrink-0 items-center justify-center" aria-hidden="true">
            <svg
              width="130"
              height="100"
              viewBox="0 0 130 100"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Soft sketch background bubble */}
              <rect x="15" y="16" width="76" height="52" rx="14" fill={isMuted ? "#202024" : "#F5F2EB"} stroke={isMuted ? "#383840" : "#1C1917"} strokeWidth="1.75" strokeLinejoin="round" />
              <path d="M26 68L22 79L36 68" fill={isMuted ? "#202024" : "#F5F2EB"} stroke={isMuted ? "#383840" : "#1C1917"} strokeWidth="1.75" strokeLinejoin="round" />
              {/* Message lines in bubble */}
              <line x1="28" y1="32" x2="68" y2="32" stroke={isMuted ? "#71717A" : "#A8A29E"} strokeWidth="2.5" strokeLinecap="round" />
              <line x1="28" y1="42" x2="52" y2="42" stroke={isMuted ? "#71717A" : "#A8A29E"} strokeWidth="2.5" strokeLinecap="round" />
              
              {/* Suspicious link warning dot in bubble */}
              <circle cx="75" cy="42" r="3" fill="#E5484D" />

              {/* Protective Shield Overlay */}
              <path
                d="M84 28C98 28 106 20 106 20C106 20 114 28 128 28C128 52 118 68 106 74C94 68 84 52 84 28Z"
                fill={isMuted ? "#161618" : "#FAF8F5"}
                stroke={isMuted ? "#EDEAE4" : "#1C1917"}
                strokeWidth="1.75"
                strokeLinejoin="round"
              />
              <path
                d="M93 34C102 34 106 28 106 28C106 28 110 34 119 34C119 50 113 60 106 65C99 60 93 50 93 34Z"
                fill="#E5484D"
                fillOpacity={isMuted ? "0.15" : "0.08"}
                stroke="#E5484D"
                strokeWidth="1.25"
                strokeDasharray="2 2"
              />

              {/* Magnifying Glass */}
              <circle cx="58" cy="52" r="16" fill={isMuted ? "#161618" : "#FAF8F5"} stroke={isMuted ? "#EDEAE4" : "#1C1917"} strokeWidth="1.75" />
              <circle cx="58" cy="52" r="13" stroke="#E5484D" strokeWidth="1" strokeDasharray="3 3" />
              <line x1="69" y1="64" x2="84" y2="80" stroke={isMuted ? "#EDEAE4" : "#1C1917"} strokeWidth="3" strokeLinecap="round" />
            </svg>
          </div>
        </div>

        {/* ── ASYMMETRIC MAIN GRID: EQUAL HEIGHT STRETCH (items-stretch) ────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          {/* LEFT: Hero Upload & Input (~62% width) */}
          <div className={result ? "lg:col-span-5 print:hidden" : "lg:col-span-7 print:hidden"}>
            <div className={`border rounded-2xl p-7 shadow-xs flex flex-col justify-between h-full space-y-5 transition-colors ${
              isMuted
                ? "bg-[#202024] border-[#2E2E34]"
                : "bg-white border-[#E7E2D9]"
            }`}>
              <div className="flex-1 flex flex-col">
                {/* Simple Underline Tab Bar */}
                <div className={`flex border-b gap-6 mb-5 ${isMuted ? "border-[#2E2E34]" : "border-[#E7E2D9]"}`}>
                  <button
                    onClick={() => { setInputMode("image"); setResult(null); }}
                    className={`pb-3 text-sm transition cursor-pointer flex items-center gap-2 ${
                      inputMode === "image"
                        ? `border-b-2 border-[#E5484D] font-semibold ${isMuted ? "text-[#EDEAE4]" : "text-[#1C1917]"}`
                        : `${isMuted ? "text-[#A19E95] hover:text-[#EDEAE4]" : "text-[#57534E] hover:text-[#1C1917]"}`
                    }`}
                  >
                    <ImageIcon className="w-4 h-4" />
                    {t.input.tabImage}
                  </button>
                  <button
                    onClick={() => { setInputMode("text"); setResult(null); }}
                    className={`pb-3 text-sm transition cursor-pointer flex items-center gap-2 ${
                      inputMode === "text"
                        ? `border-b-2 border-[#E5484D] font-semibold ${isMuted ? "text-[#EDEAE4]" : "text-[#1C1917]"}`
                        : `${isMuted ? "text-[#A19E95] hover:text-[#EDEAE4]" : "text-[#57534E] hover:text-[#1C1917]"}`
                    }`}
                  >
                    <Link2 className="w-4 h-4" />
                    {t.input.tabText}
                  </button>
                </div>

                {/* Dropzone Fills Full Height (flex-1) */}
                {inputMode === "image" ? (
                  <div
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setIsDragging(false);
                      e.dataTransfer.files[0] && handleFile(e.dataTransfer.files[0]);
                    }}
                    onClick={() => fileInputRef.current?.click()}
                    className={`flex-1 min-h-[250px] border rounded-xl p-8 text-center cursor-pointer flex flex-col items-center justify-center transition ${
                      isDragging
                        ? "border-[#E5484D] bg-[#E5484D]/10 ring-1 ring-[#E5484D]/30"
                        : isMuted
                        ? "border-[#383840] bg-[#1A1A1D] hover:border-[#52525B] hover:bg-[#1E1E22]"
                        : "border-[#D6D0C4] bg-[#FAF8F5]/60 hover:border-[#1C1917] hover:bg-[#FAF8F5]"
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                    />

                    {previewUrl ? (
                      <div className={`relative max-h-60 overflow-hidden rounded-lg border ${isMuted ? "border-[#2E2E34]" : "border-[#E7E2D9]"}`}>
                        <img src={previewUrl} alt="Preview" className="max-h-60 object-contain" />
                        {loading && (
                          <div className={`absolute inset-0 backdrop-blur-xs flex items-center justify-center ${isMuted ? "bg-[#161618]/80" : "bg-white/80"}`}>
                            <RefreshCw className="w-6 h-6 text-[#E5484D] animate-spin" />
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="space-y-2.5">
                        <UploadCloud className="w-8 h-8 mx-auto stroke-[1.75]" />
                        <div className="text-sm font-semibold">
                          {isDragging ? t.input.dropzoneDragActive : t.input.dropzoneTitle}
                        </div>
                        <p className={`text-[14px] max-w-sm leading-normal ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                          {t.input.dropzoneSubtitle}
                        </p>
                        {/* Neutral Gray Paste Hint (Not red alert) */}
                        <p className={`text-xs pt-1 font-normal ${isMuted ? "text-[#71717A]" : "text-[#78716C]"}`}>
                          {t.input.pasteHint}
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col">
                    <textarea
                      rows={8}
                      value={textInput}
                      onChange={(e) => setTextInput(e.target.value)}
                      placeholder={t.input.pastePlaceholder}
                      className={`flex-1 min-h-[250px] w-full border rounded-xl p-4 text-[15px] placeholder:text-[#71717A] focus:outline-none transition leading-relaxed ${
                        isMuted
                          ? "bg-[#1A1A1D] border-[#383840] text-[#EDEAE4] focus:border-[#EDEAE4] focus:bg-[#202024]"
                          : "bg-[#FAF8F5]/60 border-[#D6D0C4] text-[#1C1917] focus:border-[#1C1917] focus:bg-white"
                      }`}
                    />
                  </div>
                )}
              </div>

              {/* Pinned Primary CTA Button at Bottom */}
              <div className="space-y-3 pt-2">
                <button
                  onClick={runAnalysis}
                  disabled={!canAnalyze || loading}
                  className={`w-full py-3.5 px-5 font-medium text-sm rounded-xl transition flex items-center justify-center gap-2 ${
                    canAnalyze && !loading
                      ? "bg-[#E5484D] hover:bg-[#D93D42] text-white shadow-xs cursor-pointer active:scale-[0.99]"
                      : "bg-[#E5484D]/30 text-white/50 cursor-not-allowed"
                  }`}
                >
                  <FileSearch className="w-4 h-4" />
                  {t.input.btnAnalyze}
                </button>

                {loading && (
                  <div className={`p-4 border rounded-xl text-xs flex items-center gap-3 ${
                    isMuted
                      ? "bg-[#1A1A1D] border-[#2E2E34] text-[#A19E95]"
                      : "bg-[#F5F2EB] border-[#E7E2D9] text-[#57534E]"
                  }`}>
                    <RefreshCw className="w-4 h-4 animate-spin text-[#E5484D]" />
                    <div>
                      <div className="font-semibold text-inherit">{t.input.analyzing}</div>
                      <div className="text-xs opacity-80 mt-0.5">{t.input.analyzingSubtitle}</div>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="p-4 bg-[#FEF2F2] border border-[#FEE2E2] rounded-xl text-xs text-[#991B1B] flex items-start gap-2.5">
                    <AlertCircle className="w-4 h-4 text-[#E5484D] shrink-0 mt-0.5" />
                    <div className="leading-relaxed">{error}</div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* RIGHT: Real-world cases (Height-matched to Left column before results) */}
          {!result && (
            <div className="lg:col-span-5 print:hidden">
              <div className={`p-7 rounded-2xl border flex flex-col justify-between h-full shadow-xs transition-colors ${
                isMuted
                  ? "bg-[#202024] border-[#2E2E34]"
                  : "bg-white border-[#E7E2D9]"
              }`}>
                <div>
                  <div className={`flex items-center justify-between mb-4 pb-3 border-b ${isMuted ? "border-[#2E2E34]" : "border-[#E7E2D9]"}`}>
                    <h2 className="text-sm font-semibold tracking-tight">
                      {t.hero.realCases}
                    </h2>
                    <span className={`text-xs ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                      {t.hero.sampleHelper}
                    </span>
                  </div>

                  <div className={`divide-y ${isMuted ? "divide-[#2E2E34]" : "divide-[#EFECE6]"}`}>
                    {sampleCases.map((s, idx) => (
                      <div
                        key={idx}
                        onClick={() => handleSelectCase(s)}
                        className="py-4 first:pt-1 last:pb-1 cursor-pointer group"
                      >
                        <div className="flex items-start justify-between gap-3 mb-1">
                          <div className="text-[14px] font-semibold group-hover:text-[#E5484D] transition leading-snug">
                            {s.title}
                          </div>
                          {/* Dark gray text label with a small coral dot before it */}
                          <span className={`inline-flex items-center gap-1.5 text-xs font-medium shrink-0 ${
                            isMuted ? "text-[#A19E95]" : "text-[#57534E]"
                          }`}>
                            <span className="w-1.5 h-1.5 rounded-full bg-[#E5484D] shrink-0" />
                            {s.tag}
                          </span>
                        </div>
                        <p className={`text-[13px] line-clamp-2 leading-relaxed ${
                          isMuted ? "text-[#A19E95]" : "text-[#57534E]"
                        }`}>
                          {s.summary}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Grounded Disclaimer */}
                <div className={`pt-4 border-t text-xs ${
                  isMuted ? "border-[#2E2E34] text-[#71717A]" : "border-[#E7E2D9] text-[#78716C]"
                }`}>
                  {t.hero.scenarioDisclaimer}
                </div>
              </div>
            </div>
          )}

          {/* ── RESULT REPORT DISPLAY ───────────────────────────────────────────── */}
          {result && (
            <div ref={reportRef} className="lg:col-span-7 space-y-6 print:w-full print:col-span-12">
              {/* Report Header Bar */}
              <div className={`flex items-center justify-between p-4 border rounded-xl shadow-xs print:hidden flex-wrap gap-2 ${
                isMuted
                  ? "bg-[#202024] border-[#2E2E34]"
                  : "bg-white border-[#E7E2D9]"
              }`}>
                <div className={`text-xs ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                  {lang === "vi" ? "Mã giám định: " : "Case ID: "}
                  <span className="font-semibold text-inherit">{caseId}</span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleExportPdf}
                    disabled={exportingPdf}
                    className={`text-xs px-3.5 py-1.5 rounded-lg border flex items-center gap-1.5 cursor-pointer font-medium transition disabled:opacity-50 ${
                      isMuted
                        ? "bg-[#2A2A30] hover:bg-[#33333A] text-[#EDEAE4] border-[#383840]"
                        : "bg-[#F5F2EB] hover:bg-[#EAE6DD] text-[#1C1917] border-[#E7E2D9]"
                    }`}
                  >
                    <FileDown className="w-3.5 h-3.5 opacity-70" />
                    {exportingPdf ? (lang === "vi" ? "Đang xuất..." : "Exporting...") : t.family.downloadPdf}
                  </button>
                  <button
                    onClick={() => window.print()}
                    className={`text-xs px-3.5 py-1.5 rounded-lg border flex items-center gap-1.5 cursor-pointer font-medium transition ${
                      isMuted
                        ? "bg-[#2A2A30] hover:bg-[#33333A] text-[#EDEAE4] border-[#383840]"
                        : "bg-[#F5F2EB] hover:bg-[#EAE6DD] text-[#1C1917] border-[#E7E2D9]"
                    }`}
                  >
                    <Printer className="w-3.5 h-3.5 opacity-70" />
                    {t.family.printReport}
                  </button>
                </div>
              </div>

              {/* ── VERDICT CARD ────────────────────────────────────────────────────── */}
              {(() => {
                const s = result.risk_score;
                const isScam = s >= 70;
                const isSuspicious = s >= 40 && s < 70;

                return (
                  <div className={`p-6 rounded-2xl border space-y-4 shadow-xs ${
                    isMuted
                      ? isScam
                        ? "bg-[#202024] border-[#7F1D1D]"
                        : isSuspicious
                        ? "bg-[#202024] border-[#78350F]"
                        : "bg-[#202024] border-[#064E3B]"
                      : isScam
                      ? "bg-white border-[#FCA5A5]"
                      : isSuspicious
                      ? "bg-white border-[#FDE68A]"
                      : "bg-white border-[#A7F3D0]"
                  }`}>
                    <div className="flex items-start justify-between flex-wrap gap-3">
                      <div>
                        <div className="flex items-center gap-2.5 mb-1.5">
                          <span className={`w-3 h-3 rounded-full ${
                            isScam ? "bg-[#E5484D]" : isSuspicious ? "bg-[#F59E0B]" : "bg-[#10B981]"
                          }`} />
                          <span className={`text-xl font-semibold tracking-tight ${
                            isScam ? "text-[#E5484D]" : isSuspicious ? "text-[#D97706]" : "text-[#059669]"
                          }`}>
                            {s >= 80 ? t.verdict.scamDetected : s >= 60 ? t.verdict.highRisk : s >= 31 ? t.verdict.suspicious : t.verdict.safe}
                          </span>
                        </div>
                        <div className={`text-sm ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                          {t.verdict.category}: <span className="font-semibold text-inherit">{result.scam_type}</span>
                        </div>
                      </div>

                      {/* Score pill */}
                      <div className="text-right">
                        <div className="text-3xl font-semibold tracking-tight">
                          {s} <span className={`text-sm font-normal ${isMuted ? "text-[#71717A]" : "text-[#78716C]"}`}>/ 100</span>
                        </div>
                        <div className={`text-xs mt-0.5 ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                          {t.verdict.riskScore}
                        </div>
                      </div>
                    </div>

                    {/* Action Advice Box */}
                    <div className={`p-4 rounded-xl text-sm leading-relaxed border ${
                      isScam
                        ? isMuted ? "bg-[#7F1D1D]/20 text-[#FCA5A5] border-[#7F1D1D]/50" : "bg-[#FEF2F2] text-[#991B1B] border-[#FEE2E2]"
                        : isSuspicious
                        ? isMuted ? "bg-[#78350F]/20 text-[#FCD34D] border-[#78350F]/50" : "bg-[#FFFBEB] text-[#92400E] border-[#FEF3C7]"
                        : isMuted ? "bg-[#064E3B]/20 text-[#6EE7B7] border-[#064E3B]/50" : "bg-[#F0FDF4] text-[#166534] border-[#DCFCE7]"
                    }`}>
                      <span className="font-semibold">{lang === "vi" ? "Khuyến nghị an toàn: " : "Safety advice: "}</span>
                      {s >= 80 ? t.verdict.actionScam : s >= 60 ? t.verdict.actionHigh : s >= 31 ? t.verdict.actionSuspicious : t.verdict.actionSafe}
                    </div>
                  </div>
                );
              })()}

              {/* ScamGuard Proprietary Forensic ML Telemetry Dashboard */}
              {result.ml_classifier?.model_ready && (
                <div className={`p-5 border rounded-2xl space-y-4 shadow-sm ${
                  isMuted ? "bg-[#18181B] border-[#27272A]" : "bg-gradient-to-b from-[#FAF8F5] to-white border-[#E7E2D9]"
                }`}>
                  {/* Dashboard Header */}
                  <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-inherit">
                    <div className="flex items-center gap-2">
                      <span className="flex h-2.5 w-2.5 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                      </span>
                      <h4 className="font-semibold text-sm tracking-tight">
                        {lang === "vi" ? "ScamGuard Forensic ML Engine (Edge Tier)" : "ScamGuard Forensic ML Engine (Edge Tier)"}
                      </h4>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-medium ${
                        isMuted ? "bg-[#27272A] text-[#A1A1AA]" : "bg-[#ECE7DE] text-[#57534E]"
                      }`}>
                        {lang === "vi" ? "11,065 Mẫu Chuẩn Hóa • 5-Fold CV" : "11,065 Normalized Samples • 5-Fold CV"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
                        &lt; 4ms CPU
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        result.ml_classifier.ml_risk_score >= 80
                          ? "bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20"
                          : result.ml_classifier.ml_risk_score >= 30
                          ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                          : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                      }`}>
                        {result.ml_classifier.action || result.ml_classifier.ml_label}
                      </span>
                    </div>
                  </div>

                  {/* Dual-Branch Feature Telemetry (Text vs URL) */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    {/* Branch 1: Text Screening */}
                    <div className={`p-3.5 rounded-xl border space-y-2 ${
                      isMuted ? "bg-[#202024] border-[#2E2E34]" : "bg-white border-[#E7E2D9]"
                    }`}>
                      <div className="flex items-center justify-between font-medium">
                        <span className="flex items-center gap-1.5">
                          <span className="text-base">📝</span>
                          <span>{lang === "vi" ? "Nhánh Nội Dung Text" : "Text Branch"} (p_text)</span>
                        </span>
                        <span className="font-mono font-semibold text-sm">
                          {result.ml_classifier.text_score != null ? `${result.ml_classifier.text_score}%` : "N/A"}
                        </span>
                      </div>
                      <div className="w-full bg-black/10 dark:bg-white/10 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            (result.ml_classifier.text_score ?? 0) >= 50 ? "bg-red-500" : "bg-emerald-500"
                          }`}
                          style={{ width: `${Math.min(100, Math.max(0, result.ml_classifier.text_score ?? 0))}%` }}
                        />
                      </div>
                      <div className={`text-[11px] space-y-1 ${isMuted ? "text-[#A1A1AA]" : "text-[#78716C]"}`}>
                        <div className="truncate">
                          <span className="font-semibold">{lang === "vi" ? "Chuẩn hóa NFKD:" : "Normalized text:"}</span>{" "}
                          <span className="font-mono">{result.ml_classifier.normalized_text || "(Trống)"}</span>
                        </div>
                        {result.ml_classifier.text_tokens && result.ml_classifier.text_tokens.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {result.ml_classifier.text_tokens.map((tok, i) => (
                              <span key={i} className="px-1.5 py-0.2 bg-black/5 dark:bg-white/5 rounded font-mono text-[10px]">
                                {tok}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Branch 2: URL Phishing */}
                    <div className={`p-3.5 rounded-xl border space-y-2 ${
                      isMuted ? "bg-[#202024] border-[#2E2E34]" : "bg-white border-[#E7E2D9]"
                    }`}>
                      <div className="flex items-center justify-between font-medium">
                        <span className="flex items-center gap-1.5">
                          <span className="text-base">🔗</span>
                          <span>{lang === "vi" ? "Nhánh Đường Dẫn URL" : "URL Branch"} (p_url)</span>
                        </span>
                        <span className="font-mono font-semibold text-sm">
                          {result.ml_classifier.url_score != null ? `${result.ml_classifier.url_score}%` : "(Không có URL)"}
                        </span>
                      </div>
                      <div className="w-full bg-black/10 dark:bg-white/10 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            (result.ml_classifier.url_score ?? 0) >= 50 ? "bg-red-500" : "bg-emerald-500"
                          }`}
                          style={{ width: `${Math.min(100, Math.max(0, result.ml_classifier.url_score ?? 0))}%` }}
                        />
                      </div>
                      <div className={`text-[11px] space-y-1 ${isMuted ? "text-[#A1A1AA]" : "text-[#78716C]"}`}>
                        <div className="truncate">
                          <span className="font-semibold">{lang === "vi" ? "URL trích xuất:" : "Extracted URL:"}</span>{" "}
                          <span className="font-mono">{result.ml_classifier.extracted_url || "(Không phát hiện)"}</span>
                        </div>
                        {result.ml_classifier.url_signals && result.ml_classifier.url_signals.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {result.ml_classifier.url_signals.map((sig, i) => (
                              <span key={i} className="px-1.5 py-0.2 bg-amber-500/10 text-amber-700 dark:text-amber-300 rounded font-mono text-[10px]">
                                {sig}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Stacking Meta-Learner Mathematical Formulation */}
                  <div className={`p-3.5 rounded-xl border text-xs font-mono space-y-1.5 ${
                    isMuted ? "bg-[#1E1E22] border-[#2E2E34] text-[#E4E4E7]" : "bg-[#F7F4EE] border-[#E2DDD3] text-[#292524]"
                  }`}>
                    <div className="flex items-center justify-between text-[11px] font-sans font-medium text-[#78716C] dark:text-[#A1A1AA]">
                      <span>{lang === "vi" ? "Công thức toán học gộp tri thức (Stacking Meta-Learner):" : "Stacking Meta-Learner Formulation:"}</span>
                      <span>Uncertainty U(x): {result.ml_classifier.uncertainty ?? "0.0"}</span>
                    </div>
                    <div className="p-2 rounded bg-black/5 dark:bg-black/30 text-[11px] leading-relaxed break-all font-semibold">
                      s_fused = 100 · σ(-4.470 + 5.243·p_text + 4.628·p_url + 1.714·(p_text·p_url))
                    </div>
                    <div className="text-[11px] font-sans text-[#78716C] dark:text-[#A1A1AA] pt-0.5 leading-normal">
                      {lang === "vi"
                        ? "Hệ số tương tác β₃ = +1.714 kích hoạt hiệu ứng hiệp đồng đa phương thức (Synergistic Compounding) khi cả Text và Link cùng mang dấu hiệu bất thường, giải quyết triệt để lỗi báo nhầm của Max-Fusion."
                        : "Interaction coefficient β₃ = +1.714 compounds joint risk when both text and URL exhibit anomalies, resolving max-fusion false positive inflation."}
                    </div>
                  </div>
                </div>
              )}

              {/* Web Domain Intelligence */}
              {result.web_intelligence?.detected && (
                <div className={`p-5 border rounded-xl text-xs space-y-3 ${
                  isMuted ? "bg-[#202024] border-[#2E2E34]" : "bg-white border-[#E7E2D9]"
                }`}>
                  <div className={`flex items-center justify-between border-b pb-3 flex-wrap gap-2 ${
                    isMuted ? "border-[#2E2E34]" : "border-[#E7E2D9]"
                  }`}>
                    <div>
                      <div className={`text-xs ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>{t.webIntel.badgeTitle}</div>
                      <div className="font-medium text-sm mt-0.5">
                        {result.web_intelligence.domain || result.web_intelligence.url}
                      </div>
                    </div>
                    <span className={`text-xs font-medium ${
                      result.web_intelligence.domain_match === "mismatch"
                        ? "text-[#E5484D]"
                        : "text-[#10B981]"
                    }`}>
                      {result.web_intelligence.domain_match === "mismatch"
                        ? t.webIntel.fraudulentDomain
                        : t.webIntel.legitimateDomain}
                    </span>
                  </div>

                  {result.web_intelligence.brand_detected && (
                    <div className={isMuted ? "text-[#A19E95]" : "text-[#57534E]"}>
                      {t.webIntel.targetBrand} <strong className="text-inherit">{result.web_intelligence.brand_detected}</strong>
                    </div>
                  )}

                  {result.web_intelligence.suspicious_indicators?.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <div className="text-xs font-medium text-[#E5484D]">{t.webIntel.suspiciousBehaviors}</div>
                      <ul className={`list-disc list-inside space-y-1 text-xs ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                        {result.web_intelligence.suspicious_indicators.map((ind, idx) => (
                          <li key={idx}>{ind}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {result.web_intelligence.external_evidence?.length > 0 && (
                    <div className={`pt-2 border-t ${isMuted ? "border-[#2E2E34]" : "border-[#E7E2D9]"}`}>
                      <div className={`text-xs font-medium mb-2 ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>{t.webIntel.threatEvidence}</div>
                      <div className="space-y-1.5">
                        {result.web_intelligence.external_evidence.map((item, idx) => {
                          const isObj = typeof item === "object" && item !== null;
                          const title = isObj ? item.title : String(item);
                          const sourceUrl = isObj ? item.source_url : `https://www.google.com/search?q=${encodeURIComponent(String(item))}`;

                          return (
                            <a
                              key={idx}
                              href={sourceUrl}
                              target="_blank"
                              rel="noreferrer"
                              className={`text-xs flex items-center justify-between p-2.5 rounded-lg border transition ${
                                isMuted
                                  ? "bg-[#1A1A1D] hover:bg-[#2A2A30] border-[#383840] text-[#EDEAE4]"
                                  : "bg-[#FAF8F5] hover:bg-[#F5F2EB] border-[#E7E2D9] text-[#1C1917]"
                              }`}
                            >
                              <span className="truncate">{title}</span>
                              <ExternalLink className="w-3.5 h-3.5 opacity-60 shrink-0 ml-2" />
                            </a>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── RESULT TABS (Underline Style) ─────────────────────────────────── */}
              <div className={`flex border-b gap-6 print:hidden overflow-x-auto pb-0 ${
                isMuted ? "border-[#2E2E34]" : "border-[#E7E2D9]"
              }`}>
                {(["overview", "psychology", "family", "roleplay"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`pb-3 text-xs tracking-tight transition cursor-pointer whitespace-nowrap ${
                      activeTab === tab
                        ? `border-b-2 border-[#E5484D] font-semibold ${isMuted ? "text-[#EDEAE4]" : "text-[#1C1917]"}`
                        : `${isMuted ? "text-[#A19E95] hover:text-[#EDEAE4]" : "text-[#57534E] hover:text-[#1C1917]"}`
                    }`}
                  >
                    {tab === "overview" && t.tabs.overview}
                    {tab === "psychology" && t.tabs.psychology}
                    {tab === "family" && t.tabs.family}
                    {tab === "roleplay" && t.tabs.roleplay}
                  </button>
                ))}
              </div>

              {/* Tab 1: Overview */}
              {activeTab === "overview" && (
                <div className="space-y-4">
                  {/* Executive Summary */}
                  <div className={`p-6 border rounded-2xl space-y-2 shadow-xs ${
                    isMuted ? "bg-[#202024] border-[#2E2E34]" : "bg-white border-[#E7E2D9]"
                  }`}>
                    <div className={`text-xs font-semibold ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>{t.overview.executiveSummary}</div>
                    <p className="text-[15px] leading-relaxed">{result.executive_summary}</p>
                  </div>

                  {/* Evidence Comparator */}
                  {result.red_flags?.length > 0 && (
                    <div className={`p-6 border rounded-2xl space-y-4 shadow-xs ${
                      isMuted ? "bg-[#202024] border-[#2E2E34]" : "bg-white border-[#E7E2D9]"
                    }`}>
                      <div className={`text-xs font-semibold ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>{t.overview.evidenceComparator}</div>
                      <div className="space-y-3">
                        {result.red_flags.map((f, i) => (
                          <div key={i} className={`p-4 rounded-xl border text-xs space-y-2.5 ${
                            isMuted ? "bg-[#1A1A1D] border-[#2E2E34]" : "bg-[#FAF8F5] border-[#E7E2D9]"
                          }`}>
                            <div className={`p-3 rounded-lg border ${
                              isMuted ? "bg-[#7F1D1D]/20 text-[#FCA5A5] border-[#7F1D1D]/40" : "bg-[#FEF2F2] text-[#991B1B] border-[#FEE2E2]"
                            }`}>
                              <span className="font-semibold">{t.overview.detectedInData}: </span>
                              <span>{f.evidence}</span>
                            </div>

                            <div className={`p-3 rounded-lg border flex items-center justify-between gap-2 flex-wrap ${
                              isMuted ? "bg-[#064E3B]/20 text-[#6EE7B7] border-[#064E3B]/40" : "bg-[#F0FDF4] text-[#166534] border-[#DCFCE7]"
                            }`}>
                              <div>
                                <span className="font-semibold">{t.overview.officialBenchmark}: </span>
                                <span>{f.official_fact || f.explanation}</span>
                              </div>
                              {f.official_link && (
                                <a
                                  href={f.official_link}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-xs text-[#10B981] hover:underline flex items-center gap-1 shrink-0 font-medium"
                                >
                                  <span>{t.webIntel.source}</span>
                                  <ExternalLink className="w-3.5 h-3.5" />
                                </a>
                              )}
                            </div>

                            <p className={`text-xs leading-relaxed pt-1 ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                              {f.explanation}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Immediate Emergency Actions */}
                  {result.urgent_actions?.length > 0 && (
                    <div className={`p-6 border rounded-2xl space-y-3 shadow-xs ${
                      isMuted ? "bg-[#202024] border-[#2E2E34]" : "bg-white border-[#E7E2D9]"
                    }`}>
                      <div className="text-xs font-semibold">{t.overview.emergencyActions}</div>
                      <div className="space-y-2">
                        {result.urgent_actions.map((act, i) => (
                          <div key={i} className={`text-xs flex items-start gap-2.5 ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                            <span className={`w-5 h-5 rounded-full border flex items-center justify-center shrink-0 text-xs font-semibold mt-0.5 ${
                              isMuted ? "bg-[#1A1A1D] border-[#383840] text-[#EDEAE4]" : "bg-[#FAF8F5] border-[#D6D0C4] text-[#1C1917]"
                            }`}>
                              {i + 1}
                            </span>
                            <span className="leading-relaxed">{act}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Psychology */}
              {activeTab === "psychology" && (
                <div className={`p-6 border rounded-2xl space-y-4 shadow-xs ${
                  isMuted ? "bg-[#202024] border-[#2E2E34]" : "bg-white border-[#E7E2D9]"
                }`}>
                  <div className={`text-xs font-semibold ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>{t.psychology.title}</div>
                  <div className="space-y-3">
                    {result.psychological_tricks.map((tr, i) => (
                      <div key={i} className={`p-4 rounded-xl border space-y-1.5 text-xs ${
                        isMuted ? "bg-[#1A1A1D] border-[#2E2E34]" : "bg-[#FAF8F5] border-[#E7E2D9]"
                      }`}>
                        <div className="flex justify-between items-center flex-wrap gap-2">
                          <span className="font-semibold text-sm">{tr.tactic}</span>
                          <span className="text-xs text-[#E5484D] font-medium">
                            {t.psychology.targetEmotion} {tr.target_emotion}
                          </span>
                        </div>
                        <p className={`leading-relaxed text-[13px] ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>{tr.analysis}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tab 3: Family Share */}
              {activeTab === "family" && (
                <div className={`p-6 border rounded-2xl space-y-4 shadow-xs ${
                  isMuted ? "bg-[#202024] border-[#2E2E34]" : "bg-white border-[#E7E2D9]"
                }`}>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold">{t.family.title}</div>
                      <div className={`text-xs mt-0.5 ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>{t.family.keyWarning}</div>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap">
                      <button
                        onClick={handleNativeShare}
                        className="text-xs bg-[#E5484D] hover:bg-[#D93D42] text-white px-3.5 py-2 rounded-lg flex items-center gap-1.5 cursor-pointer font-medium transition"
                      >
                        <Share2 className="w-3.5 h-3.5" />
                        {lang === "vi" ? "Gửi cảnh báo" : "Share alert"}
                      </button>

                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(result.family_alert_card.shareable_text);
                          setCopied(true);
                          setTimeout(() => setCopied(false), 2000);
                        }}
                        className={`text-xs px-3.5 py-2 rounded-lg border flex items-center gap-1.5 cursor-pointer font-medium transition ${
                          isMuted
                            ? "bg-[#2A2A30] hover:bg-[#33333A] text-[#EDEAE4] border-[#383840]"
                            : "bg-[#FAF8F5] hover:bg-[#EAE6DD] text-[#1C1917] border-[#E7E2D9]"
                        }`}
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-[#10B981]" /> : <Copy className="w-3.5 h-3.5" />}
                        {copied ? t.family.copied : t.family.copyBtn}
                      </button>
                    </div>
                  </div>

                  <div className={`p-5 rounded-xl border text-[14px] leading-relaxed whitespace-pre-wrap ${
                    isMuted ? "bg-[#1A1A1D] border-[#2E2E34]" : "bg-[#FAF8F5] border-[#E7E2D9]"
                  }`}>
                    {result.family_alert_card.shareable_text}
                  </div>
                </div>
              )}

              {/* Tab 4: Roleplay Practice */}
              {activeTab === "roleplay" && (
                <div className={`p-6 border rounded-2xl space-y-4 shadow-xs ${
                  isMuted ? "bg-[#202024] border-[#2E2E34]" : "bg-white border-[#E7E2D9]"
                }`}>
                  <div className={`flex justify-between items-center border-b pb-3 ${
                    isMuted ? "border-[#2E2E34]" : "border-[#E7E2D9]"
                  }`}>
                    <div>
                      <div className="text-sm font-semibold">{t.roleplay.title}</div>
                      <p className={`text-xs ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>{t.roleplay.subtitle}</p>
                    </div>
                    <button
                      onClick={() => setRoleplayMessages(getInitialRoleplayMessages(result))}
                      className={`text-xs flex items-center gap-1 cursor-pointer ${
                        isMuted ? "text-[#A19E95] hover:text-[#EDEAE4]" : "text-[#57534E] hover:text-[#1C1917]"
                      }`}
                    >
                      <RefreshCw className="w-3 h-3" /> {t.roleplay.resetChat}
                    </button>
                  </div>

                  {/* Clean Messaging Interface */}
                  <div className={`p-5 rounded-xl border space-y-3.5 max-h-80 overflow-y-auto text-xs ${
                    isMuted ? "bg-[#1A1A1D] border-[#2E2E34]" : "bg-[#FAF8F5] border-[#E7E2D9]"
                  }`}>
                    {activeRoleplayList.map((msg) => {
                      if (msg.sender === "scammer") {
                        return (
                          <div key={msg.id} className="max-w-[85%]">
                            <div className="text-[11px] text-[#A8A29E] mb-1 font-medium">
                              {lang === "vi" ? "Kẻ lừa đảo" : "Scammer"}
                            </div>
                            <div className={`p-3.5 rounded-2xl rounded-tl-xs border leading-relaxed text-[13px] ${
                              isMuted
                                ? "bg-[#7F1D1D]/20 text-[#FCA5A5] border-[#7F1D1D]/50"
                                : "bg-[#FEF2F2] border-[#FEE2E2] text-[#991B1B]"
                            }`}>
                              {msg.text}
                            </div>
                          </div>
                        );
                      }
                      if (msg.sender === "user") {
                        return (
                          <div key={msg.id} className="max-w-[85%] ml-auto text-right">
                            <div className="text-[11px] text-[#A8A29E] mb-1 font-medium">
                              {lang === "vi" ? "Bạn" : "You"}
                            </div>
                            <div className={`p-3.5 rounded-2xl rounded-tr-xs text-left leading-relaxed text-[13px] ${
                              isMuted
                                ? "bg-[#2A2A30] text-[#EDEAE4] border border-[#383840]"
                                : "bg-[#1C1917] text-white"
                            }`}>
                              {msg.text}
                            </div>
                          </div>
                        );
                      }
                      if (msg.sender === "eval") {
                        return (
                          <div
                            key={msg.id}
                            className={`p-3.5 rounded-xl text-xs leading-relaxed border ${
                              msg.evalStatus === "danger"
                                ? isMuted ? "bg-[#7F1D1D]/20 text-[#FCA5A5] border-[#7F1D1D]/50" : "bg-[#FEF2F2] text-[#991B1B] border-[#FEE2E2]"
                                : isMuted ? "bg-[#064E3B]/20 text-[#6EE7B7] border-[#064E3B]/50" : "bg-[#F0FDF4] text-[#166534] border-[#DCFCE7]"
                            }`}
                          >
                            <span className="font-semibold">{lang === "vi" ? "Đánh giá: " : "Feedback: "}</span>
                            {msg.text}
                          </div>
                        );
                      }
                      return null;
                    })}
                  </div>

                  {/* Quick responses */}
                  <div className="space-y-2">
                    <div className={`text-xs font-medium ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                      {lang === "vi" ? "Chọn nhanh phản hồi mẫu:" : "Quick responses:"}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {quickRoleplayResponses.map((qr, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSendRoleplay(qr.text, qr.isRisky)}
                          className={`text-xs px-3.5 py-2 rounded-lg border text-left cursor-pointer transition ${
                            qr.isRisky
                              ? isMuted
                                ? "bg-[#7F1D1D]/20 border-[#7F1D1D]/40 text-[#FCA5A5] hover:bg-[#7F1D1D]/30"
                                : "bg-[#FEF2F2] border-[#FEE2E2] text-[#991B1B] hover:bg-[#FEE2E2]"
                              : isMuted
                              ? "bg-[#1A1A1D] border-[#383840] text-[#EDEAE4] hover:bg-[#2A2A30]"
                              : "bg-[#FAF8F5] border-[#E7E2D9] text-[#1C1917] hover:bg-[#EAE6DD]"
                          }`}
                        >
                          {qr.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Input Form */}
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleSendRoleplay(roleplayInput);
                    }}
                    className="flex gap-2"
                  >
                    <input
                      type="text"
                      value={roleplayInput}
                      onChange={(e) => setRoleplayInput(e.target.value)}
                      placeholder={t.roleplay.placeholder}
                      className={`flex-1 border rounded-xl px-4 py-2.5 text-xs focus:outline-none transition ${
                        isMuted
                          ? "bg-[#1A1A1D] border-[#383840] text-[#EDEAE4] focus:border-[#EDEAE4]"
                          : "bg-[#FAF8F5] border-[#D6D0C4] text-[#1C1917] focus:border-[#1C1917] focus:bg-white"
                      }`}
                    />
                    <button
                      type="submit"
                      className="px-5 py-2.5 bg-[#E5484D] hover:bg-[#D93D42] text-white text-xs font-medium rounded-xl flex items-center gap-1.5 cursor-pointer transition"
                    >
                      <Send className="w-3.5 h-3.5" />
                      {t.roleplay.send}
                    </button>
                  </form>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── RECENT ALERTS (No card container, sits directly on background with hairline dividers) ── */}
        <section className="mt-20 print:hidden">
          <div className={`mb-6 pb-3 border-b flex items-center justify-between ${
            isMuted ? "border-[#2E2E34]" : "border-[#E7E2D9]"
          }`}>
            <div>
              <h2 className="text-lg font-semibold tracking-tight">
                {t.community.title}
              </h2>
              <p className={`text-[14px] mt-0.5 ${isMuted ? "text-[#A19E95]" : "text-[#57534E]"}`}>
                {t.community.subtitle}
              </p>
            </div>
          </div>

          <div className={`divide-y ${isMuted ? "divide-[#2E2E34]" : "divide-[#E7E2D9]"}`}>
            {communityFeed.map((item) => (
              <article
                key={item.id}
                onClick={() => handleSelectFeedItem(item)}
                className={`py-5 cursor-pointer group flex items-start justify-between gap-6 px-2 rounded-lg transition ${
                  isMuted ? "hover:bg-[#202024]/60" : "hover:bg-[#F5F2EB]/40"
                }`}
              >
                <div className="space-y-1.5 max-w-3xl">
                  <div className="flex items-center gap-3">
                    <h3 className="text-[15px] font-semibold group-hover:text-[#E5484D] transition leading-snug">
                      {item.title}
                    </h3>
                    {/* Clean plain text label with a subtle coral dot */}
                    <span className={`inline-flex items-center gap-1.5 text-xs font-medium shrink-0 ${
                      isMuted ? "text-[#A19E95]" : "text-[#57534E]"
                    }`}>
                      <span className="w-1.5 h-1.5 rounded-full bg-[#E5484D] shrink-0" />
                      {item.tag}
                    </span>
                  </div>
                  <p className={`text-[14px] line-clamp-2 leading-relaxed ${
                    isMuted ? "text-[#A19E95]" : "text-[#57534E]"
                  }`}>
                    {item.summary}
                  </p>
                </div>

                <div className={`flex items-center gap-1.5 text-xs group-hover:text-[#E5484D] transition shrink-0 pt-1 ${
                  isMuted ? "text-[#A19E95]" : "text-[#57534E]"
                }`}>
                  <span className="hidden sm:inline font-medium">{t.community.viewAnalysis}</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition" />
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
