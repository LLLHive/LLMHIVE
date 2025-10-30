# How to Identify Where Your Backend is Hosted

This guide helps you determine where your LLMHive backend (orchestrator) is running. This is important for:
- Troubleshooting connection issues between frontend and backend
- Verifying your deployment configuration
- Setting up a new environment

## Step 1 — Check Your Frontend's Local Configuration

If you have the code locally, you can check the frontend configuration:

### 1.1 Navigate to the Frontend Project

1. Open the repository folder on your computer
2. Navigate to the frontend project at `ui/`

### 1.2 Check the .env.local File

1. Look for a file named `.env.local` (create it if it doesn't exist)
2. Open the file and find the line that starts with `ORCHESTRATOR_API_BASE_URL=`
3. The value after the `=` is the URL your frontend tries to reach

**Examples:**
```env
# Production backend on Google Cloud Run
ORCHESTRATOR_API_BASE_URL=https://llmhive-orchestrator-792354158895.us-east1.run.app

# Local backend running on your machine
ORCHESTRATOR_API_BASE_URL=http://127.0.0.1:8080
```

**Important Notes:**
- If the value is missing or commented out, the frontend will fall back to the default `http://127.0.0.1:8080`
- This default means it expects a backend running on your own machine
- You can use the `.env.local.example` file as a template if you need to create `.env.local`

### 1.3 Understanding the Configuration

The `.env.local` file contains:
- `ORCHESTRATOR_API_BASE_URL`: Used by the server-side proxy route (`/api/v1/orchestration`)
- `NEXT_PUBLIC_API_BASE_URL`: (Optional) Exposes the backend URL to the browser for direct connections

In most cases, you only need to set `ORCHESTRATOR_API_BASE_URL`. The frontend will proxy requests through Next.js, which helps avoid CORS issues.

## Step 2 — Check Vercel's Environment Variables

If you deploy the frontend to Vercel, check the environment variables there:

### 2.1 Access Your Vercel Project

1. Sign in to [Vercel](https://vercel.com)
2. Open the project that hosts this frontend

### 2.2 View Environment Variables

1. Go to **Settings** → **Environment Variables**
2. Look for a variable named `ORCHESTRATOR_API_BASE_URL`
3. The value shown here is the URL for your backend service

### 2.3 What If the Variable is Missing?

If the field is empty or the variable is missing:
- The Vercel build won't know how to contact your backend
- In production, the proxy route will throw an error reminding you to define it
- You'll need to:
  1. Deploy a backend (see [DEPLOYMENT.md](./DEPLOYMENT.md))
  2. Add its URL to the `ORCHESTRATOR_API_BASE_URL` environment variable in Vercel
  3. Redeploy your frontend for the changes to take effect

### 2.4 Production Build Requirements

**Important:** Production builds expect the `ORCHESTRATOR_API_BASE_URL` variable to be set. Without it:
- The `/api/v1/orchestration` proxy route will return an error
- The error message will remind you to define `ORCHESTRATOR_API_BASE_URL`
- Your frontend will not be able to communicate with the backend

## Quick Reference

### Default Values

| Environment | Default Backend URL | Notes |
|-------------|---------------------|-------|
| Local Development | `http://127.0.0.1:8080` | Expects backend running locally |
| Vercel Production | None (must be set) | Fails with error if not configured |

### Configuration Priority

The frontend determines the backend URL in this order:
1. `ORCHESTRATOR_API_BASE_URL` environment variable (recommended)
2. `NEXT_PUBLIC_API_BASE_URL` environment variable (if set)
3. Falls back to `http://127.0.0.1:8080` for local development

### Common Backend URLs

| Deployment Type | Example URL |
|----------------|-------------|
| Google Cloud Run | `https://llmhive-orchestrator-{project-id}.{region}.run.app` |
| Local Development | `http://127.0.0.1:8080` or `http://localhost:8080` |
| Other Cloud Provider | `https://your-backend-service.your-cloud.com` |

## Troubleshooting

### Frontend Can't Connect to Backend

**Symptom:** Frontend loads but API requests fail

**Solution:**
1. Check if `ORCHESTRATOR_API_BASE_URL` is set correctly
2. Verify the backend URL is accessible (try opening it in a browser)
3. Check that the backend is running (visit `/healthz` endpoint)
4. Review browser console for CORS or network errors

### Production Error: "Orchestration API base URL is not configured"

**Symptom:** Error message in production builds

**Solution:**
1. Go to Vercel dashboard → Settings → Environment Variables
2. Add `ORCHESTRATOR_API_BASE_URL` with your backend URL
3. Redeploy the application

### Backend Returns 404 on Health Check

**Symptom:** `https://your-backend-url/healthz` returns 404

**Solution:**
1. Verify you're using the correct backend URL
2. Check if the backend is deployed and running
3. Review backend logs for deployment issues
4. See [DEPLOYMENT.md](./DEPLOYMENT.md) for backend deployment help

## Next Steps

After identifying where your backend is hosted:

1. **Verify Backend Health:**
   ```bash
   curl https://your-backend-url/healthz
   # Should return: {"status":"ok"}
   ```

2. **Check Provider Configuration:**
   ```bash
   curl https://your-backend-url/api/v1/orchestration/providers
   # Shows available LLM providers
   ```

3. **Test the Connection:**
   - Run the frontend locally or visit your Vercel deployment
   - Try sending a message in the chat interface
   - Check browser console for any errors

## Additional Resources

- [UI README](./ui/README.md) - Frontend setup and configuration
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Backend deployment guide
- [VERCEL_DEPLOYMENT_GUIDE.md](./VERCEL_DEPLOYMENT_GUIDE.md) - Detailed Vercel deployment instructions
