"use client";

import React, { useState, useRef } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  UploadCloud,
  FileSearch,
  Brain,
  Forward,
  Copy,
  Check,
  Zap,
  Lock,
  RefreshCw,
  Eye,
} from "lucide-react";

interface RedFlag {
  evidence: string;
  explanation: string;
}

interface PsychTrick {
  tactic: string;
  target_emotion: string;
  analysis: string;
}

interface FamilyAlertCard {
  headline: string;
  key_warning: string;
  shareable_text: string;
}

interface ForensicResult {
  scam_detected: boolean;
  risk_score: number;
  threat_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "SAFE";
  scam_type: string;
  executive_summary: string;
  red_flags: RedFlag[];
  psychological_tricks: PsychTrick[];
  next_move_prediction: string;
  urgent_actions: string[];
  family_alert_card: FamilyAlertCard;
}

export default function ScamShieldDashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ForensicResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
      setResult(null);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
      setResult(null);
      setError(null);
    }
  };

  const analyzeImage = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("image", file);

      const res = await fetch("/api/analyze", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "Không thể phân tích ảnh");
      }

      const data: ForensicResult = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Đã xảy ra lỗi trong quá trình giám định");
    } finally {
      setLoading(false);
    }
  };

  const copyShareText = () => {
    if (!result?.family_alert_card?.shareable_text) return;
    navigator.clipboard.writeText(result.family_alert_card.shareable_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getThreatBadge = (level: string) => {
    switch (level) {
      case "CRITICAL":
        return <span className="px-3 py-1 text-xs font-bold rounded-full bg-red-950 text-red-400 border border-red-800">MỨC ĐỘ NGUY HIỂM TỐI CAO</span>;
      case "HIGH":
        return <span className="px-3 py-1 text-xs font-bold rounded-full bg-orange-950 text-orange-400 border border-orange-800">RỦI RO CAO</span>;
      case "MEDIUM":
        return <span className="px-3 py-1 text-xs font-bold rounded-full bg-yellow-950 text-yellow-400 border border-yellow-800">CẦN THẬN TRỌNG</span>;
      default:
        return <span className="px-3 py-1 text-xs font-bold rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">AN TOÀN</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 antialiased font-sans pb-20">
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600/20 border border-blue-500/40 rounded-lg text-blue-400">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <div className="font-bold tracking-wider text-base uppercase bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
                ScamShield Forensic AI
              </div>
              <div className="text-[11px] text-slate-400">Hệ thống Giám định Pháp y Số & Thao túng Lừa đảo</div>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs text-slate-400 border border-slate-800 bg-slate-900 px-3 py-1.5 rounded-full">
            <Lock className="w-3.5 h-3.5 text-blue-400" />
            <span>Google AI Studio Powered</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 mt-8">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3">
            Bóc tách bẫy lừa đảo <br />
            <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">
              bằng thị giác máy tính & tâm lý học
            </span>
          </h1>
          <p className="text-sm text-slate-400 leading-relaxed">
            Kéo thả ảnh chụp màn hình tin nhắn, ứng dụng nạp tiền hoặc đường link đáng ngờ. Hệ thống sẽ bóc tách các dấu hiệu gian lận và chiêu trò tâm lý trong 3 giây.
          </p>
        </div>

        <div className={`grid grid-cols-1 ${result ? "lg:grid-cols-12" : "max-w-xl mx-auto"} gap-6 items-start`}>
          {/* Upload Box */}
          <div className={result ? "lg:col-span-5" : "w-full"}>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[260px] ${
                previewUrl
                  ? "border-blue-500/50 bg-slate-900/40"
                  : "border-slate-800 bg-slate-900/20 hover:border-blue-500/40 hover:bg-slate-900/40"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileChange}
              />

              {previewUrl ? (
                <div className="w-full flex flex-col items-center space-y-4">
                  <div className="relative max-h-72 w-full overflow-hidden rounded-lg border border-slate-700 shadow-md flex items-center justify-center bg-slate-950">
                    <img src={previewUrl} alt="Preview" className="max-h-72 object-contain rounded-lg" />
                    {loading && (
                      <div className="absolute inset-0 bg-blue-950/80 backdrop-blur-sm flex flex-col items-center justify-center space-y-3">
                        <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
                        <span className="text-xs font-semibold tracking-wider text-blue-200 animate-pulse">
                          ĐANG GIÁM ĐỊNH PHÁP Y DỮ LIỆU...
                        </span>
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-slate-400">Bấm hoặc kéo thả ảnh khác để thay đổi</p>
                </div>
              ) : (
                <div className="space-y-3 py-6">
                  <div className="w-12 h-12 rounded-full bg-blue-600/10 text-blue-400 flex items-center justify-center mx-auto border border-blue-500/20">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <div>
                    <span className="text-sm font-medium text-slate-200">Tải ảnh chụp màn hình lên</span>
                    <p className="text-xs text-slate-500 mt-1">Hỗ trợ PNG, JPG, JPEG (Tối đa 10MB)</p>
                  </div>
                </div>
              )}
            </div>

            {file && !loading && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  analyzeImage();
                }}
                className="w-full mt-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 font-semibold text-sm rounded-xl shadow-lg shadow-blue-900/30 flex items-center justify-center space-x-2 transition-all cursor-pointer"
              >
                <FileSearch className="w-4 h-4" />
                <span>Bắt đầu Giám định Pháp y Số</span>
              </button>
            )}

            {error && (
              <div className="mt-4 p-3 bg-red-950/60 border border-red-800/80 rounded-xl text-red-300 text-xs flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Results Box */}
          {result && (
            <div className="lg:col-span-7 space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center space-x-3">
                    <div className={`p-2.5 rounded-xl border ${result.risk_score > 70 ? "bg-red-500/10 border-red-500/30 text-red-400" : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"}`}>
                      {result.risk_score > 70 ? <AlertTriangle className="w-6 h-6" /> : <ShieldCheck className="w-6 h-6" />}
                    </div>
                    <div>
                      <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Chỉ số rủi ro gian lận</div>
                      <div className="text-2xl font-black text-slate-100">{result.risk_score}/100</div>
                    </div>
                  </div>
                  {getThreatBadge(result.threat_level)}
                </div>

                <div className="border-t border-slate-800/80 pt-3">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Phân loại chiêu trò:</div>
                  <div className="text-base font-bold text-blue-400 mt-0.5">{result.scam_type}</div>
                  <p className="text-xs text-slate-300 mt-2 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    {result.executive_summary}
                  </p>
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-3">
                <div className="flex items-center space-x-2 text-sm font-bold text-slate-200">
                  <Eye className="w-4 h-4 text-cyan-400" />
                  <span>Dấu vết Vi phạm & Bằng chứng Trích xuất</span>
                </div>
                <div className="space-y-2">
                  {result.red_flags.map((flag, idx) => (
                    <div key={idx} className="p-3 bg-slate-950 rounded-xl border border-slate-800/80 space-y-1">
                      <div className="text-xs font-bold text-red-400 flex items-center space-x-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
                        <span>{flag.evidence}</span>
                      </div>
                      <p className="text-xs text-slate-400 pl-3">{flag.explanation}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-3">
                <div className="flex items-center space-x-2 text-sm font-bold text-slate-200">
                  <Brain className="w-4 h-4 text-purple-400" />
                  <span>Bóc tách Kỹ thuật Thao túng Tâm lý</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {result.psychological_tricks.map((trick, idx) => (
                    <div key={idx} className="p-3 bg-slate-950 rounded-xl border border-slate-800/80 flex flex-col justify-between">
                      <div>
                        <div className="text-xs font-bold text-purple-300">{trick.tactic}</div>
                        <div className="text-[10px] text-purple-400 font-medium mt-0.5">Nhắm vào: {trick.target_emotion}</div>
                        <p className="text-xs text-slate-400 mt-2 leading-relaxed">{trick.analysis}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-3">
                <div className="flex items-center space-x-2 text-sm font-bold text-slate-200">
                  <Forward className="w-4 h-4 text-amber-400" />
                  <span>Dự đoán Bước tiếp theo của Kẻ gian & Hành động Ngay</span>
                </div>
                <div className="p-3 bg-amber-950/20 border border-amber-900/40 rounded-xl text-xs text-amber-300 leading-relaxed">
                  <span className="font-semibold">Kịch bản bẫy tiếp theo: </span> {result.next_move_prediction}
                </div>
                <div className="space-y-1.5 pt-1">
                  <div className="text-xs font-semibold text-slate-400">Các bước xử lý khẩn cấp:</div>
                  {result.urgent_actions.map((act, idx) => (
                    <div key={idx} className="flex items-center space-x-2 text-xs text-slate-300">
                      <Zap className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                      <span>{act}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-950/40 to-slate-900 border border-indigo-500/30 shadow-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-sm font-bold text-indigo-300">
                    <ShieldAlert className="w-4 h-4 text-indigo-400" />
                    <span>Thẻ Cảnh Báo Gửi Nhanh Cho Gia Đình</span>
                  </div>
                  <button
                    onClick={copyShareText}
                    className="flex items-center space-x-1 text-xs bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 text-indigo-200 px-3 py-1.5 rounded-lg transition-all cursor-pointer"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? "Đã chép nội dung!" : "Sao chép tin nhắn"}</span>
                  </button>
                </div>
                <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap">
                  {result.family_alert_card.shareable_text}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}