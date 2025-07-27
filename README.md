# AIMhi Youth Chatbot Prototype

## Overview
This is a dual-mode chatbot prototype for the AIMhi Youth mental health support app, created as a proof of concept for Group HIT401-036. It features both rule-based responses and AI-powered conversations using Google's Gemini.

## Features
- Clean, mobile-responsive interface
- **Two chat modes:**
  - Rule-based keyword matching for offline use
  - AI-powered responses using Google Gemini for natural conversations
- Mode selector dropdown to switch between chat types
- Supports conversations about stress, anxiety, sadness, sleep issues, and more
- Typing indicator for realistic chat experience
- Secure API key storage in browser localStorage

## How to Run

### Rule-Based Mode
1. Open `chatbot.html` in any modern web browser
2. Start typing messages in the input field
3. The chatbot will respond based on keyword matching

### AI Mode (Gemini)
1. Get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Open `chatbot.html` and select "AI (Gemini)" from the dropdown
3. Enter your API key when prompted (stored securely in browser)
4. Start chatting with the AI-powered assistant

## Supported Topics
The chatbot recognizes and responds to keywords related to:
- Greetings (hello, hi, hey)
- Stress and anxiety
- Sadness and depression
- Sleep problems
- Requests for help/support
- Anger management
- Positive emotions
- Breathing exercises

## Technical Details
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Architecture:** Client-side only
  - Rule-based: Pattern matching with predefined responses
  - AI Mode: Direct API calls to Google Gemini 2.0 Flash (Experimental)
- **Context Management:** Full conversation history sent with each request
- **Responsive:** Works on desktop and mobile devices
- **Security:** API keys stored in browser localStorage (never sent to any server except Google)

## Future Enhancements
This prototype can be expanded with:
- Backend services for conversation persistence
- User authentication and profiles
- Indigenous language support
- Integration with professional help resources