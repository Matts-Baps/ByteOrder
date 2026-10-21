// Mode-neutral auth for admin pages.
//
// Pages call useAdminAuth() instead of Clerk hooks directly. Clerk hooks only
// work inside <ClerkProvider>, which exists in cloud mode only, so calling them
// from shared components crashes self-hosted installs (#54).
import { createContext, useContext, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useClerk, useOrganization } from '@clerk/clerk-react'

const AdminAuthContext = createContext(null)

export function useAdminAuth() {
  const value = useContext(AdminAuthContext)
  if (!value) throw new Error('useAdminAuth must be used inside CloudAuthProvider or SelfHostedAuthProvider')
  return value
}

// Cloud: must be rendered inside <ClerkProvider>.
export function CloudAuthProvider({ children }) {
  const { signOut } = useClerk()
  const { organization } = useOrganization()
  const value = useMemo(
    () => ({ mode: 'cloud', organization: organization ?? null, signOut: () => signOut() }),
    [organization, signOut]
  )
  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>
}

// Self-hosted: the login token lives in localStorage.
export function SelfHostedAuthProvider({ children }) {
  const navigate = useNavigate()
  const value = useMemo(
    () => ({
      mode: 'self-hosted',
      organization: null,
      signOut: () => {
        localStorage.removeItem('token')
        navigate('/login', { replace: true })
      },
    }),
    [navigate]
  )
  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>
}
