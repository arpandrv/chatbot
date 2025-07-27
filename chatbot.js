class AIMhiChatbot {
    constructor() {
        this.chatForm = document.getElementById('chatForm');
        this.chatInput = document.getElementById('chatInput');
        this.chatMessages = document.getElementById('chatMessages');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        this.responses = {
            greetings: {
                patterns: ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings'],
                responses: [
                    "Hello! I'm here to support you. How are you feeling today?",
                    "Hi there! It's good to see you. What's on your mind?",
                    "Hey! I'm here to listen. How can I help you today?"
                ]
            },
            stress: {
                patterns: ['stress', 'stressed', 'anxious', 'anxiety', 'worried', 'overwhelmed', 'pressure'],
                responses: [
                    "I hear that you're feeling stressed. Let's try a breathing exercise. Inhale slowly for 4 counts... hold for 4... and exhale for 6. Want to try it together?",
                    "Stress can be really tough. Would you like to talk about what's causing it, or would you prefer some quick relaxation tips?",
                    "You're not alone in feeling this way. Many young people experience stress. What usually helps you feel calmer?"
                ]
            },
            sadness: {
                patterns: ['sad', 'depressed', 'down', 'unhappy', 'crying', 'tears', 'lonely', 'alone'],
                responses: [
                    "I'm really sorry you're feeling this way. You're not alone, and it's okay to feel sad sometimes. Would you like to talk about what's troubling you?",
                    "Your feelings are valid. Sometimes talking helps. Is there something specific that's making you feel down?",
                    "I hear you, and I'm here for you. Remember, these feelings won't last forever. Would you like some tips for when you're feeling low?"
                ]
            },
            sleep: {
                patterns: ['sleep', 'cant sleep', 'insomnia', 'tired', 'exhausted', 'nightmares', 'dreams'],
                responses: [
                    "Sleep troubles can be really frustrating. Would you like to try a simple relaxation technique that might help?",
                    "I understand - not being able to sleep is tough. Have you tried creating a bedtime routine? Sometimes that helps.",
                    "Rest is so important for wellbeing. Let's think about what might help you wind down. What time do you usually try to sleep?"
                ]
            },
            help: {
                patterns: ['help', 'support', 'someone to talk', 'counselor', 'therapist', 'emergency'],
                responses: [
                    "I'm here to listen and support you. If you need professional help, you can also reach out to a counselor through the AIMhi app or call a helpline.",
                    "You're brave for reaching out. I'm here to chat, and there are also trained counselors available if you need more support.",
                    "Help is always available. I'm here now, and you can also connect with professional support through the app whenever you need."
                ]
            },
            anger: {
                patterns: ['angry', 'mad', 'furious', 'rage', 'annoyed', 'frustrated', 'pissed'],
                responses: [
                    "I can sense you're feeling angry. That's a valid emotion. Would you like to talk about what's making you feel this way?",
                    "Anger can be intense. Sometimes it helps to take a few deep breaths or do some physical activity. What usually helps you cool down?",
                    "It's okay to feel angry. Let's find a healthy way to work through these feelings together."
                ]
            },
            positive: {
                patterns: ['good', 'great', 'happy', 'excited', 'wonderful', 'amazing', 'better'],
                responses: [
                    "That's wonderful to hear! I'm glad you're feeling positive. What's bringing you joy today?",
                    "It's great that you're feeling good! Celebrating positive moments is important. Tell me more!",
                    "Your positive energy is inspiring! Keep nurturing what makes you feel this way."
                ]
            },
            thanks: {
                patterns: ['thank', 'thanks', 'appreciate', 'grateful', 'cheers'],
                responses: [
                    "You're very welcome! I'm always here when you need support.",
                    "It's my pleasure to help. Remember, you can come back anytime you need to talk.",
                    "Thank you for trusting me. Take care of yourself!"
                ]
            },
            breathing: {
                patterns: ['breathe', 'breathing', 'breath', 'calm down', 'relax'],
                responses: [
                    "Let's do a simple breathing exercise together. Breathe in through your nose for 4 counts... Hold for 4... Now breathe out through your mouth for 6. Let's do this 3 times.",
                    "Breathing exercises can really help. Try the 4-7-8 technique: Inhale for 4, hold for 7, exhale for 8. It's very calming.",
                    "Good idea! Deep breathing activates your body's relaxation response. Let's take 5 deep, slow breaths together."
                ]
            }
        };
        
        this.defaultResponses = [
            "I hear you. Can you tell me more about how you're feeling?",
            "Thank you for sharing that with me. How long have you been feeling this way?",
            "That sounds challenging. What do you think might help you feel better?",
            "I'm here to listen. Is there anything specific you'd like to talk about?",
            "Your feelings are important. Would you like to explore this further?"
        ];
        
        this.init();
    }
    
    init() {
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.chatInput.focus();
    }
    
    handleSubmit(e) {
        e.preventDefault();
        const message = this.chatInput.value.trim();
        
        if (!message) return;
        
        this.addMessage(message, 'user');
        this.chatInput.value = '';
        
        this.showTypingIndicator();
        
        setTimeout(() => {
            this.hideTypingIndicator();
            const response = this.generateResponse(message);
            this.addMessage(response, 'bot');
        }, 1000 + Math.random() * 1000);
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
    
    generateResponse(message) {
        const lowerMessage = message.toLowerCase();
        
        for (const [category, data] of Object.entries(this.responses)) {
            for (const pattern of data.patterns) {
                if (lowerMessage.includes(pattern)) {
                    return this.getRandomResponse(data.responses);
                }
            }
        }
        
        return this.getRandomResponse(this.defaultResponses);
    }
    
    getRandomResponse(responses) {
        return responses[Math.floor(Math.random() * responses.length)];
    }
    
    showTypingIndicator() {
        this.typingIndicator.style.display = 'flex';
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }
}

// Global functions for HTML onclick handlers
function handleModeChange(mode) {
    if (mode === 'llm') {
        window.location.href = 'chatbot-llm.html';
    }
}

function sendExample(text) {
    const chatInput = document.getElementById('chatInput');
    const chatForm = document.getElementById('chatForm');
    
    chatInput.value = text;
    chatInput.focus();
    
    // Trigger submit event
    chatForm.dispatchEvent(new Event('submit'));
}

document.addEventListener('DOMContentLoaded', () => {
    new AIMhiChatbot();
});