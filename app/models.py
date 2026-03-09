"""
Pydantic models for Carrier Guideline Extraction
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class LineOfBusiness(str, Enum):
    COMMERCIAL_AUTO = "commercial_auto"
    WORKERS_COMP = "workers_comp"

class CarrierTier(str, Enum):
    STANDARD = "standard"
    STANDARD_ES = "standard_es"
    SURPLUS = "surplus_lines"

class FleetSize(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None

class DUIPolicy(BaseModel):
    allowed: bool = True
    lookback_years: Optional[int] = None

class VehicleRequirements(BaseModel):
    max_age_years: Optional[int] = None
    min_weight_lbs: Optional[int] = None

class DriverRequirements(BaseModel):
    min_experience_years: Optional[int] = None

class HazmatPolicy(BaseModel):
    allowed: bool = True

class ExtractionResult(BaseModel):
    carrier_name: str
    line_of_business: LineOfBusiness
    states: List[str]
    tier: CarrierTier
    fleet_size: FleetSize = Field(default_factory=FleetSize)
    dui_policy: DUIPolicy = Field(default_factory=DUIPolicy)
    vehicle_requirements: VehicleRequirements = Field(default_factory=VehicleRequirements)
    driver_requirements: DriverRequirements = Field(default_factory=DriverRequirements)
    hazmat_policy: HazmatPolicy = Field(default_factory=HazmatPolicy)
    eligible_operations: List[str] = []
    ineligible_operations: List[str] = []
    technology_required: List[str] = []
    raw_text: str
    confidence_score: float = Field(ge=0, le=1)