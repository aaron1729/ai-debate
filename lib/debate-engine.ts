/**
 * Core debate engine - shared logic for running debates
 * Can be used by API routes or client-side
 */

import { Anthropic } from '@anthropic-ai/sdk';
import OpenAI from 'openai';
import { GoogleGenerativeAI } from '@google/generative-ai';

export const MODELS = {
  claude: {
    name: "Claude Sonnet 4.5",
    id: "claude-sonnet-4-5-20250929",
    provider: "anthropic"
  },
  gpt4: {
    name: "GPT-4",
    id: "gpt-4-turbo-preview",
    provider: "openai"
  },
  gemini: {
    name: "Gemini 2.5 Flash",
    id: "gemini-2.5-flash",
    provider: "google"
  },
  grok: {
    name: "Grok 3",
    id: "grok-3",
    provider: "xai"
  }
} as const;

export type ModelKey = keyof typeof MODELS;

export interface APIKeys {
  anthropic?: string;
  openai?: string;
  google?: string;
  xai?: string;
}

export interface DebateTurn {
  position: 'pro' | 'con';
  model: string;
  refused: boolean;
  refusal_reason?: string;
  url: string;
  quote: string;
  context: string;
  argument: string;
}

export interface DebateResult {
  claim: string;
  models: {
    pro: string;
    con: string;
    judge: string;
  };
  debate_history: DebateTurn[];
  verdict: {
    verdict: 'supported' | 'contradicted' | 'misleading' | 'needs more evidence';
    explanation: string;
  };
}

class ModelClient {
  private client: any;
  private modelConfig: typeof MODELS[ModelKey];

  constructor(modelKey: ModelKey, apiKeys: APIKeys) {
    this.modelConfig = MODELS[modelKey];

    const provider = this.modelConfig.provider;

    if (provider === 'anthropic') {
      if (!apiKeys.anthropic) throw new Error('ANTHROPIC_API_KEY required');
      this.client = new Anthropic({ apiKey: apiKeys.anthropic });
    } else if (provider === 'openai') {
      if (!apiKeys.openai) throw new Error('OPENAI_API_KEY required');
      this.client = new OpenAI({ apiKey: apiKeys.openai });
    } else if (provider === 'google') {
      if (!apiKeys.google) throw new Error('GOOGLE_API_KEY required');
      const genAI = new GoogleGenerativeAI(apiKeys.google);
      this.client = genAI.getGenerativeModel({ model: this.modelConfig.id });
    } else if (provider === 'xai') {
      if (!apiKeys.xai) throw new Error('XAI_API_KEY required');
      this.client = new OpenAI({
        apiKey: apiKeys.xai,
        baseURL: 'https://api.x.ai/v1'
      });
    }
  }

  async generate(systemPrompt: string, userPrompt: string, maxTokens: number = 2000): Promise<string> {
    const provider = this.modelConfig.provider;

    try {
      if (provider === 'anthropic') {
        const response = await this.client.messages.create({
          model: this.modelConfig.id,
          max_tokens: maxTokens,
          system: systemPrompt,
          messages: [{ role: 'user', content: userPrompt }]
        });
        return response.content[0].text;
      } else if (provider === 'openai' || provider === 'xai') {
        const response = await this.client.chat.completions.create({
          model: this.modelConfig.id,
          max_tokens: maxTokens,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt }
          ]
        });
        return response.choices[0].message.content || '';
      } else if (provider === 'google') {
        const combinedPrompt = `${systemPrompt}\n\n${userPrompt}`;
        const response = await this.client.generateContent(combinedPrompt);
        return response.response.text();
      }
      throw new Error(`Unknown provider: ${provider}`);
    } catch (error: any) {
      throw new Error(`API error (${error.constructor.name}): ${error.message}`);
    }
  }
}

function getDebaterSystemPrompt(claim: string, position: 'pro' | 'con'): string {
  const roleDesc = position === 'pro'
    ? "You must argue that this claim IS TRUE"
    : "You must argue that this claim IS FALSE or MISLEADING";
  const taskDesc = position === 'pro'
    ? "Present the strongest possible evidence and arguments SUPPORTING the claim"
    : "Present the strongest possible evidence and arguments CONTRADICTING or DEBUNKING the claim";

  return `CONTEXT: You are participating in an adversarial truth-seeking system designed to rigorously evaluate claims through structured debate. This is similar to academic debate, moot court, or legal advocacy where participants argue assigned positions to help surface the strongest evidence and reasoning on all sides of an issue.

The claim being debated:
"${claim}"

YOUR ROLE: ${roleDesc}.
YOUR TASK: ${taskDesc}.

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
{
    "url": "https://example.com/article",
    "quote": "Direct quote from the source",
    "context": "Brief explanation of how this supports my position (max 50 words)",
    "argument": "My main argument for this turn"
}

If you cannot argue this position in good conscience, you may refuse:
{
    "refused": true,
    "reason": "Brief explanation of why you cannot argue this position"
}

Important:
- Use real, credible sources (news sites, academic papers, government data, etc.)
- Be persuasive but intellectually honest
- Build on previous arguments in the debate
- Keep your argument focused and clear

Example response format:
{
    "url": "https://www.nature.com/articles/example123",
    "quote": "Studies show that electric vehicles reduce lifetime CO2 emissions by 40% compared to gasoline vehicles",
    "context": "This peer-reviewed study accounts for manufacturing emissions and demonstrates clear environmental benefits over the vehicle's lifetime.",
    "argument": "The scientific consensus is clear: despite higher manufacturing emissions, EVs more than make up for it through zero tailpipe emissions during their operational lifetime."
}`;
}

function getJudgeSystemPrompt(): string {
  return `You are an impartial judge evaluating a debate about a factual claim.

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

Be objective and base your decision on the evidence presented in the debate.`;
}

export async function runDebate(
  claim: string,
  turns: number,
  proModel: ModelKey,
  conModel: ModelKey,
  judgeModel: ModelKey,
  apiKeys: APIKeys
): Promise<DebateResult> {
  const proClient = new ModelClient(proModel, apiKeys);
  const conClient = new ModelClient(conModel, apiKeys);
  const judgeClient = new ModelClient(judgeModel, apiKeys);

  const debateHistory: DebateTurn[] = [];
  let debateShortened = false;

  // Run debate
  for (let turn = 0; turn < turns; turn++) {
    // Pro side
    const proResponse = await makeArgument(proClient, claim, 'pro', MODELS[proModel].name, debateHistory);
    debateHistory.push(proResponse);
    if (proResponse.refused) debateShortened = true;

    // Con side
    const conResponse = await makeArgument(conClient, claim, 'con', MODELS[conModel].name, debateHistory);
    debateHistory.push(conResponse);
    if (conResponse.refused) debateShortened = true;

    if (debateShortened) break;
  }

  // Judge
  const verdict = await judgeDebate(judgeClient, claim, debateHistory);

  return {
    claim,
    models: {
      pro: MODELS[proModel].name,
      con: MODELS[conModel].name,
      judge: MODELS[judgeModel].name
    },
    debate_history: debateHistory,
    verdict
  };
}

async function makeArgument(
  client: ModelClient,
  claim: string,
  position: 'pro' | 'con',
  modelName: string,
  debateHistory: DebateTurn[]
): Promise<DebateTurn> {
  // Build user prompt with history
  let userPrompt = '';
  if (debateHistory.length > 0) {
    const filteredHistory = debateHistory.filter(t => !t.refused);
    if (filteredHistory.length > 0) {
      userPrompt = 'DEBATE SO FAR:\n';
      filteredHistory.forEach((turn, i) => {
        userPrompt += `\nTurn ${i + 1} - ${turn.position.toUpperCase()}:\n`;
        userPrompt += `Source: ${turn.url}\n`;
        userPrompt += `Quote: "${turn.quote}"\n`;
        userPrompt += `Context: ${turn.context}\n`;
        userPrompt += `Argument: ${turn.argument}\n`;
      });
      userPrompt += '\n\nNow make your next argument. Provide your response in JSON format.';
    } else {
      userPrompt = 'Make your opening argument. Provide your response in JSON format.';
    }
  } else {
    userPrompt = 'Make your opening argument. Provide your response in JSON format.';
  }

  const systemPrompt = getDebaterSystemPrompt(claim, position);
  let result: any = null;
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < 2; attempt += 1) {
    const responseText = await client.generate(systemPrompt, userPrompt);

    try {
      result = JSON.parse(responseText);
      lastError = null;
    } catch (error) {
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          result = JSON.parse(jsonMatch[0]);
          lastError = null;
        } catch (parseError) {
          const sanitized = sanitizeJsonString(jsonMatch[0]);
          try {
            result = JSON.parse(sanitized);
            lastError = null;
          } catch (finalError) {
            lastError = finalError instanceof Error
              ? finalError
              : new Error('Unknown JSON parsing error');
            console.error('Failed to parse JSON after sanitizing:', finalError, 'Original response:', responseText);
            result = null;
          }
        }
      } else {
        lastError = new Error(`Could not parse JSON from response: ${responseText.substring(0, 200)}`);
        console.error('No JSON object found in response:', responseText);
        result = null;
      }
    }

    if (result) {
      break;
    }

    if (attempt === 0) {
      console.warn(`Malformed JSON from ${modelName} (${position}). Retrying once...`);
    }
  }

  if (!result) {
    throw lastError ?? new Error('Failed to parse model response as JSON.');
  }

  // Check for refusal
  if (result.refused) {
    return {
      position,
      model: modelName,
      refused: true,
      refusal_reason: result.reason || 'No reason provided',
      url: '',
      quote: '',
      context: '',
      argument: ''
    };
  }

  // Validate required fields
  const requiredFields = ['url', 'quote', 'context', 'argument'];
  for (const field of requiredFields) {
    if (!result[field]) {
      throw new Error(`Response missing required field: ${field}`);
    }
  }

  return {
    position,
    model: modelName,
    refused: false,
    url: result.url,
    quote: result.quote,
    context: result.context,
    argument: result.argument
  };
}

async function judgeDebate(
  client: ModelClient,
  claim: string,
  debateHistory: DebateTurn[]
): Promise<{ verdict: 'supported' | 'contradicted' | 'misleading' | 'needs more evidence'; explanation: string }> {
  // Build transcript
  let transcript = `CLAIM: ${claim}\n\nDEBATE TRANSCRIPT:\n${'='.repeat(80)}\n\n`;

  debateHistory.forEach((turn, i) => {
    transcript += `Turn ${i + 1} - ${turn.position.toUpperCase()} SIDE:\n`;
    if (turn.refused) {
      transcript += `[REFUSED TO ARGUE]\nReason: ${turn.refusal_reason}\n`;
    } else {
      transcript += `Source: ${turn.url}\n`;
      transcript += `Quote: "${turn.quote}"\n`;
      transcript += `Context: ${turn.context}\n`;
      transcript += `Argument: ${turn.argument}\n`;
    }
    transcript += `\n${'-'.repeat(80)}\n\n`;
  });

  const systemPrompt = getJudgeSystemPrompt();
  const userPrompt = `${transcript}\n\nProvide your verdict in JSON format.`;
  let result: any = null;
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < 2; attempt += 1) {
    const responseText = await client.generate(systemPrompt, userPrompt, 1500);

    try {
      result = JSON.parse(responseText);
      lastError = null;
    } catch {
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          result = JSON.parse(jsonMatch[0]);
          lastError = null;
        } catch (error) {
          lastError = error instanceof Error ? error : new Error('Could not parse JSON from judge response');
          result = null;
        }
      } else {
        lastError = new Error('Could not parse JSON from judge response');
        result = null;
      }
    }

    if (result) {
      break;
    }

    if (attempt === 0) {
      console.warn('Malformed JSON from judge. Retrying once...');
    }
  }

  if (!result) {
    throw lastError ?? new Error('Could not parse JSON from judge response');
  }

  if (!result.verdict || !result.explanation) {
    throw new Error('Judge response missing required fields');
  }

  const validVerdicts: Array<'supported' | 'contradicted' | 'misleading' | 'needs more evidence'> = ['supported', 'contradicted', 'misleading', 'needs more evidence'];
  if (!validVerdicts.includes(result.verdict)) {
    throw new Error(`Invalid verdict: ${result.verdict}`);
  }

  return {
    verdict: result.verdict as 'supported' | 'contradicted' | 'misleading' | 'needs more evidence',
    explanation: result.explanation
  };
}
function sanitizeJsonString(raw: string): string {
  let sanitized = '';
  let inString = false;
  for (let i = 0; i < raw.length; i++) {
    const char = raw[i];
    const prevChar = i > 0 ? raw[i - 1] : '';

    if (char === '"' && prevChar !== '\\') {
      inString = !inString;
      sanitized += char;
      continue;
    }

    if (inString && char === '\n') {
      sanitized += '\\n';
    } else if (inString && char === '\r') {
      sanitized += '\\r';
    } else if (inString && char === '\t') {
      sanitized += '\\t';
    } else {
      sanitized += char;
    }
  }
  return sanitized;
}
