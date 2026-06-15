# SmartDocs AI

SmartDocs is a full-stack assistant that helps you upload research papers (PDFs) and ask questions, generate summaries, or get simplified explanations of complex academic concepts. It uses RAG (Retrieval-Augmented Generation) so that all answers are grounded in the paper itself.

---

## Features

* **PDF Upload**: Upload papers and let the app split them into clean text chunks.
* **Intelligent Chat**: Get grounded answers based strictly on the uploaded text.
* **Structured Summaries & Explanations**: Detects whether you want a quick overview or a simple analogy-based explanation.
* **Source Tracking**: Toggle the source panel to see exactly which parts of the paper were used to answer your question.
* **Document Deletion**: Easily remove old or duplicate papers from your sidebar to keep your workspace clean.

---

## Setup & Running Locally

### 1. Requirements
* Python 3.9+
* Node.js 18+
* A Google Gemini API Key and a Groq API Key

### 2. Run the Backend
1. Go to the `backend` folder and create a `.env` file with your keys:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   ```
2. Activate your virtual environment and install python packages:
   ```bash
   # In backend/ directory
   pip install -r requirements.txt
   ```
3. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 3. Run the Frontend
1. Open a new terminal tab and go to the `frontend` folder.
2. Install node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite dev server:
   ```bash
   npm run dev
   ```

Open `http://localhost:5173` to run app locally!
