#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check for tea CLI
if ! command -v tea &> /dev/null; then
    echo -e "${RED}Error: tea CLI not installed${NC}"
    echo "Install: brew install tea"
    echo "Setup:   tea login add --name=skjall --url=https://git.skjall.de --token=YOUR_TOKEN"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(grep -o '"version": "[^"]*"' custom_components/vallox_rs485/manifest.json | cut -d'"' -f4)
echo -e "${YELLOW}Current version: $CURRENT_VERSION${NC}"

# Parse version
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Determine bump type
BUMP_TYPE=${1:-patch}
case $BUMP_TYPE in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo -e "${RED}Usage: $0 [major|minor|patch]${NC}"
        exit 1
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
TAG="v$NEW_VERSION"
echo -e "${GREEN}New version: $NEW_VERSION${NC}"

# Confirm
read -p "Continue with release $TAG? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Update version in manifest.json
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" custom_components/vallox_rs485/manifest.json
echo -e "${GREEN}✓ Updated manifest.json${NC}"

# Commit and tag
git add custom_components/vallox_rs485/manifest.json
git commit -m "Release $TAG"
git tag "$TAG"
echo -e "${GREEN}✓ Created commit and tag${NC}"

# Push
git push origin development
git push origin "$TAG"
echo -e "${GREEN}✓ Pushed to Gitea${NC}"

# Create PR via tea CLI
tea pr create \
    --title "Release $TAG" \
    --description "Automated release PR for version $NEW_VERSION" \
    --head development \
    --base main

echo -e "\n${GREEN}Release $TAG complete!${NC}"
