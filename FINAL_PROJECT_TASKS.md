# Final Project Tasks - Simple Instructions

**For:** Non-Technical Users  
**Date:** November 17, 2025

---

## 🎯 **YOUR MISSION**

Complete these tasks to finish the LLMHive project. Each task is explained in simple language with step-by-step instructions.

---

## ✅ **TASK 1: SET UP STRIPE (PAYMENT SYSTEM)**

### **What is Stripe?**
Stripe is a service that handles credit card payments. We need it so users can pay for subscriptions.

### **What You Need to Do:**

#### **Step 1.1: Create Stripe Account**
1. Open your web browser
2. Go to: https://stripe.com
3. Click the "Sign up" button (usually in the top right)
4. Enter your email address
5. Create a password (make it strong!)
6. Click "Create account"
7. Follow the setup steps
8. **Write down your email and password** (keep it safe!)

**⏱️ Time needed:** 10 minutes

---

#### **Step 1.2: Get Your Secret Key**
1. After logging into Stripe, look at the left side menu
2. Find and click "Developers"
3. Click "API keys" (under Developers)
4. You'll see a section called "Secret key"
5. Click the "Reveal test key" button
6. You'll see a key that starts with `sk_test_`
7. **Click the copy button** next to it
8. **Save this key somewhere safe** (like a text file or password manager)
   - This is your `STRIPE_SECRET_KEY`

**⏱️ Time needed:** 3 minutes

---

#### **Step 1.3: Set Up Webhooks**
1. Still in Stripe, stay in "Developers"
2. Click "Webhooks" (in the left menu)
3. Click "Add endpoint" button
4. In "Endpoint URL", enter:
   ```
   https://your-website.com/api/v1/billing/webhooks/stripe
   ```
   (Replace `your-website.com` with your actual website address)
5. Under "Events to send", click "Select events"
6. Check these boxes:
   - ✅ customer.subscription.created
   - ✅ customer.subscription.updated
   - ✅ customer.subscription.deleted
   - ✅ invoice.payment_succeeded
   - ✅ invoice.payment_failed
7. Click "Add endpoint"
8. You'll see a "Signing secret" - it starts with `whsec_`
9. **Click "Reveal" and copy it**
10. **Save this key somewhere safe**
    - This is your `STRIPE_WEBHOOK_SECRET`

**⏱️ Time needed:** 5 minutes

---

#### **Step 1.4: Give Keys to Your Technical Person**
1. Open an email or message to your technical person
2. Write this message:
   ```
   Hi [Name],
   
   I've set up Stripe. Please add these to the server:
   
   STRIPE_SECRET_KEY = [paste your secret key here]
   STRIPE_WEBHOOK_SECRET = [paste your webhook secret here]
   
   Also, please install: pip install stripe>=7.0.0
   
   Thanks!
   ```
3. Fill in the keys (paste them where it says `[paste...]`)
4. Send the message

**⏱️ Time needed:** 2 minutes

---

## ✅ **TASK 2: CREATE DATABASE TABLES**

### **What are Database Tables?**
Think of them like spreadsheets where we store information about subscriptions and usage.

### **What You Need to Do:**

1. **Send this message to your technical person:**
   ```
   Hi [Name],
   
   We need to create database tables for subscriptions and billing.
   The code is ready in: llmhive/src/llmhive/app/models.py
   
   Please run the database migration or use:
   Base.metadata.create_all(bind=engine)
   
   There's also a migration file at:
   llmhive/alembic/versions/001_add_billing_tables.py
   
   Thanks!
   ```

2. **Wait for them to confirm it's done**

**⏱️ Time needed:** Depends on your tech person (usually 15-30 minutes)

---

## ✅ **TASK 3: TEST THE SYSTEM**

### **What You Need to Do:**

#### **Step 3.1: Test the Website**
1. Open your LLMHive website in a browser
2. Try to use the chat feature
3. Send a test message
4. **Does it work?** ✅ Great! Continue.
5. **Does it show an error?** ❌ Write down the error and contact your tech person

**⏱️ Time needed:** 5 minutes

---

#### **Step 3.2: Test Creating a Subscription**
1. Go to your website
2. Look for a "Subscribe" or "Pricing" button
3. Try to create a test subscription
4. Use Stripe test mode (use test card: 4242 4242 4242 4242)
5. **Does it work?** ✅ Great!
6. **Does it fail?** ❌ Write down the error and contact your tech person

**⏱️ Time needed:** 10 minutes

---

#### **Step 3.3: Check Tool Usage**
1. Ask your technical person to check: `/api/v1/mcp/tools`
2. They should see a list of tools
3. **If they see tools:** ✅ Great!
4. **If they see an error:** ❌ Contact your tech person

**⏱️ Time needed:** 5 minutes (for your tech person)

---

## ✅ **TASK 4: FINAL DEPLOYMENT CHECKLIST**

### **Send This Checklist to Your Technical Person:**

```
Hi [Name],

Please check these before we go live:

[ ] All environment variables are set (especially Stripe keys)
[ ] Database tables are created
[ ] Stripe library is installed (pip install stripe)
[ ] Server is running and accessible
[ ] Health check works: /healthz
[ ] API endpoints respond correctly
[ ] No critical errors in logs

Let me know when everything is checked!
```

**⏱️ Time needed:** 30-60 minutes (for your tech person)

---

## ✅ **TASK 5: GO LIVE!**

### **What You Need to Do:**

1. **Once your tech person confirms everything is ready:**
   - Announce your launch!
   - Share your website with users
   - Monitor for any issues

2. **For the first week, check daily:**
   - Is the website working?
   - Are payments going through?
   - Are there any errors?

**⏱️ Time needed:** Ongoing monitoring

---

## 📝 **QUICK REFERENCE: MESSAGES TO SEND**

### **Message 1: Stripe Setup**
```
Please add these environment variables:
STRIPE_SECRET_KEY = [my key]
STRIPE_WEBHOOK_SECRET = [my key]
And install: pip install stripe>=7.0.0
```

### **Message 2: Database Setup**
```
Please create database tables for billing.
Use: Base.metadata.create_all() or run Alembic migration.
Migration file: llmhive/alembic/versions/001_add_billing_tables.py
```

### **Message 3: Testing**
```
Please test:
1. Subscription creation
2. Payment processing  
3. Tool usage
4. All API endpoints
```

---

## ⚠️ **COMMON PROBLEMS & SOLUTIONS**

### **Problem: "Can't find Stripe key"**
**Solution:** Make sure you copied the SECRET key (starts with `sk_`), not the publishable key

### **Problem: "Payment failed"**
**Solution:** 
- Make sure you're using test mode in Stripe
- Use test card: 4242 4242 4242 4242
- Check Stripe dashboard for error details

### **Problem: "Database error"**
**Solution:** Make sure database tables are created (Task 2)

### **Problem: "Tool not found"**
**Solution:** This might be normal. Ask your tech person to check if MCP is enabled.

---

## ✅ **YOUR COMPLETION CHECKLIST**

Use this to track your progress:

### **Stripe:**
- [ ] Account created
- [ ] Secret key copied
- [ ] Webhook secret copied
- [ ] Keys sent to tech person
- [ ] Stripe library installed (by tech person)

### **Database:**
- [ ] Tables created (by tech person)
- [ ] Confirmed working

### **Testing:**
- [ ] Website works
- [ ] Subscriptions work
- [ ] Payments work
- [ ] Tools work

### **Deployment:**
- [ ] Everything tested
- [ ] Ready to go live
- [ ] Monitoring set up

---

## 🎉 **YOU'RE DONE WHEN:**

1. ✅ Stripe is set up and working
2. ✅ Database tables are created
3. ✅ Everything is tested
4. ✅ System is running in production
5. ✅ Users can create subscriptions and make payments

---

## 📞 **NEED HELP?**

**Contact your technical person if:**
- You don't understand a step
- Something doesn't work
- You see error messages
- You're not sure if something is correct

**Always include:**
- What you were trying to do
- What step you were on
- Any error messages you saw

---

## 🚀 **GOOD LUCK!**

You've got this! Follow the steps one by one, and don't hesitate to ask for help.

**Estimated Total Time:** 2-4 hours (mostly waiting for your tech person)

---

**Last Updated:** November 17, 2025

