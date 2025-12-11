# Sentry Integration Guide

## Overview

This guide covers the Sentry integration for error tracking, performance monitoring, and logging in both the backend (Python/FastAPI) and frontend (React/TypeScript) applications.

## Quick Start

### 1. Get Your Sentry DSN

1. Create a Sentry account at https://sentry.io
2. Create a new project for each application:
   - Python project for backend
   - React project for frontend
3. Copy the DSN from Project Settings > Client Keys

### 2. Set Environment Variables

```bash
# Backend (.env)
SENTRY_DSN=https://xxxx@o123456.ingest.sentry.io/123456
ENVIRONMENT=production
APP_VERSION=1.0.0

# Frontend (.env)
VITE_SENTRY_DSN=https://xxxx@o123456.ingest.sentry.io/789012
VITE_ENVIRONMENT=production
VITE_APP_VERSION=1.0.0
```

### 3. Install Dependencies

```bash
# Backend
pip install sentry-sdk[fastapi,celery,sqlalchemy]

# Frontend
npm install @sentry/react
```

## Backend Setup

### Initialize Sentry in FastAPI

```python
# backend/app/main.py

from fastapi import FastAPI
from backend.app.core.sentry import init_sentry
from backend.app.middleware.sentry_middleware import SentryContextMiddleware

# Initialize Sentry before creating app
init_sentry(
    environment="production",
    traces_sample_rate=0.1,
)

app = FastAPI()

# Add Sentry context middleware
app.add_middleware(SentryContextMiddleware)
```

### Capture Exceptions

```python
from backend.app.core.sentry import capture_exception, capture_message

# Capture an exception with context
try:
    risky_operation()
except Exception as e:
    capture_exception(
        error=e,
        context={
            "operation": {
                "type": "document_parsing",
                "document_id": doc_id,
            }
        },
        tags={
            "feature": "parsing",
            "document_type": "pdf",
        }
    )
    raise

# Capture a warning message
capture_message(
    message="Low confidence extraction detected",
    level="warning",
    context={"field": "total_amount", "confidence": 0.45}
)
```

### Track LLM Errors

```python
from backend.app.core.sentry import track_llm_error

@track_llm_error
def call_openai(prompt: str) -> str:
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# Or manually:
from backend.app.core.sentry import capture_exception

try:
    result = call_openai(prompt)
except Exception as e:
    capture_exception(
        error=e,
        context={"llm": {"provider": "openai", "model": "gpt-4"}},
        tags={"error_type": "llm_error", "llm_provider": "openai"}
    )
    raise
```

### Track API Calls

```python
from backend.app.core.sentry import track_api_call

@track_api_call("whatsapp")
def send_whatsapp_message(to: str, message: str):
    response = requests.post(WHATSAPP_API_URL, json={...})
    response.raise_for_status()
    return response.json()
```

### Performance Monitoring

```python
from backend.app.core.sentry import SentrySpan

async def process_document(document_id: int):
    with SentrySpan("process_document", "Parse and analyze document") as span:
        span.set_tag("document_id", str(document_id))
        
        with SentrySpan("ocr", "Extract text via OCR"):
            text = await extract_text(document_id)
        
        with SentrySpan("audit", "Run audit engine"):
            result = await run_audit(text)
        
        return result
```

## Frontend Setup

### Initialize Sentry in React

```typescript
// src/main.tsx

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { initSentry } from './lib/sentry';
import ErrorBoundary from './components/ErrorBoundary';

// Initialize Sentry before rendering
initSentry({
  environment: 'production',
  tracesSampleRate: 0.1,
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
```

### Capture Exceptions

```typescript
import { captureException, captureMessage } from './lib/sentry';

// Capture an exception
try {
  await riskyOperation();
} catch (error) {
  captureException(error as Error, {
    operation: {
      type: 'file_upload',
      file_size: file.size,
    },
  }, {
    feature: 'upload',
  });
  throw error;
}

// Capture a message
captureMessage(
  'User completed onboarding',
  'info',
  { step: 'final', duration_seconds: 45 }
);
```

### Track API Errors

```typescript
import { trackApiError } from './lib/sentry';

try {
  const response = await apiClient.post('/uploads', formData);
} catch (error) {
  if (axios.isAxiosError(error)) {
    trackApiError(
      error,
      '/uploads',
      'POST',
      error.response?.status
    );
  }
  throw error;
}
```

### Track LLM Errors

```typescript
import { trackLLMError } from './lib/sentry';

try {
  const summary = await generateAuditSummary(auditData);
} catch (error) {
  trackLLMError(
    error as Error,
    'openai',
    'generate_summary',
    prompt.length
  );
  throw error;
}
```

### Set User Context

```typescript
import { setUserContext } from './lib/sentry';

// After login
setUserContext({
  id: user.id,
  email: user.email,
  username: user.username,
});

// After logout
setUserContext(null);
```

### Error Boundary Usage

```tsx
import { SentryErrorBoundary } from './components/ErrorBoundary';

function App() {
  return (
    <SentryErrorBoundary>
      <Router>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/upload" element={<UploadPage />} />
        </Routes>
      </Router>
    </SentryErrorBoundary>
  );
}
```

## What Gets Tracked

### Backend

| Event Type | Description |
|------------|-------------|
| Unhandled Exceptions | All uncaught exceptions in API routes |
| Logged Errors | `logger.error()` and `logger.warning()` calls |
| LLM Errors | OpenAI/HuggingFace API failures |
| API Call Failures | External service errors (WhatsApp, SMTP) |
| Celery Task Errors | Failed background tasks |
| Database Errors | SQLAlchemy exceptions |

### Frontend

| Event Type | Description |
|------------|-------------|
| Unhandled Exceptions | React errors and JavaScript exceptions |
| API Errors | Failed HTTP requests (5xx, 401, 403, 429) |
| LLM Errors | Frontend LLM API call failures |
| Console Errors | `console.error()` calls |
| User Feedback | Via Sentry dialog |

## Sample Rates

| Environment | Error Rate | Traces Rate | Replays Rate |
|-------------|-----------|-------------|--------------|
| Production | 100% | 10% | 10% on error, 1% always |
| Staging | 100% | 50% | 50% |
| Development | 100% | 100% | 0% |

## Filtering

### Ignored Errors

Backend:
- `ConnectionResetError`
- `BrokenPipeError`
- Health check endpoints

Frontend:
- `ResizeObserver` errors
- Network/fetch errors
- Cancelled requests
- Browser extension errors

### Ignored Endpoints

- `/health`
- `/ready`
- `/metrics`
- `/favicon.ico`

## Alerts Configuration

Configure alerts in Sentry:

1. **High Error Rate**: >5% error rate in 5 minutes
2. **New Issue**: First occurrence of an error
3. **Regression**: Error returns after being resolved
4. **LLM Failures**: Tag: `error_type:llm_error`
5. **API Failures**: Tag: `error_type:api_error`

## Best Practices

1. **Always add context**: Include relevant data to debug issues
2. **Use tags**: Make it easy to filter and search
3. **Set user context**: Track which users are affected
4. **Add breadcrumbs**: Leave a trail of user actions
5. **Don't track PII**: Scrub sensitive data before sending
6. **Use appropriate levels**: error, warning, info
7. **Group related errors**: Use fingerprints when needed

## Troubleshooting

### Events not appearing

1. Check DSN is correctly configured
2. Verify network connectivity to Sentry
3. Check sample rate isn't filtering events
4. Look for `beforeSend` filtering

### Too many events

1. Reduce sample rates
2. Add more filters to `beforeSend`
3. Use `ignoreErrors` for known issues
4. Add rate limiting in Sentry project settings

### Missing context

1. Ensure middleware is added
2. Check user context is set after login
3. Add breadcrumbs for key actions
4. Include relevant data in exception context

