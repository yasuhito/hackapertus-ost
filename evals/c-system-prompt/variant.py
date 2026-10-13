"""Strict, hash-pinned source-only experimental archive overlay."""
import hashlib
import json
from pathlib import Path
import subprocess

NAME = 'evidence-only-child'
NAMES = (NAME, 'id-existence-check')
ROOT = Path(__file__).parent / 'variants'
ROLE_FILES = {'track_2a/dev/format/' + x for x in
              ('submit-extension.ts', 'package-child.mjs', 'sdk.ts', 'run_comparison.py')}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def specification(name=NAME):
    if name not in NAMES:
        raise ValueError('UNKNOWN_VARIANT')
    spec = json.loads((ROOT / (name + '.json')).read_text())
    patch = (ROOT / (name + '.patch')).read_bytes()
    changed = {line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/')}
    scope = ROLE_FILES if name == NAME else ROLE_FILES - {'track_2a/dev/format/package-child.mjs'}
    if changed != scope or set(spec['role_hashes']) != scope or set(spec['base_role_hashes']) != scope:
        raise ValueError('VARIANT_ROLE_FILE_SCOPE_CHANGED')
    if digest(patch) != spec['patch_sha256']:
        raise ValueError('VARIANT_PATCH_FINGERPRINT_CHANGED')
    return spec, patch

def apply(workspace, name=NAME):
    spec, patch = specification(name)
    for path, sha in spec['base_role_hashes'].items():
        if digest((workspace / path).read_bytes()) != sha:
            raise ValueError('VARIANT_BASE_SOURCE_CHANGED: ' + path)
    subprocess.run(['git', 'apply', '--check', '-'], input=patch, cwd=workspace, check=True)
    subprocess.run(['git', 'apply', '-'], input=patch, cwd=workspace, check=True)
    for path, sha in spec['source_hashes'].items():
        if digest((workspace / path).read_bytes()) != sha:
            raise ValueError('VARIANT_SOURCE_CHANGED: ' + path)
    return spec

def verify_manifest(manifest, name=NAME):
    spec, _ = specification(name)
    if manifest.get('variant') != name or manifest.get('variant_patch_sha256') != spec['patch_sha256']:
        raise ValueError('VARIANT_MARKER_OR_FINGERPRINT_CHANGED')
    mapped = {k[k.index('track_2a/'):]: v for k, v in manifest['sources'].items()}
    if mapped != spec['source_hashes']:
        raise ValueError('VARIANT_EXACT_SOURCE_HASHES_CHANGED')
    policy = {k: v for k, v in manifest.items() if k not in ('sources', 'frozen', 'variant', 'variant_patch_sha256')}
    if policy != spec['policy']:
        raise ValueError('VARIANT_FIXED_POLICY_CHANGED')
    verify_policy_frozen(manifest, spec)
    if name == 'id-existence-check':
        verify_schema_delta(manifest, spec)


def verify_schema_delta(manifest, spec):
    base = json.loads(json.dumps(manifest))
    if len(spec['schema_audit']) != len(base['frozen']):
        raise ValueError('VARIANT_SCHEMA_AUDIT_CHANGED')
    for item, audit in zip(base['frozen'], spec['schema_audit']):
        if item['schema_sha256'] != audit['parent_schema_sha256']:
            raise ValueError('VARIANT_DECLARED_PARENT_SCHEMA_CHANGED')
        item['schema_sha256'] = audit['base_parent_schema_sha256']
    # The only frozen delta is the exact approved parent tool declaration.
    # Source hashes and focused schema tests independently pin submit and child.
    if frozen_hashes(base) != spec['base_frozen_hashes']:
        raise ValueError('VARIANT_UNAPPROVED_FROZEN_DELTA')


def frozen_hashes(manifest):
    hashes = []
    for item in manifest['frozen']:
        item = json.loads(json.dumps(item))
        if 'booklet' in item['case']:
            item['case']['booklet']['path'] = Path(item['case']['booklet']['path']).name
        hashes.append(digest(json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()))
    return hashes


def verify_policy_frozen(manifest, spec, baseline=False):
    policy = {k: v for k, v in manifest.items() if k not in ('sources', 'frozen', 'variant', 'variant_patch_sha256')}
    if policy != spec['policy']:
        raise ValueError('VARIANT_FIXED_POLICY_CHANGED')
    expected = spec['base_frozen_hashes'] if baseline else spec['frozen_hashes']
    if frozen_hashes(manifest) != expected:
        raise ValueError('VARIANT_FROZEN_SOURCE_OR_PARENT_SCHEMA_CHANGED')


def verify_baseline(manifest, allow_cli, name=NAME):
    spec, _ = specification(name)
    if name == 'id-existence-check':
        verify_policy_frozen(manifest, spec, baseline=True)
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
