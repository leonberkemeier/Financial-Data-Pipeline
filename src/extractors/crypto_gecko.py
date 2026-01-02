"""CoinGecko cryptocurrency data extractor."""
import requests
from requests import exceptions
import pandas as pd
import time
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger


class CoinGeckoExtractor:
    """Extract cryptocurrency data from CoinGecko API."""

    def __init__(self, rate_limit_delay: float = 1.5, cache_dir: str = "data/cache"):
        self.source_name = "coingecko"
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()
        self.rate_limit_delay = rate_limit_delay  # Delay in seconds between API calls
        
        # Setup metadata cache
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_cache_file = self.cache_dir / "crypto_metadata_cache.json"
        self.metadata_cache = self._load_metadata_cache()

    def _load_metadata_cache(self) -> Dict:
        """Load metadata cache from file."""
        if self.metadata_cache_file.exists():
            try:
                with open(self.metadata_cache_file, 'r') as f:
                    cache = json.load(f)
                logger.info(f"Loaded metadata cache with {len(cache)} entries")
                return cache
            except Exception as e:
                logger.warning(f"Failed to load metadata cache: {e}")
                return {}
        return {}
    
    def _save_metadata_cache(self):
        """Save metadata cache to file."""
        try:
            with open(self.metadata_cache_file, 'w') as f:
                json.dump(self.metadata_cache, f, indent=2)
            logger.debug(f"Saved metadata cache with {len(self.metadata_cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to save metadata cache: {e}")

    def extract_crypto_prices(
        self,
        symbols: List[str],
        days: int = 1
    ) -> pd.DataFrame:
        """
        Extract current and historical crypto prices.

        Args:
            symbols: List of cryptocurrency symbols (BTC, ETH, etc.)
            days: Number of days of historical data to fetch (1, 7, 30, etc.)

        Returns:
            DataFrame with cryptocurrency price data
        """
        logger.info(f"Extracting crypto price data for {len(symbols)} symbols from CoinGecko")
        
        all_data = []
        
        # Map common symbols to CoinGecko IDs
        symbol_to_id = self._get_symbol_mapping(symbols)
        
        for idx, (symbol, crypto_id) in enumerate(symbol_to_id.items()):
            try:
                # Rate limiting: sleep BEFORE request (except for first one)
                if idx > 0:
                    logger.debug(f"Waiting {self.rate_limit_delay} seconds before next request...")
                    time.sleep(self.rate_limit_delay)
                
                logger.debug(f"Fetching data for {symbol}")
                
                # Fetch market data
                url = f"{self.base_url}/coins/{crypto_id}/market_chart"
                params = {
                    "vs_currency": "usd",
                    "days": str(days),
                    "interval": "daily"
                }
                
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if not data.get('prices'):
                    logger.warning(f"No price data found for {symbol}")
                    continue
                
                # Extract prices, market caps, and volumes
                prices = data.get('prices', [])
                market_caps = data.get('market_caps', [])
                volumes = data.get('total_volumes', [])
                
                # Convert to DataFrame
                df = pd.DataFrame({
                    'timestamp': [pd.to_datetime(p[0], unit='ms') for p in prices],
                    'price': [p[1] for p in prices],
                    'market_cap': [m[1] if m else None for m in market_caps],
                    'volume': [v[1] if v else None for v in volumes],
                    'symbol': symbol,
                    'crypto_id': crypto_id
                })
                
                all_data.append(df)
                logger.debug(f"Successfully fetched {len(df)} records for {symbol}")
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {str(e)}")
                # Sleep longer on error to avoid further rate limiting
                if "429" in str(e) or "Too Many Requests" in str(e):
                    logger.warning(f"Rate limit hit, waiting {self.rate_limit_delay * 2} seconds...")
                    time.sleep(self.rate_limit_delay * 2)
                continue
        
        if not all_data:
            logger.warning("No crypto price data extracted from CoinGecko")
            return pd.DataFrame()
        
        # Combine all data
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data['date'] = combined_data['timestamp'].dt.date
        
        logger.info(f"Extracted {len(combined_data)} total records")
        return combined_data

    def extract_crypto_info(self, symbols: List[str]) -> pd.DataFrame:
        """
        Extract cryptocurrency metadata and information.
        Uses cache to avoid repeated API calls for the same cryptocurrency.

        Args:
            symbols: List of cryptocurrency symbols

        Returns:
            DataFrame with crypto information
        """
        logger.info(f"Extracting crypto info for {len(symbols)} symbols")
        
        crypto_data = []
        symbol_to_id = self._get_symbol_mapping(symbols)
        cache_updated = False
        
        for idx, (symbol, crypto_id) in enumerate(symbol_to_id.items()):
            # Check cache first
            if symbol in self.metadata_cache:
                logger.debug(f"Using cached metadata for {symbol}")
                crypto_data.append(self.metadata_cache[symbol])
                continue
            
            # Not in cache, fetch from API
            try:
                # Rate limiting: sleep BEFORE request (except for first uncached one)
                if idx > 0 and len([s for s in symbol_to_id.keys() if s in self.metadata_cache]) < idx:
                    logger.debug(f"Waiting {self.rate_limit_delay} seconds before next API request...")
                    time.sleep(self.rate_limit_delay)
                
                logger.debug(f"Fetching info for {symbol} from API")
                
                url = f"{self.base_url}/coins/{crypto_id}"
                params = {
                    "localization": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false"
                }
                
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                market_data = data.get('market_data', {})
                
                metadata = {
                    'symbol': symbol,
                    'name': data.get('name', symbol),
                    'chain': self._get_chain(crypto_id),
                    'description': data.get('description', {}).get('en', ''),
                    'circulating_supply': market_data.get('circulating_supply'),
                    'total_supply': market_data.get('total_supply'),
                    'max_supply': market_data.get('max_supply'),
                    'market_cap_usd': market_data.get('market_cap', {}).get('usd'),
                    'all_time_high': market_data.get('ath', {}).get('usd'),
                    'all_time_low': market_data.get('atl', {}).get('usd'),
                    'cached_at': datetime.now().isoformat()
                }
                
                crypto_data.append(metadata)
                
                # Save to cache
                self.metadata_cache[symbol] = metadata
                cache_updated = True
                
                logger.debug(f"Extracted and cached info for {symbol}")
                
            except Exception as e:
                logger.error(f"Error extracting info for {symbol}: {str(e)}")
                # Create minimal metadata entry if API fails
                minimal_metadata = {
                    'symbol': symbol,
                    'name': symbol,
                    'chain': 'Unknown',
                    'description': '',
                    'cached_at': datetime.now().isoformat()
                }
                crypto_data.append(minimal_metadata)
                # Sleep longer on rate limit errors
                if "429" in str(e) or "Too Many Requests" in str(e):
                    logger.warning(f"Rate limit hit, waiting {self.rate_limit_delay * 2} seconds...")
                    time.sleep(self.rate_limit_delay * 2)
                continue
        
        # Save cache if updated
        if cache_updated:
            self._save_metadata_cache()
        
        if not crypto_data:
            logger.warning("No crypto info extracted")
            return pd.DataFrame()
        
        df = pd.DataFrame(crypto_data)
        logger.info(f"Extracted info for {len(df)} cryptocurrencies ({len([d for d in crypto_data if 'cached_at' in self.metadata_cache.get(d['symbol'], {})])} from cache)")
        return df

    def extract_24h_change(self, symbols: List[str]) -> pd.DataFrame:
        """
        Extract 24h and 7d price change data.

        Args:
            symbols: List of cryptocurrency symbols

        Returns:
            DataFrame with price change data
        """
        logger.info(f"Extracting 24h/7d price change for {len(symbols)} symbols")
        
        change_data = []
        symbol_to_id = self._get_symbol_mapping(symbols)
        
        for idx, (symbol, crypto_id) in enumerate(symbol_to_id.items()):
            try:
                # Rate limiting: sleep BEFORE request (except for first one)
                if idx > 0:
                    logger.debug(f"Waiting {self.rate_limit_delay} seconds before next request...")
                    time.sleep(self.rate_limit_delay)
                
                url = f"{self.base_url}/coins/{crypto_id}"
                params = {
                    "localization": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false"
                }
                
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                market_data = data.get('market_data', {})
                
                change_data.append({
                    'symbol': symbol,
                    'price_change_24h': market_data.get('price_change_percentage_24h'),
                    'price_change_7d': market_data.get('price_change_percentage_7d'),
                    'price_change_30d': market_data.get('price_change_percentage_30d'),
                    'price_change_1y': market_data.get('price_change_percentage_1y')
                })
                
            except Exception as e:
                logger.error(f"Error extracting price change for {symbol}: {str(e)}")
                # Sleep longer on rate limit errors
                if "429" in str(e) or "Too Many Requests" in str(e):
                    logger.warning(f"Rate limit hit, waiting {self.rate_limit_delay * 2} seconds...")
                    time.sleep(self.rate_limit_delay * 2)
                continue
        
        if not change_data:
            logger.warning("No price change data extracted")
            return pd.DataFrame()
        
        df = pd.DataFrame(change_data)
        logger.info(f"Extracted price change for {len(df)} cryptocurrencies")
        return df

    def _get_symbol_mapping(self, symbols: List[str]) -> Dict[str, str]:
        """
        Map symbol to CoinGecko ID.

        Args:
            symbols: List of symbols to map

        Returns:
            Dictionary mapping symbol to CoinGecko ID
        """
        # Common mappings - can be extended
        common_mappings = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'ADA': 'cardano',
            'SOL': 'solana',
            'DOGE': 'dogecoin',
            'XRP': 'ripple',
            'DOT': 'polkadot',
            'MATIC': 'matic-network',
            'LINK': 'chainlink',
            'USDT': 'tether',
            'USDC': 'usd-coin',
            'BNB': 'binancecoin',
            'XLM': 'stellar',
            'AVAX': 'avalanche-2',
            'FTM': 'fantom',
            'ATOM': 'cosmos',
            'NEAR': 'near',
            'AAVE': 'aave',
            'CURVE': 'curve-dao-token',
            'UNI': 'uniswap',
            'ARB': 'arbitrum',
            'OP': 'optimism'
        }
        
        mapping = {}
        for symbol in symbols:
            symbol_upper = symbol.upper()
            if symbol_upper in common_mappings:
                mapping[symbol_upper] = common_mappings[symbol_upper]
            else:
                # Try to search for the symbol
                logger.warning(f"No direct mapping for {symbol}, attempting to search")
                # Could implement search functionality here
                mapping[symbol_upper] = symbol.lower()
        
        return mapping

    def _get_chain(self, crypto_id: str) -> str:
        """
        Get the blockchain chain for a cryptocurrency.

        Args:
            crypto_id: CoinGecko cryptocurrency ID

        Returns:
            Blockchain name
        """
        # Common chains - can be extended
        chain_mappings = {
            'bitcoin': 'Bitcoin',
            'ethereum': 'Ethereum',
            'cardano': 'Cardano',
            'solana': 'Solana',
            'dogecoin': 'Dogecoin',
            'ripple': 'Ripple',
            'polkadot': 'Polkadot',
            'matic-network': 'Polygon',
            'binancecoin': 'Binance Smart Chain',
            'avalanche-2': 'Avalanche',
            'fantom': 'Fantom',
            'cosmos': 'Cosmos',
            'near': 'NEAR Protocol',
            'aave': 'Ethereum',  # Ethereum-based token
            'chainlink': 'Ethereum'  # Ethereum-based token
        }
        
        return chain_mappings.get(crypto_id, 'Unknown')
