#!/usr/bin/env python3
"""
Initialization script for Resume Evaluator Admin System
This script sets up the initial users.json file with default users
"""

import json
import os

def initialize_users():
    """Initialize users.json with default users"""
    
    users_file = "users.json"
    
    # Default users with approval status
    default_users = {
        "shreyasgowdaravi@gmail.com": {
            "password": "shreyas123",
            "approved": True,
            "last_login": None
        },
        "darshan.n@gradientm.com": {
            "password": "darshan123", 
            "approved": True,
            "last_login": None
        },
        "akshatha.m@gradientm.com": {
            "password": "akshatha123",
            "approved": True,
            "last_login": None
        },
        "shilpas@gradientm.com": {
            "password": "shilpa123",
            "approved": True,
            "last_login": None
        }
    }
    
    # Check if users.json already exists
    if os.path.exists(users_file):
        print(f"✅ {users_file} already exists")
        with open(users_file, 'r') as f:
            existing_users = json.load(f)
        print(f"📊 Current users: {len(existing_users)}")
        for email, info in existing_users.items():
            status = "✅ Approved" if info.get('approved', False) else "⏳ Pending"
            print(f"   - {email}: {status}")
    else:
        # Create users.json with default users
        with open(users_file, 'w') as f:
            json.dump(default_users, f, indent=2)
        print(f"🎉 Created {users_file} with {len(default_users)} default users")
        print("📋 Default users:")
        for email in default_users.keys():
            print(f"   - {email}: ✅ Approved")
    
    print("\n🔐 Admin Credentials:")
    print("   Email: shreyasgowdaravi@gmail.com")
    print("   Password: admin123")
    
    print("\n🚀 Admin Features:")
    print("   - View all users and their approval status")
    print("   - Approve/deny user access")
    print("   - Delete users")
    print("   - View user statistics")
    print("   - Track last login times")
    
    print("\n📝 Usage:")
    print("   1. Start the application: python app.py")
    print("   2. Login as admin: shreyasgowdaravi@gmail.com / admin123")
    print("   3. Manage users from the admin dashboard")
    print("   4. Regular users login with their credentials")

if __name__ == "__main__":
    initialize_users()