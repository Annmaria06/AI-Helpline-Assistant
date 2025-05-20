import streamlit as st
import folium
from streamlit_folium import st_folium
import sounddevice as sd
import soundfile as sf

from src.audio_processing import save_audio
from src.transcription import transcribe_audio
from src.entity_extraction import extract_entities
from src.emotion_detection import detect_emotion
from src.map_utils import get_coordinates, get_nearby_help

# Constants
SAMPLE_RATE = 16000  # Or import from src.config if defined there

def display_folium_map(lat, lon, help_centers):
    """Displays a map with markers for reported location and nearby help centers."""
    m = folium.Map(location=[lat, lon], zoom_start=14)
    folium.Marker([lat, lon], popup="Reported Location", tooltip="Reported Location",
                  icon=folium.Icon(color="red", icon="info-sign")).add_to(m)
    for center in help_centers:
        folium.Marker([center["lat"], center["lon"]], popup=center["name"], tooltip=center["name"],
                      icon=folium.Icon(color="blue", icon="plus-sign")).add_to(m)
    st_folium(m, width=700, height=500)

def record_audio(duration=5, filename="recorded_voice.wav"):
    """Records audio from microphone for a specified duration."""
    st.info(f"🎙️ Recording for {duration} seconds... Speak now!")
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    sf.write(filename, audio.squeeze(), SAMPLE_RATE)
    return filename

# Streamlit page configuration
st.set_page_config(page_title="🚨 Emergency Voice Helpdesk", layout="wide")

# Initialize session state variables
for key in ["audio_processed", "transcript", "emotion", "confidence", "entities", "location_text", "coords", "help_centers"]:
    if key not in st.session_state:
        st.session_state[key] = None

# Custom CSS for layout
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .hero { background: linear-gradient(90deg, #ff4d4d, #ff9999); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem; }
    .badge { display: inline-block; padding: 0.4em 0.8em; font-weight: bold; border-radius: 8px; color: white; font-size: 1rem; }
    .emotion { background-color: #6a5acd; }
    .card { padding: 1rem; border-radius: 10px; background-color: #f0f2f6; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); margin-bottom: 1rem; }
    .confidence-text { font-size: 0.85rem; color: #666; margin-top: 0.3rem; }
    </style>
""", unsafe_allow_html=True)

# Display hero banner
st.markdown("""
<div class='hero'>
    <h1>🚨 Emergency Voice Helpdesk</h1>
</div>
""", unsafe_allow_html=True)

# Audio input section
st.markdown("### 🎙️ Upload or Record Voice Message")

audio_input = None
auto_trigger = False

upload_col, record_col = st.columns(2)

with upload_col:
    st.markdown("#### 📁 Upload Audio File")
    audio_file = st.file_uploader("Upload WAV or MP3", type=["wav", "mp3"])
    if audio_file:
        audio_input = save_audio(audio_file)
        st.audio(audio_input, format="audio/wav")
        auto_trigger = True

with record_col:
    st.markdown("#### 🎤 Record Voice Live")
    duration = st.slider("Select Recording Duration (seconds)", min_value=3, max_value=15, value=5)
    if st.button("🔴 Record Now"):
        recorded_path = record_audio(duration)
        audio_input = recorded_path
        st.audio(recorded_path, format="audio/wav")
        auto_trigger = True

# Process audio input
if audio_input or auto_trigger:
    with st.spinner("Analyzing and locating help..."):
        transcript = transcribe_audio(audio_input)
        emotion, confidence = detect_emotion(audio_input)
        entities = extract_entities(transcript)

        location_text = entities.get("location")
        coords = get_coordinates(location_text) if location_text else None
        help_centers = get_nearby_help(*coords, type="hospital") if coords else []

        st.session_state.update({
            "transcript": transcript,
            "emotion": emotion,
            "confidence": confidence,
            "entities": entities,
            "location_text": location_text,
            "coords": coords,
            "help_centers": help_centers,
            "audio_processed": True,
        })
    st.success("✅ Emergency Analyzed")

# Display results
if st.session_state.audio_processed:
    st.markdown("## 📝 Emergency Summary")

    priority_styles = {
        "Fearful": {"level": "High", "color": "#e60000", "emoji": "😰"},
        "Angry": {"level": "High", "color": "#e60000", "emoji": "😠"},
        "Sad": {"level": "Medium", "color": "#ffa500", "emoji": "😢"},
        "Disgust": {"level": "Medium", "color": "#ffa500", "emoji": "🤢"},
        "Surprised": {"level": "Medium", "color": "#ffa500", "emoji": "😮"},
        "Neutral": {"level": "Low", "color": "#2eb82e", "emoji": "😐"},
        "Calm": {"level": "Low", "color": "#2eb82e", "emoji": "😌"},
        "Happy": {"level": "Low", "color": "#2eb82e", "emoji": "😄"},
    }

    emo = st.session_state.emotion
    style = priority_styles.get(emo, {"level": "Low", "color": "gray", "emoji": "🧠"})

    t_col, e_col, emo_col = st.columns([1.5, 1.5, 1])

    with t_col:
        st.markdown("#### 💬 Transcription")
        st.markdown(f"<div class='card'><p><strong>Caller:</strong> {st.session_state.transcript}</p></div>", unsafe_allow_html=True)

    with e_col:
        st.markdown("#### 🧾 Extracted Entities")
        st.json(st.session_state.entities)

    with emo_col:
        st.markdown(f"<div style='text-align: right;'><div class='badge emotion' style='background-color: {style['color']};'>{style['emoji']} {emo} (Priority: {style['level']})</div><div class='confidence-text'>Confidence: {st.session_state.confidence:.2f}</div></div>", unsafe_allow_html=True)

    if st.session_state.location_text and st.session_state.coords:
        st.markdown("### 🗺️ Location & Nearby Hospitals")
        lat, lon = st.session_state.coords
        st.success(f"📍 **{st.session_state.location_text}** located at ({lat:.4f}, {lon:.4f})")

        map_col, list_col = st.columns([1.2, 1])

        with map_col:
            display_folium_map(lat, lon, st.session_state.help_centers)

        with list_col:
            if st.session_state.help_centers:
                st.markdown("#### 🏥 Nearest Hospitals")
                for center in st.session_state.help_centers:
                    st.markdown(f"<div class='card'><strong>{center['name']}</strong><br/>📍 ({center['lat']:.4f}, {center['lon']:.4f})</div>", unsafe_allow_html=True)
            else:
                st.info("No hospitals found nearby.")
    else:
        st.warning("⚠️ Location not found in the audio.")
