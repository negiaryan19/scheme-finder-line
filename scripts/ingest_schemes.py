#!/usr/bin/env python3
"""
Scheme Knowledge Base Ingestion Script

Downloads, chunks, embeds, and stores government schemes in PostgreSQL + pgvector.
Run after setting DATABASE_URL in .env
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from scheme_kb.ingest import SchemeIngester

SCHEME_SOURCES = {
    "central": [
        {"name": "PM-KISAN", "url": "https://pmkisan.gov.in/", "category": "farmer"},
        {"name": "PM-KMY", "url": "https://pmkmy.gov.in/", "category": "farmer"},
        {"name": "PM-SYM", "url": "https://pmsym.gov.in/", "category": "unorganized_worker"},
        {"name": "NPS", "url": "https://npscra.nsdl.co.in/", "category": "pension"},
        {"name": "APY", "url": "https://www.npscra.nsdl.co.in/APY", "category": "pension"},
        {"name": "PMJJBY", "url": "https://www.jansuraksha.gov.in/", "category": "insurance"},
        {"name": "PMSBY", "url": "https://www.jansuraksha.gov.in/", "category": "insurance"},
        {"name": "Ayushman Bharat", "url": "https://pmjay.gov.in/", "category": "health"},
        {"name": "NFSA", "url": "https://nfsa.gov.in/", "category": "ration"},
        {"name": "PM-AWAS", "url": "https://pmayg.nic.in/", "category": "housing"},
        {"name": "PM-UJJWALA", "url": "https://pmuy.gov.in/", "category": "energy"},
        {"name": "SSY", "url": "https://www.indiapost.gov.in/", "category": "girl_child"},
        {
            "name": "Sukanya Samriddhi",
            "url": "https://www.nsiindia.gov.in/",
            "category": "girl_child",
        },
        {"name": "KVP", "url": "https://www.nsiindia.gov.in/", "category": "savings"},
        {"name": "NSC", "url": "https://www.nsiindia.gov.in/", "category": "savings"},
        {"name": "PPF", "url": "https://www.indiapost.gov.in/", "category": "savings"},
        {
            "name": "PM-SVANidhi",
            "url": "https://pmsvanidhi.mohua.gov.in/",
            "category": "street_vendor",
        },
        {"name": "DAY-NRLM", "url": "https://nrlm.gov.in/", "category": "shg"},
        {"name": "PM-KUSUM", "url": "https://pmkusum.mnre.gov.in/", "category": "farmer_energy"},
        {"name": "Soil Health Card", "url": "https://soilhealth.dac.gov.in/", "category": "farmer"},
    ],
    "maharashtra": [
        {"name": "Maharashtra CM Farmer Scheme", "category": "farmer"},
        {"name": "Shetkari Sanman Yojana", "category": "farmer"},
        {"name": "Maharashtra Ration Card", "category": "ration"},
    ],
    "karnataka": [
        {"name": "Krishi Bhagya", "category": "farmer"},
        {"name": "Karnataka Ration Card", "category": "ration"},
        {"name": "Bhagyalakshmi", "category": "girl_child"},
    ],
    "gujarat": [
        {"name": "Gujarat Kisan Sarvoday", "category": "farmer"},
        {"name": "Gujarat Ration Card", "category": "ration"},
        {"name": "Vhali Dikri Yojana", "category": "girl_child"},
    ],
    "tamil_nadu": [
        {"name": "Tamil Nadu CM Farmers Scheme", "category": "farmer"},
        {"name": "Tamil Nadu Ration Card", "category": "ration"},
        {"name": "Moovalur Ramamirtham", "category": "girl_child"},
    ],
    "west_bengal": [
        {"name": "Krishak Bandhu", "category": "farmer"},
        {"name": "West Bengal Ration Card", "category": "ration"},
        {"name": "Kanyashree", "category": "girl_child"},
    ],
}


async def main():
    print("=" * 60)
    print("SCHEME KB INGESTION")
    print("=" * 60)

    ingester = SchemeIngester(
        database_url=os.getenv("DATABASE_URL"),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        ),
    )

    total = 0
    for state, schemes in SCHEME_SOURCES.items():
        print(f"\n📍 Ingesting {state.upper()} ({len(schemes)} schemes)...")
        for scheme in schemes:
            try:
                # In real implementation, scrape scheme details from URL
                # For MVP, use structured seed data
                await ingester.ingest_scheme(
                    scheme_name=scheme["name"],
                    state=state,
                    category=scheme["category"],
                    # In production: fetch from URL
                    description=f"Government scheme: {scheme['name']} for {scheme['category']}",
                    eligibility={},
                    benefits={},
                    documents_required=[],
                    application_process="",
                    contact_info={},
                )
                total += 1
                print(f"  ✅ {scheme['name']}")
            except Exception as e:
                print(f"  ❌ {scheme['name']}: {e}")

    print(f"\n✅ Ingested {total} schemes total")


if __name__ == "__main__":
    asyncio.run(main())
