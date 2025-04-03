#!/usr/bin/env python3

import pyaudio
import struct
import speech_recognition as sr
import os
from openai import OpenAI
import requests
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import pvporcupine
import time
import traceback
import re
from pygame import mixer
from gtts import gTTS
import json
import signal
import sys

class VoiceAssistant:
    def __init__(self):
        try:
            print("Initializing VoiceAssistant...")
            # Set up signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Configuration
            self.wake_word = "computer"  # Default wake word
            self.available_wake_words = [
                "hey google",
                "grapefruit",
                "porcupine",
                "hey siri",
                "view glass",
                "americano",
                "blueberry",
                "pico clock",
                "bumblebee",
                "grasshopper",
                "smart mirror",
                "ok google",
                "snowboy",
                "alexa",
                "computer",
                "terminator",
                "jarvis",
                "picovoice",
                "hey barista"
            ]
            
            # Load API keys from environment variables
            self.porcupine_access_key = os.getenv('PORCUPINE_ACCESS_KEY')
            if not self.porcupine_access_key:
                raise ValueError("PORCUPINE_ACCESS_KEY environment variable not set")
                
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
                
            self.xai_api_key = os.getenv('XAI_API_KEY')
            self.perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
            self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
            self.serpapi_key = os.getenv('SERPAPI_KEY')
            
            self.xai_base_url = "https://api.x.ai/v1/chat/completions"
            self.perplexity_base_url = "https://api.perplexity.ai/chat/completions"
            self.running = False
            
            # Hardcoded sound files
            self.wake_sound_file = "default_wake.wav"
            self.response_sound_file = "default_response.wav"

            # System prompt and AI model
            self.system_prompt = "You are a helpful and friendly voice assistant. Keep your responses concise and limited to 100 words maximum. Be direct and clear in your communication."
            self.current_model = "OpenAI"
            self.current_voice = "us"  # Default to US English

            # Conversation history
            self.history_file = "conversation_history.json"
            self.conversation_history = self.load_history()

            # Initialize OpenAI client
            try:
                self.client = OpenAI()  # Will use OPENAI_API_KEY environment variable
                self.screen.log_message("OpenAI client initialized successfully")
            except Exception as e:
                self.screen.log_message(f"Error initializing OpenAI client: {e}")

            # Initialize pygame mixer with higher quality settings
            mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)

            # Initialize Porcupine wake word detector
            print("Setting up PyAudio...")
            self.pa = pyaudio.PyAudio()
            self.audio_stream = self.pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=512
            )
            print("Initializing Porcupine...")
            self.porcupine = pvporcupine.create(
                access_key=self.porcupine_access_key,
                keywords=[self.wake_word]
            )

            # Initialize GUI
            print("Creating GUI...")
            self.root = tk.Tk()
            self.root.title("Voice Assistant")
            self.root.geometry("400x600")  # Reduced window height since we removed avatar

            # Status and Control Frame
            control_frame = tk.Frame(self.root)
            control_frame.pack(pady=5)
            
            self.progress_label = tk.Label(control_frame, text="Initializing...", font=("Arial", 12))
            self.progress_label.pack(side=tk.LEFT, padx=5)
            
            self.status_label = tk.Label(control_frame, text="Status: Stopped", font=("Arial", 12))
            self.status_label.pack(side=tk.LEFT, padx=5)
            
            self.start_button = tk.Button(control_frame, text="Start", command=self.start_listening)
            self.start_button.pack(side=tk.LEFT, padx=5)
            self.stop_button = tk.Button(control_frame, text="Stop", command=self.stop_listening, state="disabled")
            self.stop_button.pack(side=tk.LEFT, padx=5)

            # Voice and Model Selection Frame
            selection_frame = tk.Frame(self.root)
            selection_frame.pack(pady=5)
            
            # Voice Selection
            voice_frame = tk.Frame(selection_frame)
            voice_frame.pack(side=tk.LEFT, padx=5)
            tk.Label(voice_frame, text="Voice:").pack(side=tk.LEFT)
            self.voice_selector = ttk.Combobox(voice_frame, 
                values=["US English", "UK English", "Australian English", "Indian English", "Irish English", "South African English", "Canadian English"],
                state="readonly",
                width=15)
            self.voice_selector.set("US English")
            self.voice_selector.pack(side=tk.LEFT)
            self.voice_selector.bind("<<ComboboxSelected>>", self.update_voice)
            
            # Model Selection
            model_frame = tk.Frame(selection_frame)
            model_frame.pack(side=tk.LEFT, padx=5)
            tk.Label(model_frame, text="AI Model:").pack(side=tk.LEFT)
            self.model_selector = ttk.Combobox(model_frame, values=["OpenAI", "Grok", "Perplexity"], state="readonly")
            self.model_selector.set("OpenAI")
            self.model_selector.pack(side=tk.LEFT)
            self.model_selector.bind("<<ComboboxSelected>>", self.update_model)

            # System Prompt Frame
            prompt_frame = tk.Frame(self.root)
            prompt_frame.pack(pady=5)
            tk.Label(prompt_frame, text="System Prompt:").pack()
            self.system_prompt_entry = tk.Text(prompt_frame, width=40, height=3)
            self.system_prompt_entry.insert("1.0", self.system_prompt)
            self.system_prompt_entry.pack()
            self.update_prompt_button = tk.Button(prompt_frame, text="Update Prompt", command=self.update_system_prompt)
            self.update_prompt_button.pack()

            # Wake Word Frame
            wake_frame = tk.Frame(self.root)
            wake_frame.pack(pady=5)
            tk.Label(wake_frame, text="Wake Word:").pack()
            self.wake_word_selector = ttk.Combobox(wake_frame, values=self.available_wake_words, state="readonly")
            self.wake_word_selector.set(self.wake_word)
            self.wake_word_selector.pack()
            self.wake_word_selector.bind("<<ComboboxSelected>>", self.update_wake_word)
            self.test_wake_word_button = tk.Button(wake_frame, text="Test Wake Word", command=self.test_wake_word)
            self.test_wake_word_button.pack()

            # History Viewer Frame
            history_frame = tk.Frame(self.root)
            history_frame.pack(pady=5)
            tk.Label(history_frame, text="Conversation History:").pack()
            self.history_viewer = scrolledtext.ScrolledText(history_frame, width=40, height=10)
            self.history_viewer.pack()
            self.update_history_viewer()

            # Log Frame
            log_frame = tk.Frame(self.root)
            log_frame.pack(pady=5)
            tk.Label(log_frame, text="Log:").pack()
            self.log = scrolledtext.ScrolledText(log_frame, width=40, height=15)
            self.log.pack()

            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.progress_label.config(text="Ready")
            print("Initialization complete.")
        except Exception as e:
            print(f"Error in __init__: {e}")
            traceback.print_exc()
            raise

    def log_message(self, message):
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)

    def update_system_prompt(self):
        new_prompt = self.system_prompt_entry.get("1.0", tk.END).strip()
        if new_prompt:
            self.system_prompt = new_prompt
            self.log_message(f"System prompt updated: {self.system_prompt}")
            messagebox.showinfo("Update", "System prompt updated successfully!")
        else:
            self.log_message("System prompt cannot be empty")
            messagebox.showwarning("Error", "System prompt cannot be empty")

    def update_model(self, event):
        self.current_model = self.model_selector.get()
        self.log_message(f"Switched to model: {self.current_model}")

    def update_voice(self, event):
        voice_mapping = {
            "US English": "us",
            "UK English": "co.uk",
            "Australian English": "com.au",
            "Indian English": "co.in",
            "Irish English": "ie",
            "South African English": "co.za",
            "Canadian English": "ca"
        }
        self.current_voice = voice_mapping[self.voice_selector.get()]
        self.log_message(f"Voice changed to: {self.voice_selector.get()}")

    def play_sound(self, sound_file):
        try:
            if sound_file and os.path.exists(sound_file):
                mixer.music.load(sound_file)
                mixer.music.play()
                while mixer.music.get_busy():  # Wait for the sound to finish
                    time.sleep(0.1)
            else:
                self.log_message(f"Sound file not available: {sound_file}")
        except Exception as e:
            self.log_message(f"Error playing sound: {e}")

    def listen_for_wake_word(self):
        self.log_message(f"Listening for wake word: '{self.wake_word}'...")
        while self.running:
            try:
                pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                result = self.porcupine.process(pcm)
                if result >= 0:
                    self.log_message("Wake word detected!")
                    self.play_sound(self.wake_sound_file)
                    return True
            except IOError:
                if not self.running:
                    break
                time.sleep(0.1)
        return False

    def record_command(self):
        self.log_message("Listening for command...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio = self.recognizer.listen(source, timeout=30, phrase_time_limit=10)
                command = self.recognizer.recognize_google(audio)
                self.log_message(f"Command received: {command}")
                return command
            except sr.WaitTimeoutError:
                self.log_message("No command heard within timeout")
                return None
            except sr.UnknownValueError:
                self.log_message("Could not understand audio")
                return None
            except sr.RequestError as e:
                self.log_message(f"Could not request results; {e}")
                return None
            except Exception as e:
                if not self.running:
                    return None
                self.log_message(f"Recording error: {e}")
                return None

    def needs_realtime_data(self, command):
        realtime_indicators = [
            r"current\b", r"today\b", r"now\b", r"this week\b", 
            r"weather\b", r"news\b", r"stock\b", r"price\b", 
            r"live\b", r"update\b", r"latest\b"
        ]
        command_lower = command.lower()
        return any(re.search(pattern, command_lower) for pattern in realtime_indicators)

    def search_with_serpapi(self, query):
        try:
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": self.serpapi_key,
                "num": 5
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("organic_results", [])
            summary = ""
            for result in results[:3]:
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                summary += f"{title}: {snippet}\n"
            return summary.strip()
        except Exception as e:
            self.log_message(f"SerpApi error: {e}")
            return None

    def get_openai_response(self, command):
        if not self.openai_api_key or not self.client:
            self.log_message("OpenAI API key not set")
            return "OpenAI API key is missing."
        
        try:
            enhanced_prompt = command
            if self.needs_realtime_data(command):
                self.log_message("Query requires real-time data, performing search...")
                search_results = self.search_with_serpapi(command)
                if search_results:
                    enhanced_prompt = f"User query: {command}\n\nRelevant real-time information:\n{search_results}\n\nBased on this information, provide an accurate response:"
                else:
                    enhanced_prompt = f"User query: {command}\n\nNote: Web search failed, use your existing knowledge to respond:"

            messages = [{"role": "system", "content": self.system_prompt}] + self.conversation_history + [{"role": "user", "content": enhanced_prompt}]
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            self.log_message(f"OpenAI error: {e}")
            return "Sorry, I encountered an error processing your request."

    def get_grok_response(self, command):
        if not self.xai_api_key:
            self.log_message("xAI API key not set")
            return "xAI API key is missing."
        
        try:
            enhanced_prompt = command
            if self.needs_realtime_data(command):
                self.log_message("Query requires real-time data, performing search...")
                search_results = self.search_with_serpapi(command)
                if search_results:
                    enhanced_prompt = f"User query: {command}\n\nRelevant real-time information:\n{search_results}\n\nBased on this information, provide an accurate response:"
                else:
                    enhanced_prompt = f"User query: {command}\n\nNote: Web search failed, use your existing knowledge to respond:"

            headers = {
                "Authorization": f"Bearer {self.xai_api_key}",
                "Content-Type": "application/json"
            }
            messages = [{"role": "system", "content": self.system_prompt}] + self.conversation_history + [{"role": "user", "content": enhanced_prompt}]
            payload = {
                "model": "grok-beta",
                "messages": messages
            }
            response = requests.post(self.xai_base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            self.log_message(f"xAI error: {e}")
            return "Sorry, I encountered an error processing your request."

    def get_perplexity_response(self, command):
        if not self.perplexity_api_key:
            self.log_message("Perplexity API key not set")
            return "Perplexity API key is missing."
        
        try:
            enhanced_prompt = command
            if self.needs_realtime_data(command):
                self.log_message("Query requires real-time data, performing search...")
                search_results = self.search_with_serpapi(command)
                if search_results:
                    enhanced_prompt = f"User query: {command}\n\nRelevant real-time information:\n{search_results}\n\nBased on this information, provide an accurate response:"
                else:
                    enhanced_prompt = f"User query: {command}\n\nNote: Web search failed, use your existing knowledge to respond:"

            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            messages = [{"role": "system", "content": self.system_prompt}] + self.conversation_history + [{"role": "user", "content": enhanced_prompt}]
            payload = {
                "model": "sonar",
                "messages": messages
            }
            response = requests.post(self.perplexity_base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            self.log_message(f"Perplexity error: {e}")
            return "Sorry, I encountered an error processing your request."

    def get_response(self, command):
        if self.current_model == "OpenAI":
            return self.get_openai_response(command)
        elif self.current_model == "Grok":
            return self.get_grok_response(command)
        elif self.current_model == "Perplexity":
            return self.get_perplexity_response(command)

    def speak(self, text):
        try:
            # Split text into sentences for chunking
            # Split on sentence endings (., !, ?)
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # Play response sound at the start
            self.play_sound(self.response_sound_file)
            
            # Process each sentence
            for sentence in sentences:
                if not sentence:
                    continue
                    
                # Add leading silence to prevent clipping
                padded_text = " " + sentence
                
                # Clean the text by removing asterisks
                cleaned_text = padded_text.replace('*', '')
                
                # Generate TTS audio for this chunk with selected voice
                tts = gTTS(text=cleaned_text, lang='en', tld=self.current_voice)
                filename = f"response_chunk_{hash(sentence)}.mp3"
                tts.save(filename)
                
                # Play this chunk
                mixer.music.load(filename)
                mixer.music.play()
                while mixer.music.get_busy():  # Wait for chunk to finish
                    time.sleep(0.1)
                    
                # Add a small pause between sentences
                time.sleep(0.3)
                    
                # Clean up the chunk file
                try:
                    os.remove(filename)
                except:
                    pass
                    
        except Exception as e:
            self.log_message(f"Text-to-speech error: {e}")

    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.log_message(f"Error loading history: {e}")
            return []

    def save_history(self):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.conversation_history, f)
        except Exception as e:
            self.log_message(f"Error saving history: {e}")

    def update_history_viewer(self):
        self.history_viewer.delete('1.0', tk.END)
        for message in self.conversation_history:
            role = message["role"]
            content = message["content"]
            self.history_viewer.insert(tk.END, f"{role.title()}: {content}\n\n")
        self.history_viewer.see(tk.END)

    def run_conversation(self):
        command = self.record_command()
        if command:
            response = self.get_response(command)
            if response:
                # Add new exchange to history
                self.conversation_history.append({"role": "user", "content": command})
                self.conversation_history.append({"role": "assistant", "content": response})
                
                # Save history after each exchange
                self.save_history()
                
                # Update the history viewer
                self.update_history_viewer()
                
                self.log_message(f"You: {command}")
                self.log_message(f"Assistant: {response}")
                self.speak(response)

    def run(self):
        while self.running:
            if self.listen_for_wake_word():
                self.run_conversation()
            time.sleep(0.1)

    def start_listening(self):
        if not self.running:
            self.running = True
            self.status_label.config(text="Status: Running")
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
            self.log_message("Listening started.")

    def stop_listening(self):
        if self.running:
            self.log_message("Stop requested...")
            self.running = False
            if self.audio_stream.is_active():
                self.audio_stream.stop_stream()
            if self.thread.is_alive():
                self.thread.join(timeout=2)
                if self.thread.is_alive():
                    self.log_message("Thread did not stop cleanly; may require restart.")
                else:
                    self.log_message("Listening stopped successfully.")
            self.status_label.config(text="Status: Stopped")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")

    def cleanup(self):
        """Clean up resources before exit"""
        try:
            print("Starting cleanup...")
            self.log_message("Starting cleanup...")
            
            # Stop listening if active
            if self.running:
                self.stop_listening()
            
            # Clean up Porcupine
            if hasattr(self, 'porcupine'):
                print("Cleaning up Porcupine...")
                self.porcupine.delete()
            
            # Clean up audio stream
            if hasattr(self, 'audio_stream'):
                print("Cleaning up audio stream...")
                if self.audio_stream.is_active():
                    self.audio_stream.stop_stream()
                self.audio_stream.close()
            
            # Clean up PyAudio
            if hasattr(self, 'pa'):
                print("Cleaning up PyAudio...")
                self.pa.terminate()
            
            # Clean up pygame mixer
            if mixer.get_init():
                print("Cleaning up pygame mixer...")
                mixer.quit()
            
            # Save history and config
            print("Saving history and config...")
            self.save_history()
            self.save_config()
            
            print("Cleanup complete.")
            self.log_message("Cleanup complete.")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            traceback.print_exc()
            self.log_message(f"Error during cleanup: {e}")

    def main(self):
        try:
            print("Entering main loop...")
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            print(f"Error in main: {e}")
            traceback.print_exc()
        finally:
            self.cleanup()

    def on_closing(self):
        """Handle window closing event"""
        print("Window closing requested...")
        self.log_message("Window closing requested...")
        self.cleanup()
        self.root.destroy()
        sys.exit(0)

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.wake_word = config.get('wake_word', self.wake_word)
                    self.porcupine_access_key = config.get('porcupine_access_key', self.porcupine_access_key)
        except Exception as e:
            self.log_message(f"Error loading config: {e}")

    def save_config(self):
        try:
            config = {
                'wake_word': self.wake_word,
                'porcupine_access_key': self.porcupine_access_key
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            self.log_message(f"Error saving config: {e}")

    def update_wake_word(self, event):
        new_wake_word = self.wake_word_selector.get()
        if new_wake_word != self.wake_word:
            self.wake_word = new_wake_word
            self.log_message(f"Wake word changed to: {self.wake_word}")
            
            # Reinitialize Porcupine with new wake word
            try:
                self.porcupine.delete()
                self.porcupine = pvporcupine.create(
                    access_key=self.porcupine_access_key,
                    keywords=[self.wake_word]
                )
                self.save_config()
                messagebox.showinfo("Success", "Wake word updated successfully!")
            except Exception as e:
                self.log_message(f"Error updating wake word: {e}")
                messagebox.showerror("Error", f"Failed to update wake word: {e}")
                # Revert to previous wake word
                self.wake_word_selector.set(self.wake_word)

    def test_wake_word(self):
        self.log_message("Testing wake word detection...")
        self.log_message("Say the wake word: " + self.wake_word)
        
        # Create a temporary Porcupine instance for testing
        try:
            test_porcupine = pvporcupine.create(
                access_key=self.porcupine_access_key,
                keywords=[self.wake_word]
            )
            
            # Create a temporary audio stream for testing
            test_stream = self.pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=512
            )
            
            # Listen for 5 seconds
            start_time = time.time()
            while time.time() - start_time < 5:
                pcm = test_stream.read(test_porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * test_porcupine.frame_length, pcm)
                result = test_porcupine.process(pcm)
                if result >= 0:
                    self.log_message("Wake word detected!")
                    self.play_sound(self.wake_sound_file)
                    break
                time.sleep(0.1)
            
            # Cleanup
            test_porcupine.delete()
            test_stream.close()
            
            if time.time() - start_time >= 5:
                self.log_message("No wake word detected during test period.")
            
        except Exception as e:
            self.log_message(f"Error testing wake word: {e}")
            messagebox.showerror("Error", f"Failed to test wake word: {e}")

    def signal_handler(self, signum, frame):
        """Handle termination signals gracefully"""
        print(f"\nReceived signal {signum}. Shutting down gracefully...")
        self.log_message("Shutdown signal received. Cleaning up...")
        self.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    try:
        print("Starting Voice Assistant with Porcupine...")
        assistant = VoiceAssistant()
        assistant.main()
    except Exception as e:
        print(f"Startup error: {e}")
        traceback.print_exc()
    finally:
        if 'assistant' in locals():
            assistant.cleanup()