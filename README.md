# 📋 ContractLens

![Build Status](https://img.shields.io/github/workflow/status/yourusername/contractlens/CI?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)
![Stars](https://img.shields.io/github/stars/yourusername/contractlens?style=flat-square)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue?style=flat-square&logo=typescript)

**AI-powered contract analysis for freelancers and small businesses**

ContractLens empowers freelancers and small business owners to make informed decisions by identifying risky clauses, unfair terms, and missing protections in client contracts before signing. Upload your contracts and receive instant, comprehensive risk assessments with actionable recommendations—no legal degree required.

---

## ✨ Features

- 📄 **Smart Document Parsing** - Upload contracts in PDF or text format with automatic text extraction and structure recognition
- 🎯 **Multi-Dimensional Risk Scoring** - Analyze contracts across payment terms, liability clauses, IP rights, termination conditions, and confidentiality
- ⚡ **Instant Analysis** - Get comprehensive risk assessments in seconds using advanced NLP algorithms
- 📊 **Interactive Visualizations** - View risk breakdowns through intuitive charts and heat maps
- 💡 **Actionable Recommendations** - Receive specific suggestions for negotiating better terms and protecting your interests
- 🔒 **Secure & Private** - Your contracts are encrypted and never shared with third parties
- 📱 **Responsive Design** - Seamless experience across desktop, tablet, and mobile devices

---

## 🛠️ Tech Stack

**Frontend:**
- ![React](https://img.shields.io/badge/React-18.x-61DAFB?style=flat-square&logo=react&logoColor=white)
- ![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat-square&logo=typescript&logoColor=white)
- ![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.x-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)
- Vite
- Chart.js / Recharts

**Backend:**
- ![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat-square&logo=fastapi&logoColor=white)
- ![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
- ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat-square&logo=postgresql&logoColor=white)
- SQLAlchemy
- Pydantic
- PyPDF2 / pdfplumber

**AI/ML:**
- OpenAI API / Hugging Face Transformers
- spaCy
- NLTK

---

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (v18 or higher)
- **Python** (v3.11 or higher)
- **PostgreSQL** (v15 or higher)
- **npm** or **yarn**
- **pip** or **poetry**

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/contractlens.git
cd contractlens
```

2. **Set up the backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Set up the database**

```bash
# Create PostgreSQL database
createdb contractlens_db

# Run migrations
alembic upgrade head
```

4. **Set up the frontend**

```bash
cd ../frontend
npm install
```

5. **Configure environment variables**

```bash
# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.example frontend/.env
```

Edit the `.env` files with your configuration (see [Environment Variables](#-environment-variables)).

6. **Start the development servers**

```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Visit `http://localhost:5173` to see the application running!

---

## 📖 Usage

### Basic Contract Analysis

```typescript
// Upload and analyze a contract
import { ContractAnalyzer } from './services/analyzer';

const analyzer = new ContractAnalyzer();

// Upload contract file
const file = document.getElementById('contract-upload').files[0];
const result = await analyzer.analyzeContract(file);

console.log(result);
// {
//   riskScore: 72,
//   categories: {
//     paymentTerms: { score: 85, issues: [...] },
//     liability: { score: 45, issues: [...] },
//     ipRights: { score: 90, issues: [...] }
//   },
//   recommendations: [...]
// }
```

### API Usage

```python
# Backend API endpoint example
from fastapi import FastAPI, UploadFile
from app.services.contract_analyzer import ContractAnalyzer

@app.post("/api/analyze")
async def analyze_contract(file: UploadFile):
    analyzer = ContractAnalyzer()
    
    # Extract text from PDF
    text = await analyzer.extract_text(file)
    
    # Perform multi-criteria analysis
    analysis = await analyzer.analyze(text)
    
    return {
        "risk_score": analysis.overall_risk,
        "categories": analysis.category_scores,
        "recommendations": analysis.recommendations,
        "flagged_clauses": analysis.risky_clauses
    }
```

### Risk Score Interpretation

```typescript
const getRiskLevel = (score: number): string => {
  if (score >= 80) return "Low Risk";
  if (score >= 60) return "Moderate Risk";
  if (score >= 40) return "High Risk";
  return "Critical Risk";
};
```

---

## 🏗️ Project Architecture

```
contractlens/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ContractUpload.tsx
│   │   │   ├── RiskDashboard.tsx
│   │   │   ├── ClauseAnalysis.tsx
│   │   │   └── RecommendationPanel.tsx
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   └── analyzer.ts
│   │   ├── hooks/
│   │   │   └── useContractAnalysis.ts
│   │   ├── types/
│   │   │   └── contract.types.ts
│   │   ├── utils/
│   │   │   └── riskCalculator.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   └── tailwind.config.js
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── contracts.py
│   │   │   │   └── analysis.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   ├── contract.py
│   │   │   └── analysis.py
│   │   ├── services/
│   │   │   ├── contract_analyzer.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── risk_scorer.py
│   │   │   └── recommendation_engine.py
│   │   ├── schemas/
│   │   │   └── contract.py
│   │   └── main.py
│   ├── alembic/
│   ├── requirements.txt
│   └── pytest.ini
├── docker-compose.yml
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🔑 Environment Variables

### Backend (`backend/.env`)

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/contractlens_db

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_secret_key_here

# Server
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# File Upload
MAX_UPLOAD_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=.pdf,.txt,.docx
```

### Frontend (`frontend/.env`)

```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=ContractLens
VITE_MAX_FILE_SIZE=10485760
```

---

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit your changes** (`git commit -m 'Add some AmazingFeature'`)
4. **Push to the branch** (`git push origin feature/AmazingFeature`)
5. **Open a Pull Request**

### Development Guidelines

- Follow the existing code style and conventions
- Write meaningful commit messages
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

### Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 ContractLens

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

<div align="center">

**Built with ❤️ and Alviora AI**

⭐ Star this repo if you find it helpful!

[Report Bug](https://github.com/yourusername/contractlens/issues) · [Request Feature](https://github.com/yourusername/contractlens/issues)

</div>