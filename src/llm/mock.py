"""
Mock Evon LLM Client

Provides canned structured responses for Scheme Finder MVP
when real Evon API is unavailable. Matches expected response schema.
"""

from dataclasses import asdict, dataclass


@dataclass
class SchemeMatch:
    name: str
    category: str
    eligibility_summary: str
    benefits: str
    documents_required: list[str]
    application_link: str
    helpline: str
    state: str
    confidence: float


@dataclass
class EvonResponse:
    spoken_response: str
    schemes: list[SchemeMatch]
    missing_documents: list[str]
    next_steps: list[str]
    language: str
    disclaimer: str


# Canned responses for common query patterns
MOCK_RESPONSES = {
    "farmer_maharashtra": EvonResponse(
        spoken_response=(
            "Namaste! Aap PM-KISAN ke liye eligible hain — saal ke 6 hazar rupaye. "
            "Maharashtra ke Shetkari Sanman Yojana mein bhi 6 hazar milte hain. "
            "Pyaaz ke liye MIS scheme chal rahi hai. WhatsApp pe details bhej deta hoon."
        ),
        schemes=[
            SchemeMatch(
                name="PM-KISAN",
                category="farmer",
                eligibility_summary="All landholding farmer families with cultivable land",
                benefits="₹6,000 per year in 3 installments",
                documents_required=["Aadhaar", "Land records", "Bank passbook"],
                application_link="https://pmkisan.gov.in/",
                helpline="155261",
                state="central",
                confidence=0.95,
            ),
            SchemeMatch(
                name="Shetkari Sanman Yojana",
                category="farmer",
                eligibility_summary="Maharashtra farmers with 0.5-20 hectares",
                benefits="₹6,000 per year",
                documents_required=["7/12 extract", "Aadhaar", "Bank account"],
                application_link="https://mahadbt.maharashtra.gov.in/",
                helpline="1800-120-8040",
                state="maharashtra",
                confidence=0.90,
            ),
            SchemeMatch(
                name="Market Intervention Scheme (Onion)",
                category="farmer",
                eligibility_summary="Onion farmers in designated districts during price crash",
                benefits="Procurement at MIS rate",
                documents_required=["Farmer registration", "Crop survey", "Bank details"],
                application_link="https://nafed-india.com/",
                helpline="011-26566107",
                state="central",
                confidence=0.75,
            ),
        ],
        missing_documents=["Land record (7/12)", "Bank passbook copy"],
        next_steps=[
            "Visit nearest CSC with documents for PM-KISAN registration",
            "Check MIS procurement dates at local APMC",
            "Save WhatsApp message for reference",
        ],
        language="hi",
        disclaimer="Scheme details may change. Verify at official portal before applying.",
    ),
    "pension_elderly": EvonResponse(
        spoken_response=(
            "Aapki umar 65 saal hai, to aap National Pension Scheme aur "
            "state ke vriddha pension ke liye eligible ho sakte hain. "
            "Details WhatsApp pe bhej raha hoon."
        ),
        schemes=[
            SchemeMatch(
                name="Indira Gandhi National Old Age Pension (IGNOAPS)",
                category="pension",
                eligibility_summary="Age 60+, BPL household",
                benefits="₹200/month (central) + state top-up",
                documents_required=["Age proof", "BPL card", "Aadhaar", "Bank account"],
                application_link="https://nsap.nic.in/",
                helpline="1800-111-555",
                state="central",
                confidence=0.90,
            ),
        ],
        missing_documents=["Age certificate", "BPL ration card"],
        next_steps=[
            "Visit Gram Panchayat / Ward office with documents",
            "Apply online at nsap.nic.in if available in your state",
        ],
        language="hi",
        disclaimer="State top-up amounts vary. Check with local office.",
    ),
    "student_scholarship": EvonResponse(
        spoken_response=(
            "Beta, 12th pass ke baad kayi scholarships milti hain. "
            "Post Matric Scholarship, Pragati Scholarship, aur state-specific bhi. "
            "WhatsApp pe list bhej deta hoon."
        ),
        schemes=[
            SchemeMatch(
                name="Post Matric Scholarship (OBC/SC/ST)",
                category="scholarship",
                eligibility_summary="Class 11+, family income < ₹2.5L, OBC/SC/ST",
                benefits="Maintenance allowance + fee reimbursement",
                documents_required=[
                    "Caste certificate",
                    "Income certificate",
                    "Marksheet",
                    "Aadhaar",
                ],
                application_link="https://scholarships.gov.in/",
                helpline="011-29581118",
                state="central",
                confidence=0.85,
            ),
            SchemeMatch(
                name="Pragati Scholarship (AICTE)",
                category="scholarship",
                eligibility_summary="Girl student, 1st year technical degree, family income < ₹8L",
                benefits="₹50,000 per year",
                documents_required=["Admission letter", "Income certificate", "Aadhaar"],
                application_link="https://www.aicte-india.org/",
                helpline="011-29581000",
                state="central",
                confidence=0.80,
            ),
        ],
        missing_documents=["Caste certificate", "Income certificate", "12th marksheet"],
        next_steps=[
            "Register on National Scholarship Portal (scholarships.gov.in)",
            "Get income & caste certificates from Tehsildar",
            "Apply before deadline (usually Oct-Nov)",
        ],
        language="hi",
        disclaimer="Deadlines vary by scheme. Apply early.",
    ),
    "default": EvonResponse(
        spoken_response=(
            "Main aapki details ke basis pe schemes dhoondh raha hoon. "
            "Kripya apna rajya, vyavsay, aur umar batayein taaki main sahi bata sakoon."
        ),
        schemes=[],
        missing_documents=[],
        next_steps=[
            "Bataiye: Aap kaunse rajya se hain?",
            "Kya karte hain? (kisan, majdoor, student, pensioner)",
            "Umar kitni hai?",
        ],
        language="hi",
        disclaimer="Poori jaankari ke liye adik details chahiye.",
    ),
}


def mock_evon_response(transcript: str, scheme_chunks: list[dict], language: str = "hi-IN") -> dict:
    """
    Generate a mock Evon response based on transcript keywords.

    Args:
        transcript: User's spoken query transcript
        scheme_chunks: Retrieved scheme documents (unused in mock)
        language: Detected language code

    Returns:
        Dict matching EvonResponse schema
    """
    text = transcript.lower()

    # Simple keyword routing
    if any(kw in text for kw in ["kisan", "farmer", "kheti", "zameen", "fasal", "pyaaz", "onion"]):
        if any(kw in text for kw in ["maharashtra", "mumbai", "pune", "vidarbha", "marathi"]):
            return asdict(MOCK_RESPONSES["farmer_maharashtra"])
        return asdict(MOCK_RESPONSES["farmer_maharashtra"])  # Default to farmer

    if any(kw in text for kw in ["pension", "budhapa", "vriddha", "umra", "65", "60", "senior"]):
        return asdict(MOCK_RESPONSES["pension_elderly"])

    if any(kw in text for kw in ["scholarship", "padhai", "student", "12th", "college", "degree"]):
        return asdict(MOCK_RESPONSES["student_scholarship"])

    return asdict(MOCK_RESPONSES["default"])
