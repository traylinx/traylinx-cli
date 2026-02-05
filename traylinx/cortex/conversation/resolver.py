"""Reference resolver for multi-turn conversations.

Resolves pronouns and contextual references from conversation history:
- "it" / "that" → last mentioned entity
- "the first one" → first item from previous list
- "same agent" → previously referenced agent name
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolvedReference:
    """Result of resolving a reference."""

    original: str
    resolved: str
    reference_type: str  # "pronoun", "ordinal", "contextual"
    confidence: float


@dataclass
class EntityMention:
    """An entity mentioned in conversation."""

    entity_type: str  # "agent", "command", "file", "capability"
    value: str
    timestamp: float
    context: str = ""  # Surrounding context


class ReferenceResolver:
    """Resolves references to previously mentioned entities.

    Tracks mentioned entities and resolves pronouns/references:
    - "it", "that", "this" → Most recent entity
    - "run it", "stop that" → Most recent agent
    - "the first one", "second" → Ordinal references to lists
    - "same agent", "that capability" → Type-specific references
    """

    # Pronouns that refer to entities
    PRONOUNS = {"it", "that", "this", "them", "those"}

    # Ordinal patterns
    ORDINALS = {
        "first": 0,
        "second": 1,
        "third": 2,
        "fourth": 3,
        "fifth": 4,
        "last": -1,
        "1st": 0,
        "2nd": 1,
        "3rd": 2,
        "4th": 3,
        "5th": 4,
    }

    # Pattern for ordinal references like "the first one"
    ORDINAL_PATTERN = re.compile(
        r"\bthe\s+(first|second|third|fourth|fifth|last|1st|2nd|3rd|4th|5th)\s*(one|agent|result)?\b",
        re.IGNORECASE,
    )

    # Pattern for type-specific references like "same agent"
    TYPE_REF_PATTERN = re.compile(
        r"\b(same|that|the)\s+(agent|command|capability|file)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        """Initialize resolver with empty entity history."""
        self._entities: list[EntityMention] = []
        self._last_list: list[str] = []  # Last displayed list (for ordinals)
        self._last_list_type: str = ""  # Type of items in last list

    def add_mention(
        self,
        entity_type: str,
        value: str,
        timestamp: float | None = None,
        context: str = "",
    ) -> None:
        """Record an entity mention.

        Args:
            entity_type: Type of entity (agent, command, etc.)
            value: Entity value
            timestamp: When mentioned (default: now)
            context: Surrounding text
        """
        import time

        self._entities.append(
            EntityMention(
                entity_type=entity_type,
                value=value,
                timestamp=timestamp or time.time(),
                context=context,
            )
        )

        # Keep history bounded
        if len(self._entities) > 100:
            self._entities = self._entities[-50:]

    def set_last_list(self, items: list[str], item_type: str) -> None:
        """Record a list of items shown to user.

        Args:
            items: List of items (for ordinal resolution)
            item_type: Type of items in list
        """
        self._last_list = items.copy()
        self._last_list_type = item_type

    def get_last_entity(self, entity_type: str | None = None) -> EntityMention | None:
        """Get the most recently mentioned entity.

        Args:
            entity_type: Filter by type (optional)

        Returns:
            Most recent entity or None
        """
        if not self._entities:
            return None

        if entity_type:
            for entity in reversed(self._entities):
                if entity.entity_type == entity_type:
                    return entity
            return None

        return self._entities[-1]

    def resolve(self, text: str) -> tuple[str, list[ResolvedReference]]:
        """Resolve all references in text.

        Args:
            text: User input with potential references

        Returns:
            Tuple of (resolved text, list of resolutions)
        """
        resolutions: list[ResolvedReference] = []
        resolved_text = text

        # 1. Resolve ordinal references ("the first one")
        resolved_text, ordinal_refs = self._resolve_ordinals(resolved_text)
        resolutions.extend(ordinal_refs)

        # 2. Resolve type-specific references ("same agent", "that command")
        resolved_text, type_refs = self._resolve_type_references(resolved_text)
        resolutions.extend(type_refs)

        # 3. Resolve pronouns ("it", "that")
        resolved_text, pronoun_refs = self._resolve_pronouns(resolved_text)
        resolutions.extend(pronoun_refs)

        return resolved_text, resolutions

    def _resolve_ordinals(self, text: str) -> tuple[str, list[ResolvedReference]]:
        """Resolve ordinal references like 'the first one'."""
        refs: list[ResolvedReference] = []

        def replace_ordinal(match: re.Match) -> str:
            ordinal_word = match.group(1).lower()
            idx = self.ORDINALS.get(ordinal_word, 0)

            if not self._last_list:
                return match.group(0)  # Can't resolve, keep original

            try:
                resolved = self._last_list[idx]
                refs.append(
                    ResolvedReference(
                        original=match.group(0),
                        resolved=resolved,
                        reference_type="ordinal",
                        confidence=0.9,
                    )
                )
                return resolved
            except IndexError:
                return match.group(0)

        resolved = self.ORDINAL_PATTERN.sub(replace_ordinal, text)
        return resolved, refs

    def _resolve_type_references(self, text: str) -> tuple[str, list[ResolvedReference]]:
        """Resolve type-specific references like 'same agent'."""
        refs: list[ResolvedReference] = []

        def replace_type_ref(match: re.Match) -> str:
            entity_type = match.group(2).lower()
            entity = self.get_last_entity(entity_type)

            if not entity:
                return match.group(0)

            refs.append(
                ResolvedReference(
                    original=match.group(0),
                    resolved=entity.value,
                    reference_type="contextual",
                    confidence=0.85,
                )
            )
            return entity.value

        resolved = self.TYPE_REF_PATTERN.sub(replace_type_ref, text)
        return resolved, refs

    def _resolve_pronouns(self, text: str) -> tuple[str, list[ResolvedReference]]:
        """Resolve pronoun references like 'it', 'that'."""
        refs: list[ResolvedReference] = []
        words = text.split()
        result_words = []

        for i, word in enumerate(words):
            word_lower = word.lower().strip(".,!?")

            # Check if this looks like a pronoun reference
            if word_lower in self.PRONOUNS:
                # Context-sensitive: "run it" → agent, "show it" → logs, etc.
                entity_type = self._infer_entity_type(words, i)
                entity = self.get_last_entity(entity_type)

                if entity:
                    refs.append(
                        ResolvedReference(
                            original=word,
                            resolved=entity.value,
                            reference_type="pronoun",
                            confidence=0.75,
                        )
                    )
                    # Preserve punctuation
                    suffix = word[len(word_lower):] if len(word) > len(word_lower) else ""
                    result_words.append(entity.value + suffix)
                    continue

            result_words.append(word)

        return " ".join(result_words), refs

    def _infer_entity_type(self, words: list[str], pronoun_idx: int) -> str | None:
        """Infer the type of entity a pronoun refers to.

        Args:
            words: Tokenized input
            pronoun_idx: Index of pronoun

        Returns:
            Inferred entity type or None
        """
        # Look at preceding verb to infer type
        command_mappings = {
            "run": "agent",
            "start": "agent",
            "stop": "agent",
            "kill": "agent",
            "logs": "agent",
            "call": "agent",
            "find": "capability",
            "search": "capability",
            "discover": "capability",
        }

        # Check word before pronoun
        if pronoun_idx > 0:
            prev_word = words[pronoun_idx - 1].lower().strip(".,!?")
            if prev_word in command_mappings:
                return command_mappings[prev_word]

        # Default: return most recent entity type
        last = self.get_last_entity()
        return last.entity_type if last else None

    def clear(self) -> None:
        """Clear all entity history."""
        self._entities.clear()
        self._last_list.clear()
        self._last_list_type = ""

    def extract_entities_from_text(self, text: str, intent_type: str | None = None) -> list[EntityMention]:
        """Extract entity mentions from text based on patterns.

        Args:
            text: Input text to scan
            intent_type: Optional intent type for context

        Returns:
            List of extracted entities
        """
        import time
        entities: list[EntityMention] = []
        now = time.time()

        # Pattern for agent names (word after "agent", dash-separated words)
        agent_pattern = re.compile(r'\b(?:agent\s+)?([a-z][a-z0-9-]+(?:/[a-z0-9-]+)?)\b', re.IGNORECASE)

        # If intent is about agents, try to extract agent names
        if intent_type in ("run", "stop", "logs", "call"):
            for match in agent_pattern.finditer(text):
                candidate = match.group(1)
                # Filter out common words
                if candidate.lower() not in ("the", "a", "an", "my", "your", "agent", "agents"):
                    entities.append(
                        EntityMention(
                            entity_type="agent",
                            value=candidate,
                            timestamp=now,
                            context=text,
                        )
                    )

        return entities
