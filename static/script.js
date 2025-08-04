// 🚀 PRODUCTION SCRIPT.JS - Pine Script FVG Scanner
// ✅ PRODUCTION: Automatic environment detection
// ✅ PRODUCTION: Proper WebSocket URL handling  
// ✅ PRODUCTION: Pine Script proximity logic
// ✅ RAILWAY: Optimized for Railway deployment
// 🔧 FIXED: All message types (enhanced_fvg, stats, connection)

document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 PRODUCTION: FVG Scanner with Pine Script Logic initializing...");
    
    // Global variables
    window.fvgData = [];
    window.ws = null;
    window.isConnected = false;
    window.isScanning = false;
    window.pineSettings = {
        proximityFilter: 1.0,  // Default 1.0% like Pine Script
        showBlocks: true,
        showTouched: true,
        alertsEnabled: true
    };
    
    // Statistics tracking
    window.stats = {
        totalPairs: 0,
        scannedPairs: 0,
        totalFVGs: 0,
        bullishFVGs: 0,
        bearishFVGs: 0,
        institutionalBlocks: 0,
        touchedFVGs: 0
    };
    
    // Initialize WebSocket connection
    function initializeWebSocket() {
        console.log("🚀 PRODUCTION: Initializing WebSocket connection...");
        
        // Auto-detect WebSocket URL based on environment
        let wsUrl;
        const currentHost = window.location.host;
        
        if (currentHost.includes('railway.app')) {
            wsUrl = `wss://${currentHost}/ws`;
            console.log("🚂 RAILWAY: Detected Railway deployment -", wsUrl);
        } else if (currentHost.includes('localhost') || currentHost.includes('127.0.0.1')) {
            wsUrl = `ws://${currentHost}/ws`;
            console.log("🏠 LOCAL: Detected local development -", wsUrl);
        } else {
            // Production fallback
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            wsUrl = `${protocol}//${currentHost}/ws`;
            console.log("🌐 PRODUCTION: Auto-detected WebSocket URL -", wsUrl);
        }
        
        connectWebSocket(wsUrl);
    }
    
    // WebSocket connection function
    function connectWebSocket(url) {
        console.log("🔗 PRODUCTION: Connecting to", url);
        
        try {
            window.ws = new WebSocket(url);
            
            window.ws.onopen = function(event) {
                console.log("✅ PRODUCTION: WebSocket connected successfully");
                window.isConnected = true;
                updateConnectionStatus(true);
                
                // Send ping every 30 seconds to keep connection alive (Railway requirement)
                setInterval(() => {
                    if (window.ws && window.ws.readyState === WebSocket.OPEN) {
                        window.ws.send(JSON.stringify({ type: 'ping' }));
                    }
                }, 30000);
            };
            
            window.ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                } catch (error) {
                    console.error("❌ Error parsing WebSocket message:", error);
                }
            };
            
            window.ws.onclose = function(event) {
                console.log("❌ PRODUCTION: WebSocket connection closed:", event.code, event.reason);
                window.isConnected = false;
                updateConnectionStatus(false);
                
                // Attempt to reconnect after 5 seconds
                setTimeout(() => {
                    console.log("🔄 PRODUCTION: Attempting to reconnect...");
                    connectWebSocket(url);
                }, 5000);
            };
            
            window.ws.onerror = function(error) {
                console.error("❌ PRODUCTION: WebSocket error:", error);
                updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error("❌ PRODUCTION: Failed to create WebSocket connection:", error);
            updateConnectionStatus(false);
        }
    }
    
    // Handle WebSocket messages
    function handleWebSocketMessage(data) {
        console.log("📨 Message type:", data.type);
        
        switch (data.type) {
            case 'connection_established':
            case 'connection':  // Handle both connection types
                console.log("🎉 PRODUCTION: Connection established -", data.message || 'Connected');
                if (data.stats) {
                    window.stats = data.stats;
                    updateStatistics();
                }
                if (data.settings) {
                    window.pineSettings = { ...window.pineSettings, ...data.settings };
                    updateSettingsUI();
                }
                break;
                
            case 'fvg_data':
                // Handle direct FVG data (data is the FVG object itself)
                handleFVGData(data);
                break;
                
            case 'enhanced_fvg':
                // Handle enhanced FVG data (data is the FVG object itself)
                console.log("🔧 Processing enhanced FVG:", data.pair, data.timeframe, data.fvg_type);
                handleFVGData(data);
                break;
                
            case 'stats_update':
            case 'stats':  // Handle both stats types
                console.log("📊 Updating statistics:", data);
                if (data.stats) {
                    window.stats = data.stats;
                } else {
                    // Stats might be at root level
                    window.stats = {
                        totalPairs: data.total_pairs || window.stats.totalPairs,
                        scannedPairs: data.scanned_pairs || window.stats.scannedPairs,
                        totalFVGs: data.total_fvgs || window.stats.totalFVGs,
                        bullishFVGs: data.bullish_fvgs || window.stats.bullishFVGs,
                        bearishFVGs: data.bearish_fvgs || window.stats.bearishFVGs,
                        institutionalBlocks: data.institutional_blocks || window.stats.institutionalBlocks,
                        touchedFVGs: data.touched_fvgs || window.stats.touchedFVGs
                    };
                }
                updateStatistics();
                break;
                
            case 'scan_status':
                handleScanStatus(data);
                break;
                
            case 'settings_updated':
                if (data.settings) {
                    window.pineSettings = { ...window.pineSettings, ...data.settings };
                    updateSettingsUI();
                }
                break;
                
            case 'pong':
                console.log("🏓 Ping-pong successful");
                break;
                
            default:
                console.log("📊 Unhandled message type:", data.type, data);
        }
    }
    
    // Handle FVG data with Pine Script logic
    function handleFVGData(data) {
        if (!data) return;
        
        console.log("📊 Processing FVG data:", data.pair, data.timeframe || data.tf, data.fvg_type);
        
        // Ensure all required fields have valid values
        const safeFVG = {
            pair: data.pair || 'UNKNOWN',
            timeframe: data.timeframe || data.tf || '1h',
            type: data.fvg_type || data.type || 'Unknown',
            gap_low: Number(data.gap_low) || 0,
            gap_high: Number(data.gap_high) || 0,
            gap_size: Number(data.gap_size) || 0,
            distance_percentage: Number(data.distance_percentage) || 0,
            is_within_proximity: Boolean(data.is_within_proximity),
            is_touched: Boolean(data.is_touched),
            volume_strength: Number(data.volume_strength) || 0,
            unfilled_orders: Number(data.unfilled_orders) || 0,
            unfilled_orders_formatted: data.unfilled_orders_formatted || formatOrders(Number(data.unfilled_orders) || 0),
            power_score: Number(data.power_score) || 0,
            strength: Number(data.strength) || 0,
            timestamp: data.timestamp || new Date().toISOString(),
            is_block_member: Boolean(data.is_block_member),
            block_badge: data.block_badge || '',
            block_id: data.block_id || null
        };
        
        // Create enhanced FVG entry with Pine Script features
        const fvgEntry = {
            id: `${safeFVG.pair}_${safeFVG.timeframe}_${Date.now()}_${Math.random()}`,
            ...safeFVG,
            
            // Pine Script specific fields
            pine_distance: safeFVG.distance_percentage,
            pine_proximity: safeFVG.is_within_proximity,
            pine_touched: safeFVG.is_touched,
            pine_strength: safeFVG.strength
        };
        
        // Add to global data array
        window.fvgData.push(fvgEntry);
        
        // Limit array size for performance (keep last 1000 FVGs)
        if (window.fvgData.length > 1000) {
            window.fvgData = window.fvgData.slice(-1000);
        }
        
        // Check for alerts
        checkFVGAlerts(fvgEntry);
        
        // Update display
        filterAndDisplayData();
        
        console.log("✅ FVG processed and added to display:", fvgEntry.pair, fvgEntry.timeframe, fvgEntry.type);
    }
    
    // Pine Script alert system
    function checkFVGAlerts(fvg) {
        if (!window.pineSettings.alertsEnabled) return;
        
        // Touch alert
        if (fvg.is_touched) {
            showAlert(`🎯 FVG TOUCHED: ${fvg.pair} ${fvg.timeframe} ${fvg.type} FVG`, 'touch');
        }
        
        // Proximity alert
        if (fvg.is_within_proximity && fvg.distance_percentage <= 0.5) {
            showAlert(`⚠️ PROXIMITY: ${fvg.pair} ${fvg.timeframe} ${fvg.type} FVG - ${fvg.distance_percentage}%`, 'proximity');
        }
        
        // Block alert
        if (fvg.is_block_member) {
            showAlert(`🔥 BLOCK DETECTED: ${fvg.block_badge}`, 'block');
        }
    }
    
    // Alert display function
    function showAlert(message, type) {
        console.log(`🚨 ALERT [${type.toUpperCase()}]: ${message}`);
        
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.textContent = message;
        alertDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'touch' ? '#ff4444' : type === 'block' ? '#ff8800' : '#ffaa00'};
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            z-index: 10000;
            font-weight: bold;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(alertDiv);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    // Handle scan status updates
    function handleScanStatus(data) {
        window.isScanning = data.status === 'started';
        updateScanButtons();
        
        if (data.message) {
            console.log("📊 Scan status:", data.message);
        }
    }
    
    // Update connection status display
    function updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = connected ? 'Connected' : 'Disconnected';
            statusElement.className = connected ? 'status-connected' : 'status-disconnected';
        }
        
        const indicator = document.querySelector('.connection-indicator');
        if (indicator) {
            indicator.style.backgroundColor = connected ? '#00ff00' : '#ff0000';
        }
    }
    
    // Update scan button states
    function updateScanButtons() {
        const startBtn = document.getElementById('start-scan');
        const stopBtn = document.getElementById('stop-scan');
        
        if (startBtn) {
            startBtn.disabled = window.isScanning || !window.isConnected;
            startBtn.textContent = window.isScanning ? 'Scanning...' : 'Start Scan';
        }
        
        if (stopBtn) {
            stopBtn.disabled = !window.isScanning;
        }
    }
    
    // Update statistics display
    function updateStatistics() {
        const statElements = {
            'total-pairs': window.stats.totalPairs || 0,
            'scanned-pairs': window.stats.scannedPairs || 0,
            'total-fvgs': window.stats.totalFVGs || 0,
            'bullish-fvgs': window.stats.bullishFVGs || 0,
            'bearish-fvgs': window.stats.bearishFVGs || 0,
            'institutional-blocks': window.stats.institutionalBlocks || 0,
            'touched-fvgs': window.stats.touchedFVGs || 0
        };
        
        Object.entries(statElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
        
        // Update progress
        const remainingPairs = Math.max(0, window.stats.totalPairs - window.stats.scannedPairs);
        const remainingElement = document.getElementById('remaining-pairs');
        if (remainingElement) {
            remainingElement.textContent = remainingPairs;
        }
        
        // Update progress bar
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar && window.stats.totalPairs > 0) {
            const progress = (window.stats.scannedPairs / window.stats.totalPairs) * 100;
            progressBar.style.width = `${progress}%`;
        }
    }
    
    // Update settings UI
    function updateSettingsUI() {
        const proximityInput = document.getElementById('proximity-filter');
        if (proximityInput) {
            proximityInput.value = window.pineSettings.proximityFilter || 1.0;
        }
        
        const showBlocksCheckbox = document.getElementById('show-blocks');
        if (showBlocksCheckbox) {
            showBlocksCheckbox.checked = window.pineSettings.showBlocks !== false;
        }
        
        const alertsCheckbox = document.getElementById('alerts-enabled');
        if (alertsCheckbox) {
            alertsCheckbox.checked = window.pineSettings.alertsEnabled !== false;
        }
    }
    
    // Filter and display FVG data
    window.filterAndDisplayData = function() {
        // Try multiple ways to find the table
        let table = document.getElementById('fvg-table');
        
        if (!table) {
            // Try other common IDs
            table = document.getElementById('fvg_table') || 
                   document.getElementById('fvgTable') || 
                   document.querySelector('table') || 
                   document.querySelector('.fvg-table') ||
                   document.querySelector('[class*="table"]');
        }
        
        if (!table) {
            console.log("❌ No table found for FVG display");
            return;
        }
        
        let tbody = table.querySelector('tbody');
        
        if (!tbody) {
            // Create tbody if it doesn't exist
            tbody = document.createElement('tbody');
            table.appendChild(tbody);
            console.log("📋 Created new tbody for table");
        }
        
        // Clear existing rows
        tbody.innerHTML = '';
        
        // Get filter values (with fallbacks)
        const typeFilter = document.getElementById('type-filter')?.value || 'all';
        const timeframeFilter = document.getElementById('timeframe-filter')?.value || 'all';
        const distanceFilter = parseFloat(document.getElementById('distance-filter')?.value || 100);
        const proximityOnly = document.getElementById('proximity-only')?.checked || false;
        const blocksOnly = document.getElementById('blocks-only')?.checked || false;
        const touchedOnly = document.getElementById('touched-only')?.checked || false;
        
        // Filter data
        let filteredData = window.fvgData.filter(fvg => {
            // Type filter
            if (typeFilter !== 'all' && fvg.type !== typeFilter) return false;
            
            // Timeframe filter
            if (timeframeFilter !== 'all' && fvg.timeframe !== timeframeFilter) return false;
            
            // Distance filter
            if (fvg.distance_percentage > distanceFilter) return false;
            
            // Proximity filter (Pine Script logic)
            if (proximityOnly && !fvg.is_within_proximity) return false;
            
            // Blocks filter
            if (blocksOnly && !fvg.is_block_member) return false;
            
            // Touched filter
            if (touchedOnly && !fvg.is_touched) return false;
            
            return true;
        });
        
        // Sort by distance (closest first)
        filteredData.sort((a, b) => a.distance_percentage - b.distance_percentage);
        
        // Limit display for performance
        filteredData = filteredData.slice(0, 100);
        
        // Create table rows
        filteredData.forEach(fvg => {
            const row = createFVGTableRow(fvg);
            tbody.appendChild(row);
        });
        
        // Update count
        const countElement = document.getElementById('filtered-count');
        if (countElement) {
            countElement.textContent = filteredData.length;
        }
        
        console.log(`📊 Display updated: ${filteredData.length} FVGs shown out of ${window.fvgData.length} total`);
    };
    
    // Create FVG table row
    function createFVGTableRow(fvg) {
        const row = document.createElement('tr');
        
        // Add classes based on FVG properties
        if (fvg.is_touched) row.classList.add('fvg-touched');
        if (fvg.is_block_member) row.classList.add('fvg-block-member');
        if (fvg.is_within_proximity) row.classList.add('fvg-proximity');
        
        // Create row HTML
        row.innerHTML = `
            <td>
                <span class="pair-badge">${fvg.pair}</span>
                ${fvg.is_touched ? '<span class="touch-indicator">🎯</span>' : ''}
            </td>
            <td><span class="timeframe-badge tf-${fvg.timeframe}">${fvg.timeframe}</span></td>
            <td>
                <span class="type-badge type-${fvg.type.toLowerCase()}">${fvg.type}</span>
                ${fvg.is_block_member ? `<div class="block-badge">${fvg.block_badge}</div>` : ''}
            </td>
            <td class="price-cell">
                <div class="gap-range">
                    <div class="gap-high">${formatPrice(fvg.gap_high)}</div>
                    <div class="gap-separator">—</div>
                    <div class="gap-low">${formatPrice(fvg.gap_low)}</div>
                </div>
            </td>
            <td class="distance-cell">
                <span class="distance-badge distance-${getDistanceClass(fvg.distance_percentage)}">
                    ${fvg.distance_percentage.toFixed(2)}%
                </span>
                ${fvg.is_within_proximity ? '<span class="proximity-indicator">📍</span>' : ''}
            </td>
            <td class="volume-cell">${formatVolume(fvg.volume_strength)}</td>
            <td class="orders-cell">${fvg.unfilled_orders_formatted}</td>
            <td class="power-cell">
                <div class="power-score">
                    <span class="score">${fvg.power_score}</span>
                    <span class="score-max">/100</span>
                    <div class="power-bar">
                        <div class="power-fill" style="width: ${fvg.power_score}%"></div>
                    </div>
                </div>
            </td>
            <td class="time-cell" title="${new Date(fvg.timestamp).toLocaleString()}">
                ${formatTimeAgo(fvg.timestamp)}
            </td>
        `;
        
        return row;
    }
    
    // Utility functions
    function formatPrice(price) {
        // Handle undefined, null, or invalid price values
        if (price === undefined || price === null || isNaN(price)) {
            return "0.0000";
        }
        
        const numPrice = Number(price);
        if (numPrice >= 1) {
            return numPrice.toFixed(4);
        } else {
            return numPrice.toFixed(8);
        }
    }
    
    function formatVolume(volume) {
        // Handle undefined, null, or invalid volume values
        if (volume === undefined || volume === null || isNaN(volume)) {
            return "0";
        }
        
        const numVolume = Number(volume);
        if (numVolume >= 1_000_000_000) {
            return `${(numVolume / 1_000_000_000).toFixed(1)}B`;
        } else if (numVolume >= 1_000_000) {
            return `${(numVolume / 1_000_000).toFixed(1)}M`;
        } else if (numVolume >= 1_000) {
            return `${(numVolume / 1_000).toFixed(1)}K`;
        } else {
            return Math.floor(numVolume).toString();
        }
    }
    
    function formatOrders(orders) {
        // Handle undefined, null, or invalid order values
        if (orders === undefined || orders === null || isNaN(orders)) {
            return "0";
        }
        
        const numOrders = Number(orders);
        if (numOrders >= 1_000_000) {
            return `${(numOrders / 1_000_000).toFixed(1)}M`;
        } else if (numOrders >= 1_000) {
            return `${(numOrders / 1_000).toFixed(1)}K`;
        } else {
            return Math.floor(numOrders).toString();
        }
    }
    
    function getDistanceClass(distance) {
        if (distance === undefined || distance === null || isNaN(distance)) {
            return 'unknown';
        }
        
        const numDistance = Number(distance);
        if (numDistance <= 0.5) return 'very-close';
        if (numDistance <= 1.0) return 'close';
        if (numDistance <= 2.0) return 'medium';
        if (numDistance <= 5.0) return 'far';
        return 'very-far';
    }
    
    function formatTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
    }
    
    // Button event handlers
    document.getElementById('start-scan')?.addEventListener('click', function() {
        if (window.ws && window.ws.readyState === WebSocket.OPEN) {
            window.ws.send(JSON.stringify({ type: 'start_scan' }));
            console.log("🚀 PRODUCTION: Start scan command sent");
        }
    });
    
    document.getElementById('stop-scan')?.addEventListener('click', function() {
        if (window.ws && window.ws.readyState === WebSocket.OPEN) {
            window.ws.send(JSON.stringify({ type: 'stop_scan' }));
            console.log("⏹️ PRODUCTION: Stop scan command sent");
        }
    });
    
    document.getElementById('clear-data')?.addEventListener('click', function() {
        window.fvgData = [];
        filterAndDisplayData();
        console.log("🗑️ PRODUCTION: Data cleared");
    });
    
    document.getElementById('reconnect')?.addEventListener('click', function() {
        if (window.ws) {
            window.ws.close();
        }
        setTimeout(initializeWebSocket, 1000);
        console.log("🔄 PRODUCTION: Reconnection initiated");
    });
    
    // Filter event handlers
    document.getElementById('type-filter')?.addEventListener('change', filterAndDisplayData);
    document.getElementById('timeframe-filter')?.addEventListener('change', filterAndDisplayData);
    document.getElementById('distance-filter')?.addEventListener('input', filterAndDisplayData);
    document.getElementById('proximity-only')?.addEventListener('change', filterAndDisplayData);
    document.getElementById('blocks-only')?.addEventListener('change', filterAndDisplayData);
    document.getElementById('touched-only')?.addEventListener('change', filterAndDisplayData);
    
    // Settings event handlers
    document.getElementById('proximity-filter')?.addEventListener('change', function() {
        const value = parseFloat(this.value) || 1.0;
        window.pineSettings.proximityFilter = value;
        
        if (window.ws && window.ws.readyState === WebSocket.OPEN) {
            window.ws.send(JSON.stringify({
                type: 'update_settings',
                settings: { proximityFilter: value }
            }));
        }
    });
    
    document.getElementById('show-blocks')?.addEventListener('change', function() {
        window.pineSettings.showBlocks = this.checked;
        filterAndDisplayData();
    });
    
    document.getElementById('alerts-enabled')?.addEventListener('change', function() {
        window.pineSettings.alertsEnabled = this.checked;
    });
    
    // Debug functions for console
    window.debugFVGData = function() {
        console.log("🔍 CURRENT FVG DATA:", window.fvgData);
        console.log("📊 STATISTICS:", window.stats);
        console.log("⚙️ SETTINGS:", window.pineSettings);
        console.log("🔗 CONNECTION:", window.isConnected ? 'Connected' : 'Disconnected');
        console.log("🚀 SCANNING:", window.isScanning ? 'Active' : 'Inactive');
        console.log("📈 TOTAL FVGs RECEIVED:", window.fvgData.length);
        
        if (window.fvgData.length > 0) {
            console.log("📊 LATEST FVG:", window.fvgData[window.fvgData.length - 1]);
        }
    };
    
    window.addSampleData = function() {
        const sampleFVG = {
            id: `SAMPLE_${Date.now()}`,
            pair: 'BTCUSDT',
            timeframe: '4h',
            type: 'Bullish',
            gap_low: 95000,
            gap_high: 96000,
            gap_size: 1000,
            distance_percentage: 0.75,
            is_within_proximity: true,
            is_touched: false,
            volume_strength: 25000000,
            unfilled_orders: 5000000,
            unfilled_orders_formatted: '5.0M',
            power_score: 85,
            strength: 85,
            timestamp: new Date().toISOString(),
            is_block_member: true,
            block_badge: '🔥 BULLISH BLOCK 4h (STRONG)',
            block_id: 'BTCUSDT_4h_001'
        };
        
        window.fvgData.push(sampleFVG);
        filterAndDisplayData();
        console.log("📊 Sample FVG data added");
    };
    
    window.getConnectionStatus = function() {
        return {
            connected: window.isConnected,
            scanning: window.isScanning,
            dataCount: window.fvgData.length,
            wsState: window.ws ? window.ws.readyState : 'No WebSocket',
            lastFVG: window.fvgData.length > 0 ? window.fvgData[window.fvgData.length - 1] : null
        };
    };
    
    // Initialize everything
    initializeWebSocket();
    updateScanButtons();
    updateStatistics();
    
    console.log("✅ PRODUCTION: Pine Script FVG Scanner client initialization complete");
    console.log("🔧 Available debug functions: debugFVGData(), addSampleData(), getConnectionStatus()");
});
