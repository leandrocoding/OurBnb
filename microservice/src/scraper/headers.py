"""
Randomized HTTP headers for web scraping.

Provides realistic, varied browser headers to reduce fingerprinting risk.
"""

import random


# Realistic User-Agent strings (mix of Chrome, Firefox, Safari on various OS)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Accept-Language variations (European focus for Airbnb.ch)
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "de-CH,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "fr-CH,fr;q=0.9,de;q=0.8,en;q=0.7",
    "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "it-CH,it;q=0.9,de;q=0.8,en;q=0.7",
    "es-ES,es;q=0.9,en;q=0.8",
    "nl-NL,nl;q=0.9,en;q=0.8",
    "pt-PT,pt;q=0.9,en;q=0.8",
]

# Accept header variations
ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
]

# Sec-CH-UA (Client Hints) for Chromium browsers
SEC_CH_UA_OPTIONS = [
    '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    '"Not_A Brand";v="8", "Chromium";v="119", "Google Chrome";v="119"',
    '"Not_A Brand";v="8", "Chromium";v="121", "Google Chrome";v="121"',
    '"Chromium";v="120", "Not_A Brand";v="24", "Microsoft Edge";v="120"',
    None,  # Firefox/Safari don't send this
]

SEC_CH_UA_PLATFORM_OPTIONS = [
    '"Windows"',
    '"macOS"',
    '"Linux"',
    None,
]


def get_random_headers() -> dict:
    """
    Generate randomized but realistic browser headers.
    
    Returns:
        Dictionary of HTTP headers that mimic a real browser.
    """
    user_agent = random.choice(USER_AGENTS)
    is_chrome_based = "Chrome" in user_agent or "Edg" in user_agent
    is_firefox = "Firefox" in user_agent
    
    headers = {
        "User-Agent": user_agent,
        "Accept": random.choice(ACCEPT_HEADERS),
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    # Add Sec-Fetch headers (modern browsers)
    headers["Sec-Fetch-Dest"] = "document"
    headers["Sec-Fetch-Mode"] = "navigate"
    headers["Sec-Fetch-Site"] = random.choice(["none", "same-origin", "cross-site"])
    headers["Sec-Fetch-User"] = "?1"
    
    # Chrome/Edge specific headers
    if is_chrome_based:
        sec_ch_ua = random.choice([s for s in SEC_CH_UA_OPTIONS if s is not None])
        headers["Sec-CH-UA"] = sec_ch_ua
        headers["Sec-CH-UA-Mobile"] = "?0"
        platform = random.choice([p for p in SEC_CH_UA_PLATFORM_OPTIONS if p is not None])
        headers["Sec-CH-UA-Platform"] = platform
    
    # Firefox specific
    if is_firefox:
        headers["Sec-GPC"] = "1"  # Global Privacy Control
    
    # Randomly add DNT header (some users have it)
    if random.random() < 0.3:
        headers["DNT"] = "1"
    
    # Randomly add cache control (simulates different browsing patterns)
    if random.random() < 0.2:
        headers["Cache-Control"] = random.choice(["max-age=0", "no-cache"])
    
    return headers


def get_random_delay(min_seconds: float = 1.0, max_seconds: float = 4.0) -> float:
    """
    Get a random delay with slight bias toward the middle of the range.
    
    This creates more human-like timing patterns than uniform random.
    """
    # Use triangular distribution - more likely to be in the middle
    return random.triangular(min_seconds, max_seconds, (min_seconds + max_seconds) / 2)
