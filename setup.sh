#!/bin/bash

#===============================================
# POS System Automatic Setup Script for Linux/Mac
#===============================================
#
# This script will:
# 1. Check Python installation
# 2. Install required packages
# 3. Initialize database
# 4. Verify setup
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
#===============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step counter
STEP=1

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${BLUE}  POS SYSTEM - AUTOMATIC INSTALLATION${NC}"
    echo -e "${BLUE}=======================================${NC}"
    echo ""
}

print_step() {
    echo -e "${YELLOW}[$1/5] $2${NC}"
}

print_ok() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ===============================================
# Step 1: Check Python
# ===============================================
print_header
print_step "1" "Checking Python installation..."

if ! command -v python3 &> /dev/null; then
    print_error "Python3 not found!"
    echo ""
    echo "Please install Python:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    echo "  macOS (Homebrew): brew install python3"
    echo "  Or visit: https://www.python.org/downloads/"
    echo ""
    exit 1
fi

PYTHON_VER=$(python3 --version)
print_ok "Found: $PYTHON_VER"
echo ""

# ===============================================
# Step 2: Virtual Environment Setup (Optional)
# ===============================================
print_step "2" "Virtual Environment Setup (Optional)"

USE_VENV=0

if [ -d "venv" ]; then
    print_info "Virtual environment already exists"
    USE_VENV=1
else
    read -p "Do you want to create a virtual environment? (y/n): " create_venv
    
    if [[ "$create_venv" =~ ^[Yy]$ ]]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        
        if [ $? -eq 0 ]; then
            print_ok "Virtual environment created"
            USE_VENV=1
        else
            print_error "Failed to create virtual environment"
        fi
    fi
fi
echo ""

# ===============================================
# Step 3: Install Dependencies
# ===============================================
print_step "3" "Installing Python packages..."
echo ""

# Activate venv if created
if [ $USE_VENV -eq 1 ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        print_warning "Could not activate venv"
    fi
fi

echo "Installing required packages..."
python3 -m pip install --upgrade pip setuptools wheel > /dev/null 2>&1

echo "Installing python-telegram-bot and requests..."
python3 -m pip install python-telegram-bot requests > /dev/null 2>&1

if [ $? -eq 0 ]; then
    print_ok "Packages installed successfully"
else
    print_warning "Some packages could not be installed"
    echo "   (This is OK if using core features only)"
fi
echo ""

# ===============================================
# Step 4: Initialize Database
# ===============================================
print_step "4" "Initializing database..."
echo ""

python3 -c "
from database import DatabaseManager
try:
    db = DatabaseManager()
    print('✅ Database initialized')
    
    # Show stats
    stats = db.get_database_stats()
    print(f'   Products: {stats[\"total_products\"]}')
    print(f'   Transactions: {stats[\"total_transaksi\"]}')
    
    db.close()
except Exception as e:
    print(f'❌ Database error: {e}')
"

if [ $? -ne 0 ]; then
    print_error "Database initialization failed"
    echo ""
    exit 1
fi
echo ""

# ===============================================
# Step 5: Verify Installation
# ===============================================
print_step "5" "Verifying installation..."
echo ""

echo "Testing Python modules..."
python3 -c "
import sys
print('Python version:', sys.version.split()[0])

# Test built-in modules
try:
    import sqlite3
    print('✅ sqlite3 (built-in)')
except:
    print('❌ sqlite3 failed')

try:
    import json
    print('✅ json (built-in)')
except:
    print('❌ json failed')

try:
    import csv
    print('✅ csv (built-in)')
except:
    print('❌ csv failed')

# Test optional modules
try:
    import telegram
    print('✅ python-telegram-bot')
except:
    print('⚠️  python-telegram-bot (optional - needed for Telegram features)')

try:
    import requests
    print('✅ requests')
except:
    print('⚠️  requests (optional)')
"
echo ""

# ===============================================
# Setup Complete
# ===============================================
echo ""
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}   ✅ SETUP COMPLETE!${NC}"
echo -e "${GREEN}=======================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Read: GETTING_STARTED.md (5-minute quickstart)"
echo "  2. Read: README.md (features overview)"
echo "  3. Run:  python3 main.py"
echo ""
echo "Documentation:"
echo "  - INSTALL.md ...................... Detailed installation"
echo "  - GETTING_STARTED.md .............. Quick start guide"
echo "  - TROUBLESHOOTING.md .............. Common issues"
echo "  - README.md ....................... Full documentation"
echo "  - TELEGRAM_BOT_QUICKSTART.md ...... 5-min Telegram setup"
echo ""
echo "To start the application:"
echo "  python3 main.py"
echo ""
echo -e "${YELLOW}Quick permissions fix (if needed):${NC}"
echo "  chmod +x main.py || true"
echo "  chmod +x setup.sh || true"
echo ""
echo -e "${GREEN}=======================================${NC}"
echo ""

# ===============================================
# Optional: Offer to run program
# ===============================================
read -p "Do you want to start the program now? (y/n): " run_program

if [[ "$run_program" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting POS System..."
    echo ""
    
    # Make main.py executable if not already
    chmod +x main.py 2>/dev/null || true
    
    python3 main.py
else
    echo ""
    echo "Setup finished. Run 'python3 main.py' when ready."
    echo ""
fi
