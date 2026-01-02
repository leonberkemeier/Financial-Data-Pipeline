"""Unified ETL Pipeline - Run all data sources in a single command."""
import os
import argparse
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from loguru import logger

# Import individual pipelines
from crypto_etl_pipeline import run_crypto_pipeline
from bond_etl_pipeline import run_bond_pipeline
from economic_etl_pipeline import run_economic_pipeline
from commodity_etl_pipeline import run_commodity_pipeline

# Load environment variables
load_dotenv()


class UnifiedPipeline:
    """Orchestrates all ETL pipelines."""
    
    def __init__(self, config_path: str = "config/pipeline_config.yaml"):
        """Initialize unified pipeline with configuration."""
        self.config_path = config_path
        self.config = self.load_config()
        self.results = {}
        
    def load_config(self) -> Dict:
        """Load configuration from YAML file."""
        config_file = Path(self.config_path)
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}. Using defaults.")
            return self.get_default_config()
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Loaded configuration from: {config_file}")
        return config
    
    def get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            'stocks': {'enabled': True, 'tickers': ['AAPL', 'MSFT'], 'period': '30d'},
            'crypto': {'enabled': True, 'symbols': ['BTC', 'ETH'], 'days': 30},
            'bonds': {'enabled': True, 'periods': ['3MO', '10Y', '30Y'], 'days': 30, 'source': 'yahoo'},
            'economic': {'enabled': True, 'indicators': ['GDP', 'UNRATE'], 'days': 365},
            'commodities': {'enabled': True, 'symbols': ['CL=F', 'GC=F', 'SI=F'], 'days': 30, 'source': 'yahoo'},
            'execution': {'continue_on_error': True, 'parallel': False}
        }
    
    def run_stocks(self):
        """Run stock pipeline."""
        if not self.config.get('stocks', {}).get('enabled', False):
            logger.info("Stocks pipeline disabled in config")
            return {'status': 'skipped', 'reason': 'disabled in config'}
        
        try:
            logger.info("\n" + "🔵 " * 40)
            logger.info("RUNNING STOCKS PIPELINE")
            logger.info("🔵 " * 40)
            
            stocks_config = self.config['stocks']
            tickers = stocks_config.get('tickers', ['AAPL', 'MSFT'])
            period = stocks_config.get('period', '30d')
            
            # Run stock pipeline (from existing pipeline.py)
            from pipeline import FinancialDataPipeline
            stock_pipeline = FinancialDataPipeline(data_source='yahoo')
            stock_pipeline.run(tickers=tickers, period=period)
            
            return {'status': 'success', 'tickers': tickers, 'count': len(tickers)}
        except Exception as e:
            logger.error(f"Stocks pipeline failed: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def run_crypto(self):
        """Run crypto pipeline."""
        if not self.config.get('crypto', {}).get('enabled', False):
            logger.info("Crypto pipeline disabled in config")
            return {'status': 'skipped', 'reason': 'disabled in config'}
        
        try:
            logger.info("\n" + "🟡 " * 40)
            logger.info("RUNNING CRYPTO PIPELINE")
            logger.info("🟡 " * 40)
            
            crypto_config = self.config['crypto']
            symbols = crypto_config.get('symbols', ['BTC', 'ETH'])
            days = crypto_config.get('days', 30)
            rate_limit_delay = crypto_config.get('rate_limit_delay', 2.0)
            
            run_crypto_pipeline(symbols=symbols, days=days, rate_limit_delay=rate_limit_delay)
            
            return {'status': 'success', 'symbols': symbols, 'count': len(symbols)}
        except Exception as e:
            logger.error(f"Crypto pipeline failed: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def run_bonds(self):
        """Run bond pipeline."""
        if not self.config.get('bonds', {}).get('enabled', False):
            logger.info("Bonds pipeline disabled in config")
            return {'status': 'skipped', 'reason': 'disabled in config'}
        
        try:
            logger.info("\n" + "🟢 " * 40)
            logger.info("RUNNING BONDS PIPELINE")
            logger.info("🟢 " * 40)
            
            bonds_config = self.config['bonds']
            periods = bonds_config.get('periods', ['3MO', '10Y', '30Y'])
            days = bonds_config.get('days', 30)
            source = bonds_config.get('source', 'yahoo')
            
            run_bond_pipeline(periods=periods, days=days, source=source)
            
            return {'status': 'success', 'periods': periods, 'count': len(periods)}
        except Exception as e:
            logger.error(f"Bonds pipeline failed: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def run_economic(self):
        """Run economic indicators pipeline."""
        if not self.config.get('economic', {}).get('enabled', False):
            logger.info("Economic pipeline disabled in config")
            return {'status': 'skipped', 'reason': 'disabled in config'}
        
        try:
            logger.info("\n" + "🟣 " * 40)
            logger.info("RUNNING ECONOMIC INDICATORS PIPELINE")
            logger.info("🟣 " * 40)
            
            economic_config = self.config['economic']
            indicators = economic_config.get('indicators', ['GDP', 'UNRATE'])
            days = economic_config.get('days', 365)
            
            run_economic_pipeline(indicators=indicators, days=days)
            
            return {'status': 'success', 'indicators': indicators, 'count': len(indicators)}
        except Exception as e:
            logger.error(f"Economic pipeline failed: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def run_commodities(self):
        """Run commodities pipeline."""
        if not self.config.get('commodities', {}).get('enabled', False):
            logger.info("Commodities pipeline disabled in config")
            return {'status': 'skipped', 'reason': 'disabled in config'}
        
        try:
            logger.info("\n" + "🟠 " * 40)
            logger.info("RUNNING COMMODITIES PIPELINE")
            logger.info("🟠 " * 40)
            
            commodities_config = self.config['commodities']
            symbols = commodities_config.get('symbols', ['CL=F', 'GC=F', 'SI=F'])
            days = commodities_config.get('days', 30)
            source = commodities_config.get('source', 'yahoo')
            
            run_commodity_pipeline(symbols=symbols, days=days, source=source)
            
            return {'status': 'success', 'symbols': symbols, 'count': len(symbols)}
        except Exception as e:
            logger.error(f"Commodities pipeline failed: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def print_summary(self):
        """Print execution summary."""
        logger.info("\n" + "=" * 80)
        logger.info("UNIFIED ETL PIPELINE SUMMARY")
        logger.info("=" * 80)
        
        # Count statuses
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r['status'] == 'success')
        failed = sum(1 for r in self.results.values() if r['status'] == 'failed')
        skipped = sum(1 for r in self.results.values() if r['status'] == 'skipped')
        
        logger.info(f"\nTotal Pipelines: {total}")
        logger.info(f"✅ Successful: {success}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⏭️  Skipped: {skipped}")
        
        logger.info("\nDetailed Results:")
        
        # Stocks
        if 'stocks' in self.results:
            result = self.results['stocks']
            icon = "✅" if result['status'] == 'success' else "❌" if result['status'] == 'failed' else "⏭️"
            logger.info(f"\n{icon} Stocks:")
            if result['status'] == 'success':
                logger.info(f"   Loaded {result.get('count', 0)} tickers: {result.get('tickers', [])}")
            elif result['status'] == 'failed':
                logger.info(f"   Error: {result.get('error', 'Unknown')}")
            else:
                logger.info(f"   {result.get('reason', 'Not run')}")
        
        # Crypto
        if 'crypto' in self.results:
            result = self.results['crypto']
            icon = "✅" if result['status'] == 'success' else "❌" if result['status'] == 'failed' else "⏭️"
            logger.info(f"\n{icon} Crypto:")
            if result['status'] == 'success':
                logger.info(f"   Loaded {result.get('count', 0)} symbols: {result.get('symbols', [])}")
            elif result['status'] == 'failed':
                logger.info(f"   Error: {result.get('error', 'Unknown')}")
            else:
                logger.info(f"   {result.get('reason', 'Not run')}")
        
        # Bonds
        if 'bonds' in self.results:
            result = self.results['bonds']
            icon = "✅" if result['status'] == 'success' else "❌" if result['status'] == 'failed' else "⏭️"
            logger.info(f"\n{icon} Bonds:")
            if result['status'] == 'success':
                logger.info(f"   Loaded {result.get('count', 0)} periods: {result.get('periods', [])}")
            elif result['status'] == 'failed':
                logger.info(f"   Error: {result.get('error', 'Unknown')}")
            else:
                logger.info(f"   {result.get('reason', 'Not run')}")
        
        # Economic
        if 'economic' in self.results:
            result = self.results['economic']
            icon = "✅" if result['status'] == 'success' else "❌" if result['status'] == 'failed' else "⏭️"
            logger.info(f"\n{icon} Economic Indicators:")
            if result['status'] == 'success':
                logger.info(f"   Loaded {result.get('count', 0)} indicators: {result.get('indicators', [])}")
            elif result['status'] == 'failed':
                logger.info(f"   Error: {result.get('error', 'Unknown')}")
            else:
                logger.info(f"   {result.get('reason', 'Not run')}")
        
        # Commodities
        if 'commodities' in self.results:
            result = self.results['commodities']
            icon = "✅" if result['status'] == 'success' else "❌" if result['status'] == 'failed' else "⏭️"
            logger.info(f"\n{icon} Commodities:")
            if result['status'] == 'success':
                logger.info(f"   Loaded {result.get('count', 0)} symbols: {result.get('symbols', [])}")
            elif result['status'] == 'failed':
                logger.info(f"   Error: {result.get('error', 'Unknown')}")
            else:
                logger.info(f"   {result.get('reason', 'Not run')}")
        
        logger.info("\n" + "=" * 80)
        if failed == 0:
            logger.info("🎉 All enabled pipelines completed successfully!")
        else:
            logger.warning(f"⚠️  {failed} pipeline(s) failed. Check logs for details.")
        logger.info("=" * 80)
    
    def run(self, pipelines: List[str] = None):
        """
        Run all or specified pipelines.
        
        Args:
            pipelines: List of pipeline names to run. If None, run all enabled.
        """
        start_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info("UNIFIED ETL PIPELINE - START")
        logger.info("=" * 80)
        logger.info(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if pipelines is None:
            pipelines = ['stocks', 'crypto', 'bonds', 'economic', 'commodities']
        
        logger.info(f"Pipelines to run: {pipelines}")
        
        continue_on_error = self.config.get('execution', {}).get('continue_on_error', True)
        
        # Run each pipeline
        if 'stocks' in pipelines:
            self.results['stocks'] = self.run_stocks()
            if self.results['stocks']['status'] == 'failed' and not continue_on_error:
                logger.error("Stopping pipeline execution due to stocks failure")
                self.print_summary()
                return
        
        if 'crypto' in pipelines:
            self.results['crypto'] = self.run_crypto()
            if self.results['crypto']['status'] == 'failed' and not continue_on_error:
                logger.error("Stopping pipeline execution due to crypto failure")
                self.print_summary()
                return
        
        if 'bonds' in pipelines:
            self.results['bonds'] = self.run_bonds()
            if self.results['bonds']['status'] == 'failed' and not continue_on_error:
                logger.error("Stopping pipeline execution due to bonds failure")
                self.print_summary()
                return
        
        if 'economic' in pipelines:
            self.results['economic'] = self.run_economic()
        
        if 'commodities' in pipelines:
            self.results['commodities'] = self.run_commodities()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"\nEnd Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Duration: {duration}")
        
        # Print summary
        self.print_summary()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified ETL Pipeline - Run all financial data extractors"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all enabled pipelines"
    )
    parser.add_argument(
        "--stocks",
        action="store_true",
        help="Run stocks pipeline"
    )
    parser.add_argument(
        "--crypto",
        action="store_true",
        help="Run crypto pipeline"
    )
    parser.add_argument(
        "--bonds",
        action="store_true",
        help="Run bonds pipeline"
    )
    parser.add_argument(
        "--economic",
        action="store_true",
        help="Run economic indicators pipeline"
    )
    parser.add_argument(
        "--commodities",
        action="store_true",
        help="Run commodities pipeline"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/pipeline_config.yaml",
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    # Determine which pipelines to run
    pipelines = []
    if args.all:
        pipelines = ['stocks', 'crypto', 'bonds', 'economic', 'commodities']
    else:
        if args.stocks:
            pipelines.append('stocks')
        if args.crypto:
            pipelines.append('crypto')
        if args.bonds:
            pipelines.append('bonds')
        if args.economic:
            pipelines.append('economic')
        if args.commodities:
            pipelines.append('commodities')
    
    # If no specific pipeline selected, run all
    if not pipelines:
        pipelines = ['stocks', 'crypto', 'bonds', 'economic', 'commodities']
    
    # Create and run unified pipeline
    unified = UnifiedPipeline(config_path=args.config)
    unified.run(pipelines=pipelines)


if __name__ == "__main__":
    main()
