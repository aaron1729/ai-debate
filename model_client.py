"""
Model configuration
The portions that are not specific to debates
These are in order to encapsulate away details of different model APIs
"""

# pylint:disable=import-outside-toplevel
from typing import Iterable
import os

# fmt: off
MODELS = {
    "claude": {
        "name": "Claude Sonnet 4.5",
        "id": "claude-sonnet-4-5-20250929",
        "provider": "anthropic",
    },
    "gpt4": {
        "name": "GPT-4",
        "id": "gpt-4-turbo-preview",
        "provider": "openai"
    },
    "gemini": {
        "name": "Gemini 2.5 Flash",
        "id": "gemini-2.5-flash",
        "provider": "google",
    },
    "grok": {
        "name": "Grok 3",
        "id": "grok-3",
        "provider": "xai"
    },
}
# fmt: on

#pylint:disable=too-few-public-methods
class ModelClient:
    """Unified interface for different LLM providers."""

    def __init__(self, model_key: str):
        """
        Initialize model client.

        Args:
            model_key: Key from MODELS dict (e.g., "claude", "gpt4")
        """
        if model_key not in MODELS:
            raise ValueError(
                f"Unknown model: {model_key}. Available: {list(MODELS.keys())}"
            )

        self.model_config = MODELS[model_key]
        self.model_key = model_key
        self.provider = self.model_config["provider"]
        self.model_id = self.model_config["id"]

        # Initialize appropriate client
        if self.provider == "anthropic":
            from anthropic import Anthropic

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in environment")
            self.client = Anthropic(api_key=api_key)
        elif self.provider == "openai":
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in environment")
            self.client = OpenAI(api_key=api_key)
        elif self.provider == "google":
            import google.generativeai as genai

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set in environment")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model_id)
        elif self.provider == "xai":
            from openai import OpenAI

            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                raise ValueError("XAI_API_KEY not set in environment")
            # Grok uses OpenAI-compatible API
            self.client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    def generate(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 2000
    ) -> str:
        """
        Generate a response from the model.

        Args:
            system_prompt: System instructions
            user_prompt: User message
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model_id,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return response.content[0].text

            if self.provider in ["openai", "xai"]:
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return response.choices[0].message.content

            if self.provider == "google":
                # Gemini doesn't have explicit system prompt, prepend to user message
                combined_prompt = f"{system_prompt}\n\n{user_prompt}"
                response = self.client.generate_content(combined_prompt)
                return response.text

        except Exception as e:
            error_type = type(e).__name__
            #pylint:disable=raise-missing-from
            raise RuntimeError(f"API error ({error_type}): {str(e)}")
        raise RuntimeError(f"Unreachable {self.provider} is not accounted for")


def get_model_name(model_key: str) -> str:
    """
    What is the full model name based on just the key
    """
    return MODELS[model_key]["name"]


def get_available_models() -> Iterable[str]:
    """
    The model keys which are available
    """
    return MODELS.keys()
