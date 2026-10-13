#!/usr/bin/env python3
"""Owned actual runner/barrier controls; never acquire the public family lock.

Ported from task-pipeline 6b6d625 (test/audit_regressions/fw07_child_lifetime.py).
This repository's runner reads its plants from `.github/workflows/validate.yml`,
so each fixture writes an owned workflow instead of a `negatives/` directory. The
plant timeout control at the end is local: SD_NEG_TIMEOUT exists only here.
"""
import importlib.util
import json
import os
from pathlib import Path
import select
import shlex
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'test/negative_lock.py'
count = 0

def check(value, name):
    global count
    assert value, name
    count += 1

def wait_file(path, timeout=8):
    stop = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() > stop:
            raise AssertionError('owned barrier missing: ' + str(path))
        time.sleep(.02)
    return path.read_text()

def line(proc):
    assert select.select([proc.stdout], [], [], 8)[0], 'owned output timeout'
    return proc.stdout.readline().strip()

def workflow(source, steps):
    """Write an owned workflow whose steps are (name, script) negative self-tests."""
    out = ['jobs:', '  owned:', '    steps:']
    for name, script in steps:
        out += ['      - name: Negative self-test (' + name + ')', '        run: |']
        out += ['          ' + ln if ln else '' for ln in script.splitlines()]
    wf = source / '.github/workflows/validate.yml'
    wf.parent.mkdir(parents=True, exist_ok=True)
    wf.write_text('\n'.join(out) + '\n')

BOOT = '''import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import negatives,negative_lock
base=Path(sys.argv[2]); negative_lock.scratch_lock_path=lambda:str(base/'lock')
negatives.ROOT=str(base/'source'); negatives.WORKFLOW=str(base/'source/.github/workflows/validate.yml')
negatives.MIN_EXPECTED=1; negatives.MIN_PROPS=0
sys.exit(negatives.main(['fixture']))
'''
CONTEND = '''import sys,os
sys.path.insert(0,sys.argv[1]);import negative_lock
negative_lock.scratch_lock_path=lambda:sys.argv[2]
with negative_lock.acquire_scratch_lock() as held:
 print('ACQUIRED:'+str(os.fstat(held.fileno()).st_ino),flush=True)
'''
# Barrier files are published by rename: a reader polling for existence must never
# see a half-written file (an empty `ready` failed 1 of 8 local repeats).
WRITER = '''import os,sys,time,json,signal
from pathlib import Path
b=Path(sys.argv[1]);lock=(b/'lock').stat()
if len(sys.argv)>2:signal.signal(signal.SIGTERM,signal.SIG_IGN)
fds=[]
for fd in range(3,256):
 try:
  s=os.fstat(fd)
  if (s.st_dev,s.st_ino)==(lock.st_dev,lock.st_ino):fds.append(fd)
 except OSError:pass
(b/'ready.tmp').write_text(json.dumps({'pid':os.getpid(),'bash':os.getppid(),'fds':fds}));os.replace(b/'ready.tmp',b/'ready')
stop=time.monotonic()+12
while not (b/'go').exists():
 if time.monotonic()>stop:sys.exit(5)
 time.sleep(.02)
(b/'written.tmp').write_text('last writer completed');os.replace(b/'written.tmp',b/'written')
print('OK: owned writer complete',flush=True)
'''

for killed in ('parent', 'bash', 'term', 'int', 'normal'):
    with tempfile.TemporaryDirectory(prefix='fw07-child-lock-') as tmp:
        base=Path(tmp);source=base/'source';source.mkdir(parents=True)
        (source/'writer.py').write_text(WRITER)
        suffix=' ignore-term' if killed in ('term','int') else ''
        # A trailing command stops Bash exec-replacing itself, so 'bash' kills Bash.
        script='python3 '+shlex.quote(str(source/'writer.py'))+' '+shlex.quote(str(base))+suffix+'\n:\n'
        workflow(source,[('owned child lifetime',script)])
        parent=subprocess.Popen([sys.executable,'-u','-B','-c',BOOT,str(ROOT/'test'),str(base)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        contender=None;info=None
        try:
            info=json.loads(wait_file(base/'ready'))
            check(bool(info['fds']), killed+': actual writing Python inherits lock')
            check(info['bash']!=parent.pid, killed+': writer parent is Bash, not the runner')
            inode=(base/'lock').stat().st_ino
            if killed in ('parent','bash'):
                os.kill(parent.pid if killed=='parent' else info['bash'],signal.SIGKILL)
            elif killed in ('term','int'):
                parent.send_signal(signal.SIGTERM if killed=='term' else signal.SIGINT)
                out,err=parent.communicate(timeout=8)
                check(parent.returncode!=0 and 'plant lifecycle refused' in out,killed+': actual runner refuses interruption')
                check(not (base/'written').exists(),killed+': cancelled child did not write')
            contender=subprocess.Popen([sys.executable,'-u','-B','-c',CONTEND,str(ROOT/'test'),str(base/'lock')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            first=line(contender)
            if killed in ('parent','bash','normal'):
                check('waiting' in first,killed+': contender waits for live writer')
                check(not select.select([contender.stdout],[],[],.15)[0] and contender.poll() is None,killed+': no premature admission')
                (base/'go').write_text('release')
                check(wait_file(base/'written')=='last writer completed',killed+': original child final write observed')
                first=line(contender)
            else:
                (base/'go').write_text('release after cancelled runner')
                time.sleep(.05)
                check(not (base/'written').exists(),killed+': no writing descendant survived cancellation')
            check(first=='ACQUIRED:'+str(inode),killed+': same inode admits after lifetime')
            contender.communicate(timeout=8);check(contender.returncode==0,killed+': contender completed')
            out,err=parent.communicate(timeout=8)
            if killed=='normal':check(parent.returncode==0 and 'provably reject' in out,'normal actual runner verdict preserved')
        finally:
            if info:
                try:os.killpg(info['bash'],signal.SIGKILL)
                except (ProcessLookupError,PermissionError):pass
                try:os.kill(info['pid'],signal.SIGKILL)
                except ProcessLookupError:pass
            for proc in (parent,contender):
                if proc is not None:
                    if proc.poll() is None:proc.kill()
                    proc.communicate(timeout=5)

# Failure/cancellation must prevent new queued work and restore signal handlers.
spec=importlib.util.spec_from_file_location('owned_negative_lock',HELPER)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='fw07-child-errors-') as tmp:
    base=Path(tmp);m.scratch_lock_path=lambda:str(base/'lock')
    handlers={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    try:
        with m.ScratchProcesses() as plants:
            plants.hold(m.acquire_scratch_lock())
            plants.run(['/definitely/missing/owned-command'],cwd=base)
    except FileNotFoundError:check(True,'spawn error propagated')
    else:raise AssertionError('spawn error accepted')
    check(all(signal.getsignal(s)==h for s,h in handlers.items()),'handlers restored after spawn failure')
    with m.ScratchProcesses() as plants:
        plants.hold(m.acquire_scratch_lock());plants.cancel()
        try:plants.run([sys.executable,'-c','raise SystemExit(0)'],cwd=base)
        except InterruptedError:check(True,'cancelled queue cannot launch')
        else:raise AssertionError('cancelled launch accepted')
    with m.acquire_scratch_lock():check(True,'failed owner releases for safe retry')
# Signals while Popen has created a child but has not returned its handle must
# not lose that child or turn interruption into a successful result.
from unittest.mock import patch
for sig in (signal.SIGINT, signal.SIGTERM):
    with tempfile.TemporaryDirectory(prefix='fw07-child-startup-') as tmp:
        base=Path(tmp);m.scratch_lock_path=lambda:str(base/'lock')
        real_popen=subprocess.Popen
        def interrupted_spawn(*args, **kwargs):
            child=real_popen(*args, **kwargs)
            signal.raise_signal(sig)
            return child
        with m.ScratchProcesses() as plants:
            plants.hold(m.acquire_scratch_lock())
            try:
                with patch.object(subprocess,'Popen',side_effect=interrupted_spawn):
                    plants.run([sys.executable,'-c','import time;time.sleep(10)'],cwd=base)
            except InterruptedError:check(True,'startup signal refuses result')
            else:raise AssertionError('startup signal accepted')
            check(not plants._active,'startup child drained and deregistered')
        with m.acquire_scratch_lock():check(True,'startup cancellation permits retry')

# A communicate failure is a fixture error and must kill/drain the writer,
# including one that ignores TERM, before allowing the next lock holder.
with tempfile.TemporaryDirectory(prefix='fw07-child-communicate-') as tmp:
    base=Path(tmp);m.scratch_lock_path=lambda:str(base/'lock')
    real_popen=subprocess.Popen; children=[]
    def broken_communicate_spawn(*args, **kwargs):
        proc=real_popen(*args, **kwargs);children.append(proc)
        original=proc.communicate;first=True
        def communicate(*a, **k):
            nonlocal first
            if first:
                first=False
                raise OSError('owned communicate fault')
            return original(*a, **k)
        proc.communicate=communicate
        return proc
    with m.ScratchProcesses() as plants:
        plants.hold(m.acquire_scratch_lock())
        try:
            with patch.object(subprocess,'Popen',side_effect=broken_communicate_spawn):
                plants.run([sys.executable,'-c','import time;time.sleep(10)'],cwd=base)
        except OSError as exc:check(str(exc)=='owned communicate fault','communicate error preserved')
        else:raise AssertionError('communicate failure accepted')
        check(all(p.poll() is not None for p in children),'communicate failure drains children')
    with m.acquire_scratch_lock():check(True,'communicate failure permits retry')

# Waiting for another owner must remain interruptible before any plant launches.
for sig in (signal.SIGINT, signal.SIGTERM):
    with tempfile.TemporaryDirectory(prefix='fw07-child-wait-') as tmp:
        base=Path(tmp);workflow(base/'source',[('wait admission','echo OK: unreachable')])
        m.scratch_lock_path=lambda:str(base/'lock')
        with m.acquire_scratch_lock() as held:
            waiter=subprocess.Popen([sys.executable,'-u','-B','-c',BOOT,str(ROOT/'test'),str(base)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                check('waiting' in line(waiter),'actual runner waits before mutation')
                waiter.send_signal(sig);out,err=waiter.communicate(timeout=5)
                check(waiter.returncode==1 and 'plant lock wait interrupted' in out,'waiting runner interruption refuses promptly')
            finally:
                if waiter.poll() is None:waiter.kill();waiter.communicate(timeout=5)

# macOS answers EPERM for a group whose members exited unreaped (another thread
# owns the reap). Cancellation must keep going, escalate and drain; a group of
# zombies is not a live group.
class _Exited:
    pid=999999
    def poll(self):return 0
for err in (PermissionError, ProcessLookupError):
    sent=[]
    def killpg(pid,sig,err=err):
        sent.append(sig)
        raise err(1,'owned fixture')
    with patch.object(m.os,'killpg',side_effect=killpg):
        plants=m.ScratchProcesses();plants._active={_Exited(),_Exited()}
        plants.cancel()
        check(sent.count(signal.SIGKILL)==2, err.__name__+': cancel escalates past a refused group')
        check(m.ScratchProcesses._group_exists(_Exited(),settle=0) is False, err.__name__+': refused probe is no live group')
with patch.object(m.os,'killpg',side_effect=lambda pid,sig:None):
    check(m.ScratchProcesses._group_exists(_Exited(),settle=0.05) is True,'a group still answering after settle is live')
# cancel() failing must not skip draining the child that run() started.
with tempfile.TemporaryDirectory(prefix='fw07-child-cancelfault-') as tmp:
    base=Path(tmp);m.scratch_lock_path=lambda:str(base/'lock')
    with m.ScratchProcesses() as plants:
        plants.hold(m.acquire_scratch_lock());started=[];drained=[]
        real_popen=subprocess.Popen
        def spawn(*a,**k):
            proc=real_popen(*a,**k);started.append(proc)
            def communicate(*x,**y):raise OSError('owned communicate fault')
            proc.communicate=communicate
            return proc
        plants._drain=lambda proc:(drained.append(proc),proc.kill(),proc.wait())
        def fault():raise RuntimeError('owned cancel fault')
        plants.cancel=fault
        try:
            with patch.object(subprocess,'Popen',side_effect=spawn):
                plants.run([sys.executable,'-c','import time;time.sleep(10)'],cwd=base)
        except RuntimeError as exc:check(str(exc)=='owned cancel fault','cancel fault propagates')
        else:raise AssertionError('cancel fault accepted')
        check(drained==started and all(p.poll() is not None for p in started),'cancel fault still drains the child')
# The runner reports a lifecycle RuntimeError as a refusal and removes its snapshot.
with tempfile.TemporaryDirectory(prefix='fw07-child-runtime-') as tmp:
    base=Path(tmp);workflow(base/'source',[('runtime refusal','echo OK: owned')])
    snaps=base/'tmp';snaps.mkdir()
    code=BOOT.replace("sys.exit(negatives.main(['fixture']))","negative_lock.ScratchProcesses._group_exists=staticmethod(lambda proc,settle=1.0:True)\nsys.exit(negatives.main(['fixture']))")
    check(code!=BOOT,'runtime fixture patched the actual runner entry')
    r=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'test'),str(base)],capture_output=True,text=True,timeout=60,env={**os.environ,'TMPDIR':str(snaps)})
    check(r.returncode==1 and 'plant lifecycle refused (RuntimeError)' in r.stdout and 'Traceback' not in r.stderr,'lifecycle RuntimeError is a refusal, not a traceback: '+r.stdout[-300:]+r.stderr[-300:])
    check(not [p for p in snaps.iterdir() if p.name.startswith('tp-negatives-snap-')],'refused run removes its snapshot')

# Local to this runner: SD_NEG_TIMEOUT. A hung plant is a TEST_ERROR (an
# environment fact, never a guard verdict); the lifecycle cancels and drains every
# owned group, including a sibling still running, before the lock is released.
with tempfile.TemporaryDirectory(prefix='fw07-child-timeout-') as tmp:
    base=Path(tmp);source=base/'source';snaps=base/'tmp';snaps.mkdir()
    sleeper=('import os,sys,time;from pathlib import Path\n'
             "Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(30)\n")
    (base/'sleeper.py').write_text(sleeper)
    def hung(tag):
        return 'python3 '+shlex.quote(str(base/'sleeper.py'))+' '+shlex.quote(str(base/('pid-'+tag)))+'\n:\n'
    workflow(source,[('owned hung plant a',hung('a')),('owned hung plant b',hung('b'))])
    started=time.monotonic()
    r=subprocess.run([sys.executable,'-B','-c',BOOT,str(ROOT/'test'),str(base)],capture_output=True,text=True,timeout=60,
                     env={**os.environ,'TMPDIR':str(snaps),'SD_NEG_TIMEOUT':'1'})
    elapsed=time.monotonic()-started
    check(r.returncode==3 and 'TEST_ERROR:' in r.stdout and 'SD_NEG_TIMEOUT=1s' in r.stdout,'timeout is TEST_ERROR exit3: '+r.stdout[-300:]+r.stderr[-300:])
    check('owned hung plant' in r.stdout and 'NOT a guard verdict' in r.stdout,'timeout names the hung plant and refuses a guard verdict')
    check('plant lifecycle refused' not in r.stdout and 'did not fire' not in r.stdout and 'Traceback' not in r.stderr,'timeout is not reported as a refusal or a guard bypass')
    check(elapsed<20,'timed-out run is cancelled, not waited out: %.1fs'%elapsed)
    for tag in ('a','b'):
        pid=int((base/('pid-'+tag)).read_text())
        stop=time.monotonic()+3
        while True:
            try:os.kill(pid,0)
            except ProcessLookupError:break
            if time.monotonic()>stop:
                os.kill(pid,signal.SIGKILL)
                raise AssertionError('hung plant '+tag+' survived the timeout')
            time.sleep(.02)
        check(True,'hung plant '+tag+' was drained')
    check(not [p for p in snaps.iterdir() if p.name.startswith('tp-negatives-snap-')],'timed-out run removes its snapshot')
    m.scratch_lock_path=lambda:str(base/'lock')
    with m.acquire_scratch_lock():check(True,'timeout releases the owned lock for retry')

print(f'PASS: shared scratch child lifetime — {count} controls; owned namespaces only')
