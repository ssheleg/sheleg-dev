/** Copy beside the Stripe client and call before constructing it. No I/O or logging.
 * Prefix agreement is not credential authenticity or permission validation.
 */
export function assertStripeEnv(mode, key) {
  if (!['test', 'production'].includes(mode)) throw new Error('STRIPE_ENV_INVALID');
  if (typeof key !== 'string' || !key) throw new Error('STRIPE_KEY_MISSING');
  const match = /^(?:sk|rk)_(test|live)_[A-Za-z0-9]+$/.exec(key);
  // Organization/unknown keys do not encode a mode this assertion can prove.
  if (!match) throw new Error('STRIPE_KEY_MODE_UNVERIFIED');
  if (mode === 'test' && match[1] === 'live') {
    throw new Error('STRIPE_ENV_TEST_HOLDS_LIVE_CREDENTIAL');
  }
  if (mode === 'production' && match[1] === 'test') {
    throw new Error('STRIPE_ENV_LIVE_HOLDS_TEST_CREDENTIAL');
  }
  return mode;
}
