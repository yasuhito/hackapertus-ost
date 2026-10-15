#!/usr/bin/env python3
"""Offline, one-shot reporting of completed fictional captures. No inference mode."""
import argparse
import os
from pathlib import Path
import tempfile
import time

import provider_schema_probe as old

ROOT = old.ROOT
CONTROL = old.OUT / 'provider-schema-probe-v1-recovery-protocol.json'
JOB = old.OUT / 'provider-schema-probe-v1-recovery'
ARCHIVES = {str(ROOT / ('.auto/' + name + '.sh')):
            ROOT / ('.auto/protocol-archive/provider-probe-v1-' + name + '.sh')
            for name in ('measure', 'checks')}
SOURCES = [ROOT / ('.auto/' + name) for name in (
    'provider_schema_probe_recovery.py', 'test_provider_schema_probe_recovery.py',
    'provider-schema-probe-recovery.md', 'measure.sh', 'checks.sh')] + list(ARCHIVES.values())


def save(path, value, *, replace=False):
    """Fsync private bytes and directory; rename consumes the temporary name."""
    old.require(not path.is_symlink(), 'SYMLINK_REFUSED')
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(old.encode(value))
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(name, path)
        else:
            os.link(name, path)
            os.unlink(name)
        old.syncdir(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def digests(paths):
    result = {}
    for path in paths:
        old.require(path.is_file() and not path.is_symlink(), 'ARTIFACT_TYPE_CHANGED')
        result[str(path)] = old.sha(path.read_bytes())
    return result


def original():
    protocol = old.load(old.CONTROL)
    # Only the two additive dispatchers are relocated. Every other original pin
    # is checked at its original path, including model source and TypeBox runtime.
    for name, digest in protocol['sources'].items():
        path = ARCHIVES.get(name, Path(name))
        old.require(digests([path])[str(path)] == digest, 'ORIGINAL_SOURCE_CHANGED')
    expected = old.protocol()
    # Sources have just been checked individually against their frozen bytes.
    expected['sources'] = protocol['sources']
    old.require(protocol == expected, 'ORIGINAL_PROTOCOL_CHANGED')
    old.require(old.load(old.JOB / 'protocol.json') == protocol, 'JOB_PROTOCOL_CHANGED')
    return protocol


def protocol():
    original()
    return dict(version=1, mode='provider_schema_probe_recovered',
                original_control_sha256=old.sha(old.CONTROL.read_bytes()),
                original_completed_sha256=old.sha((old.JOB / 'completed.json').read_bytes()),
                original_artifacts=digests(sorted(old.JOB.iterdir())),
                sources=digests(SOURCES))


def verify():
    frozen = old.load(CONTROL)
    old.require(frozen == protocol(), 'RECOVERY_PROTOCOL_OR_SOURCE_CHANGED')
    return original()


def context():
    return dict(mode='provider_schema_probe_recovered', candidate='',
                protocol_sha256=old.sha(CONTROL.read_bytes()),
                report_sha256=old.sha((JOB / 'report.json').read_bytes()))


def execute_report():
    start = time.monotonic()
    frozen = verify()  # Both pinsets validated before calling the original checker.
    JOB.mkdir(mode=0o700)  # Exclusive permanent marker: no rereport or resume.
    old.syncdir(JOB.parent)
    result = old.check(frozen, old.JOB)
    report = dict(result=result, recovery_wall_seconds=time.monotonic() - start,
                  protocol_sha256=old.sha(CONTROL.read_bytes()))
    save(JOB / 'report.json', report)
    save(old.CONTEXT, context(), replace=True)
    return report


def check():
    frozen = verify()
    report = old.load(JOB / 'report.json')
    old.require(old.load(old.CONTEXT) == context(), 'RECOVERY_CONTEXT_CHANGED')
    old.require(report['protocol_sha256'] == old.sha(CONTROL.read_bytes()), 'REPORT_PROTOCOL_CHANGED')
    old.require(type(report['recovery_wall_seconds']) in (float, int) and
                0 <= report['recovery_wall_seconds'] < float('inf'), 'RECOVERY_WALL_INVALID')
    old.require(report['result'] == old.check(frozen, old.JOB), 'RECOVERY_RESULT_CHANGED')
    return report


def print_report(report):
    result = report['result']
    print(old.encode(report).decode())
    for key, value in result.items():
        if key != 'per_model_arm':
            print('METRIC ' + key + '=' + str(value))
    for model in old.load(old.CONTROL)['models']:
        label = 'model70b' if model.endswith('-70B') else 'model8b'
        for arm in ('simple', 'conditional'):
            for key, value in result['per_model_arm'][model + '/' + arm].items():
                print('METRIC ' + label + '_' + arm + '_' + key + '=' + str(value))
    print('METRIC requests=' + str(sum(x['requests'] for x in result['per_model_arm'].values())))
    print('METRIC recovery_wall_seconds=' + str(report['recovery_wall_seconds']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ('prepare', 'execute-report', 'check'):
        group.add_argument('--' + flag, action='store_true')
    args = parser.parse_args()
    if args.prepare:
        old.require(not JOB.exists(), 'REPORT_ALREADY_EXISTS')
        frozen = protocol()
        save(CONTROL, frozen)
        print('Prepared offline recovery. protocol_sha256=' + old.sha(CONTROL.read_bytes()))
    else:
        print_report(execute_report() if args.execute_report else check())


if __name__ == '__main__':
    main()
