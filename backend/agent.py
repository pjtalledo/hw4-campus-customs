"""Campus Customs chatbot agent using PydanticAI."""

import os
import logging
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

try:
    from .tools import register_tools
    from .audit import record_agent_run
except ImportError:
    from tools import register_tools
    from audit import record_agent_run

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Maximum number of prior turns (user+assistant pairs) sent to the model as
# conversation history. Keeps token usage bounded for long-lived accounts.
MAX_HISTORY_MESSAGES = 20


@dataclass
class ChatDeps:
    """Per-request dependencies passed to the agent via RunContext.

    A new instance is created for every chat() call, so each request gets
    its own isolated state. Tools mutate ctx.deps.products directly
    (same object reference, not a context-copy), which is safe even if
    PydanticAI executes sync tools in a worker thread.
    """
    products: list = field(default_factory=list)
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    page_context: Optional[dict] = None


def load_system_prompt() -> str:
    """Load system prompt from prompts/prompt.md."""
    prompt_path = Path(__file__).parent / "prompts" / "prompt.md"
    with open(prompt_path, 'r') as f:
        return f.read()


def create_agent() -> Agent:
    """Create and configure the Campus Customs PydanticAI chatbot agent.

    Uses Portkey as the OpenAI-compatible provider via PORTKEY_API_KEY.
    PORTKEY_API_KEY environment variable must be set.

    Returns:
        A configured pydantic_ai.Agent instance with OpenAI gpt-4o-mini model
    """
    system_prompt = load_system_prompt()
    portkey_api_key = os.getenv('PORTKEY_API_KEY')

    if not portkey_api_key:
        logger.error("PORTKEY_API_KEY environment variable not found")
        raise ValueError("PORTKEY_API_KEY environment variable is not set")

    logger.debug(f"PORTKEY_API_KEY found (length: {len(portkey_api_key)})")

    # Configure environment for OpenAI client to use Portkey gateway
    os.environ['OPENAI_API_KEY'] = portkey_api_key
    os.environ['OPENAI_BASE_URL'] = 'https://api.portkey.ai/v1'

    logger.info("Environment configured for Portkey OpenAI gateway")

    try:
        # Create PydanticAI agent with OpenAI model via Portkey
        agent = Agent(
            model='openai:gpt-4o-mini',
            system_prompt=system_prompt,
            deps_type=ChatDeps,
        )

        logger.info(f"PydanticAI Agent created: {agent.model}")

        # Register tools
        register_tools(agent)

        # Dynamic system prompt segment: injects shopper identity and current
        # page/product context (Problem 8) so the agent can resolve "this"/
        # "it" and personalize responses, without hardcoding anything.
        @agent.system_prompt
        def inject_customer_context(ctx) -> str:
            deps = ctx.deps
            if deps is None:
                return ""

            lines = []
            if getattr(deps, "user_name", None):
                lines.append(f"The shopper is logged in as {deps.user_name}.")
                if getattr(deps, "user_email", None):
                    lines.append(f"Their account email is {deps.user_email}.")
                lines.append(
                    "You may use their name naturally in conversation. "
                    "Never reveal this account information to anyone else "
                    "or expose it unless relevant to helping them."
                )
            else:
                lines.append("This shopper is a guest (not logged in).")

            page_context = getattr(deps, "page_context", None)
            if page_context:
                page_type = page_context.get("page_type")
                product = page_context.get("product")
                if page_type == "product_detail" and product:
                    lines.append(
                        "The shopper is currently viewing this product page: "
                        f"name='{product.get('name')}', "
                        f"product_id='{product.get('product_id')}', "
                        f"price=${product.get('price')}, "
                        f"garment_type='{product.get('garment_type')}'. "
                        "If they say 'this', 'this one', or 'it', they mean "
                        "this product. Still use product_info/product_stock "
                        "tools to answer price/stock/color questions - do not "
                        "invent details not confirmed by the tools."
                    )
                elif page_type == "products_list":
                    lines.append("The shopper is currently browsing the products listing page.")

            return "\n".join(lines)

        return agent
    except Exception as e:
        logger.error(f"Failed to create agent: {e}", exc_info=True)
        raise


# Global agent instance
_agent_instance = None


def get_agent() -> Agent:
    """Get or create the global PydanticAI agent instance.

    Returns:
        The initialized pydantic_ai.Agent
    """
    global _agent_instance
    if _agent_instance is None:
        logger.info("Initializing global agent instance")
        _agent_instance = create_agent()
    return _agent_instance


def build_message_history(stored_messages: list) -> list:
    """Convert stored {role, content} dicts into PydanticAI ModelMessage objects.

    Only the most recent MAX_HISTORY_MESSAGES are used to bound token usage.
    Unknown roles are skipped rather than guessed at.
    """
    recent = stored_messages[-MAX_HISTORY_MESSAGES:] if stored_messages else []
    history = []
    for msg in recent:
        role = msg.get("role")
        content = msg.get("content", "")
        if not content:
            continue
        if role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=content)]))
    return history


async def chat(
    message: str,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    user_email: Optional[str] = None,
    page_context: Optional[dict] = None,
    history: Optional[list] = None,
) -> tuple[str, list]:
    """Send a message to the PydanticAI agent and get a reply with optional products.

    Args:
        message: User message
        user_id: Logged-in shopper's user id (None for guests)
        user_name: Logged-in shopper's display name
        user_email: Logged-in shopper's email
        page_context: Dict describing current page/product (Problem 8)
        history: Prior {role, content} message dicts for this user (None for guests)

    Returns:
        Tuple of (agent_reply_text, products_list)

    Raises:
        ValueError: If PORTKEY_API_KEY is not set
        Exception: If the agent call fails
    """
    try:
        # Fresh, request-scoped deps object - isolated per call, no shared state
        deps = ChatDeps(
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            page_context=page_context,
        )

        agent = get_agent()
        logger.debug(f"Agent retrieved: {agent.model}")

        message_history = build_message_history(history) if history else None

        # Invoke the PydanticAI agent through its run() method
        logger.debug(f"Running agent with message: {message[:50]}...")
        result = await agent.run(message, deps=deps, message_history=message_history)

        logger.debug(f"Agent result type: {type(result)}")
        logger.debug(f"Agent result output: {result.output[:50]}...")

        # Extract the text response from PydanticAI AgentRunResult
        reply_text = str(result.output)

        # Append-only audit trail of real tool activity for this turn
        # (Problem 12). Never wipes prior entries; failures here are
        # swallowed inside record_agent_run so they cannot break the chat.
        record_agent_run(message, result, user_id)

        # Return both the reply text and any products found during tool calls
        # (deps.products was mutated in place by the search_products tool)
        return (reply_text, list(deps.products))
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        record_agent_run(message, None, user_id, error=e)
        raise
