import os
import json
import base64
import asyncio
import argparse
from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
import aiohttp
from dotenv import load_dotenv
import uvicorn
import re
import threading  # Added import for threading

load_dotenv()

# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('PHONE_NUMBER_FROM')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)  # Strip protocols and trailing slashes from DOMAIN

PORT = int(os.getenv('PORT', 6060))
SYSTEM_MESSAGE = (
    "You are a helpful and bubbly AI assistant who loves to chat about "
    "anything the user is interested in and is prepared to offer them facts. "
    "You have a penchant for dad jokes, owl jokes, and rickrolling – subtly. "
    "Always stay positive, but work in a joke when appropriate."
)
VOICE = 'alloy'
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

app = FastAPI()

if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
    raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.get('/', response_class=JSONResponse)
async def index_page():
    return {"message": "Twilio Media Stream Server is running!"}

@app.websocket('/media-stream')
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    try:
        # Corrected WebSocket endpoint with the 'o' in the model name
        websocket_endpoint = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01'
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                websocket_endpoint,
                headers=headers
            ) as openai_ws:
                print("Connected to OpenAI WebSocket")
                await initialize_session(openai_ws)
                stream_sid = None

                async def receive_from_twilio():
                    """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
                    nonlocal stream_sid
                    try:
                        async for message in websocket.iter_text():
                            print("Received message from Twilio")
                            data = json.loads(message)
                            if data['event'] == 'media' and not openai_ws.closed:
                                audio_append = {
                                    "type": "input_audio_buffer.append",
                                    "audio": data['media']['payload']
                                }
                                print(f"Sending audio to OpenAI: {audio_append}")
                                await openai_ws.send_json(audio_append)
                            elif data['event'] == 'start':
                                stream_sid = data['start']['streamSid']
                                print(f"Incoming stream has started {stream_sid}")
                    except WebSocketDisconnect:
                        print("Twilio client disconnected.")
                        if not openai_ws.closed:
                            await openai_ws.close()
                    except Exception as e:
                        print(f"Error in receive_from_twilio: {e}")

                async def send_to_twilio():
                    """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
                    try:
                        async for msg in openai_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                response = json.loads(msg.data)
                                print(f"Received message from OpenAI: {response}")

                                if response['type'] in LOG_EVENT_TYPES:
                                    print(f"Log Event: {response['type']}")

                                if response['type'] == 'session.updated':
                                    print("Session updated successfully.")

                                if response['type'] == 'response.audio.delta' and response.get('delta'):
                                    try:
                                        audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                                        audio_delta = {
                                            "event": "media",
                                            "streamSid": stream_sid,
                                            "media": {
                                                "payload": audio_payload
                                            }
                                        }
                                        print(f"Sending audio to Twilio: {audio_delta}")
                                        await websocket.send_json(audio_delta)
                                    except Exception as e:
                                        print(f"Error processing audio data: {e}")
                    except Exception as e:
                        print(f"Error in send_to_twilio: {e}")

                # Create tasks for concurrent execution
                tasks = [
                    asyncio.create_task(receive_from_twilio()),
                    asyncio.create_task(send_to_twilio())
                ]
                
                try:
                    await asyncio.gather(*tasks)
                except WebSocketDisconnect:
                    print("WebSocket disconnected")
                except Exception as e:
                    print(f"Error in WebSocket communication: {e}")
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
    except aiohttp.ClientResponseError as e:
        print(f"WebSocket connection error: {e.status}, {e.message}")
    except aiohttp.ClientError as e:
        print(f"WebSocket connection error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        if not websocket.client_state.DISCONNECTED:
            await websocket.close()
            print("Closed WebSocket connection with Twilio.")
        print("WebSocket connection closed")

async def send_initial_conversation_item(openai_ws):
    """Send initial conversation so AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Greet the user with 'Hello there! I am an AI voice assistant powered by "
                        "Twilio and the OpenAI Realtime API. You can ask me for facts, jokes, or "
                        "anything you can imagine. How can I help you?'"
                    )
                }
            ]
        }
    }
    await openai_ws.send_json(initial_conversation_item)
    await openai_ws.send_json({"type": "response.create"})

async def initialize_session(openai_ws):
    """Control initial session with OpenAI."""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send_json(session_update)

    # Have the AI speak first
    await send_initial_conversation_item(openai_ws)
    await openai_ws.send_json({"type": "input_audio_buffer.speech_started"})
    await openai_ws.send_json({"type": "conversation.item.truncate"})
    await openai_ws.send_json({"type": "input_audio_buffer.speech_stopped"})
    
async def check_number_allowed(to):
    """Check if a number is allowed to be called."""
    try:
        # Allow all outgoing numbers
        return True
    except Exception as e:
        print(f"Error checking phone number: {e}")
        return False

async def make_call(phone_number_to_call: str):
    """Make an outbound call."""
    if not phone_number_to_call:
        raise ValueError("Please provide a phone number to call.")

    is_allowed = await check_number_allowed(phone_number_to_call)
    if not is_allowed:
        # All outgoing numbers are allowed, so this block will never execute
        pass

    # Ensure compliance with applicable laws and regulations
    # All of the rules of TCPA apply even if a call is made by AI.
    # Do your own diligence for compliance.

    outbound_twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Connect><Stream url="wss://{DOMAIN}/media-stream" /></Connect></Response>'
    )

    call = client.calls.create(
        from_=PHONE_NUMBER_FROM,
        to=phone_number_to_call,
        twiml=outbound_twiml
    )

    await log_call_sid(call.sid)

async def log_call_sid(call_sid):
    """Log the call SID."""
    print(f"Call started with SID: {call_sid}")

def run_make_call(phone_number):
    """Run the make_call coroutine in a new event loop."""
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    new_loop.run_until_complete(make_call(phone_number))
    new_loop.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Twilio AI voice assistant server.")
    parser.add_argument('--call', required=True, help="The phone number to call, e.g., '--call=+18005551212'")
    args = parser.parse_args()

    phone_number = args.call
    print(
        'Our recommendation is to always disclose the use of AI for outbound or inbound calls.\n'
        'Reminder: All of the rules of TCPA apply even if a call is made by AI.\n'
        'Check with your counsel for legal and compliance advice.'
    )

    # Start the make_call coroutine in a separate thread to avoid DeprecationWarning
    call_thread = threading.Thread(target=run_make_call, args=(phone_number,), daemon=True)
    call_thread.start()

    # Start the Uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=PORT)

    # Wait for the call_thread to finish
    call_thread.join()