import os
import json
import tempfile
from verify_completion_gate import verify_completion

def test_missing_state_file():
    assert verify_completion("non_existent_file.json") == False

def test_not_complete_signal():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        json.dump({"exit_signal": "WORKING"}, f)
        temp_path = f.name
    
    assert verify_completion(temp_path) == False
    os.remove(temp_path)

def test_complete_no_artifacts_needed():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        json.dump({"exit_signal": "COMPLETE"}, f)
        temp_path = f.name
    
    assert verify_completion(temp_path) == True
    os.remove(temp_path)

def test_complete_missing_artifact_resets_signal():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        json.dump({"exit_signal": "COMPLETE"}, f)
        temp_path = f.name
    
    assert verify_completion(temp_path, ["missing_artifact.txt"]) == False
    
    with open(temp_path, "r") as f:
        state = json.load(f)
    assert state.get("exit_signal") is None
    os.remove(temp_path)

def test_complete_with_artifacts():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        json.dump({"exit_signal": "COMPLETE"}, f)
        temp_path = f.name
        
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as a:
        a.write("artifact data")
        artifact_path = a.name
    
    assert verify_completion(temp_path, [artifact_path]) == True
    
    os.remove(temp_path)
    os.remove(artifact_path)

if __name__ == '__main__':
    test_missing_state_file()
    test_not_complete_signal()
    test_complete_no_artifacts_needed()
    test_complete_missing_artifact_resets_signal()
    test_complete_with_artifacts()
    print('All tests passed.')
