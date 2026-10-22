# OS Tutor

OS Tutor is an AI-powered learning platform for Operating Systems Lab students. It provides course-material-grounded explanations, exact CPU scheduling solutions, and topic-wise student understanding tracking.

**Live Website:** https://os-tutor.lovable.app

---

## Features

### 1. Grounded OS Concept Tutor
- Answers Operating Systems questions using only the supplied course material.
- Uses Retrieval-Augmented Generation (RAG) to find relevant content before answering.
- Shows module and page citations with answers.
- Avoids unsupported answers when information is not available in the course material.

### 2. CPU Scheduling Numerical Lab
Supports exact solutions for:

- First Come First Serve (FCFS)
- Shortest Job First — Non-Preemptive (SJF)
- Priority Scheduling — Non-Preemptive
- Round Robin (RR)

For each problem, OS Tutor provides:

- Gantt chart
- Completion time
- Turnaround time
- Waiting time
- Average turnaround time
- Average waiting time
- Idle CPU periods where applicable

### 3. Student Evaluation
- Students can sign in and select an Operating Systems topic.
- The tutor generates multiple-choice and true/false questions from the course material.
- Correct answers add understanding points.
- Incorrect answers show the correct answer and provide a targeted explanation.

### 4. Understanding Tracker
- Tracks topic-wise understanding from 0% to 100%.
- Records correct and incorrect answers.
- Shows overall learning progress and mastered topics.

---

## Topics Covered

- Operating System Basics
- Processes
- Process Control Block
- CPU Scheduling
- Threads
- Process Synchronization
- Semaphores
- Deadlocks
- Memory Management
- Paging
- Segmentation
- Virtual Memory
- File Systems
- Disk Scheduling
- Protection and Security

---

## Technology Stack

### Frontend
- React
- TanStack Start
- TypeScript
- Tailwind CSS

### Backend
- Python
- FastAPI
- FAISS vector search
- FastEmbed embeddings
- Groq LLM API
- Docker

### Data and Deployment
- Lovable Cloud for student accounts and progress storage
- Render for backend deployment
- GitHub for source-code version control

---

## How It Works

```text
Student Question
      │
      ├── Theory Question
      │      │
      │      ├── Retrieve relevant course-note chunks using FAISS
      │      ├── Send retrieved context to the language model
      │      └── Return a cited answer with module and page references
      │
      └── CPU Scheduling Numerical
             │
             ├── Detect scheduling algorithm
             ├── Parse processes, burst times, arrivals, priorities, and quantum
             ├── Run deterministic scheduling solver
             └── Display Gantt chart and exact calculations


Running the Backend Locally


1. Open the backend folder


cd backend



2. Install the required packages


pip install -r requirements-cpu.txt



3. Create environment variables



Create a .env file inside the backend folder:



GENERATOR=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=qwen/qwen3.8-27b



4. Start the server


uvicorn main:app --host 0.0.0.0 --port 8000




The backend will run at:



http://localhost:8000





Important Notes




Do not upload .env files or API keys to GitHub.


The backend requires the files inside backend/data/ for course-material retrieval.


The deployed free backend may take a short time to wake up after inactivity.






Project Documents



This repository also contains:





Final Review Report


Project Presentation


Kaggle/Jupyter development notebook


Frontend and backend source code






Author

Madhav Tiwary



