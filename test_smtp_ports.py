#!/usr/bin/env python
"""
Test different SMTP ports for Brevo
"""
import socket
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_HOST = 'smtp-relay.brevo.com'
PORTS_TO_TEST = [25, 587, 465, 2525]

print("Testing SMTP port connectivity to Brevo...")
print()

for port in PORTS_TO_TEST:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((EMAIL_HOST, port))
        sock.close()
        
        if result == 0:
            print(f"✓ Port {port}: OPEN (connection successful)")
        else:
            print(f"✗ Port {port}: CLOSED (connection refused)")
    except socket.timeout:
        print(f"✗ Port {port}: TIMEOUT (blocked or filtered)")
    except Exception as e:
        print(f"✗ Port {port}: ERROR - {e}")

print("\nNote: Port 465 (SSL) is usually the most reliable")
print("If all ports fail, check if your ISP/firewall blocks SMTP")
