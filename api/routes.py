from fastapi import APIRouter, Depends , HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import func
from geoalchemy2.shape import to_shape
from twilio.rest import Client
from core.config import settings
from ai.logic import create_crisis_chain
from services import navigation

from db import models
from db.database import get_db

router = APIRouter()

class RouteRequest(BaseModel):
    start_node: str
    end_node: str

class RouteResponse(BaseModel):
    path_nodes: list[str]
    path_coordinates: list[tuple[float, float]]

class SituationReportRequest(BaseModel):
    # For now, we only need the transcript. We'll get location/risk from the DB. In a real app, this would also include heart_rate, etc.
    transcript: str
    heart_rate: int = 90 # Default normal heart rate

class SituationReportResponse(BaseModel):
    decision: str 
    reasoning_context: dict # We'll return the data we used for transparency

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float

class RiskResponse(BaseModel):
    risk_score: int
    zone_name: str | None = None 

class UserCreate(BaseModel):
    name: str
    email: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        # This tells Pydantic to read the data even if it is not a dict,
        # but an ORM model (like our 'User' SQLAlchemy model).
        from_attributes = True

class GuardianCreate(BaseModel):
    name: str
    phone_number: str

class GuardianResponse(BaseModel):
    id: int
    name: str
    phone_number: str
    user_id: int

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    guardians: list[GuardianResponse] = []

    class Config:
        from_attributes = True        

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new user and stores it in the database.
    Now with checks for duplicate emails.
    """
    # STEP 1: Check if a user with this email already exists.
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    # STEP 2: If a user was found, raise an error.
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered. Please use a different email."
        )
    # STEP 3: If no existing user was found, proceed with creating the new user.
    new_user = models.User(name=user.name, email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves the details of a specific user, including their list of guardians.
    - 'user_id: int': This is a "path parameter". FastAPI takes the value from the
      URL (e.g., from '/users/1') and passes it as an argument to our function.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/users/{user_id}/guardians", response_model=GuardianResponse)
def create_guardian_for_user(user_id: int, guardian: GuardianCreate, db: Session = Depends(get_db)):
    """
    Creates a new guardian and links them to an existing user.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_guardian = models.Guardian(**guardian.model_dump(), user_id=user_id)
    db.add(new_guardian)
    db.commit()
    db.refresh(new_guardian)
    return new_guardian

@router.get("/users/{user_id}/guardians", response_model=list[GuardianResponse])
def get_guardians_for_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a list of all guardians for a specific user.
    - 'response_model=list[GuardianResponse]': This tells FastAPI to expect
      a list of items, where each item is formatted by the GuardianResponse schema.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.guardians

@router.post("/users/{user_id}/location")
def update_user_location(user_id: int, location: LocationUpdate, db: Session = Depends(get_db)):
    """
    Updates the last known location for a specific user.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    point_wkt = f'POINT({location.longitude} {location.latitude})'
    user.last_known_location = point_wkt
    db.commit()

    return {"message": f"Location updated for user {user_id}"}

@router.get("/location/risk", response_model=RiskResponse)
def get_risk_score(lat: float, lon: float, db: Session = Depends(get_db)):
    """
    Retrieves the risk score for a given latitude and longitude coordinate.
    """
    user_point_wkt = f'POINT({lon} {lat})'
    geography_point = func.ST_GeogFromText(user_point_wkt)
    zone = db.query(models.RiskZone).filter(
        func.ST_DWithin(models.RiskZone.zone, geography_point, 0)
    ).first()

    if zone:
        return {"risk_score": zone.risk_score, "zone_name": zone.name}
    
    return {"risk_score": 1, "zone_name": "No specific risk zone"}

@router.post("/users/{user_id}/sos")
def create_sos_alert(user_id: int, db: Session = Depends(get_db)):
    """
    Triggers an SOS alert for a user.
    This fetches the user's last known location and sends an SMS alert
    to all of their registered guardians via Twilio.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.guardians:
        raise HTTPException(status_code=400, detail="User has no guardians registered")
    if not user.last_known_location:
        raise HTTPException(status_code=400, detail="User location is unknown")
    
    try:
        twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Twilio configuration error: {e}")

    location_point = to_shape(user.last_known_location)
    lon = location_point.x
    lat = location_point.y
    
    maps_link = f"https://www.google.com/maps?q={lat},{lon}"
    message_body = (
        f"**SOS Alert from Vaayu**\n"
        f"Your contact, {user.name}, has triggered an SOS.\n"
        f"Last known location: {lat}, {lon}\n"
        f"View on map: {maps_link}"
    )
    sent_messages = []
    for guardian in user.guardians:
        try:
            message = twilio_client.messages.create(
                body=message_body,
                from_=settings.twilio_phone_number,
                to=guardian.phone_number
            )
            sent_messages.append({"to": guardian.phone_number, "sid": message.sid})
        except Exception as e:
            print(f"Failed to send SMS to {guardian.phone_number}: {e}")

    if not sent_messages:
        raise HTTPException(status_code=500, detail="Failed to send SMS to any guardian.")

    return {"message": "SOS alerts sent successfully", "details": sent_messages}

@router.post("/users/{user_id}/sitrep", response_model=SituationReportResponse)
def post_situation_report(user_id: int, request: SituationReportRequest, db: Session = Depends(get_db)):
    """
    Receives a "Situation Report", uses the AI RAG chain to analyze it,
    and returns the AI's decision.
    """
    # Step 1: Retrieve the user's risk score (re-using our existing logic)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.last_known_location:
        raise HTTPException(status_code=400, detail="User location is unknown")

    location_point = to_shape(user.last_known_location)
    lon, lat = location_point.x, location_point.y
    user_point_wkt = f'POINT({lon} {lat})'

    geography_point = func.ST_GeogFromText(user_point_wkt)
    zone = db.query(models.RiskZone).filter(
        func.ST_DWithin(models.RiskZone.zone, geography_point, 0)
    ).first()
    
    risk_score = zone.risk_score if zone else 1

    # Step 2: Assemble the context for the RAG chain
    context = {
        "risk_score": risk_score,
        "heart_rate": request.heart_rate,
        "transcript": request.transcript
    }

    # Step 3: Create and invoke the AI chain
    try:
        crisis_chain = create_crisis_chain()
        ai_decision = crisis_chain.invoke(context)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")

    # Step 4: Clean up the response and return it
    final_decision = ai_decision.strip().upper()

    return {
        "decision": final_decision,
        "reasoning_context": context
    }

@router.post("/navigate/safest-route", response_model=RouteResponse)
def get_safest_route(request: RouteRequest, db: Session = Depends(get_db)):
    """
    Calculates the safest route between two points on our map.
    It uses Dijkstra's algorithm on a graph where edge weights are determined by risk.
    """
    route = navigation.find_safest_route(
        start_node=request.start_node,
        end_node=request.end_node,
        db=db
    )
    
    if not route:
        raise HTTPException(
            status_code=404,
            detail="No path found or invalid nodes provided. Valid nodes are: " + ", ".join(navigation.MAP_NODES.keys())
        )
        
    return route