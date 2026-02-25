# Profu Flutter App

A Flutter-based mobile application for Bacalaureat exam preparation with AI assistance.

## Features

- **N-am înțeles la clasă**: Chat with AI to clarify concepts you didn't understand in class
- **Vreau să rezolv o problemă**: Practice with exercises and problems (coming soon)
- **Simulare**: Test your knowledge with simulations (coming soon)

## Prerequisites

- Flutter SDK (3.0.0 or higher)
- Dart SDK
- Running backend server (see `../backend/ai_backend/README.md`)

## Installation

1. Install dependencies:
```bash
cd flutter_app
flutter pub get
```

2. Ensure the backend is running on `http://localhost:8000`

## Running the App

For development with hot reload:
```bash
flutter run
```

For web:
```bash
flutter run -d chrome
```

For Android/iOS, ensure you have the respective emulators/simulators running.

## Features Implemented

### Chat Interface with Token Streaming, LaTeX, Graph Support, and Conversation Memory

The "N-am înțeles la clasă" option opens a chat interface that:
- Sends questions to the backend API
- **Maintains conversation history** for follow-up questions and context-aware responses
- Receives streamed responses token-by-token in real-time
- Displays a modern chat UI with message bubbles
- **Renders markdown formatting** in AI responses:
  - Bold, italic, underline
  - Headings (H1, H2, H3)
  - Bullet lists and numbered lists
  - Code blocks with syntax highlighting
  - Blockquotes
  - Inline code
- **Renders mathematical formulas with LaTeX**:
  - Inline formulas: `$x^2 + y^2 = z^2$`
  - Display formulas: `$$\frac{-b \pm \sqrt{b^2-4ac}}{2a}$$`
  - Full LaTeX syntax support for integrals, limits, derivatives, matrices, etc.
  - Beautiful mathematical typography
- **Renders interactive function graphs**:
  - 2D function plots with customizable ranges
  - Supports: polynomials, trigonometric, exponential, logarithmic functions
  - Auto-scaling and grid display
  - Syntax: ` ```graph ... ``` ` blocks with function definition
  - Example: `function: f(x)=x^2+2*x-3`
- Shows streaming indicators during response generation
- Allows text selection in AI responses

The streaming is implemented using Server-Sent Events (SSE) for real-time token delivery from the Gemini 2.0 Flash model. The conversation history is maintained in memory, allowing for natural follow-up questions and contextual clarifications.

## Architecture

- `lib/main.dart`: Main app entry point and landing page
- `lib/pages/clarify_chat_page.dart`: Chat interface with streaming support
- Uses `http` package for API communication
- Implements SSE parsing for token streaming

## Configuration

The app uses the **same `.env` file as the backend** (repo root). From the repo root, run:

```bash
uv run poe ui
```

This copies the root `.env` into `flutter_app/.env` and then starts Flutter, so you only maintain one `.env` (see root `.env.example`).

- **API_BASE_URL** (optional): FastAPI backend base URL; default `http://localhost:8000`.
- **SUPABASE_URL**, **SUPABASE_ANON_KEY**: Same as for ai_backend; set in root `.env`.

If you run `flutter run` directly from `flutter_app`, copy the root env first: `cp ../.env .env` (or the committed default `.env` in `flutter_app` is used).

### Supabase (local)
The app uses Supabase for auth and for CRUD (conversations, etc.). For local development:

1. From the repo root, run `npm install` then `npx supabase start` (see `../supabase/README.md`).
2. Run the auth migration: in the Supabase SQL Editor, run `backend/sql/auth_and_rls_migration.sql` (after `init.sql`).
3. In the **repo root** `.env`, set `SUPABASE_URL` and `SUPABASE_ANON_KEY` to the API URL and **anon** key printed by `npx supabase start`. Use `poe ui` so the Flutter app gets the same values.
4. Use `Supabase.instance.client` in your code for table access; the user's JWT is sent automatically and RLS enforces per-user data.

### Google Sign-In (optional)
To enable "Sign in with Google" you **must enable the Google provider** in Supabase; otherwise you get: `Unsupported provider: provider is not enabled`.

1. In [Google Cloud Console](https://console.cloud.google.com/), create an OAuth 2.0 Client ID (Web application). For Android/iOS, add the respective client IDs.
2. **Enable Google in Supabase:**
   - **Hosted (supabase.com):** Dashboard → **Authentication** → **Providers** → **Google** → turn **Enable** ON, paste **Client ID** and **Client secret**, Save.
   - **Local (`npx supabase start`):** You must edit **supabase/config.toml** (the hosted dashboard does not apply). See **[docs/SUPABASE_GOOGLE_LOCAL.md](../docs/SUPABASE_GOOGLE_LOCAL.md)** for step-by-step: add `[auth.external.google]` with `enabled = true`, `client_id`, `secret`, then run `npx supabase stop` and `npx supabase start`.
3. **Web:** Add your app URL to **Redirect URLs** (Supabase dashboard → Auth → URL Configuration). For local dev with `--web-port 7357`, add `http://localhost:7357/` (and set **Site URL** if needed). The app uses Supabase OAuth redirect for Google on web (no popup).
4. For **mobile** native Google sign-in, set the Web client ID (e.g. `--dart-define=GOOGLE_WEB_CLIENT_ID=...` or `lib/auth_config.dart`). Web uses Supabase OAuth redirect and does not need it for the button.
5. For Android: add the Web client ID to the app (see [Supabase Google auth](https://supabase.com/docs/guides/auth/social-login/auth-google)). For iOS: add the URL scheme from Supabase Auth settings.

## Testing

The app includes widget tests and unit tests.

### Running Tests

Run all tests:
```bash
flutter test
```

Run tests with coverage:
```bash
flutter test --coverage
```

Run specific test file:
```bash
flutter test test/widget_test.dart
```

### Test Structure

```
test/
├── widget_test.dart              # Main app widget tests
└── clarify_chat_page_test.dart   # Chat page widget tests
```

Tests cover:
- ✅ App initialization and build
- ✅ Navigation and drawer menu
- ✅ Dark theme configuration
- ✅ Chat page UI components
- ✅ Text input and send button
- ✅ Message display and scrolling
- ✅ ChatMessage model validation
