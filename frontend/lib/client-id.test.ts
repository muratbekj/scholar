import { describe, expect, test } from 'bun:test';
import { getClientId } from './api';

function memoryStorage() {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => {
      data.set(key, value);
    },
  };
}

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe('getClientId', () => {
  test('creates a UUID once and reuses it', () => {
    const storage = memoryStorage();
    const first = getClientId(storage);
    expect(first).toMatch(UUID_V4);
    expect(getClientId(storage)).toBe(first);
  });

  test('different browsers get different ids', () => {
    expect(getClientId(memoryStorage())).not.toBe(getClientId(memoryStorage()));
  });
});
