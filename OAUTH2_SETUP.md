# OAuth2 Setup Guide

This guide explains how to set up OAuth2 authentication for the Spark Log Analyzer, enabling secure passwordless authentication with OpenAI, Anthropic Claude, and Google Generative AI (Gemini).

## 🎯 Why OAuth2?

Instead of pasting sensitive API keys into forms (BYOK — Bring Your Own Key), OAuth2 allows:
- **Secure token exchange** without exposing keys to the web browser
- **Automatic token management** (storage, refresh, expiration)
- **Better UX** — just click "Login with [Provider]"
- **Audit trail** — tokens tied to authenticated users

---

## 📋 Prerequisites

1. Application running with Redis (for token storage)
2. Admin access to create OAuth apps on each provider

---

## 🔧 Setup Per Provider

### 1️⃣ OpenAI

#### Step 1: Activate OpenAI OAuth (Platform)
- Visit [OpenAI Platform Settings](https://platform.openai.com/account/org-settings/general)
- Enable OAuth2 if available (currently limited)
- Note: As of 2025, OpenAI OAuth is in early access. Fallback to API keys for now.

#### Step 2: Get Client Credentials
- Client ID: `openai_oauth_...` (if available)
- Client Secret: (if available)

#### Step 3: Register Redirect URI
- Add `http://localhost:8000/api/auth/callback/openai` (dev)
- For production: `https://yourdomain.com/api/auth/callback/openai`

#### Step 4: Add to `.env`
```bash
OPENAI_OAUTH_CLIENT_ID=your-openai-client-id
OPENAI_OAUTH_CLIENT_SECRET=your-openai-client-secret
```

---

### 2️⃣ Anthropic (Claude)

#### Step 1: Create OAuth App
- Visit [Anthropic Console](https://console.anthropic.com)
- Go to Settings → API Keys or OAuth (if available)
- Create a new API application

#### Step 2: Get Client Credentials
- Copy Client ID
- Copy Client Secret

#### Step 3: Register Redirect URI
- Development: `http://localhost:8000/api/auth/callback/anthropic`
- Production: `https://yourdomain.com/api/auth/callback/anthropic`

#### Step 4: Add to `.env`
```bash
ANTHROPIC_OAUTH_CLIENT_ID=your-anthropic-client-id
ANTHROPIC_OAUTH_CLIENT_SECRET=your-anthropic-client-secret
```

---

### 3️⃣ Google (Gemini)

#### Step 1: Create OAuth Credentials
- Visit [Google Cloud Console](https://console.cloud.google.com)
- Create new Project or select existing
- Enable "Generative Language API"

#### Step 2: Create OAuth 2.0 Credentials
- Go to APIs & Services → Credentials
- Click "Create Credentials" → OAuth client ID
- Application type: Web application
- Add Authorized redirect URIs:
  - `http://localhost:8000/api/auth/callback/gemini` (dev)
  - `https://yourdomain.com/api/auth/callback/gemini` (prod)

#### Step 3: Get Client Credentials
- Copy Client ID
- Copy Client Secret

#### Step 4: Add to `.env`
```bash
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret
```

---

## 🔐 Environment Configuration

Create or update `.env` in the project root:

```bash
# ── OAuth2 Configuration ────────────────────
OPENAI_OAUTH_CLIENT_ID=...
OPENAI_OAUTH_CLIENT_SECRET=...

ANTHROPIC_OAUTH_CLIENT_ID=...
ANTHROPIC_OAUTH_CLIENT_SECRET=...

GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...

# ── Security ────────────────────────────────
# Generate a strong key: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-strong-random-secret-key-here

# Frontend URL (used for OAuth redirects)
FRONTEND_URL=http://localhost:8000

# ── Redis (for token storage) ──────────────
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Generate a Strong Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and add to `.env` as `SECRET_KEY`.

---

## 🚀 Testing the OAuth Flow

### Local Development

1. **Start the app**:
   ```bash
   docker-compose up --build
   ```
   Or:
   ```bash
   uvicorn app:app --reload
   celery -A backend.celery_app worker --loglevel=info
   ```

2. **Open the browser**:
   - Navigate to http://localhost:8000

3. **Click OAuth Login**:
   - Click "🔑 Login with OpenAI" (or other provider)
   - You'll be redirected to the provider's login page
   - Authorize the app
   - Redirected back to the app with your token stored in Redis

4. **Upload & Analyze**:
   - Your OAuth token is automatically used for LLM analysis
   - No need to paste API keys!

---

## 🛡️ Security Best Practices

### Development ✅
- Use `SECRET_KEY=dev-key` temporarily for testing
- Redis on localhost is fine
- HTTP is acceptable for local testing

### Production 🔒
- **Use HTTPS only** — never use HTTP in production
- **Generate a strong SECRET_KEY**:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- **Use environment variables** — never commit credentials to git
- **Enable Redis authentication**: `redis-cli CONFIG SET requirepass your-password`
- **Rotate tokens regularly** — implement token refresh logic
- **Monitor token storage** — keep Redis memory under control
- **Rate limit OAuth endpoints** — prevent brute forcing
- **Use secure session cookies**: `Secure; HttpOnly; SameSite=Strict`

### OAuth Provider Settings 🔐
- Keep Client Secrets **never** exposed in frontend code
- Regularly rotate secrets on the provider console
- Whitelist only necessary redirect URIs
- Regularly audit connected applications

---

## ⚠️ Troubleshooting

### "Provider not configured" error
- **Cause**: OAuth Client ID/Secret not set in `.env`
- **Fix**: Add credentials and restart the app

### "Invalid state token" error
- **Cause**: Session expired or state mismatch
- **Fix**: Clear browser cookies and try again
- **Prevention**: Ensure `SECRET_KEY` is consistent across restarts

### Tokens not persisting
- **Cause**: Redis not running or unreachable
- **Fix**: Ensure Redis is running: `docker ps` or `redis-cli ping`
- Check `CELERY_BROKER_URL` in `.env`

### "Redirect URI mismatch" on provider login
- **Cause**: Registered URI doesn't match app's callback URL
- **Fix**: Update redirect URI in provider console to match:
  ```
  http://localhost:8000/api/auth/callback/{provider}
  ```

---

## 📊 How Tokens Are Stored

Tokens are stored in **Redis** with the following structure:

```
Key: `oauth_token:{user_id}:{provider}`
TTL: Provider-specific (24-90 days usually)
Value: JSON with access_token, refresh_token, metadata
```

**Security notes**:
- Tokens are NOT persisted to disk
- Tokens expire automatically based on provider settings
- Sensitive data is isolated in Redis memory
- Each request to analyze uses stored tokens (not passed in form)

---

## 🔄 Revoking Access

To logout and remove stored tokens, use the logout endpoint:

```bash
curl -X POST http://localhost:8000/api/auth/logout/openai?user_id=YOUR_USER_ID
```

Or click the × button on the auth status panel in the web UI.

---

## 📚 Additional Resources

- [FastAPI OAuth2 Docs](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/)
- [OpenAI API Docs](https://platform.openai.com/docs/)
- [Anthropic API Docs](https://docs.anthropic.com/)
- [Google Generative AI Docs](https://ai.google.dev/)
- [RFC 6749 — OAuth 2.0 Authorization Framework](https://tools.ietf.org/html/rfc6749)

---

**Need help?** Check the README.md or open an issue on GitHub!
