# scripts/pool_jira.py
# NOTE: For new Jira integration, prefer using jira-cli (https://github.com/ankitpokhrel/jira-cli)
# See docs/jira-cli-integration.md for setup and usage guidance.

import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zecho import frontmatter as fm
from zecho import jira_adapter as ja

def build_adapter():
    if os.environ.get("JIRA_BASE_URL"):
        return ja.JiraAdapter(os.environ["JIRA_BASE_URL"], os.environ["JIRA_PROJECT"],
                              os.environ["JIRA_EMAIL"], os.environ["JIRA_TOKEN"])
    return ja.NoopAdapter()

def run(issue_path: str):
    meta, body = fm.load(issue_path)
    key = build_adapter().upsert(meta, body)
    if key and meta.get("jira_key") != key:
        meta["jira_key"] = key
        fm.save(issue_path, meta, body)
    return key

if __name__ == "__main__":
    print(run(sys.argv[1]))
