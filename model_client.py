import os
from typing import Iterable

# Model configuration
# fmt: off
MODELS = {
    "claude": {
        "name": "Claude Sonnet 4.5",
        "id": "claude-sonnet-4-5-20250929",
        "provider": "anthropic"
    },
    "gpt4": {
        "name": "GPT-4",
        "id": "gpt-4-turbo-preview",
        "provider": "openai"
    },
    "gemini": {
        "name": "Gemini 2.5 Flash",
        "id": "gemini-2.5-flash",
        "provider": "google"
    },
    "grok": {
        "name": "Grok 3",
        "id": "grok-3",
        "provider": "xai"
    }
}
# fmt: on


class ModelClient:
    """Unified interface for different LLM providers."""

    def __init__(self, model_key: str):
        """
        Initialize model client.

        Args:
            model_key: Key from MODELS dict (e.g., "claude", "gpt4")
        """
        if model_key not in MODELS:
            raise ValueError(f"Unknown model: {model_key}. Available: {list(MODELS.keys())}")

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
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1"
            )

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
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
                    messages=[{"role": "user", "content": user_prompt}]
                )
                return response.content[0].text

            elif self.provider in ["openai", "xai"]:
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response.choices[0].message.content

            elif self.provider == "google":
                # Gemini doesn't have explicit system prompt, prepend to user message
                combined_prompt = f"{system_prompt}\n\n{user_prompt}"
                response = self.client.generate_content(combined_prompt)
                return response.text

        except Exception as e:
            error_type = type(e).__name__
            raise RuntimeError(f"API error ({error_type}): {str(e)}")

def get_model_name(model_key: str) -> str:
    """
    The full name from just the model key
    e.g.
    claude -> Claude Sonnet 4.5
    """
    return MODELS[model_key]["name"]

def get_model_id(model_key: str) -> str:
    """
    The id from just the model key
    e.g.
    claude -> claude-sonnet-4-5-20250929
    """
    return MODELS[model_key]["id"]

def all_available_model_keys() -> Iterable[str]:
    """
    The keys of all available models
    """
    return MODELS.keys()

def is_not_an_available_model(model_key: str) -> bool:
    """
    This model key does not correspond to an existing/available model
    so we cannot get it's name, id or provider
    """
    return model_key not in MODELS

def average_cost_estimator(cost_per_judgment: dict[str,float], default_cost: float = 0.01) -> float:
    """
    Providing costs for each model by ID
    give the average if randomly selected one of MODELS uniformly
    """
    total_cost = 0
    for judge_id in MODELS.values():
        total_cost += cost_per_judgment.get(judge_id['id'], default_cost)

    avg_cost_per_judgment = total_cost / len(MODELS)
    return avg_cost_per_judgment
