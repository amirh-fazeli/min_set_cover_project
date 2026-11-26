"""Benchmark existing Set Cover instances. Python 3.10+, standard library only."""
import argparse
import csv
import importlib
import itertools
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import statistics
import time

ALGORITHMS = {
    'brute_force': True, 'branch_bound_v1': True, 'branch_bound_v2': True,
    'dp_bottom_up': True, 'dp_top_down': True, 'greedy': False,
    'randomized_greedy': False, 'local_search': False,
}


def load_orlib_instance(filepath):
    """Read the row-oriented OR-Library format; reject weighted instances."""
    data = list(map(int, Path(filepath).read_text().split()))
    if len(data) < 2:
        raise ValueError('Missing dimensions')
    m, n = data[:2]
    if min(m, n) < 0 or len(data) < 2 + n:
        raise ValueError('Invalid dimensions or costs')
    if any(c != 1 for c in data[2:2+n]):
        raise ValueError('Not an unweighted instance')
    subsets = [set() for _ in range(n)]
    pos = 2 + n
    for row in range(m):
        if pos >= len(data):
            raise ValueError('Missing row')
        count = data[pos]
        pos += 1
        if count < 0 or pos + count > len(data):
            raise ValueError('Invalid row count')
        columns = data[pos:pos+count]
        pos += count
        for col in columns:
            if not 1 <= col <= n:
                raise ValueError('Invalid column index')
            subsets[col-1].add(row)
    if pos != len(data):
        raise ValueError('Unexpected trailing data')
    universe = set(range(m))
    if set().union(*subsets) != universe:
        raise ValueError('Infeasible benchmark instance')
    return {'universe': universe, 'subsets': subsets}


def valid_cover(instance, solution):
    if not isinstance(solution, list):
        return False
    s = instance['subsets']
    if not all(type(i) is int and 0 <= i < len(s) for i in solution):
        return False
    return len(set(solution)) == len(solution) and instance['universe'] <= set().union(*(s[i] for i in solution))


def worker(name, instance, seed, connection):
    """Time only solve(), not import, loading, validation or serialization."""
    try:
        solve = importlib.import_module('algorithms.' + name).solve
        connection.send(('ready',))
        start = time.perf_counter()
        try:
            result = solve(instance, seed=seed)
            elapsed = time.perf_counter() - start
            status = 'ok' if valid_cover(instance, result) else 'invalid_cover'
            connection.send((status, elapsed, result, ''))
        except MemoryError:
            connection.send(('memory_error', time.perf_counter()-start, None, 'MemoryError'))
        except Exception as e:
            connection.send(('error', time.perf_counter()-start, None, repr(e)))
    except Exception as e:
        connection.send(('error', None, None, repr(e)))
    finally:
        connection.close()


def run_one(name, instance, seed, timeout, dp_limit):
    if name == 'dp_bottom_up' and len(instance['universe']) > dp_limit:
        return 'skipped_memory_risk', None, None, f'Universe exceeds DP limit {dp_limit}'
    ctx = mp.get_context('spawn')
    receive, send = ctx.Pipe(duplex=False)
    process = ctx.Process(target=worker, args=(name, instance, seed, send))
    process.start()
    send.close()
    try:
        if not receive.poll(60):
            return 'startup_timeout', None, None, 'Worker did not initialize'
        first = receive.recv()
        if first[0] != 'ready':
            return first
        if not receive.poll(timeout):
            return 'timeout', None, None, f'Time limit {timeout}s'
        return receive.recv()
    except EOFError:
        return 'worker_crash', None, None, f'Worker exited: {process.exitcode}'
    finally:
        if process.is_alive():
            process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join()
        receive.close()


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_references(path):
    if not path:
        return {}
    refs = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            kind = row['reference_type']
            if kind not in ('optimal', 'best_known') or int(row['reference_size']) < 1:
                raise ValueError('Invalid reference row: ' + str(row))
            refs[row['instance']] = (int(row['reference_size']), kind)
    return refs


def annotate_quality(rows, refs):
    for name, group_iter in itertools.groupby(rows, key=lambda r: r['instance']):
        group = list(group_iter)
        exact = {r['cover_size'] for r in group if r['status']=='ok' and ALGORITHMS[r['algorithm']]}
        sizes = [r['cover_size'] for r in group if r['status']=='ok']
        if len(exact)>1:
            raise ValueError(f'Exact solvers disagree on {name}: {exact}')
        ref, kind = refs.get(name, (None, 'unavailable'))
        if exact:
            v = next(iter(exact))
            if (kind=='optimal' and ref!=v) or (kind=='best_known' and ref<v):
                raise ValueError(f'Reference conflicts with exact result on {name}')
            ref, kind = v, 'optimal'
        if ref is None and sizes:
            ref, kind = min(sizes), 'best_observed'
        if kind=='optimal' and sizes and min(sizes)<ref:
            raise ValueError(f'Cover beats claimed optimum on {name}')
        for r in group:
            r['reference_size'] = ref
            r['reference_type'] = kind
            r['gap_percent'] = 100*(r['cover_size']-ref)/ref if r['status']=='ok' and ref else None


def summarize(rows):
    groups = {}
    for r in rows:
        groups.setdefault((r['instance'],r['algorithm']), []).append(r)
    result = []
    for (name, algo), group in groups.items():
        ok = [r for r in group if r['status']=='ok']
        times = [r['runtime_s'] for r in ok]
        sizes = [r['cover_size'] for r in ok]
        gaps = [r['gap_percent'] for r in ok if r['gap_percent'] is not None]
        result.append(dict(instance=name, algorithm=algo, family=group[0]['family'], experiments=group[0]['experiments'], target_density=group[0]['target_density'], data_seed=group[0]['data_seed'], n=group[0]['n'], m=group[0]['m'], density=group[0]['density'], runs=len(group), successful_runs=len(ok), timeouts=sum(r['status']=='timeout' for r in group), statuses=json.dumps({s:sum(r['status']==s for r in group) for s in sorted({r['status'] for r in group})}), mean_runtime_s=statistics.mean(times) if times else None, sd_runtime_s=statistics.stdev(times) if len(times)>1 else None, mean_cover_size=statistics.mean(sizes) if sizes else None, sd_cover_size=statistics.stdev(sizes) if len(sizes)>1 else None, best_cover_size=min(sizes) if sizes else None, reference_type=group[0]['reference_type'], reference_size=group[0]['reference_size'], mean_gap_percent=statistics.mean(gaps) if gaps else None, sd_gap_percent=statistics.stdev(gaps) if len(gaps)>1 else None))
    return result


def instances(args):
    """Load all selected, unit-cost datasets under datasets/existing."""
    directory = args.data_dir / "existing"
    paths = sorted(directory.rglob("*.txt"))
    if not paths:
        raise ValueError(f"No existing datasets found in {directory.resolve()}")

    print(f"Found {len(paths)} existing datasets", flush=True)
    seen = set()
    for path in paths:
        name = path.stem.lower()
        family = path.parent.name
        if name in seen:
            raise ValueError(f"Duplicate dataset: {name}")
        seen.add(name)
        instance = load_orlib_instance(path)
        yield name, "existing", instance, None, None, family


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parent / 'datasets')
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parent / 'results/results_existing')
    parser.add_argument('--references', type=Path)
    parser.add_argument('--timeout', type=float, default=10)
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--dp-limit', type=int, default=20)
    parser.add_argument('--algorithms', nargs='+', choices=list(ALGORITHMS), default=list(ALGORITHMS))
    args = parser.parse_args()
    if min(args.timeout,args.repeats)<=0 or not 0<=args.dp_limit<=22:
        parser.error('Positive repetitions/timeout required; DP limit must be 0–22')
    refs = read_references(args.references)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'environment.json').write_text(json.dumps({'python':platform.python_version(),'platform':platform.platform(),'processor':platform.processor(),'logical_cpus':os.cpu_count(),'parameters':dict(vars(args), mode='existing')},default=str,indent=2))
    rows=[]
    for name, family, instance, data_seed, p, experiments in instances(args):
        n,m=len(instance['universe']),len(instance['subsets'])
        density=sum(map(len,instance['subsets']))/(n*m) if n*m else 0
        for algo in args.algorithms:
            for rep in range(args.repeats):
                seed=42+rep
                status, elapsed, solution, error=run_one(algo,instance,seed,args.timeout,args.dp_limit)
                rows.append(dict(instance=name,family=family,experiments=experiments,n=n,m=m,density=density,target_density=p,data_seed=data_seed,algorithm=algo,exact=ALGORITHMS[algo],repeat=rep+1,seed=seed,status=status,runtime_s=elapsed,timeout_s=args.timeout,cover_size=len(solution) if status=='ok' else None,selected_indices=json.dumps(solution) if status=='ok' else None,error=error,reference_size=None,reference_type=None,gap_percent=None))
                print(name,algo,rep+1,status,elapsed,flush=True)
                # Checkpoint the raw results after each attempt.
                write_csv(args.out/'raw_results.csv',rows)
        annotate_quality(rows,refs)
        write_csv(args.out/'raw_results.csv',rows)
        write_csv(args.out/'summary.csv',summarize(rows))
    print('Finished:',args.out)


if __name__=='__main__':
    mp.freeze_support()
    main()
