import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime
import os
import random
from syllabus import syllabus

# Initialize Firebase (works with both local JSON file and Streamlit Cloud secrets)
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            # Try Streamlit secrets first (for deployment)
            if "firebase" in st.secrets:
                # Use secrets from Streamlit Cloud
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
            
            # Fallback to local JSON file (for local development)
            elif os.path.exists("firebase-service-account.json"):
                cred = credentials.Certificate("firebase-service-account.json")
                firebase_admin.initialize_app(cred)
                st.success("✅ Connected to Firebase using local service account file")
            
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
                ["Question Bank", "PYQ"],
                help="Select whether this is from Question Bank or Previous Year Question"
            )
        
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
        
        with col4:
            # Topic selection (based on selected subject)
            topics = list(syllabus[selected_subject].keys())
            selected_topic = st.selectbox(
                "Topic *",
                topics,
                help="Select the specific topic within the subject"
            )
        
        # Show topic description for reference
        if selected_topic:
            st.info(f"**📖 Topic Description:** {syllabus[selected_subject][selected_topic]['description']}")
        
        # For backward compatibility, combine subject and topic
        subject = f"{selected_subject} - {selected_topic}"
        
        st.divider()
        
        # Create the form for question content
        with st.form("mcq_form", clear_on_submit=True):
            st.subheader("✏️ Question Content")
            
            # Show current selections in the form
            col_summary1, col_summary2 = st.columns(2)
            with col_summary1:
                st.info(f"**Question Type:** {question_type}" + (f" | **Year:** {year}" if year else ""))
            with col_summary2:
                st.info(f"**Subject:** {selected_subject} | **Topic:** {selected_topic}")
            
            st.divider()
            
            # Question input
            question = st.text_area(
                "Question *",
                placeholder="Enter your question here...",
                height=100,
                help="Enter the main question that students need to answer"
            )
            
            # Four options
            st.subheader("Options")
            col1, col2 = st.columns(2)
            
            with col1:
                option_a = st.text_input(
                    "Option A *",
                    placeholder="Enter option A",
                    key="opt_a"
                )
                option_c = st.text_input(
                    "Option C *",
                    placeholder="Enter option C",
                    key="opt_c"
                )
            
            with col2:
                option_b = st.text_input(
                    "Option B *",
                    placeholder="Enter option B",
                    key="opt_b"
                )
                option_d = st.text_input(
                    "Option D *",
                    placeholder="Enter option D",
                    key="opt_d"
                )
            
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
            solution = st.text_area(
                "Solution *",
                placeholder="Provide detailed solution/explanation...",
                height=120,
                help="Explain how to solve this question"
            )
            
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
                # Validation
                if not all([question, option_a, option_b, option_c, option_d, solution]):
                    st.error("Please fill in all required fields marked with *")
                elif question_type == "PYQ" and not year:
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
                        "question_type": question_type,
                        "year": year if question_type == "PYQ" else None,
                        "subject": subject.strip() if subject else None,  # Combined for backward compatibility
                        "subject_name": selected_subject,  # Separate subject field
                        "topic_name": selected_topic,  # Separate topic field
                        "tags": [tag.strip() for tag in tags.split(",")] if tags else []
                    }
                    
                    # Save to Firebase
                    with st.spinner("Saving MCQ to Firebase..."):
                        success, result = save_mcq_to_firebase(mcq_data)
                    
                    if success:
                        st.success(f"✅ MCQ saved successfully! Document ID: {result}")
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