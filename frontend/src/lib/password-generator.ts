export interface PasswordOptions {
  length: number;
  uppercase: boolean;
  lowercase: boolean;
  numbers: boolean;
  symbols: boolean;
}

const CHAR_SETS = {
  uppercase: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
  lowercase: 'abcdefghijklmnopqrstuvwxyz',
  numbers: '0123456789',
  symbols: '!@#$%^&*()_+~`|}{[]:;?><,./-=',
};

export function generatePassword(options: PasswordOptions): string {
  let charSet = '';
  if (options.uppercase) charSet += CHAR_SETS.uppercase;
  if (options.lowercase) charSet += CHAR_SETS.lowercase;
  if (options.numbers) charSet += CHAR_SETS.numbers;
  if (options.symbols) charSet += CHAR_SETS.symbols;

  if (charSet === '') {
    charSet = CHAR_SETS.lowercase + CHAR_SETS.numbers;
  }

  const length = Math.max(1, Math.min(32, options.length));
  const randomValues = new Uint32Array(length);
  crypto.getRandomValues(randomValues);
  
  let password = '';
  for (let i = 0; i < length; i++) {
    password += charSet[randomValues[i] % charSet.length];
  }
  
  return password;
}
