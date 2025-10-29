#!/usr/bin/env python3
"""
AI Debate System - MVP
A script that conducts debates between two AI agents on user-provided claims.
"""
# pylint:disable=line-too-long, raise-missing-from, broad-exception-caught

import os
import sys
import json
import argparse
import re
from typing import Literal
from dotenv import load_dotenv

from model_client import ModelClient, get_available_models, get_model_name

# Load environment variables
load_dotenv()

# Load shared messages
# pylint:disable=unspecified-encoding
with open(os.path.join(os.path.dirname(__file__), "shared", "messages.json"), "r") as f:
    MESSAGES = json.load(f)


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
        self.model_name = get_model_name(model_key)

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
            user_prompt = (
                "Make your opening argument. Provide your response in JSON format."
            )

        # Call model API
        response_text = self.model_client.generate(
            self.get_system_prompt(claim), user_prompt
        )

        # Try to extract JSON from the response
        try:
            # First, try parsing the entire response as JSON
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to find JSON within the response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    # Malformed response - this is an error, not a refusal
                    raise ValueError(
                        f"Could not parse JSON from response: {response_text[:200]}"
                    )
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
                "argument": "",
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
        self.model_name = get_model_name(model_key)

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

IMPORTANT: Do NOT explicitly reference DH numbers in your verdict explanation. These levels are for your internal evaluation only. Your explanation should be in natural language without mentioning the hierarchy.

Respond in valid JSON format:
{
    "verdict": "one of the four labels above",
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
                transcript += "[REFUSED TO ARGUE]\n"
                transcript += (
                    f"Reason: {turn.get('refusal_reason', 'No reason provided')}\n"
                )
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
            max_tokens=1500,
        )

        # Parse the response
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse JSON from response: {response_text}")

        # Validate the response
        if "verdict" not in result or "explanation" not in result:
            raise ValueError("Judge response missing required fields")

        valid_verdicts = [
            "supported",
            "contradicted",
            "misleading",
            "needs more evidence",
        ]
        if result["verdict"] not in valid_verdicts:
            raise ValueError(f"Invalid verdict: {result['verdict']}")

        return result


# pylint:disable=too-many-arguments, too-many-positional-arguments
def format_debate_output(
    claim: str,
    debate_history: list[dict],
    verdict: dict,
    pro_model: str,
    con_model: str,
    judge_model: str,
) -> str:
    """Format the debate for console output."""
    output = "\n" + "=" * 80 + "\n"
    output += "AI DEBATE SYSTEM\n"
    output += "=" * 80 + "\n\n"

    output += f"CLAIM: {claim}\n\n"
    output += "MODELS:\n"
    output += f"  Pro: {pro_model}\n"
    output += f"  Con: {con_model}\n"
    output += f"  Judge: {judge_model}\n\n"

    output += "=" * 80 + "\n"
    output += "DEBATE TRANSCRIPT\n"
    output += "=" * 80 + "\n\n"

    for i, turn in enumerate(debate_history, 1):
        side_label = (
            "PRO (Supporting)" if turn["position"] == "pro" else "CON (Opposing)"
        )
        model_name = turn.get("model", "Unknown")
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


# pylint:disable=too-many-locals, too-many-branches, too-many-statements
def run_debate(
    claim: str, turns: int, pro_model: str, con_model: str, judge_model: str
) -> None:
    """
    Run a complete debate on the given claim.

    Args:
        claim: The claim to debate
        turns: Number of turns per side (total turns = turns * 2)
        pro_model: Model key for pro debater
        con_model: Model key for con debater
        judge_model: Model key for judge
    """
    print(f"\n{MESSAGES['start'].replace('{turns}', str(turns))}")
    print(f"Claim: {claim}")
    print(
        f"Pro: {get_model_name(pro_model)}, Con: {get_model_name(con_model)}, Judge: {get_model_name(judge_model)}\n"
    )

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
        print(
            MESSAGES["turn"]
            .replace("{turn}", str(turn + 1))
            .replace("{total_turns}", str(turns))
        )

        # Pro side argues
        print(MESSAGES["pro_turn"].replace("{model_name}", get_model_name(pro_model)))
        try:
            pro_arg = pro_debater.make_argument(claim, debate_history)
            debate_history.append(pro_arg)

            # Display the argument immediately
            print(f"\n  {'='*60}")
            if pro_arg.get("refused", False):
                print("  PRO SIDE DECLINED TO ARGUE")
                print(
                    f"  Reason: {pro_arg.get('refusal_reason', 'No reason provided')}"
                )
                debate_shortened = True
            else:
                print(f"  Source: {pro_arg['url']}")
                print(f"  Quote: \"{pro_arg['quote']}\"")
                print(f"  Context: {pro_arg['context']}")
                print(f"  Argument: {pro_arg['argument']}")
            print(f"  {'='*60}\n")
        except RuntimeError as e:
            # API errors - inform user and exit
            print(f"\n  API Error from Pro debater: {e}", file=sys.stderr)
            print("  Cannot continue debate due to API issues.\n", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            # Malformed response - inform user and exit
            print(f"\n  Response Error from Pro debater: {e}", file=sys.stderr)
            print(
                "  Cannot continue debate due to malformed response.\n", file=sys.stderr
            )
            sys.exit(1)
        except Exception as e:
            # Unexpected error
            print(f"\n  Unexpected error from Pro debater: {e}", file=sys.stderr)
            sys.exit(1)

        # Con side argues
        print(MESSAGES["con_turn"].replace("{model_name}", get_model_name(con_model)))
        try:
            con_arg = con_debater.make_argument(claim, debate_history)
            debate_history.append(con_arg)

            # Display the argument immediately
            print(f"\n  {'='*60}")
            if con_arg.get("refused", False):
                print("  CON SIDE DECLINED TO ARGUE")
                print(
                    f"  Reason: {con_arg.get('refusal_reason', 'No reason provided')}"
                )
                debate_shortened = True
            else:
                print(f"  Source: {con_arg['url']}")
                print(f"  Quote: \"{con_arg['quote']}\"")
                print(f"  Context: {con_arg['context']}")
                print(f"  Argument: {con_arg['argument']}")
            print(f"  {'='*60}\n")
        except RuntimeError as e:
            # API errors - inform user and exit
            print(f"\n  API Error from Con debater: {e}", file=sys.stderr)
            print("  Cannot continue debate due to API issues.\n", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            # Malformed response - inform user and exit
            print(f"\n  Response Error from Con debater: {e}", file=sys.stderr)
            print(
                "  Cannot continue debate due to malformed response.\n", file=sys.stderr
            )
            sys.exit(1)
        except Exception as e:
            # Unexpected error
            print(f"\n  Unexpected error from Con debater: {e}", file=sys.stderr)
            sys.exit(1)

        # If either side refused, stop the debate after allowing opponent one response
        if debate_shortened:
            print(MESSAGES["debate_shortened"])
            break

    # Judge the debate
    print(
        f"\n{MESSAGES['judge_deliberating'].replace('{model_name}', get_model_name(judge_model))}"
    )
    try:
        verdict = judge.judge_debate(claim, debate_history)
    except Exception as e:
        print(f"Error from judge: {e}", file=sys.stderr)
        sys.exit(1)

    # Output the results
    output = format_debate_output(
        claim,
        debate_history,
        verdict,
        get_model_name(pro_model),
        get_model_name(con_model),
        get_model_name(judge_model),
    )
    print(output)


def main():
    """Main entry point for the debate script."""
    available_models = get_available_models()

    parser = argparse.ArgumentParser(
        description="AI Debate System - Conduct structured debates on factual claims",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available models: {', '.join(available_models)}

Examples:
  python debate.py "Electric vehicles produce less CO2 than gas cars" --turns 2
  python debate.py "Coffee is good for your health" --pro-model gpt4 --con-model claude
  python debate.py "Climate change is real" --pro-model gemini --con-model grok --judge-model gpt4
        """,
    )

    parser.add_argument(
        "claim", type=str, help="The claim to debate (should be a factual statement)"
    )

    parser.add_argument(
        "--turns",
        type=int,
        default=2,
        choices=[1, 2, 3, 4, 5, 6],
        help="Number of turns per side (default: 2)",
    )

    parser.add_argument(
        "--pro-model",
        type=str,
        default="claude",
        choices=list(available_models),
        help="Model for pro side (default: claude)",
    )

    parser.add_argument(
        "--con-model",
        type=str,
        default="claude",
        choices=list(available_models),
        help="Model for con side (default: claude)",
    )

    parser.add_argument(
        "--judge-model",
        type=str,
        default="claude",
        choices=list(available_models),
        help="Model for judge (default: claude)",
    )

    args = parser.parse_args()

    # Run the debate
    try:
        run_debate(
            args.claim, args.turns, args.pro_model, args.con_model, args.judge_model
        )
    except KeyboardInterrupt:
        print("\n\nDebate interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
