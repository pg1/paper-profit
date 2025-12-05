import threading
import time
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any
import logging

# Set up logging - use WARNING level for background jobs to reduce noise
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(threadName)s - %(message)s')

class JobController:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.running = False
    
    def add_job_from_file(self, name: str, file_path: str, function_name: str = "run", 
                          interval: float = 1.0, args: tuple = (), kwargs: dict = None):
        """Load and add a job from a Python file.
        
        Args:
            name: Unique job identifier
            file_path: Path to Python file containing the job
            function_name: Name of function to execute (default: 'run')
            interval: Seconds between executions
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
        """
        if kwargs is None:
            kwargs = {}
        
        try:
            # Load the module from file
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            spec = importlib.util.spec_from_file_location(name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            
            # Get the function
            if not hasattr(module, function_name):
                raise AttributeError(f"Function '{function_name}' not found in {file_path}")
            
            func = getattr(module, function_name)
            
            self.jobs[name] = {
                'func': func,
                'interval': interval,
                'args': args,
                'kwargs': kwargs,
                'thread': None,
                'stop_event': threading.Event(),
                'file_path': str(file_path)
            }
            logging.info(f"Job '{name}' loaded from {file_path} with interval {interval}s")
        
        except Exception as e:
            logging.error(f"Failed to load job '{name}' from {file_path}: {e}")
            raise
    
    def _run_job(self, name: str):
        """Internal method to run a job continuously."""
        job = self.jobs[name]
        stop_event = job['stop_event']
        
        while not stop_event.is_set():
            try:
                logging.info(f"Executing job '{name}'")
                job['func'](*job['args'], **job['kwargs'])
            except Exception as e:
                logging.error(f"Error in job '{name}': {e}")
            
            stop_event.wait(job['interval'])
    
    def start(self, job_name: str = None):
        """Start one or all jobs."""
        jobs_to_start = [job_name] if job_name else list(self.jobs.keys())
        
        for name in jobs_to_start:
            if name not in self.jobs:
                logging.warning(f"Job '{name}' not found")
                continue
            
            job = self.jobs[name]
            if job['thread'] and job['thread'].is_alive():
                logging.warning(f"Job '{name}' already running")
                continue
            
            job['stop_event'].clear()
            job['thread'] = threading.Thread(target=self._run_job, args=(name,), name=name, daemon=True)
            job['thread'].start()
            logging.info(f"Job '{name}' started")
        
        self.running = True
    
    def stop(self, job_name: str = None):
        """Stop one or all jobs."""
        jobs_to_stop = [job_name] if job_name else list(self.jobs.keys())
        
        for name in jobs_to_stop:
            if name not in self.jobs:
                continue
            
            job = self.jobs[name]
            job['stop_event'].set()
            if job['thread']:
                job['thread'].join(timeout=5)
                logging.info(f"Job '{name}' stopped")
        
        if not job_name:
            self.running = False
    
    def remove_job(self, name: str):
        """Remove a job from the controller."""
        if name in self.jobs:
            self.stop(name)
            del self.jobs[name]
            logging.info(f"Job '{name}' removed")
    
    def status(self):
        """Get status of all jobs."""
        status = {}
        for name, job in self.jobs.items():
            is_alive = job['thread'].is_alive() if job['thread'] else False
            status[name] = {
                'running': is_alive,
                'interval': job['interval'],
                'file': job.get('file_path', 'N/A')
            }
        return status


if __name__ == "__main__":
        
    controller = JobController()
    
    # Add jobs from files
    controller.add_job_from_file("order_process", "jobs/process_orders.py", interval=5.0)
    controller.add_job_from_file("update_positions", "jobs/update_positions.py", interval=30.0)
    controller.add_job_from_file("update_market_data", "jobs/update_market_data.py", interval=60.0)  # Run every minute
    #controller.add_job_from_file("trading_bot", "jobs/trading_bot.py", interval=300.0)  # Run every 5 minutes
    #controller.add_job_from_file("monitor", "jobs/monitor_job.py", function_name="process", interval=3.0, args=(80,))
    #def process(threshold):
    #   print(f"Monitoring system... threshold: {threshold}")
    
    # Start all jobs
    controller.start()
    
    # Check status
    print("\nJob Status:")
    for name, info in controller.status().items():
        print(f"  {name}: {'Running' if info['running'] else 'Stopped'} "
              f"(interval: {info['interval']}s, file: {info['file']})")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all jobs...")
        controller.stop()
        print("All jobs stopped")
