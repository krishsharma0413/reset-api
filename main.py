import uvicorn
import os

if __name__ == "__main__":
    # uvicorn.run("app:app",host="0.0.0.0",port=5000, reload=False)
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.environ['PORT']), reload=False)
    # uvicorn.run("app:app", host="localhost",port=2000)