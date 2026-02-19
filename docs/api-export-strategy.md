# Official API Export Strategy

## Overview
Instead of browser automation (blocked by Cloudflare, unstable), use official APIs.

---

## 1. Gemini (Google) — READY NOW ✓

**Status:** API keys available, can start immediately

**Keys:**
- Project `leipzig-observer`: `...KBUY` (Paid Tier 1, billing active)
- Project `823511539352`: `GWOs...`, `E6io...` (free tier, enabled but wrong project)

**API Endpoint:**
```
POST https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=API_KEY
```

**For Chat History:**
Google doesn't provide direct chat history API, but:
- Use Google Takeout API (automated via script)
- Or: Access via Activity API (limited)

**Action:** Use the KBUY key for Gemini operations

---

## 2. OpenAI/ChatGPT — NEEDS CREDIT

**Status:** API key exists but no credit

**Key Location:** `/root/.bashrc` as `OPENAI_API_KEY`

**Problem:** No credit on key → all requests fail

**Solution:**
1. Go to https://platform.openai.com/account/billing
2. Add credit ($10 minimum)
3. Then use API: `https://api.openai.com/v1/chat/completions`

**Note:** ChatGPT Plus subscription ($20/mo) does NOT include API credit!
- Subscription = web access
- API = separate pay-as-you-go

**Action Needed:** Simon must add API credit

---

## 3. Microsoft Copilot — COMPLEX

**Status:** No direct API for consumer Copilot chats

**Options:**
A) **Microsoft Graph API** (enterprise only)
   - Requires Azure AD app registration
   - Only works for business accounts
   - Consumer Microsoft account = not supported

B) **Bing Chat API** (unofficial, risky)
   - Reverse-engineered endpoints
   - May break anytime
   - Not recommended

C) **Manual export** (recommended)
   - https://copilot.microsoft.com → Settings → Export data
   - Takes 5 minutes, guaranteed to work

**Action:** Manual export is the only reliable path

---

## 4. Claude/Anthropic — NO API FOR HISTORY

**Status:** Anthropic doesn't provide chat history API (privacy design)

**Only Option:** Manual export via web UI
- https://claude.ai → Settings → Export data

**Action:** Manual export required

---

## Recommended Implementation Plan

### Phase 1: Gemini (Now)
```python
# Use existing KBUY key
# Script: /opt/ai-orchestrator/bin/fetch-gemini-history.py
# Uses: Google AI Studio API
```

### Phase 2: OpenAI (After Credit)
```python
# After Simon adds $10 credit
# Script: /opt/ai-orchestrator/bin/fetch-openai-history.py
# Uses: OpenAI API (not yet public for history)
# Fallback: Continue with manual export
```

### Phase 3: Copilot + Claude (Manual)
```bash
# Simon exports manually:
# 1. copilot.microsoft.com → Settings → Export
# 2. claude.ai → Settings → Export
# Copy JSONs to: /opt/ai-orchestrator/var/chat-exports/
# Then: Run parser/indexer
```

---

## Cost Comparison

| Method | Cost | Reliability |
|--------|------|-------------|
| Browser Automation | €0 | ✗ Blocked/Crashes |
| Official API | ~$0.01-0.10 per 100 chats | ✓ Guaranteed |
| Manual Export | €0 | ✓ Guaranteed |

**Conclusion:** Hybrid approach
- APIs where available (Gemini now, OpenAI after credit)
- Manual where necessary (Copilot, Claude)

---

## Next Steps

1. **Test Gemini API with KBUY key** (5 min)
2. **Simon adds OpenAI API credit** (when convenient)
3. **Manual exports for Copilot/Claude** (5 min total)
4. **Build unified parser** for all formats (10 min)
