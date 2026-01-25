# Profu Flutter App

A Flutter-based mobile application for Bacalaureat exam preparation with AI assistance.

## Features

- **N-am înțeles la clasă**: Chat with AI to clarify concepts you didn't understand in class
- **Vreau să rezolv o problemă**: Practice with exercises and problems (coming soon)
- **Simulare**: Test your knowledge with simulations (coming soon)

## Prerequisites

- Flutter SDK (3.0.0 or higher)
- Dart SDK
- Running backend server (see `../backend/README.md`)

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

To change the backend URL, edit the `_apiUrl` variable in:
- `lib/main.dart` (line 38)
- `lib/pages/clarify_chat_page.dart` (line 18)
