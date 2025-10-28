#!/usr/bin/env python3
"""
AI Debate System - MVP
A script that conducts debates between two AI agents on user-provided claims.
"""

import os
import sys
import json
import argparse
from typing import Literal
from anthropic import Anthropic
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


class Debater:
    """An AI agent that argues for or against a claim."""

    def __init__(self, position: Literal["pro", "con"], api_key: str):
        """
        Initialize a debater.

        Args:
            position: Whether this debater argues "pro" (for) or "con" (against) the claim
            api_key: Anthropic API key
        """
        self.position = position
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-opus-20240229"

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
        messages = []

        # Add debate history (filter out refusals - opponent doesn't see them)
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

            messages.append({
                "role": "user",
                "content": f"Here is the debate history so far. Now make your next argument.{history_text}\n\nProvide your response in JSON format."
            })
        else:
            messages.append({
                "role": "user",
                "content": "Make your opening argument. Provide your response in JSON format."
            })

        # Call Claude API with proper error handling
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=self.get_system_prompt(claim),
                messages=messages
            )
        except Exception as e:
            # API errors - re-raise to be handled by caller
            error_type = type(e).__name__
            raise RuntimeError(f"API error ({error_type}): {str(e)}")

        # Parse the response
        response_text = response.content[0].text

        # Try to extract JSON from the response
        try:
            # First, try parsing the entire response as JSON
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to find JSON within the response
            import re
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

        # Valid argument - add position and return
        result["position"] = self.position
        result["refused"] = False

        return result


class Judge:
    """An AI agent that judges the outcome of a debate."""

    def __init__(self, api_key: str):
        """
        Initialize the judge.

        Args:
            api_key: Anthropic API key
        """
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-opus-20240229"

    def get_system_prompt(self) -> str:
        """Generate the system prompt for the judge."""
        return """You are an impartial judge evaluating a debate about a factual claim.

Your task: Review the complete debate transcript and determine the verdict.

You must choose ONE of these four labels:
1. "supported" - The claim is well-supported by the evidence presented
2. "contradicted" - The claim is contradicted by the evidence presented
3. "misleading" - The claim is technically true but misleading or lacks important context
4. "needs more evidence" - The debate did not provide sufficient evidence to make a determination

Respond in valid JSON format:
{
    "verdict": "one of the four labels above",
    "explanation": "A brief explanation of your reasoning (2-3 sentences)"
}

Consider:
- Quality and credibility of sources cited
- Strength of arguments on both sides
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

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            system=self.get_system_prompt(),
            messages=[{
                "role": "user",
                "content": f"{transcript}\n\nProvide your verdict in JSON format."
            }]
        )

        # Parse the response
        response_text = response.content[0].text

        # Try to extract JSON from the response
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            import re
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


def format_debate_output(claim: str, debate_history: list[dict], verdict: dict) -> str:
    """Format the debate for console output."""
    output = "\n" + "=" * 80 + "\n"
    output += "AI DEBATE SYSTEM\n"
    output += "=" * 80 + "\n\n"

    output += f"CLAIM: {claim}\n\n"
    output += "=" * 80 + "\n"
    output += "DEBATE TRANSCRIPT\n"
    output += "=" * 80 + "\n\n"

    for i, turn in enumerate(debate_history, 1):
        side_label = "PRO (Supporting)" if turn['position'] == "pro" else "CON (Opposing)"
        output += f"Turn {i} - {side_label}\n"
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
    output += "JUDGE'S VERDICT\n"
    output += "=" * 80 + "\n\n"
    output += f"Verdict: {verdict['verdict'].upper()}\n\n"
    output += f"Explanation: {verdict['explanation']}\n\n"
    output += "=" * 80 + "\n"

    return output


def run_debate(claim: str, turns: int, api_key: str) -> None:
    """
    Run a complete debate on the given claim.

    Args:
        claim: The claim to debate
        turns: Number of turns per side (total turns = turns * 2)
        api_key: Anthropic API key
    """
    print(f"\nStarting debate with {turns} turns per side...")
    print(f"Claim: {claim}\n")

    # Initialize agents
    pro_debater = Debater("pro", api_key)
    con_debater = Debater("con", api_key)
    judge = Judge(api_key)

    # Run the debate
    debate_history = []
    debate_shortened = False

    for turn in range(turns):
        print(f"Turn {turn + 1}/{turns}...")

        # Pro side argues
        print("  Pro side is arguing...")
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
        print("  Con side is arguing...")
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
    print("\nJudge is deliberating...")
    try:
        verdict = judge.judge_debate(claim, debate_history)
    except Exception as e:
        print(f"Error from judge: {e}", file=sys.stderr)
        sys.exit(1)

    # Output the results
    output = format_debate_output(claim, debate_history, verdict)
    print(output)


def main():
    """Main entry point for the debate script."""
    parser = argparse.ArgumentParser(
        description="AI Debate System - Conduct structured debates on factual claims",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python debate.py "Electric vehicles produce less CO2 than gas cars" --turns 2
  python debate.py "Coffee is good for your health" --turns 4
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

    args = parser.parse_args()

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        print("Please create a .env file with your API key or export it:", file=sys.stderr)
        print("  export ANTHROPIC_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    # Run the debate
    try:
        run_debate(args.claim, args.turns, api_key)
    except KeyboardInterrupt:
        print("\n\nDebate interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
