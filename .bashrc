#!/bin/bash

# Local .bashrc for this repository
# This file contains project-specific bash configurations

# Add LM Studio to PATH for this project (here's mine)
# export PATH="$PATH:/c/Users/tmf77/.lmstudio/bin"
# alias lms='/c/Users/tmf77/.lmstudio/bin/lms.exe'

# export PATH="$PATH:/c/Users/tmf77/AppData/Local/Programs/Ollama"
# alias ollama='/c/Users/tmf77/AppData/Local/Programs/Ollama/ollama.exe'

# Add R to your Path for this project (here's mine)
export PATH="$PATH:/c/Program Files/R/R-4.5.2/bin"
alias Rscript='/c/Program Files/R/R-4.5.2/bin/Rscript.exe'
# Add R libraries to your path for this project (here's mine)
export R_LIBS_USER="/c/Program Files/R/R-4.5.2/library"

# Add Python to your Path for this project (here's mine)
export PATH="$PATH:/c/Users/user/AppData/Local/Microsoft/WindowsApps"
alias python='/c/Users/user/AppData/Local/Microsoft/WindowsApps/PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0/python.exe'

# Add uvicorn to your Path for this project - if using Python for APIs (here's mine)
export PATH="$PATH:/c/Users/tmf77/AppData/Roaming/Python/Python312/Scripts"

echo "✅ Local .bashrc loaded."