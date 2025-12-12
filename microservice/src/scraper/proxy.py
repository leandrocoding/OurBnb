"""Proxy management for the Airbnb scraper.

Provides rotating proxy support to reduce the risk of IP blocks.
Configure proxies via the PROXY_URLS environment variable.

Proxy URL format with authentication:
  http://username:password@host:port
"""

import os
import random
import logging
import requests
import time
from typing import Optional
from urllib.parse import urlparse
from itertools import cycle

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Manages a pool of rotating proxies for web scraping.
    
    Features:
    - Round-robin rotation for even distribution
    - Random rotation for less predictable patterns
    - Automatic fallback to direct connection if no proxies configured
    - Basic HTTP auth support (credentials in URL)
    - Failed proxy tracking (optional)
    """
    
    def __init__(self, proxy_urls: Optional[list[str]] = None):
        """
        Initialize the proxy manager.
        
        Args:
            proxy_urls: List of proxy URLs in format "http://[user:pass@]host:port"
                       If None, reads from PROXY_URLS env var (comma-separated)
        """
        if proxy_urls is None:
            env_proxies = os.getenv("PROXY_URLS", "")
            proxy_urls = [p.strip() for p in env_proxies.split(",") if p.strip()]
        
        self._proxies = proxy_urls
        self._cycle = cycle(proxy_urls) if proxy_urls else None
        # Proxy URL -> unix timestamp until which it should be skipped
        self._proxy_cooldown_until: dict[str, float] = {}
        
        if self._proxies:
            logger.info(f"ProxyManager initialized with {len(self._proxies)} proxies")
        else:
            logger.info("ProxyManager initialized without proxies (direct connection)")
    
    @property
    def has_proxies(self) -> bool:
        """Check if any proxies are configured."""
        return bool(self._proxies)
    
    @property
    def proxy_count(self) -> int:
        """Get the number of configured proxies."""
        return len(self._proxies)

    @property
    def cooldown_seconds(self) -> int:
        """Cooldown duration applied when a proxy fails."""
        return int(os.getenv("PROXY_COOLDOWN_SECONDS", "120"))

    @property
    def cooldown_active_count(self) -> int:
        """Number of proxies currently in cooldown."""
        if not self._proxies:
            return 0
        now = time.time()
        self._prune_expired_cooldowns(now)
        return sum(1 for p in self._proxies if self._is_in_cooldown(p, now))
    
    def get_proxy_dict(self, proxy_url: str) -> dict:
        """Convert a proxy URL to requests-compatible dict."""
        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def _proxy_url_from_dict(self, proxy_dict: Optional[dict]) -> Optional[str]:
        if not proxy_dict:
            return None
        # We always set both http/https to the same proxy URL
        return proxy_dict.get("https") or proxy_dict.get("http")

    def _is_in_cooldown(self, proxy_url: str, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.time()
        until = self._proxy_cooldown_until.get(proxy_url)
        return bool(until and now < until)

    def _prune_expired_cooldowns(self, now: Optional[float] = None) -> None:
        if now is None:
            now = time.time()
        expired = [p for p, until in self._proxy_cooldown_until.items() if until <= now]
        for p in expired:
            self._proxy_cooldown_until.pop(p, None)
    
    def get_next(self, strategy: str = "round_robin") -> Optional[dict]:
        """
        Get the next proxy using the specified strategy.
        
        Args:
            strategy: "round_robin" for sequential, "random" for random selection
            
        Returns:
            Proxy dict for requests, or None if no proxies configured
        """
        if not self._proxies:
            return None
        
        if strategy == "random":
            proxy_url = random.choice(self._proxies)
        else:  # round_robin
            proxy_url = next(self._cycle)
        
        return self.get_proxy_dict(proxy_url)
    
    def mark_failed(self, proxy_dict: Optional[dict]) -> None:
        """
        Mark a proxy as failed and put it on cooldown.
        
        Args:
            proxy_dict: The proxy dict that failed
        """
        proxy_url = self._proxy_url_from_dict(proxy_dict)
        if not proxy_url:
            return

        cooldown_seconds = self.cooldown_seconds
        now = time.time()
        self._proxy_cooldown_until[proxy_url] = now + cooldown_seconds
        logger.warning(
            "Proxy marked as failed (cooldown %ss): %s...",
            cooldown_seconds,
            proxy_url[:30],
        )
    
    def get_healthy_proxy(self, strategy: str = "round_robin") -> Optional[dict]:
        """
        Get a proxy that hasn't been marked as failed.
        Falls back to any proxy if all have failed.
        
        Args:
            strategy: Rotation strategy
            
        Returns:
            Proxy dict or None
        """
        if not self._proxies:
            return None

        now = time.time()
        self._prune_expired_cooldowns(now)

        # Only use proxies not currently cooling down
        available = [p for p in self._proxies if not self._is_in_cooldown(p, now)]

        if not available:
            # All proxies are down/cooling -> fall back to direct connection
            return None
        
        if strategy == "random":
            proxy_url = random.choice(available)
        else:
            proxy_url = available[0]
            # Rotate the available list
            available.append(available.pop(0))
        
        return self.get_proxy_dict(proxy_url)
    
    def reset_failures(self) -> None:
        """Clear all proxy cooldowns."""
        self._proxy_cooldown_until.clear()
    
    @property
    def proxy_urls(self) -> list[str]:
        """Get the list of configured proxy URLs."""
        return self._proxies.copy()
    
    def get_proxy_hostname(self, proxy_url: str) -> str:
        """Extract hostname from proxy URL (strips credentials)."""
        parsed = urlparse(proxy_url)
        return parsed.hostname or "unknown"
    
    def get_proxy_port(self, proxy_url: str) -> int:
        """Extract port from proxy URL."""
        parsed = urlparse(proxy_url)
        return parsed.port or 8888
    
    def _mask_ip(self, ip: str) -> str:
        """
        Mask an IP address for privacy (hide last octet for IPv4, last groups for IPv6).
        
        Examples:
            192.168.1.100 -> 192.168.1.xxx
            2001:db8::1 -> 2001:db8::xxx
        """
        if not ip or ip == "unknown":
            return ip
        
        # IPv4
        if "." in ip and ip.count(".") == 3:
            parts = ip.rsplit(".", 1)
            return f"{parts[0]}.xxx"
        
        # IPv6
        if ":" in ip:
            # Hide the last segment
            parts = ip.rsplit(":", 1)
            return f"{parts[0]}:xxxx"
        
        return ip
    
    def check_proxy_ip(self, proxy_url: str, timeout: int = 10) -> dict:
        """
        Check a proxy's external IP and status using myip.wtf.
        
        Args:
            proxy_url: The proxy URL to check
            timeout: Request timeout in seconds
            
        Returns:
            Dict with hostname, status, ip, and location info
        """
        hostname = self.get_proxy_hostname(proxy_url)
        port = self.get_proxy_port(proxy_url)
        
        result = {
            "hostname": hostname,
            "port": port,
            "status": "unknown",
            "ip": None,
            "location": None,
        }
        
        try:
            proxy_dict = self.get_proxy_dict(proxy_url)
            
            # Get IP info from myip.wtf (returns JSON)
            response = requests.get(
                "https://myip.wtf/json",
                proxies=proxy_dict,
                timeout=timeout,
                headers={"User-Agent": "curl/8.0"}
            )
            response.raise_for_status()
            
            data = response.json()
            result["status"] = "up"
            # Mask the IP for privacy (hide last octet)
            raw_ip = data.get("YourFuckingIPAddress", "unknown")
            result["ip"] = self._mask_ip(raw_ip)
            result["location"] = data.get("YourFuckingLocation", "unknown")
            
        except requests.exceptions.Timeout:
            result["status"] = "timeout"
        except requests.exceptions.ProxyError:
            result["status"] = "proxy_error"
        except requests.exceptions.ConnectionError:
            result["status"] = "connection_error"
        except Exception as e:
            result["status"] = f"error: {str(e)[:50]}"
        
        return result
    
    def check_all_proxies(self, timeout: int = 10) -> list[dict]:
        """
        Check all configured proxies and return their status.
        
        Args:
            timeout: Request timeout per proxy
            
        Returns:
            List of proxy status dicts
        """
        results = []
        for proxy_url in self._proxies:
            results.append(self.check_proxy_ip(proxy_url, timeout))
        return results


# Global proxy manager instance
_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    """Get or create the global proxy manager instance."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


def configure_proxies(proxy_urls: list[str]) -> ProxyManager:
    """
    Configure the global proxy manager with specific proxies.
    
    Args:
        proxy_urls: List of proxy URLs (can include user:pass@ for auth)
        
    Returns:
        The configured ProxyManager instance
    """
    global _proxy_manager
    _proxy_manager = ProxyManager(proxy_urls=proxy_urls)
    return _proxy_manager
