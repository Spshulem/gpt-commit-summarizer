# gpt-commit-summarizer

`gpt-commit-summarizer` is a Python application that leverages OpenAI's GPT-4-Turbo language model to assist with code reviews. It provides an interface for users to interact with the GPT model to review code changes from GitHub pull requests.

## Prerequisites

Before you begin, ensure you have the following:
- Python 3.6 or higher
- `pip` for installing dependencies
- A GitHub account with access to the repositories you want to review
- An OpenAI API key

## Setup

1. **Clone the repository:**

sh
git clone https://github.com/spshulem/gpt-commit-summarizer.git
cd gpt-code-reviewer


2. **Install dependencies:**

sh
pip install -r requirements.txt


3. **Configure environment variables:**
   Set the `GITHUB_TOKEN` and `OPENAI_API_KEY` environment variables. Replace `<your_github_token>` and `<your_openai_api_key>` with your actual tokens.

sh
export GITHUB_TOKEN="<your_github_token>"
export OPENAI_API_KEY="<your_openai_api_key>"


4. **Set up the configuration file:**
   Copy the example configuration file and edit it to include the repositories you want to work with.

sh
cp config.yaml.example config.yaml
# Edit config.yaml to include your repositories and user information

sh
python repo.py


Follow the prompts to select a repository and enter the range of commits you want to review. The script will interact with the GPT model to provide summaries and feedback for the specified commits.

## Features

- Fetch and display a list of recent commits from a GitHub repository.
- Summarize code changes for individual or ranges of commits.
- Save transcripts of the review session for future reference.

## API Hosting

You can also host `gpt-code-reviewer` as an API using the following command:


## Usage

Run the script using the following command:

## API

You can also host gpt-code-reviewer as an api using `python api.py`, see `api.py` for the list of routes.

## License

This script is licensed under the MIT License. See the LICENSE file for details.
