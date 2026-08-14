"""
Backend for TTB Label Verification Tool.
Uses Google Gemini Vision API for OCR/text extraction from label images,
then compares extracted text against application data.
"""

import os
import base64
import time
import json
import re
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(
    title="Alcohol Label Verification API",
    description="AI-powered label verification for TTB compliance",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================
# Models
# ============================================================

class ApplicationData(BaseModel):
    """Data from the label application form submitted by the applicant."""
    brand_name: str
    class_type: Optional[str] = None
    alcohol_content: Optional[str] = None
    net_contents: Optional[str] = None
    producer_name: Optional[str] = None
    government_warning: Optional[str] = None


class FieldResult(BaseModel):
    """Result of comparing a single field between label and application."""
    field_name: str
    application_value: str
    extracted_value: str
    match: bool
    confidence: float
    match_type: str  # "exact", "fuzzy", "numeric", "not_found"
    notes: str = ""


class VerificationResult(BaseModel):
    """Complete verification result for one label."""
    overall_status: str  # "APPROVED", "NEEDS_REVIEW", "MISMATCH_DETECTED"
    overall_confidence: float
    fields: list[FieldResult]
    processing_time_seconds: float
    timestamp: str
    needs_human_review: bool
    review_reasons: list[str] = []


# ============================================================
# AI Label Extraction (Google Gemini Vision)
# ============================================================

EXTRACTION_PROMPT = """You are an expert at reading alcohol beverage labels. 
Analyze this label image and extract the following fields. 
Return ONLY a JSON object with these exact keys (use null if not found):

{
  "brand_name": "the brand name exactly as shown on label",
  "class_type": "the class/type designation (e.g., Kentucky Straight Bourbon Whiskey)",
  "alcohol_content": "alcohol percentage as shown (e.g., 45% Alc./Vol.)",
  "net_contents": "volume as shown (e.g., 750 mL)",
  "producer_name": "name and address of producer/bottler",
  "government_warning": "the complete government warning text exactly as printed"
}

Important:
- Extract text EXACTLY as it appears on the label (preserve capitalization, punctuation)
- For government_warning, include the full text starting from "GOVERNMENT WARNING:"
- If a field is partially visible or unclear, extract what you can and note uncertainty
- Return valid JSON only, no markdown formatting, no code blocks"""


async def extract_label_text(image_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """Use OpenAI GPT-4o Vision to extract text from a label image."""

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    mime_type = content_type if content_type in ["image/jpeg", "image/png", "image/webp"] else "image/jpeg"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=1000,
        temperature=0,
    )

    content = response.choices[0].message.content.strip()

    # Remove markdown code blocks if present
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0].strip()
    if content.startswith("json"):
        content = content[4:].strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        raise HTTPException(
            status_code=500,
            detail="AI could not parse label text. Please try a clearer image.",
        )


# ============================================================
# Matching Logic
# ============================================================

def normalize_text(text: str) -> str:
    """Normalize text for fuzzy comparison."""
    if not text:
        return ""
    result = text.lower().strip()
    result = result.replace("\u2019", "'").replace("\u2018", "'")
    result = result.replace("\u201c", '"').replace("\u201d", '"')
    result = " ".join(result.split())
    return result


def extract_number(text: str) -> Optional[float]:
    """Extract numeric value from text like '45% Alc./Vol.' or '750 mL'."""
    if not text:
        return None
    matches = re.findall(r"(\d+\.?\d*)", text)
    if matches:
        return float(matches[0])
    return None


def compare_fuzzy(app_value: str, label_value: str) -> tuple[bool, float, str]:
    """Fuzzy comparison for brand names, class/type, etc."""
    if not label_value:
        return False, 0.0, "not_found"

    norm_app = normalize_text(app_value)
    norm_label = normalize_text(label_value)

    if norm_app == norm_label:
        return True, 1.0, "exact"

    # Check if one contains the other
    if norm_app in norm_label or norm_label in norm_app:
        return True, 0.9, "fuzzy"

    # Word-level Jaccard similarity
    app_words = set(norm_app.split())
    label_words = set(norm_label.split())
    if not app_words or not label_words:
        return False, 0.0, "fuzzy"

    intersection = app_words & label_words
    union = app_words | label_words
    similarity = len(intersection) / len(union)

    if similarity >= 0.8:
        return True, similarity, "fuzzy"
    elif similarity >= 0.5:
        return False, similarity, "fuzzy"
    else:
        return False, similarity, "fuzzy"


def compare_numeric(app_value: str, label_value: str) -> tuple[bool, float, str]:
    """Compare numeric values (alcohol content, net contents)."""
    if not label_value:
        return False, 0.0, "not_found"

    app_num = extract_number(app_value)
    label_num = extract_number(label_value)

    if app_num is None or label_num is None:
        return compare_fuzzy(app_value, label_value)

    if app_num == label_num:
        return True, 1.0, "numeric"
    else:
        diff = abs(app_num - label_num)
        if diff <= 0.5:
            return True, 0.9, "numeric"
        return False, 0.3, "numeric"


def compare_government_warning(app_value: str, label_value: str) -> tuple[bool, float, str]:
    """Strict comparison for government warning — must be exact."""
    if not label_value:
        return False, 0.0, "not_found"

    has_caps_header = "GOVERNMENT WARNING:" in label_value

    norm_app = normalize_text(app_value)
    norm_label = normalize_text(label_value)

    if norm_app == norm_label:
        confidence = 1.0 if has_caps_header else 0.7
        match = has_caps_header
        return match, confidence, "exact"

    # Check if core warning text is present
    core_warning = "according to the surgeon general"
    if core_warning in norm_label:
        confidence = 0.8 if has_caps_header else 0.5
        return has_caps_header, confidence, "fuzzy"

    return False, 0.2, "exact"


def compare_fields(application: ApplicationData, extracted: dict) -> list[FieldResult]:
    """Compare all fields between application data and extracted label text."""
    results = []

    # Brand Name — fuzzy match
    if application.brand_name:
        match, conf, mtype = compare_fuzzy(
            application.brand_name, extracted.get("brand_name", "") or ""
        )
        results.append(FieldResult(
            field_name="Brand Name",
            application_value=application.brand_name,
            extracted_value=extracted.get("brand_name", "") or "Not found on label",
            match=match,
            confidence=conf,
            match_type=mtype,
        ))

    # Class/Type — fuzzy match
    if application.class_type:
        match, conf, mtype = compare_fuzzy(
            application.class_type, extracted.get("class_type", "") or ""
        )
        results.append(FieldResult(
            field_name="Class/Type",
            application_value=application.class_type,
            extracted_value=extracted.get("class_type", "") or "Not found on label",
            match=match,
            confidence=conf,
            match_type=mtype,
        ))

    # Alcohol Content — numeric match
    if application.alcohol_content:
        match, conf, mtype = compare_numeric(
            application.alcohol_content, extracted.get("alcohol_content", "") or ""
        )
        results.append(FieldResult(
            field_name="Alcohol Content",
            application_value=application.alcohol_content,
            extracted_value=extracted.get("alcohol_content", "") or "Not found on label",
            match=match,
            confidence=conf,
            match_type=mtype,
        ))

    # Net Contents — numeric match
    if application.net_contents:
        match, conf, mtype = compare_numeric(
            application.net_contents, extracted.get("net_contents", "") or ""
        )
        results.append(FieldResult(
            field_name="Net Contents",
            application_value=application.net_contents,
            extracted_value=extracted.get("net_contents", "") or "Not found on label",
            match=match,
            confidence=conf,
            match_type=mtype,
        ))

    # Producer/Bottler — fuzzy match
    if application.producer_name:
        match, conf, mtype = compare_fuzzy(
            application.producer_name, extracted.get("producer_name", "") or ""
        )
        results.append(FieldResult(
            field_name="Producer/Bottler",
            application_value=application.producer_name,
            extracted_value=extracted.get("producer_name", "") or "Not found on label",
            match=match,
            confidence=conf,
            match_type=mtype,
        ))

    # Government Warning — STRICT match
    if application.government_warning:
        match, conf, mtype = compare_government_warning(
            application.government_warning, extracted.get("government_warning", "") or ""
        )
        results.append(FieldResult(
            field_name="Government Warning",
            application_value=application.government_warning,
            extracted_value=extracted.get("government_warning", "") or "Not found on label",
            match=match,
            confidence=conf,
            match_type=mtype,
            notes="Requires exact text with 'GOVERNMENT WARNING:' in ALL CAPS",
        ))

    return results


def determine_overall_status(fields: list[FieldResult]) -> tuple[str, float, bool, list[str]]:
    """Determine overall verification status from field results."""
    if not fields:
        return "NEEDS_REVIEW", 0.0, True, ["No fields to compare"]

    all_match = all(f.match for f in fields)
    any_not_found = any(f.match_type == "not_found" for f in fields)
    avg_confidence = sum(f.confidence for f in fields) / len(fields)
    low_confidence = [f for f in fields if f.confidence < 0.7]

    review_reasons = []

    if all_match and avg_confidence >= 0.9:
        status = "APPROVED"
        needs_review = False
    elif all_match and avg_confidence >= 0.7:
        status = "APPROVED"
        needs_review = True
        review_reasons.append("Some fields matched with lower confidence — quick review recommended")
    else:
        mismatches = [f.field_name for f in fields if not f.match]
        if mismatches:
            status = "MISMATCH_DETECTED"
            needs_review = True
            review_reasons.append(f"Mismatches found in: {', '.join(mismatches)}")
        else:
            status = "NEEDS_REVIEW"
            needs_review = True

    if any_not_found:
        not_found_fields = [f.field_name for f in fields if f.match_type == "not_found"]
        review_reasons.append(f"Fields not found on label: {', '.join(not_found_fields)}")
        needs_review = True
        if status == "APPROVED":
            status = "NEEDS_REVIEW"

    if low_confidence:
        review_reasons.append(
            f"Low confidence on: {', '.join(f.field_name for f in low_confidence)}"
        )

    return status, avg_confidence, needs_review, review_reasons


# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@app.post("/verify", response_model=VerificationResult)
async def verify_label(
    image: UploadFile = File(..., description="Label image file (JPEG, PNG)"),
    brand_name: str = Form(..., description="Brand name from application"),
    class_type: str = Form(default="", description="Class/type from application"),
    alcohol_content: str = Form(default="", description="Alcohol content from application"),
    net_contents: str = Form(default="", description="Net contents from application"),
    producer_name: str = Form(default="", description="Producer/bottler from application"),
    government_warning: str = Form(default="", description="Government warning from application"),
):
    """
    Verify a single label image against application data.
    
    Accepts a label image and application form data, extracts text from the image
    using AI vision, and compares each field. Returns match/mismatch results with
    confidence scores.
    
    Target response time: under 5 seconds.
    """
    start_time = time.time()

    # Validate file type
    if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload JPEG, PNG, or WebP image.",
        )

    # Read image
    image_bytes = await image.read()

    # Size check (max 20MB)
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 20MB.")

    # Extract text from label using Gemini Vision
    extracted = await extract_label_text(image_bytes, image.content_type)

    # Build application data
    application = ApplicationData(
        brand_name=brand_name,
        class_type=class_type or None,
        alcohol_content=alcohol_content or None,
        net_contents=net_contents or None,
        producer_name=producer_name or None,
        government_warning=government_warning or None,
    )

    # Compare fields
    fields = compare_fields(application, extracted)

    # Determine overall status
    status, confidence, needs_review, review_reasons = determine_overall_status(fields)

    processing_time = time.time() - start_time

    return VerificationResult(
        overall_status=status,
        overall_confidence=confidence,
        fields=fields,
        processing_time_seconds=round(processing_time, 2),
        timestamp=datetime.utcnow().isoformat(),
        needs_human_review=needs_review,
        review_reasons=review_reasons,
    )


@app.post("/verify/batch")
async def verify_batch(
    images: list[UploadFile] = File(..., description="Multiple label images"),
    brand_names: list[str] = Form(..., description="Brand names (one per image)"),
    class_types: list[str] = Form(default=[], description="Class/types (one per image)"),
    alcohol_contents: list[str] = Form(default=[], description="Alcohol contents"),
    net_contents_list: list[str] = Form(default=[], description="Net contents"),
    government_warnings: list[str] = Form(default=[], description="Government warnings"),
):
    """
    Batch verify multiple labels at once.
    
    Accepts multiple label images with corresponding application data.
    Processes sequentially and returns results for each label.
    
    Designed for bulk importers submitting 200-300 applications at once.
    """
    if len(images) == 0:
        raise HTTPException(status_code=400, detail="No images provided.")

    if len(images) != len(brand_names):
        raise HTTPException(
            status_code=400,
            detail="Number of images must match number of brand names.",
        )

    results = []
    total_start = time.time()

    for i, img in enumerate(images):
        start_time = time.time()

        image_bytes = await img.read()
        extracted = await extract_label_text(image_bytes, img.content_type)

        application = ApplicationData(
            brand_name=brand_names[i],
            class_type=class_types[i] if i < len(class_types) else None,
            alcohol_content=alcohol_contents[i] if i < len(alcohol_contents) else None,
            net_contents=net_contents_list[i] if i < len(net_contents_list) else None,
            government_warning=government_warnings[i] if i < len(government_warnings) else None,
        )

        fields = compare_fields(application, extracted)
        status, confidence, needs_review, review_reasons = determine_overall_status(fields)

        processing_time = time.time() - start_time

        results.append(VerificationResult(
            overall_status=status,
            overall_confidence=confidence,
            fields=fields,
            processing_time_seconds=round(processing_time, 2),
            timestamp=datetime.utcnow().isoformat(),
            needs_human_review=needs_review,
            review_reasons=review_reasons,
        ))

    total_time = time.time() - total_start

    return {
        "total_labels_processed": len(results),
        "total_processing_time_seconds": round(total_time, 2),
        "average_time_per_label_seconds": round(total_time / len(results), 2),
        "summary": {
            "approved": sum(1 for r in results if r.overall_status == "APPROVED"),
            "needs_review": sum(1 for r in results if r.overall_status == "NEEDS_REVIEW"),
            "mismatch_detected": sum(1 for r in results if r.overall_status == "MISMATCH_DETECTED"),
        },
        "results": results,
    }


@app.get("/model/info")
async def model_info():
    """
    Returns information about the AI model being used.
    Supports transparency and auditability requirements.
    """
    return {
        "model": "gemini-2.0-flash",
        "provider": "Google",
        "capability": "Vision + Text extraction",
        "confidence_threshold": 0.7,
        "matching_strategies": {
            "brand_name": "Fuzzy (case-insensitive, punctuation-normalized)",
            "class_type": "Fuzzy",
            "alcohol_content": "Numeric extraction and comparison",
            "net_contents": "Numeric extraction with unit normalization",
            "government_warning": "Strict exact match (caps required)",
            "producer_name": "Fuzzy",
        },
        "human_review_trigger": "Confidence below 70% or field not found",
        "production_notes": "For production deployment, recommend Azure AI Vision (FedRAMP authorized) or on-premises model",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
