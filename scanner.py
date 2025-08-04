import asyncio
import websockets
import json
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
import time
import traceback
from collections import defaultdict
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FVGScanner:
    def __init__(self):
        self.exchange = ccxt.binance()
        self.clients = set()
        self.is_scanning = False
        self.pairs_data = {}
        self.fvg_cache = defaultdict(dict)
        self.block_cache = defaultdict(list)
        self.current_prices = {}
        self.scan_stats = {
            'total_pairs': 0,
            'scanned_pairs': 0,
            'total_fvgs': 0,
            'bullish_fvgs': 0,
            'bearish_fvgs': 0,
            'institutional_blocks': 0,
            'touched_fvgs': 0
        }
        
        # Pine Script settings
        self.pine_settings = {
            'proximity_filter': 1.0,  # Default 1.0% like Pine Script
            'lookback': 500,          # Pine Script lookback
            'min_block_fvgs': 2,      # Minimum FVGs for block
            'timeframes': ['1m', '5m', '15m', '1h', '4h', '12h', '1d', '1w']
        }

    def calculate_distance_percentage(self, current_price, fvg_low, fvg_high):
        """Calculate exact distance percentage like Pine Script"""
        if current_price >= fvg_low and current_price <= fvg_high:
            return 0.0  # Inside FVG
        elif current_price < fvg_low:
            return ((fvg_low - current_price) / current_price) * 100
        else:
            return ((current_price - fvg_high) / current_price) * 100

    def is_fvg_touched(self, current_price, fvg_low, fvg_high, tolerance=0.001):
        """Check if price touches FVG boundaries with tolerance (Pine Script logic)"""
        touch_threshold_low = fvg_low * (1 - tolerance)
        touch_threshold_high = fvg_high * (1 + tolerance)
        
        return (current_price >= touch_threshold_low and current_price <= touch_threshold_high)

    def calculate_fvg_strength(self, gap_size, volume, timeframe):
        """Calculate FVG strength based on gap size, volume, and timeframe"""
        tf_multiplier = {
            '1m': 0.5, '5m': 0.7, '15m': 1.0, '1h': 1.5, 
            '4h': 2.0, '12h': 2.5, '1d': 3.0, '1w': 4.0
        }
        
        base_strength = gap_size * 1000000  # Gap size impact
        volume_strength = volume / 1000000 if volume > 0 else 1
        tf_factor = tf_multiplier.get(timeframe, 1.0)
        
        strength = (base_strength * volume_strength * tf_factor)
        return min(max(strength, 0), 100)  # Clamp between 0-100

    def detect_institutional_blocks(self, symbol, timeframe, fvgs):
        """Detect institutional blocks - overlapping FVGs across timeframes"""
        if len(fvgs) < self.pine_settings['min_block_fvgs']:
            return []
        
        blocks = []
        block_id = 0
        
        # Group FVGs by proximity and type
        for i, base_fvg in enumerate(fvgs):
            overlapping_fvgs = [base_fvg]
            
            for j, compare_fvg in enumerate(fvgs[i+1:], i+1):
                # Check if FVGs overlap or are very close
                if (base_fvg['fvg_type'] == compare_fvg['fvg_type'] and
                    self.fvgs_overlap(base_fvg, compare_fvg)):
                    overlapping_fvgs.append(compare_fvg)
            
            # Create block if we have enough overlapping FVGs
            if len(overlapping_fvgs) >= self.pine_settings['min_block_fvgs']:
                block_strength = self.calculate_block_strength(overlapping_fvgs)
                block_badge = self.create_block_badge(overlapping_fvgs, timeframe, block_strength)
                
                block = {
                    'block_id': f"{symbol}_{timeframe}_{block_id}",
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'type': overlapping_fvgs[0]['fvg_type'],
                    'fvg_count': len(overlapping_fvgs),
                    'strength': block_strength,
                    'badge': block_badge,
                    'fvgs': overlapping_fvgs,
                    'low': min(fvg['gap_low'] for fvg in overlapping_fvgs),
                    'high': max(fvg['gap_high'] for fvg in overlapping_fvgs)
                }
                blocks.append(block)
                block_id += 1
        
        return blocks

    def fvgs_overlap(self, fvg1, fvg2, threshold=0.001):
        """Check if two FVGs overlap or are very close"""
        gap1_low, gap1_high = fvg1['gap_low'], fvg1['gap_high']
        gap2_low, gap2_high = fvg2['gap_low'], fvg2['gap_high']
        
        # Add small threshold for proximity
        gap1_low_thresh = gap1_low * (1 - threshold)
        gap1_high_thresh = gap1_high * (1 + threshold)
        gap2_low_thresh = gap2_low * (1 - threshold)
        gap2_high_thresh = gap2_high * (1 + threshold)
        
        return not (gap1_high_thresh < gap2_low_thresh or gap2_high_thresh < gap1_low_thresh)

    def calculate_block_strength(self, fvgs):
        """Calculate institutional block strength"""
        if not fvgs:
            return 0
        
        # Factors: FVG count, average gap size, volume, timeframe diversity
        fvg_count_factor = min(len(fvgs) * 10, 40)  # Max 40 points for FVG count
        
        avg_gap_size = sum((fvg['gap_high'] - fvg['gap_low']) / fvg['gap_low'] 
                          for fvg in fvgs) / len(fvgs)
        gap_size_factor = min(avg_gap_size * 10000, 30)  # Max 30 points for gap size
        
        avg_volume = sum(fvg.get('volume_strength', 0) for fvg in fvgs) / len(fvgs)
        volume_factor = min(avg_volume / 1000000, 30)  # Max 30 points for volume
        
        total_strength = fvg_count_factor + gap_size_factor + volume_factor
        return min(int(total_strength), 100)

    def create_block_badge(self, fvgs, timeframe, strength):
        """Create block badge like Pine Script"""
        fvg_type = fvgs[0]['fvg_type'].upper()
        count = len(fvgs)
        
        if strength >= 80:
            strength_label = "EXTREME"
            emoji = "🔥"
        elif strength >= 60:
            strength_label = "STRONG"
            emoji = "💪"
        elif strength >= 40:
            strength_label = "MEDIUM"
            emoji = "📊"
        else:
            strength_label = "WEAK"
            emoji = "📈"
        
        return f"{emoji} {fvg_type} BLOCK {timeframe} ({strength_label})"

    def get_ohlcv_data(self, symbol, timeframe, limit=500):
        """Fetch OHLCV data for FVG detection"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol} {timeframe}: {e}")
            return None

    def detect_fvgs(self, df):
        """Detect FVGs using Pine Script logic"""
        if df is None or len(df) < 3:
            return []
        
        fvgs = []
        
        for i in range(1, len(df) - 1):
            # Bullish FVG: previous_high < current_low
            if df.iloc[i-1]['high'] < df.iloc[i+1]['low']:
                gap_low = df.iloc[i-1]['high']
                gap_high = df.iloc[i+1]['low']
                gap_size = gap_high - gap_low
                
                if gap_size > 0:  # Valid gap
                    fvg = {
                        'index': i,
                        'fvg_type': 'Bullish',
                        'gap_low': gap_low,
                        'gap_high': gap_high,
                        'gap_size': gap_size,
                        'timestamp': df.iloc[i]['datetime'],
                        'volume_strength': df.iloc[i]['volume']
                    }
                    fvgs.append(fvg)
            
            # Bearish FVG: previous_low > current_high
            elif df.iloc[i-1]['low'] > df.iloc[i+1]['high']:
                gap_low = df.iloc[i+1]['high']
                gap_high = df.iloc[i-1]['low']
                gap_size = gap_high - gap_low
                
                if gap_size > 0:  # Valid gap
                    fvg = {
                        'index': i,
                        'fvg_type': 'Bearish',
                        'gap_low': gap_low,
                        'gap_high': gap_high,
                        'gap_size': gap_size,
                        'timestamp': df.iloc[i]['datetime'],
                        'volume_strength': df.iloc[i]['volume']
                    }
                    fvgs.append(fvg)
        
        return fvgs

    def process_fvg_with_pine_logic(self, symbol, timeframe, fvg, current_price):
        """Process FVG with complete Pine Script logic"""
        # Calculate distance and proximity
        distance = self.calculate_distance_percentage(current_price, fvg['gap_low'], fvg['gap_high'])
        is_within_proximity = distance <= self.pine_settings['proximity_filter']
        
        # Check if touched
        is_touched = self.is_fvg_touched(current_price, fvg['gap_low'], fvg['gap_high'])
        
        # Calculate strength and power score
        strength = self.calculate_fvg_strength(fvg['gap_size'], fvg['volume_strength'], timeframe)
        power_score = min(int(strength), 100)
        
        # Calculate unfilled orders (estimate based on volume and gap size)
        unfilled_orders = int(fvg['volume_strength'] * (fvg['gap_size'] / current_price) * 100000)
        
        # Format data for frontend
        enhanced_fvg = {
            'pair': symbol,
            'tf': timeframe,
            'type': 'fvg_data',  # Frontend will map to fvg_type
            'fvg_type': fvg['fvg_type'],  # Real type for frontend mapping
            'gap_low': fvg['gap_low'],
            'gap_high': fvg['gap_high'],
            'gap_size': fvg['gap_size'],
            'distance_percentage': round(distance, 2),
            'is_within_proximity': is_within_proximity,
            'is_touched': is_touched,
            'volume_strength': int(fvg['volume_strength']),
            'unfilled_orders': unfilled_orders,
            'unfilled_orders_formatted': self.format_orders(unfilled_orders),
            'power_score': power_score,
            'strength': strength,
            'timestamp': fvg['timestamp'].isoformat() if hasattr(fvg['timestamp'], 'isoformat') else str(fvg['timestamp']),
            'is_block_member': False,  # Will be updated by block detection
            'block_badge': '',
            'block_id': None
        }
        
        return enhanced_fvg

    def format_orders(self, orders):
        """Format order numbers like 1.2M, 5.4K, etc."""
        if orders >= 1_000_000:
            return f"{orders/1_000_000:.1f}M"
        elif orders >= 1_000:
            return f"{orders/1_000:.1f}K"
        else:
            return str(int(orders))

    async def scan_symbol_timeframe(self, symbol, timeframe):
        """Scan a specific symbol and timeframe for FVGs"""
        try:
            # Get current price
            ticker = self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            self.current_prices[symbol] = current_price
            
            # Get OHLCV data
            df = self.get_ohlcv_data(symbol, timeframe)
            if df is None:
                return []
            
            # Detect FVGs
            fvgs = self.detect_fvgs(df)
            
            # Process each FVG with Pine Script logic
            processed_fvgs = []
            for fvg in fvgs:
                enhanced_fvg = self.process_fvg_with_pine_logic(symbol, timeframe, fvg, current_price)
                
                # Only include FVGs within proximity filter (like Pine Script)
                if enhanced_fvg['is_within_proximity']:
                    processed_fvgs.append(enhanced_fvg)
            
            # Detect institutional blocks
            blocks = self.detect_institutional_blocks(symbol, timeframe, processed_fvgs)
            
            # Mark FVGs that are part of blocks
            for block in blocks:
                for fvg in block['fvgs']:
                    for processed_fvg in processed_fvgs:
                        if (processed_fvg['gap_low'] == fvg['gap_low'] and 
                            processed_fvg['gap_high'] == fvg['gap_high']):
                            processed_fvg['is_block_member'] = True
                            processed_fvg['block_badge'] = block['badge']
                            processed_fvg['block_id'] = block['block_id']
            
            # Update statistics
            self.update_scan_stats(processed_fvgs, blocks)
            
            return processed_fvgs
            
        except Exception as e:
            logger.error(f"Error scanning {symbol} {timeframe}: {e}")
            return []

    def update_scan_stats(self, fvgs, blocks):
        """Update scanning statistics"""
        self.scan_stats['scanned_pairs'] += 1
        self.scan_stats['total_fvgs'] += len(fvgs)
        
        for fvg in fvgs:
            if fvg['fvg_type'] == 'Bullish':
                self.scan_stats['bullish_fvgs'] += 1
            else:
                self.scan_stats['bearish_fvgs'] += 1
                
            if fvg['is_touched']:
                self.scan_stats['touched_fvgs'] += 1
        
        self.scan_stats['institutional_blocks'] += len(blocks)

    async def send_fvg_data(self, fvg_data):
        """Send FVG data to all connected clients"""
        if not self.clients:
            return
        
        message = {
            'type': 'fvg_data',
            'data': fvg_data,
            'stats': self.scan_stats.copy(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to all clients
        disconnected_clients = set()
        for client in self.clients.copy():
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending data to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected_clients

    async def scan_markets(self):
        """Main scanning loop with Pine Script logic"""
        try:
            # Get trading pairs
            markets = self.exchange.load_markets()
            usdt_pairs = [symbol for symbol in markets.keys() if symbol.endswith('/USDT')]
            
            # Filter for active pairs with good volume
            active_pairs = []
            for symbol in usdt_pairs[:50]:  # Limit for performance
                try:
                    ticker = self.exchange.fetch_ticker(symbol)
                    if ticker['quoteVolume'] and ticker['quoteVolume'] > 1000000:  # Min $1M volume
                        active_pairs.append(symbol)
                except:
                    continue
            
            self.scan_stats['total_pairs'] = len(active_pairs)
            logger.info(f"🚀 PINE SCRIPT SCANNER: Starting scan of {len(active_pairs)} pairs")
            
            # Scan each pair across all timeframes
            for symbol in active_pairs:
                if not self.is_scanning:
                    break
                
                for timeframe in self.pine_settings['timeframes']:
                    try:
                        fvgs = await self.scan_symbol_timeframe(symbol, timeframe)
                        
                        # Send each FVG individually for real-time updates
                        for fvg in fvgs:
                            await self.send_fvg_data(fvg)
                            await asyncio.sleep(0.1)  # Small delay for real-time effect
                        
                        # Small delay between timeframes
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        logger.error(f"Error scanning {symbol} {timeframe}: {e}")
                        continue
                
                # Send stats update
                await self.send_stats_update()
                await asyncio.sleep(0.5)  # Delay between symbols
            
            logger.info("🎯 PINE SCRIPT SCANNER: Scan cycle completed")
            
        except Exception as e:
            logger.error(f"Error in scan_markets: {e}")
            traceback.print_exc()

    async def send_stats_update(self):
        """Send statistics update to clients"""
        if not self.clients:
            return
        
        message = {
            'type': 'stats_update',
            'stats': self.scan_stats.copy(),
            'timestamp': datetime.now().isoformat()
        }
        
        for client in self.clients.copy():
            try:
                await client.send(json.dumps(message))
            except:
                self.clients.discard(client)

    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections"""
        self.clients.add(websocket)
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"🔗 PRODUCTION: Client connected from {client_info}")
        
        try:
            # Send welcome message with current stats
            welcome_message = {
                'type': 'connection_established',
                'message': '🚀 PINE SCRIPT FVG SCANNER - Connected successfully',
                'stats': self.scan_stats.copy(),
                'settings': self.pine_settings.copy()
            }
            await websocket.send(json.dumps(welcome_message))
            
            # Handle client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_client_message(data, websocket)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client: {message}")
                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error handling client {client_info}: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"🔌 PRODUCTION: Client {client_info} disconnected")

    async def handle_client_message(self, data, websocket):
        """Handle messages from clients"""
        message_type = data.get('type')
        
        if message_type == 'start_scan':
            if not self.is_scanning:
                self.is_scanning = True
                logger.info("🚀 PINE SCRIPT SCANNER: Starting scan requested by client")
                asyncio.create_task(self.scan_markets())
                await websocket.send(json.dumps({
                    'type': 'scan_status',
                    'status': 'started',
                    'message': '🚀 Pine Script FVG Scanner started'
                }))
        
        elif message_type == 'stop_scan':
            self.is_scanning = False
            logger.info("⏹️ PINE SCRIPT SCANNER: Stop scan requested by client")
            await websocket.send(json.dumps({
                'type': 'scan_status',
                'status': 'stopped',
                'message': '⏹️ Pine Script FVG Scanner stopped'
            }))
        
        elif message_type == 'update_settings':
            settings = data.get('settings', {})
            self.pine_settings.update(settings)
            logger.info(f"⚙️ Settings updated: {settings}")
            await websocket.send(json.dumps({
                'type': 'settings_updated',
                'settings': self.pine_settings.copy()
            }))
        
        elif message_type == 'ping':
            await websocket.send(json.dumps({'type': 'pong'}))

def main():
    scanner = FVGScanner()
    
    # Start WebSocket server
    start_server = websockets.serve(
        scanner.handle_client,
        "0.0.0.0",
        8765,
        ping_interval=30,
        ping_timeout=10
    )
    
    logger.info("🚀 PINE SCRIPT FVG SCANNER: WebSocket server starting on port 8765")
    
    # Run the server
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    main()
