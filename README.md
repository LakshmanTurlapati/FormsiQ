# FormsIQ - AI-Powered Mortgage Form Automation

FormsIQ is an intelligent application that transforms mortgage application call transcripts into completed Uniform Residential Loan Application forms (Form 1003). Using AI field extraction and sophisticated PDF form filling technology, FormsIQ streamlines the mortgage application process by automatically extracting and organizing borrower information.

## How It Works

FormsIQ follows a streamlined workflow that combines natural language processing with advanced PDF manipulation:

### 1. Transcript Input
Users paste raw call transcript text into the application. The system accepts transcripts in natural conversation format between loan officers and borrowers.

### 2. AI-Powered Field Extraction
FormsIQ offers two AI processing options - users choose their preferred approach:

**Option A: Gemma 3 12B (Local Processing)**
- Runs locally via LM Studio for complete privacy
- 12 billion parameter model for natural language understanding
- Processes mortgage-specific terminology and context
- Generates confidence scores for each extracted field

**Option B: Grok API (Cloud Processing)**
- Cloud-based processing via xAI's language model
- Real-time processing with external API
- Alternative option when local processing isn't available

### 3. Intelligent Field Mapping System
Our custom field mapping system uses multiple strategies to match extracted data to PDF form fields:

**Pattern Recognition Engine**
- Over 100 predefined patterns for mortgage-specific data
- Regex-based extraction for structured data (SSN, phone numbers, addresses)
- Context-aware field identification
- Multi-format date and currency parsing

**Field Mapping Intelligence**
- **Exact String Matching**: Direct field name correspondence
- **Fuzzy Matching**: Similarity-based matching using difflib algorithms
- **Semantic Matching**: Synonym and context-based field recognition
- **Category-Based Mapping**: Groups related fields (personal info, employment, assets)

**Confidence Scoring**
- Individual confidence assessment (0-1 scale) from AI model
- Field validation and format verification
- Pattern match strength evaluation

## AI Workflow

FormsIQ's AI processing follows a sophisticated multi-stage workflow:

### Stage 1: Transcript Preprocessing
- **Text Normalization**: Clean and standardize transcript format
- **Pattern Detection**: Identify conversation structure and participants
- **Context Preparation**: Format text for optimal AI processing

### Stage 2: AI Field Extraction
- **Model Selection**: User chooses between Gemma 3 12B (local) or Grok 3 Mini (cloud)
- **Structured Prompting**: Custom prompts optimized for mortgage data extraction
- **Field Recognition**: AI identifies and extracts specific mortgage-related fields
- **Confidence Assessment**: Each extracted field receives a confidence score (0-1 scale)

### Stage 3: Field Mapping and Validation
- **Intelligent Mapping**: Custom algorithms match extracted fields to PDF form fields
- **Fuzzy String Matching**: Handles variations in field names using difflib
- **Semantic Analysis**: Recognizes field meanings through synonym databases
- **Data Validation**: Ensures extracted data meets format requirements

### Stage 4: PDF Form Population
- **Field Type Detection**: Identifies text fields, checkboxes, and radio buttons
- **Value Formatting**: Converts data to appropriate formats for each field type
- **Form Filling**: Uses PyPDF to populate the Uniform Residential Loan Application
- **Quality Assurance**: Validates filled form for completeness and accuracy

### 4. Advanced PDF Processing
FormsIQ uses the PyPDF library with custom enhancements for comprehensive form filling:

**Text Field Processing**
- Automatic data type detection and formatting
- String normalization and validation
- Length constraint handling
- Special character processing

**Checkbox Field Handling**
- Intelligent boolean value conversion
- Custom on/off state management using NameObject values
- Support for Yes/No, True/False, and custom checkbox states
- Automatic appearance state synchronization (/AS and /V fields)

**Radio Button Group Management**
- Multi-option selection handling
- Export value mapping and validation
- Group relationship preservation
- Parent-child field coordination for radio button hierarchies

**Advanced PDF Features**
- Field discovery and cataloging
- Form field type detection (text, checkbox, radio, dropdown)
- Appearance stream management for proper rendering
- NeedAppearances flag handling for PDF viewer compatibility

## Technology Stack

### Backend (Django)
- **Django 5.2.1**: Core web framework
- **Django REST Framework**: API development
- **PyPDF 5.4.0**: Advanced PDF manipulation and form filling
- **OpenAI SDK**: AI service integration for Grok API
- **python-dotenv**: Environment configuration management

### Frontend (Angular 17)
- **Angular 17**: Modern web framework with standalone components
- **TypeScript 5.4**: Type-safe development
- **SCSS**: Advanced styling
- **Server-Side Rendering (SSR)**: Enhanced performance and SEO

### AI Integration
- **Local LM Studio**: Gemma 3 12B model hosting
- **Grok API**: Cloud-based AI processing via xAI
- **Custom NLP Pipeline**: Mortgage-specific field extraction
- **Confidence Calibration**: Model-specific accuracy tuning

### PDF Processing Libraries
Our custom PDF processing system leverages:
- **PyPDF Core**: For reading and writing PDF forms
- **NameObject Handling**: Proper PDF object type management
- **BooleanObject Processing**: Checkbox state management
- **Appearance Stream Control**: Visual form field rendering
- **Field Validation**: Constraint checking and format verification

## Key Features

### Intelligent Data Extraction
- **Multi-format Support**: Handles various transcript formats and conversation styles
- **Context-Aware Processing**: Understands mortgage terminology and relationships
- **Pattern-Based Extraction**: Uses regex patterns for structured data like SSN, phone numbers
- **Confidence Scoring**: Each extracted field includes a confidence assessment

### Advanced Form Filling
- **Complete Field Coverage**: Fills all supported fields in Form 1003
- **Checkbox Intelligence**: Accurately selects appropriate checkboxes based on extracted data
- **Radio Button Logic**: Handles complex radio button groups and dependencies
- **Data Formatting**: Automatically formats data according to form requirements

### Privacy and Security
- **Local Processing Option**: Keep sensitive data on-premises with Gemma
- **No Data Persistence**: Transcripts processed in memory only
- **Secure File Handling**: Temporary PDF generation with automatic cleanup
- **Environment-based Configuration**: Secure credential management

### User Experience
- **Simple Interface**: Clean, intuitive design for easy transcript input
- **Confidence Indicators**: Visual feedback on extraction quality for each field
- **Field Review**: Easy verification of extracted data before PDF generation
- **Instant PDF Download**: Download completed forms immediately after processing

## Architecture Overview

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Angular Frontend  │    │   Django Backend    │    │  AI Processing      │
│                     │    │                     │    │                     │
│ • Transcript Input  │───▶│ • Field Extraction  │───▶│ • Gemma 3 12B      │
│ • Results Display   │◀───│ • PDF Processing    │◀───│ • Grok API         │
│ • PDF Download      │    │ • Field Mapping     │    │ • Pattern Engine   │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

### Data Flow
1. **Input Processing**: Raw transcript text normalized and prepared
2. **AI Analysis**: Selected AI engine (Gemma or Grok) extracts field values with confidence scores
3. **Field Mapping**: Intelligent mapping to PDF form field names using custom algorithms
4. **Validation**: Data type checking and format validation
5. **PDF Generation**: Advanced form filling with PyPDF
6. **Output Delivery**: Completed form ready for download

## Unique Capabilities

### Custom Field Mapping Intelligence
FormsIQ includes a sophisticated field mapping system that goes beyond simple string matching:

- **Synonym Recognition**: Extensive database of field name variations and mortgage terminology
- **Contextual Understanding**: Recognizes fields based on surrounding context and patterns
- **Fuzzy String Matching**: Uses difflib algorithms to find similar field names
- **Category-Based Grouping**: Organizes fields by type (personal, employment, financial, etc.)

### Advanced PDF Form Handling
Our PDF processing capabilities include:

- **Complete Form Analysis**: Automatic discovery of all fillable fields
- **Field Relationship Mapping**: Understanding of form field dependencies
- **Appearance Management**: Proper visual rendering of filled forms
- **Compatibility Optimization**: Works with various PDF viewers and systems

### Flexible AI Architecture
FormsIQ's AI options provide:

- **Processing Choice**: Select between local privacy (Gemma) or cloud processing (Grok)
- **Custom Prompting**: Tailored AI instructions optimized for mortgage data extraction
- **Model-Specific Optimization**: Each AI option tuned for mortgage-specific terminology
- **Fallback Processing**: Graceful error handling when AI services are unavailable

## Prototype Disclaimer

**⚠️ Note: This is an internal prototype built for demonstration purposes only. It is not production-grade.**

This tool was developed as part of the POMS problem statement for Mr. Cooper, aiming to autofill IRS Form 1003 with approximately 80% accuracy using the Grok 3 Mini API. It supports text field population and basic checkbox handling (currently in an experimental phase).

### 🔧 Key Details:
- **Accuracy**: ~80% autofill for text fields
- **Checkbox support**: Intermittent; improvements pending
- **PDF filling**: Powered by Grok 3 Mini API
- **Gemma 3 model**: Disabled on this deployed instance (was local-only)

### ⚠️ Important Notes:
- This is a **non-production prototype** for internal illustration only
- All visual elements are inspired by Mr. Cooper's website; design rights belong to the respective owners
- **Do not reuse, share, or distribute** without permission
- For more information, access to the source code, or collaboration opportunities, feel free to reach out to me — **Venkat L. Turlapati**
- You can also check out the [GitHub repository](https://github.com/venkat-turlapati/FormsIQ) and reach out to me [here](https://www.audienclature.com)

---

FormsIQ represents an innovative approach to mortgage application processing, combining AI technology with PDF manipulation to create an automation solution focused on accuracy and ease of use for demonstration and research purposes.