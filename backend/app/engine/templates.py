"""Drain-inspired log template miner (implemented from scratch).

The classic Drain algorithm groups logs with a fixed-depth parse tree:

    root
      └─ length layer          (branch on token count)
           └─ prefix layers    (branch on the first `max_depth` tokens)
                └─ leaf         (a small list of candidate templates)

At the leaf we compare the incoming token sequence against each candidate
template by similarity. If the best match clears `sim_threshold`, we merge into
it (diverging positions collapse to the "<*>" wildcard); otherwise we create a
new template. This keeps matching close to O(depth) per line instead of the
O(n^2) of naive pairwise comparison.

We add one enhancement over textbook Drain: messages are pre-masked by
`normalize` (numbers, ids, ips, ... -> typed sentinels) before mining, which
makes the resulting templates cleaner and the tree shallower.
"""

from __future__ import annotations

from typing import Optional

from .normalize import masked_tokens
from .types import LEVEL_RANK, ParsedEvent, Template

WILDCARD = "<*>"


def _token_key(token: str) -> str:
    """Key used for tree navigation.

    Typed sentinels (``<NUM>``, ``<IP>`` ...) keep their identity so different
    variable *types* branch apart, but any residual token that still carries a
    digit is treated as a wildcard to avoid tree explosion.
    """
    if token.startswith("<") and token.endswith(">"):
        return token
    if any(ch.isdigit() for ch in token):
        return WILDCARD
    return token


class _Node:
    __slots__ = ("children", "groups")

    def __init__(self) -> None:
        self.children: dict[str, "_Node"] = {}
        self.groups: list[int] = []  # template indices, populated only at leaves


class TemplateMiner:
    def __init__(
        self,
        max_depth: int = 4,
        sim_threshold: float = 0.5,
        max_children: int = 100,
    ) -> None:
        self.max_depth = max(2, max_depth)
        self.sim_threshold = sim_threshold
        self.max_children = max_children
        self._length_layer: dict[int, _Node] = {}
        self.templates: list[Template] = []
        self._seq = 0

    # ---- public API -----------------------------------------------------

    def add_event(self, event: ParsedEvent) -> Template:
        tokens = masked_tokens(event.message) or ["<empty>"]
        template = self._match_or_create(tokens)
        self._update_template(template, event, tokens)
        return template

    def add_events(self, events: list[ParsedEvent]) -> None:
        for event in events:
            self.add_event(event)

    # ---- tree + matching ------------------------------------------------

    def _leaf_groups(self, tokens: list[str], create: bool) -> Optional[list[int]]:
        n = len(tokens)
        node = self._length_layer.get(n)
        if node is None:
            if not create:
                return None
            node = _Node()
            self._length_layer[n] = node

        depth = min(self.max_depth, n)
        for i in range(depth):
            key = _token_key(tokens[i])
            child = node.children.get(key)
            if child is None:
                if create:
                    if len(node.children) >= self.max_children:
                        child = node.children.setdefault(WILDCARD, _Node())
                    else:
                        child = node.children.setdefault(key, _Node())
                else:
                    child = node.children.get(WILDCARD)
                    if child is None:
                        return None
            node = child
        return node.groups

    def _match_or_create(self, tokens: list[str]) -> Template:
        groups = self._leaf_groups(tokens, create=True)
        assert groups is not None

        best_idx = -1
        best_sim = -1.0
        for idx in groups:
            cand = self.templates[idx]
            if cand.token_count != len(tokens):
                continue
            sim = self._similarity(cand.tokens, tokens)
            if sim > best_sim:
                best_sim = sim
                best_idx = idx

        if best_idx >= 0 and best_sim >= self.sim_threshold:
            template = self.templates[best_idx]
            merged = self._merge(template.tokens, tokens)
            template.tokens = merged
            return template

        return self._create_template(tokens, groups)

    @staticmethod
    def _similarity(template_tokens: list[str], tokens: list[str]) -> float:
        """Fraction of positions that agree; existing wildcards auto-agree."""
        if not tokens:
            return 1.0
        matches = 0
        for t, s in zip(template_tokens, tokens):
            if t == WILDCARD or t == s:
                matches += 1
        return matches / len(tokens)

    @staticmethod
    def _merge(template_tokens: list[str], tokens: list[str]) -> list[str]:
        return [t if t == s else WILDCARD for t, s in zip(template_tokens, tokens)]

    def _create_template(self, tokens: list[str], groups: list[int]) -> Template:
        self._seq += 1
        template = Template(
            template_id=f"CLU-{self._seq:03d}",
            tokens=list(tokens),
            token_count=len(tokens),
            level="UNKNOWN",
        )
        groups.append(len(self.templates))
        self.templates.append(template)
        return template

    @staticmethod
    def _update_template(template: Template, event: ParsedEvent, tokens: list[str]) -> None:
        template.count += 1
        if template.count == 1 or not template.example:
            template.example = event.message
        if len(template.examples) < 8:
            template.examples.append(event.raw)
        # keep the most severe level seen for this template
        if LEVEL_RANK.get(event.level, 1) > LEVEL_RANK.get(template.level, -1):
            template.level = event.level
        if template.first_seen is None or event.ts < template.first_seen:
            template.first_seen = event.ts
        if template.last_seen is None or event.ts > template.last_seen:
            template.last_seen = event.ts
        if event.service:
            template.services[event.service] = template.services.get(event.service, 0) + 1

    # ---- results --------------------------------------------------------

    def get_templates(self) -> list[Template]:
        """Templates sorted by volume (most frequent first)."""
        return sorted(self.templates, key=lambda t: t.count, reverse=True)
