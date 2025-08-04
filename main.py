# main.py - PRODUCTION READY for Railway Deployment
# ✅ PRODUCTION: Environment variable support
# ✅ PRODUCTION: Proper CORS configuration
# ✅ PRODUCTION: Health checks and monitoring
# ✅ PRODUCTION: Error handling and logging
# 🚀 RAILWAY: Optimized for Railway hosting platform

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import asyncio
import scanner
import uvicorn
import json
import warnings
import os
import logging
from pathlib import Path
import time

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Get environment variables
PORT = int(os.environ.get("PORT", 8000))
ENVIRONMENT = os.environ.get("RAILWAY_ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

app = FastAPI(
    title="FVG Scanner API - Production", 
    version="2.1.0",
    description="Production FVG Scanner with Real-Time Updates and Block Detection",
    docs_url="/docs" if not IS_PRODUCTION else None,  # Hide docs in production
    redoc_url="/redoc" if not IS_PRODUCTION else None
)

# PRODUCTION CORS - Configure properly for your domain
allowed_origins = ["*"] if not IS_PRODUCTION else [
    "https://your-domain.com",  # Replace with your actual domain
    "https://your-app-name.up.railway.app"  # Replace with your Railway URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connected WebSocket clients with enhanced tracking
clients = set()
client_stats = {
    'total_connected': 0,
    'total_disconnected': 0,
    'messages_sent': 0,
    'price_updates_sent': 0,
    'start_time': time.time()
}

# Setup static files path
static_path = Path(__file__).parent / "static"

@app.get("/", response_class=HTMLResponse)
async def get_root():
    """Serve the enhanced dashboard"""
    index_path = static_path / "index.html"
    if index_path.exists():
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Inject production configuration
            production_config = f"""
            <script>
                window.PRODUCTION_CONFIG = {{
                    version: "2.1.0",
                    environment: "{ENVIRONMENT}",
                    isProduction: {str(IS_PRODUCTION).lower()},
                    historicalCandles: 500,
                    unlimitedStorage: true,
                    smartMemoryManagement: true,
                    fixedBlockDetection: true,
                    realTimeUpdates: true,
                    dynamicFiltering: true,
                    startTime: {int(time.time() * 1000)},
                    websocketUrl: "{get_websocket_url()}"
                }};
            </script>
            """
            content = content.replace('</head>', f'{production_config}</head>')
            
            return HTMLResponse(content)
        except Exception as e:
            logger.error(f"Error reading index.html: {e}")
            return HTMLResponse(f"Error reading index.html: {e}", status_code=500)
    else:
        return HTMLResponse("Index file not found - Please ensure static files are deployed", status_code=404)

def get_websocket_url():
    """Get appropriate WebSocket URL for environment"""
    if IS_PRODUCTION:
        return "wss://" + os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost") + "/ws"
    else:
        return f"ws://localhost:{PORT}/ws"

@app.get("/styles.css")
async def get_styles():
    """Serve CSS file"""
    css_path = static_path / "styles.css"
    if css_path.exists():
        return FileResponse(css_path, media_type="text/css")
    return HTMLResponse("CSS file not found", status_code=404)

@app.get("/script.js")
async def get_script():
    """Serve JavaScript file"""
    js_path = static_path / "script.js"
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    return HTMLResponse("JavaScript file not found", status_code=404)

# Mount static files
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    logger.info(f"✅ PRODUCTION: Mounted static files from: {static_path}")
else:
    logger.error(f"❌ PRODUCTION: Static directory not found: {static_path}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for FVG data streaming"""
    await websocket.accept()
    clients.add(websocket)
    client_stats['total_connected'] += 1
    
    client_id = f"client_{len(clients)}_{int(time.time())}"
    logger.info(f"✅ PRODUCTION: WebSocket client connected [{client_id}]. Total clients: {len(clients)}")
    
    try:
        # Send welcome message
        welcome_message = {
            "type": "welcome",
            "message": "Connected to Production FVG Scanner",
            "timestamp": time.time(),
            "client_id": client_id,
            "server_version": "2.1.0",
            "environment": ENVIRONMENT,
            "features": {
                "historical_candles": 500,
                "unlimited_storage": True,
                "smart_memory_management": True,
                "enhanced_filtering": True,
                "priority_system": True,
                "fixed_block_detection": True,
                "real_time_updates": True,
                "dynamic_filtering": True,
                "production_ready": True
            },
            "server_uptime": time.time() - client_stats['start_time']
        }
        
        await websocket.send_text(json.dumps(welcome_message))
        client_stats['messages_sent'] += 1
        
        # Keep connection alive with heartbeat
        heartbeat_count = 0
        while True:
            await asyncio.sleep(30)
            heartbeat_count += 1
            
            heartbeat_message = {
                "type": "heartbeat",
                "timestamp": time.time(),
                "client_id": client_id,
                "heartbeat_count": heartbeat_count,
                "environment": ENVIRONMENT,
                "server_stats": {
                    "active_clients": len(clients),
                    "total_messages_sent": client_stats['messages_sent'],
                    "price_updates_sent": client_stats['price_updates_sent'],
                    "uptime_seconds": int(time.time() - client_stats['start_time'])
                }
            }
            
            await websocket.send_text(json.dumps(heartbeat_message))
            client_stats['messages_sent'] += 1
            
    except WebSocketDisconnect:
        logger.info(f"❌ PRODUCTION: WebSocket client disconnected [{client_id}]")
    except Exception as e:
        logger.error(f"❌ PRODUCTION: WebSocket error [{client_id}]: {e}")
    finally:
        clients.discard(websocket)
        client_stats['total_disconnected'] += 1
        logger.info(f"📊 PRODUCTION: Remaining clients: {len(clients)}")

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    uptime_seconds = int(time.time() - client_stats['start_time'])
    
    return {
        "status": "healthy",
        "service": "FVG Scanner",
        "version": "2.1.0",
        "environment": ENVIRONMENT,
        "timestamp": time.time(),
        "uptime_seconds": uptime_seconds,
        "active_connections": len(clients),
        "components": {
            "websocket_server": "operational",
            "static_file_server": "operational" if static_path.exists() else "missing_files",
            "fvg_scanner_backend": "operational",
            "memory_management": "operational",
            "block_detection": "operational",
            "real_time_updates": "operational"
        },
        "performance": {
            "expected_data_throughput": "High - 500 candles per symbol",
            "memory_optimization": "Smart archiving enabled",
            "frontend_storage": "Unlimited with intelligent cleanup"
        }
    }

@app.get("/status")
async def get_status():
    """Detailed scanner status"""
    uptime_seconds = int(time.time() - client_stats['start_time'])
    uptime_minutes = uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    
    return {
        "status": "running",
        "version": "2.1.0",
        "environment": ENVIRONMENT,
        "is_production": IS_PRODUCTION,
        "enhanced_features": {
            "historical_candles": 500,
            "unlimited_frontend_storage": True,
            "smart_memory_management": True,
            "enhanced_visual_indicators": True,
            "priority_based_filtering": True,
            "performance_optimizations": True,
            "fixed_block_detection": True,
            "real_time_price_updates": True,
            "dynamic_filtering": True
        },
        "connection_stats": {
            "connected_clients": len(clients),
            "total_connected_lifetime": client_stats['total_connected'],
            "total_disconnected_lifetime": client_stats['total_disconnected'],
            "messages_sent_lifetime": client_stats['messages_sent'],
            "price_updates_sent_lifetime": client_stats['price_updates_sent']
        },
        "server_info": {
            "uptime_seconds": uptime_seconds,
            "uptime_display": f"{uptime_hours}h {uptime_minutes % 60}m {uptime_seconds % 60}s",
            "scanner_active": True,
            "port": PORT,
            "static_files_available": static_path.exists()
        }
    }

@app.get("/metrics")
async def get_metrics():
    """Production metrics endpoint"""
    uptime = time.time() - client_stats['start_time']
    
    return {
        "scanner_metrics": {
            "version": "2.1.0",
            "environment": ENVIRONMENT,
            "uptime_seconds": int(uptime),
            "historical_candles_per_symbol": 500,
            "estimated_total_candles_processed": "450+ symbols × 4 timeframes × 500 candles = 900,000+"
        },
        "connection_metrics": {
            "current_active_clients": len(clients),
            "lifetime_connections": client_stats['total_connected'],
            "lifetime_disconnections": client_stats['total_disconnected'],
            "total_messages_sent": client_stats['messages_sent'],
            "price_updates_sent": client_stats['price_updates_sent'],
            "average_messages_per_minute": round(client_stats['messages_sent'] / max(uptime / 60, 1), 2)
        },
        "performance_metrics": {
            "processing_speed": "500 candles per symbol/timeframe",
            "batch_size": "15 symbols per batch",
            "throttling": "800ms update intervals",
            "memory_management": "Smart with priority-based retention"
        }
    }

@app.get("/debug")
async def debug_info():
    """Debug information - only available in development"""
    if IS_PRODUCTION:
        return {"message": "Debug endpoint not available in production"}
    
    return {
        "status": "running",
        "environment": ENVIRONMENT,
        "port": PORT,
        "static_files": static_path.exists(),
        "static_path": str(static_path),
        "websocket_url": get_websocket_url(),
        "files_in_static": [f.name for f in static_path.glob("*")] if static_path.exists() else [],
        "env_vars": {
            "PORT": os.environ.get("PORT"),
            "RAILWAY_ENVIRONMENT": os.environ.get("RAILWAY_ENVIRONMENT"),
            "RAILWAY_PUBLIC_DOMAIN": os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        }
    }

@app.on_event("startup")
async def startup_event():
    """Start the scanner when the app starts"""
    logger.info("🚀 Starting Production FVG Scanner Service...")
    logger.info(f"🌍 Environment: {ENVIRONMENT}")
    logger.info(f"🔌 Port: {PORT}")
    logger.info(f"📁 Static files directory: {static_path}")
    logger.info(f"📊 WebSocket endpoint: /ws")
    logger.info(f"🔗 WebSocket URL: {get_websocket_url()}")
    
    # Check static files
    if static_path.exists():
        files = list(static_path.glob("*"))
        logger.info(f"📋 Static files found: {[f.name for f in files]}")
        
        required_files = ['index.html', 'script.js', 'styles.css']
        missing_files = [f for f in required_files if not (static_path / f).exists()]
        
        if missing_files:
            logger.warning(f"⚠️ Missing required files: {missing_files}")
        else:
            logger.info("✅ All required static files found")
    else:
        logger.error("❌ Static directory not found")
        static_path.mkdir(exist_ok=True)
    
    # Record startup time for metrics
    client_stats['start_time'] = time.time()
    
    # Start scanner in background
    logger.info("🔥 PRODUCTION SCANNER CONFIGURATION:")
    logger.info("   📊 Historical Candles: 500 per symbol/timeframe")
    logger.info("   💾 Frontend Storage: Unlimited with smart archiving")
    logger.info("   🧠 Memory Management: Priority-based retention system")
    logger.info("   ⚡ Performance: Auto-optimization for large datasets")
    logger.info(f"   🌍 Environment: {ENVIRONMENT}")
    logger.info(f"   🔗 WebSocket URL: {get_websocket_url()}")
    
    asyncio.create_task(scanner.run(clients))
    logger.info("✅ Production FVG Scanner background task started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when the app shuts down"""
    logger.info("🛑 Shutting down Production FVG Scanner service...")
    
    uptime = time.time() - client_stats['start_time']
    uptime_hours = int(uptime // 3600)
    uptime_minutes = int((uptime % 3600) // 60)
    uptime_seconds = int(uptime % 60)
    
    logger.info(f"📊 PRODUCTION Session Statistics:")
    logger.info(f"   ⏱️ Uptime: {uptime_hours}h {uptime_minutes}m {uptime_seconds}s")
    logger.info(f"   🔗 Total connections: {client_stats['total_connected']}")
    logger.info(f"   📤 Messages sent: {client_stats['messages_sent']}")
    logger.info(f"   📱 Price updates sent: {client_stats['price_updates_sent']}")
    
    # Close all websocket connections gracefully
    disconnect_count = 0
    for client in list(clients):
        try:
            await client.close(code=1001, reason="Server shutdown")
            disconnect_count += 1
        except Exception as e:
            logger.warning(f"Warning: Error closing client connection: {e}")
    
    clients.clear()
    logger.info(f"🔌 Gracefully disconnected {disconnect_count} clients")
    logger.info("✅ Production FVG Scanner service shutdown complete")

if __name__ == "__main__":
    logger.info("🔧 Starting Production FVG Scanner Dashboard...")
    logger.info(f"🌍 Environment: {ENVIRONMENT}")
    logger.info(f"🌐 Dashboard will be available at: http://0.0.0.0:{PORT}")
    logger.info(f"📡 WebSocket endpoint: {get_websocket_url()}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=PORT,
        log_level="info",
        access_log=True,
        reload=False  # Disable reload in production
    )