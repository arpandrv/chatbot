document.addEventListener('DOMContentLoaded', () => {
    const messages = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    let sessionId = null;

    const addMessage = (sender, text) => {
        const message = document.createElement('div');
        message.classList.add('message', `${sender}-message`);
        message.innerText = text;
        messages.appendChild(message);
        messages.scrollTop = messages.scrollHeight;
    };

    const sendMessage = async () => {
        const message = messageInput.value.trim();
        if (message === '') return;

        addMessage('user', message);
        messageInput.value = '';

        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message, session_id: sessionId })
        });

        const data = await response.json();
        sessionId = data.session_id;
        addMessage('bot', data.reply);
    };

    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Initial welcome message
    addMessage('bot', 'Welcome to the AIMhi-Y Supportive Yarn Chatbot. This is a safe space to yarn about your wellbeing. To start, just say hi.');
});
