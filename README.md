# FormsIQ - Automated Mortgage Application Form Extractor

FormsIQ is an advanced application that extracts information from mortgage application call transcripts and automatically fills out the Uniform Residential Loan Application form (1003 Form).

## Architecture

The application consists of three main components:

1. **Frontend UI (Angular)**: Provides an interface for users to paste call transcripts and view/download extracted form data
2. **Backend API (Django)**: Processes transcripts and handles PDF form filling
3. **AI Language Model (Gemma via LM Studio & Grok 3 )**: Performs the extraction of relevant fields from transcripts

## Features

- Paste any call transcript text into the application
- AI-powered extraction of relevant mortgage application data
- View extracted fields with confidence scores
- Download a filled PDF form with the extracted data
- Responsive UI

## Prerequisites

- Python 3.8+ with pip
- Node.js and npm
- LM Studio with Gemma 3 12B model installed

## Setup Instructions

### Backend Setup (Django)

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Start the Django development server:
   ```
   python manage.py runserver
   ```

### Frontend Setup (Angular)

1. Navigate to the frontend directory:
   ```
   cd formsiq-ui
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the Angular development server:
   ```
   ng serve
   ```

### LM Studio Setup

1. Download and install LM Studio from [lmstudio.ai](https://lmstudio.ai)
2. In LM Studio, download the Gemma 3 12B model
3. Go to the "Local Server" tab and start the server
4. Ensure the server is running at `http://localhost:1234`

## Usage

1. Open your browser and navigate to `http://localhost:4200`
2. Paste a call transcript into the text area
3. Click "Process Transcript"
4. Review the extracted fields and confidence scores
5. Click "Download Filled PDF" to get the completed form

## Project Structure

```
FormsIQ/
├── backend/                         # Django backend
│   ├── api_processor/               # Main Django app
│   │   ├── ai_service.py            # AI interaction service
│   │   ├── field_mapping.py         # PDF field mapping
│   │   ├── pdf_service.py           # PDF filling service
│   │   ├── serializers.py           # API serializers
│   │   ├── urls.py                  # API URL configuration
│   │   └── views.py                 # API endpoint logic
│   ├── formsiq_project/             # Django project settings
│   └── media/                       # Media files
│       └── pdf/                     # PDF templates
├── form/                            # Original form files
│   └── uniform_residential_loan_application.pdf
└── formsiq-ui/                      # Angular frontend
    ├── src/
    │   ├── app/
    │   │   ├── components/          # Angular components
    │   │   │   ├── transcript-input/ # Transcript input component
    │   │   │   └── results-display/ # Results display component
    │   │   └── services/            # Angular services
    │   │       └── api.service.ts   # API communication service
    │   └── assets/                  # Static assets
    └── ...
```

