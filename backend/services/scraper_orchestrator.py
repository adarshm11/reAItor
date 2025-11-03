"""
Scraper Orchestrator Service
Coordinates all scraper agents and combines their results
"""

from typing import List
from models.schemas import Listing, UserPreferences
from agents.zillow_scraper import ZillowScraper
from agents.redfin_scraper import RedfinScraper
from agents.realtor_scraper import RealtorScraper
import asyncio


class ScraperOrchestrator:
    """Orchestrates multiple scraper agents"""

    def __init__(self):
        self.scrapers = [
            ZillowScraper(),
            RedfinScraper(),
            RealtorScraper()
        ]

    async def search_all_platforms(self, preferences: UserPreferences) -> List[Listing]:
        """
        Search all platforms in parallel and combine results

        Args:
            preferences: User's home search preferences

        Returns:
            Combined list of listings from all platforms
        """
        print(f"Starting search across {len(self.scrapers)} platforms...")

        # Run all scrapers in parallel
        tasks = [scraper.search(preferences) for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        all_listings = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Scraper {i} failed: {result}")
                continue

            if isinstance(result, list):
                all_listings.extend(result)
                print(f"Scraper {i} ({self.scrapers[i].get_source_name()}): {len(result)} listings")

        print(f"Total listings found: {len(all_listings)}")

        # Remove duplicates based on address (simple deduplication)
        unique_listings = self._deduplicate_listings(all_listings)

        print(f"Unique listings after deduplication: {len(unique_listings)}")

        return unique_listings

    def _deduplicate_listings(self, listings: List[Listing]) -> List[Listing]:
        """
        Remove duplicate listings based on address similarity

        Args:
            listings: List of all listings

        Returns:
            Deduplicated list of listings
        """
        seen_addresses = set()
        unique_listings = []

        for listing in listings:
            # Normalize address for comparison
            normalized_address = self._normalize_address(listing.address)

            if normalized_address not in seen_addresses:
                seen_addresses.add(normalized_address)
                unique_listings.append(listing)

        return unique_listings

    def _normalize_address(self, address: str) -> str:
        """
        Normalize address for deduplication

        Args:
            address: Raw address string

        Returns:
            Normalized address string
        """
        # Convert to lowercase and remove extra spaces
        normalized = address.lower().strip()

        # Remove common variations
        normalized = normalized.replace("street", "st")
        normalized = normalized.replace("avenue", "ave")
        normalized = normalized.replace("boulevard", "blvd")
        normalized = normalized.replace("drive", "dr")
        normalized = normalized.replace("road", "rd")
        normalized = normalized.replace(".", "")
        normalized = normalized.replace(",", "")

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized

    async def search_platform(
        self,
        platform: str,
        preferences: UserPreferences
    ) -> List[Listing]:
        """
        Search a specific platform

        Args:
            platform: Platform name (zillow, redfin, realtor)
            preferences: User's home search preferences

        Returns:
            List of listings from the specified platform
        """
        scraper = None

        for s in self.scrapers:
            if s.get_source_name() == platform.lower():
                scraper = s
                break

        if not scraper:
            raise ValueError(f"Unknown platform: {platform}")

        return await scraper.search(preferences)
