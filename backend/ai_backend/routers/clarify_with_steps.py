"""
Clarify Step by Step Router - Step-by-step interactive learning mode.
Uses LangGraph to guide students through prerequisites before explaining the main concept.
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import asyncio
import time
import json
import re

from .common import (
    get_llm,
    QueryRequest,
    PROMPTS,
    get_current_user_id,
    load_conversation_history_for_user,
)


router = APIRouter(prefix="/clarify", tags=["clarify_step_by_step"])


class StepByStepLearningState(TypedDict):
    """State for the step-by-step learning graph"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    original_query: str
    prerequisites: list[str]
    current_prerequisite_index: int
    prerequisites_completed: bool
    progress_preview_sent: bool  # Track if we sent the initial preview


def extract_json_from_text(text: str) -> dict:
    """Extract JSON from text that might contain markdown code blocks"""
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))
    
    # Try to find raw JSON
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))
    
    raise ValueError("No JSON found in response")


async def generate_prerequisites(state: StepByStepLearningState) -> StepByStepLearningState:
    """Node 1: Generate list of prerequisite concepts"""
    llm = get_llm()
    
    system_prompt = PROMPTS['guided_learning']['prerequisite_generator']['system_prompt']
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Elevul întreabă: {state['original_query']}")
    ]
    
    response = await llm.ainvoke(messages)
    
    try:
        # Extract JSON from response
        result = extract_json_from_text(response.content)
        prerequisites = result.get('prerequisites', [])
        
        # Generate preview message
        if prerequisites:
            preview_items = "\n".join([f"{i+1}. {concept} 🎯" for i, concept in enumerate(prerequisites)])
            preview_message = f"""Minunat! Pentru a înțelege **{state['original_query']}**, vom parcurge următoarele concepte:

{preview_items}

Să începem cu primul! 🚀"""
        else:
            preview_message = "Să începem! 🚀"
        
        # Add preview as an AI message
        preview_ai_message = AIMessage(content=preview_message)
        
        return {
            **state,
            "prerequisites": prerequisites,
            "current_prerequisite_index": 0,
            "prerequisites_completed": False,
            "progress_preview_sent": True,
            "messages": [preview_ai_message],
        }
    except Exception as e:
        # Fallback: if JSON parsing fails, return empty prerequisites
        return {
            **state,
            "prerequisites": [],
            "current_prerequisite_index": 0,
            "prerequisites_completed": True,
            "progress_preview_sent": True,
        }


async def ask_prerequisite_question(state: StepByStepLearningState) -> StepByStepLearningState:
    """Node 2: Ask about current prerequisite concept"""
    llm = get_llm()
    
    current_index = state['current_prerequisite_index']
    prerequisites = state['prerequisites']
    
    # Check if we've completed all prerequisites
    if current_index >= len(prerequisites):
        return {
            **state,
            "prerequisites_completed": True,
        }
    
    current_concept = prerequisites[current_index]
    total_prerequisites = len(prerequisites)
    system_prompt = PROMPTS['guided_learning']['question_asker']['system_prompt']
    
    # Add progress context to the system prompt
    progress_info = f"""
    Progres: Conceptul {current_index + 1} din {total_prerequisites}
    
    IMPORTANT: La începutul răspunsului tău, include un indicator de progres:
    "**[Concept {current_index + 1}/{total_prerequisites}]** [emoji relevant]"
    
    Exemple de emoji:
    - 📖 pentru concepte teoretice
    - 🔢 pentru matematică/numere
    - 📐 pentru geometrie
    - 🎯 pentru obiective
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=f"Conceptul curent de verificat: {current_concept}"),
        SystemMessage(content=progress_info),
    ]
    
    # Add conversation history (last 6 messages to keep context manageable)
    conversation_messages = state.get('messages', [])[-6:]
    messages.extend(conversation_messages)
    
    response = await llm.ainvoke(messages)
    
    # Check if the response indicates the student understands and can move on
    # Look for keywords that indicate completion
    completion_indicators = [
        "putem trece",
        "următorul pas",
        "ai înțeles",
        "foarte bine",
        "corect",
        "exact",
    ]
    
    response_lower = response.content.lower()
    should_advance = any(indicator in response_lower for indicator in completion_indicators)
    
    new_index = current_index + 1 if should_advance else current_index
    
    return {
        **state,
        "messages": [response],
        "current_prerequisite_index": new_index,
        "prerequisites_completed": new_index >= len(prerequisites),
    }


async def provide_final_explanation(state: StepByStepLearningState) -> StepByStepLearningState:
    """Node 3: Provide complete explanation of the original concept"""
    llm = get_llm()
    
    system_prompt = PROMPTS['guided_learning']['final_explainer']['system_prompt']
    
    # Build context about prerequisites covered with numbers
    prerequisites_list = state['prerequisites']
    prerequisites_summary = "\n".join([f"{i+1}. {p}" for i, p in enumerate(prerequisites_list)])
    
    # Add explicit instruction for recap format
    recap_instruction = f"""
    IMPORTANT: Începe răspunsul cu această structură EXACTĂ:
    
    📚 **Recapitulare:** Până acum am învățat despre:
    {chr(10).join([f"{i+1}. ✓ {concept}" for i, concept in enumerate(prerequisites_list)])}
    
    Acum putem înțelege pe deplin **{state['original_query']}**! 🎯
    
    [apoi continuă cu explicația completă]
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=recap_instruction),
        SystemMessage(content=f"Întrebarea inițială a elevului: {state['original_query']}"),
        SystemMessage(content=f"Concepte prerequisite acoperite:\n{prerequisites_summary}"),
        HumanMessage(content=f"Acum explică-mi complet: {state['original_query']}")
    ]
    
    response = await llm.ainvoke(messages)
    
    return {
        **state,
        "messages": [response],
    }


def should_continue_prerequisites(state: StepByStepLearningState) -> str:
    """Routing function: decide if we continue with prerequisites or move to final explanation"""
    if state.get('prerequisites_completed', False):
        return "final_explanation"
    return "ask_question"


def build_step_by_step_learning_graph():
    """Build the step-by-step learning state graph"""
    workflow = StateGraph(StepByStepLearningState)
    
    # Add nodes
    workflow.add_node("generate_prerequisites", generate_prerequisites)
    workflow.add_node("ask_question", ask_prerequisite_question)
    workflow.add_node("final_explanation", provide_final_explanation)
    
    # Set entry point
    workflow.set_entry_point("generate_prerequisites")
    
    # Add edges
    workflow.add_edge("generate_prerequisites", "ask_question")
    workflow.add_conditional_edges(
        "ask_question",
        should_continue_prerequisites,
        {
            "ask_question": "ask_question",  # Continue with prerequisites
            "final_explanation": "final_explanation",  # Move to final explanation
        }
    )
    workflow.add_edge("final_explanation", END)
    
    return workflow.compile()


@router.post("/step-by-step-stream")
async def clarify_step_by_step_stream(
    request: QueryRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Streaming endpoint for step-by-step guided learning.
    Uses LangGraph to guide students through prerequisites before explaining the main concept.
    
    Args:
        request: QueryRequest containing the user's query and conversation history
        
    Returns:
        StreamingResponse with Server-Sent Events (SSE) containing AI response tokens
    """
    async def generate():
        try:
            start_time = time.time()
            first_token_received = False

            # Prefer loading history from Supabase by conversation_id when provided,
            # fall back to the history array from the client for backwards compatibility.
            history = request.history
            if request.conversation_id is not None:
                loaded = load_conversation_history_for_user(user_id, request.conversation_id)
                if loaded:
                    history = loaded

            # Check if this is the initial query (no prior messages) or a follow-up
            is_initial_query = len(history) == 0
            
            if is_initial_query:
                # Initial query: Run the full graph starting with prerequisite generation
                graph = build_step_by_step_learning_graph()

                initial_state: StepByStepLearningState = {
                    "messages": [],
                    "original_query": request.query,
                    "prerequisites": [],
                    "current_prerequisite_index": 0,
                    "prerequisites_completed": False,
                    "progress_preview_sent": False,
                }
                
                # Run through prerequisite generation and first question
                result = await graph.ainvoke(initial_state)
                
                # Stream the response
                if result['messages']:
                    response_message = result['messages'][-1]
                    
                    # Send metadata
                    time_to_first_token = time.time() - start_time
                    metadata = json.dumps({"ttft": round(time_to_first_token, 3)})
                    yield f"data: [META]{metadata}\n\n"
                    
                    # Stream the content character by character for smooth effect
                    for char in response_message.content:
                        content = char.replace('\n', '\\n')
                        yield f"data: {content}\n\n"
                        await asyncio.sleep(0.01)
                
            else:
                # Follow-up query: Continue the conversation with question_asker logic
                # We need to rebuild state from history
                llm = get_llm()

                # Build message history
                system_prompt = PROMPTS['guided_learning']['question_asker']['system_prompt']
                messages = [SystemMessage(content=system_prompt)]

                # Add conversation history
                for msg in history:
                    if msg.role == "user":
                        messages.append(HumanMessage(content=msg.content))
                    elif msg.role == "assistant":
                        messages.append(AIMessage(content=msg.content))
                
                # Add current query
                messages.append(HumanMessage(content=request.query))
                
                # Stream the response
                async for chunk in llm.astream(messages):
                    if chunk.content:
                        if not first_token_received:
                            time_to_first_token = time.time() - start_time
                            metadata = json.dumps({"ttft": round(time_to_first_token, 3)})
                            yield f"data: [META]{metadata}\n\n"
                            first_token_received = True
                        
                        content = chunk.content.replace('\n', '\\n')
                        yield f"data: {content}\n\n"
                        await asyncio.sleep(0.01)
            
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
            "X-Accel-Buffering": "no",
        }
    )