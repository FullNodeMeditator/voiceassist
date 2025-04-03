#!/usr/bin/env python3

import pyaudio
import struct
import speech_recognition as sr
import os
from openai import OpenAI
import requests
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
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from datetime import datetime
from kivy.config import Config
from kivy.logger import Logger

# Set window size
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'resizable', '0')

# Define the Kivy UI layout
Builder.load_string('''
#:import utils kivy.utils

<CustomButton@Button>:
    background_color: utils.get_color_from_hex('#2196F3')
    color: 1, 1, 1, 1
    size_hint_y: None
    height: '50dp'
    font_size: '16sp'

<CustomLabel@Label>:
    color: 0, 0, 0, 1
    font_size: '16sp'
    bold: True
    text_size: self.size
    halign: 'left'
    valign: 'middle'
    padding: ('10dp', '5dp')

<SectionLabel@Label>:
    color: utils.get_color_from_hex('#2196F3')
    font_size: '20sp'
    bold: True
    size_hint_y: None
    height: '40dp'
    text_size: self.size
    halign: 'left'
    valign: 'middle'
    padding: ('10dp', '5dp')

<CustomTextInput@TextInput>:
    font_size: '16sp'
    multiline: True
    size_hint_y: None
    height: '120dp'
    background_color: 0.95, 0.95, 0.95, 1
    padding: ('10dp', '10dp')

<CustomSingleLineInput@TextInput>:
    font_size: '16sp'
    multiline: False
    size_hint_y: None
    height: '40dp'
    background_color: 0.95, 0.95, 0.95, 1
    padding: ('10dp', '5dp')

<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: '20dp'
        spacing: '10dp'
        canvas.before:
            Color:
                rgba: 0.98, 0.98, 0.98, 1
            Rectangle:
                pos: self.pos
                size: self.size
        
        # Title Bar
        BoxLayout:
            size_hint_y: None
            height: '60dp'
            spacing: '10dp'
            
            Label:
                text: 'Voice Assistant'
                font_size: '28sp'
                bold: True
                color: utils.get_color_from_hex('#2196F3')
                size_hint_x: 0.7
                
            CustomButton:
                id: start_button
                text: 'Start'
                size_hint_x: 0.15
                on_press: root.start_listening()
                
            CustomButton:
                id: stop_button
                text: 'Stop'
                size_hint_x: 0.15
                disabled: True
                on_press: root.stop_listening()
        
        # Status Bar
        BoxLayout:
            size_hint_y: None
            height: '40dp'
            padding: '10dp'
            canvas.before:
                Color:
                    rgba: 0.9, 0.9, 0.9, 0.3
                Rectangle:
                    pos: self.pos
                    size: self.size
            
            CustomLabel:
                id: status_label
                text: 'Status: Stopped'
        
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: '20dp'
                padding: '10dp'
                
                # Settings Section
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: '280dp'
                    spacing: '10dp'
                    canvas.before:
                        Color:
                            rgba: 1, 1, 1, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    
                    SectionLabel:
                        text: 'Settings'
                    
                    GridLayout:
                        cols: 2
                        spacing: '10dp'
                        padding: '10dp'
                        row_default_height: '50dp'
                        
                        CustomLabel:
                            text: 'Voice Selection:'
                            size_hint_x: 0.3
                            
                        Spinner:
                            id: voice_selector
                            text: 'UK English'
                            values: ['US English', 'UK English', 'Australian English', 'Indian English', 'Irish English', 'South African English', 'Canadian English']
                            on_text: root.update_voice(self.text)
                            size_hint_x: 0.7
                            
                        CustomLabel:
                            text: 'AI Model:'
                            size_hint_x: 0.3
                            
                        Spinner:
                            id: model_selector
                            text: 'Grok'
                            values: ['OpenAI', 'Grok', 'Perplexity']
                            on_text: root.update_model(self.text)
                            size_hint_x: 0.7
                            
                        CustomLabel:
                            text: 'Wake Word:'
                            size_hint_x: 0.3
                            
                        Spinner:
                            id: wake_word_selector
                            text: 'grapefruit'
                            values: root.available_wake_words
                            on_text: root.update_wake_word(self.text)
                            size_hint_x: 0.7
                
                # Personal Information Section
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: '400dp'  # Increased height to accommodate spacing
                    spacing: '10dp'
                    canvas.before:
                        Color:
                            rgba: 1, 1, 1, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    
                    SectionLabel:
                        text: 'Personal Information'
                    
                    GridLayout:
                        cols: 2
                        spacing: '10dp'
                        padding: '10dp'
                        row_default_height: '50dp'
                        
                        CustomLabel:
                            text: 'Name:'
                            size_hint_x: 0.3
                            
                        CustomSingleLineInput:
                            id: user_name
                            text: root.user_name
                            size_hint_x: 0.7
                            hint_text: 'Enter your name'
                            
                        CustomLabel:
                            text: 'Location:'
                            size_hint_x: 0.3
                            
                        CustomSingleLineInput:
                            id: user_location
                            text: root.user_location
                            size_hint_x: 0.7
                            hint_text: 'Enter your location'
                            
                        CustomLabel:
                            text: 'Interests:'
                            size_hint_x: 0.3
                            
                        CustomSingleLineInput:
                            id: user_interests
                            text: root.user_interests
                            size_hint_x: 0.7
                            hint_text: 'Enter your interests (comma-separated)'
                            
                        CustomLabel:
                            text: 'Preferences:'
                            size_hint_x: 0.3
                            
                        CustomSingleLineInput:
                            id: user_preferences
                            text: root.user_preferences
                            size_hint_x: 0.7
                            hint_text: 'Enter your preferences'
                    
                    BoxLayout:
                        size_hint_y: None
                        height: '60dp'  # Increased height
                        padding: '10dp'
                        spacing: '10dp'
                        pos_hint: {'y': 0}  # Position at bottom
                        
                        CustomButton:
                            text: 'Save Personal Info'
                            on_press: root.save_personal_info()
                            size_hint_x: 0.5
                        
                        CustomButton:
                            text: 'Reset'
                            on_press: root.reset_personal_info()
                
                # System Prompt Section
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: '220dp'
                    spacing: '10dp'
                    canvas.before:
                        Color:
                            rgba: 1, 1, 1, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    
                    SectionLabel:
                        text: 'System Prompt'
                    
                    BoxLayout:
                        orientation: 'vertical'
                        spacing: '10dp'
                        padding: '10dp'
                        
                        BoxLayout:
                            size_hint_y: None
                            height: '40dp'
                            spacing: '10dp'
                            
                            CustomLabel:
                                text: 'System Prompt:'
                                size_hint_x: 0.7
                                
                            CustomButton:
                                text: 'Update'
                                size_hint_x: 0.3
                                on_press: root.update_system_prompt()
                        
                        ScrollView:
                            CustomTextInput:
                                id: system_prompt
                                readonly: False
                                multiline: True
                                background_color: 0.95, 0.95, 0.95, 1
                                font_size: '14sp'
                                text: root.system_prompt
                
                # History Section
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: '400dp'
                    spacing: '10dp'
                    canvas.before:
                        Color:
                            rgba: 1, 1, 1, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    
                    SectionLabel:
                        text: 'Conversation History'
                    
                    BoxLayout:
                        orientation: 'horizontal'
                        spacing: '10dp'
                        padding: '10dp'
                        
                        # Short-term History
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_x: 0.5
                            spacing: '10dp'
                            
                            BoxLayout:
                                size_hint_y: None
                                height: '40dp'
                                spacing: '10dp'
                                
                                CustomLabel:
                                    text: 'Short-term History:'
                                    size_hint_x: 0.7
                                    
                                CustomButton:
                                    text: 'Clear'
                                    size_hint_x: 0.3
                                    on_press: root.clear_short_term_history()
                            
                            ScrollView:
                                TextInput:
                                    id: short_term_history_viewer
                                    readonly: True
                                    multiline: True
                                    background_color: 0.95, 0.95, 0.95, 1
                                    font_size: '14sp'
                        
                        # Long-term History
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_x: 0.5
                            spacing: '10dp'
                            
                            BoxLayout:
                                size_hint_y: None
                                height: '40dp'
                                spacing: '10dp'
                                
                                CustomLabel:
                                    text: 'Long-term History:'
                                    size_hint_x: 0.7
                                    
                                CustomButton:
                                    text: 'Clear'
                                    size_hint_x: 0.15
                                    on_press: root.clear_long_term_history()
                                
                                CustomButton:
                                    text: 'Save'
                                    size_hint_x: 0.15
                                    on_press: root.save_long_term_memory()
                            
                            ScrollView:
                                CustomTextInput:
                                    id: long_term_history_viewer
                                    readonly: False
                                    multiline: True
                                    background_color: 0.95, 0.95, 0.95, 1
                                    font_size: '14sp'
                
                # System Log Section
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: '200dp'
                    spacing: '10dp'
                    canvas.before:
                        Color:
                            rgba: 1, 1, 1, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    
                    SectionLabel:
                        text: 'System Log'
                    
                    ScrollView:
                        padding: '10dp'
                        TextInput:
                            id: log_viewer
                            readonly: True
                            multiline: True
                            background_color: 0.95, 0.95, 0.95, 1
                            font_size: '14sp'
                
                # Reminders Section
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: '300dp'
                    spacing: '10dp'
                    canvas.before:
                        Color:
                            rgba: 1, 1, 1, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    
                    SectionLabel:
                        text: 'Reminders'
                    
                    BoxLayout:
                        orientation: 'vertical'
                        spacing: '10dp'
                        padding: '10dp'
                        
                        BoxLayout:
                            size_hint_y: None
                            height: '40dp'
                            spacing: '10dp'
                            
                            CustomLabel:
                                text: 'Reminder:'
                                size_hint_x: 0.2
                                
                            CustomSingleLineInput:
                                id: reminder_text
                                size_hint_x: 0.8
                                hint_text: 'Enter reminder text'
                        
                        BoxLayout:
                            size_hint_y: None
                            height: '40dp'
                            spacing: '10dp'
                            
                            CustomLabel:
                                text: 'Day:'
                                size_hint_x: 0.2
                                
                            Spinner:
                                id: reminder_day
                                size_hint_x: 0.3
                                text: 'Monday'
                                values: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                                
                            CustomLabel:
                                text: 'Time:'
                                size_hint_x: 0.2
                                
                            CustomSingleLineInput:
                                id: reminder_time
                                size_hint_x: 0.3
                                hint_text: 'HH:MM (24-hour format)'
                        
                        BoxLayout:
                            size_hint_y: None
                            height: '40dp'
                            spacing: '10dp'
                            
                            CustomButton:
                                text: 'Add'
                                size_hint_x: 0.3
                                on_press: root.add_reminder()
                            
                            CustomButton:
                                text: 'Clear All'
                                size_hint_x: 0.35
                                on_press: root.clear_reminders()
                            
                            CustomButton:
                                text: 'Refresh'
                                size_hint_x: 0.35
                                on_press: root.refresh_reminders()
                        
                        ScrollView:
                            CustomTextInput:
                                id: reminders_viewer
                                readonly: True
                                multiline: True
                                background_color: 0.95, 0.95, 0.95, 1
                                font_size: '14sp'
''')

class MainScreen(Screen):
    def __init__(self, **kwargs):
        # Initialize personal information variables
        self.user_name = ""
        self.user_location = ""
        self.user_interests = ""
        self.user_preferences = ""
        
        # Set default system prompt and wake words
        self.system_prompt = "You are a helpful and friendly voice assistant. Keep your responses concise and limited to 50 words maximum. Be direct and clear in your communication."
        self.available_wake_words = ["grapefruit", "hey assistant", "computer"]
        self.available_models = ["gpt-3.5-turbo", "gpt-4"]
        
        # Initialize reminders
        self.reminders = []
        self.reminders_file = 'reminders.json'
        self.system_prompt_file = 'system_prompt.json'
        
        # Call parent class initialization
        super(MainScreen, self).__init__(**kwargs)
        
        # Initialize the voice assistant with a reference to this screen
        self.assistant = VoiceAssistant(self)
        
        # Load data after initialization
        self.load_reminders()
        Clock.schedule_once(lambda dt: self.load_system_prompt(), 0.1)
        
        # Start reminder checking thread
        self.reminder_check_thread = threading.Thread(target=self.check_reminders, daemon=True)
        self.reminder_check_thread.start()
        
        # Try to load personal info from file
        try:
            with open('personal_info.json', 'r') as f:
                data = json.load(f)
                self.user_name = data.get('name', '')
                self.user_location = data.get('location', '')
                self.user_interests = data.get('interests', '')
                self.user_preferences = data.get('preferences', '')
                print(f"Loaded personal info: {data}")  # Debug print
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading personal_info.json: {e}")  # Debug print
            pass
            
        # Try to load from long-term memory if personal info file is empty
        if not any([self.user_name, self.user_location, self.user_interests, self.user_preferences]):
            try:
                with open('long_term_memory.json', 'r') as f:
                    long_term_memory = json.load(f)
                    print(f"Loaded long-term memory: {long_term_memory}")  # Debug print
                    personal_info_entry = next((entry for entry in long_term_memory if entry.get('type') == 'personal_info'), None)
                    if personal_info_entry:
                        # Extract information from the content string
                        content = personal_info_entry.get('content', '')
                        print(f"Found personal info in long-term memory: {content}")  # Debug print
                        # Simple parsing of the content string
                        if 'Name:' in content:
                            self.user_name = content.split('Name:')[1].split(',')[0].strip()
                        if 'Location:' in content:
                            self.user_location = content.split('Location:')[1].split(',')[0].strip()
                        if 'Interests:' in content:
                            self.user_interests = content.split('Interests:')[1].split(',')[0].strip()
                        if 'Preferences:' in content:
                            self.user_preferences = content.split('Preferences:')[1].strip()
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error loading long_term_memory.json: {e}")  # Debug print
                pass
        
        # Update system prompt with loaded information
        self.update_system_prompt()
        
        # Setup UI
        self.setup_ui()
        
        # Update UI fields with loaded information
        if hasattr(self, 'ids'):
            self.ids.user_name.text = self.user_name
            self.ids.user_location.text = self.user_location
            self.ids.user_interests.text = self.user_interests
            self.ids.user_preferences.text = self.user_preferences
            
            # Update long-term memory viewer
            try:
                with open('long_term_memory.json', 'r') as f:
                    long_term_memory = json.load(f)
                    # Format the memory for display
                    formatted_memory = ""
                    for entry in long_term_memory:
                        formatted_memory += f"Time: {entry.get('timestamp', 'N/A')}\n"
                        formatted_memory += f"Type: {entry.get('type', 'N/A')}\n"
                        formatted_memory += f"Content: {entry.get('content', 'N/A')}\n"
                        formatted_memory += "-" * 50 + "\n"
                    self.ids.long_term_history_viewer.text = formatted_memory
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error loading long-term memory for display: {e}")  # Debug print
                self.ids.long_term_history_viewer.text = "No long-term memory available"

    def setup_ui(self):
        # Set window size and title
        Window.size = (800, 600)
        Window.title = "Voice Assistant"
        
        # Initialize UI elements
        self.status_label = self.ids.status_label
        self.start_button = self.ids.start_button
        self.stop_button = self.ids.stop_button
        self.voice_selector = self.ids.voice_selector
        self.model_selector = self.ids.model_selector
        self.wake_word_selector = self.ids.wake_word_selector
        self.short_term_history_viewer = self.ids.short_term_history_viewer
        self.long_term_history_viewer = self.ids.long_term_history_viewer
        self.log_viewer = self.ids.log_viewer
        
        # Set initial values
        self.model_selector.values = self.available_models
        self.model_selector.text = self.assistant.model
        self.wake_word_selector.values = self.available_wake_words
        self.wake_word_selector.text = self.assistant.wake_word
        
        # Load system prompt after UI is set up
        Clock.schedule_once(lambda dt: self.load_system_prompt(), 0.1)

    def refresh_reminders(self):
        try:
            if not hasattr(self, 'ids') or not hasattr(self.ids, 'reminders_viewer'):
                print("Reminders viewer not initialized yet")
                return
                
            # Sort reminders by day and time
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            self.reminders.sort(key=lambda x: (days_order.index(x['day']), x['time']))
            
            # Format reminders for display
            formatted_reminders = []
            for reminder in self.reminders:
                formatted_reminders.append(
                    f"{reminder['day']} at {reminder['time']}: {reminder['text']}"
                )
            
            self.ids.reminders_viewer.text = '\n'.join(formatted_reminders)
            print(f"Refreshed reminders display: {formatted_reminders}")  # Debug print
        except Exception as e:
            print(f"Error refreshing reminders: {e}")

    def start_listening(self):
        """Start listening for wake word"""
        self.assistant.start_listening()
        def update_ui(dt):
            self.start_button.disabled = True
            self.stop_button.disabled = False
            self.status_label.text = "Status: Running"
        Clock.schedule_once(update_ui)
        
    def stop_listening(self):
        """Stop listening for wake word"""
        self.assistant.stop_listening()
        def update_ui(dt):
            self.start_button.disabled = False
            self.stop_button.disabled = True
            self.status_label.text = "Status: Stopped"
        Clock.schedule_once(update_ui)
        
    def update_voice(self, voice):
        self.assistant.update_voice(voice)
        
    def update_model(self, model):
        self.assistant.update_model(model)
        
    def update_wake_word(self, wake_word):
        self.assistant.update_wake_word(wake_word)
        
    def update_system_prompt(self):
        try:
            if hasattr(self, 'ids') and hasattr(self.ids, 'system_prompt'):
                new_prompt = self.ids.system_prompt.text
                self.assistant.update_system_prompt(new_prompt)
                self.save_system_prompt()  # Save the prompt when updated
                print(f"Updated system prompt: {new_prompt}")  # Debug print
        except Exception as e:
            print(f"Error updating system prompt: {e}")

    def clear_short_term_history(self):
        self.assistant.conversation_history = []
        self.assistant.save_history(self.assistant.history_file, self.assistant.conversation_history)
        self.update_history_viewers()
        popup = Popup(title='Success',
                     content=Label(text='Short-term history cleared successfully!'),
                     size_hint=(None, None),
                     size=(300, 200))
        popup.open()

    def clear_long_term_history(self):
        self.assistant.long_term_history = []
        self.assistant.save_history(self.assistant.long_term_history_file, self.assistant.long_term_history)
        self.update_history_viewers()
        popup = Popup(title='Success',
                     content=Label(text='Long-term history cleared successfully!'),
                     size_hint=(None, None),
                     size=(300, 200))
        popup.open()

    def load_personal_info(self):
        try:
            with open('personal_info.json', 'r') as f:
                data = json.load(f)
                self.user_name = data.get('name', '')
                self.user_location = data.get('location', '')
                self.user_interests = data.get('interests', '')
                self.user_preferences = data.get('preferences', '')
        except FileNotFoundError:
            # Create default personal info file
            self.save_personal_info()
    
    def save_personal_info(self):
        try:
            # Get current values from the input fields
            self.user_name = self.ids.user_name.text
            self.user_location = self.ids.user_location.text
            self.user_interests = self.ids.user_interests.text
            self.user_preferences = self.ids.user_preferences.text
            
            # Save to personal info file
            data = {
                'name': self.user_name,
                'location': self.user_location,
                'interests': self.user_interests,
                'preferences': self.user_preferences
            }
            print(f"Saving personal info: {data}")  # Debug print
            
            with open('personal_info.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            # Update system prompt with new information
            self.update_system_prompt()
            
            # Save to long-term memory
            try:
                # Try to load existing long-term memory
                try:
                    with open('long_term_memory.json', 'r') as f:
                        long_term_memory = json.load(f)
                        print(f"Loaded existing long-term memory: {long_term_memory}")  # Debug print
                except (FileNotFoundError, json.JSONDecodeError):
                    long_term_memory = []
                    print("No existing long-term memory found, creating new")  # Debug print
                
                # Create personal info entry
                personal_info_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'personal_info',
                    'content': f"User's personal information: Name: {self.user_name}, Location: {self.user_location}, Interests: {self.user_interests}, Preferences: {self.user_preferences}"
                }
                print(f"Created personal info entry: {personal_info_entry}")  # Debug print
                
                # Check if personal info already exists in long-term memory
                existing_entry = next((entry for entry in long_term_memory if entry.get('type') == 'personal_info'), None)
                if existing_entry:
                    # Update existing entry
                    existing_entry.update(personal_info_entry)
                    print("Updated existing personal info entry")  # Debug print
                else:
                    # Add new entry
                    long_term_memory.append(personal_info_entry)
                    print("Added new personal info entry")  # Debug print
                
                # Save updated long-term memory
                with open('long_term_memory.json', 'w') as f:
                    json.dump(long_term_memory, f, indent=2)
                print(f"Saved updated long-term memory: {long_term_memory}")  # Debug print
                
            except Exception as e:
                print(f"Error saving to long-term memory: {e}")  # Debug print
                raise  # Re-raise to be caught by outer try-except
            
            # Show success message
            popup = Popup(title='Success',
                         content=Label(text='Personal information saved successfully!'),
                         size_hint=(None, None),
                         size=(300, 200))
            popup.open()
            
        except Exception as e:
            print(f"Error saving personal info: {e}")  # Debug print
            popup = Popup(title='Error',
                         content=Label(text=f'Error saving personal information: {str(e)}'),
                         size_hint=(None, None),
                         size=(300, 200))
            popup.open()
    
    def reset_personal_info(self):
        # Clear the input fields
        self.ids.user_name.text = ""
        self.ids.user_location.text = ""
        self.ids.user_interests.text = ""
        self.ids.user_preferences.text = ""
        
        # Reset the variables
        self.user_name = ""
        self.user_location = ""
        self.user_interests = ""
        self.user_preferences = ""
        
        # Save empty values
        self.save_personal_info()
        
        # Show success message
        popup = Popup(title='Success',
                     content=Label(text='Personal information reset successfully!'),
                     size_hint=(None, None),
                     size=(300, 200))
        popup.open()

    def get_default_system_prompt(self):
        return "You are a helpful and friendly voice assistant. Keep your responses concise and limited to 50 words maximum. Be direct and clear in your communication."

    def save_long_term_memory(self):
        try:
            # Get the current text from the viewer
            current_text = self.ids.long_term_history_viewer.text
            
            # Parse the text into entries
            entries = []
            current_entry = {}
            
            for line in current_text.split('\n'):
                if line.startswith('Time:'):
                    if current_entry:
                        entries.append(current_entry)
                    current_entry = {'timestamp': line.replace('Time:', '').strip()}
                elif line.startswith('Type:'):
                    current_entry['type'] = line.replace('Type:', '').strip()
                elif line.startswith('Content:'):
                    current_entry['content'] = line.replace('Content:', '').strip()
                elif line.strip() == '-' * 50:
                    if current_entry:
                        entries.append(current_entry)
                        current_entry = {}
            
            # Add the last entry if exists
            if current_entry:
                entries.append(current_entry)
            
            # Save to file
            with open('long_term_memory.json', 'w') as f:
                json.dump(entries, f, indent=2)
            
            # Show success message
            popup = Popup(title='Success',
                         content=Label(text='Long-term memory saved successfully!'),
                         size_hint=(None, None),
                         size=(300, 200))
            popup.open()
            
        except Exception as e:
            print(f"Error saving long-term memory: {e}")  # Debug print
            popup = Popup(title='Error',
                         content=Label(text=f'Error saving long-term memory: {str(e)}'),
                         size_hint=(None, None),
                         size=(300, 200))
            popup.open()

    def load_reminders(self):
        try:
            if os.path.exists(self.reminders_file):
                with open(self.reminders_file, 'r') as f:
                    self.reminders = json.load(f)
                print(f"Loaded reminders: {self.reminders}")  # Debug print
            else:
                self.reminders = []
            self.refresh_reminders()
        except Exception as e:
            print(f"Error loading reminders: {e}")
            self.reminders = []

    def save_reminders(self):
        try:
            with open(self.reminders_file, 'w') as f:
                json.dump(self.reminders, f, indent=2)
            print(f"Saved reminders: {self.reminders}")  # Debug print
        except Exception as e:
            print(f"Error saving reminders: {e}")

    def add_reminder(self):
        try:
            text = self.ids.reminder_text.text.strip()
            day = self.ids.reminder_day.text
            time_str = self.ids.reminder_time.text.strip()
            
            print(f"Adding reminder: {text} on {day} at {time_str}")  # Debug print
            
            if not text or not time_str:
                popup = Popup(title='Error',
                             content=Label(text='Please fill in all fields'),
                             size_hint=(None, None),
                             size=(300, 200))
                popup.open()
                return
            
            # Parse time
            try:
                time_obj = datetime.strptime(time_str, "%H:%M").time()
                print(f"Parsed time: {time_obj}")  # Debug print
            except ValueError:
                popup = Popup(title='Error',
                             content=Label(text='Invalid time format (use HH:MM)'),
                             size_hint=(None, None),
                             size=(300, 200))
                popup.open()
                return
            
            # Add reminder
            reminder = {
                'text': text,
                'day': day,
                'time': time_str,
                'notified': False
            }
            self.reminders.append(reminder)
            self.save_reminders()
            self.refresh_reminders()
            
            print(f"Added reminder: {reminder}")  # Debug print
            print(f"Current reminders: {self.reminders}")  # Debug print
            
            # Clear input fields
            self.ids.reminder_text.text = ''
            self.ids.reminder_time.text = ''
            
            popup = Popup(title='Success',
                         content=Label(text='Reminder added successfully!'),
                         size_hint=(None, None),
                         size=(300, 200))
            popup.open()
            
        except Exception as e:
            print(f"Error adding reminder: {e}")  # Debug print
            popup = Popup(title='Error',
                         content=Label(text=f'Error adding reminder: {str(e)}'),
                         size_hint=(None, None),
                         size=(300, 200))
            popup.open()

    def clear_reminders(self):
        self.reminders = []
        self.save_reminders()
        self.refresh_reminders()
        popup = Popup(title='Success',
                     content=Label(text='All reminders cleared!'),
                     size_hint=(None, None),
                     size=(300, 200))
        popup.open()

    def load_system_prompt(self):
        try:
            if os.path.exists(self.system_prompt_file):
                with open(self.system_prompt_file, 'r') as f:
                    saved_prompt = json.load(f)
                    if hasattr(self, 'ids') and hasattr(self.ids, 'system_prompt'):
                        self.ids.system_prompt.text = saved_prompt.get('prompt', '')
                        self.assistant.update_system_prompt(self.ids.system_prompt.text)
                        print(f"Loaded system prompt: {self.ids.system_prompt.text}")  # Debug print
        except Exception as e:
            print(f"Error loading system prompt: {e}")

    def save_system_prompt(self):
        try:
            if hasattr(self, 'ids') and hasattr(self.ids, 'system_prompt'):
                with open(self.system_prompt_file, 'w') as f:
                    json.dump({'prompt': self.ids.system_prompt.text}, f, indent=2)
                print(f"Saved system prompt: {self.ids.system_prompt.text}")  # Debug print
        except Exception as e:
            print(f"Error saving system prompt: {e}")

    def check_reminders(self):
        while True:
            try:
                current_time = datetime.now()
                current_day = current_time.strftime('%A')
                current_time_str = current_time.strftime('%H:%M')
                
                print(f"Checking reminders at {current_time_str} on {current_day}")  # Debug print
                print(f"Current reminders: {self.reminders}")  # Debug print
                
                for reminder in self.reminders:
                    print(f"Checking reminder: {reminder}")  # Debug print
                    if not reminder['notified'] and reminder['day'] == current_day and reminder['time'] == current_time_str:
                        print(f"Triggering reminder: {reminder['text']}")  # Debug print
                        # Notify user
                        self.speak(f"Reminder: {reminder['text']}")
                        reminder['notified'] = True
                        self.save_reminders()
                        self.refresh_reminders()
                
                # Reset notifications at midnight
                if current_time.hour == 0 and current_time.minute == 0:
                    print("Resetting notifications at midnight")  # Debug print
                    for reminder in self.reminders:
                        reminder['notified'] = False
                    self.save_reminders()
                    self.refresh_reminders()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"Error checking reminders: {e}")  # Debug print
                time.sleep(30)  # Wait 30 seconds before retrying

    def log_message(self, message):
        def update_log(dt):
            self.ids.log_viewer.text += f"{message}\n"
            self.ids.log_viewer.cursor = (0, len(self.ids.log_viewer.text))
        Clock.schedule_once(update_log)

    def speak(self, text):
        try:
            self.assistant.speak(text)
        except Exception as e:
            print(f"Error speaking: {e}")
            self.log_message(f"Error speaking: {e}")

class VoiceAssistant:
    def __init__(self, screen):
        self.screen = screen
        self.running = False
        self.current_voice = 'co.uk'  # UK English voice
        self.model = "gpt-3.5-turbo"
        self.wake_word = "grapefruit"
        self.conversation_history = []
        self.long_term_history = []
        self.system_prompt = "You are a helpful and friendly voice assistant. Keep your responses concise and limited to 50 words maximum. Be direct and clear in your communication."
        
        # Initialize audio components
        try:
            self.pa = pyaudio.PyAudio()
            self.screen.log_message("PyAudio initialized successfully")
        except Exception as e:
            self.screen.log_message(f"Error initializing PyAudio: {e}")
            self.pa = None
            
        self.porcupine = None
        self.audio_stream = None
        self.response_sound_file = "response_sound.mp3"
        
        # Initialize pygame mixer for audio playback
        try:
            mixer.init()
            self.screen.log_message("Pygame mixer initialized successfully")
        except Exception as e:
            self.screen.log_message(f"Error initializing pygame mixer: {e}")

    def initialize_porcupine(self):
        """Initialize or reinitialize Porcupine with current wake word"""
        try:
            # Clean up existing instance if any
            if self.porcupine:
                self.porcupine.delete()
                self.porcupine = None

            access_key = os.getenv('PORCUPINE_ACCESS_KEY')
            self.screen.log_message(f"Attempting to initialize Porcupine with wake word: {self.wake_word}")
            
            if not access_key:
                self.screen.log_message("Error: PORCUPINE_ACCESS_KEY not set in environment")
                return False

            self.screen.log_message("Found Porcupine access key, creating instance...")
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=[self.wake_word]
            )
            self.screen.log_message(f"Porcupine initialized successfully with wake word: {self.wake_word}")
            self.screen.log_message(f"Sample rate: {self.porcupine.sample_rate}, Frame length: {self.porcupine.frame_length}")
            return True
        except Exception as e:
            self.screen.log_message(f"Error initializing Porcupine: {str(e)}")
            self.screen.log_message(f"Stack trace: {traceback.format_exc()}")
            self.porcupine = None
            return False

    def start_listening(self):
        """Start listening for wake word"""
        if not self.running:
            try:
                self.screen.log_message("Starting listening process...")
                
                # Initialize Porcupine first
                if not self.initialize_porcupine():
                    self.screen.log_message("Failed to initialize Porcupine, cannot start listening")
                    return

                # Initialize audio stream with Porcupine's parameters
                if not self.audio_stream:
                    self.screen.log_message(f"Initializing audio stream with rate={self.porcupine.sample_rate}, frame_length={self.porcupine.frame_length}")
                    self.audio_stream = self.pa.open(
                        rate=self.porcupine.sample_rate,
                        channels=1,
                        format=pyaudio.paInt16,
                        input=True,
                        frames_per_buffer=self.porcupine.frame_length
                    )
                    self.screen.log_message("Audio stream initialized successfully")

                self.running = True
                self.thread = threading.Thread(target=self.run)
                self.thread.daemon = True
                self.thread.start()
                self.screen.log_message("Started listening for wake word")
                
            except Exception as e:
                self.screen.log_message(f"Error starting listening: {str(e)}")
                self.screen.log_message(f"Stack trace: {traceback.format_exc()}")
                self.running = False
                if self.audio_stream:
                    self.audio_stream.close()
                    self.audio_stream = None

    def run(self):
        """Main loop for voice assistant"""
        self.screen.log_message("Entering main listening loop...")
        while self.running:
            try:
                # Verify initialization
                if not self.audio_stream or not self.porcupine:
                    self.screen.log_message("Audio stream or Porcupine not initialized, retrying...")
                    time.sleep(1)
                    continue

                try:
                    # Read audio data
                    pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                    if not pcm:
                        self.screen.log_message("No audio data received")
                        time.sleep(0.1)
                        continue

                    # Convert audio data to PCM values
                    pcm_data = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                    
                    # Process with Porcupine
                    result = self.porcupine.process(pcm_data)
                    
                    if result >= 0:
                        self.screen.log_message("Wake word detected!")
                        self.play_sound(self.response_sound_file)
                        
                        # Record and process command
                        with sr.Microphone() as source:
                            recognizer = sr.Recognizer()
                            recognizer.adjust_for_ambient_noise(source, duration=0.5)
                            self.screen.log_message("Listening for command...")
                            
                            try:
                                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                                command = recognizer.recognize_google(audio)
                                self.screen.log_message(f"Command received: {command}")
                                
                                # Process command with LLM
                                self.conversation_history.append({"role": "user", "content": command})
                                
                                client = OpenAI()
                                response = client.chat.completions.create(
                                    model=self.model,
                                    messages=[
                                        {"role": "system", "content": self.system_prompt},
                                        *self.conversation_history[-6:]  # Keep last 3 exchanges
                                    ]
                                )
                                
                                assistant_response = response.choices[0].message.content
                                self.conversation_history.append({"role": "assistant", "content": assistant_response})
                                
                                self.screen.log_message(f"Assistant: {assistant_response}")
                                self.speak(assistant_response)
                                
                            except sr.WaitTimeoutError:
                                self.screen.log_message("No command heard within timeout")
                            except sr.UnknownValueError:
                                self.screen.log_message("Could not understand audio")
                            except sr.RequestError as e:
                                self.screen.log_message(f"Could not request results; {e}")
                            except Exception as e:
                                self.screen.log_message(f"Error processing command: {e}")
                
                except Exception as e:
                    self.screen.log_message(f"Error in wake word detection: {str(e)}")
                    self.screen.log_message(f"Stack trace: {traceback.format_exc()}")
                    time.sleep(0.1)
                
            except Exception as e:
                self.screen.log_message(f"Error in run loop: {str(e)}")
                self.screen.log_message(f"Stack trace: {traceback.format_exc()}")
                time.sleep(0.1)

    def update_wake_word(self, wake_word):
        """Update wake word and reinitialize Porcupine"""
        if wake_word != self.wake_word:
            self.wake_word = wake_word
            self.screen.log_message(f"Updating wake word to: {wake_word}")
            
            # Stop listening if currently running
            was_running = self.running
            if was_running:
                self.stop_listening()
            
            # Reinitialize Porcupine
            if self.initialize_porcupine():
                self.screen.log_message("Successfully updated wake word")
                # Resume listening if it was running before
                if was_running:
                    self.start_listening()
            else:
                self.screen.log_message("Failed to update wake word")

    def stop_listening(self):
        """Stop listening for wake word"""
        if self.running:
            self.running = False
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None
            if self.porcupine:
                self.porcupine.delete()
                self.porcupine = None
            self.screen.log_message("Stopped listening")

    def update_voice(self, voice_name):
        voice_mapping = {
            "US English": "us",
            "UK English": "co.uk",
            "Australian English": "com.au",
            "Indian English": "co.in",
            "Irish English": "ie",
            "South African English": "co.za",
            "Canadian English": "ca"
        }
        self.current_voice = voice_mapping[voice_name]
        self.screen.log_message(f"Voice changed to: {voice_name}")

    def update_model(self, model_name):
        self.model = model_name
        self.screen.log_message(f"Switched to model: {model_name}")

    def speak(self, text):
        try:
            # Split text into sentences for chunking
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # Play response sound at the start
            self.play_sound(self.response_sound_file)
            
            # Create a separate audio stream for wake word detection
            wake_word_stream = self.pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=512
            )
            
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
                
                # Check for wake word while playing audio
                while mixer.music.get_busy():
                    try:
                        pcm = wake_word_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                        pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                        result = self.porcupine.process(pcm)
                        if result >= 0:
                            self.screen.log_message("Wake word detected! Stopping playback...")
                            mixer.music.stop()
                            # Clean up the chunk file
                            try:
                                os.remove(filename)
                            except:
                                pass
                            # Close the wake word stream
                            wake_word_stream.stop_stream()
                            wake_word_stream.close()
                            return  # Exit the speak method
                    except Exception as e:
                        self.screen.log_message(f"Error checking wake word: {e}")
                    time.sleep(0.1)
                    
                # Add a small pause between sentences
                time.sleep(0.3)
                    
                # Clean up the chunk file
                try:
                    os.remove(filename)
                except:
                    pass
            
            # Close the wake word stream when done
            wake_word_stream.stop_stream()
            wake_word_stream.close()
                    
        except Exception as e:
            self.screen.log_message(f"Text-to-speech error: {e}")

    def play_sound(self, sound_file):
        try:
            if os.path.exists(sound_file):
                mixer.music.load(sound_file)
                mixer.music.play()
                while mixer.music.get_busy():
                    time.sleep(0.1)
        except Exception as e:
            self.screen.log_message(f"Error playing sound: {e}")

    def update_system_prompt(self, new_prompt):
        try:
            self.system_prompt = new_prompt
            self.screen.log_message("System prompt updated successfully")
        except Exception as e:
            self.screen.log_message(f"Error updating system prompt: {e}")

    def clear_history(self):
        """Clear both short-term and long-term history"""
        self.conversation_history = []
        self.long_term_history = []
        self.save_history(self.history_file, self.conversation_history)
        self.save_history(self.long_term_history_file, self.long_term_history)
        self.screen.log_message("History cleared")

class VoiceAssistantApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    try:
        # Check for Porcupine access key
        access_key = os.getenv('PORCUPINE_ACCESS_KEY')
        if not access_key:
            print("ERROR: PORCUPINE_ACCESS_KEY not set in environment")
            print("Please set the environment variable PORCUPINE_ACCESS_KEY with your Picovoice access key")
            print("You can get a free access key at https://console.picovoice.ai/")
            sys.exit(1)
            
        print("Starting Voice Assistant with Kivy...")
        print(f"Using Porcupine access key: {access_key[:4]}...{access_key[-4:]}")
        VoiceAssistantApp().run()
    except Exception as e:
        print(f"Startup error: {e}")
        traceback.print_exc()
    finally:
        if 'assistant' in locals():
            assistant.cleanup() 