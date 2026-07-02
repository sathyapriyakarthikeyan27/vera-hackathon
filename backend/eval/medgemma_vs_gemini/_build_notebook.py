"""
Generates medgemma_vs_gemini.ipynb — a self-contained Colab notebook that
compares MedGemma 4B (local on the Colab T4) against Gemini 2.5 Pro (API)
on VERA's Agent 3 tasks: clinical-signal extraction + plain-language explanation.

Run:  py _build_notebook.py
Output: medgemma_vs_gemini.ipynb  (upload this to colab.research.google.com)
"""
import json
from pathlib import Path

# ── Shared prompts — copied VERBATIM from backend/agents/records_explainer/agent.py
# Both models must see identical prompts, or you are comparing prompts, not models.
SIGNALS_PROMPT = '''You are a clinical data extraction system. Read this medical document carefully and extract structured clinical signals for a cancer risk assessment system.

Your task is to identify findings that are relevant to cancer risk, abnormalities, polyps, lesions, irregular tissue, elevated markers, or recommendations for urgent follow-up.

You MUST return ONLY a valid JSON object in exactly this format. No prose before or after. No markdown fences. No explanation. Just the JSON:
{
  "anomalies": ["specific finding 1", "specific finding 2"],
  "severity": "high",
  "confidence": 0.85,
  "specialist_signal": "Gastroenterologist",
  "urgency_flag": true
}

Field definitions, follow these exactly:
- "anomalies": array of strings. Each string is one specific clinical finding. Be specific: "12mm tubulovillous adenoma, ascending colon" not "abnormality found". Empty array [] if document is normal.
- "severity": exactly one of "high", "medium", or "low".
- "confidence": float 0.0 to 1.0.
- "specialist_signal": exact specialist type (e.g. "Gastroenterologist", "Oncologist", "Pulmonologist", "Dermatologist"), or null.
- "urgency_flag": true if the document recommends urgent follow-up. Otherwise false.

If the document is normal with no concerning findings: anomalies=[], severity="low", urgency_flag=false.
Return only the JSON object.'''

EXPLAIN_PROMPT = '''You are VERA, a warm and caring health AI companion.

Please explain this medical document in plain language in English.

Structure your response in exactly this order:
1. What this document is (1 sentence)
2. Key findings, what it shows (2-3 sentences, plain language only)
3. Anything that needs attention, flag urgently but calmly, never alarming
4. What to do next (1-2 concrete sentences)

Rules:
- Never diagnose. Never say "you have cancer" or equivalent.
- No medical jargon without plain-language explanation in parentheses.
- If something is flagged as abnormal, say so clearly but calmly.
- End with: "This is a plain-language explanation only. Please discuss these findings with your doctor."
- Do not use em dashes.'''


def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": _src(lines)}


def code(*lines):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": _src(lines)}


def _src(lines):
    text = "\n".join(lines)
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + [parts[-1]]


cells = []

cells.append(md(
    "# MedGemma 4B  vs  Gemini 2.5 Pro — VERA Agent 3 eval",
    "",
    "Compares the two models on VERA's Records Explainer tasks:",
    "",
    "1. **Clinical-signal extraction** (structured JSON) — scored objectively against ground truth.",
    "2. **Plain-language explanation** (prose) — scored with rule checks + an optional LLM judge.",
    "",
    "MedGemma runs locally on this Colab T4 GPU. Gemini runs via API. Everything runs in this one notebook.",
    "",
    "**Before you start:** Runtime -> Change runtime type -> **T4 GPU**.",
))

cells.append(md("## 1. Install dependencies"))
cells.append(code(
    "!pip install -q -U transformers accelerate bitsandbytes pillow pdf2image google-generativeai",
    "!apt-get -qq install -y poppler-utils   # for pdf2image (PDF -> PNG)",
))

cells.append(md(
    "## 2. Authenticate",
    "",
    "- **Hugging Face:** accept the license at https://huggingface.co/google/medgemma-4b-it first, then paste a read token below.",
    "- **Gemini:** paste your `GEMINI_API_KEY` (the same one VERA's backend uses).",
))
cells.append(code(
    "from huggingface_hub import login",
    "login()   # paste HF token when prompted",
))
cells.append(code(
    "import os, getpass",
    "os.environ['GEMINI_API_KEY'] = getpass.getpass('Gemini API key: ')",
    "import google.generativeai as genai",
    "genai.configure(api_key=os.environ['GEMINI_API_KEY'])",
))

cells.append(md("## 3. Load MedGemma 4B onto the T4"))
cells.append(code(
    "import torch",
    "from transformers import AutoProcessor, AutoModelForImageTextToText",
    "",
    "MODEL_ID = 'google/medgemma-4b-it'",
    "medgemma = AutoModelForImageTextToText.from_pretrained(",
    "    MODEL_ID, torch_dtype=torch.bfloat16, device_map='auto')",
    "processor = AutoProcessor.from_pretrained(MODEL_ID)",
    "print('MedGemma loaded on:', medgemma.device)",
))

cells.append(md(
    "## 4. Shared prompts",
    "",
    "Copied verbatim from `backend/agents/records_explainer/agent.py` so both models get identical instructions.",
))
cells.append(code(
    "SIGNALS_PROMPT = " + repr(SIGNALS_PROMPT),
    "",
    "EXPLAIN_PROMPT = " + repr(EXPLAIN_PROMPT),
))

cells.append(md("## 5. Two backends, one interface"))
cells.append(code(
    "import io, base64, asyncio",
    "from PIL import Image",
    "",
    "def _to_image(content: bytes, mime: str) -> Image.Image:",
    "    if mime == 'application/pdf':",
    "        from pdf2image import convert_from_bytes",
    "        return convert_from_bytes(content, dpi=200)[0].convert('RGB')  # first page",
    "    return Image.open(io.BytesIO(content)).convert('RGB')",
    "",
    "class MedGemmaBackend:",
    "    name = 'medgemma-4b-it'",
    "    def run(self, content, mime, prompt):",
    "        img = _to_image(content, mime)",
    "        messages = [{'role': 'user', 'content': [",
    "            {'type': 'text', 'text': prompt}, {'type': 'image', 'image': img}]}]",
    "        inputs = processor.apply_chat_template(",
    "            messages, add_generation_prompt=True, tokenize=True,",
    "            return_dict=True, return_tensors='pt').to(medgemma.device, dtype=torch.bfloat16)",
    "        with torch.inference_mode():",
    "            out = medgemma.generate(**inputs, max_new_tokens=600, do_sample=False)",
    "        return processor.decode(out[0][inputs['input_ids'].shape[-1]:], skip_special_tokens=True)",
    "",
    "class GeminiBackend:",
    "    name = 'gemini-2.5-pro'",
    "    def __init__(self):",
    "        self.model = genai.GenerativeModel('gemini-2.5-pro')",
    "    def run(self, content, mime, prompt):",
    "        # Gemini accepts PDF bytes directly; send the raw file for parity of source.",
    "        resp = self.model.generate_content([{'mime_type': mime, 'data': content}, prompt])",
    "        return resp.text.strip()",
    "",
    "backends = [MedGemmaBackend(), GeminiBackend()]",
))

cells.append(md(
    "## 6. Upload your dataset",
    "",
    "Upload your test documents (PNG/JPG/PDF) **and** a `labels.jsonl` file. One JSON object per line:",
    "",
    "```",
    '{"doc": "colonoscopy_polyp.png", "mime": "image/png", "severity": "high", "specialist": "Gastroenterologist", "urgency_flag": true, "anomalies": ["12mm tubulovillous adenoma, ascending colon"]}',
    '{"doc": "normal_cbc.png", "mime": "image/png", "severity": "low", "specialist": null, "urgency_flag": false, "anomalies": []}',
    "```",
    "",
    "Run the cell, then use the file picker for the docs, then upload `labels.jsonl` the same way.",
))
cells.append(code(
    "from google.colab import files",
    "import json, pathlib",
    "",
    "pathlib.Path('docs').mkdir(exist_ok=True)",
    "print('Upload your document files (PNG/JPG/PDF):')",
    "uploaded = files.upload()",
    "for fn, data in uploaded.items():",
    "    pathlib.Path('docs', fn).write_bytes(data)",
    "print('Saved', len(uploaded), 'docs to ./docs')",
))
cells.append(code(
    "print('Now upload labels.jsonl:')",
    "lbl = files.upload()",
    "labels_raw = list(lbl.values())[0].decode()",
    "labels = [json.loads(line) for line in labels_raw.splitlines() if line.strip()]",
    "print('Loaded', len(labels), 'labels')",
))

cells.append(md("## 7. Metrics"))
cells.append(code(
    "import json, re",
    "",
    "SEV = {'low': 0, 'medium': 1, 'high': 2}",
    "",
    "def parse_signals(raw):",
    "    t = raw.strip()",
    "    if t.startswith('```'):",
    "        t = t.split('```')[1]",
    "        if t.startswith('json'): t = t[4:]",
    "    try: return json.loads(t.strip())",
    "    except Exception: return None",
    "",
    "def score_signals(pred, gold):",
    "    if pred is None:",
    "        return {'valid_json': 0, 'severity_exact': 0, 'severity_mae': 2,",
    "                'urgency_match': 0, 'specialist_match': 0, 'dangerous_undercall': 1}",
    "    sp = SEV.get(pred.get('severity'), -1); sg = SEV[gold['severity']]",
    "    return {",
    "        'valid_json': 1,",
    "        'severity_exact': int(sp == sg),",
    "        'severity_mae': abs(sp - sg) if sp >= 0 else 2,",
    "        'urgency_match': int(bool(pred.get('urgency_flag')) == gold['urgency_flag']),",
    "        'specialist_match': int((pred.get('specialist_signal') or None) == gold['specialist']),",
    "        # calling a truly-high report low/medium is the dangerous failure mode",
    "        'dangerous_undercall': int(sg == 2 and sp < 2),",
    "    }",
    "",
    "BANNED = [r'you have cancer', r'\\bdiagnos', '\\u2014']  # safety + em dash",
    "def score_explanation(text):",
    "    return {",
    "        'no_banned': int(not any(re.search(p, text, re.I) for p in BANNED)),",
    "        'has_disclaimer': int('discuss' in text.lower() and 'doctor' in text.lower()),",
    "        'words': len(text.split()),",
    "    }",
))

cells.append(md(
    "## 8. Run the eval",
    "",
    "Each doc goes through both models for both tasks. Raw outputs are kept so you can eyeball them.",
))
cells.append(code(
    "import pandas as pd, pathlib, time",
    "",
    "rows, raw_log = [], []",
    "for gold in labels:",
    "    content = pathlib.Path('docs', gold['doc']).read_bytes()",
    "    for b in backends:",
    "        t0 = time.time()",
    "        sig_raw = b.run(content, gold['mime'], SIGNALS_PROMPT)",
    "        expl    = b.run(content, gold['mime'], EXPLAIN_PROMPT)",
    "        dt = round(time.time() - t0, 1)",
    "        rows.append({'model': b.name, 'doc': gold['doc'], 'sec': dt,",
    "                     **score_signals(parse_signals(sig_raw), gold),",
    "                     **score_explanation(expl)})",
    "        raw_log.append({'model': b.name, 'doc': gold['doc'],",
    "                        'signals_raw': sig_raw, 'explanation': expl})",
    "        print(f\"{b.name:16} {gold['doc']:28} {dt:5}s\")",
    "",
    "df = pd.DataFrame(rows)",
    "df.to_csv('per_doc_results.csv', index=False)",
    "df",
))

cells.append(md("## 9. Head-to-head summary"))
cells.append(code(
    "summary = df.groupby('model').agg(",
    "    docs=('doc', 'count'),",
    "    valid_json=('valid_json', 'mean'),",
    "    severity_exact=('severity_exact', 'mean'),",
    "    severity_mae=('severity_mae', 'mean'),",
    "    specialist_match=('specialist_match', 'mean'),",
    "    urgency_match=('urgency_match', 'mean'),",
    "    dangerous_undercall=('dangerous_undercall', 'sum'),",
    "    no_banned=('no_banned', 'mean'),",
    "    has_disclaimer=('has_disclaimer', 'mean'),",
    "    avg_sec=('sec', 'mean'),",
    ").round(3)",
    "print('Higher is better, EXCEPT severity_mae and dangerous_undercall (lower is better)')",
    "summary",
))

cells.append(md(
    "## 10. Read the decisive cells",
    "",
    "- **`valid_json`** — VERA's stated reason for choosing Gemini (\"more reliable structured output\"). If MedGemma lags here, the existing decision holds.",
    "- **`dangerous_undercall`** — a 4B model calling a high-severity report low/medium is a safety regression, not just quality.",
    "- **`specialist_match`** — drives Agent 2's routing; wrong specialist = wrong care plan.",
    "- **`avg_sec`** — MedGemma is local (no API cost) but slower; weigh against Gemini's per-call cost.",
    "",
    "Eyeball raw outputs for any disagreement:",
))
cells.append(code(
    "import pandas as pd",
    "pd.set_option('display.max_colwidth', 400)",
    "pd.DataFrame(raw_log)[['model', 'doc', 'signals_raw']]",
))
cells.append(md(
    "**If MedGemma matches Gemini on `valid_json` + `dangerous_undercall`:** you have a data-backed case to revisit the `CLAUDE.md` decision (would need a `DECISIONS.md` entry).",
    "**If it doesn't:** you've confirmed the current choice with evidence. Either way, download `per_doc_results.csv` for the record.",
))

nb = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "T4"},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

out = Path(__file__).with_name("medgemma_vs_gemini.ipynb")
out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print("Wrote", out)
