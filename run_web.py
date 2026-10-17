import sys
import os
import uvicorn

if __name__ == "__main__":
    # Ensure UTF-8 output on Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    root_dir = os.path.dirname(os.path.abspath(__file__))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        
    print("=" * 60)
    print(">> Starting Politeknik Student Course Management Web Server...")
    print(">> Open your browser at: http://localhost:8000")
    print("=" * 60)
    uvicorn.run("web.server:app", host="127.0.0.1", port=8000, reload=True)
