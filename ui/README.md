# LLMHive UI

This is the frontend interface for LLMHive, built with Next.js 14, React 18, and Tailwind CSS with Auth.js authentication.

## Features

- 🔐 **Secure Authentication**: GitHub OAuth integration via Auth.js (NextAuth v5)
- 🎨 **Modern UI**: Clean, minimalist design inspired by leading AI chat applications
- 💬 **Real-time Chat**: Streaming responses from the LLMHive backend
- 👤 **User Profile**: Sidebar with user information and session management
- 📱 **Responsive**: Mobile-friendly two-column layout

## Getting Started

### Prerequisites

1. Node.js 18+ installed
2. A GitHub OAuth App (see setup below)

### Environment Setup

1. Copy the example environment file:
```bash
cp .env.local.example .env.local
```

2. Create a GitHub OAuth App:
   - Go to https://github.com/settings/developers
   - Click "New OAuth App"
   - Fill in the application details:
     - **Application name**: LLMHive (or your preferred name)
     - **Homepage URL**: `http://localhost:3000` (for local dev) or your production URL
     - **Authorization callback URL**: `http://localhost:3000/api/auth/callback/github`
   - Click "Register application"
   - Copy the **Client ID** and generate a **Client Secret**

3. Generate an Auth Secret:
```bash
openssl rand -base64 32
```

4. Update `.env.local` with your values:
```env
AUTH_SECRET=<your-generated-secret>
GITHUB_ID=<your-github-client-id>
GITHUB_SECRET=<your-github-client-secret>
```

### Installation

Install the dependencies:

```bash
npm install
```

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the application.

You'll be presented with a login screen. Click "Sign in with GitHub" to authenticate.

## Build

To build for production:

```bash
npm run build
```

To run the production build:

```bash
npm run start
```

## Deployment

### Vercel Deployment

This application is configured to deploy to Vercel alongside the Python backend.

**Required Environment Variables in Vercel:**
- `AUTH_SECRET`: Your generated auth secret
- `GITHUB_ID`: Your GitHub OAuth App Client ID  
- `GITHUB_SECRET`: Your GitHub OAuth App Client Secret

**Important**: Update your GitHub OAuth App's callback URL to match your production domain:
- `https://your-domain.com/api/auth/callback/github`

See the root `vercel.json` for configuration details.

## Project Structure

```
ui/
├── app/
│   ├── api/auth/[...nextauth]/  # Auth.js API routes
│   ├── layout.tsx               # Root layout with SessionProvider
│   ├── page.tsx                 # Main page (routing logic)
│   └── globals.css              # Global styles
├── components/
│   ├── ChatInterface.tsx        # Main chat interface
│   ├── Header.tsx               # Top navigation bar
│   ├── LoginPage.tsx            # GitHub OAuth login page
│   └── Sidebar.tsx              # User sidebar with profile
├── auth.ts                      # Auth.js configuration
└── .env.local.example           # Environment template
```

## Authentication Flow

1. User visits the application
2. If not authenticated, LoginPage is shown
3. User clicks "Sign in with GitHub"
4. GitHub OAuth flow completes
5. User is redirected back to ChatInterface
6. Session is maintained via Auth.js
7. User can sign out from the sidebar

## Customization

### Adding More Auth Providers

Edit `auth.ts` and add additional providers:

```typescript
import Google from "next-auth/providers/google";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    GitHub({ /* ... */ }),
    Google({ /* ... */ }),
  ],
  // ...
});
```

### Styling

The application uses Tailwind CSS. Customize colors and themes in `tailwind.config.ts` and `app/globals.css`.

## Troubleshooting

**"Sign in failed"**: Verify your GitHub OAuth App credentials and callback URL are correct.

**"Invalid environment variables"**: Ensure all three variables (`AUTH_SECRET`, `GITHUB_ID`, `GITHUB_SECRET`) are set in `.env.local`.

**Images not loading**: GitHub avatars should load automatically. If not, check the `next.config.js` image configuration.
