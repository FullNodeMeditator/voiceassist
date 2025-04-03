# Voice Assistant

A Python-based voice assistant application built with Kivy, featuring wake word detection, speech recognition, and natural language processing.

## Features

- Wake word detection using Porcupine
- Speech recognition using Google's Speech Recognition API
- Text-to-speech using gTTS
- Natural language processing using OpenAI's GPT models
- Modern GUI built with Kivy
- Conversation history tracking
- Configurable voice settings

## Requirements

- Python 3.10+
- PyAudio
- SpeechRecognition
- OpenAI
- Kivy
- Pygame
- gTTS
- pvporcupine

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd voiceassist
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
export PORCUPINE_ACCESS_KEY='your-access-key-here'
export OPENAI_API_KEY='your-openai-api-key-here'
```

## Usage

Run the application:
```bash
python3 voice_assist_kivy.py
```

- Say "grapefruit" to activate the assistant
- Speak your command after the response sound
- The assistant will process your command and respond

## Configuration

- Wake word can be changed in the settings
- Voice settings can be adjusted (US/UK/Australian English, etc.)
- System prompt can be customized
- Personal information can be saved for context

## License

This project is licensed under the MIT License - see the LICENSE file for details. 