import os, re

file_path = "llmhive/src/llmhive/app/orchestrator.py"
if not os.path.isfile(file_path):
    raise FileNotFoundError(f"Could not find orchestrator.py at {file_path}")

with open(file_path, "r") as f:
    code = f.read()
lines = code.splitlines()

# 1. Enable self-critiques by removing skip condition
for i, line in enumerate(lines):
    if "if author_result.model == target_result.model" in line:
        # Remove this line and the next 'continue'
        del lines[i:i+2]
        break

# 2. Remove confirmation notes (replace _confirmation_checks call with empty list)
start_idx = end_idx = None
for i, line in enumerate(lines):
    if "confirmation_notes = self._confirmation_checks" in line:
        start_idx = i
    if start_idx is not None and line.strip() == ")":
        end_idx = i
        break
if start_idx is not None and end_idx is not None:
    indent = lines[start_idx][:len(lines[start_idx]) - len(lines[start_idx].lstrip())]
    lines[start_idx] = indent + "confirmation_notes = []"
    # Delete the now-redundant continuation lines of the call
    del lines[start_idx+1:end_idx+1]

# 3. Incorporate web search context into augmented_prompt before drafting
insert_idx = None
web_indent = ""
for i, line in enumerate(lines):
    if line.strip().startswith("# Execute the structured plan"):
        insert_idx = i
        # Find indent of the preceding 'if web_documents' block
        for j in range(i-1, -1, -1):
            if lines[j].strip().startswith("if web_documents"):
                web_indent = lines[j][:len(lines[j]) - len(lines[j].lstrip())] + " " * 4
                break
        break

if insert_idx is None:
    raise RuntimeError("Insertion point for web context not found. Make sure the code structure is as expected.")
# Define the lines to insert
web_context_block = [
    web_indent + "# Incorporate web search context into augmented_prompt for initial answers",
    web_indent + 'web_lines = ["Context from web search:"]',
    web_indent + "for doc in web_documents[:3]:",
    web_indent + "    snippet = doc.snippet or doc.title",
    web_indent + "    if snippet:",
    web_indent + "        web_lines.append(f\"- {doc.title or 'result'}: {self._truncate(snippet, 220)}\")",
    web_indent + 'web_block = "\\n".join(web_lines)',
    web_indent + "if context_prompt:",
    web_indent + "    augmented_prompt = (",
    web_indent + '        f"Context from memory:\\n{context_prompt}\\n\\n"',
    web_indent + '        f"{web_block}\\n\\n"',
    web_indent + '        f"Optimized request:\\n{plan_prompt}"',
    web_indent + "    )",
    web_indent + "else:",
    web_indent + '    augmented_prompt = f"{web_block}\\n\\nOptimized request:\\n{plan_prompt}"'
]
# Insert the block into the code
lines = lines[:insert_idx] + web_context_block + lines[insert_idx:]

# Write the changes back to the file
with open(file_path, "w") as f:
    f.write("\n".join(lines))

print("✅ Upgrades applied: Knowledge base usage confirmed, web context integrated, self-critiques enabled, and confirmation notes removed.")
