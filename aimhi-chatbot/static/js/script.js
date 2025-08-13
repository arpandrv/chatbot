// ================================
// Global Variables
// ================================
let sessionId = null;
let messageCount = 0;
let typingIndicator = null;

// ================================
// Message Functions
// ================================

/**
 * Add a message to the chat interface
 * @param {string} sender - 'user' or 'bot'
 * @param {string} text - Message text
 * @param {boolean} isHTML - Whether the text contains HTML
 */
const addMessage = (sender, text, isHTML = false) => {
    const messages = document.getElementById('chatMessages');
    
    // Create message wrapper
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);
    
    // Create avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.classList.add('message-avatar');
    if (sender === 'bot') {
        avatarDiv.textContent = '🌟';
    } else {
        avatarDiv.textContent = '👤';
    }
    
    // Create message bubble
    const bubbleDiv = document.createElement('div');
    bubbleDiv.classList.add('message-bubble');
    
    const messageParagraph = document.createElement('p');
    if (isHTML) {
        messageParagraph.innerHTML = text;
    } else {
        messageParagraph.textContent = text;
    }
    
    bubbleDiv.appendChild(messageParagraph);
    
    // Assemble the message
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(bubbleDiv);
    
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
    
    messageCount++;
};

/**
 * Show typing indicator
 */
const showTypingIndicator = () => {
    const messages = document.getElementById('chatMessages');
    
    // Create typing indicator if it doesn't exist
    if (!typingIndicator) {
        typingIndicator = document.createElement('div');
        typingIndicator.classList.add('message', 'bot');
        typingIndicator.id = 'typingIndicator';
        
        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('message-avatar');
        avatarDiv.textContent = '🌟';
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.classList.add('message-bubble');
        
        const typingDiv = document.createElement('div');
        typingDiv.classList.add('typing-indicator');
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dot.classList.add('typing-dot');
            typingDiv.appendChild(dot);
        }
        
        bubbleDiv.appendChild(typingDiv);
        typingIndicator.appendChild(avatarDiv);
        typingIndicator.appendChild(bubbleDiv);
    }
    
    messages.appendChild(typingIndicator);
    messages.scrollTop = messages.scrollHeight;
};

/**
 * Hide typing indicator
 */
const hideTypingIndicator = () => {
    if (typingIndicator && typingIndicator.parentNode) {
        typingIndicator.parentNode.removeChild(typingIndicator);
    }
};

// ================================
// Send Message Functions
// ================================

/**
 * Send message to backend
 */
const sendMessage = async () => {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendBtn');
    const message = messageInput.value.trim();
    
    if (message === '') return;

    // Add user message to chat
    addMessage('user', message);
    messageInput.value = '';
    
    // Disable input while processing
    messageInput.disabled = true;
    sendButton.disabled = true;

    // Hide quick actions after first message
    const quickActions = document.getElementById('quickActions');
    if (quickActions) {
        quickActions.style.display = 'none';
    }
    
    // Show typing indicator
    showTypingIndicator();

    try {
        // Send to backend
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                message: message, 
                session_id: sessionId 
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        sessionId = data.session_id;
        
        // Hide typing indicator and add bot response
        hideTypingIndicator();
        addMessage('bot', data.reply);
        
        // Update debug panel if debug info is present
        if (data.debug) {
            updateDebugPanel(data.debug, data.state);
        }
        
        // Check if this is a risk response
        if (data.risk_detected) {
            handleRiskResponse(data);
        }
        
        // Check if session is ending
        if (data.session_ending) {
            handleSessionEnd(data);
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        hideTypingIndicator();
        addMessage('bot', 'Sorry, I\'m having trouble connecting right now. Please try again.');
    } finally {
        // Re-enable input
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
};

/**
 * Send quick message
 * @param {string} message - The quick message to send
 */
const sendQuickMessage = (message) => {
    const messageInput = document.getElementById('messageInput');
    messageInput.value = message;
    sendMessage();
};

// ================================
// Special Response Handlers
// ================================

/**
 * Handle risk detection response
 * @param {Object} data - Response data from backend
 */
const handleRiskResponse = (data) => {
    const messages = document.getElementById('chatMessages');
    
    const riskDiv = document.createElement('div');
    riskDiv.classList.add('risk-message');
    
    riskDiv.innerHTML = `
        <h4><i class="bi bi-exclamation-triangle-fill"></i> Important Support Resources</h4>
        <p>I'm concerned about what you've shared. Please reach out to these 24/7 services:</p>
        <div class="help-numbers">
            <div class="help-item">
                <strong>13YARN</strong>
                <a href="tel:139276">13 92 76</a>
            </div>
            <div class="help-item">
                <strong>Lifeline</strong>
                <a href="tel:131114">13 11 14</a>
            </div>
        </div>
    `;
    
    messages.appendChild(riskDiv);
    messages.scrollTop = messages.scrollHeight;
};

/**
 * Handle session end
 * @param {Object} data - Response data from backend
 */
const handleSessionEnd = (data) => {
    const messages = document.getElementById('chatMessages');
    
    // Add session summary if available
    if (data.session_summary) {
        const summaryDiv = document.createElement('div');
        summaryDiv.classList.add('summary-box');
        
        summaryDiv.innerHTML = `
            <h3><i class="bi bi-journal-text"></i> Today's Chat Summary</h3>
            ${data.session_summary.topics ? 
                `<div class="summary-item">
                    <strong>Topics Discussed:</strong>
                    ${data.session_summary.topics.join(', ')}
                </div>` : ''}
            ${data.session_summary.strengths_identified ? 
                `<div class="summary-item">
                    <strong>Strengths Identified:</strong>
                    ${data.session_summary.strengths_identified.join(', ')}
                </div>` : ''}
            ${data.session_summary.key_insights ? 
                `<div class="summary-item">
                    <strong>Key Insights:</strong>
                    ${data.session_summary.key_insights}
                </div>` : ''}
        `;
        
        messages.appendChild(summaryDiv);
    }
    
    // Add session end message
    const endDiv = document.createElement('div');
    endDiv.classList.add('session-end');
    
    endDiv.innerHTML = `
        <i class="bi bi-heart-fill"></i>
        <h3>Take care!</h3>
        <p>Remember, support is always available when you need it.</p>
    `;
    
    messages.appendChild(endDiv);
    messages.scrollTop = messages.scrollHeight;
    
    // Disable input
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendBtn');
    messageInput.disabled = true;
    sendButton.disabled = true;
};

// ================================
// Debug Panel Functions
// ================================

/**
 * Toggle debug panel visibility
 */
const toggleDebugPanel = () => {
    const debugPanel = document.getElementById('debugPanel');
    const toggleIcon = document.getElementById('debugToggleIcon');
    
    debugPanel.classList.toggle('collapsed');
    
    if (debugPanel.classList.contains('collapsed')) {
        toggleIcon.className = 'bi bi-chevron-left';
    } else {
        toggleIcon.className = 'bi bi-chevron-right';
    }
};

/**
 * Update debug panel with backend information
 * @param {Object} debugInfo - Debug information from backend
 * @param {string} currentState - Current FSM state
 */
const updateDebugPanel = (debugInfo, currentState) => {
    // FSM State
    const fsmStateEl = document.getElementById('fsmState');
    if (fsmStateEl) {
        const stateTransition = debugInfo.fsm_state_before !== debugInfo.fsm_state_after 
            ? `${debugInfo.fsm_state_before} → ${debugInfo.fsm_state_after}`
            : currentState || debugInfo.fsm_state_after || '-';
        fsmStateEl.textContent = stateTransition;
        fsmStateEl.classList.add('updated');
        setTimeout(() => fsmStateEl.classList.remove('updated'), 500);
    }
    
    // Intent Classification
    const intentInfoEl = document.getElementById('intentInfo');
    if (intentInfoEl && debugInfo.intent_classification) {
        const intentData = debugInfo.intent_classification;
        const intentText = `Intent: ${intentData.detected_intent || 'unknown'}\nConfidence: ${
            intentData.confidence ? (intentData.confidence * 100).toFixed(1) + '%' : 'N/A'
        }\nExpected: ${intentData.expected_intent || 'any'}`;
        intentInfoEl.textContent = intentText;
        intentInfoEl.classList.add('updated');
        setTimeout(() => intentInfoEl.classList.remove('updated'), 500);
    }
    
    // Response Source
    const responseSourceEl = document.getElementById('responseSource');
    if (responseSourceEl) {
        responseSourceEl.textContent = debugInfo.response_source || 'unknown';
        responseSourceEl.classList.add('updated');
        setTimeout(() => responseSourceEl.classList.remove('updated'), 500);
    }
    
    // User Sentiment
    const userSentimentEl = document.getElementById('userSentiment');
    if (userSentimentEl) {
        const sentimentWithEmoji = {
            'positive': '😊 Positive',
            'negative': '😔 Negative', 
            'neutral': '😐 Neutral'
        };
        userSentimentEl.textContent = sentimentWithEmoji[debugInfo.user_sentiment] || debugInfo.user_sentiment || 'unknown';
        userSentimentEl.classList.add('updated');
        setTimeout(() => userSentimentEl.classList.remove('updated'), 500);
    }
    
    // Fallback Info
    const fallbackInfoEl = document.getElementById('fallbackInfo');
    if (fallbackInfoEl) {
        const fallbackText = debugInfo.fallback_triggered 
            ? `🔄 Triggered (Attempt ${debugInfo.attempt_count || 1})`
            : '✅ Not triggered';
        fallbackInfoEl.textContent = fallbackText;
        fallbackInfoEl.classList.add('updated');
        setTimeout(() => fallbackInfoEl.classList.remove('updated'), 500);
    }
    
    // Risk Detection
    const riskDetectionEl = document.getElementById('riskDetection');
    if (riskDetectionEl) {
        const riskText = debugInfo.risk_detected 
            ? '🚨 Risk detected'
            : '✅ No risk';
        riskDetectionEl.textContent = riskText;
        riskDetectionEl.classList.add('updated');
        setTimeout(() => riskDetectionEl.classList.remove('updated'), 500);
    }
};

// ================================
// Help Modal Functions
// ================================

/**
 * Show help modal
 */
const showHelp = () => {
    const helpModal = document.getElementById('helpModal');
    helpModal.style.display = 'flex';
    helpModal.setAttribute('aria-hidden', 'false');
};

/**
 * Hide help modal
 */
const hideHelp = () => {
    const helpModal = document.getElementById('helpModal');
    helpModal.style.display = 'none';
    helpModal.setAttribute('aria-hidden', 'true');
};

// ================================
// Utility Functions
// ================================

/**
 * Format timestamp for display
 * @param {Date} date - Date object
 * @returns {string} Formatted time string
 */
const formatTime = (date) => {
    return date.toLocaleTimeString('en-AU', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
};

/**
 * Check if user is idle
 * @returns {boolean} True if user has been idle for more than 5 minutes
 */
let lastActivityTime = Date.now();
const checkIdleTime = () => {
    const idleTime = Date.now() - lastActivityTime;
    return idleTime > 5 * 60 * 1000; // 5 minutes
};

/**
 * Reset idle timer
 */
const resetIdleTimer = () => {
    lastActivityTime = Date.now();
};

// ================================
// Event Listeners and Initialization
// ================================

/**
 * Initialize the application when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendBtn');
    
    // Add event listeners for message input
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
    
    if (messageInput) {
        // Send message on Enter key
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Reset idle timer on input
        messageInput.addEventListener('input', resetIdleTimer);
        
        // Character counter (optional)
        messageInput.addEventListener('input', (e) => {
            const remaining = 500 - e.target.value.length;
            if (remaining < 50) {
                // Could show a character count warning here
                console.log(`Characters remaining: ${remaining}`);
            }
        });
    }

    // Close help modal when clicking outside
    const helpModal = document.getElementById('helpModal');
    if (helpModal) {
        helpModal.addEventListener('click', (e) => {
            if (e.target === helpModal) {
                hideHelp();
            }
        });
    }
    
    // Keyboard navigation for help modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const helpModal = document.getElementById('helpModal');
            if (helpModal && helpModal.style.display === 'flex') {
                hideHelp();
            }
        }
    });
    
    // Track user activity
    document.addEventListener('click', resetIdleTimer);
    document.addEventListener('keypress', resetIdleTimer);
    
    // Check for idle timeout periodically
    setInterval(() => {
        if (checkIdleTime() && sessionId) {
            // Could send an idle notification to backend
            console.log('User has been idle for 5 minutes');
        }
    }, 60000); // Check every minute
    
    // Initialize session
    initializeSession();
});

/**
 * Initialize a new chat session
 */
const initializeSession = async () => {
    try {
        // Could make an initial request to backend to start session
        console.log('Chat session initialized');
        
        // Focus on input field
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.focus();
        }
    } catch (error) {
        console.error('Error initializing session:', error);
    }
};

// ================================
// Export functions for testing (if needed)
// ================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        addMessage,
        sendMessage,
        sendQuickMessage,
        showHelp,
        hideHelp,
        toggleDebugPanel,
        updateDebugPanel,
        formatTime,
        checkIdleTime,
        resetIdleTimer
    };
}