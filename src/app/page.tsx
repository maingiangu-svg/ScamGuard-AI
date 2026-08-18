"use client";

import React, { useState, useRef } from "react";
import {
  ShieldAlert, AlertTriangle, UploadCloud, FileSearch, Brain, Forward,
  Copy, Check, Zap, Lock, RefreshCw, Eye, Activity, Fingerprint,
  Sparkles, ChevronRight, MessageSquare, Printer, Link2, Image as ImageIcon,
  Users, Flame, Clock, ArrowUpRight, Share2, Send, Gamepad2, Bot, User
} from "lucide-react";

interface ForensicResult {
  scam_detected: boolean;
  risk_score: number;
  threat_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "SAFE";
  scam_type: string;
  executive_summary: string;
  red_flags: { evidence: string; explanation: string }[];
  psychological_tricks: { tactic: string; target_emotion: string; analysis: string }[];
  next_move_prediction: string;
  urgent_actions: string[];
  family_alert_card: { headline: string; key_warning: string; shareable_text: string };
}

interface CommunityFeedItem {
  id: string;
  timestamp: string;
  title: string;
  tag: string;
  summary: string;
  views: number;
  result: ForensicResult;
}

interface RoleplayMessage {
  id: string;
  sender: "scammer" | "user" | "eval";
  text: string;
  evalStatus?: "safe" | "danger";
}

const SAMPLE_CASES = [
  {
    title: "Bẫy đào Solana 0.065 SOL/h", tag: "Crypto Drainer", summary: "Web mạo danh Solana cam kết lãi khủng theo giờ, dụ cài app độc rút tiền ví.",
    mockResult: {
      scam_detected: true, risk_score: 98, threat_level: "CRITICAL" as const,
      scam_type: "Crypto Phishing & Wallet Drainer",
      executive_summary: "Trang web giả mạo thương hiệu Solana trên domain lạ hashrate-accesscenter.com dụ cài file độc chiếm ví.",
      red_flags: [
        { evidence: "Domain 'hashrate-accesscenter.com'", explanation: "Không thuộc sở hữu của Solana Foundation (solana.com)." },
        { evidence: "Cam kết 0.065 SOL/giờ", explanation: "Lợi nhuận phi thực tế, dấu hiệu lừa đảo Ponzi." }
      ],
      psychological_tricks: [{ tactic: "FOMO lợi nhuận", target_emotion: "Lòng tham", analysis: "Tạo cảm giác bỏ lỡ tiền miễn phí mỗi giờ." }],
      next_move_prediction: "Yêu cầu ký lệnh Approve quyền truy cập ví không giới hạn để rút sạch tiền.",
      urgent_actions: ["Đóng tab ngay lập tức", "Thu hồi quyền truy cập ví qua Revoke.cash"],
      family_alert_card: { headline: "CẢNH BÁO LỪA ĐẢO SÀN TIỀN ẢO", key_warning: "Hứa trả lãi theo giờ đều là bẫy rút cạn ví!", shareable_text: "🚨 CẢNH BÁO: Đang có web mạo danh Solana hứa đào tiền có lãi. Tuyệt đối không bấm hay nối ví kẻo mất sạch tiền!" }
    }
  },
  {
    title: "SMS mạo danh Ngân hàng", tag: "Brand Phishing", summary: "Tin nhắn dọa khóa tài khoản ngân hàng do biến động số dư bất thường.",
    mockResult: {
      scam_detected: true, risk_score: 95, threat_level: "CRITICAL" as const,
      scam_type: "SMS Phishing Brandname",
      executive_summary: "Dùng trạm BTS giả chèn tin nhắn dọa đóng băng tài khoản để chiếm đoạt mã OTP.",
      red_flags: [{ evidence: "Đường link đuôi lạ .vip", explanation: "Trang web giả mạo giao diện ngân hàng để thu thập mật khẩu." }],
      psychological_tricks: [{ tactic: "Đe dọa khóa tài khoản", target_emotion: "Sợ hãi", analysis: "Ép nạn nhân thao tác vội trong 5 phút." }],
      next_move_prediction: "Dùng OTP chiếm đoạt chuyển sạch tiền sang tài khoản rác.",
      urgent_actions: ["Không bấm vào link", "Gọi hotline ngân hàng trên thẻ để khóa tài khoản tạm thời"],
      family_alert_card: { headline: "CẢNH BÁO SMS GIẢ MẠO NGÂN HÀNG", key_warning: "Ngân hàng KHÔNG BAO GIỜ gửi link bắt nhập OTP!", shareable_text: "⚠️ CẢNH BÁO: Tuyệt đối không bấm link trong SMS dọa khóa tài khoản. Ngân hàng không bao giờ gửi link bắt nhập mã OTP!" }
    }
  },
  {
    title: "Tuyển CTV Shopee hoa hồng 20%", tag: "Task Scam", summary: "Làm nhiệm vụ chuyển khoản nạp tiền đơn hàng ảo nhận hoa hồng cao.",
    mockResult: {
      scam_detected: true, risk_score: 92, threat_level: "HIGH" as const,
      scam_type: "Tuyển dụng CTV Đơn ảo",
      executive_summary: "Dụ làm nhiệm vụ đơn hàng ảo, ban đầu trả tiền sòng phẳng rồi viện cớ lỗi hệ thống chiếm đoạt tiền nạp.",
      red_flags: [{ evidence: "Nạp tiền vào STK cá nhân", explanation: "Tiền đi thẳng vào tài khoản của kẻ lừa đảo." }],
      psychological_tricks: [{ tactic: "Bẫy chi phí chìm", target_emotion: "Tiếc tiền", analysis: "Ép nạp thêm tiền để cứu lại tiền đã bị treo." }],
      next_move_prediction: "Báo lỗi cú pháp, yêu cầu nạp thêm 50% tiền để kích hoạt hoàn tiền.",
      urgent_actions: ["Dừng chuyển thêm tiền", "Lưu sao kê và tin nhắn trình báo công an"],
      family_alert_card: { headline: "CẢNH BÁO CTV MUA HÀNG ẢO", key_warning: "Không có việc gì chỉ ngồi chuyển khoản mà có lãi 20%!", shareable_text: "📢 CẢNH BÁO: Đừng tham gia nhóm làm nhiệm vụ nạp tiền mua hàng ăn hoa hồng. Càng nạp càng mất trắng!" }
    }
  }
];

const MOCK_COMMUNITY_FEED: CommunityFeedItem[] = [
  {
    id: "VN-FS-884192",
    timestamp: "10 phút trước",
    title: "Sàn BO cam kết bao lỗ 100% / ngày",
    tag: "Sàn Quyền Chọn Giả",
    summary: "Lừa nạp tiền đánh sàn BO Binance-like giả lập kết quả thắng ban đầu, sau đó khóa rút tiền dọa thu thuế.",
    views: 342,
    result: {
      scam_detected: true, risk_score: 96, threat_level: "CRITICAL" as const,
      scam_type: "Sàn BO (Binary Options) Giả Mạo",
      executive_summary: "Sàn giao dịch quyền chọn nhị phân giả mạo thao túng nến đồ thị, dọa nạp thêm tiền thuế để rút.",
      red_flags: [
        { evidence: "Cam kết bao lỗ 100% & hoa hồng 30%", explanation: "Không sàn giao dịch tài chính hợp pháp nào bao lỗ." },
        { evidence: "Domain lạ bo-trading-vip.net", explanation: "Tên miền vừa đăng ký không có giấy phép hoạt động." }
      ],
      psychological_tricks: [{ tactic: "Tạo lòng tin ảo", target_emotion: "Lòng tham", analysis: "Cho thắng nhỏ ban đầu để nạn nhân tự tin dồn vốn lớn." }],
      next_move_prediction: "Yêu cầu nạp 20% phí xác minh tài khoản hoặc phí thuế thu nhập cá nhân mới cho rút tiền.",
      urgent_actions: ["Không nạp thêm bất kỳ khoản tiền nào", "Lưu giữ lịch sử chuyển khoản & chụp màn hình nhóm Telegram"],
      family_alert_card: { headline: "CẢNH BÁO SÀN BO LỪA ĐẢO BAO LỖ", key_warning: "Mọi cam kết bao lỗ 100% trên mạng đều là bẫy chiếm đoạt tài sản!", shareable_text: "🚨 CẢNH BÁO GIA ĐÌNH: Tuyệt đối không tham gia các sàn BO, sàn tài chính cam kết bao lỗ 100%. Càng nạp càng mất trắng!" }
    }
  },
  {
    id: "VN-FS-741029",
    timestamp: "25 phút trước",
    title: "Cuộc gọi / APK giả mạo VNeID mức 2",
    tag: "Mã Độc Android",
    summary: "Đối tượng xưng công an hướng dẫn cài file .APK VNeID giả để chiếm quyền điều khiển điện thoại và đọc mã OTP.",
    views: 518,
    result: {
      scam_detected: true, risk_score: 99, threat_level: "CRITICAL" as const,
      scam_type: "Fake Gov App / Android Malware",
      executive_summary: "Gửi link tải ứng dụng .APK chứa mã độc Accessibility Service để đọc OTP và tự động chuyển tiền.",
      red_flags: [
        { evidence: "Link tải file .APK ngoài Google Play", explanation: "Công an không bao giờ gửi link qua Zalo/SMS để cập nhật VNeID." },
        { evidence: "Yêu cầu cấp quyền Accessibility (Hỗ trợ)", explanation: "Mã độc dùng quyền này để đọc màn hình và tự thao tác app ngân hàng." }
      ],
      psychological_tricks: [{ tactic: "Mạo danh cơ quan công quyền", target_emotion: "Nỗi sợ pháp lý", analysis: "Dọa khóa tài khoản/định danh nếu không làm ngay." }],
      next_move_prediction: "Âm thầm khóa màn hình nạn nhân và thực hiện chuyển cạn tiền tài khoản ngân hàng.",
      urgent_actions: ["Tắt Wifi/4G hoặc ngắt nguồn điện thoại ngay", "Dùng máy khác gọi ngân hàng khóa khẩn cấp các tài khoản"],
      family_alert_card: { headline: "CẢNH BÁO GIẢ MẠO CÔNG AN CÀI VNeID", key_warning: "Công an KHÔNG BAO GIỜ gọi điện bảo cài app qua file APK!", shareable_text: "⚠️ CẢNH BÁO: Không bấm link hay cài file APK từ cuộc gọi tự xưng công an hỗ trợ VNeID. Kẻ gian sẽ chiếm quyền máy rút sạch tiền!" }
    }
  },
  {
    id: "VN-FS-629501",
    timestamp: "1 giờ trước",
    title: "Cuộc gọi Video Deepfake đòi nợ người thân",
    tag: "AI Deepfake Video",
    summary: "Kẻ gian cắt ghép hình ảnh Deepfake giả mặt người thân gọi video 5 giây cấp cứu cần chuyển tiền.",
    views: 412,
    result: {
      scam_detected: true, risk_score: 94, threat_level: "HIGH" as const,
      scam_type: "AI Deepfake Impersonation",
      executive_summary: "Sử dụng trí tuệ nhân tạo giả dạng khuôn mặt và giọng nói người thân trong thời gian ngắn để vay tiền gấp.",
      red_flags: [
        { evidence: "Tín hiệu video chập chờn, tắt nhanh trong vài giây", explanation: "Kẻ gian cố tình làm mờ để che đậy khuyết điểm mô phỏng cơ mặt AI." },
        { evidence: "Yêu cầu chuyển tiền vào tài khoản tên người lạ", explanation: "Viện cớ tài khoản chính bị khóa hoặc mượn tài khoản bác sĩ." }
      ],
      psychological_tricks: [{ tactic: "Tạo tình huống khẩn cấp", target_emotion: "Lo lắng cho người thân", analysis: "Gây hoảng loạn để nạn nhân không kịp gọi điện xác minh." }],
      next_move_prediction: "Tiếp tục hối thúc chuyển thêm tiền với lý do chi phí phẫu thuật/bồi thường chưa đủ.",
      urgent_actions: ["Tắt máy và gọi lại qua số điện thoại thường (GSM)", "Hỏi một câu hỏi riêng tư chỉ 2 người biết để kiểm chứng"],
      family_alert_card: { headline: "CẢNH BÁO VIDEO CALL DEEPFAKE LỪA TIỀN", key_warning: "Thấy mặt qua Video Call vẫn có thể là AI giả mạo!", shareable_text: "📢 CẢNH BÁO: Nhận cuộc gọi video hỏi vay tiền gấp, hãy cúp máy và gọi điện trực tiếp vào SĐT chính chủ để xác minh!" }
    }
  },
  {
    id: "VN-FS-391804",
    timestamp: "2 giờ trước",
    title: "Hack Telegram gửi link bình chọn cuộc thi",
    tag: "Account Takeover",
    summary: "Nhận tin nhắn từ tài khoản bạn bè nhờ click link bình chọn ảnh, thực chất là trang phishing cướp OTP Telegram.",
    views: 295,
    result: {
      scam_detected: true, risk_score: 89, threat_level: "HIGH" as const,
      scam_type: "Telegram Phishing & Session Hijacking",
      executive_summary: "Dụ nạn nhân nhập số điện thoại và mã OTP Telegram vào trang web giả mạo bình chọn để chiếm quyền quản trị tài khoản.",
      red_flags: [
        { evidence: "Yêu cầu nhập mã xác thực OTP Telegram", explanation: "Các trang bình chọn thật không bao giờ yêu cầu đăng nhập OTP Telegram." },
        { evidence: "Tên miền giả mạo (vote-kids-2026.com)", explanation: "Domain lừa đảo được tạo hàng loạt nhằm thu thập session token." }
      ],
      psychological_tricks: [{ tactic: "Lợi dụng lòng tốt & tình bạn", target_emotion: "Nhiệt tình giúp đỡ", analysis: "Gửi tin nhắn từ tài khoản người quen đã bị hack trước đó." }],
      next_move_prediction: "Chiếm tài khoản Telegram và tiếp tục tự động gửi tin nhắn lừa đảo đến toàn bộ danh bạ.",
      urgent_actions: ["Mở Telegram -> Settings -> Devices -> Terminate all other sessions", "Bật xác thực 2 lớp (Two-Step Verification)"],
      family_alert_card: { headline: "CẢNH BÁO BẪY BÌNH CHỌN TRÊN TELEGRAM", key_warning: "Tuyệt đối không nhập mã OTP Telegram vào bất kỳ trang web nào!", shareable_text: "🚨 CẢNH BÁO: Nếu nhận tin nhắn nhờ bình chọn cuộc thi qua Telegram, không được bấm link hay nhập mã OTP kẻo bị cướp nick!" }
    }
  }
];

const QUICK_ROLEPLAY_RESPONSES = [
  {
    label: "🛡️ Gọi Hotline xác minh",
    text: "Tôi sẽ gọi trực tiếp hotline chính thức của ngân hàng/cơ quan công an để kiểm tra, không thao tác qua SMS hay link lạ!",
    isRisky: false,
  },
  {
    label: "🛡️ Từ chối & Báo cáo",
    text: "Tôi không có nhu cầu. Tôi biết đây là bẫy lừa đảo và sẽ báo cáo số điện thoại/tin nhắn này ngay lập tức!",
    isRisky: false,
  },
  {
    label: "⚠️ Thử bẫy: Cung cấp OTP / Bấm link",
    text: "Dạ anh gửi link hoặc để em đọc mã OTP cho anh để xử lý giúp em ngay với ạ!",
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
  const [communityFeed, setCommunityFeed] = useState<CommunityFeedItem[]>(MOCK_COMMUNITY_FEED);
  
  // Roleplay state
  const [roleplayInput, setRoleplayInput] = useState("");
  const [roleplayMessages, setRoleplayMessages] = useState<RoleplayMessage[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const generateId = () => `VN-FS-${Math.floor(100000 + Math.random() * 900000)}`;

  const getInitialRoleplayMessages = (res: ForensicResult | null): RoleplayMessage[] => {
    if (!res) return [];
    let scammerOpening = "🚨 [KỊCH BẢN GIẢ LẬP]: Thông báo khẩn từ hệ thống! Tài khoản/thông tin của bạn đang có sự cố nghiêm trọng, bấm vào link hoặc đọc mã OTP ngay trong 3 phút!";
    if (res.red_flags?.[0]?.evidence) {
      scammerOpening = `🚨 [KỊCH BẢN LỪA ĐẢO THỰC TẾ]: "${res.red_flags[0].evidence}" - Yêu cầu bạn làm theo hướng dẫn ngay lập tức nếu không sẽ bị khóa vĩnh viễn!`;
    } else if (res.scam_type) {
      scammerOpening = `🚨 [KỊCH BẢN ${res.scam_type.toUpperCase()}]: Đối tượng đang hối thúc bạn chuyển tiền / bấm link / cung cấp mã OTP xác minh khẩn cấp!`;
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

  const handleSelectFeedItem = (item: CommunityFeedItem) => {
    setCaseId(item.id);
    setResult(item.result);
    setRoleplayMessages(getInitialRoleplayMessages(item.result));
    setActiveTab("overview");
    window.scrollTo({ top: 180, behavior: "smooth" });
  };

  const handleNativeShare = async () => {
    if (!result) return;
    const shareText = result.family_alert_card.shareable_text;
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({
          title: result.family_alert_card.headline || "Cảnh báo lừa đảo",
          text: shareText,
          url: window.location.href,
        });
      } catch (e) {
        // User closed native share dialog
      }
    } else {
      navigator.clipboard.writeText(shareText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSendRoleplay = (userText: string, isRiskyQuickChoice?: boolean) => {
    if (!userText.trim()) return;

    const userMsg: RoleplayMessage = {
      id: `u-${Date.now()}`,
      sender: "user",
      text: userText,
    };

    const lower = userText.toLowerCase();
    const isDangerous = isRiskyQuickChoice || lower.includes("otp") || lower.includes("mật khẩu") || lower.includes("chuyển tiền") || lower.includes("nạp") || lower.includes("gửi link") || lower.includes("bấm link") || lower.includes("dạ anh");

    const evalMsg: RoleplayMessage = {
      id: `e-${Date.now()}`,
      sender: "eval",
      text: isDangerous
        ? "⚠️ CẢNH BÁO NGUY HIỂM: Bạn vừa sa vào bẫy! Việc gửi mã OTP, bấm link lạ hoặc chuyển tiền sẽ khiến bạn bị chiếm đoạt tài khoản/tài sản tức thì."
        : "✅ XỬ LÝ AN TOÀN: Rất tốt! Bạn giữ tâm lý tỉnh táo, không mắc bẫy tâm lý hối thúc và chủ động xác minh qua kênh chính thống.",
      evalStatus: isDangerous ? "danger" : "safe",
    };

    const scammerReplyMsg: RoleplayMessage = {
      id: `s-${Date.now()}`,
      sender: "scammer",
      text: isDangerous
        ? "Bẫy thành công! Kẻ gian đã nhận được mã/thông tin và vừa thực hiện rút sạch số dư tài khoản của bạn. Hãy rút kinh nghiệm!"
        : "Nạn nhân này quá tỉnh táo và dứt khoát! Kẻ lừa đảo dọa nạt không thành công đành phải ngắt cuộc gọi và chuyển mục tiêu khác.",
    };

    setRoleplayMessages((prev) => {
      const base = prev.length > 0 ? prev : getInitialRoleplayMessages(result);
      return [...base, userMsg, evalMsg, scammerReplyMsg];
    });
    setRoleplayInput("");
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
        res = await fetch("/api/analyze", { method: "POST", body: fd });
      } else {
        if (!textInput.trim()) return;
        res = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ textInput }),
        });
      }
      if (!res.ok) throw new Error((await res.json()).error || "Lỗi giám định");
      const analysisData: ForensicResult = await res.json();
      const newId = generateId();
      setCaseId(newId);
      setResult(analysisData);
      setRoleplayMessages(getInitialRoleplayMessages(analysisData));
      setActiveTab("overview");

      // Auto-prepend new case to Community Feed
      const newFeedItem: CommunityFeedItem = {
        id: newId,
        timestamp: "Vừa xong",
        title: inputMode === "image" ? (file?.name ? `Ảnh: ${file.name}` : "Ảnh màn hình nghi vấn") : (textInput.slice(0, 30) + "..."),
        tag: analysisData.scam_type || "Cảnh báo mới",
        summary: analysisData.executive_summary || "Hệ thống vừa phân tích thành công",
        views: 1,
        result: analysisData,
      };
      setCommunityFeed((prev) => [newFeedItem, ...prev]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const activeRoleplayList = roleplayMessages.length > 0 ? roleplayMessages : getInitialRoleplayMessages(result);

  return (
    <div className="min-h-screen bg-[#060913] text-slate-100 font-sans pb-20 selection:bg-cyan-500 selection:text-black">
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur sticky top-0 z-50 print:hidden">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-xl text-white shadow-lg">
              <ShieldAlert className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="font-black text-sm uppercase bg-gradient-to-r from-cyan-300 to-indigo-300 bg-clip-text text-transparent">
                ScamShield Forensic AI
              </div>
              <div className="text-[11px] text-slate-400">Giám định Pháp y Số & Giải mã Thao túng Đa phương thức</div>
            </div>
          </div>
          <div className="text-xs text-slate-300 border border-slate-800 bg-slate-900 px-3 py-1.5 rounded-full font-mono flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-cyan-400" /> Gemini 2.5 Flash
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 mt-8">
        <div className="text-center max-w-2xl mx-auto mb-6 print:hidden">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-950/30 text-cyan-300 text-xs font-semibold mb-2">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" /> AI Riser Vietnam 2026
          </div>
          <h1 className="text-3xl sm:text-4xl font-black">
            Giám định Lừa đảo & Thao túng Tâm lý
          </h1>
        </div>

        {/* Quick presets */}
        <div className="mb-6 bg-slate-900/40 border border-slate-800 rounded-2xl p-3.5 print:hidden">
          <div className="text-[11px] font-bold text-slate-400 uppercase mb-2 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-cyan-400" /> Ca thực tế thử nhanh:
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {SAMPLE_CASES.map((s, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setFile(null);
                  setPreviewUrl(null);
                  setTextInput("");
                  setCaseId(generateId());
                  setResult(s.mockResult);
                  setRoleplayMessages(getInitialRoleplayMessages(s.mockResult));
                  setActiveTab("overview");
                }}
                className="text-left p-2.5 rounded-xl border border-slate-800 bg-slate-950 hover:border-cyan-500/50 transition flex flex-col justify-between cursor-pointer group"
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-bold text-slate-200 group-hover:text-cyan-300">{s.title}</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">{s.tag}</span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-1">{s.summary}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Input Box */}
          <div className={result ? "lg:col-span-5 print:hidden" : "col-span-12 flex justify-center print:hidden"}>
            <div className={result ? "space-y-3 w-full" : "max-w-2xl w-full space-y-3"}>
              <div className="flex border border-slate-800 bg-slate-900/80 p-1 rounded-xl">
                <button
                  onClick={() => { setInputMode("image"); setResult(null); }}
                  className={`flex-1 py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition ${inputMode === "image" ? "bg-cyan-600 text-white" : "text-slate-400"}`}
                >
                  <ImageIcon className="w-3.5 h-3.5" /> Quét Ảnh chụp
                </button>
                <button
                  onClick={() => { setInputMode("text"); setResult(null); }}
                  className={`flex-1 py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition ${inputMode === "text" ? "bg-cyan-600 text-white" : "text-slate-400"}`}
                >
                  <Link2 className="w-3.5 h-3.5" /> Quét Text / Link
                </button>
              </div>

              {inputMode === "image" ? (
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => { e.preventDefault(); e.dataTransfer.files[0] && handleFile(e.dataTransfer.files[0]); }}
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-800 hover:border-cyan-500/50 bg-slate-900/30 rounded-2xl p-6 text-center cursor-pointer min-h-[220px] flex flex-col items-center justify-center"
                >
                  <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
                  {previewUrl ? (
                    <div className="relative max-h-56 overflow-hidden rounded-lg">
                      <img src={previewUrl} alt="Preview" className="max-h-56 object-contain" />
                      {loading && (
                        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur flex items-center justify-center">
                          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <UploadCloud className="w-8 h-8 text-cyan-400 mx-auto" />
                      <div className="text-xs font-semibold text-slate-300">Kéo thả hoặc bấm để chọn ảnh chụp màn hình</div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <label className="text-xs font-bold text-slate-300">Dán nội dung tin nhắn, email hoặc URL nghi vấn:</label>
                  <textarea
                    rows={6}
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    placeholder="Ví dụ: 'Thong bao: Tai khoan ngan hang cua ban da bi khoa, vui long truy cap https://vietcombank-login.vip de xac thuc...'"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
              )}

              {((inputMode === "image" && file) || (inputMode === "text" && textInput.trim())) && !loading && (
                <button
                  onClick={runAnalysis}
                  className="w-full py-3 bg-gradient-to-r from-cyan-600 to-indigo-600 font-bold text-xs rounded-xl shadow-lg flex items-center justify-center gap-2 cursor-pointer active:scale-95 text-white"
                >
                  <FileSearch className="w-4 h-4" /> Bắt đầu Giám định
                </button>
              )}

              {error && <div className="p-3 bg-red-950/60 border border-red-800 rounded-xl text-red-300 text-xs">{error}</div>}
            </div>
          </div>

          {/* Results Display */}
          {result && (
            <div className="lg:col-span-7 space-y-4 print:w-full print:col-span-12">
              <div className="flex justify-between items-center bg-slate-900/80 p-3 rounded-xl border border-slate-800 print:hidden">
                <div className="text-xs font-mono text-slate-400">HỒ SƠ: <strong className="text-cyan-300">{caseId}</strong></div>
                <button onClick={() => window.print()} className="text-xs bg-slate-800 text-cyan-300 px-3 py-1.5 rounded-lg border border-cyan-500/30 flex items-center gap-1.5 cursor-pointer hover:bg-slate-700 transition">
                  <Printer className="w-3.5 h-3.5" /> In Báo Cáo
                </button>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-16 h-16 rounded-xl border-2 flex flex-col items-center justify-center font-black ${result.risk_score >= 75 ? "text-red-400 border-red-500 bg-red-950/30" : "text-emerald-400 border-emerald-500 bg-emerald-950/30"}`}>
                    <span className="text-2xl">{result.risk_score}</span>
                    <span className="text-[8px]">SCORE</span>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400">Loại hình</div>
                    <div className="text-lg font-bold">{result.scam_type}</div>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-red-500/20 text-red-400 font-bold">{result.threat_level}</span>
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-slate-800 gap-2 print:hidden overflow-x-auto pb-0.5">
                {(["overview", "psychology", "family", "roleplay"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`pb-2 px-3 text-xs font-bold border-b-2 whitespace-nowrap cursor-pointer transition ${
                      activeTab === tab ? "border-cyan-400 text-cyan-300" : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {tab === "overview" && "Dấu vết Vi phạm"}
                    {tab === "psychology" && "Giải mã Tâm lý"}
                    {tab === "family" && "Thẻ Cảnh báo Gia đình"}
                    {tab === "roleplay" && "🎯 Tập Dượt Phản Xạ"}
                  </button>
                ))}
              </div>

              {/* Tab 1: Overview */}
              {activeTab === "overview" && (
                <div className="space-y-3">
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                    <div className="text-xs font-bold text-slate-300">Tóm tắt giám định:</div>
                    <p className="text-xs text-slate-400 leading-relaxed">{result.executive_summary}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                    <div className="text-xs font-bold text-slate-300">Dấu hiệu nhận biết:</div>
                    {result.red_flags.map((f, i) => (
                      <div key={i} className="p-2.5 bg-slate-950 rounded-lg text-xs space-y-0.5">
                        <div className="font-bold text-red-400">🚨 {f.evidence}</div>
                        <div className="text-slate-400 pl-4">{f.explanation}</div>
                      </div>
                    ))}
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                    <div className="text-xs font-bold text-amber-300">Hành động 60s:</div>
                    {result.urgent_actions.map((a, i) => (
                      <div key={i} className="text-xs text-slate-300 flex items-center gap-1.5"><Zap className="w-3.5 h-3.5 text-cyan-400" /> {a}</div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tab 2: Psychology */}
              {activeTab === "psychology" && (
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                  <div className="text-xs font-bold text-purple-300">Đòn thao túng cảm xúc của kẻ gian:</div>
                  {result.psychological_tricks.map((t, i) => (
                    <div key={i} className="p-3 bg-slate-950 rounded-lg text-xs space-y-1 border border-purple-900/30">
                      <div className="flex justify-between font-bold text-purple-300">
                        <span>{t.tactic}</span>
                        <span className="text-[10px] px-2 py-0.5 bg-purple-950 rounded text-purple-400">Đánh vào: {t.target_emotion}</span>
                      </div>
                      <p className="text-slate-400">{t.analysis}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 3: Family Share */}
              {activeTab === "family" && (
                <div className="p-4 rounded-xl bg-slate-900 border border-indigo-500/30 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                    <span className="text-xs font-bold text-indigo-300">Nội dung gửi nhanh người thân (Zalo/Telegram):</span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <button
                        onClick={() => {
                          const text = encodeURIComponent(result.family_alert_card.shareable_text);
                          window.open(`https://zalo.me/share?text=${text}`, "_blank");
                        }}
                        className="text-xs bg-[#0068ff] hover:bg-[#0054d1] text-white px-2.5 py-1 rounded-md flex items-center gap-1 cursor-pointer font-semibold transition"
                      >
                        <Share2 className="w-3.5 h-3.5" /> Gửi qua Zalo
                      </button>

                      <button
                        onClick={() => {
                          const text = encodeURIComponent(result.family_alert_card.shareable_text);
                          const url = encodeURIComponent(typeof window !== "undefined" ? window.location.href : "");
                          window.open(`https://t.me/share/url?url=${url}&text=${text}`, "_blank");
                        }}
                        className="text-xs bg-[#24A1DE] hover:bg-[#1f8ec4] text-white px-2.5 py-1 rounded-md flex items-center gap-1 cursor-pointer font-semibold transition"
                      >
                        <Send className="w-3.5 h-3.5" /> Gửi Telegram
                      </button>

                      <button
                        onClick={handleNativeShare}
                        className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-2.5 py-1 rounded-md flex items-center gap-1 cursor-pointer font-semibold transition"
                      >
                        {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        {copied ? "Đã copy!" : "Copy"}
                      </button>
                    </div>
                  </div>
                  <div className="bg-[#005c4b] p-3.5 rounded-xl text-xs text-white whitespace-pre-wrap leading-relaxed shadow-inner font-sans">
                    {result.family_alert_card.shareable_text}
                  </div>
                </div>
              )}

              {/* Tab 4: Roleplay Lab */}
              {activeTab === "roleplay" && (
                <div className="p-4 rounded-xl bg-slate-900 border border-cyan-500/30 space-y-4">
                  <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                    <div>
                      <div className="text-xs font-bold text-cyan-300 flex items-center gap-1.5">
                        <Gamepad2 className="w-4 h-4 text-cyan-400" /> Giả Lập Phản Xạ Chống Lừa Đảo (Roleplay Lab)
                      </div>
                      <div className="text-[11px] text-slate-400">Tập luyện đối đáp trực tiếp với kịch bản lừa đảo vừa phát hiện</div>
                    </div>
                    <button
                      onClick={() => setRoleplayMessages(getInitialRoleplayMessages(result))}
                      className="text-[11px] px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg flex items-center gap-1 cursor-pointer transition border border-slate-700"
                    >
                      <RefreshCw className="w-3 h-3 text-cyan-400" /> Đặt lại
                    </button>
                  </div>

                  {/* Chat Log Window */}
                  <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-3.5 space-y-3 max-h-80 overflow-y-auto font-sans">
                    {activeRoleplayList.map((msg) => {
                      if (msg.sender === "scammer") {
                        return (
                          <div key={msg.id} className="flex gap-2.5 items-start max-w-[88%]">
                            <div className="w-7 h-7 rounded-lg bg-red-950 border border-red-800 flex items-center justify-center text-red-400 shrink-0 text-xs font-bold">
                              <Bot className="w-4 h-4" />
                            </div>
                            <div className="bg-red-950/40 border border-red-900/50 rounded-2xl rounded-tl-none p-3 text-xs text-red-200 leading-relaxed">
                              <div className="text-[9px] font-bold text-red-400 uppercase mb-1">Kẻ lừa đảo (Scammer AI)</div>
                              {msg.text}
                            </div>
                          </div>
                        );
                      }
                      if (msg.sender === "user") {
                        return (
                          <div key={msg.id} className="flex gap-2.5 items-start justify-end ml-auto max-w-[88%]">
                            <div className="bg-cyan-950/60 border border-cyan-800/50 rounded-2xl rounded-tr-none p-3 text-xs text-cyan-100 leading-relaxed">
                              <div className="text-[9px] font-bold text-cyan-400 uppercase mb-1 text-right">Bạn (Nạn nhân)</div>
                              {msg.text}
                            </div>
                            <div className="w-7 h-7 rounded-lg bg-cyan-950 border border-cyan-800 flex items-center justify-center text-cyan-400 shrink-0 text-xs font-bold">
                              <User className="w-4 h-4" />
                            </div>
                          </div>
                        );
                      }
                      if (msg.sender === "eval") {
                        return (
                          <div
                            key={msg.id}
                            className={`p-2.5 rounded-xl text-xs font-medium border flex items-center gap-2 ${
                              msg.evalStatus === "danger"
                                ? "bg-red-950/80 border-red-700 text-red-300"
                                : "bg-emerald-950/80 border-emerald-700 text-emerald-300"
                            }`}
                          >
                            <Zap className="w-4 h-4 shrink-0" />
                            <span>{msg.text}</span>
                          </div>
                        );
                      }
                      return null;
                    })}
                  </div>

                  {/* Quick Responses */}
                  <div className="space-y-1.5">
                    <div className="text-[10px] uppercase font-bold text-slate-400">Gợi ý câu trả lời nhanh (Click thử ngay):</div>
                    <div className="flex flex-wrap gap-2">
                      {QUICK_ROLEPLAY_RESPONSES.map((qr, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSendRoleplay(qr.text, qr.isRisky)}
                          className={`text-[11px] px-2.5 py-1.5 rounded-lg border text-left cursor-pointer transition active:scale-95 flex items-center gap-1.5 ${
                            qr.isRisky
                              ? "bg-red-950/40 border-red-800/60 text-red-300 hover:bg-red-900/50"
                              : "bg-slate-950 border-slate-800 text-slate-300 hover:border-cyan-500/50 hover:text-cyan-300"
                          }`}
                        >
                          {qr.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Custom Input */}
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
                      placeholder="Nhập câu trả lời của bạn đối đáp với kẻ gian..."
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-sans"
                    />
                    <button
                      type="submit"
                      className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-indigo-600 font-bold text-xs rounded-xl shadow-lg flex items-center gap-1.5 cursor-pointer active:scale-95 text-white"
                    >
                      <Send className="w-3.5 h-3.5" /> Gửi
                    </button>
                  </form>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Live Community Scam Feed */}
        <div className="mt-12 bg-slate-900/50 border border-slate-800/80 rounded-2xl p-5 print:hidden backdrop-blur">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 border-b border-slate-800/80 pb-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="p-2.5 bg-red-950/60 border border-red-800/50 rounded-xl text-red-400">
                  <Users className="w-5 h-5" />
                </div>
                <span className="absolute -top-1 -right-1 flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-slate-100">Live Community Scam Feed</h2>
                  <span className="text-[10px] uppercase tracking-wider font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live Real-time
                  </span>
                </div>
                <p className="text-xs text-slate-400">Cảnh báo lừa đảo mới nhất được cộng đồng phát hiện và giám định</p>
              </div>
            </div>
            <div className="text-xs text-slate-400 font-mono flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 self-start sm:self-auto">
              <Flame className="w-3.5 h-3.5 text-amber-400 animate-bounce" /> {communityFeed.length} ca đã ghi nhận
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {communityFeed.map((item) => (
              <div
                key={item.id}
                onClick={() => handleSelectFeedItem(item)}
                className="group relative bg-slate-950/80 border border-slate-800/90 hover:border-cyan-500/60 rounded-xl p-4 transition-all duration-200 cursor-pointer hover:shadow-lg hover:shadow-cyan-950/30 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/50 shrink-0">
                        {item.id}
                      </span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30 shrink-0">
                        {item.tag}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1 shrink-0 font-mono">
                      <Clock className="w-3 h-3 text-slate-400" /> {item.timestamp}
                    </span>
                  </div>

                  <h3 className="text-xs font-bold text-slate-200 group-hover:text-cyan-300 transition line-clamp-1 mb-1">
                    {item.title}
                  </h3>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed mb-3">
                    {item.summary}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2.5 border-t border-slate-900 text-[11px]">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Eye className="w-3.5 h-3.5 text-cyan-400/80" /> {item.views} lượt xem
                  </span>
                  <span className="text-cyan-400 font-bold group-hover:translate-x-0.5 transition flex items-center gap-1">
                    Xem Giám định <ArrowUpRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}