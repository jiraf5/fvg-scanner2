// PRODUCTION SCRIPT.JS - WebSocket Auto-Detection for Railway
// ✅ PRODUCTION: Automatic environment detection
// ✅ PRODUCTION: Proper WebSocket URL handling
// ✅ PRODUCTION: Error handling and reconnection
// 🚀 RAILWAY: Optimized for Railway deployment

document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 PRODUCTION: FVG Scanner with Auto WebSocket Detection");
    
    // PRODUCTION: Auto-detect WebSocket URL based on environment
    function getWebSocketURL() {
        const protocol = location.protocol === "https:" ? "wss" : "ws";
        const host = location.hostname;
        const port = location.port;
        
        // Production configuration from server
        if (window.PRODUCTION_CONFIG && window.PRODUCTION_CONFIG.websocketUrl) {
            console.log("🌐 PRODUCTION: Using server-provided WebSocket URL");
            return window.PRODUCTION_CONFIG.websocketUrl;
        }
        
        // Auto-detect Railway deployment
        if (host.includes('railway.app') || host.includes('up.railway.app')) {
            const wsUrl = `wss://${host}/ws`;
            console.log(`🚂 RAILWAY: Detected Railway deployment - ${wsUrl}`);
            return wsUrl;
        }
        
        // Auto-detect other HTTPS deployments
        if (protocol === "https:") {
            const wsUrl = `wss://${host}/ws`;
            console.log(`🔒 HTTPS: Using secure WebSocket - ${wsUrl}`);
            return wsUrl;
        }
        
        // Local development fallback
        const wsUrl = `${protocol}://${host}:${port || 8000}/ws`;
        console.log(`💻 LOCAL: Using development WebSocket - ${wsUrl}`);
        return wsUrl;
    }

    // PRODUCTION: Enhanced WebSocket connection with retry logic
    let ws;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 10;
    let reconnectDelay = 1000; // Start with 1 second
    let isConnected = false;
    let heartbeatInterval;

    function connectWebSocket() {
        try {
            const wsUrl = getWebSocketURL();
            console.log(`🔗 PRODUCTION: Connecting to ${wsUrl}`);
            
            if (ws) {
                ws.close();
            }
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function(event) {
                console.log("✅ PRODUCTION: WebSocket connected successfully");
                isConnected = true;
                reconnectAttempts = 0;
                reconnectDelay = 1000; // Reset delay
                
                updateConnectionStatus('connected');
                
                // Start heartbeat monitoring
                startHeartbeat();
            };

            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    
                    // Handle different message types
                    if (data.type === "welcome") {
                        console.log("🎉 PRODUCTION: Welcome message received", data.environment);
                        handleWelcomeMessage(data);
                    } else if (data.type === "heartbeat") {
                        console.log("💓 PRODUCTION: Heartbeat received");
                        handleHeartbeat(data);
                    } else if (data.type === "price_update" || data.type === "live_price_update") {
                        handlePriceUpdate(data);
                    } else if (data.pair && data.tf && data.type) {
                        // FVG data
                        handleFVGData(data);
                    }
                    
                } catch (error) {
                    console.error("❌ PRODUCTION: Error parsing WebSocket message:", error);
                }
            };

            ws.onclose = function(event) {
                console.log(`❌ PRODUCTION: WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);
                isConnected = false;
                updateConnectionStatus('disconnected');
                stopHeartbeat();
                
                // Attempt reconnection with exponential backoff
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    console.log(`🔄 PRODUCTION: Reconnection attempt ${reconnectAttempts}/${maxReconnectAttempts} in ${reconnectDelay}ms`);
                    
                    setTimeout(() => {
                        connectWebSocket();
                    }, reconnectDelay);
                    
                    // Exponential backoff with max delay of 30 seconds
                    reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
                } else {
                    console.error("❌ PRODUCTION: Max reconnection attempts reached");
                    updateConnectionStatus('failed');
                }
            };

            ws.onerror = function(event) {
                console.error("❌ PRODUCTION: WebSocket error occurred", event);
                updateConnectionStatus('error');
            };

        } catch (error) {
            console.error("❌ PRODUCTION: Failed to create WebSocket connection:", error);
            updateConnectionStatus('error');
        }
    }

    function startHeartbeat() {
        // Monitor heartbeat messages
        heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                // WebSocket is open, heartbeat is handled by server
                console.log("💓 PRODUCTION: WebSocket heartbeat check - OK");
            } else {
                console.warn("⚠️ PRODUCTION: WebSocket connection lost, attempting reconnect");
                connectWebSocket();
            }
        }, 60000); // Check every minute
    }

    function stopHeartbeat() {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
    }

    function updateConnectionStatus(status) {
        const statusIndicator = document.getElementById('status-indicator');
        const connectionText = document.getElementById('connectionText');
        
        if (statusIndicator) {
            statusIndicator.className = `status-indicator status-${status}`;
        }
        
        if (connectionText) {
            const statusMessages = {
                'connected': 'Production Connected ✅',
                'disconnected': 'Disconnected ❌',
                'connecting': 'Connecting... 🔄',
                'error': 'Connection Error ❌',
                'failed': 'Connection Failed ❌'
            };
            
            connectionText.textContent = statusMessages[status] || 'Unknown Status';
            connectionText.className = status === 'connected' ? 'green' : 'red';
        }

        // Update live indicator if available
        if (window.updateLiveIndicator) {
            window.updateLiveIndicator(status);
        }
    }

    function handleWelcomeMessage(data) {
        console.log("🎉 PRODUCTION: Connected to FVG Scanner", data.server_version);
        
        // Update UI with server information
        if (data.environment) {
            console.log(`🌍 Environment: ${data.environment}`);
        }
        
        if (data.features) {
            console.log("✅ Features available:", Object.keys(data.features));
        }
    }

    function handleHeartbeat(data) {
        // Update connection statistics if UI elements exist
        if (data.server_stats) {
            console.log(`📊 Server stats: ${data.server_stats.active_clients} clients, ${data.server_stats.uptime_seconds}s uptime`);
        }
    }

    function handlePriceUpdate(data) {
        // Handle real-time price updates
        if (data.pair && data.current_price) {
            console.log(`💰 Price update: ${data.pair} = ${data.current_price}`);
            
            // Update price in table if visible
            updatePriceInTable(data.pair, data.current_price);
        }
    }

    function handleFVGData(data) {
        // Handle FVG data
        console.log(`📊 FVG data: ${data.pair} ${data.tf} ${data.type}`);
        
        // Add to FVG data array if main script is loaded
        if (window.fvgData && Array.isArray(window.fvgData)) {
            window.fvgData.unshift(data);
            
            // Trigger UI update if function exists
            if (window.filterAndDisplayData) {
                window.filterAndDisplayData();
            }
        }
    }

    function updatePriceInTable(pair, newPrice) {
        try {
            const tbody = document.getElementById('fvgTableBody');
            if (!tbody) return;

            // Find rows for this pair and update prices
            Array.from(tbody.children).forEach(row => {
                if (row.cells && row.cells[0] && row.cells[0].textContent.includes(pair)) {
                    const priceCell = row.cells[5]; // Current price column
                    if (priceCell) {
                        priceCell.textContent = parseFloat(newPrice).toFixed(6);
                        
                        // Add visual feedback
                        priceCell.style.backgroundColor = 'rgba(0, 255, 136, 0.5)';
                        setTimeout(() => {
                            priceCell.style.backgroundColor = '';
                        }, 500);
                    }
                }
            });
        } catch (error) {
            console.error("❌ Error updating price in table:", error);
        }
    }

    // PRODUCTION: Manual reconnection function
    window.reconnectWebSocket = function() {
        console.log("🔄 PRODUCTION: Manual reconnection triggered");
        reconnectAttempts = 0;
        reconnectDelay = 1000;
        updateConnectionStatus('connecting');
        connectWebSocket();
    };

    // PRODUCTION: Connection status check
    window.getConnectionStatus = function() {
        return {
            connected: isConnected,
            readyState: ws ? ws.readyState : -1,
            reconnectAttempts: reconnectAttempts,
            url: ws ? ws.url : null
        };
    };

    // PRODUCTION: Environment detection
    window.getEnvironmentInfo = function() {
        return {
            isProduction: window.PRODUCTION_CONFIG?.isProduction || false,
            environment: window.PRODUCTION_CONFIG?.environment || 'development',
            websocketUrl: getWebSocketURL(),
            host: location.hostname,
            protocol: location.protocol
        };
    };

    // PRODUCTION: Initialize connection on page load
    console.log("🚀 PRODUCTION: Initializing WebSocket connection...");
    updateConnectionStatus('connecting');
    connectWebSocket();

    // PRODUCTION: Handle page visibility changes
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible' && !isConnected) {
            console.log("👁️ PRODUCTION: Page became visible, checking connection...");
            connectWebSocket();
        }
    });

    // PRODUCTION: Handle online/offline events
    window.addEventListener('online', function() {
        console.log("🌐 PRODUCTION: Network came online, reconnecting...");
        connectWebSocket();
    });

    window.addEventListener('offline', function() {
        console.log("📴 PRODUCTION: Network went offline");
        updateConnectionStatus('disconnected');
    });

    // PRODUCTION: Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        if (ws) {
            ws.close(1000, 'Page unloading');
        }
        stopHeartbeat();
    });

    console.log("✅ PRODUCTION: WebSocket client initialization complete");
});