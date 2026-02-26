"""
Threat intelligence aggregator with multiple sources, caching, and fallback.
"""
import aiohttp
import asyncio
import redis.asyncio as aioredis
import json
import logging
import os
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class ThreatIntelAggregator:
    def __init__(self, redis_client: aioredis.Redis, cache_ttl: int = 3600):
        self.redis = redis_client
        self.cache_ttl = cache_ttl
        self.apis = {
            "abuseipdb": {
                "url": "https://api.abuseipdb.com/api/v2/check",
                "api_key": os.getenv("ABUSEIPDB_API_KEY"),
                "enabled": bool(os.getenv("ABUSEIPDB_API_KEY"))
            },
            "virustotal": {
                "url": "https://www.virustotal.com/api/v3/ip_addresses/",
                "api_key": os.getenv("VIRUSTOTAL_API_KEY"),
                "enabled": bool(os.getenv("VIRUSTOTAL_API_KEY"))
            },
            # Add more sources as needed
        }
        self.fallback_score = int(os.getenv("THREAT_INTEL_FALLBACK_SCORE", "50"))
        self.timeout = aiohttp.ClientTimeout(total=5)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    async def check_ip(self, ip: str) -> int:
        """
        Return reputation score (0-100, higher is safer) for an IP.
        Uses Redis cache. On failure, returns fallback.
        """
        cache_key = f"threat:intel:{ip}"
        cached = await self.redis.get(cache_key)
        if cached:
            return int(cached)

        tasks = []
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for source, config in self.apis.items():
                if config["enabled"]:
                    if source == "abuseipdb":
                        tasks.append(self._query_abuseipdb(session, ip, config))
                    elif source == "virustotal":
                        tasks.append(self._query_virustotal(session, ip, config))
                    # Add other sources similarly

            if not tasks:
                logger.warning("No threat intel sources enabled, using fallback")
                return self.fallback_score

            results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_scores = [r for r in results if isinstance(r, int)]
        if not valid_scores:
            score = self.fallback_score
        else:
            score = sum(valid_scores) // len(valid_scores)

        await self.redis.setex(cache_key, self.cache_ttl, str(score))
        return score

    async def _query_abuseipdb(self, session, ip, config):
        try:
            headers = {"Key": config["api_key"], "Accept": "application/json"}
            params = {"ipAddress": ip, "maxAgeInDays": 90}
            async with session.get(config["url"], headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    abuse_score = data["data"]["abuseConfidenceScore"]
                    # Convert to reputation: 100 - abuse_score
                    return 100 - abuse_score
                else:
                    logger.error(f"AbuseIPDB error {resp.status} for {ip}")
                    return None
        except Exception as e:
            logger.exception(f"AbuseIPDB exception for {ip}: {e}")
            return None

    async def _query_virustotal(self, session, ip, config):
        try:
            headers = {"x-apikey": config["api_key"]}
            async with session.get(config["url"] + ip, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data["data"]["attributes"]["last_analysis_stats"]
                    total = sum(stats.values())
                    malicious = stats.get("malicious", 0)
                    if total > 0:
                        return int((total - malicious) / total * 100)
                    else:
                        return 50
                else:
                    logger.error(f"VirusTotal error {resp.status} for {ip}")
                    return None
        except Exception as e:
            logger.exception(f"VirusTotal exception for {ip}: {e}")
            return None
