from datetime import datetime

def success_response(data: dict = None, message: str = "Success") -> dict:
    """Standardized success response format"""
    return {
        "success": True,
        "data": data if data is not None else {},
        "message": message,
        "timestamp": datetime.now().isoformat()
    }

def error_response(error_code: str, message: str, details: str = None) -> dict:
    """Standardized error response format"""
    return {
        "success": False,
        "error_code": error_code,
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
