import { createServerFn } from "@tanstack/react-start";
import { generateText, type ModelMessage } from "ai";
import { z } from "zod";
import { createLovableAiGatewayProvider } from "./ai-gateway.server";

const ChatInput = z.object({
  messages: z
    .array(
      z.object({
        role: z.enum(["user", "assistant"]),
        content: z.string(),
      }),
    )
    .min(1),
});

const SYSTEM_PROMPT = `Eres Jarvis, un asistente personal inteligente y cercano, al estilo de un mayordomo digital.
- Responde SIEMPRE en español, de forma natural, clara y concisa.
- Eres educado, con un toque de ingenio, pero directo y útil.
- Si no puedes ejecutar una acción real en el equipo todavía, explícalo con honestidad y ofrece la mejor ayuda posible.
- Trata al usuario de "señor" ocasionalmente, sin abusar.`;

export const askJarvis = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => ChatInput.parse(input))
  .handler(async ({ data }) => {
    const apiKey = process.env.LOVABLE_API_KEY;
    if (!apiKey) throw new Error("Falta LOVABLE_API_KEY");

    const gateway = createLovableAiGatewayProvider(apiKey);

    const messages: ModelMessage[] = [
      { role: "system", content: SYSTEM_PROMPT },
      ...data.messages.map((m) => ({ role: m.role, content: m.content })),
    ];

    try {
      const { text } = await generateText({
        model: gateway("google/gemini-3-flash-preview"),
        messages,
      });
      return { text };
    } catch (err) {
      const status =
        err != null && typeof err === "object" && "statusCode" in err
          ? (err as { statusCode?: number }).statusCode
          : undefined;
      if (status === 429) {
        return {
          text: "Estoy recibiendo demasiadas peticiones ahora mismo, señor. Inténtelo de nuevo en un momento.",
          error: "rate_limit" as const,
        };
      }
      if (status === 402) {
        return {
          text: "Se han agotado los créditos de IA. Añada más para que pueda seguir pensando.",
          error: "no_credits" as const,
        };
      }
      throw err;
    }
  });
