import json
import uuid
import json
import uuid
import traceback
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Import the chat agent handler
from lib.agent import handle_chat_message, conversation_store
from lib.ws_manager import manager as ws_manager

load_dotenv()

router = APIRouter()

class ChatMessage(BaseModel):
	session_id: str
	message: str
	user_id: str = "user"
	timestamp: str | None = None
	message_type: str = "chat"

class ChatResponse(BaseModel):
	session_id: str
	message: str
	sender: str = "agent"
	timestamp: str
	message_type: str = "response"
	success: bool = True
	error: str | None = None

class ConnectionManager:
	def __init__(self):
		self.active_connections: list[WebSocket] = []

	async def connect(self, websocket: WebSocket):
		await websocket.accept()
		self.active_connections.append(websocket)

	def disconnect(self, websocket: WebSocket):
		self.active_connections.remove(websocket)

	async def send_message(self, message: str, websocket: WebSocket):
		await websocket.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
	# Debug: log incoming websocket headers to diagnose connection issues (Origin, Host, etc.)
	try:
		# normalize header names to lowercase
		headers = {k.decode().lower(): v.decode() for k, v in websocket.scope.get('headers', [])}
	except Exception:
		headers = {}
	origin = headers.get('origin')

	# Prepare session id early (useful for sending error responses)
	session_id = str(uuid.uuid4())

	# If an API key is configured in the environment, require clients to provide it
	# either via the x-api-key header or via the api_key query parameter (fallback).
	API_KEY = os.getenv("API_KEY")
	if API_KEY:
		provided = headers.get("x-api-key")
		# fallback: check query string for api_key
		if not provided:
			provided = websocket.query_params.get("api_key")
		if provided != API_KEY:
			# accept connection, send error and close with policy violation
			await websocket.accept()
			error_resp = ChatResponse(
				session_id=session_id,
				message="Invalid or missing API key",
				timestamp=datetime.now().isoformat(),
				success=False,
				error="Invalid or missing API key",
			)
			await websocket.send_text(error_resp.model_dump_json())
			await websocket.close(code=1008)
			return

	# Register connection with shared manager
	await ws_manager.connect(websocket)
	try:
		while True:
			data = await websocket.receive_text()
			# Try to parse JSON payloads first
			try:
				message_data = json.loads(data)
				chat_message = ChatMessage(**message_data)
				# Forward to the agent
				# Handle clear command coming from frontend
				if chat_message.message_type == "clear" or chat_message.message.lower().strip() == "/clear":
					# remove session history if present
					conversation_store.pop(chat_message.session_id, None)
					response = ChatResponse(
						session_id=chat_message.session_id or session_id,
						message="Chat history has been cleared.",
						timestamp=datetime.now().isoformat()
					)
					await ws_manager.send_message(response.model_dump_json(), websocket)
					continue
				try:
					agent_reply = await handle_chat_message(chat_message.message, session_id=chat_message.session_id)
					print("Agent reply:", agent_reply)
					response = ChatResponse(
						session_id=chat_message.session_id or session_id,
						message=agent_reply,
						timestamp=datetime.now().isoformat()
					)
				except Exception as agent_err:
					traceback.print_exc()
					response = ChatResponse(
						session_id=chat_message.session_id or session_id,
						message="Sorry, the agent encountered an error.",
						timestamp=datetime.now().isoformat(),
						success=False,
						error=str(agent_err)
					)
				await ws_manager.send_message(response.model_dump_json(), websocket)
			except json.JSONDecodeError:
				# Handle plain text messages (backwards compatibility)
				try:
					agent_reply = await handle_chat_message(data, session_id=session_id)
					response = ChatResponse(
						session_id=session_id,
						message=agent_reply,
						timestamp=datetime.now().isoformat()
					)
				except Exception as agent_err:
					traceback.print_exc()
					response = ChatResponse(
						session_id=session_id,
						message="Sorry, the agent encountered an error.",
						timestamp=datetime.now().isoformat(),
						success=False,
						error=str(agent_err)
					)
				await ws_manager.send_message(response.model_dump_json(), websocket)
			except Exception as e:
				# Generic error handling for unexpected issues
				traceback.print_exc()
				error_response = ChatResponse(
					session_id=session_id,
					message="Sorry, I encountered an error processing your message.",
					timestamp=datetime.now().isoformat(),
					success=False,
					error=str(e)
				)
				await manager.send_message(error_response.model_dump_json(), websocket)
	except WebSocketDisconnect:
		ws_manager.disconnect(websocket)
