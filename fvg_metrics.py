"""fvg_metrics.py — FIXED VERSION with Exact Distance Calculation

Functions to process and return FVG metrics for a given symbol and timeframe.

FIXED: Exact distance calculation matching your original working project
ENHANCED: Support for 500 historical candles

Main usage:
    fvgs = get_active_fvgs(ohlcv)

Returns list of dicts:
    {
        'type': 'Bullish' or 'Bearish',
        'top': float,
        'bottom': float,
        'timestamp': str('%Y-%m-%d %H:%M:%S'),
        'tested': bool,
        'distance_pct': float,  # FIXED: Exact calculation
        'is_touching': bool,
        'current_price': float
    }
"""

import ccxt.async_support as ccxt
from datetime import datetime
from typing import List, Dict

# FIXED: Exact distance calculation from your working version
def calculate_exact_distance(gap_low, gap_high, current_price):
    """
    FIXED: Distance calculation matching your original working project exactly
    
    This is the exact same calculation from your working version that produces
    accurate results like:
    - AXSUSDT: Gap 2.9160-2.9910, Price 2.8860 = 1.04% ✅
    """
    try:
        gap_low = float(gap_low)
        gap_high = float(gap_high)
        current_price = float(current_price)
        
        # Price inside the gap = 0% distance
        if current_price >= gap_low and current_price <= gap_high:
            return 0.0
        
        # Calculate distance from the nearest boundary
        if current_price < gap_low:
            # Distance to bottom of gap
            distance = ((gap_low - current_price) / current_price) * 100
        else:
            # Distance from top of gap
            distance = ((current_price - gap_high) / current_price) * 100
        
        return round(abs(distance), 2)
    except (ValueError, ZeroDivisionError):
        return 999.0

# FIXED: Exact touching detection from your working version
def calculate_exact_touching(gap_low, gap_high, current_price, tolerance=0.15):
    """
    FIXED: Touching calculation matching your original working project
    """
    try:
        gap_low = float(gap_low)
        gap_high = float(gap_high)
        current_price = float(current_price)
        
        # Price inside the gap = touching
        if current_price >= gap_low and current_price <= gap_high:
            return True
        
        # Calculate tolerance based on gap size
        gap_size = gap_high - gap_low
        tolerance_amount = gap_size * (tolerance / 100)
        
        # Check if price is within tolerance of gap boundaries
        return (abs(current_price - gap_low) <= tolerance_amount or 
                abs(current_price - gap_high) <= tolerance_amount)
    except:
        return False

async def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 500) -> List:
    """
    ENHANCED: Fetch OHLCV data with support for 500 candles
    """
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        return ohlcv
    finally:
        await exchange.close()

# ENHANCED: FVG detection with exact distance calculation
def get_active_fvgs(ohlcv: List, changelvl: bool = True) -> List[Dict]:
    """
    ENHANCED: Get active (unmitigated) FVGs with FIXED distance calculation
    
    This function now includes the exact distance calculation from your
    working version to ensure 100% accuracy.
    """
    active_bull_fvgs = []
    active_bear_fvgs = []
    
    if len(ohlcv) < 3:
        return []
    
    # Get current price for distance calculations
    current_price = ohlcv[-1][4]  # Close price of last candle
    
    for i in range(2, len(ohlcv)):
        # Detect new FVG
        timestamp, o, h, l, c, v = ohlcv[i]
        prev2_h = ohlcv[i-2][2]  # High of candle 2 bars ago
        prev2_l = ohlcv[i-2][3]  # Low of candle 2 bars ago
        
        x = 0
        top = None
        bottom = None
        
        # EXACT Pine Script FVG detection logic
        if l >= prev2_h:
            x = 1  # Bullish FVG
            top = l
            bottom = prev2_h
        elif prev2_l >= h:
            x = -1  # Bearish FVG
            top = prev2_l
            bottom = h
        
        if x != 0:
            # FIXED: Calculate exact distance using your working formula
            distance_pct = calculate_exact_distance(bottom, top, current_price)
            is_touching = calculate_exact_touching(bottom, top, current_price)
            
            fvg = {
                'type': 'Bullish' if x == 1 else 'Bearish',
                'top': top,
                'bottom': bottom,
                'timestamp': datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                'tested': False,
                'distance_pct': distance_pct,  # FIXED: Exact calculation
                'is_touching': is_touching,    # FIXED: Exact touching detection
                'current_price': current_price,
                'gap_size': top - bottom,
                'created_at': timestamp / 1000,
                'fixed_calculation': True,     # Mark as using fixed calculation
                'enhanced_version': True       # Mark as enhanced version
            }
            
            if x == 1:
                active_bull_fvgs.append(fvg)
            else:
                active_bear_fvgs.append(fvg)
        
        # Mitigate existing FVGs
        # ENHANCED: Bullish FVG mitigation with exact calculations
        new_bull = []
        for fvg in active_bull_fvgs:
            if l < fvg['bottom']:
                continue  # Mitigated - price broke below FVG
            
            if l < fvg['top']:
                if changelvl:
                    fvg['top'] = l  # Adjust FVG top level
                if not fvg['tested']:
                    fvg['tested'] = True
            
            # FIXED: Recalculate distance with exact formula
            fvg['distance_pct'] = calculate_exact_distance(fvg['bottom'], fvg['top'], current_price)
            fvg['is_touching'] = calculate_exact_touching(fvg['bottom'], fvg['top'], current_price)
            fvg['current_price'] = current_price
            
            new_bull.append(fvg)
        active_bull_fvgs = new_bull
        
        # ENHANCED: Bearish FVG mitigation with exact calculations
        new_bear = []
        for fvg in active_bear_fvgs:
            if h > fvg['top']:
                continue  # Mitigated - price broke above FVG
            
            if h > fvg['bottom']:
                if changelvl:
                    fvg['bottom'] = h  # Adjust FVG bottom level
                if not fvg['tested']:
                    fvg['tested'] = True
            
            # FIXED: Recalculate distance with exact formula
            fvg['distance_pct'] = calculate_exact_distance(fvg['bottom'], fvg['top'], current_price)
            fvg['is_touching'] = calculate_exact_touching(fvg['bottom'], fvg['top'], current_price)
            fvg['current_price'] = current_price
            
            new_bear.append(fvg)
        active_bear_fvgs = new_bear
    
    # Combine and sort by distance (closest first), then by timestamp (newest first)
    all_fvgs = active_bull_fvgs + active_bear_fvgs
    
    # ENHANCED: Sort by distance (closest first) for better priority
    all_fvgs.sort(key=lambda f: (f['distance_pct'], -f['created_at']))
    
    return all_fvgs

# ENHANCED: Get FVGs with memory tier classification
def get_fvgs_with_tiers(ohlcv: List, changelvl: bool = True) -> List[Dict]:
    """
    ENHANCED: Get FVGs with memory tier classification for smart management
    """
    fvgs = get_active_fvgs(ohlcv, changelvl)
    
    # Add memory tier classification
    for fvg in fvgs:
        distance = fvg['distance_pct']
        
        if fvg['is_touching'] or distance == 0:
            fvg['memory_tier'] = 'priority'
        elif distance < 2:
            fvg['memory_tier'] = 'high'
        elif distance < 10:
            fvg['memory_tier'] = 'medium'
        else:
            fvg['memory_tier'] = 'low'
        
        # Add timeframe strength if available
        fvg['timeframe_strength'] = 'Unknown'  # Will be set by scanner
    
    return fvgs

# ENHANCED: Validation function to test distance calculation accuracy
def test_distance_calculation_accuracy():
    """
    ENHANCED: Test function to verify distance calculation accuracy
    
    This tests the exact scenarios from your AXSUSDT example to ensure
    the calculation matches your working version exactly.
    """
    print("🧪 Testing FIXED distance calculation accuracy...")
    
    test_cases = [
        {
            'name': 'AXSUSDT Example',
            'gap_low': 2.9160,
            'gap_high': 2.9910,
            'current_price': 2.8860,
            'expected': 1.04
        },
        {
            'name': 'Inside Gap Test',
            'gap_low': 100.0,
            'gap_high': 105.0,
            'current_price': 102.5,
            'expected': 0.0
        },
        {
            'name': 'Above Gap Test',
            'gap_low': 50.0,
            'gap_high': 55.0,
            'current_price': 60.0,
            'expected': 8.33  # ((60-55)/60)*100 = 8.33%
        },
        {
            'name': 'Below Gap Test',
            'gap_low': 110.0,
            'gap_high': 115.0,
            'current_price': 100.0,
            'expected': 10.0  # ((110-100)/100)*100 = 10.0%
        }
    ]
    
    all_passed = True
    
    for test in test_cases:
        calculated = calculate_exact_distance(test['gap_low'], test['gap_high'], test['current_price'])
        expected = test['expected']
        
        # Allow small rounding differences
        passed = abs(calculated - expected) < 0.01
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test['name']}: Expected {expected}%, Got {calculated}%")
        
        if not passed:
            all_passed = False
    
    if all_passed:
        print("✅ All distance calculation tests PASSED - Accuracy restored!")
    else:
        print("❌ Some tests FAILED - Distance calculation needs fixing!")
    
    return all_passed

# ENHANCED: Advanced FVG analysis with multiple timeframes
def analyze_multi_timeframe_fvgs(symbol: str, timeframes: List[str] = None) -> Dict:
    """
    ENHANCED: Analyze FVGs across multiple timeframes with exact calculations
    """
    if timeframes is None:
        timeframes = ['4h', '12h', '1d', '1w']
    
    results = {}
    
    for tf in timeframes:
        try:
            import asyncio
            ohlcv = asyncio.run(fetch_ohlcv(symbol, tf, 500))  # ENHANCED: 500 candles
            fvgs = get_fvgs_with_tiers(ohlcv)
            
            results[tf] = {
                'fvgs': fvgs,
                'count': len(fvgs),
                'touching': len([f for f in fvgs if f['is_touching']]),
                'priority': len([f for f in fvgs if f['memory_tier'] == 'priority']),
                'high': len([f for f in fvgs if f['memory_tier'] == 'high']),
                'medium': len([f for f in fvgs if f['memory_tier'] == 'medium']),
                'low': len([f for f in fvgs if f['memory_tier'] == 'low'])
            }
            
        except Exception as e:
            print(f"❌ Error analyzing {symbol} {tf}: {e}")
            results[tf] = {'error': str(e)}
    
    return results

# CLI demo with FIXED calculations
if __name__ == "__main__":
    import asyncio, sys
    
    print("🔥 FIXED FVG Metrics - Exact Distance Calculation")
    print("✅ FIXED: Distance calculation accuracy restored")
    print("🚀 ENHANCED: 500 historical candles support")
    print()
    
    # Run accuracy test first
    test_distance_calculation_accuracy()
    print()
    
    if len(sys.argv) < 3:
        print("Usage: python -m fvg_metrics SYMBOL TIMEFRAME")
        print("Example: python -m fvg_metrics BTCUSDT 4h")
        print()
        print("Testing with BTCUSDT 4h...")
        sym, tf = "BTCUSDT", "4h"
    else:
        sym, tf = sys.argv[1], sys.argv[2]
    
    print(f"📊 Analyzing {sym} {tf} with FIXED calculations...")
    
    try:
        ohlcv = asyncio.run(fetch_ohlcv(sym, tf, 500))  # ENHANCED: 500 candles
        print(f"✅ Fetched {len(ohlcv)} candles")
        
        fvgs = get_fvgs_with_tiers(ohlcv)
        print(f"✅ Found {len(fvgs)} FVGs with FIXED distance calculations")
        
        if fvgs:
            print("\n📋 FVG Results:")
            for i, fvg in enumerate(fvgs[:10]):  # Show first 10
                print(f"  {i+1}. {fvg['type']} FVG:")
                print(f"     Gap: {fvg['bottom']:.6f} - {fvg['top']:.6f}")
                print(f"     Current Price: {fvg['current_price']:.6f}")
                print(f"     Distance: {fvg['distance_pct']:.2f}% [FIXED]")
                print(f"     Touching: {'Yes' if fvg['is_touching'] else 'No'}")
                print(f"     Memory Tier: {fvg['memory_tier'].upper()}")
                print(f"     Tested: {'Yes' if fvg['tested'] else 'No'}")
                print(f"     Created: {fvg['timestamp']}")
                print()
            
            if len(fvgs) > 10:
                print(f"... and {len(fvgs) - 10} more FVGs")
            
            # Summary statistics
            touching_count = len([f for f in fvgs if f['is_touching']])
            priority_count = len([f for f in fvgs if f['memory_tier'] == 'priority'])
            high_count = len([f for f in fvgs if f['memory_tier'] == 'high'])
            
            print("\n📊 FIXED Summary Statistics:")
            print(f"  Total FVGs: {len(fvgs)}")
            print(f"  Touching Price: {touching_count}")
            print(f"  Priority Tier: {priority_count}")
            print(f"  High Tier: {high_count}")
            print(f"  Average Distance: {sum(f['distance_pct'] for f in fvgs) / len(fvgs):.2f}%")
            
        else:
            print("No FVGs found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()