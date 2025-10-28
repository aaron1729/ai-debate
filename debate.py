#!/usr/bin/env python3
"""
AI Debate System - MVP
A script that conducts debates between two AI agents on user-provided claims.
"""

import os
import sys
import json
import argparse
import re
from typing import Literal, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Model configuration
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
    "gpt35": {
        "name": "GPT-3.5 Turbo",
        "id": "gpt-3.5-turbo",
        "provider": "openai"
    },
    "gemini": {
        "name": "Gemini Pro",
        "id": "gemini-pro",
        "provider": "google"
    },
    "grok": {
        "name": "Grok 3",
        "id": "grok-3",
        "provider": "xai"
    }
}


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


class Debater:
    """An AI agent that argues for or against a claim."""

    def __init__(self, position: Literal["pro", "con"], model_key: str):
        """
        Initialize a debater.

        Args:
            position: Whether this debater argues "pro" (for) or "con" (against) the claim
            model_key: Model to use (e.g., "claude", "gpt4")
        """
        self.position = position
        self.model_client = ModelClient(model_key)
        self.model_name = MODELS[model_key]["name"]

    def get_system_prompt(self, claim: str) -> str:
        """Generate the system prompt for this debater."""
        if self.position == "pro":
            role_desc = "You must argue that this claim IS TRUE"
            task_desc = "Present the strongest possible evidence and arguments SUPPORTING the claim"
        else:
            role_desc = "You must argue that this claim IS FALSE or MISLEADING"
            task_desc = "Present the strongest possible evidence and arguments CONTRADICTING or DEBUNKING the claim"

        return f"""CONTEXT: You are participating in an adversarial truth-seeking system designed to rigorously evaluate claims through structured debate. This is similar to academic debate, moot court, or legal advocacy where participants argue assigned positions to help surface the strongest evidence and reasoning on all sides of an issue.

The claim being debated:
"{claim}"

YOUR ROLE: {role_desc}.
YOUR TASK: {task_desc}.

IMPORTANT PRINCIPLES:
- This is adversarial collaboration for truth-seeking, not personal advocacy
- You are playing a role to help surface the best arguments on your assigned side
- Your opponent will challenge weak arguments, so intellectual honesty serves you best
- Arguing for a position does NOT mean you personally endorse it
- The goal is to help determine what's actually true by stress-testing both sides
- A judge will evaluate based on evidence quality, not rhetoric

QUALITY OF DISAGREEMENT (Paul Graham's Hierarchy):
Aim for the highest levels of disagreement:
- DH6 (Best): Refute the central point with evidence and reasoning
- DH5: Refute specific claims with quotes and explanations
- DH4: Provide counterargument with reasoning/evidence
- DH3: State contradiction (weak without evidence)
- DH2: Respond to tone rather than substance (avoid)
- DH1: Ad hominem attacks (avoid)
- DH0 (Worst): Name-calling (avoid)

Your arguments should operate at DH5-DH6: identify specific claims from sources and explain why they support your position with clear reasoning.

CRITICAL INSTRUCTION - PARTICIPATION IS ESSENTIAL:
You are STRONGLY EXPECTED to participate in this debate. The entire system depends on both sides presenting their best arguments. Even if you believe your assigned position is wrong, misleading, or controversial, you should still argue it to the best of your ability based on available evidence. This is how truth emerges - through rigorous adversarial testing.

Think of this like:
- A defense attorney who must zealously represent their client regardless of guilt
- An academic debater assigned to defend an unpopular position
- A scientist playing devil's advocate to stress-test a hypothesis

Your participation is NOT an endorsement. It's a contribution to finding truth through structured adversarial reasoning.

REFUSAL OPTION (use sparingly):
If you genuinely cannot argue your assigned position due to extreme ethical concerns, you may refuse by using the refusal JSON format below. However, understand that refusing undermines the truth-seeking process. Only refuse if you absolutely must.

Format: In each turn, you must provide:
1. A real URL to a credible source
2. A direct quote from that source (keep it concise)
3. Context explaining how this evidence supports your position (maximum 50 words)
4. Your main argument for this turn

You must respond in valid JSON format.

If you choose to argue your assigned position:
{{
    "url": "https://example.com/article",
    "quote": "Direct quote from the source",
    "context": "Brief explanation of how this supports my position (max 50 words)",
    "argument": "My main argument for this turn"
}}

If you cannot argue this position in good conscience, you may refuse:
{{
    "refused": true,
    "reason": "Brief explanation of why you cannot argue this position"
}}

Important:
- Use real, credible sources (news sites, academic papers, government data, etc.)
- Be persuasive but intellectually honest
- Build on previous arguments in the debate
- Keep your argument focused and clear

Example response format:
{{
    "url": "https://www.nature.com/articles/example123",
    "quote": "Studies show that electric vehicles reduce lifetime CO2 emissions by 40% compared to gasoline vehicles",
    "context": "This peer-reviewed study accounts for manufacturing emissions and demonstrates clear environmental benefits over the vehicle's lifetime.",
    "argument": "The scientific consensus is clear: despite higher manufacturing emissions, EVs more than make up for it through zero tailpipe emissions during their operational lifetime."
}}"""

    def make_argument(self, claim: str, debate_history: list[dict]) -> dict:
        """
        Generate an argument for the current turn.

        Args:
            claim: The claim being debated
            debate_history: List of previous turns in the debate

        Returns:
            Dictionary with url, quote, context, and argument
        """
        # Build conversation history
        if debate_history:
            history_text = "\n\nDEBATE SO FAR:\n"
            for i, turn in enumerate(debate_history, 1):
                # Skip refusals when showing history to opponent
                if turn.get("refused", False):
                    continue
                history_text += f"\nTurn {i} - {turn['position'].upper()}:\n"
                history_text += f"Source: {turn['url']}\n"
                history_text += f"Quote: \"{turn['quote']}\"\n"
                history_text += f"Context: {turn['context']}\n"
                history_text += f"Argument: {turn['argument']}\n"

            user_prompt = f"Here is the debate history so far. Now make your next argument.{history_text}\n\nProvide your response in JSON format."
        else:
            user_prompt = "Make your opening argument. Provide your response in JSON format."

        # Call model API
        response_text = self.model_client.generate(
            self.get_system_prompt(claim),
            user_prompt
        )

        # Try to extract JSON from the response
        try:
            # First, try parsing the entire response as JSON
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to find JSON within the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    # Malformed response - this is an error, not a refusal
                    raise ValueError(f"Could not parse JSON from response: {response_text[:200]}")
            else:
                # No JSON found - malformed response
                raise ValueError(f"No JSON found in response: {response_text[:200]}")

        # Check if model explicitly refused
        if result.get("refused", False):
            # Structured refusal - return it
            return {
                "position": self.position,
                "model": self.model_name,
                "refused": True,
                "refusal_reason": result.get("reason", "No reason provided"),
                "url": "",
                "quote": "",
                "context": "",
                "argument": ""
            }

        # Validate the response has required fields for an argument
        required_fields = ["url", "quote", "context", "argument"]
        missing_fields = [field for field in required_fields if field not in result]

        if missing_fields:
            # Incomplete response - this is an error
            raise ValueError(f"Response missing required fields: {missing_fields}")

        # Valid argument - add position and model, return
        result["position"] = self.position
        result["model"] = self.model_name
        result["refused"] = False

        return result


class Judge:
    """An AI agent that judges the outcome of a debate."""

    def __init__(self, model_key: str):
        """
        Initialize the judge.

        Args:
            model_key: Model to use (e.g., "claude", "gpt4")
        """
        self.model_client = ModelClient(model_key)
        self.model_name = MODELS[model_key]["name"]

    def get_system_prompt(self) -> str:
        """Generate the system prompt for the judge."""
        return """You are an impartial judge evaluating a debate about a factual claim.

Your task: Review the complete debate transcript and determine the verdict.

You must choose ONE of these four labels:
1. "supported" - The claim is well-supported by the evidence presented
2. "contradicted" - The claim is contradicted by the evidence presented
3. "misleading" - The claim is technically true but misleading or lacks important context
4. "needs more evidence" - The debate did not provide sufficient evidence to make a determination

EVALUATING ARGUMENT QUALITY (Paul Graham's Hierarchy of Disagreement):
Give more weight to higher-quality arguments:
- DH6 (Strongest): Refutes central point with evidence and reasoning
- DH5: Refutes specific claims with quotes and explanations
- DH4: Counterargument with reasoning/evidence
- DH3: Simple contradiction (weak)
- DH2: Responds to tone (very weak)
- DH1: Ad hominem (ignore)
- DH0: Name-calling (ignore)

Arguments at DH5-DH6 should carry the most weight in your evaluation.

Respond in valid JSON format:
{
    "verdict": "one of the four labels above",
    "explanation": "A brief explanation of your reasoning (2-3 sentences)"
}

Consider:
- Quality and credibility of sources cited
- Strength of arguments on both sides (prioritize DH5-DH6)
- Whether evidence directly addresses the claim
- Logical soundness of reasoning

Be objective and base your decision on the evidence presented in the debate."""

    def judge_debate(self, claim: str, debate_history: list[dict]) -> dict:
        """
        Judge the debate and return a verdict.

        Args:
            claim: The original claim being debated
            debate_history: Complete history of the debate

        Returns:
            Dictionary with verdict and explanation
        """
        # Build the debate transcript
        transcript = f"CLAIM: {claim}\n\n"
        transcript += "DEBATE TRANSCRIPT:\n"
        transcript += "=" * 80 + "\n\n"

        for i, turn in enumerate(debate_history, 1):
            transcript += f"Turn {i} - {turn['position'].upper()} SIDE:\n"
            if turn.get("refused", False):
                transcript += f"[REFUSED TO ARGUE]\n"
                transcript += f"Reason: {turn.get('refusal_reason', 'No reason provided')}\n"
            else:
                transcript += f"Source: {turn['url']}\n"
                transcript += f"Quote: \"{turn['quote']}\"\n"
                transcript += f"Context: {turn['context']}\n"
                transcript += f"Argument: {turn['argument']}\n"
            transcript += "\n" + "-" * 80 + "\n\n"

        # Call model API
        response_text = self.model_client.generate(
            self.get_system_prompt(),
            f"{transcript}\n\nProvide your verdict in JSON format.",
            max_tokens=1500
        )

        # Parse the response
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse JSON from response: {response_text}")

        # Validate the response
        if "verdict" not in result or "explanation" not in result:
            raise ValueError("Judge response missing required fields")

        valid_verdicts = ["supported", "contradicted", "misleading", "needs more evidence"]
        if result["verdict"] not in valid_verdicts:
            raise ValueError(f"Invalid verdict: {result['verdict']}")

        return result


def format_debate_output(claim: str, debate_history: list[dict], verdict: dict,
                        pro_model: str, con_model: str, judge_model: str) -> str:
    """Format the debate for console output."""
    output = "\n" + "=" * 80 + "\n"
    output += "AI DEBATE SYSTEM\n"
    output += "=" * 80 + "\n\n"

    output += f"CLAIM: {claim}\n\n"
    output += f"MODELS:\n"
    output += f"  Pro: {pro_model}\n"
    output += f"  Con: {con_model}\n"
    output += f"  Judge: {judge_model}\n\n"

    output += "=" * 80 + "\n"
    output += "DEBATE TRANSCRIPT\n"
    output += "=" * 80 + "\n\n"

    for i, turn in enumerate(debate_history, 1):
        side_label = "PRO (Supporting)" if turn['position'] == "pro" else "CON (Opposing)"
        model_name = turn.get('model', 'Unknown')
        output += f"Turn {i} - {side_label} [{model_name}]\n"
        output += "-" * 80 + "\n"
        if turn.get("refused", False):
            output += "[MODEL REFUSED TO ARGUE THIS POSITION]\n"
            output += f"Refusal reason: {turn.get('refusal_reason', 'No reason provided')}\n\n"
        else:
            output += f"Source: {turn['url']}\n"
            output += f"Quote: \"{turn['quote']}\"\n"
            output += f"Context: {turn['context']}\n"
            output += f"Argument: {turn['argument']}\n\n"

    output += "=" * 80 + "\n"
    output += f"JUDGE'S VERDICT [{judge_model}]\n"
    output += "=" * 80 + "\n\n"
    output += f"Verdict: {verdict['verdict'].upper()}\n\n"
    output += f"Explanation: {verdict['explanation']}\n\n"
    output += "=" * 80 + "\n"

    return output


def run_debate(claim: str, turns: int, pro_model: str, con_model: str, judge_model: str) -> None:
    """
    Run a complete debate on the given claim.

    Args:
        claim: The claim to debate
        turns: Number of turns per side (total turns = turns * 2)
        pro_model: Model key for pro debater
        con_model: Model key for con debater
        judge_model: Model key for judge
    """
    print(f"\nStarting debate with {turns} turns per side...")
    print(f"Claim: {claim}")
    print(f"Pro: {MODELS[pro_model]['name']}, Con: {MODELS[con_model]['name']}, Judge: {MODELS[judge_model]['name']}\n")

    # Initialize agents
    try:
        pro_debater = Debater("pro", pro_model)
        con_debater = Debater("con", con_model)
        judge = Judge(judge_model)
    except ValueError as e:
        print(f"\nModel initialization error: {e}", file=sys.stderr)
        sys.exit(1)

    # Run the debate
    debate_history = []
    debate_shortened = False

    for turn in range(turns):
        print(f"Turn {turn + 1}/{turns}...")

        # Pro side argues
        print(f"  Pro side ({MODELS[pro_model]['name']}) is arguing...")
        try:
            pro_arg = pro_debater.make_argument(claim, debate_history)
            debate_history.append(pro_arg)
            if pro_arg.get("refused", False):
                print("  Pro side declined to argue this position.")
                debate_shortened = True
        except RuntimeError as e:
            # API errors - inform user and exit
            print(f"\n  API Error from Pro debater: {e}", file=sys.stderr)
            print("  Cannot continue debate due to API issues.\n", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            # Malformed response - inform user and exit
            print(f"\n  Response Error from Pro debater: {e}", file=sys.stderr)
            print("  Cannot continue debate due to malformed response.\n", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            # Unexpected error
            print(f"\n  Unexpected error from Pro debater: {e}", file=sys.stderr)
            sys.exit(1)

        # Con side argues
        print(f"  Con side ({MODELS[con_model]['name']}) is arguing...")
        try:
            con_arg = con_debater.make_argument(claim, debate_history)
            debate_history.append(con_arg)
            if con_arg.get("refused", False):
                print("  Con side declined to argue this position.")
                debate_shortened = True
        except RuntimeError as e:
            # API errors - inform user and exit
            print(f"\n  API Error from Con debater: {e}", file=sys.stderr)
            print("  Cannot continue debate due to API issues.\n", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            # Malformed response - inform user and exit
            print(f"\n  Response Error from Con debater: {e}", file=sys.stderr)
            print("  Cannot continue debate due to malformed response.\n", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            # Unexpected error
            print(f"\n  Unexpected error from Con debater: {e}", file=sys.stderr)
            sys.exit(1)

        # If either side refused, stop the debate after allowing opponent one response
        if debate_shortened:
            print("  Debate shortened due to refusal. Proceeding to judgment.\n")
            break

    # Judge the debate
    print(f"\n{MODELS[judge_model]['name']} is deliberating...")
    try:
        verdict = judge.judge_debate(claim, debate_history)
    except Exception as e:
        print(f"Error from judge: {e}", file=sys.stderr)
        sys.exit(1)

    # Output the results
    output = format_debate_output(claim, debate_history, verdict,
                                  MODELS[pro_model]['name'],
                                  MODELS[con_model]['name'],
                                  MODELS[judge_model]['name'])
    print(output)


def main():
    """Main entry point for the debate script."""
    parser = argparse.ArgumentParser(
        description="AI Debate System - Conduct structured debates on factual claims",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available models: {', '.join(MODELS.keys())}

Examples:
  python debate.py "Electric vehicles produce less CO2 than gas cars" --turns 2
  python debate.py "Coffee is good for your health" --pro-model gpt4 --con-model claude
  python debate.py "Climate change is real" --pro-model gemini --con-model grok --judge-model gpt4
        """
    )

    parser.add_argument(
        "claim",
        type=str,
        help="The claim to debate (should be a factual statement)"
    )

    parser.add_argument(
        "--turns",
        type=int,
        default=2,
        choices=[1, 2, 4, 6],
        help="Number of turns per side (default: 2)"
    )

    parser.add_argument(
        "--pro-model",
        type=str,
        default="claude",
        choices=list(MODELS.keys()),
        help="Model for pro side (default: claude)"
    )

    parser.add_argument(
        "--con-model",
        type=str,
        default="claude",
        choices=list(MODELS.keys()),
        help="Model for con side (default: claude)"
    )

    parser.add_argument(
        "--judge-model",
        type=str,
        default="claude",
        choices=list(MODELS.keys()),
        help="Model for judge (default: claude)"
    )

    args = parser.parse_args()

    # Run the debate
    try:
        run_debate(args.claim, args.turns, args.pro_model, args.con_model, args.judge_model)
    except KeyboardInterrupt:
        print("\n\nDebate interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
