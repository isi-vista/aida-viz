from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import nltk
from immutablecollections import ImmutableDict, immutabledict
from vistautils.span import Span

from aida_viz.elements import Justification


def get_sentence_spans(document_text: str) -> List[Span]:
    tokenizer = nltk.tokenize.punkt.PunktSentenceTokenizer()

    return [
        Span(*s)
        for s in tokenizer.span_tokenize(document_text, realign_boundaries=True)
    ]


def get_title_sentence(document_text: str) -> Optional[str]:
    sentence_spans = get_sentence_spans(document_text)

    if sentence_spans:
        first_span = sentence_spans[0]
        first_sentence = document_text[first_span.start : first_span.end].split("\n\n")[
            0
        ]

        if len(first_sentence) > 100:
            first_sentence = first_sentence[0:100] + "..."

        return first_sentence

    return None


def contexts_from_justifications(
    justifications: ImmutableDict[str, Span], document
) -> ImmutableDict[str, Span]:
    document_text = document["fulltext"]
    sentence_spans = get_sentence_spans(document_text)
    contexts: Dict[str, Span] = {}

    for justification_id, justification_span in justifications.items():
        for s_span in sentence_spans:
            if s_span.contains_span(justification_span):
                # the sentence tokenizer doesn't recognize double newline as a potential sentence boundary,
                # so we split on double newlines and return the parts of the pre/post context
                # that are closest to the mention
                precontext_lines = document_text[
                    s_span.start : justification_span.start
                ].split("\n\n")
                precontext_extra = (
                    "\n\n".join(precontext_lines[:-1])
                    if len(precontext_lines) > 1
                    else ""
                )

                postcontext_lines = document_text[
                    justification_span.end : s_span.end
                ].split("\n\n")
                postcontext_extra = (
                    "\n\n".join(postcontext_lines[1:])
                    if len(postcontext_lines) > 1
                    else ""
                )

                modified_sentence_start = s_span.start + len(precontext_extra)
                modified_sentence_end = s_span.end - len(postcontext_extra)

                assert (
                    justification_id not in contexts
                ), "justification should not be overlapping with more than one sentence"
                contexts[justification_id] = Span(
                    modified_sentence_start, modified_sentence_end
                )

    return immutabledict(contexts)


def render_document(
    document_text: str,
    justification_spans: ImmutableDict[str, Span] = immutabledict(),
    context_spans: ImmutableDict[str, Span] = immutabledict(),
    include_class: bool = True,
) -> Tuple[str, ImmutableDict[str, str]]:
    context_starts: Dict[int, List[str]] = defaultdict(list)
    context_ends: Dict[int, List[str]] = defaultdict(list)
    mention_starts: Dict[int, List[str]] = defaultdict(list)
    mention_ends: Dict[int, List[str]] = defaultdict(list)

    for justification_id, span in sorted(
        justification_spans.items(), key=lambda item: item[1]
    ):
        mention_starts[span.start].append(justification_id)
        mention_ends[span.end].append(justification_id)

    for context_id, span in sorted(context_spans.items(), key=lambda item: item[1]):
        context_starts[span.start].append(context_id)
        context_ends[span.end].append(context_id)

    # NOTE: this technique fails when spans partially overlap. full overlap is ok.
    #       e.g. "this is" (0, 7) and "is a" (5, 9) will result in:
    #       <s>this <s>is</s> a</s> test

    rendered_justifications: Dict = defaultdict(list)
    tokens_to_render = ""
    position_stack = []

    for cursor, current_char in enumerate(document_text):
        for context_id in context_starts.get(cursor, []):
            position_stack.append((len(tokens_to_render), context_id))

            tokens_to_render += f'<span id="c-{context_id}"'
            if include_class:
                tokens_to_render += 'class="mention-context"'
            tokens_to_render += ">"

        for mention_id in mention_starts.get(cursor, []):
            position_stack.append((len(tokens_to_render), mention_id))

            tokens_to_render += f'<span id="m-{mention_id}"'
            if include_class:
                tokens_to_render += 'class="mention"'
            tokens_to_render += ">"

        for mention_id in mention_ends.get(cursor, []):
            start, mention_id = position_stack.pop()

            tokens_to_render += "</span>"
            rendered_justifications[mention_id] = tokens_to_render[start:]

        for context_id in context_ends.get(cursor, []):
            start, context_id = position_stack.pop()

            tokens_to_render += "</span>"
            rendered_justifications[context_id] = tokens_to_render[start:]

        tokens_to_render += current_char

    # This fixes a document scrolling issue.
    # The above code cannot just add mentionof- or contextof- to both tokens_to_render and rendered_justifications
    # because this will cause two IDs to collide. Therefore, we must add it in after the fact to
    # only the whole document render so the view will be properly scrolled.
    tokens_to_render = tokens_to_render.replace('id="c-', 'id="contextof-')
    tokens_to_render = tokens_to_render.replace('id="m-', 'id="mentionof-')

    return (
        tokens_to_render,
        immutabledict(
            {
                id: "".join(tokens_to_render)
                for id, tokens_to_render in rendered_justifications.items()
            }
        ),
    )


def render_single_justification_document(
    document: dict, justification: Justification
) -> str:

    span_start = justification.span_start
    span_end = justification.span_end

    if not span_start or not span_end:
        raise ValueError(
            "Justification to render must have values for span_start and span_end."
        )

    justification_spans: ImmutableDict[str, Span] = immutabledict(
        {f"{span_start}:{span_end}": Span(span_start, span_end + 1)}
    )

    contexts = contexts_from_justifications(justification_spans, document)

    to_render, _ = render_document(document["fulltext"], justification_spans, contexts)
    if not to_render:
        raise ValueError("Could not find anything to render.")

    return to_render
