"""
IP地理位置匹配工具
文件路径:src/infrastructure/browser/ip_matcher.py
功能:根据代理IP的地理位置自动调整指纹参数(时区、语言等)
"""

import logging
import aiohttp
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# 时区映射表(国家代码 -> 默认时区)
TIMEZONE_MAP = {
    'CN': 'Asia/Shanghai',
    'HK': 'Asia/Hong_Kong',
    'TW': 'Asia/Taipei',
    'US': 'America/New_York',
    'GB': 'Europe/London',
    'JP': 'Asia/Tokyo',
    'KR': 'Asia/Seoul',
    'SG': 'Asia/Singapore',
    'AU': 'Australia/Sydney',
    'DE': 'Europe/Berlin',
    'FR': 'Europe/Paris',
    'CA': 'America/Toronto',
    'RU': 'Europe/Moscow',
    'IN': 'Asia/Kolkata',
    'BR': 'America/Sao_Paulo',
    'MX': 'America/Mexico_City',
    'IT': 'Europe/Rome',
    'ES': 'Europe/Madrid',
    'NL': 'Europe/Amsterdam',
    'SE': 'Europe/Stockholm',
}

# 语言映射表(国家代码 -> 语言列表)
LANGUAGE_MAP = {
    'CN': ['zh-CN', 'zh', 'en'],
    'HK': ['zh-HK', 'zh', 'en'],
    'TW': ['zh-TW', 'zh', 'en'],
    'US': ['en-US', 'en'],
    'GB': ['en-GB', 'en'],
    'JP': ['ja-JP', 'ja', 'en'],
    'KR': ['ko-KR', 'ko', 'en'],
    'SG': ['en-SG', 'zh', 'en'],
    'AU': ['en-AU', 'en'],
    'DE': ['de-DE', 'de', 'en'],
    'FR': ['fr-FR', 'fr', 'en'],
    'CA': ['en-CA', 'fr-CA', 'en'],
    'RU': ['ru-RU', 'ru', 'en'],
    'IN': ['en-IN', 'hi', 'en'],
    'BR': ['pt-BR', 'pt', 'en'],
    'MX': ['es-MX', 'es', 'en'],
    'IT': ['it-IT', 'it', 'en'],
    'ES': ['es-ES', 'es', 'en'],
    'NL': ['nl-NL', 'nl', 'en'],
    'SE': ['sv-SE', 'sv', 'en'],
}

# Locale映射表(国家代码 -> 主locale)
LOCALE_MAP = {
    'CN': 'zh-CN',
    'HK': 'zh-HK',
    'TW': 'zh-TW',
    'US': 'en-US',
    'GB': 'en-GB',
    'JP': 'ja-JP',
    'KR': 'ko-KR',
    'SG': 'en-SG',
    'AU': 'en-AU',
    'DE': 'de-DE',
    'FR': 'fr-FR',
    'CA': 'en-CA',
    'RU': 'ru-RU',
    'IN': 'en-IN',
    'BR': 'pt-BR',
    'MX': 'es-MX',
    'IT': 'it-IT',
    'ES': 'es-ES',
    'NL': 'nl-NL',
    'SE': 'sv-SE',
}


class IPMatcher:
    """IP地理位置匹配工具类
    
    根据代理IP自动调整指纹参数,确保IP与指纹的一致性
    """
    
    # IP查询结果缓存
    _cache: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    async def get_geolocation(ip_address: str) -> Optional[Dict[str, Any]]:
        """查询IP地理位置信息
        
        Args:
            ip_address: IP地址
            
        Returns:
            地理位置信息字典,失败返回None
        """
        # 检查缓存
        if ip_address in IPMatcher._cache:
            logger.debug(f"使用缓存的IP信息: {ip_address}")
            return IPMatcher._cache[ip_address]
        
        try:
            # 使用 ip-api.com (免费,无需API key,限制45次/分钟)
            url = f'http://ip-api.com/json/{ip_address}'
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == 'success':
                            geo_info = {
                                'country': data.get('country'),
                                'country_code': data.get('countryCode'),
                                'region': data.get('regionName'),
                                'city': data.get('city'),
                                'timezone': data.get('timezone'),
                                'lat': data.get('lat'),
                                'lon': data.get('lon'),
                                'isp': data.get('isp')
                            }
                            
                            # 缓存结果
                            IPMatcher._cache[ip_address] = geo_info
                            logger.info(f"IP地理位置查询成功: {ip_address} -> {geo_info['country']}, {geo_info['city']}")
                            return geo_info
                        else:
                            logger.warning(f"IP查询失败: {data.get('message')}")
        except Exception as e:
            logger.error(f"IP地理位置查询异常: {e}")
        
        return None
    
    @staticmethod
    def match_timezone(country_code: str, timezone: Optional[str] = None) -> str:
        """根据国家代码匹配时区
        
        Args:
            country_code: 国家代码(如 'CN', 'US')
            timezone: IP返回的时区(优先使用)
            
        Returns:
            时区字符串(如 'Asia/Shanghai')
        """
        # 优先使用IP返回的时区
        if timezone:
            return timezone
        
        # 回退到国家默认时区
        matched = TIMEZONE_MAP.get(country_code, 'UTC')
        logger.debug(f"时区匹配: {country_code} -> {matched}")
        return matched
    
    @staticmethod
    def match_language(country_code: str) -> list:
        """根据国家代码匹配语言列表
        
        Args:
            country_code: 国家代码
            
        Returns:
            语言列表(如 ['zh-CN', 'zh', 'en'])
        """
        matched = LANGUAGE_MAP.get(country_code, ['en-US', 'en'])
        logger.debug(f"语言匹配: {country_code} -> {matched}")
        return matched
    
    @staticmethod
    def match_locale(country_code: str) -> str:
        """根据国家代码匹配主locale
        
        Args:
            country_code: 国家代码
            
        Returns:
            Locale字符串(如 'zh-CN')
        """
        matched = LOCALE_MAP.get(country_code, 'en-US')
        logger.debug(f"Locale匹配: {country_code} -> {matched}")
        return matched
    
    @staticmethod
    async def adjust_fingerprint_by_ip(
        fingerprint: Dict[str, Any],
        ip_address: str
    ) -> Dict[str, Any]:
        """根据代理IP自动调整指纹参数
        
        Args:
            fingerprint: 原始指纹配置
            ip_address: 代理IP地址
            
        Returns:
            调整后的指纹配置
        """
        logger.info(f"根据IP调整指纹: {ip_address}")
        
        # 查询IP地理位置
        geo = await IPMatcher.get_geolocation(ip_address)
        
        if not geo:
            logger.warning("IP查询失败,使用默认指纹配置")
            return fingerprint
        
        country_code = geo.get('country_code')
        if not country_code:
            logger.warning("未获取到国家代码,使用默认指纹配置")
            return fingerprint
        
        # 调整时区
        fingerprint['timezone_id'] = IPMatcher.match_timezone(
            country_code,
            geo.get('timezone')
        )
        
        # 调整语言
        languages = IPMatcher.match_language(country_code)
        fingerprint['languages'] = languages
        
        # 调整locale
        fingerprint['locale'] = IPMatcher.match_locale(country_code)
        
        logger.info(
            f"指纹已调整: timezone={fingerprint['timezone_id']}, "
            f"locale={fingerprint['locale']}, languages={languages}"
        )
        
        return fingerprint
    
    @staticmethod
    def clear_cache() -> None:
        """清空IP查询缓存"""
        IPMatcher._cache.clear()
        logger.info("IP查询缓存已清空")
