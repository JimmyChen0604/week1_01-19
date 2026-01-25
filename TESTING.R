# If you haven't yet, install these two packages:
# Set CRAN mirror
options(repos = c(CRAN = "https://cloud.r-project.org"))
# Install to user library (writable location)
user_lib <- Sys.getenv("R_LIBS_USER")
if (user_lib == "") {
  user_lib <- file.path(Sys.getenv("USERPROFILE"), "Documents", "R", "win-library", paste(R.version$major, R.version$minor, sep = "."))
}
dir.create(user_lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(user_lib, .libPaths()))
install.packages(c("usethis", "gert", "credentials"), lib = user_lib)
# Load packages
library(usethis) # for coding management helper functions
library(gert) # for github operations like commit, pull, and push
library(credentials) # for authenticating with github

# You might want to put your Personal Access Token in a .env file
# Create a .env 'environmental variables' file
file.create("tockens.env")
# open the file and add: GITHUB_PAT=whatever_it_was_here

# and then add the .env file to the .gitignore file,
# which lists which files should NEVER be uploaded to a github repository for security reasons.
usethis::use_git_ignore("tockens.env")
# Also 'vaccinate' your computer's global .gitignore file - which helps keep sensitive files out. 
# Won't change your repository's .gitignore
usethis::git_vaccinate()


# Set your Github Personal Access Token
# Check if PAT is already set, if not, try to set it (will fail in non-interactive mode)
if (Sys.getenv("GITHUB_PAT") == "") {
  # Try to set GitHub PAT (this requires interactive input)
  # In non-interactive mode, you can set it manually via:
  # Sys.setenv(GITHUB_PAT = "your_token_here")
  # Or set it in your system environment variables
  tryCatch({
    credentials::set_github_pat()
  }, error = function(e) {
    cat("⚠️  Warning: Could not set GitHub PAT interactively.\n")
    cat("   Please set it manually using one of these methods:\n")
    cat("   1. Set environment variable: GITHUB_PAT=your_token\n")
    cat("   2. Or run in R/RStudio: credentials::set_github_pat()\n")
    cat("   3. Or add to tockens.env file: GITHUB_PAT=your_token\n")
  })
} else {
  cat("✅ GitHub PAT is already set.\n")
}


# pull most recent changes from GitHub
tryCatch({
  gert::git_pull()
  cat("✅ Successfully pulled from GitHub.\n")
}, error = function(e) {
  cat("⚠️  Warning: Could not pull from GitHub:", conditionMessage(e), "\n")
})

# select any and all new files created or edited to be 'staged'
# 'staged' files are to be saved anew on GitHub 
# dir(all.files = TRUE) selects ALL files to be added.
tryCatch({
  gert::git_add(dir(all.files = TRUE))
  cat("✅ Files staged successfully.\n")
}, error = function(e) {
  cat("⚠️  Warning: Could not stage files:", conditionMessage(e), "\n")
})

# save your record of file edits - called a commit
tryCatch({
  gert::git_commit_all("my first commit")
  cat("✅ Commit created successfully.\n")
}, error = function(e) {
  cat("⚠️  Warning: Could not create commit:", conditionMessage(e), "\n")
})

# push your commit to GitHub
tryCatch({
  gert::git_push()
  cat("✅ Successfully pushed to GitHub.\n")
}, error = function(e) {
  cat("⚠️  Warning: Could not push to GitHub:", conditionMessage(e), "\n")
  cat("   Make sure you have:\n")
  cat("   1. A remote repository configured\n")
  cat("   2. Valid GitHub credentials\n")
  cat("   3. Network connection\n")
}) 