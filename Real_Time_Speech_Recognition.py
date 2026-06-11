
import streamlit as st
import speech_recognition as sr
import queue
import time
import threading  # Imported but used implicitly by listen_in_background
from pydub import AudioSegment
from io import BytesIO
import os

# Initialize session state variables
if 'q' not in st.session_state:
    st.session_state.q = queue.Queue()

if 'text' not in st.session_state:
    st.session_state.text = ""

if 'feedback' not in st.session_state:
    st.session_state.feedback = ""

if 'file_text' not in st.session_state:
    st.session_state.file_text = ""

if 'file_feedback' not in st.session_state:
    st.session_state.file_feedback = ""

if 'listening' not in st.session_state:
    st.session_state.listening = False

if 'stop_listening' not in st.session_state:
    st.session_state.stop_listening = None

# App title
st.title("Real-Time Speech-to-Text System")

# Allow user to select recognition method
method = st.selectbox("Select Recognition Method", ["Google", "Sphinx"],
                      help="Google: Online, more accurate. Sphinx: Offline, may require pocketsphinx.")

# Section for live microphone input
st.header("Live Microphone Transcription")

# Buttons for start/stop
col1, col2 = st.columns(2)
with col1:
    start_button = st.button("Start Listening")
with col2:
    stop_button = st.button("Stop Listening")

# Handle start button
if start_button and not st.session_state.listening:
    # Check for Sphinx installation
    if method == "Sphinx":
        try:
            from pocketsphinx import pocketsphinx  # Check if importable
        except ImportError:
            st.error("Pocketsphinx is not installed or not found. Please install it via 'pip install pocketsphinx' and restart the app.")
            st.stop()  # Stop execution to prevent further issues

    st.session_state.listening = True
    st.session_state.text = ""  # Clear previous text
    st.session_state.feedback = "Adjusting for ambient noise... Please wait."
    
    # Capture the queue in the main thread for use in callback
    q = st.session_state.q
    
    def callback(recognizer, audio):
        try:
            if method == "Google":
                text = recognizer.recognize_google(audio)
            elif method == "Sphinx":
                text = recognizer.recognize_sphinx(audio)
            q.put(text)
        except sr.UnknownValueError:
            q.put("Error: Could not understand audio.")
        except sr.RequestError as e:
            q.put(f"Error: Service error - {e}")
        except Exception as e:
            q.put(f"Error: Unexpected error - {e}")

    # Initialize recognizer and microphone
    r = sr.Recognizer()
    m = sr.Microphone()
    with m as source:
        r.adjust_for_ambient_noise(source, duration=1)  # Adjust for noise
    
    st.session_state.feedback = "Listening... Speak now!"
    st.session_state.stop_listening = r.listen_in_background(m, callback)
    
    st.rerun()  # Rerun to update UI immediately

# Handle stop button
if stop_button and st.session_state.listening:
    if st.session_state.stop_listening is not None:
        st.session_state.stop_listening(wait_for_stop=False)
    st.session_state.listening = False
    st.session_state.feedback = "Stopped listening."
    st.session_state.stop_listening = None
    st.rerun()  # Rerun to update UI

# Display status
if st.session_state.listening:
    st.success("Status: Listening...")
else:
    st.info("Status: Not listening.")

# Placeholders for live text and feedback
st.subheader("Transcribed Text (Live)")
text_placeholder = st.text_area("Transcribed Text (Live, hidden label)", st.session_state.text, height=300, disabled=True, label_visibility="collapsed")

st.subheader("Feedback & Errors (Live)")
feedback_placeholder = st.text_area("Feedback & Errors (Live, hidden label)", st.session_state.feedback, height=150, disabled=True, label_visibility="collapsed")

# If listening, poll the queue for updates
if st.session_state.listening:
    updated = False
    while not st.session_state.q.empty():
        msg = st.session_state.q.get()
        if isinstance(msg, str) and msg.startswith("Error:"):
            st.session_state.feedback += msg + "\n"
        else:
            st.session_state.text += msg + "\n"
        updated = True
    
    # Update placeholders if needed (though text_area is bound to session_state)
    if updated:
        st.rerun()
    
    # Sleep briefly and rerun for polling
    time.sleep(0.5)
    st.rerun()

# Section for audio file upload
st.header("Upload Audio File for Transcription")

uploader = st.file_uploader("Choose an audio file (supports WAV, OGG, MP3, FLAC, AIFF, and more with pydub/ffmpeg)", type=None)

if uploader is not None:
    transcribe_button = st.button("Transcribe File")
    
    if transcribe_button:
        # Clear previous file results
        st.session_state.file_text = ""
        st.session_state.file_feedback = "Processing audio file..."
        
        try:
            # Validate file size
            if uploader.size == 0:
                raise ValueError("Uploaded file is empty.")
            
            # Use pydub to load and convert to WAV in memory
            file_extension = uploader.name.split('.')[-1].lower() if '.' in uploader.name else None
            try:
                audio_segment = AudioSegment.from_file(uploader, format=file_extension)
            except Exception as e:
                # Fallback: Try loading without specifying format
                uploader.seek(0)  # Reset file pointer
                audio_segment = AudioSegment.from_file(uploader)
            
            wav_io = BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_io.seek(0)
            
            # Check if converted WAV is empty
            if len(wav_io.getvalue()) == 0:
                raise ValueError("Converted audio is empty. The file may be corrupted or in an unsupported format.")
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                audio = r.record(source)
            
            # Check if audio data is empty
            if len(audio.get_raw_data()) == 0:
                raise ValueError("Audio data is empty. The file may be corrupted or empty.")
            
            if method == "Google":
                text = r.recognize_google(audio)
            elif method == "Sphinx":
                text = r.recognize_sphinx(audio)
            
            st.session_state.file_text = text
            st.session_state.file_feedback = "Transcription complete."
        
        except sr.UnknownValueError:
            st.session_state.file_feedback = "Error: Could not understand audio."
        except sr.RequestError as e:
            st.session_state.file_feedback = f"Error: Service error - {e}"
        except ValueError as ve:
            st.session_state.file_feedback = f"Error: {ve}"
        except Exception as e:
            st.session_state.file_feedback = (
                f"Error: Unexpected error - {e}. Ensure ffmpeg is installed and added to PATH for MP3/OGG support. "
                "Windows: Add C:\\ffmpeg\\bin to PATH. Linux/Mac: Install via 'sudo apt-get install ffmpeg' or equivalent."
            )
        
        st.rerun()

# Placeholders for file text and feedback
st.subheader("Transcribed Text (File)")
file_text_placeholder = st.text_area("Transcribed Text (File, hidden label)", st.session_state.file_text, height=300, disabled=True, label_visibility="collapsed")

st.subheader("Feedback & Errors (File)")
file_feedback_placeholder = st.text_area("Feedback & Errors (File, hidden label)", st.session_state.file_feedback, height=150, disabled=True, label_visibility="collapsed")

# End of main app logic
