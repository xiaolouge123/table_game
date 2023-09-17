from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import HTMLResponse
from typing import List, Dict, Union, Optional
from loguru import logger

from service.websocket_agent import WebSocketAgent
from service.utils import get_random
from prompts.history import Message, Action
from boards.board import Board, WereWolvesBoard, BoardState


app = FastAPI()


class WebSocketManager:
    def __init__(self) -> None:
        # holding for all active connections
        self.active_connections: List[WebSocketAgent] = []
        # holding for room assigned connections
        self.room_assigned_connections: Dict[str, List[WebSocketAgent]] = {}
        # holding for game board
        self.room_dict: Dict[str, Board] = {}

    async def connect(self, websocket: WebSocketAgent):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocketAgent, code=None):
        await self.remove_ws_agent(websocket)
        if code is not None:
            await websocket.close(code=code)
        await websocket.close()

    async def remove_ws_agent(self, websocket: WebSocketAgent):
        # TODO need more works to clean agent resource or delay clean
        self.active_connections.remove(websocket)

    async def broadcast(
        self,
        message: str,
        sender: Optional[Union[str, WebSocketAgent]] = None,
        receivers: List[WebSocketAgent] = None,
        room_id: str = None,
        **kwargs,
    ):
        """
        message: string message to be broadcasted
        sender: sender_id or sender instance
        receivers[Optional]: list of websocket clients to receive the message
        room_id[Optional]: room id to broadcast the message to
        """
        if room_id is not None and receivers is None:
            """
            given valid room id and no receivers provided, broadcast to all agents in the room
            """
            receivers = await self.get_agents(room_id)

        # braodcasting
        if isinstance(sender, WebSocketAgent):
            sender = sender.id
        act = Action(message, sender_id=sender)
        for receiver in receivers:
            await receiver.observe(act, **kwargs)

    async def assign_to_room(self, websocket: WebSocketAgent, room_id: str):
        """
        manager can be used to assign clients to rooms
        """
        if room_id not in self.room_assigned_connections:
            self.room_assigned_connections[room_id] = []
        self.room_assigned_connections[room_id].append(websocket)

    async def get_agents(self, room_id: str):
        return self.room_assigned_connections[room_id]


websocket_manager = WebSocketManager()


@app.websocket("/ws/{room_id}")
async def websocket_endpoint_game(websocket: WebSocket, room_id: str):
    """
    creating new ws connection

    """
    logger.info(f"Open Room: {room_id}")
    if room_id not in websocket_manager.room_dict:
        await websocket.close(code=status.WS_1007_INVALID_FRAME_PAYLOAD_DATA)
        return
    ws_agent = WebSocketAgent(websocket)
    logger.info(f"New Connection: {ws_agent.id}")
    await websocket_manager.connect(ws_agent)
    await websocket_manager.assign_to_room(ws_agent, room_id)
    board = websocket_manager.room_dict[room_id]
    logger.info(f"/ws/{room_id} Board type: {type(board)}")
    try:
        while True:
            if board.state == BoardState.INIT:
                """free talking before game start"""
                act = await ws_agent.act()
                logger.info(f"Receiving data: {act.text}")
                await websocket_manager.broadcast(
                    act.text, sender=ws_agent.id, room_id=room_id
                )
            else:
                """game start"""
                await board.start()

    except WebSocketDisconnect as wsd:
        logger.warning(f"Disconnect Error: {wsd}")
        await websocket_manager.remove_ws_agent(ws_agent)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        await ws_agent.send_text("An error occurred.")
        await websocket_manager.disconnect(ws_agent, code=status.WS_1011_INTERNAL_ERROR)


@app.get("/")
async def get():
    return HTMLResponse(enter_html)


@app.get("/{room_id}")
async def get(room_id: str):
    return HTMLResponse(room_html.replace("room_id_placeholder", room_id))


@app.post("/start/{room_id}")
async def start(room_id: str):
    """
    call to start the game, broadcasting the users' identity to themselves and so on
    """
    board = websocket_manager.room_dict[room_id]
    if board.state == BoardState.INIT:
        human_agents = await websocket_manager.get_agents(room_id)
        other_agents = WereWolvesBoard.create_agents(human_agents)
        board.register_agents(human_agents, other_agents)
        logger.info(f"Register agents: {board._register_agents}")
        board.state = BoardState.RUNNING
        await board.initializing()
        logger.info(f"Board state: {board.state}")
        return {"status": "success", "msg": "game started"}
    else:
        return {"status": "failed", "msg": f"board state is {board.state}"}


@app.post("/create-room/")
async def create_room():
    room_id = get_random()
    websocket_manager.room_dict[room_id] = WereWolvesBoard(
        manager=websocket_manager, id=room_id
    )
    logger.info(
        f"Create room: {room_id}, board type: {type(websocket_manager.room_dict[room_id])}"
    )
    return {"room_id": room_id}


@app.get("/get-rooms/")
async def get_room():
    logger.info(f"Current rooms: {list(websocket_manager.room_dict.keys())}")
    return {"room_list": list(websocket_manager.room_dict.keys())}


enter_html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body {
        font-family: 'Arial, sans-serif';
    }
    .room-list {
        margin-top: 20px;
    }
    .room-list ul {
        list-style-type: none;
        padding: 0;
    }
    .room-list li {
        margin: 5px 0;
    }
    .room-link {
        text-decoration: none;
        color: blue;
        cursor: pointer;
    }
</style>
<title>Create Room</title>
</head>
<body>

<button id="create-room-button">Create Room</button>

<div class="room-list">
    <ul id="room-list"></ul>
</div>

<script>
    const roomList = document.getElementById('room-list');
    const createRoomButton = document.getElementById('create-room-button');

    async function loadRoomList() {
        try {
            const response = await fetch('/get-rooms/', {
                method: 'GET',
            });
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            const data = await response.json();
            console.log(data);
            data.room_list.forEach((roomId) => {
                const roomLink = document.createElement('a');
                roomLink.textContent = `Room ${roomId}`;
                roomLink.href = `./${roomId}`;
                roomLink.classList.add('room-link');

                const roomListItem = document.createElement('li');
                roomListItem.appendChild(roomLink);
                roomList.appendChild(roomListItem);
            });
        } catch (error) {
            console.error('There was a problem with the fetch operation:', error);
        }
    }
    document.addEventListener('DOMContentLoaded', (event) => {
        loadRoomList();
    });

    createRoomButton.addEventListener('click', async () => {
        try {
            const response = await fetch('/create-room/', {
            method: 'POST',
            });
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            const data = await response.json();
            const roomId = data.room_id;

            const roomLink = document.createElement('a');
            roomLink.textContent = `Room ${roomId}`;
            roomLink.href = `./${roomId}`;
            roomLink.classList.add('room-link');

            console.log('Room created: ${roomId}');

            const roomListItem = document.createElement('li');
            roomListItem.appendChild(roomLink);
            roomList.appendChild(roomListItem);
        } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
    }

        
    });
</script>

</body>
</html>
"""

room_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body {
        font-family: 'Arial, sans-serif';
    }
    .chat-box {
        border: 1px solid #ccc;
        padding: 10px;
        height: 300px;
        overflow-y: scroll;
        margin-bottom: 10px;
    }
    .message-input {
        width: 100%;
        padding: 10px;
        box-sizing: border-box;
    }
    .start-button {
        padding: 10px;
        font-size: 16px;
        cursor: pointer;
    }
    .text-container {
        border: 1px solid #ccc;
        padding: 10px;
        margin: 10px;
        font-size: 16px;
        line-height: 1.5;
    }
</style>
<title>Room room_id_placeholder</title>
</head>
<body>

<div class="chat-box" id="chat-box"></div>
<div class="text-container" id="text-container"></div>
<input type="text" class="message-input" id="message-input" placeholder="Type your message here...">
<button class="start-button" id="start-button">Game Start</button>

<script>
    const chatBox = document.getElementById('chat-box');
    const messageInput = document.getElementById('message-input');
    const startButton = document.getElementById('start-button');
    const textContainer = document.getElementById('text-container');

    const room_id = 'room_id_placeholder';
    const ws = new WebSocket('ws://localhost:8000/ws/room_id_placeholder');  // Replace 'room_id_placeholder' with your room ID
    
    let agent_id;

    ws.addEventListener('open', () => {
        chatBox.innerHTML += '<div>Connected</div>';
    });

    ws.addEventListener('message', (event, agent_id) => {
        console.log(event.data)
        let data;
        
        try {
            data = JSON.parse(event.data);
        } catch (error) {
            data = { text: event.data };
        };

        if (data.hasOwnProperty('text') && data.text!='' && !data.hasOwnProperty('sender_id')) {
            chatBox.innerHTML += '<div>' + 'Player ' + data.agent_id + ' : ' + data.text + '</div>';
        } else if (data.hasOwnProperty('text') && data.text!='' && data.hasOwnProperty('sender_id')) {
            chatBox.innerHTML += '<div>' + 'Player ' + data.sender_id + ' : ' + data.text + '</div>';
        } else if (data.hasOwnProperty('agent_id')){
            chatBox.innerHTML += '<div>' + 'Player ' + data.agent_id + ' online.' + '</div>';
        };

        if (!data.hasOwnProperty('next_speaker_id')) {
            messageInput.disabled = false;
            textContainer.innerText = 'Game not starts, free talks.';
        } else if (!data.hasOwnProperty('next_speaker_id') && data.text!==''){
            messageInput.disabled = false;
            textContainer.innerText = 'Game not starts, free talks.';
        } else if (data.hasOwnProperty('next_speaker_id') && data.next_speaker_id === agent_id) {
            messageInput.disabled = false;
            textContainer.innerText = 'Your turn, please speak.';
        } else {
            messageInput.disabled = true;
            textContainer.innerText = 'Not your turn, please wait.';
        };

        chatBox.scrollTop = chatBox.scrollHeight;  // Scroll to show the latest message
    });

    ws.addEventListener('close', () => {
        chatBox.innerHTML += '<div>Role Disconnected</div>';
    });

    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && messageInput.value.trim() !== '') {
            ws.send(messageInput.value);
            messageInput.value = '';
        }
    });

    startButton.addEventListener('click', async () => {
        await fetch(`/start/${room_id}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            console.log(data);
            ws.send('Game Started');
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });
</script>

</body>
</html>
"""
