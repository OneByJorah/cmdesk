from playwright.sync_api import sync_playwright
import time
import os

SCREENSHOT_DIR = "/home/j1coder/github-repos/CommandDesk/docs/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Dashboard mockup
DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CommandDesk - AI Helpdesk Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #e2e8f0; height: 100vh; display: flex; }
        .sidebar { width: 260px; background: #1e293b; padding: 20px; border-right: 1px solid #334155; }
        .logo { font-size: 20px; font-weight: 700; color: #3b82f6; margin-bottom: 32px; }
        .nav-item { padding: 12px 16px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 12px; margin-bottom: 4px; font-size: 14px; }
        .nav-item:hover { background: #334155; }
        .nav-item.active { background: #3b82f6; color: white; }
        .main { flex: 1; padding: 32px; overflow-y: auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
        .header h1 { font-size: 28px; font-weight: 700; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 32px; }
        .stat-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; }
        .stat-label { font-size: 13px; color: #94a3b8; margin-bottom: 8px; }
        .stat-value { font-size: 32px; font-weight: 700; }
        .stat-value.blue { color: #3b82f6; }
        .stat-value.green { color: #10b981; }
        .stat-value.yellow { color: #f59e0b; }
        .stat-value.red { color: #ef4444; }
        .chart-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; }
        .chart-title { font-size: 16px; font-weight: 600; margin-bottom: 20px; }
        .bar-chart { display: flex; align-items: flex-end; gap: 12px; height: 160px; padding-top: 20px; }
        .bar { flex: 1; background: linear-gradient(to top, #3b82f6, #60a5fa); border-radius: 6px 6px 0 0; position: relative; }
        .bar-label { position: absolute; bottom: -24px; left: 50%; transform: translateX(-50%); font-size: 11px; color: #94a3b8; }
        .ticket-list { list-style: none; }
        .ticket-item { padding: 16px; border: 1px solid #334155; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        .ticket-title { font-weight: 600; }
        .ticket-meta { font-size: 12px; color: #94a3b8; margin-top: 4px; }
        .ticket-status { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .ticket-status.open { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
        .ticket-status.pending { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .ticket-status.resolved { background: rgba(16, 185, 129, 0.2); color: #10b981; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">🎧 CommandDesk</div>
        <div class="nav-item active">📊 Dashboard</div>
        <div class="nav-item">🎫 Tickets</div>
        <div class="nav-item">🤖 AI Assistant</div>
        <div class="nav-item">👥 Customers</div>
        <div class="nav-item">📈 Analytics</div>
        <div class="nav-item">⚙️ Settings</div>
    </div>
    <div class="main">
        <div class="header">
            <h1>Helpdesk Dashboard</h1>
            <div style="display:flex;gap:12px;">
                <div style="background:#334155;padding:8px 16px;border-radius:8px;font-size:14px;">🔔 3</div>
                <div style="background:#3b82f6;padding:8px 16px;border-radius:8px;font-size:14px;color:white;">+ New Ticket</div>
            </div>
        </div>
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Open Tickets</div>
                <div class="stat-value blue">47</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Resolved Today</div>
                <div class="stat-value green">128</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Response Time</div>
                <div class="stat-value yellow">4.2m</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Escalated</div>
                <div class="stat-value red">5</div>
            </div>
        </div>
        <div class="chart-card">
            <div class="chart-title">Tickets by Category</div>
            <div class="bar-chart">
                <div class="bar" style="height: 80%"><div class="bar-label">Billing</div></div>
                <div class="bar" style="height: 95%"><div class="bar-label">Technical</div></div>
                <div class="bar" style="height: 60%"><div class="bar-label">Account</div></div>
                <div class="bar" style="height: 40%"><div class="bar-label">Feature</div></div>
                <div class="bar" style="height: 70%"><div class="bar-label">Bug</div></div>
                <div class="bar" style="height: 30%"><div class="bar-label">Other</div></div>
            </div>
        </div>
        <div class="chart-card" style="margin-top:20px;">
            <div class="chart-title">Recent Tickets</div>
            <ul class="ticket-list">
                <li class="ticket-item">
                    <div><div class="ticket-title">Login issue after password reset</div><div class="ticket-meta">Customer: John D. • 2m ago</div></div>
                    <div class="ticket-status open">Open</div>
                </li>
                <li class="ticket-item">
                    <div><div class="ticket-title">Billing discrepancy on invoice #4521</div><div class="ticket-meta">Customer: Sarah M. • 15m ago</div></div>
                    <div class="ticket-status pending">Pending</div>
                </li>
                <li class="ticket-item">
                    <div><div class="ticket-title">API rate limit exceeded</div><div class="ticket-meta">Customer: TechCorp • 1h ago</div></div>
                    <div class="ticket-status resolved">Resolved</div>
                </li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

# AI Assistant mockup
AI_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CommandDesk - AI Assistant</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #e2e8f0; height: 100vh; display: flex; }
        .sidebar { width: 260px; background: #1e293b; padding: 20px; border-right: 1px solid #334155; }
        .logo { font-size: 20px; font-weight: 700; color: #3b82f6; margin-bottom: 32px; }
        .nav-item { padding: 12px 16px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 12px; margin-bottom: 4px; font-size: 14px; }
        .nav-item:hover { background: #334155; }
        .nav-item.active { background: #3b82f6; color: white; }
        .main { flex: 1; display: flex; flex-direction: column; }
        .chat-header { padding: 20px 32px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }
        .chat-header h2 { font-size: 20px; font-weight: 600; }
        .chat-messages { flex: 1; padding: 32px; overflow-y: auto; }
        .message { margin-bottom: 24px; display: flex; gap: 12px; }
        .message-avatar { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
        .message-avatar.ai { background: #3b82f6; }
        .message-avatar.user { background: #334155; }
        .message-content { flex: 1; }
        .message-name { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
        .message-text { background: #1e293b; padding: 16px; border-radius: 12px; font-size: 14px; line-height: 1.6; }
        .message-text.ai { border: 1px solid #3b82f6; }
        .message-actions { display: flex; gap: 8px; margin-top: 8px; }
        .action-btn { background: #334155; border: none; color: #94a3b8; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; }
        .action-btn:hover { background: #475569; color: white; }
        .chat-input { padding: 20px 32px; border-top: 1px solid #334155; display: flex; gap: 12px; }
        .chat-input input { flex: 1; background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px 16px; color: white; font-size: 14px; }
        .chat-input input:focus { outline: none; border-color: #3b82f6; }
        .chat-input button { background: #3b82f6; border: none; color: white; padding: 14px 24px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
        .suggested { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; }
        .suggested-chip { background: #334155; padding: 8px 16px; border-radius: 20px; font-size: 13px; cursor: pointer; }
        .suggested-chip:hover { background: #475569; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">🎧 CommandDesk</div>
        <div class="nav-item">📊 Dashboard</div>
        <div class="nav-item">🎫 Tickets</div>
        <div class="nav-item active">🤖 AI Assistant</div>
        <div class="nav-item">👥 Customers</div>
        <div class="nav-item">📈 Analytics</div>
        <div class="nav-item">⚙️ Settings</div>
    </div>
    <div class="main">
        <div class="chat-header">
            <h2>🤖 AI Support Assistant</h2>
            <div style="display:flex;gap:12px;align-items:center;">
                <span style="color:#10b981;font-size:13px;">● Online</span>
                <span style="color:#94a3b8;font-size:13px;">1,847 conversations today</span>
            </div>
        </div>
        <div class="chat-messages">
            <div class="message">
                <div class="message-avatar user">👤</div>
                <div class="message-content">
                    <div class="message-name">John D.</div>
                    <div class="message-text">I'm having trouble logging in after resetting my password. I get an "Invalid credentials" error.</div>
                </div>
            </div>
            <div class="message">
                <div class="message-avatar ai">🤖</div>
                <div class="message-content">
                    <div class="message-name">AI Assistant</div>
                    <div class="message-text ai">I can help with that! Here are a few things to check:<br><br>1. Make sure you're using the new password (not the old one)<br>2. Check that Caps Lock is off<br>3. Try clearing your browser cache<br>4. Verify your account email matches<br><br>Would you like me to send a fresh reset link to your email?</div>
                    <div class="message-actions">
                        <button class="action-btn">👍 Helpful</button>
                        <button class="action-btn">📋 Copy</button>
                        <button class="action-btn">🎫 Create Ticket</button>
                    </div>
                </div>
            </div>
            <div class="message">
                <div class="message-avatar user">👤</div>
                <div class="message-content">
                    <div class="message-name">John D.</div>
                    <div class="message-text">Yes, please send a fresh reset link!</div>
                </div>
            </div>
            <div class="message">
                <div class="message-avatar ai">🤖</div>
                <div class="message-content">
                    <div class="message-name">AI Assistant</div>
                    <div class="message-text ai">Done! I've sent a fresh password reset link to john@example.com. The link will expire in 24 hours.<br><br>✅ Reset email sent successfully<br>📧 Recipient: john@example.com<br>⏰ Expires: July 19, 2026</div>
                </div>
            </div>
        </div>
        <div class="suggested">
            <div class="suggested-chip">🎫 Create ticket</div>
            <div class="suggested-chip">📊 Check status</div>
            <div class="suggested-chip">📞 Escalate</div>
        </div>
        <div class="chat-input">
            <input type="text" placeholder="Type your message..." value="Thank you! It worked.">
            <button>Send</button>
        </div>
    </div>
</body>
</html>
"""

# Costs/Costs mockup
COSTS_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CommandDesk - Cost Analytics</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #e2e8f0; height: 100vh; display: flex; }
        .sidebar { width: 260px; background: #1e293b; padding: 20px; border-right: 1px solid #334155; }
        .logo { font-size: 20px; font-weight: 700; color: #3b82f6; margin-bottom: 32px; }
        .nav-item { padding: 12px 16px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 12px; margin-bottom: 4px; font-size: 14px; }
        .nav-item:hover { background: #334155; }
        .nav-item.active { background: #3b82f6; color: white; }
        .main { flex: 1; padding: 32px; overflow-y: auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
        .header h1 { font-size: 28px; font-weight: 700; }
        .time-filter { display: flex; gap: 8px; }
        .time-btn { background: #334155; border: none; color: #94a3b8; padding: 8px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; }
        .time-btn.active { background: #3b82f6; color: white; }
        .cost-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 32px; }
        .cost-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; }
        .cost-label { font-size: 13px; color: #94a3b8; margin-bottom: 8px; }
        .cost-value { font-size: 36px; font-weight: 700; }
        .cost-change { font-size: 13px; margin-top: 8px; }
        .cost-change.positive { color: #10b981; }
        .cost-change.negative { color: #ef4444; }
        .chart-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; }
        .chart-title { font-size: 16px; font-weight: 600; margin-bottom: 20px; }
        .cost-bar-chart { display: flex; align-items: flex-end; gap: 16px; height: 200px; padding-top: 20px; }
        .cost-bar-group { flex: 1; display: flex; flex-direction: column; align-items: center; }
        .cost-bar { width: 100%; border-radius: 6px 6px 0 0; position: relative; }
        .cost-bar.ai { background: linear-gradient(to top, #3b82f6, #60a5fa); }
        .cost-bar.human { background: linear-gradient(to top, #8b5cf6, #a78bfa); }
        .cost-bar-label { font-size: 12px; color: #94a3b8; margin-top: 8px; }
        .breakdown { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
        .breakdown-item { padding: 16px; background: #0f172a; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        .breakdown-name { font-size: 14px; }
        .breakdown-value { font-weight: 600; }
        .breakdown-bar { width: 60px; height: 8px; background: #334155; border-radius: 4px; overflow: hidden; }
        .breakdown-fill { height: 100%; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">🎧 CommandDesk</div>
        <div class="nav-item">📊 Dashboard</div>
        <div class="nav-item">🎫 Tickets</div>
        <div class="nav-item">🤖 AI Assistant</div>
        <div class="nav-item">👥 Customers</div>
        <div class="nav-item active">📈 Analytics</div>
        <div class="nav-item">⚙️ Settings</div>
    </div>
    <div class="main">
        <div class="header">
            <h1>Cost Analytics</h1>
            <div class="time-filter">
                <div class="time-btn">7D</div>
                <div class="time-btn active">30D</div>
                <div class="time-btn">90D</div>
                <div class="time-btn">1Y</div>
            </div>
        </div>
        <div class="cost-grid">
            <div class="cost-card">
                <div class="cost-label">Total Cost (30D)</div>
                <div class="cost-value" style="color:#3b82f6;">$2,847</div>
                <div class="cost-change negative">↓ 12% from last month</div>
            </div>
            <div class="cost-card">
                <div class="cost-label">AI Resolution Cost</div>
                <div class="cost-value" style="color:#10b981;">$1,234</div>
                <div class="cost-change positive">↓ 23% savings vs human</div>
            </div>
            <div class="cost-card">
                <div class="cost-label">Cost per Ticket</div>
                <div class="cost-value" style="color:#f59e0b;">$3.42</div>
                <div class="cost-change positive">↓ 18% improvement</div>
            </div>
        </div>
        <div class="chart-card">
            <div class="chart-title">Monthly Cost Breakdown: AI vs Human</div>
            <div class="cost-bar-chart">
                <div class="cost-bar-group">
                    <div class="cost-bar ai" style="height: 60%; width: 28px; display: inline-block;"></div>
                    <div class="cost-bar human" style="height: 90%; width: 28px; display: inline-block; margin-left: 4px;"></div>
                    <div class="cost-bar-label">Jan</div>
                </div>
                <div class="cost-bar-group">
                    <div class="cost-bar ai" style="height: 55%; width: 28px; display: inline-block;"></div>
                    <div class="cost-bar human" style="height: 85%; width: 28px; display: inline-block; margin-left: 4px;"></div>
                    <div class="cost-bar-label">Feb</div>
                </div>
                <div class="cost-bar-group">
                    <div class="cost-bar ai" style="height: 50%; width: 28px; display: inline-block;"></div>
                    <div class="cost-bar human" style="height: 75%; width: 28px; display: inline-block; margin-left: 4px;"></div>
                    <div class="cost-bar-label">Mar</div>
                </div>
                <div class="cost-bar-group">
                    <div class="cost-bar ai" style="height: 45%; width: 28px; display: inline-block;"></div>
                    <div class="cost-bar human" style="height: 70%; width: 28px; display: inline-block; margin-left: 4px;"></div>
                    <div class="cost-bar-label">Apr</div>
                </div>
                <div class="cost-bar-group">
                    <div class="cost-bar ai" style="height: 40%; width: 28px; display: inline-block;"></div>
                    <div class="cost-bar human" style="height: 65%; width: 28px; display: inline-block; margin-left: 4px;"></div>
                    <div class="cost-bar-label">May</div>
                </div>
                <div class="cost-bar-group">
                    <div class="cost-bar ai" style="height: 35%; width: 28px; display: inline-block;"></div>
                    <div class="cost-bar human" style="height: 60%; width: 28px; display: inline-block; margin-left: 4px;"></div>
                    <div class="cost-bar-label">Jun</div>
                </div>
            </div>
            <div style="display:flex;gap:20px;margin-top:40px;justify-content:center;">
                <div style="display:flex;align-items:center;gap:8px;"><div style="width:12px;height:12px;background:#3b82f6;border-radius:3px;"></div><span style="font-size:13px;color:#94a3b8;">AI Resolution</span></div>
                <div style="display:flex;align-items:center;gap:8px;"><div style="width:12px;height:12px;background:#8b5cf6;border-radius:3px;"></div><span style="font-size:13px;color:#94a3b8;">Human Agent</span></div>
            </div>
        </div>
        <div class="chart-card" style="margin-top:20px;">
            <div class="chart-title">Cost by Category</div>
            <div class="breakdown">
                <div class="breakdown-item">
                    <span class="breakdown-name">💬 Chat Support</span>
                    <span class="breakdown-value">$892</span>
                </div>
                <div class="breakdown-item">
                    <span class="breakdown-name">📧 Email Support</span>
                    <span class="breakdown-value">$654</span>
                </div>
                <div class="breakdown-item">
                    <span class="breakdown-name">📞 Phone Support</span>
                    <span class="breakdown-value">$1,101</span>
                </div>
                <div class="breakdown-item">
                    <span class="breakdown-name">🤖 AI Auto-Resolve</span>
                    <span class="breakdown-value">$200</span>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


def capture_screenshots():
    """Capture CommandDesk screenshots using HTML mockups.

    Note: These are representative mockups, not screenshots from the running application.
    """
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        # 1. Capture dashboard
        print("Capturing dashboard...")
        page.set_content(DASHBOARD_HTML)
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/dashboard.png", full_page=False)
        size = os.path.getsize(f"{SCREENSHOT_DIR}/dashboard.png")
        print(f"  Saved: dashboard.png ({size:,} bytes)")

        # 2. Capture AI assistant
        print("Capturing AI assistant...")
        page.set_content(AI_HTML)
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/ai-assistant.png", full_page=False)
        size = os.path.getsize(f"{SCREENSHOT_DIR}/ai-assistant.png")
        print(f"  Saved: ai-assistant.png ({size:,} bytes)")

        # 3. Capture costs
        print("Capturing costs...")
        page.set_content(COSTS_HTML)
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/costs.png", full_page=False)
        size = os.path.getsize(f"{SCREENSHOT_DIR}/costs.png")
        print(f"  Saved: costs.png ({size:,} bytes)")

        browser.close()

    print(f"\nScreenshots saved to {SCREENSHOT_DIR}/")


if __name__ == "__main__":
    capture_screenshots()
