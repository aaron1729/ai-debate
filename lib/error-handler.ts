/**
 * Centralized error handling for API errors across all providers
 * Categorizes errors and provides user-friendly messages
 */

export type ErrorCategory =
  | 'OVERLOADED'
  | 'RATE_LIMITED'
  | 'AUTHENTICATION'
  | 'PERMISSION'
  | 'NOT_FOUND'
  | 'REQUEST_TOO_LARGE'
  | 'TIMEOUT'
  | 'INVALID_REQUEST'
  | 'SAFETY_FILTER'
  | 'INVALID_RESPONSE'
  | 'NETWORK'
  | 'UNKNOWN';

export type Provider = 'anthropic' | 'openai' | 'google' | 'xai';

export interface CategorizedError {
  category: ErrorCategory;
  provider: Provider;
  modelName: string;
  httpStatus?: number;
  userMessage: string;
  suggestion: string;
  technicalDetails: string;
  originalError: any;
  isRetryable: boolean;
}

/**
 * Provider-specific error patterns and detection
 */

// Anthropic Claude error detection
function categorizeAnthropicError(error: any): { category: ErrorCategory; httpStatus?: number } {
  const message = error.message || '';
  const status = error.status || error.statusCode;

  // Check for specific error types in the error object
  if (error.error?.type) {
    const errorType = error.error.type;
    switch (errorType) {
      case 'invalid_request_error':
        return { category: 'INVALID_REQUEST', httpStatus: 400 };
      case 'authentication_error':
        return { category: 'AUTHENTICATION', httpStatus: 401 };
      case 'permission_error':
        return { category: 'PERMISSION', httpStatus: 403 };
      case 'not_found_error':
        return { category: 'NOT_FOUND', httpStatus: 404 };
      case 'request_too_large':
        return { category: 'REQUEST_TOO_LARGE', httpStatus: 413 };
      case 'rate_limit_error':
        return { category: 'RATE_LIMITED', httpStatus: 429 };
      case 'api_error':
        return { category: 'UNKNOWN', httpStatus: 500 };
      case 'overloaded_error':
        return { category: 'OVERLOADED', httpStatus: 529 };
    }
  }

  // Fall back to HTTP status code
  if (status) {
    switch (status) {
      case 400:
        return { category: 'INVALID_REQUEST', httpStatus: 400 };
      case 401:
        return { category: 'AUTHENTICATION', httpStatus: 401 };
      case 403:
        return { category: 'PERMISSION', httpStatus: 403 };
      case 404:
        return { category: 'NOT_FOUND', httpStatus: 404 };
      case 413:
        return { category: 'REQUEST_TOO_LARGE', httpStatus: 413 };
      case 429:
        return { category: 'RATE_LIMITED', httpStatus: 429 };
      case 500:
        return { category: 'UNKNOWN', httpStatus: 500 };
      case 529:
        return { category: 'OVERLOADED', httpStatus: 529 };
    }
  }

  // Check message content for specific patterns
  if (message.includes('Overloaded') || message.includes('overloaded')) {
    return { category: 'OVERLOADED', httpStatus: 529 };
  }
  if (message.includes('rate limit') || message.includes('rate_limit')) {
    return { category: 'RATE_LIMITED', httpStatus: 429 };
  }
  if (message.includes('API key') || message.includes('authentication')) {
    return { category: 'AUTHENTICATION', httpStatus: 401 };
  }

  return { category: 'UNKNOWN', httpStatus: status };
}

// OpenAI error detection
function categorizeOpenAIError(error: any): { category: ErrorCategory; httpStatus?: number } {
  const message = error.message || '';
  const status = error.status || error.statusCode;
  const code = error.code;

  // Check for specific error codes
  if (code === 'insufficient_quota') {
    return { category: 'RATE_LIMITED', httpStatus: 429 };
  }
  if (code === 'invalid_api_key') {
    return { category: 'AUTHENTICATION', httpStatus: 401 };
  }
  if (code === 'model_not_found') {
    return { category: 'NOT_FOUND', httpStatus: 404 };
  }

  // Check HTTP status
  if (status) {
    switch (status) {
      case 400:
        return { category: 'INVALID_REQUEST', httpStatus: 400 };
      case 401:
        return { category: 'AUTHENTICATION', httpStatus: 401 };
      case 403:
        return { category: 'PERMISSION', httpStatus: 403 };
      case 404:
        return { category: 'NOT_FOUND', httpStatus: 404 };
      case 413:
        return { category: 'REQUEST_TOO_LARGE', httpStatus: 413 };
      case 422:
        return { category: 'INVALID_REQUEST', httpStatus: 422 };
      case 429:
        return { category: 'RATE_LIMITED', httpStatus: 429 };
      case 500:
        return { category: 'UNKNOWN', httpStatus: 500 };
      case 503:
        return { category: 'OVERLOADED', httpStatus: 503 };
    }
  }

  // Check message patterns
  if (message.includes('rate limit') || message.includes('quota')) {
    return { category: 'RATE_LIMITED', httpStatus: 429 };
  }
  if (message.includes('overloaded') || message.includes('unavailable')) {
    return { category: 'OVERLOADED', httpStatus: 503 };
  }
  if (message.includes('timeout')) {
    return { category: 'TIMEOUT' };
  }

  return { category: 'UNKNOWN', httpStatus: status };
}

// Google Gemini error detection
function categorizeGoogleError(error: any): { category: ErrorCategory; httpStatus?: number } {
  const message = error.message || '';
  const status = error.status || error.statusCode;

  // Check for safety filter blocks
  if (message.includes('SAFETY') || message.includes('Content generation stopped')) {
    return { category: 'SAFETY_FILTER', httpStatus: 400 };
  }

  // Check HTTP status
  if (status) {
    switch (status) {
      case 400:
        // Could be invalid request or safety filter
        if (message.includes('INVALID_ARGUMENT')) {
          return { category: 'INVALID_REQUEST', httpStatus: 400 };
        }
        return { category: 'INVALID_REQUEST', httpStatus: 400 };
      case 401:
        return { category: 'AUTHENTICATION', httpStatus: 401 };
      case 403:
        return { category: 'PERMISSION', httpStatus: 403 };
      case 404:
        return { category: 'NOT_FOUND', httpStatus: 404 };
      case 429:
        return { category: 'RATE_LIMITED', httpStatus: 429 };
      case 500:
        return { category: 'UNKNOWN', httpStatus: 500 };
      case 503:
        return { category: 'OVERLOADED', httpStatus: 503 };
    }
  }

  // Check message patterns
  if (message.includes('quota') || message.includes('Resource exhausted')) {
    return { category: 'RATE_LIMITED', httpStatus: 429 };
  }
  if (message.includes('model') && message.includes('not found')) {
    return { category: 'NOT_FOUND', httpStatus: 404 };
  }

  return { category: 'UNKNOWN', httpStatus: status };
}

// xAI Grok error detection (uses OpenAI-compatible API)
function categorizeXAIError(error: any): { category: ErrorCategory; httpStatus?: number } {
  // xAI uses OpenAI-compatible error format
  return categorizeOpenAIError(error);
}

/**
 * Categorize an error from any provider
 */
export function categorizeAPIError(
  error: any,
  provider: Provider,
  modelName: string
): CategorizedError {
  let category: ErrorCategory;
  let httpStatus: number | undefined;

  // Categorize based on provider
  switch (provider) {
    case 'anthropic':
      ({ category, httpStatus } = categorizeAnthropicError(error));
      break;
    case 'openai':
      ({ category, httpStatus } = categorizeOpenAIError(error));
      break;
    case 'google':
      ({ category, httpStatus } = categorizeGoogleError(error));
      break;
    case 'xai':
      ({ category, httpStatus } = categorizeXAIError(error));
      break;
    default:
      category = 'UNKNOWN';
  }

  // Check for network errors
  if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND' || error.code === 'ETIMEDOUT') {
    category = 'NETWORK';
  }

  // Generate user-friendly messages
  const messages = getUserFriendlyMessage(category, provider, modelName);

  return {
    category,
    provider,
    modelName,
    httpStatus,
    userMessage: messages.userMessage,
    suggestion: messages.suggestion,
    technicalDetails: `${error.constructor?.name || 'Error'}: ${error.message || 'Unknown error'}`,
    originalError: error,
    isRetryable: isErrorRetryable(category)
  };
}

/**
 * Get user-friendly messages for each error category
 */
function getUserFriendlyMessage(
  category: ErrorCategory,
  provider: Provider,
  modelName: string
): { userMessage: string; suggestion: string } {
  const providerName = getProviderDisplayName(provider);

  switch (category) {
    case 'OVERLOADED':
      return {
        userMessage: `${providerName} is currently experiencing high demand and cannot process your request.`,
        suggestion: 'Please wait a few minutes and try again. You can also try using a different model.'
      };

    case 'RATE_LIMITED':
      return {
        userMessage: `You've exceeded the rate limit for ${modelName}.`,
        suggestion: 'Please wait a moment before trying again, or try using a different model.'
      };

    case 'AUTHENTICATION':
      return {
        userMessage: `Authentication failed for ${providerName}.`,
        suggestion: 'Please check that your API key is valid and has not expired.'
      };

    case 'PERMISSION':
      return {
        userMessage: `Your ${providerName} API key does not have permission to use ${modelName}.`,
        suggestion: 'Please check your API key permissions or try a different model.'
      };

    case 'NOT_FOUND':
      return {
        userMessage: `The model "${modelName}" was not found or is no longer available.`,
        suggestion: 'Please try using a different model. The model may have been renamed or deprecated.'
      };

    case 'REQUEST_TOO_LARGE':
      return {
        userMessage: 'Your debate request is too large.',
        suggestion: 'Try reducing the number of debate turns or using a shorter claim.'
      };

    case 'TIMEOUT':
      return {
        userMessage: `${modelName} took too long to respond.`,
        suggestion: 'Please try again. If this persists, try using a different model.'
      };

    case 'INVALID_REQUEST':
      return {
        userMessage: 'The request to the API was invalid.',
        suggestion: 'Please try again. If this persists, there may be an issue with the debate configuration.'
      };

    case 'SAFETY_FILTER':
      return {
        userMessage: `${modelName} blocked the request due to safety filters.`,
        suggestion: 'The claim or debate content may have triggered safety policies. Try rephrasing your claim or using a different model.'
      };

    case 'INVALID_RESPONSE':
      return {
        userMessage: `${modelName} returned an invalid response.`,
        suggestion: 'Please try again. This is usually a temporary issue.'
      };

    case 'NETWORK':
      return {
        userMessage: 'Could not connect to the API service.',
        suggestion: 'Please check your internet connection and try again.'
      };

    case 'UNKNOWN':
    default:
      return {
        userMessage: `An unexpected error occurred with ${modelName}.`,
        suggestion: 'Please try again. If this persists, try using a different model.'
      };
  }
}

/**
 * Get display name for provider
 */
function getProviderDisplayName(provider: Provider): string {
  switch (provider) {
    case 'anthropic':
      return 'Claude';
    case 'openai':
      return 'OpenAI';
    case 'google':
      return 'Google Gemini';
    case 'xai':
      return 'xAI';
    default:
      return 'the API';
  }
}

/**
 * Determine if an error is retryable
 */
function isErrorRetryable(category: ErrorCategory): boolean {
  switch (category) {
    case 'OVERLOADED':
    case 'TIMEOUT':
    case 'NETWORK':
    case 'UNKNOWN':
      return true;

    case 'RATE_LIMITED':
      // Retryable but with backoff
      return true;

    case 'AUTHENTICATION':
    case 'PERMISSION':
    case 'NOT_FOUND':
    case 'REQUEST_TOO_LARGE':
    case 'INVALID_REQUEST':
    case 'SAFETY_FILTER':
    case 'INVALID_RESPONSE':
      return false;

    default:
      return false;
  }
}

/**
 * Global error handler for unexpected errors
 */
export function handleUnexpectedError(error: any, context: string): CategorizedError {
  console.error(`Unexpected error in ${context}:`, error);

  return {
    category: 'UNKNOWN',
    provider: 'anthropic', // Default fallback
    modelName: 'Unknown',
    httpStatus: undefined,
    userMessage: 'An unexpected error occurred.',
    suggestion: 'Please try again. If this persists, contact support.',
    technicalDetails: `Unexpected error in ${context}: ${error.message || String(error)}`,
    originalError: error,
    isRetryable: false
  };
}
