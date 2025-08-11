let sessionId = null;

// Add message to chat
const addMessage = (sender, text, isHTML = false) => {
    const messages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-message', `${sender}-message`);
    
    if (isHTML) {
        messageDiv.innerHTML = text;
    } else {
        messageDiv.textContent = text;
    }
    
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
};

// Send message function
const sendMessage = async () => {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (message === '') return;

    // Add user message to chat
    addMessage('user', message);
    messageInput.value = '';

    // Hide quick actions after first message
    const quickActions = document.getElementById('quickActions');
    if (quickActions) {
        quickActions.style.display = 'none';
    }

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
        
        // Add bot response
        addMessage('bot', data.reply);
        
    } catch (error) {
        console.error('Error sending message:', error);
        addMessage('bot', 'Sorry, I\'m having trouble connecting right now. Please try again.');
    }
};

// Send quick message
const sendQuickMessage = (message) => {
    const messageInput = document.getElementById('messageInput');
    messageInput.value = message;
    sendMessage();
};

// Show help modal
const showHelp = () => {
    const helpModal = document.getElementById('helpModal');
    helpModal.style.display = 'flex';
    helpModal.setAttribute('aria-hidden', 'false');
};

// Hide help modal
const hideHelp = () => {
    const helpModal = document.getElementById('helpModal');
    helpModal.style.display = 'none';
    helpModal.setAttribute('aria-hidden', 'true');
};

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendBtn');
    
    // Add event listeners
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
    
    if (messageInput) {
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
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
});
