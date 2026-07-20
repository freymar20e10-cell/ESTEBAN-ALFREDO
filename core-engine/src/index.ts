/**
 * JARVIS Core Engine — punto de entrada.
 * Compilado como IIFE: expone window.JarvisCoreEngine con { mount, ... }.
 */
export { mount, registerShape, registerAsyncShape, listShapes } from "./api";
export type { JarvisCoreHandle } from "./api";
export { DEFAULT_CONFIG } from "./config/CoreConfig";
export type { CoreConfig } from "./config/CoreConfig";
export { CORE_STATES } from "./config/CoreState";
export type { CoreStateName } from "./config/CoreState";
