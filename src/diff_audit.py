# Path: /mnt/sharedroot/projects/llm-userprofile/AUDIT/src/diff_audit.py

def dict_diff(old, new, path=""):
    """Recursively compares two dicts."""
    diffs = []
    keys = set(list(old.keys()) + list(new.keys()))
    
    for k in keys:
        p = f"{path}.{k}" if path else k
        if k not in old:
            diffs.append(f"ADDED: {p}")
        elif k not in new:
            diffs.append(f"REMOVED: {p}")
        elif old[k] != new[k]:
            if isinstance(old[k], dict) and isinstance(new[k], dict):
                diffs.extend(dict_diff(old[k], new[k], p))
            else:
                diffs.append(f"CHANGED: {p} ({old[k]} -> {new[k]})")
    return diffs
