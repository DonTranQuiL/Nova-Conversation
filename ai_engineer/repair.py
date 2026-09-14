import os
import re
from openai import OpenAI

# 1. Get the error logs
try:
    with open("failed_logs.txt", "r") as f:
        logs = f.read()[-4000:]
except FileNotFoundError:
    print("No failed_logs.txt found. Exiting.")
    exit(0)

# 2. Extract the broken file path
# Matches:
# - Ruff syntax: --> path/to/file.py:21:6
# - Python tracebacks: File "path/to/file.py", line 21
# - Pytest assertion failures: path/to/file.py:21: AssertionError
patterns = [
    r'-->\s+([a-zA-Z0-9_\-/\\]+\.py):',
    r'File\s+"([a-zA-Z0-9_\-/\\]+\.py)"',
    r'([a-zA-Z0-9_\-/\\]+\.py):\d+:',
]

file_path = None
for pattern in patterns:
    matches = re.findall(pattern, logs)
    for candidate in reversed(matches):
        # Ignore external library/runner paths
        if "site-packages" not in candidate and ".venv" not in candidate:
            if os.path.exists(candidate):
                file_path = candidate
                break
    if file_path:
        break

if not file_path:
    print("Could not identify a repo file responsible for the failure.")
    print("This usually indicates a missing dependency, runner issue, or environmental error.")
    exit(0)

# 3. Read the broken code
try:
    with open(file_path, "r") as f:
        file_content = f.read()
except FileNotFoundError:
    print(f"Could not open extracted file path: {file_path}")
    exit(0)

# 4. Initialize AI
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("No OPENROUTER_API_KEY found.")
    exit(0)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

# 5. Snoop Dogg Prompt
prompt = f"""
You are the AI Self-Healing Mechanic for 'SkyRadar Fusion'. Your persona is Snoop Dogg.
The CI pipeline just tripped up, but you stay relaxed and fix the engine while it's running.

The error occurred in this file: {file_path}

Here is the broken code:
{file_content}

Here is the error log:
{logs}

1. Drop a quick 1-2 sentence explanation of why it broke, using Snoop Dogg's smooth slang. Keep it cool.
2. Provide the COMPLETELY FIXED Python code.
3. The fixed code MUST be inside a standard ```python code block. Keep the actual Python logic strictly professional—no slang in the variables or functions, just a clean, working fix so we can merge it, ya dig?

IMPORTANT: You must start your response with the exact line:
FILEPATH: {file_path}
Then write your Snoop intro.
Then output the fixed code exactly starting with CODE: and then the ```python block.
"""

# 6. Request Fix
try:
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = completion.choices[0].message.content.strip()

    print("\n--- AI MECHANIC REPORT ---")
    print(response_text)
    print("--------------------------\n")

    # 7. Parse the code out of the response
    lines = response_text.splitlines()
    target_file = None
    code_lines = []
    is_code = False

    for line in lines:
        if line.startswith("FILEPATH:"):
            parsed_target = line.replace("FILEPATH:", "").strip()
            if parsed_target and parsed_target != "None":
                target_file = parsed_target
        elif line.startswith("CODE:") or line.startswith("```python"):
            is_code = True
            continue
        elif is_code:
            if line.startswith("```"):
                is_code = False
            else:
                code_lines.append(line)

    # 8. Apply the fix
    if target_file and os.path.exists(target_file) and code_lines:
        with open(target_file, "w") as f:
            f.write("\n".join(code_lines))
        print(f"Patched {target_file} successfully.")
    else:
        print(f"Aborting: Invalid target file ({target_file}) or no patch code generated.")

except Exception as e:
    print(f"Repair failed: {e}")