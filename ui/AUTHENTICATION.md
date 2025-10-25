# Authentication Implementation Guide

## Overview

LLMHive uses **Auth.js v5** (formerly NextAuth.js) for secure authentication with GitHub OAuth. This document explains the authentication architecture and flow.

## Architecture

### Core Components

1. **`auth.ts`** - Auth.js configuration
   - Defines GitHub OAuth provider
   - Configures session callbacks
   - Exports authentication utilities

2. **`app/api/auth/[...nextauth]/route.ts`** - API route handler
   - Handles all OAuth flows automatically
   - Endpoints: sign-in, sign-out, callbacks, session

3. **`app/layout.tsx`** - Root layout with session
   - Server-side session fetching with `auth()`
   - Wraps app with `SessionProvider`

4. **`app/page.tsx`** - Main page controller
   - Checks authentication state
   - Routes to LoginPage or ChatInterface

### UI Components

- **`LoginPage.tsx`** - Unauthenticated view
- **`ChatInterface.tsx`** - Authenticated main app
- **`Sidebar.tsx`** - User profile and navigation
- **`Header.tsx`** - Top navigation

## Authentication Flow

### Sign In Flow

1. User visits the application
2. `app/page.tsx` checks session via `useSession()`
3. If no session, `LoginPage` is displayed
4. User clicks "Sign in with GitHub"
5. `signIn("github")` redirects to GitHub OAuth
6. User authorizes the application
7. GitHub redirects back to `/api/auth/callback/github`
8. Auth.js creates session and sets secure cookies
9. User is redirected to home page
10. `ChatInterface` is displayed with user data

### Sign Out Flow

1. User clicks "Sign Out" in sidebar
2. `signOut()` is called from `next-auth/react`
3. Session is destroyed
4. User is redirected to login page

## Session Management

### Server-Side

```typescript
import { auth } from "@/auth";

// In any Server Component
const session = await auth();
if (session?.user) {
  // User is authenticated
}
```

### Client-Side

```typescript
import { useSession } from "next-auth/react";

// In any Client Component
const { data: session, status } = useSession();
if (status === "authenticated") {
  // User is authenticated
}
```

## Security Features

### Built-in Security

- **CSRF Protection**: Automatic token validation
- **Secure Cookies**: HttpOnly, SameSite cookies
- **Session Encryption**: JWT tokens signed with AUTH_SECRET
- **OAuth State Parameter**: Prevents CSRF attacks

### Environment Variables

All secrets are stored as environment variables:

- `AUTH_SECRET` - Used to encrypt JWT tokens
- `GITHUB_ID` - OAuth app client ID (not secret)
- `GITHUB_SECRET` - OAuth app client secret (very sensitive)

### Best Practices

1. **Never commit `.env.local`** - Already in .gitignore
2. **Rotate secrets regularly** - Generate new AUTH_SECRET periodically
3. **Use different secrets per environment** - Dev, staging, production
4. **Monitor OAuth app access** - Review in GitHub settings

## Adding Additional Providers

To add more OAuth providers (Google, Microsoft, etc.):

1. Install provider if needed: `npm install next-auth`
2. Import provider in `auth.ts`:
   ```typescript
   import Google from "next-auth/providers/google";
   ```
3. Add to providers array:
   ```typescript
   providers: [
     GitHub({ /* ... */ }),
     Google({
       clientId: process.env.GOOGLE_ID,
       clientSecret: process.env.GOOGLE_SECRET,
     }),
   ],
   ```
4. Add environment variables
5. Update LoginPage to show new button

## Customizing the Session

### Adding Custom User Data

Edit `auth.ts` callbacks:

```typescript
export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [/* ... */],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.customField = user.customField;
      }
      return token;
    },
    async session({ session, token }) {
      session.user.customField = token.customField;
      return session;
    },
  },
});
```

## Troubleshooting

### Common Issues

**"Sign in failed"**
- Verify GitHub OAuth app credentials
- Check callback URL matches exactly
- Ensure environment variables are set

**"Invalid session"**
- Regenerate AUTH_SECRET
- Clear browser cookies
- Restart dev server

**"Images not loading"**
- Check `next.config.js` has GitHub domain
- Verify user has public avatar

### Debug Mode

Enable debug logging in `auth.ts`:

```typescript
export const { handlers, signIn, signOut, auth } = NextAuth({
  debug: process.env.NODE_ENV === "development",
  // ...
});
```

## Production Deployment

### Vercel Setup

1. Add environment variables in Vercel dashboard
2. Update GitHub OAuth callback URL to production domain
3. Deploy and test authentication flow

### Environment-Specific URLs

- **Development**: `http://localhost:3000/api/auth/callback/github`
- **Production**: `https://your-domain.com/api/auth/callback/github`

Each environment needs its own GitHub OAuth app or update the callback URLs to include both.

## References

- [Auth.js Documentation](https://authjs.dev/)
- [GitHub OAuth Apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app)
- [Next.js Authentication](https://nextjs.org/docs/authentication)
