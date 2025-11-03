"""
Base Scraper Agent
Provides common functionality for all real estate platform scrapers
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from models.schemas import Listing, UserPreferences
from playwright.async_api import async_playwright, Browser, Page
import asyncio


class BaseScraper(ABC):
    """Abstract base class for real estate scrapers"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.max_results = 20  # Limit results per scraper

    @abstractmethod
    async def search(self, preferences: UserPreferences) -> List[Listing]:
        """
        Search for listings based on user preferences
        Must be implemented by each scraper
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return the source name (zillow, redfin, realtor)"""
        pass

    async def initialize_browser(self, headless: bool = True):
        """Initialize Playwright browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)

    async def close_browser(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()

    async def create_page(self) -> Page:
        """Create a new page with common settings"""
        if not self.browser:
            await self.initialize_browser()

        page = await self.browser.new_page()

        # Set viewport
        await page.set_viewport_size({"width": 1920, "height": 1080})

        # Set user agent to avoid detection
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        return page

    def build_search_url(self, preferences: UserPreferences) -> str:
        """
        Build search URL from preferences
        Must be implemented by each scraper
        """
        raise NotImplementedError

    async def extract_listings(self, page: Page) -> List[Listing]:
        """
        Extract listings from the page
        Must be implemented by each scraper
        """
        raise NotImplementedError

    def _format_price(self, price_str: str) -> int:
        """Convert price string to integer"""
        try:
            # Remove $ , and other characters, keep only digits
            price = ''.join(filter(str.isdigit, price_str))
            return int(price) if price else 0
        except ValueError:
            return 0

    def _format_bedrooms(self, bed_str: str) -> int:
        """Extract bedroom count from string"""
        try:
            # Extract first number from string
            numbers = ''.join(filter(str.isdigit, bed_str))
            return int(numbers) if numbers else 0
        except ValueError:
            return 0

    def _format_bathrooms(self, bath_str: str) -> float:
        """Extract bathroom count from string"""
        try:
            # Handle formats like "2.5", "2", "2.5 baths"
            import re
            match = re.search(r'\d+\.?\d*', bath_str)
            return float(match.group()) if match else 0.0
        except ValueError:
            return 0.0

    def _format_sqft(self, sqft_str: str) -> int:
        """Extract square footage from string"""
        try:
            # Remove commas and extract digits
            sqft = ''.join(filter(str.isdigit, sqft_str))
            return int(sqft) if sqft else 0
        except ValueError:
            return 0

    async def handle_rate_limiting(self, delay: float = 2.0):
        """Add delay to avoid rate limiting"""
        await asyncio.sleep(delay)
