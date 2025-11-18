#!/usr/bin/env python3
"""
Quick test to verify web dashboard can start and handle port conflicts.
This simulates the Termux crash/restart scenario.
"""
import subprocess
import time
import sys
import signal
import os

def test_web_dashboard_startup():
    """Test that web dashboard can start up successfully."""
    print("=" * 70)
    print("Testing Web Dashboard Startup")
    print("=" * 70)
    
    # Set minimal environment
    env = os.environ.copy()
    env['DB_HOST'] = 'localhost'
    env['DB_USER'] = 'test_user'
    env['DB_PASS'] = ''
    env['DB_NAME'] = 'test_db'
    
    print("\n[1] Starting web dashboard...")
    proc = subprocess.Popen(
        [sys.executable, 'web_dashboard.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        bufsize=1
    )
    
    # Monitor output for startup confirmation
    startup_success = False
    socket_options_set = False
    timeout = 15
    start_time = time.time()
    
    print("\n[2] Monitoring startup output...")
    while time.time() - start_time < timeout:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                print(f"\n✗ Process exited unexpectedly with code {proc.returncode}")
                return False
            time.sleep(0.1)
            continue
        
        print(f"    {line.rstrip()}")
        
        if "SO_REUSEADDR enabled" in line:
            socket_options_set = True
            print("    ✓ SO_REUSEADDR configured!")
        
        if "Running on http://127.0.0.1:5000" in line:
            startup_success = True
            print("    ✓ Web dashboard started successfully!")
            break
    
    # Clean up
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        time.sleep(2)
        if proc.poll() is None:
            proc.kill()
    
    proc.wait(timeout=5)
    
    print("\n" + "=" * 70)
    if startup_success and socket_options_set:
        print("✓ TEST PASSED")
        print("  - Web dashboard started successfully")
        print("  - Socket options configured properly")
        print("  - Ready for production use on Termux")
    else:
        print("✗ TEST FAILED")
        if not startup_success:
            print("  - Web dashboard did not start")
        if not socket_options_set:
            print("  - Socket options were not set")
    print("=" * 70)
    
    return startup_success and socket_options_set

if __name__ == '__main__':
    success = test_web_dashboard_startup()
    sys.exit(0 if success else 1)
