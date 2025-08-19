from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from lib.mongo import mongo_get_meeting_by_id
from lib.agent import handle_new_meeting_record

router = APIRouter()

@router.post("/webhook")
async def webhook_endpoint(request: Request):
    data = await request.json()
    # Here you can process the incoming webhook data

    meeting_id = data.get("meeting_id")

    # Get the meeting from mongodb

    meeting = mongo_get_meeting_by_id(meeting_id)

    if meeting is None:
        return JSONResponse(content={"error": "Meeting not found"}, status_code=404)

    # Send to the agent to determine the project

    response = await handle_new_meeting_record("Categorise the following meeting based on the content and assign it a meeting ID in the database.\n " + str(meeting))

    if response is None:
        return JSONResponse(content={"error": "Failed to process meeting"}, status_code=500)

    # For now, just echo back the received data
    return JSONResponse(content={"received": data, "meeting": meeting, "response": response})
