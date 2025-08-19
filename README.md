# Project Manager Agent

AI Project Manager Agent — a small, open-source MVP demonstrating agent-based task and meeting management using WebSockets and FastAPI.

This repository contains two cooperating agents:

- **Chat Agent** (`/ws/chat`) — an interactive WebSocket-powered assistant you can chat with. It discusses projects, delegates task operations to the task manager agent, and can review meeting content.
- **Meeting→Project Agent (Task Manager Agent)** — a second agent responsible for accepting task/meeting-related requests (runs as a WebSocket service, commonly on port 8001) and assigning meeting transcripts or created tasks to projects and persisting project/task data.

You can find the code for the Task Manager Agent at:  https://github.com/IAmTomShaw/task-manager-agent.

The system is designed as an educational MVP: it shows how to wire LLM-driven agents to external tools (database, Notion optional), how to use function tools, and how to operate real-time chat over WebSockets.

## 🚀 Features

- Real-time WebSocket chat agent (`/ws/chat`) with session-based conversation memory
- Task and project management tools (create/list/update/delete projects and tasks)
- Meeting transcript assignment: agent that associates a meeting transcript with an existing project
- Simple Streamlit frontend for manual testing and demos (`frontend.py`)

## 🏗️ Architecture (high-level)

1. `main.py` — FastAPI app that mounts routes in `routes/` and exposes REST + WebSocket endpoints (default port 8000).
2. `routes/chat.py` — WebSocket endpoint `/ws/chat` which implements the Chat Agent. It receives JSON or plain text, invokes the chat agent, and returns a structured response.
3. Task Manager Agent — separate agent that processes task/meeting work. In this codebase it runs via a WebSocket-compatible interface (for example, run on `ws://localhost:8001`) and exposes functions for creating projects/tasks and assigning meeting transcripts to projects.
4. `lib/` — core libraries: `agent.py`, `task_manager.py` (websocket integration), `mongo.py` (database helpers), `tools.py` (function tools exposed to the agent), and more.
5. `frontend.py` — Streamlit UI for chat interactions.

## 🛠️ Setup

### Prerequisites

- Python 3.11+ (project uses modern asyncio features)
- MongoDB (local or remote) or adjust `lib/mongo.py` to use your preferred database

### Installation

1. Clone the repo:

```bash
git clone <repo-url>
cd project-manager-agent
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` (copy `.env.example` or create) and set required variables:

```
API_KEY=your_api_key          # required for protected endpoints (communication between your agent and the Streamlit UI)
MONGO_URI=your_mongo_uri_connection_string
MONGO_DB=your_database_name
OPENAI_API_KEY=sk-...        # for LLM usage
```

4. Start MongoDB (or run via Docker Compose if you add it).

5. Run the main FastAPI server (chat agent + REST endpoints):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

6. (Optional) Start the Task Manager agent websocket service if you run it separately (default port 8001). This will be run as a separate process - see the Task Manager agent documentation for details.

7. (Optional) Run the Streamlit demo frontend:

```bash
streamlit run frontend.py
```

## 🔌 WebSocket API

### Chat Agent (`/ws/chat`)

Connect to:

```
ws://localhost:8000/ws/chat
```

If `API_KEY` is set in the server environment, the client must provide the same key. The client can send the key either as the `x-api-key` header or as an `api_key` query parameter.

### Message format (client -> agent)

Send JSON messages with this shape:

```json
{
  "session_id": "unique-session-id",
  "message": "Create a new project called Website Redesign",
  "user_id": "user",
  "timestamp": "2025-01-01T10:00:00Z",
  "message_type": "chat"
}
```

Special command: set `message` to "/clear" or `message_type: "clear"` to reset conversation history for that session.

### Response format (agent -> client)

```json
{
  "session_id": "unique-session-id",
  "message": "Project 'Website Redesign' created successfully.",
  "sender": "agent",
  "timestamp": "2025-01-01T10:00:01Z",
  "message_type": "response",
  "success": true,
  "error": null
}
```

## 🛠️ Available Tools (selected)

The agent exposes several function tools through `lib/tools.py` for interacting with the project data store:

- `create_project(title: str, due_date: str, additional_info?: str)` — create a project (calls `mongo_create_project`).
- `get_projects_list()` — list projects.
- `get_project_details(project_id: str)` — fetch project details.
- `get_meetings_list()` / `get_meeting_details(meeting_id)` — read meeting data.
- `update_meeting_project_id(meeting_id, project_id)` — assign a meeting to a project.
- `communicate_with_task_manager(message: str)` — high-level passthrough to the task manager agent.

See `lib/tools.py` for the full definitions and usage.

## 🔧 Notes on the two agents

- Chat Agent (interactive): the main conversational interface. It interprets user intent, calls tools when needed (for example to create a project), and summarizes or reviews meeting notes.
- Meeting→Project Agent: the specialist agent that receives a notification of a new meeting being added to the database and decides which project (if any) the transcript should be attached to. It can create/update projects and tasks and persists them via MongoDB or Notion (when configured).

## 🐳 Docker (optional)

Create a simple `Dockerfile` and `docker-compose.yml` to include MongoDB and the FastAPI service for reproducible local development. Example run:

```bash
# build
docker build -t project-manager-agent .

# run with .env file
docker run -p 8000:8000 --env-file .env project-manager-agent
```

## 💡 Usage examples

Create a project message (via WebSocket):

```json
{
  "session_id": "session123",
  "message": "Create a project: Website Redesign due 2025-09-01",
  "message_type": "chat"
}
```

Assign a meeting transcript to a project (agent-invoked):

```json
{
  "session_id": "session123",
  "message": "Assign meeting: <transcript text> to project 'Website Redesign'",
  "message_type": "chat"
}
```

## The New Meeting Webhook

When a new meeting is created, a webhook can be triggered to notify the relevant agents. This allows the Meeting→Project Agent to take action based on the meeting details.

### Webhook Payload

The webhook should send a POST request to the following endpoint:

```
POST /webhook

Headers:
Content-Type: application/json
x-api-key: your_api_key_here
```

The payload should include the meeting ID:

```json
{
  "meeting_id": "unique-meeting-id"
}
```

The meeting should already be stored in the database. In my case, I am ingesting meetings using a separate ingestion pipeline from my Meeting Notetaker tool.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests and linters
4. Open a pull request with a description of your changes

Please include a short description of how your change was tested.

---

Built with ❤️ by [Tom Shaw](https://tomshaw.dev)