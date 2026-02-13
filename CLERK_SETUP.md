# Clerk Authentication Setup Guide

## Understanding Clerk Keys

Clerk uses **two different keys** for frontend and backend:

### 1. **Publishable Key** (Frontend - Public)
- **Environment Variable**: `VITE_CLERK_PUBLISHABLE_KEY`
- **Location**: Frontend `.env` file
- **Purpose**: Initialize Clerk in the React app
- **Security**: Safe to expose (it's public)
- **Format**: `pk_test_...` or `pk_live_...`

### 2. **Secret Key** (Backend - Private)
- **Environment Variable**: `CLERK_SECRET_KEY`
- **Location**: Backend `.env` file (or environment variables)
- **Purpose**: Verify JWT tokens on the backend
- **Security**: **NEVER expose this** - keep it secret!
- **Format**: `sk_test_...` or `sk_live_...`

## Current Setup Issues

❌ **WRONG**: You mentioned `CLERK_SECRET_KEY` is in frontend as `VITE_CLERK_PUBLISHABLE_KEY`
- These are **different keys** with different purposes
- The secret key should **never** be in the frontend

✅ **CORRECT Setup**:

### Frontend (`.env` or `.env.local`):
```env
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxx
```

### Backend (`.env` in `backend/` folder):
```env
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxxx
OPENROUTER_API_KEY=your_openrouter_key
```

## How It Works

1. **Frontend**: Uses `VITE_CLERK_PUBLISHABLE_KEY` to initialize Clerk
2. **User Logs In**: Clerk creates a session and JWT token
3. **Frontend Gets Token**: `getToken()` from `useAuth()` hook returns JWT
4. **Backend Receives Token**: In `Authorization: Bearer <token>` header
5. **Backend Verifies Token**: 
   - **Development**: Decodes JWT directly (no API call needed)
   - **Production**: Can verify with Clerk API using `CLERK_SECRET_KEY`

## Development vs Production

### Development Mode (Current Implementation)
- Decodes JWT token directly without verification
- Works even without `CLERK_SECRET_KEY` set
- Faster (no API calls)
- Less secure (doesn't verify signature)

### Production Mode
- Verifies token with Clerk API
- Requires `CLERK_SECRET_KEY` to be set
- More secure (verifies signature)
- Slower (makes API call)

## Getting Your Keys

1. Go to [Clerk Dashboard](https://dashboard.clerk.com)
2. Select your application
3. Go to **API Keys** section
4. Copy:
   - **Publishable Key** → Use in frontend
   - **Secret Key** → Use in backend (keep secret!)

## Troubleshooting

### Issue: "Authorization header missing"
- **Cause**: Frontend not sending token
- **Fix**: Check that `getToken()` is being called and passed to API

### Issue: "Invalid or expired token"
- **Cause**: Token is malformed or expired
- **Fix**: Make sure user is logged in, token is fresh

### Issue: "User ID not found"
- **Cause**: Token doesn't contain user_id
- **Fix**: Check token payload structure

## Current Implementation

The current `auth.py` implementation:
1. ✅ Accepts JWT tokens from frontend
2. ✅ Decodes JWT to extract `user_id` (development mode)
3. ✅ Falls back to Clerk API verification if `CLERK_SECRET_KEY` is set
4. ✅ Accepts direct `user_xxx` strings for testing
5. ✅ Returns `None` if no auth header (allows anonymous access)

This setup works for **development** without requiring `CLERK_SECRET_KEY` to be set!

