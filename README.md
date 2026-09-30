---
title: SAKSHYA
emoji: 🛡️
colorFrom: indigo
colorTo: green
sdk: static
pinned: false
---

# SAKSHYA — Court-Ready Surveillance Evidence Platform

**Smart India Hackathon 2026 · Problem Statement SIH26150 · Team Aroeminds**

Standardized, offline, vendor-agnostic forensic platform for multi-vendor DVR/NVR
surveillance evidence — acquisition, deleted-clip recovery, tamper-proof SHA-256
hash-ledger, BSA §63(4) court certificates, and AI triage of recovered footage.

- **Live demo:** https://huggingface.co/spaces/Sayak-Satpathi/sakshya-demo

> This is the placeholder. Replace `index.html` (or add your app) and push — the
> GitHub Action redeploys the Hugging Face Space automatically.

## How auto-deploy works
`.github/workflows/deploy-to-hf.yml` mirrors this repo to the Hugging Face Space
on every push to `main`. The Space's SDK is set by the `sdk:` line in this file's
header above:
- **Static site** → keep `sdk: static` and serve `index.html`.
- **Gradio app** → set `sdk: gradio`, add `app.py` + `requirements.txt`.
- **Streamlit app** → set `sdk: streamlit`, add `streamlit_app.py` + `requirements.txt`.
