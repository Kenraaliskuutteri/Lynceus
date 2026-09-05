const HEADER_VALUE_PATTERN = /^[\t\x20-\x7e\x80-\xff]*$/;

export function isValidHeaderValue(value: string): boolean {
  return HEADER_VALUE_PATTERN.test(value);
}   