"""SwitchAI client using OpenAI SDK.

Connects to switchAILocal (http://localhost:18080/v1) using the OpenAI SDK.
Provides methods for chat, intent classification, and health checks.
"""

import json
from typing import Any, Iterator

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from traylinx.cortex.types import Intent, IntentType, ConfirmationLevel
from traylinx.cortex.config import load_config
from traylinx.cortex.workspace import load_persona


# System prompt for intent classification
INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for Traylinx CLI.

Available commands:
- run: Start an agent (aliases: start, launch)
- stop: Stop an agent (aliases: kill, halt)
- logs: View agent logs (aliases: tail, show logs)
- status: Check agent status
- discover: Find agents on P2P network (aliases: search, find agents)
- call: Execute A2A call to another agent
- whoami: Show authentication status
- login: Sign in to Sentinel
- logout: Sign out
- build: Build agent
- validate: Validate agent config
- publish: Publish agent to registry

Analyze the user input and respond with JSON only:
{
  "type": "cli_command" | "information_request" | "conversation",
  "command": "run" | "stop" | "logs" | ... | null,
  "parameters": {...},
  "confidence": 0.0-1.0,
  "requires_confirmation": true | false
}

Do NOT include any text outside the JSON object."""


class SwitchAIClient:
    """Client for switchAILocal using OpenAI SDK.

    Connects to the local LLM gateway at http://localhost:18080/v1.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ):
        """Initialize client.

        Args:
            base_url: SwitchAI base URL (default from config)
            api_key: API key (default from config)
            timeout: Request timeout in seconds
        """
        config = load_config()
        self.base_url = base_url or config.switchai.base_url
        self.api_key = api_key or config.switchai.api_key
        self.timeout = timeout or config.switchai.timeout
        self.default_model = config.switchai.default_model

        self._client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=float(self.timeout),
        )

    def health_check(self) -> bool:
        """Check if switchAILocal is available.

        Returns:
            True if service is healthy
        """
        try:
            # Try to list models as a health check
            self._client.models.list()
            return True
        except Exception:
            return False

    def chat(
        self,
        messages: list[ChatCompletionMessageParam],
        model: str | None = None,
        stream: bool = False,
    ) -> str:
        """Send a chat completion request.

        Args:
            messages: List of chat messages
            model: Model to use (default: auto)
            stream: Whether to stream response

        Returns:
            Assistant's response content
        """
        model = model or self.default_model

        if stream:
            return self._stream_chat(messages, model)

        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
        )

        return response.choices[0].message.content or ""

    def _stream_chat(
        self,
        messages: list[ChatCompletionMessageParam],
        model: str,
    ) -> Iterator[str]:
        """Stream a chat completion response.

        Args:
            messages: List of chat messages
            model: Model to use

        Yields:
            Response content chunks
        """
        stream = self._client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def classify_intent(self, user_input: str, context: dict[str, Any] | None = None) -> Intent:
        """Classify user input using LLM.

        Args:
            user_input: Raw user input
            context: Optional context (recent commands, etc.)

        Returns:
            Classified Intent
        """
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT},
        ]

        # Add context if provided
        if context:
            context_str = f"Context: {json.dumps(context)}"
            messages.append({"role": "system", "content": context_str})

        messages.append({"role": "user", "content": user_input})

        try:
            response = self._client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                temperature=0.1,  # Low temperature for deterministic classification
            )

            content = response.choices[0].message.content or "{}"

            # Parse JSON response
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    # Fall back to conversation type
                    return Intent(
                        type=IntentType.CONVERSATION,
                        confidence=0.5,
                        raw_input=user_input,
                    )

            # Map to Intent
            intent_type = IntentType(data.get("type", "conversation"))
            requires_conf = data.get("requires_confirmation", False)
            conf_level = ConfirmationLevel.HARD if requires_conf else ConfirmationLevel.NONE

            return Intent(
                type=intent_type,
                command=data.get("command"),
                parameters=data.get("parameters", {}),
                confidence=data.get("confidence", 0.8),
                requires_confirmation=requires_conf,
                confirmation_level=conf_level,
                raw_input=user_input,
            )

        except Exception as e:
            # LLM classification failed
            return Intent(
                type=IntentType.AMBIGUOUS,
                confidence=0.3,
                raw_input=user_input,
            )

    def generate_response(
        self,
        user_input: str,
        conversation_history: list[ChatCompletionMessageParam] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a conversational response.

        Args:
            user_input: User's message
            conversation_history: Previous messages
            system_prompt: Custom system prompt (overrides PERSONA.md)

        Returns:
            Generated response
        """
        messages: list[ChatCompletionMessageParam] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            # Load persona from PERSONA.md
            persona = load_persona()
            messages.append({"role": "system", "content": persona})

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_input})

        return self.chat(messages)
