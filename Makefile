# Makefile for Python application

# Detect operating system
ifeq ($(OS),Windows_NT)
	DETECTED_OS := Windows
	PYTHON := python
	RM := del /Q
	RM_DIR := rmdir /S /Q
	MKDIR := mkdir
else
	DETECTED_OS := $(shell uname -s)
	PYTHON := python3
	RM := rm -f
	RM_DIR := rm -rf
	MKDIR := mkdir -p
endif

# Default target
all: check_dependencies

# Check for required Python packages
check_dependencies:
	@echo "Checking for required Python packages..."
	@$(PYTHON) -c "import sys; sys.exit(0 if all(map(lambda m: m in sys.modules or __import__(m, fromlist=['']) is not None, ['flask', 'requests'])) else 1)" 2>/dev/null || (echo "Installing required packages..." && $(PYTHON) -m pip install -r requirements.txt)
	@echo "Dependencies checked."

# Run the application
run: check_dependencies
	@echo "Starting the application..."
	$(PYTHON) main.py

# Clean
clean:
	@echo "Cleaning up..."
	$(RM) *.pyc
	$(RM_DIR) __pycache__
	$(RM_DIR) build
	$(RM_DIR) dist
	$(RM_DIR) *.egg-info

# Install tkinterweb (optional)
install_tkinterweb:
	@echo "Installing tkinterweb package..."
	$(PYTHON) -m pip install tkinterweb

.PHONY: all clean run check_dependencies install_tkinterweb
