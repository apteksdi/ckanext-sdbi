// Smart Exit Intent Detection and Google Forms Popup
// Detects multiple user behaviors and shows Google Forms popup intelligently

(function () {
  'use strict';

  // Enhanced Configuration
  const SMART_EXIT_INTENT_CONFIG = {
    // Basic settings
    threshold: 10, // Distance from top edge to trigger exit intent
    delay: 0,      // Delay before showing popup (ms)
    cookieName: 'smart_exit_intent_shown',
    cookieExpiry: 1, // Days
    debug: true,

    // Smart triggers configuration
    enableMouseExit: true,           // Mouse movement to top
    enableKeyboardShortcuts: true,   // Cmd+W, Cmd+Q, Alt+F4 detection
    enableEscapeKey: true,           // Escape key detection
    enableTabSwitch: true,           // Tab switching detection
    enableFocusLoss: true,           // Focus loss detection
    enableBeforeUnload: true,        // Attempt to catch close-tab/window

    // NEW: Smart triggers
    enableScrollBased: true,         // Show form when scrolling near bottom
    enableTimeBased: true,           // Show form after X minutes on page
    enableInactivityBased: true,     // Show form after X seconds of inactivity
    enableClickBased: true,          // Show form when clicking external links

    // Timing thresholds (in milliseconds)
    escapeKeyDelay: 5000,           // Minimum time before Escape key triggers
    tabSwitchDelay: 10000,          // Minimum time before tab switch triggers
    focusLossDelay: 15000,          // Minimum time before focus loss triggers
    timeBasedDelay: 180000,         // Show form after 3 minutes (180 seconds)
    inactivityDelay: 30000,         // Show form after 30 seconds of inactivity
    scrollThreshold: 0.8,           // Show form when 80% of page is scrolled

    // Firefox-specific configuration
    enableFirefoxWorkaround: true,
    firefoxReturnDelay: 5000,

    // Smart behavior
    maxTriggersPerSession: 2,       // Maximum times to show form per session
    sessionDuration: 3600000,       // Session duration (1 hour)
    triggerCooldown: 300000,        // 5 minutes cooldown between triggers
  };

  let exitIntentTriggered = false;
  let popupShown = false;
  let triggerCount = 0;
  let lastTriggerTime = 0;
  let sessionStartTime = Date.now();
  let inactivityTimer = null;
  let timeBasedTimer = null;
  let pageLoadTime = Date.now();

  // Get Google Forms with exit intent enabled
  function getExitIntentForms() {
    return fetch('/api/google-forms/exit-intent')
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          return data.forms;
        }
        return [];
      })
      .catch(error => {
        console.error('Error fetching exit intent forms:', error);
        return [];
      });
  }

  // Create enhanced popup modal with better UX
  function createPopupModal(form) {
    const modal = document.createElement('div');
    modal.className = 'smart-exit-intent-modal';
    modal.innerHTML = `
      <div class="smart-exit-intent-overlay"></div>
      <div class="smart-exit-intent-content">
        <div class="smart-exit-intent-header">
          <div class="header-content">
            <h3><i class="fa fa-heart"></i> ${form.title}</h3>
            <p class="header-subtitle">Kami menghargai waktu Anda!</p>
          </div>
          <button class="smart-exit-intent-close" onclick="closeSmartExitIntentModal()">
            <i class="fa fa-times"></i>
          </button>
        </div>
        <div class="smart-exit-intent-body">
          <div class="form-description">
            <p>${form.description || 'Sebelum Anda melanjutkan, mohon berikan feedback singkat untuk membantu kami meningkatkan layanan.'}</p>
          </div>
          <!-- Google Forms sets CSP frame-ancestors 'none' — cannot embed in iframe.
               Open in a new tab instead (forms.gle / docs.google.com). -->
          <div class="smart-exit-intent-cta">
            <a href="${form.form_url}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-lg smart-exit-intent-open">
              <i class="fa fa-external-link"></i> Isi Survey
            </a>
          </div>
        </div>
        <div class="smart-exit-intent-footer">
          <div class="footer-actions">
            <button class="btn btn-secondary" onclick="closeSmartExitIntentModal()">
              <i class="fa fa-times"></i> Tutup
            </button>
          </div>
          <div class="footer-note">
            <small><i class="fa fa-info-circle"></i> Form ini hanya membutuhkan waktu 1-2 menit</small>
          </div>
        </div>
      </div>
    `;
    return modal;
  }



  // Show enhanced popup modal
  function showPopupModal(form) {
    if (popupShown) return;

    // Add enhanced CSS if not already added
    if (!document.getElementById('smart-exit-intent-styles')) {
      const style = document.createElement('style');
      style.id = 'smart-exit-intent-styles';
      style.textContent = `
        .smart-exit-intent-modal {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          animation: fadeIn 0.3s ease-in-out;
        }

        .smart-exit-intent-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.7);
          backdrop-filter: blur(5px);
        }

        .smart-exit-intent-content {
          position: relative;
          background: white;
          border-radius: 12px;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
          max-width: 90vw;
          max-height: 90vh;
          width: 600px;
          overflow: hidden;
          animation: slideIn 0.3s ease-out;
        }

        .smart-exit-intent-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .header-content h3 {
          margin: 0 0 5px 0;
          font-size: 18px;
          font-weight: 600;
        }

        .header-subtitle {
          margin: 0;
          font-size: 14px;
          opacity: 0.9;
        }

        .smart-exit-intent-close {
          background: none;
          border: none;
          color: white;
          font-size: 20px;
          cursor: pointer;
          padding: 5px;
          border-radius: 50%;
          transition: background 0.3s;
        }

        .smart-exit-intent-close:hover {
          background: rgba(255, 255, 255, 0.2);
        }

        .smart-exit-intent-body {
          padding: 20px;
          max-height: 60vh;
          overflow-y: auto;
        }

        .form-description {
          margin-bottom: 15px;
          color: #444;
        }

        .smart-exit-intent-cta {
          display: flex;
          justify-content: center;
          padding: 24px 0 8px;
        }

        .smart-exit-intent-open {
          font-size: 16px;
          padding: 12px 28px;
        }

        .smart-exit-intent-footer {
          padding: 15px 20px;
          background: #fafafa;
          border-top: 1px solid #eee;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .footer-actions .btn {
          margin-right: 8px;
        }

        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideIn { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } }
      `;
      document.head.appendChild(style);
    }

    const modal = createPopupModal(form);
    document.body.appendChild(modal);
    popupShown = true;

    // Set cookie to avoid showing again in the same session/day
    const expiry = new Date();
    expiry.setTime(expiry.getTime() + (SMART_EXIT_INTENT_CONFIG.cookieExpiry * 24 * 60 * 60 * 1000));
    document.cookie = `${SMART_EXIT_INTENT_CONFIG.cookieName}=1; expires=${expiry.toUTCString()}; path=/`;
  }

  // Utility functions for cookies and sessions
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  function canTriggerExitIntent() {
    if (popupShown) return false;
    // if (exitIntentTriggered && Date.now() - lastTriggerTime < SMART_EXIT_INTENT_CONFIG.triggerCooldown) {
    //   return false;
    // }

    // // Max triggers per session
    // if (triggerCount >= SMART_EXIT_INTENT_CONFIG.maxTriggersPerSession) {
    //   return false;
    // }

    // Check cookie
    if (getCookie(SMART_EXIT_INTENT_CONFIG.cookieName)) {
      return false;
    }

    return true;
  }

  // Enhanced exit intent trigger function
  function triggerExitIntent(triggerType = 'unknown') {
    if (!canTriggerExitIntent()) return;

    exitIntentTriggered = true;
    triggerCount++;
    lastTriggerTime = Date.now();

    if (SMART_EXIT_INTENT_CONFIG.debug) {
      console.log(`Smart exit intent triggered by: ${triggerType}`);
    }

    // Get exit intent forms and show popup
    getExitIntentForms().then(forms => {
      if (forms.length > 0) {
        const form = forms[0];
        setTimeout(() => {
          showPopupModal(form);
        }, SMART_EXIT_INTENT_CONFIG.delay);
      }
    });
  }

  // NEW: Scroll-based exit intent
  function handleScrollBasedExitIntent() {
    if (!SMART_EXIT_INTENT_CONFIG.enableScrollBased) return;

    const scrollPercentage = (window.scrollY + window.innerHeight) / document.documentElement.scrollHeight;
    if (scrollPercentage >= SMART_EXIT_INTENT_CONFIG.scrollThreshold) {
      triggerExitIntent('scroll');
    }
  }

  // NEW: Time-based exit intent
  function handleTimeBasedExitIntent() {
    if (!SMART_EXIT_INTENT_CONFIG.enableTimeBased) return;

    const timeOnPage = Date.now() - pageLoadTime;
    if (timeOnPage >= SMART_EXIT_INTENT_CONFIG.timeBasedDelay) {
      triggerExitIntent('time');
    }
  }

  // NEW: Inactivity-based exit intent
  function resetInactivityTimer() {
    if (inactivityTimer) {
      clearTimeout(inactivityTimer);
    }

    if (SMART_EXIT_INTENT_CONFIG.enableInactivityBased) {
      inactivityTimer = setTimeout(() => {
        triggerExitIntent('inactivity');
      }, SMART_EXIT_INTENT_CONFIG.inactivityDelay);
    }
  }

  // NEW: Click-based exit intent
  function handleClickBasedExitIntent(e) {
    if (!SMART_EXIT_INTENT_CONFIG.enableClickBased) return;

    const target = e.target.closest('a');
    if (target && target.href) {
      const url = new URL(target.href);
      const currentUrl = new URL(window.location.href);

      // Check if it's an external link
      if (url.hostname !== currentUrl.hostname) {
        triggerExitIntent('click');
      }
    }
  }

  // Original exit intent handlers (enhanced)
  function handleMouseExitIntent(e) {
    if (!SMART_EXIT_INTENT_CONFIG.enableMouseExit) return;

    if (e.clientY <= SMART_EXIT_INTENT_CONFIG.threshold) {
      triggerExitIntent('mouse');
    }
  }

  function handleKeyboardExitIntent(e) {
    if (!SMART_EXIT_INTENT_CONFIG.enableKeyboardShortcuts && !SMART_EXIT_INTENT_CONFIG.enableEscapeKey) return;

    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const cmdKey = isMac ? e.metaKey : e.ctrlKey;
    const key = (e.key || '').toLowerCase();

    if (SMART_EXIT_INTENT_CONFIG.debug) {
      try {
        const debugPayload = {
          key,
          code: e.code,
          metaKey: e.metaKey,
          ctrlKey: e.ctrlKey,
          altKey: e.altKey,
          shiftKey: e.shiftKey,
          repeat: !!e.repeat,
          targetTag: e.target && e.target.tagName,
          timeMsSinceLoad: Date.now() - pageLoadTime,
        };
        console.log('[ExitIntent][keydown]', debugPayload);
        if (key === 'w') {
          console.log('[ExitIntent] Detected key "w"');
        }
        if (e.metaKey) {
          console.log('[ExitIntent] Detected Meta/Cmd pressed');
        }
      } catch (err) {
        // no-op
      }
    }

    // Keyboard shortcuts
    if (SMART_EXIT_INTENT_CONFIG.enableKeyboardShortcuts) {
      if ((cmdKey && (key === 'w' || key === 'q' || key === 'x')) || (e.altKey && key === 'f4')) {
        e.preventDefault();
        e.stopImmediatePropagation();
        triggerExitIntent('keyboard');
        return;
      }

      // macOS specific
      if (isMac && ((e.metaKey && key === 'h') || (e.metaKey && key === 'm'))) {
        e.preventDefault();
        e.stopImmediatePropagation();
        triggerExitIntent('keyboard');
        return;
      }
    }

    // Escape key
    if (SMART_EXIT_INTENT_CONFIG.enableEscapeKey && key === 'escape') {
      if (Date.now() - pageLoadTime > SMART_EXIT_INTENT_CONFIG.escapeKeyDelay) {
        triggerExitIntent('escape');
      }
    }
  }

  function handleVisibilityChange() {
    if (!SMART_EXIT_INTENT_CONFIG.enableTabSwitch) return;

    if (Date.now() - pageLoadTime > SMART_EXIT_INTENT_CONFIG.tabSwitchDelay) {
      if (document.hidden) {
        triggerExitIntent('tab_switch');
      }
    }
  }

  function handleFocusLoss() {
    if (!SMART_EXIT_INTENT_CONFIG.enableFocusLoss) return;

    if (Date.now() - pageLoadTime > SMART_EXIT_INTENT_CONFIG.focusLossDelay) {
      triggerExitIntent('focus_loss');
    }
  }

  // Attempt to detect close tab/window via beforeunload
  function handleBeforeUnload(e) {
    if (!SMART_EXIT_INTENT_CONFIG.enableBeforeUnload) return;
    if (!canTriggerExitIntent()) return;
    // Trigger the modal and try to prevent immediate unload
    triggerExitIntent('beforeunload');
    // Modern browsers require setting returnValue to show a confirm dialog
    e.preventDefault();
    e.returnValue = '';
    return '';
  }

  // Initialize smart exit intent detection
  function initSmartExitIntent() {
    if (window.smartExitIntentInitialized) return;

    // Check if we should show exit intent (not on admin pages)
    const currentPath = window.location.pathname;
    if (currentPath.includes('/google-forms') || currentPath.includes('/admin')) {
      if (SMART_EXIT_INTENT_CONFIG.debug) {
        console.log('Smart exit intent disabled on admin pages');
      }
      return;
    }

    // Add event listeners for different triggers
    if (SMART_EXIT_INTENT_CONFIG.enableMouseExit) {
      document.addEventListener('mouseleave', handleMouseExitIntent);
      document.addEventListener('mouseout', handleMouseExitIntent);
    }

    if (SMART_EXIT_INTENT_CONFIG.enableKeyboardShortcuts || SMART_EXIT_INTENT_CONFIG.enableEscapeKey) {
      const keydownOptions = { capture: true, passive: false };
      window.addEventListener('keydown', handleKeyboardExitIntent, keydownOptions);
      document.addEventListener('keydown', handleKeyboardExitIntent, keydownOptions);
    }

    if (SMART_EXIT_INTENT_CONFIG.enableTabSwitch) {
      document.addEventListener('visibilitychange', handleVisibilityChange);
    }

    if (SMART_EXIT_INTENT_CONFIG.enableFocusLoss) {
      window.addEventListener('blur', handleFocusLoss);
    }

    if (SMART_EXIT_INTENT_CONFIG.enableBeforeUnload) {
      window.addEventListener('beforeunload', handleBeforeUnload);
    }

    // NEW: Smart triggers
    if (SMART_EXIT_INTENT_CONFIG.enableScrollBased) {
      window.addEventListener('scroll', handleScrollBasedExitIntent);
    }

    if (SMART_EXIT_INTENT_CONFIG.enableClickBased) {
      document.addEventListener('click', handleClickBasedExitIntent);
    }

    // Initialize inactivity timer
    resetInactivityTimer();

    // Add activity listeners for inactivity detection
    ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
      document.addEventListener(event, resetInactivityTimer, true);
    });

    // Set up time-based trigger
    if (SMART_EXIT_INTENT_CONFIG.enableTimeBased) {
      timeBasedTimer = setTimeout(handleTimeBasedExitIntent, SMART_EXIT_INTENT_CONFIG.timeBasedDelay);
    }



    window.smartExitIntentInitialized = true;

    if (SMART_EXIT_INTENT_CONFIG.debug) {
      console.log('Smart exit intent detection initialized');
    }
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSmartExitIntent);
  } else {
    initSmartExitIntent();
  }

  // Expose close function globally
  window.closeSmartExitIntentModal = function () {
    const modal = document.querySelector('.smart-exit-intent-modal');
    if (modal) {
      modal.parentNode.removeChild(modal);
      popupShown = false;
    }
  };
})(); 