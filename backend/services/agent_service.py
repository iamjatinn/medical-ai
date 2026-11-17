"""A small tool-using agent (the LLM function-calling loop).

    question ──► Gemini ──► "call tool X with args"
                   ▲              │
                   │              ▼
                   └──── tool result (exact data) ◄── run tool X

The loop repeats until Gemini answers in plain text, or until MAX_STEPS tool
rounds have happened (a safety limit so it can never loop forever).
"""

import logging

from google.genai import types

from services import gemini_service
from services.tools_service import TOOL_DECLARATIONS, ReportTools

logger = logging.getLogger(__name__)

MAX_STEPS = 5


def _config(system_instruction: str, with_tools: bool = True):

    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[TOOL_DECLARATIONS] if with_tools else None,
        temperature=0.2,
        # We run the loop ourselves so every step is visible, limited and testable.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def _history_to_contents(history):
    """Stored chat history ({"role": "user"|"assistant", ...}) -> Gemini contents."""

    contents = []

    for message in history:
        role = "user" if message["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=message["content"])]))

    return contents


def run_agent(
    tools: ReportTools,
    question: str,
    history,
    system_instruction: str,
    client=None,
    max_steps: int = MAX_STEPS,
) -> dict:
    """Answer a question, calling tools when needed.

    Returns {"answer": str, "tools_used": [tool names in call order], "steps": int}.
    """

    client = client or gemini_service._get_client()

    contents = _history_to_contents(history)
    contents.append(types.Content(role="user", parts=[types.Part(text=question)]))

    tools_used = []

    for step in range(1, max_steps + 1):

        response, model_used = gemini_service.generate_with_fallback(
            client=client, contents=contents, config=_config(system_instruction),
        )

        calls = response.function_calls

        if not calls:
            return {"answer": (response.text or "").strip(), "tools_used": tools_used, "steps": step, "model": model_used}

        # Keep the model's own "I want to call these tools" turn in the conversation...
        contents.append(response.candidates[0].content)

        # ...run each requested tool, and hand the results back.
        parts = []

        for call in calls:
            args = dict(call.args or {})
            logger.info("Agent step %d: calling tool %s(%s)", step, call.name, args)

            tools_used.append(call.name)

            parts.append(types.Part.from_function_response(
                name=call.name,
                response={"result": tools.execute(call.name, args)},
            ))

        contents.append(types.Content(role="user", parts=parts))

    # Step limit reached: ask for a final answer from what was gathered, with no tools.
    logger.warning("Agent hit the %d-step limit; asking for a final answer", max_steps)

    final, model_used = gemini_service.generate_with_fallback(
        client=client, contents=contents, config=_config(system_instruction, with_tools=False),
    )

    return {"answer": (final.text or "").strip(), "tools_used": tools_used, "steps": max_steps, "model": model_used}
