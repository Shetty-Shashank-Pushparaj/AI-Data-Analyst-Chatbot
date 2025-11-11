# AI Data Analyst & Chatbot

![Project Demo GIF](https://i.imgur.com/your-gif-url.gif)

*A live demo GIF is the **most important** thing for a recruiter. Use a free tool like **ScreenToGif** to record your app working (upload, charts appearing, and you asking a chat question). Upload that GIF to a site like [imgur.com](https://imgur.com/) and paste the link above.*

## 💡 About This Project

This is a full-stack web application that acts as an **AI Data Analyst**. A user (like a business analyst) can upload any raw CSV file and, within seconds, receive a complete dashboard with automated charts, high-level insights, and a chatbot ready to answer complex, natural-language questions about their data.

This project was built from scratch to handle every part of the data analysis pipeline: from data ingestion and cleaning to AI-driven visualization and calculation.

## ✨ Key Features

* **Automated Chart Generation:** The app doesn't just build charts; it uses an AI (OpenAI GPT-3.5) to analyze the data schema and **intelligently decide** which charts are the most relevant (up to 15).
* **AI-Generated Insights:** On upload, a second AI brain generates 10 high-level, actionable insights from the data, which are displayed on the dashboard.
* **Conversational Calculation Engine:** The chatbot is a custom-built **AI Data Scientist**.
    * It uses an AI-powered "meta-prompt" to **write its own Python (Pandas) code** in real-time to answer questions.
    * This is **not** a simple search; it's a **calculation engine** that can perform sums, averages, groupings, and more.
    * It runs this AI-generated code in a secure **`subprocess` sandbox** to get the final answer.
* **User-Defined Metrics:** The user can *teach* the AI their own custom business logic (e.g., `Profit Margin = (Profit / Sales) * 100`). The AI will then **use this user-defined formula** in the code it writes.
* **Conversational Memory:** The chat remembers the context of the last 6 messages, allowing for natural, follow-up questions.

## 🛠️ Tech Stack

This project is built on two main components:

### Backend (The "Brain")
* **Framework:** Python & **Flask** (as the web server)
* **AI Engine:** **OpenAI GPT-3.5** (for all chart, insight, and code generation)
* **Data Analysis:** **Pandas** (for all data manipulation)
* **Server Logic:** Secure **`subprocess`** execution for running AI-generated code.
* **Other:** `python-dotenv` (for API keys), `flask-cors` (for web security)

### Frontend (The "Website")
* **Structure:** `index.html`
* **Styling:** **Tailwind CSS** (for a modern, responsive UI)
* **Chart Library:** **Plotly.js** (for interactive visualizations)
* **Connectivity:** `fetch API` (JavaScript)

## 🏃 How to Run This Project Locally

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/AI-Data-Analyst-Chatbot.git](https://github.com/YOUR_USERNAME/AI-Data-Analyst-Chatbot.git)
    cd AI-Data-Analyst-Chatbot
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # On Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install the "parts list":**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Create your secret `.env` file:**
    * Create a file named `.env` in the main folder.
    * Add your OpenAI API key to it:
        `OPENAI_API_KEY=sk-YourSecretKeyHere`

5.  **Run the server:**
    * The server is set to run on port 5001.
    ```bash
    python app.py
    ```
    * You will see: `* Running on http://127.0.0.1:5001/`

6.  **Launch the website:**
    * Open the `index.html` file directly in your web browser.
    * Upload a CSV and start analyzing!