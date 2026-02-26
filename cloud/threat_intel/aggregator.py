import aiohttp
import asyncio
import redis.asyncio as aioredis
import json
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ThreatIntelAggregator:
    def __init__(self, redis_client: aioredis.Redis, cache_ttl: int = 3600):
        self.redis = redis_client
        self.cache_ttl = cache_ttl
        self.apis = {
            "abuseipdb": "https://api.abuseipdb.com/api/v2/check",
            "virustotal": "https://www.virustotal.com/api/v3/ip_addresses/",
        }
        self.api_keys = {
            "abuseipdb": os.getenv("ABUSEIPDB_API_KEY"),
            "virustotal": os.getenv("VIRUSTOTAL_API_KEY"),
        }
        self.fallback_score = 50  # neutral

    async def check_ip(self, ip: str) -> int:
        cache_key = f"threat:intel:{ip}"
        cached = await self.redis.get(cache_key)
        if cached:
            return int(cached)

        tasks = []
        async with aiohttp.ClientSession() as session:
            if self.api_keys["abuseipdb"]:
                tasks.append(self._query_abuseipdb(session, ip))
            if self.api_keys["virustotal"]:
                tasks.append(self._query_virustotal(session, ip))

            if not tasks:
                return self.fallback_score

            results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_scores = [r for r in results if isinstance(r, int)]
        if not valid_scores:
            score = self.fallback_score
        else:
            score = sum(valid_scores) // len(valid_scores)

        await self.redis.setex(cache_key, self.cache_ttl, str(score))
        return score

    async def _query_abuseipdb(self, session, ip) -> Optional[int]:
        try:
            headers = {"Key": self.api_keys["abuseipdb"], "Accept": "application/json"}
            params = {"ipAddress": ip, "maxAgeInDays": 90}
            async with session.get(self.apis["abuseipdb"], headers=headers, params=params, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    abuse_score = data["data"]["abuseConfidenceScore"]
                    return 100 - abuse_score
                else:
                    logger.error(f"AbuseIPDB error {resp.status}")
                    return None
        except Exception as e:
            logger.exception(f"AbuseIPDB exception: {e}")
            return None

    async def _query_virustotal(self, session, ip) -> Optional[int]:
        try:
            headers = {"x-apikey": self.api_keys["virustotal"]}
            async with session.get(self.apis["virustotal"] + ip, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data["data"]["attributes"]["last_analysis_stats"]
                    total = sum(stats.values())
                    malicious = stats.get("malicious", 0)
                    return int((total - malicious) / total * 100) if total > 0 else 50
                else:
                    logger.error(f"VirusTotal error {resp.status}")
                    return None
        except Exception as e:
            logger.exception(f"VirusTotal exception: {e}")
            return None
