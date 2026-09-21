from typing import Dict, Any, Optional
from bloodhub.providers.maps.base import MapProvider
from bloodhub.domain.geospatial import haversine_distance

class OpenStreetMapProvider(MapProvider):
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return haversine_distance(lat1, lon1, lat2, lon2)

    def geocode(self, query: str) -> Optional[Dict[str, Any]]:
        # Lightweight local geocoding dictionary for prominent Bangladeshi medical hubs
        known_hospitals = {
            "dmch": {"name": "Dhaka Medical College Hospital", "lat": 23.7258, "lon": 90.3976, "address": "Secretariat Rd, Dhaka 1000"},
            "bsmmu": {"name": "Bangabandhu Sheikh Mujib Medical University (PG)", "lat": 23.7388, "lon": 90.3957, "address": "Shahbag, Dhaka 1000"},
            "nicvd": {"name": "National Institute of Cardiovascular Diseases", "lat": 23.7702, "lon": 90.3705, "address": "Mirpur Rd, Sher-e-Bangla Nagar, Dhaka"},
            "birdem": {"name": "BIRDEM General Hospital", "lat": 23.7397, "lon": 90.3959, "address": "122 Kazi Nazrul Islam Ave, Shahbag, Dhaka"},
            "square": {"name": "Square Hospital", "lat": 23.7533, "lon": 90.3817, "address": "18/F Bir Uttam Qazi Nuruzzaman Sarak, Panthapath, Dhaka"},
            "evercare": {"name": "Evercare Hospital Dhaka", "lat": 23.8105, "lon": 90.4312, "address": "Plot 81, Block E, Bashundhara R/A, Dhaka"},
            "cmh": {"name": "Combined Military Hospital (CMH) Dhaka", "lat": 23.8210, "lon": 90.4045, "address": "Dhaka Cantonment, Dhaka"},
            "quantum": {"name": "Quantum Blood Lab", "lat": 23.7371, "lon": 90.4132, "address": "Shantinagar, Dhaka 1217"},
            "red_crescent": {"name": "Red Crescent Blood Center", "lat": 23.7601, "lon": 90.3621, "address": "Aurangzeb Road, Mohammadpur, Dhaka"},
        }
        clean_q = query.lower().replace(" ", "").replace(".", "")
        for key, info in known_hospitals.items():
            if key in clean_q or any(token in clean_q for token in key.split("_")):
                return info
        return {"name": query, "lat": 23.8103, "lon": 90.4125, "address": f"{query}, Dhaka, Bangladesh"}
