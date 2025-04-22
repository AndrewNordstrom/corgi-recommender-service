"""
Setup GUI routes for the Corgi Recommender Service.

This module provides a lightweight setup interface for demo purposes.
"""

import logging
import subprocess
import os
import json
from flask import Blueprint, render_template, request, jsonify, Response, current_app
from db.connection import get_db_connection
from utils.logging_decorator import log_route

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
setup_gui_bp = Blueprint('setup_gui', __name__, 
                        template_folder='../templates',
                        static_folder='../static/setup-gui')

@setup_gui_bp.route('', methods=['GET'])
@log_route
def setup_home():
    """
    Render the main setup GUI dashboard.
    """
    return render_template('setup.html')

@setup_gui_bp.route('/api/health', methods=['GET'])
@log_route
def check_health():
    """
    Check the health status of the service.
    """
    try:
        from routes.health import health_check
        health_response = health_check()
        if isinstance(health_response, tuple):
            response_data, status_code = health_response
        else:
            response_data = health_response.get_json()
            status_code = health_response.status_code
        
        return jsonify({"status": "ok", "health": response_data}), status_code
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@setup_gui_bp.route('/api/agent-profiles', methods=['GET'])
@log_route
def get_agent_profiles():
    """
    Get the list of available agent profiles.
    """
    try:
        from agents.user_profiles import list_available_profiles
        profiles = list_available_profiles()
        return jsonify({"status": "ok", "profiles": profiles})
    except Exception as e:
        logger.error(f"Failed to get agent profiles: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@setup_gui_bp.route('/api/mastodon-instances', methods=['GET'])
@log_route
def get_mastodon_instances():
    """
    Get a list of common Mastodon instances.
    """
    instances = [
        {"name": "mastodon.social", "url": "https://mastodon.social"},
        {"name": "fosstodon.org", "url": "https://fosstodon.org"},
        {"name": "techhub.social", "url": "https://techhub.social"},
        {"name": "infosec.exchange", "url": "https://infosec.exchange"},
        {"name": "hachyderm.io", "url": "https://hachyderm.io"}
    ]
    return jsonify({"status": "ok", "instances": instances})

@setup_gui_bp.route('/api/run-command', methods=['POST'])
@log_route
def run_command():
    """
    Run a Makefile command.
    """
    data = request.json
    command = data.get('command')
    
    if not command:
        return jsonify({"status": "error", "message": "Missing command parameter"}), 400
        
    allowed_commands = ['final-test', 'dry-validate', 'run-agent', 'check']
    command_parts = command.split()
    
    if not command_parts[0] in allowed_commands:
        return jsonify({"status": "error", "message": "Command not allowed"}), 403
        
    # Extra validation for run-agent commands
    if command_parts[0] == 'run-agent':
        # Check if we have a profile parameter
        profile_param = next((part for part in command_parts if part.startswith('profile=')), None)
        if not profile_param:
            return jsonify({"status": "error", "message": "Profile parameter is required for agent runs"}), 400
            
        # Validate that the requested profile exists
        try:
            profile_name = profile_param.split('=')[1]
            from agents.user_profiles import get_profile_by_name
            profile = get_profile_by_name(profile_name)
            logger.info(f"Validated agent profile: {profile_name}")
        except Exception as e:
            logger.error(f"Invalid agent profile requested: {str(e)}")
            return jsonify({"status": "error", "message": f"Invalid agent profile: {str(e)}"}), 400
    
    try:
        # Execute the command
        if command.startswith('run-agent'):
            # For run-agent commands, use the run-agent.sh script
            # Extract profile parameter
            profile = None
            if len(command_parts) > 1:
                for part in command_parts[1:]:
                    if part.startswith("profile="):
                        profile = part.split("=")[1]
            
            if not profile:
                return jsonify({"status": "error", "message": "Profile parameter required for run-agent"}), 400
                
            # Run the agent script
            process = subprocess.Popen(
                ["./run-agent.sh", f"profile={profile}", "headless=true"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=60)  # Set a timeout to avoid hanging
            
            # Log the command output
            log_command_output(command, stdout, stderr)
            
            if process.returncode != 0:
                return jsonify({
                    "status": "error",
                    "message": f"Command failed with exit code {process.returncode}",
                    "output": stdout,
                    "error": stderr
                }), 500
                
            return jsonify({
                "status": "ok",
                "message": f"Agent {profile} launched successfully",
                "output": stdout
            })
        else:
            # For other commands, use make
            process = subprocess.Popen(
                ["make", command_parts[0]],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=120)  # Set a timeout to avoid hanging
            
            # Log the command output
            log_command_output(command, stdout, stderr)
            
            if process.returncode != 0:
                return jsonify({
                    "status": "error",
                    "message": f"Command failed with exit code {process.returncode}",
                    "output": stdout,
                    "error": stderr
                }), 500
                
            return jsonify({
                "status": "ok",
                "message": f"Command {command} executed successfully",
                "output": stdout
            })
    except subprocess.TimeoutExpired:
        return jsonify({
            "status": "error", 
            "message": "Command execution timed out"
        }), 504
    except Exception as e:
        logger.error(f"Failed to run command {command}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@setup_gui_bp.route('/api/update-privacy', methods=['POST'])
@log_route
def update_privacy_setting():
    """
    Update privacy level for a user.
    """
    data = request.json
    user_id = data.get('user_id')
    privacy_level = data.get('privacy_level')
    
    if not user_id or not privacy_level:
        return jsonify({"status": "error", "message": "Missing required parameters"}), 400
        
    if privacy_level not in ['full', 'limited', 'none']:
        return jsonify({
            "status": "error", 
            "message": "Invalid privacy level",
            "valid_values": ['full', 'limited', 'none']
        }), 400
    
    try:
        # Use the existing privacy update endpoint
        from routes.privacy import update_privacy_level
        from utils.privacy import update_user_privacy_level
        
        with get_db_connection() as conn:
            success = update_user_privacy_level(conn, user_id, privacy_level)
            
            if not success:
                return jsonify({"status": "error", "message": "Failed to update privacy settings"}), 500
        
        return jsonify({
            "status": "ok",
            "message": f"Privacy level updated to {privacy_level}",
            "user_id": user_id,
            "privacy_level": privacy_level
        })
    except Exception as e:
        logger.error(f"Failed to update privacy settings: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@setup_gui_bp.route('/api/validation-results', methods=['GET'])
@log_route
def get_validation_results():
    """
    Get the latest validation results.
    """
    try:
        validation_file = os.path.join(os.getcwd(), 'validation_report.json')
        if not os.path.exists(validation_file):
            return jsonify({
                "status": "warning",
                "message": "No validation report found. Run validator first."
            })
            
        with open(validation_file, 'r') as f:
            validation_data = json.load(f)
            
        return jsonify({
            "status": "ok",
            "validation": validation_data
        })
    except Exception as e:
        logger.error(f"Failed to get validation results: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def log_command_output(command, stdout, stderr):
    """
    Log command output to a file for debugging.
    """
    try:
        os.makedirs('logs', exist_ok=True)
        with open('logs/setup_gui_commands.log', 'a') as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"COMMAND: {command}\n")
            f.write(f"STDOUT:\n{stdout}\n")
            f.write(f"STDERR:\n{stderr}\n")
            f.write(f"{'='*50}\n")
    except Exception as e:
        logger.error(f"Failed to log command output: {e}")