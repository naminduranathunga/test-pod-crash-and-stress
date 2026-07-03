const express = require('express');
const { exec, spawn } = require('child_process');
const crypto = require('crypto');

const app = express();
const PORT = 8080;

// Global array to hold memory references so GC doesn't clean it up early
let memHolder = [];

// Helper function to release memory after a delay
const releaseMemoryAfterDelay = (delaySeconds) => {
    setTimeout(() => {
        memHolder = [];
        console.log("Memory released successfully.");
    }, delaySeconds * 1000);
};

// Check if a binary exists (equivalent to 'which' in Linux)
const checkBinaryExists = (binary) => {
    return new Promise((resolve) => {
        exec(`which ${binary}`, (error) => {
            resolve(!error);
        });
    });
};

// --- Routes ---

// Index route
app.get('/', (req, res) => {
    return res.status(200).json({ message: "Kubernetes Pod Stress Test Service is running." });
});

// Health check endpoint
app.get('/health', (req, res) => {
    return res.status(200).json({ status: "healthy" });
});

// Crash endpoint
app.get('/crash', (req, res) => {
    console.log("Crash endpoint triggered. Exiting process...");
    // Force immediate exit bypassing normal teardowns
    process.exit(1);
});

// Stress CPU endpoint
app.get('/stress', async (req, res) => {
    const numCpu = req.query.cpu || '1';
    const timeout = req.query.timeout || '30';

    // Validation to prevent command injection
    const isDigit = /^\d+$/;
    if (!isDigit.test(numCpu) || !isDigit.test(timeout)) {
        return res.status(400).json({ error: "Parameters 'cpu' and 'timeout' must be integers." });
    }

    // Try stress-ng first, fallback to stress
    const hasStressNg = await checkBinaryExists('stress-ng');
    const binary = hasStressNg ? 'stress-ng' : 'stress';

    const args = ['--cpu', numCpu, '--timeout', timeout, '--temp-path', '/tmp'];

    try {
        // FIX: Add shell: true and pipe stdio to your container log so you can debug 
        const child = spawn(binary, args, { 
            shell: true, 
            detached: true, 
            stdio: 'inherit' // This prints stress-ng logs directly to your kubectl logs
        });
        
        child.unref(); 

        return res.status(200).json({
            status: "Stress test started",
            command_executed: `${binary} ${args.join(' ')}`,
            cores: numCpu,
            timeout_seconds: timeout
        });
    } catch (e) {
        return res.status(500).json({ error: `Failed to execute stress utility: ${e.message}` });
    }
});

// Exhaust Memory endpoint
app.get('/exhaust-mem', (req, res) => {
    const mb = parseInt(req.query.mb, 10) || 100;
    const durationSeconds = 15 * 60; // 15 minutes

    if (memHolder.length > 0) {
        return res.status(400).json({ message: "Memory test already running. Clear or wait for it to finish." });
    }

    try {
        console.log(`Allocating ${mb} MB of physical memory using random bytes...`);

        // Node's equivalent of os.urandom. Allocates chunks of 1MB buffer filled with random bytes
        for (let i = 0; i < mb; i++) {
            try {
                memHolder.push(crypto.randomBytes(1024 * 1024));
            } catch (err) {
                // Catches allocation limits before Node completely panics/OOMs out
                memHolder = []; // Clean up partial allocation
                return res.status(500).json({ error: "Out of memory error triggered while allocating!" });
            }
        }

        // Trigger the asynchronous timeout to clear memory later
        releaseMemoryAfterDelay(durationSeconds);

        return res.status(200).json({
            status: `Successfully allocated ${mb} MB of physical RAM`,
            duration: "15 minutes"
        });

    } catch (e) {
        return res.status(500).json({ error: e.message });
    }
});

// Start server on 0.0.0.0 for K8s container reachability
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on port ${PORT}`);
});