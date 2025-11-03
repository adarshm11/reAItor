"""
External Data Enrichment Service
Integrates with external APIs to provide crime, school, walkability, and transit data
"""

from typing import Dict, Optional, List, Tuple
from models.schemas import Listing
import os
import requests
from functools import lru_cache
import hashlib
import json


class ExternalDataService:
    """Service for fetching external data about property locations"""

    def __init__(self):
        # API Keys from environment
        self.walkscore_api_key = os.getenv("WALKSCORE_API_KEY")
        self.greatschools_api_key = os.getenv("GREATSCHOOLS_API_KEY")
        self.google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

        # Base URLs
        self.walkscore_url = "https://api.walkscore.com/score"
        self.greatschools_url = "https://api.greatschools.org/schools"

        # Timeout for API requests
        self.timeout = 10

    def get_location_data(self, listing: Listing) -> Dict:
        """
        Get comprehensive location data for a listing

        Args:
            listing: Property listing

        Returns:
            Dictionary with all external data
        """
        # Parse location from listing
        lat, lon = self._get_coordinates(listing)

        # Fetch data from various sources
        walkability_data = self._get_walkability_data(lat, lon, listing.address)
        school_data = self._get_school_data(lat, lon)
        crime_data = self._get_crime_data(lat, lon, listing.city, listing.state)
        transit_data = self._get_transit_data(lat, lon)
        amenities_data = self._get_amenities_data(lat, lon)

        return {
            "walkability": walkability_data,
            "schools": school_data,
            "crime": crime_data,
            "transit": transit_data,
            "amenities": amenities_data
        }

    def _get_coordinates(self, listing: Listing) -> Tuple[float, float]:
        """
        Get latitude and longitude for a listing
        Uses Google Geocoding API or falls back to estimation

        Args:
            listing: Property listing

        Returns:
            Tuple of (latitude, longitude)
        """
        if self.google_maps_api_key:
            try:
                # Use Google Geocoding API
                address = f"{listing.address}, {listing.city}, {listing.state} {listing.zip_code}"
                url = "https://maps.googleapis.com/maps/api/geocode/json"
                params = {
                    "address": address,
                    "key": self.google_maps_api_key
                }

                response = requests.get(url, params=params, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("results"):
                        location = data["results"][0]["geometry"]["location"]
                        return location["lat"], location["lng"]
            except Exception as e:
                print(f"Geocoding error: {e}")

        # Fallback: use approximate city center coordinates
        # In production, you'd have a database of city coordinates
        city_coords = self._get_approximate_city_coords(listing.city, listing.state)
        return city_coords

    def _get_approximate_city_coords(self, city: str, state: str) -> Tuple[float, float]:
        """
        Get approximate coordinates for major cities
        In production, use a proper geocoding service
        """
        # Major US city coordinates (simplified)
        cities = {
            "san francisco": (37.7749, -122.4194),
            "los angeles": (34.0522, -118.2437),
            "new york": (40.7128, -74.0060),
            "chicago": (41.8781, -87.6298),
            "houston": (29.7604, -95.3698),
            "seattle": (47.6062, -122.3321),
            "boston": (42.3601, -71.0589),
            "austin": (30.2672, -97.7431),
            "denver": (39.7392, -104.9903),
            "portland": (45.5152, -122.6784),
        }

        city_key = city.lower().strip()
        return cities.get(city_key, (37.7749, -122.4194))  # Default to SF

    def _get_walkability_data(self, lat: float, lon: float, address: str) -> Dict:
        """
        Get walkability data from Walk Score API

        Args:
            lat: Latitude
            lon: Longitude
            address: Street address

        Returns:
            Dictionary with walk score, transit score, and bike score
        """
        if not self.walkscore_api_key:
            return self._get_mock_walkability_data()

        try:
            params = {
                "format": "json",
                "address": address,
                "lat": lat,
                "lon": lon,
                "transit": 1,
                "bike": 1,
                "wsapikey": self.walkscore_api_key
            }

            response = requests.get(
                self.walkscore_url,
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "walk_score": data.get("walkscore", 50),
                    "walk_description": data.get("description", "Somewhat Walkable"),
                    "transit_score": data.get("transit", {}).get("score", 50),
                    "transit_description": data.get("transit", {}).get("description", "Some Transit"),
                    "bike_score": data.get("bike", {}).get("score", 50),
                    "bike_description": data.get("bike", {}).get("description", "Bikeable")
                }
        except Exception as e:
            print(f"Walk Score API error: {e}")

        return self._get_mock_walkability_data()

    def _get_school_data(self, lat: float, lon: float) -> List[Dict]:
        """
        Get nearby school data from GreatSchools API

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            List of nearby schools with ratings
        """
        if not self.greatschools_api_key:
            return self._get_mock_school_data()

        try:
            # GreatSchools API endpoint for nearby schools
            url = f"{self.greatschools_url}/nearby"
            params = {
                "lat": lat,
                "lon": lon,
                "radius": 5,  # 5 miles
                "limit": 5,
                "key": self.greatschools_api_key
            }

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                schools = response.json()
                return [
                    {
                        "name": school.get("name"),
                        "rating": school.get("rating", "N/A"),
                        "distance": school.get("distance", 0),
                        "level": school.get("level", ""),  # elementary, middle, high
                        "type": school.get("type", "public")
                    }
                    for school in schools[:5]
                ]
        except Exception as e:
            print(f"GreatSchools API error: {e}")

        return self._get_mock_school_data()

    def _get_crime_data(self, lat: float, lon: float, city: str, state: str) -> Dict:
        """
        Get crime data for the location
        Uses FBI Crime Data API or similar service

        Args:
            lat: Latitude
            lon: Longitude
            city: City name
            state: State code

        Returns:
            Dictionary with crime statistics
        """
        # Note: FBI UCR API doesn't provide exact coordinates
        # In production, use services like CrimeReports.com or SpotCrime

        # For now, return mock data with TODO for implementation
        # TODO: Integrate with crime data API
        return self._get_mock_crime_data()

    def _get_transit_data(self, lat: float, lon: float) -> Dict:
        """
        Get public transit information using Google Maps Transit API

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Dictionary with transit information
        """
        if not self.google_maps_api_key:
            return self._get_mock_transit_data()

        try:
            # Search for nearby transit stations
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lon}",
                "radius": 800,  # 800 meters (about 0.5 miles)
                "type": "transit_station",
                "key": self.google_maps_api_key
            }

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                if results:
                    stations = [
                        {
                            "name": place.get("name"),
                            "types": place.get("types", []),
                            "distance": self._calculate_distance(
                                lat, lon,
                                place["geometry"]["location"]["lat"],
                                place["geometry"]["location"]["lng"]
                            )
                        }
                        for place in results[:5]
                    ]

                    return {
                        "nearby_stations": stations,
                        "count": len(stations),
                        "description": f"{len(stations)} transit stations within 0.5 miles"
                    }
        except Exception as e:
            print(f"Transit API error: {e}")

        return self._get_mock_transit_data()

    def _get_amenities_data(self, lat: float, lon: float) -> Dict:
        """
        Get nearby amenities using Google Places API

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Dictionary with amenity counts and descriptions
        """
        if not self.google_maps_api_key:
            return self._get_mock_amenities_data()

        try:
            amenity_types = ["grocery_or_supermarket", "restaurant", "cafe", "park", "gym"]
            amenity_counts = {}

            for amenity_type in amenity_types:
                url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                params = {
                    "location": f"{lat},{lon}",
                    "radius": 1000,  # 1 km
                    "type": amenity_type,
                    "key": self.google_maps_api_key
                }

                response = requests.get(url, params=params, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()
                    amenity_counts[amenity_type] = len(data.get("results", []))

            return {
                "grocery_stores": amenity_counts.get("grocery_or_supermarket", 0),
                "restaurants": amenity_counts.get("restaurant", 0),
                "cafes": amenity_counts.get("cafe", 0),
                "parks": amenity_counts.get("park", 0),
                "gyms": amenity_counts.get("gym", 0),
                "description": self._describe_amenities(amenity_counts)
            }
        except Exception as e:
            print(f"Amenities API error: {e}")

        return self._get_mock_amenities_data()

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates in miles
        Uses Haversine formula
        """
        from math import radians, sin, cos, sqrt, atan2

        R = 3959  # Earth's radius in miles

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def _describe_amenities(self, counts: Dict) -> str:
        """Generate description of amenities"""
        total = sum(counts.values())
        if total > 50:
            return "Excellent - many amenities within walking distance"
        elif total > 20:
            return "Good - several amenities nearby"
        elif total > 10:
            return "Moderate - some amenities in the area"
        else:
            return "Limited - few amenities nearby"

    # Mock data methods for development/fallback

    def _get_mock_walkability_data(self) -> Dict:
        """Mock walkability data"""
        return {
            "walk_score": 85,
            "walk_description": "Very Walkable",
            "transit_score": 75,
            "transit_description": "Excellent Transit",
            "bike_score": 80,
            "bike_description": "Very Bikeable"
        }

    def _get_mock_school_data(self) -> List[Dict]:
        """Mock school data"""
        return [
            {
                "name": "Lincoln High School",
                "rating": "8/10",
                "distance": 0.5,
                "level": "high",
                "type": "public"
            },
            {
                "name": "Mission Elementary",
                "rating": "7/10",
                "distance": 0.3,
                "level": "elementary",
                "type": "public"
            },
            {
                "name": "Bay Area Middle School",
                "rating": "9/10",
                "distance": 0.8,
                "level": "middle",
                "type": "public"
            }
        ]

    def _get_mock_crime_data(self) -> Dict:
        """Mock crime data"""
        return {
            "crime_rate": "Low",
            "crime_index": 25,  # Lower is safer (0-100)
            "violent_crime": "Very Low",
            "property_crime": "Low",
            "description": "Safe neighborhood with below-average crime rates",
            "compared_to_national": "72% safer than national average"
        }

    def _get_mock_transit_data(self) -> Dict:
        """Mock transit data"""
        return {
            "nearby_stations": [
                {"name": "Powell St BART", "types": ["subway"], "distance": 0.4},
                {"name": "Montgomery St BART", "types": ["subway"], "distance": 0.6},
                {"name": "Market St Bus Stop", "types": ["bus"], "distance": 0.1}
            ],
            "count": 3,
            "description": "Excellent - 3 transit stations within 0.5 miles"
        }

    def _get_mock_amenities_data(self) -> Dict:
        """Mock amenities data"""
        return {
            "grocery_stores": 5,
            "restaurants": 25,
            "cafes": 12,
            "parks": 3,
            "gyms": 4,
            "description": "Excellent - many amenities within walking distance"
        }

    def format_for_evaluation(self, location_data: Dict) -> Dict:
        """
        Format external data for use in evaluation agent

        Args:
            location_data: Raw location data from get_location_data()

        Returns:
            Formatted dictionary suitable for evaluation agent
        """
        walkability = location_data.get("walkability", {})
        schools = location_data.get("schools", [])
        crime = location_data.get("crime", {})
        transit = location_data.get("transit", {})
        amenities = location_data.get("amenities", {})

        return {
            "crime_rate": crime.get("crime_rate", "Unknown"),
            "crime_index": crime.get("crime_index", 50),
            "crime_description": crime.get("description", ""),

            "nearby_schools": [
                {
                    "name": school.get("name"),
                    "rating": school.get("rating"),
                    "distance": f"{school.get('distance', 0):.1f} miles"
                }
                for school in schools[:3]
            ],

            "walkability_score": walkability.get("walk_score", 50),
            "walk_description": walkability.get("walk_description", "Somewhat Walkable"),

            "transit_score": walkability.get("transit_score", 50),
            "transit_access": transit.get("description", "Some transit options"),

            "local_amenities": amenities.get("description", "Moderate amenities")
        }
