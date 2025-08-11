# AIMhi-Y Supportive Yarn Chatbot

This is a web-based chatbot prototype designed to provide a culturally safe and supportive space for Aboriginal and Torres Strait Islander youth. The chatbot guides users through the AIMhi Stay Strong 4-step model.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd aimhi-chatbot
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file by copying the `.env.example` file and fill in the required values.

5.  **Run the application:**
    ```bash
    python app.py
    ```

## Usage

Open your web browser and navigate to `http://127.0.0.1:5000`.

## Project Structure

```
aimhi-chatbot/
├── app.py                 # Flask main
├── requirements.txt       # Dependencies
├── .env.example          # Environment template
├── config/                # Configuration files
├── core/                  # Core application logic (FSM, router)
├── database/              # Database schema and repository
├── docs/                  # Project documentation
├── llm/                   # LLM integration
├── nlp/                   # NLP components (risk detection, intent)
├── static/                # Static assets (CSS, JS)
├── templates/             # HTML templates
└── tests/                 # Tests
```
