class AIMhiLLMChatbot {
    constructor() {
        this.chatForm = document.getElementById('chatForm');
        this.chatInput = document.getElementById('chatInput');
        this.chatMessages = document.getElementById('chatMessages');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.apiKeyContainer = document.getElementById('apiKeyContainer');
        
        // Conversation history for context
        this.conversationHistory = [
            {
                role: "user",
                parts: [{ text: "You are a supportive mental health chatbot for First Nations youth. Be empathetic, culturally sensitive, and helpful. Keep responses concise but warm." }]
            },
            {
                role: "model",
                parts: [{ text: "I understand. I'm here to provide supportive, culturally sensitive mental health support for First Nations youth. I'll be empathetic and helpful while keeping my responses warm and concise." }]
            }
        ];
        
        this.apiKey = localStorage.getItem('gemini_api_key');
        this.apiEndpoint = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent';
        
        this.init();
    }
    
    init() {
        if (!this.apiKey) {
            this.showApiKeyPrompt();
        }
        
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.chatInput.focus();
    }
    
    showApiKeyPrompt() {
        this.apiKeyContainer.style.display = 'flex';
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        const message = this.chatInput.value.trim();
        
        if (!message) return;
        
        if (!this.apiKey) {
            alert('Please enter your Gemini API key first');
            this.showApiKeyPrompt();
            return;
        }
        
        this.addMessage(message, 'user');
        this.chatInput.value = '';
        
        // Add user message to history
        this.conversationHistory.push({
            role: "user",
            parts: [{ text: message }]
        });
        
        this.showTypingIndicator();
        
        try {
            const response = await this.generateLLMResponse();
            this.hideTypingIndicator();
            
            if (response) {
                this.addMessage(response, 'bot');
                // Add bot response to history
                this.conversationHistory.push({
                    role: "model",
                    parts: [{ text: response }]
                });
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage("I'm sorry, I'm having trouble connecting right now. Please check your API key or try again later.", 'bot');
            console.error('Error:', error);
        }
    }
    
    async generateLLMResponse() {
        try {
            const response = await fetch(`${this.apiEndpoint}?key=${this.apiKey}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    contents: this.conversationHistory,
                    generationConfig: {
                        temperature: 0.7,
                        topK: 40,
                        topP: 0.95,
                        maxOutputTokens: 256,
                    },
                    safetySettings: [
                        {
                            category: "HARM_CATEGORY_HARASSMENT",
                            threshold: "BLOCK_NONE"
                        },
                        {
                            category: "HARM_CATEGORY_HATE_SPEECH",
                            threshold: "BLOCK_NONE"
                        },
                        {
                            category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold: "BLOCK_NONE"
                        },
                        {
                            category: "HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold: "BLOCK_NONE"
                        }
                    ]
                })
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.candidates && data.candidates[0] && data.candidates[0].content) {
                return data.candidates[0].content.parts[0].text;
            } else {
                throw new Error('Unexpected response format');
            }
        } catch (error) {
            console.error('Gemini API Error:', error);
            throw error;
        }
    }
    
    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        bubbleDiv.textContent = text;
        
        messageDiv.appendChild(bubbleDiv);
        this.chatMessages.appendChild(messageDiv);
        
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    showTypingIndicator() {
        this.typingIndicator.style.display = 'flex';
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }
}

// Global function to save API key
function saveApiKey() {
    const apiKeyInput = document.getElementById('apiKeyInput');
    const apiKey = apiKeyInput.value.trim();
    
    if (!apiKey) {
        alert('Please enter a valid API key');
        return;
    }
    
    localStorage.setItem('gemini_api_key', apiKey);
    document.getElementById('apiKeyContainer').style.display = 'none';
    
    // Reload the page to initialize with the new API key
    window.location.reload();
}

// Global functions for HTML onclick handlers
function handleModeChange(mode) {
    if (mode === 'rule-based') {
        window.location.href = 'chatbot.html';
    }
}

function clearApiKey() {
    if (confirm('Are you sure you want to clear your API key? You will need to enter it again.')) {
        localStorage.removeItem('gemini_api_key');
        window.location.reload();
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AIMhiLLMChatbot();
});