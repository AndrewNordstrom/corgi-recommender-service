#!/usr/bin/env python3
"""
Web Dashboard for Agent System Management
Real-time monitoring and control interface
"""

from flask import Flask, render_template_string, jsonify, request
import sqlite3
import json
from datetime import datetime, timedelta
import asyncio
import threading
from core_agent_system import AgentOrchestrator

app = Flask(__name__)

# Global orchestrator instance
orchestrator = None

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Corgi Agent System Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #ffb300 0%, #ff8c00 100%);
            padding: 30px;
            color: white;
            text-align: center;
        }
        .header h1 { 
            font-size: 2.5em; 
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header p { 
            font-size: 1.2em; 
            opacity: 0.9;
        }
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            padding: 30px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.15);
        }
        .card h3 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.4em;
            border-bottom: 3px solid #ffb300;
            padding-bottom: 10px;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-active { background-color: #4CAF50; }
        .status-idle { background-color: #2196F3; }
        .status-error { background-color: #f44336; }
        .status-maintenance { background-color: #FF9800; }
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { 
            font-weight: 600; 
            color: #555;
        }
        .metric-value { 
            font-weight: bold; 
            color: #ffb300;
            font-size: 1.1em;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background-color: #e0e0e0;
            border-radius: 4px;
            margin-top: 8px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        .actions-list {
            max-height: 300px;
            overflow-y: auto;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
        }
        .action-item {
            background: white;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-left: 4px solid #ffb300;
            font-size: 0.9em;
        }
        .action-timestamp {
            color: #666;
            font-size: 0.8em;
            margin-bottom: 5px;
        }
        .action-success { border-left-color: #4CAF50; }
        .action-warning { border-left-color: #FF9800; }
        .action-error { border-left-color: #f44336; }
        .controls {
            background: #f8f9fa;
            padding: 20px;
            display: flex;
            gap: 15px;
            justify-content: center;
            border-top: 1px solid #e0e0e0;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: linear-gradient(135deg, #ffb300, #ff8c00);
            color: white;
        }
        .btn-secondary {
            background: linear-gradient(135deg, #6c757d, #495057);
            color: white;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .refresh-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255, 179, 0, 0.9);
            color: white;
            padding: 10px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div class="refresh-indicator" id="refreshIndicator">🔄 Auto-refresh: ON</div>
    
    <div class="container">
        <div class="header">
            <h1>🐕 Corgi Agent System</h1>
            <p>Cutting-Edge Multi-Agent Website Management</p>
        </div>

        <div class="dashboard-grid">
            <!-- System Overview -->
            <div class="card">
                <h3>📊 System Overview</h3>
                <div class="metric">
                    <span class="metric-label">Total Agents</span>
                    <span class="metric-value" id="totalAgents">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Active Agents</span>
                    <span class="metric-value" id="activeAgents">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Error Agents</span>
                    <span class="metric-value" id="errorAgents">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">System Health</span>
                    <span class="metric-value" id="systemHealth">-</span>
                </div>
            </div>

            <!-- Agent Status -->
            <div class="card">
                <h3>🤖 Agent Status</h3>
                <div id="agentStatus">Loading...</div>
            </div>

            <!-- Performance Metrics -->
            <div class="card">
                <h3>⚡ Performance Metrics</h3>
                <div class="metric">
                    <span class="metric-label">Avg Response Time</span>
                    <span class="metric-value" id="avgResponseTime">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Success Rate</span>
                    <span class="metric-value" id="successRate">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Tasks Completed</span>
                    <span class="metric-value" id="tasksCompleted">-</span>
                </div>
            </div>

            <!-- Recent Actions -->
            <div class="card">
                <h3>📝 Recent Actions</h3>
                <div class="actions-list" id="recentActions">Loading...</div>
            </div>

            <!-- Website Health -->
            <div class="card">
                <h3>🌐 Website Health</h3>
                <div class="metric">
                    <span class="metric-label">Frontend Status</span>
                    <span class="metric-value" id="frontendStatus">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Backend Status</span>
                    <span class="metric-value" id="backendStatus">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Database Status</span>
                    <span class="metric-value" id="databaseStatus">-</span>
                </div>
            </div>

            <!-- Security Status -->
            <div class="card">
                <h3>🔒 Security Status</h3>
                <div class="metric">
                    <span class="metric-label">Vulnerabilities</span>
                    <span class="metric-value" id="vulnerabilities">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Security Score</span>
                    <span class="metric-value" id="securityScore">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Last Scan</span>
                    <span class="metric-value" id="lastSecurityScan">-</span>
                </div>
            </div>
        </div>

        <div class="controls">
            <button class="btn btn-primary" onclick="runAgentCycle()">🚀 Run Agent Cycle</button>
            <button class="btn btn-secondary" onclick="toggleAutoRefresh()">⏸️ Pause Auto-Refresh</button>
            <button class="btn btn-secondary" onclick="exportReport()">📊 Export Report</button>
        </div>
    </div>

    <script>
        let autoRefresh = true;
        let refreshInterval;

        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // System Overview
                    document.getElementById('totalAgents').textContent = data.total_agents;
                    document.getElementById('activeAgents').textContent = data.active_agents;
                    document.getElementById('errorAgents').textContent = data.error_agents;
                    
                    const healthPercentage = ((data.total_agents - data.error_agents) / data.total_agents * 100).toFixed(1);
                    document.getElementById('systemHealth').textContent = healthPercentage + '%';

                    // Agent Status
                    updateAgentStatus(data.agents);
                    
                    // Performance Metrics
                    updatePerformanceMetrics(data.agents);
                })
                .catch(error => {
                    console.error('Error fetching status:', error);
                });

            fetch('/api/recent-actions')
                .then(response => response.json())
                .then(data => {
                    updateRecentActions(data);
                })
                .catch(error => {
                    console.error('Error fetching actions:', error);
                });
        }

        function updateAgentStatus(agents) {
            const container = document.getElementById('agentStatus');
            container.innerHTML = '';
            
            Object.entries(agents).forEach(([agentId, agent]) => {
                const statusDiv = document.createElement('div');
                statusDiv.className = 'metric';
                statusDiv.innerHTML = `
                    <span class="metric-label">
                        <span class="status-indicator status-${agent.status}"></span>
                        ${agent.name}
                    </span>
                    <span class="metric-value">${agent.status.toUpperCase()}</span>
                `;
                container.appendChild(statusDiv);
            });
        }

        function updatePerformanceMetrics(agents) {
            let totalTasks = 0;
            let totalErrors = 0;
            let totalResponseTime = 0;
            let agentCount = 0;

            Object.values(agents).forEach(agent => {
                totalTasks += agent.metrics.tasks_completed;
                totalErrors += agent.metrics.errors_encountered;
                if (agent.metrics.average_response_time) {
                    totalResponseTime += agent.metrics.average_response_time;
                    agentCount++;
                }
            });

            document.getElementById('avgResponseTime').textContent = 
                agentCount > 0 ? (totalResponseTime / agentCount).toFixed(2) + 's' : '-';
            
            const successRate = totalTasks > 0 ? ((totalTasks - totalErrors) / totalTasks * 100).toFixed(1) : '100';
            document.getElementById('successRate').textContent = successRate + '%';
            
            document.getElementById('tasksCompleted').textContent = totalTasks;
        }

        function updateRecentActions(actions) {
            const container = document.getElementById('recentActions');
            container.innerHTML = '';
            
            actions.slice(0, 10).forEach(action => {
                const actionDiv = document.createElement('div');
                actionDiv.className = `action-item action-${action.result}`;
                actionDiv.innerHTML = `
                    <div class="action-timestamp">${new Date(action.timestamp).toLocaleString()}</div>
                    <div><strong>${action.agent_id}:</strong> ${action.description}</div>
                `;
                container.appendChild(actionDiv);
            });
        }

        function runAgentCycle() {
            fetch('/api/run-cycle', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert('Agent cycle initiated successfully!');
                    updateDashboard();
                })
                .catch(error => {
                    alert('Error running agent cycle: ' + error);
                });
        }

        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const indicator = document.getElementById('refreshIndicator');
            const button = document.querySelector('.btn-secondary');
            
            if (autoRefresh) {
                indicator.textContent = '🔄 Auto-refresh: ON';
                button.textContent = '⏸️ Pause Auto-Refresh';
                startAutoRefresh();
            } else {
                indicator.textContent = '⏸️ Auto-refresh: OFF';
                button.textContent = '▶️ Resume Auto-Refresh';
                clearInterval(refreshInterval);
            }
        }

        function exportReport() {
            window.open('/api/export-report', '_blank');
        }

        function startAutoRefresh() {
            refreshInterval = setInterval(updateDashboard, 30000); // 30 seconds
        }

        // Initialize dashboard
        updateDashboard();
        startAutoRefresh();
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def get_status():
    """Get current system status"""
    if orchestrator:
        return jsonify(orchestrator.get_system_status())
    else:
        return jsonify({
            "total_agents": 0,
            "active_agents": 0,
            "error_agents": 0,
            "agents": {}
        })

@app.route('/api/recent-actions')
def get_recent_actions():
    """Get recent agent actions"""
    try:
        conn = sqlite3.connect('agents/agent_data.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT agent_id, action_type, description, timestamp, result, metadata
            FROM agent_actions 
            ORDER BY timestamp DESC 
            LIMIT 50
        """)
        
        actions = []
        for row in cursor.fetchall():
            actions.append({
                "agent_id": row[0],
                "action_type": row[1],
                "description": row[2],
                "timestamp": row[3],
                "result": row[4],
                "metadata": json.loads(row[5]) if row[5] else {}
            })
        
        conn.close()
        return jsonify(actions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/run-cycle', methods=['POST'])
def run_agent_cycle():
    """Manually trigger an agent cycle"""
    if orchestrator:
        try:
            # Run agent cycle in background thread
            def run_cycle():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(orchestrator.run_agent_cycle())
                loop.close()
            
            thread = threading.Thread(target=run_cycle)
            thread.start()
            
            return jsonify({"status": "success", "message": "Agent cycle initiated"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "Orchestrator not initialized"}), 500

@app.route('/api/export-report')
def export_report():
    """Export system report"""
    try:
        conn = sqlite3.connect('agents/agent_data.db')
        cursor = conn.cursor()
        
        # Get agent metrics
        cursor.execute("SELECT * FROM agent_metrics")
        metrics = cursor.fetchall()
        
        # Get recent actions
        cursor.execute("""
            SELECT * FROM agent_actions 
            WHERE timestamp > datetime('now', '-1 day')
            ORDER BY timestamp DESC
        """)
        actions = cursor.fetchall()
        
        conn.close()
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "agent_metrics": metrics,
            "recent_actions": actions,
            "system_status": orchestrator.get_system_status() if orchestrator else {}
        }
        
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def start_dashboard(port=5001):
    """Start the web dashboard"""
    global orchestrator
    
    # Initialize orchestrator
    from core_agent_system import (
        AgentOrchestrator, WebsiteHealthAgent, SecurityAgent,
        PerformanceOptimizationAgent, UserExperienceAgent,
        ContentManagementAgent, MLModelAgent, DeploymentAgent
    )
    
    orchestrator = AgentOrchestrator()
    
    # Register all agents
    orchestrator.register_agent(WebsiteHealthAgent())
    orchestrator.register_agent(SecurityAgent())
    orchestrator.register_agent(PerformanceOptimizationAgent())
    orchestrator.register_agent(UserExperienceAgent())
    orchestrator.register_agent(ContentManagementAgent())
    orchestrator.register_agent(MLModelAgent())
    orchestrator.register_agent(DeploymentAgent())
    
    print(f"🚀 Starting Corgi Agent Dashboard on http://localhost:{port}")
    print("📊 Dashboard Features:")
    print("   • Real-time agent monitoring")
    print("   • Performance metrics tracking")
    print("   • Security status overview")
    print("   • Manual agent cycle triggering")
    print("   • Action history and reporting")
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    start_dashboard() 