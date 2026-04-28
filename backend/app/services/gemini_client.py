import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from groq import Groq
from backend.app import config

# Logger setup
logger = logging.getLogger("crisisai.gemini_client")

class GeminiClient:
    """
    Client for interacting with Google Gemini API with built-in 
    circuit breaker pattern and Groq fallback.
    """

    def __init__(self):
        # API Keys from config
        self.gemini_api_key = config.GEMINI_API_KEY
        self.groq_api_key = config.GROQ_API_KEY

        # Groq model configuration
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.GROQ_FALLBACK_MODELS = [
            os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            "llama-3.1-8b-instant",
            "gemma2-9b-it"
        ]

        # Configure Gemini
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
        
        # Groq Client
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None

        # Safety Settings - BLOCK_NONE IS INTENTIONAL
        # BLOCK_NONE is intentional — emergency content is often blocked by default safety settings.
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        # Circuit Breaker State
        self.failure_count = 0
        self.circuit_open = False
        self.circuit_opened_at: Optional[datetime] = None
        self.FAILURE_THRESHOLD = 3
        self.CIRCUIT_TIMEOUT_SECONDS = 300  # 5 minutes

    def _is_circuit_open(self) -> bool:
        """Checks if the circuit breaker is open or needs reset."""
        if not self.circuit_open:
            return False
        
        # Check if timeout has passed
        if self.circuit_opened_at and (datetime.now() - self.circuit_opened_at).total_seconds() > self.CIRCUIT_TIMEOUT_SECONDS:
            self.reset_circuit()
            return False
            
        return True

    def reset_circuit(self):
        """Resets the circuit breaker state."""
        self.failure_count = 0
        self.circuit_open = False
        self.circuit_opened_at = None
        logger.warning("Circuit breaker reset. Gemini is primary again.")

    def _record_failure(self):
        """Records a failure and opens the circuit if threshold is reached."""
        self.failure_count += 1
        if self.failure_count >= self.FAILURE_THRESHOLD:
            self.circuit_open = True
            self.circuit_opened_at = datetime.now()
            logger.warning("Circuit breaker OPEN. Switching to Groq fallback for 5 minutes.")

    def _groq_generate(self, prompt: str) -> str:
        """Fallback generation using Groq fallback models."""
        if not self.groq_client:
            raise RuntimeError("Groq API key missing during fallback attempt.")
        
        last_error = ""
        for current_model in self.GROQ_FALLBACK_MODELS:
            try:
                completion = self.groq_client.chat.completions.create(
                    model=current_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1024
                )
                return completion.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Groq model {current_model} failed: {e}")
                last_error = str(e)
                continue
        
        raise RuntimeError(f"Both Gemini and Groq failed... {last_error}")

    def generate(self, prompt: str, json_mode: bool = False) -> str:
        """Generates content using Gemini or fallback to Groq."""
        logger.debug(f"Generating content (json_mode={json_mode})")

        # Check circuit breaker
        if self._is_circuit_open():
            return self._groq_generate(prompt)

        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            generation_config = {}
            if json_mode:
                generation_config["response_mime_type"] = "application/json"

            response = model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config=generation_config
            )
            
            # Reset failure count on success (but don't reset circuit if it was open)
            self.failure_count = 0
            return response.text

        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            self._record_failure()
            return self._groq_generate(prompt)

    async def stream_generate(self, prompt: str) -> AsyncGenerator[str, None]:
        """Asynchronously streams generated content."""
        logger.debug("Streaming content generation")

        # Check circuit breaker
        if self._is_circuit_open():
            yield self._groq_generate(prompt)
            return

        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            response = model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
            
            self.failure_count = 0

        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            self._record_failure()
            # Yield full Groq fallback response as a single chunk
            yield self._groq_generate(prompt)
