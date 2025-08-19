
from agents import function_tool
import datetime
from typing import Optional, Any
import json

from lib.mongo import mongo_get_meetings_list, mongo_get_meeting_by_id, mongo_get_projects_list, mongo_get_project_by_id, mongo_create_project, mongo_update_meeting_project_id


@function_tool
async def get_meeting_details(meeting_id: str) -> Any:
  return mongo_get_meeting_by_id(meeting_id)

@function_tool
async def get_meetings_list() -> Any:
  return mongo_get_meetings_list()

@function_tool
async def update_meeting_project_id(meeting_id: str, project_id: str) -> Any:
  """Update the project ID associated with a meeting."""
  return mongo_update_meeting_project_id(meeting_id, project_id)

@function_tool
async def communicate_with_task_manager(message: str) -> Any:
  """Send a message to the task manager agent. You can ask them to retreive, create, update, or delete tasks. You should send the message in clear natural language."""
  print("Communicating with task manager...: ", message)
  # Sends a message to the task manager agent which processes the message and handles all of the task related tasks
  try:
    from lib.task_manager import send_and_receive

    reply = await send_and_receive(message, uri="ws://localhost:8001", timeout=10.0)
    return {"status": "ok", "message": "sent", "reply": reply}
  except Exception as e:
    print("Error communicating with task manager websocket:", e)
    return {"status": "error", "message": str(e)}


@function_tool
async def create_project(title: str, due_date: str, additional_info: Optional[str] = None) -> Any:
  """Any additional info should be passed as a JSON string (or omitted)."""
  # Parse JSON string if provided
  info = None
  if additional_info is not None:
    try:
      info = json.loads(additional_info)
    except Exception:
      info = {"raw": additional_info}

  print(f"Creating project with title: {title}, due_date: {due_date}, additional_info: {info}")
  return mongo_create_project(title, due_date, info)

@function_tool
async def get_projects_list() -> Any:
  return mongo_get_projects_list()

@function_tool
async def get_project_details(project_id: str) -> Any:
  return mongo_get_project_by_id(project_id)