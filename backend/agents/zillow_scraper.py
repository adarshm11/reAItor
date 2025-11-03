"""
Zillow Scraper Agent
Scrapes listings from Zillow.com
"""

from typing import List
from models.schemas import Listing, UserPreferences
from agents.base_scraper import BaseScraper
from playwright.async_api import Page
import uuid
import asyncio


class ZillowScraper(BaseScraper):
    """Scraper for Zillow.com"""

    def get_source_name(self) -> str:
        return "zillow"

    def build_search_url(self, preferences: UserPreferences) -> str:
        """Build Zillow search URL from preferences"""
        base_url = "https://www.zillow.com/homes/"

        # Format location
        location = preferences.location or "San Francisco, CA"
        location_slug = location.replace(" ", "-").replace(",", "")

        # Build URL with filters
        url = f"{base_url}{location_slug}_rb/"

        # Add query parameters
        params = []

        if preferences.price_min:
            params.append(f"price:{preferences.price_min}")
        if preferences.price_max:
            params.append(f"-{preferences.price_max}")

        if preferences.bedrooms_min:
            params.append(f"beds:{preferences.bedrooms_min}")
        if preferences.bedrooms_max and preferences.bedrooms_max != preferences.bedrooms_min:
            params.append(f"-{preferences.bedrooms_max}")

        if preferences.bathrooms_min:
            params.append(f"baths:{int(preferences.bathrooms_min)}")

        if preferences.sqft_min:
            params.append(f"sqft:{preferences.sqft_min}")
        if preferences.sqft_max:
            params.append(f"-{preferences.sqft_max}")

        # Add property types
        if preferences.property_types:
            type_map = {
                "house": "house",
                "condo": "condo",
                "townhouse": "townhouse",
                "apartment": "apartment"
            }
            types = [type_map.get(pt.lower(), pt) for pt in preferences.property_types]
            params.append(f"type:{','.join(types)}")

        if params:
            url += "?" + "_".join(params)

        return url

    async def search(self, preferences: UserPreferences) -> List[Listing]:
        """Search Zillow for listings"""
        try:
            await self.initialize_browser(headless=True)
            page = await self.create_page()

            # Build and navigate to search URL
            search_url = self.build_search_url(preferences)
            print(f"Zillow: Navigating to {search_url}")

            await page.goto(search_url, wait_until="networkidle", timeout=30000)

            # Wait for listings to load
            await self.handle_rate_limiting(3.0)

            # Extract listings
            listings = await self.extract_listings(page)

            await self.close_browser()

            print(f"Zillow: Found {len(listings)} listings")
            return listings[:self.max_results]

        except Exception as e:
            print(f"Zillow scraper error: {e}")
            if self.browser:
                await self.close_browser()

            # Return mock data for development
            return self._get_mock_listings(preferences)

    async def extract_listings(self, page: Page) -> List[Listing]:
        """Extract listing data from Zillow page"""
        listings = []

        try:
            # Zillow uses article tags for listing cards
            # Note: Selectors may need updating as Zillow changes their HTML
            listing_cards = await page.query_selector_all('article[data-test="property-card"]')

            if not listing_cards:
                # Try alternate selector
                listing_cards = await page.query_selector_all('.list-card')

            for card in listing_cards[:self.max_results]:
                try:
                    listing = await self._extract_listing_from_card(card, page)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    print(f"Error extracting individual listing: {e}")
                    continue

        except Exception as e:
            print(f"Error extracting listings: {e}")

        return listings

    async def _extract_listing_from_card(self, card, page: Page) -> Listing:
        """Extract data from a single listing card"""
        # Extract URL
        link_element = await card.query_selector('a[data-test="property-card-link"]')
        if not link_element:
            link_element = await card.query_selector('a')

        url = await link_element.get_attribute('href') if link_element else ""
        if url and not url.startswith('http'):
            url = f"https://www.zillow.com{url}"

        # Extract address
        address_element = await card.query_selector('[data-test="property-card-addr"]')
        address = await address_element.inner_text() if address_element else "Address not available"

        # Extract price
        price_element = await card.query_selector('[data-test="property-card-price"]')
        price_str = await price_element.inner_text() if price_element else "$0"
        price = self._format_price(price_str)

        # Extract beds/baths/sqft
        info_element = await card.query_selector('[data-test="property-card-details"]')
        info_text = await info_element.inner_text() if info_element else "0 bd | 0 ba | 0 sqft"

        # Parse info
        parts = info_text.split('|')
        bedrooms = self._format_bedrooms(parts[0]) if len(parts) > 0 else 0
        bathrooms = self._format_bathrooms(parts[1]) if len(parts) > 1 else 0.0
        sqft = self._format_sqft(parts[2]) if len(parts) > 2 else 0

        # Create listing object
        listing = Listing(
            id=str(uuid.uuid4()),
            source="zillow",
            url=url,
            address=address,
            city="",  # Parse from address if needed
            state="",
            zip_code="",
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            sqft=sqft,
            property_type="unknown",
            description="",
            images=[],
            days_on_market=None
        )

        return listing

    def _get_mock_listings(self, preferences: UserPreferences) -> List[Listing]:
        """Return mock listings for development/testing"""
        print("Zillow: Returning mock data")

        location = preferences.location or "San Francisco, CA"

        return [
            Listing(
                id=str(uuid.uuid4()),
                source="zillow",
                url="https://www.zillow.com/mock-listing-1",
                address=f"123 Market St, {location}",
                city=location.split(',')[0] if ',' in location else location,
                state="CA",
                zip_code="94103",
                price=600000,
                bedrooms=2,
                bathrooms=2.0,
                sqft=1200,
                property_type="condo",
                description="Beautiful condo in the heart of the city with modern amenities",
                images=["https://placehold.co/600x400"],
                days_on_market=15
            ),
            Listing(
                id=str(uuid.uuid4()),
                source="zillow",
                url="https://www.zillow.com/mock-listing-2",
                address=f"456 Valencia St, {location}",
                city=location.split(',')[0] if ',' in location else location,
                state="CA",
                zip_code="94110",
                price=650000,
                bedrooms=3,
                bathrooms=2.5,
                sqft=1500,
                property_type="townhouse",
                description="Spacious townhouse with parking and rooftop deck",
                images=["https://placehold.co/600x400"],
                days_on_market=8
            )
        ]
