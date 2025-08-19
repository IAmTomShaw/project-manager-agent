from agents import Agent, Runner, TResponseInputItem
from datetime import datetime
from typing import List, Dict, Any
from lib.tools import create_project, get_meeting_details, get_meetings_list, communicate_with_task_manager, get_projects_list, update_meeting_project_id


# In-memory per-session conversation history.
# Key: session_id -> list of message dicts {role, content, timestamp}
conversation_store: Dict[str, List[Dict[str, Any]]] = {}

chat_agent = Agent(
  name="Chat Agent",
  instructions="""
  You are a helpful product manager assistant which communicates with a user via a chatbot interface. Your job is to assist the user in managing their projects by providing relevant information, answering questions, and performing tasks as requested.
  """,
  tools=[
    get_meeting_details,
    get_meetings_list,
    update_meeting_project_id,
    communicate_with_task_manager,
    create_project,
    get_projects_list
  ]
)

def _now_iso() -> str:
  return datetime.utcnow().isoformat() + "Z"


def get_history(session_id: str) -> List[Dict[str, Any]]:
  return conversation_store.setdefault(session_id, [])


async def handle_chat_message(message: str, session_id: str):
  """Handle an incoming chat message, include session history when calling the agent,
  and store the assistant response back into the history.

  This uses an in-memory store by default. For durability you can persist to the
  database (see notes below) by saving the `history` to a ConversationIntent-like model.
  """

  history = get_history(session_id)

  # Format history as TResponseInputItem
  formatted_history = [
    {"role": entry["role"], "content": entry["content"]}
    for entry in history
  ]

  # Append the user message to history
  user_entry = {"role": "user", "content": message, "timestamp": _now_iso()}
  history.append(user_entry)



  # Format history into TResponseInputItem-compatible items before calling Runner.run
  def _to_input_items(history_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for entry in history_list:
      role = entry.get("role", "user")
      # Map roles to the allowed set: user, assistant, system, developer
      if role not in ("user", "assistant", "system", "developer"):
        role = "user"
      items.append({
        "type": "message",
        "role": role,
        "content": entry.get("content", "")
      })
    return items

  input_items = _to_input_items(history)

  try:
    # Pass the typed input_items list to Runner.run
    response = await Runner.run(chat_agent, input_items)
  except Exception as e:
    # On agent error, return a friendly message and do not remove history
    return f"Agent error: {str(e)}"

  assistant_text = response.final_output if (response and getattr(response, "final_output", None)) else ""

  # Append assistant reply to history
  assistant_entry = {"role": "assistant", "content": assistant_text, "timestamp": _now_iso()}
  history.append(assistant_entry)

  return assistant_text


async def handle_new_meeting_record(message: str) -> str:

  meeting_processor_agent = Agent(
    name="Meeting Processor Agent",
    instructions="""
    You are specialised with categorising a meeting into a project based on the meeting notes, title and attendees that you are given. You can retreive the projects list from the database so that you can determine the exact project id to assign. You should then assign the meeting to the appropriate project using the tools that you have access to.
    If you cannot find the appropriate project, you can create a new project based on the contents of the meeting and assign the meeting to it.
    If needed, you can access the other meetings to see if there are any similar ones that can be referenced to help make your decision.
    """,
    tools=[
      get_meeting_details,
      get_meetings_list,
      update_meeting_project_id,
      create_project,
    ]
  )

  # Process the meeting record using the meeting_processor_agent
  response = await Runner.run(meeting_processor_agent, [{"type": "message", "role": "user", "content": message}])

  return response.final_output if response and getattr(response, "final_output", None) else ""