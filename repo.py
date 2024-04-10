import os
import openai
import yaml

from rich.console import Console
from rich.markdown import Markdown
import requests
from helpers import fetch_commits, add_message
from completion import get_completion

config = yaml.safe_load(open("config.yaml", "r", encoding="utf-8"))
console = Console()
github_repository_base_url = "https://api.github.com/repos"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_commit_diff(repository: str, commit_sha: str) -> str:
    url = f"{github_repository_base_url}/{repository}/commits/{commit_sha}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        return response.json()['files']
    else:
        console.print(f"Failed to fetch commit diff: {response.status_code}")
        return None

def summarize_changes(diff: str) -> str:
    messages = [
        {"role": "system", "content": "Please summarize the following code changes:"},
        {"role": "user", "content": diff}
    ]
    completion = get_completion(messages)
    return completion.choices[0].message.content


def chat():
    repository = "vercel/ai"  # replace with the repository you want to fetch commits from
    num_commits = 10  # replace with the number of commits you want to fetch

    commits = fetch_commits(repository, num_commits)
    if not commits:
        console.print("No commits found or failed to fetch commits.")
        return

    console.print("Most recent commits:")
    for i, commit in enumerate(commits, start=1):
        console.print(f"{i}. {commit['commit']['author']['date']} - {commit['commit']['message']}")

        # Prompt user to select a commit
    commit_range = input("Enter the range of commits to review (e.g., 1-5): ")
    start_index, end_index = map(int, commit_range.split('-'))

    for commit_index in range(start_index - 1, end_index):
        commit_sha = commits[commit_index]['sha']
        diff_files = get_commit_diff(repository, commit_sha)
        all_diffs = '\n'.join(file['patch'] for file in diff_files if 'patch' in file)
        summary = summarize_changes(all_diffs)
        console.print(Markdown(summary))

      # Concatenate diffs from all files
    all_diffs = '\n'.join(file['patch'] for file in diff_files if 'patch' in file)

    # Summarize the changes
    summary = summarize_changes(all_diffs)
    console.print(Markdown(summary))


    for i, commit in enumerate(commits, start=1):
        print(f"{i}. Commit: {commit['sha']}")
        print(f"    Message: {commit['commit']['message']}")
        print()

    messages = []

    while True:
        user_input = input("👨: ")

        if user_input == "q":
            break

        if user_input:
            console.print("Thinking...")
            add_message(messages, user_input, "user", repository)

            completion = get_completion(messages)

            reply = completion["choices"][0]["message"]["content"]

            console.print(Markdown("🤖: "))
            console.print(Markdown(reply))
            add_message(messages, reply, "assistant", repository)

if __name__ == "__main__":
    chat()