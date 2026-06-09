# Setup

## Quick Start (standalone — no M365)

```bash
cd task-manager
pip install -r requirements.txt
python task.py add          # add your first task
python task.py              # see today's priorities
```

Add a shell alias to ~/.zshrc:
```bash
alias tasks="python /Users/dev/Documents/Maven-workspace/task-manager/task.py"
```
Then: `tasks`, `tasks add`, `tasks update <id>`

---

## Microsoft 365 Setup (work machine only)

### 1. Register an Azure App
1. Go to portal.azure.com → Azure Active Directory → App registrations → New registration
2. Name it "Task Manager CLI" — Single tenant
3. Note the **Application (client) ID** and **Directory (tenant) ID**
4. Under Certificates & secrets → New client secret — note the value
5. Under API permissions → Add → Microsoft Graph → Application permissions → `Mail.Read` → Grant admin consent

### 2. Configure credentials
```bash
cp .env.example .env
```
Edit `.env`:
```
M365_CLIENT_ID=<your application id>
M365_TENANT_ID=<your tenant id>
M365_CLIENT_SECRET=<your client secret>
```

### 3. Verify
```bash
python task.py show
```
You should see `M365: connected ✓` in the footer.

---

## Pattern 3 — Resilient fallback
If M365 is unreachable, the tool uses the last cached response from `outlook_cache.json` and continues normally.
