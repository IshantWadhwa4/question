import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime
import os
import random
from syllabus import syllabus
import re
import requests
import base64
from PIL import Image
import io
import streamlit.components.v1 as components

# MathJax integration for proper math rendering
def render_mathjax():
    """Add MathJax support to the Streamlit app"""
    mathjax_script = """
    <script>
    window.MathJax = {
        tex: {
            inlineMath: [['$', '$'], ['\\(', '\\)']],
            displayMath: [['$$', '$$'], ['\\[', '\\]']],
            processEscapes: true,
            processEnvironments: true
        },
        options: {
            ignoreHtmlClass: ".*|",
            processHtmlClass: "arithmatex"
        }
    };
    </script>
    <script type="text/javascript" id="MathJax-script" async
        src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js">
    </script>
    """
    components.html(mathjax_script, height=0)

def render_math_content(content):
    """Render content with MathJax support"""
    if content.strip():
        math_html = f"""
        <div class="arithmatex">
        {content.replace(chr(10), '<br>')}
        </div>
        <script>
        if (window.MathJax) {{
            MathJax.typesetPromise();
        }}
        </script>
        """
        components.html(math_html, height=100)

# --- Image Processing Functions ---
def whiten_image_background(image: Image.Image) -> Image.Image:
    """
    Convert image background to pure white using PIL
    Works without any API calls!
    """
    # Convert to RGBA if not already
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Create a white background
    white_bg = Image.new('RGBA', image.size, (255, 255, 255, 255))
    
    # Method 1: Simple approach - make light colors white
    pixels = image.load()
    width, height = image.size
    
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            
            # If pixel is light (grayish/whitish background), make it pure white
            brightness = (r + g + b) / 3
            if brightness > 200:  # Adjust threshold as needed (0-255)
                pixels[x, y] = (255, 255, 255, 255)  # Pure white
    
    # Composite on white background
    result = Image.alpha_composite(white_bg, image)
    
    # Convert back to RGB
    return result.convert('RGB')

# --- AI OCR via Google Vision API (Optional) ---
def extract_text_from_image_google_vision(image_bytes: bytes) -> dict:
    """
    Use Google Vision API to extract text from images.
    Returns dict with keys: 'text' (plain text extracted)
    """
    try:
        from google.cloud import vision
        
        # Initialize the client (uses GOOGLE_APPLICATION_CREDENTIALS env var or service account)
        client = vision.ImageAnnotatorClient()
        
        # Create image object
        image = vision.Image(content=image_bytes)
        
        # Perform text detection
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if texts:
            # First annotation contains all detected text
            detected_text = texts[0].description
            return {
                "text": detected_text,
                "latex": detected_text,  # For compatibility, same as text
                "html": detected_text
            }
        else:
            return {"text": "", "latex": "", "html": ""}
            
    except ImportError:
        return {"error": "Google Vision API not installed. Run: pip install google-cloud-vision"}
    except Exception as e:
        return {"error": f"Google Vision error: {str(e)}"}

# Initialize Firebase (works with both local JSON file and Streamlit Cloud secrets)
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            # Prefer local JSON file for local development if present
            if os.path.exists("firebase-service-account.json"):
                cred = credentials.Certificate("firebase-service-account.json")
                firebase_admin.initialize_app(cred)
                st.success("✅ Connected to Firebase using local service account file")
            
            # Otherwise try Streamlit secrets (for deployment)
            elif "firebase" in st.secrets:
                firebase_config = {
                    "type": st.secrets["firebase"]["type"],
                    "project_id": st.secrets["firebase"]["project_id"],
                    "private_key_id": st.secrets["firebase"]["private_key_id"],
                    "private_key": st.secrets["firebase"]["private_key"].replace('\\n', '\n'),
                    "client_email": st.secrets["firebase"]["client_email"],
                    "client_id": st.secrets["firebase"]["client_id"],
                    "auth_uri": st.secrets["firebase"]["auth_uri"],
                    "token_uri": st.secrets["firebase"]["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
                    "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
                }
                cred = credentials.Certificate(firebase_config)
                firebase_admin.initialize_app(cred)
                st.success("✅ Connected to Firebase using Streamlit secrets")
            
            else:
                st.error("❌ Firebase credentials not found! Please configure Firebase secrets or add 'firebase-service-account.json' file.")
                st.info("For deployment, add Firebase credentials to Streamlit secrets. For local development, add the JSON file.")
                st.stop()
                
        except Exception as e:
            st.error(f"❌ Error initializing Firebase: {e}")
            st.stop()

# Get Firestore client
def get_firestore_client():
    return firestore.client()

def save_mcq_to_firebase(mcq_data):
    """Save MCQ data to Firebase Firestore"""
    try:
        db = get_firestore_client()
        # Add timestamp
        mcq_data['created_at'] = datetime.now()
        mcq_data['updated_at'] = datetime.now()
        

        
        # Add to Firestore
        doc_ref = db.collection('mcqs').add(mcq_data)
        return True, doc_ref[1].id
    except Exception as e:
        return False, str(e)

def query_mcqs_with_filters_firebase(difficulty=None, subject=None, subject_name=None, topic_name=None, question_type=None, year=None, tags=None):
    """Query MCQs from Firebase Firestore with specific filters"""
    try:
        db = get_firestore_client()
        query = db.collection('mcqs')
        
        # Apply filters to the Firestore query
        if difficulty and difficulty != "All":
            query = query.where('difficulty', '==', difficulty)
        
        # Use new structured fields if available, otherwise fall back to legacy subject field
        if subject_name and subject_name != "All":
            query = query.where('subject_name', '==', subject_name)
        elif subject and subject != "All":
            query = query.where('subject', '==', subject)
        
        if topic_name and topic_name != "All":
            query = query.where('topic_name', '==', topic_name)
        
        if question_type and question_type != "All":
            query = query.where('question_type', '==', question_type)
        
        if year and year != "All":
            query = query.where('year', '==', year)
        
        # Note: Firestore doesn't support array-contains with other filters efficiently
        # So we'll filter tags after the query for now
        docs = query.stream()
        
        mcqs = []
        for doc in docs:
            data = doc.to_dict()
            data['doc_id'] = doc.id
            

            
            # Apply tag filter if specified
            if tags and tags != "All":
                mcq_tags = [tag.lower() for tag in data.get('tags', [])]
                if tags.lower() not in mcq_tags:
                    continue
            
            mcqs.append(data)
        
        return mcqs
    except Exception as e:
        st.error(f"Error querying MCQs from Firebase: {e}")
        return []

def get_filter_options_firebase():
    """Get available filter options from Firebase MCQs"""
    try:
        db = get_firestore_client()
        docs = db.collection('mcqs').stream()
        
        difficulties = set()
        subjects = set()
        types = set()
        years = set()
        tags = set()
        
        for doc in docs:
            data = doc.to_dict()
            
            if data.get('difficulty'):
                difficulties.add(data['difficulty'])
            if data.get('subject'):
                subjects.add(data['subject'])
            if data.get('question_type'):
                types.add(data['question_type'])
            if data.get('year'):
                years.add(data['year'])
            if data.get('tags'):
                tags.update(data['tags'])
        
        return {
            "difficulties": sorted(list(difficulties)),
            "subjects": sorted(list(subjects)),
            "types": sorted(list(types)),
            "years": sorted(list(years), reverse=True),
            "tags": sorted(list(tags))
        }
        
    except Exception as e:
        st.error(f"Error getting filter options from Firebase: {e}")
        return {"difficulties": [], "subjects": [], "types": [], "years": [], "tags": []}

def select_random_mcqs_firebase(mcqs, count):
    """Randomly select specified number of MCQs"""
    if len(mcqs) <= count:
        return mcqs
    return random.sample(mcqs, count)

def main():
    st.set_page_config(
        page_title="Teacher MCQ Creator",
        page_icon="📚",
        layout="wide"
    )
    
    # Initialize MathJax for math rendering
    render_mathjax()
    
    # Initialize Firebase
    initialize_firebase()
    
    st.title("📚 Teacher MCQ Creator")
    st.markdown("Create and save Multiple Choice Questions to Firebase")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Create MCQ", "View Recent MCQs", "Random Question Selector"])
    
    with tab1:
        st.header("Create New MCQ")
        
        # Dynamic selections outside the form for real-time updates
        st.subheader("📋 Question Details")
        
        # Question type and year selection
        col1, col2 = st.columns(2)
        with col1:
            question_type = st.selectbox(
                "Question Type *",
                ["Question Bank", "PYQ", "Dummy"],
                help="Select whether this is from Question Bank or Previous Year Question"
            )
            st.session_state["question_type"] = question_type
            
            # Show testing note for Dummy type
            if question_type == "Dummy":
                st.markdown('<p style="color: #888888; font-size: 14px;">📝 For testing purposes only</p>', unsafe_allow_html=True)
        
        with col2:
            # Year dropdown (only if PYQ is selected)
            year = None
            if question_type == "PYQ":
                year_options = list(range(2015, 2025))  # 2015 to 2024
                year = st.selectbox(
                    "Year *",
                    year_options,
                    index=len(year_options)-1,  # Default to 2024 (last option)
                    help="Select the year for this Previous Year Question"
                )
                st.session_state["year"] = year
            else:
                st.selectbox("Year", ["Select Question Type first"], disabled=True)
        
        # Subject and topic selection
        col3, col4 = st.columns(2)
        with col3:
            subjects = list(syllabus.keys())
            selected_subject = st.selectbox(
                "Subject *",
                subjects,
                help="Select the subject for this question"
            )
            st.session_state["selected_subject"] = selected_subject
        
        with col4:
            # Topic selection (based on selected subject)
            topics = list(syllabus[selected_subject].keys())
            selected_topic = st.selectbox(
                "Topic *",
                topics,
                help="Select the specific topic within the subject"
            )
            st.session_state["selected_topic"] = selected_topic
        
        # Show topic description for reference
        if selected_topic:
            st.info(f"**📖 Topic Description:** {syllabus[selected_subject][selected_topic]['description']}")
        
        # For backward compatibility, combine subject and topic
        subject = f"{selected_subject} - {selected_topic}"
        
        st.divider()
        
        # Image Upload with Background Whitening
        st.subheader("🖼️ Add Image to Question")
        
        uploaded_img = st.file_uploader(
            "Upload question image (PNG/JPG)", 
            type=["png", "jpg", "jpeg"], 
            help="Upload an image to include with your question. Background will be automatically whitened."
        )
        
        processed_image = None
        if uploaded_img is not None:
            col_img1, col_img2 = st.columns(2)
            
            with col_img1:
                st.markdown("**Original Image:**")
                original_image = Image.open(uploaded_img)
                st.image(original_image, caption="Original", use_column_width=True)
            
            with col_img2:
                st.markdown("**Processed Image:**")
                # Process image - whiten background
                processed_image = whiten_image_background(original_image)
                st.image(processed_image, caption="White Background", use_column_width=True)
            
            # Option to use processed image
            if st.button("✅ Use This Image in Question"):
                # Convert to base64 for storage
                buffered = io.BytesIO()
                processed_image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                st.session_state["question_image"] = img_str
                st.success("✅ Image added! It will be included with your question.")
        
        # Show current question image if exists
        if st.session_state.get("question_image"):
            st.markdown("**Current Question Image:**")
            img_data = base64.b64decode(st.session_state["question_image"])
            st.image(img_data, caption="Will be saved with question", width=300)
            if st.button("🗑️ Remove Image"):
                del st.session_state["question_image"]
                st.rerun()
        

        
        # Create the form for question content
        with st.form("mcq_form", clear_on_submit=True):
            st.subheader("✏️ Question Content")
            
            # Show current selections in the form (using session state)
            col_summary1, col_summary2 = st.columns(2)
            with col_summary1:
                q_type = st.session_state.get("question_type", question_type)
                yr = st.session_state.get("year", year)
                st.info(f"**Question Type:** {q_type}" + (f" | **Year:** {yr}" if yr else ""))
            with col_summary2:
                subj = st.session_state.get("selected_subject", selected_subject)
                topic = st.session_state.get("selected_topic", selected_topic)
                st.info(f"**Subject:** {subj} | **Topic:** {topic}")
            
            st.divider()
            
            # Question input
            st.subheader("📝 Question")
            question = st.text_area(
                "Question *",
                value=st.session_state.get("prefill_question", ""),
                placeholder="Enter your question here...\n\nExample:\nFind the acceleration when F = 20N and m = 5kg using F = ma\n\nFor math symbols, use the copy-paste buttons above: x², √x, π, etc.",
                height=120,
                help="Use the copy-paste buttons above for math symbols and formulas"
            )
            
            # Live MathJax preview of the question
            if question.strip():
                st.markdown("**MathJax Preview:**")
                render_math_content(question)
            
            # Four options with LaTeX support
            st.subheader("📋 Answer Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                option_a = st.text_input(
                    "Option A *",
                    placeholder="e.g., a = 4 m/s² or 6.02×10²³",
                    key="opt_a",
                    help="Use copy-paste buttons for symbols: x², √x, π, etc."
                )
                option_c = st.text_input(
                    "Option C *",
                    placeholder="e.g., √25 = 5 or H₂O",
                    key="opt_c",
                    help="Use copy-paste buttons for symbols: x², √x, π, etc."
                )
            
            with col2:
                option_b = st.text_input(
                    "Option B *",
                    placeholder="e.g., E = mc² or 3×10⁸ m/s",
                    key="opt_b",
                    help="Use copy-paste buttons for symbols: x², √x, π, etc."
                )
                option_d = st.text_input(
                    "Option D *",
                    placeholder="e.g., v = 25 m/s or CO₂",
                    key="opt_d",
                    help="Use copy-paste buttons for symbols: x², √x, π, etc."
                )
            
            # MathJax preview for options if they contain content
            if any([option_a.strip(), option_b.strip(), option_c.strip(), option_d.strip()]):
                st.markdown("**Options MathJax Preview:**")
                col_prev1, col_prev2 = st.columns(2)
                with col_prev1:
                    if option_a.strip():
                        st.markdown("**A:**")
                        render_math_content(option_a)
                    if option_c.strip():
                        st.markdown("**C:**")
                        render_math_content(option_c)
                with col_prev2:
                    if option_b.strip():
                        st.markdown("**B:**")
                        render_math_content(option_b)
                    if option_d.strip():
                        st.markdown("**D:**")
                        render_math_content(option_d)
            
            # Correct answer
            correct_answer = st.selectbox(
                "Correct Answer *",
                ["A", "B", "C", "D"],
                help="Select the correct option"
            )
            
            # Difficulty level
            difficulty = st.selectbox(
                "Difficulty Level *",
                ["Easy", "Medium", "Hard"],
                help="Select the difficulty level of this question"
            )
            
            # Solution
            st.subheader("💡 Solution")
            solution = st.text_area(
                "Solution *",
                placeholder="Provide detailed solution/explanation...\n\nExample:\nStep 1: Apply the formula F = ma\nStep 2: Substitute values: F = 5 × 4 = 20N\nStep 3: Therefore, the force is 20N\n\nUse copy-paste buttons for symbols: ×, ², π, etc.",
                height=150,
                help="Show step-by-step working. Use the copy-paste buttons for math symbols."
            )
            
            # MathJax preview for solution if it contains content
            if solution.strip():
                st.markdown("**Solution MathJax Preview:**")
                render_math_content(solution)
            
            # Tags (additional field)
            tags = st.text_input(
                "Tags",
                placeholder="e.g., algebra, mechanics, organic chemistry (comma separated)",
                help="Optional: Add tags for better categorization"
            )
            
            # Submit button
            submitted = st.form_submit_button(
                "Save MCQ",
                type="primary",
                use_container_width=True
            )
            
            if submitted:
                # Get values from session state for validation
                q_type = st.session_state.get("question_type", "Question Bank")
                yr = st.session_state.get("year", None)
                subj = st.session_state.get("selected_subject", "")
                topic = st.session_state.get("selected_topic", "")
                
                # Validation
                if not all([question, option_a, option_b, option_c, option_d, solution]):
                    st.error("Please fill in all required fields marked with *")
                elif q_type == "PYQ" and not yr:
                    st.error("Please provide the year for PYQ questions")
                else:
                    # Prepare data for Firebase
                    mcq_data = {
                        "question": question.strip(),
                        "options": {
                            "A": option_a.strip(),
                            "B": option_b.strip(),
                            "C": option_c.strip(),
                            "D": option_d.strip()
                        },
                        "correct_answer": correct_answer,
                        "difficulty": difficulty,
                        "solution": solution.strip(),
                        "question_type": q_type,
                        "year": yr if q_type == "PYQ" else None,
                        "subject": f"{subj} - {topic}" if subj and topic else None,  # Combined for backward compatibility
                        "subject_name": subj,  # Separate subject field
                        "topic_name": topic,  # Separate topic field
                        "tags": [tag.strip() for tag in tags.split(",")] if tags else []
                    }
                    
                    # Only add question_image if there's actual image data
                    if st.session_state.get("question_image"):
                        mcq_data["question_image"] = st.session_state.get("question_image")
                    
                    # Save to Firebase
                    with st.spinner("Saving MCQ to Firebase..."):
                        success, result = save_mcq_to_firebase(mcq_data)
                    
                    if success:
                        st.success(f"✅ MCQ saved successfully! Document ID: {result}")
                        # Clear the question image from session state after successful save
                        if "question_image" in st.session_state:
                            del st.session_state["question_image"]
                        st.balloons()
                    else:
                        st.error(f"❌ Error saving MCQ: {result}")

    # Display recent MCQs (optional)
    if st.button("View Recent MCQs"):
        try:
            db = get_firestore_client()
            docs = db.collection('mcqs').order_by('created_at', direction=firestore.Query.DESCENDING).limit(5).stream()
            
            st.header("Recent MCQs")
            for doc in docs:
                data = doc.to_dict()
                with st.expander(f"Q: {data['question'][:100]}..."):
                    # Display question image first if exists
                    if data.get('question_image'):
                        try:
                            img_data = base64.b64decode(data['question_image'])
                            st.image(img_data, caption="Question Image", width=400)
                        except Exception as e:
                            st.error(f"Error loading image: {str(e)}")
                    
                    st.write(f"**Question:** {data['question']}")
                    st.write(f"**Difficulty:** {data['difficulty']}")
                    st.write(f"**Type:** {data['question_type']}")
                    if data.get('year'):
                        st.write(f"**Year:** {data['year']}")
                    st.write(f"**Correct Answer:** {data['correct_answer']}")
                    st.write(f"**Created:** {data['created_at']}")
        except Exception as e:
            st.error(f"Error fetching recent MCQs: {e}")

    with tab3:
        st.header("🎲 Random Question Selector")
        st.markdown("Query and select random questions from your Firebase question bank")
        
        # Get available filter options
        with st.spinner("Loading filter options..."):
            filter_options = get_filter_options_firebase()
        
        # Check if any MCQs exist
        total_mcqs = query_mcqs_with_filters_firebase()  # Query all without filters to get count
        
        if not total_mcqs:
            st.info("No MCQs available. Create some MCQs first in the 'Create MCQ' tab!")
        else:
            st.write(f"Total questions in Firebase: **{len(total_mcqs)}**")
            
            # Filter options
            st.subheader("🔍 Database Query Filters")
            
            # First row of filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                selected_difficulty = st.selectbox(
                    "Difficulty", 
                    ["All"] + filter_options["difficulties"],
                    help="Filter by difficulty level"
                )
            
            with col2:
                filter_subject = st.selectbox(
                    "Subject", 
                    ["All"] + list(syllabus.keys()),
                    help="Filter by subject"
                )
            
            with col3:
                # Topic filter (depends on selected subject)
                filter_topic = "All"
                if filter_subject != "All":
                    topics = list(syllabus[filter_subject].keys())
                    filter_topic = st.selectbox(
                        "Topic", 
                        ["All"] + topics,
                        help="Filter by specific topic"
                    )
                else:
                    st.selectbox("Topic", ["All"], help="Select a subject first", disabled=True)
            
            # Second row of filters
            col4, col5, col6 = st.columns(3)
            
            with col4:
                selected_type = st.selectbox(
                    "Question Type", 
                    ["All"] + filter_options["types"],
                    help="Filter by question type"
                )
            
            with col5:
                selected_year = st.selectbox(
                    "Year", 
                    ["All"] + [str(year) for year in filter_options["years"]],
                    help="Filter by year (for PYQ questions)"
                )
                if selected_year != "All":
                    selected_year = int(selected_year)
            
            with col6:
                selected_tag = st.selectbox(
                    "Tag", 
                    ["All"] + filter_options["tags"],
                    help="Filter by specific tag"
                )
            
            # Query with filters
            with st.spinner("Querying Firebase..."):
                filtered_mcqs = query_mcqs_with_filters_firebase(
                    difficulty=selected_difficulty if selected_difficulty != "All" else None,
                    subject_name=filter_subject if filter_subject != "All" else None,
                    topic_name=filter_topic if filter_topic != "All" else None,
                    question_type=selected_type if selected_type != "All" else None,
                    year=selected_year if selected_year != "All" else None,
                    tags=selected_tag if selected_tag != "All" else None
                )
            
            st.write(f"Questions matching query: **{len(filtered_mcqs)}**")
            
            if filtered_mcqs:
                # Selection options
                st.subheader("📝 Random Selection")
                col1, col2 = st.columns(2)
                
                with col1:
                    num_questions = st.number_input(
                        "Number of questions to select",
                        min_value=1,
                        max_value=len(filtered_mcqs),
                        value=min(5, len(filtered_mcqs)),
                        help=f"Maximum available: {len(filtered_mcqs)}"
                    )
                
                with col2:
                    if st.button("🎲 Generate Random Selection", type="primary"):
                        st.session_state.selected_mcqs_firebase = select_random_mcqs_firebase(filtered_mcqs, num_questions)
                        st.session_state.selection_generated_firebase = True
                
                # Display selected questions
                if st.session_state.get('selection_generated_firebase', False) and st.session_state.get('selected_mcqs_firebase'):
                    selected_mcqs = st.session_state.selected_mcqs_firebase
                    
                    st.subheader(f"✅ Selected Questions ({len(selected_mcqs)})")
                    
                    # Download options
                    col1, col2 = st.columns(2)
                    with col1:
                        # Prepare data for download
                        download_data = {
                            "selection_info": {
                                "total_questions": len(selected_mcqs),
                                "filters_applied": {
                                    "difficulty": selected_difficulty,
                                    "subject": selected_subject,
                                    "question_type": selected_type,
                                    "year": selected_year
                                },
                                "generated_at": datetime.now().isoformat(),
                                "source": "Firebase"
                            },
                            "questions": selected_mcqs
                        }
                        
                        st.download_button(
                            label="📄 Download as JSON",
                            data=json.dumps(download_data, indent=2, default=str),
                            file_name=f"firebase_random_mcqs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    
                    with col2:
                        if st.button("🔄 Generate New Selection"):
                            st.session_state.selected_mcqs_firebase = select_random_mcqs_firebase(filtered_mcqs, num_questions)
                            st.rerun()
                    
                    # Display questions
                    for i, mcq in enumerate(selected_mcqs, 1):
                        with st.expander(f"Question {i}: {mcq['question'][:80]}{'...' if len(mcq['question']) > 80 else ''}"):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                # Display question image first if exists
                                if mcq.get('question_image'):
                                    try:
                                        img_data = base64.b64decode(mcq['question_image'])
                                        st.image(img_data, caption="Question Image", width=400)
                                    except Exception as e:
                                        st.error(f"Error loading image: {str(e)}")
                                
                                st.markdown(f"**Q{i}:** {mcq['question']}")
                                
                                st.markdown("**Options:**")
                                for opt_key, opt_val in mcq['options'].items():
                                    if opt_key == mcq['correct_answer']:
                                        st.markdown(f"**{opt_key}:** {opt_val} ✅")
                                    else:
                                        st.markdown(f"**{opt_key}:** {opt_val}")
                                
                                # Toggle solution visibility
                                solution_key = f"show_solution_{i}"
                                if solution_key not in st.session_state:
                                    st.session_state[solution_key] = False
                                
                                if st.button("💡 Toggle Solution", key=f"solution_{i}"):
                                    st.session_state[solution_key] = not st.session_state[solution_key]
                                
                                if st.session_state[solution_key]:
                                    st.markdown(f"**Answer:** {mcq['correct_answer']}")
                                    st.markdown(f"**Solution:** {mcq['solution']}")
                            
                            with col2:
                                st.markdown(f"**Difficulty:** {mcq['difficulty']}")
                                st.markdown(f"**Type:** {mcq['question_type']}")
                                if mcq.get('year'):
                                    st.markdown(f"**Year:** {mcq['year']}")
                                # Display subject and topic information
                                if mcq.get('subject_name') and mcq.get('topic_name'):
                                    st.markdown(f"**Subject:** {mcq['subject_name']}")
                                    st.markdown(f"**Topic:** {mcq['topic_name']}")
                                elif mcq.get('subject'):
                                    st.markdown(f"**Subject:** {mcq['subject']}")
                                if mcq.get('tags'):
                                    st.markdown(f"**Tags:** {', '.join(mcq['tags'])}")
                                st.markdown(f"**Firebase ID:** {mcq.get('doc_id', 'N/A')}")
            else:
                st.warning("No questions match the selected query filters. Try adjusting your criteria.")

if __name__ == "__main__":
    main() 
