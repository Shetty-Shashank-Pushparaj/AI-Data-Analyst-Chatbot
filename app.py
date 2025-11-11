import os
import io
import json
import contextlib 
import subprocess 
from subprocess import TimeoutExpired # For catching long-running code
import sys 
import tempfile # <-- NEW: To find the real temp folder
from flask import Flask, request, jsonify
import pandas as pd
from dotenv import load_dotenv 
from urllib.parse import unquote # For decoding metrics

# --- 1. LOAD ENVIRONMENT KEYS ---
load_dotenv()

# --- 2. IMPORTS ---
from flask_cors import CORS
from openai import OpenAI

# --- 3. CONFIGURE OPENAI ---
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found. Make sure it's in your .env file.")
    
    client = OpenAI(api_key=api_key)
    
    print("--- OpenAI Client Initialized ---")

except Exception as e:
    print(f"Error configuring OpenAI: {e}")

# --- 4. FLASK APP CONFIGURATION ---
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
CORS(app) # Enable CORS for our website
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- 5. GLOBAL "MEMORY" FOR CHAT ---
# We no longer need to store the DataFrame, just the *path* to the file
last_uploaded_filepath = None
csv_column_names = ""

# --- 6. CHART DATA HELPER FUNCTION (Unchanged) ---
def prepare_chart_data(df, recipe):
    chart_type = recipe.get('chart_type')
    x_col = recipe.get('x_column')
    y_col = recipe.get('y_column')
    
    if not x_col or not y_col:
        print(f"Skipping chart '{recipe.get('title')}' due to missing columns.")
        return None
    if x_col not in df.columns or (y_col not in df.columns and "Count of" not in y_col):
        print(f"Skipping chart '{recipe.get('title')}' due to invalid columns: {x_col}, {y_col}")
        return None

    print(f"--- Preparing data for: {recipe.get('title')} ---")
    try:
        if chart_type in ["Bar Chart", "Pie Chart", "Line Chart"]:
            if "Count of" in y_col:
                chart_data = df.groupby(x_col).size().reset_index(name='Count')
                chart_data.rename(columns={'Count': y_col}, inplace=True)
            else:
                if pd.api.types.is_numeric_dtype(df[y_col]):
                    chart_data = df.groupby(x_col)[y_col].sum().reset_index()
                else:
                    return None
            return json.loads(chart_data.to_json(orient='records'))
        elif chart_type == "Scatter Plot":
            sample_df = df.sample(n=min(500, len(df)))
            chart_data = sample_df[[x_col, y_col]]
            return json.loads(chart_data.to_json(orient='records'))
        elif chart_type == "Histogram":
            chart_data = df[[x_col]]
            return json.loads(chart_data.to_json(orient='records'))
        else:
            return None
    except Exception as e:
        print(f"Error preparing data for '{recipe.get('title')}': {e}")
        return None

# --- 7. AI VISUALIZATION FUNCTION (Updated to 15) ---
def get_ai_visualizations(df_schema, original_df):
    print("--- Capturing data schema for AI (for charts) ---")
    buffer = io.StringIO()
    df_schema.info(buf=buffer)
    data_schema_info = buffer.getvalue()
    first_5_rows = df_schema.head().to_string()

    prompt_text = f"""
    You are a helpful data analyst. A user has uploaded a CSV file.
    Your job is to suggest the best visualizations for a dashboard.
    Here is the data schema information from pandas `df.info()`:
    ---
    {data_schema_info}
    ---
    Here are the first 5 rows of data for context:
    ---
    {first_5_rows}
    ---
    Based *only* on this information, please suggest up to 15 useful visualizations (if possible, otherwise fewer).
    For each visualization, provide:
    1.  A short, clear `title` (e.g., "Total Sales by Region").
    2.  The best `chart_type` (e.g., "Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart", "Histogram").
    3.  The `x_column` to use (the exact column name).
    4.  The `y_column` to use (e.g., "Sales", "Profit", or "Count of OrderID").
    5.  A one-sentence `description` of what this chart shows.
    Return your answer as a *single, valid JSON array* (a list of objects).
    Do not include any other text, markdown, or explanations before or after the JSON array.
    """

    print("--- Sending prompt to OpenAI (for charts)... ---")
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a data analyst that only responds in valid JSON."},
                {"role": "user", "content": prompt_text}
            ],
            model="gpt-3.5-turbo-0125",
            temperature=0.1,
        )
        ai_response_text = chat_completion.choices[0].message.content
        print("--- AI Response Received (for charts) ---")
        
        start_index = ai_response_text.find('[')
        end_index = ai_response_text.rfind(']')
        if start_index == -1 or end_index == -1:
            raise ValueError("AI response did not contain a valid JSON array.")
        
        clean_json_text = ai_response_text[start_index : end_index + 1]
        recipes_list = json.loads(clean_json_text)
        
        final_charts_list = []
        for recipe in recipes_list:
            chart_data = prepare_chart_data(original_df, recipe)
            if chart_data:
                recipe['chart_data'] = chart_data
                final_charts_list.append(recipe)
        
        return final_charts_list
    except Exception as e:
        print(f"Error calling AI or parsing JSON: {e}")
        return {"error": "Failed to get AI analysis", "details": str(e)}

# --- 7.5 NEW: AI INSIGHTS FUNCTION ---
def get_ai_insights(df_schema_info, first_5_rows):
    print("--- Sending prompt to OpenAI (for insights)... ---")
    
    prompt_text = f"""
    You are a senior data analyst. You have been given a CSV file.
    Based on the data schema and first few rows, generate 10 high-level, interesting insights.
    
    Here is the data schema information from pandas `df.info()`:
    ---
    {df_schema_info}
    ---
    Here are the first 5 rows of data for context:
    ---
    {first_5_rows}
    ---

    RULES:
    1.  Your insights should be 1-sentence bullet points.
    2.  Focus on potential relationships (e.g., "It seems 'Profit' might be related to 'Discount'").
    3.  Identify key numerical and categorical columns to summarize (e.g., "The 'Region' column seems to be a key segment").
    4.  Do not make up specific numbers, just high-level observations.
    5.  Return your answer as a *single, valid JSON array of strings*.
    
    Example response:
    [
        "The dataset tracks sales, profit, and discounts across different regions and categories.",
        "'Profit' appears to sometimes be negative, suggesting some orders lose money.",
        "'OrderDate' could be used to analyze trends over time.",
        ...
    ]
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a data analyst that only responds in valid JSON."},
                {"role": "user", "content": prompt_text}
            ],
            model="gpt-3.5-turbo-0125", # Use a fast model for this
            temperature=0.2,
        )
        ai_response_text = chat_completion.choices[0].message.content
        print("--- AI Response Received (for insights) ---")
        
        start_index = ai_response_text.find('[')
        end_index = ai_response_text.rfind(']')
        if start_index == -1 or end_index == -1:
            raise ValueError("AI insights response did not contain a valid JSON array.")
        
        clean_json_text = ai_response_text[start_index : end_index + 1]
        insights_list = json.loads(clean_json_text)
        return insights_list
        
    except Exception as e:
        print(f"Error calling AI for insights: {e}")
        return ["Failed to generate insights. The AI model may be temporarily down."]


# --- 8. THE UPLOAD API ENDPOINT (NOW GETS CHARTS *AND* INSIGHTS) ---
@app.route("/api/upload", methods=['POST'])
def upload_file():
    
    global last_uploaded_filepath, csv_column_names 
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        filename = file.filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(save_path)

            # --- 1. LOAD THE PANDAS DATAFRAME ---
            try:
                original_df = pd.read_csv(save_path, on_bad_lines='skip')
            except Exception:
                original_df = pd.read_csv(save_path, error_bad_lines=False)
            
            # --- 2. SAVE FILEPATH TO GLOBAL MEMORY ---
            last_uploaded_filepath = os.path.abspath(save_path) # Save the *full* path
            csv_column_names = ", ".join(original_df.columns)
            
            # --- 3. PREPARE DATA FOR AI PROMPTS ---
            df_for_ai = original_df.copy()
            for col in df_for_ai.columns:
                if df_for_ai[col].dtype == 'object':
                    try: 
                        df_for_ai[col] = pd.to_datetime(df_for_ai[col], errors='coerce')
                    except Exception: 
                        pass
            simple_df = df_for_ai.select_dtypes(include=['number', 'object', 'datetime64'])
            
            # Get the schema and head for the prompts
            buffer = io.StringIO()
            simple_df.info(buf=buffer)
            data_schema_info = buffer.getvalue()
            first_5_rows = simple_df.head().to_string()

            # --- 4. CALL BOTH AI FUNCTIONS ---
            visualization_suggestions = get_ai_visualizations(simple_df, original_df)
            ai_insights = get_ai_insights(data_schema_info, first_5_rows) # <-- NEW
            
            print(f"--- File saved at {last_uploaded_filepath} and ready for chat. ---")
            
            # --- 5. RETURN ALL DATA ---
            return jsonify({
                "charts": visualization_suggestions,
                "insights": ai_insights, # <-- NEW
                "filepath": last_uploaded_filepath,
                "columns": csv_column_names
            }), 200

        except Exception as e:
            print(f"Error during upload or agent creation: {e}")
            return jsonify({"error": f"Could not process file: {e}"}), 500

# --- 9. "WHY" CHAT API ENDPOINT (Stable fix with Memory) ---
@app.route("/api/chat", methods=['POST'])
def chat_with_data():
    
    data = request.json
    question = data.get('question')
    metrics_encoded = data.get('metrics', '')
    chat_history = data.get('history', 'No prior conversation.') 
    
    filepath = data.get('filepath')
    columns = data.get('columns')

    if not question:
        return jsonify({"answer": "You must ask a question."}), 400
    
    if not filepath or not columns:
        return jsonify({"answer": "I'm sorry, I can't answer questions. Please upload a CSV file first."}), 400
    
    try:
        print(f"--- Chat question received: {question} ---")

        # --- THIS IS OUR NEW "WHY" META-PROMPT ---
        
        metrics_prompt = ""
        if metrics_encoded:
            from urllib.parse import unquote
            metrics_decoded = unquote(metrics_encoded)
            metrics_prompt = f"Here are some user-defined metrics to use if needed:\n{metrics_decoded}\n"
        
        safe_filepath = filepath.replace('\\', '\\\\')

        final_prompt = f"""
        You are a data analyst AI. Your only job is to write a single, executable, standalone Python script to answer the user's question.
        
        CSV Columns: {columns}
        CHAT HISTORY (for context): {chat_history}
        {metrics_prompt}

        ---
        First, analyze the user's question: "{question}"
        
        1.  Is this a "WHAT" question (asking for a specific calculation, like "what is the total profit", "who is the top customer")?
        2.  Or is this a "WHY" or "HOW" question (asking for an explanation or correlation, like "why did sales drop", "how did discounts affect profit")?
        
        If it is a "WHAT" question:
        Write a Python script that calculates the answer and prints a concise, human-readable sentence.
        Your script MUST start with `import pandas as pd` and `df = pd.read_csv("{safe_filepath}")`.
        Your script MUST NOT include any other `import` statements.
        Your script MUST end with a single `print()` statement.
        Example for "What's the total profit?":
        import pandas as pd
        df = pd.read_csv("{safe_filepath}")
        print(f"The total profit is ${{df['Profit'].sum():,.2f}}")
        
        If it is a "WHY" or "HOW" question:
        Write a Python script that finds correlations or data points that *might* explain the answer.
        You can use `df.corr()` for numerical columns.
        You can use `df.groupby()` to compare categories.
        Your answer should be an *observation*, not a *conclusion*.
        Your script MUST start with `import pandas as pd` and `df = pd.read_csv("{safe_filepath}", parse_dates=True)`.
        Example for "Why did profit drop in March?":
        import pandas as pd
        df = pd.read_csv("{safe_filepath}", parse_dates=['OrderDate'])
        # Make sure OrderDate is a datetime object
        df['OrderDate'] = pd.to_datetime(df['OrderDate'], errors='coerce')
        df_march = df[df['OrderDate'].dt.month == 3]
        march_profit = df_march['Profit'].sum()
        feb_profit = df[df['OrderDate'].dt.month == 2]['Profit'].sum()
        # You can't know the "why", but you can find correlations.
        march_discounts = df_march['Discount'].mean()
        feb_discounts = df[df['OrderDate'].dt.month == 2]['Discount'].mean()
        print(f"Profit dropped from {{feb_profit}} in Feb to {{march_profit}} in March. One observation: the average discount also changed from {{feb_discounts:.2f}} to {{march_discounts:.2f}} in that time.")

        Now, write *only* the Python script to answer: "{question}"
        """
        
        # --- END OF NEW PROMPT ---
        
        print("--- Sending meta-prompt to OpenAI to get code... ---")
        
        # 1. Ask the AI to write the code
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a Python data scientist that only responds with raw Python code. Do not include markdown ticks ```python or ```."},
                {"role": "user", "content": final_prompt}
            ],
            model="gpt-3.5-turbo-0125",
            temperature=0,
        )
        
        python_code_to_run = chat_completion.choices[0].message.content
        print(f"--- AI wrote this code: ---\n{python_code_to_run}\n---")
        
        # 2. Save the AI's code to the *system's* temp folder
        temp_dir = tempfile.gettempdir()
        temp_script_path = os.path.join(temp_dir, 'temp_chat_script.py')
        with open(temp_script_path, 'w', encoding='utf-8') as f:
            f.write(python_code_to_run)
            
        # 3. Execute the temporary file in a subprocess
        python_executable = sys.executable 
        
        print(f"--- Running script with: {python_executable} ---")
        
        # Run the script and capture its output
        result = subprocess.run(
            [python_executable, temp_script_path],
            capture_output=True,
            text=True,
            check=True, 
            encoding='utf-8',
            timeout=15 
        )
        
        # The answer is the "standard output" (the print() statement)
        final_answer = result.stdout.strip()
        
        if not final_answer:
            print("--- Code ran, but produced no output. ---")
            final_answer = "I'm sorry, I ran the code but it didn't produce an answer. Please try rephrasing your question."

        print(f"--- Final Answer: {final_answer} ---")

        # 4. Return the final answer
        return jsonify({"answer": final_answer}), 200

    except TimeoutExpired as e:
        print(f"---!! TIMEOUT ERROR: The AI's script took too long to run. ---")
        return jsonify({"answer": f"I'm sorry, the calculation took too long to run and was stopped. Please ask a simpler question."}), 500
    except subprocess.CalledProcessError as e:
        # This catches errors *inside the AI's code*
        print(f"---!! ERROR in AI's code: {e.stderr.strip()} ---")
        return jsonify({"answer": f"I'm sorry, the AI's code failed to run. (Error: {e.stderr.strip()})"}), 500
    except Exception as e:
        # This catches all other errors (like the AI's code being invalid)
        print(f"Error in chat endpoint: {e}")
        return jsonify({"answer": f"I'm sorry, I encountered an error. The AI's code may have failed. (Error: {e})"}), 500

# --- 10. RUN THE APP (ON PORT 5001) ---
if __name__ == "__main__":
    # We are changing the port to 5001 to avoid the "zombie" server
    app.run(debug=True, port=5001)