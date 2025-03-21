import os
import json
import time
import datetime
import logging
import re
import shutil
import openai  # Use standard OpenAI client with custom base URL
from jinja2 import Template  # For dynamic prompt templating
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
import requests

# ==================== CONFIGURATION & LOGGING SETUP ====================

# Configure detailed logging (to console and file)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
LOG_FILE = "automation_log.txt"
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(file_handler)

# ==================== GLOBAL FILE PATHS & DIRECTORIES ====================

BASE_DIR = "VitB12_Synthesis_Optimizer"
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
CONTEXT_DIR = os.path.join(PROMPTS_DIR, "context")
PREVIOUS_ATTEMPTS_DIR = os.path.join(CONTEXT_DIR, "previous_attempts")
ADDITIONAL_RESOURCES_DIR = os.path.join(CONTEXT_DIR, "additional_resources")
NOTES_DIR = os.path.join(BASE_DIR, "notes")
SYNTHESIS_STEPS_DIR = os.path.join(NOTES_DIR, "synthesis_steps")
CONFIGS_DIR = os.path.join(BASE_DIR, "configs")
VERSIONS_DIR = os.path.join(BASE_DIR, "versions")

# Key files (read/write as indicated)
GENERAL_CONTEXT_FILE = os.path.join(CONTEXT_DIR, "general_context.txt")  # Read
BASE_PROMPT_FILE = os.path.join(PROMPTS_DIR, "base_prompt.md")  # Read/Write by AI
AI_PROGRESS_TRACKER_FILE = os.path.join(BASE_DIR, "AI_progress_tracker.txt")  # Read & Write
AI_REQUESTS_FILE = os.path.join(NOTES_DIR, "ai_requests.json")  # Write
USER_RESPONSES_FILE = os.path.join(NOTES_DIR, "user_responses.json")  # Read
INTERVALS_FILE = os.path.join(CONFIGS_DIR, "intervals.json")  # Config
SETTINGS_FILE = os.path.join(CONFIGS_DIR, "settings.json")  # Config
INDEX_FILE = os.path.join(BASE_DIR, "index.md")  # Auto-index file
CONTEXT_SUMMARY_FILE = os.path.join(BASE_DIR, "context_summary.txt")  # Dynamic summary file
HISTORY_FILE = os.path.join(BASE_DIR, "ai_history.json")  # Stores all AI messages

# ==================== OPENROUTER API CONFIGURATION ====================
# Use environment variables for sensitive data
OPENROUTER_API_KEY = "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"

# Configure the OpenAI client to use OpenRouter API
openai.api_base = "https://openrouter.ai/api/v1"


# ==================== UTILITY FUNCTIONS ====================

def create_directory_structure():
    """
    Create necessary directories and initialize default files, versioning, and history.
    """
    directories = [
        BASE_DIR, PROMPTS_DIR, CONTEXT_DIR, PREVIOUS_ATTEMPTS_DIR,
        ADDITIONAL_RESOURCES_DIR, NOTES_DIR, SYNTHESIS_STEPS_DIR, CONFIGS_DIR, VERSIONS_DIR
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logging.info(f"Directory ensured: {directory}")

    # Default general context
    if not os.path.exists(GENERAL_CONTEXT_FILE):
        write_file(GENERAL_CONTEXT_FILE,
                   """ # General Context and Constraints for Vitamin B12 Synthesis Optimization

Vitamin B12, also known as cobalamin, is a water-soluble vitamin essential for DNA synthesis, nervous system function, red blood cell formation, and amino acid metabolism.

## Current State:
- Synthetic pathway: 22 chemical reactions.
- Current total yield: 0.05%.

## Molecular Constraints:
- Initial constraint: prefer smaller molecules with up to 3 carbon atoms, but exceptions permitted if chemically beneficial or justified.

## Chemical Evaluation Criteria:
You will iteratively evaluate each pathway on:
- **Chemical Feasibility** (reaction validity, intermediate stability, product formation)
- **Estimated Yield** (stepwise and cumulative)
- **Reaction Conditions** (solvents, temperature, pressure, reagents, catalysts)
- **Complexity** (difficulty of reaction setup, expertise needed, purification)
- **Cost and Resource Requirements** (economic analysis, reagent availability)
- **Time Efficiency** (reaction duration per step, total duration)

## Evaluation Priorities (highest to lowest):
1. Yield improvement
2. Reduction of reaction steps
3. Complexity & resource minimization
4. Cost efficiency
5. Time efficiency
6. Environmental/Safety considerations (lowest priority)

## Interaction:
Clearly request additional scientific resources whenever you need them. Use structured syntax to issue resource requests. The provided files and resources will be managed and indexed automatically.

Continuously update your progress in the AI_progress_tracker.txt.
""")
    # Default base prompt (base plan)
    if not os.path.exists(BASE_PROMPT_FILE):
        write_file(BASE_PROMPT_FILE,
                   """# AI Prompt for Optimizing Vitamin B12 (Cobalamin) Synthesis

## Objective:
Develop an improved synthetic route for Vitamin B12 (cobalamin). The current pathway has 22 reactions and a total yield of 0.05%. Your goal is to significantly improve both the number of steps (reduce below 22) and the yield (exceed 0.05%).

## Tasks:
- **Propose Reaction Pathways** iteratively, each better than the last based on evaluation.
- **Evaluate Feasibility** of reactions: chemical viability, intermediate stability, and overall feasibility.
- **Estimate Yield**: clearly document theoretical yield per step and cumulative yield.
- **Analyze Reaction Conditions**: temperature, pressure, solvents, reagents, and catalysts.
- **Assess Complexity**: equipment needs, purification, handling, and required expertise.
- **Estimate Time and Cost**: reaction duration per step, total synthesis duration, reagent availability, and cost-effectiveness.
- **Request Additional Resources** explicitly if required, using clear, structured requests.

## Evaluation Priority (most to least important):
1. Yield improvement
2. Reduction in reaction steps
3. Reduced complexity and resource requirements
4. Economic feasibility and cost-effectiveness
5. Reaction time reduction
6. Safety and environmental factors (lowest priority)

## Output Requirements:
- Clearly explained reaction steps.
- Detailed reaction diagrams for each intermediate and mechanism.
- Summaries clearly outlining bottlenecks or limitations and suggesting improvements.

## Workflow:
Iteratively optimize through continuous trial-and-error. Summarize evaluations and explicitly justify each adjustment.

## Additional Resources:
When necessary, clearly request additional scientific resources, articles, or databases. They will be provided promptly.

Confirm your understanding of this prompt clearly before starting.
""")
    # Progress tracker
    if not os.path.exists(AI_PROGRESS_TRACKER_FILE):
        write_file(AI_PROGRESS_TRACKER_FILE, """# AI Progress Tracker

## CURRENT STATUS:
Initial setup complete. Awaiting AI confirmation and initial reaction pathway hypothesis.

## LAST DECISION MADE:
No decision yet—initial step pending.

## NEXT STEPS:
- Confirm understanding of base_prompt and general_context.
- Propose first iteration of an optimized Vitamin B12 synthesis pathway.

## CURRENT NEEDS:
No resources requested yet.

## QUESTIONS TO USER:
None yet.

## NOTES:
Program initialized successfully. Awaiting first AI-generated synthesis attempt.
""")
    # JSON files for requests and responses
    for file in [AI_REQUESTS_FILE, USER_RESPONSES_FILE]:
        if not os.path.exists(file):
            save_json_file(file, {})
    # Config files
    if not os.path.exists(INTERVALS_FILE):
        save_json_file(INTERVALS_FILE, {
    "auto_pause_interval_steps": 3,
    "progress_update_interval_minutes": 30,
    "max_retry_attempts": 3,
    "retry_wait_seconds": 10
})
    # Check if the settings file exists
    if not os.path.exists(SETTINGS_FILE):
        # Define the settings data
        settings_data = {
            "ai_model": "DeepSeek-R1-DeepThinking",
            "token_limits": {
                "detailed": 64096,
                "request": 512,
                "status": 2048
            },
            "file_structure": {
                "prompt_dir": "./prompts",
                "context_dir": "./prompts/context",
                "notes_dir": "./notes",
                "resource_request_file": "./notes/ai_requests.json",
                "user_response_file": "./notes/user_responses.json",
                "additional_resources_dir": "./prompts/context/additional_resources",
                "previous_attempts_dir": "./prompts/context/previous_attempts"
            },
            "syntax_normalization": {
                "resource_request_structure": {
                    "request_id": "string",
                    "timestamp": "ISO8601_string",
                    "requested_resources": [
                        {
                            "type": "resource_type",
                            "description": "clear_description"
                        }
                    ],
                    "reason": "string"
                }
            },
            "logging": {
                "log_file": "./progress_log.txt",
                "verbose_console_output": True
            }
        }

        # Save the settings data to a JSON file
        with open(SETTINGS_FILE, 'w') as file:
            json.dump(settings_data, file, indent=4)

    # Initialize index and context summary
    update_index_file()
    if not os.path.exists(CONTEXT_SUMMARY_FILE):
        write_file(CONTEXT_SUMMARY_FILE, "Context Summary:\n")
    if not os.path.exists(HISTORY_FILE):
        save_json_file(HISTORY_FILE, [])


def read_file(file_path, encoding='utf-8', errors='replace'):
    """Read file content with encoding error handling."""
    try:
        with open(file_path, 'r', encoding=encoding, errors=errors) as f:
            return f.read()
    except UnicodeDecodeError:
        # Try alternate encodings if UTF-8 fails
        for alt_encoding in ['cp1252', 'latin-1', 'ISO-8859-1']:
            try:
                with open(file_path, 'r', encoding=alt_encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # If all encodings fail, read as binary and decode with replacement
        with open(file_path, 'rb') as f:
            binary_content = f.read()
            return binary_content.decode('utf-8', errors='replace')


def write_file(file_path, content):
    """
    Write content to a file.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:  # Specify UTF-8 encoding
        f.write(content)

def append_to_file(file_path, content):
    """
    Append content to a file.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'a', encoding='utf-8') as f:  # Specify UTF-8 encoding
        f.write(content + "\n")


def save_json_file(filepath, data):
    """Save data as formatted JSON."""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)


def load_json_file(filepath):
    """Load JSON data from a file; return {} if error."""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def update_progress_tracker(message):
    """
    Update the AI progress tracker file with a timestamped message.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_to_file(AI_PROGRESS_TRACKER_FILE, f"[{timestamp}] {message}")
    logging.info(f"Progress tracker updated: {message}")


def update_index_file():
    """Automatically update an index file listing all accessible files."""
    index_lines = ["# Accessible Files Index\n"]
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            if file != os.path.basename(INDEX_FILE):
                index_lines.append(f"- {os.path.relpath(os.path.join(root, file), BASE_DIR)}")
    write_file(INDEX_FILE, "\n".join(index_lines))
    logging.info("Index file updated.")


def get_recent_history(n=10):
    """Return a string with the last n history entries."""
    history = load_json_file(HISTORY_FILE)
    entries = history[-n:]
    return "\n".join([f"{entry['timestamp']} - {entry['role']}: {entry['message']}" for entry in entries])


def record_history(message, role="assistant"):
    """Append an AI message to the history file."""
    history = load_json_file(HISTORY_FILE)
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "role": role,
        "message": message
    }
    history.append(entry)
    save_json_file(HISTORY_FILE, history)


def update_context_summary():
    """
    Update the context summary file by summarizing the recent progress and history.
    (This is a stub; you might integrate a summarization model here.)
    """
    recent_progress = read_file(AI_PROGRESS_TRACKER_FILE)[-1000:]  # Last 1000 characters
    recent_history = get_recent_history(10)
    summary = f"Recent Progress:\n{recent_progress}\nRecent History:\n{recent_history}\n"
    write_file(CONTEXT_SUMMARY_FILE, summary)
    logging.info("Context summary updated.")


def semantic_file_search(keyword, search_dir=CONTEXT_DIR):
    """
    Perform a simple semantic search for files containing the keyword.
    (Stub for embeddings-based search; here we do simple filename matching.)
    """
    matches = []
    for root, _, files in os.walk(search_dir):
        for file in files:
            if keyword.lower() in file.lower():
                matches.append(os.path.join(root, file))
    return matches


def render_prompt(template_str, context):
    """
    Render a prompt using Jinja2 templating with the given context.
    """
    template = Template(template_str)
    return template.render(context)


def save_versioned_file(filepath, content):
    """
    Save a version of a file by copying it into the versions folder with a timestamp.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(filepath)
    versioned_path = os.path.join(VERSIONS_DIR, f"{base_name}_{timestamp}")
    write_file(versioned_path, content)
    logging.info(f"Versioned file saved: {versioned_path}")


def pause_for_user(message="Press Enter to continue..."):
    """
    Pause execution and wait for user input.
    """
    # print(message)
    # input()
    logging.info(f"pausing skipped")


def check_for_new_resources():
    """
    Check if any new resources have been added to the resources directory.
    Returns a list of newly added resource filenames.
    """
    resources_list_file = os.path.join(CONTEXT_DIR, "resources_list.json")
    previous_resources = load_json_file(resources_list_file)

    # Get current resources
    current_resources = []
    for root, _, files in os.walk(ADDITIONAL_RESOURCES_DIR):
        for file in files:
            current_resources.append(os.path.join(root, file))

    # Find new resources
    previous_set = set(previous_resources.get("files", []))
    current_set = set(current_resources)
    new_resources = list(current_set - previous_set)

    # Update resources list
    save_json_file(resources_list_file, {"files": list(current_set)})

    return new_resources


def process_ai_commands(text):
    """
    Parse and execute AI commands embedded in the output.
    Recognized commands:
      - FILE_UPDATE: <relative_filepath> : <content>
      - FILE_ADD: <relative_filepath> : <content>
      - FILE_DELETE: <relative_filepath>
      - FILE_REQUEST: <relative_filepath>
      - PAUSE_FOR_RESOURCES
      - CONTEXT_UPDATE: <new context content>
    """
    # Improved regex pattern for multiline content
    update_matches = re.findall(r"FILE_UPDATE:\s*(.+?)\s*:([\s\S]+?)(?=FILE_|$)", text)
    for filepath, content in update_matches:
        full_path = os.path.join(BASE_DIR, filepath.strip())
        append_to_file(full_path, content.strip())
        update_progress_tracker(f"FILE_UPDATE executed for {filepath.strip()}")
        logging.info(f"FILE_UPDATE for: {filepath.strip()}")

    add_matches = re.findall(r"FILE_ADD:\s*(.+?)\s*:([\s\S]+?)(?=FILE_|$)", text)
    for filepath, content in add_matches:
        full_path = os.path.join(BASE_DIR, filepath.strip())
        write_file(full_path, content.strip())
        update_progress_tracker(f"FILE_ADD executed for {filepath.strip()}")
        logging.info(f"FILE_ADD for: {filepath.strip()}")

    delete_matches = re.findall(r"FILE_DELETE:\s*(.+?)(?=FILE_|$)", text)
    for filepath in delete_matches:
        filepath = filepath.strip()
        full_path = os.path.join(BASE_DIR, filepath)
        if os.path.exists(full_path):
            os.remove(full_path)
            update_progress_tracker(f"FILE_DELETE executed for {filepath}")
            logging.info(f"FILE_DELETE for: {filepath}")

    request_matches = re.findall(r"FILE_REQUEST:\s*(.+?)(?=FILE_|$)", text)
    for requested in request_matches:
        requested = requested.strip()
        update_progress_tracker(f"FILE_REQUEST received for {requested}")
        logging.info(f"FILE_REQUEST for: {requested}")

    if "PAUSE_FOR_RESOURCES" in text:
        update_progress_tracker("PAUSE_FOR_RESOURCES command encountered.")
        logging.info("Pausing for resources as requested by AI.")
        pause_for_user("AI requested additional resources. Please add them and press Enter to continue...")

    context_update_match = re.search(r"CONTEXT_UPDATE:\s*([\s\S]+?)(?=FILE_|PAUSE_FOR_RESOURCES|$)", text)
    if context_update_match:
        new_context = context_update_match.group(1).strip()
        append_to_file(GENERAL_CONTEXT_FILE, "\n" + new_context)
        update_progress_tracker("CONTEXT_UPDATE executed.")
        logging.info("CONTEXT_UPDATE applied.")


# ==================== OPENROUTER AI API CALL FUNCTION ====================

def call_openrouter_ai(prompt, token_limit, primary_model="deepseek/deepseek-r1:free", fallback_models=None,
                       max_retries=3):
    """
    Call the OpenRouter API with the provided prompt using requests library.
    Includes fallback logic and retry mechanism.
    """

    if fallback_models is None:
        fallback_models = ["deepseek/deepseek-r1-zero:free", "deepseek/deepseek-chat:free",
                           "deepseek/deepseek-r1-distill-qwen-32b:free", "google/gemini-2.0-flash-exp:free"]

    messages = [{"role": "user", "content": prompt}]
    attempt = 0

    while attempt < max_retries:
        try:
            # Prepare the request to OpenRouter API
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "http://localhost",  # You might want to replace this with your actual site URL
                "X-Title": "AI Assistant Application"  # You might want to replace this with your actual site name
            }

            # Prepare the payload
            payload = {
                "model": primary_model,
                "messages": messages,
                "max_tokens": token_limit
            }

            # Add fallback models if provided
            if fallback_models:
                payload["fallbacks"] = fallback_models

            # Make the API request
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload)
            )

            # Check if the request was successful
            response.raise_for_status()
            response_data = response.json()

            # Extract the generated content
            reply = response_data["choices"][0]["message"]["content"]
            model_used = response_data.get("model", primary_model)

            logging.info(f"API call successful. Model used: {model_used}")
            return reply

        except Exception as e:
            attempt += 1
            logging.error(f"API call failed (attempt {attempt}): {e}")
            time.sleep(2 * attempt)  # Exponential backoff

    logging.error("Max retries exceeded for API call.")
    return "Error: Unable to generate AI response after multiple attempts."


# ==================== MINIMAL CONTEXT & HISTORY ====================

def get_minimal_context():
    """
    Gather minimal context for each AI call.
    Always include the base prompt, general context, context summary, and recent history.
    """
    base = read_file(BASE_PROMPT_FILE)
    general = read_file(GENERAL_CONTEXT_FILE)
    summary = read_file(CONTEXT_SUMMARY_FILE)
    recent = get_recent_history(10)
    return "\n".join([base, general, summary, recent])


# ==================== MAIN STEP & SUB-STEP EXECUTION ====================

def execute_main_step(step_name, iteration, token_limit, extra_context=""):
    """
    Execute one main step by:
      1. Asking the AI for a JSON array of 5–10 sub-steps.
      2. Iterating over each sub-step (each executed via its own API call).
      3. Logging outputs, processing commands, and versioning.
    Returns the combined output of all sub-steps.
    """
    # Prompt the AI for a list of sub-steps (in JSON)
    sub_steps_prompt = (
        f"Main Step: {step_name}\nIteration: {iteration}\n{extra_context}\n"
        "Please provide a JSON array (5-10 items) listing the sub-steps required to complete this main step. "
        "Each sub-step should be a brief instruction. Output only a valid JSON array."
    )
    sub_steps_response = call_openrouter_ai(sub_steps_prompt, token_limit)
    try:
        # Extract the JSON portion by finding the first '[' and last ']'
        json_str = sub_steps_response
        # Look for JSON array pattern
        match = re.search(r'\[[\s\S]*?\]', sub_steps_response)
        if match:
            json_str = match.group(0)
        sub_steps_list = json.loads(json_str)
        if not isinstance(sub_steps_list, list):
            raise ValueError("Response is not a list")
    except Exception as e:
        logging.error(f"Error parsing sub-step list for {step_name}: {e}")
        # Fallback to simple line-by-line parsing
        sub_steps_list = [line.strip() for line in sub_steps_response.split("\n")
                          if line.strip() and not line.strip().startswith("```")]
    logging.info(f"Sub-step list for {step_name} (iter {iteration}): {sub_steps_list}")
    combined_output = []
    # Process each sub-step individually.
    for i, sub_step in enumerate(sub_steps_list, start=1):
        sub_step_prompt = (
            f"Main Step: {step_name}\nIteration: {iteration}\nSub-step {i}: {sub_step}\n"
            "Please complete this sub-step with detailed output. "
            "If you wish to update, add, or delete files, output a command using the following syntax:\n"
            "   FILE_UPDATE: <relative_filepath> : <content>\n"
            "   FILE_ADD: <relative_filepath> : <content>\n"
            "   FILE_DELETE: <relative_filepath>\n"
            "   FILE_REQUEST: <relative_filepath>\n"
            "   CONTEXT_UPDATE: <new context>\n"
            "If additional resources are needed, include the command PAUSE_FOR_RESOURCES.\n"
            "Provide detailed explanation and results for this sub-step."
        )
        sub_step_output = call_openrouter_ai(sub_step_prompt, token_limit)
        # Process any embedded AI commands.
        process_ai_commands(sub_step_output)
        # Save the sub-step output in its own versioned file.
        sub_step_filename = os.path.join(SYNTHESIS_STEPS_DIR,
                                         f"{step_name.replace(' ', '_')}_iter_{iteration}_substep_{i}.md")
        write_file(sub_step_filename, sub_step_output)
        save_versioned_file(sub_step_filename, sub_step_output)
        update_progress_tracker(f"{step_name} iter {iteration}: Sub-step {i} completed.")
        combined_output.append(sub_step_output)
        logging.info(f"Completed sub-step {i} for {step_name} (iter {iteration}).")
        print(f"[{step_name}][Iter {iteration}][Sub-step {i}]: {sub_step_output[:200]}...")
        if "PAUSE_FOR_RESOURCES" in sub_step_output:
            pause_for_user("AI requested additional resources. Please add them and press Enter to continue...")
    return "\n\n".join(combined_output)


# ==================== MAIN ITERATIVE PROCESS ====================

def main():
    """
    Main iterative loop for the AI-driven optimization process.
    Each iteration:
      - Loads minimal context (base prompt, general context, recent context summary, recent history).
      - Executes a series of main steps (each broken into multiple sub-steps).
      - Handles file requests/updates and pauses when needed.
      - Updates progress, context summary, and the file index.
    """
    create_directory_structure()
    settings = load_json_file(SETTINGS_FILE)
    intervals = load_json_file(INTERVALS_FILE)
    max_iterations = settings.get("max_iterations", 8)
    iteration_pause = intervals.get("iteration_pause", 3)
    token_limits = settings.get("token_limits", {"detailed": 32092, "request": 1024, "status": 2048})

    iteration = 8
    while iteration <= max_iterations:
        logging.info(f"--- Starting iteration {iteration} ---")
        # Build minimal context for this iteration
        minimal_context = get_minimal_context()
        # Define main steps; these can be extended or modified as needed.
        main_steps = [
            "Brainstorming Phase",
            "Develop Solutions Phase",
            "Reaction Steps Breakdown",
            "Error Checking & Corrections"
        ]
        if iteration == max_iterations:
            main_steps.extend(["Detailed Final Description to result.md", "Final Re-Check & Review"])
        main_steps.extend(["Resource Requests Check", "Index Update & Manual Oversight"])
        # Execute each main step.
        for step in main_steps:
            logging.info(f"Executing main step: {step} (Iteration {iteration})")
            step_output = execute_main_step(step, iteration, token_limits["detailed"], extra_context=minimal_context)
            step_filename = os.path.join(SYNTHESIS_STEPS_DIR, f"{step.replace(' ', '_')}_iter_{iteration}.md")
            write_file(step_filename, step_output)
            save_versioned_file(step_filename, step_output)
            update_progress_tracker(f"{step} in iteration {iteration} completed.")
            logging.info(f"Completed main step: {step} (Iteration {iteration})")
        # Check if new resources have been added.
        new_resources = check_for_new_resources()
        if new_resources:
            update_progress_tracker(f"Iteration {iteration}: New resources detected: {new_resources}")
        update_context_summary()  # Update dynamic context for subsequent iterations.
        if iteration % iteration_pause == 0 and iteration != max_iterations:
            logging.info(f"Pausing after iteration {iteration} for manual review.")
            pause_for_user()
        update_index_file()  # Always keep the file index up-to-date.
        iteration += 1
    logging.info("Optimization process completed. Review synthesis_steps and AI_progress_tracker.txt for details.")


if __name__ == "__main__":
    main()
