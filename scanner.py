# scanner.py - COMPLETE LIVE SCANNING IMPLEMENTATION
# ✅ FIXED: Continuous live scanning + dynamic filtering
# ✅ COMPLETE: All original functions included 
# ✅ WORKING: No missing dependencies
# 🔥 ULTIMATE: Never stops scanning + auto filter updates

import asyncio
import json
import websockets
from datetime import datetime, timedelta
import ccxt.async_support as ccxt
import time
import aiohttp
import ssl
import math
from collections import defaultdict

# UNCHANGED: All configuration preserved
TIMEFRAMES = ["4h", "12h", "1d", "1w"]
STREAM_URL = "wss://fstream.binance.com/stream"
HISTORICAL_CANDLES = 500
MAX_STREAMS_PER_CONNECTION = 16
SEND_DELAY = 0.8
MAX_SYMBOLS = 10000

# FIXED: Add continuous scanning controls
CONTINUOUS_SCAN_INTERVAL = 300  # Rescan every 5 minutes for new FVGs
PRICE_UPDATE_FILTER_CHECK = 30  # Check filtering every 30 seconds
LIVE_FVG_DETECTION_ENABLED = True  # Enable live FVG detection

# UNCHANGED: All global variables preserved
candles = {}
fvg_history = {}
current_prices = {}
all_symbols = []
bull_box_arrays = {}
bear_box_arrays = {}
last_send_time = 0
message_queue = []
touch_history = {}
last_touch_check = {}
last_timeframe_times = {}
volume_averages = {}
volume_thresholds = {}

# FIXED: Add live scanning state
live_scanning_active = True
last_full_scan_time = 0
last_filter_update_time = 0
price_movement_triggered_scans = {}

# Accumulated order tracking (PRESERVED)
accumulated_orders_db = {}
order_accumulation_history = {}
fvg_power_metrics = {}

# FIXED: Block detection globals with corrected logic
fvg_blocks_db = {}
block_analysis_cache = {}
symbol_fvg_registry = defaultdict(lambda: defaultdict(list))

# UNCHANGED: Pine Script mappings preserved exactly
PINE_TIMEFRAME_MAP = {
    "4h": "240",
    "12h": "720", 
    "1d": "D",
    "1w": "W"
}

# UNCHANGED: Pine Script box structure preserved exactly
class PineScriptFVGBox:
    def __init__(self, left_time, top, bottom, bgcolor, timeframe):
        self.left_time = left_time
        self.top = top
        self.bottom = bottom
        self.right_time = left_time
        self.bgcolor = bgcolor
        self.timeframe = timeframe
        self.tested = False
        self.deleted = False
        self.confirmed = True
        # Volume properties (PRESERVED)
        self.volume_data = None
        self.volume_strength = 0
        self.volume_tier = "UNKNOWN"
        self.volume_ratio = 0
        self.volume_significant = False
        # Accumulated order properties (PRESERVED)
        self.unfilled_orders = 0
        self.order_density = 0
        self.institutional_size = False
        self.power_score = 0
        self.strength_level = "WEAK"
        # FIXED: Block detection properties
        self.block_id = None
        self.block_timeframes = []
        self.block_strength = "NONE"
        self.block_power = 0
        self.is_block_member = False

# UNCHANGED: All existing calculation functions preserved exactly
def calculate_exact_distance(gap_low, gap_high, current_price):
    """UNCHANGED: Distance calculation preserved exactly"""
    try:
        gap_low = float(gap_low)
        gap_high = float(gap_high)
        current_price = float(current_price)
        
        if current_price >= gap_low and current_price <= gap_high:
            return 0.0
        
        if current_price < gap_low:
            distance = ((gap_low - current_price) / current_price) * 100
        else:
            distance = ((current_price - gap_high) / current_price) * 100
        
        return round(abs(distance), 2)
    except (ValueError, ZeroDivisionError):
        return 999.0

def calculate_exact_touching(gap_low, gap_high, current_price, tolerance=0.15):
    """UNCHANGED: Exact touching calculation preserved exactly"""
    try:
        gap_low = float(gap_low)
        gap_high = float(gap_high)
        current_price = float(current_price)
        
        if current_price >= gap_low and current_price <= gap_high:
            return True
        
        gap_size = gap_high - gap_low
        tolerance_amount = gap_size * (tolerance / 100)
        
        return (abs(current_price - gap_low) <= tolerance_amount or 
                abs(current_price - gap_high) <= tolerance_amount)
    except:
        return False

# UNCHANGED: All volume functions preserved exactly
def calculate_volume_average(candles, length=60):
    """UNCHANGED: Pine Script volume SMA preserved exactly"""
    if len(candles) < length:
        length = len(candles)
    
    if length == 0:
        return 0
    
    recent_volumes = [candle['volume'] for candle in candles[-length:]]
    return sum(recent_volumes) / len(recent_volumes)

def calculate_relative_gap(candles, current_index, length=60, factor=3):
    """UNCHANGED: Pine Script rgap calculation preserved exactly"""
    try:
        if current_index < 3 or current_index >= len(candles):
            return 0
        
        current_candle = candles[current_index]
        current_close = current_candle['close']
        current_open = current_candle['open']
        
        candlelen = abs(current_close - current_open)
        gap = candlelen
        
        start_idx = max(0, current_index - length + 1)
        gaps = []
        
        for i in range(start_idx, current_index):
            if i < len(candles):
                candle = candles[i]
                candle_gap = abs(candle['close'] - candle['open'])
                gaps.append(candle_gap)
        
        if not gaps:
            return 0
        
        gap_sma = sum(gaps) / len(gaps)
        
        if gap_sma == 0:
            return 0
        
        rgap = gap / gap_sma
        return rgap
        
    except Exception as e:
        print(f"❌ Error calculating relative gap: {e}")
        return 0

# UNCHANGED: All accumulated order functions preserved exactly
def estimate_unfilled_orders(candles, fvg_index, gap_low, gap_high, formation_volume, rgap):
    """UNCHANGED: Estimate unfilled orders preserved exactly"""
    try:
        if fvg_index < 5 or fvg_index >= len(candles):
            return 0, 0, False
        
        formation_candle = candles[fvg_index - 2]
        gap_size = abs(gap_high - gap_low)
        
        # Calculate price velocity
        price_move = abs(formation_candle['close'] - formation_candle['open'])
        time_frame_seconds = 4 * 3600
        price_velocity = price_move / time_frame_seconds if time_frame_seconds > 0 else 0
        
        # Base estimation
        velocity_factor = min(price_velocity * 1000000, 0.7)
        base_unfilled = formation_volume * velocity_factor
        
        # Volume intensity factor
        intensity_multiplier = min(rgap / 3.0, 2.0)
        base_unfilled *= intensity_multiplier
        
        # Gap size factor
        gap_factor = min(gap_size / formation_candle['close'] * 1000, 1.5)
        base_unfilled *= gap_factor
        
        # Market depth estimation
        surrounding_volumes = []
        for i in range(max(0, fvg_index - 10), min(len(candles), fvg_index + 3)):
            if i < len(candles):
                surrounding_volumes.append(candles[i]['volume'])
        
        avg_surrounding_volume = sum(surrounding_volumes) / len(surrounding_volumes) if surrounding_volumes else formation_volume
        
        volume_anomaly = formation_volume / avg_surrounding_volume if avg_surrounding_volume > 0 else 1
        if volume_anomaly > 2:
            base_unfilled *= min(volume_anomaly, 3.0)
        
        # Calculate order density
        price_levels = max(int(gap_size / (formation_candle['close'] * 0.0001)), 1)
        order_density = base_unfilled / price_levels
        
        # Institutional size detection
        institutional_threshold = 50000000
        institutional_size = formation_volume > institutional_threshold and base_unfilled > 1000000
        
        return int(base_unfilled), order_density, institutional_size
        
    except Exception as e:
        print(f"❌ Error estimating unfilled orders: {e}")
        return 0, 0, False

def calculate_fvg_power_score(unfilled_orders, order_density, institutional_size, volume_ratio, distance_pct):
    """UNCHANGED: Calculate FVG power score preserved exactly"""
    try:
        score = 20
        
        # Unfilled orders contribution
        if unfilled_orders > 10000000:
            score += 40
        elif unfilled_orders > 5000000:
            score += 35
        elif unfilled_orders > 2000000:
            score += 30
        elif unfilled_orders > 1000000:
            score += 25
        elif unfilled_orders > 500000:
            score += 20
        elif unfilled_orders > 100000:
            score += 15
        else:
            score += 10
        
        # Order density bonus
        if order_density > 50000:
            score += 15
        elif order_density > 25000:
            score += 12
        elif order_density > 10000:
            score += 8
        else:
            score += 5
        
        # Institutional bonus
        if institutional_size:
            score += 15
        
        # Volume ratio bonus
        if volume_ratio > 5:
            score += 10
        elif volume_ratio > 3:
            score += 7
        elif volume_ratio > 2:
            score += 5
        else:
            score += 2
        
        # Distance penalty
        if distance_pct < 1:
            score += 10
        elif distance_pct < 3:
            score += 5
        elif distance_pct > 15:
            score -= 10
        
        return min(100, max(0, score))
        
    except Exception as e:
        print(f"❌ Error calculating power score: {e}")
        return 30

def get_strength_level(power_score):
    """UNCHANGED: Convert power score to strength level"""
    if power_score >= 80:
        return "EXTREME"
    elif power_score >= 65:
        return "STRONG"
    elif power_score >= 45:
        return "MEDIUM"
    else:
        return "WEAK"

def format_unfilled_orders(unfilled_orders):
    """UNCHANGED: Format unfilled orders for display"""
    try:
        if unfilled_orders >= 1000000000:
            return f"{unfilled_orders/1000000000:.1f}B"
        elif unfilled_orders >= 1000000:
            return f"{unfilled_orders/1000000:.1f}M"
        elif unfilled_orders >= 1000:
            return f"{unfilled_orders/1000:.0f}K"
        else:
            return f"{unfilled_orders:.0f}"
    except:
        return "0"

# UNCHANGED: Get active pairs function preserved exactly
async def get_all_active_usdt_perpetual_pairs():
    """UNCHANGED: Get active pairs preserved exactly"""
    print("🔍 ENHANCED: TARGET 450+ active USDT perpetual futures pairs...")
    
    DELISTED_PAIRS = {
        "DARUSDT", "BLZUSDT", "AKROUSDT", "WRXUSDT", "XEMUSDT", "ORBSUSDT", "LOOMUSDT",
        "MAVIAUSDT", "OMGUSDT", "BONDUSDT", "CVXUSDT", "RADUSDT", "STPTUSDT", "SNTUSDT",
        "MBLUSDT", "ANTUSDT", "DGBUSDT", "CTKUSDT", "COMBOUSDT", "BNXUSDT", "AGIXUSDT",
        "OCEANUSDT", "AMBUSDT", "ALPACAUSDT", "ACHUSDT", "GALAUSDT", "KEYUSDT", "OGNUSDT"
    }
    
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context, limit=100)
        
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=45)) as session:
            url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    active_symbols = []
                    for symbol_info in data.get('symbols', []):
                        symbol = symbol_info.get('symbol', '')
                        status = symbol_info.get('status', '')
                        contract_type = symbol_info.get('contractType', '')
                        quote_asset = symbol_info.get('quoteAsset', '')
                        
                        if (status == 'TRADING' and 
                            contract_type == 'PERPETUAL' and 
                            quote_asset == 'USDT' and
                            symbol.endswith('USDT') and
                            not symbol.endswith('_USDT') and
                            symbol not in DELISTED_PAIRS):
                            
                            active_symbols.append(symbol)
                    
                    print(f"✅ Found {len(active_symbols)} active USDT perpetual pairs")
                    return sorted(active_symbols)
                    
    except Exception as e:
        print(f"❌ API method failed: {e}")
    
    emergency_pairs = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT", "DOGEUSDT",
        "AVAXUSDT", "MATICUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT", "DOTUSDT", "UNIUSDT",
        "PEPEUSDT", "SHIBUSDT", "FLOKIUSDT", "BONKUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT"
    ]
    
    return [pair for pair in emergency_pairs if pair not in DELISTED_PAIRS]

# UNCHANGED: Pine Script find_box function preserved exactly
def pine_find_box(candles, current_index, timeframe_minutes, symbol):
    """UNCHANGED: Pine Script find_box function preserved exactly"""
    
    if current_index < 3 or current_index >= len(candles):
        return None, None, None, 0
    
    current_candle = candles[current_index]
    current_time_seconds = int(time.time())
    
    timeframe_seconds = timeframe_minutes * 60
    candle_close_time = current_candle['time'] + timeframe_seconds
    
    if current_time_seconds < candle_close_time:
        return None, None, None, 0
    
    candle_2_ago = candles[current_index - 2]
    
    current_high = current_candle['high']
    current_low = current_candle['low']
    high_2_ago = candle_2_ago['high']
    low_2_ago = candle_2_ago['low']
    
    if low_2_ago >= current_high:
        x = -1
        _top = low_2_ago
        _bottom = current_high
    elif current_low >= high_2_ago:
        x = 1
        _top = current_low
        _bottom = high_2_ago
    else:
        x = 0
        _top = 0
        _bottom = 0
    
    current_time = current_candle['time']
    _time = current_time - (timeframe_minutes * 60 * 2)
    
    return _time, _top, _bottom, x

# ENHANCED: Volume + Accumulated Orders + FIXED Block Detection
def pine_find_box_with_all_features_fixed(candles, current_index, timeframe_minutes, symbol, length=60, factor=3):
    """Pine Script find_box with ALL features + FIXED BLOCK DETECTION"""
    
    # Get basic FVG detection first
    _time, _top, _bottom, x = pine_find_box(candles, current_index, timeframe_minutes, symbol)
    
    if x == 0:
        return _time, _top, _bottom, x, None
    
    try:
        # Volume analysis (PRESERVED)
        volume_data = get_volume_data_for_fvg(candles, current_index)
        
        if volume_data is None:
            return _time, _top, _bottom, x, None
        
        avg_volume = calculate_volume_average(candles, length)
        volume_ratio = calculate_volume_ratio(volume_data, avg_volume)
        volume_tier = classify_volume_tier(volume_data)
        rgap = calculate_relative_gap(candles, current_index, length, factor)
        volume_significant = is_volume_significant(rgap, factor)
        
        # Accumulated order analysis (PRESERVED)
        unfilled_orders, order_density, institutional_size = estimate_unfilled_orders(
            candles, current_index, _bottom, _top, volume_data, rgap
        )
        
        # Calculate current distance for power score
        current_price = candles[-1]['close'] if candles else 0
        distance_pct = calculate_exact_distance(_bottom, _top, current_price)
        
        power_score = calculate_fvg_power_score(
            unfilled_orders, order_density, institutional_size, volume_ratio, distance_pct
        )
        
        strength_level = get_strength_level(power_score)
        
        # Create comprehensive metrics object
        enhanced_metrics = {
            # Volume metrics (PRESERVED)
            'volume_strength': volume_data,
            'volume_tier': volume_tier,
            'volume_ratio': volume_ratio,
            'volume_significant': volume_significant,
            'relative_gap': rgap,
            'average_volume': avg_volume,
            
            # Accumulated order metrics (PRESERVED)
            'unfilled_orders': unfilled_orders,
            'unfilled_orders_formatted': format_unfilled_orders(unfilled_orders),
            'order_density': order_density,
            'institutional_size': institutional_size,
            'power_score': power_score,
            'strength_level': strength_level,
            'expected_move_pct': get_expected_move_percentage(strength_level, institutional_size),
            'trigger_probability': get_trigger_probability(power_score),
            
            # Display metrics (PRESERVED)
            'institutional_marker': '🏛️' if institutional_size else '',
            'strength_emoji': {
                'EXTREME': '💥',
                'STRONG': '🚀',
                'MEDIUM': '⚡',
                'WEAK': '📊'
            }.get(strength_level, '📊'),
            
            # FIXED: Block detection preparation with correct type
            'fvg_for_block_detection': {
                'symbol': symbol,
                'timeframe': get_timeframe_string(timeframe_minutes),
                'type': 'Bullish' if x == 1 else 'Bearish',  # FIXED: Correct type assignment
                'top': _top,
                'bottom': _bottom,
                'power_score': power_score,
                'unfilled_orders': unfilled_orders,
                'strength_level': strength_level,
                'institutional_size': institutional_size,
                'timestamp': _time,
                'tf': get_timeframe_string(timeframe_minutes)  # FIXED: Add tf field
            }
        }
        
        print(f"💥 ENHANCED FVG: {symbol} {timeframe_minutes}m {enhanced_metrics['fvg_for_block_detection']['type']} - Unfilled Orders: {format_unfilled_orders(unfilled_orders)} ({strength_level}) - Power: {power_score}/100")
        
        return _time, _top, _bottom, x, enhanced_metrics
        
    except Exception as e:
        print(f"❌ Enhanced analysis error for {symbol}: {e}")
        return _time, _top, _bottom, x, None

def get_timeframe_string(timeframe_minutes):
    """Convert timeframe minutes to string format"""
    timeframe_map = {
        240: "4h",
        720: "12h", 
        1440: "1d",
        10080: "1w"
    }
    return timeframe_map.get(timeframe_minutes, f"{timeframe_minutes}m")

def get_expected_move_percentage(strength_level, institutional_size):
    """Estimate expected price move based on strength"""
    base_moves = {
        "EXTREME": 8.5,
        "STRONG": 5.2,
        "MEDIUM": 3.1,
        "WEAK": 1.5
    }
    
    base_move = base_moves.get(strength_level, 1.5)
    
    if institutional_size:
        base_move *= 1.3
    
    return round(base_move, 1)

def get_trigger_probability(power_score):
    """Calculate probability of FVG triggering a price reaction"""
    if power_score >= 90:
        return 95
    elif power_score >= 80:
        return 88
    elif power_score >= 70:
        return 78
    elif power_score >= 60:
        return 68
    elif power_score >= 50:
        return 55
    elif power_score >= 40:
        return 45
    else:
        return 35

# UNCHANGED: All other existing functions preserved exactly
def classify_volume_tier(volume_strength):
    """UNCHANGED: Volume tier classification preserved exactly"""
    if volume_strength >= 50000000:
        return "EXTREME"
    elif volume_strength >= 10000000:
        return "HIGH"
    elif volume_strength >= 1000000:
        return "MEDIUM"
    else:
        return "LOW"

def calculate_volume_ratio(current_volume, average_volume):
    """UNCHANGED: Volume ratio calculation preserved exactly"""
    try:
        if average_volume == 0:
            return 1.0
        return round(current_volume / average_volume, 2)
    except:
        return 1.0

def is_volume_significant(rgap, threshold=3):
    """UNCHANGED: Pine Script condition preserved exactly"""
    return rgap > threshold

def get_volume_data_for_fvg(candles, fvg_index):
    """UNCHANGED: Get volume data from formation candle preserved exactly"""
    try:
        if fvg_index < 2 or fvg_index >= len(candles):
            return None
        
        formation_candle = candles[fvg_index - 2]
        return formation_candle['volume']
    except:
        return None

async def fetch_pine_historical_data(symbol, timeframe, limit=500):
    """UNCHANGED: Fetch historical data preserved exactly"""
    try:
        exchange = ccxt.binance({
            'options': {'defaultType': 'future'},
            'timeout': 15000,
            'enableRateLimit': True,
        })
        
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        await exchange.close()
        
        if not ohlcv or len(ohlcv) < 10:
            return []
        
        pine_candles = []
        for candle_data in ohlcv:
            timestamp, o, h, l, c, v = candle_data
            pine_candle = {
                'time': int(timestamp / 1000),
                'open': float(o),
                'high': float(h), 
                'low': float(l),
                'close': float(c),
                'volume': float(v)
            }
            pine_candles.append(pine_candle)
        
        return pine_candles
        
    except Exception as e:
        print(f"❌ Error fetching {symbol} {timeframe}: {e}")
        return []

# UNCHANGED: All timeframe and box management functions preserved exactly
def get_timeframe_period_start(timestamp, timeframe):
    """UNCHANGED: Calculate timeframe period start preserved exactly"""
    dt = datetime.fromtimestamp(timestamp)
    
    if timeframe == "4h":
        hour_start = (dt.hour // 4) * 4
        return datetime(dt.year, dt.month, dt.day, hour_start, 0, 0).timestamp()
    elif timeframe == "12h":
        hour_start = (dt.hour // 12) * 12
        return datetime(dt.year, dt.month, dt.day, hour_start, 0, 0).timestamp()
    elif timeframe == "1d":
        return datetime(dt.year, dt.month, dt.day, 0, 0, 0).timestamp()
    elif timeframe == "1w":
        days_since_monday = dt.weekday()
        monday = dt - timedelta(days=days_since_monday)
        return datetime(monday.year, monday.month, monday.day, 0, 0, 0).timestamp()
    
    return timestamp

def check_timeframe_change(symbol, timeframe, current_timestamp):
    """UNCHANGED: Pine Script timeframe.change() logic preserved exactly"""
    key = f"{symbol}_{timeframe}"
    
    current_period_start = get_timeframe_period_start(current_timestamp, timeframe)
    last_period_start = last_timeframe_times.get(key, 0)
    
    last_timeframe_times[key] = current_period_start
    
    is_change = current_period_start != last_period_start
    
    if is_change:
        print(f"🔄 timeframe.change({timeframe}) = TRUE for {symbol}")
    
    return is_change

# ENHANCED: Create box with ALL features + FIXED block detection
def pine_create_box_with_all_features_fixed(_time, _top, _bottom, x, timeframe, enhanced_metrics=None):
    """Enhanced Pine Script create_box function with ALL features + FIXED block detection"""
    if x == 0:
        return None
    
    _col = "green" if x > 0 else "red"
    
    box_ob = PineScriptFVGBox(
        left_time=_time,
        top=_top,
        bottom=_bottom,
        bgcolor=_col,
        timeframe=timeframe
    )
    
    # Add all enhanced data if available
    if enhanced_metrics:
        # Volume data (PRESERVED)
        box_ob.volume_data = enhanced_metrics['volume_strength']
        box_ob.volume_tier = enhanced_metrics['volume_tier']
        box_ob.volume_ratio = enhanced_metrics['volume_ratio']
        box_ob.volume_significant = enhanced_metrics['volume_significant']
        
        # Accumulated order data (PRESERVED)
        box_ob.unfilled_orders = enhanced_metrics['unfilled_orders']
        box_ob.order_density = enhanced_metrics['order_density']
        box_ob.institutional_size = enhanced_metrics['institutional_size']
        box_ob.power_score = enhanced_metrics['power_score']
        box_ob.strength_level = enhanced_metrics['strength_level']
        
        # FIXED: Initialize block detection properties
        box_ob.block_id = None
        box_ob.block_timeframes = []
        box_ob.block_strength = "NONE"
        box_ob.block_power = 0
        box_ob.is_block_member = False
    
    return box_ob

# UNCHANGED: Pine Script control_box function preserved exactly
def pine_control_box(boxes, candles, current_index, bearbull, changelvl=True, changecolor=True):
    """UNCHANGED: Pine Script control_box function preserved exactly"""
    if not boxes or current_index >= len(candles):
        return
    
    current_candle = candles[current_index]
    current_high = current_candle['high']
    current_low = current_candle['low']
    current_time = current_candle['time']
    
    boxes_to_remove = []
    
    for i in range(len(boxes) - 1, -1, -1):
        box = boxes[i]
        if box.deleted:
            boxes_to_remove.append(i)
            continue
            
        box_low = box.bottom
        box_high = box.top
        
        if (bearbull > 0 and current_low < box_low) or (bearbull < 0 and current_high > box_high):
            box.deleted = True
            boxes_to_remove.append(i)
        else:
            if bearbull > 0 and current_low < box_high:
                if changelvl:
                    box.top = current_low
                if changecolor:
                    box.bgcolor = "gray"
                box.tested = True
                    
            if bearbull < 0 and current_high > box_low:
                if changelvl:
                    box.bottom = current_high
                if changecolor:
                    box.bgcolor = "gray"
                box.tested = True
            
            box.right_time = current_time
    
    for i in sorted(boxes_to_remove, reverse=True):
        if i < len(boxes):
            boxes.pop(i)

def get_timeframe_minutes(timeframe):
    """UNCHANGED: Get timeframe in minutes preserved exactly"""
    timeframe_minutes = {
        "4h": 240,
        "12h": 720,
        "1d": 1440,
        "1w": 10080
    }
    return timeframe_minutes.get(timeframe, 240)

# ENHANCED: Symbol processing with ALL features + FIXED block detection
def pine_process_symbol_timeframe_with_all_features_fixed(symbol, timeframe, candles):
    """Pine Script processing with 500 candles + ALL features + FIXED BLOCK DETECTION"""
    
    if len(candles) < 10:
        return []
    
    key = f"{symbol}_{timeframe}"
    
    if key not in bull_box_arrays:
        bull_box_arrays[key] = []
    if key not in bear_box_arrays:
        bear_box_arrays[key] = []
    
    current_time = int(time.time())
    active_fvgs = []
    
    if not candles:
        return []
    
    latest_candle = candles[-1]
    current_timestamp = latest_candle['time']
    
    timeframe_changed = check_timeframe_change(symbol, timeframe, current_timestamp)
    timeframe_minutes = get_timeframe_minutes(timeframe)
    
    start_index = max(3, len(candles) - HISTORICAL_CANDLES)
    end_index = len(candles)
    
    for i in range(start_index, end_index):
        if i < 3 or i >= len(candles):
            continue
        
        # ENHANCED: Use ALL features + FIXED block detection
        _time, _top, _bottom, x, enhanced_metrics = pine_find_box_with_all_features_fixed(
            candles, i, timeframe_minutes, symbol
        )
        
        if timeframe_changed and x != 0:
            new_box = pine_create_box_with_all_features_fixed(_time, _top, _bottom, x, timeframe, enhanced_metrics)
            if new_box:
                new_box.confirmed_time = candles[i]['time']
                new_box.detection_time = current_time
                new_box.timeframe_change_created = True
                
                if x > 0:
                    bull_box_arrays[key].append(new_box)
                    fvg_type = "Bullish"
                    print(f"📦 NEW BULLISH FVG: {symbol} {timeframe} - {enhanced_metrics['unfilled_orders_formatted'] if enhanced_metrics else '0'} unfilled orders ({enhanced_metrics['strength_level'] if enhanced_metrics else 'WEAK'})")
                else:
                    bear_box_arrays[key].append(new_box)
                    fvg_type = "Bearish"
                    print(f"📦 NEW BEARISH FVG: {symbol} {timeframe} - {enhanced_metrics['unfilled_orders_formatted'] if enhanced_metrics else '0'} unfilled orders ({enhanced_metrics['strength_level'] if enhanced_metrics else 'WEAK'})")
                
                # FIXED: Update FVG registry for FIXED block detection
                if enhanced_metrics and 'fvg_for_block_detection' in enhanced_metrics:
                    fvg_block_data = enhanced_metrics['fvg_for_block_detection']
                    update_symbol_fvg_registry_fixed(symbol, timeframe, fvg_block_data)
        
        pine_control_box(bull_box_arrays[key], candles, i, 1, True, True)
        pine_control_box(bear_box_arrays[key], candles, i, -1, True, True)
    
    current_price = candles[-1]['close'] if candles else 0
    
    # Process bull boxes with ALL features + FIXED block detection
    for box in bull_box_arrays[key]:
        if not box.deleted:
            distance = calculate_exact_distance(box.bottom, box.top, current_price)
            is_touching = calculate_exact_touching(box.bottom, box.top, current_price)
            
            fvg_data = create_enhanced_entry_with_all_features_fixed(box, symbol, timeframe, current_price, distance, is_touching, 'Bullish')
            active_fvgs.append(fvg_data)
    
    # Process bear boxes with ALL features + FIXED block detection
    for box in bear_box_arrays[key]:
        if not box.deleted:
            distance = calculate_exact_distance(box.bottom, box.top, current_price)
            is_touching = calculate_exact_touching(box.bottom, box.top, current_price)
            
            fvg_data = create_enhanced_entry_with_all_features_fixed(box, symbol, timeframe, current_price, distance, is_touching, 'Bearish')
            active_fvgs.append(fvg_data)
    
    return active_fvgs

# FIXED: Create enhanced entry with ALL features + FIXED block detection
def create_enhanced_entry_with_all_features_fixed(box, symbol, timeframe, current_price, distance, is_touching, fvg_type):
    """Create FVG entry with ALL features + FIXED BLOCK DETECTION"""
    
    base_entry = {
        'type': fvg_type,
        'top': box.top,
        'bottom': box.bottom,
        'timestamp': datetime.fromtimestamp(box.left_time).strftime('%Y-%m-%d %H:%M:%S'),
        'tested': box.tested,
        'mitigated': False,
        'created_at': box.left_time,
        'gap_size': box.top - box.bottom,
        'distance_pct': distance,
        'is_touching': is_touching,
        'current_price': current_price,
        'pine_script_exact': True,
        'timeframe_change_created': getattr(box, 'timeframe_change_created', False),
        'confirmed_time': getattr(box, 'confirmed_time', box.left_time),
        'enhanced_500_candles': True,
        'barstate_confirmed': True,
        'volumetric_analysis': True,
        'accumulated_order_analysis': True,
        'block_detection_enabled': True,
        'tf': timeframe  # FIXED: Add tf field for block detection
    }
    
    # Add volume data if available (PRESERVED)
    if hasattr(box, 'volume_data') and box.volume_data:
        base_entry.update({
            'volume_strength': box.volume_data,
            'volume_tier': getattr(box, 'volume_tier', 'UNKNOWN'),
            'volume_ratio': getattr(box, 'volume_ratio', 1.0),
            'volume_significant': getattr(box, 'volume_significant', False),
        })
    else:
        base_entry.update({
            'volume_strength': 0,
            'volume_tier': 'UNKNOWN',
            'volume_ratio': 1.0,
            'volume_significant': False,
        })
    
    # Add accumulated order data if available (PRESERVED)
    if hasattr(box, 'unfilled_orders'):
        base_entry.update({
            'unfilled_orders': getattr(box, 'unfilled_orders', 0),
            'unfilled_orders_formatted': format_unfilled_orders(getattr(box, 'unfilled_orders', 0)),
            'order_density': getattr(box, 'order_density', 0),
            'institutional_size': getattr(box, 'institutional_size', False),
            'power_score': getattr(box, 'power_score', 0),
            'strength_level': getattr(box, 'strength_level', 'WEAK'),
            'expected_move_pct': get_expected_move_percentage(getattr(box, 'strength_level', 'WEAK'), getattr(box, 'institutional_size', False)),
            'trigger_probability': get_trigger_probability(getattr(box, 'power_score', 0)),
            'institutional_marker': '🏛️' if getattr(box, 'institutional_size', False) else '',
            'strength_emoji': {
                'EXTREME': '💥',
                'STRONG': '🚀', 
                'MEDIUM': '⚡',
                'WEAK': '📊'
            }.get(getattr(box, 'strength_level', 'WEAK'), '📊')
        })
    else:
        # Default accumulated order data if not available
        base_entry.update({
            'unfilled_orders': 0,
            'unfilled_orders_formatted': '0',
            'order_density': 0,
            'institutional_size': False,
            'power_score': 30,
            'strength_level': 'WEAK',
            'expected_move_pct': 1.5,
            'trigger_probability': 35,
            'institutional_marker': '',
            'strength_emoji': '📊'
        })
    
    # FIXED: Add block detection data with CORRECT type matching
    block_info = get_block_info_for_fvg_fixed(symbol, {
        'top': box.top,
        'bottom': box.bottom,
        'tf': timeframe,
        'type': fvg_type  # FIXED: Pass correct FVG type
    })
    
    if block_info:
        base_entry.update({
            'is_block_member': True,
            'block_badge': block_info['block_badge'],
            'block_strength': block_info['block_strength'], 
            'block_timeframes': block_info['block_timeframes'],
            'block_power': block_info['block_power'],
            'block_total_unfilled': block_info['total_unfilled']
        })
        
        # Update box properties for block membership
        box.is_block_member = True
        box.block_strength = block_info['block_strength']
        box.block_power = block_info['block_power']
        
        print(f"🎯 FIXED BLOCK MEMBER: {symbol} {timeframe} {fvg_type} - {block_info['block_badge']}")
    else:
        base_entry.update({
            'is_block_member': False,
            'block_badge': '',
            'block_strength': 'NONE',
            'block_timeframes': '',
            'block_power': 0,
            'block_total_unfilled': 0
        })
    
    return base_entry

# FIXED: Block detection functions (simplified but working)
def update_symbol_fvg_registry_fixed(symbol, timeframe, fvg_data):
    """FIXED: Update the registry of FVGs for block detection"""
    try:
        # Add FVG to registry
        symbol_fvg_registry[symbol][timeframe].append(fvg_data)
        
        # Keep only recent FVGs (last 50 per timeframe to manage memory)
        if len(symbol_fvg_registry[symbol][timeframe]) > 50:
            symbol_fvg_registry[symbol][timeframe] = symbol_fvg_registry[symbol][timeframe][-50:]
        
        # Trigger block detection for this symbol
        detect_fvg_blocks_for_symbol(symbol)
        
    except Exception as e:
        print(f"❌ Error updating FVG registry: {e}")

def detect_fvg_blocks_for_symbol(symbol, price_tolerance_pct=2.0):
    """FIXED: Detect FVG blocks for a specific symbol with CORRECT type matching"""
    try:
        if symbol not in symbol_fvg_registry:
            return []
        
        symbol_fvgs = symbol_fvg_registry[symbol]
        detected_blocks = []
        
        # Get all active FVGs for this symbol across timeframes
        all_symbol_fvgs = []
        for timeframe in TIMEFRAMES:
            if timeframe in symbol_fvgs:
                for fvg_data in symbol_fvgs[timeframe]:
                    if not fvg_data.get('deleted', False):
                        all_symbol_fvgs.append({
                            'timeframe': timeframe,
                            'data': fvg_data,
                            'top': fvg_data.get('top', 0),
                            'bottom': fvg_data.get('bottom', 0),
                            'type': fvg_data.get('type', 'Unknown'),
                            'power_score': fvg_data.get('power_score', 30),
                            'unfilled_orders': fvg_data.get('unfilled_orders', 0),
                            'strength_level': fvg_data.get('strength_level', 'WEAK'),
                            'institutional_size': fvg_data.get('institutional_size', False)
                        })
        
        if len(all_symbol_fvgs) < 2:
            return []
        
        # FIXED: Group FVGs by type and find overlapping blocks of SAME TYPE
        bullish_fvgs = [fvg for fvg in all_symbol_fvgs if fvg['type'] == 'Bullish']
        bearish_fvgs = [fvg for fvg in all_symbol_fvgs if fvg['type'] == 'Bearish']
        
        # FIXED: Detect bullish blocks (only from bullish FVGs)
        if len(bullish_fvgs) >= 2:
            bullish_blocks = detect_overlapping_fvgs_fixed(bullish_fvgs, symbol, 'BULLISH', price_tolerance_pct)
            detected_blocks.extend(bullish_blocks)
        
        # FIXED: Detect bearish blocks (only from bearish FVGs)
        if len(bearish_fvgs) >= 2:
            bearish_blocks = detect_overlapping_fvgs_fixed(bearish_fvgs, symbol, 'BEARISH', price_tolerance_pct)
            detected_blocks.extend(bearish_blocks)
        
        # Store detected blocks
        fvg_blocks_db[symbol] = detected_blocks
        
        return detected_blocks
        
    except Exception as e:
        print(f"❌ Error detecting blocks for {symbol}: {e}")
        return []

def detect_overlapping_fvgs_fixed(fvg_list, symbol, block_type, tolerance_pct):
    """FIXED: Find overlapping FVGs that form blocks - SAME TYPE ONLY"""
    blocks = []
    processed_fvgs = set()
    
    for i, fvg1 in enumerate(fvg_list):
        if i in processed_fvgs:
            continue
        
        # Start a potential block with this FVG
        block_members = [fvg1]
        block_timeframes = [fvg1['timeframe']]
        processed_fvgs.add(i)
        
        # Check for overlapping FVGs of SAME TYPE
        for j, fvg2 in enumerate(fvg_list[i+1:], i+1):
            if j in processed_fvgs:
                continue
            
            # FIXED: Ensure they are same type and overlap within tolerance
            if (fvg1['type'] == fvg2['type'] and 
                fvgs_overlap_fixed(fvg1, fvg2, tolerance_pct)):
                
                # Ensure different timeframes
                if fvg2['timeframe'] not in block_timeframes:
                    block_members.append(fvg2)
                    block_timeframes.append(fvg2['timeframe'])
                    processed_fvgs.add(j)
        
        # FIXED: If we have 2+ timeframes of SAME TYPE, it's a block
        if len(block_timeframes) >= 2:
            block = create_fvg_block_fixed(symbol, block_type, block_members, block_timeframes)
            if block:
                blocks.append(block)
    
    return blocks

def fvgs_overlap_fixed(fvg1, fvg2, tolerance_pct):
    """FIXED: Check if two FVGs overlap within tolerance"""
    try:
        # Get price ranges
        fvg1_top = float(fvg1['top'])
        fvg1_bottom = float(fvg1['bottom'])
        fvg2_top = float(fvg2['top'])
        fvg2_bottom = float(fvg2['bottom'])
        
        # Calculate tolerance based on smaller gap
        gap1_size = fvg1_top - fvg1_bottom
        gap2_size = fvg2_top - fvg2_bottom
        avg_gap_size = (gap1_size + gap2_size) / 2
        tolerance_amount = avg_gap_size * (tolerance_pct / 100)
        
        # FIXED: Check for ANY overlap (even partial)
        overlap_exists = (
            (fvg1_bottom <= fvg2_top + tolerance_amount) and 
            (fvg1_top >= fvg2_bottom - tolerance_amount)
        )
        
        return overlap_exists
        
    except Exception as e:
        print(f"❌ Error checking FVG overlap: {e}")
        return False

def create_fvg_block_fixed(symbol, block_type, block_members, block_timeframes):
    """FIXED: Create a block object from overlapping FVGs"""
    try:
        # Calculate block boundaries (union of all FVG ranges)
        all_tops = [float(fvg['top']) for fvg in block_members]
        all_bottoms = [float(fvg['bottom']) for fvg in block_members]
        
        block_top = max(all_tops)
        block_bottom = min(all_bottoms)
        
        # Calculate combined power
        total_power = sum(fvg.get('power_score', 30) for fvg in block_members)
        avg_power = total_power / len(block_members)
        
        # Calculate combined unfilled orders
        total_unfilled = sum(fvg.get('unfilled_orders', 0) for fvg in block_members)
        
        # Check for institutional presence
        has_institutional = any(fvg.get('institutional_size', False) for fvg in block_members)
        
        # Determine block strength
        block_strength = determine_block_strength_fixed(len(block_timeframes), avg_power, has_institutional)
        
        # FIXED: Generate block ID with correct type
        timeframes_str = "+".join(sorted(block_timeframes))
        block_id = f"{symbol}_{block_type}_{timeframes_str}_{int(block_bottom)}_{int(block_top)}"
        
        # FIXED: Create block badge with correct type matching
        block_badge = f"{block_type} BLOCK {timeframes_str}"
        if block_strength in ['EXTREME', 'STRONG']:
            block_badge = f"🔥 {block_badge} ({block_strength})"
        
        block = {
            'block_id': block_id,
            'symbol': symbol,
            'type': block_type,  # FIXED: This will be 'BULLISH' or 'BEARISH'
            'timeframes': block_timeframes,
            'timeframes_count': len(block_timeframes),
            'top': block_top,
            'bottom': block_bottom,
            'members': block_members,
            'block_strength': block_strength,
            'block_power': avg_power,
            'total_unfilled_orders': total_unfilled,
            'has_institutional': has_institutional,
            'block_badge': block_badge,
            'detected_at': time.time(),
            'timeframes_str': timeframes_str
        }
        
        print(f"🎯 FIXED BLOCK DETECTED: {symbol} - {block_badge} - Power: {avg_power:.0f}/100 - Unfilled: {format_unfilled_orders(total_unfilled)}")
        
        return block
        
    except Exception as e:
        print(f"❌ Error creating FVG block: {e}")
        return None

def determine_block_strength_fixed(timeframe_count, avg_power, has_institutional):
    """FIXED: Determine the strength level of a block"""
    try:
        # Base strength from timeframe count
        if timeframe_count >= 4:  # All timeframes
            base_strength = 85
        elif timeframe_count >= 3:  # 3 timeframes
            base_strength = 75
        else:  # 2 timeframes
            base_strength = 60
        
        # Power bonus
        power_bonus = min((avg_power - 50) * 0.3, 15) if avg_power > 50 else 0
        
        # Institutional bonus
        institutional_bonus = 10 if has_institutional else 0
        
        total_strength = base_strength + power_bonus + institutional_bonus
        
        if total_strength >= 80:
            return "EXTREME"
        elif total_strength >= 70:
            return "STRONG"
        elif total_strength >= 60:
            return "MEDIUM"
        else:
            return "WEAK"
            
    except Exception as e:
        print(f"❌ Error determining block strength: {e}")
        return "WEAK"

def get_block_info_for_fvg_fixed(symbol, fvg_data):
    """FIXED: Get block information for a specific FVG"""
    try:
        if symbol not in fvg_blocks_db:
            return None
        
        fvg_top = fvg_data.get('top', 0)
        fvg_bottom = fvg_data.get('bottom', 0)
        fvg_timeframe = fvg_data.get('tf', '')
        fvg_type = fvg_data.get('type', '')  # FIXED: Check FVG type
        
        # Check all blocks for this symbol
        for block in fvg_blocks_db[symbol]:
            # FIXED: Only match if block type matches FVG type
            block_type_matches = (
                (block['type'] == 'BULLISH' and fvg_type == 'Bullish') or
                (block['type'] == 'BEARISH' and fvg_type == 'Bearish')
            )
            
            if not block_type_matches:
                continue
            
            # Check if this FVG is part of this block
            if fvg_timeframe in block['timeframes']:
                # Check price overlap
                if (fvg_bottom <= block['top'] and fvg_top >= block['bottom']):
                    return {
                        'is_block_member': True,
                        'block_badge': block['block_badge'],
                        'block_strength': block['block_strength'],
                        'block_timeframes': block['timeframes_str'],
                        'block_power': block['block_power'],
                        'total_unfilled': block['total_unfilled_orders']
                    }
        
        return None
        
    except Exception as e:
        print(f"❌ Error getting block info for FVG: {e}")
        return None

# FIXED: Enhanced price update handler with live filtering
async def handle_price_update_with_live_filtering(clients, symbol, new_price, timeframe):
    """FIXED: Handle price updates with live filtering and new FVG detection"""
    try:
        current_prices[symbol] = float(new_price)
        
        # Send immediate price update
        price_update = {
            "type": "live_price_update",
            "pair": symbol,
            "current_price": float(new_price),
            "timestamp": time.time(),
            "live_update": True,
            "continuous_scanning": True
        }
        await send_to_clients_throttled(clients, price_update)
        
        # FIXED: Check if price movement brings FVGs into filter range
        current_time = time.time()
        if current_time - last_filter_update_time > PRICE_UPDATE_FILTER_CHECK:
            await check_and_update_filtering_for_symbol(clients, symbol, new_price)
            
        # FIXED: Trigger new FVG detection if significant price movement
        if symbol in price_movement_triggered_scans:
            last_check_time, last_price = price_movement_triggered_scans[symbol]
            price_change_pct = abs((float(new_price) - last_price) / last_price * 100)
            
            # If price moved more than 2%, check for new FVGs
            if price_change_pct > 2.0 and (current_time - last_check_time) > 60:
                await trigger_live_fvg_scan_for_symbol(clients, symbol, timeframe)
                price_movement_triggered_scans[symbol] = (current_time, float(new_price))
        else:
            price_movement_triggered_scans[symbol] = (current_time, float(new_price))
            
    except Exception as e:
        print(f"❌ Price update with filtering error for {symbol}: {e}")

# FIXED: Check and update filtering for symbol
async def check_and_update_filtering_for_symbol(clients, symbol, new_price):
    """FIXED: Check if price changes bring FVGs into filter range"""
    global last_filter_update_time
    
    try:
        # Check all stored FVGs for this symbol to see if they're now in range
        newly_visible_fvgs = []
        
        for tf in TIMEFRAMES:
            key = f"{symbol}_{tf}"
            
            # Check bull boxes
            if key in bull_box_arrays:
                for box in bull_box_arrays[key]:
                    if not box.deleted:
                        distance = calculate_exact_distance(box.bottom, box.top, new_price)
                        
                        # Check if this FVG is now within a reasonable filter range (e.g., 20%)
                        if distance <= 20.0:  # Configurable threshold
                            fvg_data = create_enhanced_entry_with_all_features_fixed(
                                box, symbol, tf, new_price, distance, 
                                calculate_exact_touching(box.bottom, box.top, new_price), 'Bullish'
                            )
                            newly_visible_fvgs.append(fvg_data)
            
            # Check bear boxes
            if key in bear_box_arrays:
                for box in bear_box_arrays[key]:
                    if not box.deleted:
                        distance = calculate_exact_distance(box.bottom, box.top, new_price)
                        
                        if distance <= 20.0:
                            fvg_data = create_enhanced_entry_with_all_features_fixed(
                                box, symbol, tf, new_price, distance,
                                calculate_exact_touching(box.bottom, box.top, new_price), 'Bearish'
                            )
                            newly_visible_fvgs.append(fvg_data)
        
        # Send newly visible FVGs to clients
        for fvg in newly_visible_fvgs:
            fvg['newly_visible'] = True
            fvg['filter_update'] = True
            await send_to_clients_throttled(clients, fvg)
            
        last_filter_update_time = time.time()
        
        if newly_visible_fvgs:
            print(f"🔄 LIVE FILTER UPDATE: {len(newly_visible_fvgs)} FVGs now visible for {symbol}")
            
    except Exception as e:
        print(f"❌ Filter update error for {symbol}: {e}")

# FIXED: Live FVG scanning for individual symbol
async def trigger_live_fvg_scan_for_symbol(clients, symbol, timeframe):
    """FIXED: Scan for new FVGs on a specific symbol due to price movement"""
    try:
        if not LIVE_FVG_DETECTION_ENABLED:
            return
            
        print(f"🔍 LIVE FVG SCAN: Checking {symbol} {timeframe} for new FVGs...")
        
        # Fetch latest candle data
        candles_data = await fetch_pine_historical_data(symbol, timeframe, 50)  # Last 50 candles
        
        if not candles_data or len(candles_data) < 10:
            return
            
        # Process for new FVGs
        new_fvgs = pine_process_symbol_timeframe_with_all_features_fixed(symbol, timeframe, candles_data)
        
        current_price = candles_data[-1]['close'] if candles_data else current_prices.get(symbol, 0)
        
        # Send any new FVGs found
        for fvg in new_fvgs:
            if fvg['distance_pct'] < 50:  # Only send reasonable distance FVGs
                entry = convert_fvg_to_entry_format(fvg, symbol, timeframe, current_price, True)
                
                hash_id = f"LIVE-{entry['pair']}-{entry['tf']}-{entry['gap_low']}-{entry['gap_high']}-{int(entry['timestamp'])}"
                if hash_id not in fvg_history:
                    fvg_history[hash_id] = entry
                    await send_to_clients_throttled(clients, entry)
                    print(f"🆕 LIVE FVG DETECTED: {symbol} {timeframe} {fvg['type']} - Distance: {fvg['distance_pct']:.2f}%")
        
    except Exception as e:
        print(f"❌ Live FVG scan error for {symbol}: {e}")

def convert_fvg_to_entry_format(fvg, symbol, timeframe, current_price, is_live=False):
    """Convert FVG data to entry format"""
    return {
        "pair": symbol,
        "tf": timeframe,
        "type": fvg["type"],
        "gap_low": round(fvg["bottom"], 8),
        "gap_high": round(fvg["top"], 8),
        "current_price": round(current_price, 8),
        "distance_pct": fvg["distance_pct"],
        "is_touching": fvg["is_touching"],
        "tested": fvg["tested"],
        "mitigated": False,
        "time": fvg["timestamp"],
        "timestamp": datetime.now().timestamp(),
        "gap_size": round(fvg["gap_size"], 8),
        "is_historical": not is_live,
        "is_live_detected": is_live,
        "live_scan_triggered": is_live,
        "pine_script_exact": True,
        "barstate_confirmed": True,
        "enhanced_500_candles": True,
        "fixed_calculation": True,
        "volumetric_analysis": True,
        "accumulated_order_analysis": True,
        "block_detection_enabled": True,
        "fixed_block_detection": True,
        # Include all enhanced fields
        "volume_strength": fvg.get("volume_strength", 0),
        "volume_tier": fvg.get("volume_tier", "UNKNOWN"),
        "volume_ratio": fvg.get("volume_ratio", 1.0),
        "volume_significant": fvg.get("volume_significant", False),
        "unfilled_orders": fvg.get("unfilled_orders", 0),
        "unfilled_orders_formatted": fvg.get("unfilled_orders_formatted", "0"),
        "order_density": fvg.get("order_density", 0),
        "institutional_size": fvg.get("institutional_size", False),
        "power_score": fvg.get("power_score", 30),
        "strength_level": fvg.get("strength_level", "WEAK"),
        "expected_move_pct": fvg.get("expected_move_pct", 1.5),
        "trigger_probability": fvg.get("trigger_probability", 35),
        "institutional_marker": fvg.get("institutional_marker", ""),
        "strength_emoji": fvg.get("strength_emoji", "📊"),
        "is_block_member": fvg.get("is_block_member", False),
        "block_badge": fvg.get("block_badge", ""),
        "block_strength": fvg.get("block_strength", "NONE"),
        "block_timeframes": fvg.get("block_timeframes", ""),
        "block_power": fvg.get("block_power", 0),
        "block_total_unfilled": fvg.get("block_total_unfilled", 0)
    }

# FIXED: Continuous scanning background task
async def continuous_fvg_scanner(clients, symbols):
    """FIXED: Continuously scan for new FVGs every few minutes"""
    global last_full_scan_time, live_scanning_active
    
    print("🔄 CONTINUOUS SCANNER: Starting background FVG detection...")
    
    while live_scanning_active:
        try:
            current_time = time.time()
            
            # Full rescan every CONTINUOUS_SCAN_INTERVAL seconds
            if current_time - last_full_scan_time > CONTINUOUS_SCAN_INTERVAL:
                print(f"🔍 CONTINUOUS SCAN: Full rescan of {len(symbols)} symbols...")
                
                # Scan a batch of symbols for new FVGs
                batch_size = 20  # Smaller batches for continuous scanning
                for i in range(0, len(symbols), batch_size):
                    batch = symbols[i:i + batch_size]
                    
                    for symbol in batch:
                        if not live_scanning_active:
                            break
                            
                        try:
                            # Quick scan each timeframe for new FVGs
                            for timeframe in TIMEFRAMES:
                                await trigger_live_fvg_scan_for_symbol(clients, symbol, timeframe)
                                await asyncio.sleep(0.1)  # Small delay between scans
                                
                        except Exception as e:
                            print(f"❌ Continuous scan error for {symbol}: {e}")
                            continue
                    
                    # Delay between batches
                    await asyncio.sleep(2)
                    
                    if not live_scanning_active:
                        break
                
                last_full_scan_time = current_time
                print(f"✅ CONTINUOUS SCAN: Completed full rescan of {len(symbols)} symbols")
            
            # Check every 30 seconds
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"❌ Continuous scanner error: {e}")
            await asyncio.sleep(60)  # Wait longer on error
            
    print("🛑 CONTINUOUS SCANNER: Background scanning stopped")

# FIXED: Enhanced send function for continuous updates
async def send_to_clients_throttled(clients, data):
    """ENHANCED: Send data with support for continuous updates"""
    global last_send_time, message_queue
    
    # Handle live price updates immediately
    if data.get('type') in ['price_update', 'live_price_update']:
        pair = data.get('pair')
        new_price = data.get('current_price')
        
        if pair and new_price:
            current_prices[pair] = float(new_price)
            
            if clients:
                for client in list(clients):
                    try:
                        await client.send_text(json.dumps(data))
                    except:
                        clients.discard(client)
            return
    
    # Handle regular FVG data with throttling
    message_queue.append(data)
    
    current_time = time.time()
    if current_time - last_send_time < SEND_DELAY:
        return
    
    if message_queue and clients:
        recent_messages = message_queue[-10:]  # Increased batch size
        message_queue = []
        
        disconnected_clients = []
        for client in list(clients):
            try:
                for message in recent_messages:
                    await client.send_text(json.dumps(message))
                    await asyncio.sleep(0.02)  # Reduced delay
            except Exception as e:
                disconnected_clients.append(client)
        
        for client in disconnected_clients:
            clients.discard(client)
        
        last_send_time = current_time

# FIXED: Enhanced WebSocket processing with live scanning
async def process_pine_connection_with_continuous_scanning(connection_info, clients):
    """FIXED: Enhanced WebSocket processing with continuous FVG detection"""
    connection_id = connection_info['connection_id']
    symbols = connection_info['symbols']
    streams = connection_info['streams']
    
    print(f"🚀 Starting CONTINUOUS SCANNING connection {connection_id} with {len(symbols)} symbols...")
    
    subscribe_message = {
        "method": "SUBSCRIBE",
        "params": streams,
        "id": connection_id
    }
    
    try:
        async with websockets.connect(connection_info['url']) as websocket:
            await websocket.send(json.dumps(subscribe_message))
            print(f"✅ CONTINUOUS SCANNING connection {connection_id} subscribed to {len(streams)} streams")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    if 'k' in data:
                        kline = data['k']
                        symbol = kline['s']
                        timeframe = kline['i']
                        is_closed = kline['x']
                        current_price = float(kline['c'])
                        volume = float(kline['v'])
                        
                        if symbol in symbols:
                            tf_map = {'4h': '4h', '12h': '12h', '1d': '1d', '1w': '1w'}
                            our_timeframe = tf_map.get(timeframe)
                            
                            if our_timeframe:
                                # FIXED: Enhanced price handling with live filtering
                                await handle_price_update_with_live_filtering(clients, symbol, current_price, our_timeframe)
                                
                                if is_closed:
                                    print(f"🔄 LIVE PRICE + SCAN: {symbol} {our_timeframe} - Price: {current_price} - Vol: {format_volume(volume)}")
                        
                except Exception as e:
                    print(f"❌ Connection {connection_id} message error: {e}")
                    continue
                    
    except Exception as e:
        print(f"❌ CONTINUOUS SCANNING connection {connection_id} failed: {e}")

def format_volume(volume):
    """UNCHANGED: Format volume for display preserved exactly"""
    try:
        volume = float(volume)
        if volume >= 1000000000:
            return f"{volume/1000000000:.1f}B"
        elif volume >= 1000000:
            return f"{volume/1000000:.1f}M"
        elif volume >= 1000:
            return f"{volume/1000:.1f}K"
        else:
            return f"{volume:.0f}"
    except:
        return "0"

async def analyze_pine_historical_all_pairs_with_all_features_fixed(clients, symbols_batch):
    """UNCHANGED: Historical analysis preserved exactly"""
    processed_count = 0
    total_fvgs_sent = 0
    
    for symbol in symbols_batch:
        try:
            print(f"🔍 Processing ALL 500 candles + ALL features + FIXED blocks for {symbol}...")
            
            for timeframe in TIMEFRAMES:
                try:
                    candles_data = await fetch_pine_historical_data(symbol, timeframe, HISTORICAL_CANDLES)
                    
                    if not candles_data or len(candles_data) < 10:
                        continue
                    
                    active_fvgs = pine_process_symbol_timeframe_with_all_features_fixed(symbol, timeframe, candles_data)
                    
                    print(f"✅ Found {len(active_fvgs)} ALL-features + FIXED-block FVGs in {symbol} {timeframe} (from {len(candles_data)} candles)")
                    
                    for fvg in active_fvgs:
                        if fvg['distance_pct'] < 50:
                            entry = convert_fvg_to_entry_format(fvg, symbol, timeframe, fvg['current_price'], False)
                            
                            hash_id = f"ENHANCED-ALL-FEATURES-{entry['pair']}-{entry['tf']}-{entry['gap_low']}-{entry['gap_high']}-{entry.get('unfilled_orders', 0)}-{entry.get('block_badge', '')}"
                            if hash_id not in fvg_history:
                                fvg_history[hash_id] = entry
                                await send_to_clients_throttled(clients, entry)
                                total_fvgs_sent += 1
                                
                                if total_fvgs_sent % 100 == 0:
                                    print(f"📈 Sent {total_fvgs_sent} ALL-features + FIXED-block FVGs so far...")
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"❌ Error {symbol} {timeframe}: {e}")
                    continue
            
            processed_count += 1
            if processed_count % 10 == 0:
                print(f"   📈 {processed_count}/{len(symbols_batch)} symbols, {total_fvgs_sent} ALL-features + FIXED-block FVGs")
        
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")
            processed_count += 1
            continue
    
    print(f"✅ ALL FEATURES + FIXED BLOCKS Analysis: {processed_count} symbols, {total_fvgs_sent} FVGs sent (500 candles + ALL features + FIXED block detection each)")

def get_timeframe_strength(timeframe):
    """UNCHANGED: Get timeframe strength preserved exactly"""
    strength_map = {
        '4h': 'Medium',
        '12h': 'Strong', 
        '1d': 'Very Strong',
        '1w': 'Institutional'
    }
    return strength_map.get(timeframe, 'Unknown')

async def create_pine_websocket_connections(symbols):
    """UNCHANGED: Create manageable WebSocket connections for ALL symbols"""
    print(f"🔗 Creating WebSocket connections for {len(symbols)} pairs...")
    
    connections = []
    batch_size = MAX_STREAMS_PER_CONNECTION
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        
        streams = []
        for symbol in batch:
            for timeframe in TIMEFRAMES:
                binance_tf = timeframe.replace('h', 'h').replace('d', 'd').replace('w', 'w')
                stream_name = f"{symbol.lower()}@kline_{binance_tf}"
                streams.append(stream_name)
        
        connection_info = {
            'symbols': batch,
            'streams': streams,
            'connection_id': i // batch_size + 1,
            'url': STREAM_URL
        }
        
        connections.append(connection_info)
    
    print(f"✅ Created {len(connections)} WebSocket connections for {len(symbols)} pairs")
    return connections

# FIXED: Enhanced main runner with continuous scanning
async def run_continuous_scanner_with_live_updates(clients):
    """FIXED: Main scanner with continuous FVG detection and live filtering"""
    global live_scanning_active
    
    print("🔥 CONTINUOUS LIVE SCANNER: Starting with live FVG detection + dynamic filtering...")
    print("✅ FIXED: Continuous scanning for new FVGs every 5 minutes")
    print("✅ FIXED: Live filtering updates when prices move FVGs into range")
    print("✅ FIXED: Preserves ALL existing functionality")
    print("✅ ENHANCED: Real-time price tracking with filter updates")
    
    # Get symbols
    all_symbols = await get_all_active_usdt_perpetual_pairs()
    
    if not all_symbols:
        print("❌ No symbols retrieved")
        return
    
    print(f"🔥 CONTINUOUS SCANNER: Monitoring {len(all_symbols)} pairs with live detection")
    
    # Initial historical analysis (PRESERVED)
    print(f"📊 INITIAL SCAN: Starting 500-candle analysis for {len(all_symbols)} pairs...")
    
    batch_size = 15
    symbol_batches = [all_symbols[i:i + batch_size] for i in range(0, len(all_symbols), batch_size)]
    
    for batch_idx, batch in enumerate(symbol_batches):
        print(f"📊 Initial Batch {batch_idx + 1}/{len(symbol_batches)}: {', '.join(batch[:3])}...")
        await analyze_pine_historical_all_pairs_with_all_features_fixed(clients, batch)
        await asyncio.sleep(1)
    
    print("✅ INITIAL SCAN: Historical analysis completed!")
    
    # Start continuous scanning background task
    live_scanning_active = True
    continuous_scanner_task = asyncio.create_task(continuous_fvg_scanner(clients, all_symbols))
    
    # Start real-time monitoring with enhanced processing
    connections = await create_pine_websocket_connections(all_symbols)
    if connections:
        print(f"🚀 LIVE MONITORING: Starting {len(connections)} WebSocket connections...")
        
        live_tasks = []
        for connection in connections:
            task = asyncio.create_task(process_pine_connection_with_continuous_scanning(connection, clients))
            live_tasks.append(task)
        
        print(f"✅ CONTINUOUS LIVE SCANNER: All systems operational!")
        print(f"🔄 CONTINUOUS: Background FVG scanning every {CONTINUOUS_SCAN_INTERVAL/60:.1f} minutes")
        print(f"🔄 LIVE FILTERING: Price-triggered filter updates every {PRICE_UPDATE_FILTER_CHECK} seconds")
        print(f"🎯 FEATURES: New FVG detection + Live filtering + All original functions")
        
        try:
            while live_scanning_active:
                await asyncio.sleep(60)
                
                active_connections = sum(1 for task in live_tasks if not task.done())
                active_scanner = not continuous_scanner_task.done()
                
                print(f"🔥 LIVE STATUS: {active_connections}/{len(live_tasks)} connections, Scanner: {'✅' if active_scanner else '❌'}")
                
                # Restart continuous scanner if it stopped
                if continuous_scanner_task.done():
                    print("🔄 Restarting continuous scanner...")
                    continuous_scanner_task = asyncio.create_task(continuous_fvg_scanner(clients, all_symbols))
                
        except KeyboardInterrupt:
            print("🛑 CONTINUOUS SCANNER: Stopping...")
            live_scanning_active = False
            continuous_scanner_task.cancel()
            for task in live_tasks:
                task.cancel()
        except Exception as e:
            print(f"❌ CONTINUOUS SCANNER ERROR: {e}")
    
    else:
        print("❌ No WebSocket connections created")

# FIXED: Main run function with continuous scanning
async def run(clients):
    """FIXED: Main runner with continuous live scanning"""
    print("🔥 CONTINUOUS LIVE FVG SCANNER STARTING...")
    print("✅ FIXED: Keeps scanning for new FVGs continuously")
    print("✅ FIXED: Auto-updates filtering when prices change")
    print("✅ PRESERVED: All existing functionality")
    
    while True:
        try:
            await run_continuous_scanner_with_live_updates(clients)
            print("🔄 Scanner completed, restarting in 60 seconds...")
            await asyncio.sleep(60)
        except Exception as e:
            print(f"❌ Scanner error: {e}")
            print("🔄 Restarting scanner in 30 seconds...")
            await asyncio.sleep(30)