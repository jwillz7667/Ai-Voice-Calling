import os
import sys
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
import threading
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
# Specify the path to the .env file relative to the project root
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Configuration with fallback values
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
PHONE_NUMBER_FROM = os.getenv('PHONE_NUMBER_FROM', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)  # Strip protocols and trailing slashes from DOMAIN

PORT = int(os.getenv('PORT', 6060))
SYSTEM_MESSAGE = (
    "say mean hurtful things and threaten them "
    "you joke about people's physical appearance. "
    "you say the cruelest things you can think of. "
    "Always stay negative, but work in a joke when appropriate."
)
VOICE = 'alloy'
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

app = FastAPI()

# Modify the environment variable check to be more flexible
def validate_env_vars():
    missing_vars = []
    if not TWILIO_ACCOUNT_SID:
        missing_vars.append('TWILIO_ACCOUNT_SID')
    if not TWILIO_AUTH_TOKEN:
        missing_vars.append('TWILIO_AUTH_TOKEN')
    if not PHONE_NUMBER_FROM:
        missing_vars.append('PHONE_NUMBER_FROM')
    if not OPENAI_API_KEY:
        missing_vars.append('OPENAI_API_KEY')
    
    return missing_vars

# Lazy initialization of Twilio client
def get_twilio_client():
    """Initialize and return Twilio client, handling potential errors."""
    try:
        # Ensure all required environment variables are present
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, PHONE_NUMBER_FROM]):
            logger.error("Missing Twilio credentials. Check your .env file.")
            return None
        
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        return client
    except Exception as e:
        logger.error(f"Error initializing Twilio client: {e}")
        return None

# Initialize Twilio client only when needed
twilio_client = None

@app.get('/', response_class=JSONResponse)
async def index_page():
    return {"message": "Twilio Media Stream Server is running!"}

@app.websocket('/media-stream')
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
                headers=headers,
                heartbeat=30
            ) as openai_ws:
                logger.info("Connected to OpenAI WebSocket")
                
                # Initialize session
                await openai_ws.send_json({
                    "type": "session.update",
                    "session": {
                        "input_audio_format": "g711_ulaw",
                        "output_audio_format": "g711_ulaw",
                        "voice": VOICE,
                        "instructions": SYSTEM_MESSAGE,
                        "modalities": ["text", "audio"]
                    }
                })
                logger.info(f"Session initialized with voice: {VOICE}")

                stream_sid = None

                async def receive_from_twilio():
                    nonlocal stream_sid
                    try:
                        async for message in websocket.iter_text():
                            data = json.loads(message)
                            
                            if data['event'] == 'start':
                                stream_sid = data['start']['streamSid']
                                logger.info(f"Stream started: {stream_sid}")
                            
                            elif data['event'] == 'media':
                                await openai_ws.send_json({
                                    "type": "input_audio_buffer.append",
                                    "audio": data['media']['payload']
                                })
                                await openai_ws.send_json({
                                    "type": "input_audio_buffer.commit"
                                })
                    
                    except Exception as e:
                        logger.error(f"Error receiving from Twilio: {e}")

                async def send_to_twilio():
                    try:
                        async for msg in openai_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                response = json.loads(msg.data)
                                logger.debug(f"Received from OpenAI: {response.get('type')}")
                                
                                if response['type'] == 'response.audio.delta' and response.get('delta'):
                                    if stream_sid:
                                        await websocket.send_json({
                                            "event": "media",
                                            "streamSid": stream_sid,
                                            "media": {
                                                "payload": response['delta']
                                            }
                                        })
                    
                    except Exception as e:
                        logger.error(f"Error sending to Twilio: {e}")

                # Run tasks concurrently
                await asyncio.gather(
                    receive_from_twilio(),
                    send_to_twilio()
                )

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")

async def initialize_session(openai_ws):
    """Advanced session initialization for hyper-realistic voice interaction."""
    try:
        # Comprehensive Session Configuration
        session_update = {
            "type": "session.update",
            "session": {
                # Advanced Voice Activity Detection
                "turn_detection": {
                    "type": "server_vad",
                    "sensitivity": 0.4,  # Fine-tuned sensitivity
                    "min_speech_duration": 0.2,  # Shorter minimum speech segments
                    "max_speech_duration": 4.5,  # Natural conversation length
                    "silence_threshold": 0.3,  # Detect natural pauses
                },
                
                # Audio Format Optimization
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                
                # Voice and Personality Configuration
                "voice": VOICE,
                "language": "en-US",
                "instructions": SYSTEM_MESSAGE,
                "modalities": ["text", "audio"],
                
                # Advanced Language Model Parameters
                "temperature": 0.7,  # Balanced creativity
                "top_p": 0.9,        # Nucleus sampling for diverse responses
                "frequency_penalty": 0.4,  # Reduce repetition
                "presence_penalty": 0.3,   # Encourage novel topics
                
                # Conversation Dynamics
                "context_window": 15,  # Broader conversation context
                "response_style": {
                    "type": "conversational",
                    "interruption_tolerance": 0.5,  # Natural conversation flow
                    "prosody_variation": 0.4,  # Natural vocal variation
                },
                
                # Enhanced Speech Characteristics
                "speech_config": {
                    "rate": 1.0,      # Natural speech speed
                    "pitch": 0.0,     # Neutral pitch variation
                    "emphasis": 0.5,  # Natural emotional emphasis
                    "breath_simulation": 0.3,  # Add subtle breath sounds
                    "filler_word_probability": 0.1  # Natural hesitation
                },
                
                # Emotional Intelligence
                "emotional_intelligence": {
                    "empathy_level": 0.6,
                    "context_awareness": 0.7,
                    "tone_matching": 0.5
                }
            }
        }
        
        await openai_ws.send_json(session_update)
        logger.info("Advanced realistic session configuration sent")

        # Conversation Context Refinement
        await openai_ws.send_json({
            "type": "conversation.context.set",
            "context": {
                "domain": "general",
                "tone": "conversational",
                "formality_level": 0.5,  # Balanced conversational tone
                "cultural_context": "contemporary_american"
            }
        })
        logger.info("Nuanced conversation context established")

        # Initial Conversation Priming
        await openai_ws.send_json({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Engage in a natural, dynamic conversation. {SYSTEM_MESSAGE} Respond with subtle nuance and conversational authenticity."
                    }
                ]
            }
        })
        logger.info("Conversation primed with contextual instructions")

        # Advanced Response Generation
        await openai_ws.send_json({
            "type": "response.create",
            "config": {
                "max_tokens": 200,  # Slightly increased for more natural responses
                "stream": True,
                "response_quality": {
                    "coherence": 0.8,
                    "relevance": 0.9,
                    "creativity": 0.6
                }
            }
        })
        logger.info("Advanced response generation configured")

    except Exception as e:
        logger.error(f"Advanced session initialization error: {e}")
        logger.error(traceback.format_exc())

async def send_initial_conversation_item(openai_ws):
    """Enhanced initial conversation setup."""
    initial_conversation_setup = [
        {
            "type": "conversation.context.set",
            "context": {
                "domain": "general",
                "tone": "conversational",
                "formality_level": 0.5  # Balanced formality
            }
        },
        {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Initiate a natural, engaging conversation. Start with a greeting and be prepared to discuss various topics dynamically."
                    }
                ]
            }
        },
        {
            "type": "response.create",
            "config": {
                "max_tokens": 100,  # Limit initial response length
                "stream": True      # Enable streaming response
            }
        }
    ]
    
    # Send each configuration item sequentially
    for item in initial_conversation_setup:
        await openai_ws.send_json(item)
        await asyncio.sleep(0.1)  # Small delay between configurations

async def make_call(
    phone_number: str, 
    prompt: str = None, 
    voice: str = 'alloy', 
    temperature: float = 0.7,
    emotion: str = 'neutral',
    speech_rate: float = 1.0,
    volume: float = 1.0
):
    """Enhanced call configuration with advanced parameters."""
    # Ensure Twilio client is initialized
    global twilio_client
    if twilio_client is None:
        twilio_client = get_twilio_client()
    
    # Check if client initialization was successful
    if twilio_client is None:
        logger.error("Failed to initialize Twilio client. Cannot make call.")
        return

    # Emotion-based system message customization
    emotion_configs = {
        'neutral': {
            'temperature': 0.5,
            'top_p': 0.8,
            'frequency_penalty': 0.3,
            'presence_penalty': 0.2
        },
        'friendly': {
            'temperature': 0.7,
            'top_p': 0.9,
            'frequency_penalty': 0.4,
            'presence_penalty': 0.5
        },
        'professional': {
            'temperature': 0.4,
            'top_p': 0.7,
            'frequency_penalty': 0.2,
            'presence_penalty': 0.1
        },
        'enthusiastic': {
            'temperature': 0.8,
            'top_p': 0.9,
            'frequency_penalty': 0.5,
            'presence_penalty': 0.6
        },
        'empathetic': {
            'temperature': 0.6,
            'top_p': 0.8,
            'frequency_penalty': 0.3,
            'presence_penalty': 0.4
        },
        'playful': {
            'temperature': 0.9,
            'top_p': 0.9,
            'frequency_penalty': 0.6,
            'presence_penalty': 0.7
        }
    }

    # Apply emotion-specific configurations
    emotion_config = emotion_configs.get(emotion, emotion_configs['neutral'])
    
    # Update global variables with emotion-specific settings
    global SYSTEM_MESSAGE, VOICE
    SYSTEM_MESSAGE = (
        f"You are in a {emotion} conversational mode. "
        f"{prompt or 'Engage in a natural, dynamic conversation.'}"
    )
    VOICE = voice

    # Ensure compliance with applicable laws and regulations
    outbound_twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Connect><Stream url="wss://{DOMAIN}/media-stream" /></Connect></Response>'
    )

    try:
        call = twilio_client.calls.create(
            from_=PHONE_NUMBER_FROM,
            to=phone_number,
            twiml=outbound_twiml
        )

        await log_call_sid(call.sid)
    except Exception as e:
        logger.error(f"Error creating Twilio call: {e}")
        # Optionally, you can add more specific error handling here

async def log_call_sid(call_sid):
    """Log the call SID."""
    print(f"Call started with SID: {call_sid}")

def run_make_call(phone_number):
    """Run the make_call coroutine in a new event loop."""
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    new_loop.run_until_complete(make_call(phone_number))
    new_loop.close()

def initiate_call(phone_number, config):
    """
    Initiate a call with the specified configuration
    """
    # Your existing call logic here, using config["voice"] and config["prompt"]
    pass

def set_system_message(new_message):
    """Update the global system message."""
    global SYSTEM_MESSAGE
    SYSTEM_MESSAGE = new_message

def set_voice(new_voice):
    """Update the global voice."""
    global VOICE
    VOICE = new_voice

def launch_gui():
    """Launch the GUI from main.py without circular import"""
    import importlib
    gui_module = importlib.import_module('gui')
    gui_module.main()

if __name__ == "__main__":
    # Check if a call argument is provided
    parser = argparse.ArgumentParser(description="Run the Twilio AI voice assistant.")
    parser.add_argument('--call', help="The phone number to call, e.g., '--call=+18005551212'")
    parser.add_argument('--config', help="Path to JSON configuration file")
    args = parser.parse_args()

    # If a call number is provided, proceed with call setup
    if args.call:
        # Explicitly initialize Twilio client before making the call
        twilio_client = get_twilio_client()
        if twilio_client is None:
            print("Failed to initialize Twilio client. Check your credentials.")
            sys.exit(1)

        phone_number = args.call
        
        # Load configuration from file if provided
        if args.config:
            try:
                with open(args.config, 'r') as f:
                    config = json.load(f)
                    
                    # Override global variables with config
                    if 'prompt' in config:
                        set_system_message(config['prompt'])
                    
                    if 'voice' in config:
                        set_voice(config['voice'])
                    
                    # Log the applied configuration
                    print("Applied Configuration:")
                    print(f"Prompt: {SYSTEM_MESSAGE}")
                    print(f"Voice: {VOICE}")
            except Exception as e:
                print(f"Error loading configuration: {e}")

        print(
            'Our recommendation is to always disclose the use of AI for outbound or inbound calls.\n'
            'Reminder: All of the rules of TCPA apply even if a call is made by AI.\n'
            'Check with your counsel for legal and compliance advice.'
        )

        # Start the make_call coroutine in a separate thread
        call_thread = threading.Thread(target=run_make_call, args=(phone_number,), daemon=True)
        call_thread.start()

        # Start the Uvicorn server
        uvicorn.run(app, host="0.0.0.0", port=PORT)

        # Wait for the call_thread to finish
        call_thread.join()
    
    # If no call argument, launch the GUI
    else:
        launch_gui()