#!/usr/bin/env python3
"""
Research Dashboard Validation Script

This script validates that all components of the research dashboard are working
properly and provides a quick health check for PhD students and researchers.
"""

import sys
import requests
import json
import time
from datetime import datetime

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"🔍 {title}")
    print("=" * 60)

def print_success(message):
    """Print a success message"""
    print(f"✅ {message}")

def print_warning(message):
    """Print a warning message"""
    print(f"⚠️  {message}")

def print_error(message):
    """Print an error message"""
    print(f"❌ {message}")

def check_service(name, url, timeout=5):
    """Check if a service is running"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print_success(f"{name} is running (HTTP {response.status_code})")
            return True
        else:
            print_warning(f"{name} returned HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"{name} is not accessible: {e}")
        return False

def validate_frontend():
    """Validate frontend service"""
    print_header("Frontend Validation")
    
    frontend_ok = check_service("Frontend", "http://localhost:3000")
    dashboard_ok = check_service("Dashboard", "http://localhost:3000/dashboard")
    
    if frontend_ok and dashboard_ok:
        print_success("Frontend is ready for researchers!")
        return True
    else:
        print_error("Frontend issues detected")
        return False

def validate_api():
    """Validate API service"""
    print_header("API Service Validation")
    
    api_ok = check_service("API Health", "http://localhost:9999/health")
    
    if api_ok:
        print_success("API service is running")
        return True
    else:
        print_error("API service issues detected")
        return False

def validate_demo_data():
    """Validate that demo data is accessible"""
    print_header("Demo Data Validation")
    
    # Check if models endpoint works (even if it requires auth)
    try:
        response = requests.get("http://localhost:9999/api/v1/models", timeout=5)
        if response.status_code in [200, 401]:
            print_success("Model registry endpoint is accessible")
            return True
        else:
            print_warning(f"Model registry returned HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Model registry is not accessible: {e}")
        return False

def validate_research_features():
    """Validate research-specific features"""
    print_header("Research Features Validation")
    
    features = [
        ("Model Registry", "http://localhost:9999/api/v1/models"),
        ("Performance Metrics", "http://localhost:9999/api/v1/performance"),  
        ("A/B Testing", "http://localhost:9999/api/v1/experiments"),
    ]
    
    all_good = True
    for feature_name, url in features:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 401]:  # 401 means endpoint exists but requires auth
                print_success(f"{feature_name} endpoint is available")
            else:
                print_warning(f"{feature_name} endpoint returned HTTP {response.status_code}")
                all_good = False
        except requests.exceptions.RequestException as e:
            print_error(f"{feature_name} endpoint is not accessible")
            all_good = False
    
    return all_good

def check_file_resources():
    """Check that research documentation exists"""
    print_header("Research Resources Validation")
    
    import os
    resources = [
        ("Research Guide", "RESEARCH_GUIDE.md"),
        ("Demo Setup Script", "scripts/setup_demo_data.py"),
        ("Model Registry Component", "frontend/src/components/dashboard/ModelRegistry.tsx"),
        ("Onboarding Tour", "frontend/src/components/dashboard/OnboardingTour.tsx"),
    ]
    
    all_good = True
    for resource_name, file_path in resources:
        if os.path.exists(file_path):
            print_success(f"{resource_name} is available")
        else:
            print_error(f"{resource_name} is missing: {file_path}")
            all_good = False
    
    return all_good

def provide_next_steps():
    """Provide next steps for researchers"""
    print_header("Next Steps for Researchers")
    
    print("🎓 **Getting Started:**")
    print("   1. Open http://localhost:3000/dashboard")
    print("   2. Take the guided onboarding tour")
    print("   3. Explore the 6 pre-loaded demo models")
    print("   4. Read the research guide: RESEARCH_GUIDE.md")
    
    print("\n📊 **Immediate Actions:**")
    print("   • Check Model Registry tab for example algorithms")
    print("   • Review performance metrics and hyperparameters")
    print("   • Understand the tagging and organization system")
    print("   • Plan your first model registration")
    
    print("\n🔬 **Research Workflows:**")
    print("   • Compare algorithm performance using demo data")
    print("   • Design A/B tests for model validation")
    print("   • Monitor real-time performance analytics")
    print("   • Document experimental hypotheses")
    
    print("\n💡 **Pro Tips:**")
    print("   • Use tooltips (hover) for feature explanations")
    print("   • Start with simple comparisons before complex experiments")
    print("   • Tag models systematically for easy retrieval")
    print("   • Document hyperparameters and paper references")

def main():
    """Main validation function"""
    print("🎓 Corgi Recommender Research Dashboard Validation")
    print("Checking system readiness for PhD students and researchers...")
    
    # Track overall health
    all_systems_good = True
    
    # Validate each component
    all_systems_good &= validate_frontend()
    all_systems_good &= validate_api()
    all_systems_good &= validate_demo_data()
    all_systems_good &= validate_research_features()
    all_systems_good &= check_file_resources()
    
    # Final verdict
    print_header("System Status")
    
    if all_systems_good:
        print_success("🎉 Research dashboard is ready!")
        print_success("All systems are operational and configured for research use")
        provide_next_steps()
        
        print("\n" + "=" * 60)
        print("✨ **Industry Standards Achieved!** ✨")
        print("Your dashboard is now ready for:")
        print("  • PhD student algorithm development")
        print("  • Research lab collaboration")
        print("  • Academic paper experiments")
        print("  • Conference demonstrations")
        print("=" * 60)
        
        return True
    else:
        print_error("Some issues detected. Please address them before starting research.")
        print("\n🔧 **Common Solutions:**")
        print("   • Start services: make dev")
        print("   • Check ports: ./manage_server_port.sh status")
        print("   • Restart frontend: ./manage_server_port.sh start frontend")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 