# Vercel Deployment Guide for LLMHive

This guide walks you through deploying the LLMHive MVP Cockpit to Vercel.

## Prerequisites

- GitHub account with access to the `LLLHive/LLMHIVE` repository
- API keys for:
  - OpenAI (`OPENAI_API_KEY`)
  - Anthropic (`ANTHROPIC_API_KEY`)
  - Tavily (`TAVILY_API_KEY`)

## Step-by-Step Deployment

### 1. Create a Vercel Account

1. Go to [vercel.com](https://vercel.com)
2. Click "Sign Up"
3. Choose "Continue with GitHub"
4. Authorize Vercel to access your GitHub account

### 2. Import the LLMHive Project

1. From your Vercel dashboard, click **"Add New..."** → **"Project"**
2. Find and select the `LLLHive/LLMHIVE` repository
3. Click **"Import"**

### 3. Configure the Project

The repository contains both a FastAPI backend and the Next.js frontend. To deploy the UI you must tell Vercel to build only the `ui/` directory.

1. In the **Project Settings** screen, expand **"Build & Output Settings"** (or click **"Settings" → "Build & Output Settings"** after the project is created).
2. Set **Root Directory** to `ui`.
3. Set **Framework Preset** to **Next.js**.
4. Ensure the commands are:
   - **Install Command**: `npm install`
   - **Build Command**: `npm run build`
   - Leave **Output Directory** blank (Vercel will use `.next`).
5. Save the settings. If Vercel shows separate **Production Overrides**, repeat the same values there before saving.

### 4. Set Environment Variables

Before deploying, add the following environment variables:

1. In the project configuration screen, find the **"Environment Variables"** section
2. Add each of the following variables:

| Variable Name | Description | Example Value |
|--------------|-------------|---------------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |
| `ANTHROPIC_API_KEY` | Your Anthropic API key | `sk-ant-...` |
| `TAVILY_API_KEY` | Your Tavily search API key | `tvly-...` |
| `CORS_ORIGINS` (Optional) | Allowed frontend domains | Leave empty for development |

> **Important**: Do NOT include quotes around the values. Just paste the key directly.

### 5. Deploy

1. Click the **"Deploy"** button
2. Wait approximately 2-3 minutes for the build and deployment to complete
3. You'll see a progress screen showing the Next.js build steps. If the log mentions searching for a FastAPI entry point, go back to Step 3 and confirm the Framework Preset and Root Directory overrides are saved.

### 6. Access Your Application

Once deployment is complete:
1. Vercel will show you a deployment URL (e.g., `https://llmhive.vercel.app`)
2. Click on the URL to open your application
3. You should see the LLMHive chat interface

## Post-Deployment Configuration

### Restrict CORS Origins (Recommended for Production)

For security, restrict CORS to only your Vercel domain:

1. Go to your project settings in Vercel
2. Navigate to **"Environment Variables"**
3. Add or update `CORS_ORIGINS` with your deployment URL:
   ```
   CORS_ORIGINS=https://your-project.vercel.app
   ```
4. Redeploy the application for the changes to take effect

### Custom Domain (Optional)

To use a custom domain like `llmhive.com`:

1. Go to **Settings** → **Domains** in your Vercel project
2. Click **"Add"**
3. Enter your domain name
4. Follow Vercel's instructions to update your DNS records
5. Update `CORS_ORIGINS` to include your custom domain

## Troubleshooting

### Build Failures

**"No FastAPI entrypoint found" error appears:**
- Vercel is still trying to run the backend builder. Confirm **Framework Preset** is set to **Next.js** and **Root Directory** is `ui` in both the general settings and any **Production Overrides**.
- Redeploy with build cache disabled after saving the overrides.

**Frontend build fails:**
- Check the build logs for specific TypeScript or dependency errors.
- Verify `ui/package.json` lists all required dependencies and scripts.

### Runtime Errors

**500 Internal Server Error:**
- Check the Function logs in Vercel dashboard
- Verify all environment variables are set correctly
- Ensure API keys are valid and not expired

**CORS Errors:**
- Check browser console for specific CORS error messages
- Verify `CORS_ORIGINS` environment variable is set correctly
- Try setting `CORS_ORIGINS` to `*` temporarily to test

**API Endpoint Not Found:**
- Verify the URL path (should be `/api/prompt` for the main endpoint)
- Check that `vercel.json` routing is configured correctly
- Review Function logs for routing errors

## Monitoring and Logs

### View Application Logs

1. Go to your project in Vercel dashboard
2. Click on the deployment
3. Navigate to the **"Functions"** tab
4. Click on a function to see its logs

### Monitor Usage

1. Go to **Settings** → **Usage**
2. Monitor:
   - Function invocations
   - Bandwidth usage
   - Build minutes

## Updating Your Deployment

### Automatic Deployments

Vercel automatically deploys when you push to your GitHub repository:
- **Production**: Pushes to `main` branch
- **Preview**: Pushes to other branches

### Manual Redeployment

To manually trigger a deployment:
1. Go to the **Deployments** tab
2. Click the **"..."** menu on a previous deployment
3. Select **"Redeploy"**

## Environment-Specific Configurations

### Development vs Production

Vercel distinguishes between:
- **Production**: Deployments from your default branch (usually `main`)
- **Preview**: Deployments from other branches

You can set different environment variables for each:
1. When adding environment variables, choose:
   - **Production** only
   - **Preview** only
   - **Both**

## Cost Considerations

Vercel Free Tier includes:
- 100 GB bandwidth per month
- 100 GB-hours serverless function execution
- Unlimited deployments

For LLMHive, this should be sufficient for:
- Development and testing
- Low-to-moderate production traffic
- Multiple team members

Upgrade to Pro ($20/month) if you need:
- More bandwidth
- More function execution time
- Team collaboration features
- Priority support

## Security Best Practices

1. ✅ **Never commit API keys** to your repository
2. ✅ **Use environment variables** for all sensitive data
3. ✅ **Restrict CORS origins** in production
4. ✅ **Enable Vercel's security features**:
   - Automatic HTTPS
   - DDoS protection
   - Password protection (Pro feature)
5. ✅ **Regularly rotate API keys**
6. ✅ **Monitor function logs** for suspicious activity

## Next Steps

After successful deployment:
1. Test the chat interface with various prompts
2. Connect the frontend to the real backend API (currently simulated)
3. Implement user authentication if needed
4. Add custom branding and styling
5. Set up monitoring and alerting
6. Configure a custom domain

## Support Resources

- **Vercel Documentation**: [vercel.com/docs](https://vercel.com/docs)
- **Next.js Documentation**: [nextjs.org/docs](https://nextjs.org/docs)
- **FastAPI Documentation**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **LLMHive Repository**: [github.com/LLLHive/LLMHIVE](https://github.com/LLLHive/LLMHIVE)

## Getting Help

If you encounter issues:
1. Check the Vercel deployment logs
2. Review the browser console for frontend errors
3. Check the Function logs for backend errors
4. Consult the troubleshooting section above
5. Open an issue on the GitHub repository
