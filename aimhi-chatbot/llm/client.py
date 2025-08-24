# aimhi-chatbot/llm/client.py

import os
import json
import logging
import requests
from typing import Optional, Dict, Any
import time

# Load environment variables securely
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Base exception for LLM client errors"""
    pass


class LLMAPIError(LLMClientError):
    """API-specific errors (rate limits, auth, etc.)"""
    def __init__(self, message: str, status_code: int = None, error_type: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type


class LLMTimeoutError(LLMClientError):
    """Request timeout errors"""
    pass


class LLMValidationError(LLMClientError):
    """Response validation errors"""
    pass


class LLMClient:
    """
    Synchronous LLM client for Anthropic API with robust error handling.
    Supports multiple model providers and graceful fallback.
    """
    
    def __init__(self, config_type: str = "conversation"):
        """
        Initialize LLM client with configuration.
        
        Args:
            config_type: Either "conversation" or "summary" for different parameter sets
        """
        self._load_config()
        self._setup_parameters(config_type)
        self._validate_setup()
        
        # Request session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AIMhi-Chatbot/1.0',
            'Content-Type': 'application/json'
        })
        
        logger.info(f"LLM Client initialized for {config_type} with model {self.model}")

    def _load_config(self) -> None:
        """Load LLM configuration from JSON file with fallback."""
        try:
            config_dir = os.path.dirname(os.path.dirname(__file__))  # Go up to project root
            config_path = os.path.join(config_dir, 'config', 'llm_config.json')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                
            logger.debug(f"Loaded LLM config from {config_path}")
            
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load llm_config.json: {e}. Using fallback defaults.")
            self._use_fallback_config()

    def _use_fallback_config(self) -> None:
        """Fallback configuration if JSON file is unavailable."""
        self.config = {
            "api_url": "https://api.anthropic.com/v1/messages",
            "models": {
                "primary": "claude-3-haiku-20240307",
                "fallback": "claude-3-sonnet-20240229"
            },
            "parameters": {
                "conversation": {
                    "max_tokens": 500,
                    "temperature": 0.8,
                    "timeout": 45
                },
                "summary": {
                    "max_tokens": 800,
                    "temperature": 0.3,
                    "timeout": 60
                }
            },
            "guardrails": {
                "max_response_length": 400,
                "enable_medical_filter": True,
                "enable_cultural_filter": True,
                "enable_pii_filter": True,
                "truncate_at_sentence": True
            }
        }

    def _setup_parameters(self, config_type: str) -> None:
        """Setup parameters based on configuration type."""
        # Get parameters for the specific config type
        params = self.config['parameters'].get(
            config_type, 
            self.config['parameters']['conversation']
        )
        
        self.model = self.config['models']['primary']
        self.fallback_model = self.config['models'].get('fallback')
        self.timeout = params['timeout']
        self.max_tokens = params['max_tokens']
        self.temperature = params['temperature']
        
        # API configuration
        self.api_url = self.config['api_url']
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Guardrails
        self.guardrails = self.config.get('guardrails', {})
        self.max_response_length = self.guardrails.get('max_response_length', 400)

    def _validate_setup(self) -> None:
        """Validate that required configuration is available."""
        if not self.api_key:
            raise LLMClientError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it to use the LLM fallback feature."
            )
        
        if not self.api_key.startswith(('sk-', 'ant-')):
            logger.warning("API key format doesn't match expected Anthropic format")
        
        if self.timeout <= 0 or self.timeout > 120:
            logger.warning(f"Unusual timeout value: {self.timeout}s")
        
        if self.max_tokens <= 0 or self.max_tokens > 4000:
            logger.warning(f"Unusual max_tokens value: {self.max_tokens}")

    def generate(self, system_prompt: str, user_message: str, temperature: Optional[float] = None) -> str:
        """
        Generate response with proper system/user message separation.
        
        Args:
            system_prompt: System instructions for the model
            user_message: User's input message
            temperature: Optional temperature override
            
        Returns:
            Generated response text
            
        Raises:
            LLMAPIError: For API-related errors
            LLMTimeoutError: For timeout errors
            LLMValidationError: For response validation errors
        """
        start_time = time.time()
        
        try:
            # Prepare request data
            request_data = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": temperature if temperature is not None else self.temperature,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_message}
                ]
            }
            
            # Prepare headers
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            logger.debug(f"Making LLM request to {self.api_url} with model {self.model}")
            
            # Make synchronous request
            response = self.session.post(
                self.api_url,
                headers=headers,
                json=request_data,
                timeout=self.timeout
            )
            
            inference_time = int((time.time() - start_time) * 1000)
            
            # Handle different response status codes
            if response.status_code == 200:
                result = response.json()
                generated_text = result['content'][0]['text']
                
                logger.debug(f"LLM response received in {inference_time}ms")
                
                # Validate response
                if not self.validate_response(generated_text):
                    raise LLMValidationError("Generated response failed validation checks")
                
                return generated_text
                
            elif response.status_code == 401:
                raise LLMAPIError("Invalid API key", response.status_code, "authentication_error")
                
            elif response.status_code == 429:
                raise LLMAPIError("Rate limit exceeded", response.status_code, "rate_limit_error")
                
            elif response.status_code == 400:
                error_detail = self._extract_error_detail(response)
                raise LLMAPIError(f"Bad request: {error_detail}", response.status_code, "invalid_request_error")
                
            elif response.status_code >= 500:
                raise LLMAPIError("Anthropic API server error", response.status_code, "api_error")
                
            else:
                error_detail = self._extract_error_detail(response)
                raise LLMAPIError(f"Unexpected API error: {error_detail}", response.status_code, "unknown_error")

        except requests.exceptions.Timeout:
            logger.error(f"LLM request timed out after {self.timeout}s")
            raise LLMTimeoutError(f"Request timed out after {self.timeout} seconds")
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise LLMAPIError("Failed to connect to Anthropic API", error_type="connection_error")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise LLMAPIError(f"Request failed: {str(e)}", error_type="request_error")
            
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Response parsing error: {e}")
            raise LLMValidationError(f"Failed to parse API response: {str(e)}")

    def _extract_error_detail(self, response: requests.Response) -> str:
        """Extract error detail from API response."""
        try:
            error_data = response.json()
            if 'error' in error_data:
                return error_data['error'].get('message', 'Unknown error')
            return error_data.get('message', 'Unknown error')
        except:
            return response.text[:200] if response.text else 'No error detail available'

    def validate_response(self, text: str) -> bool:
        """
        Validate LLM response for safety and quality.
        
        Args:
            text: Generated response text
            
        Returns:
            True if response passes all validation checks
        """
        if not text or not isinstance(text, str):
            logger.debug("Response validation failed: empty or non-string response")
            return False
        
        # Check for reasonable length
        text_stripped = text.strip()
        if len(text_stripped) < 5:
            logger.debug("Response validation failed: too short")
            return False
            
        if len(text) > self.max_response_length * 2:  # Allow some flexibility
            logger.debug("Response validation failed: too long")
            return False
        
        # Check for obvious error indicators
        error_indicators = [
            "I cannot", "I can't", "I'm not able to", "I don't have access",
            "API error", "Error:", "Failed to", "unauthorized", "rate limit"
        ]
        
        text_lower = text.lower()
        for indicator in error_indicators:
            if indicator.lower() in text_lower:
                logger.debug(f"Response validation failed: contains error indicator '{indicator}'")
                return False
        
        # Check for empty or placeholder responses
        placeholder_indicators = [
            "...", "___", "[placeholder]", "[error]", "null", "undefined"
        ]
        
        for placeholder in placeholder_indicators:
            if placeholder in text_lower:
                logger.debug(f"Response validation failed: contains placeholder '{placeholder}'")
                return False
        
        # Check for minimum content quality
        if len(text_stripped.split()) < 3:  # At least 3 words
            logger.debug("Response validation failed: too few words")
            return False
        
        return True

    def generate_with_fallback(self, system_prompt: str, user_message: str, temperature: Optional[float] = None) -> str:
        """
        Generate response with automatic fallback to secondary model if primary fails.
        
        Args:
            system_prompt: System instructions
            user_message: User input
            temperature: Optional temperature override
            
        Returns:
            Generated response text
        """
        try:
            return self.generate(system_prompt, user_message, temperature)
            
        except (LLMAPIError, LLMTimeoutError, LLMValidationError) as e:
            logger.warning(f"Primary model failed: {e}. Attempting fallback model.")
            
            if not self.fallback_model or self.fallback_model == self.model:
                logger.error("No fallback model available or same as primary")
                raise
            
            # Try with fallback model
            original_model = self.model
            try:
                self.model = self.fallback_model
                return self.generate(system_prompt, user_message, temperature)
            finally:
                self.model = original_model  # Restore original model

    def get_client_info(self) -> Dict[str, Any]:
        """Get information about the client configuration."""
        return {
            "model": self.model,
            "fallback_model": self.fallback_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "max_response_length": self.max_response_length,
            "api_url": self.api_url,
            "has_api_key": bool(self.api_key),
            "guardrails_enabled": list(self.guardrails.keys())
        }

    def __del__(self):
        """Clean up session on destruction."""
        if hasattr(self, 'session'):
            self.session.close()


# Convenience function for simple usage
def create_llm_client(config_type: str = "conversation") -> LLMClient:
    """
    Create and return a configured LLM client.
    
    Args:
        config_type: Configuration type ('conversation' or 'summary')
        
    Returns:
        Configured LLMClient instance
        
    Raises:
        LLMClientError: If client cannot be initialized
    """
    try:
        return LLMClient(config_type)
    except Exception as e:
        logger.error(f"Failed to create LLM client: {e}")
        raise LLMClientError(f"Failed to initialize LLM client: {str(e)}")


# Simple test function
def test_client():
    """Test function for development."""
    try:
        client = create_llm_client("conversation")
        print("✅ LLM Client initialized successfully")
        print(f"📋 Client info: {client.get_client_info()}")
        
        # Test with a simple prompt
        response = client.generate(
            "You are a helpful assistant.",
            "Say hello in a friendly way."
        )
        print(f"🤖 Test response: {response}")
        
    except LLMClientError as e:
        print(f"❌ LLM Client error: {e}")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")


if __name__ == "__main__":
    test_client()