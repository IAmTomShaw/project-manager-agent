import asyncio
from typing import Optional

import asyncio
import asyncio
from typing import Optional, Any
import json
import uuid
from datetime import datetime

import websockets


async def send_and_receive(message: str, uri: str = "ws://localhost:8001", timeout: float = 10.0) -> Any:
	"""Connect to a websocket at `uri`, send `message`, await a single reply, and return it.

	Behavior:
	- If `uri` ends with '/ws/chat' we send a JSON ChatMessage compatible with the FastAPI task manager.
	- Otherwise we send the raw text message (keeps compatibility with simple echo servers used in tests).

	Returns the parsed JSON response when possible, or the raw text reply.
	"""
	websocket: Optional[websockets.WebSocketClientProtocol] = None
	last_exc = None
	try_uris = [uri]
	# keep backward compatibility: if caller provided base URI, also try /ws/chat
	if not uri.rstrip('/').endswith('/ws/chat'):
		try_uris.append(uri.rstrip('/') + '/ws/chat')

	for try_uri in try_uris:
		try:
			websocket = await websockets.connect(try_uri)

			# If connecting to the FastAPI task manager endpoint, send JSON ChatMessage
			if try_uri.rstrip('/').endswith('/ws/chat'):
				payload = {
					"session_id": str(uuid.uuid4()),
					"message": message,
					"user_id": "user",
					"timestamp": datetime.utcnow().isoformat(),
					"message_type": "chat",
				}
				await websocket.send(json.dumps(payload))
			else:
				await websocket.send(message)

			reply = await asyncio.wait_for(websocket.recv(), timeout=timeout)

			# try parse JSON reply if possible
			try:
				parsed = json.loads(reply)
				# FastAPI chat returns a ChatResponse model JSON; prefer returning its 'message' field
				if isinstance(parsed, dict) and parsed.get("message") is not None:
					return parsed["message"]
				return parsed
			except Exception:
				return reply

		except Exception as e:
			last_exc = e
			# ensure websocket closed before trying next uri
			try:
				if websocket is not None:
					await websocket.close()
			except Exception:
				pass
			websocket = None
			continue

	# if we exhausted attempts, raise the last exception
	if last_exc:
		raise last_exc
	raise RuntimeError("Failed to connect to websocket")


def send_and_receive_sync(message: str, uri: str = "ws://localhost:8001", timeout: float = 10.0) -> Any:
	"""Synchronous wrapper that runs the async send_and_receive using asyncio.run.

	Useful for scripts that don't use an existing event loop.
	"""
	return asyncio.run(send_and_receive(message, uri=uri, timeout=timeout))


__all__ = ["send_and_receive", "send_and_receive_sync"]


