# zecho/jira_adapter.py
from typing import Protocol
import requests

class Adapter(Protocol):
    def upsert(self, meta: dict, body: str): ...
    def recently_changed(self) -> list: ...

class NoopAdapter:
    """Used when Jira is disabled. Pool stays file-only."""
    def upsert(self, meta: dict, body: str):
        return None
    def recently_changed(self) -> list:
        return []

class JiraAdapter:
    def __init__(self, base_url, project, email, token):
        self.base_url = base_url.rstrip("/")
        self.project = project
        self.auth = (email, token)

    def upsert(self, meta: dict, body: str):
        if meta.get("jira_key"):
            return meta["jira_key"]  # already synced (V1: no field update)
        payload = {"fields": {
            "project": {"key": self.project},
            "summary": meta.get("short_desc", meta["id"]),
            "description": body,
            "issuetype": {"name": "Bug"},
        }}
        r = requests.post(f"{self.base_url}/rest/api/2/issue",
                          json=payload, auth=self.auth, timeout=20)
        r.raise_for_status()
        return r.json()["key"]

    def recently_changed(self, minutes: int = 5) -> list:
        jql = (f'project={self.project} AND status CHANGED TO '
               f'(Done,Resolved,"Won' + "'" + 't Fix",Invalid) AFTER -{minutes}m')
        r = requests.get(f"{self.base_url}/rest/api/2/search",
                         params={"jql": jql, "fields": "status,resolution,fixVersions"},
                         auth=self.auth, timeout=20)
        r.raise_for_status()
        out = []
        for it in r.json().get("issues", []):
            f = it["fields"]
            fixed = f["fixVersions"][0]["name"] if f.get("fixVersions") else None
            out.append({"key": it["key"], "status": f["status"]["name"], "fixed_in": fixed})
        return out
