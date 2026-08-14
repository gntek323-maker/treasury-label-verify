# Technical Documentation: AI-Powered Alcohol Label Verification

## Approach

### Problem Analysis

After reviewing the stakeholder interviews, I identified these core requirements:
1. **Speed**: Must return results in under 5 seconds (previous vendor failed at 30-40 seconds)
2. **Simplicity**: UI must be usable by staff aged 25-65+ with varying technical comfort
3. **Smart Matching**: Handle case/punctuation variations for brand names (fuzzy matching)
4. **Strict Matching**: Government warning must be verified exactly (word-for-word, ALL CAPS header)
5. **Batch Capability**: Support 200-300 label uploads for bulk importers
6. **Image Tolerance**: Handle imperfect photos (angles, glare, lighting)

### Architecture Decision

I chose a **separated architecture** with three layers:

1. **React Frontend** — Clean, minimal UI with large buttons and clear visual feedback
2. **FastAPI Backend** — Python async framework handling request orchestration and comparison logic
3. **AI/OCR Layer** — Google Gemini Vision for text extraction from label images

**Why this separation matters:**
- The AI model can be swapped (e.g., to Azure AI Vision for FedRAMP compliance) without touching the frontend or comparison logic
- The comparison logic is independent of how text is extracted — could work with manual text input, OCR, or any vision AI
- Each layer scales independently

### AI Model Choice: Google Gemini Vision

| Criteria | Gemini Vision | Tesseract OCR |
|----------|-------------|---------------|
| Angled images | ✅ Handles naturally | ❌ Struggles |
| Glare/lighting | ✅ Understands context | ❌ Poor accuracy |
| Decorative fonts | ✅ Recognizes stylized text | ❌ Often fails |
| Speed | ~2-4 seconds | ~1-2 seconds |
| Cost | Free tier (15 req/min) | Free |
| Offline capable | ❌ Requires API | ✅ Runs locally |
| Production path | Azure AI Vision (FedRAMP) | Self-hosted |

**Decision:** Google Gemini Vision for the prototype because it handles the real-world image quality issues stakeholders described, and has a generous free tier. For production, recommend Azure AI Vision (FedRAMP authorized) as a drop-in replacement.

### Matching Strategy

Each field uses the appropriate matching type:

- **Fuzzy Matching** (brand name, class/type, producer): Normalizes case, punctuation, and whitespace before comparing. Uses word-level Jaccard similarity for partial matches. This handles cases like "STONE'S THROW" vs "Stone's Throw" that Dave mentioned.

- **Numeric Matching** (alcohol content, net contents): Extracts numeric values and compares. "45% Alc./Vol. (90 Proof)" matches "45%" because the core number is the same.

- **Strict Matching** (government warning): Must be word-for-word exact. Additionally checks that "GOVERNMENT WARNING:" appears in ALL CAPS, as required by TTB regulations and noted by Jenny.

### Confidence Scoring and Human-in-the-Loop

Every comparison produces a confidence score (0-100%):
- **90-100%**: High confidence match — agent can approve quickly
- **70-89%**: Moderate confidence — flagged for human glance
- **Below 70%**: Low confidence — requires human review

This follows responsible AI principles: the AI assists by flagging obvious matches and mismatches, but a human makes the final determination. The system is designed to speed up the agent's workflow, not replace their judgment.

## Tools Used

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Backend language |
| FastAPI | Async web framework (fast, production-ready) |
| Google Gemini 2.0 Flash | Vision AI for label text extraction |
| React 18 | Frontend framework |
| Tailwind CSS | Styling (clean, accessible defaults) |
| Vite | Frontend build tool |
| Pydantic | Data validation (backend) |

## Assumptions Made

1. **Prototype scope**: This is a standalone proof-of-concept, not integrated with COLA
2. **Security**: No PII is stored; images are processed in memory and discarded
3. **API availability**: Google Gemini free tier is acceptable for prototype evaluation
4. **Single user**: Designed for single concurrent user (production would add queuing)
5. **Image format**: Users can photograph or scan labels and upload as JPEG/PNG
6. **Government warning text**: Standard TTB warning text is provided in the application data

## Trade-offs and Limitations

| Trade-off | Chose | Over | Because |
|-----------|-------|------|---------|
| AI accuracy | Gemini Vision | Tesseract | Better handling of real-world image quality |
| Speed | ~3 second response | Sub-1 second | Accuracy matters more than milliseconds for compliance |
| Storage | Stateless (no persistence) | Full audit trail | Prototype scope; production would add database |
| Deployment | Cloud API dependency | Self-hosted model | Faster to build and evaluate |
| Batch processing | Sequential | Parallel | Simpler, reliable; production would use worker queues |

## Security Considerations (Production)

For a production deployment, I would add:
- FedRAMP-authorized AI service (Azure AI Vision) instead of Google Gemini
- Data encryption in transit (TLS 1.2+) and at rest
- Authentication via agency SSO/LDAP
- Role-based access control (agent, supervisor, admin)
- Complete audit trail (every verification logged with timestamp, user, result)
- Image data retention policy compliance
- Network segmentation (AI service behind internal load balancer)
- Input validation and sanitization at every layer

## Running the Application

### Quick Start

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
echo GEMINI_API_KEY=your-key > .env
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Testing

1. Open `http://localhost:5173`
2. Upload a label image (generate one with AI image tools or photograph a real label)
3. Fill in the application data fields
4. Click "Verify Label"
5. Review results — matches shown in green, mismatches in red

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /verify | Single label verification |
| POST | /verify/batch | Batch verification |
| GET | /model/info | AI model information and transparency |
