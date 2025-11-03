"""
Realtor.com Scraper Agent
Scrapes listings from Realtor.com
"""

from typing import List
from models.schemas import Listing, UserPreferences
from agents.base_scraper import BaseScraper
from playwright.async_api import Page
import uuid


class RealtorScraper(BaseScraper):
    """Scraper for Realtor.com"""

    def get_source_name(self) -> str:
        return "realtor"

    def build_search_url(self, preferences: UserPreferences) -> str:
        """Build Realtor.com search URL from preferences"""
        base_url = "https://www.realtor.com/realestateandhomes-search"

        # Format location
        location = preferences.location or "San Francisco_CA"
        location_slug = location.replace(" ", "-").replace(",", "")

        url = f"{base_url}/{location_slug}"

        # Build query parameters
        params = []

        # Price range
        if preferences.price_min and preferences.price_max:
            params.append(f"price={preferences.price_min}-{preferences.price_max}")
        elif preferences.price_min:
            params.append(f"price={preferences.price_min}-na")
        elif preferences.price_max:
            params.append(f"price=na-{preferences.price_max}")

        # Bedrooms
        if preferences.bedrooms_min and preferences.bedrooms_max:
            params.append(f"beds={preferences.bedrooms_min}-{preferences.bedrooms_max}")
        elif preferences.bedrooms_min:
            params.append(f"beds={preferences.bedrooms_min}")

        # Bathrooms
        if preferences.bathrooms_min:
            params.append(f"baths={int(preferences.bathrooms_min)}")

        # Square footage
        if preferences.sqft_min and preferences.sqft_max:
            params.append(f"sqft={preferences.sqft_min}-{preferences.sqft_max}")
        elif preferences.sqft_min:
            params.append(f"sqft={preferences.sqft_min}-na")

        # Property types
        if preferences.property_types:
            type_map = {
                "house": "single_family",
                "condo": "condo",
                "townhouse": "townhomes",
                "apartment": "condos"
            }
            types = [type_map.get(pt.lower(), pt) for pt in preferences.property_types]
            params.append(f"type={','.join(types)}")

        if params:
            url += "/" + "/".join(params)

        return url

    async def search(self, preferences: UserPreferences) -> List[Listing]:
        """Search Realtor.com for listings"""
        try:
            await self.initialize_browser(headless=True)
            page = await self.create_page()

            # Build and navigate to search URL
            search_url = self.build_search_url(preferences)
            print(f"Realtor.com: Navigating to {search_url}")

            await page.goto(search_url, wait_until="networkidle", timeout=30000)

            # Wait for listings to load
            await self.handle_rate_limiting(3.0)

            # Extract listings
            listings = await self.extract_listings(page)

            await self.close_browser()

            print(f"Realtor.com: Found {len(listings)} listings")
            return listings[:self.max_results]

        except Exception as e:
            print(f"Realtor.com scraper error: {e}")
            if self.browser:
                await self.close_browser()

            # Return mock data for development
            return self._get_mock_listings(preferences)

    async def extract_listings(self, page: Page) -> List[Listing]:
        """Extract listing data from Realtor.com page"""
        listings = []

        try:
            # Realtor.com uses li elements with specific classes
            listing_cards = await page.query_selector_all('[data-testid="property-card"]')

            if not listing_cards:
                # Try alternate selector
                listing_cards = await page.query_selector_all('.BasePropertyCard')

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
        link_element = await card.query_selector('a[data-testid="property-anchor"]')
        if not link_element:
            link_element = await card.query_selector('a')

        url = await link_element.get_attribute('href') if link_element else ""
        if url and not url.startswith('http'):
            url = f"https://www.realtor.com{url}"

        # Extract address
        address_element = await card.query_selector('[data-testid="property-address"]')
        address = await address_element.inner_text() if address_element else "Address not available"

        # Extract price
        price_element = await card.query_selector('[data-testid="property-price"]')
        price_str = await price_element.inner_text() if price_element else "$0"
        price = self._format_price(price_str)

        # Extract beds/baths/sqft
        meta_element = await card.query_selector('[data-testid="property-meta"]')
        meta_text = await meta_element.inner_text() if meta_element else "0 bed | 0 bath | 0 sqft"

        # Parse meta
        parts = [p.strip() for p in meta_text.split('|')]
        bedrooms = self._format_bedrooms(parts[0]) if len(parts) > 0 else 0
        bathrooms = self._format_bathrooms(parts[1]) if len(parts) > 1 else 0.0
        sqft = self._format_sqft(parts[2]) if len(parts) > 2 else 0

        # Create listing object
        listing = Listing(
            id=str(uuid.uuid4()),
            source="realtor",
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
        print("Realtor.com: Returning mock data")

        location = preferences.location or "San Francisco, CA"

        return [
            Listing(
                id=str(uuid.uuid4()),
                source="realtor",
                url="https://www.realtor.com/mock-listing-1",
                address=f"555 Howard St, {location}",
                city=location.split(',')[0] if ',' in location else location,
                state="CA",
                zip_code="94105",
                price=590000,
                bedrooms=2,
                bathrooms=2.0,
                sqft=1250,
                property_type="condo",
                description="Luxury condo with concierge and amenities",
                images=["https://placehold.co/600x400"],
                days_on_market=10
            ),
            Listing(
                id=str(uuid.uuid4()),
                source="realtor",
                url="https://www.realtor.com/mock-listing-2",
                address=f"888 Brannan St, {location}",
                city=location.split(',')[0] if ',' in location else location,
                state="CA",
                zip_code="94103",
                price=710000,
                bedrooms=3,
                bathrooms=3.0,
                sqft=1700,
                property_type="townhouse",
                description="Modern townhouse with rooftop terrace and EV charging",
                images=["https://placehold.co/600x400"],
                days_on_market=3
            )
        ]
