# Resume Evaluator - AI-Powered Resume Matching System

## 🚀 Overview

**Resume Evaluator** is an advanced AI-powered resume matching and evaluation system that automates the candidate screening process. Built with Flask and integrated with Azure AI services, it provides intelligent resume analysis, scoring, and hiring recommendations.

## ✨ Key Features

- 🤖 **AI-Powered Analysis** - GPT-4 integration for intelligent resume evaluation
- 📊 **Structured Scoring** - 6-criteria evaluation system with detailed breakdowns
- 📄 **Multi-Format Support** - PDF, DOCX, and TXT file processing
- 🎯 **Automated Decisions** - Shortlist/Hold/Reject recommendations
- 📈 **Professional Reports** - Branded PDF reports with detailed analysis
- 🔒 **Secure Processing** - Azure cloud integration with encrypted storage
- 📱 **Responsive UI** - Modern, mobile-friendly interface

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Interface │────│  Flask Backend   │────│  Azure Services │
│                 │    │                  │    │                 │
│ • Dashboard     │    │ • Authentication │    │ • Form Recognizer│
│ • File Upload   │    │ • File Processing│    │ • OpenAI GPT-4  │
│ • Results View  │    │ • Report Gen.    │    │ • Blob Storage  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
resume_matcher/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── .env                     # Environment configuration
├── README.md                # This documentation
├── static/
│   └── logo.png            # Company branding
├── templates/
│   ├── login.html          # Authentication page
│   ├── dashboard.html      # File upload interface
│   ├── loading.html        # Processing status
│   └── result.html         # Results display
└── utils/
    ├── form_recognizer.py  # Document parsing
    └── matcher.py          # AI evaluation logic
```

## 🛠️ Technology Stack

### Backend
- **Python 3.8+** - Core programming language
- **Flask** - Web framework
- **Azure OpenAI** - GPT-4 for intelligent analysis
- **Azure Form Recognizer** - Document text extraction
- **Azure Blob Storage** - File storage and management

### Frontend
- **HTML5/CSS3** - Modern web standards
- **Bootstrap 5** - Responsive UI framework
- **JavaScript ES6** - Interactive functionality
- **Animate.css** - Smooth animations

### Data Processing
- **pandas** - Data manipulation and analysis
- **python-docx** - Word document processing
- **xhtml2pdf** - PDF report generation

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Azure subscription with AI services
- Git for version control

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd gradientm_resume_matcher
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
# Copy and edit .env file
cp .env.example .env
```

4. **Run the application**
```bash
python app.py
```

5. **Access the application**
```
http://localhost:5000
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```env
# Azure Form Recognizer
AZURE_FORM_RECOGNIZER_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=your-form-recognizer-key

# Azure OpenAI
AZURE_OPENAI_API_KEY=your-openai-key
AZURE_OPENAI_API_BASE=https://your-openai-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
AZURE_STORAGE_CONTAINER_NAME=resumereports

# Application
SECRET_KEY=your-secret-key-here
```

### User Management

Currently uses hardcoded authentication. Update `app.py`:

```python
users = {
    "user1@company.com": "password1",
    "user2@company.com": "password2",
    # Add more users as needed
}
```

## 📊 Evaluation System

### Scoring Criteria

| Criteria | Max Score | Weight | Description |
|----------|-----------|--------|-------------|
| **Overall Experience** | 25 | 25% | Total years of professional experience |
| **Relevant Experience** | 20 | 20% | Experience matching job requirements |
| **Primary Technical Skills** | 20 | 20% | Core technical competencies required |
| **Secondary Technical Skills** | 15 | 15% | Supporting technical abilities |
| **Tools Experience** | 10 | 10% | Familiarity with required tools/software |
| **Job Stability** | 10 | 10% | Employment history and tenure analysis |

### Decision Matrix

- **🟢 Shortlist** (Score ≥ 70): Ready for interview
- **🟡 Hold** (Score 60-69): Requires further review
- **🔴 Not Relevant** (Score < 60): Poor match for position

### Additional Context (Non-Scored)
- University/Educational background
- Highest qualification details
- Domain/Industry experience
- Professional certifications

## 🔄 Workflow

### 1. Authentication
- Secure login with session management
- Role-based access control
- Protected routes

### 2. File Upload
- **Job Description**: TXT or DOCX format
- **Resumes**: PDF format (up to 10 files)
- Drag-and-drop interface with validation

### 3. AI Processing
- Document text extraction via Azure Form Recognizer
- Structured analysis using GPT-4
- Automated scoring and decision making

### 4. Results & Reports
- Interactive results dashboard
- Detailed evaluation breakdowns
- Professional PDF reports
- Bulk download functionality

## 🎨 User Interface

### Design Features
- **Modern Glassmorphism** - Translucent elements with blur effects
- **Gradient Backgrounds** - Eye-catching color schemes
- **Responsive Layout** - Mobile-first design approach
- **Interactive Animations** - Smooth transitions and hover effects
- **Progress Tracking** - Real-time processing updates

### Key Pages

1. **Login Page** - Secure authentication with animated elements
2. **Dashboard** - File upload with drag-and-drop functionality
3. **Loading Page** - Processing status with progress indicators
4. **Results Page** - Comprehensive evaluation display with filtering

## 🔒 Security Features

- **Session Management** - Secure user sessions
- **File Validation** - Type and size restrictions
- **Azure Integration** - Enterprise-grade security
- **Data Encryption** - Secure data transmission
- **Access Control** - User authentication required

## 📈 Performance

### Optimization Features
- **Batch Processing** - Handle multiple resumes simultaneously
- **Async Operations** - Non-blocking file processing
- **Caching** - Improved response times
- **CDN Integration** - Fast asset delivery

### Scalability
- **Cloud-Native** - Azure services integration
- **Horizontal Scaling** - Support for multiple instances
- **Load Balancing** - Distribute processing load

## 🧪 Testing

### Manual Testing Checklist
- [ ] User authentication flow
- [ ] File upload validation
- [ ] Document processing accuracy
- [ ] Scoring algorithm consistency
- [ ] Report generation quality
- [ ] UI responsiveness across devices

### Test Data
- Sample job descriptions in `test_data/jd/`
- Sample resumes in `test_data/resumes/`
- Expected results in `test_data/expected/`

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Production Deployment

#### Using Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

#### Using Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

#### Azure App Service
1. Create Azure App Service
2. Configure environment variables
3. Deploy via Git or ZIP
4. Configure custom domain (optional)

## 📊 Analytics & Monitoring

### Key Metrics
- **Processing Time** - Average evaluation duration
- **Accuracy Rate** - Scoring consistency
- **User Engagement** - Session duration and actions
- **Error Rates** - Failed processing attempts

### Monitoring Tools
- Azure Application Insights
- Custom logging implementation
- Performance counters
- Error tracking

## 🔧 Troubleshooting

### Common Issues

#### Authentication Problems
```python
# Check user credentials in app.py
users = {
    "your-email@domain.com": "your-password"
}
```

#### Azure Service Errors
- Verify API keys and endpoints
- Check service quotas and limits
- Ensure proper permissions

#### File Processing Issues
- Validate file formats (PDF, DOCX, TXT)
- Check file size limits (5MB per file)
- Verify Azure Form Recognizer configuration

### Debug Mode
```python
# Enable debug mode in app.py
app.debug = True
```

## 🔮 Future Enhancements

### Planned Features
- [ ] **Database Integration** - Replace hardcoded users
- [ ] **Advanced Analytics** - Hiring trends and insights
- [ ] **API Development** - RESTful API for integrations
- [ ] **Machine Learning** - Improve scoring accuracy
- [ ] **Multi-language Support** - International resume processing
- [ ] **ATS Integration** - Connect with existing HR systems

### Technical Improvements
- [ ] **Unit Testing** - Comprehensive test coverage
- [ ] **CI/CD Pipeline** - Automated deployment
- [ ] **Performance Optimization** - Faster processing times
- [ ] **Security Hardening** - Enhanced protection measures

## 🤝 Contributing

### Development Guidelines
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Standards
- Follow PEP 8 for Python code
- Use meaningful variable names
- Add comments for complex logic
- Update documentation for new features

## 📄 License

Copyright © 2025 GradientM IT Consulting & Services Pvt Ltd. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

## 📞 Support

### Contact Information
- **Email**: support@company.com
- **Phone**: +91-XXXX-XXXX
- **Website**: https://company.com

### Documentation
- **User Manual**: `/docs/user-manual.pdf`
- **API Documentation**: `/docs/api-reference.md`
- **Troubleshooting Guide**: `/docs/troubleshooting.md`

---

**Built with ❤️ by Shreyas**
*Transforming recruitment through AI-powered intelligence*