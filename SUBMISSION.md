# Ajaia Docs Submission Checklist

## Submission Assets

- [ ] Source code archive or repository link
- [ ] `README.md`
- [x] `ARCHITECTURE.md`
- [x] `AI_WORKFLOW.md`
- [ ] Live deployment URL: `<ADD_LIVE_DEPLOYMENT_URL>`
- [ ] Walkthrough video URL: `<ADD_WALKTHROUGH_VIDEO_URL>`
- [ ] Screenshots: `<ADD_SCREENSHOT_LINKS_OR_FILES>`
- [ ] Walkthrough script: `WALKTHROUGH.md`

## Demo Instructions

1. Start the application:
   ```powershell
   python -m streamlit run app.py
   ```
2. Select Youssef or Sarah from the sidebar.
3. Youssef is `youssef@example.com`.
4. Sarah is `sarah@example.com`.
5. This is demo-only user switching, not production authentication.

## Verification Checklist

- [x] 34 Pytest tests pass
- [x] Streamlit starts locally
- [x] Local HTTP endpoint returns 200
- [ ] Browser interactions manually verified for all permissions
- [ ] Rich-text formatting manually reviewed
- [ ] TXT, Markdown, and DOCX imports manually reviewed
- [ ] Screenshots captured
- [ ] Walkthrough recording completed
- [ ] Live deployment URL added, if deployment is approved

## Deployment Note

Deployment has not been implemented or verified. Do not mark the live deployment item complete until a public URL is available and the running application is tested.
