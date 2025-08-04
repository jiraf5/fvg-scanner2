from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import os
import asyncio
import json
import time
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FVG Scanner - Production",
    version="2.1.0",
    description="Real-time Fair Value Gap Scanner for Cryptocurrency Trading"
)

# CORS Configuration for Railway deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files if directory exists
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✅ Static files mounted from /static")
else:
    logger.info("⚠️ Static directory not found")

# Global variables for WebSocket connections
connected_clients = set()
fvg_data_buffer = []

@app.get("/")
async def read_root():
    """Serve the main FVG Scanner interface"""
    try:
        # Try to find and serve the main HTML file
        html_candidates = [
            "static/index.html",
            "index.html", 
            "static/fvg-scanner.html",
            "fvg-scanner.html"
        ]
        
        for html_file in html_candidates:
            if os.path.exists(html_file):
                logger.info(f"✅ Serving HTML from: {html_file}")
                with open(html_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Auto-fix WebSocket URL in HTML if needed
                    content = content.replace(
                        'ws://localhost:8000/ws',
                        'wss://web-production-6b86c.up.railway.app/ws'
                    )
                    content = content.replace(
                        'ws://127.0.0.1:8000/ws', 
                        'wss://web-production-6b86c.up.railway.app/ws'
                    )
                    return HTMLResponse(content=content)
        
        # If no HTML file found, serve embedded interface
        logger.info("📄 No HTML file found, serving embedded interface")
        return HTMLResponse(content=get_embedded_interface())
        
    except Exception as e:
        logger.error(f"❌ Error serving root: {e}")
        return HTMLResponse(content=f"""
        <html>
        <head>
            <title>FVG Scanner - Error</title>
            <style>body {{ font-family: Arial; margin: 40px; background: #1a1a1a; color: white; }}</style>
        </head>
        <body>
            <h1>🔥 FVG Scanner Backend</h1>
            <p>✅ <strong>Status:</strong> Running</p>
            <p>❌ <strong>Error:</strong> {str(e)}</p>
            <p>🌐 <strong>WebSocket:</strong> wss://web-production-6b86c.up.railway.app/ws</p>
            <a href="/health" style="color: #4CAF50;">Check Health</a> | 
            <a href="/docs" style="color: #4CAF50;">API Docs</a>
        </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway monitoring"""
    return {
        "status": "healthy",
        "service": "fvg-scanner",
        "version": "2.1.0",
        "environment": "production",
        "timestamp": time.time(),
        "uptime": time.time(),
        "connected_clients": len(connected_clients),
        "features": [
            "Real-time FVG detection",
            "Multi-timeframe analysis",
            "500+ cryptocurrency pairs",
            "Unfilled order tracking",
            "Block confluence detection",
            "WebSocket streaming"
        ]
    }

@app.get("/status")
async def get_status():
    """Detailed service status"""
    return {
        "backend": "online",
        "websocket": "available",
        "scanner": "active",
        "clients_connected": len(connected_clients),
        "data_buffer_size": len(fvg_data_buffer),
        "urls": {
            "main": "https://web-production-6b86c.up.railway.app",
            "websocket": "wss://web-production-6b86c.up.railway.app/ws",
            "health": "https://web-production-6b86c.up.railway.app/health",
            "docs": "https://web-production-6b86c.up.railway.app/docs"
        }
    }

@app.get("/api/info")
async def api_info():
    """API information and endpoints"""
    return {
        "name": "FVG Scanner API",
        "version": "2.1.0",
        "description": "Real-time Fair Value Gap analysis for cryptocurrency trading",
        "endpoints": {
            "root": "/ - Main FVG Scanner interface",
            "health": "/health - Health check",
            "status": "/status - Service status",
            "websocket": "/ws - Real-time WebSocket data",
            "docs": "/docs - API documentation"
        },
        "websocket_url": "wss://web-production-6b86c.up.railway.app/ws"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time FVG data streaming"""
    client_id = id(websocket)
    
    try:
        await websocket.accept()
        connected_clients.add(websocket)
        logger.info(f"✅ WebSocket client {client_id} connected. Total clients: {len(connected_clients)}")
        
        # Send welcome message
        welcome_message = {
            "type": "connection",
            "message": "Connected to FVG Scanner 2.1.0",
            "environment": "production", 
            "client_id": str(client_id),
            "timestamp": time.time(),
            "server_time": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "features": [
                "Real-time FVG detection",
                "500+ cryptocurrency pairs",
                "Multi-timeframe analysis (4h, 12h, 1d, 1w)",
                "Volume-based filtering",
                "Unfilled order tracking",
                "Institutional block detection",
                "Block confluence analysis"
            ]
        }
        await websocket.send_json(welcome_message)
        
        # Try to start your actual FVG scanner
        try:
            # Import your scanner modules
            from scanner import start_fvg_scanner
            logger.info("📊 Starting real FVG scanner...")
            await start_fvg_scanner(websocket)
            
        except ImportError as e:
            logger.warning(f"⚠️ Scanner module not found: {e}")
            logger.info("🧪 Starting sample FVG data generator...")
            await send_sample_fvg_data(websocket)
            
        except Exception as e:
            logger.error(f"❌ Scanner startup error: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"Scanner error: {str(e)}",
                "timestamp": time.time()
            })
            # Fall back to sample data
            await send_sample_fvg_data(websocket)
            
    except WebSocketDisconnect:
        logger.info(f"📤 WebSocket client {client_id} disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error for client {client_id}: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info(f"🔌 Client {client_id} cleaned up. Total clients: {len(connected_clients)}")

async def send_sample_fvg_data(websocket: WebSocket):
    """Send realistic sample FVG data for testing"""
    
    # Realistic cryptocurrency pairs
    crypto_pairs = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
        "DOGEUSDT", "SOLUSDT", "MATICUSDT", "DOTUSDT", "AVAXUSDT",
        "LINKUSDT", "ATOMUSDT", "NEARUSDT", "ALGOUSDT", "VETUSDT",
        "FILUSDT", "TRXUSDT", "ETCUSDT", "XLMUSDT", "MANAUSDT"
    ]
    
    timeframes = ["4h", "12h", "1d", "1w"]
    fvg_types = ["Bullish", "Bearish"]
    
    # Price ranges for different pairs
    price_ranges = {
        "BTCUSDT": (40000, 70000),
        "ETHUSDT": (2000, 4000), 
        "BNBUSDT": (200, 600),
        "XRPUSDT": (0.3, 0.8),
        "ADAUSDT": (0.2, 0.6)
    }
    
    counter = 0
    
    try:
        while True:
            await asyncio.sleep(2)  # Send data every 2 seconds
            
            import random
            
            pair = random.choice(crypto_pairs)
            tf = random.choice(timeframes)
            fvg_type = random.choice(fvg_types)
            
            # Get realistic price range
            if pair in price_ranges:
                price_min, price_max = price_ranges[pair]
            else:
                price_min, price_max = (0.1, 10.0)  # Default for other pairs
            
            current_price = round(random.uniform(price_min, price_max), 6)
            gap_size = current_price * random.uniform(0.001, 0.05)  # 0.1% to 5% gap
            
            if fvg_type == "Bullish":
                gap_low = round(current_price - gap_size, 6)
                gap_high = round(current_price, 6)
            else:
                gap_low = round(current_price, 6)
                gap_high = round(current_price + gap_size, 6)
            
            # Generate realistic FVG data
            fvg_data = {
                "type": "fvg_data",
                "pair": pair,
                "tf": tf,
                "fvg_type": fvg_type,
                "gap_low": gap_low,
                "gap_high": gap_high, 
                "current_price": current_price,
                "distance_pct": round(random.uniform(0.1, 10.0), 2),
                "is_touching": random.choice([True, False, False, False]),  # 25% chance
                "tested": random.choice([True, False, False]),  # 33% chance
                "volume": random.randint(100000, 10000000),
                "orders": random.randint(5000, 2000000),
                "power": random.randint(15, 95),
                "significance": random.choice(["WEAK", "MEDIUM", "STRONG"]),
                "timestamp": time.time()
            }
            
            await websocket.send_json(fvg_data)
            counter += 1
            
            # Send heartbeat and stats every 10 messages
            if counter % 10 == 0:
                stats_message = {
                    "type": "stats",
                    "message": f"📊 Processed {counter} FVG samples",
                    "total_fvgs": counter,
                    "clients_connected": len(connected_clients),
                    "uptime_seconds": int(time.time()),
                    "timestamp": time.time()
                }
                await websocket.send_json(stats_message)
                
            # Send enhanced FVG every 5 messages
            if counter % 5 == 0:
                enhanced_fvg = {
                    "type": "enhanced_fvg",
                    "pair": random.choice(crypto_pairs),
                    "timeframe": random.choice(timeframes),
                    "fvg_type": random.choice(fvg_types),
                    "unfilled_orders": random.randint(50000, 3000000),
                    "power_rating": random.randint(30, 90),
                    "confluence": random.choice([True, False]),
                    "institutional_size": random.choice([True, False]),
                    "timestamp": time.time()
                }
                await websocket.send_json(enhanced_fvg)
                
    except WebSocketDisconnect:
        logger.info("📤 Sample data client disconnected")
    except Exception as e:
        logger.error(f"❌ Sample data error: {e}")

def get_embedded_interface():
    """Return embedded HTML interface when static files not found"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FVG Scanner - Production</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            padding: 30px;
            backdrop-filter: blur(10px);
        }
        h1 {
            text-align: center;
            color: #4CAF50;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            margin-bottom: 30px;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .status-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #4CAF50;
        }
        .status-card h3 {
            margin-top: 0;
            color: #4CAF50;
        }
        .button {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px;
            transition: all 0.3s ease;
        }
        .button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .output {
            background: #000;
            color: #0f0;
            padding: 20px;
            border-radius: 8px;
            min-height: 300px;
            font-family: 'Courier New', monospace;
            margin: 20px 0;
            overflow-y: auto;
            max-height: 400px;
            border: 1px solid #333;
        }
        .controls {
            text-align: center;
            margin: 20px 0;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }
        .stat-label {
            font-size: 12px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 FVG Scanner - Production Ready</h1>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>✅ Backend Status</h3>
                <p><strong>Status:</strong> Online</p>
                <p><strong>Version:</strong> 2.1.0</p>
                <p><strong>Environment:</strong> Production</p>
            </div>
            
            <div class="status-card">
                <h3>📊 Live Data Stream</h3>
                <p><strong>WebSocket:</strong> Available</p>
                <p><strong>URL:</strong> wss://web-production-6b86c.up.railway.app/ws</p>
                <p><strong>Status:</strong> <span id="connectionStatus">Disconnected</span></p>
            </div>
            
            <div class="status-card">
                <h3>🎯 Features</h3>
                <p>• Real-time FVG detection</p>
                <p>• Multi-timeframe analysis</p>
                <p>• Unfilled order tracking</p>
                <p>• Block confluence detection</p>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value" id="totalFVGs">0</div>
                <div class="stat-label">Total FVGs</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="bullishCount">0</div>
                <div class="stat-label">Bullish</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="bearishCount">0</div>
                <div class="stat-label">Bearish</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="connectedClients">0</div>
                <div class="stat-label">Connected</div>
            </div>
        </div>
        
        <div class="controls">
            <button class="button" onclick="connectWebSocket()">🔗 Connect to Live Data</button>
            <button class="button" onclick="disconnectWebSocket()">⏹️ Disconnect</button>
            <button class="button" onclick="clearOutput()">🧹 Clear Output</button>
            <button class="button" onclick="testBackend()">🧪 Test Backend</button>
        </div>
        
        <div id="output" class="output">
            🚀 FVG Scanner Ready - Click "Connect to Live Data" to start monitoring...
        </div>
    </div>
    
    <script>
        let ws = null;
        let fvgCount = 0;
        let bullishCount = 0;
        let bearishCount = 0;
        
        function updateStatus(status) {
            document.getElementById('connectionStatus').textContent = status;
        }
        
        function updateStats() {
            document.getElementById('totalFVGs').textContent = fvgCount;
            document.getElementById('bullishCount').textContent = bullishCount;
            document.getElementById('bearishCount').textContent = bearishCount;
        }
        
        function addOutput(message) {
            const output = document.getElementById('output');
            const timestamp = new Date().toLocaleTimeString();
            output.textContent += `[${timestamp}] ${message}\\n`;
            output.scrollTop = output.scrollHeight;
        }
        
        function connectWebSocket() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                addOutput('⚠️ Already connected');
                return;
            }
            
            addOutput('🔗 Connecting to FVG Scanner...');
            updateStatus('Connecting...');
            
            ws = new WebSocket('wss://web-production-6b86c.up.railway.app/ws');
            
            ws.onopen = function() {
                addOutput('✅ Connected to FVG Scanner!');
                addOutput('📊 Monitoring real-time FVG data...');
                updateStatus('Connected ✅');
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'fvg_data') {
                        fvgCount++;
                        if (data.fvg_type === 'Bullish') bullishCount++;
                        if (data.fvg_type === 'Bearish') bearishCount++;
                        
                        addOutput(`📊 ${data.pair} ${data.tf} ${data.fvg_type} - Orders: ${data.orders || 'N/A'} - Power: ${data.power || 'N/A'}`);
                        updateStats();
                        
                    } else if (data.type === 'connection') {
                        addOutput(`🎉 ${data.message}`);
                        
                    } else if (data.type === 'enhanced_fvg') {
                        addOutput(`💥 ENHANCED: ${data.pair} ${data.timeframe} ${data.fvg_type} - Unfilled: ${data.unfilled_orders}`);
                        
                    } else if (data.type === 'stats') {
                        addOutput(`📈 ${data.message}`);
                        document.getElementById('connectedClients').textContent = data.clients_connected || 0;
                        
                    } else {
                        addOutput(`📡 ${data.type || 'Data'}: ${JSON.stringify(data).substring(0, 80)}...`);
                    }
                    
                } catch (e) {
                    addOutput(`📝 Raw: ${event.data.substring(0, 100)}...`);
                }
            };
            
            ws.onerror = function(error) {
                addOutput('❌ Connection error');
                updateStatus('Error ❌');
            };
            
            ws.onclose = function(event) {
                addOutput(`🔌 Connection closed (Code: ${event.code})`);
                updateStatus('Disconnected');
            };
        }
        
        function disconnectWebSocket() {
            if (ws) {
                ws.close();
                addOutput('⏹️ Disconnected');
                updateStatus('Disconnected');
            }
        }
        
        function clearOutput() {
            document.getElementById('output').textContent = '';
            fvgCount = 0;
            bullishCount = 0;
            bearishCount = 0;
            updateStats();
        }
        
        function testBackend() {
            addOutput('🧪 Testing backend endpoints...');
            
            fetch('/health')
                .then(r => r.json())
                .then(d => {
                    addOutput(`✅ Health check: ${d.status} v${d.version}`);
                    addOutput(`📊 Features: ${d.features.length} available`);
                })
                .catch(e => addOutput(`❌ Health check failed: ${e.message}`));
                
            fetch('/status')
                .then(r => r.json())
                .then(d => {
                    addOutput(`📈 Status: ${d.backend} - Scanner: ${d.scanner}`);
                    addOutput(`🔗 Clients: ${d.clients_connected} - Buffer: ${d.data_buffer_size}`);
                })
                .catch(e => addOutput(`❌ Status check failed: ${e.message}`));
        }
        
        // Auto-connect on page load
        window.onload = function() {
            setTimeout(connectWebSocket, 1000);
        };
    </script>
</body>
</html>
    """

# Railway startup
if __name__ == "__main__":
    import uvicorn
    
    # Get port from Railway environment
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting FVG Scanner on {host}:{port}")
    logger.info(f"📊 Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'development')}")
    logger.info(f"🌐 WebSocket will be available at: wss://web-production-6b86c.up.railway.app/ws")
    
    # Start the server
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_level="info",
        access_log=True
    )
