"""
Redfin Scraper Agent
Scrapes listings from Redfin.com
"""

from typing import List
from models.schemas import Listing, UserPreferences
from agents.base_scraper import BaseScraper
from playwright.async_api import Page
import uuid


class RedfinScraper(BaseScraper):
    """Scraper for Redfin.com"""

    def get_source_name(self) -> str:
        return "redfin"

    def build_search_url(self, preferences: UserPreferences) -> str:
        """Build Redfin search URL from preferences"""
        base_url = "https://www.redfin.com"

        # Format location for Redfin
        location = preferences.location or "San Francisco, CA"
        location_slug = location.replace(" ", "-").replace(",", "")

        # Start with base location search
        url = f"{base_url}/city/{location_slug}"

        # Build filter parameters
        filters = []

        # Price range
        if preferences.price_min:
            filters.append(f"min-price={preferences.price_min}")
        if preferences.price_max:
            filters.append(f"max-price={preferences.price_max}")

        # Bedrooms
        if preferences.bedrooms_min:
            filters.append(f"min-beds={preferences.bedrooms_min}")
        if preferences.bedrooms_max:
            filters.append(f"max-beds={preferences.bedrooms_max}")

        # Bathrooms
        if preferences.bathrooms_min:
            filters.append(f"min-baths={int(preferences.bathrooms_min)}")

        # Square footage
        if preferences.sqft_min:
            filters.append(f"min-sqft={preferences.sqft_min}")
        if preferences.sqft_max:
            filters.append(f"max-sqft={preferences.sqft_max}")

        # Property types
        if preferences.property_types:
            # Redfin uses numbers for property types
            type_codes = []
            for pt in preferences.property_types:
                if pt.lower() in ["house", "single-family"]:
                    type_codes.append("1")
                elif pt.lower() == "condo":
                    type_codes.append("2")
                elif pt.lower() == "townhouse":
                    type_codes.append("3")
            if type_codes:
                filters.append(f"property-type={','.join(type_codes)}")

        if filters:
            url += "/filter/" + ",".join(filters)

        return url

    async def search(self, preferences: UserPreferences) -> List[Listing]:
        """Search Redfin for listings"""
        try:
            await self.initialize_browser(headless=True)
            page = await self.create_page()

            # Build and navigate to search URL
            search_url = self.build_search_url(preferences)
            print(f"Redfin: Navigating to {search_url}")

            await page.goto(search_url, wait_until="networkidle", timeout=30000)

            # Wait for listings to load
            await self.handle_rate_limiting(3.0)

            # Extract listings
            listings = await self.extract_listings(page)

            await self.close_browser()

            print(f"Redfin: Found {len(listings)} listings")
            return listings[:self.max_results]

        except Exception as e:
            print(f"Redfin scraper error: {e}")
            if self.browser:
                await self.close_browser()

            # Return mock data for development
            return self._get_mock_listings(preferences)

    async def extract_listings(self, page: Page) -> List[Listing]:
        """Extract listing data from Redfin page"""
        listings = []

        try:
            # Redfin uses div.HomeCard for listings
            listing_cards = await page.query_selector_all('.HomeCard')

            if not listing_cards:
                # Try alternate selector
                listing_cards = await page.query_selector_all('[data-rf-test-name="abp-card"]')

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
        link_element = await card.query_selector('a.link-and-anchor')
        if not link_element:
            link_element = await card.query_selector('a')

        url = await link_element.get_attribute('href') if link_element else ""
        if url and not url.startswith('http'):
            url = f"https://www.redfin.com{url}"

        # Extract address
        address_element = await card.query_selector('.HomeCardAddress')
        address = await address_element.inner_text() if address_element else "Address not available"

        # Extract price
        price_element = await card.query_selector('.homecardV2Price')
        price_str = await price_element.inner_text() if price_element else "$0"
        price = self._format_price(price_str)

        # Extract beds/baths/sqft
        stats_element = await card.query_selector('.HomeStatsV2')
        stats_text = await stats_element.inner_text() if stats_element else "0 Beds | 0 Baths | 0 Sq Ft"

        # Parse stats
        parts = [p.strip() for p in stats_text.split('|')]
        bedrooms = self._format_bedrooms(parts[0]) if len(parts) > 0 else 0
        bathrooms = self._format_bathrooms(parts[1]) if len(parts) > 1 else 0.0
        sqft = self._format_sqft(parts[2]) if len(parts) > 2 else 0

        # Create listing object
        listing = Listing(
            id=str(uuid.uuid4()),
            source="redfin",
            url=url,
            address=address,
            city="",
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
        print("Redfin: Returning mock data")

        location = preferences.location or "San Francisco, CA"

        return [
            Listing(
                id=str(uuid.uuid4()),
                source="redfin",
                url="https://www.redfin.com/mock-listing-1",
                address=f"789 Mission St, {location}",
                city=location.split(',')[0] if ',' in location else location,
                state="CA",
                zip_code="94103",
                price=625000,
                bedrooms=2,
                bathrooms=2.0,
                sqft=1300,
                property_type="condo",
                description="Updated condo with city views and modern finishes",
                images=["https://placehold.co/600x400"],
                days_on_market=12
            ),
            Listing(
                id=str(uuid.uuid4()),
                source="redfin",
                url="https://www.redfin.com/mock-listing-2",
                address=f"321 Folsom St, {location}",
                city=location.split(',')[0] if ',' in location else location,
                state="CA",
                zip_code="94107",
                price=680000,
                bedrooms=3,
                bathrooms=2.5,
                sqft=1600,
                property_type="townhouse",
                description="Charming townhouse with private patio and garage parking",
                images=["https://placehold.co/600x400"],
                days_on_market=5
            )
        ]
