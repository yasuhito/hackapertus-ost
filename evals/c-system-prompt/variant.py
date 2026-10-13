"""Strict, hash-pinned source-only experimental archive overlay."""
import hashlib
import json
from pathlib import Path
import subprocess

NAME = 'evidence-only-child'
ROOT = Path(__file__).parent / 'variants'
ROLE_FILES = {'track_2a/dev/format/' + x for x in
              ('submit-extension.ts', 'package-child.mjs', 'sdk.ts', 'run_comparison.py')}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def specification():
    spec = json.loads((ROOT / (NAME + '.json')).read_text())
    patch = (ROOT / (NAME + '.patch')).read_bytes()
    changed = {line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/')}
    if changed != ROLE_FILES or set(spec['role_hashes']) != ROLE_FILES or set(spec['base_role_hashes']) != ROLE_FILES:
        raise ValueError('VARIANT_ROLE_FILE_SCOPE_CHANGED')
    if digest(patch) != spec['patch_sha256']:
        raise ValueError('VARIANT_PATCH_FINGERPRINT_CHANGED')
    return spec, patch

def apply(workspace):
    spec, patch = specification()
    for path, sha in spec['base_role_hashes'].items():
        if digest((workspace / path).read_bytes()) != sha:
            raise ValueError('VARIANT_BASE_SOURCE_CHANGED: ' + path)
    subprocess.run(['git', 'apply', '--check', '-'], input=patch, cwd=workspace, check=True)
    subprocess.run(['git', 'apply', '-'], input=patch, cwd=workspace, check=True)
    for path, sha in spec['source_hashes'].items():
        if digest((workspace / path).read_bytes()) != sha:
            raise ValueError('VARIANT_SOURCE_CHANGED: ' + path)
    return spec

def verify_manifest(manifest):
    spec, _ = specification()
    if manifest.get('variant') != NAME or manifest.get('variant_patch_sha256') != spec['patch_sha256']:
        raise ValueError('VARIANT_MARKER_OR_FINGERPRINT_CHANGED')
    mapped = {k[k.index('track_2a/'):]: v for k, v in manifest['sources'].items()}
    if mapped != spec['source_hashes']:
        raise ValueError('VARIANT_EXACT_SOURCE_HASHES_CHANGED')
    policy = {k: v for k, v in manifest.items() if k not in ('sources', 'frozen', 'variant', 'variant_patch_sha256')}
    if policy != spec['policy']:
        raise ValueError('VARIANT_FIXED_POLICY_CHANGED')
    hashes = []
    for item in manifest['frozen']:
        item = json.loads(json.dumps(item))
        if 'booklet' in item['case']:
            item['case']['booklet']['path'] = Path(item['case']['booklet']['path']).name
        hashes.append(digest(json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()))
    if hashes != spec['frozen_hashes']:
        raise ValueError('VARIANT_FROZEN_SOURCE_OR_PARENT_SCHEMA_CHANGED')

def verify_baseline(manifest, allow_cli):
    spec, _ = specification()
    mapped = {k[k.index('track_2a/'):]: v for k, v in manifest['sources'].items()}
    current = {**spec['source_hashes'], **spec['base_role_hashes']}
    if mapped == current:
        return []
    if mapped not in spec['historical_baseline_source_maps']:
        raise ValueError('VARIANT_BASE_EXACT_SOURCE_HASHES_CHANGED')
    changed = sorted(k for k in set(current) | set(mapped) if current.get(k) != mapped.get(k))
    approved = {'track_2a/dev/format/run_comparison.py', 'track_2a/dev/format/test_cli_paths.py'}
    if set(changed) != approved:
        raise ValueError('VARIANT_HISTORICAL_NON_CLI_CHANGE')
    if not allow_cli:
        raise ValueError('VARIANT_HISTORICAL_REQUIRES_CLI_FLAG')
    return {k: {'current_base': current.get(k), 'historical': mapped.get(k)} for k in changed}


def child_emissions(response):
    """Finite lexical audit of untouched output, including rejected repairs."""
    import re
    fields = texts = values = content_violations = unauthorized = malformed = 0
    classes = r'\b(?:entailment|neutral|contradiction|entailed|contradicted)\b'
    def class_values(obj):
        if isinstance(obj, dict):
            return sum(class_values(v) for k, v in obj.items() if k != 'candidate_ids')
        if isinstance(obj, list):
            return sum(class_values(v) for v in obj)
        return len(re.findall(classes, obj, re.I)) if isinstance(obj, str) else 0
    for choice in (response or {}).get('choices', []):
        message = choice.get('message', {})
        # Only fields actually emitted in the saved response; never request reasoning.
        for field in ('content', 'reasoning', 'reasoning_content'):
            content = message.get(field)
            if content:
                content_violations += 1
                texts += len(re.findall(r'\b(?:label|recommended[_ ]label|entailment|neutral|contradiction|entailed|contradicted)\b', str(content), re.I))
        for call in message.get('tool_calls', []):
            raw = call.get('function', {}).get('arguments', '')
            found = 0
            def pairs(items):
                nonlocal found
                found += sum('label' in k.casefold() for k, _ in items)
                return dict(items)
            try:
                obj = json.loads(raw, object_pairs_hook=pairs)
                fields += found
                values += class_values(obj)
                if isinstance(obj, dict):
                    unauthorized += sum(k != 'candidate_ids' for k in obj)
                else:
                    malformed += 1
            except (ValueError, TypeError):
                malformed += 1
                fields += len(re.findall(r'"[^"\n]*label[^"\n]*"\s*:', str(raw), re.I))
                # Exclude candidate_ids arrays from lexical fallback, too.
                rest = re.sub(r'"candidate_ids"\s*:\s*\[[^\]]*\]', '', str(raw))
                values += len(re.findall(classes, rest, re.I))
    return {'child_label_fields': fields, 'child_label_text_emissions': texts,
            'child_label_value_emissions': values, 'child_label_emissions': fields + texts + values,
            'child_output_content_violations': content_violations,
            'child_output_unauthorized_fields': unauthorized, 'child_output_malformed_arguments': malformed,
            'child_output_contract_violations': content_violations + unauthorized + malformed}
