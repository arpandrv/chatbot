# LLM Guidelines

This document outlines the guidelines for using the Large Language Model (LLM) in the AIMhi-Y Supportive Yarn Chatbot.

## LLM as a Fallback

The LLM is used as a fallback mechanism when the chatbot's rule-based system is unable to understand the user's input. The LLM is not the primary source of responses.

## Guardrails

The LLM is surrounded by a set of guardrails to ensure that its responses are safe and appropriate. These guardrails include:

*   **PII Filtering:** The LLM is not allowed to generate any personally identifiable information (PII).
*   **Content Filtering:** The LLM is not allowed to generate any harmful or inappropriate content.
*   **Length Limits:** The LLM's responses are limited in length to prevent it from generating long and rambling responses.

## Prompt Engineering

The LLM is guided by a carefully crafted system prompt that instructs it to be supportive, encouraging, and to stay within the boundaries of the AIMhi Stay Strong model.

The prompt also includes the recent conversation history to provide the LLM with context.

## Monitoring

The LLM's responses are monitored to ensure that they are safe and appropriate. Any issues with the LLM's responses are addressed immediately.
