from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv
import os
import asyncio

# Load environment variables
load_dotenv()

app = FastAPI(title="Profu API", version="1.0.0")

# Enable CORS for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific Flutter app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini model
def get_llm():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.0,
        google_api_key=api_key,
    )

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class QueryRequest(BaseModel):
    query: str
    history: list[Message] = []  # Conversation history

@app.get("/index")
async def index():
    """
    Returns a text response describing the Profu application.
    """
    return {
        "message": "Profu - Your AI-Powered Bacalaureat Preparation Assistant\n\n"
                   "Profu is an innovative educational platform designed to help Romanian high school "
                   "seniors prepare for the Bacalaureat exam. Our AI-driven application provides:\n\n"
                   "• Progressive Hints System: Upload math problems and receive step-by-step guidance\n"
                   "• Theory Bot: Ask questions and get curriculum-aligned answers\n"
                   "• 24/7 Access: Study anytime, anywhere at a fraction of the cost of private tutoring\n\n"
                   "Built with FastAPI backend and Flutter frontend."
    }

@app.get("/")
async def root():
    return {"message": "Profu API is running"}

@app.post("/clarify/stream")
async def clarify_stream(request: QueryRequest):
    """
    Streaming endpoint for clarifying concepts students didn't understand in class.
    Uses Gemini 1.5 Flash with LangChain for token streaming.
    """
    async def generate():
        try:
            llm = get_llm()
            
            # Create a system prompt for educational assistance
            system_prompt = """Ești un profesor răbdător și priceput care ajută elevii să înțeleagă concepte din programa de Bacalaureat.

Răspunde clar și concis, folosind:
- Explicații simple și accesibile
- Exemple concrete
- Analogii unde e necesar
- Structură logică, pas cu pas

Fii empatic și încurajator. Dacă elevul nu înțelege ceva specific din materia școlii, oferă clarificări detaliate.

**IMPORTANT: Formatează răspunsul în Markdown pentru o prezentare mai clară:**
- Folosește **bold** pentru concepte importante
- Folosește *italic* pentru sublinierea unor idei
- Folosește titluri (## sau ###) pentru secțiuni diferite
- Folosește liste numerotate (1., 2., 3.) pentru pași sau ordine
- Folosește liste cu bullet points (-, *) pentru enumerări
- Folosește > pentru note importante sau observații

**FORMULE MATEMATICE - FOARTE IMPORTANT:**
- Pentru formule inline (în text), folosește $formula$ (ex: $x^2 + y^2 = z^2$)
- Pentru formule pe linie separată (display), folosește $$formula$$ (ex: $$\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$$)
- Folosește sintaxa LaTeX standard pentru toate formulele matematice
- Exemple LaTeX:
  - Fracții: $\\frac{a}{b}$
  - Radicali: $\\sqrt{x}$ sau $\\sqrt[n]{x}$
  - Exponenți: $x^2$ sau $x^{2n}$
  - Indici: $x_1$ sau $x_{i,j}$
  - Integrale: $\\int_a^b f(x)dx$
  - Sume: $\\sum_{i=1}^n x_i$
  - Limite: $\\lim_{x \\to \\infty} f(x)$
  - Derivate: $\\frac{dy}{dx}$ sau $f'(x)$

**GRAFICE PENTRU FUNCȚII - FOARTE IMPORTANT:**
- Pentru a arăta graficul unei funcții, folosește:
```graph
function: f(x)=x^2
xMin: -5
xMax: 5
yMin: 0
yMax: 25
title: Graficul funcției f(x)=x²
```
- Sintaxă suportată pentru funcții:
  - Operații: +, -, *, /, ^ (putere)
  - Funcții: sin(x), cos(x), tan(x), sqrt(x), ln(x), log(x)
  - Exemple: x^2, 2*x+1, sin(x), x^3-2*x+1, sqrt(x)
- Parametrii opționali:
  - xMin, xMax: interval pentru axa X (implicit: -5 la 5)
  - yMin, yMax: interval pentru axa Y (implicit: -5 la 5)
  - title: titlu pentru grafic (opțional)
- Folosește grafice când explici funcții pentru vizualizare mai bună!

Exemplu de formatare completă:
## Conceptul de Derivată

**Definiție:** Derivata unei funcții $f(x)$ în punctul $x_0$ este:

$$f'(x_0) = \\lim_{h \\to 0} \\frac{f(x_0 + h) - f(x_0)}{h}$$

### Reguli de derivare:

1. **Regula puterii:** $(x^n)' = nx^{n-1}$
2. **Regula sumei:** $(f+g)' = f' + g'$
3. **Regula produsului:** $(f \\cdot g)' = f'g + fg'$

**Exemplu:** Derivata funcției $f(x) = x^2 + 3x + 1$:

$$f'(x) = 2x + 3$$

```graph
function: f(x)=x^2+3*x+1
xMin: -5
xMax: 2
yMin: -3
yMax: 15
title: Graficul funcției f(x)=x²+3x+1
```

> **Notă importantă:** Derivata măsoară rata de schimbare instantanee."""

            # Build message history for conversation context
            messages = [SystemMessage(content=system_prompt)]
            
            # Add conversation history
            for msg in request.history:
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))
            
            # Add current user query
            messages.append(HumanMessage(content=request.query))
            
            # Stream the response
            async for chunk in llm.astream(messages):
                if chunk.content:
                    # Escape newlines for SSE format (replace \n with placeholder)
                    content = chunk.content.replace('\n', '\\n')
                    # Send in SSE format
                    yield f"data: {content}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for smoother streaming
            
            # Signal completion
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            error_message = f"Eroare: {str(e)}"
            yield f"data: {error_message}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        }
    )
