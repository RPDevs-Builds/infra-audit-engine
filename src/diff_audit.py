# Path: src/diff_audit.py

def dict_diff(old, new, path=""):
    """Recursively compares dicts, formatting large outputs to prevent terminal noise."""
    ignore_keys = {'collected_at', 'load_average', 'memory_active', 'ssh_keys_verified'}
    diffs = []
    if not old: return diffs
    
    reg_old = old.get("environment_registry", {})
    reg_new = new.get("environment_registry", {})
    
    def format_val(v):
        """Summarizes large structures and truncates strings for clean logging."""
        if isinstance(v, dict):
            return f"[Dictionary: {len(v)} keys]"
        elif isinstance(v, list):
            return f"[List: {len(v)} items]"
        
        v_str = str(v)
        return v_str if len(v_str) < 60 else v_str[:57] + "..."
    
    def recursive_compare(o_data, n_data, current_path):
        keys = set(list(o_data.keys()) + list(n_data.keys()))
        for k in keys:
            if k in ignore_keys: continue
            
            p = f"{current_path}.{k}" if current_path else k
            o_val = o_data.get(k)
            n_val = n_data.get(k)
            
            if k not in o_data:
                diffs.append(f"ADDED: {p} | VALUE: {format_val(n_val)}")
            elif k not in n_data:
                diffs.append(f"REMOVED: {p} | OLD VALUE: {format_val(o_val)}")
            elif o_val != n_val:
                if isinstance(o_val, dict) and isinstance(n_val, dict):
                    recursive_compare(o_val, n_val, p)
                else:
                    diffs.append(f"CHANGED: {p} | OLD: {format_val(o_val)} | NEW: {format_val(n_val)}")

    recursive_compare(reg_old, reg_new, "")
    return diffs
