import { createFileRoute } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { useState, useRef, useEffect } from "react";
import { Menu, Send, MessageSquare, X } from "lucide-react";
import { JarvisCore } from "@/components/JarvisCore";
import { askJarvis } from "@/lib/jarvis-brain.functions";
import { SHAPES, type ShapeId } from "@/lib/jarvis-shapes";
import { STATES, type JarvisState } from "@/lib/jarvis-states";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  component: Index,
});

function rgbCss(c: [number, number, number], a = 1) {
  return `rgba(${Math.round(c[0] * 255)}, ${Math.round(c[1] * 255)}, ${Math.round(
    c[2] * 255,
  )}, ${a})`;
}

interface Message {
  id: number;
  role: "user" | "jarvis";
  text: string;
}

function Index() {
  const [state, setState] = useState<JarvisState>("escuchando");
  const [shape, setShape] = useState<ShapeId>("sphere");
  const [intensity, setIntensity] = useState(0.5);
  const [menuOpen, setMenuOpen] = useState(false);
  const [convOpen, setConvOpen] = useState(true);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const convEndRef = useRef<HTMLDivElement>(null);

  const [sending, setSending] = useState(false);
  const callJarvis = useServerFn(askJarvis);

  const active = STATES[state];
  const accent = rgbCss(active.color);

  useEffect(() => {
    convEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    const userMsg: Message = { id: Date.now(), role: "user", text };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setSending(true);
    setState("pensando");

    try {
      const payload = history.map((m) => ({
        role: m.role === "jarvis" ? ("assistant" as const) : ("user" as const),
        content: m.text,
      }));
      const res = await callJarvis({ data: { messages: payload } });
      setMessages((m) => [
        ...m,
        { id: Date.now() + 1, role: "jarvis", text: res.text },
      ]);
      setState("error" in res && res.error ? "error" : "listo");
    } catch {
      setMessages((m) => [
        ...m,
        {
          id: Date.now() + 1,
          role: "jarvis",
          text: "Lo siento, señor. Ha ocurrido un problema al pensar. Inténtelo de nuevo.",
        },
      ]);
      setState("error");
    } finally {
      setSending(false);
      window.setTimeout(() => setState("escuchando"), 1800);
    }
  };

  return (
    <div className="relative flex min-h-screen w-full overflow-hidden">
      {/* ============ Panel de conversación (izquierda) ============ */}
      <aside
        className={cn(
          "z-20 flex h-screen shrink-0 flex-col border-r border-border/60 bg-background/70 backdrop-blur transition-all duration-300",
          convOpen ? "w-full max-w-[340px]" : "w-0 overflow-hidden border-r-0",
        )}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            <MessageSquare className="h-4 w-4" />
            Conversación
          </div>
          <button
            onClick={() => setConvOpen(false)}
            className="rounded-md p-1 text-muted-foreground hover:text-foreground"
            aria-label="Cerrar conversación"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto px-4 pb-4">
          {messages.length === 0 && (
            <p className="mt-8 text-center text-xs text-muted-foreground">
              Aún no hay mensajes. Escríbele a Jarvis abajo.
            </p>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={cn(
                "flex",
                m.role === "user" ? "justify-end" : "justify-start",
              )}
            >
              <div
                className={cn(
                  "max-w-[85%] rounded-2xl px-3.5 py-2 text-sm",
                  m.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "glass text-foreground",
                )}
              >
                {m.text}
              </div>
            </div>
          ))}
          <div ref={convEndRef} />
        </div>
      </aside>

      {/* ============ Zona central: núcleo + estado + entrada ============ */}
      <main className="relative z-0 flex flex-1 flex-col">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            {!convOpen && (
              <button
                onClick={() => setConvOpen(true)}
                className="rounded-md p-1.5 text-muted-foreground hover:text-foreground"
                aria-label="Abrir conversación"
              >
                <MessageSquare className="h-5 w-5" />
              </button>
            )}
            <div>
              <h1 className="font-display text-xl font-black tracking-widest text-foreground md:text-2xl">
                JARVIS
              </h1>
              <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                El Núcleo · Fase 1
              </p>
            </div>
          </div>
          <button
            onClick={() => setMenuOpen(true)}
            className="glass flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-foreground hover:text-foreground"
            aria-label="Abrir menú"
          >
            <Menu className="h-4 w-4" />
            Menú
          </button>
        </header>

        {/* Núcleo */}
        <div className="flex flex-1 flex-col items-center justify-center px-4">
          <JarvisCore
            state={state}
            shape={shape}
            intensity={intensity}
            className="h-[46vh] max-h-[520px] min-h-[300px] w-[80vw] max-w-[560px]"
          />

          {/* Indicador de estado (debajo del núcleo) */}
          <div className="mt-2 flex flex-col items-center gap-2">
            <div
              className="h-1 w-40 rounded-full transition-colors"
              style={{
                backgroundColor: accent,
                boxShadow: `0 0 16px ${accent}`,
              }}
            />
            <span
              className="text-sm font-semibold uppercase tracking-[0.3em] transition-colors"
              style={{ color: accent }}
            >
              {active.label}
            </span>
          </div>
        </div>

        {/* Barra de entrada de texto */}
        <div className="mx-auto w-full max-w-2xl px-4 pb-8 pt-4">
          <div className="glass flex items-center gap-2 rounded-full px-2 py-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") send();
              }}
              disabled={sending}
              placeholder={sending ? "Jarvis está pensando…" : "Escríbele a Jarvis…"}
              className="flex-1 bg-transparent px-4 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground disabled:opacity-60"
            />
            <button
              onClick={send}
              disabled={sending}
              className="flex h-10 w-10 items-center justify-center rounded-full transition-colors disabled:opacity-50"
              style={{ backgroundColor: accent, color: "#0a0a0f" }}
              aria-label="Enviar"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </main>

      {/* ============ Menú de controles (derecha, desplegable) ============ */}
      {menuOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside
        className={cn(
          "fixed right-0 top-0 z-40 h-screen w-full max-w-sm overflow-y-auto border-l border-border/60 bg-background/95 backdrop-blur transition-transform duration-300",
          menuOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Menú de control
          </h2>
          <button
            onClick={() => setMenuOpen(false)}
            className="rounded-md p-1 text-muted-foreground hover:text-foreground"
            aria-label="Cerrar menú"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-5 pb-10">

          {/* Formas */}
          <ControlBlock title="Representación generativa">
            <div className="grid grid-cols-2 gap-2">
              {SHAPES.map((sh) => {
                const isActive = sh.id === shape;
                return (
                  <button
                    key={sh.id}
                    onClick={() => setShape(sh.id)}
                    className={cn(
                      "rounded-xl border px-3 py-3 text-sm font-semibold transition-all",
                      isActive
                        ? "border-primary bg-primary/15 text-foreground"
                        : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground",
                    )}
                  >
                    {sh.label}
                  </button>
                );
              })}
            </div>
          </ControlBlock>

          {/* Intensidad */}
          <ControlBlock
            title={`Parámetro interactivo · masa/escala (${Math.round(intensity * 100)}%)`}
          >
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={intensity}
              onChange={(e) => setIntensity(parseFloat(e.target.value))}
              className="w-full accent-primary"
              style={{ accentColor: accent }}
            />
            <p className="mt-2 text-xs text-muted-foreground">
              Ajusta la escala/energía de lo representado en tiempo real — como
              cambiar la “masa” de un agujero negro y ver el efecto reflejado.
            </p>
          </ControlBlock>
        </div>
      </aside>
    </div>
  );
}

function ControlBlock({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="glass mt-4 rounded-2xl p-4 md:p-5">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        {title}
      </h2>
      {children}
    </div>
  );
}
