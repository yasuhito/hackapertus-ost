"""Offline v16 bundle validation and source-copy-only task routing."""
import ast
import json

SYSTEM_HASHES = {
    'A': 'b2027887d2c9de4507d2ee8b2cb231cae3d4b63a6b55e353bfe3fcef80d9f6c3',
    'B': '06c89db1756d54d04cc5f1650b855acda2e2986d4c0c84943d2e54866383313c',
}
SOURCE_ARTIFACTS = {
    'A': 'output/cscs/candidate-archive/v15/v15-system.txt',
    'B': 'evals/c-system-prompt/prompts/v5-system.txt',
}
# Pinned as part of this file's protocol hash. No model receives the bundle.
WRAPPER = '''
_SYSTEM_BY_TASK = json.loads(SYSTEM)
_route_original_messages_for_pages = messages_for_pages
def messages_for_pages(case, pages):
    if ("booklet" in case) == ("reference" in case):
        raise ValueError("ROUTE_INPUT_TYPE_REQUIRED")
    messages = _route_original_messages_for_pages(case, pages)
    task = json.loads(messages[1]["content"])["task"]
    if task not in _SYSTEM_BY_TASK or task != ("A" if "booklet" in case else "B"):
        raise ValueError("ROUTE_TASK_MISMATCH")
    messages[0] = {**messages[0], "content": _SYSTEM_BY_TASK[task]}
    return messages

'''


def bundle(raw, root, digest):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('DUPLICATE_ROUTE_KEY')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    if type(value) is not dict or set(value) != {'A', 'B'}:
        raise ValueError('INVALID_ROUTE_BUNDLE')
    for task, relative in SOURCE_ARTIFACTS.items():
        original = (root / relative).read_bytes()
        if (type(value[task]) is not str or value[task].encode('utf-8') != original
                or digest(original) != SYSTEM_HASHES[task]):
            raise ValueError('ROUTE_SYSTEM_BYTES_CHANGED: ' + task)
    return value


def candidate_source(text, candidate, old):
    tree = ast.parse(text)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'messages_for_pages']
    entries = [n for n in tree.body if isinstance(n, ast.If)
               and ast.dump(n.test) == ast.dump(ast.parse('__name__ == "__main__"', mode='eval').body)]
    if len(functions) != 1 or len(entries) != 1 or functions[0].end_lineno >= entries[0].lineno:
        raise ValueError('ROUTE_SOURCE_BOUNDARY_CHANGED')
    if '_route_original_messages_for_pages' in text or '_SYSTEM_BY_TASK' in text:
        raise ValueError('ROUTE_ALREADY_INSTALLED')
    source = old.candidate_source(text, candidate)
    entry = next(n for n in ast.parse(source).body if isinstance(n, ast.If)
                 and ast.dump(n.test) == ast.dump(entries[0].test))
    lines = source.splitlines(keepends=True)
    lines.insert(entry.lineno - 1, WRAPPER)
    return ''.join(lines)


def chosen_system(candidate, case, messages):
    if ('booklet' in case) == ('reference' in case):
        raise ValueError('ROUTE_INPUT_TYPE_REQUIRED')
    task = 'A' if 'booklet' in case else 'B'
    if json.loads(messages[1]['content'])['task'] != task:
        raise ValueError('ROUTE_TASK_MISMATCH')
    return json.loads(candidate)[task]
