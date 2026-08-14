# AI-Powered Alcohol Label Verification App

## Project Overview

An AI-powered web application that assists TTB (Alcohol and Tobacco Tax and Trade Bureau) compliance agents in verifying alcohol beverage labels against application data. The system uses computer vision to extract text from label images and automatically compares it against submitted application information, flagging matches and mismatches.

## Live Demo

https://treasury-label-verify-1.onrender.com

## Problem Statement

TTB reviews approximately 150,000 label applications per year with 47 agents. Much of the review process involves manual verification — visually comparing label text against application data. This tool automates the matching/comparison step, allowing agents to focus on nuanced judgment calls rather than routine data verification.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React         │────▶│   FastAPI        │────▶│   Google        │
│   Frontend      │     │   Backend        │     │   Gemini Vision │
│   (Simple UI)   │◀────│   (Python)       │◀────│   (OCR + NLP)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │
         │                       ▼
         │              ┌─────────────────┐
         └─────────────▶│   Results       │
                        │   Dashboard     │
                        └─────────────────┘
```

### Why This Architecture:

- **Separate AI service layer**: AI/OCR logic is decoupled from the web application, allowing model swapping without touching the frontend (e.g., switching from Gemini to an on-premises OCR solution for production FedRAMP compliance)
- **FastAPI backend**: Async Python framework — handles concurrent requests efficiently, sub-5-second response time requirement
- **React frontend**: Clean, accessible UI designed for users with varying technical comfort levels (ages 25-65+)
- **Stateless design**: No sensitive data stored — images are processed and discarded (prototype security consideration)

## Key Features

1. **Single Label Verification** — Upload one label image + application data → instant comparison results
2. **Batch Upload** — Upload multiple labels at once for bulk processing (supports 200-300 labels)
3. **Smart Matching** — Fuzzy matching for brand names (handles case differences, punctuation variations)
4. **Strict Matching** — Exact verification for Government Warning Statement (all caps, correct wording)
5. **Confidence Scoring** — Each field comparison returns a confidence level; low confidence flags for human review
6. **Response Time** — Results returned in under 5 seconds per label
7. **Accessible UI** — Large buttons, clear status indicators, minimal clicks required

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18 | Component-based, accessible, widely supported |
| Backend | Python FastAPI | Async, fast, great for AI/ML workloads |
| AI/OCR | Google Gemini Vision | Best accuracy for imperfect images (angles, glare, lighting), free tier |
| Styling | Tailwind CSS | Clean, responsive, accessible defaults |
| Deployment | Render / Railway | Simple deployment, free tier available |

## Setup and Run Instructions

### Prerequisites

- Node.js 18+ (frontend)
- Python 3.10+ (backend)
- Google Gemini API key (free tier)

### Backend Setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt

# Create .env file
echo GEMINI_API_KEY=your-key-here > .env

# Run the server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`

## Approach and Design Decisions

### AI Strategy: Gemini Vision over Traditional OCR

**Trade-off considered:** Traditional OCR (Tesseract) is free and runs locally, but struggles with:
- Angled/rotated label photos
- Glare on glass bottles
- Decorative/stylized fonts common on alcohol labels
- Complex label layouts

Gemini Vision handles all of these naturally because it understands visual context, not just pixel patterns.

**Production consideration:** For a FedRAMP-compliant production deployment, the AI layer could be swapped to Azure AI Vision (FedRAMP authorized) or an on-premises model without changing the rest of the architecture. The AI service is deliberately isolated behind a clean API interface for this reason.

### Matching Logic

| Field | Match Type | Rationale |
|-------|-----------|-----------|
| Brand Name | Fuzzy (case-insensitive, punctuation-normalized) | Per stakeholder feedback: "STONE'S THROW" vs "Stone's Throw" should match |
| Class/Type | Fuzzy | Minor wording variations acceptable |
| Alcohol Content | Numeric extraction + comparison | "45% Alc./Vol." should match "45%" |
| Net Contents | Numeric extraction + unit normalization | "750 mL" = "750ml" |
| Government Warning | Strict exact match | Per TTB requirements: must be word-for-word, "GOVERNMENT WARNING:" in all caps |
| Producer/Bottler | Fuzzy | Address formatting may vary |

### Confidence Scoring

Each field comparison produces a confidence score (0-100%):
- **90-100%**: Strong match — auto-approve
- **70-89%**: Likely match — flagged for quick human glance
- **Below 70%**: Uncertain — requires human review

This follows the responsible AI principle of human-in-the-loop design: AI assists, humans decide.

## Assumptions

1. This is a standalone prototype — no integration with the existing COLA system
2. No sensitive/PII data is stored (images are processed in memory and discarded)
3. Google Gemini API is acceptable for prototype (production would use FedRAMP-authorized service)
4. Users have modern web browsers (Chrome, Edge, Firefox — last 2 versions)
5. Single concurrent user for prototype (production would need load balancing)

## Limitations and Future Improvements

- **Rate limiting**: Gemini API has rate limits (15 req/min on free tier) that would need management at scale
- **Offline capability**: Current version requires internet; production could use on-premises model
- **Batch processing**: Currently sequential; production could parallelize with worker queues
- **Audit trail**: Prototype doesn't persist results; production would need full audit logging
- **Accessibility**: Basic WCAG 2.1 compliance implemented; full accessibility audit recommended for production

## Author

Neeraj Giri
