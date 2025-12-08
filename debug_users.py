#!/usr/bin/env python3
"""
User Account Debug Utility
Helps diagnose user account issues and monitor user data integrity
"""

import json
import os
from datetime import datetime

USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ {USERS_FILE} not found")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {USERS_FILE}: {e}")
        return {}

def check_user_integrity():
    """Check for common user data issues"""
    users = load_users()
    
    if not users:
        print("❌ No users found or file corrupted")
        return
    
    print(f"📊 Total users: {len(users)}")
    
    approved_count = 0
    pending_count = 0
    issues = []
    
    for email, user_data in users.items():
        # Check required fields
        if 'password' not in user_data:
            issues.append(f"❌ {email}: Missing password field")
        
        if 'approved' not in user_data:
            issues.append(f"⚠️ {email}: Missing approved field")
            user_data['approved'] = False
        
        # Count approval status
        if user_data.get('approved', False):
            approved_count += 1
        else:
            pending_count += 1
        
        # Check for suspicious patterns
        if 'created_at' in user_data:
            try:
                created_time = datetime.strptime(user_data['created_at'], '%Y-%m-%d %H:%M:%S')
                days_old = (datetime.now() - created_time).days
                if days_old > 30 and user_data.get('last_login') is None:
                    issues.append(f"⚠️ {email}: Account {days_old} days old, never logged in")
            except ValueError:
                issues.append(f"❌ {email}: Invalid created_at format")
    
    print(f"✅ Approved users: {approved_count}")
    print(f"⏳ Pending users: {pending_count}")
    
    if issues:
        print("\n🔍 Issues found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ No issues found")

def backup_users():
    """Create a backup of users.json"""
    if not os.path.exists(USERS_FILE):
        print(f"❌ {USERS_FILE} not found")
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"users_backup_{timestamp}.json"
    
    try:
        with open(USERS_FILE, 'r') as src, open(backup_name, 'w') as dst:
            dst.write(src.read())
        print(f"✅ Backup created: {backup_name}")
    except Exception as e:
        print(f"❌ Backup failed: {e}")

def monitor_user(email):
    """Monitor specific user account"""
    users = load_users()
    
    if email not in users:
        print(f"❌ User {email} not found")
        return
    
    user_data = users[email]
    print(f"👤 User: {email}")
    print(f"📝 Name: {user_data.get('name', 'N/A')}")
    print(f"✅ Approved: {user_data.get('approved', False)}")
    print(f"🕐 Created: {user_data.get('created_at', 'N/A')}")
    print(f"🔑 Last Login: {user_data.get('last_login', 'Never')}")
    print(f"🚪 Last Logout: {user_data.get('last_logout', 'N/A')}")
    print(f"🟢 Current Login: {user_data.get('current_login', 'Not logged in')}")

def main():
    print("🔧 User Account Debug Utility")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Check user integrity")
        print("2. Backup users.json")
        print("3. Monitor specific user")
        print("4. List all users")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            check_user_integrity()
        elif choice == '2':
            backup_users()
        elif choice == '3':
            email = input("Enter user email: ").strip()
            monitor_user(email)
        elif choice == '4':
            users = load_users()
            print(f"\n📋 All users ({len(users)}):")
            for email, data in users.items():
                status = "✅ Approved" if data.get('approved', False) else "⏳ Pending"
                print(f"  {email} - {status}")
        elif choice == '5':
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()