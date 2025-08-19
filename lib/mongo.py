from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
import os
from pymongo import MongoClient

def get_db():
  client = MongoClient(os.getenv('MONGO_URI'))
  return client[os.getenv('MONGO_DB')]

def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
	"""Convert ObjectId and datetime fields into JSON-friendly representations."""
	if not doc:
		return doc
	out = dict(doc)
	# Convert _id to id string
	if "_id" in out:
		out["id"] = str(out["_id"])
		out.pop("_id", None)
	# Convert any ObjectId fields to strings (common patterns)
	for k, v in list(out.items()):
		if isinstance(v, ObjectId):
			out[k] = str(v)
		if isinstance(v, datetime):
			out[k] = v.isoformat()
	return out


def mongo_get_meetings_list(limit: int = 100, filters: Optional[Dict[str, Any]] = None, sort_field: str = "occurred_at", desc: bool = True) -> List[Dict[str, Any]]:
	"""Return a list of meetings from the `meetings` collection.

	Args:
	  limit: max number of meetings to return
	  filters: optional MongoDB filter dict
	  sort_field: field to sort by (default: occurred_at)
	  desc: sort descending if True

	Returns:
	  List of dicts with JSON-serializable values (id as string, datetimes as ISO strings)
	"""
	db = get_db()
	query = filters or {}
	sort_dir = -1 if desc else 1

	try:
		cursor = db.meetings.find(query).sort(sort_field, sort_dir).limit(limit)
		results = []
		for doc in cursor:

			serialized_doc = _serialize_doc(doc)

			summary = serialized_doc.get("summary") or {}

			info = {
				"id": serialized_doc.get("id"),
				"attendees": serialized_doc.get("attendees"),
				"short_summary": summary.get("short_summary"),
			}
			print("info: ", info)

			results.append(info)
		return results
	except Exception as e:
		# log and return empty list on error
		print(f"Error fetching meetings: {e}")
		return []


def mongo_get_meeting_by_id(meeting_id: str) -> Optional[Dict[str, Any]]:
	"""Fetch a single meeting by its ObjectId string."""
	db = get_db()
	try:
		oid = ObjectId(meeting_id)
	except Exception:
		return None
	doc = db.meetings.find_one({"_id": oid})
	return _serialize_doc(doc) if doc else None

def mongo_update_meeting_project_id(meeting_id: str, project_id: str) -> Any:
	"""Update the project ID associated with a meeting."""
	db = get_db()
	try:
		oid = ObjectId(meeting_id)
	except Exception:
		return None
	result = db.meetings.update_one({"_id": oid}, {"$set": {"project_id": project_id}})
	return result.modified_count > 0

# Projects

def mongo_create_project(title: str, due_date: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
	"""Create a new project in the `projects` collection."""
	db = get_db()
	project_doc = {
		"title": title,
		"due_date": due_date,
		"additional_info": additional_info,
		"created_at": datetime.now(timezone.utc),
		"updated_at": datetime.now(timezone.utc),
	}
	result = db.projects.insert_one(project_doc)
	return _serialize_doc(db.projects.find_one({"_id": result.inserted_id}))

def mongo_get_projects_list() -> List[Dict[str, Any]]:
	"""Fetch a list of all projects."""
	db = get_db()
	cursor = db.projects.find()
	return [_serialize_doc(doc) for doc in cursor]

def mongo_get_project_by_id(project_id: str) -> Optional[Dict[str, Any]]:
	"""Fetch a single project by its ObjectId string."""
	db = get_db()
	try:
		oid = ObjectId(project_id)
	except Exception:
		return None
	doc = db.projects.find_one({"_id": oid})
	return _serialize_doc(doc) if doc else None