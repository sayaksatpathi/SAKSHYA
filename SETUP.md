# One-time setup — GitHub push → Hugging Face goes live automatically

Do this once. After that, every `git push` to `main` auto-deploys the Space.

## 1. Create the GitHub repo
- Go to https://github.com/new
- Repository name: **SAKSHYA**  (exact — the deck links point here)
- Visibility: **Public**
- Click **Create repository**

## 2. Get a Hugging Face token (Write access)
- Go to https://huggingface.co/settings/tokens
- **New token** → Type/Role: **Write** → Create → **copy** it.

## 3. Add the token to GitHub as a secret
- In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**
- Name: **HF_TOKEN**
- Value: paste the token → **Add secret**

## 4. Push these files
From this folder (`SAKSHYA-starter`):

```bash
git init
git add .
git commit -m "SAKSHYA: initial + HF auto-deploy"
git branch -M main
git remote add origin https://github.com/sayaksatpathi/SAKSHYA.git
git push -u origin main
```

## Done
The **Deploy to Hugging Face Space** workflow runs on every push and mirrors the
repo to https://huggingface.co/spaces/Sayak-Satpathi/sakshya-demo, which then
rebuilds and goes live. Check progress under the repo's **Actions** tab.

### Notes
- If your Space needs a different runtime, edit the `sdk:` line in **README.md**
  (`static` → `gradio` / `streamlit`) and add the app files, then push.
- If your GitHub username is **not** `sayaksatpathi`, change the `origin` URL in
  step 4 — and tell me so I re-point the deck's GitHub button.
- The Space owner (`Sayak-Satpathi`) and Space name (`sakshya-demo`) are already
  wired into `.github/workflows/deploy-to-hf.yml`.
