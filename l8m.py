import streamlit as st
import music21
import requests
import tempfile
import os
import streamlit.components.v1 as components

# --- Configuration ---
st.set_page_config(page_title="MusicXML AI Editor", layout="wide")

# --- Functions ---
def get_syllables_raw(text):
    if not text or not text.strip():
        return "Error: lyrics input is empty"

    prompt = (
        f"I'd like you to split these lyrics, demarkated by ### into syllables using hyphens, retaining the original case: ###{text}###. Your response should only contain the hyphenated text."
        "Please follow these guidelines: 1. Use an online dictionary or syllable counter tool to double-check the syllable count for each word. "
        "2. Be consistent with proper pronunciation and stress marks. "
        "3. Consider 'are' as a single syllable word. "
        "4. Introduce hyphens only between syllables of a word. Dont put hyphens between words that exist seperately in the input lyrics. For example, don't put a hyphen between 'great' and 'in-deed'"
    )

    try:
        r = requests.post(
            'http://localhost:11434/api/generate',
            json={"model": "mistral-nemo:12b", "prompt": prompt, "stream": False},
            timeout=60,
        )
        r.raise_for_status()

        data = r.json()
        if not isinstance(data, dict):
            return f"Error: unexpected response body type {type(data).__name__} - {data}"

        if 'response' not in data:
            return f"Error: missing key 'response' in AI response - {data}"

        output = data['response']
        if not isinstance(output, str):
            return f"Error: expected 'response' as string but got {type(output).__name__} - {output}"

        return output.strip()

    except requests.exceptions.Timeout:
        return f"Error: timeout while contacting AI model endpoint (http://localhost:11434/api/generate)"
    except requests.exceptions.RequestException as e:
        return f"Error: request exception: {e}"
    except ValueError as e:
        return f"Error: failed to parse JSON from model response: {e}"
    except Exception as e:
        return f"Error: unexpected exception: {e}"
 

def apply_multi_voice_lyrics(score, voice_lyrics_list):
    """Aligns specific hyphenated text lists to each corresponding part in the score."""
    for part_idx, hyphenated_text in enumerate(voice_lyrics_list):
        if part_idx < len(score.parts):
            tokens = hyphenated_text.split()
            part = score.parts[part_idx]
            notes = [n for n in part.flatten().notes if n.isNote]
            
            # Clear existing lyrics for this part first to avoid overlaps
            for n in notes:
                n.lyric = None
                
            for i, n in enumerate(notes):
                if i < len(tokens):
                    n.lyric = tokens[i]
    return score

def score_to_string(score):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp:
        tmp_path = tmp.name
    try:
        score.write('musicxml', fp=tmp_path)
        with open(tmp_path, 'r', encoding='utf-8') as f:
            xml_str = f.read()
            xml_str = xml_str.replace("Music21", "")
        return xml_str
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def trim_leading_empty_measures(score):
    earliest_measure_num = None

    # Find earliest measure across all parts that contains a note
    for part in score.parts:
        for m in part.getElementsByClass('Measure'):
            has_note = any(n.isNote for n in m.notes)
            if has_note:
                if earliest_measure_num is None or m.number < earliest_measure_num:
                    earliest_measure_num = m.number
                break  # move to next part after first note

    # If no notes found at all, do nothing
    if earliest_measure_num is None:
        return score

    # Remove all measures before this number
    for part in score.parts:
        measures_to_remove = [
            m for m in part.getElementsByClass('Measure')
            if m.number < earliest_measure_num
        ]
        for m in measures_to_remove:
            part.remove(m)

    return score

# --- UI Layout ---
st.title("🎵 Multi-Voice MusicXML AI Editor")

if 'score' not in st.session_state:
    st.session_state.score = None
if 'voice_inputs' not in st.session_state:
    st.session_state.voice_inputs = {}

# Row 1: File and Main Lyrics
col1, col2, col3 = st.columns([1, 1, 0.7])

with col1:
    uploaded_file = st.file_uploader("Upload MusicXML", type=['xml', 'musicxml'])
    if uploaded_file and st.session_state.score is None:
        score = music21.converter.parse(uploaded_file.read())
        score = trim_leading_empty_measures(score)
        st.session_state.score = score
    
    if st.button("🗑️ Clear Score", use_container_width=True):
        st.session_state.score = None
        st.session_state.voice_inputs = {}
        st.rerun()

with col2:
    lyrics_input = st.text_area("1. Paste Raw Lyrics", placeholder="Enter lyrics...", height=300)

with col3:
    st.write("3. Actions")
    syllabify_btn = st.button("🪄 AI Syllabify All Voices", use_container_width=True)
    

# Row 2: Dynamic AssignEditors
if st.session_state.score:
    num_parts = len(st.session_state.score.parts)
    st.write(f"### 2. AssignEditors ({num_parts} Voices Detected)")
    
    # Create columns for the number of voices
    voice_cols = st.columns(num_parts)
    
    # Handle AI Syllabify action
    if syllabify_btn:
        llm_output = get_syllables_raw(lyrics_input)
        llm_output = llm_output.replace('-', '-  ').replace('  ', ' ')
        if llm_output.startswith("Error:"):
            st.error(llm_output)
        else:
            st.success("AI syllabification succeeded")
            # Update the session state keys directly used by the text areas
            for j in range(num_parts):
                st.session_state[f"voice_{j}"] = llm_output


    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        refresh_btn = st.button("🔄 Preview Alignment", use_container_width=True)
    with col2:
        extract_btn = st.button("📥 Extract Lyrics from Score", use_container_width=True)
    with col3:
        apply_btn = st.button("💾 Apply Edits to Score", use_container_width=True, type="primary")

    # Logic: Extract Lyrics from Score
    if extract_btn:
        for i, part in enumerate(st.session_state.score.parts):
            notes = [n for n in part.flatten().notes if n.isNote]
            lyrics = [n.lyric for n in notes if n.lyric]
            st.session_state[f"voice_{i}"] = " ".join(lyrics)
    
    # Render text areas for each voice
    current_lyrics = []
    for i in range(num_parts):
        with voice_cols[i]:
            part_name = st.session_state.score.parts[i].partName or f"Voice {i+1}"
            
            # Using the 'key' allows the Syllabify button to push data directly into the widget
            # We remove the 'value' argument to let 'key' manage the state
            st.text_area(f"Lyrics for {part_name}", height=300, key=f"voice_{i}")
            
            # Retrieve the current content of the box for the preview/apply logic
            current_lyrics.append(st.session_state.get(f"voice_{i}", ""))

    # Logic: Refresh Preview
    if refresh_btn:
        st.session_state.score = apply_multi_voice_lyrics(st.session_state.score, current_lyrics)


    # --- Preview ---
    st.divider()
    try:
        # Inside your Preview Section try/except block:
        xml_data = score_to_string(st.session_state.score)
        xml_str_escaped = xml_data.replace('`', '\\`')

        # We pull the name to use as a file title in JS
        js_filename = f"1{uploaded_file.name}.pdf" if uploaded_file else "score.pdf"

        osmd_html = f"""
        <div id="pdf-wrapper" style="width: 210mm; margin: auto; background: white; padding: 10mm;">
            <div id="osmd-container"></div>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/opensheetmusicdisplay@latest/build/opensheetmusicdisplay.min.js"></script>
        
        <script>
            const osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay("osmd-container", {{
                autoResize: true,
                drawTitle: false,
            }});
            
            osmd.load(`{xml_str_escaped}`).then(() => {{
                osmd.Zoom = 0.7;
                osmd.render();
            }});

            // Function to trigger PDF conversion of the rendered container
            function downloadPDF() {{
                const element = document.getElementById('pdf-wrapper');
                const opt = {{
                    margin:       0.3,
                    filename:     '{js_filename}',
                    image:        {{ type: 'jpeg', quality: 0.98 }},
                    html2canvas:  {{ scale: 1, useCORS: true, scrollX: 0, scrollY: 0, windowWidth: document.getElementById('pdf-wrapper').scrollWidth }},
                    jsPDF:        {{ unit: 'mm', format: 'a4', orientation: 'portrait' }},
                    pagebreak:    {{ mode: ['avoid-all', 'css', 'legacy'] }}
                }};                
                html2pdf().from(element).set(opt).save();
            }}
            
            // Expose function globally if needed
            window.downloadPDF = downloadPDF;
        </script>
        
        <button onclick="downloadPDF()" style="margin-top:10px; padding: 5px 10px; background-color: #262730; color: white; border: 1px solid #464855; border-radius: 4px; cursor: pointer;">
            📄 Save Sheet Music as PDF
        </button>
        """
        components.html(osmd_html, height=1000, scrolling=True)
    except Exception as e:
        st.error(f"Error generating preview: {e}")

    # Logic: Final Export
    # Logic: Apply + Immediate Download
    if apply_btn and uploaded_file:
        st.session_state.score = apply_multi_voice_lyrics(st.session_state.score, current_lyrics)
        final_xml = score_to_string(st.session_state.score)

        st.download_button(
            label="⬇️ Download Final MusicXML",
            data=final_xml,
            file_name=f"1{uploaded_file.name}",
            mime="application/xml",
            key="auto_download_xml"
        )