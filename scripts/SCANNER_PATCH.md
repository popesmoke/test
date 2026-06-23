# Scanner patch (apply when `desktop-client/app.py` is writable)

`app.py` was locked in the sandbox during this update. Run:

```bash
python scripts/patch_accounts.py
```

This patch:
- Fixes Roblox account filtering (`authenticated` only bug)
- Closes browsers before Roblox cookie reads
- Expands Discord desktop app paths (Microsoft Store installs)
- Reduces Swift false positives on Proton apps
- Genericizes folder-match detail strings
