# Teacher MCQ Creator

A Streamlit application for teachers to create and manage Multiple Choice Questions (MCQs) with Firebase integration.

## 🚀 Quick Start (Demo Version)

To test the app immediately without Firebase setup:

```bash
pip install streamlit
streamlit run demo_mcq_app.py
```

This demo version saves MCQs locally as JSON files.

## 📋 Features

- **User-friendly form** for creating MCQs
- **Four options** with correct answer selection
- **Difficulty levels**: Easy, Medium, Hard
- **Question types**: Question Bank or Previous Year Questions (PYQ)
- **Year field** for PYQ questions
- **Subject/Topic** categorization
- **Tags** for better organization
- **Detailed solutions** for each question
- **View saved MCQs** with organized display
- **🎲 Random Question Selector** - Query and randomly select questions based on filters
- **Database-level filtering** for efficient question retrieval
- **Export functionality** with JSON download
- **Firebase integration** for cloud storage (production version)

## 🔧 Installation

1. **Clone or download** the files
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 📱 Available Versions

### 1. Demo Version (`demo_mcq_app.py`)
- No setup required
- Saves data locally as JSON files
- Perfect for testing and offline use

### 2. Firebase Version (`teacher_mcq_firebase_app.py`)
- Requires Firebase setup
- Cloud storage with real-time sync
- Suitable for production use

## 🔥 Firebase Setup

Follow the detailed guide in `FIREBASE_SETUP_GUIDE.md`:

1. Create Firebase project
2. Enable Firestore database
3. Generate service account key
4. Place `firebase-service-account.json` in project root
5. Run the Firebase version

## 📖 Usage Examples

For detailed examples on using the Random Question Selector feature, see `USAGE_EXAMPLES.md` - it includes:
- Sample query scenarios for different test types
- Filter strategies and combinations
- Export and integration options
- Tips for effective question bank management

## 🎯 Usage

### Creating MCQs

1. **Run the app**:
   ```bash
   # Demo version
   streamlit run demo_mcq_app.py
   
   # Firebase version (after setup)
   streamlit run teacher_mcq_firebase_app.py
   ```

2. **Fill in the form**:
   - Enter your question
   - Add four options (A, B, C, D)
   - Select correct answer
   - Choose difficulty level
   - Write detailed solution
   - Select question type (Question Bank/PYQ)
   - Add year (if PYQ)
   - Optional: Add subject and tags

3. **Save**: Click "Save MCQ" button

### Viewing MCQs

- **Demo version**: Switch to "View Saved MCQs" tab
- **Firebase version**: Click "View Recent MCQs" button

### Random Question Selection

1. **Go to "Random Question Selector" tab**
2. **Set your filters**:
   - Difficulty level (Easy/Medium/Hard)
   - Subject/Topic
   - Question Type (Question Bank/PYQ)
   - Year (for PYQ questions)
   - Specific tags
3. **Specify number of questions** to select
4. **Click "Generate Random Selection"**
5. **Review and download** selected questions as JSON

> **💡 Pro Tip**: Use multiple targeted queries instead of one broad query for better question distribution in tests.

## 📊 Data Structure

Each MCQ is saved with the following structure:

```json
{
  "question": "What is the capital of France?",
  "options": {
    "A": "London",
    "B": "Berlin", 
    "C": "Paris",
    "D": "Madrid"
  },
  "correct_answer": "C",
  "difficulty": "Easy",
  "solution": "Paris is the capital and largest city of France.",
  "question_type": "Question Bank",
  "year": null,
  "subject": "Geography",
  "tags": ["geography", "capitals", "europe"],
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

## 📁 File Structure

```
your-project/
├── teacher_mcq_firebase_app.py    # Main Firebase version
├── demo_mcq_app.py                # Demo version (local storage)
├── requirements.txt               # Python dependencies
├── FIREBASE_SETUP_GUIDE.md        # Detailed Firebase setup
├── USAGE_EXAMPLES.md              # Random selector usage examples
├── README.md                      # This file
├── .gitignore                     # Git ignore patterns
├── firebase-service-account.json  # Firebase key (don't commit!)
└── demo_data/                     # Demo app data (created automatically)
```

## 🛡️ Security

- **Never commit** `firebase-service-account.json` to version control
- Use **environment variables** in production
- Set up proper **Firestore security rules**
- Enable **authentication** for production use

## 🚀 Deployment

### Streamlit Cloud
1. Push to GitHub (exclude service account file)
2. Add Firebase credentials as secrets
3. Deploy from GitHub repository

### Local Development
```bash
# Create virtual environment
python -m venv mcq_env
source mcq_env/bin/activate  # On Windows: mcq_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run demo version
streamlit run demo_mcq_app.py

# Or run Firebase version (after setup)
streamlit run teacher_mcq_firebase_app.py
```

## 📝 Requirements

- Python 3.7+
- Streamlit 1.28+
- Firebase Admin SDK (for Firebase version)
- Google Cloud Firestore (for Firebase version)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 🐛 Troubleshooting

### Common Issues

1. **"Firebase service account key not found!"**
   - Ensure `firebase-service-account.json` is in project root
   - Check filename is exactly correct

2. **Permission denied errors**
   - Verify Firestore security rules
   - Check service account permissions

3. **Import errors**
   - Install all dependencies: `pip install -r requirements.txt`
   - Use virtual environment

### Demo Version Issues

1. **Data not persisting**
   - Check if `demo_data` directory is created
   - Verify write permissions

2. **Can't view saved MCQs**
   - Ensure you've created at least one MCQ
   - Check for JSON file errors

## 📄 License

This project is open source and available under the MIT License.

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review `FIREBASE_SETUP_GUIDE.md`
3. Open an issue on GitHub

## 🌟 Features Roadmap

- [ ] User authentication
- [ ] MCQ editing/updating
- [ ] Bulk import/export
- [ ] Question banks management
- [ ] Search and filtering
- [ ] Analytics dashboard
- [ ] PDF export
- [ ] Mobile app version

---

**Happy teaching! 📚✨** 