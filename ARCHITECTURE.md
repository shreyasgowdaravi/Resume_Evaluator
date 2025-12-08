# Resume Evaluator - System Architecture

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ResumeEvaluator Architecture                        │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────┐
│   User Layer    │    │  Application     │    │  AI Services    │    │   Storage   │
│                 │    │     Layer        │    │                 │    │             │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────┐ │
│ │   Browser   │◄┼────┼►│ Flask Web App│◄┼────┼►│Azure OpenAI │ │    │ │ Azure   │ │
│ │             │ │    │ │              │ │    │ │   (GPT-4)   │ │    │ │ Blob    │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │    │ │Storage  │ │
│                 │    │                  │    │                 │    │ └─────────┘ │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │    │             │
│ │Mobile/Tablet│ │    │ │   Utils      │ │    │ │Azure Form   │ │    │ ┌─────────┐ │
│ │             │ │    │ │   Modules    │ │    │ │Recognizer   │ │    │ │ Local   │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │    │ │ Files   │ │
└─────────────────┘    └──────────────────┘    └─────────────────┘    │ └─────────┘ │
                                                                      └─────────────┘
```

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Data Flow Diagram                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

User Upload
     │
     ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   File      │───►│   Flask     │───►│  Document   │───►│   Text      │
│  Validation │    │   Routes    │    │ Processing  │    │ Extraction  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                           │
                                           ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Azure     │◄───│     AI      │◄───│  Structured │
│Form Recogn. │    │  Analysis   │    │   Prompt    │
└─────────────┘    └─────────────┘    └─────────────┘
                        │
                        ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Score     │───►│   Report    │───►│   Azure     │───►│   User      │
│ Calculation │    │ Generation  │    │   Storage   │    │ Dashboard   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## 🧩 Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Component Breakdown                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend Layer                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Login     │  │  Dashboard  │  │   Loading   │  │   Results   │            │
│  │    Page     │  │    Page     │  │    Page     │  │    Page     │            │
│  │             │  │             │  │             │  │             │            │
│  │ • Auth Form │  │ • File      │  │ • Progress  │  │ • Score     │            │
│  │ • Session   │  │   Upload    │  │   Tracking  │  │   Display   │            │
│  │   Mgmt      │  │ • Drag &    │  │ • Status    │  │ • Filter/   │            │
│  │             │  │   Drop      │  │   Updates   │  │   Search    │            │
│  └─────────────┘  │ • Progress  │  │             │  │ • Export    │            │
│                   │   Bars      │  │             │  │   Options   │            │
│                   └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                             Backend Layer                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                           Flask Application (app.py)                        │ │
│  │                                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │ │
│  │  │   Routes    │  │    Auth     │  │    File     │  │   Report    │        │ │
│  │  │             │  │             │  │  Processing │  │ Generation  │        │ │
│  │  │ • /login    │  │ • Session   │  │             │  │             │        │ │
│  │  │ • /dashboard│  │   Validation│  │ • Upload    │  │ • PDF       │        │ │
│  │  │ • /evaluate │  │ • User      │  │   Handling  │  │   Creation  │        │ │
│  │  │ • /results  │  │   Management│  │ • Format    │  │ • Azure     │        │ │
│  │  │ • /download │  │             │  │   Validation│  │   Upload    │        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                              Utils Modules                                  │ │
│  │                                                                             │ │
│  │  ┌─────────────────────────┐              ┌─────────────────────────┐       │ │
│  │  │   form_recognizer.py    │              │      matcher.py         │       │ │
│  │  │                         │              │                         │       │ │
│  │  │ • Azure Form Recognizer │              │ • OpenAI Integration    │       │ │
│  │  │   Client Setup          │              │ • Prompt Engineering    │       │ │
│  │  │ • Document Parsing      │              │ • Score Calculation     │       │ │
│  │  │ • Text Extraction       │              │ • Table Parsing         │       │ │
│  │  │ • Error Handling        │              │ • Verdict Logic         │       │ │
│  │  └─────────────────────────┘              └─────────────────────────┘       │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AI Services Layer                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐              ┌─────────────────────────┐           │
│  │    Azure OpenAI         │              │   Azure Form Recognizer │           │
│  │                         │              │                         │           │
│  │ • GPT-4 Model           │              │ • Document Analysis     │           │
│  │ • Structured Prompts    │              │ • Text Extraction       │           │
│  │ • Resume Analysis       │              │ • Multi-format Support  │           │
│  │ • Scoring Logic         │              │ • OCR Capabilities      │           │
│  │ • Decision Making       │              │ • PDF/DOCX Processing   │           │
│  └─────────────────────────┘              └─────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Storage Layer                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐              ┌─────────────────────────┐           │
│  │    Azure Blob Storage   │              │    Local File System    │           │
│  │                         │              │                         │           │
│  │ • PDF Report Storage    │              │ • Temporary Files       │           │
│  │ • Secure Access         │              │ • Upload Processing     │           │
│  │ • Scalable Storage      │              │ • Session Data          │           │
│  │ • Backup & Recovery     │              │ • Static Assets         │           │
│  └─────────────────────────┘              └─────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🔐 Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             Security Layers                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐
│  Authentication │    │   Authorization │    │   Data Security │    │   Network   │
│                 │    │                 │    │                 │    │  Security   │
│ • Session-based │    │ • Route         │    │ • File          │    │             │
│   login         │    │   Protection    │    │   Validation    │    │ • HTTPS     │
│ • Hardcoded     │    │ • User Role     │    │ • Secure        │    │   Encryption│
│   credentials   │    │   Checking      │    │   Upload        │    │ • API Key   │
│ • Session       │    │ • Access        │    │ • Azure         │    │   Protection│
│   timeout       │    │   Control       │    │   Encryption    │    │             │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────┘
```

## 📊 Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Resume Processing Pipeline                             │
└─────────────────────────────────────────────────────────────────────────────────┘

Step 1: File Upload & Validation
┌─────────────────────────────────────────────────────────────────────────────────┐
│ User uploads JD + Resumes → File type validation → Size validation → Security   │
│                                                                    check        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
Step 2: Document Processing
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Azure Form Recognizer → Text extraction → Content cleaning → Structure parsing  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
Step 3: AI Analysis
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Structured prompt → GPT-4 analysis → Score calculation → Verdict determination  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
Step 4: Report Generation
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Data formatting → PDF creation → Azure storage → Download link generation       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
Step 5: Results Display
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Dashboard rendering → Interactive tables → Filter/search → Export functionality │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🔧 Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Technology Stack                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

Frontend Technologies:
┌─────────────────────────────────────────────────────────────────────────────────┐
│ • HTML5/CSS3          • Bootstrap 5         • JavaScript ES6                   │
│ • Responsive Design    • Animate.css        • Interactive UI                   │
│ • Modern Glassmorphism • Font Awesome       • AJAX Requests                    │
└─────────────────────────────────────────────────────────────────────────────────┘

Backend Technologies:
┌─────────────────────────────────────────────────────────────────────────────────┐
│ • Python 3.8+         • Flask Framework     • Werkzeug Utils                  │
│ • Jinja2 Templates     • Session Management • File Handling                    │
│ • Environment Config   • Error Handling     • Concurrent Processing           │
└─────────────────────────────────────────────────────────────────────────────────┘

AI & Cloud Services:
┌─────────────────────────────────────────────────────────────────────────────────┐
│ • Azure OpenAI (GPT-4) • Azure Form Recognizer • Azure Blob Storage          │
│ • REST API Integration • Document Analysis     • Secure Cloud Storage         │
│ • Intelligent Analysis • OCR Capabilities      • Scalable Infrastructure      │
└─────────────────────────────────────────────────────────────────────────────────┘

Data Processing:
┌─────────────────────────────────────────────────────────────────────────────────┐
│ • pandas DataFrame     • python-docx        • xhtml2pdf                       │
│ • Regular Expressions  • JSON Processing    • Base64 Encoding                 │
│ • Text Manipulation    • Table Parsing      • PDF Generation                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🚀 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Deployment Options                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

Local Development:
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Python Flask Dev Server → localhost:5000 → Local file system → Debug mode     │
└─────────────────────────────────────────────────────────────────────────────────┘

Production Deployment:
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   Azure     │    │   Docker    │    │  Gunicorn   │    │    Nginx    │      │
│  │ App Service │    │ Container   │    │   WSGI      │    │ Load Balancer│     │
│  │             │    │             │    │   Server    │    │             │      │
│  │ • Auto      │    │ • Portable  │    │ • Multi-    │    │ • SSL       │      │
│  │   Scaling   │    │   Deploy    │    │   worker    │    │   Termination│     │
│  │ • Managed   │    │ • Consistent│    │ • Production│    │ • Static    │      │
│  │   Service   │    │   Environment│   │   Ready     │    │   Files     │      │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 📈 Scalability & Performance

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Performance Optimizations                               │
└─────────────────────────────────────────────────────────────────────────────────┘

Application Level:
┌─────────────────────────────────────────────────────────────────────────────────┐
│ • Concurrent Processing    • Efficient File Handling    • Memory Management    │
│ • ThreadPoolExecutor       • Temporary File Cleanup     • Session Optimization │
│ • Batch Operations         • Stream Processing          • Error Recovery       │
└─────────────────────────────────────────────────────────────────────────────────┘

Infrastructure Level:
┌─────────────────────────────────────────────────────────────────────────────────┐
│ • Azure Auto-scaling       • CDN Integration           • Load Balancing        │
│ • Horizontal Scaling       • Caching Strategies        • Database Optimization │
│ • Resource Monitoring      • Performance Metrics       • Health Checks         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Integration Points

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            External Integrations                                │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Azure OpenAI  │    │ Azure Form Rec. │    │ Azure Blob      │
│                 │    │                 │    │ Storage         │
│ • REST API      │    │ • REST API      │    │                 │
│ • JSON Request  │    │ • File Upload   │    │ • File Upload   │
│ • JSON Response │    │ • Text Response │    │ • URL Access    │
│ • Rate Limiting │    │ • Multi-format  │    │ • Secure Links  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

This architecture provides a comprehensive view of the TalentAligner Pro system, showing how all components work together to deliver an intelligent resume matching solution.