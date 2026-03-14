#!/bin/bash
# THOTH — CTF AI Mentor
# Install script

set -e

THOTH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_PATH="/usr/local/bin/thoth"

echo ""
echo "  𓂀  Installing THOTH..."
echo ""

# Create wrapper script
cat > /tmp/thoth_wrapper << EOF
#!/bin/bash
python3 "$THOTH_DIR/thoth.py" "\$@"
EOF

sudo mv /tmp/thoth_wrapper "$BIN_PATH"
sudo chmod +x "$BIN_PATH"

# Create thoth home dir
mkdir -p ~/.thoth

echo "  ✓ Installed to $BIN_PATH"
echo ""
echo "  Next steps:"
echo "  1. Get a free Groq API key: https://console.groq.com"
echo "  2. Run: thoth config groq_api_key gsk_your_key"
echo "  3. Run: thoth new"
echo ""
echo "  Run 'thoth' to see the banner."
echo ""
