This will crash the application if you try to run it.

## Endpoints

> /health
Returns the health status of the application.

> /crash
Crashes the application intentionally for testing purposes.

> /stress?cpu=4&timeout=60
Stresses the application by consuming CPU resources. The `cpu` parameter specifies the number of CPU cores to use, and the `timeout` parameter specifies how long to run the stress test in seconds.

> /exhaust-mem?mb=512
Allocates a specified amount of memory in megabytes. The `mb` parameter specifies how much memory to allocate. after 15 minutes the memory will be released.