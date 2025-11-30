# LLMHive Deployment Checklist

**Date:** November 17, 2025  
**Status:** Pre-Deployment

---

## ✅ **PRE-DEPLOYMENT CHECKLIST**

Use this checklist before going live. Check each item when complete.

---

## 🔐 **1. STRIPE CONFIGURATION**

- [ ] Stripe account created
- [ ] Stripe secret key obtained (`sk_test_...` or `sk_live_...`)
- [ ] Stripe webhook secret obtained (`whsec_...`)
- [ ] `STRIPE_SECRET_KEY` environment variable set on server
- [ ] `STRIPE_WEBHOOK_SECRET` environment variable set on server
- [ ] Stripe webhook endpoint configured in Stripe dashboard
- [ ] Stripe library installed (`pip install stripe>=7.0.0`)
- [ ] Test payment processed successfully

---

## 💾 **2. DATABASE SETUP**

- [ ] Database connection configured
- [ ] Database tables created (subscriptions, usage_records)
- [ ] Migration run successfully (or `Base.metadata.create_all()`)
- [ ] Database connection tested
- [ ] Can create test subscription in database

---

## 🔧 **3. ENVIRONMENT VARIABLES**

Check these are set on your server:

- [ ] `DATABASE_URL` - Database connection string
- [ ] `STRIPE_SECRET_KEY` - Stripe secret key
- [ ] `STRIPE_WEBHOOK_SECRET` - Stripe webhook secret
- [ ] `OPENAI_API_KEY` - OpenAI API key (if using OpenAI)
- [ ] `ANTHROPIC_API_KEY` - Anthropic API key (if using Claude)
- [ ] `MCP_SERVER_URL` - Optional, for external MCP server
- [ ] Any other provider API keys you're using

---

## 🧪 **4. TESTING**

### **API Endpoints:**
- [ ] `/healthz` - Health check works
- [ ] `/api/v1/orchestration/` - Orchestration works
- [ ] `/api/v1/billing/tiers` - Lists pricing tiers
- [ ] `/api/v1/billing/subscriptions` - Can create subscription
- [ ] `/api/v1/mcp/tools` - Lists MCP tools
- [ ] `/api/v1/mcp/tools/stats` - Shows tool statistics

### **Functionality:**
- [ ] Can create subscription via API
- [ ] Can process test payment
- [ ] Tools can be called by agents
- [ ] Usage tracking works
- [ ] Rate limiting works

---

## 🚀 **5. DEPLOYMENT**

- [ ] Code deployed to production server
- [ ] Server is running
- [ ] Website is accessible
- [ ] SSL certificate installed (HTTPS)
- [ ] Domain name configured
- [ ] DNS records set up correctly

---

## 📊 **6. MONITORING (Optional but Recommended)**

- [ ] Error logging set up
- [ ] Usage monitoring configured
- [ ] Performance tracking enabled
- [ ] Alerts configured (for critical errors)
- [ ] Dashboard access (if using monitoring service)

---

## 🔒 **7. SECURITY**

- [ ] API keys are in environment variables (not in code)
- [ ] Database credentials are secure
- [ ] HTTPS is enabled
- [ ] Rate limiting is active
- [ ] File system tools are restricted to safe paths
- [ ] API calls require HTTPS (except localhost)

---

## ✅ **8. FINAL VERIFICATION**

- [ ] All tests pass
- [ ] No critical errors in logs
- [ ] System responds quickly (< 5 seconds)
- [ ] Can create and pay for subscription
- [ ] Tools work correctly
- [ ] All orchestration protocols work

---

## 📝 **POST-DEPLOYMENT**

### **First Week:**
- [ ] Monitor error logs daily
- [ ] Check Stripe dashboard for payments
- [ ] Test subscription creation weekly
- [ ] Monitor system performance
- [ ] Check user feedback

### **Ongoing:**
- [ ] Weekly system health check
- [ ] Monthly subscription review
- [ ] Quarterly security review
- [ ] Regular backup verification

---

## 🆘 **IF SOMETHING GOES WRONG**

1. **Check error logs** - Look for error messages
2. **Check Stripe dashboard** - See if payments are failing
3. **Test endpoints** - Use `/healthz` to check if server is up
4. **Contact technical support** - Share error messages
5. **Check environment variables** - Make sure all are set

---

## ✅ **READY TO GO LIVE?**

Once all items above are checked, you're ready to launch! 🚀

---

**Last Updated:** November 17, 2025

