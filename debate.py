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
from datetime import datetime
from typing import Literal, Optional
from dotenv import load_dotenv
from experiment_store import SQLiteExperimentStore

# Load environment variables
load_dotenv()

# Load shared messages
with open(os.path.join(os.path.dirname(__file__), 'shared', 'messages.json'), 'r') as f:
    MESSAGES = json.load(f)

# Load valid topics
def load_topics():
    """Load valid topics from topics.json"""
    topics_file = os.path.join(os.path.dirname(__file__), 'topics.json')
    try:
        with open(topics_file, 'r') as f:
            topics = json.load(f)
            if isinstance(topics, list):
                return topics
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []

VALID_TOPICS = load_topics()

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

IMPORTANT: Do NOT explicitly reference DH numbers (like "DH5" or "DH6") in your actual argument text. These are for your internal guidance only. Your output should be natural prose without mentioning the hierarchy levels.

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

You must also provide a SCORE from 0 to 10 (or -1):
- 0 = Completely contradicted (strongest evidence against the claim)
- 1-4 = Contradicted with varying strength (1=very strong contradiction, 4=weak contradiction)
- 5 = Misleading/ambiguous (evidence on both sides, or technically true but missing context)
- 6-9 = Supported with varying strength (6=weak support, 9=very strong support)
- 10 = Completely supported (strongest evidence for the claim)
- -1 = Needs more evidence (insufficient information to determine)

The score provides nuance within each verdict category:
- "contradicted" typically maps to scores 0-4
- "misleading" typically maps to scores 3-7 (depending on which way it leans)
- "supported" typically maps to scores 6-10
- "needs more evidence" must use score -1

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

IMPORTANT: Do NOT explicitly reference DH numbers in your verdict explanation. These levels are for your internal evaluation only. Your explanation should be in natural language without mentioning the hierarchy.

Respond in valid JSON format:
{
    "verdict": "one of the four labels above",
    "score": integer from 0-10 or -1,
    "explanation": "A brief explanation of your reasoning (2-3 sentences)"
}

Consider:
- Quality and credibility of sources cited
- Strength of arguments on both sides (prioritize evidence-based refutation)
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
        if "verdict" not in result or "score" not in result or "explanation" not in result:
            raise ValueError("Judge response missing required fields (verdict, score, explanation)")

        valid_verdicts = ["supported", "contradicted", "misleading", "needs more evidence"]
        if result["verdict"] not in valid_verdicts:
            raise ValueError(f"Invalid verdict: {result['verdict']}")

        # Validate score
        if not isinstance(result["score"], int):
            raise ValueError(f"Score must be an integer, got: {type(result['score'])}")
        if result["score"] not in range(-1, 11):
            raise ValueError(f"Score must be -1 or 0-10, got: {result['score']}")

        # Validate score matches verdict
        if result["verdict"] == "needs more evidence" and result["score"] != -1:
            raise ValueError(f"Verdict 'needs more evidence' must have score -1, got: {result['score']}")

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
    output += f"Verdict: {verdict['verdict'].upper()}\n"
    output += f"Score: {verdict['score']} "
    if verdict['score'] == -1:
        output += "(needs more evidence)\n\n"
    elif verdict['score'] == 0:
        output += "(completely contradicted)\n\n"
    elif verdict['score'] == 10:
        output += "(completely supported)\n\n"
    else:
        output += f"(on scale from 0=contradicted to 10=supported)\n\n"
    output += f"Explanation: {verdict['explanation']}\n\n"
    output += "=" * 80 + "\n"

    return output


def create_experiment_json(claim: str, topic: Optional[str], claim_id: Optional[str],
                          gt_verdict: Optional[str], gt_source: Optional[str], gt_url: Optional[str],
                          debate_history: list[dict], verdict: dict, turns: int,
                          pro_model_key: str, con_model_key: str, judge_model_key: str,
                          pro_went_first: bool, timestamp: str, errors: list[dict]) -> dict:
    """
    Create experiment results in the standardized JSON format.

    Returns:
        Dictionary following the experiment schema
    """
    # Convert debate_history to transcript format
    transcript = []
    turn_num = 1
    for entry in debate_history:
        # Determine actual turn number (two debaters per turn)
        if entry['position'] == 'pro':
            if not pro_went_first:
                # If con went first, pro entries are second in each turn
                turn_for_entry = turn_num
            else:
                # If pro went first, increment turn after con's response
                turn_for_entry = (turn_num + 1) // 2 if turn_num > 1 else 1
        else:  # con
            if pro_went_first:
                turn_for_entry = turn_num
            else:
                turn_for_entry = (turn_num + 1) // 2 if turn_num > 1 else 1

        # Simplified: just use sequential turn numbers
        transcript_entry = {
            "turn": (turn_num + 1) // 2,
            "debater": entry['position'],
            "argument": entry.get('argument', ''),
            "source_url": entry.get('url', ''),
            "source_quote": entry.get('quote', '')
        }

        # Add refusal info if present
        if entry.get('refused', False):
            transcript_entry['refused'] = True
            transcript_entry['refusal_reason'] = entry.get('refusal_reason', '')

        transcript.append(transcript_entry)
        turn_num += 1

    result = {
        "claim_data": {
            "claim": claim
        },
        "ground_truth": {},
        "experiment_config": {
            "timestamp": timestamp,
            "models": {
                "pro": MODELS[pro_model_key]['id'],
                "con": MODELS[con_model_key]['id'],
                "judge": MODELS[judge_model_key]['id']
            },
            "turns": turns,
            "pro_went_first": pro_went_first
        },
        "debate_transcript": transcript,
        "judge_decision": {
            "verdict": verdict['verdict'],
            "score": verdict['score'],
            "reasoning": verdict['explanation']
        },
        "errors_or_refusals": errors
    }

    # Add optional fields if provided
    if topic:
        result["claim_data"]["topic"] = topic
    if claim_id:
        result["claim_data"]["claim_id"] = claim_id

    if gt_verdict:
        result["ground_truth"]["verdict"] = gt_verdict
    if gt_source:
        result["ground_truth"]["source"] = gt_source
    if gt_url:
        result["ground_truth"]["url"] = gt_url

    return result


def run_debate(claim: str, turns: int, pro_model: str, con_model: str, judge_model: str,
               pro_went_first: bool = True, topic: Optional[str] = None, claim_id: Optional[str] = None,
               gt_verdict: Optional[str] = None, gt_source: Optional[str] = None,
               gt_url: Optional[str] = None) -> int:
    """
    Run a complete debate on the given claim.

    Args:
        claim: The claim to debate
        turns: Number of turns per side (total turns = turns * 2)
        pro_model: Model key for pro debater
        con_model: Model key for con debater
        judge_model: Model key for judge
        pro_went_first: Whether pro debater goes first (default: True)
        topic: Optional topic category for the claim
        claim_id: Optional claim ID in format 'filename:index'
        gt_verdict: Optional ground truth verdict
        gt_source: Optional ground truth source
        gt_url: Optional ground truth URL

    Returns:
        Experiment ID in database
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    errors = []
    print(f"\n{MESSAGES['start'].replace('{turns}', str(turns))}")
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

    # Determine order of debaters
    if pro_went_first:
        first_debater = ("pro", pro_debater, pro_model, "pro_turn")
        second_debater = ("con", con_debater, con_model, "con_turn")
    else:
        first_debater = ("con", con_debater, con_model, "con_turn")
        second_debater = ("pro", pro_debater, pro_model, "pro_turn")

    for turn in range(turns):
        print(MESSAGES['turn'].replace('{turn}', str(turn + 1)).replace('{total_turns}', str(turns)))

        # Loop through both debaters in order
        for position_label, debater_obj, model_key, message_key in [first_debater, second_debater]:
            side_label = "PRO" if position_label == "pro" else "CON"
            print(MESSAGES[message_key].replace('{model_name}', MODELS[model_key]['name']))

            try:
                arg = debater_obj.make_argument(claim, debate_history)
                debate_history.append(arg)

                # Display the argument immediately
                print(f"\n  {'='*60}")
                if arg.get("refused", False):
                    print(f"  {side_label} SIDE DECLINED TO ARGUE")
                    print(f"  Reason: {arg.get('refusal_reason', 'No reason provided')}")
                    debate_shortened = True
                else:
                    print(f"  Source: {arg['url']}")
                    print(f"  Quote: \"{arg['quote']}\"")
                    print(f"  Context: {arg['context']}")
                    print(f"  Argument: {arg['argument']}")
                print(f"  {'='*60}\n")
            except RuntimeError as e:
                # API errors - inform user and exit
                print(f"\n  API Error from {side_label} debater: {e}", file=sys.stderr)
                print("  Cannot continue debate due to API issues.\n", file=sys.stderr)
                sys.exit(1)
            except ValueError as e:
                # Malformed response - inform user and exit
                print(f"\n  Response Error from {side_label} debater: {e}", file=sys.stderr)
                print("  Cannot continue debate due to malformed response.\n", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                # Unexpected error
                print(f"\n  Unexpected error from {side_label} debater: {e}", file=sys.stderr)
                sys.exit(1)

            # If this side refused, allow opponent one response then stop
            if debate_shortened:
                break

        # If either side refused, stop the debate
        if debate_shortened:
            print(MESSAGES['debate_shortened'])
            break

    # Judge the debate
    print(f"\n{MESSAGES['judge_deliberating'].replace('{model_name}', MODELS[judge_model]['name'])}")
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

    # Save to database
    experiment_data = create_experiment_json(
        claim, topic, claim_id, gt_verdict, gt_source, gt_url,
        debate_history, verdict, turns,
        pro_model, con_model, judge_model,
        pro_went_first, timestamp, errors
    )

    store = SQLiteExperimentStore()
    experiment_id = store.save(experiment_data)
    print(f"\nExperiment saved to database (ID: {experiment_id})")

    return experiment_id


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
        choices=[1, 2, 3, 4, 5, 6],
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

    parser.add_argument(
        "--pro-first",
        action="store_true",
        default=True,
        help="Pro debater goes first (default: True)"
    )

    parser.add_argument(
        "--con-first",
        action="store_true",
        help="Con debater goes first (overrides --pro-first)"
    )

    parser.add_argument(
        "--topic",
        type=str,
        choices=VALID_TOPICS if VALID_TOPICS else None,
        help=f"Topic category for the claim (optional){f': {', '.join(VALID_TOPICS)}' if VALID_TOPICS else ''}"
    )

    parser.add_argument(
        "--gt-verdict",
        type=str,
        choices=["supported", "contradicted", "misleading", "needs more evidence"],
        help="Ground truth verdict (optional)"
    )

    parser.add_argument(
        "--gt-source",
        type=str,
        help="Ground truth source (e.g., 'gpt5' or publisher name)"
    )

    parser.add_argument(
        "--gt-url",
        type=str,
        help="Ground truth URL (optional)"
    )

    parser.add_argument(
        "--claim-id",
        type=str,
        help="Claim ID in format 'filename:index' (e.g., 'claims_gpt5_01.json:0')"
    )

    args = parser.parse_args()

    # Determine who goes first
    pro_went_first = not args.con_first

    # Run the debate
    try:
        run_debate(
            args.claim, args.turns, args.pro_model, args.con_model, args.judge_model,
            pro_went_first=pro_went_first,
            topic=args.topic,
            claim_id=args.claim_id,
            gt_verdict=args.gt_verdict,
            gt_source=args.gt_source,
            gt_url=args.gt_url
        )
    except KeyboardInterrupt:
        print("\n\nDebate interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
