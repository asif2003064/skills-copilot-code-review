"""
Announcements endpoints for the High School Management System API

Provides CRUD operations for school announcements.
Active announcements are public; management requires teacher authentication.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def _serialize_announcement(doc: dict) -> dict:
    """Convert a MongoDB announcement document to a JSON-safe dict."""
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """
    Get all currently active announcements.

    Returns announcements whose expiration_date is in the future
    and whose start_date (if set) is today or earlier.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    query = {
        "expiration_date": {"$gte": today},
        "$or": [
            {"start_date": {"$exists": False}},
            {"start_date": ""},
            {"start_date": {"$lte": today}},
        ],
    }

    results = []
    for doc in announcements_collection.find(query).sort("created_at", -1):
        results.append(_serialize_announcement(doc))
    return results


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements(
    teacher_username: str = Query(..., description="Authenticated teacher username"),
) -> List[Dict[str, Any]]:
    """
    Get every announcement (active and expired) for management purposes.
    Requires teacher authentication.
    """
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    results = []
    for doc in announcements_collection.find().sort("created_at", -1):
        results.append(_serialize_announcement(doc))
    return results


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    message: str = Query(..., description="Announcement text"),
    expiration_date: str = Query(..., description="Expiration date (YYYY-MM-DD)"),
    start_date: Optional[str] = Query("", description="Optional start date (YYYY-MM-DD)"),
    teacher_username: str = Query(..., description="Authenticated teacher username"),
) -> Dict[str, Any]:
    """
    Create a new announcement. Requires teacher authentication.
    """
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate expiration date format
    try:
        datetime.strptime(expiration_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid expiration_date format. Use YYYY-MM-DD.",
        )

    # Validate optional start date format
    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid start_date format. Use YYYY-MM-DD.",
            )

    doc = {
        "message": message,
        "expiration_date": expiration_date,
        "start_date": start_date or "",
        "created_by": teacher_username,
        "created_at": datetime.now().isoformat(),
    }

    result = announcements_collection.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str = Query(..., description="Updated announcement text"),
    expiration_date: str = Query(..., description="Updated expiration date (YYYY-MM-DD)"),
    start_date: Optional[str] = Query("", description="Optional updated start date (YYYY-MM-DD)"),
    teacher_username: str = Query(..., description="Authenticated teacher username"),
) -> Dict[str, Any]:
    """
    Update an existing announcement. Requires teacher authentication.
    """
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate the announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    existing = announcements_collection.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Validate date formats
    try:
        datetime.strptime(expiration_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid expiration_date format. Use YYYY-MM-DD.",
        )

    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid start_date format. Use YYYY-MM-DD.",
            )

    update_data = {
        "message": message,
        "expiration_date": expiration_date,
        "start_date": start_date or "",
    }

    announcements_collection.update_one({"_id": obj_id}, {"$set": update_data})

    updated = announcements_collection.find_one({"_id": obj_id})
    return _serialize_announcement(updated)


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: str = Query(..., description="Authenticated teacher username"),
) -> Dict[str, str]:
    """
    Delete an announcement. Requires teacher authentication.
    """
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    result = announcements_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted successfully"}
