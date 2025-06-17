#!/usr/bin/env python3
"""
Auto Security Healing Integration Script

This script demonstrates how to integrate LLM-powered security healing
into the existing Corgi monitoring infrastructure.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add the agents directory to the path
sys.path.append(str(Path(__file__).parent.parent / "agents"))

try:
    from security_healing_agent import SecurityHealingAgent
except ImportError:
    print("⚠️  Security healing agent not available. Using basic scanning.")
    SecurityHealingAgent = None

class AutoSecurityHealer:
    """Simple integration for automated security healing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.healing_agent = SecurityHealingAgent() if SecurityHealingAgent else None
        self.scan_results = {}
        
    async def run_comprehensive_scan(self):
        """Run comprehensive security scan"""
        print("🔍 Starting comprehensive security scan...")
        
        # Run existing security tools
        scan_results = {
            'timestamp': datetime.now().isoformat(),
            'python_audit': await self._run_pip_audit(),
            'node_audit': await self._run_npm_audit(),
            'bandit_scan': await self._run_bandit(),
            'safety_check': await self._run_safety_check()
        }
        
        # Count total vulnerabilities
        total_vulns = self._count_vulnerabilities(scan_results)
        
        print(f"📊 Scan complete: {total_vulns} vulnerabilities found")
        
        return scan_results
    
    async def analyze_and_heal(self, scan_results):
        """Analyze vulnerabilities and apply healing if possible"""
        
        total_vulns = self._count_vulnerabilities(scan_results)
        
        if total_vulns == 0:
            print("✅ No vulnerabilities detected - system is secure!")
            return True
        
        print(f"🚨 Found {total_vulns} vulnerabilities")
        
        if self.healing_agent:
            print("🤖 Activating LLM-powered security healing...")
            
            try:
                # Run the healing agent
                healing_actions = await self.healing_agent.execute()
                
                # Process results
                auto_fixed = 0
                needs_approval = 0
                
                for action in healing_actions:
                    if action.result == "success":
                        auto_fixed += 1
                        print(f"✅ Auto-fixed: {action.description}")
                    elif action.action_type == "approval_request":
                        needs_approval += 1
                        print(f"⏳ Needs approval: {action.description}")
                    elif action.result == "error":
                        print(f"❌ Failed: {action.description}")
                
                print(f"\n🎯 Healing Summary:")
                print(f"   • Auto-fixed: {auto_fixed}")
                print(f"   • Needs approval: {needs_approval}")
                print(f"   • Remaining vulnerabilities: {total_vulns - auto_fixed}")
                
                if needs_approval > 0:
                    print(f"\n⚠️  {needs_approval} fixes require human approval")
                    print("   Run with --approve-all to auto-approve low-risk fixes")
                
                return auto_fixed > 0
                
            except Exception as e:
                print(f"❌ LLM healing failed: {e}")
                return await self._fallback_healing(scan_results)
        else:
            print("🔧 Using basic automated fixes...")
            return await self._fallback_healing(scan_results)
    
    async def _fallback_healing(self, scan_results):
        """Basic automated healing without LLM"""
        fixes_applied = 0
        
        # Auto-fix Python dependencies if available
        if scan_results.get('python_audit', {}).get('vulnerabilities'):
            print("🔧 Attempting to update Python dependencies...")
            try:
                result = subprocess.run([
                    "pip", "install", "--upgrade", 
                    "gunicorn", "psycopg2-binary", "urllib3", "pytest"
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    print("✅ Updated Python dependencies")
                    fixes_applied += 1
                else:
                    print(f"⚠️  Python dependency update failed: {result.stderr}")
            except Exception as e:
                print(f"❌ Python dependency update error: {e}")
        
        # Auto-fix Node.js dependencies if available
        if scan_results.get('node_audit', {}).get('vulnerabilities'):
            print("🔧 Attempting to fix Node.js dependencies...")
            try:
                result = subprocess.run([
                    "npm", "audit", "fix"
                ], cwd="frontend", capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    print("✅ Fixed Node.js dependencies")
                    fixes_applied += 1
                else:
                    print(f"⚠️  Node.js dependency fix failed: {result.stderr}")
            except Exception as e:
                print(f"❌ Node.js dependency fix error: {e}")
        
        return fixes_applied > 0
    
    async def _run_pip_audit(self):
        """Run pip-audit for Python dependencies"""
        try:
            result = subprocess.run([
                "pip-audit", "--format=json", "--progress-spinner=off"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)
            else:
                return {"vulnerabilities": []}
        except Exception as e:
            self.logger.error(f"pip-audit failed: {e}")
            return {"error": str(e)}
    
    async def _run_npm_audit(self):
        """Run npm audit for Node.js dependencies"""
        try:
            result = subprocess.run([
                "npm", "audit", "--json"
            ], cwd="frontend", capture_output=True, text=True, timeout=60)
            
            if result.stdout:
                return json.loads(result.stdout)
            else:
                return {"vulnerabilities": {}}
        except Exception as e:
            self.logger.error(f"npm audit failed: {e}")
            return {"error": str(e)}
    
    async def _run_bandit(self):
        """Run bandit for code security issues"""
        try:
            result = subprocess.run([
                "bandit", "-r", ".", "-f", "json", "-ll"
            ], capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                return json.loads(result.stdout)
            else:
                return {"results": []}
        except Exception as e:
            self.logger.error(f"bandit failed: {e}")
            return {"error": str(e)}
    
    async def _run_safety_check(self):
        """Run safety check for known vulnerabilities"""
        try:
            result = subprocess.run([
                "safety", "check", "--json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.stdout:
                return json.loads(result.stdout)
            else:
                return []
        except Exception as e:
            self.logger.error(f"safety check failed: {e}")
            return {"error": str(e)}
    
    def _count_vulnerabilities(self, scan_results):
        """Count total vulnerabilities across all scans"""
        total = 0
        
        # Python audit
        python_vulns = scan_results.get('python_audit', {}).get('vulnerabilities', [])
        total += len(python_vulns)
        
        # Node audit
        node_vulns = scan_results.get('node_audit', {}).get('vulnerabilities', {})
        total += len(node_vulns)
        
        # Bandit
        bandit_results = scan_results.get('bandit_scan', {}).get('results', [])
        total += len(bandit_results)
        
        # Safety
        safety_results = scan_results.get('safety_check', [])
        if isinstance(safety_results, list):
            total += len(safety_results)
        
        return total
    
    def save_results(self, scan_results, healing_results=None):
        """Save scan and healing results"""
        output_file = Path("logs/security_healing_results.json")
        output_file.parent.mkdir(exist_ok=True)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'scan_results': scan_results,
            'healing_results': healing_results,
            'summary': {
                'total_vulnerabilities': self._count_vulnerabilities(scan_results),
                'healing_agent_available': self.healing_agent is not None
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"📄 Results saved to {output_file}")

async def main():
    """Main execution function"""
    print("🛡️  Corgi Auto Security Healing System")
    print("=" * 50)
    
    healer = AutoSecurityHealer()
    
    try:
        # Step 1: Comprehensive scan
        scan_results = await healer.run_comprehensive_scan()
        
        # Step 2: Analyze and heal
        healing_success = await healer.analyze_and_heal(scan_results)
        
        # Step 3: Save results
        healer.save_results(scan_results, {"healing_applied": healing_success})
        
        # Step 4: Final status
        print("\n" + "=" * 50)
        if healing_success:
            print("✅ Security healing completed successfully!")
            print("🔄 Re-run to verify fixes were applied")
        else:
            print("⚠️  No automatic fixes were applied")
            print("📋 Review the results and apply manual fixes as needed")
        
        return 0
        
    except Exception as e:
        print(f"❌ Security healing failed: {e}")
        return 1

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the healing system
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 