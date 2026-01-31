#!/usr/bin/env python
import re

with open('accounts/views.py', 'r') as f:
    content = f.read()

# Replace all redirect('login') with redirect('accounts:login')
content = content.replace("redirect('login')", "redirect('accounts:login')")
# Also replace redirect('profile') with redirect('accounts:profile')
content = content.replace("redirect('profile')", "redirect('accounts:profile')")

with open('accounts/views.py', 'w') as f:
    f.write(content)

print('Fixed all redirect calls')
