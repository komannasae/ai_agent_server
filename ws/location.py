from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

connected_clients = {}  # user_id: {"ws": websocket, "team_id": team_id}


@router.websocket("/ws/location")
async def websocket_location(websocket: WebSocket):
    await websocket.accept()

    user_id = None

    try:
        while True:
            data = await websocket.receive_json()
            command = data.get("command")

            if command == "connect":
                user_id = data["user_id"]
                team_id = data["team_id"]           # 나중에 기능 추가용
                connected_clients[user_id] = {
                    "ws":      websocket,
                    "team_id": team_id
                }
                print(f"{user_id} connected (team: {team_id})")

            elif command == "update_location":
                if user_id is None:
                    await websocket.send_json({"error": "connect 먼저 보내세요"})
                    continue

                lat     = data["lat"]
                lng     = data["lng"]
                team_id = connected_clients[user_id]["team_id"]
                await _broadcast(user_id, team_id, lat, lng)

    except WebSocketDisconnect:
        print(f"{user_id} disconnected")

    finally:
        if user_id and user_id in connected_clients:
            del connected_clients[user_id]


async def _broadcast(user_id, team_id, lat, lng):
    message = {"command": "location_update", "user_id": user_id, "lat": lat, "lng": lng}

    disconnected = []
    for uid, client in connected_clients.items():
        if client["team_id"] == team_id:            # 나중에 팀 필터링 활성화
            try:
                await client["ws"].send_json(message)
            except Exception:
                disconnected.append(uid)

    for uid in disconnected:
        del connected_clients[uid]