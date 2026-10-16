"""Frozen-context contradiction recheck shared by runtime and offline bundles."""
RECHECK_INSTRUCTION = 'Contradiction check. A first reading found no decisive information. Re-read the supplied spans for a statement about the SAME matter as the claim (same proposal, actor, event, number, date or condition) whose content differs from the claim: a different number, date, actor, direction (accept versus reject), obligation, or an explicit negation. If such a statement exists, submit label 2 and cite the span IDs that state it. If every relevant detail is simply absent, submit label 1 with no IDs. Do not infer from silence.'


def recheck_item(item, legacy):
    messages = [dict(message) for message in item['messages']]
    messages[0]['content'] += '\n\n' + RECHECK_INSTRUCTION
    return {**item, 'messages': messages,
            'messages_sha256': legacy.digest(legacy.encode(messages))}
