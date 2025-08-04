/**
 * This script ensures all event handlers are properly initialized
 * It runs after both script.js and fix_filters.js and makes sure
 * the buttons and checkboxes work correctly
 */

(function() {
  console.log("🔧 Initializing UI handler fixes...");
  
  // Wait for full DOM load plus scripts
  window.addEventListener('load', function() {
    setTimeout(function() {
      fixAllHandlers();
    }, 500);
  });
  
  function fixAllHandlers() {
    console.log("🛠️ Applying UI element fixes...");
    
    // Fix button handlers
    fixButtonHandler("pauseBtn", function() {
      console.log("🔄 Pause button clicked");
      // Toggle paused state and update button appearance
      const button = document.getElementById("pauseBtn");
      if (button) {
        if (button.innerHTML.includes("Pause")) {
          button.innerHTML = "▶️ Resume";
          button.className = "btn-green";
        } else {
          button.innerHTML = "⏸ Pause";
          button.className = "btn-blue";
        }
      }
      
      // Try to trigger the original handler if available
      if (window.filterAndDisplayData) {
        window.filterAndDisplayData();
      }
    });
    
    fixButtonHandler("clearBtn", function() {
      console.log("🔄 Clear button clicked");
      
      // Clear the table content
      const tbody = document.getElementById("fvgTableBody");
      if (tbody) {
        tbody.innerHTML = "";
      }
      
      // Show no data message
      const noDataMessage = document.getElementById("noDataMessage");
      if (noDataMessage) {
        noDataMessage.style.display = 'block';
      }
      
      // Update statistics to zero
      ["totalFVGs", "bullishFVGs", "bearishFVGs", "touchingFVGs", "historicalFVGs"].forEach(id => {
        const element = document.getElementById(id);
        if (element) element.textContent = "0";
      });
      
      // Try to trigger the original handler if available
      if (window.filterAndDisplayData) {
        window.filterAndDisplayData();
      }
    });
    
    fixButtonHandler("reconnectBtn", function() {
      console.log("🔄 Manual reconnect triggered");
      // Update the status indicators
      const wsStatus = document.getElementById("wsStatus");
      const statusIndicator = document.getElementById("status-indicator");
      const connectionText = document.getElementById("connectionText");
      
      if (wsStatus) {
        wsStatus.textContent = "Connecting...";
        wsStatus.className = "yellow";
      }
      
      if (statusIndicator) {
        statusIndicator.className = "status-indicator status-connecting";
      }
      
      if (connectionText) {
        connectionText.textContent = "Connecting...";
        connectionText.className = "yellow";
      }
      
      // Reload the page to reconnect the WebSocket
      setTimeout(() => {
        location.reload();
      }, 1000);
    });
    
    fixButtonHandler("toggleDebug", function() {
      console.log("🔄 Debug toggle clicked");
      // Toggle debug log visibility
      const debugLog = document.getElementById("debugLog");
      if (debugLog) {
        debugLog.classList.toggle('hidden');
      }
    });
    
    // Fix checkbox handlers
    const timeframeCheckboxes = document.querySelectorAll(".timeframe-check");
    timeframeCheckboxes.forEach(checkbox => {
      fixCheckboxHandler(checkbox, function() {
        console.log(`🔄 Timeframe checkbox ${checkbox.value} changed to ${this.checked}`);
        
        // Update the global selectedTimeframes set directly
        if (window.selectedTimeframes) {
          if (this.checked) {
            window.selectedTimeframes.add(this.value);
          } else {
            window.selectedTimeframes.delete(this.value);
          }
          console.log(`Updated selected timeframes: ${Array.from(window.selectedTimeframes).join(', ')}`);
        }
        
        if (window.filterAndDisplayData) {
          window.filterAndDisplayData();
        }
      });
    });
    
    fixCheckboxHandler(document.getElementById("showTestData"), function() {
      console.log("🔄 Show test data checkbox changed");
      if (window.filterAndDisplayData) {
        window.filterAndDisplayData();
      }
    });
    
    // Fix select handler
    fixSelectHandler(document.getElementById("fvgFilter"), function() {
      console.log("🔄 FVG filter changed");
      if (window.filterAndDisplayData) {
        window.filterAndDisplayData();
      }
    });
    
    // Fix input handler
    fixInputHandler(document.getElementById("maxDistance"), function() {
      console.log("🔄 Distance filter changed");
      if (window.filterAndDisplayData) {
        window.filterAndDisplayData();
      }
    });
    
    console.log("✅ All UI element handlers fixed successfully");
  }
  
  function fixButtonHandler(buttonId, handler) {
    const button = document.getElementById(buttonId);
    if (button) {
      // Remove all existing click handlers
      const newButton = button.cloneNode(true);
      button.parentNode.replaceChild(newButton, button);
      
      // Add new click handler
      newButton.addEventListener('click', handler);
      console.log(`✅ Fixed handler for button: ${buttonId}`);
    } else {
      console.error(`❌ Button not found: ${buttonId}`);
    }
  }
  
  function fixCheckboxHandler(checkbox, handler) {
    if (checkbox) {
      // Remove all existing change handlers
      const newCheckbox = checkbox.cloneNode(true);
      checkbox.parentNode.replaceChild(newCheckbox, checkbox);
      
      // Add new change handler with proper context binding
      newCheckbox.addEventListener('change', function(e) {
        console.log(`🔄 Checkbox ${this.value} changed to ${this.checked}`);
        handler.call(this, e);
      });
      console.log(`✅ Fixed handler for checkbox: ${checkbox.id || checkbox.value || 'unnamed'}`);
    }
  }
  
  function fixSelectHandler(select, handler) {
    if (select) {
      // Remove all existing change handlers
      const newSelect = select.cloneNode(true);
      select.parentNode.replaceChild(newSelect, select);
      
      // Add new change handler
      newSelect.addEventListener('change', handler);
      console.log(`✅ Fixed handler for select: ${select.id}`);
    }
  }
  
  function fixInputHandler(input, handler) {
    if (input) {
      // Remove all existing input handlers
      const newInput = input.cloneNode(true);
      input.parentNode.replaceChild(newInput, input);
      
      // Add new input and change handlers
      newInput.addEventListener('input', handler);
      newInput.addEventListener('change', handler);
      console.log(`✅ Fixed handler for input: ${input.id}`);
    }
  }
})();