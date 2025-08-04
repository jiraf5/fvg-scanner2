#!/bin/bash

# 🚀 FVG Scanner - Automated Deployment Script
# This script automates the deployment process to GitHub and Railway

set -e  # Exit on any error

echo "🚀 FVG Scanner - Automated Deployment Script"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed. Please install Git first."
    exit 1
fi

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    print_status "Initializing Git repository..."
    git init
    print_success "Git repository initialized"
fi

# Get user input for GitHub repository
echo
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter your repository name (default: fvg-scanner): " REPO_NAME
REPO_NAME=${REPO_NAME:-fvg-scanner}

# Get commit message
echo
read -p "Enter commit message (default: Deploy FVG Scanner to production): " COMMIT_MESSAGE
COMMIT_MESSAGE=${COMMIT_MESSAGE:-"Deploy FVG Scanner to production"}

# Check if required files exist
print_status "Checking required files..."

required_files=("main.py" "scanner.py" "requirements.txt" "Procfile" "static/index.html" "static/script.js" "static/styles.css")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    print_error "Missing required files:"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    print_error "Please ensure all required files are present before deploying."
    exit 1
fi

print_success "All required files found"

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    print_status "Creating .gitignore file..."
    cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
*.pyc

# Virtual Environment
venv/
env/
ENV/
.venv/
.env/

# Environment Variables
.env
.env.local
.env.production
.env.development

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
*.log

# OS
.DS_Store
Thumbs.db

# Railway specific
.railway/
EOF
    print_success ".gitignore created"
fi

# Add all files to git
print_status "Adding files to Git..."
git add .

# Check if there are changes to commit
if git diff --staged --quiet; then
    print_warning "No changes to commit"
else
    # Commit changes
    print_status "Committing changes..."
    git commit -m "$COMMIT_MESSAGE"
    print_success "Changes committed"
fi

# Set up remote repository
REMOTE_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"

# Check if remote already exists
if git remote get-url origin &> /dev/null; then
    print_status "Remote origin already exists, updating URL..."
    git remote set-url origin "$REMOTE_URL"
else
    print_status "Adding remote origin..."
    git remote add origin "$REMOTE_URL"
fi

print_success "Remote repository configured: $REMOTE_URL"

# Set main branch
print_status "Setting up main branch..."
git branch -M main

# Push to GitHub
print_status "Pushing to GitHub..."
if git push -u origin main; then
    print_success "Successfully pushed to GitHub!"
else
    print_error "Failed to push to GitHub. Please check:"
    echo "  1. Repository exists on GitHub: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
    echo "  2. You have write access to the repository"
    echo "  3. Your Git credentials are configured"
    echo
    echo "To create the repository on GitHub:"
    echo "  1. Go to https://github.com/new"
    echo "  2. Repository name: $REPO_NAME"
    echo "  3. Make it Public (required for Railway free tier)"
    echo "  4. Don't initialize with README"
    echo "  5. Click 'Create repository'"
    echo
    echo "Then run this script again."
    exit 1
fi

# Provide Railway deployment instructions
echo
echo "=============================================="
print_success "🎉 GitHub deployment complete!"
echo "=============================================="
echo
print_status "Next steps for Railway deployment:"
echo
echo "1. 🌐 Go to: https://railway.app"
echo "2. 🔐 Sign up/login with your GitHub account"
echo "3. ➕ Click 'New Project'"
echo "4. 📂 Select 'Deploy from GitHub repo'"
echo "5. 🎯 Choose: $GITHUB_USERNAME/$REPO_NAME"
echo "6. 🚀 Click 'Deploy Now'"
echo
print_status "Railway will automatically:"
echo "  ✅ Detect Python application"
echo "  ✅ Install dependencies from requirements.txt"
echo "  ✅ Use Procfile for start command"
echo "  ✅ Provide public HTTPS URL"
echo "  ✅ Set up automatic deployments"
echo
print_success "Your app will be live at: https://your-app-name.up.railway.app"
echo
print_status "Repository URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo
print_warning "Note: Replace 'your-app-name' with the actual name Railway assigns"

# Check if Railway CLI is installed
if command -v railway &> /dev/null; then
    echo
    print_status "Railway CLI detected! You can also deploy using:"
    echo "  railway login"
    echo "  railway link"
    echo "  railway up"
else
    echo
    print_status "💡 Tip: Install Railway CLI for easier deployments:"
    echo "  npm install -g @railway/cli"
    echo "  railway login"
    echo "  railway link"
    echo "  railway up"
fi

# Provide update instructions
echo
print_status "🔄 For future updates:"
echo "  1. Make your changes"
echo "  2. Run: git add ."
echo "  3. Run: git commit -m 'Your update message'"
echo "  4. Run: git push origin main"
echo "  5. Railway will automatically deploy the changes!"

echo
print_success "🚀 Deployment script completed successfully!"
print_success "🌟 Your FVG Scanner is ready for production!"