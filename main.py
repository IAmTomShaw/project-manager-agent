from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from fastapi.middleware.cors import CORSMiddleware
import importlib
import os
import glob
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_KEY_NAME = "x-api-key"

# Create the FastAPI app with lifespan
app = FastAPI()

# Allow frontend connection (adjust origins as needed)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # Change to specific origin in production
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key: str = Depends(api_key_header)):
  if api_key != API_KEY:
    raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key")
  return api_key


# Dynamically import all routers from routes folder
routes_path = os.path.join(os.path.dirname(__file__), "routes")
for file in glob.glob(os.path.join(routes_path, "*.py")):
	module_name = f"routes.{os.path.splitext(os.path.basename(file))[0]}"
	module = importlib.import_module(module_name)
	if hasattr(module, "router"):
		app.include_router(module.router)