// COMPLETE SCRIPT.JS - PRODUCTION READY WITH FULL UI LOGIC
// ✅ PRODUCTION: WebSocket Auto-Detection for Railway
// ✅ COMPLETE: Full FVG data processing and display
// ✅ FIXED: All UI elements now work with incoming data
// 🚀 RAILWAY: Replace your current script.js with this file

document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 PRODUCTION: FVG Scanner with Auto WebSocket Detection");
    
    // ========== GLOBAL VARIABLES ==========
    
    // WebSocket variables
    let ws;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 10;
    let reconnectDelay = 1000;
    let isConnected = false;
    let heartbeatInterval;
    let isPaused = false;
    
    // FVG Data Storage
    window.fvgData = [];
    window.selectedTimeframes = new Set(['4h', '12h', '1d', '1w']);
    
    // Progress tracking
    let progressData = {
        scanned: 0,
        remaining: 450,
        total: 450
    };
    
    // Current sort configuration
    let currentSort = {
        column: 'distance_pct',
        direction: 'asc'
    };
    
    // Statistics tracking
    let stats = {
        totalFVGs: 0,
        bullishFVGs: 0,
        bearishFVGs: 0,
        touchingFVGs: 0,
        extremeVolumeCount: 0,
        highVolumeCount: 0,
        extremeOrdersCount: 0,
        strongOrdersCount: 0,
        mediumOrdersCount: 0,
        institutionalCount: 0,
        avgPowerScore: 0,
        totalUnfilledOrders: 0
    };
    
    // ========== WEBSOCKET FUNCTIONS ==========
    
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
                reconnectDelay = 1000;
                
                updateConnectionStatus('connected');
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
                        // FVG data - this is the key fix!
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
                
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    console.log(`🔄 PRODUCTION: Reconnection attempt ${reconnectAttempts}/${maxReconnectAttempts} in ${reconnectDelay}ms`);
                    
                    setTimeout(() => {
                        connectWebSocket();
                    }, reconnectDelay);
                    
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
        heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                console.log("💓 PRODUCTION: WebSocket heartbeat check - OK");
            } else {
                console.warn("⚠️ PRODUCTION: WebSocket connection lost, attempting reconnect");
                connectWebSocket();
            }
        }, 60000);
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
    }

    function handleWelcomeMessage(data) {
        console.log("🎉 PRODUCTION: Connected to FVG Scanner", data.server_version);
        
        if (data.environment) {
            console.log(`🌍 Environment: ${data.environment}`);
        }
        
        if (data.features) {
            console.log("✅ Features available:", Object.keys(data.features));
        }
    }

    function handleHeartbeat(data) {
        if (data.server_stats) {
            console.log(`📊 Server stats: ${data.server_stats.active_clients} clients, ${data.server_stats.uptime_seconds}s uptime`);
        }
    }

    function handlePriceUpdate(data) {
        if (data.pair && data.current_price) {
            console.log(`💰 Price update: ${data.pair} = ${data.current_price}`);
            updatePriceInTable(data.pair, data.current_price);
        }
    }

    // ========== FIXED FVG DATA HANDLER ==========
    function handleFVGData(data) {
        console.log(`📊 FVG data: ${data.pair} ${data.tf} ${data.type}`);
        
        // Add to FVG data array
        window.fvgData.unshift(data);
        
        // Update progress
        progressData.scanned++;
        progressData.remaining = Math.max(0, progressData.total - progressData.scanned);
        updateProgressDisplay();
        
        // Filter and display if not paused
        if (!isPaused) {
            window.filterAndDisplayData();
        }
    }

    function updatePriceInTable(pair, newPrice) {
        try {
            const tbody = document.getElementById('fvgTableBody');
            if (!tbody) return;

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

    // ========== UI UPDATE FUNCTIONS ==========
    
    function updateProgressDisplay() {
        const scannedElement = document.getElementById('scannedCount');
        const remainingElement = document.getElementById('remainingCount');
        const totalElement = document.getElementById('totalCount');
        const progressFill = document.getElementById('progressFill');
        
        if (scannedElement) scannedElement.textContent = progressData.scanned;
        if (remainingElement) remainingElement.textContent = progressData.remaining;
        if (totalElement) totalElement.textContent = progressData.total;
        
        if (progressFill) {
            const percentage = (progressData.scanned / progressData.total) * 100;
            progressFill.style.width = `${Math.min(percentage, 100)}%`;
        }
    }

    // ========== MAIN FILTERING AND DISPLAY FUNCTION ==========
    window.filterAndDisplayData = function() {
        if (!window.fvgData || window.fvgData.length === 0) {
            showNoDataMessage();
            return;
        }
        
        // Get filter values
        const maxDistance = parseFloat(document.getElementById('maxDistance')?.value || 20);
        const fvgFilter = document.getElementById('fvgFilter')?.value || 'all';
        const showTestData = document.getElementById('showTestData')?.checked || false;
        const dynamicFiltering = document.getElementById('dynamicFilteringCheckbox')?.checked !== false;
        
        // Filter data
        let filteredData = window.fvgData.filter(fvg => {
            // Timeframe filter
            if (!window.selectedTimeframes.has(fvg.tf)) {
                return false;
            }
            
            // Distance filter
            if (dynamicFiltering && fvg.distance_pct > maxDistance) {
                return false;
            }
            
            // Type filter
            if (fvgFilter === 'bullish' && fvg.type !== 'Bullish') return false;
            if (fvgFilter === 'bearish' && fvg.type !== 'Bearish') return false;
            if (fvgFilter === 'touching' && !fvg.is_touching) return false;
            if (fvgFilter === 'historical' && !fvg.is_historical) return false;
            if (fvgFilter === 'new' && fvg.is_historical) return false;
            if (fvgFilter === 'tested' && !fvg.tested) return false;
            if (fvgFilter === 'untested' && fvg.tested) return false;
            if (fvgFilter === 'extreme_orders' && fvg.strength_level !== 'EXTREME') return false;
            if (fvgFilter === 'strong_orders' && fvg.strength_level !== 'STRONG') return false;
            if (fvgFilter === 'institutional' && !fvg.institutional_size) return false;
            if (fvgFilter === 'blocks' && !fvg.is_block_member) return false;
            if (fvgFilter === 'extreme_blocks' && (!fvg.is_block_member || fvg.block_strength !== 'EXTREME')) return false;
            if (fvgFilter === 'strong_blocks' && (!fvg.is_block_member || fvg.block_strength !== 'STRONG')) return false;
            
            // Test data filter
            if (!showTestData && fvg.test_data) return false;
            
            return true;
        });
        
        // Sort data
        sortData(filteredData);
        
        // Update statistics
        updateStatistics(filteredData);
        
        // Display data
        displayFVGTable(filteredData);
        
        // Hide no data message
        const noDataMessage = document.getElementById('noDataMessage');
        if (noDataMessage) {
            noDataMessage.style.display = filteredData.length === 0 ? 'block' : 'none';
        }
    };

    function sortData(data) {
        data.sort((a, b) => {
            let aVal = a[currentSort.column];
            let bVal = b[currentSort.column];
            
            // Handle numeric sorting
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return currentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
            }
            
            // Handle string sorting
            aVal = String(aVal || '').toLowerCase();
            bVal = String(bVal || '').toLowerCase();
            
            if (currentSort.direction === 'asc') {
                return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
            } else {
                return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
            }
        });
    }

    function updateStatistics(data) {
        // Reset stats
        stats = {
            totalFVGs: data.length,
            bullishFVGs: 0,
            bearishFVGs: 0,
            touchingFVGs: 0,
            extremeVolumeCount: 0,
            highVolumeCount: 0,
            extremeOrdersCount: 0,
            strongOrdersCount: 0,
            mediumOrdersCount: 0,
            institutionalCount: 0,
            avgPowerScore: 0,
            totalUnfilledOrders: 0
        };
        
        let totalPowerScore = 0;
        let totalUnfilled = 0;
        
        data.forEach(fvg => {
            // Type counts
            if (fvg.type === 'Bullish') stats.bullishFVGs++;
            if (fvg.type === 'Bearish') stats.bearishFVGs++;
            if (fvg.is_touching) stats.touchingFVGs++;
            
            // Volume counts
            if (fvg.volume_tier === 'EXTREME') stats.extremeVolumeCount++;
            if (fvg.volume_tier === 'HIGH') stats.highVolumeCount++;
            
            // Order strength counts
            if (fvg.strength_level === 'EXTREME') stats.extremeOrdersCount++;
            if (fvg.strength_level === 'STRONG') stats.strongOrdersCount++;
            if (fvg.strength_level === 'MEDIUM') stats.mediumOrdersCount++;
            
            // Institutional count
            if (fvg.institutional_size) stats.institutionalCount++;
            
            // Power score and unfilled orders
            totalPowerScore += fvg.power_score || 0;
            totalUnfilled += fvg.unfilled_orders || 0;
        });
        
        stats.avgPowerScore = data.length > 0 ? Math.round(totalPowerScore / data.length) : 0;
        stats.totalUnfilledOrders = formatUnfilledOrders(totalUnfilled);
        
        // Update UI
        updateStatisticsDisplay();
    }

    function updateStatisticsDisplay() {
        const elements = {
            'totalFVGs': stats.totalFVGs,
            'bullishFVGs': stats.bullishFVGs,
            'bearishFVGs': stats.bearishFVGs,
            'touchingFVGs': stats.touchingFVGs,
            'extremeVolumeCount': stats.extremeVolumeCount,
            'highVolumeCount': stats.highVolumeCount,
            'extremeOrdersCount': stats.extremeOrdersCount,
            'strongOrdersCount': stats.strongOrdersCount,
            'mediumOrdersCount': stats.mediumOrdersCount,
            'institutionalCount': stats.institutionalCount,
            'avgPowerScore': stats.avgPowerScore,
            'totalUnfilledOrders': stats.totalUnfilledOrders
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    function displayFVGTable(data) {
        const tbody = document.getElementById('fvgTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        data.forEach(fvg => {
            const row = createFVGRow(fvg);
            tbody.appendChild(row);
        });
    }

    function createFVGRow(fvg) {
        const row = document.createElement('tr');
        row.className = 'enhanced-row';
        
        // Add border color based on type
        if (fvg.type === 'Bullish') {
            row.classList.add('border-green');
        } else if (fvg.type === 'Bearish') {
            row.classList.add('border-red');
        }
        
        // Add priority styling for touching FVGs
        if (fvg.is_touching) {
            row.classList.add('touching-priority');
        }
        
        row.innerHTML = `
            <td>
                <strong>${fvg.pair}</strong>
                ${fvg.is_block_member ? `<br><span style="color: #00ff88; font-size: 0.8rem;">${fvg.block_badge}</span>` : ''}
                ${fvg.institutional_marker ? `<br><span style="color: #8b5cf6;">${fvg.institutional_marker} Institutional</span>` : ''}
            </td>
            <td>
                <span class="timeframe-strength strength-${getTimeframeStrengthClass(fvg.tf)}">${fvg.tf}</span>
            </td>
            <td>
                <span class="${fvg.type === 'Bullish' ? 'green' : 'red'}">${fvg.type}</span>
            </td>
            <td>${parseFloat(fvg.gap_low || 0).toFixed(6)}</td>
            <td>${parseFloat(fvg.gap_high || 0).toFixed(6)}</td>
            <td>${parseFloat(fvg.current_price || 0).toFixed(6)}</td>
            <td>
                <strong class="${getDistanceColor(fvg.distance_pct)}">${fvg.distance_pct}%</strong>
                ${fvg.is_touching ? '<span class="priority-badge">TOUCHING</span>' : ''}
            </td>
            <td>
                ${formatVolume(fvg.volume_strength || 0)}
                ${getVolumeBadge(fvg.volume_tier)}
            </td>
            <td>${fvg.volume_ratio || 1.0}x</td>
            <td>
                <strong>${fvg.unfilled_orders_formatted || '0'}</strong>
                ${fvg.strength_emoji} ${fvg.strength_level}
                <br><small>Power: ${fvg.power_score || 0}/100</small>
            </td>
            <td>
                ${fvg.tested ? '✅ Tested' : '⭕ Untested'}
                ${fvg.is_touching ? '<br><span class="priority-badge">TOUCHING</span>' : ''}
                ${fvg.is_historical ? '<span class="historical-badge">Historical</span>' : '<span class="new-badge">New</span>'}
            </td>
            <td>
                <small>${formatTime(fvg.time || fvg.timestamp)}</small>
            </td>
        `;
        
        return row;
    }

    // ========== HELPER FUNCTIONS ==========
    
    function getTimeframeStrengthClass(tf) {
        const strengthMap = {
            '4h': 'medium',
            '12h': 'strong', 
            '1d': 'very-strong',
            '1w': 'institutional'
        };
        return strengthMap[tf] || 'medium';
    }

    function getDistanceColor(distance) {
        if (distance === 0) return 'purple';
        if (distance < 1) return 'red';
        if (distance < 5) return 'yellow';
        if (distance < 15) return 'green';
        return 'gray';
    }

    function getVolumeBadge(tier) {
        const badges = {
            'EXTREME': '<span class="volume-badge-extreme">EXTREME</span>',
            'HIGH': '<span class="volume-badge-high">HIGH</span>',
            'MEDIUM': '<span class="volume-badge-medium">MED</span>',
            'LOW': '<span class="volume-badge-low">LOW</span>'
        };
        return badges[tier] || '';
    }

    function formatVolume(volume) {
        if (volume >= 1000000000) {
            return `${(volume / 1000000000).toFixed(1)}B`;
        } else if (volume >= 1000000) {
            return `${(volume / 1000000).toFixed(1)}M`;
        } else if (volume >= 1000) {
            return `${(volume / 1000).toFixed(1)}K`;
        }
        return volume.toString();
    }

    function formatUnfilledOrders(orders) {
        if (orders >= 1000000000) {
            return `${(orders / 1000000000).toFixed(1)}B`;
        } else if (orders >= 1000000) {
            return `${(orders / 1000000).toFixed(1)}M`;
        } else if (orders >= 1000) {
            return `${(orders / 1000).toFixed(0)}K`;
        }
        return orders.toString();
    }

    function formatTime(timestamp) {
        if (!timestamp) return 'Unknown';
        const date = new Date(typeof timestamp === 'string' ? timestamp : timestamp * 1000);
        return date.toLocaleString();
    }

    function showNoDataMessage() {
        const noDataMessage = document.getElementById('noDataMessage');
        if (noDataMessage) {
            noDataMessage.style.display = 'block';
        }
    }

    // ========== EVENT HANDLERS ==========
    
    // Timeframe checkboxes
    document.querySelectorAll('.timeframe-check').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                window.selectedTimeframes.add(this.value);
            } else {
                window.selectedTimeframes.delete(this.value);
            }
            console.log(`🔄 Timeframe ${this.value} ${this.checked ? 'enabled' : 'disabled'}`);
            window.filterAndDisplayData();
        });
    });
    
    // Filter controls
    const maxDistanceInput = document.getElementById('maxDistance');
    if (maxDistanceInput) {
        maxDistanceInput.addEventListener('input', function() {
            console.log(`🔄 Distance filter changed to ${this.value}%`);
            window.filterAndDisplayData();
        });
    }
    
    const fvgFilterSelect = document.getElementById('fvgFilter');
    if (fvgFilterSelect) {
        fvgFilterSelect.addEventListener('change', function() {
            console.log(`🔄 FVG filter changed to ${this.value}`);
            window.filterAndDisplayData();
        });
    }
    
    const showTestDataCheck = document.getElementById('showTestData');
    if (showTestDataCheck) {
        showTestDataCheck.addEventListener('change', function() {
            console.log(`🔄 Test data ${this.checked ? 'enabled' : 'disabled'}`);
            window.filterAndDisplayData();
        });
    }
    
    const dynamicFilteringCheck = document.getElementById('dynamicFilteringCheckbox');
    if (dynamicFilteringCheck) {
        dynamicFilteringCheck.addEventListener('change', function() {
            console.log(`🔄 Dynamic filtering ${this.checked ? 'enabled' : 'disabled'}`);
            window.filterAndDisplayData();
        });
    }
    
    // Button handlers
    const pauseBtn = document.getElementById('pauseBtn');
    if (pauseBtn) {
        pauseBtn.addEventListener('click', function() {
            isPaused = !isPaused;
            this.textContent = isPaused ? '▶️ Resume' : '⏸ Pause';
            this.className = isPaused ? 'btn-green' : 'btn-blue';
            console.log(`🔄 Scanner ${isPaused ? 'paused' : 'resumed'}`);
        });
    }
    
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            window.fvgData = [];
            progressData = { scanned: 0, remaining: 450, total: 450 };
            updateProgressDisplay();
            window.filterAndDisplayData();
            console.log('🔄 Data cleared');
        });
    }
    
    const reconnectBtn = document.getElementById('reconnectBtn');
    if (reconnectBtn) {
        reconnectBtn.addEventListener('click', function() {
            console.log('🔄 Manual reconnect triggered');
            reconnectAttempts = 0;
            reconnectDelay = 1000;
            updateConnectionStatus('connecting');
            connectWebSocket();
        });
    }
    
    const toggleDebugBtn = document.getElementById('toggleDebug');
    if (toggleDebugBtn) {
        toggleDebugBtn.addEventListener('click', function() {
            const debugLog = document.getElementById('debugLog');
            if (debugLog) {
                debugLog.classList.toggle('hidden');
                console.log('🔄 Debug log toggled');
            }
        });
    }
    
    // Table sorting
    document.querySelectorAll('th[data-sort]').forEach(header => {
        header.addEventListener('click', function() {
            const column = this.dataset.sort;
            
            if (currentSort.column === column) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.column = column;
                currentSort.direction = 'asc';
            }
            
            // Update sort indicators
            document.querySelectorAll('th[data-sort]').forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            
            this.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            
            console.log(`🔄 Sorting by ${column} (${currentSort.direction})`);
            window.filterAndDisplayData();
        });
    });

    // ========== PRODUCTION FUNCTIONS ==========
    
    // Manual reconnection function
    window.reconnectWebSocket = function() {
        console.log("🔄 PRODUCTION: Manual reconnection triggered");
        reconnectAttempts = 0;
        reconnectDelay = 1000;
        updateConnectionStatus('connecting');
        connectWebSocket();
    };

    // Connection status check
    window.getConnectionStatus = function() {
        return {
            connected: isConnected,
            readyState: ws ? ws.readyState : -1,
            reconnectAttempts: reconnectAttempts,
            url: ws ? ws.url : null
        };
    };

    // Environment detection
    window.getEnvironmentInfo = function() {
        return {
            isProduction: window.PRODUCTION_CONFIG?.isProduction || false,
            environment: window.PRODUCTION_CONFIG?.environment || 'development',
            websocketUrl: getWebSocketURL(),
            host: location.hostname,
            protocol: location.protocol
        };
    };

    // ========== INITIALIZE APPLICATION ==========
    
    console.log("🚀 PRODUCTION: Initializing WebSocket connection...");
    updateConnectionStatus('connecting');
    connectWebSocket();

    // Handle page visibility changes
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible' && !isConnected) {
            console.log("👁️ PRODUCTION: Page became visible, checking connection...");
            connectWebSocket();
        }
    });

    // Handle online/offline events
    window.addEventListener('online', function() {
        console.log("🌐 PRODUCTION: Network came online, reconnecting...");
        connectWebSocket();
    });

    window.addEventListener('offline', function() {
        console.log("📴 PRODUCTION: Network went offline");
        updateConnectionStatus('disconnected');
    });

    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        if (ws) {
            ws.close(1000, 'Page unloading');
        }
        stopHeartbeat();
    });

    console.log("✅ PRODUCTION: WebSocket client initialization complete");
});
