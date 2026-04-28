---
name: geelark-api
description: Interact with GeeLark Cloud Phone API for managing cloud phones, automation tasks, and social media operations. Use when asked to create cloud phones, manage phones, run automation tasks on TikTok/Instagram/Facebook/YouTube/Reddit, or interact with GeeLark services.
---

# GeeLark Cloud Phone API Skill

> ⚠️ **EXPERIMENTAL PROJECT**: This skill is designed for AI agents. It contains safety mechanisms but should NOT be used directly in production without testing.

**Configuration**: `assets/config.json` (auto-loads token and base URL)

---

## First Time Setup

1. Initialize configuration:
   ```bash
   python3 scripts/init_config.py
   ```
2. This creates `assets/config.json` with your credentials (protected by `.gitignore`).
3. All scripts automatically load credentials from this file.
4. Install Dependencies
    ```bash
    pip install uiautomator2 --break-system-packages
    ```
---

## Quick Start

### Basic Usage

#### List Cloud Phones

```python
from scripts.geelark_boot_helper import list_cloud_phones

# Token auto-loads from config
phones = list_cloud_phones()
for phone in phones:
    print(f"{phone['serialName']} - {phone['id']}")
```

#### Boot Cloud Phone and Connect

```python
from scripts.geelark_boot_helper import boot_and_connect

# Token auto-loads from config
adb_info = boot_and_connect("phone_id")
if adb_info:
    print(f"ADB: {adb_info['ip']}:{adb_info['port']}, PWD: {adb_info['pwd']}")
```

---

## Core Workflow

### Step 1: Pre-check (Balance & Cloud Phone Confirmation) ⭐⭐⭐

**Before operating cloud phones:**
1. **Check account balance** - Confirm sufficient balance
2. **Query available cloud phones** - Confirm which phone to operate

```python
from scripts.geelark_client import GeeLarkClient
from scripts.geelark_boot_helper import list_cloud_phones

# Initialize client (auto-loads config)
client = GeeLarkClient(task_name="my_task", phone_id="batch")

# Check balance
wallet = client.wallet()
balance = wallet['data']['balance']
gift_money = wallet['data'].get('giftMoney', 0)

if balance <= 0 and gift_money <= 0:
    print("❌ Insufficient balance! Please recharge.")
    exit(1)

# List phones
phones = list_cloud_phones()
for phone in phones:
    print(f"  {phone['serialName']} (ID: {phone['id']})")
```

### Step 2: Create Cloud Phone

```python
# Create single phone
response = client.call("/open/v1/phone/addNew", {
    "mobileType": "Android 13",
    "data": [{"profileName": "MyPhone"}]
})

# Create multiple phones (requires Pro plan)
response = client.call("/open/v1/phone/addNew", {
    "mobileType": "Android 13",
    "data": [
        {"profileName": "Phone1"},
        {"profileName": "Phone2"}
    ]
})
```

### Step 3: Boot and Enable ADB

```python
from scripts.geelark_boot_helper import boot_and_connect

# This function handles:
# - Balance check
# - Cloud phone status check
# - Start cloud phone (if stopped)
# - Enable ADB (if disabled)
# - Return ADB connection info
# Token auto-loads from config

adb_info = boot_and_connect("phone_id")
```

### Step 4: Install Application ⭐⭐⭐

**Critical**: Must use `appVersionId`, NOT `appName`

```python
# Step 1: Find app and get appVersionId
response = client.call("/open/v1/app/installable/list", {
    "envId": "phone_id",
    "name": "TikTok",
    "page": 1,
    "pageSize": 20
})

app_version_id = response['data']['items'][0]['appVersionInfoList'][0]['id']

# Step 2: Install using appVersionId
response = client.call("/open/v1/app/install", {
    "envId": "phone_id",
    "appVersionId": app_version_id
})
```

### Step 5: Manage Session with PhoneManager

**Recommended**: Use `PhoneManager` for session tracking and auto-close.

```python
from scripts.phone_manager import PhoneManager

# Method 1: Context manager (recommended)
with PhoneManager(timeout_minutes=5) as manager:
    manager.start_monitor()
    
    # Connect using phone_id (required)
    d = manager.connect_device("phone_id_123", ip, port, pwd, name="Android15")
    
    # Perform operations
    d(text="Submit").click()
    manager.record_activity("phone_id_123")

# Automatically stops all phones and saves logs on exit

# Method 2: Manual control
manager = PhoneManager(timeout_minutes=5)
manager.start_monitor()
# ... operations ...
manager.stop_all()
manager.client.save_log()
```

---


## Safety Mechanisms

| Mechanism | Description |
|-----------|-------------|
| **Balance Check** | Auto-checks balance before starting cloud phones |
| **Energy Saving** | Auto enables `energySavingMode=1` to reduce costs |
| **Double Confirm** | Delete requires ID + 'YES' confirmation |
| **Auto-Close** | `PhoneManager` auto-closes idle devices |
| **Endpoint Whitelist** | Only documented endpoints can be called |
| **Logging** | All operations logged to `logs/cloudphone/` |

---

## Cloudphone Operations

### Dependencies

```bash
pip install uiautomator2 --break-system-packages
```

### Agent Workflow ⭐⭐⭐

Since this skill is designed for AI agents that need to recognize the current screen state, the recommended workflow is:

1. **Identify UI Structure**: Use `uiautomator2` to dump the current page hierarchy (`dump_hierarchy()`), enabling the agent to understand the screen layout.
   - Parse the XML hierarchy to locate target elements by `text`, `resource-id`, `content-desc`, or `class`
   - Extract element coordinates (`bounds`) for verification or fallback operations
   - If `dump_hierarchy()` fails or returns empty, proceed to Step 3 immediately

2. **Prioritize uiautomator2 Operations**: If elements can be identified and interacted with via the UI hierarchy, use `uiautomator2` for clicks, inputs, and swipes.
   - **Click**: `d(text="Button").click()` or `d(resourceId="com.example:id/btn").click()`
   - **Input**: `d(text="Username").set_text("hello")`
   - **Swipe**: `d.swipe(x1, y1, x2, y2)` or `d.swipe_ext("up")`
   - **Wait**: `d(text="Expected Text").wait(timeout=10)` before interaction
   - Always verify the element is visible and enabled before interaction

3. **Verify & Retry**: After each operation, execute `dump_hierarchy()` again to confirm the previous action succeeded.
   - Check if the expected UI state changed (e.g., new screen appeared, text updated, dialog dismissed)
   - If verification fails, retry the operation up to 3 times with brief delays (2-3 seconds)
   - If all retries fail, log the error and proceed to Step 4

4. **Fallback to ADB Screenshots**: If elements cannot be recognized or operated via `uiautomator2`, use ADB screenshots to visually confirm the state and perform coordinate-based operations.
   - Capture screenshot: `d.screenshot("/tmp/screen.png")` or via ADB `screencap`
   - Use computer vision or LLM to analyze the screenshot and identify target coordinates
   - Click coordinates: `d.click(x, y)` or `subprocess.run(['adb', '-s', 'device', 'shell', 'input', 'tap', x, y])`
   - Swipe coordinates: `subprocess.run(['adb', '-s', 'device', 'shell', 'input', 'swipe', x1, y1, x2, y2])`
   - **Note**: Coordinate-based operations are less reliable; always prefer uiautomator2 when possible

### Basic Operations

```python
import uiautomator2 as u2
import subprocess

# Connect
d = u2.connect(f"{adb_info['ip']}:{adb_info['port']}")

# Authenticate (MUST DO IMMEDIATELY)
subprocess.run(['adb', '-s', f"{adb_info['ip']}:{adb_info['port']}",
                'shell', 'glogin', adb_info['pwd']], capture_output=True)

# Get UI hierarchy (Step 1: Identify)
xml = d.dump_hierarchy()

# Find and click element (Step 2: Prioritize uiautomator2)
d(text="Submit").click()

# Input text
d(text="Username").set_text("hello world")

# Screenshot (Step 3: Fallback)
d.screenshot("/tmp/screen.png")

# Or using ADB
subprocess.run(['adb', '-s', f"{adb_info['ip']}:{adb_info['port']}",
                'shell', 'screencap', '-p', '/sdcard/screen.png'])
subprocess.run(['adb', '-s', f"{adb_info['ip']}:{adb_info['port']}",
                'pull', '/sdcard/screen.png', '/tmp/screen.png'])
```

**See**: `references/cloudphone_operations.md` for complete guide.

---

## RPA Tasks

GeeLark provides built-in RPA tasks for 9 platforms:

- TikTok (login, follow, like, comment, edit, delete)
- Instagram (login, publish reels, warmup)
- Facebook (login, publish, auto-comment, active account)
- YouTube (publish short, publish video, active account)
- Reddit (publish image/video, warmup)
- Threads (publish image/video)
- Pinterest (publish image/video)
- X/Twitter (publish)
- Google (login, app download)

**See**: `references/api_reference.md` for complete endpoint list and parameters

---

## Reference Documentation

| Document | Description | When to Read |
|----------|-------------|--------------|
| `references/api_reference.md` | Complete API endpoint list | Need to look up endpoints/parameters |
| `references/error_codes.md` | All error codes and solutions | API call fails |
| `references/best_practices.md` | Safety and performance tips | Planning operations |
| `references/cloudphone_operations.md` | ADB/uiautomator2 guide | Working with device UI |
| `references/auto_close.md` | Auto-close mechanism | Managing idle devices |

---

## Common Error Codes

| Code | Description | Action |
|------|-------------|--------|
| `0` | Success | ✅ |
| `41001` | Balance not enough | Recharge account |
| `42001` | Cloud phone does not exist | Check phone ID |
| `42002` | Cloud phone is not running | Start phone first |

**See**: `references/api_reference.md` for complete list.

---

## 🤖 AI Agent Execution Rules

**Critical Directives:**

1. **Pre-flight Check**: Always verify account balance (`wallet()`) before initiating any cloud phone operations.
2. **Safety Enforcement**: Direct deletion is blocked. You **must** use `scripts/delete_helper.py` for double-confirmation.
3. **Identifiers**: Use `phone_id` (UUID) for all API calls, not `serialName`.
4. **RPA Parameter Quirks**:
   - **YouTube**: `video` parameter is a **string**.
   - **Others (IG/FB/Reddit/etc.)**: `video`/`images` parameters are **arrays**.
   - **Instagram**: Field is `Image` (capital I), not `images`.
   - **Facebook**: Login field is `Email`, not `account`.
5. **Lifecycle Management**: You must **stop** a running phone before deleting it (otherwise error 43009).
6. **Auto-Configuration**: Credentials load automatically from `assets/config.json`. Do not pass `token` manually.
7. **Logging**: Always save operation logs to `logs/cloudphone/` upon task completion.

---

**Official Documentation**: https://github.com/GeeLark/geelark-openapi
