"""
PDF Extraction Engine
"""
import pdfplumber
import re
import io
from typing import Dict, List, Optional
from app.models import ExtractionResult, FleetSize, DUIPolicy, VehicleRequirements, DriverRequirements, HazmatPolicy, LineOfBusiness, CarrierTier

class GuidelineExtractor:
    def extract(self, pdf_bytes: bytes, carrier: str, states: List[str], lob, tier=None):
        results = []
        
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                    
        if not states:
            states = self._detect_states(full_text)
            
        for state in states:
            result = self._create_result(full_text, carrier, state, lob, tier)
            results.append(result)
            
        return results
        
    def _create_result(self, text, carrier, state, lob, tier):
        fleet = self._extract_fleet_size(text)
        dui = self._extract_dui_policy(text)
        vehicle = self._extract_vehicle_reqs(text)
        driver = self._extract_driver_reqs(text)
        hazmat = self._extract_hazmat(text)
        eligible, ineligible = self._extract_operations(text)
        
        if not tier:
            tier = self._determine_tier(carrier, text)
            
        confidence = self._calculate_confidence(fleet, dui, vehicle, driver, hazmat)
        
        return ExtractionResult(
            carrier_name=carrier,
            line_of_business=lob,
            states=[state],
            tier=tier,
            fleet_size=fleet,
            dui_policy=dui,
            vehicle_requirements=vehicle,
            driver_requirements=driver,
            hazmat_policy=hazmat,
            eligible_operations=eligible,
            ineligible_operations=ineligible,
            technology_required=self._extract_tech(text),
            raw_text=text[:50000],
            confidence_score=confidence,
            extraction_metadata={"text_length": len(text)}
        )
        
    def _extract_fleet_size(self, text):
        patterns = [
            r'(\d+)\s*[-to]+\s*(\d+)\s*(?:power units?|units?)',
            r'up to (\d+)',
            r'max(?:imum)?\s*(\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = [g for g in match.groups() if g]
                if len(groups) == 2:
                    return FleetSize(min=int(groups[0]), max=int(groups[1]))
                elif len(groups) == 1:
                    return FleetSize(min=1, max=int(groups[0]))
        return FleetSize()
        
    def _extract_dui_policy(self, text):
        text_lower = text.lower()
        if re.search(r'\bno\s+(?:dui|dwis?)\b', text_lower):
            return DUIPolicy(allowed=False)
        match = re.search(r'(?:dui|dwi)[:\s]*(\d+)\s*year', text_lower)
        if match:
            return DUIPolicy(allowed=True, lookback_years=int(match.group(1)))
        return DUIPolicy(allowed=True)
        
    def _extract_vehicle_reqs(self, text):
        reqs = VehicleRequirements()
        match = re.search(r'(?:newer than|maximum age)[:\s]*(\d+)\s*years?', text, re.IGNORECASE)
        if match:
            reqs.max_age_years = int(match.group(1))
        match = re.search(r'under (\d{1,3}(?:,\d{3})*)\s*(?:lbs?|pounds?)', text, re.IGNORECASE)
        if match:
            reqs.min_weight_lbs = int(match.group(1).replace(',', ''))
        return reqs
        
    def _extract_driver_reqs(self, text):
        reqs = DriverRequirements()
        match = re.search(r'(?:minimum|min)[:\s]*(\d+)\s*years?\s*experience', text, re.IGNORECASE)
        if match:
            reqs.min_experience_years = int(match.group(1))
        return reqs
        
    def _extract_hazmat(self, text):
        text_lower = text.lower()
        if re.search(r'\bno hazmat\b|hazmat.*(?:excluded|prohibited)', text_lower):
            return HazmatPolicy(allowed=False)
        return HazmatPolicy(allowed=True)
        
    def _extract_operations(self, text):
        ineligible = []
        text_lower = text.lower()
        common = ['hazmat', 'logging', 'mining', 'household goods']
        for op in common:
            if op in text_lower:
                ineligible.append(op)
        return [], list(set(ineligible))
        
    def _extract_tech(self, text):
        tech = []
        text_lower = text.lower()
        if 'dashcam' in text_lower or 'camera' in text_lower:
            tech.append('dashcam')
        if 'eld' in text_lower:
            tech.append('eld')
        return tech
        
    def _detect_states(self, text):
        states = []
        pattern = r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b'
        matches = re.findall(pattern, text)
        return list(set(matches)) if matches else ['XX']
        
    def _determine_tier(self, carrier, text):
        text_lower = text.lower()
        if 'surplus' in text_lower or 'non-admitted' in text_lower:
            return CarrierTier.SURPLUS
        return CarrierTier.STANDARD
        
    def _calculate_confidence(self, fleet, dui, vehicle, driver, hazmat):
        score = 0
        if fleet.max: score += 0.2
        if not dui.allowed or dui.lookback_years: score += 0.2
        if vehicle.max_age_years: score += 0.2
        if driver.min_experience_years: score += 0.2
        if not hazmat.allowed: score += 0.2
        return round(score, 2)

extractor = GuidelineExtractor()
