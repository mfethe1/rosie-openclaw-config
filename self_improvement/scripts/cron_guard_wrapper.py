def check_exit_gate(completion_indicator, exit_signal):
    if completion_indicator and exit_signal:
        return True
    return False

def check_hourly_budget(calls_this_hour, max_calls_per_hour=50):
    if calls_this_hour >= max_calls_per_hour:
        return False
    return True

def run_with_guards(task_fn, completion_indicator_fn, check_exit_signal_fn, get_calls_fn):
    calls = get_calls_fn()
    if not check_hourly_budget(calls):
        raise Exception("Hourly budget exceeded")
    
    result = task_fn()
    
    comp_ind = completion_indicator_fn(result)
    ext_sig = check_exit_signal_fn(result)
    
    if check_exit_gate(comp_ind, ext_sig):
        return result, True
    return result, False
