#!/bin/bash

# Prompt for GitHub Personal Access Token (PAT) without echoing input
read -sp "Enter your GitHub PAT: " GH_PAT
echo ""

# Define the repository to clone
REPO="https://github.com/swirlai/swirl-search.git"

# Modify the clone URL to include the PAT for authentication, using ':' as the delimiter for sed
CLONE_URL=$(echo "$REPO" | sed "s|://|://x-access-token:$GH_PAT@|")

# Clone the repository
git clone -b develop "$CLONE_URL"

# Clear the PAT variable for security
unset GH_PAT
