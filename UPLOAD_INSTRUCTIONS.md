# How to Upload This Project to GitHub

You have two paths. Pick one and stop deliberating.

---

## Path A: Web Upload (no terminal needed) — 10 minutes

**Use this if:** You want it done today and you don't already have Git configured.

### Step 1 — Create the repo
1. Go to https://github.com/new
2. **Repository name:** `gmail-jobbot-mvp` (or `serverless-gmail-triage` if you want something punchier)
3. **Description:** `Serverless Python bot on Google Cloud Run that triages job-search emails via the Gmail API.`
4. **Visibility:** Public (the whole point is recruiters can find it)
5. **Do NOT** check "Add a README", "Add .gitignore", or "Add a license" — you already have those
6. Click **Create repository**

### Step 2 — Upload files
1. On the empty repo page, click **"uploading an existing file"** (small link near the top)
2. Drag in these 6 files from the folder I created:
   - `main.py`
   - `requirements.txt`
   - `Dockerfile`
   - `.gitignore`
   - `README.md`
   - `LICENSE`
3. Commit message: `Initial commit: Serverless Gmail JobBot`
4. Click **Commit changes**

### Step 3 — Add the PDF guide
1. Click **Add file → Create new file**
2. In the filename box, type: `docs/.gitkeep` and commit (this creates the `docs` folder)
3. Click **Add file → Upload files**
4. Navigate into the `docs` folder, drag in `Gmail_JobBot_Guide.pdf`
5. Commit

### Step 4 — Add the topics (this is what makes it searchable)
1. On the repo home page, click the ⚙️ gear icon next to "About" (top right)
2. In the **Topics** field, paste:
   ```
   python google-cloud-platform cloud-run gmail-api serverless automation docker oauth2 secret-manager cloud-scheduler devops
   ```
3. Save

### Step 5 — Update the demo links in the README
1. Upload your MP3 to Google Drive (right-click → Share → "Anyone with the link")
2. Upload your MP4 to YouTube as **Unlisted** (not Private — recruiters need to view it without a Google account)
3. In the README on GitHub, click the pencil icon to edit
4. Replace `[INSERT_YOUTUBE_OR_DRIVE_LINK]` and `[INSERT_AUDIO_LINK]` with the real URLs
5. Commit

**Done.** Send the link.

---

## Path B: Command Line (Cloud Shell or local terminal)

**Use this if:** You already have your project in Cloud Shell from the original deployment.

```bash
# In your gmail-jobbot project folder
cd ~/gmail-jobbot

# Make sure your local files match the ones I created (same names, same content)

git init
git add .
git commit -m "Initial commit: Serverless Gmail JobBot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/gmail-jobbot-mvp.git
git push -u origin main
```

If GitHub asks for authentication, use a **Personal Access Token**, not your password:
1. https://github.com/settings/tokens → Generate new token (classic)
2. Scope: `repo`
3. Use the token as your password when `git push` prompts you

---

## What about the audio and video files?

**Don't put them in the repo.** Reasons:
- GitHub flags files >50MB and blocks files >100MB
- The repo download size affects clone times for anyone reviewing your code
- GitHub's video player is unreliable; YouTube embed is universal

**Do this instead:**
- **MP3:** Upload to Google Drive, set to "Anyone with the link can view", paste the link in README
- **MP4:** Upload to YouTube as Unlisted, paste the link in README

The PDF setup guide is small enough — that one belongs in `docs/` inside the repo.

---

## After upload — the actual high-leverage moves

The repo existing isn't the win. Distribution is.

1. **LinkedIn post.** Same day as the push. Format:
   - Hook: the problem (50 emails/day, 30 min wasted)
   - Solution: 1-sentence architecture summary
   - Link: GitHub URL
   - 3 hashtags max
2. **Pin the repo** on your GitHub profile (profile page → Customize your pins)
3. **Add to your resume** under Projects, with the GitHub URL inline
4. **Add to LinkedIn Featured section** with a screenshot of the architecture diagram
