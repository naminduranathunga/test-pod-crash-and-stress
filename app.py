import os
import sys
import time
import subprocess
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# Global list to hold memory references so the GC doesn't clean it up early
mem_holder = []

def release_memory_after_delay(delay_seconds):
    """Background task to clear the exhausted memory after the timeout."""
    time.sleep(delay_seconds)
    global mem_holder
    mem_holder.clear()
    print("Memory released successfully.")

@app.route('/', methods=['GET'])
def index():
    """Simple index route to confirm the service is running."""
    return jsonify({"message": "Kubernetes Pod Stress Test Service is running."}), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint to verify the service is alive."""
    return jsonify({"status": "healthy"}), 200

@app.route('/crash', methods=['GET'])
def crash():
    """Crashes the pod by exiting the process with a non-zero error code."""
    print("Crash endpoint triggered. Exiting process...")
    # Using os._exit to bypass Flask's tear-down and force an immediate exit
    os._exit(1)

@app.route('/stress', methods=['GET'])
def stress():
    """
    Stresses the CPU using the Linux 'stress-ng' or 'stress' utility.
    Query parameters:
      - cpu: Number of CPU cores to stress (default: 1)
      - timeout: Duration in seconds (default: 30)
    """
    num_cpu = request.args.get('cpu', default='1', type=str)
    timeout = request.args.get('timeout', default='30', type=str)
    
    # Validation to prevent command injection
    if not num_cpu.isdigit() or not timeout.isdigit():
        return jsonify({"error": "Parameters 'cpu' and 'timeout' must be integers."}), 400

    # Try stress-ng first, fallback to stress
    binary = "stress-ng" if subprocess.run(["which", "stress-ng"], capture_output=True).returncode == 0 else "stress"
    
    cmd = [binary, "--cpu", num_cpu, "--timeout", timeout]
    
    try:
        # Run asynchronously so the HTTP response isn't blocked if timeout is large,
        # or use Popen to return immediately. Here we run it non-blocking:
        subprocess.Popen(cmd)
        return jsonify({
            "status": "Stress test started",
            "command_executed": " ".join(cmd),
            "cores": num_cpu,
            "timeout_seconds": timeout
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to execute stress utility: {str(e)}"}), 500

@app.route('/exhaust-mem', methods=['GET'])
def exhaust_mem():
    """
    Allocates a specific amount of physical memory in MB for 15 minutes.
    Query parameters:
      - mb: Amount of megabytes to allocate (default: 100)
    """
    mb = request.args.get('mb', default=100, type=int)
    duration_seconds = 15 * 60 # 15 minutes
    
    global mem_holder
    if len(mem_holder) > 0:
        return jsonify({"message": "Memory test already running. Clear or wait for it to finish."}), 400

    try:
        print(f"Allocating {mb} MB of physical memory using random bytes...")
        
        # FIX: os.urandom(1024 * 1024) forces actual RAM allocation (RSS)
        # because the data cannot be compressed or optimized by the OS zero-page.
        mem_holder = [os.urandom(1024 * 1024) for _ in range(mb)]
        
        # Start background thread to clear memory after 15 minutes
        timer_thread = threading.Thread(target=release_memory_after_delay, args=(duration_seconds,))
        timer_thread.daemon = True
        timer_thread.start()
        
        return jsonify({
            "status": f"Successfully allocated {mb} MB of physical RAM",
            "duration": "15 minutes"
        }), 200
        
    except MemoryError:
        return jsonify({"error": "Out of memory error triggered while allocating!"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Running on 0.0.0.0 to make it accessible inside a Kubernetes container
    app.run(host='0.0.0.0', port=8080)