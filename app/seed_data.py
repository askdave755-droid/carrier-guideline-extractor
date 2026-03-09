#!/usr/bin/env python3
"""
Seed the database with extracted carrier guidelines
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'app'))

from database import db

# Pre-extracted data from Cover Whale public appetite guide
SEED_DATA = [
    {
        "carrier_name": "Cover Whale",
        "line_of_business": "commercial_auto",
        "state": "TX",
        "tier": "surplus_lines",
        "content": "Targeting 1-25 power units at bind. Growth allowance: 2 additional units per quarter up to 25 max. 2 years minimum driving experience required. Vehicle age: tractors/trailers must be newer than 23 years old. Dashcam or ELD required. No vehicles under 6,001 pounds. Max 3 cancellations in previous year.",
        "metadata": {
            "fleet_size": {"min": 1, "max": 25},
            "dui_policy": {"allowed": True, "lookback_years": None, "note": "Flexible but evaluated"},
            "hazmat_policy": {"allowed": False, "reason": "Explicitly excluded per guidelines"},
            "vehicle_requirements": {"max_age_years": 23, "min_weight_lbs": 6001},
            "driver_requirements": {"min_experience_years": 2, "cdl_required": True},
            "technology_required": ["dashcam", "eld"],
            "ineligible_operations": [
                "hazmat", "double_triple_trailers", "cement", "oversized_loads", 
                "household_goods", "mobile_homes", "logging", "mining", "garbage"
            ],
            "new_venture_max": 4,
            "cancellations_max": 3,
            "confidence_score": 0.95
        }
    },
    {
        "carrier_name": "Cover Whale",
        "line_of_business": "commercial_auto",
        "state": "MI",
        "tier": "surplus_lines",
        "content": "Same guidelines as TX. Non-admitted state. NO HAZMAT haulers explicitly excluded. No double/triple trailers. No cement haulers. No oversized loads.",
        "metadata": {
            "fleet_size": {"min": 1, "max": 25},
            "dui_policy": {"allowed": True},
            "hazmat_policy": {"allowed": False},
            "vehicle_requirements": {"max_age_years": 23},
            "technology_required": ["dashcam", "eld"],
            "ineligible_operations": ["hazmat", "double_triple_trailers", "cement", "oversized_loads"],
            "confidence_score": 0.90
        }
    },
    {
        "carrier_name": "The Hartford",
        "line_of_business": "commercial_auto",
        "state": "MI",
        "tier": "standard",
        "content": "Small business focus. Average premium $574/month. Targeting contractors, artisans, manufacturers. Strict driver requirements. Maximum fleet size typically under 50 units for standard market. No explicit DUI policy found - assumed strict.",
        "metadata": {
            "fleet_size": {"min": 1, "max": 50, "sweet_spot": "1-25"},
            "avg_premium_monthly": 574,
            "target_segments": ["contractors", "artisans", "manufacturers"],
            "dui_policy": {"allowed": False, "note": "Assumed strict - verify with UW"},
            "hazmat_policy": {"allowed": False},
            "bundling_opportunity": True,
            "workers_comp": True,
            "confidence_score": 0.70
        }
    },
    {
        "carrier_name": "Berkshire Hathaway GUARD",
        "line_of_business": "commercial_auto",
        "state": "MI",
        "tier": "standard_es",
        "content": "For-hire trucking and interstate operations. Medium risk tolerance. DUI consideration after 2 years. Automatic underwriting available for certain contracting classes. Instant bind capability.",
        "metadata": {
            "dui_policy": {"allowed": True, "lookback_years": 2},
            "hazmat_policy": {"allowed": True},
            "instant_bind": True,
            "target": ["for_hire", "interstate", "contracting"],
            "risk_tolerance": "medium",
            "automatic_underwriting": ["contractors"],
            "confidence_score": 0.85
        }
    }
]

async def seed_database():
    """Insert seed data"""
    await db.connect()
    await db.ensure_table()
    
    print("🌱 Seeding carrier guidelines...")
    
    for data in SEED_DATA:
        try:
            record_id = await db.insert_guideline(
                carrier_name=data["carrier_name"],
                line_of_business=data["line_of_business"],
                state=data["state"],
                tier=data["tier"],
                content=data["content"],
                metadata=data["metadata"]
            )
            print(f"✓ {data['carrier_name']} ({data['state']}) - ID: {record_id}")
        except Exception as e:
            print(f"✗ {data['carrier_name']} ({data['state']}) - Error: {e}")
            
    print(f"\n✅ Seeded {len(SEED_DATA)} carrier guidelines")
    await db.close()

if __name__ == "__main__":
    asyncio.run(seed_database())