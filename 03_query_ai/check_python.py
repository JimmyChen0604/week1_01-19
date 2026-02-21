import sys
import os

print("=" * 60)
print("Python Diagnostic Information")
print("=" * 60)
print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print(f"Python Path: {sys.path[:3]}")  # First 3 paths
print()

# Check if zyte_api is available
try:
    import zyte_api
    print("✅ zyte_api is installed and importable")
    print(f"   Location: {zyte_api.__file__}")
except ImportError as e:
    print(f"❌ zyte_api is NOT available: {e}")
    print()
    print("To fix this:")
    print(f"1. Run: {sys.executable} -m pip install zyte-api")
    print("2. Or configure your IDE to use this Python:")
    print(f"   {sys.executable}")

print("=" * 60)

