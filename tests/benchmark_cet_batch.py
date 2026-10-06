"""同一台 Windows 上对批次更新前后的真实 C ABI 查询做可比测量。"""
import argparse
import json
import statistics
import tempfile
import time

from test_native import ROOT, call


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True, choices=['before', 'after'])
    args = parser.parse_args()
    results = []
    with tempfile.TemporaryDirectory(prefix='wordtrail-cet-benchmark-') as user:
        start = time.perf_counter_ns()
        created = call(op='create', data_dir=str(ROOT / 'data'), user_dir=user)
        assert created['error'] is None, created
        initialization_ms = (time.perf_counter_ns() - start) / 1e6
        handle = created['handle']
        try:
            for pinyin in ['fangqi', 'fenxi', 'fazhan', 'ziyou', 'huanjie', 'gongzuo']:
                call(op='reset', handle=handle)
                for char in pinyin:
                    call(op='key', handle=handle, text=char)
                for goals in [[], ['cet4', 'cet6'], ['cet4', 'cet6', 'tem4', 'tem8', 'toefl', 'ielts']]:
                    call(op='vocabulary', handle=handle, vocabulary_targets=goals)
                    for _ in range(30):
                        call(op='state', handle=handle)
                    samples = []
                    for _ in range(180):
                        start = time.perf_counter_ns()
                        state = call(op='state', handle=handle)
                        samples.append((time.perf_counter_ns() - start) / 1e6)
                        assert state['error'] is None
                    samples.sort()
                    results.append(dict(pinyin=pinyin, goals=goals, samples=len(samples),
                                        p50_ms=statistics.median(samples), p95_ms=samples[171], p99_ms=samples[178]))
        finally:
            call(op='destroy', handle=handle)
    report = dict(label=args.label, initialization_ms=initialization_ms, results=results,
                  scope='Same Windows host debug C ABI, packed dictionary + translations + tags + IPA + JSON decode. Warm state queries; not key-to-screen or physical Android latency. Initialization includes dictionary/session load, one cold process sample.')
    path = ROOT / 'build' / ('cet-batch01-performance-' + args.label + '.json')
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(label=args.label, initialization_ms=initialization_ms,
                         p95_range_ms=[min(r['p95_ms'] for r in results), max(r['p95_ms'] for r in results)],
                         groups=len(results)), indent=2))


if __name__ == '__main__':
    main()
