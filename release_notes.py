import os
import requests
from typing import List, Dict
from datetime import datetime
import yaml
from rich.console import Console
from rich.markdown import Markdown
from completion import get_completion

console = Console()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable is not set")
GITHUB_API_BASE = "https://api.github.com/repos"

def sanitize_filename(filename: str) -> str:
    """Convert tag name to a safe filename"""
    return filename.replace('/', '_').replace('\\', '_')

def fetch_releases(repository: str) -> List[Dict]:
    """Fetch all releases from a GitHub repository"""
    url = f"{GITHUB_API_BASE}/{repository}/releases"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    releases = []
    page = 1
    
    while True:
        response = requests.get(
            url,
            headers=headers,
            params={"page": page, "per_page": 100},
            timeout=10
        )
        if response.status_code != 200:
            console.print(f"Failed to fetch releases: {response.status_code}")
            return []
        
        page_releases = response.json()
        if not page_releases:
            break
            
        releases.extend(page_releases)
        page += 1
    
    return releases

def filter_production_releases(releases: List[Dict]) -> List[Dict]:
    """Filter releases that contain 'production' in their tag name, title, or body"""
    return [r for r in releases if 
            "production" in r["tag_name"].lower() or 
            (r["name"] and "production" in r["name"].lower()) or 
            (r["body"] and "production" in r["body"].lower())]

def get_commits_between_tags(repository: str, base_tag: str, head_tag: str) -> List[Dict]:
    """Get all commits between two tags including their diffs"""
    url = f"{GITHUB_API_BASE}/{repository}/compare/{base_tag}...{head_tag}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        console.print(f"Failed to fetch commits between tags: {response.status_code}")
        return []
    
    data = response.json()
    commits = data["commits"]
    
    # Fetch detailed diff for each commit
    for commit in commits:
        commit_url = f"{GITHUB_API_BASE}/{repository}/commits/{commit['sha']}"
        commit_response = requests.get(commit_url, headers=headers, timeout=10)
        if commit_response.status_code == 200:
            commit_data = commit_response.json()
            commit['detailed_diff'] = commit_data.get('files', [])
    
    return commits

def summarize_commit(commit: Dict) -> str:
    """Generate a summary for a single commit using GPT, including code changes"""
    # Prepare the diff information
    diff_summary = []
    for file in commit.get('detailed_diff', []):
        filename = file.get('filename', '')
        changes = file.get('patch', '')
        if changes:
            diff_summary.append(f"File: {filename}\n{changes}")
    
    diff_text = "\n\n".join(diff_summary) if diff_summary else "No detailed changes available"
    
    messages = [
        {"role": "system", "content": """Please provide a concise, clear summary of the following commit in changelog format. 
Important guidelines:
- Distinguish between actual bug fixes (issues in existing functionality) and QA-related fixes (issues found during testing of new features)
- QA tickets (usually containing 'QA-' or similar in commit messages) should be categorized as 'Improvements' or 'Features' since they're enhancing new functionality
- Only categorize as 'Bug Fixes' if it's fixing existing, previously working functionality
- Focus on the impact and purpose of the changes from an end-user perspective
- Include relevant technical details only if they're important for understanding the change"""},
        {"role": "user", "content": f"Commit message: {commit['commit']['message']}\nAuthor: {commit['commit']['author']['name']}\n\nCode Changes:\n{diff_text}"}
    ]
    completion = get_completion(messages)
    return completion.choices[0].message.content

def generate_release_changelog(repository: str, current_release: Dict, previous_tag: str) -> str:
    """Generate a changelog for a specific release"""
    commits = get_commits_between_tags(repository, previous_tag, current_release["tag_name"])
    commit_summaries = []
    
    console.print(f"\nAnalyzing {len(commits)} commits...")
    for i, commit in enumerate(commits, 1):
        console.print(f"Processing commit {i}/{len(commits)}")
        summary = summarize_commit(commit)
        commit_summaries.append(summary)
    
    # Generate consolidated changelog
    messages = [
        {"role": "system", "content": """Please create a comprehensive QA-focused changelog from the following commit summaries.

Organization guidelines:

1. High-Level Summary:
   - Brief overview of the release's major changes
   - Key areas requiring focused testing
   - Potential risk areas

2. Detailed Changes (categorized):
   🚀 New Features
   - List each new feature
   - Specify what functionality needs to be tested
   - Note any dependencies or related features that could be impacted
   
   ✨ Improvements & Enhancements
   - Detail improvements to existing features
   - Highlight changes in user workflows or UI
   - Note any performance improvements that need verification
   
   🐛 Bug Fixes
   - Describe each fix and its impact
   - Specify regression testing needs
   - Note related features that should be re-tested
   
   🔧 Technical Changes
   - List infrastructure or system-level changes
   - Note any performance or security implications
   - Highlight areas needing load/stress testing

3. Testing Focus Areas:
   - Critical user paths affected
   - Cross-browser/device testing requirements
   - API endpoints or services modified
   - Database changes or data migrations
   - Performance-sensitive areas
   - Security considerations

4. Integration Points:
   - List affected third-party integrations
   - Note any API changes or versioning
   - Highlight cross-service dependencies

Make it detailed and structured, focusing on what QA needs to verify and test thoroughly."""},
        {"role": "user", "content": "\n".join(commit_summaries)}
    ]
    completion = get_completion(messages)
    return completion.choices[0].message.content

def main():
    repository = input("Enter repository (e.g., buildbetter-app/buildbetter-app): ")
    console.print("Fetching releases...")
    
    releases = fetch_releases(repository)
    if not releases:
        console.print("No releases found.")
        return
    
    production_releases = filter_production_releases(releases)
    if not production_releases:
        console.print("No production releases found.")
        return
    
    console.print(f"\nFound {len(production_releases)} production releases.")
    
    # Display mode selection
    console.print("\nSelect mode:")
    console.print("1. Analyze single release (changes since previous release)")
    console.print("2. Compare two releases (changes between any two releases)")
    
    mode = input("\nEnter mode (1 or 2): ").strip()
    
    if mode not in ['1', '2']:
        console.print("Invalid mode selected.")
        return
    
    # Display releases with numbers for selection
    for i, release in enumerate(production_releases, 1):
        release_date = datetime.strptime(release['published_at'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')
        console.print(f"{i}. {release['tag_name']} ({release_date})")
    
    if mode == '1':
        # Single release mode
        while True:
            try:
                selection = input("\nEnter the number of the release to process (or 'q' to quit): ")
                if selection.lower() == 'q':
                    break
                    
                idx = int(selection) - 1
                if 0 <= idx < len(production_releases):
                    release = production_releases[idx]
                    console.print(f"\nProcessing release: {release['tag_name']}")
                    
                    # Find the previous production release
                    previous_tag = production_releases[idx + 1]["tag_name"] if idx + 1 < len(production_releases) else None
                    
                    if previous_tag:
                        changelog = generate_release_changelog(repository, release, previous_tag)
                        console.print("\nChangelog:")
                        console.print(Markdown(changelog))
                        
                        # Create changelogs directory if it doesn't exist
                        os.makedirs("changelogs", exist_ok=True)
                        
                        # Save changelog to file with sanitized filename
                        safe_filename = sanitize_filename(release['tag_name'])
                        filepath = os.path.join("changelogs", f"changelog_{safe_filename}.md")
                        with open(filepath, "w") as f:
                            f.write(f"# Changelog for {release['tag_name']}\n\n")
                            f.write(f"Release Date: {release['published_at']}\n\n")
                            f.write(changelog)
                        console.print(f"\nChangelog saved to: {filepath}")
                    else:
                        console.print("This is the oldest release, no previous release to compare with.")
                else:
                    console.print("Invalid selection. Please try again.")
            except ValueError:
                console.print("Invalid input. Please enter a number or 'q' to quit.")
            except Exception as e:
                console.print(f"Error processing release: {str(e)}")
    else:
        # Compare two releases mode
        while True:
            try:
                console.print("\nSelect two releases to compare:")
                newer_release = input("Enter the number of the NEWER release (or 'q' to quit): ")
                if newer_release.lower() == 'q':
                    break
                
                older_release = input("Enter the number of the OLDER release: ")
                newer_idx = int(newer_release) - 1
                older_idx = int(older_release) - 1
                
                if 0 <= newer_idx < len(production_releases) and 0 <= older_idx < len(production_releases):
                    if newer_idx >= older_idx:
                        console.print("Error: First release must be newer than second release.")
                        continue
                        
                    newer = production_releases[newer_idx]
                    older = production_releases[older_idx]
                    
                    console.print(f"\nComparing changes between:")
                    console.print(f"Newer: {newer['tag_name']}")
                    console.print(f"Older: {older['tag_name']}")
                    
                    changelog = generate_release_changelog(repository, newer, older['tag_name'])
                    console.print("\nChangelog:")
                    console.print(Markdown(changelog))
                    
                    # Create changelogs directory if it doesn't exist
                    os.makedirs("changelogs", exist_ok=True)
                    
                    # Save changelog to file with sanitized filename
                    safe_filename = f"comparison_{sanitize_filename(older['tag_name'])}_to_{sanitize_filename(newer['tag_name'])}"
                    filepath = os.path.join("changelogs", f"{safe_filename}.md")
                    with open(filepath, "w") as f:
                        f.write(f"# Changes from {older['tag_name']} to {newer['tag_name']}\n\n")
                        f.write(f"Comparison Date: {datetime.now().strftime('%Y-%m-%d')}\n\n")
                        f.write(changelog)
                    console.print(f"\nChangelog saved to: {filepath}")
                else:
                    console.print("Invalid selection. Please try again.")
            except ValueError:
                console.print("Invalid input. Please enter a number or 'q' to quit.")
            except Exception as e:
                console.print(f"Error processing comparison: {str(e)}")

if __name__ == "__main__":
    main() 