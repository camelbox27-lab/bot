from fastapi import FastAPI, BackgroundTasks, HTTPException
import subprocess
import os
import sys

app = FastAPI()

def run_script(script_path, cwd):
    """Runs a python script in a specific directory."""
    python_exe = sys.executable
    print(f"Starting {script_path} in {cwd}...")
    try:
        # Capture output to log or just let it go to stdout/stderr of server
        result = subprocess.run(
            [python_exe, script_path], 
            cwd=cwd, 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            print(f"Script {script_path} failed:\n{result.stderr}")
        else:
            print(f"Script {script_path} finished successfully:\n{result.stdout}")
    except Exception as e:
        print(f"Error running {script_path}: {e}")

@app.post("/run-main")
async def run_main(background_tasks: BackgroundTasks):
    """
    Triggers the root main.py (Dropping Odds -> Sofa -> etc)
    """
    script = "main.py"
    cwd = os.getcwd()
    if not os.path.exists(os.path.join(cwd, script)):
         raise HTTPException(status_code=404, detail="main.py not found in root")
         
    background_tasks.add_task(run_script, script, cwd)
    return {"status": "Main pipeline started in background"}

@app.post("/run-stats")
async def run_stats(background_tasks: BackgroundTasks):
    """
    Triggers istatistik/main.py
    """
    script = "main.py"
    cwd = os.path.join(os.getcwd(), "istatistik")
    
    if not os.path.exists(cwd):
        raise HTTPException(status_code=404, detail="istatistik directory not found")
        
    background_tasks.add_task(run_script, script, cwd)
    return {"status": "Statistics pipeline started in background"}

@app.get("/")
def read_root():
    return {"status": "Server is running. POST to /run-main or /run-stats to execute bots."}

if __name__ == "__main__":
    import uvicorn
    # Listen on all interfaces so Docker/External can access
    uvicorn.run(app, host="0.0.0.0", port=8000)
