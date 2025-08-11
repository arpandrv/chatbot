# Safety Protocols

This document outlines the safety protocols implemented in the AIMhi-Y Supportive Yarn Chatbot.

## Risk Detection

The chatbot uses a deterministic risk detection system to identify users who may be in distress. The system is based on a curated list of risk phrases and their variants.

When a risk phrase is detected, the chatbot immediately stops the regular conversation flow and provides the user with a list of crisis resources, including phone numbers for support services.

## Content Boundaries

The chatbot is designed to provide a supportive and encouraging conversation. It is not a medical professional and does not provide medical advice or diagnosis.

The chatbot's responses are based on a pre-defined set of culturally appropriate prompts and messages. The LLM fallback is also designed to stay within these boundaries.

## Privacy

The chatbot is designed to be privacy-preserving. It does not store any personally identifiable information (PII). Session IDs are anonymous and are not linked to any personal information.

Chat history is stored for the purpose of providing context to the LLM, but it is not used for any other purpose. The chat history is also anonymized and does not contain any PII.
