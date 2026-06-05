import json
import logging
import os
from datetime import date
from calendar import monthrange
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import CalendarEvent, CalendarMember, CalendarEventType, Department, CalendarMemberDepartment, CalendarEventTypeCapacityRule
from ..schemas import success, error
from ..services import add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

AI_READ_API_KEY = os.getenv("AI_READ_API_KEY", "")

# Allowed tools for AI
ALLOWED_AI_TOOLS = {
    "calendar_events_search",
    "calendar_members_list",
    "calendar_capacity_summary"
}

# Tool definitions
TOOL_DEFINITIONS = {
    "calendar_events_search": {
        "name": "calendar_events_search",
        "description": "Search calendar events by various filters",
        "allowed_filters": ["year", "month", "start_date", "end_date", "member_name", "event_name", "event_type_name", "source_type"],
        "max_limit": 100,
        "max_date_range_days": 365
    },
    "calendar_members_list": {
        "name": "calendar_members_list",
        "description": "List calendar members with optional filters",
        "allowed_filters": ["department_name", "is_active"],
        "max_limit": 100,
        "max_date_range_days": None
    },
    "calendar_capacity_summary": {
        "name": "calendar_capacity_summary",
        "description": "Get capacity summary for a given year/month and event types",
        "allowed_filters": ["year", "month", "event_type_name"],
        "max_limit": 50,
        "max_date_range_days": 31
    }
}

def verify_ai_read_key(authorization: str = Header(None)):
    """Verify AI Read API Key for AI reference APIs"""
    if not AI_READ_API_KEY:
        logger.warning("AI_READ_API_KEY not configured")
        raise HTTPException(status_code=500, detail="AI_READ_API_KEY not configured")

    if not authorization:
        logger.warning("Missing Authorization header for AI API")
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        logger.warning("Invalid Authorization header format for AI API")
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    token = authorization.replace("Bearer ", "")
    if token != AI_READ_API_KEY:
        logger.warning("Invalid AI Read API Key")
        raise HTTPException(status_code=403, detail="Invalid API Key")

    return True

@router.get("/api/ai/calendar/capabilities")
def get_ai_capabilities(
    tool_name: str | None = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Return available AI reference tools"""
    try:
        verify_ai_read_key(authorization)
    except HTTPException as e:
        logger.warning(f"AI capabilities access denied: {e.detail}")
        raise
    
    logger.info(f"AI capabilities requested: tool_name={tool_name}")
    add_audit_log(db, "ai_capabilities", "system", None, request={"action": "get_capabilities", "tool_name": tool_name})
    
    tools_data = [
        {
            "name": tool_name_item,
            "description": tool_def["description"],
            "allowed_filters": tool_def["allowed_filters"],
            "max_limit": tool_def["max_limit"]
        }
        for tool_name_item, tool_def in TOOL_DEFINITIONS.items()
    ]
    
    # Filter by tool_name if specified
    if tool_name:
        tools_data = [t for t in tools_data if t["name"] == tool_name]
    
    return success({"tools": tools_data}, "AI capabilities retrieved")

@router.get("/api/ai/calendar/search")
def ai_search(
    tool: str,
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    member_name: str | None = None,
    event_name: str | None = None,
    event_type_name: str | None = None,
    source_type: str | None = None,
    department_name: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Search AI reference tools via GET with query parameters"""
    try:
        verify_ai_read_key(authorization)
    except HTTPException as e:
        logger.warning(f"AI search access denied: {e.detail}")
        raise
    
    # Validate tool
    if tool not in ALLOWED_AI_TOOLS:
        logger.warning(f"AI search: tool not allowed - {tool}")
        raise HTTPException(status_code=400, detail=f"Tool '{tool}' not allowed")
    
    tool_def = TOOL_DEFINITIONS[tool]
    
    # Validate limit
    if limit > tool_def["max_limit"]:
        logger.warning(f"AI search: limit exceeded - {limit} > {tool_def['max_limit']}")
        raise HTTPException(status_code=400, detail=f"Limit exceeds maximum of {tool_def['max_limit']}")
    
    # Build filters based on tool
    filters = {}
    
    if tool == "calendar_events_search":
        if year is not None:
            filters["year"] = year
        if month is not None:
            filters["month"] = month
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        if member_name:
            filters["member_name"] = member_name
        if event_name:
            filters["event_name"] = event_name
        if event_type_name:
            filters["event_type_name"] = event_type_name
        if source_type:
            filters["source_type"] = source_type
    
    elif tool == "calendar_members_list":
        if department_name:
            filters["department_name"] = department_name
        if is_active is not None:
            filters["is_active"] = is_active
    
    elif tool == "calendar_capacity_summary":
        if year is not None:
            filters["year"] = year
        if month is not None:
            filters["month"] = month
        if event_type_name:
            filters["event_type_name"] = event_type_name
    
    # Validate date range
    if tool_def["max_date_range_days"] and "start_date" in filters and "end_date" in filters:
        try:
            start = date.fromisoformat(filters["start_date"])
            end = date.fromisoformat(filters["end_date"])
            if (end - start).days > tool_def["max_date_range_days"]:
                logger.warning(f"AI search: date range too large - {(end - start).days} days")
                raise HTTPException(status_code=400, detail=f"Date range exceeds maximum of {tool_def['max_date_range_days']} days")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Execute tool
    logger.info(f"AI search executing: {tool}")
    result = execute_ai_tool(tool, filters, limit, db)
    
    add_audit_log(db, "ai_search", "system", None, request={
        "tool": tool,
        "filters": {k: v for k, v in filters.items() if k not in ["member_name", "event_name"]},
        "limit": limit,
        "result_count": len(result.get("data", [])) if isinstance(result, dict) else 0
    })
    
    return success(result, f"AI search '{tool}' executed")

@router.post("/api/ai/calendar/query")
def ai_query(
    request_data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Execute a single AI reference tool query"""
    try:
        verify_ai_read_key(authorization)
    except HTTPException as e:
        logger.warning(f"AI query access denied: {e.detail}")
        raise
    
    tool_name = request_data.get("tool")
    filters = request_data.get("filters", {})
    limit = request_data.get("limit", 50)
    
    # Validate tool
    if tool_name not in ALLOWED_AI_TOOLS:
        logger.warning(f"AI query: tool not allowed - {tool_name}")
        add_audit_log(db, "ai_query", "system", None, request={"tool": tool_name, "error": "tool_not_allowed"})
        raise HTTPException(status_code=400, detail=f"Tool '{tool_name}' not allowed")
    
    tool_def = TOOL_DEFINITIONS[tool_name]
    
    # Validate limit
    if limit > tool_def["max_limit"]:
        logger.warning(f"AI query: limit exceeded - {limit} > {tool_def['max_limit']}")
        raise HTTPException(status_code=400, detail=f"Limit exceeds maximum of {tool_def['max_limit']}")
    
    # Validate filters
    for filter_key in filters.keys():
        if filter_key not in tool_def["allowed_filters"]:
            logger.warning(f"AI query: filter not allowed - {filter_key}")
            raise HTTPException(status_code=400, detail=f"Filter '{filter_key}' not allowed for tool '{tool_name}'")
    
    # Validate date range
    if tool_def["max_date_range_days"] and "start_date" in filters and "end_date" in filters:
        try:
            start = date.fromisoformat(filters["start_date"])
            end = date.fromisoformat(filters["end_date"])
            if (end - start).days > tool_def["max_date_range_days"]:
                logger.warning(f"AI query: date range too large - {(end - start).days} days")
                raise HTTPException(status_code=400, detail=f"Date range exceeds maximum of {tool_def['max_date_range_days']} days")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Execute tool
    logger.info(f"AI query executing: {tool_name}")
    result = execute_ai_tool(tool_name, filters, limit, db)
    
    add_audit_log(db, "ai_query", "system", None, request={
        "tool": tool_name,
        "filters": {k: v for k, v in filters.items() if k not in ["member_name", "event_name"]},
        "limit": limit,
        "result_count": len(result.get("data", []))
    })
    
    return success(result, f"AI query '{tool_name}' executed")

@router.post("/api/ai/calendar/query-batch")
def ai_query_batch(
    request_data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Execute multiple AI reference tool queries in a single iteration"""
    try:
        verify_ai_read_key(authorization)
    except HTTPException as e:
        logger.warning(f"AI query-batch access denied: {e.detail}")
        raise
    
    queries = request_data.get("queries", [])
    iteration = request_data.get("iteration", 1)
    
    # Validate number of queries
    if len(queries) > 3:
        logger.warning(f"AI query-batch: too many queries - {len(queries)}")
        raise HTTPException(status_code=400, detail="Maximum 3 queries per batch")
    
    logger.info(f"AI query-batch executing: iteration {iteration}, {len(queries)} queries")
    
    results = []
    for query in queries:
        tool_name = query.get("tool")
        filters = query.get("filters", {})
        limit = query.get("limit", 50)
        
        try:
            # Validate tool
            if tool_name not in ALLOWED_AI_TOOLS:
                results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": f"Tool '{tool_name}' not allowed"
                })
                continue
            
            tool_def = TOOL_DEFINITIONS[tool_name]
            
            # Validate limit
            if limit > tool_def["max_limit"]:
                results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": f"Limit exceeds maximum of {tool_def['max_limit']}"
                })
                continue
            
            # Validate filters
            for filter_key in filters.keys():
                if filter_key not in tool_def["allowed_filters"]:
                    results.append({
                        "tool": tool_name,
                        "success": False,
                        "error": f"Filter '{filter_key}' not allowed"
                    })
                    continue
            
            # Validate date range
            if tool_def["max_date_range_days"] and "start_date" in filters and "end_date" in filters:
                try:
                    start = date.fromisoformat(filters["start_date"])
                    end = date.fromisoformat(filters["end_date"])
                    if (end - start).days > tool_def["max_date_range_days"]:
                        results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": f"Date range exceeds maximum of {tool_def['max_date_range_days']} days"
                        })
                        continue
                except ValueError:
                    results.append({
                        "tool": tool_name,
                        "success": False,
                        "error": "Invalid date format"
                    })
                    continue
            
            # Execute tool
            result = execute_ai_tool(tool_name, filters, limit, db)
            results.append({
                "tool": tool_name,
                "success": True,
                "data": result
            })
            
        except Exception as e:
            logger.error(f"AI query-batch error for {tool_name}: {str(e)}")
            results.append({
                "tool": tool_name,
                "success": False,
                "error": str(e)
            })
    
    add_audit_log(db, "ai_query_batch", "system", None, request={
        "iteration": iteration,
        "query_count": len(queries),
        "success_count": sum(1 for r in results if r.get("success"))
    })
    
    return success({
        "iteration": iteration,
        "results": results
    }, f"AI query-batch executed: iteration {iteration}")

def execute_ai_tool(tool_name: str, filters: dict, limit: int, db: Session) -> dict:
    """Execute a specific AI tool"""
    if tool_name == "calendar_events_search":
        return tool_calendar_events_search(filters, limit, db)
    elif tool_name == "calendar_members_list":
        return tool_calendar_members_list(filters, limit, db)
    elif tool_name == "calendar_capacity_summary":
        return tool_calendar_capacity_summary(filters, limit, db)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

def tool_calendar_events_search(filters: dict, limit: int, db: Session) -> dict:
    """Search calendar events"""
    query = db.query(CalendarEvent).filter(CalendarEvent.is_archived == False)
    
    # Year/Month filter
    if "year" in filters and "month" in filters:
        year = filters["year"]
        month = filters["month"]
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        query = query.filter(CalendarEvent.event_date >= start_date, CalendarEvent.event_date <= end_date)
    
    # Date range filter
    if "start_date" in filters:
        query = query.filter(CalendarEvent.event_date >= date.fromisoformat(filters["start_date"]))
    if "end_date" in filters:
        query = query.filter(CalendarEvent.event_date <= date.fromisoformat(filters["end_date"]))
    
    # Member name filter
    if "member_name" in filters:
        member = db.query(CalendarMember).filter(
            CalendarMember.display_name == filters["member_name"],
            CalendarMember.is_active == True
        ).first()
        if member:
            query = query.filter(CalendarEvent.member_id == member.id)
    
    # Event name filter
    if "event_name" in filters:
        query = query.filter(CalendarEvent.title.ilike(f"%{filters['event_name']}%"))
    
    # Event type name filter
    if "event_type_name" in filters:
        event_type = db.query(CalendarEventType).filter(
            CalendarEventType.name == filters["event_type_name"],
            CalendarEventType.is_active == True
        ).first()
        if event_type:
            query = query.filter(CalendarEvent.event_type_id == event_type.id)
    
    # Source type filter
    if "source_type" in filters:
        query = query.filter(CalendarEvent.source_type == filters["source_type"])
    
    events = query.order_by(CalendarEvent.event_date.asc()).limit(limit).all()
    
    return {
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "member_name": e.member.display_name if e.member else None,
                "event_date": e.event_date.isoformat(),
                "event_type_name": e.event_type.name if e.event_type else None,
                "title": e.title,
                "display_label": e.display_label,
                "source_type": e.source_type
            }
            for e in events
        ]
    }

def tool_calendar_members_list(filters: dict, limit: int, db: Session) -> dict:
    """List calendar members"""
    query = db.query(CalendarMember)
    
    # Department name filter
    if "department_name" in filters:
        department = db.query(Department).filter(
            Department.name == filters["department_name"],
            Department.is_active == True
        ).first()
        if department:
            member_ids = db.query(CalendarMemberDepartment.member_id).filter(
                CalendarMemberDepartment.department_id == department.id
            ).all()
            member_ids = [m[0] for m in member_ids]
            if member_ids:
                query = query.filter(CalendarMember.id.in_(member_ids))
    
    # Active filter
    if "is_active" in filters:
        query = query.filter(CalendarMember.is_active == filters["is_active"])
    
    members = query.order_by(CalendarMember.display_order, CalendarMember.id).limit(limit).all()
    
    return {
        "count": len(members),
        "members": [
            {
                "id": m.id,
                "display_name": m.display_name,
                "short_name": m.short_name,
                "is_active": m.is_active
            }
            for m in members
        ]
    }

def tool_calendar_capacity_summary(filters: dict, limit: int, db: Session) -> dict:
    """Get capacity summary"""
    if "year" not in filters or "month" not in filters:
        raise HTTPException(status_code=400, detail="year and month are required")
    
    year = filters["year"]
    month = filters["month"]
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])
    
    # Get capacity rules
    rules = db.query(CalendarEventTypeCapacityRule).filter(
        CalendarEventTypeCapacityRule.is_active == True
    ).all()
    
    summary = []
    for rule in rules:
        # Filter by event type name if specified
        if "event_type_name" in filters:
            if rule.event_type.name != filters["event_type_name"]:
                continue
        
        # Check each day in the month
        daily_summary = []
        for day in range(1, monthrange(year, month)[1] + 1):
            current_date = date(year, month, day)
            
            # Get current count for this day
            current_count = db.query(CalendarEvent).filter(
                CalendarEvent.event_date == current_date,
                CalendarEvent.event_type_id == rule.event_type_id,
                CalendarEvent.is_archived == False
            ).count()
            
            daily_summary.append({
                "date": current_date.isoformat(),
                "required": rule.required_count,
                "current": current_count,
                "sufficient": current_count >= rule.required_count
            })
        
        summary.append({
            "event_type_name": rule.event_type.name,
            "department_name": rule.department.name if rule.department else None,
            "day_type": rule.day_type,
            "daily": daily_summary
        })
    
    return {
        "count": len(summary),
        "summaries": summary
    }
