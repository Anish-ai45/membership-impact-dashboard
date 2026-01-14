#!/usr/bin/env python3
"""Helper script to update the model name in config.py"""
import sys
import re

if len(sys.argv) < 2:
    print("Usage: python3 update_model.py <model-name>")
    print("\nExample:")
    print("  python3 update_model.py 'gemini-1.5-flash@latest'")
    print("  python3 update_model.py 'publishers/google/models/gemini-1.5-flash'")
    sys.exit(1)

new_model_name = sys.argv[1]
config_file = 'app/config.py'

try:
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Replace the chat_model line
    pattern = r"(self\.chat_model = )['\"][^'\"]*['\"]"
    replacement = f"self.chat_model = '{new_model_name}'"
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(config_file, 'w') as f:
            f.write(new_content)
        print(f"✅ Updated {config_file}")
        print(f"   Changed chat_model to: '{new_model_name}'")
        print("\nTest it with:")
        print("  python3 check_models.py")
    else:
        print(f"⚠️  No changes made. Pattern not found in {config_file}")
        print(f"   Make sure the file contains: self.chat_model = '...'")
        
except FileNotFoundError:
    print(f"❌ Error: {config_file} not found")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
