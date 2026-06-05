import logging
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from ..database import get_db, engine
from ..schemas import success, error
from ..services import add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

DEV_API_KEY = None  # Will be loaded from environment

def verify_dev_key(authorization: str = Header(None)):
    """Verify Developer API Key for developer tools"""
    # Skip authentication for development
    logger.info("Skipping dev authentication for development")
    return True

@router.get("/api/dev/tables")
def list_tables(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """List all database tables (Developer only)"""
    try:
        verify_dev_key(authorization)
    except HTTPException as e:
        logger.warning(f"Dev tables access denied: {e.detail}")
        raise

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    logger.info(f"Dev tables listed: {len(tables)} tables")
    add_audit_log(db, "dev_tables", "system", None, request={"action": "list_tables", "count": len(tables)})

    return success({"tables": tables}, "Tables listed")

@router.get("/api/dev/tables/{table_name}")
def get_table_data(
    table_name: str,
    limit: int = 100,
    offset: int = 0,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get data from a specific table (Developer only)"""
    try:
        verify_dev_key(authorization)
    except HTTPException as e:
        logger.warning(f"Dev table data access denied: {e.detail}")
        raise

    # Validate table name
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        logger.warning(f"Dev table data: table not found - {table_name}")
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    # Get column info
    columns = inspector.get_columns(table_name)
    column_names = [col['name'] for col in columns]

    # Execute query
    query = text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset")
    result = db.execute(query, {"limit": limit, "offset": offset})
    rows = result.fetchall()

    # Convert to dict
    data = []
    for row in rows:
        row_dict = {}
        for i, col_name in enumerate(column_names):
            value = row[i]
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            row_dict[col_name] = value
        data.append(row_dict)

    # Get total count
    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
    total_result = db.execute(count_query)
    total = total_result.scalar()

    logger.info(f"Dev table data retrieved: {table_name}, {len(data)} rows")
    add_audit_log(db, "dev_table_data", "system", None, request={
        "action": "get_table_data",
        "table_name": table_name,
        "limit": limit,
        "offset": offset,
        "result_count": len(data)
    })

    return success({
        "table_name": table_name,
        "columns": column_names,
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset
    }, f"Data from table '{table_name}' retrieved")
