# Hackathon Submission Guide

Step-by-step guide to submit this project to the Hugging Face MCP Hackathon.

---

## Step 1: Create GitHub Repository

### 1.1 Initialize Git (if not already done)

```bash
cd /Users/seunghoonpaik/hoonproj/localvault/playland/mcp-hackathon

# Initialize git if needed
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Drive-Time Plotter MCP for HF MCP Hackathon"
```

### 1.2 Create GitHub Repository

1. Go to https://github.com/new
2. **Repository name:** `drive-time-plotter-mcp` (or your preferred name)
3. **Description:** "Lightning-fast MCP server for traffic analysis - Built for Hugging Face MCP Hackathon"
4. **Visibility:** Public
5. **DO NOT** initialize with README (you already have one)
6. Click "Create repository"

### 1.3 Push to GitHub

GitHub will show you commands. Use these:

```bash
# Add remote
git remote add origin https://github.com/YOUR_USERNAME/drive-time-plotter-mcp.git

# Push
git branch -M main
git push -u origin main
```

### 1.4 Update README Links

After pushing, update the TODO links in README.md:

```markdown
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/YOUR_USERNAME/drive-time-plotter-mcp)
```

---

## Step 2: Create Hugging Face Space

### 2.1 Create Account (if needed)

1. Go to https://huggingface.co/join
2. Sign up with email or GitHub

### 2.2 Create New Space

1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Fill in:
   - **Owner:** Your username
   - **Space name:** `drive-time-plotter-mcp`
   - **License:** MIT
   - **Select SDK:** **Gradio**
   - **Space hardware:** CPU basic (free tier)
   - **Visibility:** Public
4. Click **"Create Space"**

### 2.3 Link GitHub Repository to Space

**Option A: Git Clone Method** (Recommended)

```bash
# Clone the Hugging Face Space repo
git clone https://huggingface.co/spaces/YOUR_USERNAME/drive-time-plotter-mcp hf-space

# Copy your files
cd hf-space
cp -r ../mcp-hackathon/* .

# Commit and push
git add .
git commit -m "Add Drive-Time Plotter MCP"
git push
```

**Option B: Direct Upload via Web UI**

1. In your Space, click "Files and versions"
2. Click "Add file" → "Upload files"
3. Upload all files from your project
4. Commit changes

### 2.4 Add Required Files for Hugging Face Space

The Space needs these special files:

**Create `requirements.txt` (you already have this)**
Already exists with all dependencies.

**Create `app.py`** (for Gradio - we'll create this in next step)

---

## Step 3: Create Demo Video

### 3.1 Video Content (3-5 minutes)

**Outline:**

1. **Introduction (30 sec)**
   - "Hi, I'm [name], and I built Drive-Time Plotter MCP"
   - "Solves the problem of not knowing when to leave for commute"

2. **Quick Demo (1 min)**
   - Show `./test.sh` running
   - Point out the 4-second speed
   - Show the beautiful plot

3. **Full Analysis (1 min)**
   - Show `./test_custom.sh` with Evans Hall → SFO
   - Explain the three lines (optimistic/pessimistic/average)
   - Point out best/worst times

4. **Claude Integration (1 min)**
   - Show Claude Desktop config
   - Ask Claude "When should I drive from X to Y?"
   - Show it using your MCP tools

5. **Key Innovations (1 min)**
   - 120x speedup via parallel processing
   - Human-aware recommendations (sleep consideration)
   - Dual output (ANSI + plain text)
   - Smart retry logic

6. **Conclusion (30 sec)**
   - "Built for HF MCP Hackathon Track 1"
   - "Check out the code on GitHub"
   - "Thanks for watching!"

### 3.2 Recording Tools

**Free options:**
- **macOS:** QuickTime Player (⌘+Shift+5)
- **Screen recording:** OBS Studio (free, powerful)
- **Editing:** iMovie (macOS) or DaVinci Resolve (free)

### 3.3 Upload Video

1. Upload to YouTube:
   - Title: "Drive-Time Plotter MCP - Hugging Face MCP Hackathon"
   - Description: Include GitHub link
   - Tags: MCP, Hugging Face, AI, traffic analysis
   - Visibility: Unlisted or Public

2. Update README.md with video link:
```markdown
[![Demo Video](https://img.shields.io/badge/Demo-Video-red?logo=youtube)](https://youtube.com/watch?v=YOUR_VIDEO_ID)
```

---

## Step 4: Create Social Media Post

### 4.1 Post Template (Twitter/LinkedIn)

```
🚗 Just built Drive-Time Plotter MCP for the @huggingface MCP Hackathon!

⚡ Lightning-fast traffic analysis (4 seconds for 24 hours!)
🤖 Works with @AnthropicAI Claude Desktop
📊 Beautiful terminal visualizations
🧠 Human-aware recommendations (actually considers sleep!)

Built with:
✨ 120x speedup via parallel processing
✨ Smart retry logic with multiple rounds
✨ Dual output formats (ANSI + plain text)

🎯 Track 1: Building MCP - Consumer Category

🔗 GitHub: [link]
🎥 Demo: [link]
📝 Try it: [HF Space link]

#MCP #HuggingFace #AI #MachineLearning #OpenSource

What's your commute route? Drop it below! 👇
```

### 4.2 Post to Social Media

**Platforms:**
- Twitter: https://twitter.com/compose/tweet
- LinkedIn: https://linkedin.com/feed
- Both recommended for maximum reach

### 4.3 Save Link

After posting, copy the link and update README.md:
```markdown
[![Social Post](https://img.shields.io/badge/Social-Post-blue?logo=twitter)](https://twitter.com/YOUR_USERNAME/status/YOUR_POST_ID)
```

---

## Step 5: Submit to Hackathon

### 5.1 Join MCP-1st-Birthday Organization

1. Go to https://huggingface.co/MCP-1st-Birthday
2. Check for submission instructions (usually a form or specific repository)

### 5.2 Submit Your Space

Follow the hackathon-specific submission process:
- Usually involves adding your Space to the organization
- Or submitting via a form with links

**Information you'll need:**
- ✅ Hugging Face Space URL: `https://huggingface.co/spaces/YOUR_USERNAME/drive-time-plotter-mcp`
- ✅ GitHub Repository: `https://github.com/YOUR_USERNAME/drive-time-plotter-mcp`
- ✅ Demo Video: YouTube link
- ✅ Social Media Post: Twitter/LinkedIn link
- ✅ Track: Track 1 - Building MCP
- ✅ Category: Consumer MCP Servers

---

## Step 6: Update README with All Links

After completing all steps, update your README.md:

```markdown
[![Demo Video](https://img.shields.io/badge/Demo-Video-red?logo=youtube)](https://youtube.com/watch?v=YOUR_VIDEO_ID)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/YOUR_USERNAME/drive-time-plotter-mcp)
[![Social Post](https://img.shields.io/badge/Social-Post-blue?logo=twitter)](https://twitter.com/YOUR_USERNAME/status/POST_ID)
[![Hugging Face](https://img.shields.io/badge/🤗-Space-yellow)](https://huggingface.co/spaces/YOUR_USERNAME/drive-time-plotter-mcp)
```

Then commit and push:
```bash
git add README.md
git commit -m "Add hackathon submission links"
git push
```

---

## Checklist

### Before Submission

- [ ] GitHub repository created and pushed
- [ ] README.md has hackathon tags (YAML frontmatter)
- [ ] Hugging Face Space created
- [ ] Demo video recorded and uploaded
- [ ] Social media post published
- [ ] All links added to README.md
- [ ] Tested that all links work

### Track 1 Specific

- [ ] MCP server works with Claude Desktop
- [ ] CLI tools work standalone
- [ ] Documentation is comprehensive
- [ ] Code is clean and commented
- [ ] LICENSE file (MIT) is present

---

## Quick Command Reference

```bash
# Create GitHub repo and push
git init
git add .
git commit -m "Initial commit for HF MCP Hackathon"
git remote add origin https://github.com/YOUR_USERNAME/drive-time-plotter-mcp.git
git push -u origin main

# Clone HF Space and add files
git clone https://huggingface.co/spaces/YOUR_USERNAME/drive-time-plotter-mcp hf-space
cd hf-space
cp -r ../mcp-hackathon/* .
git add .
git commit -m "Add MCP server for hackathon"
git push

# Update links and push
git add README.md
git commit -m "Update submission links"
git push
```

---

## Need Help?

**Common Issues:**

1. **"Permission denied" when pushing to GitHub**
   - Use GitHub CLI: `gh auth login`
   - Or use Personal Access Token instead of password

2. **"Space fails to build"**
   - Check requirements.txt has all dependencies
   - Ensure Python version compatibility

3. **"Video is too large"**
   - Compress with HandBrake (free)
   - Keep under 5 minutes
   - 720p is sufficient quality

---

## Timeline Suggestion

**Day 1 (Today):**
- [ ] Create GitHub repo (15 min)
- [ ] Push code (5 min)
- [ ] Create HF Space (10 min)

**Day 2:**
- [ ] Record demo video (1-2 hours)
- [ ] Edit video (30 min)
- [ ] Upload to YouTube (15 min)

**Day 3:**
- [ ] Create social media post (15 min)
- [ ] Update README links (10 min)
- [ ] Submit to hackathon (15 min)

**Total time: ~4-5 hours spread over 3 days**

---

Good luck! 🚀
