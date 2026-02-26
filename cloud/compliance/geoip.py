"""
GeoIP enforcement using MaxMind database.
"""
import geoip2.database
import os
import logging

logger = logging.getLogger(__name__)

class GeoIPEnforcer:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.getenv("GEOIP_DB_PATH", "GeoLite2-Country.mmdb")
        try:
            self.reader = geoip2.database.Reader(db_path)
            logger.info(f"GeoIP database loaded from {db_path}")
        except Exception as e:
            logger.error(f"Failed to load GeoIP database: {e}")
            self.reader = None

    def get_country(self, ip: str) -> str:
        if not self.reader:
            return None
        try:
            response = self.reader.country(ip)
            return response.country.iso_code
        except:
            return None

    def is_allowed(self, ip: str, allowed_countries: list) -> bool:
        country = self.get_country(ip)
        if not country:
            # Unknown location – deny by default (can be configured)
            return False
        return country in allowed_countries
