"""
Tests for command-line argument handling in the Corgi server scripts.

This module tests that command-line arguments correctly override configuration
values from environment variables and defaults.
"""

import os
import sys
import unittest
import argparse
from unittest.mock import patch

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the functions we want to test
from config import parse_port
from run_server import parse_args as server_parse_args
from run_proxy_server import parse_args as proxy_parse_args
from special_proxy import parse_args as special_parse_args


class TestPortValidation(unittest.TestCase):
    """Test port validation function in config.py."""
    
    def test_valid_port(self):
        """Test that valid ports are accepted."""
        self.assertEqual(parse_port("8080"), 8080)
        self.assertEqual(parse_port("1024"), 1024)
        self.assertEqual(parse_port("65535"), 65535)
    
    def test_invalid_port(self):
        """Test that invalid ports fall back to default."""
        self.assertEqual(parse_port("0"), 5002)  # Below valid range
        self.assertEqual(parse_port("70000"), 5002)  # Above valid range
        self.assertEqual(parse_port("not a port"), 5002)  # Not a number
        self.assertEqual(parse_port(None), 5002)  # None
        self.assertEqual(parse_port(""), 5002)  # Empty string
        
    def test_custom_default(self):
        """Test that custom default value is used."""
        self.assertEqual(parse_port("invalid", default=9999), 9999)


class TestServerArgParsing(unittest.TestCase):
    """Test argument parsing in run_server.py."""
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_host_override(self, mock_parse_args):
        """Test that --host overrides environment variable."""
        mock_parse_args.return_value = argparse.Namespace(
            host="example.com", 
            port=5002, 
            no_https=False,
            force_http=False,
            cert=None,
            key=None
        )
        args = server_parse_args()
        self.assertEqual(args.host, "example.com")
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_port_override(self, mock_parse_args):
        """Test that --port overrides environment variable."""
        mock_parse_args.return_value = argparse.Namespace(
            host=None, 
            port=9090, 
            no_https=False,
            force_http=False,
            cert=None,
            key=None
        )
        args = server_parse_args()
        self.assertEqual(args.port, 9090)
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_no_https_flag(self, mock_parse_args):
        """Test that --no-https flag is recognized."""
        mock_parse_args.return_value = argparse.Namespace(
            host=None, 
            port=5002, 
            no_https=True,
            force_http=False,
            cert=None,
            key=None
        )
        args = server_parse_args()
        self.assertTrue(args.no_https)
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_force_http_flag(self, mock_parse_args):
        """Test that --force-http flag is recognized."""
        mock_parse_args.return_value = argparse.Namespace(
            host=None, 
            port=5002, 
            no_https=False,
            force_http=True,
            cert=None,
            key=None
        )
        args = server_parse_args()
        self.assertTrue(args.force_http)
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_cert_path_override(self, mock_parse_args):
        """Test that --cert overrides environment variable."""
        mock_parse_args.return_value = argparse.Namespace(
            host=None, 
            port=5002, 
            no_https=False,
            force_http=False,
            cert="/custom/cert.pem",
            key=None
        )
        args = server_parse_args()
        self.assertEqual(args.cert, "/custom/cert.pem")
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_key_path_override(self, mock_parse_args):
        """Test that --key overrides environment variable."""
        mock_parse_args.return_value = argparse.Namespace(
            host=None, 
            port=5002, 
            no_https=False,
            force_http=False,
            cert=None,
            key="/custom/key.pem"
        )
        args = server_parse_args()
        self.assertEqual(args.key, "/custom/key.pem")


class TestProxyArgParsing(unittest.TestCase):
    """Test argument parsing in run_proxy_server.py."""
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_host_override(self, mock_parse_args):
        """Test that --host overrides environment variable."""
        mock_parse_args.return_value = argparse.Namespace(
            host="example.com", 
            port=5003, 
            no_https=False,
            force_http=False,
            cert=None,
            key=None
        )
        args = proxy_parse_args()
        self.assertEqual(args.host, "example.com")
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_port_override(self, mock_parse_args):
        """Test that --port overrides environment variable."""
        mock_parse_args.return_value = argparse.Namespace(
            host=None, 
            port=9090, 
            no_https=False,
            force_http=False,
            cert=None,
            key=None
        )
        args = proxy_parse_args()
        self.assertEqual(args.port, 9090)


class TestSpecialProxyArgParsing(unittest.TestCase):
    """Test argument parsing in special_proxy.py."""
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_host_override(self, mock_parse_args):
        """Test that --host overrides environment variable."""
        mock_parse_args.return_value = argparse.Namespace(
            host="example.com", 
            port=5004, 
            no_https=False,
            force_http=False,
            cert=None,
            key=None
        )
        args = special_parse_args()
        self.assertEqual(args.host, "example.com")
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_port_override(self, mock_parse_args):
        """Test that --port overrides environment variable."""
        mock_parse_args.return_value = argparse.Namespace(
            host=None, 
            port=9090, 
            no_https=False,
            force_http=False,
            cert=None,
            key=None
        )
        args = special_parse_args()
        self.assertEqual(args.port, 9090)


if __name__ == '__main__':
    unittest.main()