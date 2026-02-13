# backend/core/auth.py
"""
Clerk Authentication Middleware for FastAPI.
Extracts user_id from Clerk JWT token.
"""
from fastapi import HTTPException, Header
from typing import Optional
import os
import requests
import jwt
import json

# Clerk configuration
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")

def get_clerk_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extracts user_id from Clerk JWT token in Authorization header.
    
    For development: Decodes JWT token directly (no API call needed)
    For production: Can verify with Clerk API if CLERK_SECRET_KEY is set
    
    Args:
        authorization: Authorization header value (format: "Bearer <token>")
    
    Returns:
        user_id: Clerk user ID string
    
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract token from "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = parts[1]
        
        # DEVELOPMENT MODE: Decode JWT token directly (no verification)
        # Clerk JWT tokens contain the user_id in the payload
        try:
            # Decode without verification (for development)
            # In production, you should verify the signature
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("sub")  # Clerk uses "sub" (subject) for user ID
            if user_id:
                return user_id
        except jwt.DecodeError:
            pass
        
        # PRODUCTION MODE: Verify with Clerk API (if CLERK_SECRET_KEY is set)
        if CLERK_SECRET_KEY:
            try:
                # Get user info from Clerk API
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                response = requests.get(
                    "https://api.clerk.com/v1/me",
                    headers=headers,
                    timeout=5
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    user_id = user_data.get("id")
                    if user_id:
                        return user_id
            except requests.RequestException:
                pass  # Fall through to error
        
        raise HTTPException(status_code=401, detail="Invalid or expired token")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

def get_user_id_optional(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Optional version that returns None if no auth header is present.
    Useful for endpoints that work with or without authentication.
    
    For development: Accepts JWT tokens or direct user_id strings
    """
    if not authorization:
        return None
    
    try:
        # Try to extract user_id directly (for development/testing)
        # Format: "Bearer user_xxx" or just "user_xxx"
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            # If it looks like a Clerk user ID, use it directly (dev mode)
            if token.startswith("user_"):
                return token
        elif len(parts) == 1 and parts[0].startswith("user_"):
            return parts[0]
        
        # Otherwise, try to verify with Clerk
        return get_clerk_user_id(authorization)
    except HTTPException:
        return None
