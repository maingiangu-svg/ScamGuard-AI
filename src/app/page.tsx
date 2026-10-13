"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  ShieldAlert, AlertTriangle, UploadCloud, FileSearch, Brain, Forward,
  Copy, Check, Zap, Lock, RefreshCw, Eye, Activity, Fingerprint,
  Sparkles, ChevronRight, MessageSquare, Printer, Link2, Image as ImageIcon,
  Users, Flame, Clock, ArrowUpRight, Share2, Send, Gamepad2, Bot, User, Globe,
  ExternalLink, FileDown, X, HelpCircle
} from "lucide-react";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";

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
    title: "Solana Cloud Mining Trap 0.065 SOL/h",
    tag: "Crypto Drainer",
    summary: "Phishing site impersonating Solana Foundation, promising hourly yields to lure users into installing malicious wallet-draining scripts.",
    mockResult: {
      scam_detected: true,
      risk_score: 98,
      threat_level: "CRITICAL" as const,
      scam_type: "Crypto Phishing & Wallet Drainer",
      executive_summary: "Phishing platform impersonating the Solana Foundation on fraudulent domain hashrate-accesscenter.com designed to drain user Web3 wallets.",
      web_intelligence: {
        detected: true,
        url: "https://hashrate-accesscenter.com/solana-miner",
        domain: "hashrate-accesscenter.com",
        brand_detected: "Solana Foundation",
        domain_match: "mismatch" as const,
        website_status: "accessible" as const,
        suspicious_indicators: [
          "Requests unlimited wallet approval and asset permissions",
          "Guarantees unrealistic fixed hourly returns",
          "Newly registered domain lacking corporate SSL and verified entity"
        ],
        external_evidence: [
          {
            title: "Web3 Security Advisory: Fake Solana Cloud Mining Drainers",
            source_url: "https://www.google.com/search?q=solana+mining+drainer+scam+alert"
          },
          {
            title: "Official Solana Foundation Domain (solana.com)",
            source_url: "https://solana.com"
          }
        ],
        confidence: 96,
      },
      red_flags: [
        {
          evidence: "Domain 'hashrate-accesscenter.com'",
          official_fact: "The only official website of the Solana Foundation is solana.com.",
          official_link: "https://solana.com",
          explanation: "Unregistered third-party domain creating a trap to drain connected Web3 wallets."
        },
        {
          evidence: "Guaranteed 0.065 SOL/hour (~1.56 SOL/day)",
          official_fact: "Legitimate Solana staking APY is approximately 6-7% annually.",
          official_link: "https://solana.com",
          explanation: "Yield promises exceeding market benchmarks by 100x indicate a fraudulent Ponzi wallet drainer."
        }
      ],
      psychological_tricks: [
        {
          tactic: "Profit FOMO",
          target_emotion: "Greed",
          analysis: "Instills urgency and fear of missing out on risk-free passive hourly income."
        }
      ],
      next_move_prediction: "Requests unlimited token spending approval to siphon all native SOL and SPL tokens from the wallet.",
      urgent_actions: [
        "Close browser tab immediately",
        "Revoke suspicious token approvals via Revoke.cash"
      ],
      family_alert_card: {
        headline: "FRAUD ALERT: CRYPTO DRAINER PHISHING",
        key_warning: "Any website promising hourly crypto profits is a wallet-draining scam!",
        shareable_text: "🚨 WARNING: A fraudulent site is impersonating Solana promising high mining profits. Do not connect your crypto wallet or approve any transactions!"
      }
    }
  },
  {
    title: "SMS Banking Brandname Spoofing",
    tag: "Brand Phishing",
    summary: "Fake SMS threatening that the bank account is locked due to suspicious transactions, coercing victims into entering OTP credentials.",
    mockResult: {
      scam_detected: true,
      risk_score: 95,
      threat_level: "CRITICAL" as const,
      scam_type: "SMS Brandname Phishing",
      executive_summary: "Threat actor uses rogue BTS stations or SMS spoofing to broadcast fake account lock warnings and harvest two-factor credentials.",
      web_intelligence: {
        detected: true,
        url: "https://vietcombank-login.vip/verify-otp",
        domain: "vietcombank-login.vip",
        brand_detected: "Vietcombank",
        domain_match: "mismatch" as const,
        website_status: "accessible" as const,
        suspicious_indicators: [
          "Phishing login form collecting banking credentials and credentials",
          "Demands real-time SMS/Smart OTP submission",
          "Cheap generic TLD (.vip) impersonating financial institution"
        ],
        external_evidence: [
          { title: "Official Vietcombank Banking Portal", source_url: "https://www.vietcombank.com.vn" },
          { title: "Advisory on Fake BTS SMS Impersonation Attacks", source_url: "https://www.vietcombank.com.vn" }
        ],
        confidence: 98,
      },
      red_flags: [
        {
          evidence: "Suspicious URL domain vietcombank-login.vip",
          official_fact: "Official banking portals exclusively operate on registered enterprise domains (e.g., vietcombank.com.vn).",
          official_link: "https://www.vietcombank.com.vn",
          explanation: "Fraudulent clone page designed to intercept internet banking credentials and SMS OTP."
        }
      ],
      psychological_tricks: [
        {
          tactic: "Account Freezing Threat",
          target_emotion: "Fear",
          analysis: "Creates artificial panic forcing victims to act within minutes without cross-checking."
        }
      ],
      next_move_prediction: "Uses stolen credentials and OTP to execute unauthorized transfers to money mule accounts.",
      urgent_actions: [
        "Do not click or submit information",
        "Immediately contact bank fraud hotline to freeze account"
      ],
      family_alert_card: {
        headline: "CRITICAL ALERT: FAKE BANKING SMS",
        key_warning: "Banks NEVER send links requiring you to enter OTP codes or passwords!",
        shareable_text: "⚠️ WARNING: Do not click links in SMS claiming your bank account is locked. Banks never request passwords or OTP via SMS links!"
      }
    }
  },
  {
    title: "E-Commerce Task Scam (20% Commission)",
    tag: "Task Scam",
    summary: "Victims are solicited to transfer money for fake purchase orders with promises of high cashback, followed by total fund lockouts.",
    mockResult: {
      scam_detected: true,
      risk_score: 92,
      threat_level: "HIGH" as const,
      scam_type: "E-Commerce Order Task Scam",
      executive_summary: "Task scam luring victims with minor early payouts, then freezing funds and demanding larger deposits to unlock refunds.",
      web_intelligence: {
        detected: true,
        url: "https://shopee-nhiemvu.top/task-claim",
        domain: "shopee-nhiemvu.top",
        brand_detected: "Shopee Vietnam",
        domain_match: "mismatch" as const,
        website_status: "accessible" as const,
        suspicious_indicators: [
          "Requires upfront wire transfers to personal bank accounts to complete tasks",
          "Domain squatted brand name on .top TLD"
        ],
        external_evidence: [
          { title: "Official Shopee Platform", source_url: "https://shopee.vn" },
          { title: "Security Warning Regarding Recruitment & Order Tasks", source_url: "https://shopee.vn" }
        ],
        confidence: 94,
      },
      red_flags: [
        {
          evidence: "Demands deposits into an individual bank account (JOHN DOE)",
          official_fact: "Legitimate e-commerce marketplaces never recruit affiliates via personal wire transfers for order clearance.",
          official_link: "https://shopee.vn",
          explanation: "Funds are transferred directly into money mule accounts with zero real merchant connection."
        }
      ],
      psychological_tricks: [
        {
          tactic: "Sunk Cost Trap",
          target_emotion: "Regret & Anxiety",
          analysis: "Compels victims to deposit more funds under the pretext of unfreezing previously held deposits."
        }
      ],
      next_move_prediction: "Claims system syntax error and demands an additional 50% deposit to unlock refund authorization.",
      urgent_actions: [
        "Halt all further deposits immediately",
        "Export transaction logs and chat records for police reporting"
      ],
      family_alert_card: {
        headline: "ALERT: ONLINE ORDER TASK SCAM",
        key_warning: "No legitimate job pays 20% guaranteed commission simply for wire transferring money!",
        shareable_text: "📢 WARNING: Never join online groups asking for upfront deposits to process shopping orders. You will lose all deposited funds!"
      }
    }
  }
];

const MOCK_COMMUNITY_FEED: CommunityFeedItem[] = [
  {
    id: "VN-FS-884192",
    timestamp: "10 mins ago",
    title: "Fake Binary Options (BO) Platform: 100% Loss Protection",
    tag: "Fake Trading Exchange",
    summary: "Rigged candlestick charts simulate initial trading wins, then withdrawal is locked demanding additional 'tax' deposits.",
    views: 342,
    result: {
      scam_detected: true,
      risk_score: 96,
      threat_level: "CRITICAL" as const,
      scam_type: "Fake Binary Options (BO) Exchange",
      executive_summary: "Illegitimate binary options exchange manipulating prices and demanding fee deposits before permitting withdrawal.",
      web_intelligence: {
        detected: true,
        url: "https://bo-trading-vip.net/trade",
        domain: "bo-trading-vip.net",
        brand_detected: "Binance / BO Exchange",
        domain_match: "mismatch" as const,
        website_status: "accessible" as const,
        suspicious_indicators: [
          "Guarantees 100% loss protection & 30% commission",
          "Locks withdrawals and demands unverified tax clearance fees"
        ],
        external_evidence: [
          { title: "Securities Commission Fraud Advisory", source_url: "https://ssc.gov.vn" },
          { title: "ChongLuaDao Threat Database Entry", source_url: "https://chongluadao.vn" }
        ],
        confidence: 95,
      },
      red_flags: [
        {
          evidence: "Guaranteed 100% loss protection & 30% commission",
          official_fact: "All state-regulated financial investment vehicles entail risk and never guarantee 100% loss indemnity.",
          official_link: "https://ssc.gov.vn",
          explanation: "Psychological bait designed to reassure victims into depositing large sums of capital."
        },
        {
          evidence: "Unregulated domain bo-trading-vip.net without financial license",
          official_fact: "State financial regulators do not license any binary options (BO) trading platforms.",
          official_link: "https://ssc.gov.vn",
          explanation: "The exchange synthesizes artificial candlestick charts to confiscate investor capital."
        }
      ],
      psychological_tricks: [
        {
          tactic: "Artificial Trust Generation",
          target_emotion: "Greed",
          analysis: "Awards minor simulated wins initially so victims gain confidence and commit massive capital."
        }
      ],
      next_move_prediction: "Demands a 20% account verification fee or personal income tax prepayment before releasing funds.",
      urgent_actions: [
        "Do not deposit any further funds",
        "Archive bank transaction receipts & capture Telegram conversation logs"
      ],
      family_alert_card: {
        headline: "WARNING: FAKE LOSS-PROTECTED TRADING PLATFORM",
        key_warning: "Any online claim of 100% guaranteed loss protection is an asset-seizure scam!",
        shareable_text: "🚨 FAMILY ALERT: Never participate in binary options or trading sites claiming 100% loss coverage. Any deposited funds will be stolen!"
      }
    }
  },
  {
    id: "VN-FS-741029",
    timestamp: "25 mins ago",
    title: "Malicious Android APK Impersonating Public Identification",
    tag: "Android Malware",
    summary: "Impostor posing as police directs victim to install Trojan .APK to seize device control and intercept banking OTP.",
    views: 518,
    result: {
      scam_detected: true,
      risk_score: 99,
      threat_level: "CRITICAL" as const,
      scam_type: "Fake Gov App / Android Malware",
      executive_summary: "Distribution of malicious .APK exploiting Android Accessibility Service to remotely control banking apps and harvest OTP.",
      web_intelligence: {
        detected: true,
        url: "https://vneid-gov.apk-download.site/vneid.apk",
        domain: "vneid-gov.apk-download.site",
        brand_detected: "Public Identity Portal / Gov Authority",
        domain_match: "mismatch" as const,
        website_status: "accessible" as const,
        suspicious_indicators: [
          "Direct .APK download via spoofed government portal URL",
          "Requests Accessibility Service permissions for remote device control"
        ],
        external_evidence: [
          { title: "Official National Identification App Portal", source_url: "https://vneid.gov.vn" },
          { title: "National Cyber Security Center Malware Warning", source_url: "https://khonggianmang.vn" }
        ],
        confidence: 99,
      },
      red_flags: [
        {
          evidence: "Download link for vneid-gov.apk outside Google Play",
          official_fact: "Official public identification apps are distributed strictly via Google Play and Apple App Store.",
          official_link: "https://vneid.gov.vn",
          explanation: "Government authorities never send links over SMS or social media to install APK updates."
        },
        {
          evidence: "Demands Accessibility Service permissions",
          official_fact: "Legitimate public administration applications never require Accessibility permissions.",
          official_link: "https://khonggianmang.vn",
          explanation: "Malware exploits Accessibility to read screen content and automate illicit banking transfers."
        }
      ],
      psychological_tricks: [
        {
          tactic: "State Authority Impersonation",
          target_emotion: "Legal Fear",
          analysis: "Threatens legal sanctions or account freezing if instructions are not carried out immediately."
        }
      ],
      next_move_prediction: "Remotely locks victim device display and executes unauthorized withdrawals from banking apps.",
      urgent_actions: [
        "Disconnect Wi-Fi/Cellular data and power down phone immediately",
        "Use a separate phone to call banking fraud hotlines to freeze all accounts"
      ],
      family_alert_card: {
        headline: "CRITICAL WARNING: POLICE IMPERSONATION & FAKE APK",
        key_warning: "Law enforcement officers NEVER call asking you to install .APK files!",
        shareable_text: "⚠️ ALERT: Never click links or install APK files from calls claiming to be police officers updating ID profiles. They will hijack your phone and drain your bank account!"
      }
    }
  },
  {
    id: "VN-FS-629501",
    timestamp: "1 hour ago",
    title: "AI Deepfake Video Call Emergency Impersonation",
    tag: "AI Deepfake Video",
    summary: "Fraudsters synthesize 5-second video call mimicking family member in urgent medical distress needing rapid wire transfer.",
    views: 412,
    result: {
      scam_detected: true,
      risk_score: 94,
      threat_level: "HIGH" as const,
      scam_type: "AI Deepfake Impersonation",
      executive_summary: "Real-time AI voice and face synthesis used in brief emergency distress call to trigger hasty wire transfer.",
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
          evidence: "Glitchy video stream terminated after a few seconds",
          official_fact: "Current real-time generative deepfakes struggle with continuous facial consistency and prolonged voice alignment.",
          official_link: "https://khonggianmang.vn",
          explanation: "Attackers intentionally induce blur and latency to conceal AI synthesis artifacts."
        },
        {
          evidence: "Demands immediate transfer to an unfamiliar third-party account",
          official_fact: "Family members in legitimate emergencies use their own accounts or verified contacts.",
          official_link: "https://khonggianmang.vn",
          explanation: "Pretends personal account is locked or provides an alleged hospital account."
        }
      ],
      psychological_tricks: [
        {
          tactic: "Fabricated Emergency",
          target_emotion: "Family Concern",
          analysis: "Induces panic to prevent the victim from calmly making a direct phone call to verify."
        }
      ],
      next_move_prediction: "Follows up aggressively demanding additional money claiming surgical or compensation costs increased.",
      urgent_actions: [
        "Hang up and place a direct cellular call (GSM) to the family member",
        "Ask a personal question only the real person would know to verify identity"
      ],
      family_alert_card: {
        headline: "ALERT: DEEPFAKE VIDEO CALL MONEY REQUEST",
        key_warning: "Seeing a familiar face on a video call can still be an AI-generated fake!",
        shareable_text: "📢 WARNING: If you receive a video call from a relative asking for emergency money, hang up and call their direct phone number to verify!"
      }
    }
  },
  {
    id: "VN-FS-391804",
    timestamp: "2 hours ago",
    title: "Compromised Telegram Account: Fake Contest Voting Phishing",
    tag: "Account Takeover",
    summary: "Compromised friend account shares link to vote in photo contest, leading to phishing site harvesting Telegram login OTP.",
    views: 295,
    result: {
      scam_detected: true,
      risk_score: 89,
      threat_level: "HIGH" as const,
      scam_type: "Telegram Phishing & Session Hijacking",
      executive_summary: "Session hijacking attack stealing phone numbers and 2FA authentication codes via fraudulent contest portals.",
      web_intelligence: {
        detected: true,
        url: "https://vote-kids-2026.com/telegram-login",
        domain: "vote-kids-2026.com",
        brand_detected: "Telegram",
        domain_match: "mismatch" as const,
        website_status: "accessible" as const,
        suspicious_indicators: [
          "Phishing form spoofing Telegram login requesting phone number & OTP",
          "Disguised as a children's talent photo voting competition"
        ],
        external_evidence: [
          { title: "Official Telegram Portal", source_url: "https://telegram.org" },
          { title: "ChongLuaDao Telegram Phishing Advisory", source_url: "https://chongluadao.vn" }
        ],
        confidence: 92,
      },
      red_flags: [
        {
          evidence: "Requests Telegram OTP authentication code on vote-kids-2026.com",
          official_fact: "Telegram never prompts users to submit login OTP codes on external third-party websites.",
          official_link: "https://telegram.org",
          explanation: "Phishing voting websites intercept OTP codes to take over Telegram user sessions."
        },
        {
          evidence: "Spoofed domain vote-kids-2026.com",
          official_fact: "Legitimate Telegram authentication is strictly hosted on telegram.org domain infrastructure.",
          official_link: "https://telegram.org",
          explanation: "Disposable domain used to harvest active session tokens."
        }
      ],
      psychological_tricks: [
        {
          tactic: "Exploiting Social Goodwill",
          target_emotion: "Helpfulness",
          analysis: "Dispatches phishing lures from a known peer's compromised account to lower vigilance."
        }
      ],
      next_move_prediction: "Hijacks Telegram account and automatically blasts phishing lures to all contacts in address book.",
      urgent_actions: [
        "Open Telegram -> Settings -> Devices -> Terminate all other sessions",
        "Enable Two-Step Verification (cloud password)"
      ],
      family_alert_card: {
        headline: "ALERT: TELEGRAM PHOTO CONTEST TRAP",
        key_warning: "Never enter your Telegram login OTP on any external website!",
        shareable_text: "🚨 WARNING: If you receive a message asking to vote in a contest via Telegram, do not click links or enter your OTP or your account will be stolen!"
      }
    }
  }
];

const QUICK_ROLEPLAY_RESPONSES = [
  {
    label: "🛡️ Call Official Hotline",
    text: "I am hanging up to contact the official hotline of the institution directly. I do not take action through suspicious SMS or links.",
    isRisky: false,
  },
  {
    label: "🛡️ Decline & Report",
    text: "I am not interested. This is an obvious fraudulent scheme and I am reporting this sender immediately.",
    isRisky: false,
  },
  {
    label: "⚠️ Bait Trap: Provide OTP / Click Link",
    text: "Sure, please send me the link or I can read my OTP code to you right now to fix the issue!",
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
  const [roleplayLoading, setRoleplayLoading] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const reportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && !localStorage.getItem("scamshield-onboarded")) {
      setShowOnboarding(true);
    }
  }, []);

  const dismissOnboarding = () => {
    localStorage.setItem("scamshield-onboarded", "1");
    setShowOnboarding(false);
  };

  const generateId = () => `SCAM-FS-${Math.floor(100000 + Math.random() * 900000)}`;

  const getInitialRoleplayMessages = (res: ForensicResult | null): RoleplayMessage[] => {
    if (!res) return [];
    let scammerOpening = "🚨 [SIMULATED SCENARIO]: Urgent alert from the system! Your account has encountered a critical anomaly. Click the link or provide your OTP within 3 minutes!";
    if (res.red_flags?.[0]?.evidence) {
      scammerOpening = `🚨 [ACTIVE THREAT SCENARIO]: "${res.red_flags[0].evidence}" - You must comply with instructions immediately or face permanent suspension!`;
    } else if (res.scam_type) {
      scammerOpening = `🚨 [SIMULATED ${res.scam_type.toUpperCase()}]: The fraudster is pressuring you for emergency fund transfer, link activation, or OTP disclosure!`;
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
          title: result.family_alert_card.headline || "Fraud Security Alert",
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
      const isDangerous = isRiskyQuickChoice || lower.includes("otp") || lower.includes("password") || lower.includes("transfer") || lower.includes("click");
      setRoleplayMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          sender: "eval",
          text: isDangerous
            ? "⚠️ CRITICAL WARNING: Dangerous response — never provide OTP, passwords, or initiate funds transfer to unauthorized parties."
            : "✅ SECURE RESPONSE: Excellent composure — safely declining and verifying via authorized channels.",
          evalStatus: isDangerous ? "danger" : "safe",
        },
        {
          id: `s-${Date.now()}`,
          sender: "scammer",
          text: isDangerous ? "Trap succeeded! The fraudster has gained control of your credentials. Learn from this simulation." : "The fraudster failed to intimidate you and abandoned the attack to target someone else.",
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
        backgroundColor: "#060913",
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
        res = await fetch("/api/analyze", { method: "POST", body: fd });
      } else {
        if (!textInput.trim()) return;
        res = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ textInput }),
        });
      }
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        let rawErr = errData.error || "Forensic analysis failed";
        if (typeof rawErr === "object") rawErr = JSON.stringify(rawErr);
        if (typeof rawErr === "string" && (rawErr.includes("API key not valid") || rawErr.includes("INVALID_ARGUMENT"))) {
          rawErr = "⚠️ GEMINI_API_KEY is missing or invalid. Please configure GEMINI_API_KEY in your environment.";
        }
        throw new Error(rawErr);
      }
      const analysisData: ForensicResult = await res.json();
      const newId = generateId();
      setCaseId(newId);
      setResult(analysisData);
      setRoleplayMessages(getInitialRoleplayMessages(analysisData));
      setActiveTab("overview");

      // Auto-prepend new case to Community Feed
      const newFeedItem: CommunityFeedItem = {
        id: newId,
        timestamp: "Just now",
        title: inputMode === "image" ? (file?.name ? `Image: ${file.name}` : "Suspicious Screenshot") : (textInput.slice(0, 30) + "..."),
        tag: analysisData.scam_type || "New Alert",
        summary: analysisData.executive_summary || "Investigation completed successfully",
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
              <div className="text-[11px] text-slate-400">Digital Forensic Investigation & Multimodal Cognitive Deception Defense</div>
            </div>
          </div>
          <div className="text-xs text-slate-300 border border-slate-800 bg-slate-900 px-3 py-1.5 rounded-full font-mono flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-cyan-400" /> Gemini 2.5 Flash
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 mt-8">
        {showOnboarding && (
          <div className="mb-6 bg-gradient-to-r from-cyan-950/60 to-indigo-950/60 border border-cyan-500/30 rounded-2xl p-4 print:hidden relative">
            <button onClick={dismissOnboarding} className="absolute top-3 right-3 text-slate-400 hover:text-white cursor-pointer" aria-label="Dismiss guide">
              <X className="w-4 h-4" />
            </button>
            <div className="flex items-start gap-3">
              <HelpCircle className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <div className="text-sm font-bold text-cyan-200 mb-2">3-Step Quick Guide — Accessible to Everyone</div>
                <ol className="text-xs text-slate-300 space-y-1.5 list-decimal list-inside">
                  <li><strong>Screenshot</strong> suspicious SMS/chat or <strong>paste</strong> suspicious URLs / text</li>
                  <li>Click <strong>Start Forensic Analysis</strong> — AI evaluates in ~10 seconds</li>
                  <li>Review the report → <strong>Share emergency alert</strong> with friends and family</li>
                </ol>
              </div>
            </div>
          </div>
        )}

        <div className="text-center max-w-2xl mx-auto mb-6 print:hidden">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-950/30 text-cyan-300 text-xs font-semibold mb-2">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" /> AI Riser Vietnam 2026
          </div>
          <h1 className="text-3xl sm:text-4xl font-black">
            Forensic Scam Detection & Cognitive Deception Analysis
          </h1>
        </div>

        {/* Quick presets */}
        <div className="mb-6 bg-slate-900/40 border border-slate-800 rounded-2xl p-3.5 print:hidden">
          <div className="text-[11px] font-bold text-slate-400 uppercase mb-2 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-cyan-400" /> Real-world Forensic Cases:
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
                  <ImageIcon className="w-3.5 h-3.5" /> Image Scan
                </button>
                <button
                  onClick={() => { setInputMode("text"); setResult(null); }}
                  className={`flex-1 py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition ${inputMode === "text" ? "bg-cyan-600 text-white" : "text-slate-400"}`}
                >
                  <Link2 className="w-3.5 h-3.5" /> Text / URL Scan
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
                      <div className="text-xs font-semibold text-slate-300">Drag & drop or click to upload screenshot</div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <label className="text-xs font-bold text-slate-300">Paste suspicious message text, email, or URL:</label>
                  <textarea
                    rows={6}
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    placeholder="Example: 'Notice: Your banking profile has been restricted due to abnormal activity. Visit https://vietcombank-login.vip immediately to verify...'"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
              )}

              {((inputMode === "image" && file) || (inputMode === "text" && textInput.trim())) && !loading && (
                <button
                  onClick={runAnalysis}
                  className="w-full py-3 bg-gradient-to-r from-cyan-600 to-indigo-600 font-bold text-xs rounded-xl shadow-lg flex items-center justify-center gap-2 cursor-pointer active:scale-95 text-white"
                >
                  <FileSearch className="w-4 h-4" /> Start Forensic Analysis
                </button>
              )}

              {error && <div className="p-3 bg-red-950/60 border border-red-800 rounded-xl text-red-300 text-xs">{error}</div>}
            </div>
          </div>

          {/* Results Display */}
          {result && (
            <div ref={reportRef} className="lg:col-span-7 space-y-4 print:w-full print:col-span-12">
              <div className="flex justify-between items-center bg-slate-900/80 p-3 rounded-xl border border-slate-800 print:hidden flex-wrap gap-2">
                <div className="text-xs font-mono text-slate-400">CASE ID: <strong className="text-cyan-300">{caseId}</strong></div>
                <div className="flex gap-2">
                  <button onClick={handleExportPdf} disabled={exportingPdf} className="text-xs bg-slate-800 text-cyan-300 px-3 py-1.5 rounded-lg border border-cyan-500/30 flex items-center gap-1.5 cursor-pointer hover:bg-slate-700 transition disabled:opacity-50">
                    <FileDown className="w-3.5 h-3.5" /> {exportingPdf ? "Exporting..." : "Download PDF"}
                  </button>
                  <button onClick={() => window.print()} className="text-xs bg-slate-800 text-cyan-300 px-3 py-1.5 rounded-lg border border-cyan-500/30 flex items-center gap-1.5 cursor-pointer hover:bg-slate-700 transition">
                    <Printer className="w-3.5 h-3.5" /> Print Report
                  </button>
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-16 h-16 rounded-xl border-2 flex flex-col items-center justify-center font-black ${result.risk_score >= 75 ? "text-red-400 border-red-500 bg-red-950/30" : "text-emerald-400 border-emerald-500 bg-emerald-950/30"}`}>
                    <span className="text-2xl">{result.risk_score}</span>
                    <span className="text-[8px]">SCORE</span>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400">Threat Category</div>
                    <div className="text-lg font-bold">{result.scam_type}</div>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-red-500/20 text-red-400 font-bold">{result.threat_level}</span>
                  </div>
                </div>
              </div>

              {/* WEB INTELLIGENCE Section */}
              {result.web_intelligence?.detected && (
                <div className="p-4 rounded-xl bg-slate-900/90 border border-cyan-500/30 space-y-3 font-sans">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 gap-2 flex-wrap">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="text-[10px] uppercase tracking-wider font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 flex items-center gap-1 shrink-0">
                        <Globe className="w-3 h-3 text-cyan-400" /> WEB INTELLIGENCE
                      </span>
                      <span className="text-xs font-mono font-semibold text-slate-200 truncate max-w-[200px] sm:max-w-xs">
                        {result.web_intelligence.domain || result.web_intelligence.url}
                      </span>
                    </div>

                    {/* Domain Match Status Badge */}
                    {result.web_intelligence.domain_match === "mismatch" ? (
                      <span className="text-[10px] font-bold px-2.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/40 flex items-center gap-1 font-mono shrink-0">
                        🚨 Fraudulent Domain (MISMATCH)
                      </span>
                    ) : result.web_intelligence.domain_match === "match" ? (
                      <span className="text-[10px] font-bold px-2.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center gap-1 font-mono shrink-0">
                        ✅ Legitimate Domain (MATCH)
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold px-2.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1 font-mono shrink-0">
                        ⚠️ Unverified Match (UNKNOWN)
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                      <div className="text-[10px] text-slate-400 font-bold uppercase">Claimed Brand / Impersonation Target:</div>
                      <div className="font-bold text-slate-200">{result.web_intelligence.brand_detected || "Unidentified"}</div>
                    </div>
                    <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                      <div className="text-[10px] text-slate-400 font-bold uppercase">Web Verification Confidence:</div>
                      <div className="font-bold text-cyan-300 font-mono">{result.web_intelligence.confidence}% Confidence</div>
                      {result.web_intelligence.verified_live !== undefined && (
                        <div className={`text-[10px] font-bold ${result.web_intelligence.verified_live ? "text-emerald-400" : "text-amber-400"}`}>
                          {result.web_intelligence.verified_live
                            ? `✓ Verified Live HTTP ${result.web_intelligence.http_status ?? "OK"}`
                            : "⚠ URL unreachable during live probe"}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Suspicious Indicators */}
                  {result.web_intelligence.suspicious_indicators?.length > 0 && (
                    <div className="space-y-1">
                      <div className="text-[10px] font-bold text-red-400 uppercase">Suspicious Web Behaviors:</div>
                      <div className="flex flex-wrap gap-1.5">
                        {result.web_intelligence.suspicious_indicators.map((ind, idx) => (
                          <span key={idx} className="text-[11px] px-2 py-0.5 bg-red-950/60 border border-red-800/60 text-red-300 rounded-md">
                            • {ind}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* External Evidence with Clickable Source Links */}
                  {result.web_intelligence.external_evidence?.length > 0 && (
                    <div className="space-y-1.5">
                      <div className="text-[10px] font-bold text-cyan-300 uppercase flex items-center gap-1">
                        EXTERNAL EVIDENCE BENCHMARKS (CLICK TO VERIFY):
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
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
                              className="group/link text-[11px] text-slate-200 bg-slate-950 hover:bg-slate-900 p-2.5 rounded-lg border border-slate-800 hover:border-cyan-500/50 flex items-center justify-between gap-2 transition cursor-pointer"
                            >
                              <span className="truncate group-hover/link:text-cyan-300 transition">
                                🔍 {title}
                              </span>
                              <ExternalLink className="w-3.5 h-3.5 text-cyan-400 shrink-0 opacity-70 group-hover/link:opacity-100 transition" />
                            </a>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

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
                    {tab === "overview" && "Forensic Evidence"}
                    {tab === "psychology" && "Cognitive Deception"}
                    {tab === "family" && "Family Alert Card"}
                    {tab === "roleplay" && "🎯 Roleplay Reflex Lab"}
                  </button>
                ))}
              </div>

              {/* Tab 1: Overview */}
              {activeTab === "overview" && (
                <div className="space-y-3">
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                    <div className="text-xs font-bold text-slate-300">Executive Forensic Summary:</div>
                    <p className="text-xs text-slate-400 leading-relaxed">{result.executive_summary}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                    <div className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-red-400" /> Ground-Truth Evidence Comparator:
                    </div>
                    <div className="space-y-3">
                      {result.red_flags.map((f, i) => (
                        <div key={i} className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl text-xs space-y-2">
                          {/* Row 1: Evidence (Detected - Red) */}
                          <div className="flex items-start gap-2 bg-red-950/40 border border-red-900/40 p-2.5 rounded-lg text-red-300">
                            <span className="px-1.5 py-0.5 rounded bg-red-900/70 text-red-200 text-[10px] font-bold uppercase shrink-0 font-mono">
                              [Detected in Data]
                            </span>
                            <span className="font-bold">{f.evidence}</span>
                          </div>

                          {/* Row 2: Official Fact (Official benchmark - Green/Emerald) + Clickable Official Link */}
                          <div className="flex items-center justify-between gap-2 bg-emerald-950/40 border border-emerald-900/40 p-2.5 rounded-lg text-emerald-300 flex-wrap">
                            <div className="flex items-start gap-2">
                              <span className="px-1.5 py-0.5 rounded bg-emerald-900/70 text-emerald-200 text-[10px] font-bold uppercase shrink-0 font-mono">
                                [Official Benchmark]
                              </span>
                              <span className="font-semibold">{f.official_fact || f.explanation}</span>
                            </div>
                            {f.official_link && (
                              <a
                                href={f.official_link}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-bold bg-emerald-900/60 hover:bg-emerald-800/80 text-emerald-200 rounded border border-emerald-700/50 transition cursor-pointer shrink-0 font-mono"
                              >
                                <span>Source</span>
                                <ExternalLink className="w-3 h-3 text-emerald-300" />
                              </a>
                            )}
                          </div>

                          {/* Row 3: Explanation */}
                          <div className="text-slate-400 pl-1 text-[11px] leading-relaxed pt-0.5">
                            💡 <strong className="text-slate-300">Forensic Analysis:</strong> {f.explanation}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                    <div className="text-xs font-bold text-amber-300">60-Second Emergency Actions:</div>
                    {result.urgent_actions.map((a, i) => (
                      <div key={i} className="text-xs text-slate-300 flex items-center gap-1.5"><Zap className="w-3.5 h-3.5 text-cyan-400" /> {a}</div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tab 2: Psychology */}
              {activeTab === "psychology" && (
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                  <div className="text-xs font-bold text-purple-300">Psychological Exploitation Tactics:</div>
                  {result.psychological_tricks.map((t, i) => (
                    <div key={i} className="p-3 bg-slate-950 rounded-lg text-xs space-y-1 border border-purple-900/30">
                      <div className="flex justify-between font-bold text-purple-300">
                        <span>{t.tactic}</span>
                        <span className="text-[10px] px-2 py-0.5 bg-purple-950 rounded text-purple-400">Target Emotion: {t.target_emotion}</span>
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
                    <span className="text-xs font-bold text-indigo-300">Quick Family Emergency Dispatch (Messaging/Telegram):</span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <button
                        onClick={() => {
                          const text = encodeURIComponent(result.family_alert_card.shareable_text);
                          window.open(`https://api.whatsapp.com/send?text=${text}`, "_blank");
                        }}
                        className="text-xs bg-[#25D366] hover:bg-[#20ba5a] text-white px-2.5 py-1 rounded-md flex items-center gap-1 cursor-pointer font-semibold transition"
                      >
                        <Share2 className="w-3.5 h-3.5" /> WhatsApp / Chat
                      </button>

                      <button
                        onClick={() => {
                          const text = encodeURIComponent(result.family_alert_card.shareable_text);
                          const url = encodeURIComponent(typeof window !== "undefined" ? window.location.href : "");
                          window.open(`https://t.me/share/url?url=${url}&text=${text}`, "_blank");
                        }}
                        className="text-xs bg-[#24A1DE] hover:bg-[#1f8ec4] text-white px-2.5 py-1 rounded-md flex items-center gap-1 cursor-pointer font-semibold transition"
                      >
                        <Send className="w-3.5 h-3.5" /> Telegram
                      </button>

                      <button
                        onClick={handleNativeShare}
                        className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-2.5 py-1 rounded-md flex items-center gap-1 cursor-pointer font-semibold transition"
                      >
                        {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        {copied ? "Copied!" : "Copy"}
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
                        <Gamepad2 className="w-4 h-4 text-cyan-400" /> Anti-Fraud Reflex Simulation (Roleplay Lab)
                      </div>
                      <div className="text-[11px] text-slate-400">Powered by Gemini 2.5 Flash — practice countering active fraud scenarios in real time</div>
                    </div>
                    <button
                      onClick={() => setRoleplayMessages(getInitialRoleplayMessages(result))}
                      className="text-[11px] px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg flex items-center gap-1 cursor-pointer transition border border-slate-700"
                    >
                      <RefreshCw className="w-3 h-3 text-cyan-400" /> Reset
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
                              <div className="text-[9px] font-bold text-red-400 uppercase mb-1">Scammer (Gemini AI)</div>
                              {msg.text}
                            </div>
                          </div>
                        );
                      }
                      if (msg.sender === "user") {
                        return (
                          <div key={msg.id} className="flex gap-2.5 items-start justify-end ml-auto max-w-[88%]">
                            <div className="bg-cyan-950/60 border border-cyan-800/50 rounded-2xl rounded-tr-none p-3 text-xs text-cyan-100 leading-relaxed">
                              <div className="text-[9px] font-bold text-cyan-400 uppercase mb-1 text-right">You (Target)</div>
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
                    <div className="text-[10px] uppercase font-bold text-slate-400">Quick Reflex Responses (Click to test):</div>
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
                      placeholder="Enter your response to counter the fraudster..."
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-sans"
                    />
                    <button
                      type="submit"
                      className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-indigo-600 font-bold text-xs rounded-xl shadow-lg flex items-center gap-1.5 cursor-pointer active:scale-95 text-white"
                    >
                      <Send className="w-3.5 h-3.5" /> Send
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
                <p className="text-xs text-slate-400">Latest scam threats identified and verified by community members</p>
              </div>
            </div>
            <div className="text-xs text-slate-400 font-mono flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 self-start sm:self-auto">
              <Flame className="w-3.5 h-3.5 text-amber-400 animate-bounce" /> {communityFeed.length} cases recorded
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
                    <Eye className="w-3.5 h-3.5 text-cyan-400/80" /> {item.views} views
                  </span>
                  <span className="text-cyan-400 font-bold group-hover:translate-x-0.5 transition flex items-center gap-1">
                    Inspect Case <ArrowUpRight className="w-3.5 h-3.5" />
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