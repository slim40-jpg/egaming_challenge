```bash
#!/bin/bash

echo "=========================================="
echo "  COMPILING GAMING AGENT (Linux)"
echo "=========================================="
echo

CXX=g++
CXXFLAGS="-std=c++17 -O2 -Wall -Wextra -Wno-unused-parameter"

echo "Compiling main.cpp and game_discovery.cpp..."

$CXX $CXXFLAGS \
    -o gaming_agent \
    main.cpp game_discovery.cpp

if [ $? -eq 0 ]; then
    echo
    echo "=========================================="
    echo "  BUILD SUCCESSFUL!"
    echo "=========================================="
    echo
    echo "Executable: gaming_agent"
    echo "Size:"
    ls -lh gaming_agent
    echo
    echo "Run with:"
    echo "  ./gaming_agent"
else
    echo
    echo "=========================================="
    echo "  BUILD FAILED!"
    echo "=========================================="
    exit 1
fi
```