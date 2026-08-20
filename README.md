# ScamShield Forensic AI

> Giám định pháp y số & giải mã thao túng đa phương thức — dự án **AI Riser Vietnam 2026** (hạng mục Phòng chống lừa đảo)

Ứng dụng web giúp người Việt **phát hiện lừa đảo** qua ảnh chụp màn hình hoặc tin nhắn/link, powered by **Google Gemini 2.5 Flash**.

## Tính năng

- **Quét ảnh / text / URL** — phân tích đa phương thức bằng Gemini
- **Báo cáo pháp y** — risk score, dấu hiệu vi phạm, so sánh bằng chứng
- **Web Intelligence** — verify domain thật (HTTP check + đối chiếu brand VN)
- **Giải mã tâm lý** — chiêu trò thao túng cảm xúc của kẻ lừa đảo
- **Thẻ cảnh báo gia đình** — chia sẻ nhanh qua Zalo / Telegram
- **Roleplay Lab** — luyện phản xạ với AI mô phỏng kẻ lừa đảo
- **3 ca demo Việt Nam** — Solana drainer, SMS ngân hàng, CTV Shopee

## Tech Stack

| Layer | Công nghệ |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| AI | Google Gemini 2.5 Flash (`@google/genai`) |
| Deploy | Docker → Google Cloud Run |

## Cài đặt local

```bash
git clone https://github.com/maingiangu-svg/ScamGuard-AI.git
cd ScamGuard-AI
npm install
cp .env.example .env.local
# Điền GEMINI_API_KEY tại https://aistudio.google.com/apikey
npm run dev
```

Mở [http://localhost:3000](http://localhost:3000)

## Deploy Google Cloud Run (+10 điểm bonus AI Riser)

```bash
export GCP_PROJECT_ID=your-project-id
export GEMINI_API_KEY=your-gemini-key
chmod +x scripts/deploy-cloud-run.sh
./scripts/deploy-cloud-run.sh
```

Hoặc deploy thủ công:

```bash
gcloud run deploy scamshield-forensic \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=xxx
```

## Quy trình Google AI Studio

1. Thiết kế prompt & schema tại [Google AI Studio](https://aistudio.google.com)
2. Export logic sang Next.js API Route (`src/app/api/analyze/route.ts`)
3. Deploy lên Cloud Run

## AI Riser Vietnam 2026

- **Chủ đề:** Phòng chống lừa đảo
- **Đăng ký:** [goo.gle/airiservietnam](https://goo.gle/airiservietnam) (đến 30/8/2026)
- **Hashtag:** #BuildwithGoogleAI #VibeCoding #AIRiserVietnam

## License

MIT
