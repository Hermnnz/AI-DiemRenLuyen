declare module 'node:test' {
  export function describe(name: string, fn: () => void | Promise<void>): void;
  export function it(name: string, fn: () => void | Promise<void>): void;
  export function test(name: string, fn: () => void | Promise<void>): void;
  const _default: {
    describe: typeof describe;
    it: typeof it;
    test: typeof test;
  };
  export default _default;
}

declare module 'node:assert/strict' {
  export function equal(actual: unknown, expected: unknown, message?: string): void;
  export function strictEqual(actual: unknown, expected: unknown, message?: string): void;
  export function ok(value: unknown, message?: string): void;
  export function fail(message?: string | Error): never;
  export function throws(fn: () => unknown, error?: unknown): void;
  export function rejects(fn: () => Promise<unknown>, error?: unknown): Promise<void>;
  const assert: {
    equal: typeof equal;
    strictEqual: typeof strictEqual;
    ok: typeof ok;
    fail: typeof fail;
    throws: typeof throws;
    rejects: typeof rejects;
  };
  export default assert;
}
