#!/usr/bin/env python3
"""
Test script for detective and trolly problem fixes.
"""

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import detective_game, trolly_problem

def test_case_hash():
    """Test that case hash generation works and is unique."""
    print("Testing case hash generation...")
    
    case_data_1 = {
        'title': 'Test Case',
        'victim': 'John Doe',
        'suspects': [
            {'name': 'Alice'},
            {'name': 'Bob'},
            {'name': 'Charlie'},
            {'name': 'Dave'}
        ],
        'murderer_index': 0
    }
    
    case_data_2 = {
        'title': 'Test Case',
        'victim': 'John Doe',
        'suspects': [
            {'name': 'Alice'},
            {'name': 'Bob'},
            {'name': 'Charlie'},
            {'name': 'Dave'}
        ],
        'murderer_index': 0
    }
    
    case_data_3 = {
        'title': 'Different Case',
        'victim': 'Jane Doe',
        'suspects': [
            {'name': 'Alice'},
            {'name': 'Bob'},
            {'name': 'Charlie'},
            {'name': 'Dave'}
        ],
        'murderer_index': 1
    }
    
    hash1 = detective_game.compute_case_hash(case_data_1)
    hash2 = detective_game.compute_case_hash(case_data_2)
    hash3 = detective_game.compute_case_hash(case_data_3)
    
    assert hash1 == hash2, "Identical cases should have same hash"
    assert hash1 != hash3, "Different cases should have different hashes"
    assert len(hash1) == 64, "Hash should be SHA256 (64 hex chars)"
    
    print(f"✓ Case hash 1: {hash1[:16]}...")
    print(f"✓ Case hash 2: {hash2[:16]}...")
    print(f"✓ Case hash 3: {hash3[:16]}...")
    print("✓ Case hash generation works correctly!\n")

def test_problem_hash():
    """Test that trolly problem hash generation works and is unique."""
    print("Testing trolly problem hash generation...")
    
    problem_data_1 = {
        'scenario': 'A trolley is heading toward 5 people...',
        'option_a': 'Do nothing',
        'option_b': 'Pull the lever'
    }
    
    problem_data_2 = {
        'scenario': 'A trolley is heading toward 5 people...',
        'option_a': 'Do nothing',
        'option_b': 'Pull the lever'
    }
    
    problem_data_3 = {
        'scenario': 'Different scenario',
        'option_a': 'Different option A',
        'option_b': 'Different option B'
    }
    
    hash1 = trolly_problem.compute_problem_hash(problem_data_1)
    hash2 = trolly_problem.compute_problem_hash(problem_data_2)
    hash3 = trolly_problem.compute_problem_hash(problem_data_3)
    
    assert hash1 == hash2, "Identical problems should have same hash"
    assert hash1 != hash3, "Different problems should have different hashes"
    assert len(hash1) == 64, "Hash should be SHA256 (64 hex chars)"
    
    print(f"✓ Problem hash 1: {hash1[:16]}...")
    print(f"✓ Problem hash 2: {hash2[:16]}...")
    print(f"✓ Problem hash 3: {hash3[:16]}...")
    print("✓ Trolly problem hash generation works correctly!\n")

def test_murder_case_class():
    """Test MurderCase class instantiation."""
    print("Testing MurderCase class...")
    
    case_data = {
        'case_id': 1,
        'title': 'Test Murder',
        'description': 'A test murder case',
        'location': 'Test Location',
        'victim': 'Test Victim',
        'suspects': [
            {'name': 'Suspect 1', 'occupation': 'Job 1'},
            {'name': 'Suspect 2', 'occupation': 'Job 2'},
            {'name': 'Suspect 3', 'occupation': 'Job 3'},
            {'name': 'Suspect 4', 'occupation': 'Job 4'}
        ],
        'murderer_index': 2,
        'evidence': ['Evidence 1', 'Evidence 2'],
        'hints': ['Hint 1', 'Hint 2'],
        'difficulty': 3
    }
    
    case = detective_game.MurderCase(case_data)
    
    assert case.case_id == 1
    assert case.case_title == 'Test Murder'
    assert len(case.suspects) == 4
    assert case.murderer_index == 2
    assert case.is_correct_murderer(2) == True
    assert case.is_correct_murderer(0) == False
    assert case.get_suspect(2)['name'] == 'Suspect 3'
    
    print("✓ MurderCase class works correctly!\n")

def test_trolly_problem_class():
    """Test TrollyProblem class instantiation."""
    print("Testing TrollyProblem class...")
    
    problem_data = {
        'problem_id': 1,
        'scenario': 'Test scenario',
        'option_a': 'Option A',
        'option_b': 'Option B',
        'personalization_level': 'generic'
    }
    
    problem = trolly_problem.TrollyProblem(problem_data)
    
    assert problem.problem_id == 1
    assert problem.scenario == 'Test scenario'
    assert problem.option_a == 'Option A'
    assert problem.option_b == 'Option B'
    assert problem.personalization_level == 'generic'
    
    print("✓ TrollyProblem class works correctly!\n")

def main():
    """Run all tests."""
    print("=" * 60)
    print("Running Detective and Trolly Problem Fixes Tests")
    print("=" * 60 + "\n")
    
    try:
        test_case_hash()
        test_problem_hash()
        test_murder_case_class()
        test_trolly_problem_class()
        
        print("=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
