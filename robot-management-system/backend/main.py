from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx
import asyncio

import models
from database import engine, get_db, Base
from robot_client import RobotClient

# .INITIALIZE DATABASE 
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ground Control Station API")

# CORS SECURITY MIDDLEWARE 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

robot = RobotClient()


class MoveCommand(BaseModel):
    x: int
    y: int
    user: str = "Commander"


@app.get("/")
async def root():
    return {"message": "Ground Control Station is running!"}

@app.get("/check-robot")
async def check_robot_status():
    try:
        data = await robot.get_status()
        return {"status": "success", "robot_data": data}
    except Exception as e:
        return {"status": "error", "message": f"Robot unreachable: {e}"}

@app.post("/command/move")
async def send_move_command(command: MoveCommand, db: Session = Depends(get_db)):
    """Logs movement and sends command to robot."""
    #  Audit Trail
    new_log = models.AuditLog(
        user_role=command.user,
        command_type="MOVE_CMD",
        details=f"Target: ({command.x}, {command.y})"
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    #  Dispatch command to the Docker robot simulation
    try:
        result = await robot.move_robot(command.x, command.y)
        return {"status": "success", "log_id": new_log.id, "robot_response": result}
    except Exception as e:
        # Log failure to audit log for system diagnosis
        error_log = models.AuditLog(
            user_role="System",
            command_type="ERROR",
            details=f"Move failed: {str(e)}"
        )
        db.add(error_log)
        db.commit()
        raise HTTPException(status_code=503, detail=str(e))

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """Streams robot data to the frontend dashboard in real-time."""
    await websocket.accept()
    try:
        while True:
            try:
                stats = await robot.get_status()
                await websocket.send_json(stats)
            except Exception:
                await websocket.send_json({"error": "Robot connection noisy..."})
            
            # Broadcast telemetry updates 
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Frontend client disconnected from telemetry stream.")