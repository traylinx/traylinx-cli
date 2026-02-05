"""REPL loop for Cortex chat interface.

The main Read-Eval-Print Loop that:
1. Reads user input
2. Resolves references from conversation history
3. Classifies intent
4. Handles clarifications if needed
5. Executes command or generates response
6. Displays result
7. Repeats
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from traylinx.cortex.types import Intent, IntentType, ExecutionResult, ExecutionStatus
from traylinx.cortex.intent.classifier import IntentClassifier
from traylinx.cortex.executor.executor import CommandExecutor
from traylinx.cortex.executor.formatters import display_result, ResultType
from traylinx.cortex.session import SessionManager
from traylinx.cortex.conversation import (
    ConversationState,
    ConversationPhase,
    ReferenceResolver,
    ClarificationGenerator,
)


console = Console()


class ChatREPL:
    """Interactive REPL for Cortex chat.

    Handles the main conversation loop, special commands,
    session management, and multi-turn conversations.
    """

    def __init__(self, use_llm: bool = True, session_id: str | None = None):
        """Initialize REPL.

        Args:
            use_llm: Whether to use LLM for classification/responses
            session_id: Optional session ID to resume
        """
        self.classifier = IntentClassifier(use_llm=use_llm)
        self.executor = CommandExecutor()
        self.session_manager = SessionManager()
        self.running = False
        self.history: list[str] = []

        # Multi-turn conversation support
        self.conversation_state = ConversationState()
        self.reference_resolver = ReferenceResolver()
        self.clarification_generator = ClarificationGenerator()

        # Start or resume session
        if session_id:
            from uuid import UUID
            self.session_manager.resume_session(UUID(session_id))
        else:
            self.session_manager.start_session()

    def display_banner(self) -> None:
        """Display welcome banner."""
        from traylinx.cortex import __version__

        banner = f"""[bold blue]🧠 Traylinx Cortex[/bold blue] v{__version__}
[dim]Type [cyan]/help[/cyan] for commands, [cyan]/exit[/cyan] to quit[/dim]"""

        console.print(
            Panel(
                banner,
                border_style="blue",
                padding=(0, 2),
            )
        )
        console.print()

    def run(self) -> None:
        """Run the REPL loop."""
        self.display_banner()
        self.running = True

        while self.running:
            try:
                # Read input
                user_input = Prompt.ask("[bold green]You[/bold green]")
                if not user_input.strip():
                    continue

                self.history.append(user_input)

                # Process input
                self.process_input(user_input)

            except KeyboardInterrupt:
                console.print("\n[dim]Use /exit to quit[/dim]")
            except EOFError:
                self.running = False

        console.print("\n[bold]👋 Goodbye![/bold]")

    def process_input(self, user_input: str) -> ExecutionResult | None:
        """Process a single user input.

        Args:
            user_input: User's input string

        Returns:
            ExecutionResult if a command was executed
        """
        # Record user message
        self.session_manager.add_user_message(user_input)

        # Handle clarification response if awaiting
        if self.conversation_state.is_awaiting_clarification():
            return self._handle_clarification_response(user_input)

        # Resolve references ("it", "that", "the first one")
        resolved_input, resolutions = self.reference_resolver.resolve(user_input)

        # Show resolution if any
        if resolutions:
            resolution_list = [f"'{r.original}' → '{r.resolved}'" for r in resolutions]
            console.print(f"[dim]Resolved: {', '.join(resolution_list)}[/dim]")

        # Set state to classifying
        self.conversation_state.start_classification()

        # Classify intent using resolved input
        intent = self.classifier.classify(resolved_input)

        # Check if clarification is needed
        if self.clarification_generator.needs_clarification(
            intent.command,
            intent.parameters,
            intent.confidence,
        ):
            context = self.session_manager.build_context()
            clarification = self.clarification_generator.generate(
                intent.command,
                intent.parameters,
                intent.confidence,
                context={
                    "running_agents": context.running_agents,
                    "recent_agents": self._get_recent_agents(),
                },
            )
            if clarification:
                self.conversation_state.request_clarification(
                    original_input=user_input,
                    question=clarification.question,
                    options=clarification.options,
                    context_key=clarification.context_key,
                    partial_intent={
                        "command": intent.command,
                        "parameters": intent.parameters,
                    },
                )
                self.clarification_generator.set_recent_suggestions(clarification.options)
                console.print(f"[yellow]❓ {clarification.question}[/yellow]")
                if clarification.options:
                    for i, opt in enumerate(clarification.options, 1):
                        console.print(f"   [cyan]{i}[/cyan]. {opt}")
                return None

        # Handle based on type
        if intent.type == IntentType.CLI_COMMAND:
            return self._handle_command(intent)
        elif intent.type == IntentType.CONVERSATION:
            return self._handle_conversation(intent)
        elif intent.type == IntentType.INFORMATION_REQUEST:
            return self._handle_info_request(intent)
        else:
            return self._handle_ambiguous(intent)

    def _handle_clarification_response(self, answer: str) -> ExecutionResult | None:
        """Handle response to a clarification question.

        Args:
            answer: User's answer

        Returns:
            ExecutionResult if command was executed
        """
        merged = self.conversation_state.receive_clarification(answer)

        if not merged:
            console.print("[dim]No pending clarification.[/dim]")
            return None

        # Merge clarification into parameters and re-classify
        command = merged.get("command")
        parameters = self.clarification_generator.merge_clarification(
            merged.get("parameters", {}),
            self.conversation_state.accumulated_context.get("_last_key", ""),
            answer,
        )

        # Create an intent with the merged parameters
        intent = Intent(
            type=IntentType.CLI_COMMAND,
            command=command,
            parameters=parameters,
            confidence=0.9,
            raw_input=answer,
        )

        # Record the entity for future reference
        if "agent_name" in parameters:
            self.reference_resolver.add_mention(
                "agent",
                parameters["agent_name"],
                context=f"clarification for {command}",
            )

        return self._handle_command(intent)

    def _get_recent_agents(self) -> list[str]:
        """Get recently mentioned agent names.

        Returns:
            List of agent names from history
        """
        agents = []
        for entity in self.reference_resolver._entities[:10]:
            if entity.entity_type == "agent" and entity.value not in agents:
                agents.append(entity.value)
        return agents

    def _handle_command(self, intent: Intent) -> ExecutionResult | None:
        """Handle CLI command intent."""
        # Check for special commands
        if intent.command == "exit":
            self.running = False
            return None
        elif intent.command == "help":
            self._show_help()
            return None
        elif intent.command == "clear":
            console.clear()
            return None
        elif intent.command == "history":
            self._show_history()
            return None

        # Track entity mentions for reference resolution
        if "agent_name" in intent.parameters:
            self.reference_resolver.add_mention(
                "agent",
                intent.parameters["agent_name"],
                context=f"executed {intent.command}",
            )

        # Update conversation state
        self.conversation_state.start_execution()

        # Execute CLI command
        result = self.executor.execute(intent)
        console.print(result.formatted_output)

        # Reset conversation state
        self.conversation_state.reset()

        # Record execution
        status = ExecutionStatus.SUCCESS if result.success else ExecutionStatus.ERROR
        self.session_manager.record_execution(
            command=result.command,
            status=status,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            parameters=intent.parameters,
        )

        # Record assistant response
        if result.success:
            self.session_manager.add_assistant_message(f"Executed: {result.command}")
        else:
            self.session_manager.add_assistant_message(
                f"Command failed: {result.command}\n{result.stderr or 'Unknown error'}"
            )

        return result

    def _handle_conversation(self, intent: Intent) -> None:
        """Handle conversational input.

        For now, just acknowledge. LLM integration will handle this properly.
        """
        console.print(
            "[dim]I understood that as conversation. "
            "Try a command like 'start my agent' or type /help.[/dim]"
        )

    def _handle_info_request(self, intent: Intent) -> None:
        """Handle information request."""
        console.print(
            "[dim]Looking for information... This feature requires LLM integration.[/dim]"
        )

    def _handle_ambiguous(self, intent: Intent) -> None:
        """Handle ambiguous input."""
        console.print(
            "[yellow]I'm not sure what you mean.[/yellow] "
            "Try being more specific, or type /help for available commands."
        )

    def _show_help(self) -> None:
        """Display help information."""
        help_text = """[bold]Available Commands:[/bold]

[cyan]Agent Lifecycle:[/cyan]
  start/run agent     Start your agent
  stop agent          Stop running agent
  show logs           View agent logs
  status              Check agent status

[cyan]Discovery & Networking:[/cyan]
  find agents         Discover agents on the network
  call <peer>         Call a specific agent

[cyan]Authentication:[/cyan]
  whoami              Show your identity
  login               Sign in to Sentinel
  logout              Sign out

[cyan]Build & Publish:[/cyan]
  build               Build your agent
  validate            Validate agent config
  publish             Publish to registry

[cyan]Special Commands:[/cyan]
  /help               Show this help
  /history            Show command history
  /clear              Clear screen
  /exit               Exit chat

[dim]Examples:[/dim]
  "start my agent"
  "show me the logs"
  "find agents that can translate"
  "call my-peer with action ping"
"""
        console.print(Panel(help_text, title="[bold]Cortex Help[/bold]", border_style="blue"))

    def _show_history(self) -> None:
        """Display command history."""
        if not self.history:
            console.print("[dim]No history yet.[/dim]")
            return

        console.print("[bold]Command History:[/bold]")
        for i, cmd in enumerate(self.history[-20:], 1):
            console.print(f"  {i}. {cmd}")
