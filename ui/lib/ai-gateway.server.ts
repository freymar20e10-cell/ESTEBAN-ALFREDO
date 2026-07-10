import { createOpenAICompatible } from "@ai-sdk/openai-compatible";

/**
 * Provider helper that connects the AI SDK to the Lovable AI Gateway.
 * Server-only: reads LOVABLE_API_KEY and must never be imported by client code.
 */
export function createLovableAiGatewayProvider(apiKey: string) {
  return createOpenAICompatible({
    name: "lovable-gateway",
    baseURL: "https://ai.gateway.lovable.dev/v1",
    headers: { "Lovable-API-Key": apiKey },
  });
}
