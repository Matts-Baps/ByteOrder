const lock = require('../package-lock.json')

// GHSA-wpqf-h9rq-rg73: @clerk/backend before 3.28.0 can accept OIDC ID tokens as
// session tokens, letting an approved OAuth client sign in as the user.
const PATCHED = [3, 28, 0]

function isAtLeast(version, minimum) {
  const parts = version.split('.').map(Number)
  for (let i = 0; i < minimum.length; i++) {
    if (parts[i] !== minimum[i]) return parts[i] > minimum[i]
  }
  return true
}

describe('@clerk/backend', () => {
  it('is locked to a release patched for GHSA-wpqf-h9rq-rg73', () => {
    const { version } = lock.packages['node_modules/@clerk/backend']
    expect(isAtLeast(version, PATCHED)).toBe(true)
  })
})
